# Domain Entities - UOW-003 Search And Link Collection

## Entity Overview

UOW-003 defines search and link collection entities for FMKorea. These entities describe implementation contracts, not necessarily final file names.

This unit turns configured entrypoints into deduplicated UOW-001 `PostCandidate` values. It does not parse final post metadata, body content, comments, media, storage output, checkpoints, CLI prompts, containers, or MCP tools.

## Collector Components

### LinkCollectorService

Responsibilities:

- dispatch by `JobConfig.source.type`
- create mode-specific collectors
- return candidates and a collector summary
- keep queue ownership out of UOW-003

Collaborators:

- UOW-002 `HttpClient`
- `DirectPostCollector`
- `BoardListCollector`
- `BoardSearchCollector`
- `IntegratedSearchCollector`
- `DeepSearchCollector`
- `NoKeywordRangeCollector`
- `RealtimeCollectionCycle`

### DirectPostCollector

Responsibilities:

- normalize direct FMKorea URLs into `PostCandidate`
- accept short and query-based URL forms
- extract `document_srl`, `document_id_raw`, and possible `board_id`
- dedupe direct URLs

Accepted forms:

- `https://www.fmkorea.com/<document_srl>`
- `https://www.fmkorea.com/best/<document_srl>`
- `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- `https://www.fmkorea.com/search.php?mid=<board_id>&document_srl=<document_srl>`

### BoardListCollector

Responsibilities:

- build board list URLs
- traverse configured page range
- call `BoardPageParser`
- apply range filter and dedupe
- return `SearchPage` and candidates

### BoardSearchCollector

Responsibilities:

- build board search URLs
- traverse configured page range
- call `BoardPageParser`
- apply range filter and dedupe
- return `SearchPage` and candidates

### IntegratedSearchCollector

Responsibilities:

- build integrated search URLs
- traverse pages until configured page end, parsed page end, no-result, or page 1000
- call `IntegratedSearchParser`
- apply range filter and dedupe
- produce board ID candidates for deep search

### NoKeywordRangeCollector

Responsibilities:

- reuse board list traversal
- require `RangeFilter`
- apply date/document range filtering
- preserve optional category filter

It does not invent a blank keyword search API.

### DeepSearchCollector

Responsibilities:

- run integrated search discovery
- dedupe seed board IDs
- run sequential board keyword searches per board
- apply range filter and candidate dedupe
- record partial board failures

Integrated search seed posts are used only to discover boards. Final candidates come from per-board searches.

### RealtimeCollectionCycle

Responsibilities:

- run one latest collection cycle
- support realtime keyword and realtime all modes
- apply a provided dedupe set
- return only new candidates

It does not own timers, loops, checkpoints, queues, or termination conditions.

## Parser Components

### BoardPageParser

Input:

- HTML text
- base URL
- current request URL
- current page number

Output:

- `SearchPage`

Extracts:

- post candidate rows
- candidate URL
- `document_srl`
- candidate title
- candidate category hint
- candidate comment count hint
- candidate created date hint
- candidate view/reaction hints
- page end or next-page availability

### IntegratedSearchParser

Input:

- HTML text
- base URL
- current request URL
- current page number

Output:

- `IntegratedSearchPage`

Extracts:

- post candidate items
- candidate board IDs
- page end or next-page availability
- no-result state

## URL Components

### DirectPostUrlNormalizer

Responsibilities:

- parse FMKorea direct post URLs
- reject unsupported hosts
- normalize relative links to absolute `https://www.fmkorea.com/...`
- produce a `PostCandidate`

### BoardUrlBuilder

Responsibilities:

- build board list URLs
- build board search URLs
- add optional category filter
- percent-encode user keyword and query parameter values using structured URL APIs

Board list form:

- `https://www.fmkorea.com/<board_id>?page=<page>`

Board search form:

- `https://www.fmkorea.com/search.php?mid=<board_id>&search_target=<target>&search_keyword=<keyword>&page=<page>`

### IntegratedSearchUrlBuilder

Responsibilities:

- build integrated search URLs
- add `act=IS`
- add `is_keyword`
- add `where=document`
- add `search_target`
- add `page`
- add optional `sph_sort`

Integrated search form:

- `https://www.fmkorea.com/search.php?act=IS&is_keyword=<keyword>&where=document&search_target=<target>&page=<page>&sph_sort=<sort>`

## Policy Components

### RangeFilterEvaluator

Responsibilities:

- decide candidate inclusion
- decide skip-and-continue
- decide current traversal termination when descending order makes it safe

Inputs:

- `RangeFilter`
- candidate `document_srl`
- candidate created date hint
- known traversal ordering

### CandidateDeduper

Responsibilities:

- track seen candidate keys
- return only first occurrence
- expose seen set for realtime cycles

Primary key:

- `(site_id, board_id, document_id_raw)`

Fallback key:

- `(site_id, document_id_raw)`

### BoardCandidateDeduper

Responsibilities:

- dedupe deep search board IDs

Key:

- `board_id`

## Data Entities

### SearchTraversalState

Fields:

- `mode`
- `board_id`
- `page`
- `page_end`
- `current_url`
- `has_next`

Purpose:

- supports collector traversal and later checkpoint handoff

### BoardCandidate

Fields:

- `board_id`
- `board_name`
- `board_url`

Purpose:

- deep search per-board expansion

### CollectorSummary

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

- gives UOW-005 enough information for logs and checkpoint state

### CollectorFailure

Fields:

- `stage`
- `board_id`
- `url`
- `reason`
- `retryable`

Purpose:

- records partial failures, especially in deep search

## Relationships To Other Units

| Unit | Relationship |
|---|---|
| UOW-001 | consumes source models, `RangeFilter`, `PostCandidate`, typed errors |
| UOW-002 | uses `HttpClient` for all network I/O |
| UOW-004 | receives `PostCandidate` for detail parsing later |
| UOW-005 | owns queue insertion, repeated realtime loop, checkpoint, cancellation, and worker ordering |
| UOW-006 | owns final output dedupe and idempotent storage |
| UOW-007 | builds source config from CLI options |
| UOW-008 | provides container/MCP adapter wiring later |
