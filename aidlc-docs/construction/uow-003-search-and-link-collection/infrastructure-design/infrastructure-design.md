# Infrastructure Design - UOW-003 Search And Link Collection

## Scope

UOW-003 is not a deployable scraper worker. It defines an importable Python link collection library used by later units:

- direct post URL normalization
- board list URL traversal
- board keyword search traversal
- integrated search traversal
- no-keyword range traversal
- deep-search board discovery and sequential per-board search
- realtime one-cycle candidate discovery
- safe collector summaries and parser failure records

Post detail parsing, queue insertion, checkpoint persistence, JSONL/Garage output storage, PostgreSQL checkpoint storage, container entrypoints, MCP tools, and AWS CDK resources are handled by later units.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for standalone UOW-003 service/container deployment |
| Compute | local development and CI test runner only |
| Storage | no storage infrastructure; candidates and summary are returned to callers |
| Messaging/queue | no queue infrastructure; async iterator/list API only |
| Networking | all outbound HTTP goes through caller-injected UOW-002 `HttpClient`/`HttpPort` |
| Monitoring | no external monitoring stack; safe collector events through UOW-001 `LoggerPort` only |
| Live smoke | excluded by default; env-gated board list or integrated search 1-page smoke only |
| Shared infrastructure | no Garage, PostgreSQL, queue, or shared infrastructure artifact for UOW-003 |

## Deployment Environment

UOW-003 is an importable library layer, not a standalone service.

Required environment:

- Python package build/import environment
- local unit/PBT execution environment
- CI unit/PBT execution environment
- optional live smoke execution environment when explicitly enabled

Not required:

- Docker image owned by UOW-003
- worker scheduler
- queue consumer
- hosted service
- MCP server process
- AWS account resources
- CDN, load balancer, VPC, or NAT owned by this unit

## Compute Infrastructure

No persistent compute infrastructure is provisioned for UOW-003.

The only execution targets are:

- local developer machine for URL, policy, parser fixture, and fake HTTP tests
- CI runner for unit tests and property-based tests
- optional manual smoke run against FMKorea when enabled by environment variable

Worker container sizing, scale-out policy, realtime loop timing, and queue consumer counts are deferred to JobRunner and container units.

## Storage Infrastructure

No storage infrastructure is defined for UOW-003.

UOW-003 returns:

- `PostCandidate` values
- collector summaries
- safe partial failure records
- final traversal state for handoff

UOW-003 must not write:

- JSONL files
- media files
- parser failure reports
- checkpoint records
- PostgreSQL rows
- Garage/S3 objects
- local debug output by default

Output storage and idempotent writes are deferred to UOW-006 and container/storage units.

## Messaging And Queue Infrastructure

No messaging infrastructure is defined for UOW-003.

UOW-003 provides:

- async iterator collection API
- `collect_all()` convenience helper for tests and small one-shot calls

UOW-003 must not own:

- `asyncio.Queue`
- SQS
- scheduler loops
- worker pools
- retry queues
- dead-letter queues

Queue insertion and worker lifecycle belong to UOW-005.

## Networking Infrastructure

No concrete networking infrastructure is defined for UOW-003.

UOW-003 sends requests only through a caller-injected UOW-002 HTTP boundary:

- `HttpClient`
- or `HttpPort`

UOW-003 must not configure:

- proxy gateways
- proxy pools
- VPC
- NAT gateway
- load balancer
- API gateway
- host egress topology
- direct `httpx.AsyncClient`

Proxy, User-Agent, cookie, timeout, retry, rate-limit, and response classification behavior remain in UOW-002.

## Monitoring Infrastructure

No external monitoring stack is defined for UOW-003.

UOW-003 may emit safe structured events through UOW-001 `LoggerPort`:

- collector start
- collector end
- page fetched
- candidate count summary
- range termination
- row/item parse failure
- deep-search per-board failure

OpenTelemetry, Prometheus, alerting, log shipping, and dashboarding are deferred until there is a deployed worker/container runtime.

## Live Smoke Test Infrastructure

Live smoke tests are optional and disabled by default.

Activation:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Allowed live smoke scope:

- one board list page
- or one integrated search page
- no persisted cookies
- no CAPTCHA bypass
- no browser automation
- no output storage writes

Live smoke is not part of mandatory unit tests or the mandatory CI gate.

## Shared Infrastructure

No shared infrastructure is created by UOW-003.

Deferred shared infrastructure:

| Infrastructure | Target Unit |
|---|---|
| Garage S3-compatible JSONL/media storage | UOW-006 and UOW-008 |
| PostgreSQL checkpoint store | UOW-005 and UOW-008 |
| local/async worker queue | UOW-005 |
| future SQS Job Queue | later platform/CDK work |
| container entrypoint and env injection | UOW-008 |
| MCP server hosting | UOW-008 or later adapter unit |
| AWS CDK resources | later infrastructure UOW |

## Implementation Impact

Code generation for UOW-003 should not create Docker, Terraform, AWS CDK, database migrations, object storage buckets, queues, scheduler config, or monitoring configuration.

Code generation may create:

- `src/fmkorea_scraper/collect/` package modules
- BeautifulSoup parser dependency if missing
- URL builder tests
- parser fixture tests
- policy property-based tests
- optional live smoke test marker
- safe collector summary/event structures

## Deferred Items

| Deferred Item | Target Unit |
|---|---|
| post/comment/media parsers | UOW-004 |
| worker queue and checkpoint orchestration | UOW-005 |
| JSONL/media/Garage storage | UOW-006 |
| CLI command and wizard wiring | UOW-007 |
| container entrypoint, PostgreSQL checkpoint, MCP integration | UOW-008 |
| parser failure retry execution | UOW-009 |
| AWS CDK infrastructure | later infrastructure UOW |
