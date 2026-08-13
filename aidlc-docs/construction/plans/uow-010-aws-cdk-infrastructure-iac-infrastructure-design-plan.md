# Infrastructure Design Plan - UOW-010 AWS CDK Infrastructure IaC

이 계획은 `UOW-010 AWS CDK Infrastructure IaC`의 논리 컴포넌트를 실제 AWS CDK 리소스, 설정 파일, 테스트, 실행 명령으로 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-010 AWS CDK Infrastructure IaC
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: `infra/cdk` Python CDK v2 project, environment YAML config, shared infra stack, worker stack, VPC/S3/RDS/ECS/Secrets/CloudWatch resources, least-privilege IAM, no-NAT default network, CDK assertion tests, synth commands
- **Likely Infrastructure Scope**: AWS-native S3/RDS/ECS Fargate/Secrets Manager/CloudWatch/EventBridge resources created by CDK, with image build/push and live deploy smoke outside the default gate
- **Out Of Scope**: EKS/Kubernetes, SQS worker queue, centralized multi-community management platform, dashboard, CDK-driven Docker image build, runtime scraper code changes, default live AWS deploy/destroy smoke

## Infrastructure Design 작업 체크리스트

- [x] UOW-010 Functional Design 승인 확인
- [x] UOW-010 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 매핑 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Review Result

- Q1-Q10은 모두 A로 확정되었습니다.
- 답변 간 충돌은 없습니다.
- follow-up 질문은 필요하지 않습니다.
- 확정 방향은 최소 Python CDK dependency, 단일 environment YAML 구조, 새 no-NAT VPC, 환경별 shared S3 bucket, 환경별 shared RDS PostgreSQL, shared ECS cluster와 worker별 Fargate task definition, YAML non-secret env와 Secrets Manager ECS secret injection, scoped IAM/security group, CloudWatch LogGroup과 EventBridge task failure signal, pytest CDK assertions + `cdk synth` 검증입니다.
- 별도 shared infrastructure 산출물은 만들지 않습니다. UOW-010의 shared infrastructure는 `infrastructure-design.md`와 `deployment-architecture.md` 안에서 직접 다룹니다.
- 산출물 생성 후 UOW-010 Infrastructure Design Review 단계에서 사용자 승인을 대기합니다.

## Infrastructure Design Questions

### Question 1. CDK Dependency And Tooling Boundary

`infra/cdk`의 의존성과 실행 도구는 어떻게 구성할까요?

A) (권장) `requirements.txt`에 `aws-cdk-lib>=2,<3`, `constructs>=10,<11`, `PyYAML>=6,<7`, `pytest`만 둔다. CDK CLI는 로컬/CI에 설치된 `cdk` 명령을 사용하고, Node/CDK CLI 설치 자동화는 문서화만 한다.

추천 사유: Python CDK 구현에 필요한 최소 의존성입니다. CDK CLI까지 프로젝트가 설치/관리하려고 하면 범위가 커집니다.

B) CDK CLI 설치까지 npm wrapper/script로 자동화한다.

C) lock file과 정확한 patch 버전을 이번 설계에서 모두 고정한다.

X) 기타

[Answer]: A

### Question 2. Environment Config File Shape

환경별 YAML 설정은 어떤 구조로 둘까요?

A) (권장) `aws`, `naming`, `removal_policy`, `network`, `s3`, `rds`, `ecs`, `workers` 섹션을 둔다. secret은 값이 아니라 name/ARN만 받으며, dev/staging/prod 예시 config를 모두 만든다.

추천 사유: 설정 범위가 명확하고, 후속 worker를 추가할 때 `workers` 섹션만 늘리면 됩니다.

B) shared infra config와 worker config를 완전히 별도 YAML 파일로 나눈다.

C) YAML 없이 CDK context CLI 인자만 사용한다.

X) 기타

[Answer]: A

### Question 3. VPC And Subnet Design

VPC와 subnet은 어떻게 생성할까요?

A) (권장) 기본은 새 VPC를 생성한다. `max_azs=2`, `nat_gateways=0`, public subnet과 isolated/private DB subnet을 만들고, 기존 VPC import는 후속 확장으로 둔다.

추천 사유: 지금은 작고 검증 가능한 baseline이 필요합니다. import까지 동시에 지원하면 config와 테스트가 커집니다.

B) 새 VPC 생성과 기존 VPC import를 둘 다 이번 UOW에서 구현한다.

C) 기존 VPC import만 지원하고 새 VPC는 만들지 않는다.

X) 기타

[Answer]: A

### Question 4. S3 Bucket Design

S3 output bucket은 어떻게 구성할까요?

A) (권장) 환경별 shared bucket 하나를 만든다. block public access, S3 managed encryption, lifecycle disabled를 기본으로 하고, object prefix는 `outputs/{environment}/{site_id}/{job_id}/{run_id}/...` 패턴을 지원한다. versioning은 기본 off, prod만 config로 켤 수 있게 둔다.

