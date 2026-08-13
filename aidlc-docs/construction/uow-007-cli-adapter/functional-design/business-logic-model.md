# Business Logic Model - UOW-007 CLI Adapter

## Purpose

UOW-007 provides the local terminal adapter for running the FMKorea scraper.

This unit owns command parsing, the terminal wizard, CLI-to-model mapping, local dependency assembly, User-Agent import, Proxy `.env` setup, cookie file option flow, terminal messages, exit codes, resume command handling, and parser-failure retry command shell. It does not own FMKorea HTML parsing, source traversal internals, worker queue internals, storage layout rules, container entrypoint, PostgreSQL checkpoint storage, MCP tools, GUI/Web UI, or AWS CDK.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Entrypoint | `fmkorea_scraper.adapters.cli.main(argv: list[str] | None = None) -> int` |
| Console script | `pyproject.toml` console script `fmkorea-scraper` calls `main` |
| Import safety | importing the CLI module must not run a Job, create files, read environment variables, prompt, or perform network I/O |
| Command shape | stdlib `argparse` with `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard` subcommands |
| Run sources | `run --source direct-post|board-list|board-search|integrated-search|deep-search|no-keyword-range` |
| Realtime source | read `FMKOREA_REALTIME_*` environment variables and build realtime source models |
| Model mapping | pure `build_job_config`, `build_resume_request`, and `build_retry_request` helpers |
| Source mapping | CLI source options map directly to existing UOW-001 source models |
| Run id | CLI creates one `run_id` and passes it to both `StorageFactory` and `JobRunner`; runner keeps optional internal run id generation for compatibility |
| Runtime assembly | CLI creates existing HTTP, collector, parser/detail, storage, and runner objects, then calls `core.api.run_job()` or `core.api.resume_job()` |
| Output base | `--output-path` maps to `StorageConfig.base_output_path`; omitted value uses current working directory through UOW-006 |
| User-Agent | `--user-agent-file` and `--user-agent-rotate-every` configure current run; `import-user-agents` copies to `user-agents.txt` |
| Proxy | explicit CLI proxy values win, then `.env`, then disabled; `configure-proxy` writes plaintext `FMKOREA_PROXY_*` values after warning |
| Cookie | `--cookie-file` applies only to the current runtime and is never logged, persisted to output, or stored in checkpoints |
| Scrape options | comment mode, media mode, attachment flag, request interval, retry count, worker count, queue size, and timeout map to existing models |
| Terminal output | print safe start summary, final report summary, and resume command; raw traceback is printed only with `--debug` |
| Exit codes | success `0`, validation/usage error `2`, stopped/CAPTCHA/block/runtime error `1` |
| Wizard | interactive numbered wizard is included and must reuse the same builders and command handlers as command mode |

## Command Flow

1. `main(argv)` builds an `argparse.ArgumentParser`.
2. Parser selects one subcommand.
3. CLI resolves the execution directory from the process working directory.
4. CLI builds command-specific models or performs command-specific file operations.
5. CLI prints safe human-readable status.
6. CLI returns a process exit code.

`main()` returns an integer. The console script may call `raise SystemExit(main())`.

## `run` Flow

1. Parse `run` options.
2. If `FMKOREA_REALTIME_ENABLED=true`, build a realtime source from environment variables.
3. If realtime is not enabled, build the selected source from `--source`.
4. Build `ScrapeOptions`, `WorkerConfig`, `RuntimeConfig`, and `StorageConfig`.
5. Validate the resulting `JobConfig` through Pydantic model construction.
6. Generate one `run_id`.
7. Build `HttpRuntimeConfig` from request interval, timeout, User-Agent, Proxy, cookie file handling boundary, and execution directory.
8. Open one `HttpClient` lifecycle for the Job run.
9. Create:
   - `LinkCollectorService`
   - `PostDetailService`
   - UOW-006 `StorageFactory` bundle with `job_id` and `run_id`
   - `JobRunDependencies`
   - `JobRunner`
10. Call `core.api.run_job(config, runner=runner)`.
11. Print final `JobReport` or `JobRunResult` summary and resume command.
12. Return the mapped exit code.

The CLI must not implement board pagination, integrated search parsing, post parsing, media parsing, worker scheduling, checkpoint ordering, or JSONL path rules itself.

## Run ID And Storage Flow

UOW-006 storage objects require `run_id` before the runner starts. UOW-005 currently creates `run_id` internally.

UOW-007 resolves this by adding backward-compatible optional `run_id` parameters to runner entrypoints:

```python
await runner.run(config, run_id=run_id)
await runner.resume(request, run_id=run_id)
```

