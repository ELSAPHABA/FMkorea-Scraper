# NFR Design Patterns - UOW-004 Post Detail And Content Parsing

## Scope

This document turns the UOW-004 NFR requirements into implementation patterns.

UOW-004 owns FMKorea detail HTML parsing, final metadata extraction, ordered body content parsing, media and attachment metadata extraction, comment/reply parsing, BEST comment fields, safe parser warnings, and backward-compatible model extensions.

It does not own list/search traversal, worker queue lifecycle, checkpoint persistence, JSONL/Garage/PostgreSQL storage, media file downloads, CLI prompts, container entrypoints, MCP tools, or cloud infrastructure.

## Confirmed Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Use a small `src/fmkorea_scraper/parse/` package with `models.py`, `metadata.py`, `content.py`, `media.py`, `comments.py`, `warnings.py`, and `service.py`. |
| Q2 | A | Public parsing API accepts `PostCandidate` or `PostRequest` and returns `PostResult`; parser internals are not extra public contracts. |
| Q3 | A | Use caller-injected UOW-002 `HttpClient`/`HttpPort`; UOW-004 does not create or close HTTP clients. |
| Q4 | A | `MetadataParser` parses detail page values from `#bd_capture`; candidate metadata is fallback only. |
| Q5 | A | `ContentParser` finds scoped `.xe_content` once and emits ordered content blocks by linear DOM traversal. |
| Q6 | A | Split `MediaBlockParser` and `AttachmentParser`; content parser owns order, media parser owns URL normalization and per-post dedupe. |
| Q7 | A | `CommentParser` emits one flat comment list with BEST fields, reactions, source order, and safe parent hints. |
| Q8 | A | Use safe `ParseWarning` values stored under `PostResult.metadata["parse_warnings"]`. |
| Q9 | A | Extend UOW-001 models only with optional typed media/attachment fields; uncertain values remain in metadata. |
| Q10 | A | Test DOM selectors with fixtures; test URL, dedupe, comment ID, reaction score, validation, and redaction policies with pytest/Hypothesis. |

No follow-up question is required. The decisions are internally consistent and preserve the baseline scraper structure where it fits FMKorea.

## Package Separation Pattern

UOW-004 uses one package:

- `src/fmkorea_scraper/parse/models.py`
- `src/fmkorea_scraper/parse/metadata.py`
- `src/fmkorea_scraper/parse/content.py`
- `src/fmkorea_scraper/parse/media.py`
- `src/fmkorea_scraper/parse/comments.py`
- `src/fmkorea_scraper/parse/warnings.py`
- `src/fmkorea_scraper/parse/service.py`

| Module | Owns |
|---|---|
| `models.py` | Parser-only value objects and parse options. |
| `metadata.py` | Detail identity, title, author, date, counters, category, and canonical URL parsing. |
| `content.py` | Scoped content container lookup, DOM-order traversal, text/link block creation, and content text extraction. |
| `media.py` | Image, FMKorea video, YouTube, X/Twitter, attachment parsing, URL normalization, and per-post media dedupe keys. |
| `comments.py` | Comment/reply/BEST parsing, comment ID extraction, reaction parsing, source order, and parent hints. |
| `warnings.py` | Safe `ParseWarning` values, warning collection, and redaction helpers. |
| `service.py` | HTTP handoff, mode orchestration, parser composition, and final `PostResult` assembly. |

The package must not import storage, CLI, container, MCP, checkpoint, or queue adapters.

## Service Output Pattern

The primary API returns UOW-001 `PostResult`.

Inputs:

- `PostCandidate`
- `PostRequest`

Outputs:

- `PostResult`

Intermediate parsed values may exist inside package modules for tests, but they should not become broad public contracts unless code generation needs a small value object.

UOW-004 must not return JSONL strings or write output files.

## HTTP Boundary Pattern

`PostDetailService` receives a caller-managed UOW-002 HTTP client/port.

Rules:

- do not create `httpx.AsyncClient`
- do not close the injected HTTP client
- do not read `.env`, user-agent files, proxy config, or cookie files
- let UOW-002 classify CAPTCHA/block/login-required/unavailable responses
- fetch additional comment pages sequentially through the same injected HTTP path

This keeps runtime policy in UOW-002 and parsing logic in UOW-004.

