# Build Instructions - UOW-007 CLI Adapter

## Prerequisites

- **Build Tool**: `pip wheel` with hatchling PEP 517 backend
- **Python**: 3.11+ required, validated on Python 3.13.9
- **Dependencies**: project dependencies from `pyproject.toml`
- **Required Environment Variables**: none for default build
- **Optional Environment Variables**: live/S3/Polars smoke variables are not required for UOW-007 default gate

## Build Steps

### 1. Install Test Dependencies

```powershell
python -m pip install -e ".[test]"
```

### 2. Build Wheel

```powershell
python -m pip wheel . --no-deps -w dist
```

Expected artifact:

```text
dist/fmkorea_scraper-0.1.0-py3-none-any.whl
```

### 3. Verify CLI Module Help

```powershell
$env:PYTHONPATH='src'
python -m fmkorea_scraper.adapters.cli --help
```

Expected result:

- command exits `0`
- help lists `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard`

## Latest Build Result

- **Executed At**: 2026-08-13T01:26:37Z
- **Build Command**: `python -m pip wheel . --no-deps -w dist`
- **Status**: PASS
- **Artifact**: `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
- **Artifact Size**: 75751 bytes
- **Artifact SHA256**: `294305329e7aa4fb2365c72c2419a89856a0b51d499083b2d50e6cdbf814794c`

## Troubleshooting

### Build Fails with Missing Hatchling

Cause: build isolation could not install the backend.

Fix:

```powershell
python -m pip install --upgrade pip
python -m pip wheel . --no-deps -w dist
```

### CLI Module Help Fails

Cause: package source path is not visible to Python.

Fix:

```powershell
$env:PYTHONPATH='src'
python -m fmkorea_scraper.adapters.cli --help
```
