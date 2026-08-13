# Unit Test Instructions - UOW-009 Parser Failure Retry Reprocessor

## Focused UOW-009 Tests

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_parser_failure_retry.py tests\test_parser_failure_retry_properties.py tests\test_cli_adapter.py tests\test_mcp_adapter.py tests\test_container_adapter.py -q --tb=short
```

UOW-009 result:

```text
45 passed in 13.84s
```

Coverage:

- parser-stage failure selection
- malformed JSONL tolerance
- parser reason allowlist and infrastructure failure exclusion
- duplicate last-valid behavior
- existing success skip
- inaccessible input validation before retry Job start
- fake runner direct-post assembly
- CLI retry safe summary
- container retry argv path
- MCP retry safe summary
- import side-effect safety

## Full Default Suite

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests -q --tb=short
```

UOW-009 result:

```text
151 passed, 3 skipped in 23.73s
```

Default tests do not require Docker, Garage, PostgreSQL, MCP runtime, Polars, or live network access.

## Compile Check

```powershell
$env:PYTHONPATH='src'
py -3.12 -m compileall -q src tests
```

UOW-009 result:

```text
PASS
```
