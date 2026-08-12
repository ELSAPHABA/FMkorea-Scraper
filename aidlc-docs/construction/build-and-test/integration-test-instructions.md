# Integration Test Instructions - UOW-004 Post Detail And Content Parsing

## Purpose

Validate that UOW-004 turns UOW-001 post candidates/requests into `PostResult` objects while using only the injected UOW-002 HTTP boundary.

## Current Integration Coverage

### UOW-001 Model Integration

- `PostCandidate`
- `PostRequest`
- `PostResult`
- `PostContent`
- content block models
- `Attachment`
- `MediaItem`
- `Comment`

### UOW-002 HTTP Boundary Integration

UOW-004 parser tests use a fake HTTP object with:

```python
async def get(url: str) -> str
```

The production path accepts UOW-002 `HttpClient.get()` results because `PostDetailService` reads the `.text` attribute from response objects.

### Comment Page Integration

When `ParserOptions(max_comment_pages=N)` is set, `PostDetailService.parse()` discovers comment page links, fetches them sequentially through the injected HTTP client, and dedupes duplicate comment IDs.

## Run Integration-Relevant Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_parse_service.py tests\test_api_ports.py
```

## Deferred Integration Tests

The following require later units:

- UOW-005 queue insertion and checkpoint lifecycle
- UOW-006 JSONL/Garage/PostgreSQL storage interaction
- UOW-007 CLI command wiring
- UOW-008 container/MCP adapter integration

No external service is required for current integration tests.
