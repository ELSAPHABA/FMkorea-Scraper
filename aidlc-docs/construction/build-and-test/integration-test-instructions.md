# Integration Test Instructions - UOW-010 AWS CDK Infrastructure IaC

## Scope

UOW-010 integration validation is local-only. It verifies that the generated CDK stacks integrate with the existing container runtime contract without deploying to AWS.

Live AWS deployment, ECS RunTask smoke, RDS connection smoke, and S3 object-write smoke are deferred until real AWS account, image registry, and Secrets Manager values are available.

## CDK Synth Integration

Run:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
$env:PATH = (Join-Path $venv 'Scripts') + ';' + $env:PATH
cd infra/cdk
cdk synth -c env=dev
```

Verified result:

```text
Successfully synthesized to D:\HongDev\ELSAPHABA\FMkorea-Scraper\infra\cdk\cdk.out
Supply a stack id (community-scraper-dev-shared, community-scraper-dev-fmkorea-worker) to display its template.
```

## Container Contract Smoke

Build:

```powershell
docker build -t fmkorea-scraper:uow-010-build-test .
```

Check dependency integrity inside the built image:

```powershell
docker run --rm --entrypoint python fmkorea-scraper:uow-010-build-test -m pip check
```

Verified result:

```text
No broken requirements found.
```

Check that container commands fail safely when required environment variables are missing:

```powershell
docker run --rm fmkorea-scraper:uow-010-build-test run
docker run --rm fmkorea-scraper:uow-010-build-test retry-parser-failures --failure-path s3://bucket/failures.jsonl
```

Verified result:

```text
exit code 2 with safe validation JSON for missing DATABASE_URL
```

This confirms the CDK-provided secret contract is still required before live task execution.

## Deferred Live Integration

Before live ECS execution:

- publish the worker image to the configured ECR repository
- create referenced Secrets Manager values for `DATABASE_URL`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY`
- update `infra/cdk/config/{env}.yaml` placeholder account/image values
- bootstrap the target AWS account for CDK
- run `cdk deploy -c env=<env> -c use_config_account=true`
