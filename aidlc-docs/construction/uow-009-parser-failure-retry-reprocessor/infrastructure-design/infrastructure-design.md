# Infrastructure Design - UOW-009 Parser Failure Retry Reprocessor

## Scope

UOW-009 adds a parser-failure retry execution path over existing scraper infrastructure.

In scope:

- one-shot retry execution through existing CLI/container command boundary
- MCP `retry_parser_failures` tool through existing stdio runtime
- explicit local failure and existing-success input refs
- explicit S3/Garage failure and existing-success input refs
- existing Garage/S3 storage config reuse
- existing PostgreSQL checkpoint store reuse during retry execution
- optional retry smoke markers

Out of scope:

- new container image
- new entrypoint script
- new inbound server port
- new PostgreSQL schema or staging table
- new queue, DLQ, scheduler, or retry daemon
- S3 prefix/output-root auto-discovery
- AWS CDK or production cloud provisioning
- CAPTCHA bypass

## Confirmed Decisions

| Area | Decision |
|---|---|
| Infrastructure footprint | no new container image, server, storage, or queue; reuse existing worker container, CLI, MCP, Garage/S3, PostgreSQL, and `JobRunner` |
| Container invocation | run existing `retry-parser-failures` command through the existing container argv/entrypoint path |
| Failure input refs | support explicit local path, `file://`, `s3://bucket/key`, and configured-bucket object key only |
| Existing success refs | optional explicit refs using the same reader boundary as failure input |
| S3/Garage access | reuse UOW-008 storage config and runtime env injection; no retry-specific credential env |
| PostgreSQL | no new table/schema; checkpoint behavior remains owned by existing `JobRunner`/`PostgresCheckpointStore` |
| Worker volume | no required persistent volume; local inputs use read-only bind mount when needed |
| MCP runtime | reuse existing stdio MCP runtime and `retry_parser_failures` binding |
| Smoke tests | default local fixture/fake runner; S3/Garage, MCP, and live retry are optional markers/env gates |
| Queue/DLQ | future platform work only; current retry is one-shot over explicit refs |

## Worker Container Boundary

UOW-009 does not add a retry-specific image.

Container execution reuses the existing worker image and entrypoint:

```text
docker run ... fmkorea-scraper-worker retry-parser-failures ...
```

Runtime flow:

```text
existing docker-entrypoint.sh
  -> python -m fmkorea_scraper.adapters.container "$@"
  -> existing command dispatch
  -> retry-parser-failures
  -> ParserFailureRetryService
  -> existing JobRunner
```

The retry command must not require:

- a second shell script
- a long-running retry daemon
- an inbound health/API port
- a retry-specific image tag

## Failure Input Reference Contract

Retry input is explicit.

Allowed failure input refs:

- local path
- `file://` URI
- `s3://bucket/key`
- object key when bucket/storage config is already provided

Not supported in UOW-009:

- scanning an output root
- scanning an S3 prefix
- selecting the latest `failures.jsonl`
- looking up input paths from PostgreSQL
- mutating old failure files or objects

All declared inputs must be accessible before the retry Job starts.

## Existing Success Input Contract

Existing success skip is optional and explicit.

Allowed success input refs:

- local path
- `file://` URI
- `s3://bucket/key`
- object key when bucket/storage config is already provided

The success input is streamed and converted into a key-only skip set.

No report/checkpoint output discovery is required for UOW-009 infrastructure.

## S3/Garage Access Boundary

S3/Garage input reads reuse existing storage config.

Runtime env remains the UOW-008 contract:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- optional `S3_REGION`
- optional `S3_FORCE_PATH_STYLE`
- optional `S3_PREFIX`

Credential rules:

- credentials are injected at runtime
- credentials are never baked into an image
- credentials are never printed in safe summaries
- user-visible refs never include credentials or signed URLs

Garage-specific APIs are not required; S3-compatible access is enough.

## PostgreSQL And Checkpoint Boundary

UOW-009 adds no PostgreSQL schema.

Retry execution uses existing checkpoint behavior:

```text
ParserFailureRetryService
  -> DirectPostSource retry Job
  -> existing JobRunner
  -> existing PostgresCheckpointStore when container checkpoint mode is configured
```

No retry candidate staging table is created.

Checkpoint progress and stop behavior remain owned by `JobRunner`.

## Local Filesystem And Volume Boundary

The worker container has no required persistent volume.

Local input usage:

```text
host failures.jsonl
  -> read-only bind mount
  -> container path passed to retry-parser-failures
```

Durable output still goes to configured output storage.

For local non-container CLI execution, normal filesystem path permissions apply.

## MCP Runtime Boundary

MCP retry uses the existing tool name:

```text
retry_parser_failures
```

Deployment shape:

```text
local agent
  -> stdio
  -> python -m fmkorea_scraper.adapters.mcp
  -> retry_parser_failures handler
  -> ParserFailureRetryService
```

UOW-009 does not add:

- HTTP/SSE MCP transport
- retry-specific MCP server
- inbound network port
- separate MCP authentication layer

Those belong to later platform deployment work.

## Optional Smoke Infrastructure

Default tests must use:

- local JSONL fixtures
- fake failure reader or temp files
- fake runner

Optional smoke markers/env gates may cover:

- S3/Garage failure input read
- MCP runtime call
- live direct-post retry

Default test gate must not require:

- Docker
- Garage
- S3 network
- PostgreSQL
- MCP runtime
- live FMKorea network

## Shared Infrastructure Impact

No shared infrastructure change is required for UOW-009.

UOW-009 consumes shared infrastructure already introduced by UOW-008:

- PostgreSQL checkpoint endpoint
- Garage/S3 output endpoint
- runtime env injection
- optional smoke marker contract
- MCP stdio runtime

Future shared platform work may add SQS/DLQ, schedulers, managed infrastructure, or queue consumers, but UOW-009 does not depend on them.

## Implementation Impact

Code generation for UOW-009 may create:

- `src/fmkorea_scraper/retry/parser_failures.py`
- CLI command wiring for `retry-parser-failures`
- MCP tool wiring for `retry_parser_failures`
- tests for local fixture retry
- optional marker/env-gated smoke tests

Code generation for UOW-009 should not create:

- new Dockerfile
- new entrypoint script
- compose stack
- PostgreSQL migration/init SQL
- queue/DLQ resource
- scheduler process
- AWS CDK
