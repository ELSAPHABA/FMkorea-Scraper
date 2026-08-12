# Public Contracts - UOW-006 Output And Storage

## Package

Public imports live under:

- `fmkorea_scraper.outputs`

The package is import-safe. Importing it must not write files, read environment variables, import `boto3`, connect to S3, or create external resources.

## Primary Exports

| Export | Purpose |
|---|---|
| `OutputRunLayout` | Derives sanitized local paths and S3-compatible object keys for one `job_id`/`run_id`. |
| `JsonlWriter` | Appends one JSON object per line using Pydantic `model_dump(mode="json")` when available. |
| `AtomicJsonWriter` | Writes small JSON documents by temp-file plus `os.replace`. |
| `LocalOutputStore` | Implements post JSONL append and report JSON write for local storage. |
| `LocalFailureStore` | Implements failure JSONL write/read for local storage. |
| `LocalMediaStore` | Stores caller-supplied media bytes locally or returns metadata-only media. |
| `LocalCheckpointStore` | Saves, loads, and load-latest local `Checkpoint.json` records. |
| `S3ObjectStore` | Writes posts, failures, reports, and media through an S3-compatible client. |
| `S3JsonlSpool` | Maintains a file-backed JSONL spool and uploads the same object key after each append. |
| `StorageFactory` | Creates local or S3-compatible concrete stores from `StorageConfig`. |
| `sanitize_failure_context` | Keeps only safe failure detail keys and drops credential/raw-body fields. |

`StorageFactory` is also exported from top-level `fmkorea_scraper`.

## StorageFactory Contract

```python
from fmkorea_scraper.models.job import StorageConfig
from fmkorea_scraper.outputs import StorageFactory

bundle = StorageFactory.create(
    StorageConfig(base_output_path="out"),
    job_id="job-1",
    run_id="run-1",
)
```

Returned `StorageBundle` fields:

- `output_store`
- `failure_store`
- `media_store`
- `checkpoint_store`
- `layout`

Local mode returns:

- `LocalOutputStore`
- `LocalFailureStore`
- `LocalMediaStore`
- `LocalCheckpointStore`

S3-compatible output mode returns one `S3ObjectStore` instance for output, failure, and media stores, plus local checkpoint store when `checkpoint_mode=local`.

PostgreSQL checkpoint creation is intentionally rejected in UOW-006. It is deferred to a later runtime/storage unit.

## Local Layout Contract

With `StorageConfig.base_output_path=<base>`, UOW-006 writes:

```text
<base>/
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
                <source_order>-<filename>
  Checkpoint.json
```

If `base_output_path` is missing, the runtime working directory is used.

`job_id`, `run_id`, media path fields, and filenames are sanitized. Local paths are checked so generated paths cannot escape the base output directory.

## S3-Compatible Contract

S3 mode uses `StorageConfig.s3`:

- `endpoint_url`
- `bucket`
- optional `prefix`
- optional `region`

Object keys mirror local relative paths:

```text
<prefix>/outputs/<job_id>/<run_id>/posts.jsonl
<prefix>/outputs/<job_id>/<run_id>/failures.jsonl
<prefix>/outputs/<job_id>/<run_id>/report.json
<prefix>/outputs/<job_id>/<run_id>/media/<board_id>/<document_srl_or_raw_id>/<media_type>/<source_order>-<filename>
```

`boto3` is imported only when S3 mode is constructed without an injected client. Tests and later adapters can inject a compatible client with `put_object` and optionally `get_object`.

UOW-006 does not create buckets, policies, Garage services, or custom S3 signing.

## JSONL Contract

`posts.jsonl` and `failures.jsonl` contain one JSON object per line.

Writer behavior:

- `BaseModel` values use `model_dump(mode="json")`.
- UTF-8 is used.
- `ensure_ascii=False` is preserved.
- Unicode line separators that can split a physical JSONL record are escaped.
- One trailing `\n` is written after each record.

## Failure Redaction Contract

`LocalFailureStore` and `S3ObjectStore.write_failure` sanitize `FailureRecord.details` before writing.

Allowed detail keys include:

- `request_url`
- `http_status`
- `response_kind`
- `parser_stage`
- `warning_codes`
- `stage`
- `reason`
- `code`
- `job_id`
- `board_id`
- `document_id_raw`

Dropped or redacted fields include credential, cookie, proxy, token, password, header, raw HTML, raw body, and content-like fields.

## Checkpoint Contract

`LocalCheckpointStore` stores one local document:

```json
{
  "schema_version": "fmkorea.local_checkpoint.v1",
  "updated_at": "...",
  "checkpoints": {
    "<job_id>": {}
  }
}
```

It supports:

- `save(checkpoint)`
- `load(job_id)`
- `load_latest()`

Writes use atomic JSON replacement and an in-process lock.

## Optional Smoke Contracts

S3 smoke:

- marker: `s3_smoke`
- gate: `FMKOREA_S3_SMOKE_ENABLED=true`
- env: `FMKOREA_S3_ENDPOINT_URL`, `FMKOREA_S3_BUCKET`, `FMKOREA_S3_ACCESS_KEY_ID`, `FMKOREA_S3_SECRET_ACCESS_KEY`

Polars smoke:

- marker: `polars_smoke`
- skips when `polars` is not installed
- verifies `polars.read_ndjson` can read generated `posts.jsonl`

Both smoke paths are outside the default mandatory external-service contract.
