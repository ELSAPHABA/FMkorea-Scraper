# Build Instructions - UOW-002 HTTP Runtime Policy

## Prerequisites

- **Python**: 3.11 or newer
- **Build backend**: hatchling via PEP 517
- **Package manager**: pip
- **Runtime dependencies**: `pydantic>=2,<3`, `httpx>=0.28,<1`, `python-dotenv>=1,<2`
- **Test dependencies**: `pytest>=8,<9`, `hypothesis>=6,<7`
- **Environment variables**: none required for default tests

UOW-002 must remain import-safe. Building or importing the package must not read `.env`, `user-agents.txt`, proxy values, cookie files, or perform network requests.

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
- **Size**: 36048 bytes
- **SHA256**: `19030995f6ca3f43f1af314f7593a9020010af918183c332fbdb70476f69d778`
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
