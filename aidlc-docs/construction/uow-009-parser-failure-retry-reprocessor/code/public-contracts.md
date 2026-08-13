# Public Contracts - UOW-009 Parser Failure Retry Reprocessor

## Library API

```python
from fmkorea_scraper.retry import ParserFailureRetryService, select_parser_failure_retries
```

Contract:

- importing `fmkorea_scraper.retry` performs no file, S3, env, HTTP, or output I/O
- `ParserFailureRetryService.run(request)` accepts `RetryRequest`
- `ParserFailureRetryService.retry(request, execute_job=...)` accepts an injected async direct-post Job executor
- selected posts are retried by building a normal `DirectPostSource` and `JobConfig`
- source `failures.jsonl` and existing `posts.jsonl` refs are read-only

## Retry Request

```python
from fmkorea_scraper.models.job import RetryRequest
```

Fields:

- `failure_input.failure_path`
- `failure_input.job_id`
- `failure_input.stage_allowlist`
- `skip_existing_success`
- `existing_success_path`
- `from_report_path`
- `from_checkpoint_path`
- `retry_job_id`

Contract:

- `from_report_path` and `from_checkpoint_path` cannot be combined
- `existing_success_path` is optional
- `retry_job_id` controls the new retry run job id when supplied
- runtime HTTP values such as proxy and User-Agent are still adapter/runtime inputs, not persisted in `RetryRequest`

## Failure Input Readers

```python
from fmkorea_scraper.retry import LocalFailureInputReader, S3FailureInputReader, CompositeFailureInputReader
```

Supported refs:

- local path
- `file://` URI
- `s3://bucket/key`
- configured-bucket object key when a default bucket is supplied by container/S3 reader setup

Contract:

- local reader streams UTF-8 lines
- S3 reader uses the existing S3-compatible/boto3 boundary
- inaccessible inputs fail before the retry Job executor is called
- malformed JSONL lines are counted and skipped
- raw invalid lines are not stored in reports or adapter summaries

## Selection Contract

```python
select_parser_failure_retries(
    {"failures.jsonl": lines},
    job_id="job-1",
    stage_allowlist=["post"],
    existing_keys=...
)
```

Eligible failure records:

- `stage == "post"`
- reason contains parser, metadata, content, identity, title, author, or comment parse fragments
- URL is present and normalizes as an FMKorea direct post URL

Excluded failure records:

- CAPTCHA
- block
- network
- storage
- checkpoint
- media
- output
- manual/cancel

Deduplication key:

```text
(site_id, board_id, document_srl, document_id_raw)
```

Duplicate keys keep the last valid failure record.

## Retry Report

```python
from fmkorea_scraper.models.report import RetryReport
```

Top-level fields:

- `selected_count`
- `skipped_count`
- inherited `stored_count`
- inherited `failure_count`
- inherited `output_refs`

Diagnostics:

```text
metadata["parser_failure_retry"]
```

Keys:

- `retry_source_failure_refs`
- `initial_failure_count`
- `invalid_failure_record_count`
- `ineligible_failure_count`
- `selected_count`
- `deduped_failure_count`
- `skipped_existing_count`
- `existing_success_invalid_record_count`
- `remaining_failure_count`

## CLI Contract

```powershell
python -m fmkorea_scraper.adapters.cli retry-parser-failures `
  --failure-path .\outputs\job\run\failures.jsonl `
  --existing-success-path .\outputs\job\run\posts.jsonl `
  --job-id job-1 `
  --retry-job-id retry-1
```

Supported options:

- `--failure-path`
- `--existing-success-path`
- `--from-report`
- `--from-checkpoint`
- `--retry-job-id`
- `--job-id`
- `--stage`
- `--skip-existing-success`
- `--no-skip-existing-success`
- normal runtime options such as output path, parser guardrails, workers, User-Agent, proxy, timeout

Safe summary output:

```text
retry selected=<n> skipped=<n> stored=<n> remaining_failure=<n>
```

Exit codes:

- `0`: completed retry report
- `1`: stopped/runtime failure
- `2`: validation failure

## Container Contract

The existing worker container accepts the same retry command:

```powershell
docker run --rm --env-file .env fmkorea-scraper-worker `
  retry-parser-failures `
  --failure-path s3://bucket/path/failures.jsonl
```

Contract:

- no new Dockerfile or entrypoint is required
- existing `docker-entrypoint.sh` delegates argv to the container adapter
- S3/Garage and PostgreSQL env contract is reused
- output/checkpoint behavior follows the existing `JobRunner`

## MCP Contract

Tool:

```text
retry_parser_failures
```

Payload shape follows `RetryRequest`.

Response data is safe summary only:

```json
{
  "selected": 1,
  "skipped": 0,
  "stored": 1,
  "remaining_failure": 0,
  "report": "outputs/job/run/report.json"
}
```

MCP response must not include raw failure lines, raw HTML, headers, cookies, credentials, or stack traces.

## Boundaries

UOW-009 does not add queue/DLQ infrastructure, a scheduler, PostgreSQL staging tables, S3 prefix discovery, parser selector changes, CAPTCHA bypass, or production cloud provisioning.
