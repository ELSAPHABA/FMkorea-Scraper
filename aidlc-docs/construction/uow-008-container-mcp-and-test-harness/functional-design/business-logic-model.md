# Business Logic Model - UOW-008 Container, MCP, And Test Harness

## Purpose

UOW-008 provides the deployable adapter layer and quality harness around the existing FMKorea scraper core.

This unit owns the one-shot worker container entrypoint, Docker build context filter, container environment mapping, PostgreSQL checkpoint store, S3-compatible/Garage output wiring, MCP tool adapter, and result quality test harness. It does not own FMKorea selector logic, HTTP retry policy internals, worker queue internals, CLI wizard UX, parser-failure retry execution, CAPTCHA bypass, GUI/Web UI, distributed scheduling, or AWS CDK.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Container entrypoint | root `docker-entrypoint.sh` called by Dockerfile `ENTRYPOINT`, delegating to `python -m fmkorea_scraper.adapters.container "$@"` |
| Docker context | root `.dockerignore` excludes local state, cache, outputs, `.env` secret candidates, and documentation artifacts |
| New container jobs | reuse UOW-007 CLI command shape and `build_job_config` path |
| Container resume | `RESUME=true` resumes by `JOB_ID` or latest PostgreSQL checkpoint |
| Container storage | S3-compatible/Garage output plus PostgreSQL checkpoint by default |
| Environment source | storage, resume, realtime, proxy, and User-Agent settings come from environment variables or mounted files |
| Checkpoint storage | `PostgresCheckpointStore` stores full `Checkpoint` JSON in one table |
| S3/Garage output | use S3-compatible output with local JSONL spool and durable object upload before reporting success |
| MCP tools | provide `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, and `retry_parser_failures` shape |
| MCP execution | one-shot synchronous tool calls return JSON-serializable results |
| Retry MCP tool | `retry_parser_failures` returns safe unsupported until UOW-009 implements the retry engine |
| Error shape | adapters use `ErrorMapper`; no stack trace, raw env, raw body, cookies, or credentials in responses |
| Quality harness | fixture-based JSONL/report/failure checks including content block, media, comment, and BEST comment shape |
| Default tests | fake clients, static fixtures, PBT, no required Docker/Garage/PostgreSQL/MCP/live network |
| Smoke tests | Docker, Garage, PostgreSQL, MCP server, and live FMKorea checks are env-gated optional smoke tests |

## Container Flow

1. Docker starts `/app/docker-entrypoint.sh`.
2. The script preserves argv and executes `python -m fmkorea_scraper.adapters.container "$@"`.
3. `fmkorea_scraper.adapters.container.main(argv=None)` reads container environment variables.
4. If `RESUME=true`, it builds `ResumeRequest(job_id=JOB_ID or None)`.
5. If `RESUME` is not true, it reuses UOW-007 command normalization and `build_job_config` to build `JobConfig`.
6. It overrides container storage to S3-compatible output and PostgreSQL checkpoint.
7. It builds container runtime dependencies:
   - `HttpClient`
   - `LinkCollectorService`
   - `PostDetailService`
   - S3-compatible output, failure, and media stores
   - `PostgresCheckpointStore`
   - `JobRunDependencies`
   - `JobRunner`
8. It calls `core.api.run_job()` or `core.api.resume_job()`.
9. It writes safe JSON or safe structured summaries to stdout/stderr.
10. It returns exit code `0` on completed report, `2` on validation errors, and `1` on runtime/stopped errors.

The container adapter must not parse FMKorea HTML, collect links directly, write checkpoints manually, or implement a separate worker scheduler.

## Docker Build Context Flow

`.dockerignore` keeps Docker build context focused on runtime inputs.

Excluded groups:

- `.git` and local repository metadata
- virtual environments and Python caches
- test caches and generated output
- `.env` and `.env.*` secret candidates
- documentation and AI-DLC workflow artifacts
- build/dist artifacts

The Dockerfile still copies only explicit runtime inputs. `.dockerignore` exists to reduce build context size and accidental local file exposure.

## Container Environment Flow

Required storage variables:

- `DATABASE_URL`
- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Optional variables:

- `S3_REGION`
- `S3_FORCE_PATH_STYLE`
- `S3_PREFIX`
- `RESUME`
- `JOB_ID`
- `FMKOREA_REALTIME_ENABLED`
- `FMKOREA_REALTIME_MODE`
- `FMKOREA_REALTIME_KEYWORD`
- `FMKOREA_REALTIME_DURATION_SECONDS`
- `FMKOREA_REALTIME_END_AT`
- `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS`
- `FMKOREA_PROXY_HOST`
- `FMKOREA_PROXY_ID`
- `FMKOREA_PROXY_PW`
- User-Agent file path

Job-specific source/options continue to use the UOW-007 `run` argument shape where possible. Storage and container lifecycle settings stay in environment variables.

## PostgreSQL Checkpoint Flow

`PostgresCheckpointStore` implements the checkpoint port used by UOW-005.

Table:

```text
fmkorea_checkpoints(
  job_id text primary key,
  updated_at timestamptz not null,
  checkpoint_json jsonb not null
)
```

Behavior:

1. `save(checkpoint)` upserts by `job_id`.
2. `load(job_id)` reads one checkpoint by primary key.
3. `load_latest()` returns the highest `updated_at` checkpoint.
4. Stored JSON is validated back into the shared `Checkpoint` model before returning.

The first implementation stores the full checkpoint document as JSON rather than normalizing checkpoint fields into separate columns.

## S3/Garage Output Flow

S3-compatible object storage is append-hostile. JSONL append therefore uses a local spool file as the working copy and uploads the full object after each append.

Flow for post/failure append:

1. Append one JSON line to local spool.
2. Upload the updated spool object to S3-compatible storage.
3. Return `StoredObjectRef` only after upload success.

Flow for report/media:

1. Serialize the report or receive media bytes.
2. Upload the target object.
3. Return `StoredObjectRef` after upload success.

This preserves UOW-005's rule: checkpoint progress advances only after durable output storage succeeds.

## MCP Tool Flow

MCP tools are adapter wrappers over existing core APIs.

Tools:

- `search_board`
- `search_integrated`
- `fetch_post`
- `fetch_comments`
- `run_job`
- `resume_job`
- `retry_parser_failures`

Rules:

1. Validate tool input through shared request models or UOW-007 builder functions.
2. Create runtime dependencies for the tool call.
3. Await the core API call.
4. Return `model_dump(mode="json")` style JSON-serializable results.
5. Map errors through `ErrorMapper`.

`run_job` and `resume_job` are one-shot calls in UOW-008. Background job registry, progress polling, cancellation tools, and distributed scheduling are deferred.

`retry_parser_failures` is exposed as a stable tool name but returns safe unsupported until UOW-009 implements parser-stage retry execution.

## Result Quality Harness Flow

The quality harness validates saved result shapes using small fixtures.

Checks:

- required top-level post fields
- ordered `content.blocks` shape
- media and attachment reference shape
- comment flat-list shape
- BEST comment `is_best=true` and `badges` containing `BEST`
- optional/null fields remain representable
- report counts match fixture contents
- failure records contain safe reason fields only
- JSONL can be loaded line by line with stdlib JSON
- optional Polars read check runs only when Polars is installed or an analysis/test extra is enabled

The quality harness does not replace parser fixture tests from UOW-003/UOW-004. It verifies output compatibility and review readiness.

## Terminal And Adapter Error Flow

Container and MCP adapters use `ErrorMapper`.

Container:

- prints safe summary
- returns exit code `2` for validation errors
- returns exit code `1` for runtime/stopped errors
- returns exit code `0` for completed jobs

MCP:

- returns JSON-serializable error objects
- does not expose stack traces, proxy password, raw env, raw HTTP body, cookies, tokens, raw headers, or raw content

## Deferred Behavior

- parser-failure retry execution engine until UOW-009
- Docker compose-based integration smoke
- live FMKorea smoke
- production Kubernetes manifests
- background MCP job registry
- distributed queue and scheduler
- GUI/Web UI
- CAPTCHA bypass
