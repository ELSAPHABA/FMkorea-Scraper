# Performance Test Instructions

## Scope

UOW-001 defines model contracts only. There is no network, parser, storage, worker, or media download runtime to load test.

## Current Performance Requirement

The active requirement is qualitative:

- model validation and JSON serialization must not become the primary bottleneck for normal post payloads
- unbounded metadata recursion and oversized metadata must be rejected

No fixed millisecond SLA is set for UOW-001. Exact measurement belongs to parser/job integration after real post and comment fixtures are available.

## Current Result

- **Load test**: N/A
- **Stress test**: N/A
- **Model invariant tests**: PASS through unit and property-based tests

## Future Performance Tests

Add focused benchmarks after parser/runtime units exist:

- `PostResult` validation with real large post fixtures
- comment-heavy post serialization
- JSONL append throughput
- worker queue link consumption
- media metadata extraction without downloads
