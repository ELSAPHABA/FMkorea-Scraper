# Performance Test Instructions - UOW-005 Job Runner And Checkpoint

## Status

Load and stress testing are not required for UOW-005.

## Reason

UOW-005 is an importable in-process JobRunner library. It does not own:

- process replica count
- container sizing
- external Job queue leases
- SQS/DLQ throughput
- live scraper smoke execution
- cloud scheduler loops
- Garage/S3/PostgreSQL provisioning

Those concerns belong to UOW-007, UOW-008, UOW-010, and later platform work.

## Current Performance Guardrails

Default tests cover bounded and deterministic behavior:

- `post_worker_count` controls worker task count
- `queue_max_size` creates bounded in-process queue backpressure
- `media_worker_count` caps concurrent media downloads with a semaphore
- completed-key skip avoids repeated detail fetches
- checkpoint cadence is every 10 successful output writes
- runner does not retain all parsed `PostResult` values after output write
- property tests cover cadence and counter consistency

## Future Performance Tests

Add load/stress tests when CLI/container runtime exists.

Suggested future targets:

- post worker throughput under fake HTTP/parser/store
- checkpoint save cadence under high candidate counts
- media download concurrency behavior under realistic file sizes
- S3-compatible output latency with Garage
- resume dedupe cost with large completed-key sets
- parser failure record readback cost for UOW-009 retry selection
