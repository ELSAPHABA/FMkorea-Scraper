# Business Rules - UOW-001 Core Models And Config

## Model Rules

### BR-001. Pydantic Version

All models in this unit must target Pydantic v2.

Implementation implications:

- Use `BaseModel`.
- Use `ConfigDict(extra="forbid")`.
- Use `model_dump(mode="json")` for JSONL, checkpoint, failure, and report serialization.

### BR-002. Extra Field Policy

Public input, config, and scrape result models must reject unknown fields.

Allowed extension path:

- `metadata: dict[str, Any]`

Unknown top-level fields must not be silently accepted.

### BR-003. Import Side Effects

Importing `fmkorea_scraper` must not:

- start network requests
- read or write files
- prompt terminal input
- create output directories
- load `.env`
- load `user-agents.txt`

Runtime side effects occur only when an API, CLI command, container entrypoint, or MCP tool is invoked.

### BR-004. Schema Version Fields

The following persisted top-level models must include `schema_version`:

- `PostResult`: `fmkorea.post.v1`
- `Checkpoint`: `fmkorea.checkpoint.v1`
- `FailureRecord`: `fmkorea.failure.v1`
- `JobReport`: `fmkorea.job_report.v1`

Nested models do not need independent schema versions unless they become separately persisted artifacts.

## Job Config Rules

### BR-005. Job Type And Source Must Match

`JobConfig.job_type` must match the discriminator of `JobConfig.source`.

Invalid example:

- `job_type="deep_search"` with `source.type="board_search"`

This must fail validation.

### BR-006. Site ID Is Fixed

All source JSONL and job models in this scraper must use:

- `site_id="fmkorea"`

Adapter input must not override this with a different site ID.

### BR-007. Direct Post Source

`direct_post` source must include at least one valid post URL.

Each URL must contain enough information to derive:

- `document_srl`, or
- a raw document identifier that later URL parsing can resolve.

### BR-008. Board List Source

`board_list` source must include:

- `board_id`
- `page_start`

`page_start` must be greater than or equal to 1.

If `page_end` is present, `page_start <= page_end` must hold.

### BR-009. Board Search Source

`board_search` source must include:

- `board_id`
- non-empty `keyword`
- `search_target`
- `page_start`

Candidate metadata from board search is not final persisted post metadata.

### BR-010. Integrated Search Source

`integrated_search` source must include:

- non-empty `keyword`
- `search_target`
- `page_start`

Pagination limits and search result parsing are implemented in UOW-003.

### BR-011. Deep Search Source

`deep_search` source must include:

- non-empty `keyword`
- `seed_page_limit`
- `range_filter`

`range_filter` must include at least one of:

- date range
- document number range

If both are absent, validation must fail.

### BR-012. No-Keyword Range Source

`no_keyword_range` source must include:

- `board_id`
- `range_filter`

It must not require a keyword.

### BR-013. Realtime Source

Realtime sources must include exactly one termination condition:

- `duration_seconds`
- `end_at`

If both are present or both are missing, validation must fail.

`realtime_keyword` must include a non-empty keyword.

### BR-014. Range Validation

If both `date_from` and `date_to` exist, `date_from <= date_to` must hold.

If both `min_document_srl` and `max_document_srl` exist, `min_document_srl <= max_document_srl` must hold.

## Result Schema Rules

### BR-015. PostResult Required Fields

`PostResult` must include:

- `schema_version`
- `scraped_at`
- `site_id`
- `board_id`
- `document_srl`
- `document_id_raw`
- `canonical_url`
- `title`
- `author`
- `created_at`
- `created_at_raw`
- `views`
- `reactions`
- `comment_count`
- `content`
- `attachments`
- `media`
- `comments`
- `metadata`

### BR-016. No Repost Fields

FMKorea source JSONL must not include:

- `is_repost`
- `repost`

If common-schema normalization later needs those columns, the normalizer may synthesize null/default values outside the source JSONL.

### BR-017. Candidate Metadata Is Not Final Metadata

List/search pages may provide candidate title, category, date, views, reactions, and comment count.

These values may be stored in `PostCandidate.metadata` only for:

- filtering
- dedupe
- diagnostics
- range pruning

Final JSONL post metadata must be parsed from the detail page.

### BR-018. Identifier Preservation

Raw source identifiers must be preserved as strings when available.

Numeric comparison fields must be stored as `int | None`.

Examples:

