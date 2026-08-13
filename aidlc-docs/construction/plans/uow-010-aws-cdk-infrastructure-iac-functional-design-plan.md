# Functional Design Plan - UOW-010 AWS CDK Infrastructure IaC

이 계획은 `UOW-010 AWS CDK Infrastructure IaC`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-010 AWS CDK Infrastructure IaC
- **Depends On**: UOW-006 Output And Storage, UOW-008 Container, MCP, And Test Harness, UOW-009 Parser Failure Retry Reprocessor
- **Primary Story**: US-020
- **Related Stories**: US-012, US-013, US-015, US-016A, US-018, US-019
- **Scope**: 후속 스크래퍼들이 공유할 수 있는 AWS CDK 인프라 표준, shared infra stack, reusable worker stack pattern, worker execution infrastructure, object storage mapping, PostgreSQL checkpoint mapping, secrets, logs, environment separation, synth/deploy documentation
- **Out Of Scope**: scraper runtime behavior changes, parser changes, scraper별 API/query/parser logic, centralized multi-community scheduler/platform implementation, production incident automation, CAPTCHA bypass, non-AWS object store implementation

## Design Direction

UOW-010은 특정 커뮤니티 스크래퍼 하나에만 종속되는 CDK도 아니고, 여러 스크래퍼를 통합 생성/관리하는 완성형 플랫폼 CDK도 아닙니다.

이 단계의 목표는 아래 2개 경계를 먼저 표준화하는 것입니다.

- **Shared Infra Stack**: 여러 스크래퍼가 공유할 수 있는 S3/RDS/Secrets/Logs/Network 기반 리소스
- **Worker Stack Pattern**: `site_id`, `image_uri`, runtime env, optional schedule을 입력받아 특정 스크래퍼 컨테이너를 one-shot worker로 실행하는 재사용 패턴

향후 통합 관리 플랫폼은 이 표준 위에 별도 stack 또는 별도 유닛으로 추가합니다.

## Functional Design 작업 체크리스트

