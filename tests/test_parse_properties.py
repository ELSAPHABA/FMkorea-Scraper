from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from fmkorea_scraper.models.comment import ReactionInfo
from fmkorea_scraper.models.content import BodyContent, TextBlock
from fmkorea_scraper.parse.comments import CommentParser
from fmkorea_scraper.parse.media import MediaDeduper, normalize_url
from fmkorea_scraper.parse.warnings import WarningRedactor


@given(st.lists(st.integers(min_value=0, max_value=1000), unique=True))
def test_body_content_accepts_unique_orders(orders: list[int]) -> None:
    content = BodyContent(blocks=[TextBlock(order=order, text="x") for order in orders])
    assert [block.order for block in content.blocks] == orders


@given(st.text(min_size=1, max_size=50))
def test_normalize_url_keeps_protocol_relative_urls_absolute(path: str) -> None:
    normalized = normalize_url(f"//example.com/{path}")
    assert normalized is not None
    assert normalized.startswith("https://example.com/")


@given(st.text(min_size=1, max_size=50))
def test_media_deduper_is_idempotent(key: str) -> None:
    deduper = MediaDeduper()
    assert deduper.is_new("image", file_srl=key) is True
    assert deduper.is_new("image", file_srl=key) is False


@given(st.integers(min_value=0, max_value=100), st.integers(min_value=0, max_value=100))
def test_reaction_score_is_up_minus_down(up: int, down: int) -> None:
    reactions = ReactionInfo(up_count=up, down_count=down)
    assert reactions.score == up - down


@given(st.integers(min_value=0, max_value=10**12))
def test_comment_id_parser_extracts_numeric_id(comment_id: int) -> None:
    assert CommentParser()._comment_srl(f"comment_{comment_id}_") == comment_id


@given(st.text(min_size=1, max_size=100))
def test_warning_redactor_redacts_html_like_payloads(payload: str) -> None:
    assert WarningRedactor.safe_text(f"<html>{payload}</html>") == "[REDACTED]"
