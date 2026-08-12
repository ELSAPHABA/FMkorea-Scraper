# Deployment Architecture - UOW-001 Core Models And Config

## Architecture Classification

UOW-001 has no deployed runtime architecture.

It is a shared package layer consumed by later scraper units and adapters.

```text
Developer or CI
    |
    v
UOW-001 Python package
    |
    +-- models and validation
    +-- errors and redaction helpers
    +-- schema snapshots and compatibility checks
    +-- port protocols
    |
    v
Unit tests, property-based tests, schema compatibility checks

Later units import UOW-001 contracts:
UOW-002 HTTP runtime
UOW-003 search collection
UOW-004 post parsing
UOW-005 JobRunner
UOW-006 storage
UOW-007 CLI
UOW-008 container and MCP
UOW-009 parser failure retry
UOW-010 AWS CDK infrastructure
```

## Environment Topology

| Environment | UOW-001 Role | Infrastructure |
|---|---|---|
| Local development | run model tests and validate schema behavior | developer Python environment |
| CI | run unit tests, PBT, schema compatibility checks | CI runner |
| Runtime scraper | imported by later units | no UOW-001-owned runtime resources |

## Runtime Boundaries

UOW-001 import must not:

- make network requests
- read or write files
- prompt terminal input
- load `.env`
- load `user-agents.txt`
- create output directories

Side effects begin only in later adapter/runtime units.

## External Services

UOW-001 does not connect to external services.

| Service Type | Status | Reason |
|---|---|---|
| FMKorea HTTP | Deferred to UOW-002 to UOW-004 | UOW-001 only defines `HttpPort` |
| Garage object storage | Deferred to UOW-006 and UOW-008 | UOW-001 only defines storage config and ports |
| PostgreSQL checkpoint store | Deferred to UOW-008 | UOW-001 only defines checkpoint model and port |
| Proxy service | Deferred to UOW-002 | UOW-001 must not load runtime secrets |
| Monitoring backend | Deferred | no deployed process exists in UOW-001 |

## Deployment Flow

There is no UOW-001 deployment flow.

The practical delivery flow is:

1. generate package code and tests
2. run local tests
3. run CI tests
4. allow later units to import the validated contracts

## Infrastructure Handoff

UOW-001 hands off provider-neutral contracts:

- `HttpPort`
- `OutputStorePort`
- `MediaStorePort`
- `FailureStorePort`
- `CheckpointStorePort`
- `ClockPort`
- `LoggerPort`
- `StorageConfig`
- `WorkerConfig`

Later units map these contracts to concrete infrastructure only when runtime behavior exists.

## Shared Infrastructure Decision

No `shared-infrastructure.md` is created for this unit.

Shared Garage, PostgreSQL, queue, and cloud infrastructure decisions belong to the later storage, container, and CDK units that actually use those resources.
