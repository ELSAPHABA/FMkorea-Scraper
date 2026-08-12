# NFR Requirements - UOW-002 HTTP Runtime Policy

## Scope

This document defines non-functional requirements for `UOW-002 HTTP Runtime Policy`.

In scope:

- `httpx.AsyncClient` runtime dependency
- Job-scoped HTTP client lifecycle
- timeout and retry/backoff policy
- Job-scoped async rate limiting
- bounded connection pool configuration
- User-Agent rotation behavior
- proxy and static cookie secret handling
- classified response body handling
- safe structured HTTP logging
- deterministic unit/property testing with no live network

Out of scope:

- FMKorea URL/query construction
- BeautifulSoup parsing
- storage/checkpoint persistence
- CLI wizard and `.env` creation flow
- container entrypoint
- MCP tools
- deployed monitoring backend or cloud infrastructure

## Security Requirements

### NFR-SEC-001. Minimal HTTP Dependency Surface

UOW-002 must add `httpx>=0.27,<1` as the HTTP runtime dependency.

User-Agent rotation, proxy config conversion, cookie header handling, retry predicates, and safe URL/log shaping must use stdlib plus httpx. New dependencies require explicit justification in a later plan.

Security mapping:

- SECURITY-10: supply-chain surface is minimized.

### NFR-SEC-002. Explicit Timeouts

All external HTTP calls must have explicit timeouts.

Defaults:

- page/comment request timeout: `RuntimeConfig.timeout_seconds`, default 30 seconds
- media download timeout: default 120 seconds

Both values must be overrideable through validated Job/runtime config.

Security and resiliency mapping:

- SECURITY-15: external calls fail safely.
- RESILIENCY-10: no unbounded waits.

### NFR-SEC-003. Secret Protection

Proxy passwords, credential-bearing proxy URLs, Cookie headers, Authorization headers, and `.env` values must not appear in:

- logs
- exception messages
- `ErrorResult.details`
- failure details
- checkpoints
- object representation output

Secrets must be stored through `SecretStr` or an equivalent masked value.

Security mapping:

- SECURITY-03: sensitive data is excluded from application logs.
- SECURITY-09: production errors do not expose internal/secret values.
- SECURITY-12: no hardcoded credentials or secret leakage.

### NFR-SEC-004. Safe Structured HTTP Logs

HTTP log events may include only:

- method
- host
- path
- status code
- `ResponseKind`
- attempt
- elapsed seconds
- request kind

Forbidden:

- raw query string
- Cookie
- Authorization
- Proxy-Authorization
- proxy ID/password
- `.env` content
- full response body

Security mapping:

- SECURITY-03: structured logging with secret masking.

### NFR-SEC-005. Import Side-Effect Safety

Importing the HTTP package must not:

- instantiate an `httpx.AsyncClient`
- read `.env`
- read `user-agents.txt`
- read cookie files
- open sockets
- prompt terminal input
- create output directories

Runtime file/network behavior starts only when an explicit client/provider method is called.

Security mapping:

- SECURITY-15: resource lifecycle is explicit and safe.

### NFR-SEC-006. Response Body Handling

Page/comment responses may return text for parser use, and media downloads may return bytes for later storage.

Restrictions:

- classification should inspect only bounded body samples when body matching is needed
- logs must never contain body content
- response body persistence belongs to parser/storage units, not HTTP logging

## Reliability And Resiliency Requirements

### NFR-REL-001. Job-Scoped Client Lifecycle

One HTTP client is created per Job execution and closed at Job shutdown.

The implementation must avoid:

- process-global singleton clients
- one client per request

Resiliency mapping:

- RESILIENCY-10: connection pools are isolated per Job.
- SECURITY-15: resources are cleaned up.

### NFR-REL-002. Shared Async Rate Limiter

All external request types must pass through one Job-scoped async limiter.

The limiter must use `asyncio.Lock` or an equivalent concurrency-safe primitive so multiple workers cannot bypass the configured interval.

### NFR-REL-003. Retry And Backoff

