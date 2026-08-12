# Tech Stack Decisions - UOW-006 Output And Storage

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches existing package baseline. |
| Local filesystem | `pathlib`, `tempfile`, `os.replace` | Standard library covers safe path handling and atomic replace. |
| JSON serialization | stdlib `json` plus Pydantic `model_dump(mode="json")` | Keeps output deterministic without another dependency. |
| Process-local lock | stdlib lock primitive | Enough for single-process local checkpoint writes. |
| S3-compatible client | optional `s3` extra with `boto3` | Garage/SeaweedFS should use a proven S3 client instead of custom request signing. |
| Polars smoke | optional `analysis` extra | Analysis readiness is useful but not required for core local storage. |

## Dependency Decisions

| Dependency | Selection | Scope |
|---|---|---|
| Pydantic | existing core dependency | Serialize validated models. |
| JSONL library | Not added | One JSON object plus newline is trivial with stdlib `json`. |
| File lock library | Not added | Multi-process local checkpoint locking is out of scope. |
| Polars | optional `analysis` extra only | Used for source JSONL smoke, not required to write JSONL. |
| S3 client | existing optional `s3` extra, `boto3` first | Avoids S3 signing code and keeps local installs small. |
| Async S3 client | Not added by default | UOW-006 storage can remain simple; JobRunner can decide executor offload later. |
| Garage-specific client | Not added | S3-compatible boundary keeps SeaweedFS replaceable. |

## Storage Strategy

| Area | Decision |
|---|---|
| Post output | append-only `posts.jsonl` |
| Failure output | append-only `failures.jsonl` |
| Report output | atomic replace `report.json` |
| Checkpoint output | atomic replace `Checkpoint.json` |
| Resume output | same `job_id`, new `run_id` |
| Media output | local file path or S3 object key on `MediaItem` |
| S3 object paths | mirror local relative paths |
| S3 JSONL append | file-backed spool plus same-key upload after each append |

## Durability Strategy

| Area | Decision |
|---|---|
| JSONL flush | after every record |
| JSONL fsync | optional, disabled by default |
| JSONL repair | ignore final invalid partial line during later recovery |
| Single JSON docs | temp file and atomic replace |
| S3 append success | success only after upload completes |
| Checkpoint concurrency | process-local lock only |

## Security Strategy

| Area | Decision |
|---|---|
| Path safety | sanitize each segment and verify resolved path stays below base directory |
| Failure context | allow-list only |
| Allowed request fields | URL, status code, response kind, parser warning code |
| Forbidden fields | proxy ID/PW, cookies, tokens, passwords, raw headers, raw HTML/body/content |
| Credentials in refs | forbidden |
| Local generated files | excluded by `.gitignore` policy |

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example tests | pytest | Existing test runner. |
| PBT | Hypothesis | Existing project choice. |
| Temporary dirs | pytest `tmp_path` | Keeps local storage tests isolated. |
| S3 tests | key/spool behavior in default tests; live Garage optional | Default tests remain fast and deterministic. |
| Polars tests | optional `analysis` extra smoke | Verifies source JSONL remains analysis-friendly without core dependency bloat. |

Required default test categories:

- local output append
- failure output append and redaction
- report atomic write
- local media save
- checkpoint save/load/load_latest
- path traversal rejection
- JSONL round trip
- S3 key generation
- S3 spool same-key upload behavior with fake object store
- pure function PBT

## Deferred Decisions

These are intentionally left for later units:

- JobRunner checkpoint commit ordering
- worker retry policy
- HTTP media download
- PostgreSQL checkpoint adapter
- CLI output path prompts
- container Garage provisioning
- MCP storage tool surface
- AWS CDK storage infrastructure
