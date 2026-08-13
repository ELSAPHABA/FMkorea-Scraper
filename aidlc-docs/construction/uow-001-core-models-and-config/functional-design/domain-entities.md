# Domain Entities - UOW-001 Core Models And Config

## Entity Overview

UOW-001 defines shared contracts for the FMKorea scraper. These entities describe Pydantic model contracts, validation boundaries, and port-facing data shapes. Network behavior, HTML parsing selectors, storage implementation, CLI prompts, container entrypoint behavior, and MCP wrappers are designed in later UOWs.

## Base Model Policy

All domain models use Pydantic v2.

Common model policy:

- `extra="forbid"` for public input, config, and persisted result models.
- `metadata: dict[str, Any]` is the only generic extension point.
- `model_dump(mode="json")` is the JSONL/checkpoint/report serialization boundary.
- Importing the package must not trigger file I/O, network I/O, environment loading, or terminal prompts.

## Enumerations

### JobType

Supported values:

- `direct_post`
- `board_list`
- `board_search`
- `integrated_search`
- `deep_search`
- `no_keyword_range`
- `realtime_keyword`
- `realtime_all`
- `parser_failure_retry`

### ContentBlockType

Supported values:

- `text`
- `image`
- `fmk_video`
- `youtube`
- `x`
- `link`
- `attachment`
- `unknown_embed`

### CommentMode

Supported values:

- `none`
- `all`
- `best_only`

### MediaMode

Supported values:

- `url_only`
- `download`

### StorageMode

Supported values:

- `local`
- `s3_compatible`

### CheckpointMode

Supported values:

- `local`
- `postgres`

### CheckpointStatus

Supported values:

- `running`
- `stopped`
- `completed`

### StopReason

Supported values:

- `captcha`
- `blocked`
- `manual_stop`
- `error`
- `timeout`
- `lease_expired`

### ResponseKind

Supported values:

- `ok`
- `captcha`
- `blocked`
- `not_found`
- `login_required`
- `rate_limited`
- `server_error`
- `network_error`

## Configuration Entities

### JobConfig

Represents one scrape job.

Fields:

- `job_id: str`
- `job_type: JobType`
- `site_id: Literal["fmkorea"]`
- `source: JobSource`
- `scrape_options: ScrapeOptions`
- `worker_config: WorkerConfig`
- `storage_config: StorageConfig`
- `created_at: datetime`
- `metadata: dict[str, Any]`

Relationships:

- owns exactly one `JobSource`
- owns one `ScrapeOptions`
- owns one `WorkerConfig`
- owns one `StorageConfig`
- does not persist HTTP runtime inputs such as User-Agent file path, proxy, or timeout; adapters map those inputs to `HttpRuntimeConfig` at execution time
- drops legacy `runtime_config` when loading older checkpoint payloads

### JobSource

Discriminated union for collection entrypoints.

Variants:

- `DirectPostSource`
- `BoardListSource`
- `BoardSearchSource`
- `IntegratedSearchSource`
- `DeepSearchSource`
- `NoKeywordRangeSource`
- `RealtimeKeywordSource`
- `RealtimeAllSource`
- `ParserFailureRetrySource`

### DirectPostSource

Fields:

- `type: Literal["direct_post"]`
- `urls: list[str]`
- `metadata: dict[str, Any]`

### BoardListSource

Fields:

- `type: Literal["board_list"]`
- `board_id: str`
- `category_id: str | None`
- `page_start: int`
- `page_end: int | None`
- `range_filter: RangeFilter | None`
- `metadata: dict[str, Any]`

### BoardSearchSource

Fields:

- `type: Literal["board_search"]`
- `board_id: str`
- `keyword: str`
- `search_target: str`
- `category_id: str | None`
- `page_start: int`
- `page_end: int | None`
- `range_filter: RangeFilter | None`
- `metadata: dict[str, Any]`

### IntegratedSearchSource

Fields:

- `type: Literal["integrated_search"]`
- `keyword: str`
- `search_target: str`
- `page_start: int`
- `page_end: int | None`
- `range_filter: RangeFilter | None`
- `metadata: dict[str, Any]`

### DeepSearchSource

Fields:

- `type: Literal["deep_search"]`
- `keyword: str`
- `seed_search_target: str`
- `seed_page_limit: int`
- `board_ids: list[str] | None`
- `range_filter: RangeFilter`
- `metadata: dict[str, Any]`

### NoKeywordRangeSource

Fields:

- `type: Literal["no_keyword_range"]`
- `board_id: str`
- `category_id: str | None`
- `range_filter: RangeFilter`
- `metadata: dict[str, Any]`

### RealtimeKeywordSource

Fields:

- `type: Literal["realtime_keyword"]`
- `scope: Literal["board", "integrated"]`
- `board_id: str | None`
- `keyword: str`
- `poll_interval_seconds: float`
- `termination: RealtimeTermination`
- `metadata: dict[str, Any]`

