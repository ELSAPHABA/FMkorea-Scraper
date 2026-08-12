# Integration Test Instructions - UOW-003 Search And Link Collection

## Purpose

Validate that UOW-003 works with existing UOW-001 models and the UOW-002 HTTP boundary without owning network, queue, checkpoint, or storage infrastructure.

## Current Integration Coverage

### UOW-001 Model Integration

- `DirectPostSource`
- `BoardListSource`
- `BoardSearchSource`
- `IntegratedSearchSource`
- `DeepSearchSource`
- `NoKeywordRangeSource`
- `RealtimeKeywordSource`
- `RealtimeAllSource`
- `RangeFilter`
- `PostCandidate`
- `SearchPage`
- `IntegratedSearchPage`

### UOW-002 HTTP Boundary Integration

UOW-003 collector tests use a fake HTTP object with:

```python
async def get(url: str) -> str
```

The production path accepts UOW-002 `HttpClient.get()` results because `LinkCollectorService` reads the `.text` attribute from response objects.

## Run Integration-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_collect_service.py tests\test_api_ports.py
```

## Deferred Integration Tests

The following require later units:

- UOW-004 post detail parsing from `PostCandidate`
- UOW-005 queue insertion and checkpoint lifecycle
- UOW-006 JSONL/Garage/PostgreSQL storage interaction
- UOW-007 CLI command wiring
- UOW-008 container/MCP adapter integration

No external service is required for current integration tests.
