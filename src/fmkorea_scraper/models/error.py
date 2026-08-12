"""Adapter-facing error result contract."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from fmkorea_scraper.models.base import StrictBaseModel, validate_metadata


class ErrorResult(StrictBaseModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    safe_to_log: bool = True

    @field_validator("details")
    @classmethod
    def _validate_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
