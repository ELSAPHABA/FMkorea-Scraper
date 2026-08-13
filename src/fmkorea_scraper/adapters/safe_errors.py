"""Shared safe adapter error payloads."""

from __future__ import annotations

from fmkorea_scraper.core.errors import ErrorMapper


def safe_error_payload(exc: Exception, *, stage: str | None = None) -> dict[str, object]:
    return ErrorMapper.map(exc, stage=stage).model_dump(mode="json")
