"""S3-compatible output stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fmkorea_scraper.models.enums import StorageMode
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import FailureInput, S3StorageConfig
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, StoredObjectRef
from fmkorea_scraper.outputs.errors import StorageConfigurationError, StorageReadError, StorageWriteError, safe_error_details
from fmkorea_scraper.outputs.jsonl import JsonlWriter, to_jsonable
from fmkorea_scraper.outputs.layout import OutputRunLayout
from fmkorea_scraper.outputs.local import _filter_failures
from fmkorea_scraper.outputs.redaction import sanitize_failure_context


class S3JsonlSpool:
    def __init__(self, path: Path, *, client: Any, bucket: str, object_key: str) -> None:
        self.path = path
        self.client = client
        self.bucket = bucket
        self.object_key = object_key
        self._writer = JsonlWriter(path)

    def append(self, value: Any) -> None:
        self._writer.append(value)
        self._upload()

    def close(self) -> None:
        self._writer.close()

    def _upload(self) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=self.object_key, Body=self.path.read_bytes())
        except Exception as exc:
            raise StorageWriteError(
                "failed to upload JSONL spool",
                details=safe_error_details(bucket=self.bucket, object_key=self.object_key, error=exc.__class__.__name__),
            ) from exc


class S3ObjectStore:
    def __init__(
        self,
        layout: OutputRunLayout,
        config: S3StorageConfig,
        *,
        client: Any | None = None,
        spool_dir: Path | None = None,
    ) -> None:
        self.layout = layout
        self.config = config
        self.client = client or self._create_client(config)
        self.spool_dir = spool_dir or layout.run_dir / ".spool"
        self._posts = S3JsonlSpool(self.spool_dir / "posts.jsonl", client=self.client, bucket=config.bucket, object_key=layout.posts_key)
        self._failures = S3JsonlSpool(
            self.spool_dir / "failures.jsonl",
            client=self.client,
            bucket=config.bucket,
            object_key=layout.failures_key,
        )

    async def append_post(self, post: PostResult) -> StoredObjectRef:
        self._posts.append(post)
        return self._ref(self.layout.posts_key)

    async def write_report(self, report: JobReport) -> StoredObjectRef:
        self._put_json(self.layout.report_key, report)
        return self._ref(self.layout.report_key)

    async def write_failure(self, failure: FailureRecord) -> StoredObjectRef:
        safe_failure = failure.model_copy(update={"details": sanitize_failure_context(failure.details)})
        self._failures.append(safe_failure)
        return self._ref(self.layout.failures_key)

    async def read_failures(self, failure_input: FailureInput | Any) -> list[FailureRecord]:
        object_key = getattr(failure_input, "failure_path", self.layout.failures_key)
        if object_key.startswith("s3://"):
            object_key = object_key.split("/", 3)[-1]
        try:
            response = self.client.get_object(Bucket=self.config.bucket, Key=object_key)
            body = response["Body"]
            raw = body.read() if hasattr(body, "read") else body
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            records = [FailureRecord.model_validate(json.loads(line)) for line in text.splitlines() if line.strip()]
        except Exception as exc:
            raise StorageReadError(
                "failed to read S3 failure records",
                details=safe_error_details(bucket=self.config.bucket, object_key=object_key, error=exc.__class__.__name__),
            ) from exc
        return _filter_failures(
            records,
            job_id=getattr(failure_input, "job_id", None),
            stage_allowlist=getattr(failure_input, "stage_allowlist", None),
        )

    async def save_media(self, item: MediaItem, content: bytes) -> MediaItem:
        object_key = self.layout.media_key(item)
        self._put_bytes(object_key, content)
        return item.model_copy(update={"object_key": object_key})

    async def save_metadata_only(self, item: MediaItem) -> MediaItem:
        return item

    async def finalize(self) -> None:
        self._posts.close()
        self._failures.close()

    def _put_json(self, object_key: str, value: Any) -> None:
        body = json.dumps(to_jsonable(value), ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
        self._put_bytes(object_key, body)

    def _put_bytes(self, object_key: str, body: bytes) -> None:
        try:
            self.client.put_object(Bucket=self.config.bucket, Key=object_key, Body=body)
        except Exception as exc:
            raise StorageWriteError(
                "failed to upload object",
                details=safe_error_details(bucket=self.config.bucket, object_key=object_key, error=exc.__class__.__name__),
            ) from exc

    def _ref(self, object_key: str) -> StoredObjectRef:
        return StoredObjectRef(storage_mode=StorageMode.S3_COMPATIBLE, bucket=self.config.bucket, object_key=object_key)

    @staticmethod
    def _create_client(config: S3StorageConfig) -> Any:
        try:
            import boto3
        except ImportError as exc:
            raise StorageConfigurationError("boto3 is required for s3_compatible output") from exc
        return boto3.client("s3", endpoint_url=config.endpoint_url, region_name=config.region)


__all__ = ["S3JsonlSpool", "S3ObjectStore"]
