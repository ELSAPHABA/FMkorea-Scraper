"""Post result contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.comment import AuthorInfo, Comment, ReactionInfo
from fmkorea_scraper.models.content import BodyContent
from fmkorea_scraper.models.job import utc_now
from fmkorea_scraper.models.media import Attachment, MediaItem


class CategoryInfo(MetadataModel):
    category_id: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=4096)


class PostResult(MetadataModel):
    schema_version: Literal["fmkorea.post.v1"] = "fmkorea.post.v1"
    scraped_at: datetime = Field(default_factory=utc_now)
    site_id: Literal["fmkorea"] = "fmkorea"
    board_id: str | None = Field(default=None, max_length=100)
    board_name: str | None = Field(default=None, max_length=200)
    document_srl: int | None = Field(default=None, ge=0)
    document_id_raw: str = Field(min_length=1, max_length=100)
    canonical_url: str = Field(min_length=1, max_length=4096)
    category: CategoryInfo | None = None
    title: str = Field(min_length=1, max_length=1000)
    author: AuthorInfo
    created_at: datetime | None = None
    created_at_raw: str | None = Field(default=None, max_length=100)
    views: int | None = Field(default=None, ge=0)
    reactions: ReactionInfo = Field(default_factory=ReactionInfo)
    comment_count: int | None = Field(default=None, ge=0)
    content: BodyContent = Field(default_factory=BodyContent)
    attachments: list[Attachment] = Field(default_factory=list)
    media: list[MediaItem] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
