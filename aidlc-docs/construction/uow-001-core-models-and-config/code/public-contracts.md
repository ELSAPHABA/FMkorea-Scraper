# Public Contracts - UOW-001 Core Models And Config

## Scope

UOW-001 defines the import-safe core contracts used by later scraper units. It does not perform HTTP requests, parse HTML, write output files, run workers, expose CLI commands, start containers, or open MCP tools.

## Package Contract

- Package name: `fmkorea-scraper`
- Import package: `fmkorea_scraper`
- Runtime dependency: `pydantic>=2,<3`
- Python version: `>=3.11`
- Public import surface: `JobConfig`, `PostResult`, `Comment`, `Checkpoint`, search/fetch/run/resume/retry async entrypoints

Console script entrypoints are intentionally deferred until the CLI unit creates `adapters.cli`.

## Schema Versions

| Model | Schema Version | Purpose |
|---|---|---|
| `PostResult` | `fmkorea.post.v1` | One scraped post, including content blocks, media, attachments, and flat comments |
| `Checkpoint` | `fmkorea.checkpoint.v1` | Resume state for an interrupted or stopped job |
| `FailureRecord` | `fmkorea.failure.v1` | Safe parser/runtime failure record for retry units |
| `JobReport` | `fmkorea.job_report.v1` | Job-level completion and output summary |

Committed schema hashes live in `tests/snapshots/schema_versions.json`.

## Model Rules

All public models inherit from `StrictBaseModel` and reject unknown fields with `extra="forbid"`.

Models that expose `metadata` inherit from `MetadataModel`. Metadata must be JSON-compatible, finite, bounded to depth 8, and bounded to 8192 serialized UTF-8 bytes.

## Job And Source Contracts

`JobConfig.job_type` must match `source.type`.

Supported source types:

- `direct_post`
- `board_list`
- `board_search`
- `integrated_search`
- `deep_search`
- `no_keyword_range`
- `realtime_keyword`
- `realtime_all`
- `parser_failure_retry`

Validation rules:

- `RangeFilter.date_from <= date_to`
- `RangeFilter.min_document_srl <= max_document_srl`
- `deep_search` and `no_keyword_range` require at least one date or document-number bound
- realtime sources require exactly one stop condition: `duration_seconds` or `end_at`
- board/integrated source page ranges require `page_start <= page_end`
- direct post URLs must point to `fmkorea.com`

## Runtime And Storage Config

`JobConfig` does not persist HTTP runtime inputs such as User-Agent file path, rotation period, proxy, or timeout. CLI, container, MCP, and library adapters map those execution inputs to `HttpRuntimeConfig` when they open a client.

Older checkpoint payloads that contain `job_config.runtime_config` are accepted by dropping that legacy field during model loading. New checkpoint writes must not include it.

`StorageConfig` supports local output and S3-compatible output contracts. If `output_mode=s3_compatible`, `s3` config is required. If `checkpoint_mode=postgres`, `postgres` config is required.

## Post Content Contract

`PostResult` stores post identity, board/category metadata, title, author, date, views, reactions, comment count, ordered body content, media, attachments, and flat comments.

FMKorea source JSON does not contain `is_repost` or `repost`. Those fields are reserved for other community-specific schemas or later common normalization output.

`BodyContent.blocks` is ordered by unique `order` values and supports `text`, `image`, `fmk_video`, `youtube`, `x`, `link`, `attachment`, and `unknown_embed`.

## Comment Contract

Comments are stored as a flat list under `PostResult.comments`. BEST comments use `is_best=true`; `badges` is normalized to include `BEST`.

`ReactionInfo.score` must equal `up_count - down_count`. If omitted, it is filled automatically.

## Checkpoint Contract

`Checkpoint` records the original `job_config`, cursor state, completed keys, queued links, status, reason, and update time. If `status=stopped`, `reason` is required. If status is not stopped, `reason` must be null.

## Failure And Error Contracts

`FailureRecord` stores retryable parser/runtime failures with safe details only.

`ErrorMapper` converts exceptions into `ErrorResult`. `SecretRedactor` keeps only allowlisted detail keys and removes or redacts likely secrets such as password, token, cookie, credential, and proxy values.

## Port Protocols

UOW-001 declares runtime-checkable structural protocols for later adapters:

- `HttpPort`
- `OutputStorePort`
- `MediaStorePort`
- `FailureStorePort`
- `CheckpointStorePort`
- `ClockPort`
- `LoggerPort`

## Public API Placeholders

The public async functions are stable signatures only. Until later units implement runtime behavior, direct calls without an injected runner/service raise `UnsupportedSourceError`.
