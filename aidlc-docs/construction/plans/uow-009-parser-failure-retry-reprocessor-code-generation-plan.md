# Code Generation Plan - UOW-009 Parser Failure Retry Reprocessor

이 문서는 `UOW-009 Parser Failure Retry Reprocessor` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Created At**: 2026-08-13T12:40:53Z
- **Plan Status**: Code Generated
- **Code Generated At**: 2026-08-13T12:58:22Z

## Unit Context

- **Unit**: UOW-009 Parser Failure Retry Reprocessor
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-008 implementation
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`
- **Documentation Location**: `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/`
- **Primary Stories**: parser-stage failed post retry, CLI/container/MCP retry execution
- **Supporting Stories**: checkpoint/resume, Garage/S3 output, PostgreSQL checkpoint, safe adapter output, optional smoke tests
- **Supporting Role**: 이전 scrape run의 `failures.jsonl`에서 파서 실패 게시글만 선별해 기존 direct-post `JobRunner` 경로로 재수집한다.

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
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-009 implements:

- `src/fmkorea_scraper/retry/parser_failures.py`
- retry package export
- parser-failure selector and summary helpers
- local failure/success JSONL line reader
- S3/Garage failure/success JSONL line reader through existing S3-compatible boundary
- existing success key index
- direct-post retry `JobConfig` assembly
- `ParserFailureRetryService`
- `core.api.retry_parser_failures` default service path
- CLI `retry-parser-failures` execution instead of unsupported placeholder
- MCP `retry_parser_failures` execution instead of unsupported placeholder
- minimal `RetryRequest` fields for explicit existing success input and option restore refs
- `RetryReport.metadata["parser_failure_retry"]` diagnostics
- default local fixture/fake runner tests
- selector property tests
- safe CLI/MCP summary tests
- code public-contract and summary docs

UOW-009 does not implement:

- new Dockerfile or entrypoint
- PostgreSQL staging table
- queue, DLQ, or scheduler
- S3 prefix/output-root auto-discovery
- retry of network/storage/checkpoint/CAPTCHA/block failures
- parser selector changes
- production cloud provisioning or CDK

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| retry package | `src/fmkorea_scraper/retry/__init__.py` |
| retry service and selector | `src/fmkorea_scraper/retry/parser_failures.py` |
| retry request model extension | `src/fmkorea_scraper/models/job.py` |
| retry core API default path | `src/fmkorea_scraper/core/api.py` |
| CLI command wiring | `src/fmkorea_scraper/adapters/cli.py` |
| MCP tool wiring | `src/fmkorea_scraper/adapters/mcp.py` |
| container argv support | `src/fmkorea_scraper/adapters/container.py` |
| unit tests | `tests/test_parser_failure_retry.py` |
| property tests | `tests/test_parser_failure_retry_properties.py` |
| public contract docs | `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/public-contracts.md` |
| code summary docs | `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/code-generation-summary.md` |

## Model Changes

Use existing models first.

Allowed minimal extensions:

- `RetryRequest.existing_success_path: str | None`
- `RetryRequest.from_report_path: str | None`
- `RetryRequest.from_checkpoint_path: str | None`
- `RetryRequest.retry_job_id: str | None`

Rules:

- explicit retry options remain adapter/runtime inputs
- `from_report_path` and `from_checkpoint_path` cannot both be set
- `RetryReport.selected_count` and `RetryReport.skipped_count` keep their current meaning
- additional selector diagnostics go under existing inherited `metadata["parser_failure_retry"]`

No new report schema is generated.

## Step Sequence

### Step 1. Model Contract Updates

- [x] Extend `RetryRequest` with optional existing success and restore ref fields.
- [x] Validate `from_report_path` and `from_checkpoint_path` are not combined.
- [x] Preserve existing `FailureInput`, `DirectPostSource`, `ParserFailureRetrySource`, `RetryReport`, and `PostKey` contracts where possible.
- [x] Add/adjust model tests for the new request fields.

### Step 2. Retry Package And Selector

- [x] Create `src/fmkorea_scraper/retry/__init__.py`.
- [x] Create `src/fmkorea_scraper/retry/parser_failures.py`.
- [x] Add `RetryCandidate` and `RetrySelectionSummary` as small internal dataclasses or models.
- [x] Implement parser failure reason allowlist.
- [x] Implement JSONL line selection with malformed-line counters.
- [x] Include only `stage="post"` parser/metadata/content failures.
- [x] Require usable FMKorea direct post URL.
- [x] Dedupe by `(site_id, board_id, document_srl, document_id_raw)` with last valid duplicate winning.
- [x] Skip existing-success keys when provided.
- [x] Do not store raw invalid lines.

### Step 3. Input Readers

- [x] Implement `FailureInputReader` protocol.
- [x] Implement `LocalFailureInputReader` for local path and `file://`.
- [x] Implement `S3FailureInputReader` for explicit S3/Garage refs.
- [x] Reuse existing S3-compatible config/client boundary.
- [x] Validate all declared inputs before retry Job start.
- [x] Keep source failure and success inputs read-only.
- [x] Keep retry module imports side-effect free.

