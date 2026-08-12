# Business Logic Model - UOW-003 Search And Link Collection

## Purpose

UOW-003 turns configured FMKorea entrypoints into deduplicated `PostCandidate` values.

This unit owns search/list traversal and candidate extraction. It does not own post detail parsing, storage, checkpoint writes, realtime loops, or queue lifecycle.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Collector output | async iterator/list of `PostCandidate`; queue insertion belongs to UOW-005 |
| Direct URL normalization | accept short, `/best/`, `index.php`, and `search.php` document URL forms |
| Board list/search URL builder | structured FMKorea board/list and `search.php` URL builders |
| Board parser scope | candidate rows plus metadata hints only |
| Integrated search | `search.php?act=IS` builder, parser, board discovery, max page 1000 when no explicit page end |
| Range filter | applied during link collection, with final detail validation still possible later |
| No-keyword range | board list traversal plus range filter |
| Deep search | integrated board discovery, then sequential per-board keyword search |
| Realtime | UOW-003 provides one latest collection cycle; loop/timer/checkpoint belongs to UOW-005 |
| Dedupe | `(site_id, board_id, document_id_raw)` with `(site_id, document_id_raw)` fallback |

## Collector Flow

1. Caller provides a UOW-001 source config and UOW-002 `HttpClient`.
2. `LinkCollectorService` dispatches to the matching collector.
3. Collector builds URLs through structured URL builders.
4. Collector fetches HTML through `HttpClient`.
5. BeautifulSoup parsers extract `PostCandidate` values and traversal metadata.
6. `RangeFilterEvaluator` decides whether each candidate is included, skipped, or should end the current traversal.
7. `CandidateDeduper` removes duplicates.
8. Collector returns candidates and `CollectorSummary`.

## Supported Modes

| Mode | Source Model | Collector |
|---|---|---|
| direct URL | `DirectPostSource` | `DirectPostCollector` |
| board list | `BoardListSource` | `BoardListCollector` |
| board search | `BoardSearchSource` | `BoardSearchCollector` |
| integrated search | `IntegratedSearchSource` | `IntegratedSearchCollector` |
| deep search | `DeepSearchSource` | `DeepSearchCollector` |
| no-keyword range | `NoKeywordRangeSource` | `NoKeywordRangeCollector` |
| realtime keyword | `RealtimeKeywordSource` | `RealtimeCollectionCycle` |
| realtime all | `RealtimeAllSource` | `RealtimeCollectionCycle` |

## Direct URL Flow

Accepted forms:

- `https://www.fmkorea.com/<document_srl>`
- `https://www.fmkorea.com/best/<document_srl>`
- `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- `https://www.fmkorea.com/search.php?mid=<board_id>&document_srl=<document_srl>`

Flow:

1. Validate host belongs to FMKorea.
2. Parse `document_srl` from path or query.
3. Parse `board_id` from `mid` query when available.
4. Normalize relative URLs to `https://www.fmkorea.com/...`.
5. Build `PostCandidate`.
6. Dedupe candidates.

If `board_id` is missing, UOW-004 may resolve it from the detail page.

## Board List Flow

URL form:

- `https://www.fmkorea.com/<board_id>?page=<page>`
- optional `category=<category_id>`

Traversal:

1. Start at configured `page_start`.
2. Fetch current page.
3. Parse rows and page metadata.
4. Apply range filtering and dedupe.
5. Stop at configured `page_end`, parsed page end, no valid rows, no next-page evidence, or range termination.

## Board Search Flow

URL form:

- `https://www.fmkorea.com/search.php?mid=<board_id>&search_target=<target>&search_keyword=<keyword>&page=<page>`
- optional `category=<category_id>`

Traversal:

1. Start at configured `page_start`.
2. Fetch current page.
3. Parse rows and page metadata through the same `BoardPageParser`.
4. Apply range filtering and dedupe.
5. Stop at configured `page_end`, parsed page end, no-result state, no valid rows, or range termination.

## Board Page Parser Flow

`BoardPageParser` searches under:

- `div.bd table tbody tr`

Candidate link selectors:

- `a.hx[href]`
- `td.title a[href]`

Extraction:

- detail URL
- `document_srl`
- candidate title
- category hint
- comment count hint
- created date hint
- views/reactions hints
- page end or next-page availability

Excluded rows:

- notice rows
- ad rows
- power-link/search ad rows
- rows without parseable `document_srl`

Candidate metadata remains diagnostic only.

## Integrated Search Flow

URL form:

- `https://www.fmkorea.com/search.php?act=IS&is_keyword=<keyword>&where=document&search_target=<target>&page=<page>&sph_sort=<sort>`

Traversal:

1. Start at configured `page_start`.
2. Fetch current page.
3. Parse result items and board candidates.
4. Apply range filter to result post candidates.
5. Stop at configured `page_end`, parsed page end, no-result state, missing next-page evidence, or page 1000.

Integrated search outputs:

- `PostCandidate` list for normal integrated search mode
- `board_id` candidates for deep search

## Integrated Parser Flow

`IntegratedSearchParser` extracts:

- title and detail URL
- preview text when available
- board name and board URL when available
- board ID
- created date hint
- `document_srl`
- page end or no-result state

The parser should be tolerant of missing preview or board name. A missing `document_srl` drops the result item.

## Range Filter Flow

Inclusion checks:

- `date_from <= candidate_created_at <= date_to`
- `min_document_srl <= document_srl <= max_document_srl`

Early termination for descending lists/searches:

- stop when a candidate is older than `date_from`
- stop when a candidate `document_srl` is lower than `min_document_srl`

Skip and continue:

- candidate newer than `date_to`
- candidate `document_srl` greater than `max_document_srl`

The collector treats list/search metadata as hints. UOW-004/UOW-005 may re-check final detail metadata later.

## No-Keyword Range Flow

No-keyword range reuses board list traversal.

Flow:

1. Validate `NoKeywordRangeSource.range_filter` exists.
2. Build board list URL with optional category.
3. Traverse pages.
4. Apply range filter and early termination.
5. Return candidates and summary.

## Deep Search Flow

Flow:

1. Run integrated search for the keyword.
2. Extract candidate board IDs.
3. Dedupe board IDs.
4. For each board ID, run board search with the same keyword.
5. Apply range filter and candidate dedupe.
6. Record per-board failures without failing the whole collection.

Integrated search seed posts are not emitted as final candidates in deep search.

Deep search requires at least one date or document range. UOW-001 validates this.

## Realtime Cycle Flow

UOW-003 implements one reusable collection cycle.

Realtime keyword:

- board scope: run one latest board search cycle
- integrated scope: run one latest integrated search cycle

Realtime all:

- run one latest board list cycle

The cycle applies the provided dedupe set and returns only new candidates.

UOW-005 owns:

- repeated loop
- timer/end-at termination
- checkpoint save
- queue insertion

## Testable Properties

- Direct URL normalization extracts deterministic `document_id_raw`.
- Board URL builder preserves `board_id`, `page`, keyword, target, and category.
- Integrated search URL builder preserves `act=IS`, keyword, target, page, and sort.
- Integrated search traversal never exceeds page 1000 without explicit page bounds.
- Candidate dedupe is idempotent.
- Range filter inclusion is monotonic for descending document IDs.
- Realtime cycle returns no candidate already present in the dedupe set.
- Deep search board dedupe uses `board_id`.
