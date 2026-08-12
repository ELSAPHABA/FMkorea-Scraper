# Build Instructions - UOW-003 Search And Link Collection

## Prerequisites

- **Python**: 3.11 or newer
- **Build backend**: hatchling via PEP 517
- **Package manager**: pip
- **Runtime dependencies**: `pydantic>=2,<3`, `httpx>=0.28,<1`, `python-dotenv>=1,<2`, `beautifulsoup4>=4,<5`
- **Test dependencies**: `pytest>=8,<9`, `hypothesis>=6,<7`
- **Environment variables**: none required for default tests

UOW-003 must remain import-safe. Building or importing the package must not make network requests, read runtime files, prompt terminal input, write outputs, create queues, or create HTTP clients.

## Build Steps

### 1. Install Dependencies

```powershell
python -m pip install -e ".[test]"
```

If editable install is not desired, tests can be run with `PYTHONPATH=src` after dependencies are available.

### 2. Check Installed Requirements

```powershell
python -m pip check
```

### 3. Build Wheel

```powershell
python -m pip wheel . --no-deps -w dist
```

### 4. Verify Build Success

Expected artifact:

```text
dist/fmkorea_scraper-0.1.0-py3-none-any.whl
```

Successful build output should include:

```text
Successfully built fmkorea-scraper
```

## Current Build Result

- **Command**: `python -m pip wheel . --no-deps -w dist`
- **Status**: PASS
- **Artifact**: `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
- **Size**: 45192 bytes
- **SHA256**: `d301f5c4b5dea6e9255968026a0658851221ed9c1a32301630aa59a6905d7a29`
- **Dependency Check**: PASS

## Troubleshooting

### Build Fails With Missing Build Backend

Cause: pip cannot install `hatchling` into the isolated build environment.

Fix:

```powershell
python -m pip install hatchling
python -m pip wheel . --no-deps -w dist
```

### Tests Cannot Import Package

Cause: package is not installed and `PYTHONPATH` is not set.

Fix:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```
