"""Runner value objects."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fmkorea_scraper.core.ports import (
    CheckpointStorePort,
    ClockPort,
    FailureStorePort,
    HttpPort,
    LoggerPort,
    MediaStorePort,
    OutputStorePort,
)
from fmkorea_scraper.models.checkpoint import Checkpoint, CollectorCursor
from fmkorea_scraper.models.enums import JobReportStatus, StopReason
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey, utc_now
from fmkorea_scraper.models.report import JobReport, StoredObjectRef


class SystemClock:
    def now_utc(self) -> datetime:
        return utc_now()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


@dataclass(slots=True)
class JobRunDependencies:
    collector: Any
    detail_service: Any
    output_store: OutputStorePort
    failure_store: FailureStorePort
    media_store: MediaStorePort
    checkpoint_store: CheckpointStorePort
    http: HttpPort | None = None
    clock: ClockPort | None = None
    logger: LoggerPort | None = None

    def resolved_clock(self) -> ClockPort:
        return self.clock or SystemClock()


@dataclass(slots=True)
class RunnerCounters:
    collected_count: int = 0
    queued_count: int = 0
    skipped_completed_count: int = 0
    stored_count: int = 0
    failure_count: int = 0
    media_stored_count: int = 0


@dataclass(slots=True)
class RunnerState:
    job_config: JobConfig
    run_id: str
    started_at: datetime
    status: JobReportStatus = JobReportStatus.RUNNING
    reason: StopReason | None = None
    collector_cursor: CollectorCursor | None = None
    queued_links: list[PostCandidate] | None = None
    last_checkpoint_stored_count: int = 0

    def set_terminal(self, status: JobReportStatus, reason: StopReason | None = None) -> None:
        if self.status != JobReportStatus.RUNNING:
            return
        self.status = status
        self.reason = reason


@dataclass(slots=True)
class JobRunResult:
    job_id: str
    run_id: str
    status: JobReportStatus
    reason: StopReason | None
    report: JobReport
    checkpoint: Checkpoint | None
    stored_count: int
    failure_count: int
    skipped_count: int
    output_refs: list[StoredObjectRef] = field(default_factory=list)


CompletedKeyToken = tuple[str, str | None, int | None, str]


__all__ = [
    "CompletedKeyToken",
    "JobRunDependencies",
    "JobRunResult",
    "RunnerCounters",
    "RunnerState",
    "SystemClock",
]
