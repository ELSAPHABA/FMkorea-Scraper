"""Post worker and media coordination."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fmkorea_scraper.core.errors import NetworkFailureError
from fmkorea_scraper.models.enums import JobReportStatus, MediaMode, StopReason
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, StoredObjectRef
from fmkorea_scraper.runner.checkpointing import CheckpointCoordinator
from fmkorea_scraper.runner.models import CompletedKeyToken, JobRunDependencies, RunnerCounters, RunnerState
from fmkorea_scraper.runner.policies import (
    completed_key_map,
    failure_reason,
    failure_retryable,
    is_runner_fatal,
    post_key_from_candidate,
    post_key_token,
    report_status_for_failure,
    safe_failure_details,
    stop_reason_for_exception,
    unique_stored_refs,
)


class _QueueSentinel:
    pass


QUEUE_SENTINEL = _QueueSentinel()


class CompletedKeyTracker:
    def __init__(self, completed_keys: list[PostKey] | None = None) -> None:
        self._completed = completed_key_map(completed_keys or [])
        self._in_progress: set[CompletedKeyToken] = set()
        self._lock = asyncio.Lock()

    async def claim(self, key: PostKey) -> bool:
        token = post_key_token(key)
        async with self._lock:
            if token in self._completed or token in self._in_progress:
                return False
            self._in_progress.add(token)
            return True

    async def mark_completed(self, key: PostKey) -> None:
        token = post_key_token(key)
        async with self._lock:
            self._completed[token] = key
            self._in_progress.discard(token)

    async def release(self, key: PostKey) -> None:
        async with self._lock:
            self._in_progress.discard(post_key_token(key))

    def completed_keys(self) -> list[PostKey]:
        return list(self._completed.values())


class MediaDownloadCoordinator:
    def __init__(self, dependencies: JobRunDependencies, media_worker_count: int) -> None:
        self.dependencies = dependencies
        self._semaphore = asyncio.Semaphore(media_worker_count)

    async def process(self, post: PostResult, config: JobConfig) -> tuple[PostResult, int]:
        if not post.media:
            return post, 0
        mode = config.scrape_options.media_mode
        if mode == MediaMode.URL_ONLY:
            media = [await self.dependencies.media_store.save_metadata_only(_with_post_metadata(item, post)) for item in post.media]
            return post.model_copy(update={"media": media}), 0
        if self.dependencies.http is None:
            raise NetworkFailureError("http port is required for media download", details={"stage": "media"})
        saved: list[MediaItem] = []
        for item in post.media:
            item = _with_post_metadata(item, post)
            async with self._semaphore:
                content = await self.dependencies.http.download(item.url)
                saved.append(await self.dependencies.media_store.save_media(item, content))
        return post.model_copy(update={"media": saved}), len(saved)


def _with_post_metadata(item: MediaItem, post: PostResult) -> MediaItem:
    metadata = dict(item.metadata)
    metadata.setdefault("board_id", post.board_id)
    metadata.setdefault("document_id_raw", post.document_id_raw)
    return item.model_copy(update={"metadata": metadata})


class FailureRecorder:
    def __init__(self, dependencies: JobRunDependencies) -> None:
        self.dependencies = dependencies

    async def record(
        self,
        *,
        job_id: str,
        stage: str,
        exc: BaseException,
        url: str | None = None,
        post_key: PostKey | None = None,
    ) -> StoredObjectRef:
        reason = failure_reason(exc)
        retryable = failure_retryable(stage, exc)
        failure = FailureRecord(
            job_id=job_id,
            stage=stage,
            reason=reason,
            retryable=retryable,
            url=url,
            post_key=post_key,
            safe_message=str(getattr(exc, "safe_message", exc.__class__.__name__)),
            details=safe_failure_details(
                job_id=job_id,
                stage=stage,
                reason=reason,
                retryable=retryable,
                url=url,
                post_key=post_key,
            ),
        )
        return await self.dependencies.failure_store.write_failure(failure)


@dataclass(slots=True)
class OutputRefCollector:
    refs: list[StoredObjectRef] = field(default_factory=list)

    def add(self, ref: StoredObjectRef | None) -> None:
        if ref is not None:
            self.refs = unique_stored_refs([*self.refs, ref])


class ReportBuilder:
    def __init__(self, clock: Any, refs: OutputRefCollector) -> None:
        self.clock = clock
        self.refs = refs

    def build(self, state: RunnerState, counters: RunnerCounters) -> JobReport:
        return JobReport(
            job_id=state.job_config.job_id,
            status=state.status,
            started_at=state.started_at,
            finished_at=self.clock.now_utc(),
            collected_count=counters.collected_count,
            stored_count=counters.stored_count,
            failure_count=counters.failure_count,
            output_refs=self.refs.refs,
        )


class PostWorkerPool:
    def __init__(
        self,
        dependencies: JobRunDependencies,
        state: RunnerState,
        counters: RunnerCounters,
        tracker: CompletedKeyTracker,
        checkpoint_coordinator: CheckpointCoordinator,
        media_coordinator: MediaDownloadCoordinator,
        failure_recorder: FailureRecorder,
        refs: OutputRefCollector,
        stop_event: asyncio.Event,
    ) -> None:
        self.dependencies = dependencies
        self.state = state
        self.counters = counters
        self.tracker = tracker
        self.checkpoint_coordinator = checkpoint_coordinator
        self.media_coordinator = media_coordinator
        self.failure_recorder = failure_recorder
        self.refs = refs
        self.stop_event = stop_event

    async def run(self, queue: asyncio.Queue[PostCandidate | _QueueSentinel]) -> None:
        workers = [
            asyncio.create_task(self._worker(worker_id, queue))
            for worker_id in range(self.state.job_config.worker_config.post_worker_count)
        ]
        await asyncio.gather(*workers)

    async def _worker(self, worker_id: int, queue: asyncio.Queue[PostCandidate | _QueueSentinel]) -> None:
        _ = worker_id
        while True:
            item = await queue.get()
            try:
                if item is QUEUE_SENTINEL:
                    return
                if self.stop_event.is_set():
                    continue
                await self._process_candidate(item)
            finally:
                queue.task_done()

    async def _process_candidate(self, candidate: PostCandidate) -> None:
        key = post_key_from_candidate(candidate)
        if not await self.tracker.claim(key):
            self.counters.skipped_completed_count += 1
            return
        try:
            post = await self._parse(candidate, key)
            if post is None:
                return
            post = await self._process_media(post, candidate, key)
            if post is None:
                return
            ref = await self._append_post(post, candidate, key)
            if ref is None:
                return
            await self.tracker.mark_completed(key)
            self.counters.stored_count += 1
            self.refs.add(ref)
            await self._save_running_checkpoint(candidate, key)
        finally:
            await self.tracker.release(key)

    async def _parse(self, candidate: PostCandidate, key: PostKey) -> PostResult | None:
        try:
            return await self.dependencies.detail_service.parse(candidate)
        except Exception as exc:
            await self._handle_failure("post", exc, candidate, key)
            return None

    async def _process_media(self, post: PostResult, candidate: PostCandidate, key: PostKey) -> PostResult | None:
        try:
            post, media_stored = await self.media_coordinator.process(post, self.state.job_config)
            self.counters.media_stored_count += media_stored
            return post
        except Exception as exc:
            await self._handle_failure("media", exc, candidate, key)
            return None

    async def _append_post(self, post: PostResult, candidate: PostCandidate, key: PostKey) -> StoredObjectRef | None:
        try:
            return await self.dependencies.output_store.append_post(post)
        except Exception as exc:
            await self._handle_failure("output", exc, candidate, key)
            return None

    async def _save_running_checkpoint(self, candidate: PostCandidate, key: PostKey) -> None:
        try:
            await self.checkpoint_coordinator.save_running_if_due(
                self.state,
                self.counters,
                completed_keys=self.tracker.completed_keys(),
            )
        except Exception as exc:
            await self._handle_failure("checkpoint", exc, candidate, key)

    async def _handle_failure(self, stage: str, exc: BaseException, candidate: PostCandidate, key: PostKey) -> None:
        self.counters.failure_count += 1
        try:
            self.refs.add(
                await self.failure_recorder.record(
                    job_id=self.state.job_config.job_id,
                    stage=stage,
                    exc=exc,
                    url=candidate.url,
                    post_key=key,
                )
            )
        except Exception:
            self.state.set_terminal(JobReportStatus.FAILED, StopReason.ERROR)
            self.stop_event.set()
            return
        status = report_status_for_failure(stage, exc)
        if status != JobReportStatus.RUNNING:
            self.state.set_terminal(status, stop_reason_for_exception(exc) or StopReason.ERROR)
            self.stop_event.set()
        elif is_runner_fatal(stage, exc):
            self.state.set_terminal(JobReportStatus.FAILED, StopReason.ERROR)
            self.stop_event.set()


__all__ = [
    "CompletedKeyTracker",
    "FailureRecorder",
    "MediaDownloadCoordinator",
    "OutputRefCollector",
    "PostWorkerPool",
    "QUEUE_SENTINEL",
    "ReportBuilder",
]