Retry is allowed only for:

- network error
- timeout
- HTTP 429
- HTTP 5xx

Defaults:

- max attempts: 3
- base backoff: 1 second
- max backoff: 30 seconds
- jitter: small bounded jitter

Non-retryable:

- CAPTCHA
- blocked response
- not found
- login required
- deleted/private/unavailable content

### NFR-REL-004. Classified Response Contract

Every HTTP outcome must map to a `ResponseKind`.

Callers receive a classified response object rather than raw `httpx.Response`.

The HTTP layer must classify but not save checkpoints. UOW-005 owns stop/checkpoint behavior.

### NFR-REL-005. Bounded Connection Pool

The default connection pool limit must be derived from Job worker settings:

```text
post_worker_count + media_worker_count + 2
```

The limit must be overrideable for future tuning.

### NFR-REL-006. CAPTCHA Handling

CAPTCHA detection must not attempt bypass.

HTTP behavior:

- classify as `ResponseKind.CAPTCHA`
- do not retry
- return the classification to the caller

Job behavior is deferred to UOW-005.

## Performance Requirements

### NFR-PERF-001. Rate Limiter Predictability

The rate limiter must make effective outbound request timing predictable at the Job process level.

It does not need cross-process or cross-container coordination.

### NFR-PERF-002. Low Policy Overhead

HTTP policy overhead should be negligible compared with network latency.

No fixed millisecond SLA is set for UOW-002. Exact throughput and concurrency measurements belong to UOW-005/UOW-008 when worker queues and smoke harnesses exist.

### NFR-PERF-003. Bounded Resource Use

The implementation must bound:

- connection pool size
- retry attempts
- backoff duration
- response body sample used for classification

## Observability Requirements

### NFR-OBS-001. Adapter-Neutral Logging

UOW-002 emits safe structured events through `LoggerPort`.

It must not implement a concrete metrics backend, file logger, CloudWatch integration, or dashboard.

Adapter/infrastructure units decide where logs are shipped.

### NFR-OBS-002. Attempt-Level Visibility

Each request attempt should be observable through a safe event containing attempt number, elapsed time, status, and `ResponseKind`.

This supports retry debugging without exposing sensitive request data.

## Maintainability Requirements

### NFR-MAINT-001. Central HTTP Boundary

Later search/parser/media units must not create raw `httpx.AsyncClient` instances for FMKorea requests.

All external HTTP calls route through UOW-002.

### NFR-MAINT-002. Provider Separation

User-Agent, proxy, cookie, retry, rate-limit, and classification behavior must stay in small focused components rather than one untestable client method.

The components should remain concrete and minimal; do not add speculative interfaces when UOW-001 ports already cover external boundaries.

### NFR-MAINT-003. Baseline Inheritance

UOW-002 follows the baseline scraper pattern:

- Job-scoped HTTP lifecycle
- adapter-neutral core
- no automatic CAPTCHA bypass
- safe logging
- deterministic offline tests

FMKorea-specific differences are limited to response marker classification refinements discovered in later parser/search fixture work.

## Testing Requirements

### NFR-TEST-001. Example-Based Tests

UOW-002 must include example tests for:

- GET success with `httpx.MockTransport`
- POST success with `httpx.MockTransport`
- media download success with separate timeout
- retry for 429 and 5xx
- retry for network exception/timeout
- no retry for CAPTCHA/block/not found/login required
- static cookie header attached only when enabled
- proxy config masking
- safe log event excludes query/cookie/proxy secret/body
- import side-effect safety

### NFR-TEST-002. Property-Based Tests

UOW-002 must include Hypothesis tests for:

- User-Agent rotation every N outbound attempts
- retry predicate classification
- bounded exponential backoff
- proxy string masking
- safe log URL sanitization
- response classification invariants

PBT mapping:

