# Tech Stack Decisions - UOW-011 Scrapling Runtime Refactor

## Accepted Stack

| Area | Decision | Reason |
| --- | --- | --- |
| Static parser runtime | Scrapling `Selector` | Replaces BeautifulSoup while keeping parser code local and fixture-testable. |
| Normal HTTP runtime | `httpx.AsyncClient` | Preserves the existing async request, retry, proxy, timeout, and User-Agent policy. |
| Browser fallback runtime | Scrapling `DynamicFetcher` with general Playwright | Handles required DOM absence without adding stealth or bypass behavior. |
| Browser timeout | Reuse `HttpRuntimeConfig.timeout.read_seconds` | Avoids a second timeout setting for an exception path. |
| Browser concurrency | Serialize fallback inside `HttpClient` | Prevents multiple Chromium fallbacks from running concurrently in one worker process. |
| Browser dependency packaging | Optional `browser` extra plus Docker worker inclusion | Keeps library installs light while making the worker image operationally ready. |
| Required selector storage | Code constants plus fixture regression tests | Keeps parser contracts reviewable and avoids user-side selector misconfiguration. |
| Safe logging | Existing redacted structured logging | Prevents raw HTML, headers, cookies, proxy secrets, and env dumps from leaking. |
| Default verification | `pytest`, `compileall`, `pip check`, fixture/fake fallback tests | Fast enough for default use and stable without live network dependency. |
| Docker verification | Release/runtime-change smoke | Validates browser packaging when it matters without slowing every local run. |
| Live verification | Opt-in live smoke only | Remote site behavior is unstable and should not be a default gate. |
| Job Queue integration | External orchestrator boundary | Queue consume/ack/nack/DLQ/autoscaling belongs to the future platform, not this scraper. |
| Spider migration | Next separate UOW PoC/planning | User selected early Spider PoC, but it remains outside UOW-011 implementation. |

## Deferred Or Rejected Choices

| Choice | Status | Reason |
| --- | --- | --- |
| CAPTCHA bypass | Rejected | Conflicts with fail-closed security requirements. |
| Stealth or anti-detect browser mode | Rejected | User already chose general Playwright fallback, not stealth. |
| Browser fallback for confirmed blocks | Rejected | Would act like bypass behavior and weaken checkpoint safety. |
| Browser-specific timeout option | Rejected for UOW-011 | Existing HTTP read timeout is enough. |
| Browser fallback worker-count option | Rejected for UOW-011 | One-at-a-time fallback is simpler and safer. |
| Raw HTML/header/screenshot debug artifacts | Rejected by default | Too easy to leak cookies, proxy data, or security pages. |
| Required selector CLI/env override | Rejected | Selector contracts should change through code review and tests. |
| Internal RabbitMQ consumer | Rejected | Queue lifecycle belongs to the external orchestration platform. |
| Scrapling Spider implementation in UOW-011 | Deferred | It changes the execution engine and needs its own UOW. |

## Implementation Impact For Later Stages

- UOW-011 Code Generation must add an `HttpClient` browser fallback lock or equivalent one-at-a-time guard.
- UOW-011 Code Generation must keep `DynamicFetcher` timeout wired to `timeout.read_seconds`.
- UOW-011 Code Generation must preserve `BrowserFallbackError` as non-retryable by default.
- UOW-011 Code Generation must keep browser dependencies optional for base installs and included in the Docker worker image.
- After UOW-011 completion, the next new UOW should cover Scrapling Spider PoC/planning if the user continues in that direction.
