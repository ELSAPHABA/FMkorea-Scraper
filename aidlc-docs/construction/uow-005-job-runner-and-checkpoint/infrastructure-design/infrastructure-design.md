# Infrastructure Design - UOW-005 Job Runner And Checkpoint

## Scope

UOW-005 is not a deployable scraper worker. It defines an importable Python JobRunner library used by later CLI, container, MCP, and platform units.

In scope:

- in-process `asyncio` Job orchestration
- post-candidate queue lifecycle
- fake dependency unit/PBT test environment
- explicit dependency injection boundary
- checkpoint save/load call timing
- safe report/failure/checkpoint payload boundary
- adapter handoff points for future runtime units

Out of scope:

- CLI wizard and terminal prompts
- container entrypoint
- MCP server hosting
- PostgreSQL checkpoint adapter
- parser-stage retry reprocessor
- SQS/DLQ and lease protocol
- Docker Compose topology
- AWS CDK resources
- centralized platform scheduler

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for standalone UOW-005 service/container deployment |
| Compute infrastructure | no persistent compute; local/CI Python runner tests only |
| Storage infrastructure | no new storage resources; use UOW-006 ports |
| Messaging infrastructure | in-process `asyncio.Queue[PostCandidate]` only |
| Networking infrastructure | no network topology; use injected UOW-002 `HttpPort` |
| Runtime config boundary | accept `JobConfig` and explicit dependencies only |
| Checkpoint infrastructure | define timing/payload rules; storage backend belongs to UOW-006/later adapters |
| Observability infrastructure | no monitoring stack; emit safe events through `LoggerPort` |
| Live smoke | deferred to CLI/container adapter once real Job execution exists |
| Shared infrastructure | not created or owned by UOW-005 |

## Deployment Environment

UOW-005 runs inside whichever Python process imports it.

Required environment:

- Python package build/import environment
- local unit/PBT execution environment
- CI unit/PBT execution environment
- fake collector/parser/http/storage dependencies for default tests
- temp filesystem only when fake/local stores need it

Not required:

- Docker image owned by UOW-005
- ECS/EKS service
- Kubernetes deployment
- queue consumer process
- Garage/S3-compatible storage provisioning
- PostgreSQL server
- MCP server process
- AWS account resources

## Compute Infrastructure

UOW-005 does not allocate persistent compute infrastructure.

Runtime compute is one Python process controlled by a caller:

```text
Caller process
    |
    v
JobRunner
    |
    +-- collector task
    +-- post worker task 1
    +-- post worker task 2
    +-- ...
```

`WorkerConfig.post_worker_count` controls in-process post worker tasks. It does not imply external container replicas, ECS tasks, Kubernetes pods, or distributed workers.

## Storage Infrastructure

UOW-005 does not define new storage resources.

It uses injected ports:

- `OutputStorePort`
- `FailureStorePort`
- `MediaStorePort`
- `CheckpointStorePort`

Storage behavior owned by UOW-005:

- call output before completed-key advancement
- call checkpoint after completed-key advancement
- save running checkpoint every 10 successful output appends
- save terminal checkpoint on completed/stopped/failed runs
- write final report when possible
- avoid unsafe payloads in checkpoint/report/failure context

Storage behavior not owned by UOW-005:

- local file layout
- S3-compatible object key layout
- Garage/SeaweedFS deployment
- bucket creation
- PostgreSQL schema/migrations
- JSONL append internals
- media file path generation

## Messaging And Queue Infrastructure

UOW-005 uses only an internal `asyncio.Queue`.

Queue role:

- move `PostCandidate` values from collector task to post worker tasks
- apply bounded backpressure when `queue_max_size` is configured
- carry internal sentinel values to stop workers after collection completes

Not included:

- external Job queue
- SQS
- DLQ
- Redis queue
- visibility timeout
- lease renewal
- distributed worker scaling

Future platform queue consumers should create or load `JobConfig`, then call `JobRunner` instead of replacing the in-process candidate queue.

## Networking Infrastructure

UOW-005 does not own network topology.

Network calls occur through dependencies:

- UOW-003 collector uses configured HTTP runtime
- UOW-004 detail parser uses configured HTTP runtime for detail/comment requests
- UOW-005 media download path calls injected UOW-002 `HttpPort.download`

Proxy, User-Agent, cookies, request pacing, retry policy, timeout policy, and block/CAPTCHA response classification remain UOW-002 or adapter responsibilities.

