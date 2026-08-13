from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from fmkorea_scraper.adapters.mcp import McpToolHandlers
from fmkorea_scraper.models.enums import JobReportStatus, JobType
from fmkorea_scraper.models.report import JobReport, RetryReport


class FakeRunner:
    def __init__(self) -> None:
        self.config = None
        self.request = None

    async def run(self, config):
        self.config = config
        return JobReport(job_id=config.job_id, status=JobReportStatus.COMPLETED, stored_count=1)

    async def resume(self, request):
        self.request = request
        return JobReport(job_id=request.job_id or "latest", status=JobReportStatus.COMPLETED)


class FakeRetryService:
    def __init__(self) -> None:
        self.request = None

    async def run(self, request):
        self.request = request
        return RetryReport(job_id=request.failure_input.job_id or "retry", status=JobReportStatus.COMPLETED, selected_count=1)


def run(coro):
    return asyncio.run(coro)


def job_payload() -> dict[str, object]:
    return {
        "job_id": "job-1",
        "job_type": JobType.DIRECT_POST.value,
        "source": {"type": "direct_post", "urls": ["https://www.fmkorea.com/best/101"]},
    }


def test_mcp_run_job_returns_json_safe_payload() -> None:
    runner = FakeRunner()
    result = run(McpToolHandlers().run_job(job_payload(), runner=runner))

    assert result["ok"] is True
    assert result["data"]["job_id"] == "job-1"
    assert result["data"]["status"] == "completed"
    assert runner.config.job_id == "job-1"


def test_mcp_resume_job_returns_json_safe_payload() -> None:
    runner = FakeRunner()
    result = run(McpToolHandlers().resume_job({"job_id": "job-1"}, runner=runner))

    assert result["ok"] is True
    assert result["data"]["job_id"] == "job-1"
    assert runner.request.job_id == "job-1"


def test_mcp_retry_parser_failures_can_delegate_to_service() -> None:
    service = FakeRetryService()
    result = run(
        McpToolHandlers().retry_parser_failures(
            {"failure_input": {"failure_path": "failures.jsonl", "job_id": "job-1"}},
            retry_service=service,
        )
    )

    assert result["ok"] is True
    assert result["data"]["selected_count"] == 1
    assert service.request.failure_input.failure_path == "failures.jsonl"


def test_mcp_validation_error_is_safe() -> None:
    result = run(McpToolHandlers().run_job({"secret": "value"}, runner=FakeRunner()))

    assert result["ok"] is False
    assert result["error"]["code"] == "validation_error"
    assert "secret" not in str(result["error"])


def test_mcp_search_placeholder_returns_safe_unsupported() -> None:
    result = run(
        McpToolHandlers().search_board(
            {"board_id": "best", "keyword": "test", "search_target": "title_content"},
            http_client=object(),
        )
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "unsupported_source"
    assert result["error"]["safe_to_log"] is True


def test_mcp_import_has_no_runtime_side_effects(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    result = subprocess.run(
        [sys.executable, "-c", "import fmkorea_scraper.adapters.mcp; print('ok')"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "ok"
