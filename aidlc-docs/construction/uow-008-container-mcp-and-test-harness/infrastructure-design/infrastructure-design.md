# Infrastructure Design - UOW-008 Container, MCP, And Test Harness

## Scope

UOW-008 is the first deployable adapter unit for the FMKorea scraper package.

In scope:

- one-shot worker container image
- container entrypoint and environment contract
- PostgreSQL checkpoint adapter endpoint
- Garage/S3-compatible output endpoint
- optional MCP server entrypoint
- optional local/smoke compose contract
- Docker signal and exit code boundary
- default and optional smoke test infrastructure
- shared infrastructure summary for common PostgreSQL/Garage use

Out of scope:

- production Kubernetes manifests
- managed cloud provisioning
- distributed queue or scheduler
- long-running worker daemon
- GUI/Web UI
- CAPTCHA bypass

## Confirmed Decisions

| Area | Decision |
|---|---|
| Worker image | one `Dockerfile` on Python 3.11+ slim; `.dockerignore` filters build context; install `.[s3,postgres]`; entrypoint calls `/app/docker-entrypoint.sh`, which delegates to `python -m fmkorea_scraper.adapters.container` |
| MCP runtime | separate optional MCP entrypoint/console script with `.[mcp]`; not included in default worker image |
| MCP transport | stdio by default; HTTP/SSE transport deferred |
| Compose | optional local/smoke contract only, not production ownership |
| Secret injection | runtime `--env` or `--env-file`; no credentials baked into image |
| Network | worker opens no inbound port; outbound only to FMKorea, PostgreSQL, and Garage/S3 |
| Persistent storage | worker has no required persistent volume; durable data lives in Garage/S3 and PostgreSQL |
| PostgreSQL schema | adapter runs idempotent `CREATE TABLE IF NOT EXISTS`; no init SQL requirement |
| Signals and exit codes | SIGTERM/Ctrl+C request graceful stop; exit codes remain `0`, `1`, `2` |
| Shared infrastructure | summarize common PostgreSQL/Garage/env/network/volume contract in this unit; no production cloud provisioning |

## Worker Container

The worker container is a one-shot process.

Image contract:

```text
Dockerfile
  context: .dockerignore excludes local state, caches, outputs, docs, workflow artifacts, secret candidates
  base: python:3.11+ slim
  install: pip install .[s3,postgres]
  entrypoint: /app/docker-entrypoint.sh
  delegates: python -m fmkorea_scraper.adapters.container "$@"
```

The container must not:

- run a server
- expose an inbound port
- own PostgreSQL or Garage lifecycle
- include database, S3, or proxy credentials in the image
- start scraping on module import

The container may run either a new Job or resume one Job based on documented environment values.

## Environment Contract

Runtime env is injected with `docker run --env` or `--env-file`.

Required storage env:

- `DATABASE_URL`
- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Optional env:

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

The entrypoint reads only documented env keys through `ContainerEnvConfig.from_env`.

Missing or invalid required env returns validation exit code `2` before a Job starts.

Secrets must not appear in logs, repr output, MCP responses, reports, object refs, or safe error details.

## Shared Infrastructure Boundary

PostgreSQL and Garage are shared infrastructure, not FMKorea-scraper-owned sidecars.

Intended platform shape:

```text
Common infrastructure
  PostgreSQL
  Garage/S3-compatible storage
  shared Docker network or service endpoints

Worker containers
  fmkorea-scraper
  other-community-scraper
  later platform workers
```

The FMKorea worker connects to shared services by environment variables.

This keeps later community scrapers free to reuse the same checkpoint and object storage layer without being coupled to a scraper-specific compose stack.

## Optional Compose Boundary

Compose is allowed only as local development or smoke-test infrastructure.

It may provide:

- PostgreSQL
- Garage/S3-compatible storage
- one worker container for connection smoke

Compose must not be treated as the production deployment topology.

