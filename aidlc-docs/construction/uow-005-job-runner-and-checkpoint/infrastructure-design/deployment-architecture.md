# Deployment Architecture - UOW-005 Job Runner And Checkpoint

## Architecture Classification

UOW-005 has no standalone deployed runtime architecture.

It is a JobRunner package layer consumed by later scraper adapters.

```text
Developer or CI
    |
    v
UOW-005 Python JobRunner package
    |
    +-- JobRunner
    +-- RunnerState / RunnerCounters
    +-- CandidateQueue
    +-- CollectorTask
    +-- PostWorkerPool
    +-- CheckpointCoordinator
    +-- MediaDownloadCoordinator
    +-- FailureRecorder
    +-- ReportBuilder
    |
    v
Unit tests, fake dependency tests, policy PBT

Later units import UOW-005:
CLI adapter
container/runtime adapter
MCP adapter
parser-stage retry unit
future platform queue consumer
future CDK/platform infrastructure
```

## Environment Topology

| Environment | UOW-005 Role | Infrastructure |
|---|---|---|
| Local development | run deterministic runner tests with fakes | developer Python environment |
| CI | run unit/PBT tests without live services | CI runner and temp filesystem |
| Runtime CLI | imported by future CLI command/wizard | no UOW-005-owned resources |
| Runtime container | imported by future worker entrypoint | no UOW-005-owned resources |
| MCP server | imported by future MCP tools | no UOW-005-owned resources |
| Platform worker | future SQS/platform consumer calls runner | queue infrastructure deferred |

## Runtime Boundaries

UOW-005 import must not:

- read environment variables
- read `.env`
- prompt terminal input
- open user-agent files
- open cookie files
- connect to FMKorea
- connect to S3/Garage
- connect to PostgreSQL
- create queues
- start background workers

Runtime side effects begin only when a caller constructs `JobRunner` with explicit dependencies and calls `run` or resume behavior.

At runtime, UOW-005 may:

- create `asyncio` tasks
- create an in-process `asyncio.Queue`
- call injected collector/parser/http/storage ports
- update in-memory counters
- save checkpoints through injected port
- write failure/report data through injected ports
- finalize injected stores best-effort

At runtime, UOW-005 must not:

- create concrete storage from environment
- create HTTP clients from environment
- solve or bypass CAPTCHA
- own external Job queue leases
- provision cloud resources

## Configuration Flow

```text
CLI/container/MCP/future platform adapter
    |
    v
environment variables, args, prompt, or platform payload
    |
    v
JobConfig
    |
    +-- UOW-002 HttpPort
    +-- UOW-003 collector
    +-- UOW-004 detail service
    +-- UOW-006 stores
    +-- clock/logger
    |
    v
JobRunner
```

Core UOW-005 code receives configuration through `JobConfig` and dependencies. Adapter-level mapping is deferred.

## In-Process Execution Topology

```text
JobRunner
    |
    +-- asyncio.Event stop_event
    +-- asyncio.Queue[PostCandidate]
    |
    +-- CollectorTask
    |       |
    |       v
    |   LinkCollectorService.collect(...)
    |
    +-- PostWorker 1
    +-- PostWorker 2
    +-- ...
            |
            v
        PostDetailService.parse(...)
            |
            v
        optional HttpPort.download(...)
            |
            v
        OutputStorePort / MediaStorePort / FailureStorePort
            |
            v
        CheckpointStorePort
```

The queue is internal to one Job run. It is not a distributed queue.

## Storage Runtime Handoff

Storage is supplied by UOW-006 or later compatible adapters.

```text
JobRunner
    |
    +-- append_post(PostResult)
    +-- write_failure(FailureRecord)
    +-- save_media(MediaItem, bytes)
    +-- save_metadata_only(MediaItem)
    +-- save(Checkpoint)
    +-- write_report(JobReport)
    |
    v
Injected storage ports
```

UOW-005 decides call order. Storage adapters decide persistence details.

## Checkpoint Runtime Handoff

```text
RunnerState
    |
    v
CheckpointCoordinator
    |
    +-- running checkpoint every 10 stored posts
    +-- stopped checkpoint on stop-class events
    +-- completed checkpoint on normal completion
    +-- failed checkpoint when possible
    |
    v
CheckpointStorePort
```

Resume creates a new `run_id` and uses restored completed keys for dedupe.

## External Services

| Service Type | Status | Reason |
|---|---|---|
| Local filesystem | Indirect dependency | used only through injected UOW-006 local stores |
| Garage/S3-compatible object storage | Indirect dependency | used only through injected UOW-006 stores |
| SeaweedFS | Deferred replacement option | storage contract remains S3-compatible |
| PostgreSQL | Deferred | checkpoint adapter is not in UOW-005 |
| Queue/SQS/DLQ | Deferred | platform-level Job queue is outside this unit |
| Monitoring backend | Deferred | UOW-005 emits safe events only through `LoggerPort` |
| AWS CDK | Deferred | no cloud resources are created in this unit |

## Test Architecture

Default test path:

```text
pytest / Hypothesis
    |
    +-- fake collector
    +-- fake detail service
    +-- fake HTTP downloader
    +-- fake output/failure/media/checkpoint stores
    +-- fake clock/logger
    |
    v
deterministic JobRunner tests
```

Test categories:

- runner service examples
- worker behavior examples
- checkpoint coordinator examples
- pure policy examples
- pure policy property tests

No default UOW-005 test reaches external websites or external storage.

## Observability Handoff

Safe logger events are optional and port-based.

Allowed runtime observability:

- aggregate counters
- status
- stop reason
- safe post key
- safe URL
- checkpoint save event
- worker lifecycle event

Deferred observability:

- metrics backend
- tracing backend
- log collector
- alerting
- dashboards

## Security Boundary

Required behavior:

- no raw HTML in checkpoint/report/failure/log context
- no raw body in checkpoint/report/failure/log context
- no full post/comment body text in operational context
- no cookies, proxy passwords, tokens, access keys, or secret keys in runner-created payloads
- no environment values read by core runner
- no CAPTCHA bypass automation

## Infrastructure Handoff

UOW-005 hands off execution capability to later units:

- public `fmkorea_scraper.runner` exports
- explicit dependency bundle
- in-process worker lifecycle
- checkpoint timing contract
- resume/new-run behavior
- safe failure/report event contract

Later units decide:

- CLI commands and wizard prompts
- runtime `.env` mapping
- user-agent/cookie/proxy file loading
- container entrypoint
- MCP tool shapes
- PostgreSQL checkpoint backend
- SQS/DLQ queue consumer
- Garage/SeaweedFS deployment
- AWS CDK resources

## Deployment Summary

UOW-005 ships as library code and tests only.

No UOW-005-specific Docker image, Compose stack, Kubernetes manifest, Terraform module, CDK stack, database migration, bucket policy, queue, scheduler, monitoring stack, or live smoke environment is created in this phase.
