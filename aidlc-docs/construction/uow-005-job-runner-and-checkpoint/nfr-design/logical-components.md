# Logical Components - UOW-005 Job Runner And Checkpoint

## Component Overview

UOW-005 logical components orchestrate a single scraper Job. They do not implement FMKorea URL/query parsing, detail HTML parsing, storage internals, CLI prompts, container entrypoints, PostgreSQL checkpoint storage, parser-stage retry reprocessing, SQS/DLQ, or AWS CDK.

| Component | Purpose |
|---|---|
| `JobRunner` | owns one Job lifecycle from collection through output, checkpoint, report, and finalization |
| `JobRunDependencies` | explicit dependency bundle for collector, parser, HTTP, storage, clock, and logger |
| `JobRunResult` | in-memory return value for library/adapters |
| `RunnerState` | mutable run lifecycle state converted into checkpoints |
| `RunnerCounters` | aggregate counts used by checkpoint/report/failure logic |
| `CandidateQueue` | bounded or unbounded `asyncio.Queue` of `PostCandidate` plus internal sentinel |
| `CollectorTask` | iterates UOW-003 collector output and enqueues candidates |
| `PostWorkerPool` | starts N post worker tasks and waits for completion |
| `PostWorker` | processes one `PostCandidate` at a time |
| `MediaDownloadCoordinator` | applies media mode and semaphore-limited downloads |
| `CheckpointCoordinator` | saves running/terminal checkpoints and loads resume state |
| `FailureRecorder` | creates and writes safe `FailureRecord` values |
| `ReportBuilder` | creates final aggregate `JobReport` |
| `runner.policies` | pure helpers for keys, cadence, stop mapping, and counters |
| `tests/strategies/runner.py` | reusable Hypothesis strategies for pure policy tests |

## JobRunner

Responsibilities:

- create a new `run_id` for normal runs
- create a new `run_id` for resumed runs
- initialize queue, state, counters, checkpoint coordinator, and worker pool
- start the collector task
- start post worker tasks
- handle normal completion, stop, cancellation, and failure paths
- write final checkpoint and report when possible
- finalize stores best-effort
- return `JobRunResult`

Boundaries:

- does not read environment variables
- does not parse CLI args
- does not prompt the terminal
- does not create concrete HTTP/storage adapters from config files
- does not parse HTML itself

## JobRunDependencies

Responsibilities:

- hold explicit runtime dependencies
- make tests able to inject fakes
- keep library use independent from CLI/container/MCP adapters

Expected dependencies:

- UOW-003 link collector
- UOW-004 `PostDetailService`
- UOW-002 `HttpPort`
- UOW-006 `OutputStorePort`
- UOW-006 `FailureStorePort`
- UOW-006 `MediaStorePort`
- UOW-006 `CheckpointStorePort`
- optional `ClockPort`
- optional `LoggerPort`

Rules:

- no import-time side effects
- no implicit environment lookup
- no hidden file reads

## JobRunResult

Responsibilities:

- return final in-memory run summary to library callers
- include the final `JobReport`
- include final checkpoint when available
- expose `job_id`, `run_id`, `status`, `reason`, and key counters

Persistence:

- `JobReport` is the persisted report
- `JobRunResult` is not the source JSONL record

## RunnerState

Responsibilities:

- track `job_config`
- track `run_id`
- track lifecycle status and stop reason
- track `collector_cursor`
- hold `completed_keys`
- hold optional `queued_links`
- hold last checkpoint cadence counter

Security boundary:

- no raw HTML
- no raw response body
- no cookies
- no proxy password
- no storage credentials
- no full post/comment body

## RunnerCounters

Responsibilities:

- count collected candidates
- count queued candidates
- count skipped completed candidates
- count stored posts
- count failures
- count stored media items
- feed `JobReport`
- feed failure/report diagnostics

Counters are in-memory aggregate values. They are not a substitute for `failures.jsonl`.

## CandidateQueue

Responsibilities:

- carry `PostCandidate` values from collector to workers
- enforce `queue_max_size` when configured
- provide backpressure to collector
- deliver one sentinel per worker after collection completes
- unblock shutdown paths

Boundaries:

- no external Job queue
- no SQS/DLQ
- no parser retry commands
- no raw HTML payloads

## CollectorTask

Responsibilities:

- call UOW-003 collector for the configured source
- enqueue collected `PostCandidate` values
- update collected/queued counters
- update safe collector cursor when available
- stop adding candidates when stop flag is set
- add worker sentinels on normal completion

Boundaries:

- does not fetch post detail pages
- does not append output
- does not decide completed-key advancement

