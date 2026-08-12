# Deployment Architecture - UOW-002 HTTP Runtime Policy

## Architecture Classification

UOW-002 has no standalone deployed runtime architecture.

It is a shared HTTP runtime package layer consumed by later scraper units and adapters.

```text
Developer or CI
    |
    v
UOW-002 Python HTTP runtime package
    |
    +-- httpx.AsyncClient lifecycle
    +-- request limiter
    +-- retry/backoff
    +-- timeout config
    +-- User-Agent provider
    +-- Proxy provider and .env reader
    +-- response classifier
    +-- safe HTTP event builder
    |
    v
Unit tests, property-based tests, fake transport tests

Optional manual path:
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
single lightweight FMKorea HEAD/GET smoke

Later units import UOW-002 runtime:
UOW-003 search collection
UOW-004 post/comment/media fetches
UOW-005 JobRunner
UOW-007 CLI
UOW-008 container and MCP
```

## Environment Topology

| Environment | UOW-002 Role | Infrastructure |
|---|---|---|
| Local development | run fake transport tests and optional live smoke | developer Python environment |
| CI | run unit tests and PBT without live network by default | CI runner |
| Runtime scraper | imported by later JobRunner/CLI/container units | no UOW-002-owned runtime resources |
| Optional live smoke | verify one external HTTP call when explicitly enabled | local or CI runner with outbound internet |

## Runtime Boundaries

UOW-002 import must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create output directories

Runtime side effects begin only when a caller explicitly creates runtime objects.

At runtime creation, UOW-002 may:

- read explicit User-Agent file path
- read execution-location `user-agents.txt`
- read execution-location `.env`
- create one `httpx.AsyncClient`
- initialize in-memory cookie state

At close, UOW-002 must:

- close `httpx.AsyncClient`
- drop in-memory cookies

## External Services

| Service Type | Status | Reason |
|---|---|---|
| FMKorea HTTP | Optional | only env-gated live smoke in UOW-002; normal scraping occurs in later units |
| Proxy service | Configured only | UOW-002 accepts proxy config but does not provision proxy infrastructure |
| Garage object storage | Deferred | output storage belongs to UOW-006 and UOW-008 |
| PostgreSQL checkpoint store | Deferred | checkpoint persistence belongs to UOW-005 and UOW-008 |
| Queue/scheduler | Deferred | worker orchestration belongs to UOW-005 and UOW-008 |
| Monitoring backend | Deferred | UOW-002 only emits safe events through `LoggerPort` |

## Configuration Flow

```text
Caller runtime options
    |
    +-- explicit proxy option?
    |       |
    |       v
    |   ProxyProvider
    |
    +-- explicit .env path or execution-location .env
    |       |
    |       v
    |   DotenvProxyLoader using dotenv_values()
    |
    +-- explicit User-Agent path or execution-location user-agents.txt
            |
            v
        UserAgentProvider
```

Proxy priority:

1. explicit runtime option
2. `.env`
3. disabled

User-Agent priority:

1. explicit file path
2. execution-location `user-agents.txt`
3. built-in default User-Agent

## Test Architecture

Default test path:

```text
pytest / Hypothesis
    |
    +-- fake clock
    +-- fake sleeper
    +-- httpx.MockTransport or small fake transport
    |
    v
deterministic HTTP runtime policy tests
```

Live smoke path:

```text
FMKOREA_LIVE_SMOKE_ENABLED=true
    |
    v
marked live smoke test
    |
    v
single lightweight HEAD/GET request
```

Live smoke is not a default CI gate.

## Security Boundary

The deployment boundary for UOW-002 is the caller process.

Required security behavior:

- `trust_env=False`
- no process environment mutation through `load_dotenv()`
- no raw `.env` logging
- no proxy password logging
- no credential proxy URL logging
- no raw cookie logging
- no raw header/body logging by default
- no CAPTCHA bypass automation

## Infrastructure Handoff

UOW-002 hands off HTTP runtime capability to later units:

- `HttpClient`
- `RuntimePolicyService`
- `ProxyProvider`
- `UserAgentProvider`
- `ResponseClassifier`
- `SafeHttpEventBuilder`

Later units decide:

- concrete scraper worker process
- checkpoint persistence
- JSONL/media output storage
- container env injection
- CLI terminal prompts
- MCP server hosting
- monitoring backend
