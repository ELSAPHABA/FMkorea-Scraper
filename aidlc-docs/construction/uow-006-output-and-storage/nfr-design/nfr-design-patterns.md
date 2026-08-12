# NFR Design Patterns - UOW-006 Output And Storage

## Scope

This document translates UOW-006 NFR requirements into implementation patterns. It covers output package layout, JSONL writes, path sanitization, output run layout, safe failure context, atomic JSON writes, optional S3 dependency loading, S3 JSONL spool, local checkpoint document handling, optional Polars smoke tests, test organization, and optional Garage smoke tests.

## Confirmed Design Decisions

| Question | Answer | Design Decision |
|---|---|---|
| Q1 | A | Put output/storage code under `src/fmkorea_scraper/outputs/` with focused modules for layout, JSONL, local storage, S3, redaction, checkpoint, and factory creation. |
| Q2 | A | Use a small `JsonlWriter` with Pydantic JSON mode, stdlib `json`, newline append, flush, and optional fsync. |
| Q3 | A | Use `sanitize_path_segment(value, fallback)` with allow-list characters and verify resolved local paths stay below the base output directory. |
| Q4 | A | Use `OutputRunLayout` to derive local paths and S3 object keys from `job_id`, `run_id`, base path, and prefix. |
| Q5 | A | Use `sanitize_failure_context` with allow-list fields and default-drop unknown context. |
| Q6 | A | Use `AtomicJsonWriter` for `Checkpoint.json` and `report.json`; do not use it for JSONL append. |
| Q7 | A | Lazy import `boto3` inside `S3ObjectStore`; local imports must work without S3 packages. |
| Q8 | A | Use `S3JsonlSpool` or `SpoolingJsonlUploader` for file-backed append plus same-key upload. |
| Q9 | A | Let `LocalCheckpointStore` own process-local lock, checkpoint document load/validate, job replacement, and `load_latest()`. |
| Q10 | A | Keep Polars smoke as optional test-only behavior, skipped when Polars is absent. |
| Q11 | A | Put default output tests, PBT, strategies, S3 smoke, and Polars smoke in separate files. |
| Q12 | A | Run Garage/S3 smoke only with `FMKOREA_S3_SMOKE_ENABLED=true` and complete S3 env. |

No follow-up question is required.

## Pattern 1. Output Package Layout

UOW-006 implementation belongs under:

```text
src/fmkorea_scraper/outputs/
  __init__.py
  layout.py
  jsonl.py
  local.py
  s3.py
  redaction.py
  checkpoint.py
  factory.py
```

Responsibilities:

- `layout.py`: path and object key derivation
- `jsonl.py`: JSONL append and atomic JSON helpers
- `local.py`: local output, failure, and media stores
- `s3.py`: S3-compatible object store and JSONL spool
- `redaction.py`: failure context allow-list redaction
- `checkpoint.py`: local `Checkpoint.json` document store
- `factory.py`: storage creation from `StorageConfig`

Package import must not require S3, Polars, external services, file writes, or environment reads.

## Pattern 2. JSONL Writer

`JsonlWriter` owns newline-delimited JSON append.

Responsibilities:

- accept a Pydantic model or dict
- call `model_dump(mode="json")` for Pydantic models
- encode through stdlib `json.dumps(ensure_ascii=False)`
- append one newline
- flush after each record
- optionally call `fsync` when configured

It does not validate scraper business rules. Model validation remains in UOW-001 models.

## Pattern 3. Path Sanitization And Containment

`sanitize_path_segment(value, fallback)`:

- converts input to string
- keeps only `[A-Za-z0-9._-]`
- replaces all other characters with `_`
- strips leading/trailing unsafe separators
- returns `fallback` when the result is empty

`ensure_under_base(base, target)` resolves both paths and rejects targets outside `base`.

Use this for:

- `job_id`
- `run_id`
- `board_id`
- `document_srl`
- `document_id_raw`
- `media_type`
- media filenames

## Pattern 4. OutputRunLayout

`OutputRunLayout` derives all run paths and keys.

Inputs:

- `job_id`
- `run_id`
- `base_output_path`
- optional S3 prefix

Outputs:

- local `posts.jsonl` path
- local `failures.jsonl` path
- local `report.json` path
- local media path
- matching S3 object keys

The local and S3 layouts must use the same relative path contract:

