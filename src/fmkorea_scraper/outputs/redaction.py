"""Safe failure context redaction."""

from __future__ import annotations

import re
from typing import Any

from fmkorea_scraper.models.base import validate_metadata

ALLOWED_FAILURE_DETAIL_KEYS = {
    "board_id",
    "code",
    "document_id_raw",
    "http_status",
    "job_id",
    "parser_stage",
    "reason",
    "request_url",
    "response_kind",
    "retryable",
    "stage",
    "warning_codes",
}

FORBIDDEN_KEY_PATTERN = re.compile(r"(authorization|body|content|cookie|credential|header|html|passwd|password|proxy|secret|token)", re.I)
FORBIDDEN_VALUE_PATTERN = re.compile(r"(authorization|cookie|passwd|password|secret|token)\s*[:=]", re.I)


def sanitize_failure_context(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    safe: dict[str, Any] = {}
    for key, value in details.items():
        if key not in ALLOWED_FAILURE_DETAIL_KEYS or FORBIDDEN_KEY_PATTERN.search(key):
            continue
        safe_value = _sanitize_value(value)
        if safe_value is not _DROP:
            safe[key] = safe_value
    return validate_metadata(safe)


class _Drop:
    pass


_DROP = _Drop()


def _sanitize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if FORBIDDEN_VALUE_PATTERN.search(value):
            return "[REDACTED]"
        return value[:1000]
    if isinstance(value, list):
        cleaned = [_sanitize_value(item) for item in value[:50]]
        return [item for item in cleaned if item is not _DROP]
    return _DROP


__all__ = ["ALLOWED_FAILURE_DETAIL_KEYS", "sanitize_failure_context"]