If a compose file is created during code generation, it should be named as smoke/dev-only, for example:

```text
docker-compose.smoke.yml
```

The default test gate must not require compose, Docker, PostgreSQL, or Garage.

## PostgreSQL Checkpoint Infrastructure

`PostgresCheckpointStore` owns checkpoint persistence.

Infrastructure requirements:

- one PostgreSQL endpoint from `DATABASE_URL`
- idempotent table creation inside the adapter
- no required migration container
- no required compose init SQL

The first schema is owned by the adapter through:

```sql
CREATE TABLE IF NOT EXISTS fmkorea_checkpoints (...);
```

The exact SQL can stay minimal in code generation because UOW-008 stores checkpoint JSON and validates it back through the shared `Checkpoint` model.

## Garage/S3-Compatible Output Infrastructure

`S3OutputStore` writes JSONL, report, and media objects to an S3-compatible endpoint.

Garage is the default target. SeaweedFS remains a future-compatible alternative through the same S3-compatible boundary.

Object storage owns durable output:

```text
<prefix>/outputs/<job_id>/<run_id>/posts.jsonl
<prefix>/outputs/<job_id>/<run_id>/failures.jsonl
<prefix>/outputs/<job_id>/<run_id>/report.json
<prefix>/outputs/<job_id>/<run_id>/media/...
```

The worker may use process-local temp spool files, but those files are not persistent state.

## Network Boundary

Worker outbound access:

- FMKorea HTTP endpoints
- PostgreSQL endpoint
- Garage/S3 endpoint
- optional proxy endpoint when configured

Worker inbound access:

- none

MCP stdio mode:

- no inbound network port
- local agent process starts and communicates over stdio

Network-exposed MCP transports such as HTTP/SSE are deferred until a later deployment design defines authentication and exposure rules.

## Volume Boundary

The worker container does not require a persistent volume.

Persistent state lives in:

- PostgreSQL for checkpoints
- Garage/S3 for JSONL, reports, and media

Optional smoke compose may use named volumes only for PostgreSQL/Garage service data.

Do not attach a default worker output volume for container mode unless a later measured need appears.

## Signal And Exit Boundary

Container stop behavior:

- SIGTERM requests `JobRunner.request_stop()` or the existing stop API when possible
- graceful stop follows the same final checkpoint/report path as local Ctrl+C
- a second forced termination may exit without full cleanup

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | completed successfully |
| 1 | stopped, CAPTCHA, runtime failure, or forced interrupt |
| 2 | validation failure before Job start |

## MCP Runtime

MCP is optional infrastructure.

Default MCP deployment shape:

```text
python -m fmkorea_scraper.adapters.mcp
```

or an equivalent console script installed with the `mcp` extra.

The worker image does not need the MCP extra by default.

MCP tool handlers must remain testable without starting an MCP server process.

## Test Infrastructure

Default tests use fakes and fixtures only.

Default tests must not require:

- Docker
- Garage
- PostgreSQL
- MCP runtime
- live FMKorea network
- Polars

Optional smoke markers:

- `docker`
- `garage`
- `postgres`
- `mcp`
- `live`

Each smoke test must skip cleanly unless its marker and required env flag are explicitly enabled.

## Implementation Impact

Code generation for UOW-008 may create:

- `Dockerfile`
- `.dockerignore`
- `docker-entrypoint.sh`
- `src/fmkorea_scraper/adapters/container.py`
- `src/fmkorea_scraper/adapters/mcp.py`
- `src/fmkorea_scraper/outputs/postgres_checkpoint.py`
- `src/fmkorea_scraper/outputs/s3_output.py`
- optional smoke compose example or documented contract
- adapter/storage/quality harness tests
- optional extras in `pyproject.toml`

Code generation for UOW-008 should not create:

- production Kubernetes manifests
- cloud provisioning scripts
- distributed queue
- long-running scheduler
- GUI/Web UI
- CAPTCHA bypass code
