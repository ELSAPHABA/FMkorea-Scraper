from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmkorea_scraper.adapters import cli
from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.models.enums import JobReportStatus
from fmkorea_scraper.models.job import RetryRequest
from fmkorea_scraper.models.report import JobReport, StoredObjectRef
from fmkorea_scraper.models.enums import StorageMode
from fmkorea_scraper.retry import ParserFailureRetryService, select_parser_failure_retries


class FakeRunner:
    def __init__(self) -> None:
        self.config = None
        self.run_id = None

    async def run(self, config, *, run_id=None):
        self.config = config
        self.run_id = run_id
        return JobReport(
            job_id=config.job_id,
            status=JobReportStatus.COMPLETED,
            collected_count=len(config.source.urls),
            stored_count=len(config.source.urls),
            output_refs=[
                StoredObjectRef(storage_mode=StorageMode.LOCAL, path="/tmp/report.json"),
            ],
            metadata=config.metadata,
        )


def _line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False) + "\n"


def _failure(document_id_raw: str, reason: str = "post title missing", *, stage: str = "post", job_id: str = "job-1") -> dict:
    document_srl = int(document_id_raw)
    return {
        "job_id": job_id,
        "stage": stage,
        "reason": reason,
        "retryable": True,
        "url": f"https://www.fmkorea.com/best/{document_id_raw}",
        "post_key": {"board_id": "best", "document_srl": document_srl, "document_id_raw": document_id_raw},
        "safe_message": "safe parser failure",
    }


def test_selector_filters_invalid_ineligible_and_dedupes_last_url() -> None:
    lines = [
        "{bad json}\n",
        _line(_failure("101", "post title missing")),
        _line(_failure("101", "metadata parse failure")),
        _line(_failure("102", "network failure")),
    ]

    candidates, summary = select_parser_failure_retries({"failures.jsonl": lines})

    assert [candidate.document_id_raw for candidate in candidates] == ["101"]
    assert summary.initial_failure_count == 4
    assert summary.invalid_failure_record_count == 1
    assert summary.ineligible_failure_count == 1
    assert summary.deduped_failure_count == 1
    assert summary.selected_count == 1


def test_service_skips_existing_success_and_adds_retry_metadata(tmp_path: Path) -> None:
    failures = tmp_path / "failures.jsonl"
    failures.write_text(_line(_failure("101")) + _line(_failure("102", "content parse failure")), encoding="utf-8")
    posts = tmp_path / "posts.jsonl"
    posts.write_text(_line({"site_id": "fmkorea", "board_id": "best", "document_srl": 101, "document_id_raw": "101"}), encoding="utf-8")
    captured = {}

    async def execute(config):
        captured["config"] = config
        return JobReport(job_id=config.job_id, status=JobReportStatus.COMPLETED, stored_count=1, metadata=config.metadata)

    request = cli.build_retry_request(
        {
            "subcommand": "retry-parser-failures",
            "failure_path": str(failures),
            "existing_success_path": str(posts),
            "job_id": "job-1",
            "retry_job_id": "retry-1",
        }
    )
    report = asyncio.run(ParserFailureRetryService().retry(request, execute_job=execute))

    assert captured["config"].source.urls == ["https://www.fmkorea.com/best/102"]
    metadata = report.metadata["parser_failure_retry"]
    assert report.job_id == "retry-1"
    assert report.selected_count == 1
    assert report.skipped_count == 1
    assert metadata["skipped_existing_count"] == 1
    assert metadata["remaining_failure_count"] == 0


def test_retry_request_restore_sources_are_mutually_exclusive() -> None:
    with pytest.raises(ValidationError):
        RetryRequest(
            failure_input={"failure_path": "failures.jsonl"},
            from_report_path="report.json",
            from_checkpoint_path="checkpoint.json",
        )


def test_cli_retry_parser_failures_uses_injected_runner(tmp_path: Path) -> None:
    failures = tmp_path / "failures.jsonl"
    failures.write_text(_line(_failure("101")), encoding="utf-8")
    runner = FakeRunner()
    output = io.StringIO()

    code = asyncio.run(
        cli.retry_parser_failures_command_async(
            {"subcommand": "retry-parser-failures", "failure_path": str(failures), "job_id": "job-1", "retry_job_id": "retry-1"},
            runner=runner,
            output=output,
            run_id_factory=lambda: "run-retry",
        )
    )

    assert code == cli.EXIT_SUCCESS
    assert runner.config.source.type == "direct_post"
    assert runner.config.source.urls == ["https://www.fmkorea.com/best/101"]
    assert runner.run_id == "run-retry"
    assert "retry selected=1 skipped=0 stored=1 remaining_failure=0" in output.getvalue()


def test_retry_service_requires_runner() -> None:
    request = cli.build_retry_request({"subcommand": "retry-parser-failures", "failure_path": "failures.jsonl"})

    with pytest.raises(ValidationFailure):
        asyncio.run(ParserFailureRetryService().run(request))


def test_inaccessible_input_fails_before_execute(tmp_path: Path) -> None:
    called = False
    request = cli.build_retry_request({"subcommand": "retry-parser-failures", "failure_path": str(tmp_path / "missing.jsonl")})

    async def execute(config):
        nonlocal called
        called = True
        return JobReport(job_id=config.job_id, status=JobReportStatus.COMPLETED)

    with pytest.raises(ValidationFailure):
        asyncio.run(ParserFailureRetryService().retry(request, execute_job=execute))

    assert called is False


def test_retry_modules_import_without_runtime_side_effects(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    code = "import fmkorea_scraper.retry, pathlib; print(pathlib.Path('.env').exists(), pathlib.Path('user-agents.txt').exists())"
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "False False"
