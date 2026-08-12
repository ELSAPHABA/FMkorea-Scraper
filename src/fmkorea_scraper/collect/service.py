"""Collector orchestration services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fmkorea_scraper.collect.models import (
    BoardCandidate,
    CollectorFailure,
    CollectorRun,
    CollectorSummary,
    RangeDecisionKind,
    SearchTraversalState,
)
from fmkorea_scraper.collect.parsers import BoardPageParser, IntegratedSearchParser
from fmkorea_scraper.collect.policies import BoardCandidateDeduper, CandidateDeduper, RangeFilterEvaluator
from fmkorea_scraper.collect.urls import BoardUrlBuilder, DirectPostUrlNormalizer, IntegratedSearchUrlBuilder
from fmkorea_scraper.core.errors import UnsupportedSourceError, ValidationFailure
from fmkorea_scraper.models.job import (
    BoardListSource,
    BoardSearchSource,
    DeepSearchSource,
    DirectPostSource,
    IntegratedSearchSource,
    NoKeywordRangeSource,
    PostCandidate,
    RangeFilter,
    RealtimeAllSource,
    RealtimeKeywordSource,
)


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise TypeError("HTTP response must provide text")


class LinkCollectorService:
    def __init__(
        self,
        http: Any,
        *,
        direct_normalizer: DirectPostUrlNormalizer | None = None,
        board_urls: BoardUrlBuilder | None = None,
        integrated_urls: IntegratedSearchUrlBuilder | None = None,
        board_parser: BoardPageParser | None = None,
        integrated_parser: IntegratedSearchParser | None = None,
        range_evaluator: RangeFilterEvaluator | None = None,
    ) -> None:
        self.http = http
        self.direct_normalizer = direct_normalizer or DirectPostUrlNormalizer()
        self.board_urls = board_urls or BoardUrlBuilder()
        self.integrated_urls = integrated_urls or IntegratedSearchUrlBuilder()
        self.board_parser = board_parser or BoardPageParser()
        self.integrated_parser = integrated_parser or IntegratedSearchParser()
        self.range_evaluator = range_evaluator or RangeFilterEvaluator()

    async def collect(self, source: Any) -> AsyncIterator[PostCandidate]:
        run = await self.collect_with_summary(source)
        for candidate in run.candidates:
            yield candidate

    async def collect_with_summary(self, source: Any) -> CollectorRun:
        source_type = getattr(source, "type", None)
        if source_type == "direct_post":
            return await self._collect_direct(source)
        if source_type == "board_list":
            return await self._collect_board_list(source)
        if source_type == "board_search":
            return await self._collect_board_search(source)
        if source_type == "integrated_search":
            return await self._collect_integrated(source)
        if source_type == "no_keyword_range":
            return await self._collect_no_keyword(source)
        if source_type == "deep_search":
            return await self._collect_deep_search(source)
        if source_type == "realtime_keyword":
            return await self._collect_realtime_keyword(source)
        if source_type == "realtime_all":
            return await self._collect_realtime_all(source)
        raise UnsupportedSourceError("unsupported collector source", details={"source_type": str(source_type)})

    async def _collect_direct(self, source: DirectPostSource) -> CollectorRun:
        deduper = CandidateDeduper()
        failures: list[CollectorFailure] = []
        candidates: list[PostCandidate] = []
        for url in source.urls:
            try:
                candidate = self.direct_normalizer.normalize(url)
            except Exception as exc:
                failures.append(CollectorFailure(stage="direct_url", reason=exc.__class__.__name__, retryable=False))
                continue
            if deduper.is_new(candidate):
                candidates.append(candidate)
        return CollectorRun(candidates=candidates, summary=self._summary("direct_post", candidates, failures=failures))

    async def _collect_board_list(self, source: BoardListSource) -> CollectorRun:
        return await self._collect_board_pages(
            mode="board_list",
            board_id=source.board_id,
            page_start=source.page_start,
            page_end=source.page_end,
            range_filter=source.range_filter,
            build_url=lambda page: self.board_urls.build_list_url(source.board_id, page, source.category_id),
        )

    async def _collect_board_search(self, source: BoardSearchSource) -> CollectorRun:
        return await self._collect_board_pages(
            mode="board_search",
            board_id=source.board_id,
            page_start=source.page_start,
            page_end=source.page_end,
            range_filter=source.range_filter,
            build_url=lambda page: self.board_urls.build_search_url(
                source.board_id,
                source.keyword,
                source.search_target,
                page,
                source.category_id,
            ),
        )

    async def _collect_no_keyword(self, source: NoKeywordRangeSource) -> CollectorRun:
        return await self._collect_board_pages(
            mode="no_keyword_range",
            board_id=source.board_id,
            page_start=1,
            page_end=None,
            range_filter=source.range_filter,
            build_url=lambda page: self.board_urls.build_list_url(source.board_id, page, source.category_id),
        )

    async def _collect_integrated(self, source: IntegratedSearchSource) -> CollectorRun:
        return await self._collect_integrated_pages(
            mode="integrated_search",
            keyword=source.keyword,
            search_target=source.search_target,
            page_start=source.page_start,
            page_end=source.page_end,
            range_filter=source.range_filter,
        )

    async def _collect_deep_search(self, source: DeepSearchSource) -> CollectorRun:
        seed = await self._collect_integrated_pages(
            mode="deep_search_seed",
            keyword=source.keyword,
            search_target=source.seed_search_target,
            page_start=1,
            page_end=source.seed_page_limit,
            range_filter=None,
            emit_candidates=False,
        )
        board_deduper = BoardCandidateDeduper(set(source.board_ids or []))
        board_ids = list(source.board_ids or [])
        for failure in seed.summary.failures:
            pass
        for board_id in seed.summary.metadata.get("board_ids", []):
            if board_deduper.is_new(str(board_id)):
                board_ids.append(str(board_id))

        candidates: list[PostCandidate] = []
        failures = list(seed.summary.failures)
        deduper = CandidateDeduper()
        visited_pages = seed.summary.visited_pages
        for board_id in board_ids:
            try:
                run = await self._collect_board_pages(
                    mode="deep_search_board",
                    board_id=board_id,
                    page_start=1,
                    page_end=None,
                    range_filter=source.range_filter,
                    build_url=lambda page, board_id=board_id: self.board_urls.build_search_url(
                        board_id,
                        source.keyword,
                        source.seed_search_target,
                        page,
                    ),
                    deduper=deduper,
                )
            except Exception as exc:
                failures.append(CollectorFailure(stage="deep_search_board", board_id=board_id, reason=exc.__class__.__name__))
                continue
            candidates.extend(run.candidates)
            failures.extend(run.summary.failures)
            visited_pages += run.summary.visited_pages

        summary = self._summary("deep_search", candidates, failures=failures)
        summary.visited_pages = visited_pages
        summary.board_candidate_count = len(board_ids)
        return CollectorRun(candidates=candidates, summary=summary)

    async def _collect_realtime_keyword(self, source: RealtimeKeywordSource) -> CollectorRun:
        if source.scope == "integrated":
            return await self._collect_integrated_pages(
                mode="realtime_keyword",
                keyword=source.keyword,
                search_target="title_content",
                page_start=1,
                page_end=1,
                range_filter=None,
            )
        if not source.board_id:
            raise ValidationFailure("board_id is required for board realtime keyword", details={"reason": "missing_board_id"})
        return await self._collect_board_pages(
            mode="realtime_keyword",
            board_id=source.board_id,
            page_start=1,
            page_end=1,
            range_filter=None,
            build_url=lambda page: self.board_urls.build_search_url(source.board_id or "", source.keyword, "title_content", page),
        )

    async def _collect_realtime_all(self, source: RealtimeAllSource) -> CollectorRun:
        return await self._collect_board_pages(
            mode="realtime_all",
            board_id=source.board_id,
            page_start=1,
            page_end=1,
            range_filter=None,
            build_url=lambda page: self.board_urls.build_list_url(source.board_id, page, source.category_id),
        )

    async def _collect_board_pages(
        self,
        *,
        mode: str,
        board_id: str,
        page_start: int,
        page_end: int | None,
        range_filter: RangeFilter | None,
        build_url: Any,
        deduper: CandidateDeduper | None = None,
    ) -> CollectorRun:
        deduper = deduper or CandidateDeduper()
        candidates: list[PostCandidate] = []
        failures: list[CollectorFailure] = []
        skipped = deduped = visited = 0
        stop_reason: str | None = None
        current_page = page_start

        while True:
            if page_end is not None and current_page > page_end:
                stop_reason = "page_end"
                break
            url = build_url(current_page)
            page_model, page_failures = self.board_parser.parse(
                _response_text(await self.http.get(url)),
                board_id=board_id,
                request_url=url,
                page=current_page,
            )
            visited += 1
            failures.extend(page_failures)
            if not page_model.candidates:
                stop_reason = "no_candidates"
                break
            for candidate in page_model.candidates:
                decision = self.range_evaluator.evaluate(range_filter, candidate)
                if decision.kind == RangeDecisionKind.STOP_TRAVERSAL:
                    stop_reason = decision.reason or decision.kind.value
                    break
                if decision.kind == RangeDecisionKind.SKIP_CONTINUE:
                    skipped += 1
                    continue
                if not deduper.is_new(candidate):
                    deduped += 1
                    continue
                candidates.append(candidate)
            if stop_reason:
                break
            if page_end is not None and current_page >= page_end:
                stop_reason = "page_end"
                break
            if not page_model.has_next:
                stop_reason = "no_next"
                break
            current_page += 1

        summary = self._summary(mode, candidates, failures=failures)
        summary.visited_pages = visited
        summary.skipped_count = skipped
        summary.deduped_count = deduped
        summary.range_stop_reason = stop_reason
        summary.final_state = SearchTraversalState(
            mode=mode,
            board_id=board_id,
            page=current_page,
            page_end=page_end,
            safe_url_label=self.board_urls.safe_label(build_url(current_page)),
            has_next=False,
            stop_reason=stop_reason,
            visited_pages=visited,
        )
        return CollectorRun(candidates=candidates, summary=summary)

    async def _collect_integrated_pages(
        self,
        *,
        mode: str,
        keyword: str,
        search_target: str,
        page_start: int,
        page_end: int | None,
        range_filter: RangeFilter | None,
        emit_candidates: bool = True,
    ) -> CollectorRun:
        deduper = CandidateDeduper()
        board_deduper = BoardCandidateDeduper()
        candidates: list[PostCandidate] = []
        board_candidates: list[BoardCandidate] = []
        failures: list[CollectorFailure] = []
        skipped = deduped = visited = 0
        stop_reason: str | None = None
        current_page = page_start

        while current_page <= (page_end or 1000):
            url = self.integrated_urls.build_search_url(keyword, search_target, current_page)
            page_model, boards, page_failures = self.integrated_parser.parse(
                _response_text(await self.http.get(url)),
                keyword=keyword,
                request_url=url,
                page=current_page,
            )
            visited += 1
            failures.extend(page_failures)
            board_candidates.extend(board_deduper.filter_new(boards))
            if not page_model.candidates:
                stop_reason = "no_candidates"
                break
            if emit_candidates:
                for candidate in page_model.candidates:
                    decision = self.range_evaluator.evaluate(range_filter, candidate)
                    if decision.kind == RangeDecisionKind.STOP_TRAVERSAL:
                        stop_reason = decision.reason or decision.kind.value
                        break
                    if decision.kind == RangeDecisionKind.SKIP_CONTINUE:
                        skipped += 1
                        continue
                    if not deduper.is_new(candidate):
                        deduped += 1
                        continue
                    candidates.append(candidate)
            if stop_reason:
                break
            if page_end is not None and current_page >= page_end:
                stop_reason = "page_end"
                break
            if not page_model.has_next or current_page >= 1000:
                stop_reason = "no_next" if not page_model.has_next else "integrated_page_limit"
                break
            current_page += 1

        summary = self._summary(mode, candidates, failures=failures)
        summary.visited_pages = visited
        summary.skipped_count = skipped
        summary.deduped_count = deduped
        summary.range_stop_reason = stop_reason
        summary.board_candidate_count = len(board_candidates)
        summary.metadata = {"board_ids": [board.board_id for board in board_candidates]}
        summary.final_state = SearchTraversalState(
            mode=mode,
            page=current_page,
            page_end=page_end,
            safe_url_label=self.integrated_urls.safe_label(self.integrated_urls.build_search_url(keyword, search_target, current_page)),
            has_next=False,
            stop_reason=stop_reason,
            visited_pages=visited,
        )
        return CollectorRun(candidates=candidates, summary=summary)

    def _summary(self, mode: str, candidates: list[PostCandidate], *, failures: list[CollectorFailure]) -> CollectorSummary:
        return CollectorSummary(
            mode=mode,
            candidate_count=len(candidates),
            failures=failures,
        )


async def collect_all(service: LinkCollectorService, source: Any) -> list[PostCandidate]:
    return [candidate async for candidate in service.collect(source)]
