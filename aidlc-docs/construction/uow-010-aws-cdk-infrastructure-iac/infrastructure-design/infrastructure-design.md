# Infrastructure Design - UOW-010 AWS CDK Infrastructure IaC

## Purpose

UOW-010 implements an AWS CDK baseline for scraper worker containers.

The implementation must create AWS-native shared infrastructure and a reusable worker stack pattern without introducing the future centralized management platform.

## Confirmed Infrastructure Answers

| Question | Answer | Infrastructure Decision |
|---|---|---|
| Q1 | A | Use minimal Python CDK dependencies and rely on externally installed CDK CLI. |
| Q2 | A | Use one environment YAML per env with `aws`, `naming`, `removal_policy`, `network`, `s3`, `rds`, `ecs`, and `workers` sections. |
| Q3 | A | Create a new default VPC with `max_azs=2`, no NAT Gateway, public worker subnets, and private/isolated DB subnets. |
| Q4 | A | Create one shared S3 output bucket per environment. |
| Q5 | A | Create one shared RDS PostgreSQL instance per environment with low-cost non-prod defaults and prod hardening options. |
| Q6 | A | Create ECS cluster in shared infra stack; create Fargate task definitions in worker stacks. |
| Q7 | A | Read non-secret env from YAML and inject sensitive values through Secrets Manager ECS secrets. |
| Q8 | A | Define scoped task IAM and security groups in CDK. |
| Q9 | A | Use CloudWatch Log Groups and EventBridge ECS task-state failure signal, with optional SNS target. |
| Q10 | A | Verify with `python -m pytest infra/cdk/tests` and `cdk synth -c env=dev`; generate two infrastructure artifacts. |

No follow-up question is required.

## CDK Project Structure

The implementation adds a CDK-only project:

```text
infra/cdk/
  requirements.txt
  app.py
  stacks/
    __init__.py
    config.py
    naming.py
    shared_infra_stack.py
    worker_stack.py
  config/
    dev.yaml
    staging.yaml
    prod.yaml
  tests/
    test_config.py
    test_naming.py
    test_shared_infra_stack.py
    test_worker_stack.py
```

`infra/cdk/requirements.txt` contains only:

- `aws-cdk-lib>=2,<3`
- `constructs>=10,<11`
- `PyYAML>=6,<7`
- `pytest`

CDK CLI installation is documented, not automated by this unit.

## Environment Config Shape

Each environment uses:

```text
infra/cdk/config/{env}.yaml
```

Required top-level sections:

```yaml
aws:
  account: "123456789012"
  region: "ap-northeast-2"

naming:
  project: "community-scraper"
  name_prefix: "community-scraper"

removal_policy:
  profile: "dev"
  allow_destroy_stateful: false

network:
  max_azs: 2
  nat_gateways: 0

s3:
  bucket_name: null
  versioned: false

rds:
  database_name: "scraper"
  engine_version: null
  allocated_storage_gb: 20
  instance_class: "burstable-low-cost"
  multi_az: false
  backup_retention_days: 1

ecs:
  cpu: 512
  memory_mib: 1024
  ephemeral_storage_gib: null

workers:
  - site_id: "fmkorea"
    image_uri: "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/fmkorea-scraper"
    image_tag: "latest"
    command: ["run"]
    schedule: null
    environment:
      JOB_ID: "manual"
      RESUME: "false"
      S3_FORCE_PATH_STYLE: "false"
    secrets:
      database_url:
        name: "community-scraper/dev/database-url"
      proxy_url:
        name: null
```

Config rules:

- secret values are forbidden
- secret references may be names or ARNs
- worker entries may be extended for later scrapers without changing stack code
- prod config defaults to retained stateful resources
- dev config can permit disposable cleanup, but stateful destroy still requires explicit opt-in

## Stack Mapping

| Stack | Owns | Does Not Own |
|---|---|---|
| `SharedInfraStack` | VPC, S3 bucket, RDS PostgreSQL, ECS cluster, common refs | scraper runtime code, source query logic, SQS queue, platform registry |
| `WorkerStack` | Fargate task definition, task/execution roles, log group, optional EventBridge schedule, failure signal | Docker image build, always-on service, parser logic, centralized scheduler |

