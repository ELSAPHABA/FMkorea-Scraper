# NFR Requirements - UOW-001 Core Models And Config

## Scope

This document defines non-functional requirements for `UOW-001 Core Models And Config`.

In scope:

- Pydantic v2 model validation
- public input/config schema safety
- source JSONL, checkpoint, failure, and report schema compatibility
- error redaction contract
- model serialization and validation properties
- dependency and maintainability constraints

Out of scope:

- HTTP retry/rate-limit implementation
- parser selector behavior
- concrete local/S3/PostgreSQL storage implementation
- container runtime infrastructure
- MCP server registration
- AWS CDK resources

## Security Requirements

### NFR-SEC-001. Strict Input Validation

All public input/config models must use explicit validation constraints.

Required controls:

- type validation
- max string length for public input fields
- max array/list counts for public request fields
- URL format validation where applicable
- allowed enum values for job type, content block type, comment mode, media mode, storage mode, checkpoint status, and stop reason
- `extra="forbid"` for public input/config/result models

Security mapping:

- SECURITY-05: compliant for UOW-001 input schema design
- SECURITY-13: compliant by safe Pydantic validation and safe JSON serialization

### NFR-SEC-002. Metadata Bounds

`metadata` fields must be constrained.

Requirements:

- metadata must be JSON-serializable
- metadata values may only contain primitives, lists, and dicts
- metadata depth must have a configured upper bound
- serialized metadata byte size must have a configured upper bound
- metadata must not be used to bypass top-level schema constraints

### NFR-SEC-003. Error Redaction

Adapter-facing `ErrorResult.details` must not include raw input values by default.

Allowed fields:

- error code
- field path
- safe reason
- retryable flag
- safe context labels

Forbidden fields:

- proxy password
- raw cookie
- token
- full `.env` content
- full credential file content
- raw environment variable dump
- raw URL query when it may contain secret material
- internal stack trace

Security mapping:

- SECURITY-03: supports sensitive-data-safe structured logging
- SECURITY-09: prevents internal/raw error detail exposure
- SECURITY-15: supports safe user-facing errors

### NFR-SEC-004. Import Side-Effect Safety

Importing `fmkorea_scraper` must not read credentials, write files, prompt users, create output directories, load `.env`, load `user-agents.txt`, or perform network calls.

This protects library, CLI, test, and MCP usage from accidental side effects.

## Reliability And Resiliency Requirements

### NFR-REL-001. Deterministic Validation

For identical input data and identical dependency versions, model validation must produce the same output or the same validation error.

### NFR-REL-002. Schema Versioning

Persisted top-level models must include schema versions:

- `PostResult.schema_version = "fmkorea.post.v1"`
- `Checkpoint.schema_version = "fmkorea.checkpoint.v1"`
- `FailureRecord.schema_version = "fmkorea.failure.v1"`
- `JobReport.schema_version = "fmkorea.job_report.v1"`

Same major version compatibility policy:

- field removal is forbidden
- field type change is forbidden
- required field addition is forbidden
- nullable field addition is allowed
- enum value addition requires migration note and downstream compatibility review

### NFR-REL-003. Checkpoint Model Consistency

Checkpoint status/reason validation must prevent invalid persisted states.

Rules:

- `status="stopped"` requires `reason`
- non-stopped status requires `reason=null`
- `updated_at` must be UTC-compatible

Resiliency mapping:

- RESILIENCY-10: supports fail-closed error paths
- RESILIENCY-12: concrete backup/storage is N/A for this unit
- RESILIENCY-15: supports incident-safe structured error state

### NFR-REL-004. BEST Comment Consistency

BEST comment model state must be internally consistent.

Rules:

- `is_best=true` should include `"BEST"` in `badges` when the source UI exposes the label.
- `comment_mode="best_only"` must not persist non-BEST comments.
- `reactions.score` must equal `up_count - down_count`.

## Performance Requirements

### NFR-PERF-001. Model Overhead Must Not Be The Primary Bottleneck

Single `PostResult` validation and JSON serialization must not become the primary bottleneck for normal post fixtures.

No fixed millisecond SLA is set in this unit. Exact measurement belongs to UOW-004/UOW-005 integration when real post/comment payload sizes are available.

### NFR-PERF-002. Avoid Unbounded Validation Work

Validation must reject or bound data structures that can grow recursively or unexpectedly.

Required bounds:

- metadata depth
- metadata serialized size
- public request list sizes
- content block count
- comment count accepted in one modeled payload, with final thresholds decided during parser/job integration

## Maintainability Requirements

### NFR-MAINT-001. Public Contract Documentation

Public models, enums, and port protocols must have code docstrings and corresponding markdown contract documentation.

When a public model changes, the change must update:

