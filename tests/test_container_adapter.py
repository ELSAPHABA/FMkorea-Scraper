from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path

from fmkorea_scraper.adapters.container import (
    EXIT_RUNTIME_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    ContainerEnvConfig,
    build_container_runtime,
    run_container_async,
)
from fmkorea_scraper.models.enums import CheckpointMode, JobReportStatus, JobType, StorageMode
from fmkorea_scraper.models.job import JobConfig
from fmkorea_scraper.models.report import JobReport


class FakeRunner:
    def __init__(self, status: JobReportStatus = JobReportStatus.COMPLETED) -> None:
        self.status = status
        self.config = None
        self.request = None
        self.run_id = None
        self.stopped_reason = None

    def stop(self, reason=None) -> None:
        self.stopped_reason = reason

    async def run(self, config, *, run_id=None):
        self.config = config
        self.run_id = run_id
        return JobReport(job_id=config.job_id, status=self.status, collected_count=1, stored_count=1)

    async def resume(self, request, *, run_id=None):
        self.request = request
        self.run_id = run_id
        return JobReport(job_id=request.job_id or "latest", status=self.status, stored_count=1)


class FakeHttpClient:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeS3Client:
    def put_object(self, **kwargs):
        return None


class FakePostgresConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        return None

    def fetchone(self):
        return None


def run(coro):
    return asyncio.run(coro)


def container_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql://user:pass@postgres/fmkorea",
        "S3_ENDPOINT_URL": "http://garage:3900",
        "S3_BUCKET": "scraper",
        "S3_ACCESS_KEY_ID": "access",
        "S3_SECRET_ACCESS_KEY": "secret",
        "S3_PREFIX": "fmkorea",
    }


def direct_post_job() -> JobConfig:
    return JobConfig(
        job_id="job-1",
        job_type=JobType.DIRECT_POST,
        source={"type": "direct_post", "urls": ["https://www.fmkorea.com/best/101"]},
    )


def _failure_line(document_id_raw: str) -> str:
    return json.dumps(
        {
            "job_id": "job-1",
            "stage": "post",
            "reason": "post title missing",
            "retryable": True,
            "url": f"https://www.fmkorea.com/best/{document_id_raw}",
            "post_key": {"board_id": "best", "document_srl": int(document_id_raw), "document_id_raw": document_id_raw},
            "safe_message": "safe parser failure",
        },
        ensure_ascii=False,
    ) + "\n"


def test_container_env_config_maps_storage_and_redacts_secrets() -> None:
    config = ContainerEnvConfig.from_env(container_env())
    storage = config.storage_config()

    assert storage.output_mode == StorageMode.S3_COMPATIBLE
    assert storage.checkpoint_mode == CheckpointMode.POSTGRES
    assert storage.s3 is not None
    assert storage.s3.prefix == "fmkorea"
    assert storage.postgres is not None
    assert config.browser_fallback_enabled is True
    assert "secret" not in repr(config)
    assert "postgresql://user:pass" not in repr(config)


def test_container_env_can_disable_default_browser_fallback() -> None:
    config = ContainerEnvConfig.from_env({**container_env(), "FMKOREA_BROWSER_FALLBACK": "false"})

    assert config.browser_fallback_enabled is False


def test_container_missing_env_returns_validation_exit() -> None:
    err = io.StringIO()

    code = run(run_container_async(["run"], env={}, runner=FakeRunner(), error_output=err))

    assert code == EXIT_VALIDATION_ERROR
    assert "DATABASE_URL" in err.getvalue()
    assert "secret" not in err.getvalue()


def test_container_run_uses_cli_job_with_s3_and_postgres_storage() -> None:
    out = io.StringIO()
    runner = FakeRunner()

    code = run(
        run_container_async(
            ["run", "--source", "direct-post", "--job-id", "job-1", "--url", "https://www.fmkorea.com/best/101"],
            env=container_env(),
            runner=runner,
            output=out,
        )
    )

    assert code == EXIT_SUCCESS
    assert runner.config.storage_config.output_mode == StorageMode.S3_COMPATIBLE
    assert runner.config.storage_config.checkpoint_mode == CheckpointMode.POSTGRES
    assert runner.config.storage_config.s3.prefix == "fmkorea"
    assert runner.run_id
    assert '"ok": true' in out.getvalue()


def test_container_retry_uses_existing_entrypoint_and_storage(tmp_path: Path) -> None:
    failures = tmp_path / "failures.jsonl"
    failures.write_text(_failure_line("101"), encoding="utf-8")
    runner = FakeRunner()
    out = io.StringIO()

    code = run(
        run_container_async(
            ["retry-parser-failures", "--failure-path", str(failures), "--job-id", "job-1"],
            env=container_env(),
            runner=runner,
            output=out,
        )
    )

    assert code == EXIT_SUCCESS
    assert runner.config.source.type == "direct_post"
    assert runner.config.storage_config.output_mode == StorageMode.S3_COMPATIBLE
    assert '"selected_count": 1' in out.getvalue()


def test_container_resume_uses_env_job_id() -> None:
    runner = FakeRunner()
    env = {**container_env(), "RESUME": "true", "JOB_ID": "job-resume"}

    code = run(run_container_async([], env=env, runner=runner, output=io.StringIO()))

    assert code == EXIT_SUCCESS
    assert runner.request.job_id == "job-resume"


def test_container_runtime_builds_real_runner_without_opening_network() -> None:
    env_config = ContainerEnvConfig.from_env(container_env())
    http_client = FakeHttpClient()
    runtime = build_container_runtime(
        direct_post_job(),
        env_config,
        http_client=http_client,
        s3_client=FakeS3Client(),
        postgres_connection_factory=lambda dsn: FakePostgresConnection(),
        run_id="run-1",
    )

    assert runtime.config.storage_config.output_mode == StorageMode.S3_COMPATIBLE
    assert runtime.runner.dependencies.http is http_client
    run(runtime.close())
    assert http_client.closed


def test_container_runtime_error_status_returns_runtime_exit() -> None:
    code = run(run_container_async(["run", "--source", "direct-post", "--url", "https://www.fmkorea.com/best/101"], env=container_env(), runner=FakeRunner(JobReportStatus.FAILED)))

    assert code == EXIT_RUNTIME_ERROR
