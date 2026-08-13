# Tech Stack Decisions - UOW-005 Job Runner And Checkpoint

## Decision Summary

| Concern | Decision | Reason |
|---|---|---|
| Async orchestration | Python standard `asyncio` | Existing requirement and enough for in-process workers. |
| Candidate queue | `asyncio.Queue[PostCandidate]` | Matches feature spec; no external Job queue in UOW-005. |
| Backpressure | bounded `asyncio.Queue` when configured | Limits memory without dropping candidates. |
| Worker fan-out | `asyncio.Task` workers | Minimal dependency-free implementation. |
| Media concurrency | `asyncio.Semaphore` | Caps downloads without a separate media queue. |
| Time boundary | injected clock/fake clock | Deterministic realtime/timeout tests. |
| Checkpoint cadence | internal constant `10` successful outputs | Matches feature spec without expanding config yet. |
| Resume dedupe | `completed_keys` set behavior | Avoids old JSONL mutation and in-flight restore complexity. |
| Failure/report safety | allow-list context | Prevents secret/raw payload leakage. |
| Default tests | fake dependencies | Fast, deterministic, no live infrastructure. |
| PBT | pure policies only | Useful signal without async scheduling flakiness. |

## Dependencies

No new runtime dependency is added for UOW-005.

Already available dependencies remain:

- `pydantic` for models
- `httpx` through UOW-002 HTTP runtime
- `beautifulsoup4` through UOW-003/UOW-004 parsing
- standard library `asyncio`
- standard library `uuid`, `datetime`, and `contextlib` as needed

Test dependencies already available:

- `pytest`
- `hypothesis`

## Rejected Dependencies

| Dependency | Decision | Reason |
|---|---|---|
| `anyio` | Not added | Backend-neutral async is unnecessary for current in-process runner. |
| Celery/Dramatiq/RQ | Not added | External distributed worker framework belongs outside UOW-005. |
| SQS client | Not added | SQS/DLQ is later platform/CDK work. |
| PostgreSQL driver use | Not added in this unit | PostgreSQL checkpoint adapter is deferred. |
| Browser automation | Not added | CAPTCHA bypass and browser-driven scraping are out of scope. |

## Module Direction

Recommended code layout for UOW-005:

```text
src/fmkorea_scraper/runner/
  __init__.py
  models.py
  policies.py
  checkpointing.py
  workers.py
  service.py
```

Purpose:

- `models.py`: `JobRunDependencies`, `JobRunResult`, `RunnerCounters`, runner state value objects
- `policies.py`: completed-key conversion, checkpoint cadence, stop reason mapping, report status/counter helpers
- `checkpointing.py`: checkpoint load/save coordination
- `workers.py`: post worker pool and media download coordination
- `service.py`: `JobRunner`

Keep this package boring. Do not add an interface for every helper until there is another implementation.

## Integration Contracts

UOW-005 consumes:

| Contract | Owner | Usage |
|---|---|---|
| `HttpPort` | UOW-001/UOW-002 | media download and lower-level HTTP errors |
| collector service | UOW-003 | enqueue `PostCandidate` values |
| `PostDetailService` | UOW-004 | parse one candidate into `PostResult` |
| `OutputStorePort` | UOW-001/UOW-006 | append post and write report |
| `FailureStorePort` | UOW-001/UOW-006 | write safe failures |
| `MediaStorePort` | UOW-001/UOW-006 | write media bytes or metadata-only references |
| `CheckpointStorePort` | UOW-001/UOW-006 | save/load checkpoint |
| `ClockPort` | UOW-001 | deterministic time handling |
| `LoggerPort` | UOW-001 | safe structured events |

## Runtime Boundary

UOW-005 runner creation must not:

- read environment variables
- read CLI args
- prompt terminal input
- open `.env`
- open `user-agents.txt`
- accept user-provided cookie input
- connect to S3
- connect to PostgreSQL
- create SQS queues
- start a container/MCP server

Those concerns stay with adapter or infrastructure units.

## Resiliency Decisions

| Scenario | Required Behavior |
|---|---|
| post parser failure | write safe failure, continue unless stop-class |
| media download failure | write safe failure; post output policy must be explicit in NFR design/code plan |
| output append failure | do not advance completed key; record safe failure when possible |
| checkpoint save failure | treat as runner failure; do not pretend progress was committed |
| CAPTCHA/block | fail closed, stop new work, save stopped checkpoint |
| manual stop | stop new work, save stopped checkpoint |
| realtime termination | stop collecting, drain queued work, save completed checkpoint |
| cancellation | best-effort finalize stores |

## Testing Stack

Default tests:

- `tests/test_runner_service.py`
- `tests/test_runner_policies.py`
- `tests/test_runner_checkpointing.py`
- `tests/test_runner_workers.py`
- `tests/test_runner_properties.py`
- `tests/strategies/runner.py`

Test doubles:

- fake collector
- fake detail service
- fake HTTP downloader
- fake output store
- fake failure store
- fake media store
- fake checkpoint store
- fake clock/logger

No live smoke test is required for UOW-005. Live behavior is already owned by HTTP/parser/storage smoke tests in earlier units or later adapter units.

## Security Decisions

Runner-created event/failure/report details must use allow-list safe fields.

Forbidden values:

- raw HTML
- raw response body
- full post/comment body text
- raw headers
- cookies
- proxy IDs/passwords
- access keys
- secret keys
- tokens

UOW-006 failure store redaction remains the final storage boundary, but UOW-005 must not intentionally pass unsafe data.

## Future Extension Notes

Later units may add:

- CLI storage and resume options
- container env injection
- PostgreSQL checkpoint adapter
- MCP tools
- parser-stage retry reprocessor
- SQS/DLQ and lease handling
- AWS CDK resources

These extensions should call or wrap UOW-005 runner APIs instead of duplicating orchestration logic.
