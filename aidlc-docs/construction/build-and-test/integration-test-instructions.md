# Integration Test Instructions

## Scope

UOW-001 has no HTTP client, parser, storage adapter, worker runtime, CLI, container, database, or MCP server implementation. Full integration tests are therefore not applicable yet.

## Covered Interaction Checks

The current test suite still verifies the integration-facing contracts that later units depend on:

- public async API placeholders are import-safe
- `run_job` can delegate to an injected runner
- port protocols are structurally usable by fake implementations
- package import creates no `.env`, `user-agents.txt`, output directory, terminal prompt, or network side effect

## Current Result

- **Integration runtime tests**: N/A for UOW-001
- **Contract interaction checks**: PASS through `tests/test_api_ports.py`

## Future Integration Tests

Later UOWs should add integration tests when these concrete adapters exist:

- HTTP client plus URL builder
- board/search parser plus post candidate collector
- post/comment parser plus `PostResult`
- local/S3 output storage
- checkpoint persistence
- CLI and wizard flow
- container and MCP entrypoints