추천 사유: 비용을 낮추면서도 다중 worker 공유와 향후 플랫폼 prefix 정규화가 가능합니다.

B) worker마다 bucket을 별도로 만든다.

C) versioning과 lifecycle transition을 모든 환경에서 기본 활성화한다.

X) 기타

[Answer]: A

### Question 5. RDS PostgreSQL Design

RDS PostgreSQL은 어떤 기본값으로 만들까요?

A) (권장) 환경별 shared PostgreSQL 인스턴스 하나를 만든다. engine version은 CDK에서 지원하는 stable PostgreSQL 버전을 config로 지정하고, dev/staging 기본은 single-AZ, 20GiB, 작은 instance class, 짧은 backup retention으로 둔다. prod는 Multi-AZ, backup retention, instance class를 config로 강화 가능하게 둔다.

추천 사유: 체크포인트 저장소는 공유하되, 초기 비용은 낮추고 운영 환경만 강화할 수 있습니다.

B) 모든 환경에서 prod급 Multi-AZ와 큰 instance class를 기본값으로 둔다.

C) RDS는 이번 CDK에서 만들지 않고 외부 PostgreSQL secret/endpoint import만 지원한다.

X) 기타

[Answer]: A

### Question 6. ECS Cluster And Worker Task Placement

ECS cluster와 worker task definition은 어디에 둘까요?

A) (권장) ECS cluster는 shared infra stack에서 만들고, worker stack은 cluster ref를 받아 Fargate task definition, task role, log group, optional schedule만 만든다.

추천 사유: 여러 worker가 같은 cluster를 공유할 수 있고, worker stack은 컨테이너별 차이에 집중할 수 있습니다.

B) worker stack마다 ECS cluster를 따로 만든다.

C) shared infra stack과 worker stack을 합쳐 cluster/task를 한 stack에 둔다.

X) 기타

[Answer]: A

### Question 7. Worker Runtime Env And Secret Mapping

worker task의 environment와 secret은 어떻게 매핑할까요?

A) (권장) non-secret env는 YAML `workers[].environment`에서 받고, CDK가 S3/RDS 기본 env를 합성한다. `DATABASE_URL`, proxy/S3-compatible credential 같은 민감값은 Secrets Manager reference를 ECS secret으로 주입한다.

추천 사유: 기존 컨테이너 계약을 유지하면서 plaintext secret 노출을 피할 수 있습니다.

B) 모든 env를 YAML에서 수동으로 받는다.

C) secret도 일반 environment variable로 평문 주입한다.

X) 기타

[Answer]: A

### Question 8. IAM And Security Group Detail

IAM policy와 security group은 어느 수준까지 CDK가 정의할까요?

A) (권장) CDK가 worker task role에 S3 bucket/prefix read-write, declared secrets read, 필요한 logs 권한만 부여한다. security group은 worker inbound 없음, RDS inbound는 worker SG에서 PostgreSQL port만 허용한다.

추천 사유: 최소 권한과 네트워크 경계가 템플릿 테스트로 검증 가능한 수준까지 문서화됩니다.

B) worker task role에 넓은 S3/Secrets/Logs wildcard를 부여한다.

C) security group과 IAM 세부 정책은 운영자가 콘솔에서 별도 구성한다.

X) 기타

[Answer]: A

### Question 9. Observability And Failure Signal

one-shot worker 실패 감지는 어떻게 구현할까요?

A) (권장) worker별 CloudWatch LogGroup을 만들고, EventBridge ECS Task State Change rule로 STOPPED/failed event를 잡는다. rule matched event count 기반 CloudWatch alarm과 optional SNS target을 config로 제공한다.

추천 사유: one-shot task에는 서비스 health check보다 task 종료 이벤트가 더 직접적입니다. SNS는 알림 대상이 없을 수 있으므로 optional로 두는 편이 작습니다.

B) CloudWatch dashboard와 custom scraper metric까지 이번 UOW에서 만든다.

C) LogGroup만 만들고 실패 이벤트/알림은 만들지 않는다.

X) 기타

[Answer]: A

### Question 10. CDK Verification And Output Artifacts

Infrastructure Design의 검증 및 산출물 경계는 어떻게 둘까요?

A) (권장) 기본 검증은 `python -m pytest infra/cdk/tests`와 `cdk synth -c env=dev`로 둔다. tests는 S3/RDS/ECS/Secrets/EventBridge 리소스 존재, secret 미노출, NAT Gateway 없음, RDS public access 차단, prod retain 정책을 assert한다. 산출물은 `infrastructure-design.md`, `deployment-architecture.md` 2개만 만든다.

추천 사유: 실제 AWS 배포 없이도 구현 위험을 대부분 잡을 수 있고, 문서 산출물도 필요한 만큼만 유지됩니다.

B) 기본 검증에 실제 AWS `cdk deploy`/`destroy` smoke까지 포함한다.

C) 테스트 없이 `cdk synth`만 검증한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-010 Infrastructure Design 산출물 2개를 생성합니다.
4. shared infrastructure 산출물 필요 여부를 기록합니다.
5. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.
