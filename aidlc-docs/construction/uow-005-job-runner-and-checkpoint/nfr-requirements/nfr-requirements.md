# NFR Requirements - UOW-005 Job Runner And Checkpoint

## Purpose

This document defines non-functional requirements for the FMKorea scraper JobRunner and checkpoint orchestration unit.

UOW-005 coordinates already-built HTTP, collector, parser, and storage components. It must be deterministic under tests, safe under stop-class failures, and conservative about checkpoint advancement.

## Confirmed NFR Decisions

| Question | Selected | Decision |
|---|---|---|
| Q1 | A | Use Python standard `asyncio` only for internal orchestration. |
| Q2 | A | Use bounded `asyncio.Queue` when `queue_max_size` is configured; never silently drop candidates. |
| Q3 | A | Stop/cancel runner tasks and call store `finalize` best-effort. |
| Q4 | A | Advance completed keys and checkpoints only after durable UOW-006 output success. |
| Q5 | A | Save running checkpoint every 10 successful post outputs and immediately on terminal states. |
| Q6 | A | Use checkpoint `completed_keys` for resume idempotency and write resumed output to a new `run_id`. |
| Q7 | A | Treat CAPTCHA/block/timeout/manual stop as fail-closed stop-class events. |
| Q8 | A | Use allow-list safe context for failure/report/log payloads. |
| Q9 | A | Limit media download concurrency with `media_worker_count` semaphore inside post workers. |
| Q10 | A | Use injected clock for deterministic realtime termination tests. |
| Q11 | A | Use fake collector/detail/http/storage/clock in default tests; no live network/storage required. |
| Q12 | A | Apply PBT to pure runner policies, not full async scheduling interleavings. |

## Performance Requirements

### NFR-UOW005-PERF-001. Asyncio-Only Orchestration

JobRunner must use Python standard `asyncio` primitives.

Allowed primitives include:

- `asyncio.Queue`
- `asyncio.Task`
- `asyncio.Event`
- `asyncio.Semaphore`
- task cancellation and gather/wait patterns

UOW-005 must not add `anyio`, Celery, Dramatiq, SQS clients, or external worker frameworks.

### NFR-UOW005-PERF-002. Bounded Queue Backpressure

When `WorkerConfig.queue_max_size` is set, the post candidate queue must be bounded.

The collector must wait for queue capacity instead of dropping candidates.

When a stop event occurs, enqueue waiting must be interruptible or bounded by the runner stop path.

### NFR-UOW005-PERF-003. Worker Count Respect

The runner must create no more than `WorkerConfig.post_worker_count` post worker tasks for one Job.

`post_worker_count` must be treated as the detail fetch/parse/output concurrency limit.

### NFR-UOW005-PERF-004. Media Download Concurrency

When `MediaMode.DOWNLOAD` is active, media downloads must be limited by `WorkerConfig.media_worker_count`.

The implementation may use one shared `asyncio.Semaphore` for media downloads.

UOW-005 must not add a separate media queue unless later design proves it necessary.

### NFR-UOW005-PERF-005. Memory Growth Guard

The runner must not retain every parsed `PostResult` in memory after it is written.

Required retained state is limited to:

- counters
- completed keys
- current queue
- optional queued link snapshot
- current checkpoint state
- bounded failure context

## Reliability Requirements

### NFR-UOW005-REL-001. Output-Before-Checkpoint Boundary

The runner must update completed keys only after:

1. post detail parsing succeeds
2. required media handling succeeds or is explicitly non-fatal
3. `OutputStorePort.append_post` succeeds

Checkpoint save must happen after the completed key update.

### NFR-UOW005-REL-002. Checkpoint Cadence

The runner must save a running checkpoint after every 10 successful post output writes.

The runner must save a terminal checkpoint immediately for:

- normal completion
- manual stop
- CAPTCHA
- blocked response
- timeout
- unrecoverable runner error
- future lease expiry

### NFR-UOW005-REL-003. Resume New Run

Resume must create a new `run_id`.

Resume must not append to an older run's `posts.jsonl`.

Resume must use checkpoint `completed_keys` to skip already stored candidates before detail fetch.

### NFR-UOW005-REL-004. In-Flight Restore Limitation

Exact restoration of in-flight requests is not required.

The runner must document this limitation and rely on completed-key dedupe to avoid re-storing already committed posts.

### NFR-UOW005-REL-005. Store Finalization

The runner must call output/failure store finalization on completion, stop, cancellation, and runner failure paths when the store exposes `finalize`.

Finalization failure must not expose secrets or raw payloads.

### NFR-UOW005-REL-006. Checkpoint Failure Handling

Checkpoint save/load failure must be surfaced as a runner failure.

