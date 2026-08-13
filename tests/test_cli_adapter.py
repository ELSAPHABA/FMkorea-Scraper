from __future__ import annotations

import asyncio
import io
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError as PydanticValidationError

from fmkorea_scraper.adapters import cli
from fmkorea_scraper.core.api import run_job
from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.models.enums import JobReportStatus, JobType, StorageMode
from fmkorea_scraper.models.job import JobConfig
from fmkorea_scraper.models.report import JobReport, StoredObjectRef


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


def test_parser_accepts_confirmed_subcommands() -> None:
    parser = cli.build_parser()

    assert parser.parse_args(["wizard"]).subcommand == "wizard"
    assert parser.parse_args(["resume"]).subcommand == "resume"
    assert parser.parse_args(["retry-parser-failures", "--failure-path", "failures.jsonl"]).subcommand == "retry-parser-failures"
    assert parser.parse_args(["import-user-agents", "agents.txt"]).subcommand == "import-user-agents"
    assert parser.parse_args(["configure-proxy", "--host", "proxy.local:8080"]).subcommand == "configure-proxy"
    args = parser.parse_args(["run", "--source", "direct-post", "--url", "https://www.fmkorea.com/best/101"])
    assert args.subcommand == "run"


def test_parser_rejects_user_cookie_file_option() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--source",
                "direct-post",
                "--url",
                "https://www.fmkorea.com/best/101",
                "--cookie-file",
                "cookies.txt",
            ]
        )


def test_build_job_config_maps_board_search() -> None:
    config = cli.build_job_config(
        {
            "subcommand": "run",
            "source": "board-search",
            "job_id": "job-1",
            "board_id": "best",
            "keyword": "test",
            "output_path": "out",
            "post_worker_count": 3,
        },
        env={},
    )

    assert config.source.type == "board_search"
    assert config.source.board_id == "best"
    assert config.storage_config.base_output_path == "out"
    assert config.worker_config.post_worker_count == 3


def test_build_no_keyword_range_requires_range() -> None:
    with pytest.raises(PydanticValidationError):
        cli.build_job_config({"subcommand": "run", "source": "no-keyword-range", "board_id": "best"}, env={})

    config = cli.build_job_config(
        {
            "subcommand": "run",
            "source": "no-keyword-range",
            "board_id": "best",
            "date_from": "2026-08-13",
        },
        env={},
    )
    assert config.source.type == "no_keyword_range"


def test_build_resume_and_retry_requests() -> None:
    assert cli.build_resume_request({"subcommand": "resume"}).job_id is None
    request = cli.build_retry_request({"subcommand": "retry-parser-failures", "failure_path": "failures.jsonl"})
    assert request.failure_input.failure_path == "failures.jsonl"
    assert request.failure_input.stage_allowlist == ["post"]


def test_realtime_env_validation() -> None:
    config = cli.build_job_config(
        {"subcommand": "run"},
        env={
            "FMKOREA_REALTIME_ENABLED": "true",
            "FMKOREA_REALTIME_MODE": "keyword",
            "FMKOREA_REALTIME_KEYWORD": "test",
            "FMKOREA_REALTIME_DURATION_SECONDS": "60",
        },
    )
    assert config.source.type == "realtime_keyword"
    assert config.source.scope == "integrated"

    with pytest.raises(ValidationFailure):
        cli.build_job_config(
            {"subcommand": "run"},
            env={
                "FMKOREA_REALTIME_ENABLED": "true",
                "FMKOREA_REALTIME_MODE": "keyword",
                "FMKOREA_REALTIME_KEYWORD": "test",
                "FMKOREA_REALTIME_DURATION_SECONDS": "60",
                "FMKOREA_REALTIME_END_AT": "2026-08-13T00:00:00Z",
            },
        )


def test_import_user_agents_rejects_blank_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "blank.txt"
    destination = tmp_path / "user-agents.txt"
    source.write_text("\n\n", encoding="utf-8")
    destination.write_text("Mozilla/5.0\n", encoding="utf-8")

    with pytest.raises(ValidationFailure):
        cli.import_user_agents(source, destination)

    assert destination.read_text(encoding="utf-8") == "Mozilla/5.0\n"


