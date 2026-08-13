# Unit Test Instructions - UOW-010 AWS CDK Infrastructure IaC

## Application Test Suite

Run from the repository root:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m pytest tests -q --tb=short
```

Verified result:

```text
151 passed, 3 skipped in 18.47s
```

## Application Compile Check

```powershell
$env:PYTHONPATH='src'
py -3.12 -m compileall -q src tests
```

Verified result: pass.

## CDK Template Tests

Run from the repository root:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
& (Join-Path $venv 'Scripts\python.exe') -m pytest infra\cdk\tests -q --tb=short
```

Verified result:

```text
11 passed in 36.86s
```

The CDK tests cover config validation, deterministic naming, no-NAT shared infrastructure, private RDS placement, S3 hardening, ECS worker task wiring, Secrets Manager injection, and worker failure signal resources.

## CDK Compile Check

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
& (Join-Path $venv 'Scripts\python.exe') -m compileall -q infra\cdk
```

Verified result: pass.

## Smoke Checks

```powershell
$env:PYTHONPATH='src'
py -3.12 -c "import fmkorea_scraper, fmkorea_scraper.adapters.cli, fmkorea_scraper.adapters.container, fmkorea_scraper.adapters.mcp; print('ok')"
py -3.12 -m fmkorea_scraper.adapters.cli --help
```

Verified result: import returned `ok`; CLI help printed successfully.
