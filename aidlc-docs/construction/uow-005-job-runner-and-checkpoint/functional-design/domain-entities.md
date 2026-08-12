# Domain Entities - UOW-005 Job Runner And Checkpoint

## Existing Contract Entities

UOW-005 reuses model and port contracts from earlier units.

| Entity | Source | Role |
|---|---|---|
| `JobConfig` | `models/job.py` | immutable Job configuration used by the runner |
| `WorkerConfig` | `models/job.py` | post worker count, media concurrency, queue size |
| `ScrapeOptions` | `models/job.py` | media mode, comment mode, retry-related scrape options |
| `RealtimeTermination` | `models/job.py` | realtime duration or end-at stop condition |
| `PostCandidate` | `models/job.py` | queue item collected by UOW-003 |
| `PostKey` | `models/job.py` | completed-key identity stored in checkpoint |
| `Checkpoint` | `models/checkpoint.py` | resumable lifecycle state |
| `CollectorCursor` | `models/checkpoint.py` | collector progress hint |
| `PostResult` | `models/post.py` | parsed detail result from UOW-004 |
| `MediaItem` | `models/media.py` | media metadata and storage reference |
| `FailureRecord` | `models/failure.py` | safe failure record written by UOW-006 |
| `JobReport` | `models/report.py` | final Job summary |
| `StoredObjectRef` | `models/report.py` | output reference returned by storage |
| `HttpPort` | `core/ports.py` | media download and lower-layer HTTP boundary |
| `OutputStorePort` | `core/ports.py` | post/report output |
| `MediaStorePort` | `core/ports.py` | media byte/metadata storage |
| `FailureStorePort` | `core/ports.py` | failure write/read |
| `CheckpointStorePort` | `core/ports.py` | checkpoint save/load |
| `LoggerPort` | `core/ports.py` | safe runner events |
| `ClockPort` | `core/ports.py` | timeout and testable time handling |

## New Runner Entities

### JobRunner

Core orchestrator for one Job.

Responsibilities:

- validate and run `JobConfig`
- create queue and worker tasks
- call collector, parser, HTTP download, and storage dependencies
- maintain counters
- save checkpoints
- write final report
- handle stop/cancel/error paths

Non-responsibilities:

- CLI parsing
- environment loading
- HTML parsing implementation
- storage implementation internals
- PostgreSQL adapter
- SQS/DLQ

### JobRunDependencies

Dependency bundle passed to `JobRunner`.

Fields:

- `http_client` or `http_port`
- `collector`
- `detail_service`
- `output_store`
- `failure_store`
- `media_store`
- `checkpoint_store`
- optional `clock`
- optional `logger`

Rules:

- dependencies are explicit
- import-time side effects are not allowed
- tests can inject fake dependencies

### JobRunResult

Small return object for runner execution.

Fields:

- `job_id`
- `run_id`
- `status`
- `reason`
- `report`
- `checkpoint`
- `stored_count`
- `failure_count`
- `skipped_count`

`JobReport` remains the persisted summary. `JobRunResult` is the in-memory API result for adapters and tests.

### RunnerCounters

Mutable in-memory counters for one run.

Fields:

- `collected_count`
- `queued_count`
- `skipped_completed_count`
- `stored_count`
- `failure_count`
- `media_stored_count`

Counters feed the final `JobReport`.

### RunnerState

Mutable lifecycle state for one run.

Fields:

- `job_config`
- `run_id`
- `status`
- `reason`
- `collector_cursor`
- `completed_keys`
- `queued_links`
- `stop_requested`
- `last_checkpoint_completed_count`

Runner state is converted into `Checkpoint` for persistence.

### PostWorkItem

Internal queue item.

Fields:

- `candidate: PostCandidate`

The item intentionally stays small. Job-level metadata is already in runner state.

### WorkerSummary

Per-worker or aggregate post worker result.

Fields:

- `worker_id`
- `processed_count`
- `stored_count`
- `failure_count`
- `cancelled`

This is diagnostic in-memory data, not required source JSONL output.

## Service Components

### PostWorkerPool

Consumes `PostCandidate` queue items.

Responsibilities:

- start `post_worker_count` workers
- skip completed keys before detail fetch
- call detail parser
- handle media according to `MediaMode`
- write successful post output
- write failure records
- signal stop-class failures to runner

### CheckpointCoordinator

Converts runner state to checkpoint documents.

Responsibilities:

- save running checkpoint every 10 stored posts
- save stopped checkpoint immediately
- save completed checkpoint at normal completion
- load checkpoint for resume
- preserve completed keys

### MediaDownloadCoordinator

Coordinates optional media download inside post worker flow.

Responsibilities:

- respect `MediaMode`
- cap download concurrency with `media_worker_count`
- call UOW-002 `download`
- call UOW-006 `save_media` or `save_metadata_only`
- return updated `MediaItem` list

### FailureRecorder

Creates and writes safe failure records.

Responsibilities:

- map exception/stage to `FailureRecord`
- set retryable flag consistently
- distinguish parser-stage retry candidates from stop/network/storage/checkpoint failures
- delegate redaction to UOW-006 failure store

### ReportBuilder

Builds final `JobReport`.

Responsibilities:

- map final runner status to report status
- include counts
- include safe output refs
- omit unsafe payloads

## Dependency Boundaries

| Boundary | Owner | UOW-005 Usage |
|---|---|---|
| Link collection | UOW-003 | enqueue candidates |
| Detail parsing | UOW-004 | parse one candidate into `PostResult` |
| HTTP media download | UOW-002 | download media bytes only when requested |
| Output storage | UOW-006 | append posts and write reports |
| Failure storage | UOW-006 | write failure records |
| Media storage | UOW-006 | save bytes or metadata-only references |
| Checkpoint storage | UOW-006 now, UOW-008 later | save/load checkpoints |

## Identity Rules

`PostKey` is the completed-key identity.

Preferred identity fields:

- `site_id`
- `board_id`
- `document_srl`
- `document_id_raw`

When `document_srl` is unavailable, `document_id_raw` remains required and must be stable enough for dedupe.

## Persistence Rules

Persisted by UOW-005 through UOW-006 ports:

- `PostResult` -> `posts.jsonl`
- `FailureRecord` -> `failures.jsonl`
- `JobReport` -> `report.json`
- `Checkpoint` -> `Checkpoint.json` or future checkpoint backend
- `MediaItem` bytes -> local path or S3 object key

Not persisted by UOW-005:

- raw HTML
- raw response body
- cookies
- proxy password
- S3 credentials
- exact in-flight task stack

## Test Entities

Expected fake objects for code generation:

- fake collector that enqueues known candidates
- fake detail service that returns `PostResult` or raises errors
- fake HTTP port for media downloads
- fake output/failure/media/checkpoint stores
- fake clock for realtime/timeout behavior

These fakes allow runner tests without external network, browser automation, Garage, PostgreSQL, SQS, container, or CLI.
