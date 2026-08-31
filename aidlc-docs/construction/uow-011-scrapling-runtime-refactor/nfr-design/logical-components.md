# Logical Components - UOW-011 Scrapling Runtime Refactor

This document defines logical components for the UOW-011 implementation.

## Component Overview

| Component | Responsibility |
|---|---|
| `HttpClient` | Owns HTTP-first request flow and browser fallback dispatch. |
| `BrowserFallbackLock` | Per-`HttpClient` `asyncio.Lock` that serializes fallback execution. |
| `RequiredDomSelectorMapping` | Code constants defining required DOM selectors for list/search/detail pages. |
| `DynamicFetcherBridge` | Thin call boundary to Scrapling `DynamicFetcher.async_fetch`. |
| `BrowserFallbackError` | Existing terminal fallback failure type with safe reason details. |
| `SafeHttpEventBuilder` | Builds redacted HTTP/fallback log fields. |
| `RuntimeConfigBuilders` | CLI/Docker builders that decide fallback defaults and disable switches. |
| `FallbackVerificationTests` | Fake-fetcher tests for fallback trigger, block safety, and serialization. |
| `ExternalOrchestratorBoundary` | Future platform boundary for Job Queue consumption. |
| `FutureSpiderPoCPlan` | Separate post-UOW-011 planning path for Scrapling Spider. |

## `HttpClient`

Location:

- `src/fmkorea_scraper/http/runtime.py`

Responsibilities:

- execute the normal `httpx.AsyncClient` request path
- classify HTTP responses before any fallback decision
- inspect required DOM selectors on successful responses
- dispatch browser fallback only when enabled and required DOM is missing
- close the client on terminal CAPTCHA/block/fallback failures

Must not:

- run browser fallback for confirmed CAPTCHA or blocked responses
- persist cookies
- write parser/storage/checkpoint data directly
- expose raw headers or HTML in logs

## `BrowserFallbackLock`

Location:

- internal field on `HttpClient`

Responsibilities:

- serialize `_render_with_browser()` per `HttpClient` instance
- allow multiple containers to remain independent
- avoid global process locks and user-facing concurrency settings

Behavior:

```text
async with self._browser_fallback_lock:
  render with browser
  classify rendered response
  validate required selector
```

Cancellation must propagate normally through the lock wait and render call.

## `RequiredDomSelectorMapping`

Location:

- `src/fmkorea_scraper/collect/parsers.py`
- imported by collection service and public API helpers

Current selectors:

- board list/search: `div.bd`
- integrated search: `.searchResult, .search_result`
- post detail: `#bd_capture`

Rules:

- selectors are code constants
- no CLI/env override is added
- fixture regression tests must fail when selector contracts break

## `DynamicFetcherBridge`

Location:

- `HttpClient._dynamic_browser_fetch`

Responsibilities:

- import `scrapling.fetchers.DynamicFetcher` lazily
- pass `headless=True`, `google_search=False`, `load_dom=True`
- pass `wait_selector=required_selector`
- pass timeout from `HttpRuntimeConfig.timeout.read_seconds`
- pass caller headers and resolved proxy when present

Failure handling:

- missing dependency becomes `BrowserFallbackError` with `browser_dependency_missing`
- unexpected runtime failures become `BrowserFallbackError` with the exception class name as safe reason

## `BrowserFallbackError`

Location:

- `src/fmkorea_scraper/core/errors.py`

Responsibilities:

- represent browser fallback dependency, runtime, and required-DOM failures
- remain non-retryable by default
- feed existing runner stop reason and terminal checkpoint behavior

No child exception hierarchy is required for UOW-011.

## `SafeHttpEventBuilder`

Location:

- `src/fmkorea_scraper/http/runtime.py`

Responsibilities:

- redact URLs by dropping query strings
- include safe proxy labels only
- drop headers, body, content, cookies, passwords, and raw env fields
- emit fallback events with safe fields only

Fallback logs:

- `browser_fallback_start`
- `browser_fallback_end`

No raw debug artifacts are emitted by default.

## `RuntimeConfigBuilders`

Locations:

- `src/fmkorea_scraper/adapters/cli.py`
- `src/fmkorea_scraper/adapters/container.py`

Responsibilities:

- keep CLI/Docker browser fallback enabled by default
- support CLI `--no-browser-fallback`
- support Docker `FMKOREA_BROWSER_FALLBACK=false`
- keep `HttpRuntimeConfig` library default explicit and backward-compatible
- keep browser dependencies optional outside Docker

## `FallbackVerificationTests`

Location:

- `tests/test_http_runtime.py`
- adapter tests under `tests/test_cli_adapter.py` and `tests/test_container_adapter.py`

Responsibilities:

- test fallback trigger using fake HTTP responses and fake browser fetcher
- test block/CAPTCHA responses do not call browser fetcher
- test missing required DOM after fallback is terminal
- test per-client fallback serialization with an async counter/barrier
- test CLI/Docker default and disable behavior

Default tests must not require a live browser.

## `ExternalOrchestratorBoundary`

Responsibilities:

- define what this scraper does not own
- preserve one-shot worker assumptions for the future platform

Out of scope here:

- RabbitMQ consumer
- queue ack/nack
- DLQ
- job lease
- autoscaling
- central scheduler

The future platform starts containers with `JobConfig` inputs and reads checkpoint/report outputs.

## `FutureSpiderPoCPlan`

Responsibility:

- record that Spider work starts as UOW-012 after UOW-011 Build/Test approval

Rules:

- no Spider code is added in UOW-011
- UOW-012 starts with Functional Design questions
- Spider is treated as a runner/checkpoint/failure lifecycle change
- current `JobRunner` remains authoritative until that separate UOW is approved