- `document_id_raw: str`
- `document_srl: int | None`
- `comment_id_raw: str | None`
- `comment_srl: int | None`

If integer conversion fails, the raw value remains and the normalized integer field is `null`.

## Content Rules

### BR-019. Body Text

`BodyContent.text` stores normalized plain text for search and Polars processing.

It must not include:

- player UI text
- attachment table boilerplate
- copy/share UI labels
- hidden lazy-load markers
- ad text

### BR-020. Content Order

`BodyContent.blocks` must preserve source body order by `order`.

Each block must have a unique non-negative `order` within one post.

### BR-021. Content Block Discriminator

Each content block must have a `type` matching one supported content block variant.

Unsupported embeds may use `unknown_embed`.

`unknown_embed.metadata` must not store full raw HTML unless a later parser design explicitly allows it.

### BR-022. Media Summary

Top-level `media` is a compatibility/storage summary derived from media-bearing content blocks.

It must not replace `content.blocks` as the source order representation.

### BR-023. External Embed Download Policy

YouTube and X/Twitter embeds are represented as metadata/link blocks.

Their external media files are not downloaded by this scraper unless a later UOW explicitly changes that policy.

### BR-024. FMKorea Video Description

`FmkVideoBlock.description` and `MediaItem.description` are nullable.

If the source has no video description, store `null`.

## Comment Rules

### BR-025. Flat Comment List

Normal comments, replies, and BEST comments use the same `Comment` model and are stored in `PostResult.comments`.

The source JSONL must not create a separate `best_comments` array.

### BR-026. BEST Comment Fields

BEST comments must be represented by:

- `is_best=true`
- `badges` containing `"BEST"` when the source UI exposes that label

Other future source UI labels may also be preserved in `badges`.

### BR-027. Comment Reactions

Comment reactions use `ReactionInfo`.

Rules:

- empty up/down values normalize to `0`
- `score = up_count - down_count`
- parser failures for reaction values should preserve safe raw hints in `metadata`

### BR-028. Reply Relationships

Replies should set:

- `depth=1`
- `parent_comment_srl=<parent id>` when available

If the parent cannot be determined:

- `depth=null`
- `parent_comment_srl=null`
- source classes or safe hints may be preserved in `metadata`

### BR-029. Comment Ordering

`source_order` records the order encountered in the source DOM/page.

Analysis code must not rely only on JSON array order. Polars normalization should sort explicitly by available fields such as:

- `created_at`
- `comment_srl`
- `source_order`

### BR-030. BEST-Only Comment Mode

When `comment_mode="best_only"`, returned/stored comments must include only comments with `is_best=true`.

The parser may still inspect all comments internally if needed to detect relationships, but non-BEST comments must not be persisted in that mode.

## Checkpoint Rules

### BR-031. Checkpoint Status

Checkpoint status must be one of:

- `running`
- `stopped`
- `completed`

### BR-032. Stop Reason

When `status="stopped"`, `reason` is required.

When `status!="stopped"`, `reason` must be `null`.

### BR-033. Checkpoint Snapshot Scope

Checkpoint may store:

- job config
- collector cursor
- completed post keys
- queued links snapshot

Checkpoint does not guarantee exact restoration of in-flight requests.

### BR-034. Checkpoint Advance Order

Completed post keys should advance only after the post result is stored successfully.

Storage implementation details are handled in UOW-005 and UOW-006.

## Error Rules

### BR-035. Typed Core Exceptions

Core code may raise typed exceptions for:

- validation failure
- unsupported source
- unavailable content
- CAPTCHA detection
- blocked response
- network failure
- parse failure
- storage failure
- checkpoint failure

### BR-036. Adapter Error Result

Adapters must convert exceptions to `ErrorResult` before returning through CLI, container, or MCP boundaries.

`ErrorResult.message` must be safe for users.

`ErrorResult.details` must not include:

- proxy password
- raw cookie
- token
- full credential file content
- raw private environment data
- internal stack trace

## Port Rules

### BR-037. Port Boundaries

Ports define behavior, not implementation policy.

Required protocol boundaries:

- HTTP
- output store
- media store
- failure store
- checkpoint store
- clock
- logger

Concrete HTTP, local file, S3-compatible, PostgreSQL, and logger behavior belongs to later UOWs.

### BR-038. Async Boundary

Public scrape APIs and I/O ports are async by default.

Pure validation and model conversion functions may remain synchronous.
