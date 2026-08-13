# Security Test Instructions - UOW-009 Parser Failure Retry Reprocessor

## Security Checks

UOW-009 security checks focus on safe retry diagnostics.

Validated by default tests:

- raw malformed failure lines are not included in reports
- CLI retry output is a numeric safe summary
- MCP retry output is a numeric safe summary
- S3 refs do not include credentials
- container missing-env validation returns safe JSON
- retry imports have no filesystem/env/network side effects
- existing failure inputs and success inputs are read-only

## Commands

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_parser_failure_retry.py tests\test_cli_adapter.py tests\test_mcp_adapter.py tests\test_container_adapter.py -q --tb=short
```

Result:

```text
PASS
```

## Docker Secret Boundary

Docker image build still uses runtime env injection only.

Checks:

```powershell
docker run --rm fmkorea-scraper:uow-009-build-test retry-parser-failures --failure-path s3://bucket/failures.jsonl
```

Expected without env:

- safe validation JSON
- exit code `2`
- no credential output
