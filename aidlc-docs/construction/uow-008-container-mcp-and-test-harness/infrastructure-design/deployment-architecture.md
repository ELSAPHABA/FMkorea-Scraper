# Deployment Architecture - UOW-008 Container, MCP, And Test Harness

## Architecture Classification

UOW-008 defines deployable adapters, not a full production platform.

Primary deployment shapes:

- one-shot worker container
- optional local MCP stdio server
- optional smoke/dev compose stack

It does not define Kubernetes, cloud-managed services, or a distributed scheduler.

## Platform Topology

Recommended shared-infrastructure topology:

```text
                         +----------------------+
                         | FMKorea HTTP         |
                         +----------^-----------+
                                    |
                                    |
+----------------------+   outbound |   +----------------------+
| PostgreSQL           |<-----------+---| fmkorea worker       |
| checkpoints          |                | one-shot container   |
+----------------------+                +----------+-----------+
                                                   |
                                                   | outbound
+----------------------+                           v
| Garage/S3 storage    |<--------------------------+
| JSONL/report/media   |
+----------------------+

Later:
  other-community worker containers reuse PostgreSQL/Garage by env endpoints.
```

The scraper container does not own PostgreSQL or Garage lifecycle.

## Worker Container Runtime

Container execution:

```powershell
docker run --rm `
  --env-file .env `
  fmkorea-scraper-worker
```

Runtime flow:

```text
container process
  |
  +-- /app/docker-entrypoint.sh
  +-- python -m fmkorea_scraper.adapters.container
  +-- ContainerEnvConfig.from_env(os.environ)
  +-- build_container_runtime(...)
  +-- run_job(...) or resume_job(...)
  +-- save output to Garage/S3
  +-- save checkpoint to PostgreSQL
  +-- exit 0/1/2
```

The container has no inbound HTTP API.

## Environment Injection

The image is immutable and credential-free.

Runtime configuration enters through:

- `docker run --env KEY=value`
- `docker run --env-file .env`
- equivalent orchestrator secret/env injection later

Required runtime links:

| Env | Target |
|---|---|
| `DATABASE_URL` | PostgreSQL checkpoint database |
| `S3_ENDPOINT_URL` | Garage/S3-compatible endpoint |
| `S3_BUCKET` | object storage bucket |
| `S3_ACCESS_KEY_ID` | object storage access key |
| `S3_SECRET_ACCESS_KEY` | object storage secret key |

Optional runtime links:

| Env | Purpose |
|---|---|
| `S3_REGION` | S3 client region |
| `S3_FORCE_PATH_STYLE` | Garage/path-style compatibility |
| `S3_PREFIX` | object key prefix |
| `RESUME` | run resume mode |
| `JOB_ID` | select checkpoint/job id |
| `FMKOREA_REALTIME_*` | realtime mode end condition |
| `FMKOREA_PROXY_*` | optional proxy runtime |

## Storage Architecture

Durable output path:

```text
worker -> temp spool -> Garage/S3 object upload -> output success
```

Checkpoint path:

```text
worker -> PostgresCheckpointStore -> fmkorea_checkpoints
```

Checkpoint progress advances only after durable output succeeds.

Resume creates a new output run object set and loads checkpoint state from PostgreSQL.

## Optional Compose Architecture

Compose may exist only for local/smoke use.

Allowed smoke topology:

```text
docker-compose.smoke.yml
  postgres
  garage
  fmkorea-worker
```

Rules:

- not part of default tests
- not the production topology
- no hard coupling between FMKorea worker and storage lifecycle
- storage services should be replaceable by external endpoints through env

This prevents a scraper-specific compose stack from becoming the shared platform boundary for later community scrapers.

## MCP Deployment Shape

Default MCP shape:

```text
local agent process
  |
  +-- stdio
      |
      +-- python -m fmkorea_scraper.adapters.mcp
          |
          +-- MCP tool handlers
          +-- core scraper APIs
```

The MCP server:

- starts only from explicit MCP entrypoint
- uses optional `mcp` dependency
- exposes no network port in the first deployment shape
- returns safe JSON payloads

HTTP/SSE MCP transport is deferred.

## Network Architecture

Worker:

| Direction | Endpoint | Required |
|---|---|---|
| outbound | FMKorea | yes |
| outbound | PostgreSQL | yes for container checkpoint mode |
| outbound | Garage/S3 | yes for container output mode |
| outbound | proxy | optional |
| inbound | none | no |

MCP stdio:

| Direction | Endpoint |
|---|---|
| local stdio | MCP client/agent process |
| inbound network | none |

## Volume Architecture

Worker:

- no required persistent volume
- process-local temp spool only
- cleanup is best effort

PostgreSQL/Garage:

- persistent volume or external managed storage is required outside the worker
- optional smoke compose may use named volumes for these services

## Signal Architecture

```text
Docker stop / SIGTERM
  |
  +-- ContainerMain requests JobRunner stop API
      |
      +-- current unit completes best-effort
      +-- output/checkpoint/report path runs
      +-- process exits with code 1 if stopped
```

Normal completion exits `0`.

Validation failure before a Job starts exits `2`.

## Test Deployment Architecture

Default gate:

```text
pytest
  |
  +-- fake PostgreSQL connection
  +-- fake S3 client
  +-- MCP handlers without MCP server
  +-- JSONL/report fixtures
  +-- no Docker or live network
```

Optional smoke gate:

```text
pytest -m "docker or garage or postgres or mcp or live"
```

Each smoke test must require explicit env and skip by default.

## Security Boundary

Required runtime safety:

- no credential in image
- no credential in logs
- no raw env dump
- no signed URL or secret in `StoredObjectRef`
- no traceback or secret in MCP error responses
- no inbound worker port

## Infrastructure Handoff

Future platform units may add:

- shared scheduler or queue
- multi-community worker orchestration
- production deployment manifests
- managed PostgreSQL/Garage provisioning
- networked MCP transport with auth
- monitoring/metrics stack

UOW-008 keeps those as handoff items and implements only the adapter/runtime boundary needed now.