```text
outputs/<job_id>/<run_id>/posts.jsonl
outputs/<job_id>/<run_id>/failures.jsonl
outputs/<job_id>/<run_id>/report.json
outputs/<job_id>/<run_id>/media/<board_id>/<document_srl_or_raw_id>/<media_type>/<filename>
```

## Pattern 5. Safe Failure Context

Failure context uses allow-list serialization.

Allowed fields:

- `job_id`
- `stage`
- `reason`
- `retryable`
- `url`
- `post_key`
- `safe_message`
- `http_status`
- `response_kind`
- `parser_warning_code`

Forbidden fields:

- proxy ID
- proxy password
- cookies
- tokens
- passwords
- raw headers
- raw HTML/body/content
- credential file contents

Unknown fields are dropped by default.

## Pattern 6. Atomic JSON Writer

`AtomicJsonWriter` writes small single-document JSON files.

Flow:

1. create temp file in the target directory
2. write UTF-8 JSON
3. flush the file
4. replace the target with `os.replace`

Used for:

- `Checkpoint.json`
- `report.json`

Not used for:

- `posts.jsonl`
- `failures.jsonl`
- media files

## Pattern 7. S3 Optional Dependency Boundary

`S3ObjectStore` lazy-loads `boto3`.

Rules:

- package import must succeed without S3 dependencies
- local storage tests must run without S3 dependencies
- S3 mode without `boto3` raises a clear configuration error
- object keys mirror local relative paths
- Garage-specific APIs are not required
- custom S3 signing is not implemented

## Pattern 8. S3 JSONL Spool

S3-compatible JSONL output uses a file-backed spool.

Flow:

1. append one JSONL record to local spool
2. flush spool writer
3. upload the full spool file to the configured object key
4. return `StoredObjectRef` only after upload succeeds

The same object key is reused for every append in the same run. This preserves the Job-level `posts.jsonl` and `failures.jsonl` contract.

## Pattern 9. Local Checkpoint Document

`LocalCheckpointStore` owns `Checkpoint.json`.

Responsibilities:

- hold a process-local lock
- load existing checkpoint document
- validate document shape
- replace one `job_id` entry on save
- write through `AtomicJsonWriter`
- implement `load(job_id)`
- implement `load_latest()` by `updated_at`

Logical file shape:

```json
{
  "schema_version": "fmkorea.local_checkpoint.v1",
  "updated_at": "2026-08-12T00:00:00Z",
  "checkpoints": {
    "<job_id>": {}
  }
}
```

## Pattern 10. Optional Polars Smoke

Polars smoke is test-only.

Rules:

- import Polars inside the test
- skip explicitly when Polars is not installed
- write a small source `posts.jsonl` fixture through UOW-006 output path
- verify `read_ndjson`
- verify top-level post identity projection
- verify nested `comments` explode
- verify `content.blocks` and `media` projection

No production normalization module is created in UOW-006.

## Pattern 11. Test Organization

Default tests:

- `tests/test_outputs_storage.py`
- `tests/test_outputs_properties.py`
- `tests/strategies/outputs.py`

Optional tests:

- `tests/test_outputs_s3_smoke.py`
- `tests/test_outputs_polars_smoke.py`

Default pytest must not require Garage, S3 credentials, Polars, or external services.

## Pattern 12. Garage Smoke Guard

Garage/S3 smoke runs only when:

- `FMKOREA_S3_SMOKE_ENABLED=true`
- endpoint env exists
- bucket env exists
- access key env exists
- secret key env exists

Smoke scope:

- put one small object
- get or head the object
- delete the object

It does not run a full scraper Job.

## Compliance Mapping

| Requirement Area | Design Pattern |
|---|---|
| append-only JSONL | `JsonlWriter` |
| atomic checkpoint/report | `AtomicJsonWriter` |
| path traversal prevention | `sanitize_path_segment`, `ensure_under_base` |
| local/S3 layout parity | `OutputRunLayout` |
| failure redaction | `sanitize_failure_context` allow-list |
| local checkpoint concurrency | process-local lock in `LocalCheckpointStore` |
| optional S3 dependency | lazy import in `S3ObjectStore` |
| S3 same-key JSONL append | `S3JsonlSpool` |
| optional Polars analysis smoke | optional Polars test file |
| deterministic tests | local example tests and PBT |
| optional external test | env-gated Garage smoke |
