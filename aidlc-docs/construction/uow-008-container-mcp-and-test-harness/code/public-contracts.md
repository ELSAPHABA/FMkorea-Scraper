# Public Contracts - UOW-008 Container, MCP, And Test Harness

## Docker Entrypoint

```powershell
docker build -t fmkorea-scraper:local .
docker run --rm --env-file .env fmkorea-scraper:local run --source direct-post --url "https://www.fmkorea.com/best/101"
```

Container bootstrap:

```sh
/app/docker-entrypoint.sh
python -m fmkorea_scraper.adapters.container "$@"
```

Contract:

- root `Dockerfile` installs `.[s3,postgres]`
- root `.dockerignore` excludes local outputs, caches, docs, tests, workflow artifacts, CDK synth artifacts, and local env files from image context
- root `.gitattributes` keeps `*.sh` as LF for Linux containers
- importing `fmkorea_scraper.adapters.container` has no env read, network call, database connection, or job start side effect

## Container Environment

Required:

- `DATABASE_URL`
- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Optional:

- `S3_REGION`
- `S3_PREFIX`
- `S3_FORCE_PATH_STYLE`
- `RESUME`
- `JOB_ID`
- `FMKOREA_USER_AGENT_FILE`
- `FMKOREA_USER_AGENT_ROTATE_EVERY`
- `FMKOREA_PROXY_HOST`
- `FMKOREA_PROXY_ID`
- `FMKOREA_PROXY_PW`

Contract:

- container jobs always map output to `StorageMode.S3_COMPATIBLE`
- container checkpoints always map to `CheckpointMode.POSTGRES`
- secret env values are not included in dataclass repr or safe error details
- validation failure exits with code `2`
- runtime/stopped/failed reports exit with code `1`
- completed report exits with code `0`

## Container Adapter API

```python
from fmkorea_scraper.adapters.container import (
    ContainerEnvConfig,
    build_container_runtime,
    run_container_async,
    main,
)
```

Contract:

- `ContainerEnvConfig.from_env(env)` validates documented env keys
- `run_container_async(argv, env=...)` accepts the existing UOW-007 `run` CLI arguments
- `RESUME=true` runs resume mode with optional `JOB_ID`
- `build_container_runtime()` wires `HttpClient`, collector, post detail service, S3 output/media/failure store, PostgreSQL checkpoint store, and `JobRunner`
- first `SIGINT`/`SIGTERM` calls `JobRunner.stop(StopReason.MANUAL_STOP)` where available
- HTTP client is closed in `finally`

## S3-Compatible Output Store

```python
from fmkorea_scraper.outputs import S3OutputStore, S3Spool
```

Contract:

- post JSONL appends upload the complete object before returning success
- failure JSONL appends redact unsafe details before upload
- report writes a JSON object
- media bytes write to the existing `OutputRunLayout.media_key()` path
- returned `StoredObjectRef` includes bucket and object key only, never credentials
- default spool is process-local temp storage and is cleaned on `finalize()`

Object layout:

```text
<prefix>/outputs/<job_id>/<run_id>/posts.jsonl
<prefix>/outputs/<job_id>/<run_id>/failures.jsonl
<prefix>/outputs/<job_id>/<run_id>/report.json
<prefix>/outputs/<job_id>/<run_id>/media/<board>/<post>/<type>/<filename>
```

## PostgreSQL Checkpoint Store

```python
from fmkorea_scraper.outputs import PostgresCheckpointStore
```

Table initialized by the adapter:

```sql
create table if not exists fmkorea_checkpoints (
  job_id text primary key,
  updated_at timestamptz not null,
  checkpoint_json jsonb not null
)
```

Contract:

- `save(checkpoint)` upserts by `job_id`
- `load(job_id)` returns `Checkpoint | None`
- `load_latest()` returns the most recently updated checkpoint
- `psycopg` is imported only when the adapter opens a real connection
- loaded JSON is validated through the `Checkpoint` model
- failures map to safe `CheckpointFailureError`

## MCP Adapter

```python
from fmkorea_scraper.adapters.mcp import McpToolHandlers, create_mcp_server
```

Tool handler methods:

- `search_board(payload)`
- `search_integrated(payload)`
- `fetch_post(payload)`
- `fetch_comments(payload)`
- `run_job(payload)`
- `resume_job(payload)`
- `retry_parser_failures(payload)`

Contract:

- importing `fmkorea_scraper.adapters.mcp` does not require the MCP runtime package
- MCP runtime import happens only in `create_mcp_server()`
- handlers return JSON-safe `{"ok": true, "data": ...}` or `{"ok": false, "error": ...}`
- validation and unsupported placeholders are mapped through the shared safe error mapper
- `retry_parser_failures` remains an MCP shape boundary; full retry execution belongs to UOW-009

## Quality Harness

Fixtures:

- `tests/fixtures/quality/posts.jsonl`
- `tests/fixtures/quality/failures.jsonl`
- `tests/fixtures/quality/report.json`

Contract:

- fixture posts contain top-level post identity, author, content blocks, media records, comments, and BEST comment reactions
- fixture failures contain only safe details
- fixture report counts match the fixture set
- Polars readability is checked only when Polars is installed

## Boundaries

UOW-008 does not implement parser changes, parser-failure retry execution, distributed job queues, production cloud provisioning, GUI/Web UI, CAPTCHA bypass, or network-exposed MCP HTTP/SSE hosting.
