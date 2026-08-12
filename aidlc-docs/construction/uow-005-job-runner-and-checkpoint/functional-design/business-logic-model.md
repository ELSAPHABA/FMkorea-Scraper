# Business Logic Model - UOW-005 Job Runner And Checkpoint

## Purpose

UOW-005 orchestrates one scraper Job from link collection through post detail parsing, optional media download, durable output, checkpoint update, and final report generation.

This unit owns Job lifecycle control, `asyncio.Queue`-based post fan-out, worker cancellation, stop/resume behavior, checkpoint save timing, and storage success ordering. It does not own FMKorea URL/query parsing, detail page parsing, storage implementation internals, CLI prompts, container entrypoints, MCP tools, PostgreSQL checkpoint storage, SQS/DLQ, or AWS CDK.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Runner boundary | `JobRunner` receives `JobConfig` and injected collector/parser/http/storage dependencies, then returns `JobReport` or `JobRunResult`. |
| Queue topology | One collector task enqueues `PostCandidate` items; multiple post workers consume candidate units. |
| Worker count | `WorkerConfig.post_worker_count` controls post workers; `queue_max_size` controls optional backpressure. |
| Media handling | No separate media worker pool in UOW-005; `media_worker_count` is used as media download concurrency limit inside post processing. |
| Checkpoint advance | Completed keys advance only after optional media handling and `append_post` succeed. |
| Checkpoint cadence | Save running checkpoint every 10 stored posts and immediately on stop/error/CAPTCHA/block/timeout/completion. |
| Resume | Restore `job_config`, `collector_cursor`, `completed_keys`, and optional `queued_links`; create a new `run_id`. |
| In-flight restore | Exact in-flight request restoration is not guaranteed. Completed key dedupe prevents duplicate output. |
| Stop policy | CAPTCHA/block fail closed. No automatic CAPTCHA bypass. |
| Failure output | Safe `FailureRecord` values are written for parser, media, storage, checkpoint, and stop-class failures. |
| Realtime termination | Stop collecting new candidates when duration/end-at condition is reached; finish already queued candidates before completed checkpoint/report. |
| Public API | Add a small `fmkorea_scraper.runner` package for library use; adapters call the same core runner later. |

## Normal Job Flow

1. Caller builds or validates `JobConfig`.
2. Caller creates concrete dependencies:
   - UOW-002 HTTP client/port
   - UOW-003 link collector
   - UOW-004 detail parser
   - UOW-006 storage bundle
   - optional logger/clock
3. `JobRunner.run(job_config)` creates a new `run_id`.
4. Runner creates `asyncio.Queue[PostCandidate]`.
5. Runner creates one collector task.
6. Runner creates `post_worker_count` post worker tasks.
7. Collector traverses the configured source and enqueues candidates.
8. Workers parse detail pages, handle media according to `MediaMode`, write output, and advance checkpoint only after output succeeds.
9. Runner waits until collection ends and the queue is drained.
10. Runner writes a completed checkpoint and final `JobReport`.
11. Runner finalizes output/failure stores and returns the report/result.

## Candidate Queue Flow

The queue item is one `PostCandidate`.

```text
SearchCollectionService
    |
    v
asyncio.Queue[PostCandidate]
    |
    +-- PostWorker 1
    +-- PostWorker 2
    +-- ...
```

Rules:

- There is one collector task per Job.
- There are `WorkerConfig.post_worker_count` post workers.
- `queue_max_size` creates bounded queue backpressure when provided.
- Job-level queueing is out of scope and belongs to later platform/SQS work.

## Post Worker Flow

For each candidate:

1. Build a stable `PostKey`.
2. Skip if the key already exists in checkpoint `completed_keys`.
3. Fetch/parse detail through UOW-004 `PostDetailService`.
4. If `MediaMode.DOWNLOAD`, download media bytes through UOW-002 and store them through UOW-006 `MediaStorePort`.
5. If media mode is URL-only, keep URL metadata and avoid HTTP media download.
6. Append final `PostResult` through UOW-006 `OutputStorePort`.
7. Add the key to completed keys.
8. Save running checkpoint when cadence is reached.
9. Update counters used for final `JobReport`.

