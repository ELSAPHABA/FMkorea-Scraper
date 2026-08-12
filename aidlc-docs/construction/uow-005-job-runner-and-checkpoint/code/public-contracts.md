# Public Contracts - UOW-005 Job Runner And Checkpoint

## Public Package

UOW-005 exposes the import-safe runner package:

```python
from fmkorea_scraper.runner import JobRunDependencies, JobRunResult, JobRunner
```

Package import does not read environment variables, `.env`, user-agent files, cookie files, proxy profiles, storage credentials, or start network/storage connections.

## JobRunDependencies

`JobRunDependencies` is the explicit dependency bundle for `JobRunner`.

Required dependencies:

- `collector`: object with `collect(source)` async iterator yielding `PostCandidate`
- `detail_service`: object with `parse(candidate)` returning `PostResult`
- `output_store`: `OutputStorePort`
- `failure_store`: `FailureStorePort`
- `media_store`: `MediaStorePort`
- `checkpoint_store`: `CheckpointStorePort`

Optional dependencies:

- `http`: `HttpPort`, required only when `MediaMode.DOWNLOAD` needs byte downloads
- `clock`: `ClockPort`, defaults to `SystemClock`
- `logger`: `LoggerPort`, reserved for safe events

## JobRunner

Primary methods:

```python
runner = JobRunner(dependencies)
result = await runner.run(job_config)
result = await runner.resume(resume_request)
runner.stop()
```

`run` starts a new run id. `resume` loads a checkpoint, restores `job_config`, `collector_cursor`, `completed_keys`, optional `queued_links`, and starts a new run id.

## JobRunResult

`JobRunResult` contains:

- `job_id`
- `run_id`
- `status`
- `reason`
- `report`
- `checkpoint`
- `stored_count`
- `failure_count`
- `skipped_count`
- `output_refs`

The persisted report remains `JobReport`; `JobRunResult` is the in-memory library/adapters return value.

## Core API Bridge

`core.api.run_job(config, runner=...)` delegates to the explicit runner and returns `JobReport`.

`core.api.resume_job(request, runner=...)` delegates to the explicit runner and returns `JobReport`.

When no runner is passed, both functions keep raising `UnsupportedSourceError` until CLI/container/MCP wiring exists.

## Checkpoint Contract

Checkpoint advancement rules:

- completed keys advance only after `OutputStorePort.append_post` succeeds
- running checkpoint is saved every 10 successful post outputs
- terminal checkpoint is saved on completed/stopped/failed paths when possible
- failed paths use stopped checkpoint status with `StopReason.ERROR` because the existing checkpoint schema has no failed status
- resume creates a new run id and does not append to older run output

## Failure Contract

Runner-created failures use `FailureRecord` and safe allow-list details.

Tracked stages:

- `collect`
- `post`
- `media`
- `output`
- `checkpoint`
- `runner`

CAPTCHA and blocked responses fail closed as stopped Jobs. Parser/media failures are recorded and can continue when not stop-class. Output/checkpoint failures stop the Job as failed.

## Media Contract

`MediaMode.URL_ONLY` does not call `HttpPort.download`.

`MediaMode.DOWNLOAD` uses one shared `asyncio.Semaphore(media_worker_count)`, calls `HttpPort.download`, then stores bytes through `MediaStorePort.save_media`.

## Deferred Contracts

Not implemented in UOW-005:

- CLI wizard
- environment mapping
- concrete HTTP/storage construction
- PostgreSQL checkpoint adapter
- parser-stage retry reprocessor
- SQS/DLQ
- container entrypoint
- MCP tools
- Docker/CDK/cloud resources
