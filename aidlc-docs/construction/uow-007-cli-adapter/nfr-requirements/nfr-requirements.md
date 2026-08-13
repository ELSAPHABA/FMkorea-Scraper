# NFR Requirements - UOW-007 CLI Adapter

## Scope

This document defines non-functional requirements for `UOW-007 CLI Adapter`.

In scope:

- terminal command UX
- terminal numbered wizard UX
- CLI argument and wizard-answer mapping
- safe error and debug traceback output
- import side-effect safety
- Proxy credential input and `.env` file update
- User-Agent file import
- cookie file option safety
- runtime dependency lifecycle
- Ctrl+C/manual stop handling
- run id and storage alignment
- adapter tests

Out of scope:

- scraper parsing correctness
- HTTP retry policy internals
- worker queue scheduling
- storage layout internals
- Docker entrypoint
- MCP adapter
- GUI/Web UI
- AWS CDK

## Confirmed Questionnaire Decisions

| Question | Answer | Decision |
|---|---|---|
| Q1 | A | Use only standard library CLI primitives: `argparse`, `getpass`, `shutil`, `traceback`, `signal`, `uuid`, and `input`; add no Click/Typer/Rich dependency. |
| Q2 | A | Print safe summary first; print traceback only with `--debug`; do not dump locals, config, raw exception details, or unsafe values. |
| Q3 | A | Use normal input for proxy host/ID and `getpass.getpass()` for proxy password. |
| Q4 | A | Update only `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, and `FMKOREA_PROXY_PW` in existing `.env`; preserve other lines. |
| Q5 | A | Import User-Agent file only if it is a readable regular UTF-8 text file with at least one non-blank line. |
| Q6 | A | First Ctrl+C requests graceful `JobRunner.stop(StopReason.MANUAL_STOP)`; second Ctrl+C performs best-effort cleanup and exits `1`. |
| Q7 | A | Close `HttpClient` through async context or `try/finally`; rely on UOW-006 stores for write safety. |
| Q8 | A | Generate `run-<uuid4 hex>` by default and inject a deterministic run id factory in tests. |
| Q9 | A | Wizard is a numbered text menu with defaults, retryable invalid input, cancel/back behavior, and injectable streams for tests. |
| Q10 | A | Default tests use no live network and cover command parsing, wizard flow, builders, env validation, exit codes, run id/storage alignment, fake runner, Ctrl+C hook, imports, and config file writes. |
| Q11 | A | PBT targets pure mappings and redaction/path handling, not prompt/signal/live-network behavior. |

No follow-up question is required. The answers are internally consistent.

## Performance Requirements

### NFR-UOW007-PERF-001. Import Safety And Speed

Importing `fmkorea_scraper.adapters.cli` must be side-effect free.

Import must not:

- start a scrape
- read environment variables
- read `.env`
- read `user-agents.txt`
- read cookie files
- create files
- prompt terminal input
- perform network I/O

### NFR-UOW007-PERF-002. No Heavy CLI Dependencies

CLI and wizard implementation must not add Click, Typer, Rich, prompt-toolkit, curses wrappers, or other TUI dependencies.

The implementation must use standard library terminal primitives.

### NFR-UOW007-PERF-003. Bounded Wizard Prompt Loop

Wizard invalid input handling must retry the current prompt.

Prompt loops must have explicit cancel or exit paths such as `q`, back, or empty required input cancellation.

### NFR-UOW007-PERF-004. File Import Cost

`import-user-agents` must read the selected file once for validation and copy it once.

The command must not perform expensive browser/user-agent grammar validation.

## Reliability And Resiliency Requirements

### NFR-UOW007-REL-001. Shared Validation Boundary

Command-line arguments and wizard answers must both build the same `JobConfig`, `ResumeRequest`, and `RetryRequest` model contracts.

UOW-007 must not maintain a separate validation rule set for wizard mode.

### NFR-UOW007-REL-002. Graceful Manual Stop

During a running Job, the first Ctrl+C must request `JobRunner.stop(StopReason.MANUAL_STOP)`.

The CLI must wait for UOW-005 final checkpoint/report behavior on the normal stop path.

### NFR-UOW007-REL-003. Second Interrupt Boundary

If the user sends Ctrl+C again after graceful stop was requested, CLI may stop waiting and return exit code `1`.

Before returning, it must make a best-effort attempt to close the HTTP runtime.

### NFR-UOW007-REL-004. Runtime Cleanup

`HttpClient` must be closed through async context management or `try/finally`.

Cleanup failure must produce only a safe warning and must not print credentials, cookies, raw headers, or raw bodies.

### NFR-UOW007-REL-005. `.env` Preservation

When updating an existing `.env`, CLI must replace only these keys:

- `FMKOREA_PROXY_HOST`
- `FMKOREA_PROXY_ID`
- `FMKOREA_PROXY_PW`

Other lines must be preserved.

### NFR-UOW007-REL-006. User-Agent Import Validation

`import-user-agents` must fail safely when the source path is missing, not a regular file, unreadable, invalid UTF-8, or contains no non-blank lines.

Failure must not modify the existing destination `user-agents.txt`.

### NFR-UOW007-REL-007. Wizard Cancel Behavior

Wizard mode must allow the user to leave a prompt without starting a scrape.

Cancel/exit paths must not create output files, write `.env`, write `user-agents.txt`, or start network I/O unless the selected action explicitly requires it.

### NFR-UOW007-REL-008. Run ID Alignment

CLI must generate one `run_id` for each run/resume attempt and pass the same value to `StorageFactory` and `JobRunner`.

Tests must be able to inject a deterministic run id factory.

## Security Requirements

### NFR-UOW007-SEC-001. Safe Error Summary

On errors, CLI must print a safe summary before optional debug traceback.

The summary must not include:

- proxy password
- raw `.env`
- cookies
- tokens
- raw headers
- raw HTML/body/content

### NFR-UOW007-SEC-002. Debug Traceback Safety

Traceback output is allowed only with `--debug`.

CLI must not dump locals, full config objects, raw exception details, raw HTTP payloads, or environment contents.

Known validation and scraper exceptions must pass through safe mapping before user-facing display.

### NFR-UOW007-SEC-003. Password Input

Proxy password input must use `getpass.getpass()` so it is not echoed to the terminal.

The password must not be printed after saving.

### NFR-UOW007-SEC-004. Plaintext `.env` Warning

Before writing Proxy credentials to `.env`, CLI must warn that credentials are stored in plaintext.

This warning must not include the credential values.

### NFR-UOW007-SEC-005. Proxy Loading Boundary

CLI and UOW-002 runtime must not call `load_dotenv()` or mutate `os.environ` for Proxy loading.

Proxy reading must remain allow-list based on documented `FMKOREA_PROXY_*` keys.

### NFR-UOW007-SEC-006. Cookie File Safety

Cookie file support must remain explicit and disabled by default.

CLI must not print, copy, persist, or checkpoint raw cookie contents.

### NFR-UOW007-SEC-007. Import Command Side Effects

`import-user-agents` and `configure-proxy` must not start scraper network activity.

Their file writes are limited to `user-agents.txt` and `.env` in the execution directory.

## Maintainability Requirements

### NFR-UOW007-MAINT-001. Standard Library CLI

CLI implementation must use Python standard library modules where sufficient:

- `argparse`
- `getpass`
- `shutil`
- `traceback`
- `signal`
- `uuid`
- `pathlib`
- `os`

### NFR-UOW007-MAINT-002. Builder Reuse

`wizard` must convert collected answers into the same internal command shape used by command-line parsing.

It must call the same `build_job_config`, `build_resume_request`, and `build_retry_request` helpers.

### NFR-UOW007-MAINT-003. Adapter Boundary

UOW-007 must remain an adapter.

It must not duplicate:

- search URL traversal
- post parsing
- worker queue scheduling
- JSONL layout
- checkpoint ordering

### NFR-UOW007-MAINT-004. Stream Injection

Wizard input/output streams must be injectable for tests.

Tests must not depend on a real interactive terminal.

## Test Requirements

### NFR-UOW007-TEST-001. Default Test Gate

Default tests must not require:

- live FMKorea access
- real proxy
- real cookie file with secret values
- real CAPTCHA response
- Garage/S3
- PostgreSQL
- interactive terminal

### NFR-UOW007-TEST-002. Required Example Tests

Tests must cover:

- CLI import has no runtime side effects
- `argparse` subcommand parsing
- `build_job_config`
- `build_resume_request`
- `build_retry_request`
- realtime environment validation
- wizard input/output flow
- invalid wizard input retry/cancel behavior
- exit code mapping
- run id and storage alignment
- fake runner invocation
- Ctrl+C graceful stop hook
- User-Agent import
- Proxy `.env` writer preserving unrelated lines
- Proxy password not echoed or printed
- cookie file path validation without raw cookie output

### NFR-UOW007-TEST-003. Property-Based Tests

PBT must cover pure functions only:

- source CLI args to `JobConfig` mapping
- wizard answers to command shape mapping
- realtime exactly-one termination validation
- exit code mapping
- safe error field redaction
- local config file path handling

PBT must not randomize:

- live network behavior
- terminal prompt timing
- OS signal delivery
- real async cancellation scheduling

## Acceptance Criteria

- CLI imports without reading files, prompting, or making network calls.
- `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard` are parseable subcommands.
- Command mode and wizard mode use the same model builders.
- Wizard can start, resume, build parser failure retry input, import User-Agent file, configure Proxy, and exit.
- Invalid wizard input can be corrected without crashing.
- First Ctrl+C requests graceful manual stop.
- Second Ctrl+C exits with code `1` after best-effort cleanup.
- Proxy password is entered without echo and never printed.
- Existing `.env` non-proxy lines are preserved.
- CLI-generated `run_id` is shared by storage and runner.
- Default tests run without live FMKorea access.