## PostWorkerPool

Responsibilities:

- start `WorkerConfig.post_worker_count` workers
- share stop flag, queue, media coordinator, failure recorder, checkpoint coordinator, and counters
- wait for workers to finish
- cancel or drain according to stop class
- surface unrecoverable worker failures to `JobRunner`

## PostWorker

Responsibilities for each candidate:

1. Build completed key.
2. Skip candidate if completed key already exists.
3. Call UOW-004 detail parser.
4. Process media according to `MediaMode`.
5. Append final `PostResult` through UOW-006 output store.
6. Add completed key only after output success.
7. Trigger checkpoint cadence after completed-key update.
8. Record safe failures for parser, media, output, or stop-class errors.

Boundaries:

- does not mutate old JSONL files
- does not retry CAPTCHA/block
- does not run parser-stage retry reprocessing

## MediaDownloadCoordinator

Responsibilities:

- check `MediaMode`
- skip byte download in `URL_ONLY`
- use `HttpPort.download` only in `DOWNLOAD`
- cap concurrent downloads with `asyncio.Semaphore`
- call `MediaStorePort.save_media`
- call `MediaStorePort.save_metadata_only` when metadata-only persistence is needed
- return updated media items

Boundaries:

- no separate media worker queue
- no direct HTTP client creation
- no storage path/key calculation

## CheckpointCoordinator

Responsibilities:

- load checkpoint for resume
- build checkpoint from `RunnerState`
- save running checkpoint every 10 successful outputs
- save completed checkpoint on normal completion
- save stopped checkpoint on manual stop, timeout, CAPTCHA, block, or lease expiry
- save failed checkpoint on unrecoverable runner failure when possible
- call UOW-006 `CheckpointStorePort`

Boundaries:

- does not implement local/S3/PostgreSQL storage
- does not store unsafe context
- does not claim checkpoint success if save fails

## FailureRecorder

Responsibilities:

- map failure stage and exception class to safe failure data
- classify retryability for later parser-failure retry filtering
- distinguish parser-stage failures from network, storage, checkpoint, CAPTCHA, block, timeout, and manual stop
- call `FailureStorePort.write_failure`

Allowed details:

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

Forbidden details:

- raw headers
- raw HTML
- raw response body
- cookies
- proxy credentials
- access keys
- secret keys
- tokens

## ReportBuilder

Responsibilities:

- map final runner state to `JobReportStatus`
- include aggregate counters
- include safe output refs when available
- include stop reason when applicable
- omit detailed unsafe failure payloads

Detailed failures stay in `failures.jsonl`.

## Runner Policies

Pure helpers in `policies.py` cover:

- completed-key creation
- completed-key skip
- completed-key advancement eligibility
- checkpoint cadence calculation
- stop reason mapping
- report status mapping
- counter consistency checks

These helpers are the main PBT target.

## Test Components

### `tests/test_runner_service.py`

Covers:

- normal run completion
- collector-to-worker flow
- final report writing
- store finalization
- public API result shape

### `tests/test_runner_workers.py`

Covers:

- completed-key skip before detail fetch
- parser failure recording
- output failure preventing completed-key advancement
- media download mode behavior
- media semaphore limit
- stop-class worker signaling

### `tests/test_runner_checkpointing.py`

Covers:

- 10-success running checkpoint cadence
- terminal checkpoint saves
- checkpoint save failure behavior
- resume with completed keys
- resume with queued links
- new `run_id` on resume

### `tests/test_runner_policies.py`

Covers:

- key normalization examples
- stop reason mapping examples
- report status mapping examples
- cadence examples

### `tests/test_runner_properties.py`

Covers:

- completed-key dedupe idempotence
- checkpoint cadence properties
- report counter consistency
- resume skip set behavior
- safe context allow-list properties

### `tests/strategies/runner.py`

Provides:

- generated post keys
- generated candidate identities
- generated counter values
- generated safe/unsafe context dicts

## Component Boundaries

- UOW-003 owns link collection and source traversal.
- UOW-004 owns detail page parsing and comment/content extraction.
- UOW-002 owns HTTP runtime and media byte download primitive.
- UOW-006 owns JSONL, media, report, failure, and checkpoint persistence.
- UOW-005 owns orchestration order, worker lifecycle, checkpoint timing, resume dedupe, and safe final reporting.
- UOW-009 owns parser-stage failure retry reprocessing.
- Later adapter/platform work owns CLI wizard, container entrypoint, MCP, PostgreSQL checkpoint adapter, SQS/DLQ, Docker, CDK, and centralized scheduling.
