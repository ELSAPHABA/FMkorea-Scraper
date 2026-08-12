# NFR Design Patterns - UOW-005 Job Runner And Checkpoint

## Scope

This document translates UOW-005 NFR requirements into implementation patterns. It covers runner package layout, `asyncio` task lifecycle, queue item/sentinel handling, completed-key policy, checkpoint coordination, resume, stop/failure mapping, media concurrency, safe failure/report builders, deterministic time, test organization, and public API boundaries.

## Confirmed Design Decisions

| Question | Answer | Design Decision |
|---|---|---|
| Q1 | A | Put runner code under `src/fmkorea_scraper/runner/` with focused modules for models, policies, checkpointing, workers, and service orchestration. |
| Q2 | A | Let `JobRunner` own one collector task, N post worker tasks, shared stop event, and sentinel-based shutdown. |
| Q3 | A | Use `PostCandidate` as the external queue item and one internal sentinel per worker after collection completes. |
| Q4 | A | Put completed-key helpers in `policies.py` and advance completed keys only after output append success. |
| Q5 | A | Use a `CheckpointCoordinator` for running/terminal checkpoint snapshots, 10-success cadence, and storage delegation. |
| Q6 | A | Resume from checkpoint by restoring config, cursor, completed keys, optional queued links, and creating a new `run_id`. |
| Q7 | A | Map stop-class events and failures through pure policy helpers; CAPTCHA/block fail closed without retry loops. |
| Q8 | A | Use a shared `asyncio.Semaphore(media_worker_count)` inside a `MediaDownloadCoordinator`. |
| Q9 | A | Use allow-list `FailureRecorder` and `ReportBuilder` payloads before calling storage. |
| Q10 | A | Inject a small clock dependency for realtime/timeout behavior and fake it in tests. |
| Q11 | A | Split runner service, worker, checkpoint, policy, PBT, and strategy tests; default tests use fakes only. |
| Q12 | A | Export `JobRunner`, `JobRunDependencies`, and `JobRunResult` from `fmkorea_scraper.runner` without environment or terminal side effects. |

No follow-up question is required.

## Pattern 1. Runner Package Layout

UOW-005 implementation belongs under:

```text
src/fmkorea_scraper/runner/
  __init__.py
  models.py
  policies.py
  checkpointing.py
  workers.py
  service.py
```

Responsibilities:

- `models.py`: `JobRunDependencies`, `JobRunResult`, `RunnerCounters`, `RunnerState`, internal queue item aliases
- `policies.py`: completed-key conversion, checkpoint cadence, stop reason mapping, report status/counter helpers
- `checkpointing.py`: checkpoint snapshot creation, save/load coordination, resume state preparation
- `workers.py`: candidate queue consumption, post processing, media download coordination
- `service.py`: `JobRunner` orchestration and public run/resume methods

Package import must not read CLI args, environment variables, `.env`, user-agent files, cookie files, S3 credentials, PostgreSQL settings, or MCP configuration.

## Pattern 2. Task Lifecycle

`JobRunner.run(job_config)` owns one in-process Job lifecycle.

Normal flow:

1. Create a new `run_id`.
2. Build `RunnerState`, `RunnerCounters`, `asyncio.Event` stop flag, and bounded or unbounded `asyncio.Queue`.
3. Start one collector task.
4. Start `WorkerConfig.post_worker_count` post worker tasks.
5. Collector iterates UOW-003 candidates and enqueues them.
6. Workers consume candidates, parse details, optionally process media, append output, and trigger checkpoint updates.
7. Collector completion enqueues one sentinel per worker.
8. Runner waits for queue drain and worker completion.
9. Runner writes terminal checkpoint and final report.
10. Runner calls store finalization best-effort.

Stop-class flow:

1. Set stop flag.
2. Stop collecting new candidates.
3. Let safe queued work finish only when the stop reason allows it.
4. Save stopped checkpoint immediately.
5. Write final report when storage remains available.
6. Finalize stores best-effort.

## Pattern 3. Queue Item And Sentinel

The queue is post-candidate based.

External payload:

- `PostCandidate`

Internal control payload:

- private sentinel value used only by `workers.py`

Rules:

- queue item is not a Job
- queue item is not raw HTML
- queue item is not a retry command
- collector adds one sentinel per worker after normal collection completion
- stop path must unblock enqueue/worker waits
- bounded queue backpressure waits instead of dropping candidates

`queue_max_size=None` keeps the queue unbounded. A configured positive size creates `asyncio.Queue(maxsize=queue_max_size)`.

## Pattern 4. Completed-Key Policy

Completed-key behavior is centralized in `policies.py`.

Policy helpers:

- build stable key from `PostCandidate`
- build stable key from `PostResult` when needed
- normalize key to checkpoint-storable value
- decide whether a candidate should skip detail fetch
- calculate whether checkpoint cadence is due

Rules:

- skip completed candidates before detail fetch
- do not add completed key after parser failure
- do not add completed key after fatal media failure
- do not add completed key after output append failure
- add completed key only after `OutputStorePort.append_post` succeeds
- save checkpoint after completed-key update

This keeps idempotency independent from output storage implementation.

## Pattern 5. Checkpoint Coordinator