## Metadata Parser Pattern

`MetadataParser` starts from `#bd_capture`.

Parsed detail values:

- `document_srl`
- `document_id_raw`
- `canonical_url`
- `board_id`
- `board_name`
- `category`
- `title`
- `author`
- `created_at`
- `created_at_raw`
- `views`
- `reactions`
- `comment_count`

Candidate metadata from UOW-003 is fallback only. A parsed detail value must not be overwritten by a candidate hint.

Missing required identity fields raise post-level parser failure:

- `document_srl` or `document_id_raw`
- canonical/detail URL
- title

## Content Traversal Pattern

`ContentParser` locates the scoped content container once:

1. `#bd_capture .rd_body article > .xe_content`
2. `#bd_capture .rd_body .xe_content`

Then it traverses child nodes in DOM order and emits content blocks:

- `text`
- `image`
- `fmk_video`
- `youtube`
- `x`
- `link`
- `attachment`
- `unknown_embed`

Each block gets a unique `order`.

`content.text` is derived from meaningful text/link blocks and excludes player UI, attachment tables, counters, ads, and empty nodes.

## Media And Attachment Pattern

`AttachmentParser` builds a lookup from:

- `.rd_file a[data-href]`

`MediaBlockParser` handles:

- image URL priority: parent `a.highslide[href]`, then `img[src]`
- FMKorea video: one logical `fmk_video` block per wrapper/video/source set
- YouTube: static watch, short, and existing embed URLs
- X/Twitter: static status links and existing embed URLs
- attachment block creation from attachment lookup

Per-post media dedupe uses available keys:

- block type
- normalized URL
- `file_srl`

Storage-wide dedupe is deferred to later storage units.

## Comment Parser Pattern

`CommentParser` parses:

- `.fdb_lst_ul > li`

It emits one flat `Comment` list.

Each comment should include when available:

- numeric comment ID
- raw DOM ID
- source order
- depth
- parent comment ID
- author
- date
- content
- up/down reactions
- score
- `is_best`
- `badges`

BEST comments are not duplicated into a separate array. They remain in the flat list with `is_best=true` and `badges=["BEST"]`.

## Parser Warning Pattern

Recoverable problems use `ParseWarning`.

Allowed warning fields:

- `code`
- `stage`
- `selector`
- `order`
- `reason`
- safe identifiers such as `board_id` and `document_srl`

Disallowed warning fields:

- raw HTML
- raw response body
- full post body text
- full comment text
- cookies
- proxy credentials
- raw `.env` contents
- raw cookie content

Warnings are stored under:

- `PostResult.metadata["parse_warnings"]`

## Model Extension Pattern

UOW-004 may extend UOW-001 models with typed optional fields for documented values.

Allowed examples:

- image `file_srl`, `width`, `height`, `download_url`, `download`
- video `file_srl`, `download_url`, `name`, `upload_date`, `width`, `height`
- YouTube `start_seconds`
- X/Twitter `tweet_id`, `embed_url`
- attachment `file_srl`, `sid`, `mid`, download text

Existing required fields and meanings must remain compatible.

Raw HTML fields must not be added.

## Test Harness Pattern

Default tests are deterministic and offline.

Required fixture/example tests:

- detail metadata
- text and image content
- FMKorea video
- YouTube
- X/Twitter
- attachments
- normal comments and replies
- BEST comments
- optional field absence
- malformed optional block/comment warning
- required field failure

Required PBT targets:

- URL normalization
- content block order uniqueness
- media dedupe idempotence
- comment ID extraction
- reaction score calculation
- required-field validation
- warning payload redaction

Optional live smoke tests run only when:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Live smoke must not persist JSONL or download media.

## Compliance Summary

### Security

- Safe warnings and logs exclude raw HTML, secrets, full body/comment text, and user cookie contents.
- Importing UOW-004 has no network, file, env, prompt, storage, queue, or HTTP-client side effects.
- CAPTCHA/block classifications propagate upward.

### Resiliency

- Required identity failures become post-level parser failures.
- Optional metadata/content/media/attachment/comment failures become safe warnings.
- Additional comment pages are sequential and bounded.

### PBT

- PBT targets pure helper and policy logic.
- DOM parsing uses small deterministic fixtures.
