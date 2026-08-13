# Logical Components - UOW-010 AWS CDK Infrastructure IaC

This document defines logical components for the UOW-010 implementation.

## Component Overview

| Component | Responsibility |
|---|---|
| `CdkAppEntrypoint` | loads environment config and wires shared/worker stacks |
| `EnvironmentConfigLoader` | reads and validates non-secret environment YAML |
| `EnvironmentConfig` | carries account, region, names, tags, removal profile, and defaults |
| `NamingAndTaggingHelper` | creates deterministic names and standard tags |
| `SharedInfraStack` | defines shared VPC, S3, RDS, common secrets, and exported references |
| `SharedInfraRefs` | carries shared resource references into worker stacks |
| `WorkerStack` | defines reusable ECS Fargate one-shot worker infrastructure |
| `WorkerTaskDefinitionBuilder` | maps image, command, env, secrets, logs, CPU/memory inputs to ECS task definition |
| `SecretReferenceResolver` | imports Secrets Manager references and maps them to ECS container secrets |
| `WorkerIamPolicyBuilder` | grants scoped S3, Secrets Manager, logs, and related task permissions |
| `NetworkSecurityModel` | creates public outbound worker networking and private/isolated RDS access rules |
| `ObservabilityConstruct` | creates log group, retention, and task failure alarm/hook |
| `TemplateVerificationTests` | validates synthesized templates without AWS deploy access |

## `CdkAppEntrypoint`

Location:

- `infra/cdk/app.py`

Responsibilities:

- read selected environment from CDK context or CLI context
- call `EnvironmentConfigLoader`
- instantiate `SharedInfraStack`
- instantiate one or more `WorkerStack` instances from config
- apply common tags

Must not:

- import scraper runtime modules
- build Docker images
- read plaintext secrets
- start scraper jobs

## `EnvironmentConfigLoader`

Location:

- `infra/cdk/stacks/config.py`

Responsibilities:

- load `infra/cdk/config/{env}.yaml`
- validate required fields
- reject plaintext secret-like values
- normalize optional fields to defaults
- build dataclass config objects

Validation targets:

- environment identity
- AWS account and region
- name prefix
- stateful removal policy profile
- S3/RDS defaults
- worker image, command, env, schedule, and secret refs

## `EnvironmentConfig`

Responsibilities:

- carry non-secret environment settings
- expose environment-aware removal policy decisions
- expose log retention and backup retention defaults
- expose tagging values

Must not contain:

- proxy passwords
- database passwords
- S3 access key secret values
- cookies
- raw credentials

## `NamingAndTaggingHelper`

Location:

- `infra/cdk/stacks/naming.py`

Responsibilities:

- create stable names from prefix, environment, site ID, and resource purpose
- keep names short enough for AWS service limits
- apply common tags consistently
- allow explicit physical name override for stateful resources

Tests should cover deterministic output and basic length/sanitization behavior.

## `SharedInfraStack`

Location:

- `infra/cdk/stacks/shared_infra_stack.py`

Responsibilities:

- create or import VPC boundary
- create S3 output bucket
- create RDS PostgreSQL checkpoint database
- create or import common secret references
- expose `SharedInfraRefs`

Default resource behavior:

- S3 block public access and encryption enabled
- S3 lifecycle deletion disabled
- RDS private/isolated subnet placement
- RDS storage encryption enabled
- prod stateful retention by default

Must not:

- know source-specific scraper query rules
- create SQS queues or platform registry tables
- deploy Garage or SeaweedFS

## `SharedInfraRefs`

Responsibilities:

- pass bucket name/ARN
- pass database endpoint/security group/secret refs
- pass VPC and subnet refs
- pass common log defaults

Rules:

- no plaintext secret values
- stable enough for worker stacks to consume
- compatible with later imported shared infrastructure

## `WorkerStack`

Location:

- `infra/cdk/stacks/worker_stack.py`

Responsibilities:

- define ECS cluster or consume shared cluster if later configured
- define one-shot Fargate task definition
- define task and execution roles
- configure container image URI/tag
- configure command and non-secret env vars
- inject secrets
- attach log group
- optionally define EventBridge schedule
- attach basic task failure alarm/hook

Must not:

- implement scraper runtime behavior
- implement central queue consumption
- create always-on services by default
- expose inbound application ports

## `WorkerTaskDefinitionBuilder`

Responsibilities:

- configure Fargate CPU, memory, and optional ephemeral storage from config
- attach container image reference
- map command list and environment variables
- map ECS secrets from `SecretReferenceResolver`
- use CloudWatch log driver

Exact CPU, memory, and storage defaults are decided in Infrastructure Design.

## `SecretReferenceResolver`

Responsibilities:

- import existing Secrets Manager secrets by name or ARN
- map optional JSON fields to ECS secret values
- pass RDS generated secret reference into worker configuration
- fail config validation when a required secret ref is missing

Must not:

- receive plaintext secret values
- log secret values
- synthesize secret values into CloudFormation templates

## `WorkerIamPolicyBuilder`

Responsibilities:

- grant S3 access to configured bucket/prefix
- grant read access to declared Secrets Manager secrets
- attach only required task permissions
- avoid broad task role wildcards

Implementation rule:

- prefer CDK grant helpers
- use inline policy statements only for gaps

## `NetworkSecurityModel`

Responsibilities:

- create public subnets for outbound worker tasks
- create private/isolated DB subnets for RDS
- keep NAT Gateway disabled by default
- create worker and database security groups
- allow only worker security group to reach RDS PostgreSQL port

Must not:

- make RDS publicly accessible
- open worker inbound application ports
- create NAT Gateway by default

## `ObservabilityConstruct`

Responsibilities:

- create explicit CloudWatch Log Group
- apply environment-aware retention
- route ECS task logs to the log group
- define task failure alarm or notification hook from ECS task state changes

Deferred:

- dashboards
- custom scraper metrics
- production incident automation

## `TemplateVerificationTests`

Location:

- `infra/cdk/tests/`

Responsibilities:

- synthesize stacks in tests
- assert expected resource categories exist
- assert no plaintext secret values are embedded
- assert S3 public access block and encryption
- assert RDS is not publicly accessible
- assert NAT Gateway is absent in the default config
- assert worker task has no inbound listener
- assert task role permissions are scoped to declared resources where feasible
- assert prod config retains stateful resources

Default tests must not call AWS APIs or require deployment credentials.
