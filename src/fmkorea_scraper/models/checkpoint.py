"""Checkpoint contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.enums import CheckpointStatus, JobType, StopReason
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey, utc_now


class CollectorCursor(MetadataModel):
    source_type: JobType
    page: int | None = Field(default=None, ge=1)
    board_id: str | None = Field(default=None, max_length=100)
    last_document_srl: int | None = Field(default=None, ge=0)
    last_url: str | None = Field(default=None, max_length=4096)


class Checkpoint(MetadataModel):
    schema_version: Literal["fmkorea.checkpoint.v1"] = "fmkorea.checkpoint.v1"
    job_id: str = Field(min_length=1, max_length=200)
    status: CheckpointStatus = CheckpointStatus.RUNNING
    reason: StopReason | None = None
    job_config: JobConfig
    collector_cursor: CollectorCursor | None = None
    completed_keys: list[PostKey] = Field(default_factory=list)
    queued_links: list[PostCandidate] | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_status_reason(self) -> "Checkpoint":
        if self.status == CheckpointStatus.STOPPED and self.reason is None:
            raise ValueError("reason is required when checkpoint is stopped")
        if self.status != CheckpointStatus.STOPPED and self.reason is not None:
            raise ValueError("reason must be null unless checkpoint is stopped")
        return self
