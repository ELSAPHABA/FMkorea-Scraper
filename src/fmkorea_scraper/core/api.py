"""Public async API surface.

Executable scraper behavior is implemented by later units. These functions
keep the library import-safe and establish stable type contracts for adapters.
"""

from __future__ import annotations

from typing import Any

from fmkorea_scraper.core.errors import UnsupportedSourceError
from fmkorea_scraper.models.comment import Comment
from fmkorea_scraper.models.job import (
    BoardSearchRequest,
    IntegratedSearchPage,
    IntegratedSearchRequest,
    JobConfig,
    RetryRequest,
    SearchPage,
    PostRequest,
    CommentRequest,
    ResumeRequest,
)
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, RetryReport


async def search_board(request: BoardSearchRequest, http_client: Any | None = None) -> SearchPage:
    raise UnsupportedSourceError("search_board is implemented in UOW-003", details={"stage": "search"})


async def search_integrated(request: IntegratedSearchRequest, http_client: Any | None = None) -> IntegratedSearchPage:
    raise UnsupportedSourceError("search_integrated is implemented in UOW-003", details={"stage": "search"})


async def fetch_post(request: PostRequest, http_client: Any | None = None) -> PostResult:
    raise UnsupportedSourceError("fetch_post is implemented in UOW-004", details={"stage": "post"})


async def fetch_comments(request: CommentRequest, http_client: Any | None = None) -> list[Comment]:
    raise UnsupportedSourceError("fetch_comments is implemented in UOW-004", details={"stage": "comment"})


async def run_job(config: JobConfig, *, runner: Any | None = None) -> JobReport:
    if runner is not None:
        return _report_from_result(await runner.run(config))
    raise UnsupportedSourceError("run_job is implemented in UOW-005", details={"stage": "job"})


async def resume_job(request: ResumeRequest, *, runner: Any | None = None) -> JobReport:
    if runner is not None:
        return _report_from_result(await runner.resume(request))
    raise UnsupportedSourceError("resume_job is implemented in UOW-005", details={"stage": "job"})


async def retry_parser_failures(request: RetryRequest, *, retry_service: Any | None = None) -> RetryReport:
    if retry_service is not None:
        return await retry_service.run(request)
    raise UnsupportedSourceError("retry_parser_failures is implemented in UOW-009", details={"stage": "retry"})


def _report_from_result(result: Any) -> JobReport:
    if isinstance(result, JobReport):
        return result
    report = getattr(result, "report", None)
    if isinstance(report, JobReport):
        return report
    return result
