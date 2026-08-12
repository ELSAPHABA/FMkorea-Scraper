"""Output and storage exceptions."""

from __future__ import annotations

from typing import Any

from fmkorea_scraper.core.errors import StorageFailureError


class OutputStorageError(StorageFailureError):
    """Base class for UOW-006 storage failures."""


class StorageConfigurationError(OutputStorageError):
    """Raised when a selected storage backend is not configured."""

    retryable = False


class PathTraversalError(OutputStorageError):
    """Raised when a generated local path escapes the configured base path."""

    retryable = False


class StorageReadError(OutputStorageError):
    """Raised when stored data cannot be loaded."""


class StorageWriteError(OutputStorageError):
    """Raised when output data cannot be written."""


def safe_error_details(**details: Any) -> dict[str, Any]:
    return {key: value for key, value in details.items() if value is not None}


__all__ = [
    "OutputStorageError",
    "PathTraversalError",
    "StorageConfigurationError",
    "StorageReadError",
    "StorageWriteError",
    "safe_error_details",
]
