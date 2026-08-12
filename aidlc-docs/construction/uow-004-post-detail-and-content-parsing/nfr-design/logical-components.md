# Logical Components - UOW-004 Post Detail And Content Parsing

## Component Overview

UOW-004 is a parser layer between UOW-003 link collection and later worker/storage units.

It receives one post candidate or direct post request, uses UOW-002 HTTP when fetching is needed, parses the detail page, and returns a final UOW-001 `PostResult`.

## Component Map

| Component | Module | Responsibility |
|---|---|---|
| `PostDetailService` | `parse/service.py` | Fetch detail/comment HTML through injected HTTP and assemble final `PostResult`. |
| `PostDetailParser` | `parse/service.py` | Coordinate metadata, content, media, attachment, comment, and warning parsing. |
| `ParserOptions` | `parse/models.py` | Hold optional guardrails such as `max_comment_pages`, `max_content_blocks`, and `max_comments`. |
| `DetailParseContext` | `parse/models.py` | Carry candidate hints, source URL, base URL, and safe identifiers inside parser flow. |
| `MetadataParser` | `parse/metadata.py` | Parse detail identity, canonical URL, title, author, date, counters, and category. |
| `ContentParser` | `parse/content.py` | Locate scoped content container and emit ordered body blocks. |
| `TextNormalizer` | `parse/content.py` | Normalize meaningful text and exclude UI/noise text. |
| `AttachmentParser` | `parse/media.py` | Parse `.rd_file a[data-href]` and provide lookup by `file_srl`. |
| `MediaBlockParser` | `parse/media.py` | Parse image, FMKorea video, YouTube, X/Twitter, link, and unknown embed blocks. |
| `MediaDeduper` | `parse/media.py` | Dedupe media blocks within one post. |
| `CommentParser` | `parse/comments.py` | Parse flat comments/replies, BEST fields, reactions, source order, and safe parent hints. |
| `ParseWarningCollector` | `parse/warnings.py` | Collect and serialize safe parser warnings. |
| `WarningRedactor` | `parse/warnings.py` | Ensure warnings/log payloads do not include raw HTML, secrets, or full text. |

## Dependency Direction

Allowed dependencies:

- `parse/service.py` may depend on parser modules, UOW-001 models, UOW-002 HTTP port/client, and UOW-003 `PostCandidate`.
- `parse/metadata.py` may depend on BeautifulSoup, stdlib URL/date helpers, and UOW-001 model types.
- `parse/content.py` may depend on BeautifulSoup, `parse/media.py`, and `parse/warnings.py`.
- `parse/media.py` may depend on BeautifulSoup, `urllib.parse`, `re`, and UOW-001 content/media model types.
- `parse/comments.py` may depend on BeautifulSoup, `re`, date helpers, and UOW-001 comment/reaction model types.
- `parse/warnings.py` may depend on stdlib dataclasses/enums only.
- `parse/models.py` may depend on stdlib dataclasses/enums and UOW-001/UOW-003 types only where necessary.

Disallowed dependencies:

- storage adapters
- checkpoint stores
- queues
- CLI prompts
- container entrypoints
- MCP servers
- browser automation
- direct `httpx.AsyncClient` construction
- media downloader libraries

## PostDetailService

### Construction

Inputs:

- UOW-002 `HttpClient` or `HttpPort`
- optional parser instances for tests
- optional safe logger
- optional `ParserOptions`

The service does not own the HTTP client lifecycle.

### Public Methods

- `parse(candidate_or_request) -> PostResult`
- `parse_html(html, candidate_or_request) -> PostResult` for tests and already-fetched callers

`parse_html()` is a convenience parser path. It must not bypass required field validation or warning redaction.

### Fetch Flow

1. Resolve detail URL from `PostCandidate` or `PostRequest`.
2. Fetch detail HTML through injected UOW-002 HTTP.
3. Parse initial detail page.
4. Fetch discovered comment pages sequentially when enabled and bounded.
5. Return final `PostResult`.

## DetailParseContext

Fields:

- `source_url`
- `base_url`
- `candidate`
- `post_request`
- `site_id`
- `board_id_hint`
- `document_id_hint`

Purpose:

- avoids passing loose dictionaries through parser functions
- keeps fallback metadata explicit
- gives warning redaction safe identifiers

## MetadataParser

Input:

- BeautifulSoup document
- `DetailParseContext`

Output:

