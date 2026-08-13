from __future__ import annotations

import asyncio
import io
import json
from datetime import datetime, timezone

from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.comment import AuthorInfo
from fmkorea_scraper.models.enums import ContentBlockType, JobReportStatus, JobType
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import JobConfig, S3StorageConfig
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport
from fmkorea_scraper.outputs.layout import OutputRunLayout
from fmkorea_scraper.outputs.postgres_checkpoint import PostgresCheckpointStore
from fmkorea_scraper.outputs.s3_output import S3OutputStore


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket: str, Key: str):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


class FakePostgres:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[datetime, str]] = {}
        self.current_row = None
        self.statements: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).lower()
        self.statements.append(normalized)
        if normalized.startswith("insert into fmkorea_checkpoints"):
            self.rows[params[0]] = (params[1], params[2])
        elif "where job_id" in normalized:
            row = self.rows.get(params[0])
            self.current_row = (row[1],) if row else None
        elif "order by updated_at desc" in normalized:
            row = max(self.rows.values(), key=lambda item: item[0]) if self.rows else None
            self.current_row = (row[1],) if row else None

    def fetchone(self):
        return self.current_row


def run(coro):
    return asyncio.run(coro)


def post(document_id_raw: str = "101") -> PostResult:
    return PostResult(
        board_id="best",
        document_srl=int(document_id_raw),
        document_id_raw=document_id_raw,
        canonical_url=f"https://www.fmkorea.com/best/{document_id_raw}",
        title="sample",
        author=AuthorInfo(nickname="writer"),
    )


def job_config(job_id: str = "job-1") -> JobConfig:
    return JobConfig(
        job_id=job_id,
        job_type=JobType.DIRECT_POST,
        source={"type": "direct_post", "urls": ["https://www.fmkorea.com/best/101"]},
    )


def test_s3_output_store_uploads_jsonl_report_failure_and_media(tmp_path) -> None:
    client = FakeS3Client()
    layout = OutputRunLayout("job-1", "run-1", base_output_path=tmp_path, s3_prefix="prefix")
    store = S3OutputStore(
        layout,
        S3StorageConfig(endpoint_url="http://garage.local", bucket="bucket", prefix="prefix"),
        client=client,
    )

    post_ref = run(store.append_post(post("101")))
    run(store.append_post(post("102")))
    failure_ref = run(
        store.write_failure(
            FailureRecord(
                job_id="job-1",
                stage="post",
                reason="parse_failed",
                safe_message="parse failed",
                details={"password": "secret", "parser_stage": "content"},
            )
        )
    )
    report_ref = run(store.write_report(JobReport(job_id="job-1", status=JobReportStatus.COMPLETED)))
    media = run(store.save_media(MediaItem(media_type=ContentBlockType.IMAGE, source_block_order=0, url="https://x/y.jpg"), b"jpg"))
    run(store.finalize())

    assert post_ref.object_key == "prefix/outputs/job-1/run-1/posts.jsonl"
    assert client.objects[("bucket", post_ref.object_key)].count(b"\n") == 2
    assert b"secret" not in client.objects[("bucket", failure_ref.object_key)]
    assert json.loads(client.objects[("bucket", report_ref.object_key)])["status"] == "completed"
    assert client.objects[("bucket", media.object_key)] == b"jpg"


def test_postgres_checkpoint_store_saves_loads_and_loads_latest() -> None:
    db = FakePostgres()
    store = PostgresCheckpointStore("postgresql://example", connection_factory=lambda dsn: db)
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

    run(store.save(early))
    run(store.save(late))

    assert run(store.load("job-1")) == early
    assert run(store.load_latest()) == late
    assert any(statement.startswith("create table if not exists fmkorea_checkpoints") for statement in db.statements)
