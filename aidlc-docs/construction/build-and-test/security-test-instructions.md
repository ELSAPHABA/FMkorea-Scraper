# Security Test Instructions - UOW-005 Job Runner And Checkpoint

## Current Security Checks

UOW-005 security behavior is verified through unit and property tests.

Covered:

- runner package import has no runtime side effects
- runner receives `JobConfig` and explicit dependencies only
- runner does not read environment variables, `.env`, user-agent files, cookie files, proxy profiles, or storage credentials
- CAPTCHA and blocked responses fail closed
- completed keys advance only after output append success
- failure records use safe allow-list context
- report output uses aggregate counts and stored object refs only
- checkpoint persistence goes through injected checkpoint port
- media byte download uses injected `HttpPort` only when `MediaMode.DOWNLOAD`
- default tests do not require live FMKorea, browser automation, Garage/S3, PostgreSQL, SQS/DLQ, Docker, MCP, or CDK

## Dependency Check

Command:

```powershell
python -m pip check
```

Current result:

```text
No broken requirements found.
```

## Import Safety

Manual or automated checks should verify importing these modules has no runtime side effects:

```powershell
$env:PYTHONPATH='src'
python -c "import fmkorea_scraper.runner"
```

Expected behavior:

- no environment read
- no `.env` read
- no terminal prompt
- no file write
- no FMKorea request
- no S3 connection
- no queue service connection
- no database connection

## Deferred Security Tests

Later units should add checks for:

- CLI input validation and secret masking
- container env secret injection
- PostgreSQL credential redaction
- MCP input validation
- SQS/DLQ payload redaction
- AWS CDK no hardcoded secrets
