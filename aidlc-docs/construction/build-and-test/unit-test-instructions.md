# Unit Test Execution - UOW-004 Post Detail And Content Parsing

## Run Unit Tests

### 1. Execute All Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

Expected result:

```text
72 passed
```

### 2. Execute UOW-004 Tests Only

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_parse_service.py tests\test_parse_properties.py
```

Expected result:

```text
10 passed
```

## Covered UOW-004 Test Areas

- scoped detail metadata parsing
- ordered content block extraction
- image, FMKorea video, YouTube, X/Twitter, link, attachment, and unknown embed behavior
- attachment query metadata parsing
- media summary and per-post dedupe
- comment parsing with BEST status, badges, reactions, and score
- bounded extra comment page fetch through injected HTTP
- duplicate comment ID suppression
- required metadata failure
- safe parser warning redaction
- property-based parser invariants

## Live Network Tests

Default unit tests do not access FMKorea.

No live smoke test was executed in this Build and Test stage.
