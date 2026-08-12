# Code Generation Plan - UOW-001 Core Models And Config

이 문서는 `UOW-001 Core Models And Config` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Approved At**: 2026-08-12T03:05:26Z
- **Code Generated At**: 2026-08-12T03:20:40Z
- **Validation**: `$env:PYTHONPATH='src'; python -m pytest tests` -> 33 passed

## Unit Context

- **Unit**: UOW-001 Core Models And Config
- **Project Type**: Greenfield Python package
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`
- **Documentation Location**: `aidlc-docs/construction/uow-001-core-models-and-config/code/`
- **Primary Story**: US-015 Python 라이브러리 API를 제공한다
- **Supporting Role**: UOW-002부터 UOW-010까지 공유할 모델, 설정, 오류, schema, port 계약 제공

## Dependencies

| Dependency | Status |
|---|---|
| Prior unit dependency | None |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-001 implements:

- Pydantic v2 strict base model
- enums and shared value models
- Job source, request, config, result, checkpoint, failure, report, and error models
- FMKorea source schema versions: `fmkorea.post.v1`, `fmkorea.checkpoint.v1`, `fmkorea.failure.v1`, `fmkorea.job_report.v1`
- BEST comment fields: `is_best`, `badges`, `reactions`
- metadata bounds validation
- typed core exceptions
- adapter-safe error mapping and secret redaction
- schema snapshot and compatibility helpers
- port protocols
- import-safe public package exports
- example tests and property-based test strategies

UOW-001 does not implement:

- HTTP requests
- FMKorea HTML parsing
- file/object/database storage
- worker queue runtime
- CLI command parsing
- container entrypoint
- MCP tools
- Docker, compose, Terraform, CDK, database migration, object storage, queue, or monitoring artifacts

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Package metadata | `pyproject.toml` |
| Public package exports | `src/fmkorea_scraper/__init__.py` |
| Core API placeholder signatures | `src/fmkorea_scraper/core/api.py` |
| Typed exceptions | `src/fmkorea_scraper/core/errors.py` |
| Validation helpers | `src/fmkorea_scraper/core/validation.py` |
| Port protocols | `src/fmkorea_scraper/core/ports.py` |
| Schema compatibility helpers | `src/fmkorea_scraper/core/schema.py` |
| Base model and enums | `src/fmkorea_scraper/models/base.py`, `src/fmkorea_scraper/models/enums.py` |
| Job/request/config models | `src/fmkorea_scraper/models/job.py` |
| Content/media/comment/post models | `src/fmkorea_scraper/models/content.py`, `src/fmkorea_scraper/models/media.py`, `src/fmkorea_scraper/models/comment.py`, `src/fmkorea_scraper/models/post.py` |
| Checkpoint/failure/report/error models | `src/fmkorea_scraper/models/checkpoint.py`, `src/fmkorea_scraper/models/failure.py`, `src/fmkorea_scraper/models/report.py`, `src/fmkorea_scraper/models/error.py` |

## Database Entities

No database entities or migration scripts are owned by UOW-001.

Persisted JSON-compatible contracts are:

- `PostResult`
- `Checkpoint`
- `FailureRecord`
- `JobReport`

Concrete PostgreSQL checkpoint storage is deferred to UOW-008.

## Step Sequence

### Step 1. Project Structure Setup

- [x] Create `pyproject.toml` with Python 3.11+, Pydantic v2 runtime dependency, and pytest/Hypothesis test dependencies.
- [x] Create `src/fmkorea_scraper/` package directories: `core/`, `models/`.
- [x] Create `tests/`, `tests/strategies/`, and `tests/snapshots/`.
- [x] Create package marker files where needed.
- [x] Do not create runtime Docker/cloud/deployment files for UOW-001.

### Step 2. Business Logic Generation - Base Models And Enums

- [x] Create `src/fmkorea_scraper/models/base.py` with `StrictBaseModel`, metadata default helper, and bounded metadata validation hook.
- [x] Create `src/fmkorea_scraper/models/enums.py` with Job, content, comment, media, storage, checkpoint, stop reason, response, and schema-related enums.
- [x] Ensure public models reject unknown fields with Pydantic v2 `extra="forbid"`.

### Step 3. Business Logic Generation - Job And Request Models

- [x] Create `src/fmkorea_scraper/models/job.py`.
- [x] Implement `JobConfig`, `ScrapeOptions`, `WorkerConfig`, `RuntimeConfig`, `StorageConfig`, `RangeFilter`, realtime termination options, source discriminated unions, and public request models.
- [x] Validate job/source type matching, range ordering, deep-search range requirement, no-keyword range requirement, and realtime exactly-one termination condition.

### Step 4. Business Logic Generation - Post, Comment, Media, Checkpoint, Failure, Report, Error Models

- [x] Create `src/fmkorea_scraper/models/content.py`, `media.py`, `comment.py`, `post.py`, `checkpoint.py`, `failure.py`, `report.py`, and `error.py`.
- [x] Implement ordered content blocks for text, image, FMKorea video, YouTube, X, link, attachment, and unknown embeds.
- [x] Implement flat `Comment` with BEST fields and reaction score consistency.
- [x] Implement checkpoint status/reason consistency and schema version defaults.
- [x] Keep `is_repost` and `repost` out of FMKorea source JSON models.

### Step 5. Business Logic Generation - Validation And Error Helpers

- [x] Create `src/fmkorea_scraper/core/validation.py` with `MetadataValidator`, `JobConfigValidator`, and bounded metadata checks.
- [x] Create `src/fmkorea_scraper/core/errors.py` with typed core exceptions.
- [x] Implement `ErrorMapper` and `SecretRedactor` for adapter-safe `ErrorResult` creation.

### Step 6. Business Logic Generation - Schema Compatibility Helpers

- [x] Create `src/fmkorea_scraper/core/schema.py`.
- [x] Implement `SchemaSnapshot`, `SchemaSnapshotWriter`, and `SchemaCompatibilityChecker`.
- [x] Add initial schema handling for post, checkpoint, failure, and job report.
- [x] Create committed schema snapshots under `tests/snapshots/`.
- [x] Do not introduce migration registry or data migration runner in UOW-001.

### Step 7. API Layer Generation - Ports And Public API

- [x] Create `src/fmkorea_scraper/core/ports.py` with `HttpPort`, `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, `CheckpointStorePort`, `ClockPort`, and `LoggerPort` protocols.
- [x] Create `src/fmkorea_scraper/core/api.py` with import-safe public async function signatures for search, fetch, run, resume, and retry entrypoints.
- [x] Export stable public names from `src/fmkorea_scraper/__init__.py`.

