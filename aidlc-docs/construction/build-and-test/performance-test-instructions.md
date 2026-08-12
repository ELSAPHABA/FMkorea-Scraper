# Performance Test Instructions - UOW-002 HTTP Runtime Policy

## Scope

UOW-002 defines HTTP runtime policy only. It has no search traversal, parser, storage writer, worker queue, media download persistence, or live scraping loop to load test.

## Current Performance Requirement

The active requirement is qualitative:

- retry/backoff must be bounded
- rate limiting must be deterministic under fake time
- User-Agent rotation must be O(1) per request attempt
- safe event building must drop secrets without serializing response bodies

No fixed throughput or latency SLA is set for UOW-002.

## Current Result

- **Load test**: N/A
- **Stress test**: N/A
- **Policy invariant tests**: PASS through unit and property-based tests

## Future Performance Tests

Add focused benchmarks after parser/runtime units exist:

- link collection throughput with fake HTML fixtures
- comment-heavy post fetch and parse cost
- media metadata extraction without downloads
- JSONL append throughput
- worker queue link consumption
- real rate-limit behavior under configurable request intervals
