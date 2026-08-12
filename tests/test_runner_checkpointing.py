from __future__ import annotations

import asyncio

import pytest

from fmkorea_scraper.core.errors import CheckpointFailureError
from fmkorea_scraper.models.enums import JobReportStatus
from fmkorea_scraper.models.job import ResumeRequest
from fmkorea_scraper.runner.checkpointing import CheckpointCoordinator
from fmkorea_scraper.runner.models import RunnerState, SystemClock
from tests.test_runner_service import FakeCheckpointStore, job_config


def run(coro):
    return asyncio.run(coro)


class FailingCheckpointStore(FakeCheckpointStore):
    async def save(self, checkpoint) -> None:
        raise RuntimeError("disk full")


def test_load_for_resume_requires_existing_checkpoint() -> None:
    coordinator = CheckpointCoordinator(FakeCheckpointStore(), SystemClock())

    with pytest.raises(CheckpointFailureError):
        run(coordinator.load_for_resume(ResumeRequest(job_id="missing")))


def test_checkpoint_save_failure_is_mapped_to_checkpoint_failure() -> None:
    coordinator = CheckpointCoordinator(FailingCheckpointStore(), SystemClock())

    with pytest.raises(CheckpointFailureError):
        state = RunnerState(
            job_config=job_config(),
            run_id="run-1",
            started_at=SystemClock().now_utc(),
        )
        state.set_terminal(JobReportStatus.COMPLETED)
        run(coordinator.save_terminal(state, completed_keys=[]))
