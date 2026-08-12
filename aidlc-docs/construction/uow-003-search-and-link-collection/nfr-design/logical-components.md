# Logical Components - UOW-003 Search And Link Collection

## Component Overview

UOW-003 is a thin collection layer between UOW-001 source models and UOW-004 post detail parsing.

It receives configured sources, uses UOW-002 HTTP, extracts `PostCandidate` values, and returns candidates plus safe summary data.

## Component Map

| Component | Module | Responsibility |
|---|---|---|
| `LinkCollectorService` | `collect/service.py` | Dispatch source config to the matching collector. |
| `DirectPostCollector` | `collect/service.py` | Normalize direct post URLs into candidates. |
| `BoardListCollector` | `collect/service.py` | Traverse board list pages. |
| `BoardSearchCollector` | `collect/service.py` | Traverse board keyword search pages. |
| `IntegratedSearchCollector` | `collect/service.py` | Traverse integrated search pages. |
| `DeepSearchCollector` | `collect/service.py` | Discover boards, then run per-board searches sequentially. |
| `NoKeywordRangeCollector` | `collect/service.py` | Traverse board list pages with a required range. |
| `RealtimeCollectionCycle` | `collect/service.py` | Run one latest collection cycle. |
| `DirectPostUrlNormalizer` | `collect/urls.py` | Parse and normalize supported direct URL forms. |
| `BoardUrlBuilder` | `collect/urls.py` | Build board list and board search URLs. |
| `IntegratedSearchUrlBuilder` | `collect/urls.py` | Build integrated search URLs. |
| `BoardPageParser` | `collect/parsers.py` | Parse board list/search HTML. |
| `IntegratedSearchParser` | `collect/parsers.py` | Parse integrated search HTML and board candidates. |
| `RangeFilterEvaluator` | `collect/policies.py` | Decide include, skip, stop, or detail validation needed. |
| `CandidateDeduper` | `collect/policies.py` | Remove duplicate post candidates in one collection run. |
| `BoardCandidateDeduper` | `collect/policies.py` | Remove duplicate board IDs for deep search. |

## Dependency Direction

Allowed dependencies:

- `collect/service.py` may depend on `collect/models.py`, `collect/urls.py`, `collect/parsers.py`, `collect/policies.py`, UOW-001 models, and UOW-002 HTTP port/client.
- `collect/parsers.py` may depend on BeautifulSoup, `collect/models.py`, and UOW-001 `PostCandidate`.
- `collect/urls.py` may depend on `urllib.parse`, `collect/models.py`, and UOW-001 `PostCandidate`.
- `collect/policies.py` may depend on `collect/models.py` and UOW-001 `RangeFilter`/`PostCandidate`.
- `collect/models.py` may depend on stdlib dataclasses/enums and UOW-001 types only where necessary.

Disallowed dependencies:

- storage adapters
- checkpoint stores
- queues
- CLI prompts
- container entrypoints
- MCP servers
- browser automation
- direct `httpx.AsyncClient` construction

## LinkCollectorService

### Construction

Inputs:

- UOW-002 `HttpClient` or `HttpPort`
- optional `LoggerPort`
- optional parser and policy instances for tests

The service does not own the HTTP client lifecycle.

### Public Methods

- `collect(source) -> AsyncIterator[PostCandidate]`
- `collect_with_summary(source) -> CollectorRun`
- `collect_all(source) -> list[PostCandidate]`

`collect_all()` is a small helper over the async iterator.

### Dispatch

| Source Type | Collector |
|---|---|
| `direct_post` | `DirectPostCollector` |
| `board_list` | `BoardListCollector` |
| `board_search` | `BoardSearchCollector` |
| `integrated_search` | `IntegratedSearchCollector` |
| `deep_search` | `DeepSearchCollector` |
| `no_keyword_range` | `NoKeywordRangeCollector` |
| `realtime_keyword` | `RealtimeCollectionCycle` |
| `realtime_all` | `RealtimeCollectionCycle` |

Unsupported source types raise a typed unsupported-source error.

## CollectorRun

Fields:

- `candidates`
- `summary`

Purpose:

- gives tests and UOW-005 a simple object containing both data and safe execution metadata

## SearchTraversalState

Fields:

- `mode`
- `board_id`
- `page`
- `page_end`
- `safe_url_label`
- `has_next`
- `stop_reason`
- `visited_pages`

Purpose:

- describes current and final traversal state without persisting checkpoints

