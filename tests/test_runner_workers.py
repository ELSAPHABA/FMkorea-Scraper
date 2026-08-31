from __future__ import annotations

import asyncio

from fmkorea_scraper.core.errors import BrowserFallbackError, CaptchaDetectedError
from fmkorea_scraper.models.comment import AuthorInfo
from fmkorea_scraper.models.enums import ContentBlockType, JobReportStatus, JobType, MediaMode, StopReason
from fmkorea_scraper.models.job import JobConfig, PostCandidate, ScrapeOptions, WorkerConfig
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.runner import JobRunDependencies, JobRunner
from tests.test_runner_service import (
    FakeCheckpointStore,
    FakeCollector,
    FakeFailureStore,
    FakeMediaStore,
    FakeOutputStore,
    candidate,
)


def run(coro):
    return asyncio.run(coro)


def media_post(raw: str) -> PostResult:
    return PostResult(
        board_id="best",
        document_srl=int(raw),
        document_id_raw=raw,
        canonical_url=f"https://www.fmkorea.com/best/{raw}",
        title=f"title {raw}",
        author=AuthorInfo(nickname="user"),
        media=[
            MediaItem(
                media_type=ContentBlockType.IMAGE,
                source_block_order=0,
                url=f"https://image.example.com/{raw}.jpg",
            )
        ],
    )


class CaptchaDetailService:
    async def parse(self, item: PostCandidate) -> PostResult:
        raise CaptchaDetectedError("captcha", details={"stage": "post"})


class BrowserFallbackFailureDetailService:
    async def parse(self, item: PostCandidate) -> PostResult:
        raise BrowserFallbackError("browser fallback failed", details={"stage": "browser_fallback"})


class MediaDetailService:
    async def parse(self, item: PostCandidate) -> PostResult:
        return media_post(item.document_id_raw)


class SlowHttp:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def download(self, url: str, *, headers=None) -> bytes:
        _ = headers
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return url.encode()


def test_captcha_failure_stops_job_and_saves_stopped_checkpoint() -> None:
    output = FakeOutputStore()
    failure = FakeFailureStore()
    checkpoints = FakeCheckpointStore()
    deps = JobRunDependencies(
        collector=FakeCollector([candidate("101"), candidate("102")]),
        detail_service=CaptchaDetailService(),
        output_store=output,
        failure_store=failure,
        media_store=FakeMediaStore(),
        checkpoint_store=checkpoints,
    )

    result = run(JobRunner(deps).run(JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})))

    assert result.status == JobReportStatus.STOPPED
    assert result.reason == StopReason.CAPTCHA
    assert output.posts == []
    assert failure.failures[0].stage == "post"
    assert checkpoints.saved[-1].reason == StopReason.CAPTCHA


def test_browser_fallback_failure_stops_job_and_saves_terminal_checkpoint() -> None:
    output = FakeOutputStore()
    failure = FakeFailureStore()
    checkpoints = FakeCheckpointStore()
    deps = JobRunDependencies(
        collector=FakeCollector([candidate("101")]),
        detail_service=BrowserFallbackFailureDetailService(),
        output_store=output,
        failure_store=failure,
        media_store=FakeMediaStore(),
        checkpoint_store=checkpoints,
    )

    result = run(JobRunner(deps).run(JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})))

    assert result.status == JobReportStatus.FAILED
    assert result.reason == StopReason.ERROR
    assert checkpoints.saved[-1].reason == StopReason.ERROR


def test_media_downloads_are_limited_by_media_worker_count() -> None:
    output = FakeOutputStore()
    failure = FakeFailureStore()
    http = SlowHttp()
    deps = JobRunDependencies(
        collector=FakeCollector([candidate("101"), candidate("102")]),
        detail_service=MediaDetailService(),
        output_store=output,
        failure_store=failure,
        media_store=FakeMediaStore(),
        checkpoint_store=FakeCheckpointStore(),
        http=http,
    )
    config = JobConfig(
        job_id="job-1",
        job_type=JobType.BOARD_LIST,
        source={"type": "board_list", "board_id": "best"},
        scrape_options=ScrapeOptions(media_mode=MediaMode.DOWNLOAD),
        worker_config=WorkerConfig(post_worker_count=2, media_worker_count=1),
    )

    result = run(JobRunner(deps).run(config))

    assert result.status == JobReportStatus.COMPLETED
    assert result.stored_count == 2
    assert result.failure_count == 0
    assert result.report.output_refs
    assert http.max_active == 1
