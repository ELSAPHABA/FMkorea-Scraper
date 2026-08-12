# Security Test Instructions - UOW-003 Search And Link Collection

## Current Security Checks

UOW-003 security behavior is verified through unit, fixture, and property tests.

Covered:

- unsupported direct URL host rejection
- safe URL labels omit raw query strings and raw keywords
- row/item parser failures are recorded as safe `CollectorFailure` values
- collector service uses injected HTTP only
- no browser automation dependency
- no queue, storage, database, or runtime infrastructure dependency

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
python -c "import fmkorea_scraper.collect"
```

Expected behavior:

- no network request
- no `.env` read
- no `user-agents.txt` read
- no terminal prompt
- no file write
- no queue creation
- no HTTP client creation

## Deferred Security Tests

Later units should add checks for:

- CAPTCHA/block checkpoint stop behavior
- storage secret redaction
- container env injection
- MCP input validation
- AWS CDK no hardcoded secrets
