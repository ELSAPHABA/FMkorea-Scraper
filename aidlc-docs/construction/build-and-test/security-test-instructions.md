# Security Test Instructions - UOW-004 Post Detail And Content Parsing

## Current Security Checks

UOW-004 security behavior is verified through unit, fixture, and property tests.

Covered:

- parser service uses injected HTTP only
- parser warnings redact raw HTML-like content and sensitive marker values
- no raw HTML fields are added to persisted models
- malformed optional blocks/comments do not leak full source payloads
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
python -c "import fmkorea_scraper.parse"
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