### Step 4. Existing Success Index

- [x] Stream existing `posts.jsonl` when `existing_success_path` is provided.
- [x] Extract only `(site_id, board_id, document_srl, document_id_raw)` keys.
- [x] Count invalid existing success records.
- [x] Do not load full post bodies into memory.

### Step 5. Retry Job Assembly

- [x] Convert selected candidates into a `DirectPostSource`.
- [x] Build a new `JobConfig(job_type=JobType.DIRECT_POST, source=DirectPostSource(...))`.
- [x] Preserve finalized scrape, worker, and storage config from adapters.
- [x] Call existing `run_job(..., runner=...)` or injected `JobRunner`.
- [x] Return a `RetryReport` with selection counters and metadata diagnostics.
- [x] Preserve existing checkpoint/stop/output behavior.

### Step 6. Core API Wiring

- [x] Update `core.api.retry_parser_failures` to create/use the default `ParserFailureRetryService` when no fake service is supplied.
- [x] Keep fake service injection working for tests.
- [x] Keep import side effects at zero.

### Step 7. CLI Wiring

- [x] Replace `retry-parser-failures is not available until UOW-009` placeholder.
- [x] Add CLI args for `--existing-success-path`, `--from-report`, `--from-checkpoint`, and optional retry job id if needed.
- [x] Reuse existing command normalization and runtime option builders.
- [x] Build finalized retry request/options in adapter layer.
- [x] Print safe summary: `selected`, `skipped`, `stored`, `remaining_failure`, `report`.
- [x] Return exit code `0`, `1`, or `2` consistently.

### Step 8. Container Wiring

- [x] Allow existing container adapter command dispatch to accept `retry-parser-failures`.
- [x] Reuse UOW-008 env/storage dependency construction.
- [x] Do not add a retry-specific entrypoint or Dockerfile.
- [x] Validate S3/Garage env before retry starts when S3 refs are used.

### Step 9. MCP Wiring

- [x] Replace MCP retry placeholder with real `retry_parser_failures` execution.
- [x] Reuse safe error payload handling.
- [x] Return JSON-safe summary fields only.
- [x] Keep MCP runtime optional and import-safe.

### Step 10. Tests

- [x] Add `tests/test_parser_failure_retry.py`.
- [x] Add `tests/test_parser_failure_retry_properties.py`.
- [x] Cover local fixture retry selection.
- [x] Cover malformed line tolerance.
- [x] Cover parser reason allowlist and exclusions.
- [x] Cover duplicate last-wins behavior.
- [x] Cover existing success skip.
- [x] Cover inaccessible input validation.
- [x] Cover fake runner direct-post assembly.
- [x] Cover safe CLI/MCP summary output.
- [x] Cover import side-effect safety.
- [x] Keep S3/Garage, MCP runtime, and live retry smoke optional/skipped by default.

### Step 11. Documentation

- [x] Create `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/code-generation-summary.md`.
- [x] Record generated files, public functions/classes, CLI/MCP contracts, retry input refs, summary output, tests, and deferred boundaries.

### Step 12. Validation

- [x] Run focused UOW-009 tests.
- [x] Run full default test suite.
- [x] Run compile check for `src` and `tests`.
- [x] Run import side-effect checks for retry, CLI, container, and MCP adapters.
- [x] Record validation command results in code generation summary.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| Parser failure retry | selects parser-stage post failures and retries them through direct-post JobRunner |
| Safe operation | safe CLI/MCP summaries and no raw failure line output |
| Checkpoint/resume | retry execution reuses existing JobRunner checkpoint/stop behavior |
| Garage/S3 | explicit S3/Garage failure/success input refs and normal retry output storage |
| MCP | `retry_parser_failures` tool becomes functional |
| Container | existing one-shot worker accepts retry command argv |
| Future platform | queue/DLQ remains a documented future boundary |

## Completion Criteria

- [x] `retry-parser-failures` CLI command runs a real retry path.
- [x] MCP `retry_parser_failures` runs a real retry path.
- [x] Container argv can run retry without a new image or entrypoint.
- [x] Parser selector is deterministic and PBT-covered.
- [x] Malformed failure JSONL lines are counted and skipped.
- [x] Inaccessible inputs fail validation before Job start.
- [x] Existing success skip prevents already recovered posts from retry.
- [x] Retry execution writes a new normal output run.
- [x] Safe summaries exclude raw lines, credentials, headers, cookies, and stack traces.
- [x] Default tests pass without Docker, Garage, PostgreSQL, MCP runtime, or live FMKorea.
- [x] Code docs exist under `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/`.

## Approval Gate

UOW-009 Code Generation이 완료되었습니다.

승인 후 Build and Test 단계로 진행한다.
