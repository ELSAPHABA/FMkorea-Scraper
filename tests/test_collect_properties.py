from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from fmkorea_scraper.collect.models import RangeDecisionKind  # noqa: E402
from fmkorea_scraper.collect.policies import BoardCandidateDeduper, CandidateDeduper, RangeFilterEvaluator  # noqa: E402
from fmkorea_scraper.collect.urls import BoardUrlBuilder, IntegratedSearchUrlBuilder  # noqa: E402
from fmkorea_scraper.models.job import PostCandidate, RangeFilter  # noqa: E402
from tests.strategies.collect import board_ids, document_ids, post_candidates  # noqa: E402


@given(board_ids, st.text(min_size=1, max_size=30), st.integers(min_value=1, max_value=10_000))
def test_board_search_url_builder_is_deterministic(board_id: str, keyword: str, page: int) -> None:
    builder = BoardUrlBuilder()

    assert builder.build_search_url(board_id, keyword, "title_content", page) == builder.build_search_url(
        board_id,
        keyword,
        "title_content",
        page,
    )


@given(st.integers(min_value=1, max_value=100_000))
def test_integrated_page_clamp_never_exceeds_limit(page: int) -> None:
    assert IntegratedSearchUrlBuilder().clamp_page(page) <= 1000


@given(post_candidates)
def test_candidate_dedupe_is_idempotent(candidate: PostCandidate) -> None:
    deduper = CandidateDeduper()

    assert deduper.is_new(candidate) is True
    assert deduper.is_new(candidate) is False


@given(document_ids)
def test_range_filter_document_bounds_are_monotonic(document_srl: int) -> None:
    candidate = PostCandidate(
        document_srl=document_srl,
        document_id_raw=str(document_srl),
        url=f"https://www.fmkorea.com/{document_srl}",
    )
    decision = RangeFilterEvaluator().evaluate(
        RangeFilter(min_document_srl=100, max_document_srl=200),
        candidate,
    )

    if document_srl < 100:
        assert decision.kind == RangeDecisionKind.STOP_TRAVERSAL
    elif document_srl > 200:
        assert decision.kind == RangeDecisionKind.SKIP_CONTINUE
    else:
        assert decision.kind == RangeDecisionKind.INCLUDE


@given(st.lists(board_ids, min_size=1, max_size=20))
def test_board_candidate_dedupe_keeps_unique_ids(ids: list[str]) -> None:
    deduper = BoardCandidateDeduper()

    kept = [board_id for board_id in ids if deduper.is_new(board_id)]

    assert kept == list(dict.fromkeys(ids))
