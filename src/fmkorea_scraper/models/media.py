"""Media and attachment contracts."""

from __future__ import annotations

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.enums import ContentBlockType


class Attachment(MetadataModel):
    file_name: str | None = Field(default=None, max_length=500)
    url: str = Field(min_length=1, max_length=4096)
    size_text: str | None = Field(default=None, max_length=100)
    file_srl: str | None = Field(default=None, max_length=100)
    sid: str | None = Field(default=None, max_length=200)
    mid: str | None = Field(default=None, max_length=100)
    download_text: str | None = Field(default=None, max_length=500)
    file_path: str | None = None
    object_key: str | None = None


class MediaItem(MetadataModel):
    media_id: str | None = Field(default=None, max_length=200)
    media_type: ContentBlockType
    source_block_order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    file_path: str | None = None
    object_key: str | None = None
    description: str | None = None
    provider: str | None = Field(default=None, max_length=100)
    embed_url: str | None = Field(default=None, max_length=4096)
    file_srl: str | None = Field(default=None, max_length=100)
