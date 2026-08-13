# NFR Design Patterns - UOW-010 AWS CDK Infrastructure IaC

This document translates UOW-010 NFR requirements into CDK implementation patterns.

## Confirmed Design Answers

| Question | Answer | Design Pattern |
|---|---|---|
| Q1 | A | Keep a small Python CDK v2 app under `infra/cdk` and do not import scraper runtime code. |
| Q2 | A | Split `SharedInfraStack` and `WorkerStack`; use small shared config/props dataclasses. |
| Q3 | A | Load `config/{env}.yaml` and validate it with dataclass-based checks. |
| Q4 | A | Use deterministic naming and standard tags from `name_prefix`, `environment`, and `site_id`. |
| Q5 | A | Use environment removal policy profiles and explicit stateful destroy opt-in. |
| Q6 | A | Harden S3 and RDS defaults without forcing expensive production settings on every env. |
| Q7 | A | Inject runtime secrets through Secrets Manager references and ECS container secrets. |
| Q8 | A | Use CDK grants plus small inline policies for least-privilege worker task roles. |
| Q9 | A | Use no-NAT VPC defaults: public outbound worker, private/isolated RDS, SG-limited DB access. |
| Q10 | A | Use CloudWatch Logs, task failure alarm, pytest CDK assertions, and `cdk synth`. |

No follow-up question is required.

## CDK Project Layout Pattern

First implementation uses a small CDK-only layout:

```text
infra/cdk/
  requirements.txt
  app.py
  stacks/
    shared_infra_stack.py
    worker_stack.py
    config.py
    naming.py
  config/
    dev.yaml
    staging.yaml
    prod.yaml
  tests/
    test_config.py
    test_shared_infra_stack.py
    test_worker_stack.py
```

Rules:

- CDK code must not import `src/fmkorea_scraper`.
- Runtime contracts are represented as container command strings, environment variables, secret names, and output paths.
- CDK synth and template tests must not require the scraper package to be installed.
- Do not add plugin registries, worker factories, or a platform SDK in this unit.

## Stack Boundary Pattern

Use two stack types:

- `SharedInfraStack`: owns or imports VPC, S3 bucket, RDS PostgreSQL, common secret references, and shared log defaults.
- `WorkerStack`: owns ECS cluster/task definition, container env/secrets, task IAM, optional EventBridge schedule, CloudWatch log group, and task failure alarm.

Small dataclasses carry props between the app and stacks:

- `EnvironmentConfig`
- `SharedInfraConfig`
- `WorkerConfig`
- `SharedInfraRefs`

Do not create base-stack inheritance or construct factories until repeated workers prove the need.

## Environment Config Pattern

Environment config is loaded from:

```text
infra/cdk/config/{env}.yaml
```

Validation rules:

- required identity fields must exist: environment, account, region, name prefix
- secret values are forbidden; only secret names or ARNs are allowed
- prod must default stateful resources to retain
- dev may allow disposable cleanup, but stateful destroy requires explicit opt-in
- worker configs must include `site_id`, image reference, command, non-secret env, and secret refs

The loader should stay small and dataclass-based. A YAML parser is enough; do not add a separate validation framework just for CDK config.

## Naming And Tagging Pattern

Use a deterministic helper to build resource names from:

- `name_prefix`
- `environment`
- `site_id` where worker-specific
- short resource purpose

Apply standard tags:

- `Project`
- `Environment`
- `ManagedBy`
- `SiteId` for worker-specific resources

Allow explicit name overrides for stateful resources such as S3 buckets and RDS instances, because those names may need stable retention across stack changes.

## Stateful Resource Safety Pattern

Stateful resource deletion must be guarded by environment policy:

- prod stateful resources default to retain
- dev can destroy disposable resources
- S3/RDS destroy requires explicit `allow_destroy_stateful`
- lifecycle deletion is off by default
- retry/failure/report objects remain preserved by default

Template tests must verify that prod-like config does not synthesize destructive stateful removal policies.

## Storage And Database Hardening Pattern

S3 default pattern:

- block public access
- server-side encryption enabled
- lifecycle rules disabled by default
- bucket/prefix permissions scoped to worker task role

RDS default pattern:

- PostgreSQL engine
- storage encryption enabled
- private or isolated subnet placement
- credentials from Secrets Manager
- environment-configurable backup retention
- production-configurable Multi-AZ

Exact storage size, engine version, instance class, and backup days are Infrastructure Design decisions.

## Secrets Injection Pattern

Config stores secret references only:

- secret name
- secret ARN
- optional JSON field name

CDK resolves those references and injects them as ECS container secrets.

Examples:

- `DATABASE_URL`
- S3-compatible access credentials if needed
- proxy credentials

Rules:

- no plaintext secret values in YAML, CDK source, synthesized template, or logs
- no automatic rotation by default
- RDS-generated secret may be passed through directly
- operator-managed secrets may be imported by name or ARN

## IAM Policy Pattern

Worker task role permissions are scoped by need:

- S3 read/write only to the configured bucket and output prefix
- `secretsmanager:GetSecretValue` only for declared secrets
- CloudWatch Logs permissions only where required for task logging
- RDS connectivity through security group rules, not broad database admin permissions

Use CDK grant helpers first. Add small inline policies only where grants are not precise enough.

Avoid broad `*` resource permissions in task roles. AWS managed policies may remain on the ECS execution role where CDK/ECS normally requires them.

## Network Pattern

Default VPC pattern:

```text
Internet
  |
Public subnet: ECS Fargate worker with public IP, outbound-only
  |
Security group rule: worker -> RDS on PostgreSQL port only
  |
Private/isolated DB subnet: RDS PostgreSQL
```

Rules:

- NAT Gateway count is `0` by default
- worker containers expose no inbound application ports
- RDS is not publicly accessible
- RDS security group accepts PostgreSQL traffic only from worker security group
- private-worker plus NAT mode is deferred until a measured security/operations need appears

## Observability And Verification Pattern

Observability defaults:

- explicit CloudWatch Log Group
- environment-aware log retention
- ECS task failure visibility through EventBridge task state change and CloudWatch alarm or notification hook

Default verification:

- pytest CDK assertions
- `cdk synth`
- template checks for expected resource types
- template checks that secret values are not embedded as plaintext
- template checks for S3 public access block and encryption
- template checks for RDS private placement/security group intent where feasible
- template checks for task role scoped permissions

Live AWS deploy/destroy smoke tests are optional and not part of the default gate.

## Compliance Check

| Requirement Area | Design Compliance |
|---|---|
| Security | secret references only, ECS secret injection, private RDS, no inbound worker ports, scoped IAM |
| Resiliency | prod retain defaults, backups configurable, preserved S3 outputs/failures/reports |
| Cost | one-shot Fargate, NAT Gateway disabled by default, optional schedule, small configurable RDS |
| Maintainability | small Python CDK layout, separate stacks, no runtime package imports |
| Verification | CDK assertions plus `cdk synth`, optional live smoke only |
| PBT | pure naming/config helpers can be property-tested if useful; infrastructure confidence mainly comes from template assertions |