UOW-005 must not:

- create an HTTP client from environment
- read proxy credentials
- read cookie files
- open browser automation
- configure VPC/NAT/proxy gateway resources

## Runtime Configuration Boundary

UOW-005 receives already-built values.

Inputs:

- `JobConfig`
- `JobRunDependencies`
- optional explicit resume checkpoint/request

Configuration not read by UOW-005:

- process environment
- `.env`
- terminal input
- user-agent file
- cookie file
- proxy profile
- container secrets

Adapters map runtime sources into models before constructing the runner.

```text
CLI/container/MCP/future platform adapter
    |
    v
env, args, prompt, platform payload
    |
    v
JobConfig + concrete dependencies
    |
    v
JobRunner
```

## Checkpoint Infrastructure Boundary

UOW-005 owns checkpoint timing and safe payload rules.

UOW-005 does:

- load checkpoint for resume through `CheckpointStorePort`
- restore `job_config`, `collector_cursor`, `completed_keys`, and optional `queued_links`
- create a new `run_id` on resume
- save running checkpoints every 10 successful outputs
- save terminal checkpoints immediately when possible

UOW-005 does not:

- implement local `Checkpoint.json`
- implement PostgreSQL checkpoint tables
- choose object storage versus filesystem
- append to old run output after resume
- store raw request/response payloads in checkpoints

## Observability Infrastructure

No external monitoring infrastructure is created by UOW-005.

Safe observability events may be emitted through `LoggerPort`:

- job started
- collector started/completed
- worker started/completed
- candidate skipped because completed
- post stored
- checkpoint saved
- failure recorded
- stop requested
- job completed/stopped/failed

Event payloads must be allow-listed and must not include:

- raw HTML
- raw response body
- full post/comment body text
- raw headers
- cookies
- proxy credentials
- storage credentials
- tokens

Prometheus, OpenTelemetry, log shipping, alerting, and dashboards are deferred to runtime/operations units.

## Test Infrastructure

Default tests require no live infrastructure.

Default test dependencies:

- fake collector
- fake detail service
- fake HTTP downloader
- fake output store
- fake failure store
- fake media store
- fake checkpoint store
- fake clock/logger

Default test scope:

- normal run lifecycle
- worker fan-out
- bounded queue behavior
- completed-key skip
- output-before-checkpoint ordering
- checkpoint cadence
- stop-class checkpoint save
- resume with new run id
- media semaphore limit
- safe failure/report payloads
- store finalization
- pure policy PBT

No default test should require outbound network, FMKorea live pages, browser automation, Garage/S3, PostgreSQL, SQS/DLQ, Docker, MCP, or CDK.

## Live Smoke Boundary

UOW-005 does not define a live smoke environment.

Reason:

- the runner is an orchestration library
- live smoke requires concrete CLI/container/runtime wiring
- UOW-003/UOW-004/UOW-006 already own lower-level parser/storage smoke boundaries

Future CLI/container smoke tests should verify the full path:

```text
runtime config
    |
    v
collector -> runner queue -> parser -> media policy -> output -> checkpoint -> report
```

## Shared Infrastructure

No shared infrastructure is created by UOW-005.

Deferred shared infrastructure:

| Infrastructure | Target Area |
|---|---|
| CLI wizard and command mapping | future CLI unit |
| container entrypoint and env injection | future container/runtime unit |
| MCP server hosting | future MCP adapter unit |
| PostgreSQL checkpoint adapter | future storage/runtime unit |
| parser-stage retry reprocessor | UOW-009 |
| SQS/DLQ and lease protocol | future platform/CDK work |
| Garage/SeaweedFS service topology | operations/CDK work |
| AWS CDK resources | later infrastructure UOW |

## Implementation Impact

Code generation for UOW-005 should not create Docker, Compose, Terraform, AWS CDK, database migrations, object storage buckets, queues, schedulers, or monitoring configuration.

Code generation may create:

- `src/fmkorea_scraper/runner/` package
- runner models
- runner policies
- checkpoint coordinator
- worker pool
- media download coordinator
- failure recorder
- report builder
- fake dependency tests
- pure policy PBT
- public runner exports

## Deferred Items

- interactive CLI wizard
- concrete `python -m ...` command execution flow
- Docker/container entrypoint
- MCP tool wrapper
- PostgreSQL checkpoint backend
- parser-stage failure retry unit
- SQS/DLQ job consumer
- cloud deployment/IaC
