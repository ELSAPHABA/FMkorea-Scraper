# NFR Design Patterns - UOW-002 HTTP Runtime Policy

## Scope

This document translates UOW-002 NFR requirements into concrete design patterns.

The design follows the baseline scraper structure:

- one job-scoped HTTP client
- adapter-neutral core
- small concrete policy components
- no live network in default tests
- no CAPTCHA bypass
- no storage/checkpoint/CLI/container responsibility in HTTP runtime

## Selected Patterns

| Concern | Pattern |
|---|---|
| Package layout | focused modules under `src/fmkorea_scraper/http/` |
| Client construction | `HttpClient.from_job_config(...)` factory classmethod |
| Time source | `ClockPort` with default `AsyncioClock` and test `FakeClock` |
| Rate limiting | Job-scoped lock-backed async limiter |
| Retry/backoff | pure `RetryPolicy` value object |
| Response classification | status/header baseline plus bounded body marker inspection |
| Secret masking | masked config objects plus log/error allowlist sanitizer |
| Safe logging | URL sanitizer and structured `HttpLogEvent` builder |
| Connection limits | `HttpClientConfig` computes bounded httpx limits |
| Tests | production-free fake clock/logger and `httpx.MockTransport` helpers |
| Circuit breaker | deferred to UOW-005 Job-level stop policy |

## Package Separation Pattern

HTTP runtime code is organized under:

```text
src/fmkorea_scraper/http/
  __init__.py
  client.py
  config.py
  rate_limit.py
  retry.py
  user_agent.py
  proxy.py
  classify.py
  logging.py
```

Pattern rules:

- `client.py` orchestrates request execution only.
- `rate_limit.py`, `retry.py`, `user_agent.py`, `proxy.py`, `classify.py`, and `logging.py` hold focused policy logic.
- `config.py` holds HTTP-runtime value objects such as `HttpClientConfig`, `HttpRequest`, and `HttpResponse`.
- No module reads `.env` or `user-agents.txt` on import.
- No speculative abstract interfaces are added; UOW-001 ports already define external I/O boundaries.

## Client Factory Pattern

`HttpClient` is constructed through a factory classmethod:

```python
HttpClient.from_job_config(
    job_config,
    *,
    env,
    logger,
    clock,
    transport=None,
)
```

Responsibilities:

1. Read adapter-provided `HttpRuntimeConfig`, `ScrapeOptions`, and `WorkerConfig`.
2. Build `HttpClientConfig`.
3. Build `UserAgentProvider`.
4. Build `ProxyConfig` from explicit adapter values or env mapping.
5. Build `RateLimiter`.
6. Build `RetryPolicy`.
7. Build `ResponseClassifier`.
8. Create one `httpx.AsyncClient` with memory-only server cookie behavior.

Rules:

- `transport` exists for tests and is passed to httpx.
- Adapters may pass env mappings; UOW-002 does not discover env files.
- The client is async-closeable and must be closed at Job shutdown.

## Rate Limiter Pattern

`RateLimiter` uses a Job-scoped lock to serialize request timing across concurrent workers.

Behavior:

1. Acquire lock.
2. Compare current clock time with last request time.
3. Sleep for remaining interval if needed.
4. Update last request time.
5. Release lock.

Design constraints:

- `interval_seconds=0` skips waiting but still exercises the same hook.
- Time and sleep come from `ClockPort`.
- Tests use `FakeClock` to avoid real sleeps.
- No cross-container coordination is attempted.

## Retry Policy Pattern

`RetryPolicy` is a pure value object.

Core methods:

- `should_retry(kind, status_code, error, attempt) -> bool`
- `backoff_seconds(attempt) -> float`

Retryable:

- transport network error
- timeout
- `ResponseKind.RATE_LIMITED`
- `ResponseKind.SERVER_ERROR`

Non-retryable:

- `ResponseKind.CAPTCHA`
- `ResponseKind.BLOCKED`
- `ResponseKind.NOT_FOUND`
- `ResponseKind.LOGIN_REQUIRED`
- unavailable/deleted/private content classifications

Pattern benefits:

- retry predicates are testable without network
- backoff bounds are testable with property-based tests
- `HttpClient` stays as execution code, not policy storage

## Response Classification Pattern

`ResponseClassifier` maps raw HTTP outcomes into UOW-001 `ResponseKind`.

Classification order:

1. Transport exception or timeout -> `network_error`
2. Status 429 -> `rate_limited`
3. Status 5xx -> `server_error`
4. Status 404 -> `not_found`
5. Status 401 or login markers -> `login_required`
6. Status 403 or block markers -> `blocked`
7. CAPTCHA markers -> `captcha`
8. Otherwise 2xx/3xx -> `ok`

Body handling:

- only a bounded sample is inspected for marker matching
- body is never logged
- FMKorea marker constants can be refined later from UOW-003/UOW-004 fixtures

## Secret Masking Pattern

Secret-bearing config objects use two layers of protection:

1. Object-level masking with `SecretStr` or equivalent.
2. Log/error output allowlist sanitizer.

Required safe object:

- `ProxyConfig`

Rules:

- `repr(config)` must not expose secret values.
- `to_safe_dict()` returns masked or omitted secret fields.
- proxy passwords, proxy auth URLs, Cookie values, and Authorization values are never emitted to logs/errors.

## Safe Logging Pattern

`logging.py` owns safe event construction.

Functions/value objects:

- `sanitize_url_for_log(url) -> tuple[host, path]`
- `HttpLogEvent`
- `build_http_log_event(...)`

Rules:

- raw query string is dropped structurally
- fragment is dropped
- request/response headers are not logged except safe derived fields
- body is never logged
- attempts, elapsed seconds, status, and `ResponseKind` are retained

PBT invariant:

- sanitized log output must never contain query strings, cookie values, authorization values, or proxy credentials.

## Connection Limit Pattern

`HttpClientConfig` computes httpx connection limits.

Default:

```text
max_connections = post_worker_count + media_worker_count + 2
max_keepalive_connections = max(1, max_connections)
```

Rules:

- explicit override wins when provided by future adapter config
- computed values must be at least 1
- `HttpClient` consumes the computed config only

## Test Harness Pattern

Default tests use:

- `httpx.MockTransport`
- `FakeClock`
- `FakeLogger`
- Hypothesis strategies for URLs, statuses, response kinds, proxy config, and User-Agent lists

Production package must not include test-only fake helpers.

Test coverage expectations:

- example tests pin request success and retry behavior
- PBT tests cover policy invariants
- live network smoke remains deferred to UOW-008 opt-in harness

## Circuit Breaker Deferral

UOW-002 does not implement a circuit breaker.

Reason:

- circuit breaking requires Job-level state and stop/checkpoint decisions
- UOW-005 owns Job runner behavior and repeated failure handling
- UOW-002 already provides timeout, retry, rate limit, and response classification

Future hook:

- UOW-005 may treat repeated `blocked`, `captcha`, `rate_limited`, or network failure classifications as stop/checkpoint conditions.

## Compliance Summary

### Security

- Secrets are masked at config and log/error output boundaries.
- No raw response body, cookie, authorization, query, or proxy credential is logged.
- Import side effects are forbidden.
- CAPTCHA bypass is explicitly excluded.

### Resiliency

- All requests have explicit timeouts.
- Retries are bounded and limited to transient conditions.
- Rate limiting is shared across the Job process.
- Connection pools are bounded by worker count.

### PBT

- Retry/backoff, User-Agent rotation, classifier invariants, safe log sanitization, and proxy masking have identified property-based tests.