`CheckpointCoordinator` converts runner state into `Checkpoint` and delegates persistence to `CheckpointStorePort`.

Responsibilities:

- load checkpoint for resume
- create running checkpoint snapshots
- create completed/stopped/failed terminal checkpoint snapshots
- save every 10 successful output appends
- save immediately on terminal states
- preserve completed keys and safe collector cursor
- omit raw body, headers, cookies, proxy secrets, storage credentials, and raw HTML

It does not:

- write JSON files itself
- choose local versus S3-compatible storage
- own PostgreSQL storage
- append posts
- parse HTML

## Pattern 6. Resume

Resume uses a checkpoint as a safe starting point and always creates a new run.

Resume flow:

1. Load checkpoint by `job_id`, or by latest checkpoint only when caller explicitly uses that path.
2. Validate checkpoint model.
3. Restore `job_config`.
4. Restore `collector_cursor`.
5. Restore `completed_keys`.
6. Requeue `queued_links` first when present.
7. Start normal run flow with a new `run_id`.

Limitations:

- exact in-flight request restoration is not required
- old `posts.jsonl` is not appended
- duplicate prevention depends on restored completed keys

## Pattern 7. Stop Reason And Failure Mapping

Stop/failure mapping is pure policy.

Mapped stop reasons:

- `manual_stop`
- `timeout`
- `captcha`
- `blocked`
- `lease_expired`
- runner error

Rules:

- CAPTCHA and blocked responses are stopped states, not retry loops
- parser-stage failures can become safe failure records and continue when not stop-class
- checkpoint save/load failure becomes runner failure
- output append failure prevents completed-key advancement
- final report status is derived from terminal runner status

The mapper must not inspect raw HTML/body or secrets.

## Pattern 8. Media Download Coordination

`MediaDownloadCoordinator` handles optional media download inside post worker flow.

`MediaMode.URL_ONLY`:

- do not call `HttpPort.download`
- keep URL metadata
- call `MediaStorePort.save_metadata_only` only when the storage adapter needs a metadata-only reference

`MediaMode.DOWNLOAD`:

1. Acquire shared `asyncio.Semaphore(media_worker_count)`.
2. Call UOW-002 `HttpPort.download(url)`.
3. Call UOW-006 `MediaStorePort.save_media(media_item, bytes)`.
4. Replace the media item with returned storage metadata.
5. Release semaphore.

No separate media queue is created in UOW-005.

## Pattern 9. Safe Failure And Report Builders

`FailureRecorder` creates safe `FailureRecord` values.

Allowed context examples:

- `job_id`
- `run_id`
- `stage`
- `reason`
- `retryable`
- `url`
- `post_key`
- `response_kind`
- `stop_reason`
- bounded counters

Forbidden context:

- raw HTML
- raw response body
- full post/comment body text
- raw headers
- cookies
- proxy credentials
- storage credentials
- tokens

`ReportBuilder` creates aggregate `JobReport` values with safe `StoredObjectRef` references and counts. Detailed errors remain in `failures.jsonl`.

## Pattern 10. Deterministic Clock

Runner time behavior uses an injected clock boundary.

Production default:

- current UTC time
- async sleep

Tests:

- fake current time
- fake sleep advancement
- no real wait for realtime termination tests

Used for:

- timeout decisions
- realtime duration/end-at checks
- checkpoint timestamps
- report timestamps

## Pattern 11. Test Organization

Default tests:

- `tests/test_runner_service.py`
- `tests/test_runner_workers.py`
- `tests/test_runner_checkpointing.py`
- `tests/test_runner_policies.py`
- `tests/test_runner_properties.py`
- `tests/strategies/runner.py`

Default fakes:

- fake collector
- fake detail service
- fake HTTP downloader
- fake output store
- fake failure store
- fake media store
- fake checkpoint store
- fake clock/logger

Default pytest must not require live FMKorea, browser automation, Garage/S3, PostgreSQL, SQS/DLQ, Docker, MCP, or CDK.

## Pattern 12. Public API Boundary

Public exports:

- `JobRunner`
- `JobRunDependencies`
- `JobRunResult`

Core API bridge:

- `core.api.run_job(config, runner=...)` may delegate to an explicit runner
- `core.api.resume_job(request, runner=...)` may delegate to an explicit runner
- no default concrete runner is created from environment

Future adapters:

- CLI
- container entrypoint
- MCP server
- platform/SQS consumer

These adapters should call the same core runner instead of duplicating orchestration logic.

## Compliance Mapping

| Requirement Area | Design Pattern |
|---|---|
| asyncio-only orchestration | `JobRunner`, collector task, worker tasks, stop event |
| bounded queue backpressure | `asyncio.Queue(maxsize=queue_max_size)` |
| worker count respect | one worker task per configured post worker |
| media concurrency | shared `asyncio.Semaphore(media_worker_count)` |
| output-before-checkpoint | completed-key policy and checkpoint coordinator |
| checkpoint cadence | 10-success cadence helper |
| resume idempotency | completed-key skip and new `run_id` |
| fail-closed CAPTCHA/block | stop reason mapper |
| safe failure/report payload | allow-list builders |
| deterministic realtime tests | injected clock and fake clock |
| no live default tests | fake dependency test harness |
| PBT scope | pure policy helpers |
