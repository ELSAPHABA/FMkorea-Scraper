"""Collector-only value objects."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.job import PostCandidate


class RangeDecisionKind(str, Enum):
    INCLUDE = "include"
    SKIP_CONTINUE = "skip_continue"
    STOP_TRAVERSAL = "stop_traversal"
    INCLUDE_NEEDS_DETAIL_VALIDATION = "include_needs_detail_validation"


class RangeDecision(MetadataModel):
    kind: RangeDecisionKind
    reason: str | None = Field(default=None, max_length=200)


class SearchTraversalState(MetadataModel):
    mode: str = Field(min_length=1, max_length=100)
    board_id: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    safe_url_label: str | None = Field(default=None, max_length=500)
    has_next: bool = False
    stop_reason: str | None = Field(default=None, max_length=200)
    visited_pages: int = Field(default=0, ge=0)


class BoardCandidate(MetadataModel):
    board_id: str = Field(min_length=1, max_length=100)
    board_name: str | None = Field(default=None, max_length=200)
    board_url: str | None = Field(default=None, max_length=4096)


class CollectorFailure(MetadataModel):
    stage: str = Field(min_length=1, max_length=100)
    board_id: str | None = Field(default=None, max_length=100)
    safe_url_label: str | None = Field(default=None, max_length=500)
    reason: str = Field(min_length=1, max_length=300)
    retryable: bool = False


class CollectorSummary(MetadataModel):
    mode: str = Field(min_length=1, max_length=100)
    visited_pages: int = Field(default=0, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    deduped_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    range_stop_reason: str | None = Field(default=None, max_length=200)
    board_candidate_count: int = Field(default=0, ge=0)
    failures: list[CollectorFailure] = Field(default_factory=list)
    final_state: SearchTraversalState | None = None


class CollectorRun(MetadataModel):
    candidates: list[PostCandidate] = Field(default_factory=list)
    summary: CollectorSummary


SearchMode = Literal[
    "direct_post",
    "board_list",
    "board_search",
    "integrated_search",
    "deep_search",
    "no_keyword_range",
    "realtime_keyword",
    "realtime_all",
]
