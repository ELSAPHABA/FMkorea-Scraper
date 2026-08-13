# Tech Stack Decisions - UOW-010 AWS CDK Infrastructure IaC

## Accepted Stack

| Area | Decision | Reason |
| --- | --- | --- |
| IaC framework | AWS CDK v2 | Matches the requested AWS CDK direction and keeps infrastructure in code. |
| CDK language | Python | Matches the scraper project language and avoids a separate TypeScript toolchain. |
| CDK location | `infra/cdk` | Keeps deployment code separate from scraper runtime code. |
| Compute | ECS Fargate one-shot task | Fits batch-style scraping without an always-on service. |
| Container image source | ECR image URI/tag input | Keeps image build/push outside CDK and allows later scraper images to reuse the stack. |
| Manual execution | ECS RunTask-compatible task definition | Supports operator/CI-triggered one-shot jobs. |
| Optional schedule | EventBridge rule | Covers fixed schedules without introducing a central scheduler platform. |
| Object storage | AWS S3 | AWS-native target for JSONL, reports, failures, and media. |
| Checkpoint database | RDS PostgreSQL | AWS-managed PostgreSQL target for checkpoint state. |
| Secret storage | AWS Secrets Manager | Supports ECS secret injection without plaintext config. |
| Logs | CloudWatch Logs | Native ECS logging target. |
| Basic alerting | CloudWatch alarm for task failure | Small default visibility without custom dashboards. |
| Network baseline | RDS private subnet, worker public subnet outbound-only | Avoids NAT Gateway default cost while keeping RDS private. |
| IAM baseline | Least-privilege task role | Limits shared-infra blast radius across scraper workers. |
| Environment config | `infra/cdk/config/{env}.yaml` plus CDK context | Keeps non-secret config reviewable and environment-aware. |
| CDK tests | `cdk synth` plus template-level tests | Verifies generated infrastructure without requiring AWS deploy access. |

## Deferred Or Rejected Choices

| Choice | Status | Reason |
| --- | --- | --- |
| EKS or Kubernetes | Deferred | Too much platform overhead for the current one-shot worker need. |
| AWS Batch | Deferred | ECS Fargate is enough for the current container execution model. |
| Always-on ECS service | Rejected for default | Scraping jobs are one-shot and should not incur idle service cost. |
| NAT Gateway by default | Rejected for default | Cost is not justified for the initial baseline. |
| SQS queue and worker registry | Deferred | Belongs to the later centralized management platform. |
| CDK Docker image build | Rejected for default | `cdk synth` should not depend on local Docker build state. |
| Default S3 lifecycle deletion | Rejected for default | Preserved outputs and failures are needed for retry and audit. |
| Secret auto-rotation | Deferred | Useful later, but it adds operational coupling and validation work. |
| CloudWatch dashboard/custom metrics | Deferred | Basic logs and task failure alarm are enough until real operations data exists. |
| Live deploy/destroy smoke in default gate | Deferred | CI should not require AWS account permissions by default. |
| Garage or SeaweedFS deployment in AWS CDK | Out of scope | Existing S3-compatible adapter remains the non-AWS storage boundary. |

## Required CDK Inputs

- `environment`: deployment environment such as `dev`, `staging`, or `prod`
- `account` and `region`
- `site_id`
- `image_uri`
- `image_tag` or image digest
- `container_command`
- non-secret runtime environment variables
- Secrets Manager secret names or ARNs
- optional EventBridge schedule expression
- shared infrastructure references when using imported resources

## Technology Constraints For Later Design

- Exact CPU, memory, storage size, log retention days, RDS class, and backup retention values are decided in Infrastructure Design.
- Environment config files must not contain secret values.
- Task definitions must use ECS secret injection for sensitive values.
- Shared infrastructure and worker stacks must remain separable.
- Future platform support is limited to reusable inputs and stack boundaries in this unit.
