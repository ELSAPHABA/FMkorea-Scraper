# Security Test Instructions - UOW-010 AWS CDK Infrastructure IaC

## Security Checks

Run CDK template tests:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
& (Join-Path $venv 'Scripts\python.exe') -m pytest infra\cdk\tests -q --tb=short
```

Verified result:

```text
11 passed in 36.86s
```

Covered invariants:

- plaintext secret-like values are rejected from CDK YAML config
- ECS container secrets are injected through Secrets Manager references
- secret values are not embedded in synthesized templates
- S3 bucket blocks public access and uses encryption
- RDS is not public
- worker security group has no inbound app ports
- worker-to-RDS ingress is limited to PostgreSQL port 5432
- worker S3 permissions are scoped to `outputs/{environment}/{site_id}`
- prod-like stateful resources retain by default

## Dependency Checks

Clean application venv:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-app-venv'
& (Join-Path $venv 'Scripts\python.exe') -m pip check
```

Verified result:

```text
No broken requirements found.
```

Docker image:

```powershell
docker run --rm --entrypoint python fmkorea-scraper:uow-010-build-test -m pip check
```

Verified result:

```text
No broken requirements found.
```

## Environment Note

Host-level `py -3.12 -m pip check` reported unrelated global package conflicts involving Google/gRPC/protobuf, Selenium typing extensions, and `update/style`. Clean venv and Docker checks passed, so the project dependency gate is pass.
