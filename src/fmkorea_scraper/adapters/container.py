"""One-shot container entrypoint."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from fmkorea_scraper.adapters import cli
from fmkorea_scraper.adapters.safe_errors import safe_error_payload
from fmkorea_scraper.collect import LinkCollectorService
from fmkorea_scraper.core.api import resume_job, run_job
from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig, ProxyConfig, RetryPolicy, UserAgentConfig
from fmkorea_scraper.models.enums import CheckpointMode, JobReportStatus, JobType, StorageMode, StopReason
from fmkorea_scraper.models.job import (
    DirectPostSource,
    JobConfig,
    PostgresCheckpointConfig,
    ResumeRequest,
    S3StorageConfig,
    ScrapeOptions,
    StorageConfig,
)
from fmkorea_scraper.outputs import OutputRunLayout, PostgresCheckpointStore, S3OutputStore
from fmkorea_scraper.outputs.errors import StorageConfigurationError
from fmkorea_scraper.parse import ParserOptions, PostDetailService
from fmkorea_scraper.runner import JobRunDependencies, JobRunner

EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_VALIDATION_ERROR = 2


@dataclass(frozen=True)
class ContainerEnvConfig:
    database_url: str = field(repr=False)
    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key_id: str = field(repr=False)
    s3_secret_access_key: str = field(repr=False)
    s3_region: str | None = None
    s3_prefix: str | None = None
    s3_force_path_style: bool = False
    resume: bool = False
    job_id: str | None = None
    user_agent_file: str | None = None
    user_agent_rotate_every: int = 10
    proxy_host: str | None = None
    proxy_id: str | None = None
    proxy_pw: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ContainerEnvConfig":
        return cls(
            database_url=_required_env(env, "DATABASE_URL"),
            s3_endpoint_url=_required_env(env, "S3_ENDPOINT_URL"),
            s3_bucket=_required_env(env, "S3_BUCKET"),
            s3_access_key_id=_required_env(env, "S3_ACCESS_KEY_ID"),
            s3_secret_access_key=_required_env(env, "S3_SECRET_ACCESS_KEY"),
            s3_region=_blank_none(env.get("S3_REGION")),
            s3_prefix=_blank_none(env.get("S3_PREFIX")),
            s3_force_path_style=_env_bool(env, "S3_FORCE_PATH_STYLE", default=False),
            resume=_env_bool(env, "RESUME", default=False),
            job_id=_blank_none(env.get("JOB_ID")),
            user_agent_file=_blank_none(env.get("FMKOREA_USER_AGENT_FILE")),
            user_agent_rotate_every=_env_int(env, "FMKOREA_USER_AGENT_ROTATE_EVERY", default=10),
            proxy_host=_blank_none(env.get("FMKOREA_PROXY_HOST")),
            proxy_id=_blank_none(env.get("FMKOREA_PROXY_ID")),
            proxy_pw=_blank_none(env.get("FMKOREA_PROXY_PW")),
        )

    def storage_config(self, *, base_output_path: str | None = None, prefix: str | None = None) -> StorageConfig:
        return StorageConfig(
            output_mode=StorageMode.S3_COMPATIBLE,
            checkpoint_mode=CheckpointMode.POSTGRES,
            base_output_path=base_output_path,
            s3=S3StorageConfig(
                endpoint_url=self.s3_endpoint_url,
                bucket=self.s3_bucket,
                prefix=prefix or self.s3_prefix,
                region=self.s3_region,
            ),
            postgres=PostgresCheckpointConfig(dsn=self.database_url),
        )


@dataclass
class ContainerRuntime:
    config: JobConfig
    http_client: Any
    runner: JobRunner

    async def close(self) -> None:
        close = getattr(self.http_client, "close", None)
        if close is not None:
            await close()


def build_container_runtime(
    config: JobConfig,
    env_config: ContainerEnvConfig,
    *,
    http_client: Any | None = None,
    s3_client: Any | None = None,
    postgres_connection_factory: Any | None = None,
    run_id: str | None = None,
) -> ContainerRuntime:
    storage_config = env_config.storage_config(
        base_output_path=config.storage_config.base_output_path,
        prefix=config.storage_config.s3.prefix if config.storage_config.s3 else None,
    )
    config = config.model_copy(update={"storage_config": storage_config})
    client = http_client or _build_http_client(config, env_config)
    layout = OutputRunLayout(
        config.job_id,
        run_id or _new_run_id(),
        base_output_path=storage_config.base_output_path,
        s3_prefix=storage_config.s3.prefix if storage_config.s3 else None,
    )
    s3_config = storage_config.s3
    if s3_config is None:
        raise StorageConfigurationError("s3 config is required for container output")
    object_store = S3OutputStore(layout, s3_config, client=s3_client or _create_s3_client(env_config))
    checkpoint_store = PostgresCheckpointStore(env_config.database_url, connection_factory=postgres_connection_factory)
    runner = JobRunner(
        JobRunDependencies(
            collector=LinkCollectorService(client),
            detail_service=PostDetailService(client, options=_parser_options(config.scrape_options)),
            output_store=object_store,
            failure_store=object_store,
            media_store=object_store,
            checkpoint_store=checkpoint_store,
            http=client,
        )
    )
    return ContainerRuntime(config=config, http_client=client, runner=runner)


async def run_container_async(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    runner: Any | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    env = os.environ if env is None else env
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    runtime: ContainerRuntime | None = None
    try:
        env_config = ContainerEnvConfig.from_env(env)
        run_id = _new_run_id()
        if env_config.resume:
            request = ResumeRequest(job_id=env_config.job_id)
            if runner is None:
                runtime = build_container_runtime(_resume_placeholder_job(env_config.job_id), env_config, run_id=run_id)
                runner = runtime.runner
            with ContainerSignalController(runner, output=error_output):
                report = await resume_job(request, runner=runner, run_id=run_id)
        else:
            command = _parse_container_command(argv)
            config = cli.build_job_config(command, env=env)
            storage_config = env_config.storage_config(base_output_path=config.storage_config.base_output_path)
            config = config.model_copy(update={"storage_config": storage_config})
            if runner is None:
                runtime = build_container_runtime(config, env_config, run_id=run_id)
                runner = runtime.runner
                config = runtime.config
            with ContainerSignalController(runner, output=error_output):
                report = await run_job(config, runner=runner, run_id=run_id)
        _write_json(output, {"ok": True, "report": report.model_dump(mode="json")})
        return EXIT_SUCCESS if report.status == JobReportStatus.COMPLETED else EXIT_RUNTIME_ERROR
    except (ValidationFailure, ValidationError) as exc:
        _write_json(error_output, {"ok": False, "error": safe_error_payload(exc, stage="container")})
        return EXIT_VALIDATION_ERROR
    except KeyboardInterrupt:
        _write_json(error_output, {"ok": False, "error": {"code": "interrupted", "message": "interrupted"}})
        return EXIT_RUNTIME_ERROR
    except Exception as exc:
        _write_json(error_output, {"ok": False, "error": safe_error_payload(exc, stage="container")})
        return EXIT_RUNTIME_ERROR
    finally:
        if runtime is not None:
            await runtime.close()


class ContainerSignalController:
    def __init__(self, runner: Any, *, output: TextIO) -> None:
        self.runner = runner
        self.output = output
        self.count = 0
        self._previous: dict[int, Any] = {}
        self._installed = False

    def __enter__(self) -> "ContainerSignalController":
        try:
            for signum in {signal.SIGINT, signal.SIGTERM}:
                self._previous[signum] = signal.getsignal(signum)
                signal.signal(signum, self._handle)
            self._installed = True
        except ValueError:
            self._installed = False
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        if self._installed:
            for signum, previous in self._previous.items():
                signal.signal(signum, previous)
        return False

    def _handle(self, signum: int, frame: Any) -> None:
        _ = signum, frame
        self.count += 1
        if self.count == 1:
            if hasattr(self.runner, "stop"):
                self.runner.stop(StopReason.MANUAL_STOP)
            elif hasattr(self.runner, "request_stop"):
                self.runner.request_stop()
            self.output.write("stop requested; saving checkpoint when possible\n")
            self.output.flush()
            return
        raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run_container_async(argv))


def _parse_container_command(argv: list[str] | None) -> dict[str, Any]:
    parser = cli.build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        raise ValidationFailure("invalid container arguments", details={"reason": "invalid_args"}) from exc
    command = cli.normalize_command(args)
    if command.get("subcommand") != "run":
        raise ValidationFailure("container entrypoint supports run or RESUME=true", details={"reason": "unsupported_command"})
    return command


def _build_http_client(config: JobConfig, env_config: ContainerEnvConfig) -> HttpClient:
    proxy = ProxyConfig.from_values(
        host=env_config.proxy_host,
        username=env_config.proxy_id,
        password=env_config.proxy_pw,
        source="env",
    )
    return HttpClient(
        HttpRuntimeConfig(
            request_interval_seconds=config.scrape_options.request_interval_seconds,
            retry_policy=RetryPolicy(max_attempts=config.scrape_options.max_post_retries + 1),
            user_agent=UserAgentConfig(
                explicit_file_path=env_config.user_agent_file,
                rotation_interval_requests=env_config.user_agent_rotate_every,
            ),
            proxy=proxy,
            execution_dir=os.getcwd(),
        )
    )


def _create_s3_client(env_config: ContainerEnvConfig) -> Any:
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise StorageConfigurationError("boto3 is required for s3_compatible output") from exc
    config = Config(s3={"addressing_style": "path"}) if env_config.s3_force_path_style else None
    return boto3.client(
        "s3",
        endpoint_url=env_config.s3_endpoint_url,
        region_name=env_config.s3_region,
        aws_access_key_id=env_config.s3_access_key_id,
        aws_secret_access_key=env_config.s3_secret_access_key,
        config=config,
    )


def _parser_options(scrape_options: ScrapeOptions) -> ParserOptions:
    return ParserOptions(
        max_comment_pages=scrape_options.max_comment_pages,
        max_content_blocks=scrape_options.max_content_blocks,
        max_comments=scrape_options.max_comments,
    )


def _resume_placeholder_job(job_id: str | None) -> JobConfig:
    return JobConfig(
        job_id=job_id or "resume",
        job_type=JobType.DIRECT_POST,
        source=DirectPostSource(urls=["https://www.fmkorea.com/1"]),
    )


def _required_env(env: Mapping[str, str], key: str) -> str:
    value = _blank_none(env.get(key))
    if value is None:
        raise ValidationFailure("missing required container env", details={"reason": "missing_required", "field_path": key})
    return value


def _env_bool(env: Mapping[str, str], key: str, *, default: bool) -> bool:
    value = _blank_none(env.get(key))
    if value is None:
        return default
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValidationFailure("invalid boolean env", details={"reason": "invalid_boolean", "field_path": key})


def _env_int(env: Mapping[str, str], key: str, *, default: int) -> int:
    value = _blank_none(env.get(key))
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValidationFailure("invalid integer env", details={"reason": "invalid_integer", "field_path": key}) from exc
    if parsed < 1:
        raise ValidationFailure("integer env must be positive", details={"reason": "invalid_integer", "field_path": key})
    return parsed


def _blank_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _write_json(output: TextIO, payload: Mapping[str, Any]) -> None:
    output.write(json.dumps(payload, ensure_ascii=False, allow_nan=False, default=str) + "\n")
    output.flush()


if __name__ == "__main__":
    raise SystemExit(main())
