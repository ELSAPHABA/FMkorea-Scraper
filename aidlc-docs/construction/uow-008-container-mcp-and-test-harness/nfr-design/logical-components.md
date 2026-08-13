# Logical Components - UOW-008 Container, MCP, And Test Harness

This document defines logical components for the UOW-008 implementation.

## Component Overview

| Component | Responsibility |
|---|---|
| `ContainerMain` | one-shot container entrypoint and exit code mapping |
| `ContainerEnvConfig` | documented env parsing and validation |
| `ContainerRuntimeBuilder` | wires existing core services to container storage adapters |
| `PostgresCheckpointStore` | checkpoint port backed by PostgreSQL |
| `S3OutputStore` | output/media store backed by S3-compatible object storage |
| `S3Spool` | temp local JSONL spool and cleanup |
| `McpToolHandlers` | async tool functions over core APIs |
| `McpServerBinding` | optional MCP runtime registration/entrypoint |
| `SafeAdapterError` | shared safe error payload helper |
| `QualityHarness` | test-only JSONL/report fixture validators |
| `OptionalSmokeTests` | env-gated Docker/Garage/PostgreSQL/MCP/live smoke checks |

## ContainerMain

Location:

- `src/fmkorea_scraper/adapters/container.py`

Responsibilities:

- parse container argv where needed
- read env through `ContainerEnvConfig.from_env`
- choose run vs resume from `RESUME`
- build `JobConfig` or `ResumeRequest`
- call `build_container_runtime`
- call core API run/resume flow
- map success/validation/runtime failures to exit codes

Must not:

- run on import
- connect to DB/S3 on import
- parse FMKorea HTML
- implement worker queue logic

## ContainerEnvConfig

Shape:

```text
ContainerEnvConfig.from_env(env: Mapping[str, str]) -> ContainerEnvConfig
```

Responsibilities:

- validate required storage env
- parse booleans such as `RESUME` and `S3_FORCE_PATH_STYLE`
- expose optional `JOB_ID`
- expose S3/PostgreSQL config values
- expose proxy/User-Agent runtime inputs
- avoid secret values in repr/log output

Errors:

- missing required env -> `ValidationFailure`
- invalid boolean/value -> `ValidationFailure`

## ContainerRuntimeBuilder

Function:

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

It is a function, not a factory class.

## PostgresCheckpointStore

Location:

- `src/fmkorea_scraper/outputs/postgres_checkpoint.py`

Public methods:

- `save(checkpoint)`
- `load(job_id)`
- `load_latest()`

Responsibilities:

- create `fmkorea_checkpoints` table idempotently
- upsert checkpoint JSON by `job_id`
- load one checkpoint
- load latest checkpoint by `updated_at desc`
- validate loaded JSON as `Checkpoint`
- map DB failures to safe checkpoint/storage errors

Testing:

- injectable connection factory
- fake connection/cursor
- no real PostgreSQL required in default gate

## S3OutputStore

Location:

- `src/fmkorea_scraper/outputs/s3_output.py`

Responsibilities:

- append post JSONL to local spool
- upload updated post JSONL object
- append failure JSONL to local spool
- upload updated failure JSONL object
- upload final report
- upload media bytes or return metadata-only refs
- return `StoredObjectRef` after durable upload

Uses:

- existing output layout and JSON serialization helpers from UOW-006
- existing S3-compatible boundary/client concepts
- `anyio.to_thread.run_sync()` for blocking upload calls

Must not:

- expose credentials in refs
- fire-and-forget uploads
- append to previous resumed run spool

## S3Spool

Responsibilities:

- own temp spool directory
- expose post/failure spool paths
- append one JSON line
- read bytes for upload
- best-effort cleanup

Failure handling:

- spool write failure -> storage failure
- cleanup failure -> safe warning only

## McpToolHandlers

Location:

- `src/fmkorea_scraper/adapters/mcp.py`

Tools:

- `search_board`
- `search_integrated`
- `fetch_post`
- `fetch_comments`
- `run_job`
- `resume_job`
- `retry_parser_failures`

Responsibilities:

- validate input
- create needed runtime dependencies
- call core API
- return JSON-serializable result dict
- return safe error dict on failure

Tool handlers should be testable without an MCP server process.

## McpServerBinding

Responsibilities:

- import MCP dependency only when the MCP entrypoint/registration is used
- register tool handlers
- start MCP server only from explicit entrypoint

Out of scope:

- background job registry
- cancellation/progress tools
- scheduler integration

## SafeAdapterError

Function:

```text
safe_error_payload(exc, stage=None) -> dict
```

Responsibilities:

- use `ErrorMapper`
- return JSON-safe error payload
- remove unsafe details
- provide shared container/MCP error shape

## QualityHarness

Location:

- `tests/test_quality_harness.py`
- `tests/fixtures/quality/`

Responsibilities:

- validate post JSONL fixture required fields
- validate content block/media/attachment shape
- validate normal comment shape
- validate BEST comment `is_best=true`, `badges`, and reaction shape
- validate optional/null representation
- validate report counts
- validate failure safe fields
- optionally validate Polars read when installed

Must not:

- become runtime package code
- require Polars by default
- require live FMKorea access

## OptionalSmokeTests

Markers:

- `docker`
- `garage`
- `postgres`
- `mcp`
- `live`

Rules:

- each smoke test checks required env flag
- missing env/service means skip, not fail
- default test gate remains deterministic

## Boundary Summary

UOW-008 owns deployable adapters and validation harnesses.

It delegates:

- validation models to UOW-001
- HTTP runtime to UOW-002
- search collection to UOW-003
- detail parsing to UOW-004
- orchestration to UOW-005
- base storage layout/serialization to UOW-006
- command/job builder reuse to UOW-007
