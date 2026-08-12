# Unit Test Execution - UOW-006 Output And Storage

## Run Unit Tests

### 1. Execute All Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

Expected current result:

```text
83 passed, 2 skipped
```

### 2. Execute UOW-006 Tests Only

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_storage.py tests\test_outputs_properties.py
```

## Covered UOW-006 Test Areas

- local output layout and path sanitization
- local post JSONL append
- local failure JSONL write/read
- failure detail redaction
- local report JSON write
- local media byte write and metadata-only pass-through
- local `Checkpoint.json` save/load/load-latest
- local path traversal rejection
- S3-compatible object key generation
- fake S3 JSONL same-key spool upload
- storage factory mode selection
- PostgreSQL checkpoint mode rejection in this unit
- JSONL line-separator escaping
- property-based output key, JSONL, and redaction invariants

## Optional Smoke Tests

Default unit tests do not require Garage/S3 or Polars.

Polars smoke is skipped when Polars is not installed:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_polars_smoke.py
```

S3-compatible smoke is skipped unless explicitly enabled:

```powershell
$env:FMKOREA_S3_SMOKE_ENABLED='true'
$env:FMKOREA_S3_ENDPOINT_URL='http://127.0.0.1:3900'
$env:FMKOREA_S3_BUCKET='your-bucket'
$env:FMKOREA_S3_ACCESS_KEY_ID='your-access-key'
$env:FMKOREA_S3_SECRET_ACCESS_KEY='your-secret-key'
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_s3_smoke.py
```
