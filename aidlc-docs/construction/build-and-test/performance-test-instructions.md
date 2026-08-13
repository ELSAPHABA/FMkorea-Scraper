# Performance Test Instructions - UOW-010 AWS CDK Infrastructure IaC

## Scope

UOW-010 does not add scraper throughput logic. Performance validation is limited to infrastructure shape and build-time checks.

## Verified Cost/Capacity Defaults

The CDK template tests verify:

- no NAT Gateway in default config
- one Fargate worker task definition per configured worker
- configurable ECS CPU and memory values
- private/isolated RDS placement
- bounded S3 prefix permissions per environment/site worker

## Commands

Run the CDK template test suite:

```powershell
$venv = Join-Path $env:TEMP 'fmkorea-uow010-cdk-venv'
& (Join-Path $venv 'Scripts\python.exe') -m pytest infra\cdk\tests -q --tb=short
```

Verified result:

```text
11 passed in 36.86s
```

## Deferred Performance Tests

Live performance tests require deployed AWS resources and real workload input:

- ECS task cold-start timing
- scraper throughput per task CPU/memory setting
- RDS checkpoint write latency
- S3 output write latency
- EventBridge scheduled run behavior

These remain operations/deployment validation, not local Build and Test gates.
