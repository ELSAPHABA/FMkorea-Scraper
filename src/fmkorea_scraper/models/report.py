"""Job report contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.enums import JobReportStatus, StorageMode
from fmkorea_scraper.models.job import utc_now


class StoredObjectRef(MetadataModel):
    storage_mode: StorageMode
    path: str | None = Field(default=None, max_length=4096)
    bucket: str | None = Field(default=None, max_length=255)
    object_key: str | None = Field(default=None, max_length=1024)


class JobReport(MetadataModel):
    schema_version: Literal["fmkorea.job_report.v1"] = "fmkorea.job_report.v1"
    job_id: str = Field(min_length=1, max_length=200)
    status: JobReportStatus
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    collected_count: int = Field(default=0, ge=0)
    stored_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    output_refs: list[StoredObjectRef] = Field(default_factory=list)


class RetryReport(JobReport):
    selected_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
