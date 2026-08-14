"""Common analytics/operations normalization helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey
from fmkorea_scraper.models.report import JobReport, StoredObjectRef


class NormalizedRunReport(MetadataModel):
    schema_version: Literal["community.run_report.v1"] = "community.run_report.v1"
    scraper_id: str | None = Field(default=None, max_length=100)
    site_id: str = Field(min_length=1, max_length=50)
    job_id: str = Field(min_length=1, max_length=200)
    run_id: str | None = Field(default=None, max_length=200)
    status: str = Field(min_length=1, max_length=100)
    stop_reason: str | None = Field(default=None, max_length=100)
    started_at: datetime
    finished_at: datetime | None = None
    candidate_seen_count: int | None = Field(default=None, ge=0)
    candidate_collected_count: int | None = Field(default=None, ge=0)
    post_stored_count: int | None = Field(default=None, ge=0)
    failure_count: int = Field(default=0, ge=0)
    duplicate_skipped_count: int | None = Field(default=None, ge=0)
    range_filtered_count: int | None = Field(default=None, ge=0)
    output_ref_count: int = Field(default=0, ge=0)
    output_refs: list[dict[str, Any]] = Field(default_factory=list)
    native_report: dict[str, Any]


class NormalizedCheckpoint(MetadataModel):
    schema_version: Literal["community.checkpoint.v1"] = "community.checkpoint.v1"
    scraper_id: str | None = Field(default=None, max_length=100)
    site_id: str = Field(min_length=1, max_length=50)
    job_id: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=100)
    stop_reason: str | None = Field(default=None, max_length=100)
    updated_at: datetime
    collector_page: int | None = Field(default=None, ge=1)
    collector_board_id: str | None = Field(default=None, max_length=100)
    collector_cursor_value: str | None = Field(default=None, max_length=4096)
    last_completed_post_key: str | None = Field(default=None, max_length=500)
    processed_count: int | None = Field(default=None, ge=0)
    lease_until: datetime | None = None
    worker_id: str | None = Field(default=None, max_length=100)
    job_config: dict[str, Any]
    native_checkpoint: dict[str, Any]


class NormalizedCheckpointCompletedPost(MetadataModel):
    schema_version: Literal["community.checkpoint_completed_post.v1"] = "community.checkpoint_completed_post.v1"
    scraper_id: str | None = Field(default=None, max_length=100)
    site_id: str = Field(min_length=1, max_length=50)
    job_id: str = Field(min_length=1, max_length=200)
    post_key: str = Field(min_length=1, max_length=500)
    board_id: str | None = Field(default=None, max_length=100)
    post_id: str | None = Field(default=None, max_length=100)
    completed_at: datetime | None = None
    native_key: dict[str, Any]


class NormalizedCheckpointPendingQueue(MetadataModel):
    schema_version: Literal["community.checkpoint_pending_queue.v1"] = "community.checkpoint_pending_queue.v1"
    scraper_id: str | None = Field(default=None, max_length=100)
    site_id: str = Field(min_length=1, max_length=50)
    job_id: str = Field(min_length=1, max_length=200)
    queue_order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    board_id: str | None = Field(default=None, max_length=100)
    post_id: str | None = Field(default=None, max_length=100)
    candidate_payload: dict[str, Any]


class NormalizedCheckpointBundle(MetadataModel):
    checkpoint: NormalizedCheckpoint
    completed_posts: list[NormalizedCheckpointCompletedPost] = Field(default_factory=list)
    pending_queue: list[NormalizedCheckpointPendingQueue] = Field(default_factory=list)


def normalize_job_report(
    report: JobReport,
    *,
    run_id: str | None = None,
    scraper_id: str | None = None,
) -> NormalizedRunReport:
    output_refs = [_dump(ref) for ref in report.output_refs]
    return NormalizedRunReport(
        scraper_id=scraper_id,
        site_id="fmkorea",
        job_id=report.job_id,
        run_id=run_id or _run_id_from_refs(report.job_id, report.output_refs),
        status=_value(report.status) or "unknown",
        stop_reason=None,
        started_at=report.started_at,
        finished_at=report.finished_at,
        candidate_seen_count=report.collected_count,
        candidate_collected_count=report.collected_count,
        post_stored_count=report.stored_count,
        failure_count=report.failure_count,
        duplicate_skipped_count=None,
        range_filtered_count=None,
        output_ref_count=len(output_refs),
        output_refs=output_refs,
        metadata=dict(report.metadata),
        native_report=report.model_dump(mode="json"),
    )


def normalize_checkpoint(checkpoint: Checkpoint, *, scraper_id: str | None = None) -> NormalizedCheckpointBundle:
    site_id = "fmkorea"
    job_config = checkpoint.job_config
    completed = [
        _completed_row(key, job_id=checkpoint.job_id, site_id=site_id, scraper_id=scraper_id)
        for key in checkpoint.completed_keys
    ]
    pending = [
        _pending_row(candidate, index, job_id=checkpoint.job_id, site_id=site_id, scraper_id=scraper_id)
        for index, candidate in enumerate(checkpoint.queued_links or [])
    ]
    cursor = checkpoint.collector_cursor
    common = NormalizedCheckpoint(
        scraper_id=scraper_id,
        site_id=site_id,
        job_id=checkpoint.job_id,
        status=_value(checkpoint.status) or "unknown",
        stop_reason=_value(checkpoint.reason),
        updated_at=checkpoint.updated_at,
        collector_page=cursor.page if cursor else None,
        collector_board_id=(cursor.board_id if cursor else None) or _source_board_id(job_config),
        collector_cursor_value=_cursor_value(cursor),
        last_completed_post_key=completed[-1].post_key if completed else None,
        processed_count=len(completed),
        lease_until=None,
        worker_id=None,
        job_config=job_config.model_dump(mode="json"),
        native_checkpoint=checkpoint.model_dump(mode="json"),
        metadata=dict(checkpoint.metadata),
    )
    return NormalizedCheckpointBundle(checkpoint=common, completed_posts=completed, pending_queue=pending)


def _completed_row(
    key: PostKey,
    *,
    job_id: str,
    site_id: str,
    scraper_id: str | None,
) -> NormalizedCheckpointCompletedPost:
    post_id = _candidate_id(document_srl=key.document_srl, document_id_raw=key.document_id_raw)
    return NormalizedCheckpointCompletedPost(
        scraper_id=scraper_id,
        site_id=site_id,
        job_id=job_id,
        post_key=_post_key(key.site_id, key.board_id, post_id),
        board_id=key.board_id,
        post_id=post_id,
        native_key=key.model_dump(mode="json"),
    )


def _pending_row(
    candidate: PostCandidate,
    index: int,
    *,
    job_id: str,
    site_id: str,
    scraper_id: str | None,
) -> NormalizedCheckpointPendingQueue:
    post_id = _candidate_id(document_srl=candidate.document_srl, document_id_raw=candidate.document_id_raw)
    return NormalizedCheckpointPendingQueue(
        scraper_id=scraper_id,
        site_id=site_id,
        job_id=job_id,
        queue_order=index,
        url=candidate.url,
        board_id=candidate.board_id,
        post_id=post_id,
        candidate_payload=candidate.model_dump(mode="json"),
    )


def _source_board_id(config: JobConfig) -> str | None:
    return getattr(config.source, "board_id", None)


def _cursor_value(cursor: Any | None) -> str | None:
    if cursor is None:
        return None
    if cursor.last_url:
        return cursor.last_url
    if cursor.last_document_srl is not None:
        return str(cursor.last_document_srl)
    return None


def _candidate_id(*, document_srl: int | None, document_id_raw: str | None) -> str | None:
    if document_srl is not None:
        return str(document_srl)
    return document_id_raw


def _run_id_from_refs(job_id: str, refs: list[StoredObjectRef]) -> str | None:
    for ref in refs:
        for value in (ref.object_key, ref.path):
            run_id = _run_id_from_path(job_id, value)
            if run_id:
                return run_id
    return None


def _run_id_from_path(job_id: str, value: str | None) -> str | None:
    parts = str(value or "").replace("\\", "/").split("/")
    for index, part in enumerate(parts[:-2]):
        if part == "outputs" and parts[index + 1] == job_id:
            return parts[index + 2]
    return None


def _post_key(site_id: str | None, board_id: str | None, post_id: str | None) -> str:
    return ":".join((site_id or "", board_id or "", post_id or ""))


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))