def test_update_proxy_env_preserves_unrelated_lines(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEEP=1\nFMKOREA_PROXY_HOST=old\n", encoding="utf-8")

    cli.update_proxy_env(
        env_file,
        {
            "FMKOREA_PROXY_HOST": "proxy.local:8080",
            "FMKOREA_PROXY_ID": "user",
            "FMKOREA_PROXY_PW": "secret",
        },
    )

    text = env_file.read_text(encoding="utf-8")
    assert "KEEP=1" in text
    assert "FMKOREA_PROXY_HOST=proxy.local:8080" in text
    assert "FMKOREA_PROXY_ID=user" in text
    assert "FMKOREA_PROXY_PW=secret" in text


def test_run_command_uses_injected_runner_without_network() -> None:
    output = io.StringIO()
    runner = FakeRunner()

    code = asyncio.run(
        cli.run_scrape_command_async(
            {
                "subcommand": "run",
                "source": "direct-post",
                "job_id": "job-1",
                "urls": ["https://www.fmkorea.com/best/101"],
            },
            env={},
            runner=runner,
            output=output,
            run_id_factory=lambda: "run-fixed",
        )
    )

    assert code == cli.EXIT_SUCCESS
    assert runner.config.job_id == "job-1"
    assert runner.run_id == "run-fixed"
    assert "resume:" in output.getvalue()


def test_resume_command_uses_injected_runner_without_network() -> None:
    runner = FakeRunner()
    code = asyncio.run(
        cli.resume_scrape_command_async(
            {"subcommand": "resume", "job_id": "job-1"},
            runner=runner,
            output=io.StringIO(),
            run_id_factory=lambda: "run-resume",
        )
    )

    assert code == cli.EXIT_SUCCESS
    assert runner.request.job_id == "job-1"
    assert runner.run_id == "run-resume"


def test_retry_parser_failures_is_safe_unsupported_until_uow009() -> None:
    error = io.StringIO()
    code = asyncio.run(
        cli.retry_parser_failures_command_async(
            {"subcommand": "retry-parser-failures", "failure_path": "failures.jsonl"},
            error_output=error,
        )
    )

    assert code == cli.EXIT_RUNTIME_ERROR
    assert "UOW-009" in error.getvalue()


def test_build_local_runtime_passes_run_id_to_storage_factory(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_create(config, *, job_id, run_id, s3_client=None):
        calls.append((config.base_output_path, job_id, run_id, s3_client))
        store = SimpleNamespace()
        return SimpleNamespace(output_store=store, failure_store=store, media_store=store, checkpoint_store=store, layout=None)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.StorageFactory, "create", staticmethod(fake_create))
    config = cli.build_job_config(
        {"subcommand": "run", "source": "direct-post", "job_id": "job-1", "urls": ["https://www.fmkorea.com/best/101"]},
        env={},
    )

    client, _runner = cli.build_local_runtime(config, run_id="run-fixed", command={})
    asyncio.run(client.close())

    assert calls == [(None, "job-1", "run-fixed", None)]


def test_core_api_passes_optional_run_id() -> None:
    job = JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})
    runner = FakeRunner()

    report = asyncio.run(run_job(job, runner=runner, run_id="run-core"))

    assert report.job_id == "job-1"
    assert runner.run_id == "run-core"


def test_wizard_maps_direct_post_to_run_command() -> None:
    session = cli.WizardSession(
        input_stream=io.StringIO("1\n1\njob-1\n\nhttps://www.fmkorea.com/best/101\n"),
        output_stream=io.StringIO(),
    )

    command = session.collect_command()

    assert command["subcommand"] == "run"
    assert command["source"] == "direct_post"
    assert command["job_id"] == "job-1"
    assert command["urls"] == ["https://www.fmkorea.com/best/101"]


def test_wizard_invalid_input_can_exit() -> None:
    output = io.StringIO()
    session = cli.WizardSession(input_stream=io.StringIO("x\n6\n"), output_stream=output)

    assert session.collect_command() is None
    assert "다시 입력" in output.getvalue()


def test_interrupt_controller_first_stop_second_interrupt() -> None:
    runner = FakeRunner()
    output = io.StringIO()

    with pytest.raises(KeyboardInterrupt):
        with cli.InterruptController(runner, output=output) as controller:
            controller._handle(2, None)
            controller._handle(2, None)

    assert runner.stopped_reason is not None
    assert "Graceful stop requested" in output.getvalue()


def test_print_error_uses_safe_summary_and_debug_gate() -> None:
    output = io.StringIO()
    cli.print_error(
        ValidationFailure("failed", details={"password": "secret", "reason": "safe"}),
        output=output,
        debug=False,
    )

    text = output.getvalue()
    assert "validation_error" in text
    assert "secret" not in text
    assert "Traceback" not in text


def test_cli_import_has_no_runtime_side_effects(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    code = "import fmkorea_scraper.adapters.cli, pathlib; print(pathlib.Path('.env').exists(), pathlib.Path('user-agents.txt').exists())"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False False"


def test_python_module_help_runs(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "fmkorea_scraper.adapters.cli", "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "fmkorea-scraper" in result.stdout
