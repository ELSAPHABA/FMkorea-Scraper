# NFR Requirements - UOW-008 Container, MCP, And Test Harness

## Scope

This document defines non-functional requirements for `UOW-008 Container, MCP, And Test Harness`.

In scope:

- one-shot worker container runtime
- `docker-entrypoint.sh` and `.dockerignore`
- container environment validation
- PostgreSQL checkpoint adapter
- S3-compatible/Garage output wiring
- MCP tool adapter
- result quality fixture harness
- optional smoke hooks
- import side-effect safety

Out of scope:

- parser-failure retry execution engine
- distributed scheduler or queue consumer
- background MCP job registry
- production Kubernetes manifests
- CAPTCHA bypass
- GUI/Web UI
- scraper parser redesign

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Add `psycopg[binary]>=3,<4` only under a `postgres` optional extra; container installs `.[postgres,s3]` or an equivalent extra set. |
| Q2 | A | Reuse the existing `s3` extra and `boto3`; do not add `aioboto3` or `aiobotocore`. |
| Q3 | A | Use one Python 3.11+ slim Dockerfile; Dockerfile entrypoint calls `/app/docker-entrypoint.sh`, which delegates to `python -m fmkorea_scraper.adapters.container`. |
| Q4 | A | Add `.dockerignore`; exclude local state, secrets, docs, workflow artifacts, caches, outputs, and build artifacts; keep `docker-entrypoint.sh` LF-compatible. |
| Q5 | A | Read and validate env only at container entrypoint runtime; missing required env returns validation exit code `2`; secrets never print. |
| Q6 | A | Create checkpoint table with idempotent `CREATE TABLE IF NOT EXISTS`; do not add Alembic. |
| Q7 | A | Use process-local temp spool for S3 JSONL append; upload full object after append; best-effort cleanup; resume creates a new run object. |
| Q8 | A | Redact proxy/cookie/header/env secrets; do not support user-provided cookie files; server-set cookies stay in `HttpClient` memory only. |
| Q9 | A | Put MCP dependencies in an `mcp` optional extra; no MCP dependency in default scraper/runtime/container install. |
| Q10 | A | MCP tools are one-shot and return safe `ErrorMapper` JSON errors without traceback or secrets. |
| Q11 | A | Default quality tests use stdlib `json`; Polars read checks are optional via `analysis` or `test-analysis` extra. |
| Q12 | A | Default tests use fakes, fixtures, and PBT; Docker/Garage/PostgreSQL/MCP/live smoke tests are opt-in by marker/env flag. |

No follow-up question is required. The answers are internally consistent and preserve the baseline scraper structure where FMKorea-specific behavior does not require divergence.

## Performance Requirements

### NFR-UOW008-PERF-001. Optional Heavy Dependencies

PostgreSQL, MCP, and Polars dependencies must not be installed by default.

They must be isolated behind optional extras:

- `postgres`
- `mcp`
- `analysis` or `test-analysis`

### NFR-UOW008-PERF-002. S3 Dependency Reuse

S3-compatible writes must reuse the existing `s3` extra and `boto3` boundary.

UOW-008 must not add `aioboto3`, `aiobotocore`, or another S3 SDK unless later measurement proves the sync boundary is the bottleneck.

### NFR-UOW008-PERF-003. Container Image Simplicity

The first container image must use one Dockerfile and one runtime target.

Multi-stage build or multiple target images are deferred unless build size, reproducibility, or security scanning later creates real pressure.

### NFR-UOW008-PERF-004. S3 Spool Cost Boundary

`S3OutputStore` may upload the full JSONL object after each append.

This is accepted for the first implementation because it preserves durable write semantics before checkpoint progress. Throughput tuning is deferred until real output sizes show pressure.

## Reliability And Resiliency Requirements

### NFR-UOW008-REL-001. Import Safety

Importing container, MCP, PostgreSQL, or S3 adapter modules must not:

- start a Job
- read environment variables
- connect to PostgreSQL
- connect to S3/Garage
- start an MCP server
- create files
- perform FMKorea HTTP requests

### NFR-UOW008-REL-002. Entrypoint Environment Validation

Container environment variables must be read at process execution time.

Missing required env must fail before a Job starts and return validation exit code `2`.

### NFR-UOW008-REL-003. PostgreSQL Checkpoint Table Creation

`PostgresCheckpointStore` must create its table idempotently with `CREATE TABLE IF NOT EXISTS`.

Schema creation must be safe to call repeatedly from one-shot container processes.

### NFR-UOW008-REL-004. Checkpoint JSON Validation

Loaded checkpoint JSON must validate through the shared `Checkpoint` model before it is returned to `JobRunner`.

Invalid stored checkpoint JSON must fail safely with a checkpoint/storage error.

### NFR-UOW008-REL-005. Durable Output Before Checkpoint Progress

`S3OutputStore.append_post()`, media writes, and `write_failure()` must return success only after the S3-compatible object upload succeeds.

