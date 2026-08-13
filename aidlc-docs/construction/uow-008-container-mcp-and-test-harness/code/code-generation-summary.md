# Code Generation Summary - UOW-008 Container, MCP, And Test Harness

- **Generated At**: 2026-08-13T07:58:49Z
- **Validation**: focused UOW-008 tests, full default tests, compile check, and adapter import check passed

## Created Files

| Area | Files |
|---|---|
| Docker root | `Dockerfile`, `.dockerignore`, `.gitattributes`, `docker-entrypoint.sh` |
| adapters | `src/fmkorea_scraper/adapters/container.py`, `src/fmkorea_scraper/adapters/mcp.py`, `src/fmkorea_scraper/adapters/safe_errors.py` |
| output adapters | `src/fmkorea_scraper/outputs/postgres_checkpoint.py`, `src/fmkorea_scraper/outputs/s3_output.py` |
| tests | `tests/test_container_adapter.py`, `tests/test_mcp_adapter.py`, `tests/test_s3_output_and_postgres.py`, `tests/test_quality_harness.py` |
| fixtures | `tests/fixtures/quality/posts.jsonl`, `tests/fixtures/quality/failures.jsonl`, `tests/fixtures/quality/report.json` |
| code docs | `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/public-contracts.md`, `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/code/code-generation-summary.md` |

## Modified Files

| File | Change |
|---|---|
| `pyproject.toml` | added `anyio` runtime dependency and optional smoke markers: `docker`, `garage`, `postgres`, `mcp`, `live` |
| `src/fmkorea_scraper/outputs/__init__.py` | exported `PostgresCheckpointStore`, `S3OutputStore`, and `S3Spool` |
| `src/fmkorea_scraper/outputs/factory.py` | wired S3-compatible output to `S3OutputStore` and PostgreSQL checkpoint mode to `PostgresCheckpointStore` |
| `tests/test_outputs_storage.py` | updated PostgreSQL checkpoint factory expectation from deferred rejection to import-safe store construction |

## Implemented Contracts

- container one-shot `python -m fmkorea_scraper.adapters.container`
- Docker `docker-entrypoint.sh` delegation
- container env validation and safe exit codes
- S3-compatible JSONL/report/media output adapter
- PostgreSQL checkpoint save/load/latest adapter
- MCP handler boundary and optional MCP server creation
- shared adapter safe error payload helper
- quality fixture harness for JSONL/report/failure shape

## Validation Results

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\test_container_adapter.py tests\test_mcp_adapter.py tests\test_s3_output_and_postgres.py tests\test_quality_harness.py tests\test_outputs_storage.py -q --tb=short
```

Result:

```text
26 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short
```

Result:

```text
144 passed, 1 skipped
```

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src tests
```

Result:

```text
passed
```

```powershell
$env:PYTHONPATH='src'; python -c "import fmkorea_scraper.adapters.container, fmkorea_scraper.adapters.mcp; print('ok')"
```

Result:

```text
ok
```

## Deferred Boundaries

- `retry_parser_failures` can expose the MCP payload boundary, but full execution is UOW-009.
- Docker image build, Garage smoke, PostgreSQL smoke, MCP runtime smoke, and live site smoke remain opt-in checks.
- Production IaC and shared multi-scraper platform provisioning remain later UOW/platform work.
