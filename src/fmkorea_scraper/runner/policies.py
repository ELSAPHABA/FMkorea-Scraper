"""Pure runner policies."""

from __future__ import annotations

from typing import Any

from fmkorea_scraper.core.errors import (
    BlockedResponseError,
    CaptchaDetectedError,
    CheckpointFailureError,
    ParseFailureError,
    ScraperError,
    StorageFailureError,
)
from fmkorea_scraper.models.enums import CheckpointStatus, JobReportStatus, StopReason
from fmkorea_scraper.models.job import PostCandidate, PostKey
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import StoredObjectRef
from fmkorea_scraper.outputs.redaction import sanitize_failure_context
from fmkorea_scraper.runner.models import CompletedKeyToken, RunnerCounters

CHECKPOINT_SUCCESS_INTERVAL = 10


def post_key_from_candidate(candidate: PostCandidate) -> PostKey:
    return PostKey(
        site_id=candidate.site_id,
        board_id=candidate.board_id,
        document_srl=candidate.document_srl,
        document_id_raw=candidate.document_id_raw,
    )


def post_key_from_result(post: PostResult) -> PostKey:
    return PostKey(
        site_id=post.site_id,
        board_id=post.board_id,
        document_srl=post.document_srl,
        document_id_raw=post.document_id_raw,
    )


def post_key_token(key: PostKey) -> CompletedKeyToken:
    return (key.site_id, key.board_id, key.document_srl, key.document_id_raw)


def completed_key_map(keys: list[PostKey]) -> dict[CompletedKeyToken, PostKey]:
    return {post_key_token(key): key for key in keys}


def should_save_running_checkpoint(
    stored_count: int,
    last_checkpoint_stored_count: int,
    *,
    interval: int = CHECKPOINT_SUCCESS_INTERVAL,
) -> bool:
    return stored_count > 0 and stored_count - last_checkpoint_stored_count >= interval


def checkpoint_status_for_report(status: JobReportStatus) -> CheckpointStatus:
    if status == JobReportStatus.COMPLETED:
        return CheckpointStatus.COMPLETED
    return CheckpointStatus.STOPPED


def stop_reason_for_exception(exc: BaseException) -> StopReason | None:
    if isinstance(exc, CaptchaDetectedError):
        return StopReason.CAPTCHA
    if isinstance(exc, BlockedResponseError):
        return StopReason.BLOCKED
    if isinstance(exc, CheckpointFailureError):
        return StopReason.ERROR
    return None


def is_runner_fatal(stage: str, exc: BaseException) -> bool:
    if stop_reason_for_exception(exc) is not None:
        return True
    return stage in {"checkpoint", "output", "runner"} or isinstance(exc, StorageFailureError)


def report_status_for_failure(stage: str, exc: BaseException) -> JobReportStatus:
    reason = stop_reason_for_exception(exc)
    if reason in {StopReason.CAPTCHA, StopReason.BLOCKED, StopReason.TIMEOUT, StopReason.MANUAL_STOP}:
        return JobReportStatus.STOPPED
    if is_runner_fatal(stage, exc):
        return JobReportStatus.FAILED
    return JobReportStatus.RUNNING


def failure_retryable(stage: str, exc: BaseException) -> bool:
    if isinstance(exc, ParseFailureError):
        return True
    if stage in {"checkpoint", "output"}:
        return True
    return bool(getattr(exc, "retryable", False))


def failure_reason(exc: BaseException) -> str:
    return str(getattr(exc, "code", exc.__class__.__name__))


def safe_failure_details(
    *,
    job_id: str,
    stage: str,
    reason: str,
    retryable: bool,
    url: str | None = None,
    post_key: PostKey | None = None,
    response_kind: str | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "job_id": job_id,
        "stage": stage,
        "reason": reason,
        "retryable": retryable,
        "request_url": url,
        "response_kind": response_kind,
    }
    if post_key is not None:
        details["board_id"] = post_key.board_id
        details["document_id_raw"] = post_key.document_id_raw
    return sanitize_failure_context(details)


def report_counter_consistency(counters: RunnerCounters) -> bool:
    return counters.collected_count >= counters.stored_count + counters.skipped_completed_count


def stored_ref_token(ref: StoredObjectRef) -> tuple[str, str | None, str | None, str | None]:
    return (ref.storage_mode.value, ref.path, ref.bucket, ref.object_key)


def unique_stored_refs(refs: list[StoredObjectRef]) -> list[StoredObjectRef]:
    seen: set[tuple[str, str | None, str | None, str | None]] = set()
    unique: list[StoredObjectRef] = []
    for ref in refs:
        token = stored_ref_token(ref)
        if token in seen:
            continue
        seen.add(token)
        unique.append(ref)
    return unique


__all__ = [
    "CHECKPOINT_SUCCESS_INTERVAL",
    "checkpoint_status_for_report",
    "completed_key_map",
    "failure_reason",
    "failure_retryable",
    "is_runner_fatal",
    "post_key_from_candidate",
    "post_key_from_result",
    "post_key_token",
    "report_counter_consistency",
    "report_status_for_failure",
    "safe_failure_details",
    "should_save_running_checkpoint",
    "stop_reason_for_exception",
    "unique_stored_refs",
]