### Step 8. Business Logic Unit Testing - Example Tests

- [x] Create example tests for valid minimal `JobConfig` per source type.
- [x] Test invalid job/source mismatch, invalid realtime termination options, invalid deep-search/no-keyword range, stopped checkpoint without reason, BEST comment consistency, and error redaction.
- [x] Test package import side-effect safety.

### Step 9. Business Logic Unit Testing - Property-Based Strategies

- [x] Create `tests/strategies/job_configs.py`.
- [x] Create `tests/strategies/post_results.py`.
- [x] Create `tests/strategies/content_blocks.py`.
- [x] Create `tests/strategies/comments.py`.
- [x] Create `tests/strategies/checkpoints.py`.
- [x] Create `tests/strategies/errors.py`.

### Step 10. Business Logic Unit Testing - Property-Based Tests

- [x] Create property tests for JSON round trip, range invariants, realtime invariant, content order invariant, BEST comment invariant, checkpoint status/reason consistency, and schema version preservation.
- [x] Keep Hypothesis shrinking and seed reproducibility enabled.

### Step 11. API Layer Unit Testing

- [x] Test port protocols are importable and structurally usable by simple fake implementations.
- [x] Test public API placeholders are import-safe and do not trigger network, file, terminal, `.env`, or `user-agents.txt` side effects.

### Step 12. Documentation Generation

- [x] Create `aidlc-docs/construction/uow-001-core-models-and-config/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-001-core-models-and-config/code/code-generation-summary.md`.
- [x] Document generated public models, schema versions, error mapping, schema snapshots, and deferred runtime responsibilities.

### Step 13. Dependency Lock Handling

- [x] Use compatible dependency ranges in `pyproject.toml`.
- [x] Check lockfile resolver availability during generation; `uv` was not available in this environment.
- [x] If no resolver is available, record lock generation as a Build & Test follow-up instead of manually inventing exact versions.

### Step 14. Deployment Artifacts Generation

- [x] Do not create Docker, compose, Terraform, CDK, database migration, object storage, queue, or monitoring artifacts for UOW-001.
- [x] Record this as N/A in the code generation summary.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-015 Python 라이브러리 API를 제공한다 | public package exports, core API signatures, strict request/result models |
| US-001 | shared `JobConfig` and validation contracts for CLI/wizard |
| US-002 | runtime/proxy/cookie config fields and safe error contracts |
| US-003 | worker/request option models |
| US-004, US-005, US-006 | search/source request models and candidate contracts |
| US-007, US-008, US-009 | post, content block, media, comment, BEST comment contracts |
| US-010, US-011 | JSONL/failure/report contracts and Polars-friendly schema readiness |
| US-013 | checkpoint/resume request contracts |
| US-017 | MCP-facing request/result model contracts |

## Completion Criteria

- All planned source files exist under `src/fmkorea_scraper/`.
- Tests for UOW-001 contracts exist under `tests/`.
- Documentation summary exists under `aidlc-docs/construction/uow-001-core-models-and-config/code/`.
- No runtime infrastructure artifact is created for UOW-001.
- All checkboxes in this plan are marked complete after generation.
