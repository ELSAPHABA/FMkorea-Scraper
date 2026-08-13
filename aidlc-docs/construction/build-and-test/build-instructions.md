# Build Instructions - UOW-009 Parser Failure Retry Reprocessor

## Wheel Build

```powershell
py -3.12 -m pip wheel . --no-deps -w dist
```

Result:

```text
Successfully built fmkorea-scraper
```

Artifact:

- `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
- size: `87472` bytes
- SHA256: `B22590BA2332B664C36D5F1AEFA8C4557D50F2030BDC7FB97BAE23C548D00BCA`

## Docker Build

```powershell
docker build -t fmkorea-scraper:uow-009-build-test .
```

Result:

```text
PASS
```

Image:

- `fmkorea-scraper:uow-009-build-test`
- image id: `sha256:1dfa421b147a03ab3f360075e4b3e79b642c689e6fd89e46cd4e47d550c1b422`
- entrypoint: `["/app/docker-entrypoint.sh"]`

## Container Validation Smoke

```powershell
docker run --rm fmkorea-scraper:uow-009-build-test run
docker run --rm fmkorea-scraper:uow-009-build-test retry-parser-failures --failure-path s3://bucket/failures.jsonl
```

Both commands return safe validation JSON and exit with code `2` when required env is missing.

## Dependency Check

```powershell
docker run --rm --entrypoint python fmkorea-scraper:uow-009-build-test -m pip check
```

Result:

```text
No broken requirements found.
```
