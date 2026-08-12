# Infrastructure Design - UOW-002 HTTP Runtime Policy

## Scope

UOW-002 is not a deployable scraper worker. It defines an importable Python HTTP runtime used by later units:

- `httpx.AsyncClient` lifecycle
- request limiter
- retry and timeout policy
- User-Agent rotation
- Proxy resolution from explicit options or `.env`
- response classification
- safe structured HTTP events
- fake transport and optional live smoke test boundary

Search traversal, post/comment/media parsing, JobRunner orchestration, Garage output storage, PostgreSQL checkpoint storage, container entrypoints, and MCP tools are handled by later units.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for standalone UOW-002 service/container deployment |
| Compute | local development and CI test runner only |
| Runtime files | explicit path first; otherwise execution-location `.env` and `user-agents.txt` at runtime creation only |
| Networking | no proxy gateway, VPC, NAT, or egress topology in this unit |
| Secret storage | plaintext `.env` accepted as documented exception; redaction required at log/error boundaries |
| Monitoring | no external monitoring stack; safe events through UOW-001 `LoggerPort` only |
| Live smoke | excluded by default; env-gated single HEAD/GET smoke only |
| Shared infrastructure | no Garage, PostgreSQL, queue, or shared infrastructure artifact for UOW-002 |

## Deployment Environment

UOW-002 is an importable runtime package layer, not a standalone service.

Required environment:

- Python package build/import environment
- local unit/PBT execution environment
- CI unit/PBT execution environment
- optional live smoke execution environment when explicitly enabled

Not required:

- Docker image owned by UOW-002
- scheduler
- queue consumer
- hosted service
- MCP server process
- cloud account resources

## Compute Infrastructure

No persistent compute infrastructure is provisioned for UOW-002.

The only execution targets are:

- local developer machine for fake transport, limiter, retry, redaction, and config tests
- CI runner for unit tests and property-based tests
- optional manual smoke run against FMKorea when enabled by environment variable

Worker container sizing, scale-out policy, and multi-worker scheduling are deferred to JobRunner and container units.

## Runtime File Boundary

Runtime file lookup rules:

1. Use explicit runtime file path when provided.
2. If no explicit path exists, read execution-location `.env` for proxy profile.
3. If no explicit User-Agent path exists, read execution-location `user-agents.txt`.
4. Read both files only at runtime creation.

UOW-002 may read these files:

- `.env`
- `user-agents.txt`

UOW-002 must not:

- create missing files
- open terminal file pickers
- prompt for proxy credentials
- edit `.env`
- edit `user-agents.txt`
- read files at package import

File creation and terminal UX belong to CLI/container adapter units.

## Networking Infrastructure

No concrete networking infrastructure is defined for UOW-002.

UOW-002 only configures outbound HTTP behavior inside `httpx.AsyncClient`:

- `proxy=...` when proxy config is valid
- `trust_env=False`
- explicit timeout
- safe headers
- in-memory cookies only

Not defined in this unit:

- proxy gateway
- proxy pool
- VPC
- NAT gateway
- load balancer
- API gateway
- egress topology

## Secret And Configuration Storage

Plaintext `.env` is accepted as a documented local/container exception.

Required controls:

- raw `.env` content is never logged
- proxy password is never logged
- credential-containing proxy URL is never logged
- raw cookies are never logged or persisted
- safe events may include only proxy enabled state, source, and redacted host label

No secret manager or encrypted credential store is introduced in UOW-002.

## Monitoring Infrastructure

No external monitoring stack is defined for UOW-002.

UOW-002 emits safe structured events through UOW-001 `LoggerPort`:

- request start
- request end
- retry attempt
- classified failure
- proxy enabled state
- User-Agent rotation

OpenTelemetry, Prometheus, alerting, log shipping, and dashboarding are deferred until there is a deployed worker/container runtime.

## Live Smoke Test Infrastructure

Live smoke tests are optional and disabled by default.

Activation:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Rules:

- not part of mandatory unit tests
- not part of mandatory CI gate
- use a dedicated test marker
- perform at most one lightweight HEAD/GET request
- no CAPTCHA bypass or automation
- no persisted cookies

## Shared Infrastructure

No shared infrastructure is created by UOW-002.

Deferred shared infrastructure:

| Infrastructure | Target Unit |
|---|---|
| Garage S3-compatible JSONL/media storage | UOW-006 and UOW-008 |
| PostgreSQL checkpoint store | UOW-008 |
| queue or worker scheduler | UOW-005 and UOW-008 |
| container entrypoint `.env` injection | UOW-008 |
| MCP server hosting | UOW-008 or later adapter unit |
| SeaweedFS extension path | later storage evolution |

## Implementation Impact

Code generation for UOW-002 should not create Docker, Terraform, cloud resource definitions, database migrations, object storage buckets, queues, scheduler config, or monitoring configuration.

Code generation may create:

- HTTP runtime package modules
- `httpx` and `python-dotenv` dependencies
- fake transport tests
- optional live smoke test marker
- safe logging helpers
- User-Agent and Proxy runtime readers

## Deferred Items

| Deferred Item | Target Unit |
|---|---|
| search collectors and pagination traversal | UOW-003 |
| post/comment/media parsers | UOW-004 |
| worker queue and checkpoint orchestration | UOW-005 |
| JSONL/media/Garage storage | UOW-006 |
| CLI runtime prompts and file creation | UOW-007 |
| container entrypoint, PostgreSQL checkpoint, MCP, live smoke harness integration | UOW-008 |
