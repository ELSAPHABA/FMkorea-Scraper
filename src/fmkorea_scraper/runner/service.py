"""Job runner orchestration service."""

from __future__ import annotations

import asyncio
import inspect
import uuid
from typing import Any

from fmkorea_scraper.core.errors import CheckpointFailureError
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.enums import JobReportStatus, StopReason
from fmkorea_scraper.models.job import JobConfig, PostCandidate, ResumeRequest
from fmkorea_scraper.models.report import JobReport
from fmkorea_scraper.runner.checkpointing import CheckpointCoordinator
from fmkorea_scraper.runner.models import JobRunDependencies, JobRunResult, RunnerCounters, RunnerState
from fmkorea_scraper.runner.policies import report_status_for_failure, stop_reason_for_exception
from fmkorea_scraper.runner.workers import (
    CompletedKeyTracker,
    FailureRecorder,
    MediaDownloadCoordinator,
    OutputRefCollector,
    PostWorkerPool,
    QUEUE_SENTINEL,
    ReportBuilder,
)


class JobRunner:
    def __init__(self, dependencies: JobRunDependencies) -> None:
        self.dependencies = dependencies
        self.clock = dependencies.resolved_clock()
        self._stop_event: asyncio.Event | None = None
        self._stop_reason: StopReason = StopReason.MANUAL_STOP

    def stop(self, reason: StopReason = StopReason.MANUAL_STOP) -> None:
        self._stop_reason = reason
        if self._stop_event is not None:
            self._stop_event.set()

    async def run(self, config: JobConfig, *, run_id: str | None = None) -> JobRunResult:
        return await self._run(config, resume_checkpoint=None, run_id=run_id)

    async def resume(self, request: ResumeRequest, *, run_id: str | None = None) -> JobRunResult:
        checkpoint = await CheckpointCoordinator(self.dependencies.checkpoint_store, self.clock).load_for_resume(request)
        return await self._run(checkpoint.job_config, resume_checkpoint=checkpoint, run_id=run_id)

    async def _run(self, config: JobConfig, *, resume_checkpoint: Checkpoint | None, run_id: str | None = None) -> JobRunResult:
        run_id = run_id or _new_run_id()
        counters = RunnerCounters()
        state = RunnerState(
            job_config=config,
            run_id=run_id,
            started_at=self.clock.now_utc(),
            collector_cursor=resume_checkpoint.collector_cursor if resume_checkpoint else None,
            queued_links=resume_checkpoint.queued_links if resume_checkpoint else None,
        )
        tracker = CompletedKeyTracker(resume_checkpoint.completed_keys if resume_checkpoint else [])
        stop_event = asyncio.Event()
        self._stop_event = stop_event
        checkpoint_coordinator = CheckpointCoordinator(self.dependencies.checkpoint_store, self.clock)
        failure_recorder = FailureRecorder(self.dependencies)
        refs = OutputRefCollector()
        media = MediaDownloadCoordinator(self.dependencies, config.worker_config.media_worker_count)
        queue: asyncio.Queue[PostCandidate | object] = asyncio.Queue(maxsize=config.worker_config.queue_max_size or 0)
        worker_pool = PostWorkerPool(
            self.dependencies,
            state,
            counters,
            tracker,
            checkpoint_coordinator,
            media,
            failure_recorder,
            refs,
            stop_event,
        )
        report_builder = ReportBuilder(self.clock, refs)
        terminal_checkpoint: Checkpoint | None = None
        try:
            collector_task = asyncio.create_task(
                self._collect(config, state, counters, queue, stop_event, failure_recorder, refs)
            )
            workers_task = asyncio.create_task(worker_pool.run(queue))
            await collector_task
            await queue.join()
            await workers_task
            self._finish_state(state, stop_event)
            terminal_checkpoint = await self._save_terminal_checkpoint(checkpoint_coordinator, state, tracker)
        except asyncio.CancelledError:
            state.set_terminal(JobReportStatus.STOPPED, StopReason.MANUAL_STOP)
            await self._save_terminal_checkpoint(checkpoint_coordinator, state, tracker, suppress=True)
            raise
        except Exception as exc:
            state.set_terminal(report_status_for_failure("runner", exc), stop_reason_for_exception(exc) or StopReason.ERROR)
            terminal_checkpoint = await self._save_terminal_checkpoint(checkpoint_coordinator, state, tracker, suppress=True)
        finally:
            self._stop_event = None
        report = report_builder.build(state, counters)
        await self._write_report(report, refs)
        await self._finalize_stores()
        return JobRunResult(
            job_id=config.job_id,
            run_id=run_id,
            status=state.status,
            reason=state.reason,
            report=report,
            checkpoint=terminal_checkpoint,
            stored_count=counters.stored_count,
            failure_count=counters.failure_count,
            skipped_count=counters.skipped_completed_count,
            output_refs=refs.refs,
        )

    async def _collect(
        self,
        config: JobConfig,
        state: RunnerState,
        counters: RunnerCounters,
        queue: asyncio.Queue[PostCandidate | object],
        stop_event: asyncio.Event,
        failure_recorder: FailureRecorder,
        refs: OutputRefCollector,
    ) -> None:
        try:
            for candidate in state.queued_links or []:
                if stop_event.is_set():
                    break
                if await _put_stop_aware(queue, candidate, stop_event):
                    counters.collected_count += 1
                    counters.queued_count += 1
            async for candidate in self.dependencies.collector.collect(config.source):
                if stop_event.is_set():
                    break
                if await _put_stop_aware(queue, candidate, stop_event):
                    counters.collected_count += 1
                    counters.queued_count += 1
                else:
                    break
        except Exception as exc:
            counters.failure_count += 1
            try:
                refs.add(
                    await failure_recorder.record(
                        job_id=config.job_id,
                        stage="collect",
                        exc=exc,
                    )
                )
            finally:
                state.set_terminal(report_status_for_failure("collect", exc), stop_reason_for_exception(exc) or StopReason.ERROR)
                stop_event.set()
        finally:
            for _ in range(config.worker_config.post_worker_count):
                await queue.put(QUEUE_SENTINEL)

    def _finish_state(self, state: RunnerState, stop_event: asyncio.Event) -> None:
        if state.status != JobReportStatus.RUNNING:
            return
        if stop_event.is_set():
            state.set_terminal(JobReportStatus.STOPPED, self._stop_reason)
        else:
            state.set_terminal(JobReportStatus.COMPLETED)

    async def _save_terminal_checkpoint(
        self,
        checkpoint_coordinator: CheckpointCoordinator,
        state: RunnerState,
        tracker: CompletedKeyTracker,
        *,
        suppress: bool = False,
    ) -> Checkpoint | None:
        try:
            return await checkpoint_coordinator.save_terminal(state, completed_keys=tracker.completed_keys())
        except CheckpointFailureError:
            if not suppress:
                raise
        except Exception:
            if not suppress:
                raise
        return None

    async def _write_report(self, report: JobReport, refs: OutputRefCollector) -> None:
        try:
            refs.add(await self.dependencies.output_store.write_report(report))
        except Exception:
            return

    async def _finalize_stores(self) -> None:
        for store in (self.dependencies.output_store, self.dependencies.failure_store):
            finalize = getattr(store, "finalize", None)
            if finalize is None:
                continue
            result = finalize()
            if inspect.isawaitable(result):
                await result


async def _put_stop_aware(
    queue: asyncio.Queue[PostCandidate | object],
    item: PostCandidate,
    stop_event: asyncio.Event,
) -> bool:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(queue.put(item), timeout=0.1)
            return True
        except asyncio.TimeoutError:
            continue
    return False


def _new_run_id() -> str:
    return f"run-{uuid.uuid4().hex}"


__all__ = ["JobRunner"]
