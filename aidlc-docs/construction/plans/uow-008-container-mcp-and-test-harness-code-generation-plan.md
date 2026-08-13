# Code Generation Plan - UOW-008 Container, MCP, And Test Harness

이 문서는 `UOW-008 Container, MCP, And Test Harness` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Created At**: 2026-08-13T07:35:33Z
- **Plan Status**: Code Generated
- **Code Generated At**: 2026-08-13T07:58:49Z

## Unit Context

- **Unit**: UOW-008 Container, MCP, And Test Harness
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-007 implementation
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`, Docker root files
- **Documentation Location**: `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/`
- **Primary Stories**: US-016, US-017
- **Supporting Stories**: US-002, US-010, US-012, US-013, US-015
- **Supporting Role**: 로컬 CLI 중심 scraper core를 one-shot worker container, PostgreSQL checkpoint, Garage/S3 output, MCP tool adapter, quality harness까지 확장한다.

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
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-008 implements:

- root `Dockerfile`
- root `.dockerignore`
- root `.gitattributes` shell LF rule
- root `docker-entrypoint.sh`
- import-safe container adapter `src/fmkorea_scraper/adapters/container.py`
- import-safe MCP adapter `src/fmkorea_scraper/adapters/mcp.py`
- PostgreSQL checkpoint adapter `src/fmkorea_scraper/outputs/postgres_checkpoint.py`
- container S3 output/media/failure/report adapter `src/fmkorea_scraper/outputs/s3_output.py`
- output package exports for new adapters
- optional smoke pytest markers
- container env validation and redaction boundaries
- one-shot run/resume container execution
- MCP search/fetch/run/resume tool handler boundary
- safe unsupported `retry_parser_failures` MCP shape until UOW-009
- test-only JSONL/report/failure quality harness
- adapter/storage/quality tests without Docker/Garage/PostgreSQL/MCP/live network by default
- code public-contract and summary docs

UOW-008 does not implement:

- FMKorea selector/parser changes
- parser-failure retry execution engine
- distributed queue or scheduler
- production Kubernetes/cloud provisioning
- background MCP job registry
- network-exposed MCP HTTP/SSE transport
- GUI/Web UI
- CAPTCHA bypass

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Worker image build | `Dockerfile` |
| Docker build context filter | `.dockerignore` |
| shell LF rule | `.gitattributes` |
| Docker bootstrap | `docker-entrypoint.sh` |
| Container adapter | `src/fmkorea_scraper/adapters/container.py` |
| MCP adapter | `src/fmkorea_scraper/adapters/mcp.py` |
| PostgreSQL checkpoint store | `src/fmkorea_scraper/outputs/postgres_checkpoint.py` |
| S3 output/media store | `src/fmkorea_scraper/outputs/s3_output.py` |
| output package exports | `src/fmkorea_scraper/outputs/__init__.py` |
| pytest marker registry | `pyproject.toml` |
| container tests | `tests/test_container_adapter.py` |
| MCP tests | `tests/test_mcp_adapter.py` |
| S3/PostgreSQL tests | `tests/test_s3_output_and_postgres.py` |
| quality harness tests | `tests/test_quality_harness.py` |
| quality fixtures | `tests/fixtures/quality/` |
| public contract docs | `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/public-contracts.md` |
| code summary docs | `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/code-generation-summary.md` |

## Database Entities

UOW-008 owns one PostgreSQL checkpoint table initialized idempotently by the adapter:

```text
fmkorea_checkpoints(
  job_id text primary key,
  updated_at timestamptz not null,
  checkpoint_json jsonb not null
)
```

No Alembic migration, init container, or compose init SQL is generated in the first pass.

## Step Sequence

### Step 1. Docker Root Files

- [x] Create `Dockerfile`.
- [x] Create `.dockerignore`.
- [x] Create `.gitattributes` with `*.sh text eol=lf` if missing.
- [x] Create `docker-entrypoint.sh`.
- [x] Dockerfile copies explicit runtime inputs only.
- [x] Dockerfile installs `.[s3,postgres]`.
- [x] Dockerfile entrypoint calls `/app/docker-entrypoint.sh`.
- [x] Entrypoint delegates to `python -m fmkorea_scraper.adapters.container "$@"`.

### Step 2. Pytest Marker And Dependency Check

- [x] Confirm optional extras `s3`, `postgres`, `mcp`, `analysis`, and `test` exist.
- [x] Do not add async S3 SDK or migration framework.
- [x] Register optional smoke markers `docker`, `garage`, `postgres`, `mcp`, and `live`.
- [x] Preserve existing smoke markers when possible.

### Step 3. S3 Output Store

- [x] Create `src/fmkorea_scraper/outputs/s3_output.py`.
- [x] Reuse existing `S3ObjectStore`, output layout, JSONL writers, media store concepts, and failure redaction helpers.
- [x] Implement process-local spool for post/failure JSONL.
- [x] Upload full JSONL object after each append before returning success.
- [x] Upload report JSON.
- [x] Upload media bytes or return metadata-only media items.
- [x] Ensure `StoredObjectRef` never contains credentials.
- [x] Clean spool best-effort at finalize.

### Step 4. PostgreSQL Checkpoint Store

- [x] Create `src/fmkorea_scraper/outputs/postgres_checkpoint.py`.
- [x] Use optional `psycopg` import inside adapter execution path.
- [x] Add injectable connection factory for tests.
- [x] Run `CREATE TABLE IF NOT EXISTS fmkorea_checkpoints`.
- [x] Implement `save`, `load`, and `load_latest`.
- [x] Validate loaded JSON through `Checkpoint`.
- [x] Map DB failures to safe checkpoint/storage errors.

### Step 5. Output Package Exports

- [x] Export `S3OutputStore` and spool helpers as needed from `fmkorea_scraper.outputs`.
- [x] Export `PostgresCheckpointStore`.
- [x] Keep imports side-effect free.
- [x] Do not connect to S3/PostgreSQL on import.

### Step 6. Container Adapter

- [x] Create `src/fmkorea_scraper/adapters/container.py`.
- [x] Implement `ContainerEnvConfig.from_env`.
- [x] Read only documented env keys.
- [x] Validate required storage env before Job start.
- [x] Keep secret values out of repr/log/error details.
- [x] Implement `build_container_runtime(config, env_config)`.
- [x] Reuse UOW-007 command normalization and `build_job_config` for new runs.
- [x] Support `RESUME=true` with optional `JOB_ID`.
- [x] Wire `HttpClient`, collectors, detail service, `S3OutputStore`, `PostgresCheckpointStore`, `JobRunDependencies`, and `JobRunner`.
- [x] Map exit code `0` for completed, `1` for stopped/runtime failure, `2` for validation failure.
- [x] Close HTTP client in `finally`.
- [x] Connect SIGTERM/KeyboardInterrupt to the existing runner stop API where possible.

### Step 7. MCP Adapter

- [x] Create `src/fmkorea_scraper/adapters/mcp.py`.
- [x] Implement runtime-independent async tool handler functions.
- [x] Implement `safe_error_payload(exc, stage=None)` over `ErrorMapper`.
- [x] Implement tool shapes for `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, and `resume_job`.
- [x] Keep `retry_parser_failures` as safe unsupported until UOW-009.
- [x] Import MCP runtime only inside explicit server entrypoint/registration.
- [x] Support `python -m fmkorea_scraper.adapters.mcp`.
- [x] Do not start MCP server on import.

