# Integration Test Instructions - UOW-008 Container, MCP, And Test Harness

## Import Safety

```powershell
$env:PYTHONPATH='src'
py -3.12 -c "import fmkorea_scraper.adapters.container, fmkorea_scraper.adapters.mcp; print('ok')"
```

Expected:

```text
ok
```

This confirms adapter imports do not read env, open network connections, connect to PostgreSQL/S3, or start an MCP server.

## CLI Help Smoke

```powershell
$env:PYTHONPATH='src'
py -3.12 -m fmkorea_scraper.adapters.cli --help
```

Expected:

- command exits successfully
- shows `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard`

## Container Local Validation Smoke

```powershell
$env:PYTHONPATH='src'
py -3.12 -m fmkorea_scraper.adapters.container run
```

Expected:

- exits with code `2`
- prints safe JSON validation error
- does not include secret values

## Docker Validation Smoke

```powershell
docker build -t fmkorea-scraper:uow-008-build-test .
docker run --rm fmkorea-scraper:uow-008-build-test run
Write-Output "LAST=$LASTEXITCODE"
```

Expected:

- Docker build succeeds
- Docker run exits with `LAST=2`
- output is safe validation JSON for missing `DATABASE_URL`

## Optional External Smoke Tests

External checks are not default tests. Run only when endpoints are intentionally available:

- Garage/S3-compatible object storage
- PostgreSQL
- MCP runtime package
- live site network access

Use pytest markers to gate those tests:

```powershell
py -3.12 -m pytest -m "docker or garage or postgres or mcp or live"
```

Do not run optional live/storage smoke checks during default CI unless the required env values are explicitly provided.
