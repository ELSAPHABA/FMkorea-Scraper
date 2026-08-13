# Logical Components - UOW-002 HTTP Runtime Policy

## Component Overview

UOW-002 introduces concrete HTTP runtime components under `fmkorea_scraper.http`. They implement policy around the UOW-001 `HttpPort`, `ClockPort`, and `LoggerPort` boundaries.

## Component Map

| Component | Module | Responsibility |
|---|---|---|
| `HttpClient` | `http/client.py` | job-scoped async HTTP request execution |
| `HttpClientConfig` | `http/config.py` | derived timeout, pool, retry, and request config |
| `HttpRequest` | `http/config.py` | internal request value object |
| `HttpResponse` | `http/config.py` | classified response value object |
| `RateLimiter` | `http/rate_limit.py` | shared Job-scoped request interval enforcement |
| `RetryPolicy` | `http/retry.py` | retry predicate and backoff calculation |
| `UserAgentProvider` | `http/user_agent.py` | file/default based sequential UA rotation |
| `ProxyProvider` | `http/proxy.py` | explicit/env proxy config conversion |
| `ProxyConfig` | `http/proxy.py` | masked proxy settings |
| `ResponseClassifier` | `http/classify.py` | status/header/body-sample classification |
| `HttpLogEvent` | `http/logging.py` | safe structured request attempt event |
| `sanitize_url_for_log` | `http/logging.py` | host/path extraction without query |
| `AsyncioClock` | `http/rate_limit.py` or `core` support module | default `ClockPort` implementation |

## Dependency Direction

```text
HttpClient
  -> HttpClientConfig
  -> RateLimiter
  -> RetryPolicy
  -> UserAgentProvider
  -> ProxyProvider / ProxyConfig
  -> ResponseClassifier
  -> HttpLogEvent builder
  -> httpx.AsyncClient
  -> ClockPort
  -> LoggerPort
```

Rules:

- downstream search/parser code depends on `HttpClient`, not raw httpx
- provider components do not depend on search/parser/storage/job runner modules
- adapters pass env/file paths into factory methods but do not duplicate policy logic

## HttpClient

### Public Methods

| Method | Input | Output | Notes |
|---|---|---|---|
| `from_job_config` | `JobConfig`, env mapping, logger, clock, optional transport | `HttpClient` | factory for job-scoped client |
| `get` | `url`, optional headers, request kind | `HttpResponse` | page/comment request path |
| `post` | `url`, data, optional headers, request kind | `HttpResponse` | future form/ajax support |
| `download` | `url`, optional headers | `HttpResponse` | returns bytes in `content` |
| `close` | none | `None` | closes underlying `httpx.AsyncClient` |

### Internal Flow

1. Build request headers.
2. Apply User-Agent.
3. Wait on `RateLimiter`.
4. Send with `httpx.AsyncClient`.
5. Keep server-set cookies only in the current client memory.
6. Classify response or exception.
7. Emit safe log event.
8. Retry if `RetryPolicy` allows.
9. Return final `HttpResponse`.

## HttpClientConfig

### Fields

- `page_timeout_seconds`
- `media_timeout_seconds`
- `max_connections`
- `max_keepalive_connections`
- `max_attempts`
- `base_backoff_seconds`
- `max_backoff_seconds`
- `jitter_seconds`
- `body_sample_bytes`

### Derived Defaults

| Field | Default |
|---|---|
| `page_timeout_seconds` | adapter-provided `HttpRuntimeConfig.timeout`, default 30 |
| `media_timeout_seconds` | 120 |
| `max_connections` | `post_worker_count + media_worker_count + 2` |
| `max_keepalive_connections` | `max(1, max_connections)` |
| `max_attempts` | 3 |
| `base_backoff_seconds` | 1 |
| `max_backoff_seconds` | 30 |

## RateLimiter

### Fields

- `interval_seconds`
- `last_request_at`
- `lock`
- `clock`

### Behavior

- serializes request timing within one Job process
- sleeps through injected `ClockPort`
- allows zero interval without special-case bypass outside the component

## RetryPolicy

### Fields

- `max_attempts`
- `base_backoff_seconds`
- `max_backoff_seconds`
- `jitter_seconds`
- `retry_kinds`

### Methods

- `should_retry(kind, status_code, error, attempt)`
- `backoff_seconds(attempt)`

### Invariants

- backoff is never negative
- backoff is never above max
- CAPTCHA/block/not-found/login-required are never retryable
- attempt count never exceeds max attempts

## UserAgentProvider

### Construction

- `from_lines(lines, rotate_every, default_user_agent)`
- `from_file(path, rotate_every, default_user_agent)`

### Methods

- `next_user_agent()`

### Invariants

- provider always has at least one UA
- blank lines are ignored
- rotation is deterministic
- retry attempts count as request attempts

## ProxyProvider And ProxyConfig

### ProxyProvider Methods

- `from_options_or_env(options, env, enabled, prefix)`
- `to_httpx_proxy(proxy_config)`

### ProxyConfig Fields

- `host`
- `username`
- `password`
- `scheme`

### Safety

- `password` is masked
- safe dict omits or masks credentials
- raw proxy URL with credentials is not logged

## In-Memory Cookie Lifecycle

Rules:

- user-provided cookie files are not supported
- static `Cookie` headers are not injected
- server-set cookies may stay only in the current `httpx.AsyncClient` memory
- User-Agent rotation clears the in-memory cookie jar
- closing `HttpClient` drops temporary cookies

## ResponseClassifier

### Inputs

- status code
- headers
- bounded body sample
- final URL
- optional transport exception

### Outputs

- UOW-001 `ResponseKind`

### Marker Configuration

- default generic markers are built in
- FMKorea marker list can be configured and expanded later from fixtures
- body sample length is bounded by `HttpClientConfig.body_sample_bytes`

## HttpLogEvent

### Fields

- `method`
- `host`
- `path`
- `status_code`
- `kind`
- `attempt`
- `elapsed_seconds`
- `request_kind`

### Exclusions

- query string
- fragment
- headers containing secrets
- body
- proxy credentials

## Test Components

Test-only components live under `tests/`, not production code.

| Test Component | Purpose |
|---|---|
| `FakeClock` | deterministic rate limiter and backoff tests |
| `FakeLogger` | capture safe log events |
| `httpx.MockTransport` handlers | deterministic HTTP responses and exceptions |
| Hypothesis strategies | URLs, statuses, proxy configs, UA lists, response kinds |

## Integration Points

### UOW-003 Search And Link Collection

Consumes:

- `HttpClient.get`
- `HttpResponse.text`
- `HttpResponse.kind`

### UOW-004 Post Detail And Content Parsing

Consumes:

- `HttpClient.get`
- `HttpClient.download`
- classified responses for detail/comment/media requests

### UOW-005 Job Runner And Checkpoint

Consumes:

- `ResponseKind.CAPTCHA`
- `ResponseKind.BLOCKED`
- `ResponseKind.RATE_LIMITED`
- network failure categories

UOW-005 decides whether to stop, checkpoint, or continue.

### UOW-007 CLI Adapter

Provides:

- User-Agent file path
- proxy explicit values
- timeout/retry/rate-limit options

### UOW-008 Container And MCP

Provides:

- env mapping
- optional transport/smoke harness configuration
- production logger implementation

## Excluded Components

UOW-002 does not create:

- circuit breaker
- queue worker pool
- storage adapter
- checkpoint store
- parser failure retry unit
- CLI prompt/wizard
- Docker entrypoint
- MCP server
- cloud metric backend

These exclusions keep the HTTP runtime focused and compatible with the inherited scraper architecture.