### Step 8. Quality Fixtures And Harness

- [x] Add `tests/fixtures/quality/posts.jsonl`.
- [x] Add `tests/fixtures/quality/failures.jsonl`.
- [x] Add `tests/fixtures/quality/report.json`.
- [x] Add `tests/test_quality_harness.py`.
- [x] Validate required post top-level fields.
- [x] Validate content/media/comment shape.
- [x] Validate BEST comment `is_best=true`, `badges`, and reaction fields.
- [x] Validate failure safe fields.
- [x] Validate report counts.
- [x] Keep optional Polars read check skipped unless Polars is available.

### Step 9. Adapter And Storage Tests

- [x] Add `tests/test_container_adapter.py`.
- [x] Add `tests/test_mcp_adapter.py`.
- [x] Add `tests/test_s3_output_and_postgres.py`.
- [x] Use fake S3 client/object store.
- [x] Use fake PostgreSQL connection/cursor.
- [x] Verify env validation and secret redaction.
- [x] Verify import side-effect safety.
- [x] Verify optional smoke tests skip by default if included.
- [x] Avoid Docker, Garage, PostgreSQL, MCP runtime, and live FMKorea in default tests.

### Step 10. Documentation

- [x] Create `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/code-generation-summary.md`.
- [x] Record generated files, public functions/classes, entrypoints, env contract, storage table, object output shape, tests, and deferred boundaries.

### Step 11. Validation

- [x] Run focused UOW-008 tests.
- [x] Run full default test suite.
- [x] Run compile check for `src` and `tests`.
- [x] Run import side-effect checks for container and MCP adapters.
- [x] Build Docker image only if local Docker is available and smoke gate is explicitly chosen.
- [x] Record validation command results in code generation summary.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-002 | secret/cookie/proxy redaction in container/MCP error boundaries |
| US-010 | Garage/S3-compatible JSONL/media/report output from worker container |
| US-012 | MCP search/fetch/run/resume tool boundary |
| US-013 | PostgreSQL checkpoint save/load/latest and container resume |
| US-015 | quality fixture harness and report/failure safety checks |
| US-016 | one-shot worker container and Docker entrypoint |
| US-017 | optional smoke infrastructure and shared PostgreSQL/Garage contract |

## Completion Criteria

- [x] Docker root files exist and are Linux-container safe.
- [x] Container adapter imports without reading env or starting IO.
- [x] MCP adapter imports without requiring MCP runtime or starting a server.
- [x] Container env validation fails before Job start with exit code `2`.
- [x] S3 output writes are durable before success return.
- [x] PostgreSQL checkpoint store can save, load, and load latest with fake/local substitute tests.
- [x] MCP tool handlers return JSON-safe success/error payloads.
- [x] Quality harness validates FMKorea JSONL/report/failure fixture shape including BEST comments.
- [x] Default tests do not require Docker, Garage, PostgreSQL, MCP, Polars, or live FMKorea.
- [x] Code docs exist under `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/`.

## Approval Gate

UOW-008 Code Generation이 완료되었습니다.

승인 후 Build and Test 단계로 진행한다.

