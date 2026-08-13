"""Parser-only value objects."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.enums import CommentMode
from fmkorea_scraper.models.job import PostCandidate, PostRequest


class ParserOptions(MetadataModel):
    comment_mode: CommentMode = CommentMode.ALL
    max_comment_pages: int | None = Field(default=None, ge=1)
    max_content_blocks: int | None = Field(default=None, ge=1)
    max_comments: int | None = Field(default=None, ge=1)


@dataclass(frozen=True)
class DetailParseContext:
    source_url: str
    base_url: str
    candidate: PostCandidate | None = None
    post_request: PostRequest | None = None
    site_id: str = "fmkorea"
    board_id_hint: str | None = None
    document_id_hint: str | None = None
