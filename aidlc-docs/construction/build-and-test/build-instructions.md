# Build Instructions - UOW-004 Post Detail And Content Parsing

## Prerequisites

- **Python**: 3.11 or newer
- **Build backend**: hatchling via PEP 517
- **Package manager**: pip
- **Runtime dependencies**: `pydantic>=2,<3`, `httpx>=0.28,<1`, `python-dotenv>=1,<2`, `beautifulsoup4>=4,<5`
- **Test dependencies**: `pytest>=8,<9`, `hypothesis>=6,<7`
- **Environment variables**: none required for default tests

UOW-004 must remain import-safe. Building or importing the parser package must not make network requests, read runtime files, prompt terminal input, write outputs, create queues, create storage clients, or create HTTP clients.

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
- **Size**: 57249 bytes
- **SHA256**: `818f358004ade2e35c4642481c59f80f5055c9c39343659ae835f62057de95d7`
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
