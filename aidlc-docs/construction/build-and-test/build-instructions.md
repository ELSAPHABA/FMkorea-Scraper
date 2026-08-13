# Build Instructions - UOW-008 Container, MCP, And Test Harness

## Python Version

Use a supported Python version. In this workspace, plain `python` resolves to 3.10.20, which is below `requires-python >=3.11`, so official checks use:

```powershell
py -3.12 --version
```

Expected:

```text
Python 3.12.10
```

## Wheel Build

```powershell
py -3.12 -m pip wheel . --no-deps -w dist
```

Expected artifact:

```text
dist/fmkorea_scraper-0.1.0-py3-none-any.whl
```

UOW-008 result:

```text
size: 81648 bytes
sha256: 77d72f19fb25a68597dee4cce293e54977ee335cc25b1fdea7154665fcafb800
```

## Docker Image Build

```powershell
docker build -t fmkorea-scraper:uow-008-build-test .
```

Expected:

- image builds from `python:3.11-slim`
- `docker-entrypoint.sh` is executable in the image
- package installs with `.[s3,postgres]`

UOW-008 result:

```text
PASS
image: sha256:e49d413822544a7c1b5e237f5c7fdd0ad5f1c093ffdc5d7cd0383facc3e12025
```

## Docker Entrypoint Check

```powershell
docker image inspect fmkorea-scraper:uow-008-build-test --format '{{json .Config.Entrypoint}}'
```

Expected:

```text
["/app/docker-entrypoint.sh"]
```

Safe validation smoke:

```powershell
docker run --rm fmkorea-scraper:uow-008-build-test run
Write-Output "LAST=$LASTEXITCODE"
```

Expected:

```text
LAST=2
{"ok": false, "error": {"code": "validation_error", ...}}
```

This smoke intentionally omits storage env values so it does not contact Garage, PostgreSQL, or the live site.
