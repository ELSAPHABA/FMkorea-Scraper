# NFR Requirements - UOW-011 Scrapling Runtime Refactor

## Purpose

UOW-011 must keep the Scrapling runtime refactor safe, cheap on the normal path, and compatible with the existing one-shot worker architecture.

The normal path remains `httpx` plus Scrapling `Selector`. Browser rendering is an exception path for successful responses that lack required DOM.

## Confirmed Questionnaire Answers

- Q1 Browser Fallback Timeout: A
- Q2 Browser Fallback Concurrency: A
- Q3 Browser Fallback Failure Retryability: A
- Q4 Safe Logging And Debug Artifacts: A
- Q5 Browser Dependency Packaging: A
- Q6 Default Test Gate: A
- Q7 Required Selector Maintenance: A
- Q8 External Job Queue Boundary: A
- Q9 Future Spider Migration Gate: B

## Performance Requirements

- `httpx.AsyncClient` must remain the default request path.
- Scrapling `DynamicFetcher` must run only after a successful HTTP response lacks the required DOM selector.
- Browser fallback timeout must reuse `HttpRuntimeConfig.timeout.read_seconds`.
- Browser fallback must be serialized inside one `HttpClient` process so concurrent post workers cannot launch multiple browser fallbacks at once.
- No separate `--browser-fallback-workers` or browser timeout option is required.
- Existing request interval, retry policy, User-Agent rotation, and proxy settings continue to apply.

## Reliability Requirements

- CAPTCHA, HTTP 430, and clear block responses must fail closed without browser fallback.
- Browser launch failure, browser fetch failure, or required DOM absence after rendering must be terminal for the current Job.
- Terminal browser fallback failure must allow the existing `JobRunner` checkpoint/report flow to record the stopped state.
- Browser fallback failures remain non-retryable by default.
- Parser-failure retry and checkpoint resume may be used by the operator, but UOW-011 must not add automatic fallback retry loops.

## Security Requirements

- No CAPTCHA bypass, stealth mode, anti-detect mode, or block circumvention component is introduced.
- Logs and failure details must remain safe to print and store.
- Raw HTML, rendered DOM dumps, request/response headers, cookies, screenshots, proxy passwords, and environment dumps must not be stored by default.
- Browser fallback must use the same safe logging rules as the HTTP runtime.
- Server-set cookies may exist only in the current in-memory `HttpClient` lifecycle and must not be persisted.

## Packaging Requirements

- Base library installation must include Scrapling parser support without forcing Playwright/Chromium on all users.
- Browser fallback dependencies must remain behind the optional `browser` extra.
- Docker worker images must include the browser extra and Chromium so CLI/Docker fallback works without a second image.
- A separate browser-only image is not required.

## Maintainability Requirements

- Required DOM selectors must stay in code constants with fixture-backed regression tests.
- CLI/env overrides for required selectors are not supported.
- Selector changes are treated as parser contract changes and must be reviewed in code.
- The public CLI, Docker, MCP, and library contracts should remain compatible unless a later UOW explicitly changes them.

## Test Requirements

- Default local gate: full `pytest`, `compileall`, `pip check`, fixture parser tests, and fake browser-fetcher tests.
- Docker build and Chromium smoke should run for releases or runtime/dependency changes.
- Live site smoke remains opt-in because it depends on network state and remote anti-abuse behavior.
- Tests must cover that confirmed CAPTCHA/block responses do not invoke browser fallback.
- Tests must cover that required DOM absence can invoke fallback when enabled.
- UOW-011 Code Generation must add or keep a test proving browser fallback is serialized.

## External Orchestration Requirements

- This repository must remain a one-shot worker.
- RabbitMQ or other Job Queue consume, ack/nack, lease, DLQ, scheduling, and autoscaling are owned by the future external orchestration platform.
- This repository only needs to preserve a stable `JobConfig` input and checkpoint/report output contract for that future platform.

## Future Spider Requirement

- Scrapling Spider is not implemented in UOW-011.
- The next separate UOW should be a Spider PoC/planning unit if the user chooses to continue after UOW-011.
- That future UOW must treat Spider as an execution-engine change, not a parser-only change.
- The Spider UOW must explicitly map request scheduling, checkpoint timing, failure records, retry behavior, and worker lifecycle.

## Acceptance Criteria

- NFR decisions match the approved UOW-011 Functional Design.
- HTTP-first scraping remains the normal path.
- Browser fallback is bounded by existing timeout and one-at-a-time execution.
- Browser fallback does not run for confirmed CAPTCHA/block responses.
- No unsafe raw debug artifacts are emitted by default.
- Base installation stays lightweight while Docker worker remains fallback-ready.
- Queue consumption remains outside this repository.
- Spider work is deferred to the next separate UOW, not mixed into UOW-011 implementation.
