# NFR Design Patterns - UOW-008 Container, MCP, And Test Harness

This document translates UOW-008 NFR requirements into implementation patterns.

## Confirmed Design Answers

| Question | Answer | Design Pattern |
|---|---|---|
| Q1 | A | Use a small flat set of adapter/storage/test files; avoid nested adapter packages in first implementation. |
| Q2 | A | Use `build_container_runtime(config, env_config)` function; no factory class. |
| Q3 | A | Use small `ContainerEnvConfig.from_env(env)` helper; no new Pydantic model for env. |
| Q4 | A | Use sync `psycopg` through `anyio.to_thread.run_sync()` inside async checkpoint port methods. |
| Q5 | A | Wrap boto3/S3 upload calls with `anyio.to_thread.run_sync()`; keep local spool writes simple. |
| Q6 | A | Use temp spool directory and best-effort cleanup at Job end. |
| Q7 | A | Keep MCP tool logic as async functions testable without MCP runtime; server binding is thin. |
| Q8 | A | Use shared `safe_error_payload(exc, stage=None)` over `ErrorMapper`. |
| Q9 | A | Keep quality harness in tests, not runtime package. |
| Q10 | A | Split optional smoke markers by external dependency: `docker`, `garage`, `postgres`, `mcp`, `live`. |

No follow-up question is required.

## Module Layout Pattern

First implementation uses a small flat layout:

```text
src/fmkorea_scraper/adapters/
  container.py
  mcp.py

src/fmkorea_scraper/outputs/
  s3_output.py
  postgres_checkpoint.py

tests/
  test_container_adapter.py
  test_mcp_adapter.py
  test_quality_harness.py
  fixtures/quality/
```

Do not create nested adapter packages until file size or repeated patterns justify it.

## Container Runtime Assembly Pattern

Use a function:

```text
build_container_runtime(config, env_config)
```

Creates:

- `HttpClient`
- board/integrated collectors
- post detail service
- `S3OutputStore`
- `PostgresCheckpointStore`
- `JobRunDependencies`
- `JobRunner`

The function wires existing components only. It must not parse env directly, run jobs, or implement scrape logic.

## Env Config Pattern

`ContainerEnvConfig.from_env(env)`:

1. accepts a `Mapping[str, str]`
2. reads only documented keys
3. validates required storage keys
4. returns a small dataclass
5. raises `ValidationFailure` for missing/invalid values

Secret fields must not be included in `repr`, safe logs, or error details.

Required keys:

- `DATABASE_URL`
- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Optional keys:

- `S3_REGION`
- `S3_FORCE_PATH_STYLE`
- `S3_PREFIX`
- `RESUME`
- `JOB_ID`
- `FMKOREA_REALTIME_*`
- `FMKOREA_PROXY_HOST`
- `FMKOREA_PROXY_ID`
- `FMKOREA_PROXY_PW`
- User-Agent file path

User-provided cookie files are not supported.

## PostgreSQL Adapter Pattern

`PostgresCheckpointStore` implements the existing checkpoint store port.

Pattern:

- sync `psycopg` connection
- injectable connection factory for tests
- `CREATE TABLE IF NOT EXISTS` before first operation or during init
- async public methods wrap short blocking DB work with `anyio.to_thread.run_sync()`
- stored checkpoint JSON validates back into the shared `Checkpoint` model

No Alembic, no asyncpg, no normalized checkpoint columns in first pass.

## S3 Output Pattern

`S3OutputStore` implements the output/media store behavior needed for container mode.

Pattern:

1. create temp spool directory
2. append post/failure JSONL to local spool
3. upload full JSONL object through existing S3-compatible client boundary
4. return `StoredObjectRef` only after upload success
5. upload report/media objects directly
6. clean temp spool best-effort at Job end

Blocking boto3 upload calls are wrapped with `anyio.to_thread.run_sync()`.

No background fire-and-forget upload is allowed because checkpoint progress depends on durable output success.

## MCP Tool Pattern

MCP tool logic is separate from MCP server registration.

Tool functions:

- are `async def`
- accept plain dict or validated request values
- validate through shared models or UOW-007 builder helpers
- call public core APIs
- return JSON-serializable dicts
- map errors through `safe_error_payload`

MCP server binding:

- imports MCP dependency only in server entrypoint or registration function
- registers tool functions
- does not contain scrape logic

This keeps unit tests runnable without the `mcp` extra.

## Safe Error Pattern

Use one helper:

```text
safe_error_payload(exc, stage=None) -> dict
```

Behavior:

1. calls `ErrorMapper.map(exc, stage=stage)`
2. returns JSON-safe fields:
   - `code`
   - `message`
   - `details`
   - `retryable`
3. excludes traceback and unsafe values

Container logs may print this safe payload. MCP tools return it as response error payload.

Forbidden:

- stack trace in MCP response
- raw env
- database/S3/proxy credentials
- cookies
- raw headers
- raw HTML/body/content

## Quality Harness Pattern

Keep quality checks under tests.

Default checks use:

- stdlib `json`
- small JSONL/report fixtures
- pytest assertions
- optional Polars import guarded by skip

Checks include FMKorea-specific BEST comment shape:

- `is_best=true`
- `badges` containing `BEST`
- up/down reaction fields
- parent/depth representation

Do not add runtime package code for analysis-only quality checks.

## Optional Smoke Marker Pattern

Markers:

- `docker`
- `garage`
- `postgres`
- `mcp`
- `live`

Each optional smoke test must check its own env flag and skip cleanly by default.

Default `pytest` must pass without:

- Docker
- Garage
- PostgreSQL
- MCP runtime
- live FMKorea network
- Polars

## Compliance Check

| Requirement Area | Design Compliance |
|---|---|
| Security | safe error payload, secret-free refs/logs, env allow-list, MCP no traceback |
| Resiliency | durable S3 upload before success, checkpoint JSON validation, idempotent table creation |
| Maintainability | flat module layout, function assembly, optional extras, no migration framework |
| PBT | env mapping, checkpoint JSON round trip, S3 ref safety, MCP JSON payloads |
| Import safety | env/DB/S3/MCP startup only at explicit entrypoints |
