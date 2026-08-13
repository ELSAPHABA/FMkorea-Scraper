# Performance Test Instructions - UOW-008 Container, MCP, And Test Harness

## Status

No dedicated performance benchmark is required for UOW-008.

Reason:

- the unit adds adapter boundaries, Docker packaging, S3/PostgreSQL storage adapters, MCP handler wrappers, and fixture checks
- it does not add a parser hot path, scheduler, queue algorithm, or network pagination strategy

## Substitute Checks

Use the default validation suite as the regression baseline:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests -q --tb=short
```

UOW-008 result:

```text
142 passed, 3 skipped in 28.20s
```

## Future Benchmarks

Add targeted benchmarks only if later units introduce:

- high-volume parser-failure retry processing
- queue consumers
- multi-scraper orchestration
- large S3 JSONL spool throughput requirements
- PostgreSQL checkpoint contention
