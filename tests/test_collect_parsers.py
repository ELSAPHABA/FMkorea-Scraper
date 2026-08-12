from __future__ import annotations

from pathlib import Path

from fmkorea_scraper.collect.parsers import BoardPageParser, IntegratedSearchParser

FIXTURES = Path(__file__).parent / "fixtures" / "collect"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_board_page_parser_extracts_candidates_and_skips_notice() -> None:
    page, failures = BoardPageParser().parse(fixture("board_list.html"), board_id="best", page=1)

    assert len(page.candidates) == 2
    assert failures == []
    assert page.candidates[0].document_srl == 10195585295
    assert page.candidates[0].candidate_title == "첫 글"
    assert page.candidates[0].candidate_created_at is not None
    assert page.has_next is False


def test_board_page_parser_records_malformed_row_failure() -> None:
    page, failures = BoardPageParser().parse(fixture("board_malformed.html"), board_id="best", page=1)

    assert [candidate.document_srl for candidate in page.candidates] == [10195585297]
    assert len(failures) == 1
    assert failures[0].stage == "board_row"


def test_integrated_search_parser_extracts_posts_and_boards() -> None:
    page, boards, failures = IntegratedSearchParser().parse(
        fixture("integrated_search.html"),
        keyword="검색",
        page=1,
    )

    assert [candidate.document_srl for candidate in page.candidates] == [10196696065, 10192764813]
    assert [board.board_id for board in boards] == ["football_world", "lol"]
    assert page.board_ids == ["football_world", "lol"]
    assert page.has_next is True
    assert failures == []


def test_empty_page_parser_returns_no_candidates() -> None:
    page, failures = BoardPageParser().parse(fixture("empty.html"), board_id="best", page=1)

    assert page.candidates == []
    assert failures == []
