# NFR Requirements - UOW-003 Search And Link Collection

## Scope

This document defines non-functional requirements for `UOW-003 Search And Link Collection`.

In scope:

- direct URL normalization
- board list/search URL generation
- integrated search URL generation
- BeautifulSoup parser correctness for list/search pages
- traversal bounds
- candidate dedupe
- range filtering
- deep search board discovery
- realtime one-cycle collection
- safe structured collector logging

Out of scope:

- post detail parsing
- result storage
- checkpoint persistence
- queue lifecycle
- CLI prompt UX
- container/MCP hosting

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | `page_end` wins; integrated search has max page 1000 without explicit bound; board list/search use page end, no-result, valid-row absence, range termination, and optional `max_pages`. |
| Q2 | A | Code generation must include fixtures for direct URL, board list, board search, integrated search, no-result page, and deep-search board discovery. |
| Q3 | A | Individual row/item parse failures become safe `CollectorFailure` records; page-level unknown structure and CAPTCHA/block propagate. |
| Q4 | A | Candidate dedupe uses in-memory set with optional `max_seen_candidates`; persistent dedupe is deferred to UOW-006. |
| Q5 | A | `document_srl` ranges apply strongly; date ranges apply strongly only when list dates are absolute and parseable. Ambiguous dates are included with metadata. |
| Q6 | A | Safe structured events cover collector lifecycle, page progress, counts, range termination, and deep-search per-board failures. |
| Q7 | A | PBT targets pure URL/policy logic; BeautifulSoup DOM parsing uses fixture/example tests. |
| Q8 | A | Live smoke tests are excluded from default tests and mandatory CI unless explicitly enabled. |
| Q9 | A | Use BeautifulSoup and stdlib `urllib.parse`; no extra scraping framework or URL builder dependency. |

No follow-up question is required. The answers are internally consistent.

Dependency note: BeautifulSoup is already selected by the function specification. If `beautifulsoup4` is not yet present in `pyproject.toml`, UOW-003 Code Generation may add that required parser dependency. No additional runtime dependency is added for URL building, browser automation, queues, storage, or scraping frameworks.

## Performance Requirements

### NFR-UOW003-PERF-001. Bounded Traversal

Integrated search must never request page greater than 1000 unless a smaller configured `page_end` applies.

Board list/search traversal terminates on:

- configured `page_end`
- parsed page end
- no-result state
- no valid candidate rows
- absent next-page evidence
- range termination
- optional `max_pages`

### NFR-UOW003-PERF-002. Bounded Dedupe Memory

Candidate dedupe may use an in-memory set.

If `max_seen_candidates` is configured and exceeded, the collector must stop with a safe bounded-resource error rather than growing unbounded memory.

Persistent or large-scale dedupe is deferred to UOW-006 output/idempotency work.

### NFR-UOW003-PERF-003. Sequential Deep Search Expansion

Deep search per-board expansion runs sequentially in UOW-003.

Broad parallel board traversal is deferred to UOW-005 if a measured throughput need appears.

## Reliability And Resiliency Requirements

### NFR-UOW003-REL-001. Parser Failure Isolation

Individual row/item parser failures must not fail the whole page.

Required behavior:

- record a safe `CollectorFailure`
- skip the failed row/item
- continue parsing remaining rows/items

Exceptions:

- CAPTCHA/block/unavailable errors from UOW-002 propagate
- page-level unrecognized search result structure may fail the page

### NFR-UOW003-REL-002. Partial Deep Search Failure

Failure in one candidate board must not fail the whole deep search.

The collector records:

- board ID
- safe URL/path
- safe reason
- retryable flag when available

CAPTCHA/block responses are not partial failures. They propagate to UOW-005.

### NFR-UOW003-REL-003. Deterministic Traversal State

Collector summaries must expose enough state for UOW-005 handoff:

- mode
- board ID
- page
- current URL safe label
- visited page count
- accepted/deduped/skipped counts
- range stop reason
- partial failures

UOW-003 does not persist checkpoints.

### NFR-UOW003-REL-004. Ambiguous Date Safety

If a list/search date cannot be parsed as an absolute date, UOW-003 must not reject the candidate solely because of that date.

The candidate should be retained with metadata indicating that final date validation is required after UOW-004 detail parsing.

## Security Requirements

### NFR-UOW003-SEC-001. Safe Logging

Logs must not include:

- raw HTML
- raw response body
- raw cookie
- proxy credential
- full URL query
- user-provided keyword in a raw query string