- PBT-02: URL/log sanitization normalization may use round-trip or parser/formatter properties where implemented
- PBT-03: retry/backoff/classification invariants
- PBT-04: safe log sanitization and secret masking idempotence
- PBT-07: domain-specific generators for URLs, statuses, response kinds, and proxy configs
- PBT-08: shrinking and reproducibility required
- PBT-09: Hypothesis remains selected
- PBT-10: PBT complements example-based MockTransport tests

### NFR-TEST-003. Default Tests Do Not Use Live Network

Default tests must not make live FMKorea requests.

Live smoke tests are deferred to UOW-008 opt-in harnesses.

## Extension Compliance Summary

### Security Baseline

| Rule | Status | Rationale |
|---|---|---|
| SECURITY-01 | N/A | No persistent data store is created in UOW-002 |
| SECURITY-02 | N/A | No load balancer, gateway, or CDN is created |
| SECURITY-03 | Compliant | Safe structured log requirements exclude secrets |
| SECURITY-04 | N/A | No HTML-serving endpoint is implemented |
| SECURITY-05 | Compliant | Runtime config comes from UOW-001 validated models |
| SECURITY-06 | N/A | No IAM policy is created |
| SECURITY-07 | N/A | No network infrastructure is created |
| SECURITY-08 | N/A | No authenticated application endpoint exists |
| SECURITY-09 | Compliant | Error/log output must not expose internals or secrets |
| SECURITY-10 | Compliant | Dependency surface minimized to httpx plus existing test stack; lock/scanning required downstream |
| SECURITY-11 | Compliant | Rate limiting and misuse cases are explicit |
| SECURITY-12 | Compliant | Secret handling forbids hardcoded/logged credentials |
| SECURITY-13 | Compliant | No unsafe deserialization; response body handling is bounded |
| SECURITY-14 | N/A | Alerting backend is later adapter/infra scope |
| SECURITY-15 | Compliant | Timeouts, cleanup, and fail-closed classification are required |

### Resiliency Baseline

| Rule | Status | Rationale |
|---|---|---|
| RESILIENCY-01 | N/A | UOW-002 is a library/runtime unit, not deployable alone |
| RESILIENCY-02 | N/A | RTO/RPO belongs to deployable runtime/infrastructure stages |
| RESILIENCY-03 | N/A | Change process is project-level, not HTTP policy-specific |
| RESILIENCY-04 | N/A | Deployment automation is not in this unit |
| RESILIENCY-05 | Compliant | Structured event contract supports later centralized observability |
| RESILIENCY-06 | N/A | No service health endpoint exists in this unit |
| RESILIENCY-07 | N/A | No deployed capacity/scaling resource exists |
| RESILIENCY-08 | N/A | No deployment topology is defined |
| RESILIENCY-09 | N/A | No compute scaling resource is defined |
| RESILIENCY-10 | Compliant | Explicit timeout, retry, pool bounds, and rate limiter are required |
| RESILIENCY-11 | N/A | No persistent state or DR strategy in this unit |
| RESILIENCY-12 | N/A | No backup resource in this unit |
| RESILIENCY-13 | N/A | Failover runbooks are infrastructure/operations scope |
| RESILIENCY-14 | N/A | Chaos/DR tests are not meaningful for this library unit |
| RESILIENCY-15 | Compliant | Safe failure classification and incident-friendly logs are required |

### Property-Based Testing

| Rule | Status | Rationale |
|---|---|---|
| PBT-01 | Compliant | Functional Design identified HTTP policy properties |
| PBT-02 | Compliant | URL/log sanitizer properties apply where implemented |
| PBT-03 | Compliant | Retry/backoff/classification invariants required |
| PBT-04 | Compliant | Masking and safe log sanitization idempotence required |
| PBT-05 | N/A | No separate oracle implementation is required |
| PBT-06 | N/A | Stateful PBT is not required beyond simple provider counters |
| PBT-07 | Compliant | Domain-specific generators required |
| PBT-08 | Compliant | Hypothesis shrinking and reproducibility required |
| PBT-09 | Compliant | Hypothesis selected |
| PBT-10 | Compliant | PBT complements example-based MockTransport tests |
