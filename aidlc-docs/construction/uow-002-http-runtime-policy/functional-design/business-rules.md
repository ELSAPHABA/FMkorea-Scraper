# Business Rules - UOW-002 HTTP Runtime Policy

## Client Lifecycle Rules

### BR-001. Job-Scoped Client

One `HttpClient` instance must be created per Job execution.

The client is shared by:

- link collector requests
- post detail worker requests
- comment requests
- media download requests

The client must be closed explicitly when the Job ends.

### BR-002. No Process-Global Client

The HTTP client must not be a process-global singleton.

Reason:

- Job-specific proxy, cookie, timeout, and User-Agent settings must not bleed across jobs.

### BR-003. No Per-Request Client

The implementation must not create a new `httpx.AsyncClient` for every request.

Reason:

- connection pooling and DNS/TLS reuse should work within a Job.

## Rate Limit Rules

### BR-004. Shared Job Rate Limiter

Every external request must pass through one Job-scoped async rate limiter.

Covered request types:

- board/list pages
- board search pages
- integrated search pages
- post detail pages
- comment pages or comment subrequests
- image/video downloads

### BR-005. Worker-Shared Limit

The limiter is shared by all workers in one Job process.

It does not coordinate across:

- separate processes
- separate containers
- future distributed worker pools

### BR-006. Zero Delay Is Allowed

`request_interval_seconds=0` may disable waiting, but the request still goes through the limiter hook.

This keeps tests and future policy extensions consistent.

## Retry Rules

### BR-007. Retryable Conditions

Automatic retry is allowed only for transient failures:

- network exception
- timeout
- HTTP 429
- HTTP 5xx

### BR-008. Non-Retryable Conditions

The client must not automatically retry:

- CAPTCHA
- blocked response
- 404/not found
- login required
- deleted/private/unavailable content

These responses are returned as classified `HttpResponse` values or mapped to typed errors by the caller layer.

### BR-009. Backoff

Retry waits must use exponential backoff with a bounded maximum delay.

A small jitter may be added to avoid exact repeated request timing.

### BR-010. Attempt Counting

Every retry attempt counts as a real outbound request for:

- rate limiting
- User-Agent rotation
- safe log events

## Response Classification Rules

### BR-011. Classified Response Object

`HttpClient` must return a value object with:

- status code
- headers
- response text or bytes
- final URL
- `ResponseKind`
- attempt count
- elapsed time

### BR-012. No Raw httpx Response Leakage

Parser, search, and job code must not depend on raw `httpx.Response`.

Reason:

- callers should consume the stable scraper response contract, not an adapter-specific object.

### BR-013. Classification Does Not Save Checkpoints

UOW-002 only classifies CAPTCHA, block, rate-limit, and unavailable responses.

Checkpoint saving and Job stop behavior belongs to UOW-005.

### BR-014. CAPTCHA Bypass Is Forbidden

The scraper must not attempt automatic CAPTCHA bypass.

When CAPTCHA is detected, the response is classified as `ResponseKind.CAPTCHA`; later job orchestration stops and saves checkpoint.

## User-Agent Rules

### BR-015. User-Agent File Format

User-Agent file format is one User-Agent string per line.

Rules:

- blank lines are ignored
- surrounding whitespace is stripped
- no encoding/encryption layer is added by core

### BR-016. Default User-Agent Fallback

If no User-Agent file is provided, missing, unreadable, or empty after filtering, the provider uses one default User-Agent.

### BR-017. Rotation

User-Agent rotates sequentially after `user_agent_rotate_every` outbound attempts.

Default:

- `user_agent_rotate_every=10`

### BR-018. Job-Scoped Counter

The request counter is shared inside one Job process.

It is not shared across containers.

## Proxy Rules

### BR-019. Proxy Priority

Proxy config source priority:

1. explicit options provided by adapter
2. environment mapping
3. disabled

### BR-020. No `.env` Side Effects

UOW-002 must not create, edit, or automatically discover `.env` files.

CLI and container adapters may read/create `.env` later and pass values into UOW-002.

### BR-021. Proxy Secret Safety

Proxy password and credential-bearing proxy URLs must not be:

- logged
- stored in failure records
- stored in checkpoints
- exposed in adapter-facing error details

## Cookie Rules

### BR-022. Cookie Disabled By Default

Cookie support is disabled unless the user explicitly provides a cookie file path through adapter configuration.

### BR-023. Static Cookie Header Only

When cookie file is used, UOW-002 reads a static cookie header and attaches it to requests.

The client must not:

- store `Set-Cookie`
- mutate the cookie file
- maintain a cookie jar across requests

### BR-024. Cookie Secret Safety

Raw cookie values must never appear in:

- logs
- failure details
- checkpoint metadata
- user-facing error results

## Logging Rules

### BR-025. Safe Request Logging

HTTP log events may include:

- method
- host
- path
- status code
- `ResponseKind`
- attempt
- elapsed time
- request kind

### BR-026. Forbidden Log Fields

HTTP log events must not include:

- raw query string
- Cookie
- Authorization
- Proxy-Authorization
- proxy ID/password
- raw `.env` values
- full response body

## Media Request Rules

### BR-027. Shared Policy For Media

Media downloads use the same:

- `HttpClient`
- rate limiter
- User-Agent provider
- proxy config
- response classification policy

### BR-028. Separate Download Timeout Allowed

Media download timeout may be configured separately from page timeout.

Actual media file persistence belongs to UOW-006.

## Testing Rules

### BR-029. No Live Network In Default Tests

UOW-002 default tests must not call live FMKorea or any external website.

### BR-030. MockTransport And Fake Clock

HTTP policy tests should use:

- `httpx.MockTransport`
- fake clock or fake sleeper
- deterministic retry/backoff inputs

### BR-031. Import Side Effects

Importing the HTTP package must not:

- create an `AsyncClient`
- read `.env`
- read `user-agents.txt`
- read cookie files
- open network sockets
- prompt terminal input
