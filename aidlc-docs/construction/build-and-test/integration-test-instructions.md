# Integration Test Instructions - UOW-007 CLI Adapter

## Purpose

Validate UOW-007 integration with the existing local package boundaries:

- UOW-001 Pydantic models
- UOW-002 HTTP runtime config objects
- UOW-003 link collector service wiring
- UOW-004 post detail parser service wiring
- UOW-005 runner API
- UOW-006 storage factory

## Default Integration Tests

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_cli_adapter.py -q --tb=short
```

Key scenarios:

- `core.api.run_job(..., run_id=...)` forwards `run_id` to runners that support it
- `build_local_runtime()` creates the existing collector/parser/storage/runner dependency graph
- `StorageFactory.create()` receives the CLI-generated `run_id`
- `python -m fmkorea_scraper.adapters.cli --help` works without installing the package
- fake runner execution does not hit live FMKorea

## External Integration Tests

External live tests are not part of the default UOW-007 gate.

Not required:

- live FMKorea access
- real Proxy
- real cookie file
- Garage/S3
- PostgreSQL
- Docker
- MCP server

These remain later-unit or optional smoke-test concerns.

## Cleanup

Default integration tests use `tmp_path` and fake dependencies. No manual cleanup is required.
