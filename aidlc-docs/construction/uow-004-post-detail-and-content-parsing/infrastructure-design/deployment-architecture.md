# Deployment Architecture - UOW-004 Post Detail And Content Parsing

## Architecture Classification

UOW-004 has no standalone deployed runtime architecture.

It is a detail parser package layer consumed by later scraper units and adapters.

```text
Developer or CI
    |
    v
UOW-004 Python detail parser package
    |
    +-- metadata parser
    +-- scoped content parser
    +-- media and attachment parser
    +-- comment parser
    +-- parser warning collector
    |
    v
Unit tests, fixture tests, property-based tests

Optional manual path:
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
single public FMKorea detail-page smoke

Later units import UOW-004:
UOW-005 JobRunner and queue/checkpoint orchestration
UOW-006 JSONL/media storage
UOW-007 CLI
UOW-008 container and MCP
```

## Environment Topology

| Environment | UOW-004 Role | Infrastructure |
|---|---|---|
| Local development | run parser fixture, fake HTTP, PBT, and optional live smoke tests | developer Python environment |
| CI | run unit tests, parser fixtures, and PBT without live network by default | CI runner |
| Runtime scraper | imported by later JobRunner/CLI/container units | no UOW-004-owned runtime resources |
| Optional live smoke | verify one external detail parsing path when explicitly enabled | local or CI runner with outbound internet |

## Runtime Boundaries

UOW-004 import must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create output directories
- create queues
- create HTTP clients

Runtime side effects begin only when a caller explicitly invokes `PostDetailService` with an injected HTTP client.

At runtime, UOW-004 may:

- call the injected UOW-002 HTTP client
- parse returned HTML with BeautifulSoup
- keep in-memory parse context
- keep in-memory per-post media dedupe state
- emit safe events through `LoggerPort`
- return final `PostResult`

At runtime, UOW-004 must not:

- close the injected HTTP client
- persist checkpoints
- write output files
- write storage records
- download media files
- mutate process environment

## External Services

| Service Type | Status | Reason |
|---|---|---|
| FMKorea HTTP | Optional through UOW-002 | only env-gated smoke in UOW-004; normal runtime calls occur inside caller process |
| Proxy service | Deferred to UOW-002 | UOW-004 does not configure proxy infrastructure |
| Garage object storage | Deferred | output storage belongs to UOW-006 and UOW-008 |
| PostgreSQL checkpoint store | Deferred | checkpoint persistence belongs to UOW-005 and UOW-008 |
| Queue/scheduler | Deferred | worker orchestration belongs to UOW-005 and UOW-008 |
| Monitoring backend | Deferred | UOW-004 only emits safe events through `LoggerPort` |

## Configuration Flow

```text
PostCandidate or PostRequest
    |
    v
PostDetailService
    |
    v
Injected UOW-002 HttpClient / HttpPort
    |
    v
detail HTML and optional comment page HTML
    |
    v
BeautifulSoup parsers
    |
    +-- MetadataParser
    +-- AttachmentParser
    +-- ContentParser
    +-- MediaBlockParser
    +-- CommentParser
    +-- ParseWarningCollector
    |
    v
PostResult
```

UOW-004 does not read runtime files. Runtime files and environment values are resolved before the injected UOW-002 HTTP client is constructed.

## Test Architecture

Default test path:

```text
pytest / Hypothesis
    |
    +-- metadata fixture tests
    +-- content/media fixture tests
    +-- attachment fixture tests
    +-- comment/BEST fixture tests
    +-- fake HTTP detail service tests
    +-- URL/media/comment/warning PBT
    |
    v
deterministic detail parser tests
```

Live smoke path:

```text
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
marked live smoke test
    |
    v
single public detail request through UOW-002 HTTP
    |
    v
parse identity/title/content summary only
```

Live smoke is not a default CI gate and must not write JSONL or download media.

## Security Boundary

The deployment boundary for UOW-004 is the caller process.

Required security behavior:

- no raw HTML in logs or warning records
- no full post body/comment text in logs
- no cookie/proxy data in warnings
- no user-provided cookie path/content in warnings
- no CAPTCHA bypass automation
- CAPTCHA/block classifications propagate upward

## Infrastructure Handoff

UOW-004 hands off detail parsing capability to later units:

- `PostDetailService`
- metadata/content/media/comment parser components
- parser warning structures
- optional model extensions
- final `PostResult`

Later units decide:

- concrete scraper worker process
- queue consumption
- checkpoint persistence
- JSONL/media output storage
- media file download/write
- container env injection
- CLI terminal prompts
- MCP server hosting
- monitoring backend
