# Domain Entities - UOW-008 Container, MCP, And Test Harness

## DockerEntrypointScript

Represents the root `docker-entrypoint.sh` file copied into the worker image.

Fields:

- `path`: `docker-entrypoint.sh`
- `image_path`: `/app/docker-entrypoint.sh`
- `delegated_module`: `fmkorea_scraper.adapters.container`
- `argv`: all arguments passed by Docker after image name

Rules:

- Preserves argv.
- Delegates to `python -m fmkorea_scraper.adapters.container "$@"`.
- Contains Docker bootstrap only, not scraper business logic.
- Uses Linux-compatible line endings.

## DockerignoreContract

Represents the build context exclusion contract.

Excluded groups:

- repository metadata
- virtual environments
- Python/test caches
- local outputs and checkpoints
- `.env` secret candidates
- docs and AI-DLC workflow artifacts
- build/dist artifacts

Rules:

- Must not exclude Dockerfile runtime copy inputs.
- Reduces context size and accidental local file exposure.
- Does not decide what is in the image; Dockerfile `COPY` still decides image contents.

## ContainerCommand

Represents one container process invocation.

Fields:

- `argv`: command-line arguments passed to the container entrypoint
- `env`: process environment mapping
- `resume`: boolean derived from `RESUME`
- `job_id`: optional checkpoint job id

Rules:

- `resume=true` selects resume flow.
- `resume=false` selects new Job flow.
- Job source/options use UOW-007 command mapping where possible.

## ContainerExecutionConfig

Container-only runtime settings derived from environment variables.

Fields:

- `database_url`
- `s3_endpoint_url`
- `s3_bucket`
- `s3_access_key_id`
- `s3_secret_access_key`
- `s3_region`
- `s3_force_path_style`
- `s3_prefix`
- `job_id`
- `resume`
- `realtime_env`
- `proxy_env`
- `user_agent_file`
- `user_agent_rotate_every`

Rules:

- Required storage fields must be present before container run/resume starts.
- Secrets are stored in memory only and are not logged.
- Realtime fields keep the same semantics as UOW-007.
- User-provided cookie files are not supported; server-set cookies stay in HTTP client memory only.

## PostgresCheckpointStore

Checkpoint store implementation for container mode.

Methods:

- `save(checkpoint: Checkpoint) -> None`
- `load(job_id: str) -> Checkpoint | None`
- `load_latest() -> Checkpoint | None`

Storage table:

```text
fmkorea_checkpoints(
  job_id text primary key,
  updated_at timestamptz not null,
  checkpoint_json jsonb not null
)
```

Rules:

- Stored JSON validates as the shared `Checkpoint` model.
- `load_latest()` orders by `updated_at desc`.
- Failed database operations surface as safe checkpoint/storage failures.

## S3CompatibleOutputStore

Output store implementation for S3-compatible object storage.

Responsibilities:

- append post JSONL records
- append failure JSONL records
- upload final report JSON
- upload media bytes or metadata-only refs
- return `StoredObjectRef`

Key behavior:

- Object keys follow the UOW-006 `OutputRunLayout` relative key rules.
- S3 object references use `s3://<bucket>/<key>`.
- Credentials never appear in refs.
- JSONL append uses local spool plus upload.

## S3ContainerStorageConfig

Container storage configuration for S3-compatible output.

Fields:

- `endpoint_url`
- `bucket`
- `access_key_id`
- `secret_access_key`
- `region`
- `force_path_style`
- `prefix`

Rules:

- Garage is the default target.
- Implementation must remain S3-compatible rather than Garage-specific.
- SeaweedFS remains a future compatible target.

## McpToolRequest

Validated MCP tool input wrapper.

Common fields:

- `tool_name`
- `arguments`
- `request_id`

Tool-specific models:

- board search request
- integrated search request
- post fetch request
- comment fetch request
- Job run command
- Job resume command
- parser failure retry request

Rules:

- Arguments validate through shared models or UOW-007 builder logic.
- Invalid input maps to safe validation error payloads.

## McpToolResponse

JSON-serializable MCP tool response.

Fields:

- `ok`: boolean
- `result`: JSON value when successful
- `error`: safe error object when failed

Rules:

- Success results use Pydantic `model_dump(mode="json")` style structures.
- Failure payloads use `ErrorMapper`.
- No stack trace, raw env, raw HTTP body, cookie, token, credential, raw header, or raw content fields.

## QualityFixtureSet

Collection of deterministic fixtures used to validate output quality.

Includes:

- post JSONL fixture with text/content/media blocks
- comment fixture with normal and BEST comments
- failure JSONL fixture
- Job report fixture
- optional malformed fixture

Checks:

- required top-level fields
- content block ordering and optional/null representation
- media and attachment reference shape
- comment parent/depth/reaction shape
- BEST comment `is_best=true` and `badges` containing `BEST`
- report count consistency
- safe failure context
- optional Polars loading when enabled

## OptionalSmokeConfig

Configuration for opt-in smoke tests.

Fields:

- `docker_smoke_enabled`
- `garage_smoke_enabled`
- `postgres_smoke_enabled`
- `mcp_smoke_enabled`
- `live_fmkorea_smoke_enabled`

Rules:

- Default test run leaves all smoke flags disabled.
- Smoke tests must skip cleanly when required env vars or services are missing.

## Entity Relationships

```text
DockerEntrypointScript
  -> ContainerCommand
  -> ContainerExecutionConfig
  -> JobConfig or ResumeRequest
  -> JobRunner
  -> S3CompatibleOutputStore
  -> PostgresCheckpointStore

McpToolRequest
  -> shared request model or Job builder
  -> core API
  -> McpToolResponse

QualityFixtureSet
  -> JSONL/report validators
  -> optional Polars load check
```

## Boundary Summary

- Container and MCP entities are adapters over existing core models.
- Storage entities implement existing output/checkpoint ports.
- Quality harness entities validate output compatibility and do not perform scraping.
