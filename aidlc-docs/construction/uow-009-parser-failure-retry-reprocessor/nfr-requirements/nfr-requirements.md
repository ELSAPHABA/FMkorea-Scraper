# NFR Requirements - UOW-009 Parser Failure Retry Reprocessor

## Scope

This document defines non-functional requirements for `UOW-009 Parser Failure Retry Reprocessor`.

In scope:

- local and S3/Garage failure input reads
- parser-stage post failure selection
- existing success skip
- duplicate failure dedupe
- direct-post retry Job creation
- retry report counters
- CLI, library, and MCP execution boundary
- default fake/fixture/PBT test gate

Out of scope:

- CAPTCHA bypass
- network, storage, checkpoint, and block failure retry
- distributed DLQ or background scheduler
- parser selector changes
- S3 prefix auto-discovery
- AWS CDK

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Stream failure JSONL inputs and keep only dedupe/skip keys plus counters in memory. |
| Q2 | A | Reuse the existing `s3` optional extra and S3-compatible object boundary; add no new S3 SDK. |
| Q3 | A | Inaccessible failure or existing-post inputs fail validation before retry Job start. |
| Q4 | A | Malformed JSONL lines are counted and skipped; unreadable inputs fail validation. |
| Q5 | A | Preserve existing report fields and use `RetryReport` counters first; add only minimal optional metadata if needed. |
| Q6 | A | Restore only allowlisted options; explicit options win; `--from-report` and `--from-checkpoint` cannot be combined. |
| Q7 | A | Import retry modules without file/S3/env I/O; add import side-effect tests. |
| Q8 | A | Return safe summary output and store detailed counters in `RetryReport`/`report.json`. |
| Q9 | A | Default tests use temp files, fake object store, fake runner, fixtures, and PBT; external smoke is optional. |
| Q10 | A | Retry follows normal direct-post request interval, worker, User-Agent, and proxy policies. |

No follow-up question is required. The answers are internally consistent.

## Performance Requirements

### NFR-UOW009-PERF-001. Streaming Failure Reads

Failure JSONL inputs must be read line by line.

The implementation must not load full raw failure files into memory before selection.

### NFR-UOW009-PERF-002. Bounded In-Memory State

The retry selector may keep these structures in memory:

- dedupe key map
- existing success key set
- retry candidate list after filtering
- aggregate counters

It must not keep every invalid or ineligible raw input record.

### NFR-UOW009-PERF-003. Default Scale Target

The first implementation must comfortably handle tens of thousands of input lines and should be designed for hundreds of thousands of lines without changing the public contract.

SQLite or external queue staging is deferred until real input size shows memory pressure.

### NFR-UOW009-PERF-004. Existing Rate Policy Reuse

Retry Jobs must use the same request interval, worker count, User-Agent rotation, proxy, and HTTP retry policies as normal direct-post Jobs.

Retry mode must not increase default speed.

## Reliability And Resiliency Requirements

### NFR-UOW009-REL-001. Source Failure Input Preservation

Input failure files and S3 objects are read-only.

The retry unit must not delete, compact, overwrite, or append to source failure inputs.

### NFR-UOW009-REL-002. Input Accessibility Validation

Every declared failure input and existing-post input must be accessible before the retry Job starts.

If any input is missing or inaccessible, validation fails and no partial retry Job starts.

### NFR-UOW009-REL-003. Malformed Line Tolerance

Malformed JSONL lines inside accessible inputs are counted and excluded.

Malformed lines must not stop the whole retry unless the input itself cannot be opened or read as a line stream.

### NFR-UOW009-REL-004. Last-Wins Dedupe

Duplicate retry candidates are deduped by `(site_id, board_id, document_srl, document_id_raw)`.

When duplicate keys have different URLs, the last valid failure record wins.

### NFR-UOW009-REL-005. Existing Success Skip

Optional existing `posts.jsonl` inputs are indexed by `(site_id, board_id, document_srl, document_id_raw)`.

Candidates present in that index are skipped before retry execution.

### NFR-UOW009-REL-006. Existing Stop And Checkpoint Behavior

CAPTCHA, block detection, manual stop, and checkpoint saving must use the existing `JobRunner` behavior.

The retry unit must not implement a second stop or checkpoint system.

### NFR-UOW009-REL-007. Reported Partial Results

If retry execution starts and some posts still fail, those failures are written through the normal retry run `failures.jsonl`.

The report must include enough counters to distinguish selected, skipped, succeeded, and remaining failed posts.

## Security Requirements

### NFR-UOW009-SEC-001. Safe Failure Diagnostics

Retry reports, terminal summaries, and MCP responses must not include:

- raw HTML
- cookies
- proxy passwords
- S3 credentials
- tokens
- raw headers
- raw environment values
- stack traces

### NFR-UOW009-SEC-002. S3 Credential Isolation

S3/Garage input reads must use existing storage configuration and optional dependency boundaries.

S3 refs in user-visible output must not include credentials or signed URLs.

### NFR-UOW009-SEC-003. Restore Option Allowlist

`--from-report` and `--from-checkpoint` may restore only allowlisted scrape, worker, and storage settings.

They must not restore raw secrets, raw headers, cookies, raw request bodies, or hidden internal state.

### NFR-UOW009-SEC-004. Safe Adapter Output

CLI and MCP output must contain safe summary counts and output locations only.

Detailed invalid-line diagnostics must avoid printing raw line contents.

### NFR-UOW009-SEC-005. Import Safety

Importing retry service or adapter modules must not:

- read local files
- read S3/Garage objects
- read `.env` or raw environment maps
- create output files
- start a scrape
- perform HTTP requests

## Maintainability Requirements

### NFR-UOW009-MAINT-001. Existing Service Reuse

UOW-009 must reuse:

- `FailureRecord`
- `RetryRequest`
- `FailureInput`
- `JobConfig`
- `DirectPostSource`
- `ScrapeOptions`
- `WorkerConfig`
- `StorageConfig`
- existing output stores
- existing `JobRunner`
- existing CLI/container/MCP safe error boundaries

### NFR-UOW009-MAINT-002. Thin Adapters

CLI and MCP retry entrypoints must only validate input, build retry requests/dependencies, call `ParserFailureRetryService`, and return a safe summary.

Selection and retry orchestration logic belongs in the service.

### NFR-UOW009-MAINT-003. Small Report Extension

If current `RetryReport` cannot store retry counters, add the smallest optional metadata or summary field needed.

Do not create a parallel report schema unless later consumers require it.

### NFR-UOW009-MAINT-004. No New Scheduler

UOW-009 must not add distributed queues, background workers, or DLQ scheduling.

Those features remain future platform work.

## Test Requirements

### NFR-UOW009-TEST-001. Default Test Gate

Default tests must not require:

- Garage
- S3 network access
- live site access
- Docker
- PostgreSQL
- MCP server runtime

### NFR-UOW009-TEST-002. Required Example Tests

Default example tests must cover:

- failure JSONL streaming selection
- parser allowlist inclusion/exclusion
- malformed line tolerance
- inaccessible input validation
- duplicate last-wins behavior
- existing success skip
- option precedence
- safe summary output
- import side-effect safety
- fake runner direct-post retry execution

### NFR-UOW009-TEST-003. Required Property-Based Tests

PBT must cover at least:

- dedupe idempotency
- last-wins duplicate selection
- ineligible reason exclusion
- existing success skip never increases selected count
- explicit options always override restored options

### NFR-UOW009-TEST-004. Optional Smoke Tests

S3/Garage input reads, MCP runtime, and live retry smoke tests are optional and marker/env-gated.

They must be skipped by default.
