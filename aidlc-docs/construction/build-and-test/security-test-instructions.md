# Security Test Instructions - UOW-002 HTTP Runtime Policy

## Scope

UOW-002 security validation focuses on HTTP runtime secret safety and import side-effect safety. It has no deployed service, authentication layer, browser surface, object storage adapter, or database adapter.

## Covered Security Checks

The current tests cover:

- `.env` proxy loading uses `FMKOREA_PROXY_*` allowlist fields
- `.env` loading does not mutate `os.environ`
- explicit proxy values override `.env`
- proxy password does not appear in safe labels
- safe events drop query strings
- safe events omit headers, body, cookies, and passwords
- CAPTCHA responses are not retried
- cancellation closes the async client
- package import remains safe

## Run Security-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_http_runtime.py tests/test_http_properties.py tests/test_api_ports.py
python -m pip check
```

## Current Result

- **Status**: PASS
- **Dependency Check**: PASS, no broken requirements
- **Vulnerability scanner**: N/A for this unit; dependency/security scanning belongs to CI/container stages
- **Secret handling**: PASS through redaction, proxy, and import side-effect tests
