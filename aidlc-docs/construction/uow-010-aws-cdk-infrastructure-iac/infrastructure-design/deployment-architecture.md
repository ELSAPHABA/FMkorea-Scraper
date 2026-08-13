# Deployment Architecture - UOW-010 AWS CDK Infrastructure IaC

## Architecture Overview

```text
Operator / CI
  |
  | cdk synth / cdk deploy
  v
AWS CDK App: infra/cdk
  |
  +-- SharedInfraStack
  |     +-- VPC
  |     +-- S3 output bucket
  |     +-- RDS PostgreSQL
  |     +-- ECS cluster
  |     +-- shared references
  |
  +-- WorkerStack
        +-- Fargate task definition
        +-- task role / execution role
        +-- CloudWatch Log Group
        +-- optional EventBridge schedule
        +-- failure signal rule/alarm/optional SNS target
```

The scraper container image is built and pushed outside CDK. CDK only references the image URI and tag.

## Runtime Flow

Manual run:

```text
Operator / CI
  |
  | ecs run-task
  v
ECS Fargate one-shot task
  |
  +-- reads non-secret environment
  +-- reads ECS-injected secrets
  +-- writes JSONL/report/media to S3
  +-- writes checkpoint state to RDS PostgreSQL
  +-- writes stdout/stderr to CloudWatch Logs
  |
  v
task exits with existing container exit-code contract
```

Scheduled run:

```text
EventBridge schedule
  |
  v
same ECS Fargate task definition
  |
  v
same output, checkpoint, and log flow
```

## Network Architecture

```text
Internet
  |
Public subnet
  |
ECS Fargate worker task with public IP
  |
Security group: outbound allowed, no inbound app ports
  |
Security group rule: PostgreSQL port only
  |
Private/isolated DB subnet
  |
RDS PostgreSQL
```

Default properties:

- NAT Gateway count is `0`
- worker uses public subnet outbound access
- RDS is private and not publicly accessible
- only worker security group can reach RDS PostgreSQL port

## Storage Architecture

S3 stores scraper run outputs:

```text
outputs/{environment}/{site_id}/{job_id}/{run_id}/posts.jsonl
outputs/{environment}/{site_id}/{job_id}/{run_id}/failures.jsonl
outputs/{environment}/{site_id}/{job_id}/{run_id}/report.json
outputs/{environment}/{site_id}/{job_id}/{run_id}/media/...
```

Rules:

- one shared bucket per environment
- lifecycle deletion disabled by default
- block public access enabled
- server-side encryption enabled
- prod versioning can be enabled through config

RDS stores checkpoint data for worker jobs:

```text
worker task -> DATABASE_URL secret -> RDS PostgreSQL
```

## Secret Flow

```text
Secrets Manager
  |
  | ECS secret injection
  v
worker container environment
```

Rules:

- YAML contains secret names or ARNs only
- CDK source contains no secret values
- synthesized CloudFormation templates contain no plaintext secrets
- task logs must not print secret values

## Stack Deployment Order

1. Install local CDK Python dependencies.
2. Run CDK tests.
3. Run `cdk synth -c env=dev`.
4. Deploy shared infra stack.
5. Deploy worker stack.
6. Build and push scraper image outside CDK when needed.
7. Run worker manually through ECS RunTask or let EventBridge schedule invoke it.

The exact deploy command names are decided during Code Generation after stack IDs are fixed.

## Default Verification Gate

Default local gate:

```powershell
cd infra/cdk
python -m pytest tests
cdk synth -c env=dev
```

This gate validates templates only. It does not require AWS credentials that can deploy resources.

Optional live gate:

```powershell
cd infra/cdk
cdk deploy -c env=dev
cdk destroy -c env=dev
```

Live deploy/destroy smoke is optional and must not run by default.

## Environment Deployment Model

| Environment | Default Use | Stateful Policy | Cost Posture |
|---|---|---|---|
| `dev` | local/CI synth and disposable AWS smoke | stateful destroy requires explicit opt-in | lowest |
| `staging` | production-like validation | conservative retention unless configured | low |
| `prod` | real operation | retain stateful resources by default | configurable hardening |

Environment config controls account, region, names, backup retention, RDS sizing, versioning, and schedules.

## Failure Signal Architecture

```text
ECS task state change
  |
  v
EventBridge rule
  |
  +-- CloudWatch alarm or matched-event metric
  |
  +-- optional SNS target
```

Failure signal scope:

- detects stopped/failed one-shot worker tasks
- does not parse scraper report contents
- does not implement incident automation
- does not create dashboards

## Shared Infrastructure Scope

UOW-010 does not need a third shared infrastructure artifact.

Shared infrastructure is implemented as `SharedInfraStack` and documented in:

- `infrastructure-design.md`
- `deployment-architecture.md`

Future centralized platform work may reuse the same shared infra references and worker stack inputs, but no platform queue, registry, or dashboard is created in this unit.
