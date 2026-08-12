# NFR Requirements - UOW-006 Output And Storage

## Scope

This document defines non-functional requirements for `UOW-006 Output And Storage`.

In scope:

- Job JSONL output
- failure JSONL output
- final Job report output
- local media storage
- S3-compatible object storage boundary
- Garage default object storage target
- local `Checkpoint.json` persistence
- source JSONL Polars smoke checks

Out of scope:

- worker queue lifecycle
- retry scheduling
- HTTP media download
- PostgreSQL checkpoint adapter
- CLI prompt UX
- container/MCP hosting
- AWS CDK

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | JSONL appends flush after each record; OS-level fsync is optional and disabled by default. |
| Q2 | A | `Checkpoint.json` and `report.json` use temp-file replace; JSONL remains append-only and recoverable by line validation. |
| Q3 | A | All path segments from user or remote input are allow-list sanitized, and resolved local paths must remain under the base output directory. |
| Q4 | A | Failure redaction uses allow-list safe context only and drops proxy credentials, cookies, tokens, passwords, raw headers, and raw body/html/content. |
| Q5 | A | S3-compatible upload uses optional `s3` extra with `boto3`; no custom signing and no core dependency expansion. |
| Q6 | A | S3-compatible JSONL append uses a run-local spool file and uploads the same object key after each append. |
| Q7 | A | Local checkpoint concurrency targets single process/single Job writes with process-local locking and atomic replace. |
| Q8 | A | Default tests cover local storage, JSONL round trip, media save, checkpoint load/save/latest, traversal rejection, redaction, and S3 key generation. |
| Q9 | A | PBT targets pure storage transforms: path sanitize, object key generation, JSONL round trip, checkpoint document round trip, and redaction idempotence. |
| Q10 | A | Polars smoke tests run only when the optional `analysis` extra is installed; otherwise they explicitly skip. |
| Q11 | A | JSONL writes stream record-by-record and S3 spool uses files, not full in-memory JSONL buffers. |
| Q12 | A | PostgreSQL checkpoint NFR remains deferred to UOW-008. |

No follow-up question is required. The answers are internally consistent.

## Performance Requirements

### NFR-UOW006-PERF-001. Append-Only JSONL

Post and failure outputs must append one line at a time.

The implementation must not rewrite the whole JSONL file per record.

### NFR-UOW006-PERF-002. Default Flush Policy

Each JSONL append must flush Python/user-space buffers after the record is written.

OS-level `fsync` must be available as an option but disabled by default.

### NFR-UOW006-PERF-003. Streaming Serialization

JSONL serialization must process one record at a time.

The store must not keep the full `posts.jsonl` or `failures.jsonl` content in memory.

### NFR-UOW006-PERF-004. File-Based S3 Spool

S3-compatible JSONL output must use a file-backed spool.

The spool must not require loading the entire JSONL object into memory before upload.

### NFR-UOW006-PERF-005. Bounded Local Checkpoint Size

`Checkpoint.json` stores only the latest checkpoint per `job_id`.

It must not store historical checkpoint snapshots for every update.

## Reliability And Resiliency Requirements

### NFR-UOW006-REL-001. Atomic Single-Document Writes

`Checkpoint.json` and `report.json` must be written through:

1. write temp file in the same directory
2. flush file content
3. replace target file atomically

### NFR-UOW006-REL-002. JSONL Recovery Boundary

JSONL files are append-only.

If a process stops during append, later recovery may ignore the final invalid partial line. UOW-006 does not rewrite the full file to repair it.

### NFR-UOW006-REL-003. Resume-Safe Output Layout

Resume must use the same `job_id` and a new `run_id`.

The resumed run must write to a new run directory and must not append to the previous run's `posts.jsonl` or `failures.jsonl`.

### NFR-UOW006-REL-004. S3 Durable Append Boundary

In S3-compatible mode, `append_post` and `write_failure` must return success only after the updated spool is uploaded to the configured object key.

UOW-005 must checkpoint only after that returned success.

### NFR-UOW006-REL-005. Storage Error Propagation

Local write, serialization, media write, checkpoint write, and S3 upload failures must be surfaced as typed storage errors with safe details.

The storage layer must not silently drop failed writes.

### NFR-UOW006-REL-006. Local Checkpoint Concurrency Boundary

