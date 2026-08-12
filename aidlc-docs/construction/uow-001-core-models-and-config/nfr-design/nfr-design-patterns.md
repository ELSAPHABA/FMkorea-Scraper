# NFR Design Patterns - UOW-001 Core Models And Config

## Scope

This document translates UOW-001 NFR requirements into design patterns. It covers model validation, metadata bounds, error redaction, schema compatibility, property-based testing organization, performance guardrails, and port protocol shape.

UOW-001 remains a model/config contract unit. It does not implement concrete HTTP clients, parser selectors, storage adapters, container runtime, MCP server registration, or AWS resources.

## Pattern 1. Split Validation Boundary

Use two validation layers:

| Layer | Responsibility |
|---|---|
| Pydantic field/model validators | single-model type, format, enum, length, count, and local invariant checks |
| `JobConfigValidator` facade | raw adapter input normalization and cross-model composition checks |

Examples:

- `date_from <= date_to`: model-level validator on `RangeFilter`
- `min_document_srl <= max_document_srl`: model-level validator on `RangeFilter`
- realtime exactly-one termination condition: model-level validator on `RealtimeTermination`
- `JobConfig.job_type` matches `source.type`: model-level validator on `JobConfig`
- CLI/env/MCP raw input conversion: `JobConfigValidator`

Reasoning:

- Local invariants stay close to the model.
- Adapter-specific parsing does not leak into domain models.
- CLI, container, MCP, and library callers share the same typed validation result.

## Pattern 2. Bounded Metadata

Use a shared `MetadataValidator` helper for every `metadata` field.

Rules:

- allow JSON-compatible primitives, lists, and dicts only
- reject objects, bytes, callables, and arbitrary class instances
- enforce maximum nesting depth
- enforce maximum serialized byte size
- return normalized metadata that is safe for `model_dump(mode="json")`

Design constraint:

- `metadata` is an explicit extension point, not a bypass for missing top-level schema.

## Pattern 3. Allowlist Error Redaction

Use `ErrorMapper` and `SecretRedactor` as separate components.

`ErrorMapper` responsibilities:

- map typed core exceptions to stable error codes
- create user-safe messages
- attach candidate details such as field paths and safe reasons
- set retryability

`SecretRedactor` responsibilities:

- allowlist permitted detail keys
- drop raw input values by default
- remove secret-like keys and values
- return `ErrorResult` data safe for CLI, container, and MCP

Allowed detail keys:

- `code`
- `field_path`
- `reason`
- `retryable`
- `stage`
- `source_type`
- `schema_version`

Forbidden details:

- proxy password
- raw cookie
- token
- full `.env`
- full credential file
- raw environment dump
- raw URL query when it may include secrets
- internal stack trace

## Pattern 4. Schema Snapshot Compatibility Check

Use a lightweight schema snapshot check during code generation.

Components:

- `SchemaSnapshot`
- `SchemaSnapshotWriter`
- `SchemaCompatibilityChecker`

Required behavior:

- generate JSON-schema-like snapshots from persisted Pydantic models
- commit snapshots for `fmkorea.post.v1`, `fmkorea.checkpoint.v1`, `fmkorea.failure.v1`, and `fmkorea.job_report.v1`
- compare current generated snapshots against committed snapshots
- classify changes as compatible, migration-note-required, or breaking
- fail tests on same-major breaking changes

Compatibility rules:

| Change | Same Major Version |
|---|---|
| nullable field addition | allowed |
| required field addition | breaking |
| field removal | breaking |
| existing field type change | breaking |
| enum value addition | requires migration note |
| schema version removal | breaking |

The first implementation does not include a migration registry or data migration runner.

## Pattern 5. Domain-Specific PBT Strategies

Place reusable Hypothesis strategies under `tests/strategies/`.

Strategy groups:

- `job_configs.py`
- `post_results.py`
- `content_blocks.py`
- `comments.py`
- `checkpoints.py`
- `errors.py`

Required properties:

- JSON round trip preserves model values
- invalid discriminator combinations fail validation
- range lower bound never exceeds upper bound
- realtime source has exactly one termination condition
- content block orders are unique and non-negative
- BEST comments keep `is_best`, `badges`, and reaction score consistency
- stopped checkpoint requires reason
- schema version is preserved across serialization

Shrinking and seed reproducibility must remain enabled.

## Pattern 6. Optional Smoke Benchmark

Do not make model benchmark a CI gate in UOW-001.

Design:

- provide an optional benchmark command or test marker
- use representative post/checkpoint fixtures
- record validation and JSON serialization timings
- use results as signal during UOW-004/UOW-005 integration

This avoids arbitrary performance thresholds before real parser and JobRunner payloads exist.

## Pattern 7. Minimal Port Protocol Set

Define only the first-pass external I/O ports:

- `HttpPort`
- `OutputStorePort`
- `MediaStorePort`
- `FailureStorePort`
- `CheckpointStorePort`
- `ClockPort`
- `LoggerPort`

Rules:

- request-type-specific HTTP ports are not introduced in UOW-001
- local/S3/PostgreSQL-specific storage ports are not introduced in UOW-001
- concrete adapters are implemented in later units
- parser and service classes are not wrapped in speculative protocols

## Extension Compliance

### Security

| Rule | Status | Design Response |
|---|---|---|
| SECURITY-03 | Compliant | `ErrorMapper` and `SecretRedactor` prevent secret logging |
| SECURITY-05 | Compliant | Pydantic validators and `JobConfigValidator` provide input validation |
| SECURITY-09 | Compliant | adapter-facing errors are safe and redacted |
| SECURITY-10 | Compliant | dependency pinning remains required by NFR requirements |
| SECURITY-13 | Compliant | Pydantic JSON serialization avoids unsafe deserialization |
| SECURITY-15 | Compliant | typed exceptions and safe `ErrorResult` support fail-safe errors |

Other Security Baseline rules are N/A for this model-only unit.

### Resiliency

| Rule | Status | Design Response |
|---|---|---|
| RESILIENCY-10 | Compliant | model states support fail-closed behavior |
| RESILIENCY-15 | Compliant | structured errors and checkpoint enums support incident triage |

Other Resiliency Baseline rules are N/A for this non-deployable model unit.

### Property-Based Testing

| Rule | Status | Design Response |
|---|---|---|
| PBT-01 | Compliant | testable properties identified |
| PBT-02 | Compliant | JSON round trip property required |
| PBT-03 | Compliant | range, realtime, status, content, and comment invariants required |
| PBT-04 | Compliant | schema/error normalization idempotence applies where implemented |
| PBT-07 | Compliant | domain-specific strategies under `tests/strategies/` |
| PBT-08 | Compliant | shrinking and seed reproducibility remain enabled |
| PBT-09 | Compliant | Hypothesis selected |
| PBT-10 | Compliant | example tests remain required |

PBT-05 and PBT-06 are N/A for this unit.
