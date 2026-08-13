"""Stdlib CLI adapter for local FMKorea scraper execution."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import shlex
import signal
import sys
import tempfile
import traceback
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from fmkorea_scraper.collect import LinkCollectorService
from fmkorea_scraper.core.api import resume_job, run_job
from fmkorea_scraper.core.errors import ErrorMapper, StorageFailureError, ValidationFailure
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig, ProxyConfig, RetryPolicy, TimeoutConfig, UserAgentConfig
from fmkorea_scraper.models.enums import CommentMode, JobReportStatus, JobType, MediaMode, StopReason
from fmkorea_scraper.models.job import (
    BoardListSource,
    BoardSearchSource,
    DeepSearchSource,
    DirectPostSource,
    FailureInput,
    IntegratedSearchSource,
    JobConfig,
    NoKeywordRangeSource,
    RangeFilter,
    RealtimeAllSource,
    RealtimeKeywordSource,
    RealtimeTermination,
    ResumeRequest,
    RetryRequest,
    ScrapeOptions,
    StorageConfig,
    WorkerConfig,
)
from fmkorea_scraper.outputs import LocalCheckpointStore, OutputRunLayout, StorageFactory
from fmkorea_scraper.parse import ParserOptions, PostDetailService
from fmkorea_scraper.retry import ParserFailureRetryService, retry_safe_summary
from fmkorea_scraper.runner import JobRunDependencies, JobRunner

EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_VALIDATION_ERROR = 2

SOURCE_CHOICES = (
    "direct-post",
    "board-list",
    "board-search",
    "integrated-search",
    "deep-search",
    "no-keyword-range",
)
SOURCE_ALIASES = {choice: choice.replace("-", "_") for choice in SOURCE_CHOICES}
SOURCE_ALIASES.update({value: value for value in SOURCE_ALIASES.values()})
PROXY_ENV_KEYS = ("FMKOREA_PROXY_HOST", "FMKOREA_PROXY_ID", "FMKOREA_PROXY_PW")
RunIdFactory = Callable[[], str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fmkorea-scraper")
    parser.add_argument("--debug", action="store_true", help="print debug traceback on errors")
    subcommands = parser.add_subparsers(dest="subcommand", required=True)

    run = subcommands.add_parser("run", help="run one scrape job")
    run.add_argument("--source", choices=SOURCE_CHOICES)
    run.add_argument("--job-id")
    run.add_argument("--url", dest="urls", action="append")
    run.add_argument("--board-id")
    run.add_argument("--category-id")
    run.add_argument("--keyword")
    run.add_argument("--search-target", default="title_content")
    run.add_argument("--page-start", type=int, default=1)
    run.add_argument("--page-end", type=int)
    run.add_argument("--seed-page-limit", type=int, default=20)
    run.add_argument("--board-candidate", dest="board_ids", action="append")
    _add_range_options(run)
    _add_runtime_options(run)

    resume = subcommands.add_parser("resume", help="resume from local checkpoint")
    resume.add_argument("--job-id")
    _add_runtime_options(resume)

    retry = subcommands.add_parser("retry-parser-failures", help="build parser failure retry input")
    retry.add_argument("--failure-path", required=True)
    retry.add_argument("--existing-success-path")
    retry.add_argument("--from-report")
    retry.add_argument("--from-checkpoint")
    retry.add_argument("--retry-job-id")
    retry.add_argument("--job-id")
    retry.add_argument("--stage", dest="stage_allowlist", action="append")
    retry.add_argument("--skip-existing-success", dest="skip_existing_success", action="store_true", default=True)
    retry.add_argument("--no-skip-existing-success", dest="skip_existing_success", action="store_false")
    _add_runtime_options(retry)

    import_uas = subcommands.add_parser("import-user-agents", help="copy a UTF-8 User-Agent list to ./user-agents.txt")
    import_uas.add_argument("source_path")

    proxy = subcommands.add_parser("configure-proxy", help="write proxy values to ./.env")
    proxy.add_argument("--host")
    proxy.add_argument("--id", dest="proxy_id")
    proxy.add_argument("--password", dest="proxy_pw")

    subcommands.add_parser("wizard", help="open a numbered terminal wizard")
    return parser


def _add_range_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--min-document-srl", type=int)
    parser.add_argument("--max-document-srl", type=int)
    parser.add_argument("--min-post-number", dest="min_document_srl", type=int)
    parser.add_argument("--max-post-number", dest="max_document_srl", type=int)


def _add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-path")
    parser.add_argument("--comment-mode", choices=[item.value for item in CommentMode])
    parser.add_argument("--media-mode", choices=[item.value for item in MediaMode])
    parser.add_argument("--include-attachments", dest="include_attachments", action="store_true", default=None)
    parser.add_argument("--no-attachments", dest="include_attachments", action="store_false")
    parser.add_argument("--request-interval-seconds", type=float)
    parser.add_argument("--max-post-retries", type=int)
    parser.add_argument("--post-worker-count", type=int)
    parser.add_argument("--media-worker-count", type=int)
    parser.add_argument("--queue-max-size", type=int)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--max-comment-pages", type=int)
    parser.add_argument("--max-comments", type=int)
    parser.add_argument("--max-content-blocks", type=int)
    parser.add_argument("--user-agent-file")
    parser.add_argument("--user-agent-rotate-every", type=int)
    parser.add_argument("--proxy-host")
    parser.add_argument("--proxy-id")
    parser.add_argument("--proxy-pw")


def normalize_command(value: argparse.Namespace | Mapping[str, Any]) -> dict[str, Any]:
    command = vars(value).copy() if isinstance(value, argparse.Namespace) else dict(value)
    if "command" in command and "subcommand" not in command:
        command["subcommand"] = command.pop("command")
    source = command.get("source")
    if source:
        command["source"] = normalize_source_name(str(source))
    return {key: value for key, value in command.items() if value is not None}


def normalize_source_name(value: str) -> str:
    try:
        return SOURCE_ALIASES[value]
    except KeyError as exc:
        raise ValidationFailure("unsupported source", details={"reason": "unsupported_source"}) from exc


def build_job_config(command: Mapping[str, Any], *, env: Mapping[str, str] | None = None) -> JobConfig:
    command = normalize_command(command)
    env = os.environ if env is None else env
    source = _build_realtime_source(command, env) if _env_true(env.get("FMKOREA_REALTIME_ENABLED")) else _build_source(command)
    return JobConfig(
        job_id=str(command.get("job_id") or _new_job_id()),
        job_type=JobType(source.type),
        source=source,
        scrape_options=_build_scrape_options(command),
        worker_config=_build_worker_config(command),
        storage_config=StorageConfig(base_output_path=_blank_none(command.get("output_path"))),
    )


def build_resume_request(command: Mapping[str, Any]) -> ResumeRequest:
    command = normalize_command(command)
    return ResumeRequest(job_id=_blank_none(command.get("job_id")))


def build_retry_request(command: Mapping[str, Any]) -> RetryRequest:
    command = normalize_command(command)
    stages = command.get("stage_allowlist") or ["post"]
    return RetryRequest(
        failure_input=FailureInput(
            failure_path=str(_required(command, "failure_path")),
            job_id=_blank_none(command.get("job_id")),
            stage_allowlist=[str(stage) for stage in stages],
        ),
        skip_existing_success=bool(command.get("skip_existing_success", True)),
        existing_success_path=_blank_none(command.get("existing_success_path")),
        from_report_path=_blank_none(command.get("from_report")),
        from_checkpoint_path=_blank_none(command.get("from_checkpoint")),
        retry_job_id=_blank_none(command.get("retry_job_id")),
    )


def _build_source(command: Mapping[str, Any]) -> Any:
    source_type = command.get("source")
    if not source_type:
        raise ValidationFailure("source is required", details={"reason": "source_required", "field_path": "source"})
    source_type = normalize_source_name(str(source_type))
    range_filter = _build_range_filter(command)

    if source_type == "direct_post":
        return DirectPostSource(urls=list(command.get("urls") or []))
    if source_type == "board_list":
        return BoardListSource(
            board_id=str(_required(command, "board_id")),
            category_id=_blank_none(command.get("category_id")),
            page_start=int(command.get("page_start") or 1),
            page_end=_optional_int(command.get("page_end")),
            range_filter=range_filter,
        )
    if source_type == "board_search":
        return BoardSearchSource(
            board_id=str(_required(command, "board_id")),
            category_id=_blank_none(command.get("category_id")),
            keyword=str(_required(command, "keyword")),
            search_target=str(command.get("search_target") or "title_content"),
            page_start=int(command.get("page_start") or 1),
            page_end=_optional_int(command.get("page_end")),
            range_filter=range_filter,
        )
    if source_type == "integrated_search":
        return IntegratedSearchSource(
            keyword=str(_required(command, "keyword")),
            search_target=str(command.get("search_target") or "title_content"),
            page_start=int(command.get("page_start") or 1),
            page_end=_optional_int(command.get("page_end")),
            range_filter=range_filter,
        )
    if source_type == "deep_search":
        return DeepSearchSource(
            keyword=str(_required(command, "keyword")),
            seed_search_target=str(command.get("search_target") or "title_content"),
            seed_page_limit=int(command.get("seed_page_limit") or 20),
            board_ids=list(command.get("board_ids") or []) or None,
            range_filter=range_filter or RangeFilter(),
        )
    if source_type == "no_keyword_range":
        return NoKeywordRangeSource(
            board_id=str(_required(command, "board_id")),
            category_id=_blank_none(command.get("category_id")),
            range_filter=range_filter or RangeFilter(),
        )
    raise ValidationFailure("unsupported source", details={"reason": "unsupported_source"})


def _build_realtime_source(command: Mapping[str, Any], env: Mapping[str, str]) -> RealtimeKeywordSource | RealtimeAllSource:
    if command.get("source"):
        raise ValidationFailure("realtime mode cannot be combined with --source", details={"reason": "realtime_source_conflict"})
    mode = _blank_none(env.get("FMKOREA_REALTIME_MODE"))
    if mode not in {"keyword", "all"}:
        raise ValidationFailure("FMKOREA_REALTIME_MODE must be keyword or all", details={"reason": "invalid_realtime_mode"})
    termination = _build_realtime_termination(env)
    poll_interval = float(_blank_none(env.get("FMKOREA_REALTIME_POLL_INTERVAL_SECONDS")) or 30.0)

    if mode == "keyword":
        scope = "board" if _blank_none(command.get("board_id")) else "integrated"
        return RealtimeKeywordSource(
            scope=scope,
            board_id=_blank_none(command.get("board_id")),
            keyword=str(_required(env, "FMKOREA_REALTIME_KEYWORD")),
            poll_interval_seconds=poll_interval,
            termination=termination,
        )
    return RealtimeAllSource(
        board_id=str(_required(command, "board_id")),
        category_id=_blank_none(command.get("category_id")),
        poll_interval_seconds=poll_interval,
        termination=termination,
    )


def _build_realtime_termination(env: Mapping[str, str]) -> RealtimeTermination:
    duration = _blank_none(env.get("FMKOREA_REALTIME_DURATION_SECONDS"))
    end_at = _blank_none(env.get("FMKOREA_REALTIME_END_AT"))
    if (duration is None) == (end_at is None):
        raise ValidationFailure(
            "exactly one realtime termination condition is required",
            details={"reason": "invalid_realtime_termination"},
        )
    return RealtimeTermination(duration_seconds=int(duration) if duration else None, end_at=end_at)


def _build_range_filter(command: Mapping[str, Any]) -> RangeFilter | None:
    range_filter = RangeFilter(
        date_from=_blank_none(command.get("date_from")),
        date_to=_blank_none(command.get("date_to")),
        min_document_srl=command.get("min_document_srl"),
        max_document_srl=command.get("max_document_srl"),
    )
    return range_filter if range_filter.has_any_bound() else None


def _build_scrape_options(command: Mapping[str, Any]) -> ScrapeOptions:
    data = {
        key: command[key]
        for key in (
            "include_attachments",
            "request_interval_seconds",
            "max_post_retries",
            "max_comment_pages",
            "max_content_blocks",
            "max_comments",
        )
        if key in command
    }
    if command.get("comment_mode"):
        data["comment_mode"] = CommentMode(str(command["comment_mode"]))
    if command.get("media_mode"):
        data["media_mode"] = MediaMode(str(command["media_mode"]))
    return ScrapeOptions(**data)


def _build_worker_config(command: Mapping[str, Any]) -> WorkerConfig:
    data = {key: command[key] for key in ("post_worker_count", "media_worker_count", "queue_max_size") if key in command}
    return WorkerConfig(**data)


def build_local_runtime(config: JobConfig, *, run_id: str, command: Mapping[str, Any]) -> tuple[HttpClient, JobRunner]:
    execution_dir = Path.cwd()
    timeout_seconds = float(command.get("timeout_seconds") or 30.0)
    proxy = None
    if command.get("proxy_host"):
        proxy = ProxyConfig.from_values(
            host=str(command.get("proxy_host") or ""),
            username=_blank_none(command.get("proxy_id")),
            password=_blank_none(command.get("proxy_pw")),
            source="cli",
        )
    http_config = HttpRuntimeConfig(
        request_interval_seconds=config.scrape_options.request_interval_seconds,
        timeout=TimeoutConfig(
            connect_seconds=timeout_seconds,
            read_seconds=timeout_seconds,
            write_seconds=timeout_seconds,
            pool_seconds=timeout_seconds,
        ),
        retry_policy=RetryPolicy(max_attempts=config.scrape_options.max_post_retries + 1),
        user_agent=UserAgentConfig(
            explicit_file_path=_blank_none(command.get("user_agent_file")),
            rotation_interval_requests=int(command.get("user_agent_rotate_every") or 10),
        ),
        proxy=proxy,
        proxy_env_path=execution_dir / ".env",
        execution_dir=execution_dir,
    )
    client = HttpClient(http_config)
    bundle = StorageFactory.create(config.storage_config, job_id=config.job_id, run_id=run_id)
    runner = JobRunner(
        JobRunDependencies(
            collector=LinkCollectorService(client),
            detail_service=PostDetailService(client, options=_parser_options(config.scrape_options)),
            output_store=bundle.output_store,
            failure_store=bundle.failure_store,
            media_store=bundle.media_store,
            checkpoint_store=bundle.checkpoint_store,
            http=client,
        )
    )
    return client, runner


async def run_scrape_command_async(
    command: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    runner: Any | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
    run_id_factory: RunIdFactory = lambda: f"run-{uuid.uuid4().hex}",
) -> int:
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    command = normalize_command(command)
    config = build_job_config(command, env=env)
    run_id = run_id_factory()
    _print_start(config, run_id, output)
    client = None
    if runner is None:
        client, runner = build_local_runtime(config, run_id=run_id, command=command)
    try:
        with InterruptController(runner, output=error_output):
            report = await run_job(config, runner=runner, run_id=run_id)
    finally:
        if client is not None:
            await client.close()
    _print_report(report, config.storage_config.base_output_path, output)
    return _exit_code_for_report(report)


async def resume_scrape_command_async(
    command: Mapping[str, Any],
    *,
    runner: Any | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
    run_id_factory: RunIdFactory = lambda: f"run-{uuid.uuid4().hex}",
) -> int:
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    command = normalize_command(command)
    request = build_resume_request(command)
    run_id = run_id_factory()
    storage_config = StorageConfig(base_output_path=_blank_none(command.get("output_path")))
    client = None
    if runner is None:
        job_id = await _resume_layout_job_id(request, storage_config, run_id)
        config = JobConfig(
            job_id=job_id,
            job_type=JobType.DIRECT_POST,
            source={"type": "direct_post", "urls": ["https://www.fmkorea.com/1"]},
            storage_config=storage_config,
        )
        client, runner = build_local_runtime(config, run_id=run_id, command=command)
    try:
        with InterruptController(runner, output=error_output):
            report = await resume_job(request, runner=runner, run_id=run_id)
    finally:
        if client is not None:
            await client.close()
    _print_report(report, storage_config.base_output_path, output)
    return _exit_code_for_report(report)


async def retry_parser_failures_command_async(
    command: Mapping[str, Any],
    *,
    runner: Any | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
    run_id_factory: RunIdFactory = lambda: f"run-{uuid.uuid4().hex}",
) -> int:
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    command = normalize_command(command)
    request = build_retry_request(command)
    service = ParserFailureRetryService(
        scrape_options=_build_scrape_options(command),
        worker_config=_build_worker_config(command),
        storage_config=StorageConfig(base_output_path=_blank_none(command.get("output_path"))),
    )

    async def _execute(config: JobConfig) -> Any:
        run_id = run_id_factory()
        client = None
        actual_runner = runner
        if actual_runner is None:
            client, actual_runner = build_local_runtime(config, run_id=run_id, command=command)
        try:
            with InterruptController(actual_runner, output=error_output):
                return await run_job(config, runner=actual_runner, run_id=run_id)
        finally:
            if client is not None:
                await client.close()

    report = await service.retry(request, execute_job=_execute)
    _print_retry_summary(report, output)
    _print_report(report, command.get("output_path"), output)
    return _exit_code_for_report(report)


def import_user_agents(source: str | Path, destination: str | Path) -> None:
    source_path = Path(source)
    destination_path = Path(destination)
    if not source_path.is_file():
        raise ValidationFailure("User-Agent source file not found", details={"reason": "file_not_found"})
    try:
        text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationFailure("User-Agent source file must be UTF-8", details={"reason": "invalid_utf8"}) from exc
    if not any(line.strip() for line in text.splitlines()):
        raise ValidationFailure("User-Agent source file is blank", details={"reason": "blank_user_agent_file"})
    _atomic_write_text(destination_path, text)


def update_proxy_env(path: str | Path, values: Mapping[str, str | None]) -> None:
    target = Path(path)
    existing = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    remaining = {key: str(values.get(key) or "") for key in PROXY_ENV_KEYS}
    output_lines: list[str] = []

    for line in existing:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in PROXY_ENV_KEYS:
            if key in remaining:
                output_lines.append(f"{key}={remaining.pop(key)}")
            continue
        output_lines.append(line)
    output_lines.extend(f"{key}={value}" for key, value in remaining.items())
    _atomic_write_text(target, "\n".join(output_lines).rstrip("\n") + "\n")


class WizardSession:
    def __init__(self, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> None:
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout

    def collect_command(self) -> dict[str, Any] | None:
        while True:
            self._write(
                "1. 스크래핑 시작하기\n"
                "2. 이어서 실행하기\n"
                "3. 파서 실패 재시도\n"
                "4. User-Agent 가져오기\n"
                "5. Proxy 설정하기\n"
                "6. 종료\n"
            )
            choice = self._ask("번호 입력: ")
            if choice in {"q", "6", ""}:
                return None
            if choice == "1":
                return self._collect_run()
            if choice == "2":
                return {"subcommand": "resume", "job_id": self._optional("Job ID(비우면 최신 체크포인트): ")}
            if choice == "3":
                return {
                    "subcommand": "retry-parser-failures",
                    "failure_path": self._ask("failures.jsonl 경로: "),
                    "job_id": self._optional("Job ID(선택): "),
                }
            if choice == "4":
                return {"subcommand": "import-user-agents", "source_path": self._ask("User-Agent 파일 경로: ")}
            if choice == "5":
                return {
                    "subcommand": "configure-proxy",
                    "host": self._ask("Proxy host: "),
                    "proxy_id": self._optional("Proxy ID(선택): "),
                    "proxy_pw": self._optional("Proxy PW(선택): "),
                }
            self._write("다시 입력해 주세요.\n")

    def _collect_run(self) -> dict[str, Any]:
        self._write(
            "1. direct-post\n"
            "2. board-list\n"
            "3. board-search\n"
            "4. integrated-search\n"
            "5. deep-search\n"
            "6. no-keyword-range\n"
        )
        source = {
            "1": "direct_post",
            "2": "board_list",
            "3": "board_search",
            "4": "integrated_search",
            "5": "deep_search",
            "6": "no_keyword_range",
        }.get(self._ask("소스 번호: "), "direct_post")
        command: dict[str, Any] = {
            "subcommand": "run",
            "source": source,
            "job_id": self._optional("Job ID(선택): "),
            "output_path": self._optional("출력 경로(선택): "),
        }
        if source == "direct_post":
            command["urls"] = [self._ask("게시글 URL: ")]
        elif source in {"board_list", "board_search", "no_keyword_range"}:
            command["board_id"] = self._ask("게시판 ID: ")
            if source == "board_search":
                command["keyword"] = self._ask("검색어: ")
            if source in {"board_list", "board_search"}:
                command["page_start"] = _optional_int(self._optional("시작 페이지(기본 1): ")) or 1
                command["page_end"] = _optional_int(self._optional("끝 페이지(선택): "))
            if source == "no_keyword_range":
                self._collect_range(command)
        elif source in {"integrated_search", "deep_search"}:
            command["keyword"] = self._ask("검색어: ")
            if source == "integrated_search":
                command["page_start"] = _optional_int(self._optional("시작 페이지(기본 1): ")) or 1
                command["page_end"] = _optional_int(self._optional("끝 페이지(선택): "))
            else:
                self._collect_range(command)
        return {key: value for key, value in command.items() if value is not None and value != ""}

    def _collect_range(self, command: dict[str, Any]) -> None:
        command["date_from"] = self._optional("시작일 YYYY-MM-DD(선택): ")
        command["date_to"] = self._optional("종료일 YYYY-MM-DD(선택): ")
        command["min_document_srl"] = _optional_int(self._optional("최소 글번호(선택): "))
        command["max_document_srl"] = _optional_int(self._optional("최대 글번호(선택): "))

    def _ask(self, prompt: str) -> str:
        self._write(prompt)
        return self.input_stream.readline().strip()

    def _optional(self, prompt: str) -> str | None:
        return _blank_none(self._ask(prompt))

    def _write(self, text: str) -> None:
        self.output_stream.write(text)
        self.output_stream.flush()


class InterruptController:
    def __init__(self, runner: Any, *, output: TextIO | None = None) -> None:
        self.runner = runner
        self.output = output or sys.stderr
        self.count = 0
        self._previous: Any = None
        self._installed = False

    def __enter__(self) -> "InterruptController":
        try:
            self._previous = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, self._handle)
            self._installed = True
        except ValueError:
            self._installed = False
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        if self._installed and self._previous is not None:
            signal.signal(signal.SIGINT, self._previous)
        return False

    def _handle(self, signum: int, frame: Any) -> None:
        _ = signum, frame
        self.count += 1
        if self.count == 1:
            if hasattr(self.runner, "stop"):
                self.runner.stop(StopReason.MANUAL_STOP)
            self.output.write("Ctrl+C received. Graceful stop requested. Press Ctrl+C again to force exit.\n")
            self.output.flush()
            return
        raise KeyboardInterrupt


def print_error(
    exc: Exception,
    *,
    stage: str | None = None,
    output: TextIO | None = None,
    debug: bool = False,
) -> None:
    output = output or sys.stderr
    mapped = ErrorMapper.map(exc, stage=stage)
    output.write(f"ERROR [{mapped.code}] {mapped.message}\n")
    for key, value in sorted(mapped.details.items()):
        output.write(f"{key}: {value}\n")
    if debug:
        output.write("Traceback (most recent call last):\n")
        output.writelines(traceback.format_tb(exc.__traceback__))
        output.write(f"{exc.__class__.__name__}: {mapped.message}\n")
    output.flush()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    command = normalize_command(args)
    debug = bool(command.get("debug"))
    try:
        return _dispatch_command(command)
    except (ValidationFailure, ValidationError) as exc:
        print_error(exc, stage=command.get("subcommand"), debug=debug)
        return EXIT_VALIDATION_ERROR
    except KeyboardInterrupt:
        sys.stderr.write("Interrupted.\n")
        return EXIT_RUNTIME_ERROR
    except Exception as exc:
        print_error(exc, stage=command.get("subcommand"), debug=debug)
        return EXIT_RUNTIME_ERROR


def _dispatch_command(command: Mapping[str, Any]) -> int:
    subcommand = command.get("subcommand")
    if subcommand == "run":
        return asyncio.run(run_scrape_command_async(command))
    if subcommand == "resume":
        return asyncio.run(resume_scrape_command_async(command))
    if subcommand == "retry-parser-failures":
        return asyncio.run(retry_parser_failures_command_async(command))
    if subcommand == "import-user-agents":
        import_user_agents(str(command["source_path"]), Path.cwd() / "user-agents.txt")
        print("Imported User-Agent file to user-agents.txt")
        return EXIT_SUCCESS
    if subcommand == "configure-proxy":
        _configure_proxy(command)
        print("Proxy profile saved to .env")
        return EXIT_SUCCESS
    if subcommand == "wizard":
        selected = WizardSession().collect_command()
        return EXIT_SUCCESS if selected is None else _dispatch_command(selected)
    raise ValidationFailure("unsupported command", details={"reason": "unsupported_command"})


def _configure_proxy(command: Mapping[str, Any]) -> None:
    print("Proxy credentials will be saved as plaintext in .env.")
    host = _blank_none(command.get("host")) or input("Proxy host: ").strip()
    if not host:
        raise ValidationFailure("proxy host is required", details={"reason": "proxy_host_required"})
    proxy_id = _blank_none(command.get("proxy_id")) or input("Proxy ID(optional): ").strip()
    proxy_pw = _blank_none(command.get("proxy_pw"))
    if proxy_pw is None:
        proxy_pw = getpass.getpass("Proxy PW(optional): ")
    update_proxy_env(
        Path.cwd() / ".env",
        {
            "FMKOREA_PROXY_HOST": host,
            "FMKOREA_PROXY_ID": proxy_id,
            "FMKOREA_PROXY_PW": proxy_pw,
        },
    )


def _print_start(config: JobConfig, run_id: str, output: TextIO) -> None:
    output.write(f"job_id: {config.job_id}\n")
    output.write(f"run_id: {run_id}\n")
    output.write(f"source: {config.source.type}\n")
    output.write(f"output_path: {config.storage_config.base_output_path or str(Path.cwd())}\n")
    output.write(f"workers: {config.worker_config.post_worker_count}\n")
    output.write(f"request_interval_seconds: {config.scrape_options.request_interval_seconds}\n")
    output.write(f"comment_mode: {config.scrape_options.comment_mode.value}\n")
    output.write(f"media_mode: {config.scrape_options.media_mode.value}\n")
    output.flush()


def _print_report(report: Any, output_path: str | None, output: TextIO) -> None:
    output.write(f"status: {getattr(report.status, 'value', report.status)}\n")
    output.write(f"collected_count: {getattr(report, 'collected_count', 0)}\n")
    output.write(f"stored_count: {getattr(report, 'stored_count', 0)}\n")
    output.write(f"failure_count: {getattr(report, 'failure_count', 0)}\n")
    for ref in getattr(report, "output_refs", []) or []:
        label = ref.path or ref.object_key or ref.bucket
        if label:
            output.write(f"output_ref: {label}\n")
    output.write(f"resume: {_resume_command(report.job_id, output_path)}\n")
    output.flush()


def _print_retry_summary(report: Any, output: TextIO) -> None:
    summary = retry_safe_summary(report)
    output.write(
        "retry "
        f"selected={summary['selected']} "
        f"skipped={summary['skipped']} "
        f"stored={summary['stored']} "
        f"remaining_failure={summary['remaining_failure']}\n"
    )
    output.flush()


def _resume_command(job_id: str, output_path: str | None) -> str:
    parts = ["python", "-m", "fmkorea_scraper.adapters.cli", "resume", "--job-id", job_id]
    if output_path:
        parts.extend(["--output-path", output_path])
    return " ".join(shlex.quote(part) for part in parts)


def _exit_code_for_report(report: Any) -> int:
    return EXIT_SUCCESS if report.status == JobReportStatus.COMPLETED else EXIT_RUNTIME_ERROR


async def _resume_layout_job_id(request: ResumeRequest, storage_config: StorageConfig, run_id: str) -> str:
    if request.job_id:
        return request.job_id
    layout = OutputRunLayout("resume", run_id, base_output_path=storage_config.base_output_path)
    checkpoint = await LocalCheckpointStore(layout).load_latest()
    return checkpoint.job_id if checkpoint else "resume"


def _parser_options(scrape_options: ScrapeOptions) -> ParserOptions:
    return ParserOptions(
        comment_mode=scrape_options.comment_mode,
        max_comment_pages=scrape_options.max_comment_pages,
        max_content_blocks=scrape_options.max_content_blocks,
        max_comments=scrape_options.max_comments,
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temp_name = file.name
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        raise StorageFailureError("file write failed", details={"stage": "cli_file", "reason": exc.__class__.__name__}) from exc


def _new_job_id() -> str:
    return f"job-{uuid.uuid4().hex[:12]}"


def _blank_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    return int(value) if value not in {None, ""} else None


def _required(source: Mapping[str, Any], key: str) -> Any:
    value = _blank_none(source.get(key))
    if value is None:
        raise ValidationFailure(f"{key} is required", details={"reason": "missing_required", "field_path": key})
    return value


def _env_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
