# Code Generation Plan - UOW-006 Output And Storage

이 문서는 `UOW-006 Output And Storage` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Approved At**: 2026-08-12T14:02:34Z
- **Code Generated At**: 2026-08-12T14:02:34Z
- **Validation**: `$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short` -> 83 passed, 2 skipped; `$env:PYTHONPATH='src'; python -m compileall -q src tests` -> passed

## Unit Context

- **Unit**: UOW-006 Output And Storage
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-004 code
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`
- **Documentation Location**: `aidlc-docs/construction/uow-006-output-and-storage/code/`
- **Primary Stories**: US-010, US-011
- **Supporting Stories**: US-008, US-009, US-012, US-013, US-014, US-016
- **Supporting Role**: UOW-005 JobRunner가 사용할 output, media, failure, local checkpoint 저장 계층 제공

## Dependencies

| Dependency | Status |
|---|---|
| Prior unit dependency | UOW-001, UOW-002, UOW-003, and UOW-004 approved and implemented |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-006 implements:

- output package under `src/fmkorea_scraper/outputs/`
- local run layout and path sanitization
- JSONL writer for `PostResult` and `FailureRecord`
- atomic JSON writer for report/checkpoint files
- local output store for `posts.jsonl` and `report.json`
- local failure store for `failures.jsonl` read/write
- local media store for caller-supplied media bytes and metadata-only mode
- local checkpoint store backed by `Checkpoint.json`
- safe failure detail redaction
- S3-compatible object store through optional `s3` dependency
- file-backed S3 JSONL spool and same-key upload behavior
- storage factory from existing `StorageConfig`
- local/fake S3/property tests
- optional env-gated S3 smoke test
- optional Polars read smoke test

UOW-006 does not implement:

- link collection traversal
- post detail parsing
- HTTP media download
- worker queues or checkpoint advancement order
- duplicate prevention
- parser-failure retry scheduling
- PostgreSQL checkpoint adapter
- CLI commands or terminal wizard
- container entrypoint
- MCP tools
- Docker, Terraform, AWS CDK, Garage provisioning, SQS, or monitoring infrastructure

## File Layout Decision

Implement the storage package as:

- `src/fmkorea_scraper/outputs/__init__.py`
- `src/fmkorea_scraper/outputs/errors.py`
- `src/fmkorea_scraper/outputs/layout.py`
- `src/fmkorea_scraper/outputs/jsonl.py`
- `src/fmkorea_scraper/outputs/redaction.py`
- `src/fmkorea_scraper/outputs/local.py`
- `src/fmkorea_scraper/outputs/checkpoint.py`
- `src/fmkorea_scraper/outputs/s3.py`
- `src/fmkorea_scraper/outputs/factory.py`

Reason:

- matches the approved NFR Design logical components
- keeps pathing, serialization, redaction, local storage, checkpoint, S3, and factory code separated by real responsibility
- avoids a speculative `StorageService` layer before UOW-005 defines orchestration pressure
- preserves the existing UOW-001 port contracts

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Public output package exports | `src/fmkorea_scraper/outputs/__init__.py` |
| Storage exceptions | `src/fmkorea_scraper/outputs/errors.py` |
| Run layout and path/key helpers | `src/fmkorea_scraper/outputs/layout.py` |
| JSONL and atomic JSON writers | `src/fmkorea_scraper/outputs/jsonl.py` |
| Failure detail redaction | `src/fmkorea_scraper/outputs/redaction.py` |
| Local output/failure/media stores | `src/fmkorea_scraper/outputs/local.py` |
| Local checkpoint store | `src/fmkorea_scraper/outputs/checkpoint.py` |
| Optional S3-compatible store/spool | `src/fmkorea_scraper/outputs/s3.py` |
| Storage factory | `src/fmkorea_scraper/outputs/factory.py` |
| Optional smoke markers | `pyproject.toml` |
| Local/fake S3 tests | `tests/test_outputs_storage.py` |
| Output PBT tests | `tests/test_outputs_properties.py` |
| PBT strategies | `tests/strategies/outputs.py` |
| Optional S3 smoke | `tests/test_outputs_s3_smoke.py` |
| Optional Polars smoke | `tests/test_outputs_polars_smoke.py` |
| Public contract documentation | `aidlc-docs/construction/uow-006-output-and-storage/code/public-contracts.md` |
| Code generation summary | `aidlc-docs/construction/uow-006-output-and-storage/code/code-generation-summary.md` |

## Database Entities

No database entities or migration scripts are owned by UOW-006.

PostgreSQL checkpoint storage remains deferred to UOW-008 or a later storage/runtime unit.

## Step Sequence

### Step 1. Dependency And Marker Check

- [x] Reuse existing optional `s3` extra with `boto3`.
- [x] Reuse existing optional `analysis` extra with `polars`.
- [x] Add pytest markers for optional S3 and Polars smoke tests if missing.
- [x] Do not add async S3, storage framework, queue, database, Docker, or cloud dependency.

### Step 2. Output Package Setup

- [x] Create `src/fmkorea_scraper/outputs/`.
- [x] Create import-safe public exports.
- [x] Avoid file writes, environment reads, S3 imports, or external connections at package import.

### Step 3. Storage Errors

- [x] Implement a small typed storage error hierarchy.
- [x] Preserve safe context only.
- [x] Avoid including raw credentials, cookies, headers, raw HTML, or post body text in error fields.

### Step 4. Layout And Path Safety

- [x] Implement `OutputRunLayout`.
- [x] Implement safe path segment sanitization.
- [x] Implement local path containment checks.
- [x] Implement matching S3 object key generation.
- [x] Cover traversal and key generation with property tests.

### Step 5. JSONL And Atomic JSON Writers

- [x] Implement `JsonlWriter`.
- [x] Serialize Pydantic models with `model_dump(mode="json")`.
- [x] Write UTF-8, one object per line.
- [x] Implement `AtomicJsonWriter` using same-directory temp files and `os.replace`.
- [x] Test round trips and partial-invalid input failure behavior.

### Step 6. Local Stores

- [x] Implement `LocalOutputStore`.
- [x] Implement `LocalFailureStore`.
- [x] Implement `LocalMediaStore`.
- [x] Return `StoredObjectRef` and updated `MediaItem` values.
- [x] Ensure report and checkpoint writes are atomic.
- [x] Ensure generated files stay under configured base path.

### Step 7. Local Checkpoint Store

- [x] Implement `LocalCheckpointDocument`.
- [x] Implement `LocalCheckpointStore.save`.
- [x] Implement `LocalCheckpointStore.load(job_id)`.
- [x] Implement `LocalCheckpointStore.load_latest`.
- [x] Guard in-process file updates with a local lock.
- [x] Keep PostgreSQL checkpoint mode unsupported in this unit with a clear error.

### Step 8. Failure Redaction

- [x] Implement `sanitize_failure_context`.
- [x] Keep only allowed operational fields.
- [x] Drop or mask credential-like keys.
- [x] Reject raw HTML/body/content/header/cookie/proxy/token fields.
- [x] Add idempotence and forbidden-key property tests.

### Step 9. S3-Compatible Store

- [x] Implement lazy `boto3` import in S3 mode only.
- [x] Implement S3-compatible object writes from configured endpoint/bucket/prefix.
- [x] Implement S3 media/report object writes.
- [x] Implement `S3JsonlSpool` with file-backed append and same-key upload.
- [x] Test key/spool behavior with a fake uploader.
- [x] Do not call Garage-specific APIs or create buckets.

### Step 10. Storage Factory

- [x] Implement `StorageFactory`.
- [x] Create local stores for local output/checkpoint mode.
- [x] Create S3-compatible output stores only when `StorageConfig.output_mode` selects it.
- [x] Reject unsupported PostgreSQL checkpoint creation in UOW-006 with a clear message.
- [x] Do not read environment variables inside the factory.

### Step 11. Optional Smoke Tests

- [x] Add S3 smoke test gated by `FMKOREA_S3_SMOKE_ENABLED=true` and complete S3 env.
- [x] Add Polars smoke test that skips when Polars is unavailable.
- [x] Keep both smoke paths out of the mandatory default test contract.

### Step 12. Documentation

- [x] Generate public contract documentation.
- [x] Generate code generation summary.
- [x] Record no deployment artifacts for this unit.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-008 | content/media blocks remain nested and JSONL-readable |
| US-009 | comments remain nested and Polars-explodable from post JSONL |
| US-010 | Job-level post JSONL, failure JSONL, report, media references, and resume-new-run layout |
| US-011 | source JSONL can be read by Polars without source mutation |
| US-012 | local checkpoint store foundation for fail-closed checkpoint save |
| US-013 | local checkpoint load/load-latest foundation for resume |
| US-014 | failure JSONL read path for later parser-stage retry |
| US-016 | S3-compatible output contract for later container/shared storage |

## Completion Criteria

- [x] UOW-006 source files exist under `src/fmkorea_scraper/outputs/`.
- [x] Existing UOW-001 ports are satisfied by concrete local/S3-compatible implementations.
- [x] Tests for local output, failure, media, checkpoint, layout safety, redaction, fake S3, and Polars smoke behavior exist under `tests/`.
- [x] Documentation summary exists under `aidlc-docs/construction/uow-006-output-and-storage/code/`.
- [x] No runtime infrastructure artifact is created for UOW-006.
- [x] `$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short` passes after implementation.

## Approval Gate

UOW-006 Code Generation 산출물이 생성되었습니다.

승인 후 다음 단계는 `UOW-006 Build and Test`이다.
