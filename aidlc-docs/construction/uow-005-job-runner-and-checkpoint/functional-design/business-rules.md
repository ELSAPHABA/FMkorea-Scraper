# Business Rules - UOW-005 Job Runner And Checkpoint

## Runner Boundary Rules

- UOW-005 must expose a core runner API callable from library code.
- UOW-005 must receive dependencies through explicit construction or parameters.
- UOW-005 must not read CLI arguments.
- UOW-005 must not read environment variables.
- UOW-005 must not create container, MCP, SQS, Docker, CDK, or PostgreSQL infrastructure.
- UOW-005 must not parse FMKorea list/search/detail HTML itself.

## Queue Rules

- Internal queue items must be `PostCandidate` values.
- One Job must have one collector task.
- One Job may have multiple post worker tasks.
- `WorkerConfig.post_worker_count` must be at least 1 and controls post worker task count.
- `WorkerConfig.queue_max_size` must create a bounded queue when present.
- Queue backpressure must slow candidate enqueue instead of dropping candidates.
- External Job queueing is out of scope for UOW-005.

## Completed Key Rules

- Completed key dedupe must use stable post identity from `PostKey`.
- If `document_srl` exists, it is part of the preferred identity.
- If `document_srl` is missing, `document_id_raw` and URL-derived identity remain usable.
- A candidate whose key is already completed must be skipped before detail fetch.
- Completed keys must be updated only after post output write succeeds.
- Completed keys must not be updated after parser failure, media failure chosen as fatal, storage failure, or checkpoint failure.

## Storage Ordering Rules

- Detail parsing must finish before post output write.
- Required media download/storage must finish before post output write.
- `OutputStorePort.append_post` success is the durability boundary for completed-key advancement.
- Checkpoint save must happen after completed-key update.
- Report write happens at Job end or terminal stop/failure.
- Store finalization must be attempted even when the Job stops or fails.

## Checkpoint Cadence Rules

- Running checkpoint must be saved after every 10 successful post outputs.
- Running checkpoint may be saved more often only if a later explicit configuration says so.
- Stopped checkpoint must be saved immediately for manual stop, CAPTCHA, block, timeout, error, or future lease expiry.
- Completed checkpoint must be saved on normal completion.
- Checkpoint must contain `job_config`, completed keys, and safe progress state.
- Checkpoint must not contain raw cookie, proxy password, S3 credentials, raw headers, raw HTML, or full post body.

## Resume Rules

- Resume must load a valid `Checkpoint`.
- Resume must restore `job_config`.
- Resume must preserve `completed_keys`.
- Resume may requeue saved `queued_links` before starting collector resume.
- Resume should use `collector_cursor` when the collector supports it.
- Resume must create a new `run_id`.
- Resume must not append to an earlier run's JSONL file.
- Exact in-flight request restoration is not required.

## Stop And Cancellation Rules

- CAPTCHA and blocked response are stop-class conditions.
- CAPTCHA automatic solving or bypass must not be attempted.
- Manual stop sets `status=stopped` and `reason=manual_stop`.
- Timeout sets `status=stopped` and `reason=timeout`.
- CAPTCHA sets `status=stopped` and `reason=captcha`.
- Blocked response sets `status=stopped` and `reason=blocked`.
- Future lease expiry maps to `reason=lease_expired`.
- Workers must not keep accepting new work after stop event is set.

## Failure Record Rules

- Post parser failure must write a safe `FailureRecord`.
- Content/comment parser-stage failures that fail the post must write safe failure records.
- Media download failure must write a safe failure record.
- Storage failure must write a safe failure record when possible.
- Checkpoint failure must be surfaced as a runner failure and recorded when possible.
- CAPTCHA, block, storage, checkpoint, network, and manual stop failures must be distinguishable from parser-stage failures for later retry filtering.
- UOW-005 does not implement parser-stage retry selection; UOW-009 owns that.

## Media Rules

- `MediaMode.URL_ONLY` must not download media bytes.
- `MediaMode.DOWNLOAD` uses UOW-002 `download`.
- Media bytes must be saved through UOW-006 `MediaStorePort`.
- UOW-004 parser must not be asked to download files.
- UOW-006 media store must not be asked to fetch URLs.
- Media download concurrency must not exceed `WorkerConfig.media_worker_count`.

## Realtime Rules

- UOW-001 already enforces exactly one realtime termination condition.
- The runner must pass realtime source execution to the collector.
- When realtime termination is reached, collector stops adding new candidates.
- Workers finish queued candidates unless a stop-class event occurs.
- Normal realtime termination produces completed checkpoint/report.
- Stop-class realtime termination produces stopped checkpoint/report.

## Report Rules

- Final `JobReport` must be written for completed, stopped, and failed Jobs when storage is available.
- Report must include collected, stored, and failure counts.
- Report may include safe output refs.
- Report must not include raw HTML, raw response body, cookies, proxy password, tokens, or S3 credentials.
- Failure details belong in `failures.jsonl`, not in report.

## Public API Rules

- Public runner objects should live under `fmkorea_scraper.runner`.
- The API must be usable by Python library callers.
- CLI/container/MCP adapters should call the same core runner later.
- Public API must not require terminal interaction.
- Public API must not require environment variables at import time.

## Out Of Scope Rules

- UOW-005 does not implement CLI wizard.
- UOW-005 does not implement container entrypoint.
- UOW-005 does not implement MCP tools.
- UOW-005 does not implement PostgreSQL checkpoint adapter.
- UOW-005 does not implement parser-stage retry reprocessor.
- UOW-005 does not implement SQS/DLQ.
- UOW-005 does not implement AWS CDK resources.
