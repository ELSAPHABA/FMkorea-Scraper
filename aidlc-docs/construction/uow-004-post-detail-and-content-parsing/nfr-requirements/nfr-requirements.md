# NFR Requirements - UOW-004 Post Detail And Content Parsing

## Scope

This document defines non-functional requirements for `UOW-004 Post Detail And Content Parsing`.

In scope:

- detail HTML fetch handoff through UOW-002
- final detail metadata parsing
- ordered body content parsing
- image, FMKorea video, YouTube, X/Twitter, link, and attachment metadata extraction
- comment and reply parsing
- BEST comment fields
- safe parser warnings
- backward-compatible UOW-001 model extension requirements

Out of scope:

- list/search traversal
- worker queue lifecycle
- checkpoint persistence
- JSONL/storage writes
- media file download
- CLI prompt UX
- container/MCP hosting

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Missing document identity, canonical/detail URL, or title is a post-level parser failure. Optional metadata/content/media/comment failures become safe warnings. |
| Q2 | A | Code generation must include fixtures for detail metadata, text+image, FMKorea video, YouTube, X/Twitter, attachments, normal comments/replies, BEST comments, and malformed optional blocks. |
| Q3 | A | Content parsing finds the scoped container once and traverses child DOM linearly with BeautifulSoup. Browser rendering and repeated global scans are excluded. |
| Q4 | A | Media dedupe is per-post using available logical keys: type, normalized URL, and `file_srl`. Multiple video sources emit one `fmk_video` block. |
| Q5 | A | Initial detail comments are parsed first; discovered comment pages/fragments are fetched sequentially with optional `max_comment_pages`; duplicate comment IDs are stored once. |
| Q6 | A | Individual comment parse failures become safe warnings; CAPTCHA/block/unavailable responses propagate from UOW-002. |
| Q7 | A | Logs and warnings include safe identifiers and parser stage details only. Raw HTML, full body/comment text, cookies, proxy data, and user cookie contents are excluded. |
| Q8 | A | PBT covers pure parsing-policy helpers; BeautifulSoup selector correctness remains fixture/example tested. |
| Q9 | A | Live smoke is optional and env-gated by `FMKOREA_LIVE_SMOKE_ENABLED=true`. It must not persist output or download media. |
| Q10 | A | No new runtime dependency is added. Use BeautifulSoup, `urllib.parse`, `re`, and injected UOW-002 HTTP. |
| Q11 | A | Existing UOW-001 field meanings and requiredness stay compatible. New media/attachment fields are typed optional fields; raw HTML fields are not added. |
| Q12 | A | Normal output preserves all valid blocks/comments; optional `max_content_blocks` and `max_comments` guardrails may stop oversized pages safely. |

No follow-up question is required. The answers are internally consistent.

## Performance Requirements

### NFR-UOW004-PERF-001. Linear Content Traversal

The content parser must locate the scoped content container once:

1. `#bd_capture .rd_body article > .xe_content`
2. `#bd_capture .rd_body .xe_content`

After the container is found, the parser must traverse child nodes in DOM order and avoid repeated global document scans for each block type.

### NFR-UOW004-PERF-002. No Browser Rendering

UOW-004 must not depend on Playwright, Selenium, or browser rendering for default parsing.

Static HTML parsing with BeautifulSoup is the default implementation boundary.

### NFR-UOW004-PERF-003. Per-Post Media Dedupe

Media dedupe is bounded to one post parse.

Logical media keys may use:

- block type
- normalized URL
- `file_srl`

UOW-004 must not perform storage-wide or cross-run media dedupe.

### NFR-UOW004-PERF-004. Optional Output Size Guardrails

UOW-004 may support optional guardrails:

- `max_content_blocks`
- `max_comments`
- `max_comment_pages`

If a guardrail is exceeded, the parser must produce a safe bounded-resource failure or warning rather than silently discarding data.

## Reliability And Resiliency Requirements

### NFR-UOW004-REL-001. Required Field Failure Boundary

Post-level parser failure is required when any of these cannot be resolved:

- `document_srl` or `document_id_raw`
- canonical/detail URL
- title

These failures are parser-stage failures and are eligible for later UOW-009 retry.

### NFR-UOW004-REL-002. Optional Parse Failure Isolation

The parser must continue when recoverable optional fields fail.

Recoverable examples:

- author detail missing
- category missing
- counter text malformed
- one content block malformed
- one media item malformed
- one attachment malformed
- one comment item malformed
- ambiguous optional date

Each recoverable issue must become a safe parser warning.

### NFR-UOW004-REL-003. Comment Page Bound

Additional comment page or fragment fetching must be sequential through injected UOW-002 HTTP.

The parser must dedupe comments by numeric comment ID when available.

When `max_comment_pages` is configured and exceeded, UOW-004 must stop safely and record a warning or bounded-resource failure.

### NFR-UOW004-REL-004. CAPTCHA And Block Propagation

CAPTCHA, block, unavailable, and hard HTTP classification errors from UOW-002 must not be converted into successful empty content or comments.

They propagate to later worker/checkpoint units.

### NFR-UOW004-REL-005. Candidate Metadata Fallback

UOW-003 candidate metadata is fallback only.

Detail page values win whenever present.

The parser must not overwrite a parsed detail value with a candidate hint.

## Security Requirements

