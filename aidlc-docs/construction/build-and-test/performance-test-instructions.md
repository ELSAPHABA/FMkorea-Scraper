# Performance Test Instructions - UOW-004 Post Detail And Content Parsing

## Status

Load and stress testing are N/A for UOW-004.

## Reason

UOW-004 is an importable detail parsing library. It does not own:

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

- optional `max_content_blocks`
- optional `max_comments`
- optional `max_comment_pages`
- per-post media dedupe
- duplicate comment suppression
- sequential extra comment page fetch

## Future Performance Tests

Add load/stress tests when UOW-005 JobRunner and worker queues exist.

Suggested future targets:

- post detail parse throughput
- detail worker fan-out
- extra comment page fetch latency
- checkpoint write cadence
- storage write latency
- live smoke request pacing
