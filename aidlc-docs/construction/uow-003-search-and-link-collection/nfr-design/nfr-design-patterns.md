# NFR Design Patterns - UOW-003 Search And Link Collection

## Scope

This document turns the UOW-003 NFR requirements into implementation patterns.

UOW-003 owns FMKorea search/list URL construction, HTML list/search parsing, bounded traversal, range filtering, candidate dedupe, deep-search board expansion, realtime one-cycle collection, and safe collector summaries.

It does not own post detail parsing, queue insertion, checkpoint persistence, storage, CLI prompts, container entrypoints, MCP tools, or cloud infrastructure.

## Confirmed Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Use a small `src/fmkorea_scraper/collect/` package with `models.py`, `urls.py`, `parsers.py`, `policies.py`, and `service.py`. |
| Q2 | A | Provide async iterator collection APIs plus a small `collect_all()` helper for tests and small one-shot runs. |
| Q3 | A | Use caller-injected UOW-002 `HttpClient`/`HttpPort`; UOW-003 does not create or close HTTP clients. |
| Q4 | A | Use a small `SearchTraversalState` value object; checkpoint persistence remains in UOW-005. |
| Q5 | A | Isolate row/item parser failures as safe `CollectorFailure` records; propagate CAPTCHA/block/login-required errors. |
| Q6 | A | Put range logic in a pure `RangeFilterEvaluator` returning include/skip/stop decisions. |
| Q7 | A | Use run-local in-memory candidate dedupe with primary and fallback keys. |
| Q8 | A | Deep search discovers board IDs through integrated search, then runs per-board searches sequentially. |
| Q9 | A | Emit safe structured summaries/events without raw HTML, cookies, proxy credentials, or full query strings. |
| Q10 | A | Test URL/range/dedupe with pytest/Hypothesis, parser behavior with fixtures, and live smoke only behind env opt-in. |

No follow-up question is required. The decisions are internally consistent and preserve the baseline scraper structure where it fits FMKorea.

## Package Separation Pattern

UOW-003 uses one package:

- `src/fmkorea_scraper/collect/models.py`
- `src/fmkorea_scraper/collect/urls.py`
- `src/fmkorea_scraper/collect/parsers.py`
- `src/fmkorea_scraper/collect/policies.py`
- `src/fmkorea_scraper/collect/service.py`

This keeps the implementation small while separating the parts that change for different reasons.

| Module | Owns |
|---|---|
| `models.py` | Collector-only value objects and result summaries. |
| `urls.py` | Direct URL normalization, board URLs, integrated search URLs, and safe URL labels. |
| `parsers.py` | BeautifulSoup row/item parsing for board pages and integrated search pages. |
| `policies.py` | Range decisions, candidate dedupe, board dedupe, traversal guards. |
| `service.py` | Mode dispatch and collector orchestration. |

The package must not import storage, CLI, container, MCP, or checkpoint adapters.

## Async Streaming Pattern

Collectors expose an async streaming API as the primary path:

- downstream can consume candidates as they are found
- UOW-005 can enqueue candidates without waiting for the full search to finish
- memory use is bounded by traversal state plus dedupe state

A `collect_all()` helper may collect the stream into a list for tests and small one-shot callers.

`collect_all()` is convenience only. It must not become the internal execution model for large searches.

## HTTP Boundary Pattern

UOW-003 receives a caller-managed UOW-002 `HttpClient` or `HttpPort`.

Rules:

- do not create `httpx.AsyncClient`
- do not close the injected HTTP client
- do not read `.env`, user-agent files, proxy config, or cookie files
- let UOW-002 classify CAPTCHA/block/login-required responses

This keeps runtime policy in UOW-002 and collection logic in UOW-003.

## Traversal State Pattern

Each collector maintains a `SearchTraversalState`.

The state is in-memory only and supports:

- current mode
- board ID
- current page
- requested page end
- safe current URL label
- last stop reason
- visited page count

UOW-003 may return the final state in `CollectorSummary`. UOW-005 decides whether and how to persist it as a checkpoint.

## Parser Failure Isolation Pattern

BeautifulSoup parsers isolate failures at the smallest useful unit:

- board list/search: one table row
- integrated search: one result item
- deep search board discovery: one board candidate

Recoverable row/item failures produce `CollectorFailure` records and parsing continues.

Propagated failures:

- CAPTCHA detected
- blocked response
- login-required response
- unavailable response classified by UOW-002
- page-level unknown DOM structure where no safe parsing path remains

Failures must not include raw HTML or full query URLs.

## Range Decision Pattern

`RangeFilterEvaluator` returns explicit decisions:

- `include`
- `skip_continue`
- `stop_traversal`
- `include_needs_detail_validation`

Document ID bounds are strong when `document_srl` is parseable.

Date bounds are strong only when the list/search date is absolute and parseable. Ambiguous dates keep the candidate and mark it for detail validation.

For descending pages, the evaluator may stop traversal when:

- `document_srl < min_document_srl`
- absolute parsed date is older than `date_from`

The evaluator is pure and suitable for PBT.

## Candidate Dedupe Pattern

Candidate dedupe is run-local and in-memory.

Primary key:

- `(site_id, board_id, document_id_raw)`

Fallback key:

- `(site_id, document_id_raw)`

If `max_seen_candidates` is later exposed by config and exceeded, the collector fails with a bounded-resource error instead of growing memory without limit.

Persistent/job-to-job dedupe is deferred to UOW-006.

## Deep Search Pattern

Deep search runs in two stages:

1. integrated search discovers board IDs
2. each board is searched sequentially with the same keyword and range filter

Integrated seed posts are not emitted as final candidates for deep search.

Board-level failures are partial failures unless UOW-002 classified the response as CAPTCHA/block/login-required. Partial failures are included in `CollectorSummary`.

Board-level parallelism is deferred to UOW-005 or later throughput work.

## Safe Observability Pattern

Collector events and summaries may include:

- mode
- board ID
- page number
- visited page count
- accepted candidate count
- skipped candidate count
- deduped candidate count
- stop reason
- safe failure reason

Collector events and summaries must not include:

- raw HTML
- raw response body
- raw cookie
- proxy credentials
- full query strings
- raw keyword embedded in a full request URL

If a URL label is needed, use a safe label from `urls.py`, such as host, path, and page number.

## Test Harness Pattern

Default tests are deterministic and offline.

Required fixture/example tests:

- direct URL normalization
- board list rows and page end
- board search rows and no-result state
- integrated search results and board ID discovery
- row/item parser failure isolation

Required PBT targets:

- URL builder determinism
- integrated search page clamp
- range filter monotonicity
- candidate dedupe idempotence
- realtime dedupe exclusion
- deep-search board dedupe

Optional live smoke tests run only when:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Live smoke must not be a default CI gate.

## Compliance Summary

### Security

- Safe logging excludes raw HTML, secrets, and full query URLs.
- Importing UOW-003 has no network, file, env, prompt, storage, or queue side effects.
- CAPTCHA/block classifications propagate upward.

### Resiliency

- Row/item parser failures do not fail the entire collection.
- Deep-search board failures can be partial.
- Traversal is bounded by configured limits, parser signals, range termination, and integrated page cap.

### PBT

- PBT targets pure URL and policy logic.
- DOM parsing uses small deterministic fixtures.
