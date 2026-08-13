"""Container-facing S3-compatible output store."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import anyio

from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import S3StorageConfig
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, StoredObjectRef
from fmkorea_scraper.outputs.layout import OutputRunLayout
from fmkorea_scraper.outputs.redaction import sanitize_failure_context
from fmkorea_scraper.outputs.s3 import S3JsonlSpool, S3ObjectStore


class S3OutputStore(S3ObjectStore):
    def __init__(
        self,
        layout: OutputRunLayout,
        config: S3StorageConfig,
        *,
        client: Any | None = None,
        spool_dir: Path | None = None,
    ) -> None:
        self._tempdir: tempfile.TemporaryDirectory[str] | None = None
        if spool_dir is None:
            self._tempdir = tempfile.TemporaryDirectory(prefix="fmkorea-s3-spool-")
            spool_dir = Path(self._tempdir.name)
        super().__init__(layout, config, client=client, spool_dir=spool_dir)

    async def append_post(self, post: PostResult) -> StoredObjectRef:
        await anyio.to_thread.run_sync(self._posts.append, post)
        return self._ref(self.layout.posts_key)

    async def write_report(self, report: JobReport) -> StoredObjectRef:
        await anyio.to_thread.run_sync(self._put_json, self.layout.report_key, report)
        return self._ref(self.layout.report_key)

    async def write_failure(self, failure: FailureRecord) -> StoredObjectRef:
        safe_failure = failure.model_copy(update={"details": sanitize_failure_context(failure.details)})
        await anyio.to_thread.run_sync(self._failures.append, safe_failure)
        return self._ref(self.layout.failures_key)

    async def save_media(self, item: MediaItem, content: bytes) -> MediaItem:
        object_key = self.layout.media_key(item)
        await anyio.to_thread.run_sync(self._put_bytes, object_key, content)
        return item.model_copy(update={"object_key": object_key})

    async def finalize(self) -> None:
        await anyio.to_thread.run_sync(self._posts.close)
        await anyio.to_thread.run_sync(self._failures.close)
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None


S3Spool = S3JsonlSpool


__all__ = ["S3OutputStore", "S3Spool"]