## CollectorSummary

Fields:

- `mode`
- `visited_pages`
- `candidate_count`
- `deduped_count`
- `skipped_count`
- `range_stop_reason`
- `board_candidate_count`
- `failures`
- `final_state`

Purpose:

- supports safe logs, later Job reports, and checkpoint handoff

## CollectorFailure

Fields:

- `stage`
- `board_id`
- `safe_url_label`
- `reason`
- `retryable`

Rules:

- no raw HTML
- no raw response body
- no cookie/proxy data
- no full query string

## URL Components

### DirectPostUrlNormalizer

Accepted inputs:

- `https://www.fmkorea.com/<document_srl>`
- `https://www.fmkorea.com/best/<document_srl>`
- `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- `https://www.fmkorea.com/search.php?mid=<board_id>&document_srl=<document_srl>`

Outputs:

- normalized absolute URL
- `document_srl`
- `document_id_raw`
- optional `board_id`
- `PostCandidate`

### BoardUrlBuilder

Methods:

- `build_list_url(board_id, page, category_id=None) -> str`
- `build_search_url(board_id, keyword, search_target, page, category_id=None) -> str`
- `safe_label(url) -> str`

Uses stdlib `urllib.parse`.

### IntegratedSearchUrlBuilder

Methods:

- `build_search_url(keyword, search_target, page, sort=None) -> str`
- `clamp_page(page) -> int`
- `safe_label(url) -> str`

Integrated search page must not exceed 1000 unless a smaller configured end is used.

## Parser Components

### BoardPageParser

Input:

- HTML text
- base URL
- request URL
- page number

Output:

- `SearchPage`
- parse failures

Selectors:

- `div.bd table tbody tr`
- `a.hx[href]`
- `td.title a[href]`

Ignored rows:

- notice rows
- ad rows
- power-link/search ad rows
- rows without parseable `document_srl`

### IntegratedSearchParser

Input:

- HTML text
- base URL
- request URL
- page number

Output:

- `IntegratedSearchPage`
- board candidates
- parse failures

Extracts when present:

- title
- detail URL
- preview text
- board name
- board URL
- board ID
- date hint
- `document_srl`

Missing preview or board name does not fail the item.

## Policy Components

### RangeFilterEvaluator

Inputs:

- `RangeFilter`
- candidate `document_srl`
- candidate date hint
- known descending traversal flag

Outputs:

- `include`
- `skip_continue`
- `stop_traversal`
- `include_needs_detail_validation`

The evaluator is pure and has no HTTP or DOM dependency.

### CandidateDeduper

Methods:

- `seen_key(candidate) -> tuple`
- `is_new(candidate) -> bool`
- `filter_new(candidates) -> list[PostCandidate]`

Primary key:

- `(site_id, board_id, document_id_raw)`

Fallback key:

- `(site_id, document_id_raw)`

### BoardCandidateDeduper

Methods:

- `is_new(board_id) -> bool`
- `filter_new(board_candidates) -> list[BoardCandidate]`

Key:

- `board_id`

## Integration Points

### UOW-001 Core Models And Config

Consumes:

- source models
- `RangeFilter`
- `PostCandidate`
- typed errors

### UOW-002 HTTP Runtime Policy

Consumes:

- `HttpClient` or `HttpPort`
- CAPTCHA/block classifications
- retry/rate-limit/proxy/User-Agent behavior

### UOW-004 Post Detail And Content Parsing

Provides:

- candidate links for final detail parsing
- diagnostic candidate metadata only

UOW-004 re-parses final title, writer, date, category, body, media, and comments from the detail page.

### UOW-005 Job Runner And Checkpoint

Provides:

- async candidate stream
- final `CollectorSummary`
- final `SearchTraversalState`

UOW-005 owns:

- queue insertion
- realtime loop
- cancellation
- checkpoint persistence

## Test Components

Test-only helpers:

- fake HTTP port with URL-to-HTML mapping
- board list HTML fixtures
- board search HTML fixtures
- integrated search HTML fixtures
- malformed row/item fixtures
- Hypothesis strategies for URL inputs, ranges, candidate keys, and board IDs

Production package must not include test-only fakes.

## Excluded Components

UOW-003 does not implement:

- post detail parser
- media downloader
- comment parser
- JSONL writer
- Garage/S3 adapter
- PostgreSQL checkpoint store
- parser failure retry unit
- CLI wizard
- Docker entrypoint
- MCP server
