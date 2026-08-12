# Logical Components - UOW-006 Output And Storage

## Component Overview

UOW-006 logical components store already-produced scraper results. They do not collect links, fetch posts, download media, run workers, or own checkpoint commit ordering.

| Component | Purpose |
|---|---|
| `OutputRunLayout` | derives sanitized local paths and S3 object keys for one `job_id`/`run_id` |
| `JsonlWriter` | appends one validated model/dict as one JSONL record |
| `AtomicJsonWriter` | writes small JSON documents with temp-file replace |
| `LocalOutputStore` | writes `posts.jsonl` and `report.json` locally |
| `LocalFailureStore` | writes and reads `failures.jsonl` locally |
| `LocalMediaStore` | writes media bytes locally or returns metadata-only media |
| `LocalCheckpointStore` | saves and loads local `Checkpoint.json` |
| `LocalCheckpointDocument` | in-file map of latest checkpoints keyed by `job_id` |
| `S3ObjectStore` | writes output/media objects through an optional S3-compatible client |
| `S3JsonlSpool` | file-backed JSONL append plus same-key S3 upload |
| `sanitize_failure_context` | redacts safe failure context through allow-list rules |
| `outputs.layout` | path sanitization and containment helpers |
| `StorageFactory` | creates local or S3-compatible stores from `StorageConfig` |
| `tests/strategies/outputs.py` | reusable Hypothesis strategies for storage transforms |

## OutputRunLayout

Responsibilities:

- accept `job_id`, `run_id`, and optional base/prefix
- sanitize path segments
- provide paths for `posts.jsonl`, `failures.jsonl`, `report.json`, and media
- provide matching S3 object keys
- reject local paths that escape the base output directory

Default relative structure:

```text
outputs/<job_id>/<run_id>/
  posts.jsonl
  failures.jsonl
  report.json
  media/<board_id>/<document_srl_or_raw_id>/<media_type>/<filename>
```

## JsonlWriter

Responsibilities:

- serialize Pydantic models with `model_dump(mode="json")`
- serialize dict values through stdlib `json`
- write UTF-8
- append newline
- flush per record
- optionally fsync per record

Consumers:

- `LocalOutputStore.append_post`
- `LocalFailureStore.write_failure`
- `S3JsonlSpool.append`

## AtomicJsonWriter

Responsibilities:

- write JSON to a temp file in the target directory
- flush the temp file
- atomically replace the target path with `os.replace`

Consumers:

- `LocalOutputStore.write_report`
- `LocalCheckpointStore.save`

## LocalOutputStore

Implements `OutputStorePort`.

Responsibilities:

- create the run directory
- append `PostResult` to `posts.jsonl`
- write final `JobReport` to `report.json`
- return `StoredObjectRef` values with `storage_mode=local`
- finalize or close pending writer state

Boundaries:

- does not deduplicate posts
- does not update checkpoints
- does not download media
- does not store secrets

## LocalFailureStore

Implements `FailureStorePort`.

Responsibilities:

- append safe `FailureRecord` values to `failures.jsonl`
- use `sanitize_failure_context` before serializing optional details
- read failure records back for later parser-failure retry input
- return `StoredObjectRef` values with `storage_mode=local`

Boundaries:

- does not classify retry policy
- does not schedule retry Jobs
- does not preserve unsafe context fields

## LocalMediaStore

Implements `MediaStorePort`.

Responsibilities:

- receive `MediaItem` and bytes from caller
- save bytes under the run media directory
- return `MediaItem` with `file_path`
- return unchanged or metadata-only updated `MediaItem` for metadata mode

Boundaries:

- does not create HTTP clients
- does not fetch URLs
- does not decide which media should be downloaded

## LocalCheckpointStore

Implements `CheckpointStorePort`.

Responsibilities:

- save multiple latest checkpoints in `Checkpoint.json`
- load by `job_id`
- load latest by `updated_at`
- guard in-process access with a local lock
- write using `AtomicJsonWriter`

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

## S3ObjectStore

Implements S3-compatible object writing.

Responsibilities:

- lazy import `boto3`
- validate S3 mode has required config
- write JSONL/report/media objects to configured bucket
- return `StoredObjectRef` values with `storage_mode=s3_compatible`
- build keys from `OutputRunLayout`

Boundaries:

- no Garage-specific API dependency
- no custom S3 signing
- no package-level S3 import
- no default test dependency on Garage

## S3JsonlSpool

Responsibilities:

- maintain a file-backed spool for one JSONL object
- append one JSONL record through `JsonlWriter`
- upload the updated spool to the same S3 object key
- return `StoredObjectRef` only after upload success

Consumers:

- S3-compatible post output
- S3-compatible failure output

## Failure Redaction

`sanitize_failure_context` responsibilities:

- accept failure context from callers
- keep only allow-list fields
- drop unknown fields by default
- reject proxy credentials, cookies, tokens, passwords, raw headers, and raw HTML/body/content

Output:

- safe metadata dict
- or safe `details` content merged before `FailureRecord` serialization

## Pathing Helpers

`sanitize_path_segment(value, fallback)`:

- allow-list characters
- replace unsafe characters with `_`
- return fallback if empty

`ensure_under_base(base, target)`:

- resolve paths
- reject traversal outside base

These helpers are pure enough for PBT.

## StorageFactory

Responsibilities:

- inspect `StorageConfig`
- create local output, failure, media, and checkpoint stores
- create S3-compatible stores only when selected
- avoid importing S3 dependencies for local mode
- raise clear configuration errors for unsupported combinations

PostgreSQL checkpoint creation is out of scope for UOW-006.

## Test Components

### `tests/test_outputs_storage.py`

Covers:

- local post append
- local failure append
- report atomic write
- media bytes save
- metadata-only media save
- checkpoint save/load/load_latest
- path traversal rejection
- safe failure redaction
- fake S3 key/spool behavior

### `tests/test_outputs_properties.py`

Covers:

- path segment sanitization properties
- output key generation properties
- JSONL round trip properties
- checkpoint document round trip properties
- failure redaction idempotence

### `tests/test_outputs_s3_smoke.py`

Skipped by default.

Runs only when `FMKOREA_S3_SMOKE_ENABLED=true` and all required S3 env values exist.

### `tests/test_outputs_polars_smoke.py`

Skipped when Polars is unavailable.

Covers:

- `read_ndjson`
- top-level identity projection
- nested `comments` explode
- `content.blocks` and `media` projection

## Component Boundaries

- JobRunner decides when to call output and checkpoint stores.
- UOW-006 only reports storage success or failure.
- Duplicate prevention belongs to UOW-005.
- PostgreSQL checkpoint storage belongs to UOW-008 or later adapter work.
- Production Polars normalization belongs to future platform processing.