This preserves the UOW-005 checkpoint rule: checkpoint progress advances only after durable output storage succeeds.

### NFR-UOW008-REL-006. Resume Output Isolation

Resume creates a new run output object set.

It must not append to or reuse an old local spool from a previous process.

### NFR-UOW008-REL-007. Optional Smoke Isolation

Docker, Garage, PostgreSQL, MCP server, and live FMKorea smoke tests must be skipped by default unless their marker and required environment flags are explicitly enabled.

## Security Requirements

### NFR-UOW008-SEC-001. Secret Redaction

Adapters must not print or return:

- database password
- S3 access key
- S3 secret key
- proxy password
- raw `.env` values
- raw environment maps
- cookies
- tokens
- raw HTTP headers
- raw HTML/body/content

### NFR-UOW008-SEC-002. Safe Adapter Errors

Container and MCP errors must use `ErrorMapper` or equivalent safe error mapping.

MCP errors must be JSON-serializable and must not include Python traceback text.

### NFR-UOW008-SEC-003. Environment Scope

Container adapters must read only documented environment variables.

They must not dump `os.environ` or pass raw env maps into public error details.

### NFR-UOW008-SEC-004. S3 Reference Safety

`StoredObjectRef` values for S3 output must contain bucket/key identifiers only.

They must not contain credentials, signed URLs, or raw endpoint credentials.

### NFR-UOW008-SEC-005. Cookie Boundary

User-provided cookie files must not be supported.

Server-set cookies may exist only inside the current in-memory `HttpClient` lifecycle and must not be persisted to outputs, checkpoints, reports, failures, logs, or MCP responses.

### NFR-UOW008-SEC-006. MCP Server Side Effects

Installing the `mcp` extra or importing MCP modules must not start a server.

The MCP server starts only through the MCP entrypoint.

## Maintainability Requirements

### NFR-UOW008-MAINT-001. Adapter Reuse

Container and MCP adapters must reuse:

- UOW-001 models
- UOW-007 command builders where applicable
- UOW-002 HTTP runtime
- UOW-003 search collection
- UOW-004 detail services
- UOW-005 runner
- UOW-006 output/checkpoint ports

### NFR-UOW008-MAINT-002. No Migration Framework In First Pass

UOW-008 must not add Alembic or another migration framework for one checkpoint table.

If future normalized checkpoint schema or multiple tables appear, migration tooling can be reconsidered.

### NFR-UOW008-MAINT-003. Optional Extras Boundary

Optional capabilities must stay isolated:

- `s3`: S3-compatible/Garage writes
- `postgres`: PostgreSQL checkpoint store
- `mcp`: MCP server/tools
- `analysis` or `test-analysis`: Polars checks

### NFR-UOW008-MAINT-004. One-Shot MCP Boundary

MCP `run_job` and `resume_job` must remain one-shot calls in UOW-008.

Background job registry, cancellation, progress polling, and distributed scheduling are deferred.

## Test Requirements

### NFR-UOW008-TEST-001. Default Test Gate

Default tests must not require:

- Docker
- Garage
- PostgreSQL
- MCP server process
- live FMKorea network access
- Polars

### NFR-UOW008-TEST-002. Required Example Tests

Default tests must cover:

- adapter import side-effect safety
- container env validation
- container exit code mapping
- PostgreSQL checkpoint store behavior with fake or local substitute
- S3 output behavior with fake S3 client
- MCP input validation
- MCP safe error payloads
- JSONL/report quality fixture validation
- BEST comment schema fixture validation
- optional smoke test skip behavior

### NFR-UOW008-TEST-003. Property-Based Tests

PBT must cover pure or bounded logic:

- env-to-config mapping
- checkpoint serialization round trip
- S3 key/ref safety
- MCP response JSON serialization
- quality fixture invariants
- secret redaction allow-list behavior

PBT must not depend on real Docker, database, object storage, MCP server, or live network behavior.

### NFR-UOW008-TEST-004. Optional Smoke Tests

Optional smoke tests may cover:

- Docker image startup
- PostgreSQL checkpoint table creation
- Garage/S3-compatible upload
- MCP server tool listing/call
- live FMKorea smoke with tiny read-only request

They must require explicit marker and environment flag activation.

## Acceptance Criteria

- Default package import remains side-effect free.
- Container entrypoint validates required env before starting a Job.
- `.dockerignore` excludes local state, secrets, docs, workflow artifacts, caches, outputs, and build artifacts.
- `docker-entrypoint.sh` delegates to `python -m fmkorea_scraper.adapters.container "$@"` with Linux-compatible line endings.
- PostgreSQL checkpoint adapter can save, load, and load latest checkpoint.
- S3 output adapter returns only after fake/client upload success.
- S3 refs do not expose credentials.
- MCP tools return JSON-serializable success and safe error payloads.
- Quality harness validates JSONL/report fixtures without Polars by default.
- Polars checks are optional and skipped when the extra is absent.
- Default tests run without Docker, Garage, PostgreSQL, MCP server, or live network.
