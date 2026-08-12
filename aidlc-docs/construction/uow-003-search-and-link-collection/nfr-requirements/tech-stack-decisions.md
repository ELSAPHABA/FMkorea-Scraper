# Tech Stack Decisions - UOW-003 Search And Link Collection

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches existing package and async runtime. |
| HTTP runtime | UOW-002 `HttpClient` | Keeps request delay, retry, proxy, User-Agent, and classification centralized. |
| HTML parser | BeautifulSoup | Required by project constraints and avoids browser automation. |
| URL/query handling | `urllib.parse` | Standard library is enough for URL building and query extraction. |
| JSON handling | stdlib `json` | Enough for small parser fixtures or future endpoint payloads. |

## Dependency Decisions

| Dependency | Selection | Scope |
|---|---|---|
| BeautifulSoup | `beautifulsoup4` if missing | Board/list/search fixture parsing. |
| HTTP | reuse `httpx` through UOW-002 | UOW-003 does not create a parallel HTTP stack. |
| Browser automation | Not added | Playwright/Selenium are out of scope. |
| Scraping framework | Not added | Scrapy is unnecessary for this bounded parser/collector unit. |
| URL builder library | Not added | `urllib.parse` is sufficient. |
| Queue/storage/database | Not added | Queue, checkpoint, and storage are later units. |

Exact package versions are fixed by the lock file during Code Generation/Build and Test if a resolver is available.

## Parser Strategy

| Area | Decision |
|---|---|
| Direct URL parser | `urllib.parse` path/query extraction |
| Board list parser | BeautifulSoup selectors from `docs/FMKorea-Scraper_Function_Specification.md` |
| Board search parser | same row parser as board list, with search no-result detection |
| Integrated search parser | BeautifulSoup selectors from `docs/FMKorea-Scraper_Function_Specification.md` |
| Parser failures | row/item-level safe failure records where possible |

## Traversal Decisions

| Area | Decision |
|---|---|
| Board list | `page_start` to `page_end` or parser/range termination |
| Board search | `page_start` to `page_end` or parser/range termination |
| Integrated max page | 1000 when no smaller `page_end` exists |
| No-keyword range | board list traversal plus `RangeFilter` |
| Deep search | integrated board discovery then sequential per-board keyword search |
| Realtime | one collection cycle only; UOW-005 owns loop and checkpoint |

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example tests | pytest | Existing test runner. |
| PBT | Hypothesis | Existing project choice. |
| Fixture format | inline strings or small files under `tests/fixtures/` | Keeps parser tests deterministic. |
| HTTP fake | UOW-002 fake/MockTransport pattern | No live network in default tests. |
| Live smoke | env-gated optional test | Keeps CI deterministic. |

Required test categories:

- direct URL normalization
- board URL building
- integrated search URL building
- parser fixture extraction
- no-result detection
- row/item failure isolation
- deep-search board dedupe
- range filter
- realtime dedupe
- safe logging fields

## Deferred Decisions

These are intentionally left for later units:

- post detail parser selectors
- comment/media parsing
- queue insertion and worker lifecycle
- checkpoint persistence
- JSONL/Garage output
- CLI options
- container/MCP live smoke wiring
