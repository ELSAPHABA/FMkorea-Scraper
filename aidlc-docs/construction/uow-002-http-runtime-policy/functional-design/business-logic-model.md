# Business Logic Model - UOW-002 HTTP Runtime Policy

## Purpose

UOW-002 provides one reusable HTTP runtime policy for every later scraper unit. It follows the baseline scraper structure: centralize network behavior in `HttpClient`, keep parsers pure, keep adapters responsible for terminal/container file flows, and let Job orchestration decide checkpoint behavior.

This unit owns:

- job-scoped async HTTP client lifecycle
- request delay/rate limiting
- retry and backoff policy
- User-Agent rotation
- proxy config conversion
- in-memory server cookie lifecycle
- response classification
- safe HTTP log event shaping

This unit does not own:

- FMKorea URL/query generation
- HTML parsing selectors
- Job queue orchestration
- checkpoint persistence
- JSONL/media storage
- `.env` creation or terminal prompts
- container entrypoint env file generation
- MCP adapter behavior

## Design Decisions

| Area | Decision |
|---|---|
| Client lifecycle | one `HttpClient` per Job execution |
| Rate limiting | one shared Job-scoped async limiter for all external request types |
| Retry target | network error, timeout, 429, 5xx only |
| Backoff | exponential backoff with bounded max and small jitter |
| Response output | classified `HttpResponse` value object |
| CAPTCHA/block | classify only; no bypass and no checkpoint write in HTTP layer |
| User-Agent | sequential rotation every configured outbound attempts, default 10 |
| Proxy | pure provider from explicit options/env mapping to httpx config |
| Cookie | server-set in-memory cookies only; clear on User-Agent rotation and client close |
| Logging | safe method/host/path/status/kind/attempt/elapsed only |
| Tests | `httpx.MockTransport` and fake clock, no live network by default |

## Client Setup Flow

1. Job runner or service receives validated UOW-001 `JobConfig`.
2. Adapter builds `HttpRuntimeConfig` from CLI/env/MCP/library execution inputs.
3. `UserAgentProvider` is created from supplied UA file path or default fallback.
4. `ProxyProvider` receives explicit proxy values or env mapping from adapter and produces `ProxyConfig | None`.
5. `RateLimiter` is created from `request_interval_seconds`.
6. `RetryPolicy` is created from configured retry count and defaults.
7. `HttpClient` opens one `httpx.AsyncClient`.
8. Server-set cookies may live only inside that client instance.
9. All later requests use this same `HttpClient`.
10. Job shutdown closes the client and drops the in-memory cookies.

## Request Execution Flow

For `get`, `post`, and `download`:

1. Build internal `HttpRequest`.
2. Derive safe log labels from method, host, path, and request kind.
3. Wait on Job-scoped `RateLimiter`.
4. Ask `UserAgentProvider` for the current User-Agent.
5. Use the current `httpx.AsyncClient` in-memory cookie jar; do not inject user-provided cookie headers.
6. Send request through `httpx.AsyncClient`.
7. Classify the raw response or transport failure.
8. If retryable and attempts remain, calculate backoff and retry.
9. Return classified `HttpResponse`.
10. Emit safe log event for each attempt.

## Retry Decision Flow

```text
request attempt
  |
  v
transport exception?
  | yes -> kind=network_error -> retry if attempts remain
  | no
  v
status == 429?
  | yes -> kind=rate_limited -> retry if attempts remain
  | no
  v
status >= 500?
  | yes -> kind=server_error -> retry if attempts remain
  | no
  v
captcha/block/login/not_found?
  | yes -> classify and return, no retry
  | no
  v
kind=ok -> return
```

## Response Classification Logic

Classification is intentionally conservative.

Initial mapping:

- `2xx`: `ok`, unless body/final URL indicates CAPTCHA or block
- `404`: `not_found`
- `401` or login-required page marker: `login_required`
- `403`: `blocked`, unless later evidence classifies differently
- `429`: `rate_limited`
- `5xx`: `server_error`
- transport exception or timeout without response: `network_error`

CAPTCHA/block body markers are site-specific and may be refined during UOW-003/UOW-004 fixture work. UOW-002 owns the classifier hook and general output shape.

## User-Agent Rotation Logic

The provider maintains:

- a list of valid UA strings
- `rotate_every`
- total outbound attempt count
- current index

Pseudo-flow:

```text
before request attempt:
  count += 1
  if count > 1 and (count - 1) % rotate_every == 0:
      current_index = (current_index + 1) % len(user_agents)
  return user_agents[current_index]
```

Retry attempts call the same flow.

## Proxy Logic

Adapter layers are responsible for collecting proxy input.

UOW-002 receives:

- explicit proxy values, or
- env mapping values, or
- disabled flag

Decision:

```text
explicit host/url present -> explicit proxy config
env mapping has host/url -> env proxy config
otherwise -> no proxy
```

The resulting config is converted to the format accepted by `httpx.AsyncClient`.

## Cookie Logic

Cookie behavior matches the baseline scraper.

Flow:

1. User-provided cookie files and static `Cookie` headers are not supported.
2. `httpx.AsyncClient` may keep server-set `Set-Cookie` values only in the current client lifecycle.
3. User-Agent rotation clears the in-memory cookie jar before the next request.
4. `HttpClient.close()` drops the in-memory cookie jar.
5. Restart, resume, proxy change, or a new Job never reuses old cookies.
6. Raw cookie values are never written to logs, checkpoints, reports, failure records, or JSONL output.

## Error And Stop Handling

HTTP layer:

- classifies responses
- raises or returns typed network-level failures where appropriate
- does not save checkpoints
- does not decide whether a Job is stopped

Job/service layer:

- sees `ResponseKind.CAPTCHA` or `ResponseKind.BLOCKED`
- maps to stop reason
- saves checkpoint
- writes safe failure/report details

## Testable Properties

Property and example tests should cover:

- User-Agent sequence rotates every N outbound attempts
- retry attempts count toward UA rotation
- rate limiter sleeps before each request after the first as configured
- retry happens for 429/5xx/network/timeout only
- CAPTCHA/block/404/login-required are not retried
- proxy password is masked in string/log/error paths
- server-set cookies stay memory-only inside one `HttpClient` lifecycle
- User-Agent rotation clears the in-memory cookie jar
- `HttpResponse.kind` is always set
- import has no file, network, or terminal side effects

## UOW Integration Points

| Downstream UOW | Uses From UOW-002 |
|---|---|
| UOW-003 Search And Link Collection | `HttpClient.get`, classified page responses, safe network errors |
| UOW-004 Post Detail And Content Parsing | detail/comment/media request methods and response classification |
| UOW-005 Job Runner And Checkpoint | CAPTCHA/block response kinds and network failure categories |
| UOW-007 CLI Adapter | User-Agent/proxy/runtime option values passed into providers |
| UOW-008 Container/MCP/Test Harness | env-provided proxy/runtime config and fake/live smoke harness |

## UOW Exclusions

UOW-002 does not implement:

- board or integrated search URLs
- BeautifulSoup selectors
- parser-stage failure records
- checkpoint save/load
- JSONL output
- media file save paths
- terminal wizard
- Docker entrypoint
- MCP server
