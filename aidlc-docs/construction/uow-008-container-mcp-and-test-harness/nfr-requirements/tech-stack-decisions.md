# Tech Stack Decisions - UOW-008 Container, MCP, And Test Harness

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches existing package baseline and Docker target. |
| Container entrypoint | `/app/docker-entrypoint.sh` -> `python -m fmkorea_scraper.adapters.container` | Splits Docker bootstrap from package runtime behavior. |
| Container image | single Python slim Dockerfile | Enough for first one-shot worker image. |
| Docker build context | `.dockerignore` excludes local state, outputs, caches, docs, workflow artifacts, build outputs, and secret candidates | Keeps image builds smaller and avoids sending unnecessary or sensitive local files to Docker. |
| Environment loading | stdlib `os.environ` at entrypoint runtime | Preserves import safety and avoids `.env` mutation inside the image. |
| Error mapping | existing `ErrorMapper` | Shared safe error boundary. |

## Dependency Decisions

| Dependency | Selection | Scope |
|---|---|---|
| `psycopg[binary]>=3,<4` | Add under `postgres` optional extra | PostgreSQL checkpoint adapter only. |
| `boto3` | Reuse existing `s3` optional extra | S3-compatible/Garage output. |
| `aioboto3`/`aiobotocore` | Not added | Extra dependency cost without current measured need. |
| Alembic | Not added | One JSON checkpoint table does not need migration framework. |
| MCP package | Add under `mcp` optional extra | MCP server/tool adapter only. |
| Polars | Add only under `analysis` or `test-analysis` optional extra if needed | Result review, not scraper runtime. |
| Docker compose | Optional smoke tool only | Not required for default tests. |

## Optional Extras Strategy

| Extra | Intended Contents | Used By |
|---|---|---|
| `s3` | `boto3>=1.34,<2` or the existing project S3 SDK boundary | Garage/S3-compatible output |
| `postgres` | `psycopg[binary]>=3,<4` | PostgreSQL checkpoint adapter |
| `mcp` | MCP server/tool package | MCP adapter entrypoint |
| `analysis` or `test-analysis` | Polars | Optional quality/analysis checks |

Default install remains focused on local scraper runtime. Container images install `.[s3,postgres]`. MCP server environments install `.[mcp]` plus any storage extras they need.

## Container Strategy

| Area | Decision |
|---|---|
| Build file | one Dockerfile |
| Context filter | `.dockerignore` |
| Base | Python 3.11+ slim image |
| Install | `pip install .[s3,postgres]` or equivalent locked install |
| Entrypoint | thin `docker-entrypoint.sh` script delegating to package module entrypoint |
| Run model | one-shot process |
| Resume | `RESUME=true`, optional `JOB_ID` |
| Storage env | `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_BUCKET`, S3 credentials |
| Logs | stdout/stderr safe structured output |

Deferred:

- multi-stage image
- multiple image targets
- Kubernetes manifests
- service scheduler

## Docker Build Context Strategy

| Area | Decision |
|---|---|
| `.git` | excluded |
| virtual environments | excluded |
| caches | excluded |
| local outputs/checkpoints | excluded |
| `.env` secret candidates | excluded |
| docs and AI-DLC workflow artifacts | excluded |
| build/dist artifacts | excluded |
| Dockerfile runtime inputs | not excluded |

`docker-entrypoint.sh` must use LF line endings so Linux containers can execute it reliably from a Windows-authored repository.

## PostgreSQL Strategy

| Area | Decision |
|---|---|
| Driver | `psycopg[binary]` optional extra |
| Schema creation | `CREATE TABLE IF NOT EXISTS` |
| Table | `fmkorea_checkpoints` |
| Primary key | `job_id` |
| Latest checkpoint | `updated_at desc` |
| Payload | full checkpoint JSON |
| Migration framework | none for first pass |

This keeps checkpoint persistence close to the existing `Checkpoint` model and avoids premature schema normalization.

## S3/Garage Strategy

| Area | Decision |
|---|---|
| SDK | existing lazy `boto3` S3 boundary |
| Async SDK | not added |
| JSONL append | local temp spool plus full object upload |
| Upload timing | upload before returning success |
| Resume | new run objects, no previous spool reuse |
| Compatibility | S3-compatible, not Garage-specific |

If real runs show S3 upload overhead dominates, later work can measure batching or async upload options. UOW-008 keeps the simpler durable-write boundary.

## MCP Strategy

| Area | Decision |
|---|---|
| Packaging | optional `mcp` extra |
| Server start | explicit MCP entrypoint only |
| Tools | search/fetch/run/resume |
| Job mode | one-shot tool call |
| Result shape | JSON-serializable success payload |
| Error shape | `ErrorMapper` safe JSON object |
| Tracebacks | not returned to MCP clients |

Deferred:

- background job registry
- progress polling
- cancellation tools
- distributed scheduler integration

## Cookie And Proxy Strategy

| Area | Decision |
|---|---|
| User cookie file | not supported |
| Server-set cookie | current `HttpClient` memory only |
| Proxy env | read at runtime only |
| Proxy password | redacted from logs, reports, failures, and MCP responses |
| Raw headers/env | not logged or returned |

## Quality Harness Strategy

| Area | Decision |
|---|---|
| Default parser | stdlib `json` |
| Fixtures | small JSONL/report/failure fixtures |
| Required checks | top-level fields, content/media/comment shape, BEST comments, nulls, report counts, safe failures |
| Polars | optional extra only |
| Live data | optional smoke only |

## Test Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example tests | pytest | Existing test runner. |
| PBT | Hypothesis | Existing project choice. |
| Fake DB/S3 | fakes or local substitutes | Keeps default tests deterministic. |
| Docker/Garage/PostgreSQL smoke | marker/env-gated | Avoids hard dependency in default gate. |
| MCP server smoke | marker/env-gated | Avoids requiring MCP runtime in default gate. |
| Live FMKorea smoke | marker/env-gated | Keeps default tests stable. |

Required default test categories:

- import side-effect safety
- env validation and redaction
- PostgreSQL checkpoint adapter with fake/local substitute
- S3 output adapter with fake client
- MCP tool validation and safe error mapping
- JSONL/report quality fixtures
- BEST comment fixture
- optional smoke skip behavior
- PBT for pure config/serialization/ref safety logic

## Deferred Decisions

- production-grade migration framework
- async S3 SDK
- multi-stage Docker image
- Docker compose as default gate
- background MCP job registry
- Kubernetes deployment manifests
- mandatory Polars runtime dependency
