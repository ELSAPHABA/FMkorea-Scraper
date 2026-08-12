# Performance Test Instructions - UOW-006 Output And Storage

## Status

Load and stress testing are N/A for UOW-006.

## Reason

UOW-006 is an importable output/storage library. It does not own:

- worker count
- queue lifecycle
- retry scheduling
- checkpoint advancement cadence
- container runtime
- scheduler loops
- cloud object-store provisioning

Those concerns belong to UOW-005, UOW-007, UOW-008, and later infrastructure work.

## Current Performance Guardrails

Default tests cover bounded and deterministic behavior:

- one JSON object per physical JSONL line
- file-backed S3 JSONL spool instead of full in-memory buffers
- atomic JSON writes for small report/checkpoint documents
- path/key generation without network access
- fake S3 write behavior without external latency
- local checkpoint `load_latest()` correctness for current file-backed scope

## Future Performance Tests

Add load/stress tests when UOW-005 JobRunner and worker queues exist.

Suggested future targets:

- post output append throughput
- S3 spool upload latency
- checkpoint save cadence under worker fan-out
- media byte write throughput
- Garage/S3-compatible object-store smoke latency
- failure JSONL readback cost for parser-failure retry
