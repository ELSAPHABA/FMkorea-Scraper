# Code Generation Plan - UOW-011 Scrapling Runtime Refactor

이 문서는 `UOW-011 Scrapling Runtime Refactor` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Created At**: 2026-08-31
- **Plan Approved At**: 2026-08-31
- **Code Generated At**: 2026-08-31
- **Plan Status**: Code Generated - Review Required

## Unit Context

- **Unit**: UOW-011 Scrapling Runtime Refactor
- **Project Type**: Greenfield Python package with an already implemented Scrapling refactor
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`
- **Documentation Location**: `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/code/`
- **Primary Role**: 승인된 UOW-011 질문지에서 남은 코드 델타만 적용한다.
- **Brownfield Rule**: 기존 파일을 제자리에서 수정하며 중복 파일을 만들지 않는다.

## Dependencies

| Dependency | Status |
|---|---|
| UOW-001 Core Models And Config | Implemented and approved |
| UOW-002 HTTP Runtime Policy | Implemented and approved |
| UOW-003 Search And Link Collection | Implemented and approved |
| UOW-004 Post Detail And Content Parsing | Implemented and approved |
| UOW-006 Output And Storage | Implemented and approved |
| UOW-005 Job Runner And Checkpoint | Implemented and approved |
| UOW-007 CLI Adapter | Implemented and approved |
| UOW-008 Container, MCP, And Test Harness | Implemented and approved |
| UOW-009 Parser Failure Retry Reprocessor | Implemented and approved |
| UOW-010 AWS CDK Infrastructure IaC | Implemented and approved |
| UOW-011 Functional Design | Approved |
| UOW-011 NFR Requirements | Approved |
| UOW-011 NFR Design | Approved |
| UOW-011 Infrastructure Design | Approved |

## Scope

UOW-011 Code Generation implements:

- per-`HttpClient` browser fallback serialization with `asyncio.Lock`
- deterministic fake browser-fetcher test proving only one fallback runs at once per `HttpClient`
- verification that CAPTCHA/block responses still do not invoke fallback
- verification that existing CLI/container browser fallback defaults remain unchanged
- code public-contract and summary docs

UOW-011 Code Generation does not implement:

- Scrapling Spider
- RabbitMQ, SQS, DLQ, queue consumer, lease, scheduler, or autoscaler
- stealth mode, CAPTCHA bypass, or anti-detect mode
- fallback-specific storage, metrics, dashboard, or raw debug dump
- new public CLI options for browser worker count or timeout
- infrastructure changes

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| HTTP runtime fallback lock | `src/fmkorea_scraper/http/runtime.py` |
| runtime fallback tests | `tests/test_http_runtime.py` |
| code public contract docs | `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/code/public-contracts.md` |
| code summary docs | `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/code/code-generation-summary.md` |

## Story Traceability

| Story / Requirement | Code Generation Coverage |
|---|---|
| HTTP-first scraping with optional browser fallback | Keep existing `HttpClient.get(required_selector=...)` behavior and verify it remains intact. |
| Safe blocking behavior | Keep CAPTCHA/block classification before fallback and verify fallback is not invoked for blocked responses. |
| One-shot worker compatibility | Keep all fallback execution inside the existing process and `HttpClient` lifecycle. |
| Resource control | Serialize browser fallback per `HttpClient`; do not add new worker-count config. |
| External orchestration boundary | Do not add queue consumer code. |
| Future Spider boundary | Keep Spider out of UOW-011 and leave it for the next separate UOW. |

## Step Sequence

### Step 1. Pre-Generation Guardrails

- [x] Re-read `src/fmkorea_scraper/http/runtime.py` and `tests/test_http_runtime.py`.
- [x] Confirm current code has no RabbitMQ consumer and no Scrapling Spider execution path.
- [x] Confirm existing CLI/container fallback defaults and required selector paths are already present.

### Step 2. HTTP Runtime Fallback Lock

- [x] Add a per-instance `asyncio.Lock` to `HttpClient`.
- [x] Guard browser fallback execution with `async with` that lock.
- [x] Keep `HttpResponse` unchanged.
- [x] Keep `BrowserFallbackError` unchanged.
- [x] Keep browser timeout behavior tied to `HttpRuntimeConfig.timeout.read_seconds`.
- [x] Preserve cancellation propagation and existing client-close behavior on terminal fallback failure.

### Step 3. Runtime Unit Tests

- [x] Add a fake async browser-fetcher test proving concurrent fallback calls on one `HttpClient` are serialized.
- [x] Keep or adjust tests proving blocked/CAPTCHA responses do not invoke browser fallback.
- [x] Keep or adjust tests proving fallback output is revalidated against the required selector.
- [x] Avoid real Chromium in default unit tests.

### Step 4. Adapter And Selector Regression Check

- [x] Confirm CLI fallback default remains enabled unless `--no-browser-fallback` is passed.
- [x] Confirm container fallback default remains enabled unless `FMKOREA_BROWSER_FALLBACK=false`.
- [x] Confirm list/search/detail required selectors still route through `HttpClient.get(..., required_selector=...)`.
- [x] Make only minimal code fixes if any of these checks fail.

### Step 5. Code Documentation

- [x] Create `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/code/code-generation-summary.md`.
- [x] Document that queue, Spider, stealth, and new infra remain out of scope.

### Step 6. Focused Verification

- [x] Run `py -3.12 -m pytest tests/test_http_runtime.py tests/test_cli_adapter.py tests/test_container_adapter.py -q`.
- [x] Run `py -3.12 -m compileall -q src tests`.
- [x] Leave full Docker/live smoke for Build and Test unless the implementation changes packaging behavior.

### Step 7. Workflow State Update

- [x] Mark this plan's generation steps complete after code generation.
- [x] Update `aidlc-docs/aidlc-state.md` to UOW-011 Code Generation Review.
- [x] Append the UOW-011 Code Generation completion record to `aidlc-docs/audit.md`.

## Acceptance Criteria

- Browser fallback is at most one concurrent execution per `HttpClient`.
- Concurrent normal HTTP requests are not globally serialized.
- CAPTCHA/block responses still fail without invoking fallback.
- Fallback result is still checked against the original required selector.
- No new public runtime config is added for browser worker count or fallback timeout.
- No queue, Spider, stealth, debug dump, storage, metric, dashboard, or infrastructure change is introduced.
- Focused verification commands pass before Code Generation review.
