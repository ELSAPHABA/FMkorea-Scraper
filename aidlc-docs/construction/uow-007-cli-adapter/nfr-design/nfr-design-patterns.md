# NFR Design Patterns - UOW-007 CLI Adapter

This document translates UOW-007 NFR requirements into implementation patterns for the FMKorea CLI adapter.

## Confirmed Design Answers

| Question | Answer | Design Pattern |
|---|---|---|
| Q1 | A | Keep first implementation in `src/fmkorea_scraper/adapters/cli.py`; split later only if tests or file size force it. |
| Q2 | A | Normalize both `argparse.Namespace` and wizard answers to a small command dict before model building. |
| Q3 | A | Use a small `WizardSession(input_stream, output_stream)` helper for prompt/read/write only. |
| Q4 | A | Use one `print_error(exc, *, stage, output, debug=False)` function. |
| Q5 | A | Update `.env` through `update_proxy_env(path, values)` using temp file and `os.replace`. |
| Q6 | A | Import User-Agent files through `import_user_agents(source, destination)` with validation and atomic replace. |
| Q7 | A | Connect first interrupt to `JobRunner.stop(StopReason.MANUAL_STOP)` and second interrupt to best-effort exit `1`. |
| Q8 | A | Use a function/context helper for local runtime assembly; do not add a factory class. |
| Q9 | A | Generate one `run_id` and pass it to both `StorageFactory` and `JobRunner`; inject deterministic factory in tests. |
| Q10 | A | Put example tests in `tests/test_cli_adapter.py`, PBT in `tests/test_cli_properties.py`, strategies in `tests/strategies/cli.py`. |
| Q11 | A | Support console script and `python -m fmkorea_scraper.adapters.cli`; do not create root `main.py`. |

No follow-up question is required.

## Module Pattern

First implementation lives in one module:

```text
src/fmkorea_scraper/adapters/
  __init__.py
  cli.py
```

`src/fmkorea_scraper/adapters/__init__.py` remains import-safe and should not expose runtime side effects.

No root `main.py` is created for UOW-007.

## Command Normalization Pattern

Both command mode and wizard mode flow into the same model builders:

```text
argparse.Namespace
  -> command dict
  -> build_job_config(command)
  -> JobConfig

wizard answers
  -> command dict
  -> build_job_config(command)
  -> JobConfig
```

For resume:

```text
argparse.Namespace or wizard answers
  -> command dict
  -> build_resume_request(command)
  -> ResumeRequest
```

For parser failure retry:

```text
argparse.Namespace or wizard answers
  -> command dict
  -> build_retry_request(command)
  -> RetryRequest
```

The command dict is an internal adapter shape. It must not become a public model unless later reuse requires it.

## Wizard Pattern

`WizardSession` owns only terminal interaction:

- read one line from input stream
- write prompts and safe messages to output stream
- show numbered menu
- retry invalid input
- return a command dict or exit intent

It does not:

- validate Pydantic models directly
- create HTTP clients
- call `run_job`
- parse FMKorea pages
- write output files unless delegating to import/config command handlers

Wizard defaults and cancel paths:

- defaults are shown inline when available
- invalid values retry current prompt
- `q` returns to previous menu or exits
- empty required input cancels the current action when no default exists

## Safe Error Pattern

`print_error` writes:

1. safe mapped error summary
2. traceback from `traceback.format_exception(...)` only when `debug=True`

It must not print:

- locals
- full config objects
- raw `.env`
- proxy password
- cookies
- raw headers
- raw HTML/body/content
- tokens

Known validation and scraper errors should use the safe mapped summary before optional debug traceback output.

## `.env` Update Pattern

`update_proxy_env(path, values)`:

1. reads existing file if present
2. preserves unrelated lines
3. replaces or appends only:
   - `FMKOREA_PROXY_HOST`
   - `FMKOREA_PROXY_ID`
   - `FMKOREA_PROXY_PW`
4. writes to temp file in the same directory
5. calls `os.replace`

The helper must not call `load_dotenv()` and must not mutate `os.environ`.

## User-Agent Import Pattern

`import_user_agents(source, destination)`:

1. verifies source is a regular file
2. reads UTF-8 text
3. requires at least one non-blank line
4. writes destination through temp file plus `os.replace`

It does not perform browser grammar validation.

## Ctrl+C Pattern

Running command creates a concrete `JobRunner`.

Interrupt behavior:

- first interrupt calls `runner.stop(StopReason.MANUAL_STOP)`
- user sees a safe stopping message
- CLI waits for final checkpoint/report path
- second interrupt exits with code `1` after best-effort HTTP close

The signal hook must be scoped to the running command and restored afterward when feasible.

## Runtime Assembly Pattern

Use a small helper such as:

```text
build_local_runtime(config, run_id, runtime_options)
```

The helper creates:

- `HttpRuntimeConfig`
- `HttpClient`
- `LinkCollectorService`
- `PostDetailService`
- `StorageFactory` bundle
- `JobRunDependencies`
- `JobRunner`

No factory class is required.

## Run ID Alignment Pattern

Use:

```text
run_id = new_run_id()
bundle = StorageFactory.create(config.storage_config, job_id=config.job_id, run_id=run_id)
runner = JobRunner(dependencies)
await runner.run(config, run_id=run_id)
```

Resume follows the same pattern with a new run id:

```text
run_id = new_run_id()
await runner.resume(request, run_id=run_id)
```

`new_run_id()` returns `run-<uuid4 hex>`. Tests can inject a deterministic `run_id_factory`.

## Entrypoint Pattern

Supported official entrypoints:

- `python -m fmkorea_scraper.adapters.cli ...`
- installed console script, for example `fmkorea-scraper ...`

Both must delegate to the same `main(argv=None) -> int`.

`pyproject.toml` adds the console script.

## Test Pattern

Default tests:

```text
tests/test_cli_adapter.py
tests/test_cli_properties.py
tests/strategies/cli.py
```

Default tests must not use live network.

Test doubles:

- fake runner
- fake input/output streams
- deterministic run id factory
- temporary directories for `.env` and `user-agents.txt`
- monkeypatched runtime helper where needed

PBT targets pure transformations only.

## Compliance Check

| Requirement Area | Design Compliance |
|---|---|
| Security | safe error summary, debug-only traceback, no locals/config dump, getpass password, allow-list `.env` update |
| Resiliency | atomic config file replace, graceful first Ctrl+C, best-effort second Ctrl+C cleanup |
| Maintainability | one module first, shared builders, no new CLI dependency |
| PBT | pure command/wizard/env/path mappings only |
| Import safety | parser and helpers load without file, prompt, env, or network side effects |
