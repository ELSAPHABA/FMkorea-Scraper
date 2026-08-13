# Code Generation Plan - UOW-010 AWS CDK Infrastructure IaC

이 문서는 `UOW-010 AWS CDK Infrastructure IaC` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Created At**: 2026-08-13T13:58:17Z
- **Plan Approved At**: 2026-08-13T14:15:56Z
- **Code Generated At**: 2026-08-13T14:15:56Z
- **Plan Status**: Code Generated - Review Required

## Unit Context

- **Unit**: UOW-010 AWS CDK Infrastructure IaC
- **Project Type**: Greenfield Python package with completed scraper runtime/container/MCP/retry implementation
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `infra/cdk/`
- **Documentation Location**: `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/`
- **Primary Role**: AWS CDK v2로 shared infra stack과 reusable worker stack pattern을 만든다.
- **Supporting Role**: 후속 scraper worker와 미래 통합 플랫폼이 재사용할 수 있는 AWS 배포 표준을 제공한다.

## Dependencies

| Dependency | Status |
|---|---|
| UOW-006 Output And Storage | Implemented and approved |
| UOW-008 Container, MCP, And Test Harness | Implemented and approved |
| UOW-009 Parser Failure Retry Reprocessor | Implemented and approved |
| UOW-010 Functional Design | Approved |
| UOW-010 NFR Requirements | Approved |
| UOW-010 NFR Design | Approved |
| UOW-010 Infrastructure Design | Approved |

## Scope

UOW-010 implements:

- Python CDK v2 app under `infra/cdk`
- CDK-only code with no `fmkorea_scraper` runtime imports
- environment YAML config for `dev`, `staging`, and `prod`
- small dataclass-based config loader and validator
- deterministic naming/tagging helper
- `SharedInfraStack` for VPC, S3, RDS PostgreSQL, and ECS cluster
- `WorkerStack` for Fargate task definition, IAM, secrets, log group, optional schedule, and failure signal
- no-NAT default network
- public outbound worker task placement
- private/isolated RDS placement
- S3 block public access and S3-managed encryption
- RDS storage encryption and generated/imported credential references
- ECS secret injection from Secrets Manager references
- ECR/generic image URI support through config
- account-agnostic default synth with optional config-account mode
- CDK assertion tests for config, naming, shared infra, and worker stack
- code public-contract and summary docs

UOW-010 does not implement:

- scraper runtime behavior changes
- new CLI/MCP/container commands
- Docker image build/push automation
- live AWS deploy/destroy smoke as default gate
- EKS/Kubernetes
- SQS queue or worker registry
- centralized multi-community management platform
- dashboard or custom scraper metrics
- existing VPC import in the first implementation

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| CDK app entrypoint | `infra/cdk/app.py` |
| CDK CLI config | `infra/cdk/cdk.json` |
| CDK dependencies | `infra/cdk/requirements.txt` |
| CDK stack package | `infra/cdk/stacks/` |
| environment config | `infra/cdk/config/dev.yaml`, `staging.yaml`, `prod.yaml` |
| CDK tests | `infra/cdk/tests/` |
| code public contract docs | `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/public-contracts.md` |
| code summary docs | `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/code-generation-summary.md` |

## Step Sequence

### Step 1. CDK Project Skeleton

- [x] Create `infra/cdk/requirements.txt`.
- [x] Create `infra/cdk/cdk.json`.
- [x] Create `infra/cdk/app.py`.
- [x] Create `infra/cdk/stacks/__init__.py`.
- [x] Ensure CDK code does not import `src/fmkorea_scraper`.

### Step 2. Environment Config Files

- [x] Create `infra/cdk/config/dev.yaml`.
- [x] Create `infra/cdk/config/staging.yaml`.
- [x] Create `infra/cdk/config/prod.yaml`.
- [x] Use `site_id: fmkorea`.
- [x] Use FMKorea worker image examples such as `fmkorea-scraper`.
- [x] Keep secret values out of YAML; only names/ARNs are allowed.

### Step 3. Config Loader

- [x] Create `infra/cdk/stacks/config.py`.
- [x] Implement dataclasses for AWS, naming, removal policy, network, S3, RDS, ECS, worker, and secret refs.
- [x] Load `config/{env}.yaml`.
- [x] Validate required sections and fields.
- [x] Reject plaintext secret-like values.
- [x] Provide defaults for non-prod/prod-safe config.