- schema version policy if needed
- migration note if compatibility is affected
- tests or generated sample fixtures

### NFR-MAINT-002. Downstream Stability

The model contract must remain stable for:

- CLI
- container adapter
- MCP tools
- JSONL storage
- Polars normalization
- future RAG/chunking pipelines

### NFR-MAINT-003. Community-Specific Schema Boundaries

FMKorea source JSONL keeps FMKorea-native fields only.

Common schema normalization may synthesize cross-community fields later, but source JSONL must not be polluted with fields that are not native to this scraper.

## Testing Requirements

### NFR-TEST-001. Example-Based Tests

UOW-001 must include example tests for:

- valid minimal `JobConfig` per source type
- invalid source/job type mismatch
- invalid realtime termination condition
- invalid deep search without range
- invalid stopped checkpoint without reason
- BEST comment consistency
- error redaction excluding secret-like data

### NFR-TEST-002. Property-Based Tests

UOW-001 must include Hypothesis property-based tests for:

- JSON serialization/deserialization round trip
- `JobConfig` discriminator validation
- date range invariant
- document number range invariant
- realtime termination invariant
- content block order invariant
- BEST comment invariant
- checkpoint status/reason invariant
- schema version preservation

PBT mapping:

- PBT-01: properties identified in Functional Design and this NFR document
- PBT-02: JSON round trip
- PBT-03: validation invariants
- PBT-04: schema/error normalization idempotence where implemented
- PBT-07: domain-specific generators required
- PBT-08: seed logging and shrinking required
- PBT-09: Hypothesis selected
- PBT-10: PBT complements example tests

## Extension Compliance Summary

### Security Baseline

| Rule | Status | Rationale |
|---|---|---|
| SECURITY-01 | N/A | UOW-001 defines models only, no persistence resource |
| SECURITY-02 | N/A | No network intermediary in this unit |
| SECURITY-03 | Compliant | Error and logger contracts prohibit secret logging |
| SECURITY-04 | N/A | No HTML-serving endpoint |
| SECURITY-05 | Compliant | Strict input validation and bounds required |
| SECURITY-06 | N/A | No IAM policy in this unit |
| SECURITY-07 | N/A | No network configuration in this unit |
| SECURITY-08 | N/A | No authenticated resource endpoint |
| SECURITY-09 | Compliant | ErrorResult redaction and safe messages required |
| SECURITY-10 | Compliant | dependency pinning and lock file required |
| SECURITY-11 | Compliant | validation and error boundaries are separated |
| SECURITY-12 | N/A | No user authentication in this unit |
| SECURITY-13 | Compliant | safe validation and JSON serialization required |
| SECURITY-14 | N/A | alerting implemented in later runtime/infrastructure units |
| SECURITY-15 | Compliant | typed exceptions and adapter-safe errors required |

### Resiliency Baseline

| Rule | Status | Rationale |
|---|---|---|
| RESILIENCY-01 | N/A | UOW-001 is a library/model unit, not deployable alone |
| RESILIENCY-02 | N/A | recovery targets already captured globally; no stateful deployment here |
| RESILIENCY-03 | N/A | change process already captured globally |
| RESILIENCY-04 | N/A | deployment handled in later units |
| RESILIENCY-05 | N/A | runtime monitoring handled in later units |
| RESILIENCY-06 | N/A | no service health endpoint in this unit |
| RESILIENCY-07 | N/A | no deployed capacity in this unit |
| RESILIENCY-08 | N/A | no topology in this unit |
| RESILIENCY-09 | N/A | no compute scaling in this unit |
| RESILIENCY-10 | Compliant | timeout/retry implementation is later, but fail-closed model states are required |
| RESILIENCY-11 | N/A | no DR strategy for standalone models |
| RESILIENCY-12 | N/A | no backup resource in this unit |
| RESILIENCY-13 | N/A | failover runbooks are later infrastructure work |
| RESILIENCY-14 | N/A | resiliency testing belongs to later runtime/infrastructure stages |
| RESILIENCY-15 | Compliant | structured error states support incident triage |

### Property-Based Testing

| Rule | Status | Rationale |
|---|---|---|
| PBT-01 | Compliant | model properties are identified |
| PBT-02 | Compliant | JSON round trip required |
| PBT-03 | Compliant | range/status/content/comment invariants required |
| PBT-04 | Compliant | schema/error normalization idempotence applies where implemented |
| PBT-05 | N/A | no alternate oracle implementation in this unit |
| PBT-06 | N/A | no mutable state machine in this unit |
| PBT-07 | Compliant | domain-specific Hypothesis generators required |
| PBT-08 | Compliant | seed logging and shrinking required |
| PBT-09 | Compliant | Hypothesis selected |
| PBT-10 | Compliant | PBT complements example tests |
