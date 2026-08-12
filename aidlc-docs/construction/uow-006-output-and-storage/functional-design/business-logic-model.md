# Business Logic Model - UOW-006 Output And Storage

## Purpose

UOW-006 stores scraper outputs produced by earlier units.

This unit owns Job JSONL output, failure JSONL output, final Job report output, local media writes, S3-compatible object writes, local checkpoint file persistence, and small Polars-readiness checks. It does not own link collection, post parsing, HTTP media download, retry scheduling, worker orchestration, PostgreSQL checkpoint storage, CLI prompts, container runtime, MCP hosting, or AWS CDK.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Store boundary | Implement concrete stores behind `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, and `CheckpointStorePort`. |
| JSONL naming | local/S3 object layout uses `outputs/<job_id>/<run_id>/posts.jsonl`; resume creates a new `run_id`. |
| JSON shape | `PostResult.model_dump(mode="json")` is written as one JSON object per line with nested `content`, `attachments`, `media`, and `comments` preserved. |
| FMKorea source fields | FMKorea source JSONL does not add `is_repost` or `repost`. |
| Local write policy | JSONL files append; report and checkpoint writes use temp-file write plus atomic replace. |
| Media storage | `MediaStorePort` stores already downloaded bytes and updates `MediaItem.file_path` or `MediaItem.object_key`; HTTP download belongs outside UOW-006. |
| Failure/report output | failures go to `outputs/<job_id>/<run_id>/failures.jsonl`; final summary goes to `outputs/<job_id>/<run_id>/report.json`. |
| Failure safety | raw HTML/body/content, cookies, proxy credentials, tokens, passwords, and raw headers are never written. |
| Local checkpoint | `Checkpoint.json` stores latest checkpoints for multiple `job_id` values and is written by temporary-file replace. |
| S3-compatible storage | Garage is the default deployment target through S3-compatible configuration; no Garage-only API is required. |
| S3 JSONL append | S3-compatible JSONL uses a local spool file and overwrites the same object key after each append. |
| Idempotency | output stores are append-only; duplicate prevention belongs to UOW-005 checkpoint/completed-key logic. |
| Polars boundary | UOW-006 smoke-tests source JSONL readability; production common-schema normalization is deferred. |

## Output Flow

1. Caller creates or resumes a Job run and chooses a `run_id`.
2. Caller opens output, media, failure, and checkpoint stores from `StorageConfig`.
3. For each successful `PostResult`, caller invokes `append_post`.
4. Store serializes the post with Pydantic JSON mode.
5. Store writes exactly one newline-delimited JSON object to `posts.jsonl`.
6. Store returns a `StoredObjectRef`.
7. For each failed item, caller invokes `write_failure`.
8. At Job end, caller invokes `write_report` and `finalize`.

Checkpoint commit ordering is not decided inside UOW-006. UOW-005 must call checkpoint save only after the relevant output call succeeds.

## Local Output Layout

Default local layout:

```text
<base_output_path>/
  outputs/
    <job_id>/
      <run_id>/
        posts.jsonl
        failures.jsonl
        report.json
        media/
          <board_id>/
            <document_srl_or_raw_id>/
              <media_type>/
                <filename>
  Checkpoint.json
```

If `StorageConfig.base_output_path` is missing, the runtime working directory is the base path.

`run_id` must be unique for each run attempt. Resume reuses the same `job_id` but creates a new `run_id`, so old JSONL files are never appended after resume.

## JSONL Serialization Flow

`PostResult` records are serialized by:

1. `model_dump(mode="json")`
2. safe JSON encoding with `ensure_ascii=False`
3. append one object plus `\n`
4. flush according to the concrete writer policy

Nested fields are preserved:

- `content`
- `attachments`
- `media`
- `comments`
- `metadata`

Optional values remain `null`. Empty collections remain empty arrays.

## Failure Output Flow

`FailureRecord` writes use the same JSONL rules as posts.

Allowed safe context:

- `job_id`
- `stage`
- `reason`
- `retryable`
- `url`
- `post_key`
- `safe_message`
- bounded structured `details` after redaction

Forbidden context:

- proxy ID
- proxy password
- cookie values
- token values
- password values
- raw request or response headers
- raw HTML/body/content
- credential file contents

If a lower layer supplies unsafe fields, UOW-006 must drop or redact them before writing.

## Media Storage Flow

`MediaStorePort.save_media(item, content)` receives:

- a `MediaItem`
- already downloaded bytes

The media store:

1. derives a safe filename from `media_id`, `file_srl`, URL path, or media type fallback
2. writes bytes under `media/<board_id>/<document_srl_or_raw_id>/<media_type>/`
3. returns the updated `MediaItem`

Local mode sets `file_path`. S3-compatible mode sets `object_key`. Metadata-only mode calls `save_metadata_only` and does not write bytes.

## Local Checkpoint Flow

`CheckpointStorePort.save` updates `Checkpoint.json`.

File shape:

```json
{
  "schema_version": "fmkorea.local_checkpoint.v1",
  "updated_at": "2026-08-12T00:00:00Z",
  "checkpoints": {
    "<job_id>": {}
  }
}
```

Write flow:

1. load existing checkpoint map if present
2. replace the target `job_id`
3. write the whole document to a temp file in the same directory
4. atomically replace `Checkpoint.json`

`load(job_id)` reads the matching entry. `load_latest()` returns the checkpoint with the newest `updated_at`.

## S3-Compatible Flow

S3-compatible output uses the same object keys as local mode:

```text
<prefix>/outputs/<job_id>/<run_id>/posts.jsonl
<prefix>/outputs/<job_id>/<run_id>/failures.jsonl
<prefix>/outputs/<job_id>/<run_id>/report.json
<prefix>/outputs/<job_id>/<run_id>/media/<board_id>/<document_srl_or_raw_id>/<media_type>/<filename>
```

Garage is configured through standard S3-compatible fields:

- endpoint URL
- bucket
- optional prefix
- optional region
- access key and secret from runtime configuration

S3-compatible storage has no native append. UOW-006 therefore uses a run-local spool file for JSONL and uploads the full object to the same key after each append. This preserves the one-JSONL-file contract and allows UOW-005 to checkpoint only after a durable object write succeeds.

SeaweedFS can later replace Garage through the same S3-compatible boundary.

## Polars Readiness Flow

UOW-006 validates source JSONL shape with a small fixture:

1. read `posts.jsonl` with Polars `read_ndjson`
2. project top-level post identity fields
3. explode nested `comments`
4. project `content.blocks` and `media`

This is a smoke check only. Production common-schema normalization remains a later platform processing step that reads source JSONL without modifying it.

## Testable Properties

- `append_post` writes exactly one JSON line per `PostResult`.
- `write_failure` writes exactly one JSON line per failure and omits forbidden context.
- Resume creates a different `run_id` path under the same `job_id`.
- JSONL records preserve nested comments/content/media structures.
- Local checkpoint save can load the same checkpoint back.
- Local checkpoint `load_latest()` returns the newest updated checkpoint.
- Media save never performs HTTP requests.
- S3 object keys match local relative paths.
- S3-compatible JSONL append uploads the same object key after each append.
