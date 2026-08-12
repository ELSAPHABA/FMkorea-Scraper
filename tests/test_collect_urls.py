from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from fmkorea_scraper.collect.urls import BoardUrlBuilder, DirectPostUrlNormalizer, IntegratedSearchUrlBuilder
from fmkorea_scraper.core.errors import ValidationFailure


def test_direct_post_normalizer_accepts_query_url() -> None:
    candidate = DirectPostUrlNormalizer().normalize(
        "https://www.fmkorea.com/index.php?mid=best&document_srl=10195585295"
    )

    assert candidate.board_id == "best"
    assert candidate.document_srl == 10195585295
    assert candidate.document_id_raw == "10195585295"


def test_direct_post_normalizer_rejects_other_host() -> None:
    with pytest.raises(ValidationFailure):
        DirectPostUrlNormalizer().normalize("https://example.com/10195585295")


def test_board_search_url_uses_structured_query_encoding() -> None:
    url = BoardUrlBuilder().build_search_url("best", "검색 단어", "title_content", page=3, category_id="1")
    query = parse_qs(urlsplit(url).query)

    assert query["mid"] == ["best"]
    assert query["search_keyword"] == ["검색 단어"]
    assert query["search_target"] == ["title_content"]
    assert query["page"] == ["3"]
    assert query["category"] == ["1"]


def test_integrated_search_url_clamps_page_and_safe_label_drops_keyword() -> None:
    builder = IntegratedSearchUrlBuilder()
    url = builder.build_search_url("비밀 키워드", "title_content", page=9999)
    query = parse_qs(urlsplit(url).query)

    assert query["page"] == ["1000"]
    assert "비밀" not in builder.safe_label(url)
