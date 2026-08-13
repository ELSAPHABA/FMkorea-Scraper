# Integration Test Instructions - UOW-009 Parser Failure Retry Reprocessor

## Default Integration Boundary

UOW-009 integration checks stay local and fake-backed by default.

Covered by default tests:

- CLI `retry-parser-failures` to `ParserFailureRetryService`
- service to injected direct-post `JobRunner`
- container argv acceptance for `retry-parser-failures`
- MCP `retry_parser_failures` safe summary response
- `RetryRequest` model validation
- S3/Garage env validation boundary without live storage

## Commands

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_parser_failure_retry.py tests\test_cli_adapter.py tests\test_container_adapter.py tests\test_mcp_adapter.py -q --tb=short
```

The full default suite was also run:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests -q --tb=short
```

Result:

```text
151 passed, 3 skipped in 23.73s
```

## Optional External Smoke

These remain opt-in:

- Garage/S3 input object read
- PostgreSQL checkpoint integration
- MCP runtime process
- live FMKorea retry

Use project markers/env gates for those checks. They are not required for the default Build and Test gate.
