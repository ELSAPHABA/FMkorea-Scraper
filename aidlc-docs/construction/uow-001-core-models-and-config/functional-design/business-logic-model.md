# Business Logic Model - UOW-001 Core Models And Config

## Purpose

UOW-001 fixes the shared contracts used by every later FMKorea scraper unit. It does not implement HTTP requests, HTML parsing, file writes, terminal prompts, containers, MCP tools, or AWS resources.

This unit owns:

- Pydantic v2 model contracts
- source/result/checkpoint/failure/report schema versions
- Job config validation shape
- public API request/result models
- typed core exceptions
- minimal external I/O port protocols

## Design Decisions

| Area | Decision |
|---|---|
| Model library | Pydantic v2 |
| Extra fields | Input/config/result models use `extra="forbid"` |
| Extension point | Explicit `metadata: dict[str, Any]` only |
| Job config | `JobConfig.job_type` plus `source` discriminated union |
| Content blocks | `type` based discriminated union |
| Identifiers | Raw source IDs as `str`, numeric comparison fields as `int | None` |
| Comments | Flat `comments` list for normal, reply, and BEST comments |
| BEST comments | `is_best`, `badges`, and `reactions` fields on `Comment` |
| Error handling | Core raises typed exceptions; adapters return `ErrorResult` |
| Ports | Minimal external I/O protocols only |

## Public API Logic

Public APIs receive and return Pydantic models. They may raise typed core exceptions. Adapters convert those exceptions into `ErrorResult`.

| API | Input Model | Output Model |
|---|---|---|
| `search_board` | `BoardSearchRequest` | `SearchPage` |
| `search_integrated` | `IntegratedSearchRequest` | `IntegratedSearchPage` |
| `fetch_post` | `PostRequest` | `PostResult` |
| `fetch_comments` | `CommentRequest` | `list[Comment]` |
| `run_job` | `JobConfig` | `JobReport` |
| `resume_job` | `ResumeRequest` | `JobReport` |
| `retry_parser_failures` | `RetryRequest` | `RetryReport` |

Importing the package must be side-effect free. Runtime side effects start only after an API or adapter entrypoint is invoked.

## Job Config Validation Flow

1. Adapter or library caller provides a raw mapping or a typed request.
2. `JobConfigValidator` validates common fields.
3. The `source.type` discriminator selects one source model.
4. `job_type` and `source.type` must match.
5. Source-specific required fields are validated.
6. Range and realtime termination conflicts are rejected.
7. A typed `JobConfig` is returned to the caller.

Validation failures raise typed validation exceptions in core code.

## Job Source Logic

| Source Type | Required Data | Key Validation |
|---|---|---|
| `direct_post` | one or more post URLs | non-empty URL list |
| `board_list` | board ID, start page | page starts at 1 |
| `board_search` | board ID, keyword, search target | keyword is non-empty |
| `integrated_search` | keyword, search target | keyword is non-empty |
| `deep_search` | keyword, seed page limit, range filter | date or document range required |
| `no_keyword_range` | board ID, range filter | keyword not required |
| `realtime_keyword` | scope, keyword, poll interval, termination | exactly one termination condition |
| `realtime_all` | board ID, poll interval, termination | exactly one termination condition |
| `parser_failure_retry` | failure input | retry selection details handled in UOW-009 |

## Result Serialization Logic

`PostResult` is the source JSONL unit. One post equals one JSON object line.

Serialization rule:

```python
post_result.model_dump(mode="json")
```

The source JSONL preserves FMKorea-specific fields. It does not include generic fields that are not native to this source, such as repost fields from another scraper family.

Common schema normalization for Polars happens later and must not mutate the source JSONL.

## Content Block Logic

`BodyContent.blocks` preserves original body order.

Every block has:

- `type`
- `order`
- `metadata`

Variant payload is stored only on the matching block model.

Examples:

- `TextBlock` stores `text`.
- `ImageBlock` stores image URLs and optional saved object references.
- `FmkVideoBlock` stores video URL, poster URL, nullable description, and optional saved object references.
- `YouTubeBlock` stores URL/embed/video ID metadata.
- `XBlock` stores URL/status metadata.
- `LinkBlock` stores general links.
- `AttachmentBlock` references an `Attachment`.

Top-level `media` is derived from media-bearing blocks for storage/reporting convenience. It does not replace ordered content blocks.

## Comment Logic

`Comment` represents:

- normal comments
- replies
- BEST comments

BEST comments are not duplicated into a separate array.

Recommended persisted shape:

```json
{
  "comment_srl": 10197967615,
  "source_dom_id": "comment_10197967615_",
  "source_order": 0,
  "parent_comment_srl": null,
  "depth": 0,
  "is_best": true,
  "badges": ["BEST"],
  "reactions": {
    "up_count": 375,
    "down_count": 4,
    "score": 371
  }
}
```

The array order records scraper output order only. Analytical ordering must use explicit fields such as `created_at`, `comment_srl`, and `source_order`.

## Identifier Logic

Raw identifiers are preserved as strings where available.

Normalized integer fields are added for sorting, range filtering, and dedupe.

| Source Value | Raw Field | Numeric Field |
|---|---|---|
| post document ID | `document_id_raw` | `document_srl` |
| comment ID | `comment_id_raw` | `comment_srl` |
| parent comment ID | `parent_comment_id_raw` | `parent_comment_srl` |

If conversion fails, the numeric field is `null` and the raw field remains.

## Checkpoint Logic

Checkpoint captures job progress, not exact coroutine state.

Checkpoint may contain:

- full `JobConfig`
- collector cursor
- completed post keys
- queued post candidates snapshot

It does not guarantee restoration of in-flight HTTP requests. Later job runner logic uses completed keys and dedupe to avoid duplicate persisted posts.

## Error Logic

Core exceptions:

- `ValidationError`
- `UnsupportedSourceError`
- `UnavailableContentError`
- `CaptchaDetectedError`
- `BlockedResponseError`
- `NetworkFailureError`
- `ParseFailureError`
- `StorageFailureError`
- `CheckpointFailureError`

Adapter `ErrorResult` fields:

- `code`
- `message`
- `details`
- `retryable`
- `safe_to_log`

Secret-bearing values are never included in adapter-facing error details.

## Port Logic

UOW-001 defines protocols only.

| Port | Purpose | Async |
|---|---|---|
| `HttpPort` | GET/POST/download/classify boundary | Yes |
| `OutputStorePort` | append post JSONL and write reports | Yes |
| `MediaStorePort` | save media bytes or metadata-only records | Yes |
| `FailureStorePort` | write/read failure records | Yes |
| `CheckpointStorePort` | save/load checkpoint | Yes |
| `ClockPort` | provide UTC timestamps and sleeps | Mixed |
| `LoggerPort` | structured safe logging | No |

Concrete implementations are later UOW responsibilities.

## UOW Exclusions

UOW-001 does not implement:

- HTTP retry, proxy, User-Agent, cookie loading
- URL/query builders
- HTML selectors or BeautifulSoup parsing
- worker queues
- JSONL file writing
- S3-compatible storage
- PostgreSQL checkpoint storage
- CLI command parsing or wizard prompts
- container entrypoint
- MCP server/tool registration
- AWS CDK resources
