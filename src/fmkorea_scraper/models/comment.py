"""Author, reaction, and comment contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from fmkorea_scraper.models.base import MetadataModel


class AuthorInfo(MetadataModel):
    nickname: str | None = Field(default=None, max_length=200)
    member_srl: str | None = Field(default=None, max_length=200)
    level: str | None = Field(default=None, max_length=100)
    profile_url: str | None = Field(default=None, max_length=4096)


class ReactionInfo(MetadataModel):
    up_count: int = Field(default=0, ge=0)
    down_count: int = Field(default=0, ge=0)
    score: int | None = None

    @model_validator(mode="after")
    def _validate_or_fill_score(self) -> "ReactionInfo":
        expected = self.up_count - self.down_count
        if self.score is None:
            self.score = expected
            return self
        if self.score != expected:
            raise ValueError("score must equal up_count - down_count")
        return self


class Comment(MetadataModel):
    comment_srl: int | None = Field(default=None, ge=0)
    comment_id_raw: str | None = Field(default=None, max_length=100)
    source_dom_id: str | None = Field(default=None, max_length=200)
    source_order: int = Field(ge=0)
    parent_comment_srl: int | None = Field(default=None, ge=0)
    parent_comment_id_raw: str | None = Field(default=None, max_length=100)
    depth: int | None = Field(default=0, ge=0)
    is_best: bool = False
    badges: list[str] = Field(default_factory=list, max_length=20)
    author: AuthorInfo = Field(default_factory=AuthorInfo)
    created_at: datetime | None = None
    created_at_raw: str | None = Field(default=None, max_length=100)
    content: str = ""
    reactions: ReactionInfo = Field(default_factory=ReactionInfo)
    permalink: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def _normalize_best_badge(self) -> "Comment":
        if self.is_best and "BEST" not in self.badges:
            self.badges = [*self.badges, "BEST"]
        return self
