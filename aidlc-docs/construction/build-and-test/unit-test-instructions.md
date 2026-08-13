# Unit Test Execution - UOW-007 CLI Adapter

## Run Unit Tests

### Focused CLI Tests

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_cli_adapter.py tests\test_cli_properties.py -q --tb=short
```

Latest result:

```text
21 passed
```

### Full Default Suite

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q --tb=short
```

Latest result:

```text
118 passed, 2 skipped in 20.71s
```

## Covered UOW-007 Behavior

- CLI parser accepts confirmed subcommands
- CLI source options map to existing UOW-001 source models
- realtime env validation enforces exactly one termination condition
- `resume` and `retry-parser-failures` request builders validate input
- fake runner execution avoids live network
- CLI-generated `run_id` reaches the runner
- runtime builder passes the same `run_id` to `StorageFactory`
- `import-user-agents` rejects invalid input without overwriting
- Proxy `.env` update preserves unrelated lines
- wizard answers map to the same command dict shape as argparse
- safe error output redacts unsafe details
- Ctrl+C handler requests `JobRunner.stop(StopReason.MANUAL_STOP)`
- importing `fmkorea_scraper.adapters.cli` has no runtime side effects

## Property-Based Tests

Tool: Hypothesis

Covered properties:

- direct-post command mapping preserves URL lists
- realtime keyword env maps to duration termination source
- source alias normalization accepts both hyphen and underscore forms

## Failure Handling

If tests fail:

1. inspect the first failing test in pytest output
2. fix the shared builder/runtime boundary instead of patching individual callers
3. rerun focused CLI tests
4. rerun the full default suite
