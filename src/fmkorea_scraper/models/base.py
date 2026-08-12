"""Shared Pydantic base models and bounded metadata validation."""

from __future__ import annotations

import json
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_METADATA_DEPTH = 8
MAX_METADATA_BYTES = 8192


def empty_metadata() -> dict[str, Any]:
    return {}


def validate_metadata(
    value: dict[str, Any],
    *,
    max_depth: int = MAX_METADATA_DEPTH,
    max_bytes: int = MAX_METADATA_BYTES,
) -> dict[str, Any]:
    """Validate metadata is bounded and JSON-compatible."""
    if not isinstance(value, dict):
        raise TypeError("metadata must be a dict")
    _validate_json_value(value, depth=0, max_depth=max_depth)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata must be JSON-serializable") from exc
    if len(encoded) > max_bytes:
        raise ValueError("metadata is too large")
    return value


def _validate_json_value(value: Any, *, depth: int, max_depth: int) -> None:
    if depth > max_depth:
        raise ValueError("metadata is too deeply nested")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata float values must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1, max_depth=max_depth)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("metadata keys must be strings")
            _validate_json_value(item, depth=depth + 1, max_depth=max_depth)
        return
    raise TypeError("metadata values must be JSON-compatible primitives, lists, or dicts")


class StrictBaseModel(BaseModel):
    """Base model for public contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class MetadataModel(StrictBaseModel):
    """Base model with a bounded metadata extension point."""

    metadata: dict[str, Any] = Field(default_factory=empty_metadata)

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
