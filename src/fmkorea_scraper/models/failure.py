"""Failure record contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from fmkorea_scraper.models.base import MetadataModel, validate_metadata
from fmkorea_scraper.models.job import FailureInput, PostKey, utc_now


class FailureRecord(MetadataModel):
    schema_version: Literal["fmkorea.failure.v1"] = "fmkorea.failure.v1"
    job_id: str = Field(min_length=1, max_length=200)
    stage: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    retryable: bool = False
    url: str | None = Field(default=None, max_length=4096)
    post_key: PostKey | None = None
    safe_message: str = Field(min_length=1, max_length=1000)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("details")
    @classmethod
    def _validate_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)


__all__ = ["FailureInput", "FailureRecord"]
