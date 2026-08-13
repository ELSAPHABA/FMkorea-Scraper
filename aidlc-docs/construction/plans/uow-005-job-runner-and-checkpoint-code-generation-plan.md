# Code Generation Plan - UOW-005 Job Runner And Checkpoint

이 문서는 `UOW-005 Job Runner And Checkpoint` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Approved At**: 2026-08-12T17:47:59Z
- **Code Generated At**: 2026-08-12T17:47:59Z
- **Validation**: `$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short` -> 97 passed, 2 skipped; `$env:PYTHONPATH='src'; python -m compileall -q src tests` -> passed

## Unit Context

- **Unit**: UOW-005 Job Runner And Checkpoint
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-004 and UOW-006 code
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`
- **Documentation Location**: `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/code/`
- **Primary Stories**: US-012, US-013
- **Supporting Stories**: US-001, US-003, US-005, US-006, US-010, US-014, US-015, US-016, US-017
- **Supporting Role**: UOW-003/UOW-004/UOW-006을 연결해 하나의 Job 실행, stop/checkpoint/resume, output-before-checkpoint 순서를 제공

## Dependencies

| Dependency | Status |
|---|---|
| Prior unit dependency | UOW-001, UOW-002, UOW-003, UOW-004, and UOW-006 approved and implemented |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-005 implements:

- runner package under `src/fmkorea_scraper/runner/`
- `JobRunner` public orchestration service
- `JobRunDependencies`, `JobRunResult`, `RunnerState`, `RunnerCounters`
- pure runner policies for post keys, checkpoint cadence, stop/report mapping, safe context filtering, and counter consistency
- in-process `asyncio.Queue[PostCandidate]` fan-out with one collector task and N post workers
- sentinel-based worker shutdown
- completed-key dedupe before detail fetch
- output-before-checkpoint advancement
- running checkpoint every 10 successful post outputs
- terminal checkpoint on completed/stopped/failed paths
- checkpoint resume with new `run_id`
- media download coordination with `media_worker_count` semaphore
- safe failure records for parser, media, output, checkpoint, stop-class, and runner failures
- final `JobReport` writing and `JobRunResult` return
- `core.api.run_job` and `core.api.resume_job` bridge updates for explicit runner delegation
- fake dependency tests and pure policy PBT
- code documentation

UOW-005 does not implement:

- CLI commands or terminal wizard
- runtime environment mapping
- user-agent/proxy loading
- concrete HTTP client construction
- list/search/detail HTML parsing
- JSONL/media/checkpoint storage internals
- PostgreSQL checkpoint adapter
- parser-stage retry reprocessor
- SQS/DLQ or lease protocol
- container entrypoint
- MCP tools
- Docker, Terraform, AWS CDK, Garage, PostgreSQL, SQS, or monitoring infrastructure

## File Layout Decision

Implement the runner package as:

- `src/fmkorea_scraper/runner/__init__.py`
- `src/fmkorea_scraper/runner/models.py`
- `src/fmkorea_scraper/runner/policies.py`
- `src/fmkorea_scraper/runner/checkpointing.py`
- `src/fmkorea_scraper/runner/workers.py`
- `src/fmkorea_scraper/runner/service.py`

Update only where needed:

- `src/fmkorea_scraper/core/api.py`
- `src/fmkorea_scraper/__init__.py`

Reason:

- matches approved NFR Design
- keeps orchestration, policy, checkpoint, and worker logic separated by real responsibility
- avoids external worker frameworks and speculative adapter abstractions
- preserves existing model and port contracts

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Public runner exports | `src/fmkorea_scraper/runner/__init__.py` |
| Runner value objects | `src/fmkorea_scraper/runner/models.py` |
| Pure runner policies | `src/fmkorea_scraper/runner/policies.py` |
| Checkpoint coordinator | `src/fmkorea_scraper/runner/checkpointing.py` |
| Post workers and media coordinator | `src/fmkorea_scraper/runner/workers.py` |
| `JobRunner` service | `src/fmkorea_scraper/runner/service.py` |
| Public API bridge | `src/fmkorea_scraper/core/api.py` |
| Package exports | `src/fmkorea_scraper/__init__.py` |
| Runner service tests | `tests/test_runner_service.py` |
| Runner worker tests | `tests/test_runner_workers.py` |
| Runner checkpoint tests | `tests/test_runner_checkpointing.py` |
| Runner policy tests | `tests/test_runner_policies.py` |
| Runner PBT tests | `tests/test_runner_properties.py` |
| PBT strategies | `tests/strategies/runner.py` |
| Public contract documentation | `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/code/public-contracts.md` |
| Code generation summary | `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/code/code-generation-summary.md` |

## Database Entities

No database entities or migration scripts are owned by UOW-005.

PostgreSQL checkpoint storage remains deferred to a later storage/runtime unit.

## Step Sequence

### Step 1. Dependency Check

- [x] Reuse Python standard `asyncio`.
- [x] Reuse existing Pydantic models and core ports.
- [x] Do not add `anyio`, Celery, Dramatiq, SQS client, database driver usage, browser automation, or new storage dependencies.

### Step 2. Runner Package Setup

- [x] Create `src/fmkorea_scraper/runner/`.
- [x] Create import-safe public exports.
- [x] Avoid network, file, env, prompt, storage, queue service, or concrete adapter creation at import time.

### Step 3. Runner Models

- [x] Implement `JobRunDependencies`.
- [x] Implement `JobRunResult`.
- [x] Implement `RunnerCounters`.
- [x] Implement `RunnerState`.
- [x] Keep internal sentinel/control values private to runner code.
- [x] Do not persist raw HTML, raw response bodies, cookies, proxy credentials, or storage secrets.

### Step 4. Pure Policies

- [x] Implement completed-key creation from `PostCandidate` and `PostResult`.
- [x] Implement completed-key skip checks.
- [x] Implement checkpoint cadence calculation with default 10-success interval.
- [x] Implement stop reason mapping.
- [x] Implement report status mapping.
- [x] Implement safe failure context allow-list helper.
- [x] Cover policies with example tests and PBT.

### Step 5. Checkpoint Coordinator

- [x] Implement checkpoint load for resume.
- [x] Implement running checkpoint snapshot creation.
- [x] Implement completed/stopped/failed terminal checkpoint creation.
- [x] Save running checkpoint after every 10 successful post outputs.
- [x] Save terminal checkpoint immediately when possible.
- [x] Treat checkpoint save/load failure as runner failure.

### Step 6. Worker And Queue Flow

- [x] Implement one collector task that iterates UOW-003 collector candidates.
- [x] Implement bounded or unbounded `asyncio.Queue` from `WorkerConfig.queue_max_size`.
- [x] Enqueue `PostCandidate` values only.
- [x] Enqueue one sentinel per worker after collection completes.
- [x] Implement `post_worker_count` post workers.
- [x] Stop accepting new work when stop event is set.

### Step 7. Post Processing

- [x] Skip completed candidates before detail fetch.
- [x] Call UOW-004 detail service for one candidate.
- [x] Process media according to `MediaMode`.
- [x] Append final `PostResult` through `OutputStorePort.append_post`.
- [x] Add completed key only after append success.
- [x] Trigger checkpoint cadence after completed-key update.
- [x] Record safe failures and continue when failure is non-stop-class.

### Step 8. Media Coordination

- [x] Use shared `asyncio.Semaphore(media_worker_count)`.
- [x] Do not download bytes in `MediaMode.URL_ONLY`.
- [x] Use `HttpPort.download` only in `MediaMode.DOWNLOAD`.
- [x] Store downloaded bytes through `MediaStorePort.save_media`.
- [x] Use `MediaStorePort.save_metadata_only` only for URL-only metadata persistence when needed.

### Step 9. Stop, Resume, And Finalization

- [x] Implement fail-closed CAPTCHA/block handling.
- [x] Implement manual stop/timeout stop state support where exposed by runner API.
- [x] Resume with restored `job_config`, `collector_cursor`, `completed_keys`, and optional `queued_links`.
- [x] Create a new `run_id` on resume.
- [x] Do not append to older run JSONL output.
- [x] Write final report on completed, stopped, and failed paths when possible.
- [x] Finalize stores best-effort on completion, stop, cancellation, and failure.

### Step 10. Public API Bridge

- [x] Export `JobRunner`, `JobRunDependencies`, and `JobRunResult`.
- [x] Keep `core.api.run_job(config, runner=...) -> JobReport`.
- [x] Keep `core.api.resume_job(request, runner=...) -> JobReport`.
- [x] If `JobRunner.run/resume` returns `JobRunResult`, unwrap and return `.report` in `core.api`.
- [x] Keep no-runner calls raising the existing unsupported-source error until adapter wiring exists.

### Step 11. Testing

- [x] Add runner service tests with fake dependencies.
- [x] Add worker flow tests.
- [x] Add checkpoint coordinator tests.
- [x] Add pure policy tests.
- [x] Add Hypothesis tests for completed-key dedupe, cadence, report counters, resume skip sets, and safe context allow-listing.
- [x] Keep default tests free of live FMKorea, browser automation, Garage/S3, PostgreSQL, SQS/DLQ, Docker, MCP, and CDK.

### Step 12. Documentation

- [x] Generate public contract documentation.
- [x] Generate code generation summary.
- [x] Record no deployment artifacts for this unit.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-001 | future CLI creates `JobConfig` and calls the same runner |
| US-003 | worker count and media concurrency are applied inside one Job |
| US-005 | deep/integrated search candidates can flow through worker fan-out |
| US-006 | realtime collection stops adding new candidates and runner drains safe queued work |
| US-010 | output/failure/report writes are called in durable order |
| US-012 | CAPTCHA/block stop-class events save stopped checkpoints |
| US-013 | checkpoint resume restores completed-key dedupe and starts a new run |
| US-014 | failure records include parser-stage distinction for later retry unit |
| US-015 | public library runner API is available |
| US-016 | future worker container can call the same runner with shared storage dependencies |
| US-017 | future MCP tools can call the same runner API |

## Completion Criteria

- [x] UOW-005 source files exist under `src/fmkorea_scraper/runner/`.
- [x] Existing UOW-001 ports and UOW-003/UOW-004/UOW-006 services are consumed through explicit dependencies.
- [x] `core.api.run_job` and `core.api.resume_job` support explicit runner delegation.
- [x] Tests for runner lifecycle, workers, checkpointing, policies, and PBT exist under `tests/`.
- [x] Documentation summary exists under `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/code/`.
- [x] No runtime infrastructure artifact is created for UOW-005.
- [x] `$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short` passes after implementation.
- [x] `$env:PYTHONPATH='src'; python -m compileall -q src tests` passes after implementation.

## Approval Gate

UOW-005 Code Generation 산출물이 생성되었습니다.

승인 후 다음 단계는 `UOW-005 Build and Test`이다.
