# NFR Design Patterns - UOW-011 Scrapling Runtime Refactor

This document translates UOW-011 NFR requirements into implementation patterns.

## Confirmed Design Answers

| Question | Answer | Design Pattern |
|---|---|---|
| Q1 | A | Put an `asyncio.Lock` on each `HttpClient` instance and guard `_render_with_browser()`. |
| Q2 | A | Wait for the instance lock; use the existing browser fetch timeout only after fallback starts. |
| Q3 | A | Keep `HttpResponse` unchanged and rely on safe `browser_fallback_start/end` logs. |
| Q4 | A | Keep one `BrowserFallbackError` and distinguish causes through safe `details.reason`. |
| Q5 | A | Do not add raw HTML/header/screenshot dump features. |
| Q6 | A | Verify serialization with fake async browser fetcher tests, not default Chromium tests. |
| Q7 | A | Start Spider PoC/planning only after UOW-011 Build/Test approval as a separate UOW-012. |

No follow-up question is required.

## Browser Fallback Serialization Pattern

`HttpClient` owns the browser fallback concurrency guard.

Implementation shape:

```text
HttpClient.__init__
  -> self._browser_fallback_lock = asyncio.Lock()

HttpClient.get(required_selector=...)
  -> HTTP success
  -> required selector missing
  -> _render_with_browser(...)

HttpClient._render_with_browser(...)
  -> async with self._browser_fallback_lock
  -> run DynamicFetcher or injected fake browser_fetcher
  -> validate required selector again
```

Rules:

- The lock is per `HttpClient` instance, not process-global.
- Separate worker containers keep independent fallback execution.
- One Job container normally shares one `HttpClient`, so one container runs at most one browser fallback at a time.
- No `browser_fallback_workers` or browser semaphore config is added.

## Lock Wait Pattern

Fallback requests wait for the instance lock.

Rules:

- Lock wait has no separate timeout.
- Existing task cancellation must still propagate.
- Actual browser fetch timeout reuses `HttpRuntimeConfig.timeout.read_seconds`.
- Request interval policy still applies before fallback starts.
- Retry policy is not used to loop browser fallback failures.

This keeps the runtime small and avoids a second timeout model.

## Response Metadata Pattern

`HttpResponse` stays unchanged.

Rules:

- No `rendered_by_browser` field is added.
- No JSONL post metadata is added only to mark fallback use.
- Safe logs remain the source of fallback observability:
  - `browser_fallback_start`
  - `browser_fallback_end`

The parser and storage layers continue to receive HTML response text without knowing how it was obtained.

## Error Pattern

Fallback failures use the existing `BrowserFallbackError`.

Safe reasons:

- `browser_dependency_missing`
- `required_selector_missing`
- browser runtime exception class name

Rules:

- Do not add new exception classes for UOW-011.
- Do not convert fallback failures into `NetworkFailureError`.
- Keep `BrowserFallbackError.retryable` false by default.
- Existing runner stop-reason mapping handles terminal checkpoint behavior.

## Safe Debug Pattern

Default debugging remains safe-log only.

Rejected by default:

- raw HTML snapshots
- rendered DOM dumps
- screenshots
- request or response headers
- cookies
- proxy credentials
- environment dumps

If live analysis is needed, it stays outside default execution through opt-in smoke testing or manually curated fixtures.

## Verification Pattern

Default tests use deterministic local doubles.

Required checks:

- missing required DOM invokes fallback when enabled
- confirmed CAPTCHA/block responses never invoke fallback
- fallback result is revalidated against the same required selector
- fallback failure raises `BrowserFallbackError`
- concurrent fallback calls on one `HttpClient` are serialized
- CLI/Docker default fallback settings remain covered

Preferred serialization test:

```text
fake browser_fetcher:
  increment active counter
  assert active counter never exceeds 1
  await short sleep/barrier
  decrement counter
```

Real Chromium, Docker, and live site smoke tests remain outside the default gate unless a release or runtime/dependency change needs them.

## External Orchestration Pattern

The scraper remains a one-shot worker.

Rules:

- No RabbitMQ consumer in this repository.
- No ack/nack, lease, DLQ, scheduler, or autoscaler code in this repository.
- Future external orchestrator converts Job Queue messages into `JobConfig`/env/argv and starts worker containers.
- UOW-011 must preserve stable `JobConfig`, checkpoint, and report contracts for that future platform.

## Spider PoC Boundary Pattern

Spider is not part of UOW-011 implementation.

The next Spider work starts only after UOW-011 Build/Test approval:

```text
UOW-011 Build/Test approved
  -> UOW-012 Scrapling Spider PoC/planning
  -> Functional Design questions
  -> NFR Requirements/Design
  -> Infrastructure Design if needed
  -> Code Generation only after approval
```

The Spider UOW must explicitly map:

- request scheduling
- checkpoint timing
- failure record creation
- parser retry compatibility
- worker lifecycle
- one-shot container behavior

## Compliance Check

| Requirement Area | Design Compliance |
|---|---|
| Security | no bypass/stealth, no raw debug dumps, safe logs only |
| Resiliency | terminal fallback failure, checkpoint via runner, non-retryable fallback errors |
| Performance | HTTP-first path, per-client fallback serialization, existing timeout reuse |
| Maintainability | no new response fields, no selector config surface, one fallback error type |
| Verification | fake async fallback tests in default gate, Docker/Chromium/live as opt-in |
| Platform boundary | external queue ownership, stable one-shot worker contract |
