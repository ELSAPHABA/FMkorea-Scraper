"""Local filesystem output stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fmkorea_scraper.models.enums import StorageMode
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import FailureInput
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, StoredObjectRef
from fmkorea_scraper.outputs.errors import StorageReadError, StorageWriteError, safe_error_details
from fmkorea_scraper.outputs.jsonl import AtomicJsonWriter, JsonlWriter
from fmkorea_scraper.outputs.layout import OutputRunLayout, ensure_under_base
from fmkorea_scraper.outputs.redaction import sanitize_failure_context


class LocalOutputStore:
    def __init__(self, layout: OutputRunLayout) -> None:
        self.layout = layout
        self._posts = JsonlWriter(layout.posts_path)
        self._json = AtomicJsonWriter()

    async def append_post(self, post: PostResult) -> StoredObjectRef:
        self._posts.append(post)
        return self._ref(self.layout.posts_path, self.layout.posts_key)

    async def write_report(self, report: JobReport) -> StoredObjectRef:
        self._json.write(self.layout.report_path, report)
        return self._ref(self.layout.report_path, self.layout.report_key)

    async def finalize(self) -> None:
        self._posts.close()

    @staticmethod
    def _ref(path: Path, object_key: str) -> StoredObjectRef:
        return StoredObjectRef(storage_mode=StorageMode.LOCAL, path=str(path), object_key=object_key)


class LocalFailureStore:
    def __init__(self, layout: OutputRunLayout) -> None:
        self.layout = layout
        self._failures = JsonlWriter(layout.failures_path)

    async def write_failure(self, failure: FailureRecord) -> StoredObjectRef:
        safe_failure = failure.model_copy(update={"details": sanitize_failure_context(failure.details)})
        self._failures.append(safe_failure)
        return StoredObjectRef(storage_mode=StorageMode.LOCAL, path=str(self.layout.failures_path), object_key=self.layout.failures_key)

    async def read_failures(self, failure_input: FailureInput | Any) -> list[FailureRecord]:
        path = self._input_path(failure_input)
        records = _read_failure_records(path)
        job_id = getattr(failure_input, "job_id", None)
        stage_allowlist = getattr(failure_input, "stage_allowlist", None)
        return _filter_failures(records, job_id=job_id, stage_allowlist=stage_allowlist)

    async def finalize(self) -> None:
        self._failures.close()

    def _input_path(self, failure_input: FailureInput | Any) -> Path:
        raw_path = getattr(failure_input, "failure_path", str(self.layout.failures_path))
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.layout.base_path / path
        return ensure_under_base(self.layout.base_path, path)


class LocalMediaStore:
    def __init__(self, layout: OutputRunLayout, *, board_id: str | None = None, document_id_raw: str | None = None) -> None:
        self.layout = layout
        self.board_id = board_id
        self.document_id_raw = document_id_raw

    async def save_media(self, item: MediaItem, content: bytes) -> MediaItem:
        path = self.layout.media_path(item, board_id=self.board_id, document_id_raw=self.document_id_raw)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except Exception as exc:
            raise StorageWriteError(
                "failed to write media",
                details=safe_error_details(path=str(path), error=exc.__class__.__name__),
            ) from exc
        return item.model_copy(update={"file_path": str(path)})

    async def save_metadata_only(self, item: MediaItem) -> MediaItem:
        return item


def _read_failure_records(path: Path) -> list[FailureRecord]:
    if not path.exists():
        return []
    records: list[FailureRecord] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(FailureRecord.model_validate(json.loads(line)))
    except Exception as exc:
        raise StorageReadError(
            "failed to read failure records",
            details=safe_error_details(path=str(path), error=exc.__class__.__name__),
        ) from exc
    return records


def _filter_failures(
    records: list[FailureRecord],
    *,
    job_id: str | None,
    stage_allowlist: list[str] | None,
) -> list[FailureRecord]:
    if job_id is not None:
        records = [record for record in records if record.job_id == job_id]
    if stage_allowlist:
        allowed = set(stage_allowlist)
        records = [record for record in records if record.stage in allowed]
    return records


__all__ = ["LocalFailureStore", "LocalMediaStore", "LocalOutputStore"]
