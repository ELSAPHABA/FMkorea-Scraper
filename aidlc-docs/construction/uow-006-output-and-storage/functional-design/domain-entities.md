# Domain Entities - UOW-006 Output And Storage

## Existing Contract Entities

UOW-006 reuses the UOW-001 model and port contracts below.

| Entity | Source | Role |
|---|---|---|
| `StorageConfig` | `models/job.py` | selects local or S3 output and local or PostgreSQL checkpoint mode |
| `S3StorageConfig` | `models/job.py` | contains endpoint, bucket, prefix, and region for S3-compatible output |
| `PostResult` | `models/post.py` | successful post scrape output written to `posts.jsonl` |
| `FailureRecord` | `models/failure.py` | failed item output written to `failures.jsonl` |
| `JobReport` | `models/report.py` | final run report written to `report.json` |
| `StoredObjectRef` | `models/report.py` | reference returned after writing an object |
| `MediaItem` | `models/media.py` | media metadata updated with local path or object key |
| `Checkpoint` | `models/checkpoint.py` | local checkpoint payload saved in `Checkpoint.json` |
| `OutputStorePort` | `core/ports.py` | post/report output store protocol |
| `MediaStorePort` | `core/ports.py` | media store protocol |
| `FailureStorePort` | `core/ports.py` | failure store protocol |
| `CheckpointStorePort` | `core/ports.py` | checkpoint store protocol |

## Store Components

### LocalOutputStore

Concrete local implementation of `OutputStorePort`.

Responsibilities:

- create `outputs/<job_id>/<run_id>/`
- append posts to `posts.jsonl`
- write `report.json`
- return local `StoredObjectRef` values
- close or flush local writer state on `finalize`

### LocalFailureStore

Concrete local implementation of `FailureStorePort`.

Responsibilities:

- append failures to `failures.jsonl`
- redact unsafe detail fields before writing
- read failures back for later parser-failure retry input

### JsonlWriter

Small helper for newline-delimited JSON writes.

Responsibilities:

- serialize one model/dict per line
- write UTF-8
- append newline
- flush records according to the concrete writer policy

### LocalMediaStore

Concrete local implementation of `MediaStorePort`.

Responsibilities:

- save bytes under the run media directory
- derive safe filenames
- set `MediaItem.file_path`
- support metadata-only pass-through

### LocalCheckpointStore

Concrete local implementation of `CheckpointStorePort`.

Responsibilities:

- save multiple latest checkpoints in `Checkpoint.json`
- load by `job_id`
- load latest by `updated_at`
- write through same-directory temp file and atomic replace

### S3ObjectStore

S3-compatible implementation shared by output and media storage.

Responsibilities:

- put JSONL/report/media objects into configured bucket
- build object keys from the same relative paths as local mode
- return S3-style `StoredObjectRef` values
- work with Garage by configuration only

### S3JsonlSpool

Small helper for S3-compatible JSONL writes.

Responsibilities:

- keep a run-local spool file
- append one JSONL record to the spool
- upload the complete JSONL object to the same S3 key after each append
- expose the same object key as the final output object

## Output Layout Entity

### OutputRunLayout

Derived value object for run-relative paths.

Fields:

- `job_id`
- `run_id`
- `base_path` or S3 `prefix`
- `posts_path`
- `failures_path`
- `report_path`
- `media_prefix`

Rules:

- all paths are relative below `outputs/<job_id>/<run_id>/`
- path segments are sanitized before joining
- resume uses a new `run_id`

## Failure Context Entity

### SafeFailureContext

Optional safe context that can be merged into `FailureRecord.details`.

Allowed fields:

- `request_url`
- `http_status`
- `response_kind`
- `parser_stage`
- bounded parser warning codes

Forbidden fields:

- `proxy_id`
- `proxy_password`
- `cookie`
- `token`
- `password`
- `headers`
- `raw_html`
- `raw_body`
- `content`

## Checkpoint File Entity

### LocalCheckpointDocument

Logical JSON document stored as `Checkpoint.json`.

Fields:

- `schema_version`
- `updated_at`
- `checkpoints`

`checkpoints` is keyed by `job_id` and stores serialized `Checkpoint` objects.

## Stored Object Reference Rules

Local objects:

- `storage_mode`: `local`
- `path`: local file path
- `bucket`: `null`
- `object_key`: run-relative path

S3-compatible objects:

- `storage_mode`: `s3_compatible`
- `path`: `null`
- `bucket`: configured bucket
- `object_key`: bucket object key

## Entity Boundaries

- `PostResult` remains FMKorea-native and nested.
- `PostResult` does not receive `is_repost` or `repost`.
- `FailureRecord` remains safe and retry-oriented.
- `Checkpoint` remains lifecycle state, not output data.
- `MediaItem` stores metadata plus storage reference, not raw bytes.
- S3 credentials are configuration/runtime data, not domain data.
