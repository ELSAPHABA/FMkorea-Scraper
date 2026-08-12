"""Validation facades used by adapters."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.models.base import validate_metadata
from fmkorea_scraper.models.job import JobConfig


class MetadataValidator:
    """Facade for bounded metadata validation."""

    @staticmethod
    def validate(value: dict[str, Any], *, max_depth: int = 8, max_bytes: int = 8192) -> dict[str, Any]:
        return validate_metadata(value, max_depth=max_depth, max_bytes=max_bytes)


class JobConfigValidator:
    """Normalize adapter input into a validated `JobConfig`."""

    @staticmethod
    def validate(raw: JobConfig | dict[str, Any]) -> JobConfig:
        if isinstance(raw, JobConfig):
            return raw
        try:
            return JobConfig.model_validate(raw)
        except PydanticValidationError as exc:
            first = exc.errors(include_url=False, include_input=False)[0]
            source = raw.get("source", {}) if isinstance(raw, dict) else {}
            raise ValidationFailure(
                "invalid job config",
                details={
                    "field_path": ".".join(str(part) for part in first.get("loc", ())),
                    "reason": first.get("msg", "validation failed"),
                    "source_type": source.get("type"),
                },
            ) from exc
