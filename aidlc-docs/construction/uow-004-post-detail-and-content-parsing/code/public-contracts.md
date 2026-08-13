# Public Contracts - UOW-004 Post Detail And Content Parsing

## Package

UOW-004 exposes import-safe post detail parsing contracts from:

- `fmkorea_scraper.parse`

Public exports:

- `PostDetailService`
- `ParserOptions`
- `DetailParseContext`
- `MetadataParser`
- `AttachmentParser`
- `MediaBlockParser`
- `ContentParser`
- `CommentParser`
- `ParseWarning`
- `ParseWarningCollector`

## Main Service

### `PostDetailService`

Construction:

- `PostDetailService(http=None, *, options=None, metadata_parser=None, attachment_parser=None, content_parser=None, comment_parser=None)`

The optional `http` object must provide:

- `async get(url: str) -> object`

The returned object may be:

- a string containing HTML
- or an object with a `.text` string attribute, such as UOW-002 `HttpResponse`

Public methods:

- `parse(candidate_or_request) -> PostResult`
- `parse_html(html, candidate_or_request) -> PostResult`

Accepted inputs:

- UOW-001 `PostCandidate`
- UOW-001 `PostRequest`

`parse()` fetches the detail page through the injected HTTP boundary. `parse_html()` is a synchronous parser for already-fetched HTML and does not perform network requests.

## Parser Options

`ParserOptions` fields:

- `max_comment_pages: int | None`
- `max_content_blocks: int | None`
- `max_comments: int | None`

Adapters should derive these values from persisted UOW-001 `ScrapeOptions` when a parser is used as part of a Job run.

When `max_comment_pages` is set, `parse()` fetches discovered comment page links sequentially through the injected HTTP client. Duplicate comment IDs are stored once. `parse_html()` parses only the provided HTML.

## Parsed Output

The service returns UOW-001 `PostResult` with:

- final detail metadata: board ID/name, document ID, canonical URL, category, title, author, date, views, reactions, and comment count
- `content.blocks` preserving source DOM order
- `content.text` built from meaningful text/link content
- attachments parsed from `.rd_file a[data-href]`
- media summary records for image, FMKorea video, YouTube, and X/Twitter blocks
- flat comments with BEST status, badges, author, date, content, up/down counts, and score
- safe parser warnings under `metadata.parse_warnings` when recoverable parse issues occur

## Content Block Types

UOW-004 fills existing UOW-001 content models and adds optional fields only:

- `TextBlock`
- `ImageBlock`
- `FmkVideoBlock`
- `YouTubeBlock`
- `XBlock`
- `LinkBlock`
- `AttachmentBlock`
- `UnknownEmbedBlock`

No raw HTML field is exposed.

## Failure Contract

Post-level parse failure is raised when required detail identity or title cannot be resolved.

Recoverable malformed block/comment cases are isolated as safe parser warnings and do not fail the whole post.

## Import Safety

Importing `fmkorea_scraper.parse` does not:

- make network requests
- read files
- read environment variables
- prompt terminal input
- write outputs
- create queues
- create HTTP clients

## Infrastructure

UOW-004 creates no deployment, storage, queue, database, container, MCP, or CDK artifact.
