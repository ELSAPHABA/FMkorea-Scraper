# Performance Test Instructions - UOW-007 CLI Adapter

## Scope

UOW-007 is a local CLI adapter. It has no standalone server, distributed worker service, database, or cloud runtime.

Load/stress testing is not applicable in this unit.

## Default Performance Checks

The default gate uses lightweight substitutes:

- import-safety subprocess test
- parser construction test
- fake-runner command execution
- property-based command mapping tests
- no-live-network default suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_cli_adapter.py tests\test_cli_properties.py -q --tb=short
```

Latest result:

```text
21 passed
```

## Deferred Performance Work

Later units may add:

- container startup timing
- queue-backed worker throughput
- live smoke rate-limit validation
- S3-compatible output throughput
- PostgreSQL checkpoint latency

Those are outside UOW-007.
