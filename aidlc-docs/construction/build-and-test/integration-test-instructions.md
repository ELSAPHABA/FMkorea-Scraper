# Integration Test Instructions - UOW-002 HTTP Runtime Policy

## Scope

UOW-002 has a concrete HTTP runtime, but no search parser, post parser, storage adapter, worker runtime, CLI, container, database, or MCP server implementation yet.

Therefore, integration coverage is limited to fake transport HTTP behavior inside the package.

## Covered Interaction Checks

The current test suite verifies:

- `HttpClient` can run through `httpx.MockTransport`
- retry attempts pass through the shared limiter
- proxy config resolves explicit options before `.env`
- `DotenvProxyLoader` reads allowlisted `FMKOREA_PROXY_*` keys without mutating process env
- User-Agent rotation clears in-memory cookies
- cancellation closes the underlying async client
- public package imports stay side-effect free

## Current Result

- **Integration runtime tests**: PASS through fake transport tests
- **Live network tests**: not executed by default
- **Contract interaction checks**: PASS through `tests/test_api_ports.py`

## Optional Live Smoke

Live smoke remains opt-in only:

```powershell
$env:FMKOREA_LIVE_SMOKE_ENABLED='true'
python -m pytest -m live_smoke
```

No live smoke test is currently required for UOW-002 Build and Test.

## Future Integration Tests

Later UOWs should add integration tests when these concrete adapters exist:

- HTTP client plus FMKorea URL builder
- board/search parser plus post candidate collector
- post/comment parser plus `PostResult`
- local/S3 output storage
- checkpoint persistence
- CLI and wizard flow
- container and MCP entrypoints