### NFR-UOW004-SEC-001. Safe Parser Logging

Logs and parser warnings may include:

- `site_id`
- `board_id`
- `document_srl`
- safe stage name
- selector/key
- warning code
- block order
- comment order
- safe reason

Logs and parser warnings must not include:

- raw HTML
- raw response body
- full post body text
- full comment text
- raw cookie
- proxy credential
- raw `.env` contents
- user-provided cookie path or file contents
- secret-bearing full query string

### NFR-UOW004-SEC-002. Import Side-Effect Safety

Importing UOW-004 modules must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create queues
- create HTTP clients

### NFR-UOW004-SEC-003. No Raw HTML Output

UOW-004 must not add raw HTML fields to `PostResult`, content blocks, comments, warnings, or failure payloads.

## Observability Requirements

### NFR-UOW004-OBS-001. Safe Detail Parser Events

UOW-004 should emit safe structured events for:

- detail parse start
- detail parse end
- required field failure
- recoverable parser warning
- content block count summary
- media dedupe summary
- comment page fetched
- comment count summary

Event payloads must follow `NFR-UOW004-SEC-001`.

## Maintainability Requirements

### NFR-UOW004-MAINT-001. Dependency Boundary

Allowed runtime dependencies for UOW-004:

- existing `beautifulsoup4`
- existing UOW-002 HTTP runtime
- Python standard library modules such as `urllib.parse`, `re`, and `datetime`

Not allowed in UOW-004:

- browser automation dependency
- scraping framework
- database dependency
- queue dependency
- storage dependency
- media downloader dependency

### NFR-UOW004-MAINT-002. Parser Boundary

UOW-004 may parse and return metadata/download candidates.

UOW-004 must not:

- download media files
- finalize file paths or object keys
- write JSONL
- write checkpoints
- create worker queues

### NFR-UOW004-MAINT-003. Backward-Compatible Models

UOW-004 Code Generation may extend UOW-001 models only with typed optional fields for documented media/attachment values.

Existing field meanings and requiredness must remain compatible.

Unknown or low-confidence fields may use `metadata`.

## Testing Requirements

### NFR-UOW004-TEST-001. Example And Fixture Tests

UOW-004 must include fixture/example tests for:

- detail metadata parsing
- text and image body parsing
- FMKorea video parsing
- YouTube parsing
- X/Twitter parsing
- attachment parsing
- normal comments and replies
- BEST comments
- optional field absence
- malformed optional block/comment warning
- required field failure

### NFR-UOW004-TEST-002. Property-Based Tests

UOW-004 must include Hypothesis tests for:

- URL normalization
- content block order uniqueness
- media dedupe idempotence
- comment ID extraction
- reaction score calculation
- required-field validation
- warning payload redaction

PBT targets pure helper/policy logic. BeautifulSoup selector correctness remains fixture-based.

### NFR-UOW004-TEST-003. Optional Live Smoke

Live smoke tests are not part of default unit tests or mandatory CI.

They may run only when explicitly enabled:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Allowed live smoke scope:

- one public detail page
- parser success
- key identity/title fields present
- no JSONL persistence
- no media file download
- no CAPTCHA automation

## Extension Compliance Summary

### Security Baseline

| Rule | Status | Rationale |
|---|---|---|
| SECURITY-03 | Compliant | Safe parser events exclude raw HTML, body/comment text, cookies, proxy credentials, and user cookie contents. |
| SECURITY-05 | Compliant | Parser guardrails validate required fields and optional bounds. |
| SECURITY-09 | Compliant | Parser failures expose safe reasons only. |
| SECURITY-10 | Compliant | dependency pinning remains required at code generation. |
| SECURITY-11 | Compliant | parser, HTTP runtime, worker, storage, and checkpoint responsibilities remain separated. |
| SECURITY-13 | Compliant | URL and ID extraction use structured parsing or constrained regex. |
| SECURITY-15 | Compliant | CAPTCHA/block propagation supports fail-closed Job behavior. |

Other Security Baseline rules are N/A for this parser-only unit.

### Resiliency Baseline

| Rule | Status | Rationale |
|---|---|---|
| RESILIENCY-10 | Compliant | required-field failure, optional warning isolation, and CAPTCHA propagation are required. |
| RESILIENCY-14 | Compliant | fixture/fake HTTP tests verify parser behavior without live network dependency. |
| RESILIENCY-15 | Compliant | safe parser warnings and structured events support incident triage. |

Other Resiliency Baseline rules are N/A for this non-deployable unit.

### Property-Based Testing

| Rule | Status | Rationale |
|---|---|---|
| PBT-01 | Compliant | testable parser helper properties are identified. |
| PBT-03 | Compliant | URL normalization, order uniqueness, media dedupe, comment ID, reaction score, validation, and redaction invariants are required. |
| PBT-04 | Compliant | media dedupe and warning redaction idempotence are required. |
| PBT-07 | Compliant | domain-specific strategies are required for URLs, block orders, media keys, comments, and warning payloads. |
| PBT-08 | Compliant | Hypothesis shrinking and reproducibility remain enabled. |
| PBT-09 | Compliant | Hypothesis remains selected. |
| PBT-10 | Compliant | fixture/example tests remain required beside PBT. |

PBT-02, PBT-05, and PBT-06 are N/A for this unit.
