# Unit Test Execution

## Scope

UOW-001 tests validate model contracts, public API placeholders, port protocols, schema snapshots, metadata bounds, error redaction, import side-effect safety, and property-based invariants.

## Run Unit Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

## Expected Result

- **Total tests**: 33
- **Expected failures**: 0
- **Expected status**: PASS

## Current Result

```text
33 passed
```

## Test Groups

- `tests/test_models.py`: example-based model validation tests
- `tests/test_api_ports.py`: public API placeholder and protocol tests
- `tests/test_schema.py`: schema registry and snapshot tests
- `tests/test_properties.py`: Hypothesis property-based tests

## Failure Handling

If tests fail:

1. Read the first failing assertion or validation error.
2. Fix the model, schema, or test contract at the source.
3. If a persisted schema intentionally changed, update `tests/snapshots/schema_versions.json` and document compatibility impact.
4. Rerun `python -m pytest tests`.
