# Domain Entities - UOW-002 HTTP Runtime Policy

## Entity Overview

UOW-002 defines runtime HTTP policy entities for the FMKorea scraper. It inherits the baseline scraper boundary: all external requests go through one job-scoped HTTP client policy layer, while URL generation, HTML parsing, storage, checkpoint persistence, CLI prompts, container entrypoints, and MCP wrappers stay outside this unit.

## Core Runtime Entities

### HttpClient

Represents the job-scoped async HTTP client.

Responsibilities:

- own one `httpx.AsyncClient` per Job execution
- apply rate limiting before every external request
- apply User-Agent headers
- apply optional static cookie header
- apply proxy config
- apply timeout and retry policy
- return classified `HttpResponse` values
- close the underlying async client at Job end

Relationships:

- uses `RateLimiter`
- uses `RetryPolicy`
- uses `UserAgentProvider`
- uses `ProxyProvider`
- uses `CookieProvider`
- emits safe log events through `LoggerPort`
- uses `ClockPort` for sleeps and elapsed timing

### HttpRequest

Internal value object representing a single outbound request.

Fields:

- `method: Literal["GET", "POST"]`
- `url: str`
- `headers: Mapping[str, str]`
- `data: Mapping[str, Any] | bytes | None`
- `timeout_seconds: float`
- `request_kind: Literal["page", "comment", "media", "other"]`
- `metadata: dict[str, Any]`

Rules:

- `url` is used for the actual request.
- safe logging must derive host/path from `url` and omit raw query values.
- cookie/proxy secrets must not be stored in metadata.

### HttpResponse

Internal value object returned by `HttpClient`.

Fields:

- `status_code: int | None`
- `headers: Mapping[str, str]`
- `text: str | None`
- `content: bytes | None`
- `final_url: str`
- `kind: ResponseKind`
- `elapsed_seconds: float | None`
- `attempt_count: int`
- `metadata: dict[str, Any]`

Rules:

- page/comment requests normally populate `text`.
- media download requests normally populate `content`.
- `kind` is always set by response classification.
- raw `httpx.Response` is not exposed to parser or collector code.

## Policy Entities

### RateLimiter

Job-scoped async limiter used by all workers in the same Job.

Fields:

- `interval_seconds: float`
- `last_request_at: datetime | None`
- `metadata: dict[str, Any]`

Rules:

- applied before every external request
- shared by list/search/detail/comment/media requests
- shared by all workers within one Job process
- does not coordinate across containers or processes

### RetryPolicy

Defines retry eligibility and wait calculation.

Fields:

- `max_attempts: int`
- `base_backoff_seconds: float`
- `max_backoff_seconds: float`
- `jitter_seconds: float`
- `retry_status_codes: set[int]`
- `retry_response_kinds: set[ResponseKind]`
- `metadata: dict[str, Any]`

Default retry targets:

- network failure
- timeout
- HTTP 5xx
- HTTP 429

Non-retry targets:

- CAPTCHA
- blocked response
- 404/not found
- login required
- deleted/private/unavailable content

### ResponseClassifier

Classifies raw HTTP outcomes into `ResponseKind`.

Inputs:

- `status_code`
- response headers
- response body text when available
- final URL
- transport exception type when no response exists

Outputs:

- `ResponseKind.OK`
- `ResponseKind.CAPTCHA`
- `ResponseKind.BLOCKED`
- `ResponseKind.NOT_FOUND`
- `ResponseKind.LOGIN_REQUIRED`
- `ResponseKind.RATE_LIMITED`
- `ResponseKind.SERVER_ERROR`
- `ResponseKind.NETWORK_ERROR`

Rules:

- classification is policy-level detection, not CAPTCHA bypass.
- checkpoint and stop handling belongs to UOW-005.
- parser-specific unavailable-detail classification can refine the result in UOW-004.

### UserAgentProvider

Job-scoped User-Agent selector.

Fields:

- `user_agents: list[str]`
- `rotate_every: int`
- `request_count: int`
- `current_index: int`
- `default_user_agent: str`
- `metadata: dict[str, Any]`

Rules:

- loads valid non-empty lines from a provided `user-agents.txt` path when adapter supplies one
- falls back to exactly one default User-Agent when no valid file entries exist
- rotates sequentially every `rotate_every` outbound attempts
- counts retry attempts because they are real external requests
- shares the counter across all workers in one Job process

### ProxyProvider

Pure provider that converts explicit options or environment mapping into an HTTP client proxy config.

Inputs:

- explicit proxy host/url
- explicit proxy ID
- explicit proxy password
- environment mapping using `FMKOREA_PROXY_*` or configured prefix

Outputs:

- `ProxyConfig | None`

Rules:

- explicit option has priority over env mapping
- no proxy is used when neither explicit option nor env mapping provides a host
- UOW-002 does not create or edit `.env`
- raw proxy password is never logged, persisted, or exposed in `ErrorResult.details`

### ProxyConfig

Fields:

- `host: str`
- `username: str | None`
- `password: SecretStr | None`
- `scheme: Literal["http", "https", "socks5"] | None`
- `metadata: dict[str, Any]`

Rules:

- may be transformed to httpx proxy configuration
- string representation must mask password

### CookieProvider

Optional static cookie header provider.

Fields:

- `cookie_header: str | None`
- `source_path: str | None`
- `metadata: dict[str, Any]`

Rules:

- disabled by default
- used only when adapter provides an explicit cookie file path
- reads a static cookie header for request headers
- does not persist `Set-Cookie`
- does not maintain a mutable cookie jar across requests
- raw cookie is never logged or persisted

## Log Entity

### HttpLogEvent

Safe structured log data for one request attempt.

Fields:

- `method: str`
- `host: str`
- `path: str`
- `status_code: int | None`
- `kind: ResponseKind`
- `attempt: int`
- `elapsed_seconds: float | None`
- `request_kind: str`

Excluded fields:

- raw query string
- Cookie
- Authorization
- Proxy-Authorization
- proxy password
- `.env` values
- full response body

## Boundary Entities From UOW-001

UOW-002 consumes these existing UOW-001 contracts:

- `ScrapeOptions`
- `ResponseKind`
- `NetworkFailureError`
- `BlockedResponseError`
- `CaptchaDetectedError`
- `ErrorResult`
- `HttpPort`
- `ClockPort`
- `LoggerPort`

UOW-002 may add concrete HTTP package models, but persisted source JSONL, checkpoint, failure, and report schemas remain owned by UOW-001/UOW-005/UOW-006.
