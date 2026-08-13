# Business Rules - UOW-010 AWS CDK Infrastructure IaC

## Stack Boundary Rules

- UOW-010 must create a reusable AWS CDK infrastructure standard, not a one-off scraper-specific stack.
- UOW-010 must not implement the future centralized multi-community management platform.
- Shared infrastructure and worker stacks must be separated.
- Shared infrastructure may be reused by multiple scraper workers.
- Worker stack inputs must identify the specific scraper through `site_id`, image reference, command, runtime environment, and optional schedule.
- Scraper API query rules, parser rules, and source-specific options must stay outside CDK stack logic.

## Shared Infrastructure Rules

- Shared infra stack creates AWS S3 for object output by default.
- Shared infra stack creates RDS PostgreSQL for checkpoint storage by default.
- Shared infra stack must preserve the existing S3-compatible and PostgreSQL runtime contracts.
- S3 object keys must remain compatible with the shared storage contract.
- PostgreSQL must be reachable from Fargate tasks.
- Shared infra stack must expose outputs or importable references needed by worker stacks.
- Garage and SeaweedFS are not deployed in UOW-010 AWS CDK; they remain non-AWS-compatible alternatives through the existing S3-compatible adapter boundary.

## Worker Execution Rules

- Worker execution target is ECS Fargate.
- The worker runs as one Fargate task per Job invocation.
- The worker task must use the existing container entrypoint contract from UOW-008.
- The worker stack must support manual task execution.
- The worker stack may define an optional EventBridge schedule using the same task definition.
- Central queue consumption, worker registry, dashboard, and scheduler platform features are out of scope.
- Worker tasks must not expose inbound application ports by default.
- Worker task success and failure follow the UOW-008 exit code contract.

## Container Image Rules

- Worker stack receives an ECR repository/image URI and image tag as input.
- CDK synth and deploy must not require local Docker build by default.
- Image build/push is handled outside CDK by manual commands or CI.
- The worker stack must not assume a single hard-coded scraper image.
- Future scraper workers should be able to reuse the same worker stack pattern by changing image and runtime inputs.

## Configuration Rules

- Sensitive values must come from Secrets Manager references.
- CDK source code must not contain plaintext proxy passwords, database passwords, S3 access keys, or other runtime secrets.
- CloudFormation templates must not contain plaintext secret values.
- Non-sensitive settings may come from CDK context, config files, or stack parameters.
- Task definition environment variables must match the existing container runtime contract:
  - `DATABASE_URL`
  - `S3_ENDPOINT_URL`
  - `S3_BUCKET`
  - `S3_ACCESS_KEY_ID`
  - `S3_SECRET_ACCESS_KEY`
  - `S3_REGION`
  - `S3_FORCE_PATH_STYLE`
  - `S3_PREFIX`
  - `RESUME`
  - `JOB_ID`
  - `FMKOREA_USER_AGENT_FILE`
  - `FMKOREA_USER_AGENT_ROTATE_EVERY`
  - `FMKOREA_REALTIME_*`
  - `FMKOREA_PROXY_HOST`
  - `FMKOREA_PROXY_ID`
  - `FMKOREA_PROXY_PW`
- Secret-backed task variables must use ECS secret injection.

## Environment Separation Rules

- The same CDK app must support `dev`, `staging`, and `prod`.
- Environment name must affect stack names and resource names.
- `dev` may use destructive removal policies for disposable resources.
- `prod` must retain stateful resources by default.
- Production and non-production resources must not share mutable data stores unless explicitly configured.
- Operators must be able to identify the environment from resource names and tags.

## Network Rules

- RDS runs in private subnets.
- Fargate tasks may run in public subnets with public IP for outbound-only scraping.
- No inbound internet access to worker containers is required by default.
- Security groups must allow worker-to-RDS connectivity only on the PostgreSQL port.
- If a later NFR requires all compute in private subnets, NAT Gateway/private subnet mode can be added in Infrastructure Design.

## Observability Rules

- Worker task logs must go to CloudWatch Logs.
- Log groups must have environment-aware retention settings.
- A basic task failure alarm must be available.
- Default observability should focus on task status, exit code, and stdout/stderr.
- Dashboards, custom metrics, and platform-wide worker registry views are deferred until operational data justifies them.

## Storage And Checkpoint Mapping Rules

- S3 bucket name and endpoint configuration must be injected so existing S3 output code can run unchanged.
- AWS S3 deployments may omit custom endpoint configuration if the existing adapter supports AWS default endpoint behavior.
- RDS credentials must be provided through a secret-derived `DATABASE_URL` or equivalent secret composition defined later.
- CDK must not require scraper code to understand AWS resource ARNs directly.
- Existing retry outputs and `parser_failure_retry` report metadata remain stored in normal run outputs.

## Schedule Rules

- EventBridge schedule is optional.
- Scheduled tasks must use the same task definition as manual tasks unless a later design proves separate task definitions are needed.
- A schedule must define a deterministic command/env template.
- Schedule configuration must not create a central Job platform or dynamic worker registry in this unit.

## Verification Rules

- Default verification must include `cdk synth`.
- Default verification should include template-level tests or snapshot checks.
- Default verification must not require deploying resources to AWS.
- Deploy smoke tests are optional and belong to later Build and Test gates.
- Synth output must be inspectable for expected resource categories:
  - S3 bucket
  - RDS PostgreSQL
  - ECS task definition
  - task role
  - CloudWatch log group
  - Secrets Manager references
  - optional EventBridge rule

## Out Of Scope Rules

- UOW-010 does not change `fmkorea_scraper` runtime package behavior.
- UOW-010 does not implement new CLI commands.
- UOW-010 does not implement Kubernetes/EKS deployment.
- UOW-010 does not implement SQS queue workers.
- UOW-010 does not implement a dashboard.
- UOW-010 does not implement a multi-community worker registry.
- UOW-010 does not deploy Garage or SeaweedFS inside AWS.
- UOW-010 does not solve CAPTCHA or alter rate-limit policy.
