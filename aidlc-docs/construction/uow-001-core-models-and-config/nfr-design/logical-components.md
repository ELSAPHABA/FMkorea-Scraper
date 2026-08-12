# Logical Components - UOW-001 Core Models And Config

## Component Overview

UOW-001 logical components define shared contracts used by later runtime, parser, storage, CLI, container, and MCP units.

| Component | Purpose |
|---|---|
| `StrictBaseModel` | common Pydantic v2 configuration |
| `MetadataValidator` | reusable metadata depth/type/size validation |
| `JobConfigValidator` | raw adapter input to validated `JobConfig` |
| `ErrorMapper` | typed exception to `ErrorResult` mapping |
| `SecretRedactor` | allowlist-based safe details redaction |
| `SchemaSnapshot` | generated persisted-schema snapshot |
| `SchemaSnapshotWriter` | snapshot fixture writer for tests/code generation |
| `SchemaCompatibilityChecker` | compatibility check between schema snapshots |
| `DomainStrategies` | reusable Hypothesis strategies for model tests |
| `SmokeBenchmark` | optional model validation/serialization timing |
| `Ports` | protocol definitions for external dependencies |

## StrictBaseModel

Responsibilities:

- set `extra="forbid"`
- provide JSON serialization convention
- centralize shared model config
- keep import side-effect free

Consumers:

- request models
- config models
- result models
- checkpoint/failure/report models

## MetadataValidator

Responsibilities:

- validate metadata is JSON-compatible
- enforce maximum depth
- enforce serialized byte size
- reject unsafe Python objects

Inputs:

- `metadata: dict[str, Any]`
- `max_depth`
- `max_bytes`

Output:

- normalized metadata dict

Used by:

- model validators on every model with `metadata`

## JobConfigValidator

Responsibilities:

- convert CLI/env/MCP/library raw input into `JobConfig`
- normalize adapter-level input shapes
- delegate local model invariants to Pydantic
- return typed validation errors with field paths

It does not:

- perform network checks
- test if a post URL currently exists
- create output directories
- load proxy, cookie, or user-agent files at import time

## ErrorMapper

Responsibilities:

- map typed exceptions to stable error codes
- create user-safe messages
- attach candidate safe details
- mark retryability

Example exception mappings:

| Exception | Error Code | Retryable |
|---|---|---|
| `ValidationFailure` | `validation_error` | false |
| `UnsupportedSourceError` | `unsupported_source` | false |
| `CaptchaDetectedError` | `captcha_detected` | true |
| `BlockedResponseError` | `blocked_response` | true |
| `ParseFailureError` | `parse_failure` | false |
| `StorageFailureError` | `storage_failure` | true |
| `CheckpointFailureError` | `checkpoint_failure` | true |

## SecretRedactor

Responsibilities:

- drop raw input values by default
- allow only known-safe detail keys
- redact secret-like keys by name
- redact secret-like string values by pattern when possible

Default allowlist:

- `field_path`
- `reason`
- `stage`
- `source_type`
- `retryable`
- `schema_version`

## SchemaSnapshot

Responsibilities:

- store generated schema structure
- store schema version
- store model name
- store stable hash for comparison

Initial persisted schemas:

- `fmkorea.post.v1`
- `fmkorea.checkpoint.v1`
- `fmkorea.failure.v1`
- `fmkorea.job_report.v1`

## SchemaSnapshotWriter

Responsibilities:

- generate snapshots from current Pydantic models
- write stable snapshot fixtures during code generation
- keep key ordering deterministic

Persistence:

- committed fixture under `tests/snapshots/` or an equivalent schema snapshot directory

## SchemaCompatibilityChecker

Responsibilities:

- compare current schema snapshot to committed snapshot
- classify changes
- fail on same-major breaking changes
- report migration-note-required changes

Change classes:

- `compatible`
- `migration_note_required`
- `breaking`

## DomainStrategies

Responsibilities:

- provide reusable Hypothesis strategies
- generate structurally valid domain models
- include boundary values
- preserve business constraints

Strategy modules:

- `tests/strategies/job_configs.py`
- `tests/strategies/post_results.py`
- `tests/strategies/content_blocks.py`
- `tests/strategies/comments.py`
- `tests/strategies/checkpoints.py`
- `tests/strategies/errors.py`

## SmokeBenchmark

Responsibilities:

- validate representative model payloads
- serialize representative model payloads
- report elapsed time for local inspection

Rules:

- not a CI gate in UOW-001
- may become a thresholded integration guard after UOW-004/UOW-005

## Ports

### HttpPort

Defines async HTTP call contract for later runtime unit.

Methods:

- `get`
- `post`
- `download`
- `close`

### OutputStorePort

Defines async result output contract.

Methods:

- `append_post`
- `write_report`
- `finalize`

### MediaStorePort

Defines async media save contract.

Methods:

- `save_media`
- `save_metadata_only`

### FailureStorePort

Defines async failure record contract.

Methods:

- `write_failure`
- `read_failures`

### CheckpointStorePort

Defines async checkpoint persistence contract.

Methods:

- `save`
- `load`
- `load_latest`

### ClockPort

Defines time source contract.

Methods:

- `now_utc`
- `sleep`

### LoggerPort

Defines structured logging contract.

Methods:

- `debug`
- `info`
- `warning`
- `error`

## Interaction Flows

### Validation Flow

1. Adapter/library caller provides raw input.
2. `JobConfigValidator` normalizes raw input.
3. Pydantic validates typed models and local invariants.
4. Valid `JobConfig` is returned or a typed validation exception is raised.

### Error Flow

1. Core raises a typed exception.
2. Adapter catches the exception.
3. `ErrorMapper` creates candidate `ErrorResult` fields.
4. `SecretRedactor` applies allowlist redaction.
5. Adapter returns or logs only the safe result.

### Schema Compatibility Flow

1. Code generation creates or updates persisted model classes.
2. `SchemaSnapshotWriter` generates current snapshots.
3. `SchemaCompatibilityChecker` compares current snapshots with committed snapshots.
4. Same-major breaking changes fail tests.
5. Enum additions and other compatible-but-visible changes require migration notes.

### PBT Flow

1. `DomainStrategies` generates valid and boundary model data.
2. Example tests cover named invalid cases.
3. Property tests check round trip and invariants.
4. Failing seeds are retained by Hypothesis output.

## Exclusions

These components are not introduced in UOW-001:

- migration registry
- full data migration runner
- request-type-specific HTTP ports
- storage-implementation-specific ports
- parser/service interface hierarchy
- runtime circuit breaker
- queue, cache, or scheduler infrastructure