`SharedInfraStack` exports or passes a `SharedInfraRefs` object into worker stacks.

No third shared-infrastructure document is required. Shared infrastructure is the main subject of this UOW and is covered by this document plus `deployment-architecture.md`.

## VPC And Subnet Design

Default VPC:

- created by CDK
- `max_azs=2`
- `nat_gateways=0`
- public subnets for ECS Fargate workers
- private or isolated DB subnets for RDS

Network rules:

- worker tasks receive public IP for outbound scraping
- worker containers expose no inbound application ports
- RDS is not publicly accessible
- RDS security group accepts PostgreSQL traffic only from worker security group
- existing VPC import is deferred

## S3 Bucket Design

One shared output bucket is created per environment.

Defaults:

- block public access
- S3 managed server-side encryption
- lifecycle rules disabled
- versioning disabled by default
- prod versioning configurable
- stateful removal policy follows environment profile

Output prefix contract:

```text
outputs/{environment}/{site_id}/{job_id}/{run_id}/...
```

The runtime adapter may keep writing current key shapes as long as the configured base output path maps to this prefix.

## RDS PostgreSQL Design

One shared PostgreSQL instance is created per environment.

Defaults:

- PostgreSQL engine
- engine version configurable
- storage encryption enabled
- dev/staging single-AZ by default
- dev/staging allocated storage starts at 20 GiB
- dev/staging use a small low-cost instance class
- short non-prod backup retention
- prod Multi-AZ, backup retention, and instance class configurable
- credentials stored in Secrets Manager
- private or isolated subnet placement

The generated or imported database secret is passed to worker tasks through an ECS secret mapping, normally as `DATABASE_URL` or equivalent composed connection string.

## ECS Worker Design

Shared infra stack:

- creates one ECS cluster per environment

Worker stack:

- creates one Fargate task definition per worker entry
- uses image URI/tag supplied in config
- creates task role and execution role
- maps non-secret env vars
- injects Secrets Manager values as ECS secrets
- attaches a worker-specific CloudWatch Log Group
- optionally creates an EventBridge schedule

The stack does not create an always-on ECS service by default.

Manual runs use ECS RunTask against the generated task definition.

## Runtime Environment Mapping

CDK composes runtime variables from shared infra and worker config.

Non-secret examples:

- `JOB_ID`
- `RESUME`
- `S3_BUCKET`
- `S3_REGION`
- `S3_FORCE_PATH_STYLE`
- `S3_ENDPOINT_URL` when needed
- scraper runtime tuning values such as request interval and worker count

Secret examples:

- `DATABASE_URL`
- proxy credentials
- S3-compatible credentials if a non-AWS endpoint is later imported

Secrets must be ECS container secrets, not plaintext task environment values.

## IAM And Security Group Design

Worker task role:

- S3 read/write to configured bucket and output prefix
- Secrets Manager read only for declared secrets
- log permissions required by ECS logging
- no broad S3 or Secrets Manager wildcard by default

Execution role:

- uses standard ECS image pull/logging permissions where required

Security groups:

- worker security group has no inbound application rule
- RDS security group allows inbound PostgreSQL only from worker security group
- RDS is not public

## Observability Design

Each worker stack creates:

- explicit CloudWatch Log Group
- environment-aware retention
- EventBridge rule for ECS task-state failure detection
- CloudWatch alarm or optional SNS notification target based on configured failure signal

Deferred:

- dashboards
- custom scraper metrics
- central worker registry view
- production incident automation

## Verification Design

Default verification commands:

```powershell
cd infra/cdk
python -m pytest tests
cdk synth -c env=dev
```

Template tests must assert:

- S3 bucket exists
- S3 public access is blocked
- S3 encryption is enabled
- RDS instance exists
- RDS is not publicly accessible
- default template has no NAT Gateway
- ECS task definition exists
- worker task has no inbound listener
- Secrets Manager references are used without plaintext secret values
- EventBridge schedule/failure resources exist when configured
- prod-like config retains stateful resources

Default verification does not deploy to AWS.

## Out Of Scope

- EKS/Kubernetes
- SQS job queue
- centralized management platform
- dashboard
- CDK-managed Docker image build/push
- default deploy/destroy smoke
- scraper runtime code changes
- external VPC import support in first implementation