Local checkpoint writes must be protected by a process-local lock.

Multi-process checkpoint concurrency is out of scope for local mode and belongs to the PostgreSQL checkpoint adapter in UOW-008.

## Security Requirements

### NFR-UOW006-SEC-001. Path Traversal Prevention

Every user or remote input used in a local path segment must be sanitized with an allow-list rule.

After joining paths, the resolved path must be verified to stay under the configured output base directory.

### NFR-UOW006-SEC-002. Safe Failure Context

Failure output may contain:

- `job_id`
- `stage`
- `reason`
- `retryable`
- `url`
- `post_key`
- `safe_message`
- HTTP status code
- response kind
- parser warning code

Failure output must not contain:

- proxy ID
- proxy password
- cookies
- tokens
- passwords
- raw headers
- raw HTML/body/content
- credential file contents

### NFR-UOW006-SEC-003. Allow-List Redaction

Failure redaction must use allow-list serialization.

Unknown context fields must be dropped unless explicitly added to the safe list.

### NFR-UOW006-SEC-004. Credential-Free Storage Metadata

`StoredObjectRef`, `MediaItem.file_path`, `MediaItem.object_key`, JSONL records, and report files must not contain S3 credentials, proxy credentials, cookies, tokens, or passwords.

### NFR-UOW006-SEC-005. Local Output Ignore Policy

Local runtime outputs must remain excluded from version control:

- `.env`
- `Checkpoint.json`
- `outputs/`
- downloaded media files
- generated object-store credentials

## Maintainability Requirements

### NFR-UOW006-MAINT-001. Port Boundary

All storage implementations must satisfy UOW-001 ports:

- `OutputStorePort`
- `MediaStorePort`
- `FailureStorePort`
- `CheckpointStorePort`

Adapters and JobRunner code must depend on these ports, not concrete file/S3 implementations.

### NFR-UOW006-MAINT-002. Standard Library First

Local storage must use Python standard library primitives where sufficient:

- `json`
- `pathlib`
- `tempfile`
- `os.replace`
- process-local locks

### NFR-UOW006-MAINT-003. Optional S3 Dependency

S3-compatible storage dependencies must be optional and installed only when S3 output is used.

Core local JSONL/checkpoint usage must work without S3 client packages.

### NFR-UOW006-MAINT-004. Optional Polars Dependency

Polars must remain in the optional `analysis` extra.

Core output storage must work without Polars installed.

### NFR-UOW006-MAINT-005. PostgreSQL Scope Guard

UOW-006 must not implement PostgreSQL checkpoint storage.

PostgreSQL security, concurrency, migration, and deployment requirements belong to UOW-008.

## Test Requirements

### NFR-UOW006-TEST-001. Default Test Gate

Default tests must cover:

- local `posts.jsonl` append
- local `failures.jsonl` append
- `report.json` atomic write
- JSONL round trip
- media bytes save
- metadata-only media save
- checkpoint save/load
- checkpoint `load_latest`
- path traversal rejection
- failure redaction
- S3 object key generation
- S3 JSONL spool key reuse behavior

### NFR-UOW006-TEST-002. Property-Based Tests

PBT must cover:

- path segment sanitization
- output key generation
- JSONL serialization round trip
- checkpoint document round trip
- failure redaction idempotence

### NFR-UOW006-TEST-003. Optional Garage Smoke

Actual Garage/S3-compatible integration test must be optional and env-gated.

It must not be part of default unit tests or mandatory local CI.

### NFR-UOW006-TEST-004. Optional Polars Smoke

Polars source JSONL smoke must be optional and skip explicitly when Polars is not installed.

When enabled, it must verify:

- `read_ndjson` can read source `posts.jsonl`
- top-level identity fields can be projected
- nested `comments` can be exploded
- `content.blocks` and `media` can be projected

## Acceptance Criteria

- Local output writes one valid JSON object per line.
- Resume output uses a new `run_id` directory.
- `Checkpoint.json` can save/load multiple latest Job checkpoints.
- `load_latest()` returns the newest checkpoint.
- Unsafe local paths are rejected.
- Failure records omit credentials and raw response data.
- Media storage does not perform HTTP download.
- S3-compatible output works through optional `s3` extra.
- Polars smoke works through optional `analysis` extra.
- Core package still imports without S3 or Polars extras installed.
