# Unit Test Execution - UOW-002 HTTP Runtime Policy

## Scope

UOW-002 tests validate HTTP runtime policy plus the existing UOW-001 model contracts.

Covered HTTP runtime behavior:

- `.env` proxy allowlist loading
- explicit proxy priority over `.env`
- User-Agent file loading and rotation
- in-memory cookie clear on User-Agent rotation
- retry and limiter interaction
- CAPTCHA no-retry behavior
- cancellation cleanup
- safe HTTP event redaction
- property-based header, proxy, classifier, and secret-redaction invariants

## Run Unit Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

## Expected Result

- **Total tests**: 45
- **Expected failures**: 0
- **Expected status**: PASS

## Current Result

```text
45 passed in 4.88s
```

## Test Groups

- `tests/test_http_runtime.py`: example-based HTTP runtime tests
- `tests/test_http_properties.py`: HTTP runtime property-based tests
- `tests/strategies/http_runtime.py`: HTTP runtime Hypothesis strategies
- `tests/test_models.py`: model validation tests
- `tests/test_api_ports.py`: public API placeholder and protocol tests
- `tests/test_schema.py`: schema registry and snapshot tests
- `tests/test_properties.py`: model property-based tests

## Failure Handling

If tests fail:

1. Read the first failing assertion or exception.
2. Fix the shared runtime policy component instead of patching only one caller.
3. Rerun `$env:PYTHONPATH='src'; python -m pytest tests`.
4. If dependency resolution breaks, run `python -m pip check`.
