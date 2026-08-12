"""Ordered post body content block contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.media import Attachment


class TextBlock(MetadataModel):
    type: Literal["text"] = "text"
    order: int = Field(ge=0)
    text: str


class ImageBlock(MetadataModel):
    type: Literal["image"] = "image"
    order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    original_url: str | None = Field(default=None, max_length=4096)
    alt: str | None = Field(default=None, max_length=1000)
    file_path: str | None = None
    object_key: str | None = None


class FmkVideoBlock(MetadataModel):
    type: Literal["fmk_video"] = "fmk_video"
    order: int = Field(ge=0)
    video_url: str | None = Field(default=None, max_length=4096)
    poster_url: str | None = Field(default=None, max_length=4096)
    description: str | None = None
    duration: str | None = Field(default=None, max_length=100)
    file_path: str | None = None
    object_key: str | None = None


class YouTubeBlock(MetadataModel):
    type: Literal["youtube"] = "youtube"
    order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    video_id: str | None = Field(default=None, max_length=200)
    embed_url: str | None = Field(default=None, max_length=4096)
    title: str | None = Field(default=None, max_length=1000)


class XBlock(MetadataModel):
    type: Literal["x"] = "x"
    order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    username: str | None = Field(default=None, max_length=200)
    status_id: str | None = Field(default=None, max_length=200)
    text: str | None = None


class LinkBlock(MetadataModel):
    type: Literal["link"] = "link"
    order: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=4096)
    text: str | None = Field(default=None, max_length=1000)
    title: str | None = Field(default=None, max_length=1000)


class AttachmentBlock(MetadataModel):
    type: Literal["attachment"] = "attachment"
    order: int = Field(ge=0)
    attachment: Attachment


class UnknownEmbedBlock(MetadataModel):
    type: Literal["unknown_embed"] = "unknown_embed"
    order: int = Field(ge=0)
    provider: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=4096)
    safe_text: str | None = Field(default=None, max_length=2000)


ContentBlock = Annotated[
    TextBlock
    | ImageBlock
    | FmkVideoBlock
    | YouTubeBlock
    | XBlock
    | LinkBlock
    | AttachmentBlock
    | UnknownEmbedBlock,
    Field(discriminator="type"),
]


class BodyContent(MetadataModel):
    text: str = ""
    blocks: list[ContentBlock] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_orders(self) -> "BodyContent":
        orders = [block.order for block in self.blocks]
        if len(orders) != len(set(orders)):
            raise ValueError("content block orders must be unique")
        return self