If parsing or media handling fails, the worker writes a safe `FailureRecord` and continues unless the failure is a stop-class condition.

## Media Download Flow

`MediaMode.URL_ONLY`:

- Do not download files.
- Preserve media URLs and metadata in `PostResult`.
- Optionally call `save_metadata_only` when the storage adapter needs to update references.

`MediaMode.DOWNLOAD`:

1. Iterate media items from `PostResult.media`.
2. Use UOW-002 `download(url)`.
3. Store bytes with UOW-006 `MediaStorePort.save_media`.
4. Replace the media item with the returned item containing `file_path` or `object_key`.
5. Continue with post output write.

Media download failure is recorded as failure. The exact policy for partial media failure must be explicit in business rules before code generation.

## Checkpoint Flow

Running checkpoint contains:

- `job_id`
- `status=running`
- `job_config`
- latest `collector_cursor` when available
- `completed_keys`
- optional `queued_links`
- `updated_at`

Save timing:

- after every 10 successful post outputs
- immediate manual stop
- immediate CAPTCHA/block stop
- immediate timeout/error stop
- normal completion

Completed checkpoint uses:

- `status=completed`
- `reason=null`

Stopped checkpoint uses:

- `status=stopped`
- `reason` set to the mapped `StopReason`

Checkpoint writes must not contain raw cookie, proxy credentials, access keys, raw HTML, headers, or full body text.

## Resume Flow

Resume loads a checkpoint by `job_id`, or the latest checkpoint if the caller allows that behavior.

Resume behavior:

1. Validate checkpoint schema through UOW-001 models.
2. Restore `job_config`.
3. Restore `completed_keys`.
4. Requeue `queued_links` first when present.
5. Resume collector from `collector_cursor` when present and supported by the collector.
6. Create a new `run_id`.
7. Run the normal queue/worker pipeline.

Resume must not append to an earlier `posts.jsonl`. UOW-006 creates a new run output path.

## Stop And Failure Flow

Stop-class events:

- manual stop
- timeout
- CAPTCHA
- blocked response
- unrecoverable runner error
- lease expired in future platform integration

Stop behavior:

1. Set the runner stop event.
2. Stop collecting new candidates.
3. Cancel or finish workers according to failure class.
4. Save stopped checkpoint with reason.
5. Write final report.
6. Finalize stores.

CAPTCHA and blocked response fail closed. The runner does not bypass, solve, or automate CAPTCHA.

## Realtime Flow

Realtime Job sources use `RealtimeTermination`.

Rules:

- Exactly one of `duration_seconds` or `end_at` is valid because UOW-001 validates it.
- Collector polling stops when the termination condition is reached.
- Already queued candidates are allowed to finish.
- Final status is completed unless a stop/error condition occurs.
- Manual stop, CAPTCHA, block, timeout, and error still produce stopped checkpoint.

## Report Flow

Runner maintains counters:

- collected candidates
- skipped completed candidates
- stored posts
- failures
- media stored
- stop reason

At end, runner writes `JobReport` through UOW-006:

- completed Job -> `status=completed`
- stopped Job -> `status=stopped`
- unrecoverable failure -> `status=failed`

Report output includes safe `StoredObjectRef` values and aggregate counts only. Detailed safe failures remain in `failures.jsonl`.

## Testable Properties

- Queue items are post candidates, not Jobs.
- Completed keys are advanced only after post output succeeds.
- Resume creates a new run while preserving completed-key dedupe.
- Stop-class failures save stopped checkpoint with a reason.
- Completed realtime termination saves completed checkpoint after queued work drains.
- Failure records are safe and do not include raw secret or body fields.
- Worker cancellation finalizes stores.
- No CLI, container, MCP, SQS, or CDK behavior is required in UOW-005.
