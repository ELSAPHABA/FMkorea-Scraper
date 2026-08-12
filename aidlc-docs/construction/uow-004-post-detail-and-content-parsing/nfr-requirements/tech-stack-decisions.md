# Tech Stack Decisions - UOW-004 Post Detail And Content Parsing

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches existing package and async runtime. |
| HTTP runtime | UOW-002 `HttpClient`/HTTP port | Keeps delay, retry, proxy, User-Agent, cookie policy, and block classification centralized. |
| HTML parser | BeautifulSoup | Required by project constraints and enough for static detail HTML parsing. |
| URL/query handling | `urllib.parse` | Standard library is enough for canonical URL, relative URL, and media URL normalization. |
| ID extraction | stdlib `re` plus structured URL parsing | Enough for document, file, video, tweet, and comment IDs. |
| Data models | Existing UOW-001 models with optional extensions | Preserves current schema while allowing documented media/attachment fields. |

## Dependency Decisions

| Dependency | Selection | Scope |
|---|---|---|
| BeautifulSoup | reuse existing `beautifulsoup4` | Detail HTML, content, media, attachment, and comment parsing. |
| HTTP | reuse UOW-002 `httpx` wrapper | UOW-004 does not create a parallel HTTP stack. |
| Browser automation | Not added | Playwright/Selenium are out of scope for default parsing. |
| Scraping framework | Not added | Scrapy or similar frameworks are unnecessary for this parser unit. |
| Media downloader | Not added | File download is later storage/worker scope. |
| Queue/storage/database | Not added | Queue, checkpoint, JSONL, Garage/S3, and PostgreSQL are later units. |

Exact package versions are fixed by the lock file during Code Generation/Build and Test if a resolver is available.

## Parser Strategy

| Area | Decision |
|---|---|
| Detail metadata | BeautifulSoup selectors scoped under `#bd_capture` with candidate fallback only when detail values are missing. |
| Canonical URL | Compare current/detail URL, canonical/document address when present, and UOW-003 candidate hints. |
| Content body | Find scoped `.xe_content` container once and traverse child DOM in order. |
| Text extraction | Normalize meaningful text and skip player/UI/attachment-table noise. |
| Images | Prefer `a.highslide[href]`, fall back to `img[src]`, and match attachment metadata by `file_srl` when possible. |
| FMKorea video | Emit one logical `fmk_video` block from wrapper/video/source/schema.org metadata. |
| YouTube | Parse static `youtube.com`, `youtu.be`, and existing embed iframe URLs. |
| X/Twitter | Parse static `x.com`, `twitter.com`, and existing embed iframe URLs. |
| Attachments | Parse `.rd_file a[data-href]` with `file_srl`, `sid`, `mid`, filename, URL, and size/download text when available. |
| Comments | Parse `.fdb_lst_ul > li`, BEST status, author/date/content/reactions, source order, and safe reply parent when available. |

## Failure And Warning Strategy

| Area | Decision |
|---|---|
| Required identity failure | Raise post-level parser failure. |
| Optional metadata failure | Record safe warning and continue. |
| Optional content/media/attachment failure | Record safe warning and continue. |
| Individual comment failure | Record safe warning and continue. |
| CAPTCHA/block/unavailable | Propagate UOW-002 classification. |
| Oversized output guardrail | Optional `max_content_blocks`, `max_comments`, `max_comment_pages` with safe failure/warning. |

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example tests | pytest | Existing test runner. |
| PBT | Hypothesis | Existing project choice. |
| Fixture format | inline strings or small files under `tests/fixtures/` | Keeps parser tests deterministic. |
| HTTP fake | UOW-002 fake/MockTransport pattern | No live network in default tests. |
| Live smoke | env-gated optional test | Keeps CI deterministic. |

Required test categories:

- detail metadata fixture
- text/image fixture
- FMKorea video fixture
- YouTube fixture
- X/Twitter fixture
- attachment fixture
- normal comment/reply fixture
- BEST comment fixture
- required field failure fixture
- malformed optional block/comment warning fixture
- URL normalization property
- block order uniqueness property
- media dedupe idempotence property
- comment ID extraction property
- reaction score property
- warning redaction property

## Deferred Decisions

These are intentionally left for later units:

- worker queue concurrency
- checkpoint persistence
- JSONL/Garage/S3 output
- media file download
- parser-stage failure retry execution
- CLI options
- container/MCP live smoke wiring
