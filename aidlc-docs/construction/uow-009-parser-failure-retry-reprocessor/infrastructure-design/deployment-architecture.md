# Deployment Architecture - UOW-009 Parser Failure Retry Reprocessor

## Architecture Classification

UOW-009 is an operational command path inside the existing scraper runtime.

Primary deployment shapes:

- local CLI retry command
- one-shot worker container retry command
- optional MCP stdio retry tool

It does not define a new service, daemon, queue consumer, or production platform.

## Platform Topology

Recommended topology:

```text
                         +----------------------+
                         | FMKorea HTTP         |
                         +----------^-----------+
                                    |
                                    | outbound retry requests
+----------------------+            |
| PostgreSQL           |<-----------+---+----------------------+
| checkpoints          |                | existing worker      |
+----------------------+                | one-shot container   |
                                        | retry command        |
+----------------------+                +----------+-----------+
| Garage/S3 storage    |<--------------------------+
| failures/posts input |
| retry output/media   |
+----------------------+
```

The retry command is not a storage owner. It reads explicit failure/success refs and writes a new retry run through the existing output path.

## Local CLI Runtime

Local execution shape:

```text
python -m fmkorea_scraper.adapters.cli retry-parser-failures ...
  -> build retry request/options
  -> ParserFailureRetryService
  -> select parser failures
  -> DirectPostSource
  -> JobRunner
  -> local or configured output store
```

Local input refs may be normal filesystem paths.

S3/Garage refs require the existing S3-compatible config.

## Container Runtime

Container execution shape:

```text
docker run --rm `
  --env-file .env `
  fmkorea-scraper-worker `
  retry-parser-failures `
  --failure-input s3://bucket/path/failures.jsonl
```

Flow:

```text
container process
  -> existing docker-entrypoint.sh
  -> python -m fmkorea_scraper.adapters.container "$@"
  -> retry-parser-failures command
  -> storage env validation
  -> input accessibility validation
  -> ParserFailureRetryService
  -> existing JobRunner
  -> retry output to Garage/S3
  -> checkpoint to PostgreSQL when configured
  -> exit 0/1/2
```

No inbound port is required.

## Local Input Bind Mount

When the failure input is a host local file, mount it read-only:

```text
host ./outputs/run/failures.jsonl
  -> container /input/failures.jsonl:ro
  -> --failure-input /input/failures.jsonl
```

The container should not require a writable persistent worker volume.

## Storage Runtime

Failure input read:

```text
explicit input ref
  -> LocalFailureInputReader or S3FailureInputReader
  -> streaming selector
```

Existing success skip:

```text
optional explicit posts.jsonl ref
  -> same reader boundary
  -> key-only ExistingSuccessIndex
```

Retry output:

```text
selected retry URLs
  -> DirectPostSource
  -> JobRunner
  -> output store
  -> new posts.jsonl / failures.jsonl / report.json
```

Source `failures.jsonl` and old `posts.jsonl` refs are never mutated.

## Environment Injection

Container and S3/Garage retry reads reuse existing env injection.

Required when using S3/Garage storage:

| Env | Purpose |
|---|---|
| `S3_ENDPOINT_URL` | Garage/S3-compatible endpoint |
| `S3_BUCKET` | default bucket for object-key refs |
| `S3_ACCESS_KEY_ID` | access key |
| `S3_SECRET_ACCESS_KEY` | secret key |

Required for PostgreSQL checkpoint mode:

| Env | Purpose |
|---|---|
| `DATABASE_URL` | checkpoint database |

No retry-specific secret env is introduced.

## MCP Deployment Shape

MCP runtime:

```text
local MCP client
  -> stdio
  -> python -m fmkorea_scraper.adapters.mcp
  -> retry_parser_failures
  -> ParserFailureRetryService
```

The MCP tool returns safe summary fields only:

- `selected`
- `skipped`
- `stored`
- `remaining_failure`
- `report`

MCP does not expose HTTP/SSE transport in UOW-009.

## Network Architecture

Worker retry command:

| Direction | Endpoint | Required |
|---|---|---|
| outbound | FMKorea | yes, when retrying posts |
| outbound | Garage/S3 | yes, when reading/writing S3-compatible refs |
| outbound | PostgreSQL | yes, when checkpoint store is configured |
| outbound | proxy | optional |
| inbound | none | no |

MCP stdio:

| Direction | Endpoint |
|---|---|
| local stdio | MCP client/agent process |
| inbound network | none |

## Exit And Failure Behavior

Exit code contract follows existing worker behavior:

| Code | Meaning |
|---:|---|
| 0 | retry completed |
| 1 | runtime failure, blocked/CAPTCHA stop, or interrupted execution |
| 2 | validation failure before retry Job start |

Validation failures before Job start include:

- inaccessible failure input
- inaccessible existing success input
- invalid combined restore options
- missing required storage config for S3/Garage refs

## Optional Smoke Deployment

Default gate:

```text
pytest tests/test_parser_failure_retry.py
pytest tests/test_parser_failure_retry_properties.py
```

Optional smoke gate:

```text
pytest -m "garage or mcp or live"
```

Smoke tests must skip unless required env flags are present.

## Future Handoff

Future platform units may add:

- SQS or another Job Queue
- DLQ-backed retry scheduling
- worker fleet orchestration
- shared production CDK/Kubernetes deployment
- S3 prefix discovery/report lookup helpers
- networked MCP transport with auth

UOW-009 remains usable without those features because explicit input refs and one-shot retry execution are enough for the first implementation.