### RealtimeAllSource

Fields:

- `type: Literal["realtime_all"]`
- `board_id: str`
- `category_id: str | None`
- `poll_interval_seconds: float`
- `termination: RealtimeTermination`
- `metadata: dict[str, Any]`

### ParserFailureRetrySource

Fields:

- `type: Literal["parser_failure_retry"]`
- `failure_input: FailureInput`
- `skip_existing_success: bool`
- `metadata: dict[str, Any]`

### ScrapeOptions

Controls optional scrape behavior.

Fields:

- `comment_mode: CommentMode`
- `media_mode: MediaMode`
- `include_attachments: bool`
- `request_interval_seconds: float`
- `max_post_retries: int`
- `max_comment_pages: int | None`
- `max_content_blocks: int | None`
- `max_comments: int | None`
- `metadata: dict[str, Any]`

Parser guardrail values are persisted here, not only in adapter-local parser settings, so checkpoint resume and parser-failure retry can rebuild the same detail parser behavior.

### WorkerConfig

Controls worker execution.

Fields:

- `post_worker_count: int`
- `media_worker_count: int`
- `queue_max_size: int | None`
- `metadata: dict[str, Any]`

### StorageConfig

Defines storage mode, not concrete storage implementation.

Fields:

- `output_mode: StorageMode`
- `checkpoint_mode: CheckpointMode`
- `base_output_path: str | None`
- `s3: S3StorageConfig | None`
- `postgres: PostgresCheckpointConfig | None`
- `metadata: dict[str, Any]`

## Request And Search Entities

### BoardSearchRequest

Fields:

- `board_id: str`
- `keyword: str | None`
- `search_target: str | None`
- `category_id: str | None`
- `page: int`
- `metadata: dict[str, Any]`

### IntegratedSearchRequest

Fields:

- `keyword: str`
- `search_target: str`
- `page: int`
- `metadata: dict[str, Any]`

### PostRequest

Fields:

- `url: str`
- `board_id: str | None`
- `document_srl: int | None`
- `document_id_raw: str | None`
- `scrape_options: ScrapeOptions`
- `metadata: dict[str, Any]`

### CommentRequest

Fields:

- `url: str`
- `board_id: str | None`
- `document_srl: int | None`
- `comment_mode: CommentMode`
- `metadata: dict[str, Any]`

### ResumeRequest

Fields:

- `job_id: str | None`
- `metadata: dict[str, Any]`

### PostCandidate

Fields:

- `site_id: Literal["fmkorea"]`
- `board_id: str | None`
- `document_srl: int | None`
- `document_id_raw: str`
- `url: str`
- `candidate_title: str | None`
- `candidate_created_at: datetime | None`
- `metadata: dict[str, Any]`

Rule:

- Candidate metadata is only for filtering, dedupe, and diagnostics. Final persisted metadata is parsed again from the detail page.

## Result Entities

### PostResult

JSONL top-level post result.

Fields:

- `schema_version: Literal["fmkorea.post.v1"]`
- `scraped_at: datetime`
- `site_id: Literal["fmkorea"]`
- `board_id: str | None`
- `board_name: str | None`
- `document_srl: int | None`
- `document_id_raw: str`
- `canonical_url: str`
- `category: CategoryInfo | None`
- `title: str`
- `author: AuthorInfo`
- `created_at: datetime | None`
- `created_at_raw: str | None`
- `views: int | None`
- `reactions: ReactionInfo`
- `comment_count: int | None`
- `content: BodyContent`
- `attachments: list[Attachment]`
- `media: list[MediaItem]`
- `comments: list[Comment]`
- `metadata: dict[str, Any]`

Excluded fields:

- `is_repost`
- `repost`

### BodyContent

Fields:

- `text: str`
- `blocks: list[ContentBlock]`
- `metadata: dict[str, Any]`

### AuthorInfo

Fields:

- `nickname: str | None`
- `member_srl: str | None`
- `level: str | None`
- `profile_url: str | None`
- `metadata: dict[str, Any]`

### CategoryInfo

Fields:

- `category_id: str | None`
- `name: str | None`
- `url: str | None`
- `metadata: dict[str, Any]`

### ReactionInfo

Fields:

- `up_count: int`
- `down_count: int`
- `score: int`
- `metadata: dict[str, Any]`

## Content Entities

### ContentBlock

Discriminated union by `type`.

Common fields:

- `type: ContentBlockType`
- `order: int`
- `metadata: dict[str, Any]`

Variants:

- `TextBlock`
- `ImageBlock`
- `FmkVideoBlock`
- `YouTubeBlock`
- `XBlock`
- `LinkBlock`
- `AttachmentBlock`
- `UnknownEmbedBlock`

### TextBlock

Fields:

- `type: Literal["text"]`
- `order: int`
- `text: str`
- `metadata: dict[str, Any]`

### ImageBlock

Fields:

