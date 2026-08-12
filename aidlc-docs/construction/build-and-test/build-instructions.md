# Build Instructions - UOW-006 Output And Storage

## Prerequisites

- **Python**: 3.11 or newer
- **Build backend**: hatchling via PEP 517
- **Package manager**: pip
- **Runtime dependencies**: `pydantic>=2,<3`, `httpx>=0.28,<1`, `python-dotenv>=1,<2`, `beautifulsoup4>=4,<5`
- **Optional dependencies**: `boto3>=1.34,<2` for S3-compatible smoke, `polars>=1,<2` for analysis smoke
- **Test dependencies**: `pytest>=8,<9`, `hypothesis>=6,<7`
- **Environment variables**: none required for default tests

UOW-006 must remain import-safe. Building or importing the output package must not read environment variables, connect to S3, create buckets, write output files, prompt terminal input, create queues, or create database connections.

## Build Steps

### 1. Install Dependencies

```powershell
python -m pip install -e ".[test]"
```

Optional smoke dependencies:

```powershell
python -m pip install -e ".[test,s3,analysis]"
```

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
- **Size**: 67741 bytes
- **SHA256**: `5a46db015b219eeac272673f13d6a673037ff65fb8cfb9f7ff7e4121b532c2e6`
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
