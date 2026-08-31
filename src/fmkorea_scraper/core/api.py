"""Public async API surface.

Executable scraper behavior is implemented by later units. These functions
keep the library import-safe and establish stable type contracts for adapters.
"""

from __future__ import annotations

import inspect
from typing import Any

from fmkorea_scraper.collect.parsers import (
    BOARD_PAGE_REQUIRED_SELECTOR,
    INTEGRATED_SEARCH_REQUIRED_SELECTOR,
    BoardPageParser,
    IntegratedSearchParser,
)
from fmkorea_scraper.collect.urls import BoardUrlBuilder, IntegratedSearchUrlBuilder
from fmkorea_scraper.core.errors import UnsupportedSourceError, ValidationFailure
from fmkorea_scraper.models.comment import Comment
from fmkorea_scraper.models.job import (
    BoardSearchRequest,
    IntegratedSearchPage,
    IntegratedSearchRequest,
    JobConfig,
    RetryRequest,
    ScrapeOptions,
    SearchPage,
    PostRequest,
    CommentRequest,
    ResumeRequest,
)
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport, RetryReport
from fmkorea_scraper.parse import ParserOptions, PostDetailService


async def search_board(request: BoardSearchRequest, http_client: Any | None = None) -> SearchPage:
    if http_client is None:
        raise ValidationFailure("http_client is required", details={"reason": "http_client_required"})
    urls = BoardUrlBuilder()
    url = (
        urls.build_search_url(request.board_id, request.keyword, request.search_target or "title_content", request.page, request.category_id)
        if request.keyword
        else urls.build_list_url(request.board_id, request.page, request.category_id)
    )
    page, failures = BoardPageParser().parse(
        _response_text(await http_client.get(url, required_selector=BOARD_PAGE_REQUIRED_SELECTOR)),
        board_id=request.board_id,
        request_url=url,
        page=request.page,
    )
    return _with_failures(page, failures)


async def search_integrated(request: IntegratedSearchRequest, http_client: Any | None = None) -> IntegratedSearchPage:
    if http_client is None:
        raise ValidationFailure("http_client is required", details={"reason": "http_client_required"})
    url = IntegratedSearchUrlBuilder().build_search_url(request.keyword, request.search_target, request.page)
    page, boards, failures = IntegratedSearchParser().parse(
        _response_text(await http_client.get(url, required_selector=INTEGRATED_SEARCH_REQUIRED_SELECTOR)),
        keyword=request.keyword,
        request_url=url,
        page=request.page,
    )
    board_ids = list(dict.fromkeys([*page.board_ids, *(board.board_id for board in boards)]))
    return _with_failures(page.model_copy(update={"board_ids": board_ids}), failures)


async def fetch_post(request: PostRequest, http_client: Any | None = None) -> PostResult:
    if http_client is None:
        raise ValidationFailure("http_client is required", details={"reason": "http_client_required"})
    return await PostDetailService(http_client, options=_parser_options(request.scrape_options)).parse(request)


async def fetch_comments(request: CommentRequest, http_client: Any | None = None) -> list[Comment]:
    if http_client is None:
        raise ValidationFailure("http_client is required", details={"reason": "http_client_required"})
    post = await fetch_post(
        PostRequest(
            url=request.url,
            board_id=request.board_id,
            document_srl=request.document_srl,
            scrape_options=ScrapeOptions(comment_mode=request.comment_mode),
        ),
        http_client=http_client,
    )
    return post.comments


async def run_job(config: JobConfig, *, runner: Any | None = None, run_id: str | None = None) -> JobReport:
    if runner is not None:
        return _report_from_result(await _call_runner(runner.run, config, run_id=run_id))
    raise UnsupportedSourceError("run_job is implemented in UOW-005", details={"stage": "job"})


async def resume_job(request: ResumeRequest, *, runner: Any | None = None, run_id: str | None = None) -> JobReport:
    if runner is not None:
        return _report_from_result(await _call_runner(runner.resume, request, run_id=run_id))
    raise UnsupportedSourceError("resume_job is implemented in UOW-005", details={"stage": "job"})


async def retry_parser_failures(request: RetryRequest, *, retry_service: Any | None = None) -> RetryReport:
    if retry_service is not None:
        return await retry_service.run(request)
    from fmkorea_scraper.retry import ParserFailureRetryService

    return await ParserFailureRetryService().run(request)


def _report_from_result(result: Any) -> JobReport:
    if isinstance(result, JobReport):
        return result
    report = getattr(result, "report", None)
    if isinstance(report, JobReport):
        return report
    return result


async def _call_runner(method: Any, payload: Any, *, run_id: str | None) -> Any:
    if run_id is None or not _accepts_run_id(method):
        return await method(payload)
    return await method(payload, run_id=run_id)


def _accepts_run_id(method: Any) -> bool:
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        return False
    return "run_id" in parameters or any(parameter.kind == parameter.VAR_KEYWORD for parameter in parameters.values())


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise TypeError("HTTP response must provide text")


def _with_failures(page: Any, failures: list[Any]) -> Any:
    if not failures:
        return page
    metadata = dict(page.metadata)
    metadata["failures"] = [failure.model_dump(mode="json") for failure in failures]
    return page.model_copy(update={"metadata": metadata})


def _parser_options(scrape_options: ScrapeOptions) -> ParserOptions:
    return ParserOptions(
        comment_mode=scrape_options.comment_mode,
        max_comment_pages=scrape_options.max_comment_pages,
        max_content_blocks=scrape_options.max_content_blocks,
        max_comments=scrape_options.max_comments,
    )
