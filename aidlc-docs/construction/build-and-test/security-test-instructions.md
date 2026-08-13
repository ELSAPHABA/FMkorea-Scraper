# Security Test Instructions - UOW-008 Container, MCP, And Test Harness

## Safe Error Checks

Run:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_container_adapter.py tests\test_mcp_adapter.py tests\test_quality_harness.py -q --tb=short
```

Covered:

- `ContainerEnvConfig` repr excludes `DATABASE_URL` and S3 secret values
- container validation errors expose only safe details
- MCP validation and unsupported errors use safe payloads
- fixture failure records exclude raw HTML, cookies, passwords, and tokens

## Docker Context Checks

Root files verified by build:

- `.dockerignore`
- `.gitattributes`
- `Dockerfile`
- `docker-entrypoint.sh`

Expected security behavior:

- local `.env` and `.env.*` files are excluded from Docker context
- local output/checkpoint/cache directories are excluded from Docker context
- shell script line endings stay LF in Git
- worker container exposes no inbound port by default

## Dependency Checks

Clean image check:

```powershell
docker run --rm --entrypoint python fmkorea-scraper:uow-008-build-test -m pip check
```

UOW-008 result:

```text
No broken requirements found.
```

Host global check note:

```powershell
py -3.12 -m pip check
```

The host global Python 3.12 environment has unrelated package issues involving Google packages, `selenium`, and `update`. The clean Docker image built from this project passes dependency validation, so the host global issue is not treated as a UOW-008 project failure.
