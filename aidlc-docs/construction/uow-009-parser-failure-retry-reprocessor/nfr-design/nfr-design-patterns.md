# NFR Design Patterns - UOW-009 Parser Failure Retry Reprocessor

This document translates UOW-009 NFR requirements into implementation patterns.

## Confirmed Design Answers

| Question | Answer | Design Pattern |
|---|---|---|
| Q1 | A | Keep retry logic in one small retry module; keep CLI/MCP adapters thin. |
| Q2 | A | Use a `FailureInputReader` protocol with local and S3-compatible implementations. |
| Q3 | A | Keep retry selection as I/O-free streaming selector logic. |
| Q4 | A | Build existing-success skip index from streaming key extraction only. |
| Q5 | A | Restore report/checkpoint options in request builder/adapters, not inside service selection. |
| Q6 | A | Reuse `RetryReport` counters and add small optional metadata only if needed. |
| Q7 | A | Convert selected URLs to `DirectPostSource` and run through existing `JobRunner`. |
| Q8 | A | Return safe summary counts and output refs from CLI/MCP. |
| Q9 | A | Apply PBT to pure selector behavior only. |
| Q10 | A | Keep local fixture retry smoke in default tests; gate S3/MCP/live smoke tests. |

No follow-up question is required.

## Module Layout Pattern

First implementation uses one focused runtime module:

```text
src/fmkorea_scraper/retry/
  parser_failures.py

tests/
  test_parser_failure_retry.py
  test_parser_failure_retry_properties.py
```

`parser_failures.py` contains:

- `ParserFailureRetryService`
- `FailureInputReader` protocol
- `LocalFailureInputReader`
- `S3FailureInputReader`
- selector helpers
- existing-success index helpers
- safe summary helper

CLI and MCP files only connect existing command/tool names to the service:

- CLI: `retry-parser-failures`
- MCP: `retry_parser_failures`

Do not create a nested retry package until repeated code or file size requires it.

## Failure Input Reader Pattern

Use a small protocol:

```text
FailureInputReader.iter_lines(input_ref) -> Iterable[str]
```

Implementations:

- `LocalFailureInputReader` for local paths and `file://` refs
- `S3FailureInputReader` for explicit S3/Garage object refs

Rules:

- service consumes line iterators
- all declared inputs are checked before retry Job start
- input files/objects are read-only
- importing retry modules performs no file, env, S3, or HTTP I/O
- S3 support reuses the existing optional `s3` dependency boundary

## Streaming Selector Pattern

Selection uses a pure helper or small class:

```text
select_parser_failure_candidates(lines, existing_success_keys=None)
  -> (list[RetryCandidate], RetrySelectionSummary)
```

Behavior:

1. stream failure JSONL one line at a time
2. ignore empty lines
3. count malformed JSON or invalid records
4. include only parser-stage post failures by allowlist
5. require a usable direct post URL
6. dedupe by `(site_id, board_id, document_srl, document_id_raw)`
7. keep last valid duplicate candidate
8. skip candidates already present in existing success keys

The selector must not store raw invalid lines or full ineligible records.

## Existing Success Index Pattern

Existing `posts.jsonl` inputs are read as streams.

Only this set is retained:

```text
set[(site_id, board_id, document_srl, document_id_raw)]
```

Invalid success lines increment diagnostics and are not added to the index.

No full post body list, database staging table, or Polars processing is needed in UOW-009.

## Option Restoration Pattern

`--from-report` and `--from-checkpoint` are adapter/request-builder conveniences.

Pattern:

1. CLI/MCP/API builder reads the restore source.
2. builder restores allowlisted scrape, worker, and storage settings.
3. explicit retry options override restored values.
4. builder rejects combined `from-report` and `from-checkpoint`.
5. service receives finalized `RetryRequest`, `ScrapeOptions`, `WorkerConfig`, and `StorageConfig`.

The service does not read report or checkpoint refs.

## Retry Report Pattern

Use existing `RetryReport` and `JobReport` semantics.

Required top-level counters:

- `selected_count`
- `skipped_count`
- inherited `stored_count`
- inherited `failure_count`

Additional selector diagnostics may be stored as:

```text
metadata["parser_failure_retry"]
```

Suggested metadata keys:

- `initial_failure_count`
- `invalid_failure_record_count`
- `ineligible_failure_count`
- `deduped_failure_count`
- `skipped_existing_count`
- `invalid_existing_success_count`

Do not create a parallel report schema unless later consumers require it.

## DirectPost Job Assembly Pattern

Selected candidates become a direct-post retry Job:

```text
RetryCandidate list
-> URL list
-> DirectPostSource
-> JobConfig(job_type="direct_post")
-> existing JobRunner
```

The retry unit reuses existing behavior for:

- request interval
- worker count
- User-Agent rotation
- proxy policy
- media download
- checkpointing
- CAPTCHA/block stop handling
- output storage

Tests may inject a fake runner to verify assembly without live scraping.

## Adapter Summary Pattern

CLI and MCP return only safe operational summary fields:

- `selected`
- `skipped`
- `stored`
- `remaining_failure`
- `report`

Forbidden in terminal/MCP output:

- raw failure line
- raw HTML
- raw headers
- cookies
- proxy credentials
- S3 credentials
- stack trace

## Property-Based Test Pattern

Apply PBT to selector logic only.

Required properties:

- dedupe is idempotent
- duplicate keys keep the last valid URL
- ineligible reasons are never selected
- existing success skip never increases selected count
- explicit options override restored options

Do not include S3 readers, MCP runtime, or live runner behavior in PBT.

## Optional Smoke Pattern

Default tests include local fixture retry smoke.

Optional smoke tests are marker/env gated:

- S3/Garage input read
- MCP runtime
- live post retry

Default `pytest` must pass without Garage, S3 network, live site access, Docker, PostgreSQL, or MCP server runtime.

## Compliance Check

| Requirement Area | Design Compliance |
|---|---|
| Performance | streaming input reads, key-only success index, no full raw file load |
| Reliability | input validation before Job start, source inputs read-only, existing JobRunner stop/checkpoint reuse |
| Security | safe summaries, no raw line/secret output, S3 refs without credentials |
| Maintainability | one focused retry module, thin adapters, existing JobRunner/output reuse |
| PBT | pure selector properties only, external integrations left to optional smoke |
| Import safety | no file/S3/env/HTTP side effects during module import |
