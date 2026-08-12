from __future__ import annotations

import asyncio
from pathlib import Path

from fmkorea_scraper.collect import LinkCollectorService
from fmkorea_scraper.models.job import BoardListSource, BoardSearchSource, DeepSearchSource, IntegratedSearchSource, RangeFilter

FIXTURES = Path(__file__).parent / "fixtures" / "collect"


class FakeHttp:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    async def get(self, url: str):
        self.requested.append(url)
        return self.responses[url]


def run(coro):
    return asyncio.run(coro)


def text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_board_list_collector_uses_injected_http_and_returns_summary() -> None:
    url = "https://www.fmkorea.com/best?page=1"
    service = LinkCollectorService(FakeHttp({url: text("board_list.html")}))

    result = run(service.collect_with_summary(BoardListSource(board_id="best", page_end=1)))

    assert len(result.candidates) == 2
    assert result.summary.visited_pages == 1
    assert result.summary.final_state is not None
    assert result.summary.final_state.stop_reason == "page_end"


def test_integrated_collector_extracts_candidates() -> None:
    url = "https://www.fmkorea.com/search.php?act=IS&is_keyword=%EA%B2%80%EC%83%89&where=document&search_target=title_content&page=1"
    service = LinkCollectorService(FakeHttp({url: text("integrated_search.html")}))

    result = run(
        service.collect_with_summary(
            IntegratedSearchSource(keyword="검색", search_target="title_content", page_end=1)
        )
    )

    assert [candidate.board_id for candidate in result.candidates] == ["football_world", "lol"]
    assert result.summary.board_candidate_count == 2


def test_deep_search_uses_seed_boards_then_board_search() -> None:
    seed = "https://www.fmkorea.com/search.php?act=IS&is_keyword=%EA%B2%80%EC%83%89&where=document&search_target=title_content&page=1"
    football = "https://www.fmkorea.com/search.php?mid=football_world&search_target=title_content&search_keyword=%EA%B2%80%EC%83%89&page=1"
    lol = "https://www.fmkorea.com/search.php?mid=lol&search_target=title_content&search_keyword=%EA%B2%80%EC%83%89&page=1"
    service = LinkCollectorService(
        FakeHttp(
            {
                seed: text("integrated_search.html"),
                football: text("board_list.html"),
                lol: text("empty.html"),
            }
        )
    )

    result = run(
        service.collect_with_summary(
            DeepSearchSource(
                keyword="검색",
                seed_search_target="title_content",
                seed_page_limit=1,
                range_filter=RangeFilter(min_document_srl=1),
            )
        )
    )

    assert result.summary.board_candidate_count == 2
    assert [candidate.document_srl for candidate in result.candidates] == [10195585295, 10195585296]


def test_collect_all_helper_consumes_async_iterator() -> None:
    url = "https://www.fmkorea.com/search.php?mid=best&search_target=title_content&search_keyword=%EA%B2%80%EC%83%89&page=1"
    service = LinkCollectorService(FakeHttp({url: text("board_list.html")}))

    async def scenario():
        return [candidate async for candidate in service.collect(BoardSearchSource(board_id="best", keyword="검색", search_target="title_content", page_end=1))]

    assert len(run(scenario())) == 2