- [x] UOW-009 Build and Test 승인 확인
- [x] UOW-010 범위 확인
- [x] UOW-006/UOW-008/UOW-009 계약 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/functional-design/domain-entities.md` 생성

## Answer Validation Notes

- Q1-Q10 all selected A.
- The confirmed direction is ECS Fargate one-shot task execution, AWS S3 and RDS PostgreSQL in a shared infra stack, reusable worker stack pattern, ECR image reference by URI/tag, manual task run plus optional EventBridge schedule, Secrets Manager secret injection, public-subnet outbound worker with private RDS, minimal CloudWatch observability, environment-aware resource naming/removal policy, and Python CDK v2 under `infra/cdk`.
- No follow-up question is required before Functional Design artifact review.

## Functional Design Questions

### Question 1. Worker Execution Target

AWS에서 스크래퍼 컨테이너는 어떤 실행 대상으로 배포할까요?

A) (권장) ECS Fargate one-shot task를 기본으로 두고, 필요 시 EventBridge schedule에서 같은 task definition을 실행한다.

추천 사유: 현재 컨테이너가 "하나의 프로세스가 하나의 Job"인 구조라 Fargate task와 잘 맞습니다. 서버 관리가 없고, Lambda보다 긴 실행과 Docker 이미지 재사용에 유리합니다.

B) AWS Batch job으로 실행한다.

C) Lambda container image로 실행한다.

D) EC2에 Docker를 직접 실행한다.

X) 기타

[Answer]: A

### Question 2. Shared Storage Resource Strategy

공통 저장소 stack은 저장소를 어떻게 다룰까요?

A) (권장) shared infra stack이 AWS S3 bucket과 RDS PostgreSQL을 생성한다. 기존 S3 호환/Garage 계약은 유지하되 AWS 배포에서는 S3를 기본 구현으로 사용한다.

추천 사유: AWS 안에서는 S3와 RDS가 운영 부담이 가장 작습니다. 애플리케이션은 이미 S3 호환 API와 PostgreSQL DSN을 사용하므로 런타임 코드 변경도 줄어듭니다.

B) shared infra stack이 ECS 위에 Garage와 PostgreSQL 컨테이너까지 함께 띄운다.

C) 저장소는 외부에서 이미 준비된 것으로 보고 CDK는 worker stack이 참조할 bucket/DSN/secret 이름만 입력받는다.

X) 기타

[Answer]: A

### Question 3. Shared Infrastructure Boundary

여러 후속 스크래퍼를 고려할 때 CDK stack 경계는 어떻게 나눌까요?

A) (권장) 공통 저장소/네트워크/secret 기반 shared infra stack과, 스크래퍼 컨테이너별 worker stack pattern을 분리한다.

추천 사유: S3/PostgreSQL을 공유하면서도 개별 스크래퍼 worker를 따로 배포, 교체, 제거하기 쉽습니다. 앞서 정한 공유 저장소 규약과도 맞습니다.

B) 현재 스크래퍼 전용 단일 stack에 저장소와 worker를 모두 넣는다.

C) 처음부터 통합 관리 플랫폼 stack까지 포함해 scheduler, queue, dashboard, worker registry를 함께 설계한다.

X) 기타

[Answer]: A

### Question 4. Container Image Source

CDK는 스크래퍼 컨테이너 이미지를 어떻게 참조할까요?

A) (권장) ECR repository와 image tag를 입력으로 받고, 이미지 build/push는 CDK 밖의 수동 절차 또는 CI에서 수행한다.

추천 사유: CDK synth/deploy가 Docker build에 묶이지 않아 빠르고 예측 가능합니다. 여러 스크래퍼가 같은 패턴으로 ECR tag만 바꿔 배포하기도 쉽습니다.

B) CDK `DockerImageAsset`으로 로컬 Dockerfile을 build하고 배포한다.

C) public registry 이미지를 직접 참조한다.

X) 기타

[Answer]: A

### Question 5. Job Invocation Model

배포된 worker Job은 어떻게 실행되도록 설계할까요?

A) (권장) 수동 실행용 task run 명령과 선택적 EventBridge schedule을 제공한다. 중앙 Job queue는 UOW-010 범위에서 제외한다.

추천 사유: 현재 컨테이너 계약은 CLI 인자와 환경변수로 one-shot Job을 실행합니다. 중앙 queue까지 넣으면 운영 플랫폼 설계가 커지므로 별도 유닛으로 빼는 편이 안전합니다.

B) EventBridge schedule 전용으로만 실행한다.

C) SQS queue, worker registry, scheduler까지 포함한 통합 관리 플랫폼 실행 모델을 만든다.

X) 기타

[Answer]: A

### Question 6. Secret And Configuration Handling

Proxy, S3/RDS credential, 런타임 옵션은 어떻게 주입할까요?

A) (권장) 비밀값은 Secrets Manager에 저장하고, 비민감 설정은 CDK context 또는 stack parameter로 분리한다. task definition에는 secret reference와 환경변수 이름만 둔다.

추천 사유: secret을 CDK source나 CloudFormation template에 평문으로 남기지 않습니다. dev/prod 설정 분리도 단순합니다.

B) 모든 값을 `.env` 파일로 만들어 컨테이너 이미지에 포함한다.

C) 모든 값을 CDK 코드 상수로 둔다.

X) 기타

[Answer]: A

### Question 7. Network Model

Fargate worker와 RDS는 어떤 네트워크 구조에 둘까요?

A) (권장) VPC 안에 RDS는 private subnet, Fargate task는 public subnet에서 public IP를 받아 outbound-only로 실행한다. inbound는 열지 않는다.

추천 사유: 스크래퍼는 외부 사이트로 나가는 트래픽이 필요하지만 외부에서 들어오는 요청은 필요 없습니다. NAT Gateway 없이 시작할 수 있어 비용과 구성이 작습니다.

B) Fargate task와 RDS를 모두 private subnet에 두고 NAT Gateway로 outbound를 처리한다.

C) 기존 VPC/subnet/security group을 입력받아 사용한다.

X) 기타

[Answer]: A

### Question 8. Observability Contract

CDK가 기본으로 제공할 관측성은 어디까지로 둘까요?

A) (권장) CloudWatch Log Group, task exit code 확인, 실패 task alarm 정도만 기본 제공한다.

추천 사유: 지금 필요한 운영 신호는 task 성공/실패와 stdout report 확인입니다. 대시보드와 세부 metric은 실제 운영 패턴이 쌓인 뒤 추가하는 편이 낫습니다.

B) CloudWatch dashboard, custom metric, alarm을 모두 만든다.

C) 로그 그룹만 만들고 alarm은 만들지 않는다.

X) 기타

[Answer]: A

### Question 9. Environment Separation

dev/staging/prod 환경은 어떻게 분리할까요?

A) (권장) 같은 CDK app에서 environment name을 받아 stack 이름, resource name, removal policy를 분리한다. dev는 destroy 가능, prod는 retain 기본값을 둔다.

추천 사유: 코드 중복 없이 환경별 배포가 가능하고, 운영 데이터 삭제 위험을 줄입니다.

B) 환경마다 완전히 별도 CDK app 디렉터리를 둔다.

C) 처음에는 dev 하나만 만들고 prod 분리는 후속으로 둔다.

X) 기타

[Answer]: A

### Question 10. CDK Project Layout And Verification

CDK 코드는 repo 안에 어떻게 배치하고 검증할까요?

A) (권장) `infra/cdk` 아래 Python CDK v2 app을 두고, shared infra stack과 reusable worker stack pattern을 같은 app 안에 분리한다. 기본 검증은 `cdk synth`와 snapshot 수준의 template test로 제한한다.

추천 사유: 본 프로젝트가 Python 패키지이므로 언어를 맞추면 유지보수가 쉽습니다. 처음부터 deploy 통합 테스트까지 넣으면 AWS 계정 의존성이 커집니다.

B) repo root에 CDK app을 섞어 둔다.

C) TypeScript CDK app을 별도 디렉터리에 둔다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-010 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-010 NFR Requirements로 넘어가지 않습니다.
