# Component Dependencies

## Dependency Matrix

| Component | Depends On | Communication |
|---|---|---|
| `CliAdapter` | `JobConfigValidator`, `ScraperFacade` | Direct async call through `asyncio.run()` |
| `ContainerAdapter` | `JobConfigValidator`, `ScraperFacade` | Direct async call |
| `McpAdapter` | `JobConfigValidator`, `ScraperFacade` | Direct async call from MCP tool |
| `ScraperFacade` | `JobRunner`, `SearchCollectionService`, `PostDetailService`, `ParserFailureRetryService` | Direct async call |
| `JobRunner` | `SearchCollectionService`, `PostWorkerPool`, `StorageService`, `CheckpointStorePort` | Queue plus direct async call |
| `SearchCollectionService` | `HttpClient`, `FmkoreaUrlBuilder`, `BoardSearchParser`, `IntegratedSearchParser` | HTTP plus parser calls |
| `PostWorkerPool` | `PostDetailService`, `StorageService` | Queue plus direct async call |
| `PostDetailService` | `HttpClient`, `PostMetadataParser`, `ContentBlockParser`, `CommentService`, `MediaService` | HTTP plus parser calls |
| `CommentService` | `CommentParser`, optional `HttpClient` | Parser call, optional comment page request |
| `MediaService` | `ContentBlockParser`, `HttpClient`, `MediaStorePort` | Parser/download/store calls |
| `StorageService` | `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, `CheckpointStorePort` | Port calls |
| `ParserFailureRetryService` | `FailureStorePort`, `JobRunner`, `OutputStorePort` | Failure read plus direct Job call |
| `HttpClient` | `UserAgentProvider`, `ProxyProvider`, `ClockPort`, `LoggerPort` | Direct calls |
| `OutputStorePort` | Local or S3-compatible implementation | Port implementation |
| `MediaStorePort` | Local or S3-compatible implementation | Port implementation |
| `FailureStorePort` | Local or S3-compatible implementation | Port implementation |
| `CheckpointStorePort` | Local or PostgreSQL implementation | Port implementation |
| `CdkApp` | `ContainerAdapter` runtime contract, storage/checkpoint env contract | Deployment configuration |

## Runtime Flow

1. CLI, container, or MCP translates input into `JobConfig`, `ResumeRequest`, or API request models.
2. `ScraperFacade` receives the typed request.
3. Job execution requests are delegated to `JobRunner`.
4. `JobRunner` starts one `SearchCollectionService` and a bounded `PostWorkerPool`.
5. `SearchCollectionService` enqueues `PostCandidate` objects into an `asyncio.Queue`.
6. `PostWorkerPool` consumes candidates and calls `PostDetailService`.
7. `PostDetailService` uses parser components to build `PostResult`.
8. `StorageService` writes posts, media, failures, and checkpoint updates through ports.
9. Checkpoint advances only after the post result is stored successfully.

## Storage Flow

| Data | Owner Component | Local Mode | Container Mode |
|---|---|---|---|
| posts JSONL | `OutputStorePort` | local JSONL file | S3-compatible object storage |
| media files | `MediaStorePort` | local media directory | S3-compatible object storage |
| failures JSONL | `FailureStorePort` | local JSONL file | S3-compatible object storage |
| job report | `OutputStorePort` | local JSON file | S3-compatible object storage |
| checkpoint/status | `CheckpointStorePort` | local checkpoint file | PostgreSQL |

Garage is the default S3-compatible object store. SeaweedFS can replace it later through the same S3-compatible port if media/storage requirements justify the change.

## Communication Patterns

1. **Adapter to core**: CLI, container, MCP only translate input/output. They do not parse FMKorea HTML.
2. **Collector to worker**: `SearchCollectionService` writes `PostCandidate` values to an `asyncio.Queue`.
3. **Worker to output**: `PostWorkerPool` stores `PostResult` through `StorageService`.
4. **Output to checkpoint**: checkpoint completed position is updated only after post result storage succeeds.
5. **HTTP policy**: all FMKorea requests go through `HttpClient`; parsers never call network directly.
6. **Storage policy**: concrete storage implementations stay behind ports.
7. **Retry policy**: parser-stage retry composes failure input and direct-post Job execution instead of duplicating parser logic.

## Data Ownership

| Data | Owner Component | Storage |
|---|---|---|
| Job config | `JobConfigValidator` | In memory, checkpoint snapshot |
| Post candidates | `SearchCollectionService` | Queue, optional checkpoint snapshot |
| Post result JSONL | `OutputStorePort` | Local file or S3-compatible object store |
| Comment list | `PostDetailService` and `CommentParser` | Nested under post JSONL, normalized later |
| BEST comment flags | `CommentParser` | `comments[].is_best`, `comments[].badges` |
| Comment reactions | `CommentParser` | `comments[].reactions` |
| Media files | `MediaStorePort` | Local directory or S3-compatible object store |
| Failed post/media records | `FailureStorePort` | Failure JSONL/report |
| Checkpoint/status | `CheckpointStorePort` | Local file or PostgreSQL |
| Structured logs | `LoggerPort` implementation | stdout/stderr or local logs |

## Boundary Decisions

- FMKorea parser logic is site-specific and lives in `search` and `post_detail`.
- Cross-community sharing is limited to schema concepts, storage contracts, checkpoint contracts, and adapter shape.
- Scrapling is the parser runtime; optional `DynamicFetcher`/Playwright is isolated behind list/search/detail required-DOM fallback and is never used for confirmed CAPTCHA/block responses.
- No CAPTCHA auto-bypass component is introduced.
- No community plugin framework is introduced in this phase.
