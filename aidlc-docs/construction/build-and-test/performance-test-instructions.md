# Performance Test Instructions - UOW-003 Search And Link Collection

## Status

Load and stress testing are N/A for UOW-003.

## Reason

UOW-003 is an importable link collection library. It does not own:

- worker count
- queue lifecycle
- checkpoint persistence
- storage writes
- container runtime
- scheduler loops
- network rate policy

Those concerns belong to UOW-002, UOW-005, UOW-006, UOW-007, and UOW-008.

## Current Performance Guardrails

Default tests cover bounded and deterministic behavior:

- integrated search page clamp at 1000
- page traversal stop conditions
- run-local in-memory dedupe
- range-filter early stop behavior
- sequential deep-search board expansion

## Future Performance Tests

Add load/stress tests when UOW-005 JobRunner and worker queues exist.

Suggested future targets:

- candidate queue throughput
- detail worker fan-out
- checkpoint write cadence
- storage write latency
- live smoke request pacing
