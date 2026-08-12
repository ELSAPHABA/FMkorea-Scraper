# Security Test Instructions - UOW-006 Output And Storage

## Current Security Checks

UOW-006 security behavior is verified through unit and property tests.

Covered:

- generated local paths are contained under the configured base output path
- path traversal attempts are rejected
- failure details drop credential, cookie, proxy, token, header, raw HTML, raw body, and content-like fields
- S3 credentials are not stored in `StoredObjectRef`
- S3 dependency is lazy-loaded only when S3 mode is constructed
- package import does not write files or connect to external services
- PostgreSQL checkpoint mode is rejected in this unit instead of silently half-supporting it
- JSONL writer escapes line-separator characters that can split one logical record into multiple physical lines

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
python -c "import fmkorea_scraper.outputs"
```

Expected behavior:

- no environment read
- no `.env` read
- no terminal prompt
- no file write
- no S3 connection
- no bucket creation
- no queue creation
- no database connection

## Deferred Security Tests

Later units should add checks for:

- checkpoint advancement only after durable output write
- container env secret injection
- PostgreSQL credential redaction
- MCP input validation
- AWS CDK no hardcoded secrets
