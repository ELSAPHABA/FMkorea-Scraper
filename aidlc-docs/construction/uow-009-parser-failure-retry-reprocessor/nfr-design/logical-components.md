# Logical Components - UOW-009 Parser Failure Retry Reprocessor

This document defines logical components for the UOW-009 implementation.

## Component Overview

| Component | Responsibility |
|---|---|
| `ParserFailureRetryService` | orchestrates failure input selection and direct-post retry execution |
| `FailureInputReader` | protocol for line-streaming failure and success JSONL inputs |
| `LocalFailureInputReader` | streams local path and `file://` JSONL refs |
| `S3FailureInputReader` | streams explicit S3/Garage object refs through existing S3-compatible boundary |
| `ParserFailureSelector` | pure selector for eligible parser-stage post failures |
| `ExistingSuccessIndex` | key-only set of already stored posts |
| `RetryOptionRequestBuilder` | adapter-side restore/override logic for report/checkpoint inputs |
| `RetryJobAssembler` | builds `DirectPostSource` and `JobConfig` from selected candidates |
| `RetrySafeSummary` | CLI/MCP-safe result payload |
| `ParserFailureRetryTests` | default example and property tests |
| `OptionalRetrySmokeTests` | env-gated S3/MCP/live smoke tests |

## ParserFailureRetryService

Location:

- `src/fmkorea_scraper/retry/parser_failures.py`

Responsibilities:

- accept finalized retry request and runtime dependencies
- validate declared failure and existing success inputs are accessible
- stream failure JSONL through `FailureInputReader`
- call `ParserFailureSelector`
- build existing success index when configured
- assemble a direct-post retry Job
- call existing `JobRunner`
- return `RetryReport` with selection counters

Must not:

- parse post HTML
- implement a second HTTP client
- implement a second worker queue
- mutate source failure input
- read report/checkpoint restore refs directly
- perform I/O at import time

## FailureInputReader

Shape:

```text
iter_lines(input_ref) -> Iterable[str]
validate_accessible(input_ref) -> None
```

Responsibilities:

- expose line streams
- fail inaccessible inputs before retry Job start
- hide local/S3 read details from selector logic

Errors:

- inaccessible local path or S3 object -> validation failure
- malformed JSON line -> handled by selector as invalid line counter

## LocalFailureInputReader

Responsibilities:

- accept local paths
- accept `file://` refs after path validation
- open as UTF-8 text
- stream lines without loading full file

Must not:

- delete, compact, or rewrite source files
- prompt for paths

## S3FailureInputReader

Responsibilities:

- accept explicit S3/Garage object refs
- use existing S3-compatible storage config and optional dependency boundary
- return text line iterator
- keep credentials out of user-visible refs and errors

Must not:

- add a new S3 SDK
- require Garage-specific APIs
- auto-discover prefixes in UOW-009

## ParserFailureSelector

Function:

```text
select_parser_failure_candidates(lines, existing_success_keys)
```

Inputs:

- failure JSONL line iterator
- optional existing success key set

Outputs:

- deduped `RetryCandidate` list
- `RetrySelectionSummary`

Responsibilities:

- parse JSON safely
- validate failure records through existing models where possible
- include only `stage="post"` parser/metadata/content failures
- skip CAPTCHA, block, network, storage, checkpoint, media, and manual stop failures
- require usable direct post URL
- dedupe by `(site_id, board_id, document_srl, document_id_raw)`
- keep last valid duplicate
- skip existing successes

## ExistingSuccessIndex

Shape:

```text
keys: set[(site_id, board_id, document_srl, document_id_raw)]
invalid_record_count: int
```

Responsibilities:

- stream `posts.jsonl`
- extract post identity keys
- count invalid success records
- provide constant-time membership checks

It is not a database table and does not store full posts.

## RetryOptionRequestBuilder

Location:

- existing CLI/API builder path
- existing MCP tool handler path

Responsibilities:

- parse explicit retry options
- optionally read `from-report`
- optionally read `from-checkpoint`
- reject both restore sources together
- restore only allowlisted options
- apply explicit option precedence
- produce finalized service input

Must not restore:

- cookies
- proxy passwords
- raw headers
- raw HTML
- raw env values
- hidden internal state

## RetryJobAssembler

Responsibilities:

- convert selected candidates to direct post URL list
- build `DirectPostSource`
- build `JobConfig(job_type="direct_post")`
- preserve finalized scrape, worker, and storage options
- inject fake runner in tests

It delegates execution to existing `JobRunner`.

## RetrySafeSummary

Shape:

```text
{
  "selected": int,
  "skipped": int,
  "stored": int,
  "remaining_failure": int,
  "report": StoredObjectRef | str | None
}
```

Responsibilities:

- provide CLI/MCP-safe output
- hide raw lines and stack traces
- include enough counts for operators to decide whether a second retry is needed

## ParserFailureRetryTests

Default tests cover:

- import side-effect safety
- inaccessible input validation
- streaming failure selection
- malformed line tolerance
- parser reason allowlist
- duplicate last-wins behavior
- existing success skip
- option precedence
- fake runner direct-post Job assembly
- safe summary payload

PBT covers only pure selector behavior.

## OptionalRetrySmokeTests

Markers/env gates:

- S3/Garage input read
- MCP runtime
- live post retry

Rules:

- skip cleanly by default
- never require external services for default tests
- never print credentials or raw failure input

## Boundary Summary

UOW-009 owns parser-failure retry selection and direct-post retry assembly.

It delegates:

- model validation to UOW-001
- HTTP and rate policy to UOW-002
- direct post source behavior to UOW-003/UOW-007
- post parsing to UOW-004
- workers, checkpoint, and stop behavior to UOW-005
- output and failure storage to UOW-006/UOW-008
- container/MCP safe runtime boundaries to UOW-008
