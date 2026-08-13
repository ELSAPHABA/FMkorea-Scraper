# Domain Entities - UOW-010 AWS CDK Infrastructure IaC

## Overview

These entities describe the functional model for AWS CDK infrastructure around scraper workers. They are infrastructure-domain concepts, not scraper runtime models.

## `CdkApp`

Root CDK application.

Attributes:

- `app_name`
- `environment`
- `account`
- `region`
- `shared_infra_stack`
- `worker_stacks`

Rules:

- Owns stack assembly.
- Loads environment-specific configuration.
- Does not contain scraper parser or runtime logic.

## `EnvironmentConfig`

Environment-specific deployment configuration.

Attributes:

- `environment`: `dev`, `staging`, or `prod`
- `account`
- `region`
- `name_prefix`
- `removal_policy_profile`
- `log_retention_days`
- `tags`

Rules:

- `prod` defaults to retaining stateful resources.
- Environment appears in stack and resource names.
- Secrets are referenced by name/ARN, not stored as plaintext values.

## `SharedInfraStackSpec`

Definition of reusable infrastructure shared by one or more scraper workers.

Attributes:

- `stack_name`
- `environment_config`
- `network`
- `object_storage`
- `checkpoint_database`
- `shared_secrets`
- `logging_defaults`

Relationships:

- produces references consumed by `WorkerStackSpec`
- owns stateful resources unless imported

Rules:

- Does not know scraper query/parser logic.
- Provides stable outputs for worker stacks.

## `WorkerStackSpec`

Reusable worker deployment pattern for a scraper container.

Attributes:

- `stack_name`
- `site_id`
- `image`
- `task`
- `runtime_environment`
- `secret_bindings`
- `schedule`
- `observability`

Relationships:

- consumes `SharedInfraReference`
- creates `FargateTaskSpec`
- may create `ScheduleSpec`

Rules:

- One worker stack pattern can be reused for many scraper images.
- Worker stack remains one-shot task oriented.
- Central platform concepts are not modeled here.

## `SharedInfraReference`

Reference object passed from shared infra to worker stacks.

Attributes:

- `s3_bucket_name`
- `s3_endpoint_url`
- `database_secret_name`
- `database_endpoint`
- `vpc_id`
- `subnet_ids`
- `security_group_ids`
- `log_group_prefix`

Rules:

- May come from stacks created in the same CDK app or imported external resources.
- Must not expose plaintext secret values.

## `ObjectStorageSpec`

S3 object storage contract for scraper outputs.

Attributes:

- `bucket_name`
- `prefix_strategy`
- `force_path_style`
- `region`
- `retention_policy`
- `encryption_enabled`

Rules:

- Must support existing output paths such as `outputs/<job_id>/<run_id>/...`.
- Must allow future transition to `outputs/<environment>/<site_id>/<job_id>/<run_id>/...`.
- Must not encode scraper-specific API/query logic.

## `CheckpointDatabaseSpec`

RDS PostgreSQL checkpoint storage contract.

Attributes:

- `engine`
- `database_name`
- `endpoint`
- `port`
- `credentials_secret`
- `backup_retention`
- `removal_policy`

Rules:

- Engine is PostgreSQL-compatible.
- Credentials are stored in Secrets Manager.
- Worker tasks connect through `DATABASE_URL` or an equivalent composed secret.

## `SecretBinding`

Mapping from a secret manager value to an ECS task secret.

Attributes:

- `env_name`
- `secret_name`
- `json_field`
- `required`

Examples:

- `DATABASE_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `FMKOREA_PROXY_PW`

Rules:

- Secret values are never written to CDK source.
- Secret values are never written as plaintext CloudFormation parameters.

## `RuntimeEnvironmentSpec`

Non-secret environment variables injected into the worker container.

Attributes:

- `job_id`
- `resume`
- `s3_bucket`
- `s3_region`
- `s3_force_path_style`
- `s3_prefix`
- `user_agent_file`
- `user_agent_rotate_every`
- `request_interval_seconds`
- `post_worker_count`
- `site_specific_env`

Rules:

- Must match the existing container environment variable contract.
- Should stay generic enough for future scraper workers.

## `ImageReference`

Container image selected for a worker.

Attributes:

- `repository_uri`
- `tag`
- `digest`

Rules:

- CDK references the image.
- CDK does not build the image by default.
- CI or operator flow owns build and push.

## `FargateTaskSpec`

One-shot ECS Fargate task definition.

Attributes:

- `cpu`
- `memory`
- `ephemeral_storage`
- `task_role`
- `execution_role`
- `container_command`
- `environment`
- `secrets`
- `log_group`

Rules:

- Runs one Job per invocation.
- Uses the existing container entrypoint.
- Requires outbound network access.
- Requires no inbound listener by default.

## `WorkerInvocationSpec`

Manual invocation configuration for a worker task.

Attributes:

- `cluster_name`
- `task_definition`
- `subnet_selection`
- `security_groups`
- `command`
- `environment_overrides`

Rules:

- Supports `run`, `retry-parser-failures`, and default container command shapes.
- Must allow explicit `JOB_ID`.
- Does not implement central queue polling.

## `ScheduleSpec`

Optional EventBridge schedule for a worker.

Attributes:

- `enabled`
- `schedule_expression`
- `command`
- `environment_overrides`
- `job_id_strategy`

Rules:

- Uses the same worker task definition.
- Disabled by default unless configured.
- Does not replace manual task run support.

## `ObservabilitySpec`

Logging and minimal alarm contract.

Attributes:

- `log_group_name`
- `retention_days`
- `failure_alarm_enabled`
- `alarm_topic_arn`

Rules:

- Captures stdout/stderr.
- Provides task failure signal.
- Does not require dashboard or custom metric by default.

## `NetworkSpec`

VPC, subnet, and security group model.

Attributes:

- `vpc_id`
- `rds_subnet_type`
- `worker_subnet_type`
- `assign_public_ip`
- `rds_security_group`
- `worker_security_group`

Rules:

- RDS is private.
- Worker default is public subnet with outbound access and no inbound application ports.
- Security group allows worker-to-RDS PostgreSQL only.

## `SynthVerificationSpec`

Verification contract for the CDK app.

Attributes:

- `synth_command`
- `template_test_command`
- `expected_resource_types`
- `snapshot_paths`

Rules:

- Must run without AWS deployment.
- Must validate expected resource categories.
- Deploy smoke tests are optional later gates.
