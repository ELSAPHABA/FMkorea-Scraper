"""Pure range, dedupe, and traversal policies."""

from __future__ import annotations

from datetime import datetime

from fmkorea_scraper.collect.models import BoardCandidate, RangeDecision, RangeDecisionKind
from fmkorea_scraper.collect.urls import INTEGRATED_MAX_PAGE
from fmkorea_scraper.models.job import PostCandidate, RangeFilter


class RangeFilterEvaluator:
    def evaluate(
        self,
        range_filter: RangeFilter | None,
        candidate: PostCandidate,
        *,
        descending: bool = True,
    ) -> RangeDecision:
        if range_filter is None or not range_filter.has_any_bound():
            return RangeDecision(kind=RangeDecisionKind.INCLUDE)

        if candidate.document_srl is not None:
            if range_filter.min_document_srl is not None and candidate.document_srl < range_filter.min_document_srl:
                return RangeDecision(
                    kind=RangeDecisionKind.STOP_TRAVERSAL if descending else RangeDecisionKind.SKIP_CONTINUE,
                    reason="below_min_document_srl",
                )
            if range_filter.max_document_srl is not None and candidate.document_srl > range_filter.max_document_srl:
                return RangeDecision(kind=RangeDecisionKind.SKIP_CONTINUE, reason="above_max_document_srl")

        created = candidate.candidate_created_at
        if created is None and (range_filter.date_from or range_filter.date_to):
            return RangeDecision(kind=RangeDecisionKind.INCLUDE_NEEDS_DETAIL_VALIDATION, reason="missing_candidate_date")

        if created is not None:
            candidate_date = created.date()
            if range_filter.date_from and candidate_date < range_filter.date_from:
                return RangeDecision(
                    kind=RangeDecisionKind.STOP_TRAVERSAL if descending else RangeDecisionKind.SKIP_CONTINUE,
                    reason="older_than_date_from",
                )
            if range_filter.date_to and candidate_date > range_filter.date_to:
                return RangeDecision(kind=RangeDecisionKind.SKIP_CONTINUE, reason="newer_than_date_to")

        return RangeDecision(kind=RangeDecisionKind.INCLUDE)


class CandidateDeduper:
    def __init__(self, seen: set[tuple[str, ...]] | None = None) -> None:
        self.seen = seen if seen is not None else set()

    def key(self, candidate: PostCandidate) -> tuple[str, ...]:
        if candidate.board_id:
            return (candidate.site_id, candidate.board_id, candidate.document_id_raw)
        return (candidate.site_id, candidate.document_id_raw)

    def is_new(self, candidate: PostCandidate) -> bool:
        key = self.key(candidate)
        if key in self.seen:
            return False
        self.seen.add(key)
        return True

    def filter_new(self, candidates: list[PostCandidate]) -> list[PostCandidate]:
        return [candidate for candidate in candidates if self.is_new(candidate)]


class BoardCandidateDeduper:
    def __init__(self, seen: set[str] | None = None) -> None:
        self.seen = seen if seen is not None else set()

    def is_new(self, candidate: BoardCandidate | str) -> bool:
        board_id = candidate if isinstance(candidate, str) else candidate.board_id
        if board_id in self.seen:
            return False
        self.seen.add(board_id)
        return True

    def filter_new(self, candidates: list[BoardCandidate]) -> list[BoardCandidate]:
        return [candidate for candidate in candidates if self.is_new(candidate)]


def clamp_integrated_page(page: int) -> int:
    if page < 1:
        raise ValueError("page must be >= 1")
    return min(page, INTEGRATED_MAX_PAGE)
