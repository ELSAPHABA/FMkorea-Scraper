# Business Rules - UOW-003 Search And Link Collection

## Runtime Boundary Rules

### BR-003-001. Import Side Effects

Importing UOW-003 modules must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create queues

### BR-003-002. HTTP Boundary

All network I/O must go through UOW-002 `HttpClient`.

UOW-003 must not create a separate `httpx.AsyncClient`, use `requests`, or use browser automation.

### BR-003-003. Queue Boundary

UOW-003 returns candidates through async iterator/list APIs.

`asyncio.Queue` ownership belongs to UOW-005.

### BR-003-004. No Storage

UOW-003 does not write JSONL, media files, failure records, checkpoints, or Job reports.

## Candidate Rules

### BR-003-005. Candidate Key

Primary candidate dedupe key is:

- `(site_id, board_id, document_id_raw)`

Fallback key when `board_id` is unknown:

- `(site_id, document_id_raw)`

### BR-003-006. Candidate Metadata Is Not Final Metadata

List/search pages may provide candidate title, category, date, views, reactions, and comment count.

These values may be stored only as filtering, dedupe, and diagnostic hints in `PostCandidate.metadata`.

Final persisted metadata is parsed again from the detail page by UOW-004.

### BR-003-007. Candidate Ordering

Collectors preserve source page and DOM order.

UOW-003 does not guarantee final persisted order because UOW-005 may process candidates with multiple workers.

### BR-003-008. Direct URL Normalization

Direct post URLs must be normalized into `PostCandidate` values by parsing:

- `document_srl`
- `document_id_raw`
- possible `board_id`
- normalized absolute URL

Accepted URL forms:

- `https://www.fmkorea.com/<document_srl>`
- `https://www.fmkorea.com/best/<document_srl>`
- `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- `https://www.fmkorea.com/search.php?mid=<board_id>&document_srl=<document_srl>`

Unsupported hosts are rejected by UOW-001 validation or UOW-003 normalization.

## Board List And Search Rules

### BR-003-009. Board List URL

Board list requests use:

- `https://www.fmkorea.com/<board_id>?page=<page>`

Optional category filter:

- `category=<category_id>`

### BR-003-010. Board Search URL

Board search requests use:

- `https://www.fmkorea.com/search.php`

Parameters:

- `mid=<board_id>`
- `search_target=<search_target>`
- `search_keyword=<keyword>`
- `page=<page>`
- optional `category=<category_id>`

### BR-003-011. Search Target Values

UOW-003 passes validated `search_target` values from UOW-001 source config.

Known values include:

- `title_content`
- `title_content_summary`
- `title`
- `content`
- `nick_name`
- `comment`

### BR-003-012. Board Row Inclusion

The parser searches under:

- `div.bd table tbody tr`

Candidate link selectors:

- `a.hx[href]`
- `td.title a[href]`

Rows are ignored when they are clearly:

- notice rows
- ad rows
- power-link/search ad rows
- rows without a parseable `document_srl`

### BR-003-013. Board Page End

Page traversal stops when:

- configured `page_end` is reached
- parsed page end is reached
- no valid candidate rows exist
- no next page evidence exists
- range termination decides further pages cannot match

## Integrated Search Rules

### BR-003-014. Integrated Search URL

Integrated search requests use:

- `https://www.fmkorea.com/search.php`

Parameters:

- `act=IS`
- `is_keyword=<keyword>`
- `where=document`
- `search_target=<search_target>`
- `page=<page>`
- optional `sph_sort=<sort>`

### BR-003-015. Integrated Search Page Limit

If `page_end` is not provided, traversal may continue until page 1000.

Traversal still stops earlier when the parser detects no results, page end, or missing next-page evidence.

### BR-003-016. Integrated Result Parsing

Integrated search parsing extracts:

- detail URL
- title
- preview text when available
- board ID
- board name when available
- created date hint
- `document_srl`

Each result may also produce a board candidate for deep search.

## Range Rules

### BR-003-017. Range Inclusion

A candidate is included only when it satisfies all configured bounds that can be evaluated:

- `date_from <= candidate_created_at <= date_to`
- `min_document_srl <= document_srl <= max_document_srl`

Missing candidate date is not enough to reject by date unless the mode relies on date-based termination and the page has no usable date signal.

### BR-003-018. Range Termination

For descending list/search results, traversal may stop when:

- candidate date is older than `date_from`
- candidate `document_srl` is lower than `min_document_srl`

The collector skips candidates newer than `date_to` or greater than `max_document_srl` and continues.

### BR-003-019. Final Range Validation Remains Possible

UOW-003 range filtering is an optimization and early rejection layer.

UOW-004/UOW-005 may still validate final metadata from the detail page before storage.

## No-Keyword Range Rules

### BR-003-020. No-Keyword Range Reuses Board List

No-keyword range collection reuses board list traversal.

It does not use blank keyword search unless a later verified FMKorea endpoint requires it.

### BR-003-021. No-Keyword Range Requires Bounds

`NoKeywordRangeSource` must include at least one date or document range bound.

UOW-001 validates this. UOW-003 must not silently run unbounded no-keyword collection.

## Deep Search Rules

### BR-003-022. Deep Search Required Range

Deep search requires at least one date or document range bound.

UOW-001 validates this. UOW-003 must not silently run unbounded deep search.

### BR-003-023. Deep Search Board Discovery

Deep search discovers board IDs through integrated search.

Board dedupe key:

- `board_id`

### BR-003-024. Deep Search Final Candidates

Integrated search seed posts are not directly emitted as final candidates.

Final candidates are emitted from per-board keyword searches after board discovery.

### BR-003-025. Deep Search Sequential Board Traversal

Per-board keyword searches run sequentially inside UOW-003.

Broad parallel board traversal is deferred until there is a measured need and a Job-level concurrency policy in UOW-005.

### BR-003-026. Deep Search Partial Failure

Failure in one candidate board does not fail the whole deep search.

The collector records:

- board ID
- safe URL
- safe reason
- retryable flag

CAPTCHA/block errors are exceptions to this partial-failure rule and propagate to UOW-005.

## Realtime Rules

### BR-003-027. Realtime Cycle Only

UOW-003 implements a single collection cycle for realtime modes.

UOW-005 owns loop, sleep, termination, checkpoint, cancellation, and queue insertion.

### BR-003-028. Realtime Keyword

Realtime keyword cycle:

- uses board search when `scope="board"` and `board_id` exists
- uses integrated search when `scope="integrated"`
- returns only candidates not present in the provided dedupe set

### BR-003-029. Realtime All

Realtime all cycle:

- uses board list latest page
- preserves optional category filter
- returns only candidates not present in the provided dedupe set

### BR-003-030. Realtime Dedupe

Realtime cycle must not return candidates already present in the provided dedupe set.

## Error Rules

### BR-003-031. Safe Errors

Parser and collector failures must use UOW-001 typed exceptions or safe failure structures.

Raw HTML, raw cookies, proxy credentials, and full URLs with sensitive query values must not be logged.

### BR-003-032. CAPTCHA And Block Propagation

CAPTCHA/block errors from UOW-002 are not swallowed by UOW-003.

They propagate to UOW-005 so the Job can stop and save checkpoint.
