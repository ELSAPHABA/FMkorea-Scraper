# Public Contracts - UOW-002 HTTP Runtime Policy

## Package

UOW-002 exposes import-safe HTTP runtime components from:

- `fmkorea_scraper.http`
- selected convenience exports from `fmkorea_scraper`

Importing these modules must not read files, open network sockets, create an `httpx.AsyncClient`, prompt terminal input, or mutate environment variables.

## Runtime Config

| Contract | Purpose |
|---|---|
| `TimeoutConfig` | connect/read/write/pool timeout conversion to `httpx.Timeout` |
| `RetryPolicy` | max attempts and bounded exponential backoff inputs |
| `UserAgentConfig` | explicit/fallback User-Agent file path and rotation interval |
| `ProxyConfig` | masked proxy host/credential config |
| `HttpRuntimeConfig` | Job-scoped HTTP runtime options |

## Providers And Policy Components

| Contract | Purpose |
|---|---|
| `UserAgentProvider` | loads non-empty User-Agent lines and rotates sequentially |
| `DotenvProxyLoader` | reads `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW` without mutating process env |
| `ProxyProvider` | explicit proxy first, `.env` second, disabled fallback |
| `RequestRateLimiter` | async per-client request spacing |
| `BackoffCalculator` | bounded exponential retry delay |
| `HeaderBuilder` | default/runtime/caller header merge |
| `ResponseClassifier` | classifies success, retryable, CAPTCHA, block, unavailable, and network categories |
| `SafeHttpEventBuilder` | builds safe log fields without query, header, body, cookie, or password leakage |

## HttpClient

`HttpClient` is a Job-scoped async client implementing the UOW-001 `HttpPort` shape.

Public methods:

- `get(url, headers=None, params=None, referer=None)`
- `post(url, data=None, headers=None, referer=None)`
- `download(url, headers=None)`
- `request(method, url, params=None, data=None, headers=None, referer=None)`
- `close()`

Behavior:

- creates one `httpx.AsyncClient` per `HttpClient`
- sets `trust_env=False`
- applies rate limiting before first attempts and retries
- retries network errors, timeouts, 429, and 5xx only
- raises typed scraper errors for CAPTCHA, blocked, unavailable, and exhausted network failures
- closes the underlying client on cancellation or final classified failure

## Secret Boundary

The runtime must not log or expose:

- raw `.env` values
- proxy password
- credential-bearing proxy URL
- raw `Cookie`
- raw `Authorization`
- raw query string
- response body

Safe events may include redacted URL path, status, attempt, response classification, and proxy safe label.
