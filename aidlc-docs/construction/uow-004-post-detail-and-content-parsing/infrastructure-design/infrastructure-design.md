# Infrastructure Design - UOW-004 Post Detail And Content Parsing

## Scope

UOW-004 is not a deployable scraper worker. It defines an importable Python detail parser library used by later units:

- detail HTML fetch handoff through injected UOW-002 HTTP
- final detail metadata parsing
- ordered body content parsing
- media and attachment metadata extraction
- comment/reply parsing
- BEST comment fields
- safe parser warnings
- `PostResult` assembly

List/search traversal, queue insertion, checkpoint persistence, JSONL/Garage output storage, PostgreSQL checkpoint storage, media file downloads, container entrypoints, MCP tools, and AWS CDK resources are handled by later units.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for standalone UOW-004 service/container deployment |
| Compute | local development and CI test runner only |
| Storage | no storage infrastructure; `PostResult` and safe warnings are returned to callers |
| Messaging/queue | no queue infrastructure; one post request/candidate in, one `PostResult` out |
| Networking | all detail/comment HTTP goes through caller-injected UOW-002 `HttpClient`/`HttpPort` |
| Monitoring | no external monitoring stack; safe parser events through UOW-001 `LoggerPort` only |
| Live smoke | excluded by default; env-gated public detail-page smoke only |
| Shared infrastructure | no Garage, PostgreSQL, queue, or shared infrastructure artifact for UOW-004 |

## Deployment Environment

UOW-004 is an importable library layer, not a standalone service.

Required environment:

- Python package build/import environment
- local unit/PBT execution environment
- CI unit/PBT execution environment
- optional live smoke execution environment when explicitly enabled

Not required:

- Docker image owned by UOW-004
- worker scheduler
- queue consumer
- hosted service
- MCP server process
- AWS account resources
- CDN, load balancer, VPC, or NAT owned by this unit

## Compute Infrastructure

No persistent compute infrastructure is provisioned for UOW-004.

The only execution targets are:

- local developer machine for parser fixture, policy, and fake HTTP tests
- CI runner for unit tests and property-based tests
- optional manual smoke run against FMKorea when enabled by environment variable

Worker container sizing, scale-out policy, realtime loop timing, and queue consumer counts are deferred to JobRunner and container units.

## Storage Infrastructure

No storage infrastructure is defined for UOW-004.

UOW-004 returns:

- final `PostResult`
- content blocks
- media and attachment metadata/download candidates
- comments
- safe parser warnings

UOW-004 must not write:

- JSONL files
- media files
- parser failure reports
- checkpoint records
- PostgreSQL rows
- Garage/S3 objects
- local debug output by default

Output storage, idempotent writes, and media file downloads are deferred to UOW-006 and container/storage units.

## Messaging And Queue Infrastructure

No messaging infrastructure is defined for UOW-004.

UOW-004 provides:

- one-candidate or one-request parse API
- optional `parse_html()` test/already-fetched path

UOW-004 must not own:

- `asyncio.Queue`
- SQS
- scheduler loops
- worker pools
- retry queues
- dead-letter queues

Queue consumption and worker lifecycle belong to UOW-005.

## Networking Infrastructure

No concrete networking infrastructure is defined for UOW-004.

UOW-004 sends requests only through a caller-injected UOW-002 HTTP boundary:

- `HttpClient`
- or `HttpPort`

UOW-004 must not configure:

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

No external monitoring stack is defined for UOW-004.

UOW-004 may emit safe structured events through UOW-001 `LoggerPort`:

- detail parse start
- detail parse end
- required field failure
- recoverable parser warning
- content block count summary
- media dedupe summary
- comment page fetched
- comment count summary

OpenTelemetry, Prometheus, alerting, log shipping, and dashboarding are deferred until there is a deployed worker/container runtime.

## Live Smoke Test Infrastructure

Live smoke tests are optional and disabled by default.

Activation:

- `FMKOREA_LIVE_SMOKE_ENABLED=true`

Allowed live smoke scope:

- one public detail page
- parser success
- key identity/title fields present
- no persisted cookies
- no CAPTCHA bypass
- no browser automation
- no output storage writes
- no media download

Live smoke is not part of mandatory unit tests or the mandatory CI gate.

## Shared Infrastructure

No shared infrastructure is created by UOW-004.

Deferred shared infrastructure:

| Infrastructure | Target Unit |
|---|---|
| local/async worker queue | UOW-005 |
| PostgreSQL checkpoint store | UOW-005 and UOW-008 |
| Garage S3-compatible JSONL/media storage | UOW-006 and UOW-008 |
| media file download/write path | UOW-006 |
| future SQS Job Queue | later platform/CDK work |
| container entrypoint and env injection | UOW-008 |
| MCP server hosting | UOW-008 or later adapter unit |
| AWS CDK resources | later infrastructure UOW |

## Implementation Impact

Code generation for UOW-004 should not create Docker, Terraform, AWS CDK, database migrations, object storage buckets, queues, scheduler config, or monitoring configuration.

Code generation may create:

- `src/fmkorea_scraper/parse/` package modules
- parser model extensions in UOW-001-compatible models
- BeautifulSoup parser fixtures
- parser property-based tests
- fake HTTP parser tests
- optional live smoke test marker
- safe parser warning/event structures

## Deferred Items

| Deferred Item | Target Unit |
|---|---|
| worker queue and checkpoint orchestration | UOW-005 |
| JSONL/media/Garage storage | UOW-006 |
| CLI command and wizard wiring | UOW-007 |
| container entrypoint, PostgreSQL checkpoint, MCP integration | UOW-008 |
| parser failure retry execution | UOW-009 |
| AWS CDK infrastructure | later infrastructure UOW |
