# Business Logic Model - UOW-010 AWS CDK Infrastructure IaC

## Purpose

UOW-010 defines an AWS CDK infrastructure standard for scraper workers.

It is not a scraper-specific CDK stack and it is not the future centralized multi-community management platform. It provides:

- shared infrastructure that multiple scraper workers can reuse
- a reusable worker stack pattern for one-shot scraper containers
- deploy/synth documentation and verification boundaries

## Scope

Included:

- shared S3 bucket for scraper output objects
- RDS PostgreSQL for checkpoint storage
- Secrets Manager references for credentials and runtime secrets
- CloudWatch logs and basic task failure alarm
- ECS Fargate one-shot task pattern
- optional EventBridge schedule using the same task definition
- environment separation for dev/staging/prod
- Python CDK v2 project under `infra/cdk`

Excluded:

- scraper runtime behavior changes
- parser/query/source option logic
- central Job queue
- worker registry
- dashboard
- cross-community orchestration platform
- CAPTCHA bypass or production incident automation

## High-Level Model

```text
Operator or Schedule
        |
        v
Worker Stack Pattern
        |
        v
ECS Fargate Task Definition
        |
        v
Scraper Container
        |
        +--> S3 bucket outputs/<job_id>/<run_id>/...
        |
        +--> RDS PostgreSQL checkpoint table
        |
        +--> CloudWatch Logs
        |
        +--> Secrets Manager values injected as task secrets
```

Shared infrastructure is separated from worker infrastructure:

```text
Shared Infra Stack
  - VPC
  - S3 bucket
  - RDS PostgreSQL
  - shared secrets
  - shared log defaults

Worker Stack Pattern
  - ECS cluster/task definition
  - per-worker env
  - per-worker image URI/tag
  - task role permissions
  - optional EventBridge schedule
```

## Main Functional Flows

### 1. Shared Infra Synth

Inputs:

- environment name: `dev`, `staging`, or `prod`
- AWS account and region
- resource name prefix
- removal policy profile

Flow:

1. CDK app loads environment configuration.
2. Shared infra stack creates or references the VPC boundary.
3. Shared infra stack creates S3 output bucket.
4. Shared infra stack creates RDS PostgreSQL checkpoint database.
5. Shared infra stack creates required secret placeholders or secret references.
6. CDK synth emits a CloudFormation template.

Output:

- shared resource ARNs, names, endpoints, and secret reference names for worker stacks

### 2. Worker Stack Synth

Inputs:

- `site_id`
- `image_uri`
- worker command arguments
- runtime environment variables
- shared infra outputs or imported names
- optional schedule expression

Flow:

1. Worker stack resolves shared infra references.
2. Worker stack creates an ECS Fargate task definition.
3. Worker stack maps non-sensitive configuration to task environment variables.
4. Worker stack maps sensitive values through Secrets Manager task secrets.
5. Worker stack grants task role access to S3, Secrets Manager, CloudWatch Logs, and RDS connectivity as needed.
6. If configured, EventBridge schedule starts the task with the same task definition.
7. CDK synth emits a CloudFormation template.

Output:

- reusable Fargate task definition and optional scheduled execution rule

### 3. Manual Worker Job Run

Inputs:

- task definition
- container command, for example `run ...`, `retry-parser-failures ...`, or default entrypoint
- `JOB_ID`
- runtime options

Flow:

1. Operator or CI invokes ECS RunTask.
2. Fargate starts one scraper container.
3. Container reads injected environment variables and CLI args.
4. Container writes outputs to S3 and checkpoints to PostgreSQL.
5. Container exits with the UOW-008 exit code contract.
6. CloudWatch captures stdout/stderr.

Output:

- S3 `posts.jsonl`, `failures.jsonl`, `report.json`, media objects
- PostgreSQL checkpoint rows
- CloudWatch task logs

### 4. Scheduled Worker Job Run

Inputs:

- EventBridge schedule expression
- fixed command/env template for the worker
- per-schedule `JOB_ID` strategy

Flow:

1. EventBridge starts the Fargate task.
2. Task runs the configured one-shot command.
3. Outputs, checkpoints, and logs follow the manual run flow.
4. Failed task state triggers the basic alarm contract.

Output:

- same as manual worker Job run

### 5. Retry Worker Job Run

Inputs:

- `retry-parser-failures` command
- explicit `s3://bucket/key` failure refs
- optional existing `posts.jsonl` object refs

Flow:

1. Operator starts the worker task with `retry-parser-failures`.
2. Container reuses the existing parser failure retry path.
3. Retry results are written to a new run.
4. Original failure objects remain unchanged.

Output:

- retry run output and `report.metadata.parser_failure_retry`

## Data Flow

```text
CDK context/parameters
  -> Stack config objects
  -> CloudFormation resources
  -> ECS task env/secrets
  -> Existing scraper container contract
  -> S3/RDS/CloudWatch outputs
```

UOW-010 only maps infrastructure configuration to existing runtime contracts. It does not add new scraper source types or change `JobConfig`.

## Environment Flow

Each environment uses the same CDK app with different configuration:

```text
infra/cdk
  app.py
  stacks/
    shared_infra_stack.py
    worker_stack.py
  config/
    dev.yaml
    staging.yaml
    prod.yaml
```

Functional differences by environment:

- `dev`: destructive cleanup allowed for non-critical resources
- `staging`: production-like names, lower capacity
- `prod`: retain critical data resources by default

## Verification Flow

Default verification:

1. install CDK app dependencies
2. run unit/template tests
3. run `cdk synth`
4. inspect synthesized template for expected resource categories

No default verification requires live deployment to an AWS account.

## Handoff To Later Stages

NFR Requirements should define:

- cost constraints
- retention requirements
- RDS size and backup requirements
- IAM least privilege depth
- alarm thresholds

Infrastructure Design should define:

- exact CDK construct choices
- resource names
- IAM policy statements
- subnet/security group layout
- secret names
- synth/deploy commands
