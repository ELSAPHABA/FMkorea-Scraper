from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from fmkorea_scraper.core.api import run_job, search_board
from fmkorea_scraper.core.errors import UnsupportedSourceError
from fmkorea_scraper.core.ports import ClockPort, OutputStorePort
from fmkorea_scraper.models.enums import JobReportStatus, JobType
from fmkorea_scraper.models.job import BoardSearchRequest, JobConfig
from fmkorea_scraper.models.report import JobReport


class FakeRunner:
    async def run(self, config: JobConfig) -> JobReport:
        return JobReport(job_id=config.job_id, status=JobReportStatus.COMPLETED)


class FakeOutputStore:
    async def append_post(self, post):
        return None

    async def write_report(self, report):
        return None

    async def finalize(self):
        return None


class FakeClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    async def sleep(self, seconds: float) -> None:
        return None


def test_run_job_can_delegate_to_runner() -> None:
    job = JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})
    report = asyncio.run(run_job(job, runner=FakeRunner()))
    assert report.job_id == "job-1"
    assert report.status == JobReportStatus.COMPLETED


def test_api_placeholder_has_no_runtime_side_effects() -> None:
    request = BoardSearchRequest(board_id="best", keyword="test", search_target="title_content")
    with pytest.raises(UnsupportedSourceError):
        asyncio.run(search_board(request))


def test_ports_are_structurally_usable() -> None:
    assert isinstance(FakeOutputStore(), OutputStorePort)
    assert isinstance(FakeClock(), ClockPort)