Allowed values:

- redacted URL/path
- board ID
- page number
- accepted/skipped/deduped counts
- safe reason
- range stop reason

### NFR-UOW003-SEC-002. CAPTCHA And Block Propagation

CAPTCHA/block classifications from UOW-002 must not be swallowed or converted into successful empty results.

They propagate to UOW-005 so the Job can stop and save checkpoint.

### NFR-UOW003-SEC-003. Import Side-Effect Safety

Importing UOW-003 modules must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create queues

## Observability Requirements

### NFR-UOW003-OBS-001. Safe Collector Events

UOW-003 must emit safe structured events for:

- collector start
- collector end
- page fetched
- candidate count summary
- range termination
- row/item parse failure
- deep-search per-board failure

Raw HTML and full query URLs are excluded from event payloads.

## Maintainability Requirements

### NFR-UOW003-MAINT-001. Dependency Boundary

Allowed runtime dependency for UOW-003:

- `beautifulsoup4`, if it is not already present

Not allowed in UOW-003:

- browser automation dependency
- scraping framework
- database dependency
- queue dependency
- storage dependency
- custom URL builder dependency

### NFR-UOW003-MAINT-002. Parser Boundary

Search/list parsers may extract candidate metadata needed for filtering and dedupe.

Detailed post body, comments, media, output schema finalization, and storage remain in later units.

## Testing Requirements

### NFR-UOW003-TEST-001. Example And Fixture Tests

UOW-003 must include fixtures for:

- direct URL normalization
- board list rows and pagination
- board search rows and no-result state
- integrated search result list and page end
- deep-search board candidate extraction
- row/item parse failure isolation

### NFR-UOW003-TEST-002. Property-Based Tests

UOW-003 must include Hypothesis tests for:

- board URL round trip
- integrated search query determinism
- integrated max page clamp
- candidate dedupe idempotence
- range filter monotonicity
- realtime dedupe exclusion
- deep-search board dedupe

PBT must target pure policy/URL logic. BeautifulSoup DOM parser correctness remains fixture-based.

### NFR-UOW003-TEST-003. Optional Live Smoke

Live smoke tests are not part of default unit tests or mandatory CI.

They may run only when explicitly enabled:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Allowed live smoke scope:

- one board list page
- or one integrated search page
- no CAPTCHA handling automation
- no persisted cookies

## Extension Compliance Summary

### Security Baseline

| Rule | Status | Rationale |
|---|---|---|
| SECURITY-03 | Compliant | Safe collector events exclude raw HTML, cookies, proxy credentials, and full query URLs. |
| SECURITY-05 | Compliant | Source config validation comes from UOW-001; traversal guardrails validate bounds. |
| SECURITY-09 | Compliant | Parser failures expose safe reasons only. |
| SECURITY-10 | Compliant | dependency pinning remains required at code generation. |
| SECURITY-11 | Compliant | collector, parser, HTTP runtime, storage, and checkpoint responsibilities remain separated. |
| SECURITY-13 | Compliant | URL/query parsing uses structured parsing. |
| SECURITY-15 | Compliant | CAPTCHA/block propagation supports fail-closed Job behavior. |

Other Security Baseline rules are N/A for this library/search unit.

### Resiliency Baseline

| Rule | Status | Rationale |
|---|---|---|
| RESILIENCY-10 | Compliant | bounded traversal, parser failure isolation, and CAPTCHA propagation are required. |
| RESILIENCY-14 | Compliant | fixture/fake HTTP tests verify failure behavior without live network dependency. |
| RESILIENCY-15 | Compliant | collector summaries and safe events support incident triage. |

Other Resiliency Baseline rules are N/A for this non-deployable unit.

### Property-Based Testing

| Rule | Status | Rationale |
|---|---|---|
| PBT-01 | Compliant | testable search/link properties are identified. |
| PBT-03 | Compliant | URL, bounds, dedupe, range, and realtime invariants are required. |
| PBT-04 | Compliant | dedupe idempotence and deterministic URL building are required. |
| PBT-07 | Compliant | domain-specific strategies are required for URLs, candidates, ranges, and boards. |
| PBT-08 | Compliant | Hypothesis shrinking and reproducibility remain enabled. |
| PBT-09 | Compliant | Hypothesis remains selected. |
| PBT-10 | Compliant | fixture/example tests remain required beside PBT. |

PBT-02, PBT-05, and PBT-06 are N/A for this unit.
