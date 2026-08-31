from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from fmkorea_scraper.core.api import run_job, search_board
from fmkorea_scraper.core.errors import ValidationFailure
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


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeHttp:
    def __init__(self, text: str) -> None:
        self.text = text
        self.urls: list[str] = []

    async def get(self, url: str, **kwargs):
        _ = kwargs
        self.urls.append(url)
        return FakeResponse(self.text)


def test_run_job_can_delegate_to_runner() -> None:
    job = JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})
    report = asyncio.run(run_job(job, runner=FakeRunner()))
    assert report.job_id == "job-1"
    assert report.status == JobReportStatus.COMPLETED


def test_public_search_api_requires_injected_client() -> None:
    request = BoardSearchRequest(board_id="best", keyword="test", search_target="title_content")
    with pytest.raises(ValidationFailure):
        asyncio.run(search_board(request))


def test_search_board_collects_one_page_with_injected_client() -> None:
    html = """
    <div class="bd"><table><tbody>
      <tr><td class="title"><a class="hx" href="/best/10195585295">sample</a></td><td>2026.08.14</td></tr>
    </tbody></table></div>
    <a href="/best?page=2">2</a>
    """
    http = FakeHttp(html)
    request = BoardSearchRequest(board_id="best", keyword="test", search_target="title_content")

    page = asyncio.run(search_board(request, http_client=http))

    assert page.candidates[0].document_id_raw == "10195585295"
    assert page.has_next is True
    assert "search.php" in http.urls[0]


def test_ports_are_structurally_usable() -> None:
    assert isinstance(FakeOutputStore(), OutputStorePort)
    assert isinstance(FakeClock(), ClockPort)
