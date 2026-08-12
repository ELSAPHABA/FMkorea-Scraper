"""Checkpoint coordination for runner state."""

from __future__ import annotations

from fmkorea_scraper.core.errors import CheckpointFailureError
from fmkorea_scraper.core.ports import CheckpointStorePort, ClockPort
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.enums import CheckpointStatus, JobReportStatus, StopReason
from fmkorea_scraper.models.job import ResumeRequest, PostKey
from fmkorea_scraper.runner.models import RunnerCounters, RunnerState
from fmkorea_scraper.runner.policies import checkpoint_status_for_report, should_save_running_checkpoint


class CheckpointCoordinator:
    def __init__(self, store: CheckpointStorePort, clock: ClockPort) -> None:
        self.store = store
        self.clock = clock

    async def load_for_resume(self, request: ResumeRequest) -> Checkpoint:
        try:
            checkpoint = await self.store.load(request.job_id) if request.job_id else await self.store.load_latest()
        except Exception as exc:
            raise CheckpointFailureError(
                "failed to load checkpoint",
                details={"stage": "checkpoint", "reason": exc.__class__.__name__},
            ) from exc
        if checkpoint is None:
            raise CheckpointFailureError("checkpoint not found", details={"stage": "checkpoint"})
        return checkpoint

    async def save_running_if_due(
        self,
        state: RunnerState,
        counters: RunnerCounters,
        *,
        completed_keys: list[PostKey],
    ) -> Checkpoint | None:
        if not should_save_running_checkpoint(counters.stored_count, state.last_checkpoint_stored_count):
            return None
        checkpoint = self.build_checkpoint(
            state,
            completed_keys=completed_keys,
            status=CheckpointStatus.RUNNING,
            reason=None,
        )
        await self._save(checkpoint)
        state.last_checkpoint_stored_count = counters.stored_count
        return checkpoint

    async def save_terminal(
        self,
        state: RunnerState,
        *,
        completed_keys: list[PostKey],
    ) -> Checkpoint:
        checkpoint_status = checkpoint_status_for_report(state.status)
        reason = state.reason if checkpoint_status == CheckpointStatus.STOPPED else None
        if checkpoint_status == CheckpointStatus.STOPPED and reason is None:
            reason = StopReason.ERROR if state.status == JobReportStatus.FAILED else StopReason.MANUAL_STOP
        checkpoint = self.build_checkpoint(
            state,
            completed_keys=completed_keys,
            status=checkpoint_status,
            reason=reason,
        )
        await self._save(checkpoint)
        return checkpoint

    def build_checkpoint(
        self,
        state: RunnerState,
        *,
        completed_keys: list[PostKey],
        status: CheckpointStatus,
        reason: StopReason | None,
    ) -> Checkpoint:
        return Checkpoint(
            job_id=state.job_config.job_id,
            status=status,
            reason=reason,
            job_config=state.job_config,
            collector_cursor=state.collector_cursor,
            completed_keys=completed_keys,
            queued_links=state.queued_links,
            updated_at=self.clock.now_utc(),
        )

    async def _save(self, checkpoint: Checkpoint) -> None:
        try:
            await self.store.save(checkpoint)
        except CheckpointFailureError:
            raise
        except Exception as exc:
            raise CheckpointFailureError(
                "failed to save checkpoint",
                details={"stage": "checkpoint", "reason": exc.__class__.__name__},
            ) from exc


__all__ = ["CheckpointCoordinator"]
