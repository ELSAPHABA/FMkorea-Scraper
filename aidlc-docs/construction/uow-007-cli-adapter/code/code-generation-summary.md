# Code Generation Summary - UOW-007 CLI Adapter

- **Generated At**: 2026-08-13T01:20:08Z
- **Validation**: focused CLI tests, full default tests, and compile check passed

## Created Files

| Area | Files |
|---|---|
| adapter package | `src/fmkorea_scraper/adapters/__init__.py`, `src/fmkorea_scraper/adapters/cli.py` |
| example tests | `tests/test_cli_adapter.py` |
| property tests | `tests/test_cli_properties.py`, `tests/strategies/cli.py` |
| code docs | `aidlc-docs/construction/uow-007-cli-adapter/code/public-contracts.md`, `aidlc-docs/construction/uow-007-cli-adapter/code/code-generation-summary.md` |

## Modified Files

| File | Change |
|---|---|
| `pyproject.toml` | added `fmkorea-scraper` console script |
| `.gitignore` | ignored local scraper runtime files: `outputs/`, `Checkpoint.json`, `user-agents.txt` |
| `src/fmkorea_scraper/core/api.py` | added optional `run_id` passthrough to injected runners |
| `src/fmkorea_scraper/runner/service.py` | added backward-compatible optional `run_id` for run/resume |

## Implemented Contracts

- `main(argv=None) -> int`
- `build_parser()`
- `normalize_command()`
- `build_job_config()`
- `build_resume_request()`
- `build_retry_request()`
- `run_scrape_command_async()`
- `resume_scrape_command_async()`
- `retry_parser_failures_command_async()`
- `import_user_agents()`
- `update_proxy_env()`
- `WizardSession`
- `InterruptController`
- `print_error()`

## Validation Results

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\test_cli_adapter.py tests\test_cli_properties.py -q --tb=short
```

Result:

```text
21 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short
```

Result:

```text
118 passed, 2 skipped
```

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src tests
```

Result:

```text
passed
```

## Deferred Boundaries

- `retry-parser-failures` validates command input but returns an unsupported message until UOW-009 implements execution.
- Docker entrypoint, PostgreSQL checkpointing, MCP tools, and AWS CDK remain deferred to later units.
- User-provided cookie input is not accepted; server-set temporary cookies remain inside the HTTP runtime memory lifecycle.
