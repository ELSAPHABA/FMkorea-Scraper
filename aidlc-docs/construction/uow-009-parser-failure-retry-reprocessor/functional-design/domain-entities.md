# Domain Entities - UOW-009 Parser Failure Retry Reprocessor

## ParserFailureRetryService

Importable service that prepares and runs parser failure retries.

Responsibilities:

- read a failure JSONL input from local path or S3-compatible/Garage object reference
- select eligible parser-stage post failures
- dedupe retry candidates
- optionally skip posts already present in successful `posts.jsonl`
- build a `DirectPostSource`
- call the existing Job execution path
- return a retry report

The service must not parse post HTML itself.

## RetryRequest

Existing UOW-001 request model used by CLI, MCP, and library callers.

Fields:

- `failure_input`: `FailureInput`
- `skip_existing_success`: bool

UOW-009 may add only the smallest required fields for:

- existing success `posts.jsonl` input reference
- option restoration from report/checkpoint
- retry job id override

Rules:

- `failure_input.failure_path` points to a local path, `file://` URI, `s3://bucket/key`, or S3 object key understood by the configured storage adapter.
- explicit retry options override restored values.
- source failure input is read-only evidence.

## FailureInput

Existing input model for reading failure records.

Fields:

- `failure_path`
- `job_id`
- `stage_allowlist`

Rules:

- default stage allowlist remains `["post"]`.
- S3-compatible reads use the existing output/failure store boundary.
- refs must never include credentials.

## RetryFailureRecord

Internal validated view of an input `FailureRecord`.

Fields:

- `site_id`
- `board_id`
- `document_srl`
- `document_id_raw`
- `url`
- `stage`
- `reason`
- `retryable`
- `source_line_number`

Rules:

- `site_id` defaults to `fmkorea` when absent.
- records without a usable retry URL are skipped as invalid selection records.
- source line number is diagnostic only.

## RetryCandidate

Direct-post retry target produced from an eligible failure.

Fields:

- `key`: `(site_id, board_id, document_srl, document_id_raw)`
- `url`
- `board_id`
- `document_srl`
- `document_id_raw`
- `last_failure_reason`

Rules:

- converted candidates must validate as `PostCandidate` or `DirectPostSource` URL input.
- duplicate keys keep the last valid candidate.

## ExistingPostIndex

In-memory set of already successful post keys.

Fields:

- `keys`: set of `(site_id, board_id, document_srl, document_id_raw)`
- `invalid_record_count`

Rules:

- used only for skip decisions.
- does not create a database table.

## RetrySelectionSummary

Selection and filtering diagnostics before the retry job starts.

Fields:

- `initial_failure_count`
- `invalid_failure_record_count`
- `ineligible_failure_count`
- `selected_count`
- `deduped_failure_count`
- `skipped_existing_count`

Rules:

- counters are included in `RetryReport`.
- invalid and skipped rows are not written as new retry failures unless execution itself fails.

## RetryReport

Existing `RetryReport(JobReport)` model returned by retry service.

Fields:

- inherited `JobReport` fields
- `selected_count`
- `skipped_count`

UOW-009 may minimally extend this model if required for remaining failure counts or selection diagnostics.

Rules:

- `failure_count` keeps the normal meaning: failures from the retry run.
- successful retry outputs remain in the retry run `posts.jsonl`.

## Retry Parser CLI/MCP Boundary

Existing adapter names are reused:

- CLI: `retry-parser-failures`
- MCP: `retry_parser_failures`

Rules:

- adapters build `RetryRequest`.
- adapters delegate selection and execution to `ParserFailureRetryService`.
- adapters do not duplicate retry selection logic.