- fields used to populate `PostResult`
- safe warnings

Selector baseline:

- `#bd_capture`
- `.rd_hd h1 .np_18px_span`
- `.rd_hd h1`
- `.rd_hd .member_plate`
- `.rd_hd .btm_area .side.fr span`
- `a.category[href*="category="]`

Failure boundary:

- missing document identity, canonical/detail URL, or title raises post-level parser failure
- missing optional metadata creates warnings or `null` values

## ContentParser

Input:

- BeautifulSoup document
- attachment lookup
- `DetailParseContext`

Output:

- `BodyContent`
- media-bearing blocks
- safe warnings

Container priority:

1. `#bd_capture .rd_body article > .xe_content`
2. `#bd_capture .rd_body .xe_content`

Rules:

- preserve DOM order
- assign unique block order
- skip empty/UI/noise text
- call media helpers for dedicated media blocks
- create general link blocks only when no dedicated block applies

## AttachmentParser

Input:

- BeautifulSoup document
- base URL

Output:

- attachment list
- lookup by `file_srl`
- safe warnings

Selector:

- `.rd_file a[data-href]`

Parsed values:

- filename
- URL
- `file_srl`
- `sid`
- `mid`
- size/download text when available

## MediaBlockParser

Input:

- DOM node
- base URL
- attachment lookup
- media dedupe state

Output:

- one content block
- or `None` when the node is not a supported media block
- safe warnings

Supported media:

- image
- FMKorea video
- YouTube
- X/Twitter
- attachment
- unknown embed

Deduplication key priority:

1. `(type, file_srl)`
2. `(type, normalized_url)`
3. `(type, order-local fallback)`

## CommentParser

Input:

- BeautifulSoup document or comment fragment
- starting source order

Output:

- flat list of comments
- next source order
- safe warnings

Selectors:

- `.fdb_lst_ul > li`
- `li[id^="comment_"]`

Parsed values:

- numeric comment ID
- source DOM ID
- source order
- depth
- parent comment ID when safe
- author
- date
- content
- reactions
- BEST status and badges

Failure handling:

- one bad comment creates a warning and parsing continues
- CAPTCHA/block/unavailable responses are not handled here and must propagate from UOW-002

## ParseWarningCollector

Fields per warning:

- `code`
- `stage`
- `selector`
- `order`
- `reason`
- safe identifiers

Output:

- serializable list stored at `PostResult.metadata["parse_warnings"]`

Rules:

- no raw HTML
- no full post body text
- no full comment text
- no cookie/proxy/user-cookie values
- no raw `.env` content

## Integration Points

### UOW-001 Core Models And Config

Consumes and may extend:

- `PostResult`
- `BodyContent`
- content block models
- media models
- attachment models
- `Comment`
- reaction/author/category models
- typed parser errors

### UOW-002 HTTP Runtime Policy

Consumes:

- `HttpClient` or `HttpPort`
- CAPTCHA/block classifications
- retry/rate-limit/proxy/User-Agent/cookie behavior

### UOW-003 Search And Link Collection

Consumes:

- `PostCandidate`
- candidate metadata fallback

UOW-004 re-parses final saved fields from the detail page.

### UOW-005 Job Runner And Checkpoint

Provides:

- one-post parsing service
- parser-stage failures
- safe parser warnings

UOW-005 owns:

- queue consumption
- cancellation
- retry orchestration
- checkpoint persistence

### UOW-006 Storage

Consumes:

- final `PostResult`
- media/attachment metadata and download candidates

UOW-006 owns:

- JSONL writing
- media file download/write
- Garage/S3 output
- local output paths

## Test Components

Test-only helpers:

- detail metadata fixture
- text/image content fixture
- FMKorea video fixture
- YouTube fixture
- X/Twitter fixture
- attachment fixture
- normal comment/reply fixture
- BEST comment fixture
- malformed optional block fixture
- malformed comment fixture
- required field failure fixture
- fake UOW-002 HTTP port for detail/comment pages
- Hypothesis strategies for URLs, media keys, comment IDs, reactions, warnings, and block orders

Production package must not include test-only fakes.

## Excluded Components

UOW-004 does not implement:

- link/list/search collector
- worker queue
- checkpoint store
- JSONL writer
- Garage/S3 adapter
- PostgreSQL adapter
- media downloader
- parser failure retry runner
- CLI wizard
- Docker entrypoint
- MCP server
