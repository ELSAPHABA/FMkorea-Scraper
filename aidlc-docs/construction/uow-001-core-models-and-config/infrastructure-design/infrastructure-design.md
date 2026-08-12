# Infrastructure Design - UOW-001 Core Models And Config

## Scope

UOW-001 is not a deployable scraper runtime. It defines importable Python package contracts used by later units:

- Pydantic models
- Job configuration validation
- typed errors and safe adapter error results
- schema snapshot and compatibility helpers
- port protocols
- property-based test strategies

Concrete HTTP clients, parser execution, Job workers, Garage output storage, PostgreSQL checkpoint storage, container entrypoints, MCP tools, and AWS resources are handled by later units.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for UOW-001 runtime deployment |
| Compute | local development and CI test runner only |
| Storage | repository fixtures/docs for schema snapshots and migration notes |
| Messaging | no broker or queue infrastructure |
| Networking | no load balancer, gateway, VPC, or proxy infrastructure |
| Monitoring | no external monitoring stack |
| Shared infrastructure | no shared infrastructure artifact for UOW-001 |

## Deployment Environment

UOW-001 is an importable package layer, not a standalone service.

Required environment:

- Python package build/import environment
- local test execution environment
- CI test execution environment

Not required:

- container runtime
- scheduler
- hosted service
- worker deployment
- cloud account resources

## Compute Infrastructure

No persistent compute infrastructure is provisioned for UOW-001.

The only execution targets are:

- local developer machine for model and validation tests
- CI runner for unit tests, property-based tests, and schema compatibility checks

Worker container sizing and scaling are deferred to UOW-005 and UOW-008.

## Storage Infrastructure

UOW-001 stores schema compatibility artifacts inside the repository.

Expected repository artifacts:

- committed schema snapshots for persisted top-level models
- migration notes for breaking schema changes or enum changes
- test fixtures used by schema diff checks

External storage is not used in this unit.

Deferred storage decisions:

- Garage S3-compatible output storage: UOW-006 and UOW-008
- PostgreSQL checkpoint adapter: UOW-008
- SeaweedFS extension path: later storage evolution, behind the same S3-compatible port

## Messaging Infrastructure

No messaging infrastructure is defined for UOW-001.

`WorkerConfig` and port protocols may describe future queue behavior, but actual queue ownership belongs to JobRunner in UOW-005.

## Networking Infrastructure

No networking infrastructure is defined for UOW-001.

`HttpPort` is a protocol contract only. Real HTTP behavior, User-Agent rotation, Proxy handling, request delay, timeout, retry, and CAPTCHA/block classification are handled in UOW-002.

## Monitoring Infrastructure

No external monitoring stack is defined for UOW-001.

UOW-001 only provides:

- `LoggerPort` contract
- typed exceptions
- `ErrorResult` safe for adapter output
- test output from unit tests, property-based tests, schema checks, and optional smoke benchmarks

Runtime metrics, alerting, and log shipping are deferred until a runtime unit exists.

## Shared Infrastructure

No shared infrastructure is created by UOW-001.

Provider-neutral configuration models and ports remain in UOW-001 so later units can plug in local, Garage-compatible S3, PostgreSQL, and future SeaweedFS-backed implementations without changing public model contracts.

## Implementation Impact

Code generation for UOW-001 should not create:

- Dockerfiles
- compose files
- Terraform/CDK/cloud resource definitions
- database migrations
- object storage buckets
- queues
- monitoring configuration

Code generation may create:

- package metadata
- Pydantic models
- validation helpers
- error helpers
- port protocols
- schema snapshot helpers
- test fixtures and property-based strategies

## Deferred Items

| Deferred Item | Target Unit |
|---|---|
| HTTP runtime policy | UOW-002 |
| search collectors | UOW-003 |
| post/comment/media parsers | UOW-004 |
| worker queue and checkpoint orchestration | UOW-005 |
| JSONL/media/Garage storage | UOW-006 |
| CLI runtime | UOW-007 |
| container, PostgreSQL checkpoint, MCP, live smoke harness | UOW-008 |
| parser failure retry runtime | UOW-009 |
| AWS CDK infrastructure | UOW-010 |
