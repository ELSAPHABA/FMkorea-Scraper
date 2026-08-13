# Performance Test Instructions - UOW-009 Parser Failure Retry Reprocessor

## Scope

UOW-009 performance risk is bounded to retry selection over JSONL inputs.

The design keeps:

- streaming failure input reads
- key-only existing success index
- no raw invalid-line storage
- direct-post execution through existing worker/rate policy

## Default Checks

Property tests cover selector invariants:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests\test_parser_failure_retry_properties.py -q --tb=short
```

Included in focused result:

```text
45 passed in 13.84s
```

## Deferred Checks

Large-file benchmarks are deferred until real failure files show memory or runtime pressure.

Future benchmarks should measure:

- 10k, 100k, and 1M failure line selection
- existing success index memory use
- S3/Garage object streaming latency
- queue/DLQ retry throughput after platform queue work exists
