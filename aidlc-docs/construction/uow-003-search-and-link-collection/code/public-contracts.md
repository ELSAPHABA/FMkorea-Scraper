# Public Contracts - UOW-003 Search And Link Collection

## Package

UOW-003 exposes import-safe link collection contracts from:

- `fmkorea_scraper.collect`

Top-level convenience export:

- `fmkorea_scraper.LinkCollectorService`

## Main Service

### `LinkCollectorService`

Construction:

- `LinkCollectorService(http, *, direct_normalizer=None, board_urls=None, integrated_urls=None, board_parser=None, integrated_parser=None, range_evaluator=None)`

The `http` object must provide:

- `async get(url: str) -> object`

The returned object may be:

- a string containing HTML
- or an object with a `.text` string attribute, such as UOW-002 `HttpResponse`

Public methods:

- `collect(source) -> AsyncIterator[PostCandidate]`
- `collect_with_summary(source) -> CollectorRun`

Module helper:

- `collect_all(service, source) -> list[PostCandidate]`

## Supported Sources

`LinkCollectorService` dispatches by UOW-001 source `type`:

- `direct_post`
- `board_list`
- `board_search`
- `integrated_search`
- `deep_search`
- `no_keyword_range`
- `realtime_keyword`
- `realtime_all`

Unsupported source types raise `UnsupportedSourceError`.

## URL Components

### `DirectPostUrlNormalizer`

Accepted URL forms:

- `https://www.fmkorea.com/<document_srl>`
- `https://www.fmkorea.com/best/<document_srl>`
- `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- `https://www.fmkorea.com/search.php?mid=<board_id>&document_srl=<document_srl>`

Returns:

- UOW-001 `PostCandidate`

### `BoardUrlBuilder`

Methods:

- `build_list_url(board_id, page=1, category_id=None)`
- `build_search_url(board_id, keyword, search_target, page=1, category_id=None)`
- `safe_label(url)`

### `IntegratedSearchUrlBuilder`

Methods:

- `build_search_url(keyword, search_target, page=1, sort=None)`
- `clamp_page(page)`
- `safe_label(url)`

Integrated search page is clamped to max `1000`.

## Parser Components

### `BoardPageParser`

Method:

- `parse(html, *, board_id, base_url=..., request_url=..., page=1)`

Returns:

- `(SearchPage, list[CollectorFailure])`

### `IntegratedSearchParser`

Method:

- `parse(html, *, keyword, base_url=..., request_url=..., page=1)`

Returns:

- `(IntegratedSearchPage, list[BoardCandidate], list[CollectorFailure])`

## Policy Components

### `RangeFilterEvaluator`

Method:

- `evaluate(range_filter, candidate, *, descending=True) -> RangeDecision`

Decision kinds:

- `include`
- `skip_continue`
- `stop_traversal`
- `include_needs_detail_validation`

### `CandidateDeduper`

Primary key:

- `(site_id, board_id, document_id_raw)`

Fallback key:

- `(site_id, document_id_raw)`

### `BoardCandidateDeduper`

Key:

- `board_id`

## Import Safety

Importing `fmkorea_scraper.collect` does not:

- make network requests
- read files
- read environment variables
- prompt terminal input
- write outputs
- create queues
- create HTTP clients

## Infrastructure

UOW-003 creates no deployment, storage, queue, database, container, MCP, or CDK artifact.
