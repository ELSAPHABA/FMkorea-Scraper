# Build Instructions

## Prerequisites

- **Python**: 3.11 or newer
- **Build backend**: hatchling via PEP 517
- **Package manager**: pip
- **Runtime dependency**: `pydantic>=2,<3`
- **Test dependencies**: `pytest>=8,<9`, `hypothesis>=6,<7`
- **Environment variables**: none required for UOW-001

UOW-001 must remain import-safe. Building or importing the package must not read `.env`, `user-agents.txt`, proxy values, cookie files, or perform network requests to the target site.

## Build Steps

### 1. Install Dependencies

```powershell
python -m pip install -e ".[test]"
```

If editable install is not desired, tests can be run with `PYTHONPATH=src` after dependencies are available.

### 2. Build Wheel

```powershell
python -m pip wheel . --no-deps -w dist
```

### 3. Verify Build Success

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
- **Size**: 29974 bytes
- **SHA256**: `6f9b3ff98fee1be38d0d24cdc0be8ee542f2203fbc06a11ddb77c77fd4a228be`

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
