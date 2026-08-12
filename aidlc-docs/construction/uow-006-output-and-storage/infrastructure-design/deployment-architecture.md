# Deployment Architecture - UOW-006 Output And Storage

## Architecture Classification

UOW-006 has no standalone deployed runtime architecture.

It is an output/storage package layer consumed by later scraper units and adapters.

```text
Developer or CI
    |
    v
UOW-006 Python output/storage package
    |
    +-- OutputRunLayout
    +-- JSONL writer
    +-- local object/media store
    +-- local checkpoint store
    +-- optional S3-compatible object store
    +-- optional S3 JSONL spool
    +-- StorageFactory
    |
    v
Unit tests, fake S3 tests, optional smoke tests

Later units import UOW-006:
UOW-005 JobRunner and checkpoint advancement
UOW-007 CLI
UOW-008 container and MCP
later CDK/platform infrastructure
```

## Environment Topology

| Environment | UOW-006 Role | Infrastructure |
|---|---|---|
| Local development | write local output to configured base path or temp dirs | developer Python environment and filesystem |
| CI | run deterministic local/fake S3 tests | CI runner and temp filesystem |
| Runtime scraper | imported by later JobRunner/CLI/container units | no UOW-006-owned runtime resources |
| Optional S3 smoke | verify S3-compatible write/read/delete path | external Garage/S3-compatible endpoint supplied by env/config |
| Optional Polars smoke | verify JSONL can be read by Polars | local Python environment with optional `analysis` extra |

## Runtime Boundaries

UOW-006 import must not:

- read environment variables
- read `.env`
- prompt terminal input
- create output directories
- connect to S3
- connect to PostgreSQL
- create buckets
- create queues
- start background workers

Runtime side effects begin only when a caller explicitly constructs stores and writes output.

At runtime, UOW-006 may:

- create configured output directories
- append JSONL records
- write media bytes supplied by callers
- write report JSON
- save/load local checkpoint JSON
- upload objects to a configured S3-compatible endpoint
- keep a local S3 spool file for JSONL output

At runtime, UOW-006 must not:

- fetch media from HTTP URLs
- decide scraper worker lifecycle
- advance checkpoints before the caller confirms durable write ordering
- store secrets in generated artifacts
- provision external infrastructure

## Configuration Flow

```text
CLI/container/MCP/future platform adapter
    |
    v
environment variables, args, or platform config
    |
    v
StorageConfig
    |
    v
StorageFactory
    |
    +-- Local output/checkpoint stores
    |
    +-- optional S3-compatible output store
```

Core UOW-006 code receives configuration through `StorageConfig`. Adapter-level environment mapping is deferred to later units.

## Local Output Runtime

```text
StorageConfig(base_output_path=...)
    |
    v
OutputRunLayout(job_id, run_id)
    |
    +-- posts.jsonl
    +-- failures.jsonl
    +-- report.json
    +-- media/...
    +-- Checkpoint.json
```

Local writes use the local filesystem only. Tests use temp directories.

## S3-Compatible Runtime

```text
StorageConfig(output_mode=s3_compatible, s3=...)
    |
    v
StorageFactory
    |
    +-- S3ObjectStore
    |
    +-- S3JsonlSpool
            |
            +-- append local spool
            +-- upload same object key after each append
```

S3 object keys mirror local relative paths under the configured prefix.

Garage is the default external target, but the deployment architecture depends only on the S3-compatible endpoint/bucket/prefix contract.

## External Services

| Service Type | Status | Reason |
|---|---|---|
| Local filesystem | In scope | primary local output/checkpoint target |
| Garage/S3-compatible object storage | Optional external dependency | used only when S3 output mode or smoke test is selected |
| SeaweedFS | Deferred replacement option | same S3-compatible contract can support it later |
| PostgreSQL | Deferred | UOW-006 only implements local checkpoint file persistence |
| Queue/SQS/DLQ | Deferred | worker orchestration and retry scheduling belong to later units |
| Monitoring backend | Deferred | UOW-006 only emits safe storage errors/events through existing ports when available |
| AWS CDK | Deferred | no cloud resources are created in this unit |

## Test Architecture

Default test path:

```text
pytest / Hypothesis
    |
    +-- output layout tests
    +-- JSONL writer tests
    +-- failure redaction tests
    +-- media path/key tests
    +-- local checkpoint tests
    +-- fake S3 key/spool tests
    +-- traversal rejection tests
    |
    v
deterministic output/storage tests
```

S3 smoke path:

```text
FMKOREA_S3_SMOKE_ENABLED=true
complete S3-compatible env/config
    |
    v
small object write/read/delete smoke
    |
    v
Garage or another S3-compatible endpoint
```

Polars smoke path:

```text
optional analysis extra installed
    |
    v
sample posts.jsonl
    |
    v
polars.read_ndjson
```

Smoke tests are not mandatory default CI gates.

## Security Boundary

Required security behavior:

- no access key or secret key in JSONL
- no access key or secret key in checkpoint/report/failure files
- no endpoint credential fragments in logs or errors
- no cookie/proxy/token/password in stored object refs
- no generated output outside configured output root
- no path traversal through job, post, board, media type, or filename fields

## Infrastructure Handoff

UOW-006 hands off storage capability to later units:

- output layout contract
- local JSONL/media/report/checkpoint implementations
- S3-compatible object key contract
- S3 spool durability boundary
- storage factory contract
- optional smoke test gates

Later units decide:

- JobRunner checkpoint advancement timing
- concrete CLI flags and wizard prompts
- container env injection
- Garage/PostgreSQL service deployment
- MCP tool exposure
- SQS/DLQ integration
- AWS CDK resource definitions

## Deployment Summary

UOW-006 ships as library code and tests only.

No UOW-006-specific Docker image, Compose stack, Kubernetes manifest, Terraform module, CDK stack, database migration, bucket policy, queue, scheduler, or monitoring stack is created in this phase.
