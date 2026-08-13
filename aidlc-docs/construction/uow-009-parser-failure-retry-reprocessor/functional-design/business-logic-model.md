# Business Logic Model - UOW-009 Parser Failure Retry Reprocessor

## Purpose

UOW-009 adds a focused reprocessing path for post-level parser failures found in previous scrape runs.

The unit reads a failure input, selects only parser-stage post failures, builds a direct-post retry batch, and executes that batch through the existing `JobRunner` and `PostDetailService` path. It preserves the original failure file or object and writes retry results as a new run with normal `posts.jsonl`, `failures.jsonl`, and `report.json` outputs.

This unit does not change parser selectors, HTTP retry policy, checkpoint semantics, output JSON schema, CAPTCHA handling, or distributed queue behavior.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Retry input | local failure JSONL and S3/Garage object refs are supported |
| Retry selection | include only `stage="post"` parser/metadata/content failures by allowlist |
| Missing identity | URL is required; missing key can be recovered from URL, but missing URL is skipped |
| Existing success skip | optional existing `posts.jsonl` input skips already recovered post keys |
| Duplicate failures | dedupe by `(site_id, board_id, document_srl, document_id_raw)`; last failure URL wins |
| Execution path | convert candidates to `DirectPostSource` and reuse existing `JobRunner` |
| Scrape options | accept normal retry options and optional `from-report`/`from-checkpoint` restoration helpers |
| Output semantics | never mutate original failures; write a new retry run/report |
| Public boundary | provide importable `ParserFailureRetryService`, CLI execution, and MCP execution |
| Stop conditions | reuse existing CAPTCHA/block/manual stop checkpoint behavior |
| Tests | default tests use fixtures/fakes; external storage/MCP/live checks stay opt-in |

## Retry Flow

1. User calls CLI `retry-parser-failures`, MCP `retry_parser_failures`, or library `ParserFailureRetryService`.
2. Adapter validates `RetryRequest`, runtime options, optional existing success input, and optional restore helpers.
3. Service reads the failure input as UTF-8 JSONL.
4. Each non-empty line is parsed as JSON and validated as `FailureRecord`.
5. Service keeps only eligible retry records:
   - `stage` is `post`
   - `reason` matches parser/metadata/content allowlist
   - `url` exists and is a usable FMKorea direct post URL
6. Service converts eligible failures into retry candidates.
7. Service dedupes candidates by `(site_id, board_id, document_srl, document_id_raw)`.
8. Service reads optional existing `posts.jsonl` input and builds an `ExistingPostIndex`.
9. Candidates already present in `ExistingPostIndex` are skipped.
10. Remaining candidate URLs become a `DirectPostSource`.
11. A new `JobConfig` is created with `job_type="direct_post"`, selected `DirectPostSource`, scrape options, worker config, and storage config.
12. Service calls existing `run_job(config, runner=...)` or equivalent `JobRunner.run(config)` path.
13. Returned `JobReport` is represented as `RetryReport` with selection counters.

## Input Source Flow

Failure input may be:

- local filesystem path
- `file://` URI
- `s3://bucket/key` URI
- S3-compatible object key when a bucket is already configured

Local reads use streaming file reads. S3/Garage reads use the existing S3-compatible object boundary; Garage-specific APIs are not required.

Automatic recursive discovery of failure files under an output root is out of scope for the core service.

## Option Restoration Flow

Retry can be configured in three ways:

- explicit retry options passed through CLI/API
- `--from-report` to restore compatible options from a prior `report.json`
- `--from-checkpoint` to restore compatible options from a prior checkpoint

Precedence:

1. explicit retry CLI/API options
2. restored report/checkpoint values
3. normal `run` defaults

The service must not require report/checkpoint restoration because failure records alone do not carry every original scrape option.

## Report Flow

Retry report must expose:

- `selected_count`
- `skipped_count`
- inherited `stored_count`
- inherited `failure_count`
- inherited `output_refs`

If code generation needs more diagnostics, it may add the smallest compatible `RetryReport` field for selection summary.

## Adapter Flow

CLI and MCP adapters do only four things:

1. parse payload or argv
2. build `RetryRequest` and runtime dependencies
3. call `ParserFailureRetryService`
4. print or return safe report/error payloads

They must not duplicate failure selection, dedupe, skip indexing, or retry job construction.

## Deferred Behavior

- distributed DLQ or scheduler
- automatic background retry daemon
- mutating or compacting old `failures.jsonl`
- retrying network, storage, checkpoint, CAPTCHA, or block failures
- HTML archive reparse without a network request
- S3 prefix discovery beyond explicit object refs
- AWS CDK infrastructure
