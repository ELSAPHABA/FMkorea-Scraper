"""Job configuration, source, request, and search result contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fmkorea_scraper.models.base import MetadataModel
from fmkorea_scraper.models.enums import CheckpointMode, CommentMode, JobType, MediaMode, StorageMode


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RangeFilter(MetadataModel):
    date_from: date | None = None
    date_to: date | None = None
    min_document_srl: int | None = Field(default=None, ge=0)
    max_document_srl: int | None = Field(default=None, ge=0)

    def has_any_bound(self) -> bool:
        return any(
            value is not None
            for value in (
                self.date_from,
                self.date_to,
                self.min_document_srl,
                self.max_document_srl,
            )
        )

    @model_validator(mode="after")
    def _validate_order(self) -> "RangeFilter":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before or equal to date_to")
        if (
            self.min_document_srl is not None
            and self.max_document_srl is not None
            and self.min_document_srl > self.max_document_srl
        ):
            raise ValueError("min_document_srl must be <= max_document_srl")
        return self


class RealtimeTermination(MetadataModel):
    duration_seconds: int | None = Field(default=None, ge=1)
    end_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_exactly_one_stop_condition(self) -> "RealtimeTermination":
        if (self.duration_seconds is None) == (self.end_at is None):
            raise ValueError("exactly one of duration_seconds or end_at is required")
        return self


class ScrapeOptions(MetadataModel):
    comment_mode: CommentMode = CommentMode.ALL
    media_mode: MediaMode = MediaMode.URL_ONLY
    include_attachments: bool = True
    request_interval_seconds: float = Field(default=1.0, ge=0)
    max_post_retries: int = Field(default=3, ge=0)


class WorkerConfig(MetadataModel):
    post_worker_count: int = Field(default=1, ge=1)
    media_worker_count: int = Field(default=1, ge=1)
    queue_max_size: int | None = Field(default=None, ge=1)


class RuntimeConfig(MetadataModel):
    user_agent_file: str | None = Field(default=None, max_length=4096)
    user_agent_rotate_every: int = Field(default=10, ge=1)
    proxy_enabled: bool = False
    proxy_env_prefix: str = Field(default="FMKOREA_PROXY", min_length=1, max_length=100)
    cookie_file: str | None = Field(default=None, max_length=4096)
    timeout_seconds: float = Field(default=30.0, gt=0)


class S3StorageConfig(MetadataModel):
    endpoint_url: str = Field(min_length=1, max_length=4096)
    bucket: str = Field(min_length=1, max_length=255)
    prefix: str | None = Field(default=None, max_length=1024)
    region: str | None = Field(default=None, max_length=100)


class PostgresCheckpointConfig(MetadataModel):
    dsn: str = Field(min_length=1, max_length=4096)


class StorageConfig(MetadataModel):
    output_mode: StorageMode = StorageMode.LOCAL
    checkpoint_mode: CheckpointMode = CheckpointMode.LOCAL
    base_output_path: str | None = Field(default=None, max_length=4096)
    s3: S3StorageConfig | None = None
    postgres: PostgresCheckpointConfig | None = None

    @model_validator(mode="after")
    def _validate_selected_backends(self) -> "StorageConfig":
        if self.output_mode == StorageMode.S3_COMPATIBLE and self.s3 is None:
            raise ValueError("s3 config is required when output_mode is s3_compatible")
        if self.checkpoint_mode == CheckpointMode.POSTGRES and self.postgres is None:
            raise ValueError("postgres config is required when checkpoint_mode is postgres")
        return self


class FailureInput(MetadataModel):
    failure_path: str = Field(min_length=1, max_length=4096)
    job_id: str | None = Field(default=None, max_length=200)
    stage_allowlist: list[str] = Field(default_factory=lambda: ["post"], max_length=20)


class DirectPostSource(MetadataModel):
    type: Literal["direct_post"] = "direct_post"
    urls: list[str] = Field(min_length=1, max_length=100_000)

    @field_validator("urls")
    @classmethod
    def _validate_urls(cls, urls: list[str]) -> list[str]:
        for url in urls:
            if "fmkorea.com" not in url:
                raise ValueError("url must be an FMKorea URL")
        return urls


class BoardListSource(MetadataModel):
    type: Literal["board_list"] = "board_list"
    board_id: str = Field(min_length=1, max_length=100)
    category_id: str | None = Field(default=None, max_length=100)
    page_start: int = Field(default=1, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    range_filter: RangeFilter | None = None

    @model_validator(mode="after")
    def _validate_page_range(self) -> "BoardListSource":
        if self.page_end is not None and self.page_start > self.page_end:
            raise ValueError("page_start must be <= page_end")
        return self


class BoardSearchSource(BoardListSource):
    type: Literal["board_search"] = "board_search"
    keyword: str = Field(min_length=1, max_length=500)
    search_target: str = Field(min_length=1, max_length=100)


class IntegratedSearchSource(MetadataModel):
    type: Literal["integrated_search"] = "integrated_search"
    keyword: str = Field(min_length=1, max_length=500)
    search_target: str = Field(min_length=1, max_length=100)
    page_start: int = Field(default=1, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    range_filter: RangeFilter | None = None

    @model_validator(mode="after")
    def _validate_page_range(self) -> "IntegratedSearchSource":
        if self.page_end is not None and self.page_start > self.page_end:
            raise ValueError("page_start must be <= page_end")
        return self


class DeepSearchSource(MetadataModel):
    type: Literal["deep_search"] = "deep_search"
    keyword: str = Field(min_length=1, max_length=500)
    seed_search_target: str = Field(min_length=1, max_length=100)
    seed_page_limit: int = Field(default=20, ge=1)
    board_ids: list[str] | None = Field(default=None, max_length=10_000)
    range_filter: RangeFilter

    @model_validator(mode="after")
    def _validate_range(self) -> "DeepSearchSource":
        if not self.range_filter.has_any_bound():
            raise ValueError("deep_search requires a date or document range")
        return self


class NoKeywordRangeSource(MetadataModel):
    type: Literal["no_keyword_range"] = "no_keyword_range"
    board_id: str = Field(min_length=1, max_length=100)
    category_id: str | None = Field(default=None, max_length=100)
    range_filter: RangeFilter

    @model_validator(mode="after")
    def _validate_range(self) -> "NoKeywordRangeSource":
        if not self.range_filter.has_any_bound():
            raise ValueError("no_keyword_range requires a date or document range")
        return self


class RealtimeKeywordSource(MetadataModel):
    type: Literal["realtime_keyword"] = "realtime_keyword"
    scope: Literal["board", "integrated"] = "board"
    board_id: str | None = Field(default=None, max_length=100)
    keyword: str = Field(min_length=1, max_length=500)
    poll_interval_seconds: float = Field(default=30.0, ge=1.0)
    termination: RealtimeTermination


class RealtimeAllSource(MetadataModel):
    type: Literal["realtime_all"] = "realtime_all"
    board_id: str = Field(min_length=1, max_length=100)
    category_id: str | None = Field(default=None, max_length=100)
    poll_interval_seconds: float = Field(default=30.0, ge=1.0)
    termination: RealtimeTermination


class ParserFailureRetrySource(MetadataModel):
    type: Literal["parser_failure_retry"] = "parser_failure_retry"
    failure_input: FailureInput
    skip_existing_success: bool = True


JobSource = Annotated[
    DirectPostSource
    | BoardListSource
    | BoardSearchSource
    | IntegratedSearchSource
    | DeepSearchSource
    | NoKeywordRangeSource
    | RealtimeKeywordSource
    | RealtimeAllSource
    | ParserFailureRetrySource,
    Field(discriminator="type"),
]


class JobConfig(MetadataModel):
    job_id: str = Field(min_length=1, max_length=200)
    job_type: JobType
    site_id: Literal["fmkorea"] = "fmkorea"
    source: JobSource
    scrape_options: ScrapeOptions = Field(default_factory=ScrapeOptions)
    worker_config: WorkerConfig = Field(default_factory=WorkerConfig)
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)
    storage_config: StorageConfig = Field(default_factory=StorageConfig)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_source_type(self) -> "JobConfig":
        if self.job_type.value != self.source.type:
            raise ValueError("job_type must match source.type")
        return self


class BoardSearchRequest(MetadataModel):
    board_id: str = Field(min_length=1, max_length=100)
    keyword: str | None = Field(default=None, max_length=500)
    search_target: str | None = Field(default=None, max_length=100)
    category_id: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)


class IntegratedSearchRequest(MetadataModel):
    keyword: str = Field(min_length=1, max_length=500)
    search_target: str = Field(min_length=1, max_length=100)
    page: int = Field(default=1, ge=1)


class PostRequest(MetadataModel):
    url: str = Field(min_length=1, max_length=4096)
    board_id: str | None = Field(default=None, max_length=100)
    document_srl: int | None = Field(default=None, ge=0)
    document_id_raw: str | None = Field(default=None, max_length=100)
    scrape_options: ScrapeOptions = Field(default_factory=ScrapeOptions)


class CommentRequest(MetadataModel):
    url: str = Field(min_length=1, max_length=4096)
    board_id: str | None = Field(default=None, max_length=100)
    document_srl: int | None = Field(default=None, ge=0)
    comment_mode: CommentMode = CommentMode.ALL


class ResumeRequest(MetadataModel):
    job_id: str | None = Field(default=None, max_length=200)


class RetryRequest(MetadataModel):
    failure_input: FailureInput
    skip_existing_success: bool = True


class PostKey(MetadataModel):
    site_id: Literal["fmkorea"] = "fmkorea"
    board_id: str | None = Field(default=None, max_length=100)
    document_srl: int | None = Field(default=None, ge=0)
    document_id_raw: str = Field(min_length=1, max_length=100)


class PostCandidate(MetadataModel):
    site_id: Literal["fmkorea"] = "fmkorea"
    board_id: str | None = Field(default=None, max_length=100)
    document_srl: int | None = Field(default=None, ge=0)
    document_id_raw: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=4096)
    candidate_title: str | None = Field(default=None, max_length=1000)
    candidate_created_at: datetime | None = None


class SearchPage(MetadataModel):
    board_id: str | None = Field(default=None, max_length=100)
    page: int = Field(ge=1)
    candidates: list[PostCandidate] = Field(default_factory=list)
    has_next: bool = False


class IntegratedSearchPage(MetadataModel):
    keyword: str = Field(min_length=1, max_length=500)
    page: int = Field(ge=1)
    candidates: list[PostCandidate] = Field(default_factory=list)
    board_ids: list[str] = Field(default_factory=list, max_length=10_000)
    has_next: bool = False


BoardSearchPage = SearchPage
