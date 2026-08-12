# Integration Test Instructions - UOW-006 Output And Storage

## Purpose

Validate that UOW-006 stores UOW-001/UOW-004 model outputs through the UOW-001 storage ports without owning JobRunner orchestration or external infrastructure.

## Current Integration Coverage

### UOW-001 Model And Port Integration

- `PostResult`
- `FailureRecord`
- `JobReport`
- `StoredObjectRef`
- `MediaItem`
- `Checkpoint`
- `StorageConfig`
- `S3StorageConfig`
- `OutputStorePort`
- `FailureStorePort`
- `MediaStorePort`
- `CheckpointStorePort`

### UOW-004 Parser Output Compatibility

`LocalOutputStore.append_post()` and `S3ObjectStore.append_post()` accept completed `PostResult` objects, preserving nested fields:

- `content`
- `attachments`
- `media`
- `comments`
- `metadata`

### S3-Compatible Boundary

UOW-006 fake S3 tests validate object key and spool behavior without requiring Garage:

- `put_object(Bucket=..., Key=..., Body=...)`
- same object key after each JSONL append
- local spool file as implementation detail

## Run Integration-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_outputs_storage.py tests\test_api_ports.py
```

## Deferred Integration Tests

The following require later units:

- UOW-005 queue and checkpoint advancement lifecycle
- UOW-007 CLI storage option wiring
- UOW-008 container env injection
- UOW-008 PostgreSQL checkpoint adapter
- UOW-008 MCP adapter integration
- UOW-010 AWS CDK storage/checkpoint resources

No external service is required for current default integration tests.