- `type: Literal["image"]`
- `order: int`
- `url: str`
- `original_url: str | None`
- `alt: str | None`
- `file_path: str | None`
- `object_key: str | None`
- `metadata: dict[str, Any]`

### FmkVideoBlock

Fields:

- `type: Literal["fmk_video"]`
- `order: int`
- `video_url: str | None`
- `poster_url: str | None`
- `description: str | None`
- `duration: str | None`
- `file_path: str | None`
- `object_key: str | None`
- `metadata: dict[str, Any]`

### YouTubeBlock

Fields:

- `type: Literal["youtube"]`
- `order: int`
- `url: str`
- `video_id: str | None`
- `embed_url: str | None`
- `title: str | None`
- `metadata: dict[str, Any]`

### XBlock

Fields:

- `type: Literal["x"]`
- `order: int`
- `url: str`
- `username: str | None`
- `status_id: str | None`
- `text: str | None`
- `metadata: dict[str, Any]`

### LinkBlock

Fields:

- `type: Literal["link"]`
- `order: int`
- `url: str`
- `text: str | None`
- `title: str | None`
- `metadata: dict[str, Any]`

### AttachmentBlock

Fields:

- `type: Literal["attachment"]`
- `order: int`
- `attachment: Attachment`
- `metadata: dict[str, Any]`

### UnknownEmbedBlock

Fields:

- `type: Literal["unknown_embed"]`
- `order: int`
- `provider: str | None`
- `url: str | None`
- `safe_text: str | None`
- `metadata: dict[str, Any]`

### Attachment

Fields:

- `file_name: str | None`
- `url: str`
- `size_text: str | None`
- `file_path: str | None`
- `object_key: str | None`
- `metadata: dict[str, Any]`

### MediaItem

Top-level compatibility and storage summary item derived from content blocks.

Fields:

- `media_id: str | None`
- `media_type: ContentBlockType`
- `source_block_order: int`
- `url: str`
- `file_path: str | None`
- `object_key: str | None`
- `description: str | None`
- `metadata: dict[str, Any]`

## Comment Entities

### Comment

Represents normal comments, replies, and BEST comments in one flat list.

Fields:

- `comment_srl: int | None`
- `comment_id_raw: str | None`
- `source_dom_id: str | None`
- `source_order: int`
- `parent_comment_srl: int | None`
- `parent_comment_id_raw: str | None`
- `depth: int | None`
- `is_best: bool`
- `badges: list[str]`
- `author: AuthorInfo`
- `created_at: datetime | None`
- `created_at_raw: str | None`
- `content: str`
- `reactions: ReactionInfo`
- `permalink: str | None`
- `metadata: dict[str, Any]`

Rules:

- BEST comments remain in `comments`.
- No separate `best_comments` array is used.
- `badges` preserves source UI labels such as `BEST`.

## Runtime State Entities

### Checkpoint

Fields:

- `schema_version: Literal["fmkorea.checkpoint.v1"]`
- `job_id: str`
- `status: CheckpointStatus`
- `reason: StopReason | None`
- `job_config: JobConfig`
- `collector_cursor: CollectorCursor | None`
- `completed_keys: list[PostKey]`
- `queued_links: list[PostCandidate] | None`
- `updated_at: datetime`
- `metadata: dict[str, Any]`

### CollectorCursor

Fields:

- `source_type: JobType`
- `page: int | None`
- `board_id: str | None`
- `last_document_srl: int | None`
- `last_url: str | None`
- `metadata: dict[str, Any]`

### PostKey

Fields:

- `site_id: Literal["fmkorea"]`
- `board_id: str | None`
- `document_srl: int | None`
- `document_id_raw: str`

## Failure And Report Entities

### FailureRecord

Fields:

- `schema_version: Literal["fmkorea.failure.v1"]`
- `job_id: str`
- `stage: str`
- `reason: str`
- `retryable: bool`
- `url: str | None`
- `post_key: PostKey | None`
- `safe_message: str`
- `details: dict[str, Any]`
- `created_at: datetime`

### FailureInput

Fields:

- `failure_path: str`
- `job_id: str | None`
- `stage_allowlist: list[str]`
- `metadata: dict[str, Any]`

### JobReport

Fields:

- `schema_version: Literal["fmkorea.job_report.v1"]`
- `job_id: str`
- `status: str`
- `started_at: datetime`
- `finished_at: datetime | None`
- `collected_count: int`
- `stored_count: int`
- `failure_count: int`
- `output_refs: list[StoredObjectRef]`
- `metadata: dict[str, Any]`

### ErrorResult

Fields:

- `code: str`
- `message: str`
- `details: dict[str, Any]`
- `retryable: bool`
- `safe_to_log: bool`

### StoredObjectRef

Fields:

- `storage_mode: StorageMode`
- `path: str | None`
- `bucket: str | None`
- `object_key: str | None`
- `metadata: dict[str, Any]`