If possible, the runner should write a safe failure record and final failed report.

The runner must not continue pretending checkpoint advancement succeeded.

### NFR-UOW005-REL-007. Stop-Class Fail Closed

CAPTCHA and blocked response errors must stop collection of new candidates.

The runner must not attempt CAPTCHA bypass, solving, browser automation, or repeated probing.

### NFR-UOW005-REL-008. Realtime Determinism

Realtime termination must use an injectable clock boundary.

Tests must be able to evaluate duration/end-at behavior without real sleeps.

When realtime termination is reached normally, queued candidates may finish before completed checkpoint/report.

## Security Requirements

### NFR-UOW005-SEC-001. No Runtime Config Side Effects

Core runner code must not read:

- command-line arguments
- environment variables
- `.env`
- `user-agents.txt`
- cookie files

Adapters in later units own runtime file and environment mapping.

### NFR-UOW005-SEC-002. Safe Failure Context

Runner-created `FailureRecord` details must use allow-list safe context only.

Allowed examples:

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

Forbidden examples:

- raw HTML
- raw response body
- full post body text
- raw headers
- cookies
- proxy password
- access keys
- secret keys
- tokens

### NFR-UOW005-SEC-003. Safe Checkpoint Payload

Checkpoint payload must not contain raw secrets or raw response payloads.

Checkpoint may contain:

- `job_config`
- `collector_cursor`
- `completed_keys`
- `queued_links`
- lifecycle status/reason

### NFR-UOW005-SEC-004. Safe Report Payload

`JobReport` must contain aggregate counts and safe output references only.

Detailed failures must be written to `failures.jsonl`.

Report must not include raw HTML, raw body, cookies, proxy credentials, tokens, or storage credentials.

### NFR-UOW005-SEC-005. Dependency Injection Boundary

External capabilities must be injected.

Runner must not instantiate concrete HTTP, collector, parser, S3, PostgreSQL, CLI, or MCP adapters from environment at import time.

## Maintainability Requirements

### NFR-UOW005-MAINT-001. Small Runner Package

Runner code should live under `src/fmkorea_scraper/runner/`.

Suggested modules:

- `models.py`
- `policies.py`
- `checkpointing.py`
- `workers.py`
- `service.py`

Do not create plugin registries or framework abstractions before there is more than one implementation.

### NFR-UOW005-MAINT-002. Explicit Fakes For Tests

Default tests must use simple fake dependencies for:

- collector
- detail service
- HTTP download
- output store
- failure store
- media store
- checkpoint store
- clock

Tests must not require live FMKorea, Garage, PostgreSQL, SQS, Docker, or MCP.

### NFR-UOW005-MAINT-003. Clear Deferred Boundaries

The following remain out of UOW-005:

- CLI prompt UX
- container entrypoint
- PostgreSQL checkpoint adapter
- MCP tools
- parser-stage retry reprocessor
- SQS/DLQ
- Docker
- AWS CDK
- centralized platform scheduler

## Testability Requirements

### NFR-UOW005-TEST-001. Default Test Scope

Default tests must cover:

- queue fan-out
- completed-key skip before detail fetch
- output-before-checkpoint ordering
- checkpoint cadence
- stop-class checkpoint save
- resume from checkpoint
- media download semaphore
- failure record generation
- report counter consistency
- store finalization on stop/error

### NFR-UOW005-TEST-002. Property-Based Test Scope

PBT should cover pure runner policies:

- completed-key dedupe idempotence
- checkpoint cadence calculation
- stop reason mapping
- report counter consistency
- resume skip set behavior

Async task scheduling interleavings should use example tests, not broad PBT.

### NFR-UOW005-TEST-003. No Live Dependency In Default Gate

Default test gate must not require:

- outbound network
- FMKorea live pages
- browser automation
- Garage or S3-compatible object storage
- PostgreSQL
- SQS/DLQ
- container runtime

### NFR-UOW005-TEST-004. Deterministic Time

Realtime and timeout behavior must be testable with a fake clock.

Tests must avoid real sleep-based timing where a fake clock or fake sleeper can prove the same behavior.

## Acceptance Criteria

- UOW-005 uses only standard `asyncio` for worker orchestration.
- Candidate queue item is one `PostCandidate`.
- Bounded queue does not silently drop candidates.
- Completed key updates happen only after output write success.
- Running checkpoint cadence is 10 successful outputs.
- Terminal checkpoint is saved for completed, stopped, and failed runs when possible.
- Resume uses a new `run_id` and completed-key skip.
- CAPTCHA/block stop path is fail-closed.
- Failure/checkpoint/report/log payloads exclude raw secrets and raw body fields.
- Default tests use fake dependencies and pass without live services.
- PBT targets pure runner policies.
