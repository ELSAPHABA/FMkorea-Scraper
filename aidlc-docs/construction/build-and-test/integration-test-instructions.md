# Integration Test Instructions - UOW-005 Job Runner And Checkpoint

## Purpose

Validate that UOW-005 coordinates UOW-001 models and UOW-002/UOW-003/UOW-004/UOW-006 ports through explicit dependencies without owning CLI, container, MCP, external queue, or storage infrastructure.

## Current Integration Coverage

### UOW-001 Model And Port Integration

- `JobConfig`
- `WorkerConfig`
- `PostCandidate`
- `PostKey`
- `Checkpoint`
- `FailureRecord`
- `JobReport`
- `StoredObjectRef`
- `HttpPort`
- `OutputStorePort`
- `FailureStorePort`
- `MediaStorePort`
- `CheckpointStorePort`
- `ClockPort`

### UOW-003 Collector Boundary

`JobRunner` consumes an injected collector with `collect(source)` and receives `PostCandidate` values only.

### UOW-004 Detail Parser Boundary

`JobRunner` calls an injected detail service with `parse(candidate)` and expects a `PostResult`.

### UOW-006 Storage Boundary

`JobRunner` uses injected output, failure, media, and checkpoint stores. Tests verify output-before-checkpoint ordering and final report writing through fake stores.

## Run Integration-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_runner_service.py tests\test_runner_workers.py tests\test_runner_checkpointing.py tests\test_api_ports.py
```

## Deferred Integration Tests

The following require later units:

- UOW-007 CLI option and wizard wiring
- UOW-008 container env injection
- UOW-008 MCP adapter integration
- UOW-008 PostgreSQL checkpoint adapter
- UOW-009 parser-stage retry reprocessor
- UOW-010 AWS CDK storage/checkpoint/queue resources
- future SQS/DLQ platform worker integration

No external service is required for current default integration tests.
