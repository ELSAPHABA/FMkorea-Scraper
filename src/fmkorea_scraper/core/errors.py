"""Typed core exceptions and adapter-safe error mapping."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from fmkorea_scraper.models.error import ErrorResult


class ScraperError(Exception):
    code = "scraper_error"
    retryable = False

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.safe_message = message or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.safe_message)


class ValidationFailure(ScraperError):
    code = "validation_error"


class UnsupportedSourceError(ScraperError):
    code = "unsupported_source"


class UnavailableContentError(ScraperError):
    code = "unavailable_content"


class CaptchaDetectedError(ScraperError):
    code = "captcha_detected"
    retryable = True


class BlockedResponseError(ScraperError):
    code = "blocked_response"
    retryable = True


class NetworkFailureError(ScraperError):
    code = "network_failure"
    retryable = True


class ParseFailureError(ScraperError):
    code = "parse_failure"


class StorageFailureError(ScraperError):
    code = "storage_failure"
    retryable = True


class CheckpointFailureError(ScraperError):
    code = "checkpoint_failure"
    retryable = True


class SecretRedactor:
    """Allowlist-based details redactor."""

    allowed_keys = {
        "code",
        "field_path",
        "reason",
        "retryable",
        "schema_version",
        "source_type",
        "stage",
    }
    secret_key_pattern = re.compile(r"(password|passwd|token|cookie|secret|credential|proxy_pw|env)", re.I)
    secret_value_pattern = re.compile(
        r"(password|passwd|token|cookie|secret|authorization|fmkorea_proxy_pw)\s*[:=]",
        re.I,
    )

    @classmethod
    def redact(cls, details: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in details.items():
            if key not in cls.allowed_keys or cls.secret_key_pattern.search(key):
                continue
            if isinstance(value, str) and cls.secret_value_pattern.search(value):
                safe[key] = "[REDACTED]"
            else:
                safe[key] = value
        return safe


class ErrorMapper:
    """Map exceptions to adapter-facing `ErrorResult`."""

    @classmethod
    def map(cls, exc: Exception, *, stage: str | None = None) -> ErrorResult:
        if isinstance(exc, ScraperError):
            details = {"reason": exc.safe_message, **exc.details}
            if stage:
                details["stage"] = stage
            return ErrorResult(
                code=exc.code,
                message=exc.safe_message,
                details=SecretRedactor.redact(details),
                retryable=exc.retryable,
                safe_to_log=True,
            )
        if isinstance(exc, PydanticValidationError):
            first = exc.errors(include_url=False, include_input=False)[0]
            details = {
                "field_path": ".".join(str(part) for part in first.get("loc", ())),
                "reason": first.get("msg", "validation failed"),
            }
            if stage:
                details["stage"] = stage
            return ErrorResult(
                code="validation_error",
                message="validation failed",
                details=SecretRedactor.redact(details),
                retryable=False,
                safe_to_log=True,
            )
        details = {"reason": exc.__class__.__name__}
        if stage:
            details["stage"] = stage
        return ErrorResult(
            code="internal_error",
            message="internal error",
            details=SecretRedactor.redact(details),
            retryable=False,
            safe_to_log=False,
        )