### Step 4. Naming And Tagging

- [x] Create `infra/cdk/stacks/naming.py`.
- [x] Implement deterministic name helper.
- [x] Implement standard tags: `Project`, `Environment`, `ManagedBy`, and worker `SiteId`.
- [x] Keep names AWS-safe and length-limited.

### Step 5. Shared Infra Stack

- [x] Create `infra/cdk/stacks/shared_infra_stack.py`.
- [x] Create no-NAT VPC with public worker and private/isolated DB subnets.
- [x] Create environment shared S3 output bucket.
- [x] Apply S3 block public access and encryption.
- [x] Create RDS PostgreSQL with private placement and encryption.
- [x] Create ECS cluster.
- [x] Expose `SharedInfraRefs` for worker stacks.

### Step 6. Worker Stack

- [x] Create `infra/cdk/stacks/worker_stack.py`.
- [x] Create one Fargate task definition per configured worker.
- [x] Reference container image URI/tag from YAML.
- [x] Map non-secret runtime env from YAML plus generated S3 values.
- [x] Inject Secrets Manager refs as ECS secrets.
- [x] Create task/execution roles.
- [x] Scope S3, Secrets Manager, and log permissions.
- [x] Create worker security group with no inbound app ports.
- [x] Allow worker security group to reach RDS PostgreSQL only.
- [x] Create worker CloudWatch Log Group.
- [x] Create optional EventBridge schedule.
- [x] Create ECS task failure EventBridge/CloudWatch signal.

### Step 7. CDK Tests

- [x] Create `infra/cdk/tests/conftest.py`.
- [x] Create `test_config.py`.
- [x] Create `test_naming.py`.
- [x] Create `test_shared_infra_stack.py`.
- [x] Create `test_worker_stack.py`.
- [x] Assert expected S3/RDS/ECS/Secrets/EventBridge resources.
- [x] Assert no NAT Gateway in default config.
- [x] Assert RDS is not publicly accessible.
- [x] Assert secret values are not embedded in templates.
- [x] Assert prod-like stateful resources retain.

### Step 8. Ignore Generated CDK Artifacts

- [x] Add or update `.gitignore` entries for `infra/cdk/cdk.out/` and `infra/cdk/cdk.context.json`.
- [x] Do not commit synth output or Python cache files.

### Step 9. Documentation

- [x] Create `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/code-generation-summary.md`.
- [x] Record generated files, config contract, stack contract, verification commands, and deferred boundaries.

### Step 10. Validation

- [x] Run CDK unit/template tests.
- [x] Run `cdk synth -c env=dev` when local CDK CLI/dependencies are available.
- [x] CDK CLI/dependencies were available; no dependency blocker to record.
- [x] Default project test subset not required; generated changes are isolated to `infra/cdk`, `.gitignore`, and AI-DLC docs.
- [x] Record validation results in code generation summary.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| AWS CDK infrastructure | creates `infra/cdk` app and stack definitions |
| Shared storage/checkpoint | maps AWS S3 and RDS PostgreSQL to existing container contracts |
| Container worker | deploys existing worker image as ECS Fargate one-shot task |
| Security | Secrets Manager injection, scoped IAM, private RDS, no inbound worker ports |
| Cost | no NAT Gateway default, one-shot Fargate, small configurable RDS |
| Future platform | keeps reusable worker stack inputs without implementing queue/registry/dashboard |

## Completion Criteria

- [x] `infra/cdk` project exists and is importable by its tests.
- [x] Environment YAML files exist for `dev`, `staging`, and `prod`.
- [x] CDK app can synthesize shared and worker stacks for `env=dev`.
- [x] Worker config uses `site_id=fmkorea`.
- [x] CDK code does not import scraper runtime modules.
- [x] Default design creates no NAT Gateway.
- [x] S3 bucket blocks public access and uses encryption.
- [x] RDS is not public and lives in DB subnets.
- [x] Worker secrets use ECS secret injection.
- [x] Template tests cover security/cost invariants.
- [x] Code docs exist under `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/code/`.

## Approval Gate

UOW-010 Code Generation이 완료되었습니다.

승인 후 UOW-010 Build and Test 단계로 진행한다.
