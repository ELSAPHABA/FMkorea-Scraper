# Unit Test Execution - UOW-003 Search And Link Collection

## Run Unit Tests

### 1. Execute All Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests
```

Expected result:

```text
62 passed
```

### 2. Execute UOW-003 Tests Only

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_collect_urls.py tests\test_collect_parsers.py tests\test_collect_service.py tests\test_collect_properties.py
```

Expected result:

```text
17 passed
```

## Covered UOW-003 Test Areas

- direct post URL normalization
- board list/search URL builder query handling
- integrated search URL builder page clamp and safe label behavior
- BeautifulSoup board page parser fixture extraction
- BeautifulSoup integrated search parser fixture extraction
- malformed row/item failure isolation
- fake HTTP collector service flow
- range filter document bound behavior
- candidate and board dedupe idempotence
- property-based URL/policy invariants

## Live Network Tests

Default unit tests do not access FMKorea.

Live smoke remains optional and must be explicitly enabled with:

```powershell
$env:FMKOREA_LIVE_SMOKE_ENABLED='true'
```

No live smoke test was executed in this Build and Test stage.
