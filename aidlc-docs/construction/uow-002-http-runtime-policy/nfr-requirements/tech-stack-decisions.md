# Tech Stack Decisions - UOW-002 HTTP Runtime Policy

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches UOW-001 and supports modern async typing |
| Async runtime | `asyncio` | Standard library, aligns with `httpx.AsyncClient` |
| HTTP client | `httpx>=0.27,<1` | Async client, MockTransport tests, proxy support, timeout support |
| Rate limiter primitive | `asyncio.Lock` plus injected clock/sleeper | Minimal dependency surface and deterministic tests |

## Dependency Management

| Decision | Selection | Rationale |
|---|---|---|
| HTTP dependency | `httpx>=0.27,<1` | Stable async HTTP client with test transport |
| User-Agent dependency | none | File load and sequential rotation are simple stdlib logic |
| Proxy dependency | none | httpx accepts proxy configuration directly |
| Cookie dependency | none | Static Cookie header handling needs no cookie jar package |
| Retry dependency | none | Retry predicate and backoff are simple local policy |
| Test dependencies | pytest, Hypothesis | Existing test stack from UOW-001 |
| Lock file | Required when resolver is available | SECURITY-10 reproducibility requirement |

## HTTP Runtime Decisions

| Area | Selection |
|---|---|
| Client lifecycle | One `httpx.AsyncClient` per Job execution |
| Page/comment timeout | `RuntimeConfig.timeout_seconds`, default 30 seconds |
| Media timeout | default 120 seconds, overrideable |
| Retry attempts | max 3 attempts by default |
| Retry targets | network error, timeout, HTTP 429, HTTP 5xx |
| Backoff | exponential, base 1s, max 30s, small jitter |
| Response shape | scraper-owned `HttpResponse`, not raw `httpx.Response` |
| Response classifier | maps outcome to UOW-001 `ResponseKind` |
| Connection pool default | `post_worker_count + media_worker_count + 2` |

## User-Agent, Proxy, Cookie Decisions

| Area | Selection | Rationale |
|---|---|---|
| User-Agent source | provided file path or default fallback | preserves baseline `user-agents.txt` behavior without import side effects |
| Rotation | sequential every configured outbound attempts, default 10 | deterministic and testable |
| Proxy source priority | explicit adapter values, then env mapping, then disabled | matches function specification |
| Proxy storage | not owned by UOW-002 | `.env` creation/editing belongs to CLI/container adapters |
| Proxy secrets | masked value such as `SecretStr` | prevents accidental log/repr exposure |
| Cookie behavior | explicit static Cookie header only | avoids persistent tracking state |
| Cookie jar | disabled | response `Set-Cookie` is ignored |

## Logging And Observability

| Decision | Selection | Rationale |
|---|---|---|
| Logging boundary | UOW-001 `LoggerPort` | adapter-neutral core |
| Metric backend | deferred | concrete backend belongs to container/infra UOWs |
| Safe log fields | method, host, path, status, kind, attempt, elapsed, request_kind | enough for debugging without secrets |
| Forbidden fields | query, Cookie, Authorization, proxy credentials, `.env`, body | prevents sensitive data leakage |

## Security Decisions

| Area | Decision |
|---|---|
| External calls | explicit timeout required |
| CAPTCHA | detect/classify only, no bypass |
| Blocked response | classify and do not retry |
| Secrets | never logged, persisted, or emitted in error details |
| Response body | no body in logs; bounded sample only for classification |
| Import behavior | no network, file, env, terminal, or client creation side effects |

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| HTTP tests | `httpx.MockTransport` | deterministic no-network HTTP behavior |
| Time tests | fake clock/fake sleeper | avoids slow/flaky sleep tests |
| Log tests | fake logger | verifies safe structured event fields |
| Property-based testing | Hypothesis | matches UOW-001 and supports policy invariant generation |
| Live smoke | deferred to UOW-008 opt-in harness | avoids default test instability |

Required example tests:

- successful GET/POST/download
- timeout/network retry
- 429/5xx retry
- CAPTCHA/block/not-found/login-required no-retry
- static cookie header behavior
- proxy masking
- safe log event shape
- import side-effect safety

Required PBT categories:

- User-Agent rotation sequence
- retry predicate invariants
- bounded backoff
- proxy masking
- safe log URL sanitization
- response classification invariants

## Performance Decisions

No fixed throughput SLA is set for UOW-002.

Performance posture:

- policy overhead should be negligible compared with network latency
- connection pool is bounded by worker count
- retry and backoff are bounded
- classification body sample is bounded
- full throughput measurement is deferred to Job runner and smoke harness units

## Deferred Decisions

These are intentionally deferred:

- exact FMKorea CAPTCHA/block body markers beyond initial conservative detection
- concrete CLI options for timeout/backoff/pool overrides
- concrete `.env` read/write flow
- Docker entrypoint env injection
- centralized metric/log backend
- live smoke test target URLs and schedules
