# Unit Test Execution - UOW-005 Job Runner And Checkpoint

## Run Unit Tests

### 1. Execute All Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

Expected current result:

```text
97 passed, 2 skipped
```

### 2. Execute UOW-005 Tests Only

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_runner_service.py tests\test_runner_workers.py tests\test_runner_checkpointing.py tests\test_runner_policies.py tests\test_runner_properties.py
```

## Covered UOW-005 Test Areas

- normal JobRunner completion
- final report writing
- output store and failure store finalization
- completed-key skip before detail fetch
- resume from checkpoint with a new run result
- `core.api.run_job` explicit runner delegation
- CAPTCHA fail-closed stopped Job handling
- stopped checkpoint reason persistence
- media download semaphore limit
- checkpoint load failure mapping
- checkpoint save failure mapping
- completed-key token stability
- 10-success checkpoint cadence
- stop reason mapping
- parser failure retryability
- property-based completed-key dedupe
- property-based cadence behavior
- property-based report counter consistency

## Optional Smoke Tests

UOW-005 has no live smoke test by default.

Live Job smoke is deferred to the future CLI/container adapter because it requires concrete runtime option mapping and real storage wiring.

Existing optional lower-level smoke tests remain available:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_polars_smoke.py
```

```powershell
$env:FMKOREA_S3_SMOKE_ENABLED='true'
$env:FMKOREA_S3_ENDPOINT_URL='http://127.0.0.1:3900'
$env:FMKOREA_S3_BUCKET='your-bucket'
$env:FMKOREA_S3_ACCESS_KEY_ID='your-access-key'
$env:FMKOREA_S3_SECRET_ACCESS_KEY='your-secret-key'
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_s3_smoke.py
```
