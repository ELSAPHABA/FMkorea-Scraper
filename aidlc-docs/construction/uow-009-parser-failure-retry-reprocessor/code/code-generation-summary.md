# Code Generation Summary - UOW-009 Parser Failure Retry Reprocessor

- **Generated At**: 2026-08-13T12:40:53Z
- **Validation**: focused UOW-009 tests, full default tests, compile check, and import check passed

## Created Files

| Area | Files |
|---|---|
| retry package | `src/fmkorea_scraper/retry/__init__.py`, `src/fmkorea_scraper/retry/parser_failures.py` |
| tests | `tests/test_parser_failure_retry.py`, `tests/test_parser_failure_retry_properties.py` |
| code docs | `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/public-contracts.md`, `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/code/code-generation-summary.md` |

## Modified Files

| File | Change |
|---|---|
| `src/fmkorea_scraper/models/job.py` | extended `RetryRequest` with existing success, restore ref, and retry job id fields |
| `src/fmkorea_scraper/core/api.py` | connected `retry_parser_failures` to default `ParserFailureRetryService` path |
| `src/fmkorea_scraper/adapters/cli.py` | replaced UOW-009 placeholder with real retry execution and safe summary output |
| `src/fmkorea_scraper/adapters/container.py` | allowed existing container argv path to run `retry-parser-failures` |
| `src/fmkorea_scraper/adapters/mcp.py` | returned safe summary for `retry_parser_failures` |
| `src/fmkorea_scraper/__init__.py` | exported `ParserFailureRetryService` |
| `tests/test_cli_adapter.py` | removed unsupported-placeholder assertion |
| `tests/test_container_adapter.py` | added retry command container-path test |
| `tests/test_mcp_adapter.py` | updated retry MCP assertion to safe summary shape |

## Implemented Contracts

- parser-stage post failure selection from JSONL
- malformed failure line tolerance
- parser reason allowlist and infrastructure failure exclusions
- last-valid duplicate behavior
- optional existing success skip
- direct-post retry `JobConfig` assembly
- `RetryReport.metadata["parser_failure_retry"]` diagnostics
- CLI `retry-parser-failures` execution
- container retry command execution through existing entrypoint
- MCP `retry_parser_failures` safe summary
- import side-effect safety tests

## Validation Results

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\test_parser_failure_retry.py tests\test_parser_failure_retry_properties.py tests\test_cli_adapter.py tests\test_mcp_adapter.py tests\test_container_adapter.py -q --tb=short
```

Result:

```text
45 passed
```

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src tests
```

Result:

```text
passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short
```

Result:

```text
151 passed, 3 skipped
```

```powershell
$env:PYTHONPATH='src'; python -c "import fmkorea_scraper, fmkorea_scraper.retry, fmkorea_scraper.adapters.cli, fmkorea_scraper.adapters.container, fmkorea_scraper.adapters.mcp; print('ok')"
```

Result:

```text
ok
```

## Deferred Boundaries

- `from_report_path` and `from_checkpoint_path` are validated request fields, but automatic option restoration is still limited by available stored report/checkpoint contracts.
- Queue/DLQ, scheduler, S3 prefix discovery, and platform retry workers remain future platform work.
- S3/Garage, MCP runtime, and live retry smoke tests remain opt-in.
