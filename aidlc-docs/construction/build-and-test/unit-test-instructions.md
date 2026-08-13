# Unit Test Instructions - UOW-008 Container, MCP, And Test Harness

## Focused UOW-008 Tests

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_container_adapter.py tests\test_mcp_adapter.py tests\test_s3_output_and_postgres.py tests\test_quality_harness.py tests\test_outputs_storage.py -q --tb=short
```

UOW-008 result:

```text
25 passed, 1 skipped in 7.84s
```

Coverage:

- container env mapping and exit code behavior
- container runtime assembly with fake S3/PostgreSQL/HTTP
- MCP JSON-safe success/error handler boundary
- S3-compatible output and media upload behavior with fake client
- PostgreSQL checkpoint save/load/latest with fake connection
- JSONL/report/failure quality fixture shape

## Full Default Suite

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests -q --tb=short
```

UOW-008 result:

```text
142 passed, 3 skipped in 28.20s
```

Default tests must not require Docker, Garage, PostgreSQL, MCP runtime, Polars, or live network access.

## Compile Check

```powershell
$env:PYTHONPATH='src'
py -3.12 -m compileall -q src tests
```

UOW-008 result:

```text
PASS
```
