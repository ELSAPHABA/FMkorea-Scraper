# Build and Test Summary - UOW-009 Parser Failure Retry Reprocessor

## Build Status

- **Build Tool**: pip wheel with hatchling PEP 517 backend
- **Python Used**: Python 3.12.10 via `py -3.12`
- **Build Status**: PASS
- **Build Command**: `py -3.12 -m pip wheel . --no-deps -w dist`
- **Build Artifact**: `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
- **Artifact Size**: 87472 bytes
- **Artifact SHA256**: `B22590BA2332B664C36D5F1AEFA8C4557D50F2030BDC7FB97BAE23C548D00BCA`

## Docker Build Status

- **Docker Version**: Docker 29.7.2
- **Docker Build Command**: `docker build -t fmkorea-scraper:uow-009-build-test .`
- **Docker Build Status**: PASS
- **Image ID**: `sha256:1dfa421b147a03ab3f360075e4b3e79b642c689e6fd89e46cd4e47d550c1b422`
- **Entrypoint Inspect**: `["/app/docker-entrypoint.sh"]`
- **Container Run Env Validation Smoke**: `docker run --rm fmkorea-scraper:uow-009-build-test run` -> `$LASTEXITCODE=2`
- **Container Retry Env Validation Smoke**: `docker run --rm fmkorea-scraper:uow-009-build-test retry-parser-failures --failure-path s3://bucket/failures.jsonl` -> `$LASTEXITCODE=2`
- **Container Dependency Check**: `docker run --rm --entrypoint python fmkorea-scraper:uow-009-build-test -m pip check` -> `No broken requirements found.`

## Test Execution Summary

### Focused UOW-009 Tests

- **Command**: `$env:PYTHONPATH='src'; py -3.12 -m pytest tests\test_parser_failure_retry.py tests\test_parser_failure_retry_properties.py tests\test_cli_adapter.py tests\test_mcp_adapter.py tests\test_container_adapter.py -q --tb=short`
- **Passed**: 45
- **Skipped**: 0
- **Failed**: 0
- **Status**: PASS
- **Result**: `45 passed in 13.84s`

### Full Default Tests

- **Command**: `$env:PYTHONPATH='src'; py -3.12 -m pytest tests -q --tb=short`
- **Passed**: 151
- **Skipped**: 3
- **Failed**: 0
- **Status**: PASS
- **Result**: `151 passed, 3 skipped in 23.73s`

### Compile Check

- **Command**: `$env:PYTHONPATH='src'; py -3.12 -m compileall -q src tests`
- **Status**: PASS

### Import And Help Smoke

- **Import Command**: `$env:PYTHONPATH='src'; py -3.12 -c "import fmkorea_scraper, fmkorea_scraper.retry, fmkorea_scraper.adapters.cli, fmkorea_scraper.adapters.container, fmkorea_scraper.adapters.mcp; print('ok')"`
- **Import Status**: PASS, `ok`
- **CLI Help Command**: `$env:PYTHONPATH='src'; py -3.12 -m fmkorea_scraper.adapters.cli --help`
- **CLI Help Status**: PASS
- **Container Local Validation Command**: `$env:PYTHONPATH='src'; py -3.12 -m fmkorea_scraper.adapters.container run`
- **Container Local Validation Status**: PASS, exit code `2` with safe validation JSON

## Dependency Checks

- **Clean Docker Image**: PASS, `No broken requirements found.`
- **Host pip notice**: pip reported an available update only; not a project failure.

## Security Checks

- **Status**: PASS
- **Covered**: safe retry summaries, no raw failure line output, no credential output in retry refs, MCP safe error payloads, import side-effect safety, container validation redaction

## Performance Tests

- **Status**: PASS by scoped substitute checks
- **Covered**: selector property tests, streaming JSONL selection tests, key-only existing success skip tests
- **Deferred**: large-file benchmark and queue/DLQ throughput tests remain future platform work

## Environment

- **Platform**: Windows
- **Supported Python Used For Official Checks**: 3.12.10
- **Docker**: Docker 29.7.2
- **Lockfile**: not generated in this stage

## Overall Status

- **Wheel Build**: PASS
- **Docker Build**: PASS
- **Default Tests**: PASS
- **Compile Check**: PASS
- **Clean Dependency Check**: PASS
- **Ready For Next Stage**: Yes, after review approval

## Generated Instruction Files

- `aidlc-docs/construction/build-and-test/build-instructions.md`
- `aidlc-docs/construction/build-and-test/unit-test-instructions.md`
- `aidlc-docs/construction/build-and-test/integration-test-instructions.md`
- `aidlc-docs/construction/build-and-test/performance-test-instructions.md`
- `aidlc-docs/construction/build-and-test/security-test-instructions.md`
- `aidlc-docs/construction/build-and-test/build-and-test-summary.md`
