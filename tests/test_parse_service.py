from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from fmkorea_scraper.core.errors import ParseFailureError
from fmkorea_scraper.models.content import FmkVideoBlock, ImageBlock, XBlock, YouTubeBlock
from fmkorea_scraper.models.enums import CommentMode
from fmkorea_scraper.models.job import PostCandidate
from fmkorea_scraper.parse import ParserOptions, PostDetailService

FIXTURES = Path(__file__).parent / "fixtures" / "parse"


class FakeHttp:
    def __init__(self, html: str | dict[str, str]) -> None:
        self.html = html
        self.requested: list[str] = []

    async def get(self, url: str):
        self.requested.append(url)
        if isinstance(self.html, dict):
            return self.html[url]
        return self.html


def text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def candidate() -> PostCandidate:
    return PostCandidate(
        board_id="best",
        document_srl=10195585295,
        document_id_raw="10195585295",
        url="https://www.fmkorea.com/best/10195585295",
        candidate_title="candidate title",
    )


def test_parse_html_extracts_metadata_content_media_attachments_and_comments() -> None:
    post = PostDetailService().parse_html(text("detail_full.html"), candidate())

    assert post.document_srl == 10195585295
    assert post.board_id == "best"
    assert post.title == "sample title"
    assert post.views == 1234
    assert post.reactions.up_count == 56
    assert post.comment_count == 2
    assert "hello world" in post.content.text
    assert any(isinstance(block, ImageBlock) and block.file_srl == "fs1" for block in post.content.blocks)
    assert any(isinstance(block, FmkVideoBlock) and block.video_url.endswith("/video.mp4") for block in post.content.blocks)
    assert any(isinstance(block, YouTubeBlock) and block.video_id == "abc123" for block in post.content.blocks)
    assert any(isinstance(block, XBlock) and block.tweet_id == "987654321" for block in post.content.blocks)
    assert post.attachments[0].file_srl == "fs1"
    assert post.comments[0].is_best is True
    assert post.comments[0].reactions.score == 5
    assert {item.media_type.value for item in post.media} >= {"image", "fmk_video", "youtube", "x"}


def test_parse_uses_injected_http() -> None:
    http = FakeHttp(text("detail_full.html"))
    post = asyncio.run(PostDetailService(http).parse(candidate()))

    assert post.title == "sample title"
    assert http.requested == ["https://www.fmkorea.com/best/10195585295"]


def test_parse_respects_comment_mode_none() -> None:
    post = PostDetailService(options=ParserOptions(comment_mode=CommentMode.NONE)).parse_html(text("detail_full.html"), candidate())

    assert post.comments == []


def test_parse_skips_server_log_text() -> None:
    html = text("detail_full.html").replace("<p>hello world</p>", "<p>hello world</p><p>serverLog: f32</p>")
    post = PostDetailService().parse_html(html, candidate())

    assert "hello world" in post.content.text
    assert "serverLog:" not in post.content.text


def test_parse_fetches_bounded_extra_comment_pages_and_dedupes_comments() -> None:
    first_url = "https://www.fmkorea.com/best/10195585295"
    second_url = "https://www.fmkorea.com/best/10195585295?cpage=2"
    http = FakeHttp({first_url: text("detail_full.html"), second_url: text("comment_page.html")})

    post = asyncio.run(PostDetailService(http, options=ParserOptions(max_comment_pages=1)).parse(candidate()))

    assert http.requested == [first_url, second_url]
    assert [comment.comment_srl for comment in post.comments] == [101, 202]
    assert post.comments[1].source_order == 2
    assert post.comments[1].reactions.score == 2


def test_missing_required_metadata_raises_parse_failure() -> None:
    with pytest.raises(ParseFailureError):
        PostDetailService().parse_html(text("detail_missing_required.html"), candidate())
