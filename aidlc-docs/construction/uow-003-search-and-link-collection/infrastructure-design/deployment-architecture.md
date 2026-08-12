# Deployment Architecture - UOW-003 Search And Link Collection

## Architecture Classification

UOW-003 has no standalone deployed runtime architecture.

It is a link collection package layer consumed by later scraper units and adapters.

```text
Developer or CI
    |
    v
UOW-003 Python link collection package
    |
    +-- direct URL normalization
    +-- board URL builder
    +-- integrated search URL builder
    +-- BeautifulSoup board parser
    +-- BeautifulSoup integrated parser
    +-- range filter evaluator
    +-- candidate deduper
    +-- deep-search board deduper
    |
    v
Unit tests, fixture tests, property-based tests

Optional manual path:
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
single FMKorea board list or integrated search smoke

Later units import UOW-003:
UOW-004 post detail parsing
UOW-005 JobRunner and queue/checkpoint orchestration
UOW-007 CLI
UOW-008 container and MCP
```

## Environment Topology

| Environment | UOW-003 Role | Infrastructure |
|---|---|---|
| Local development | run URL, policy, parser fixture, and optional live smoke tests | developer Python environment |
| CI | run unit tests, parser fixtures, and PBT without live network by default | CI runner |
| Runtime scraper | imported by later JobRunner/CLI/container units | no UOW-003-owned runtime resources |
| Optional live smoke | verify one external list/search collection path when explicitly enabled | local or CI runner with outbound internet |

## Runtime Boundaries

UOW-003 import must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create output directories
- create queues
- create HTTP clients

Runtime side effects begin only when a caller explicitly invokes a collector with an injected HTTP client.

At runtime, UOW-003 may:

- build URLs with `urllib.parse`
- call the injected UOW-002 HTTP client
- parse returned HTML with BeautifulSoup
- keep in-memory traversal state
- keep in-memory dedupe sets
- emit safe events through `LoggerPort`

At runtime, UOW-003 must not:

- close the injected HTTP client
- persist checkpoints
- write output files
- write storage records
- mutate process environment

## External Services

| Service Type | Status | Reason |
|---|---|---|
| FMKorea HTTP | Optional through UOW-002 | only env-gated smoke in UOW-003; normal runtime calls occur inside caller process |
| Proxy service | Deferred to UOW-002 | UOW-003 does not configure proxy infrastructure |
| Garage object storage | Deferred | output storage belongs to UOW-006 and UOW-008 |
| PostgreSQL checkpoint store | Deferred | checkpoint persistence belongs to UOW-005 and UOW-008 |
| Queue/scheduler | Deferred | worker orchestration belongs to UOW-005 and UOW-008 |
| Monitoring backend | Deferred | UOW-003 only emits safe events through `LoggerPort` |

## Configuration Flow

```text
JobConfig.source
    |
    v
LinkCollectorService
    |
    +-- DirectPostUrlNormalizer
    +-- BoardUrlBuilder
    +-- IntegratedSearchUrlBuilder
    +-- RangeFilterEvaluator
    +-- CandidateDeduper
    |
    v
Injected UOW-002 HttpClient / HttpPort
    |
    v
HTML response
    |
    v
BeautifulSoup parser
    |
    v
PostCandidate stream + CollectorSummary
```

UOW-003 does not read runtime files. Runtime files and environment values are resolved before the injected UOW-002 HTTP client is constructed.

## Test Architecture

Default test path:

```text
pytest / Hypothesis
    |
    +-- URL builder tests
    +-- range filter PBT
    +-- dedupe PBT
    +-- BeautifulSoup fixture tests
    +-- fake HTTP port collector tests
    |
    v
deterministic link collection tests
```

Live smoke path:

```text
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
marked live smoke test
    |
    v
single board list or integrated search request through UOW-002 HTTP
```

Live smoke is not a default CI gate.

## Security Boundary

The deployment boundary for UOW-003 is the caller process.

Required security behavior:

- no raw HTML in logs or failure records
- no full query URL in logs
- no raw keyword embedded in safe URL labels
- no cookie/proxy data in summaries
- no CAPTCHA bypass automation
- CAPTCHA/block classifications propagate upward

## Infrastructure Handoff

UOW-003 hands off link collection capability to later units:

- `LinkCollectorService`
- URL builders and normalizers
- BeautifulSoup parsers
- range filter evaluator
- candidate deduper
- collector summary/failure structures

Later units decide:

- concrete scraper worker process
- queue insertion
- checkpoint persistence
- JSONL/media output storage
- container env injection
- CLI terminal prompts
- MCP server hosting
- monitoring backend
