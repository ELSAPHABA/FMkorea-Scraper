# Build Instructions - UOW-010 AWS CDK Infrastructure IaC

## Prerequisites

- Python 3.12 for the application package checks
- Python 3.12 virtual environment for `infra/cdk`
- Docker 29.7.2 or compatible for container build checks
- AWS CDK CLI 2.1135.1 or compatible for `cdk synth`

No AWS credentials are required for the default local checks. Live deploy is not part of this Build and Test stage.

## Application Package Build

Run from the repository root:

```powershell
py -3.12 -m pip wheel . --no-deps -w dist
```

Expected artifact:

```text
dist/fmkorea_scraper-0.1.0-py3-none-any.whl
```

Verified result:

```text
size=87472
sha256=B22590BA2332B664C36D5F1AEFA8C4557D50F2030BDC7FB97BAE23C548D00BCA
```

## CDK Dependency Setup

Use a separate venv for the CDK app:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
py -3.12 -m venv $venv
& (Join-Path $venv 'Scripts\python.exe') -m pip install -r infra\cdk\requirements.txt
```

## CDK Synth

Run with the CDK venv first on `PATH`:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
$env:PATH = (Join-Path $venv 'Scripts') + ';' + $env:PATH
cd infra/cdk
cdk synth -c env=dev
```

Expected stack IDs:

```text
community-scraper-dev-shared
community-scraper-dev-fmkorea-worker
```

`cdk synth` may report unconfigured CDK feature flags. This is informational and did not fail the verified build.

## Docker Build

Run from the repository root:

```powershell
docker build -t fmkorea-scraper:uow-010-build-test .
```

Verified image:

```text
sha256:ed8b487f929bfa6193e8f6741ec0065896494eb58aa6f900ee5b799fc4be318f
```

Verified entrypoint:

```text
["/app/docker-entrypoint.sh"]
```

## Generated Artifacts

- `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
- `infra/cdk/cdk.out/` generated locally by `cdk synth` and ignored by git
- Docker image `fmkorea-scraper:uow-010-build-test`

## Troubleshooting

- If `cdk synth` cannot import `aws_cdk`, ensure the CDK venv `Scripts` directory is first on `PATH`.
- If Docker build fails on line endings, confirm `docker-entrypoint.sh` is committed with LF endings via `.gitattributes`.
- If host `pip check` reports unrelated global package conflicts, rerun dependency validation in a clean venv.