If `run_id` is omitted, `JobRunner` keeps its current internal run id generation. CLI always passes an explicit `run_id` so storage layout and runner result/report use the same value.

## `resume` Flow

1. Parse optional `job_id`.
2. Build `ResumeRequest(job_id=...)`.
3. Generate a new `run_id`.
4. Build the same local dependencies as `run`, using the restored job config after checkpoint lookup where needed.
5. Call `core.api.resume_job(request, runner=runner)`.
6. If `job_id` is omitted, the checkpoint store may load the latest checkpoint through the UOW-006 checkpoint contract.
7. Print final summary and resume command.
8. Return the mapped exit code.

Resume reuses the same `job_id` but creates a new `run_id`; it must not append to an older JSONL output file.

## `retry-parser-failures` Flow

1. Parse failure input path, optional `job_id`, and `skip_existing_success`.
2. Build `RetryRequest`.
3. In UOW-007, provide the command shape and validation boundary.
4. If the UOW-009 retry service is not yet available, fail with a safe unsupported message.
5. Once UOW-009 exists, call `core.api.retry_parser_failures(request, retry_service=...)`.

UOW-007 does not implement parser-failure selection or direct-post retry batch execution itself.

## `import-user-agents` Flow

1. Read the source file path from CLI arguments.
2. Validate that the file exists and is readable.
3. Copy it to `<execution_dir>/user-agents.txt`.
4. Preserve plaintext UTF-8 content so users can edit it.
5. Do not validate every User-Agent string in this command; runtime loading already ignores blank lines and falls back safely.

## `configure-proxy` Flow

1. Print a plaintext credential storage warning.
2. Prompt for host, ID, and password or accept explicit command options if provided by the final CLI design.
3. Write `<execution_dir>/.env` with only:
   - `FMKOREA_PROXY_HOST`
   - `FMKOREA_PROXY_ID`
   - `FMKOREA_PROXY_PW`
4. Keep the file editable plaintext by requirement.
5. Do not print the password or raw `.env` content.

## Realtime Environment Flow

Realtime execution is enabled only when `FMKOREA_REALTIME_ENABLED=true`.

Supported variables:

- `FMKOREA_REALTIME_MODE=keyword|all`
- `FMKOREA_REALTIME_KEYWORD`
- `FMKOREA_REALTIME_DURATION_SECONDS`
- `FMKOREA_REALTIME_END_AT`
- `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS`

Rules:

- `keyword` mode requires a keyword.
- `all` mode requires a board ID.
- `keyword` mode can run as board-scoped or integrated-scoped depending on CLI scope options.
- exactly one of duration seconds or end-at is required.
- both missing or both present is a validation error.
- realtime environment and non-realtime `--source` must not silently combine.

## `wizard` Flow

1. Parse the `wizard` subcommand.
2. Print a numbered menu for:
   - scraping start
   - resume
   - parser failure retry
   - import User-Agent file
   - configure Proxy
   - exit
3. For scraping start, ask the same required source/options that `run` accepts.
4. Convert wizard answers into the same internal command shape used by `build_job_config`.
5. For resume, convert wizard answers into the same internal command shape used by `build_resume_request`.
6. For parser failure retry, convert answers into the same internal command shape used by `build_retry_request`.
7. For User-Agent import and Proxy configure, call the same command handlers as command mode.
8. Run through the same runtime assembly and terminal reporting path as command mode.

The wizard is an input convenience layer only.

## Terminal Output Flow

Start output includes:

- `job_id`
- `run_id`
- output base path
- source summary
- worker count
- request interval
- comment and media mode

Completion output includes:

- status
- stored count
- failure count
- skipped count
- output references when available
- resume command when the Job can be resumed

For errors, CLI prints a safe summary. Raw traceback is printed only when `--debug` is set, and secret/raw response redaction boundaries still apply.

## Testable Properties

- CLI import has no side effects.
- Parser accepts all confirmed subcommands.
- `build_job_config` creates the matching `JobConfig.source` variant.
- realtime environment validation preserves the exactly-one termination rule.
- `build_resume_request` accepts explicit and omitted `job_id`.
- `build_retry_request` validates parser-failure retry input shape.
- CLI-generated `run_id` is shared by storage assembly and runner invocation.
- `--output-path` maps only to `StorageConfig.base_output_path`.
- User-Agent import writes `user-agents.txt`.
- Proxy configuration writes only documented `.env` keys.
- Wizard answers map to the same model builders as command arguments.
- CLI uses fake runner/dependencies in tests without live network.
- exit codes match success, validation error, and runtime/stopped failure classes.
