# Security Test Instructions

## Scope

UOW-001 security validation is limited to model/input safety and safe error output. It has no deployed service, authentication layer, browser surface, object storage adapter, or database adapter.

## Covered Security Checks

The current tests cover:

- unknown public fields are rejected
- invalid job/source combinations are rejected
- invalid realtime stop conditions are rejected
- invalid ranges are rejected
- invalid checkpoint stop states are rejected
- error details redact secret-like data
- package import does not read credential files or create side effects
- metadata is constrained by JSON compatibility, depth, and serialized size validators

## Run Security-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_models.py tests/test_properties.py
```

## Current Result

- **Status**: PASS
- **Vulnerability scanner**: N/A for this unit; dependency/security scanning belongs to CI/container stages
- **Secret handling**: PASS through redaction and import side-effect tests
