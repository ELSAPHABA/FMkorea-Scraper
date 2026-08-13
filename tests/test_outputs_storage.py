from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.comment import AuthorInfo
from fmkorea_scraper.models.enums import CheckpointMode, ContentBlockType, JobReportStatus, JobType, StorageMode
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import (
    FailureInput,
    JobConfig,
    PostgresCheckpointConfig,
    S3StorageConfig,
    StorageConfig,
)
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport
from fmkorea_scraper.outputs import (
    OutputRunLayout,
    PathTraversalError,
    PostgresCheckpointStore,
    StorageConfigurationError,
    StorageFactory,
    ensure_under_base,
)


def run(coro):
    return asyncio.run(coro)


def post(document_id_raw: str = "101") -> PostResult:
    return PostResult(
        board_id="best",
        document_srl=int(document_id_raw),
        document_id_raw=document_id_raw,
        canonical_url=f"https://www.fmkorea.com/best/{document_id_raw}",
        title="sample",
        author=AuthorInfo(nickname="user"),
    )


def job_config(job_id: str = "job-1") -> JobConfig:
    return JobConfig(
        job_id=job_id,
        job_type=JobType.BOARD_LIST,
        source={"type": "board_list", "board_id": "best"},
    )


def failure(job_id: str = "job-1") -> FailureRecord:
    return FailureRecord(
        job_id=job_id,
        stage="post",
        reason="parse_failed",
        retryable=True,
        safe_message="parse failed",
        details={
            "http_status": 200,
            "parser_stage": "content",
            "password": "secret",
            "raw_html": "<html>secret</html>",
        },
    )


def test_local_stores_write_posts_failures_report_media_and_checkpoint(tmp_path: Path) -> None:
    bundle = StorageFactory.create(
        StorageConfig(base_output_path=str(tmp_path)),
        job_id="job:1",
        run_id="run/1",
    )

    post_ref = run(bundle.output_store.append_post(post()))
    report_ref = run(
        bundle.output_store.write_report(
            JobReport(job_id="job-1", status=JobReportStatus.COMPLETED, collected_count=1, stored_count=1)
        )
    )
    failure_ref = run(bundle.failure_store.write_failure(failure()))
    saved_media = run(
        bundle.media_store.save_media(
            MediaItem(
                media_type=ContentBlockType.IMAGE,
                source_block_order=1,
                url="https://image.example.com/original/photo.jpg",
                metadata={"board_id": "best", "document_id_raw": "101"},
            ),
            b"image-bytes",
        )
    )
    checkpoint = Checkpoint(job_id="job-1", job_config=job_config())
    run(bundle.checkpoint_store.save(checkpoint))
    run(bundle.output_store.finalize())
    run(bundle.failure_store.finalize())

    assert Path(post_ref.path or "").read_text(encoding="utf-8").count("\n") == 1
    assert Path(report_ref.path or "").exists()
    assert Path(failure_ref.path or "").exists()
    assert saved_media.file_path is not None
    assert Path(saved_media.file_path).read_bytes() == b"image-bytes"
    assert run(bundle.checkpoint_store.load("job-1")) == checkpoint
    assert run(bundle.checkpoint_store.load_latest()) == checkpoint


def test_failure_store_reads_filtered_redacted_records(tmp_path: Path) -> None:
    bundle = StorageFactory.create(StorageConfig(base_output_path=str(tmp_path)), job_id="job-1", run_id="run-1")

    run(bundle.failure_store.write_failure(failure("job-1")))
    run(bundle.failure_store.write_failure(failure("job-2")))
    run(bundle.failure_store.finalize())

    records = run(
        bundle.failure_store.read_failures(
            FailureInput(failure_path=str(bundle.layout.failures_path), job_id="job-1", stage_allowlist=["post"])
        )
    )

    assert len(records) == 1
    assert records[0].job_id == "job-1"
    assert records[0].details == {"http_status": 200, "parser_stage": "content"}


def test_checkpoint_store_keeps_latest_by_updated_at(tmp_path: Path) -> None:
    bundle = StorageFactory.create(StorageConfig(base_output_path=str(tmp_path)), job_id="job-1", run_id="run-1")
    early = Checkpoint(
        job_id="job-1",
        job_config=job_config("job-1"),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    late = Checkpoint(
        job_id="job-2",
        job_config=job_config("job-2"),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    run(bundle.checkpoint_store.save(early))
    run(bundle.checkpoint_store.save(late))

    assert run(bundle.checkpoint_store.load_latest()) == late


def test_path_containment_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(PathTraversalError):
        ensure_under_base(tmp_path, tmp_path.parent / "outside.json")


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket: str, Key: str):
        return {"Body": FakeBody(self.objects[(Bucket, Key)])}


class FakeBody:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body


def test_s3_store_uses_matching_keys_and_same_key_spool(tmp_path: Path) -> None:
    client = FakeS3Client()
    bundle = StorageFactory.create(
        StorageConfig(
            output_mode=StorageMode.S3_COMPATIBLE,
            base_output_path=str(tmp_path),
            s3=S3StorageConfig(endpoint_url="http://garage.local", bucket="bucket", prefix="prefix"),
        ),
        job_id="job-1",
        run_id="run-1",
        s3_client=client,
    )

    first_ref = run(bundle.output_store.append_post(post("101")))
    second_ref = run(bundle.output_store.append_post(post("102")))
    failure_ref = run(bundle.failure_store.write_failure(failure()))
    media = run(bundle.media_store.save_media(MediaItem(media_type=ContentBlockType.IMAGE, source_block_order=0, url="https://x/y.jpg"), b"jpg"))
    run(bundle.output_store.finalize())

    assert first_ref.object_key == second_ref.object_key == "prefix/outputs/job-1/run-1/posts.jsonl"
    assert client.objects[("bucket", first_ref.object_key)].count(b"\n") == 2
    assert failure_ref.object_key == "prefix/outputs/job-1/run-1/failures.jsonl"
    assert media.object_key == "prefix/outputs/job-1/run-1/media/unknown_board/unknown_post/image/0-y.jpg"


def test_factory_builds_postgres_checkpoint_store_without_connecting(tmp_path: Path) -> None:
    bundle = StorageFactory.create(
        StorageConfig(
            base_output_path=str(tmp_path),
            checkpoint_mode=CheckpointMode.POSTGRES,
            postgres=PostgresCheckpointConfig(dsn="postgresql://example"),
        ),
        job_id="job-1",
        run_id="run-1",
    )

    assert isinstance(bundle.checkpoint_store, PostgresCheckpointStore)


def test_output_layout_sanitizes_local_paths_and_keys(tmp_path: Path) -> None:
    layout = OutputRunLayout("job:/1", "run\\2", base_output_path=tmp_path, s3_prefix="site/fmkorea")

    assert layout.posts_path == tmp_path / "outputs" / "job_1" / "run_2" / "posts.jsonl"
    assert layout.posts_key == "site/fmkorea/outputs/job_1/run_2/posts.jsonl"
