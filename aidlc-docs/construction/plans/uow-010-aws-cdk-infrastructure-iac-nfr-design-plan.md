# NFR Design Plan - UOW-010 AWS CDK Infrastructure IaC

이 계획은 `UOW-010 AWS CDK Infrastructure IaC`의 NFR 요구사항을 CDK 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-010 AWS CDK Infrastructure IaC
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-006 Output And Storage, UOW-008 Container, MCP, And Test Harness, UOW-009 Parser Failure Retry Reprocessor
- **Scope**: Python CDK v2 app layout, shared infra stack, reusable worker stack pattern, environment config validation, S3/RDS/Secrets/CloudWatch/ECS Fargate mapping, least-privilege IAM, no-NAT default network, template verification
- **Out Of Scope**: EKS/Kubernetes, SQS worker queue, centralized management platform, dashboard, CDK-driven Docker image build, live AWS deploy smoke as a default gate, scraper runtime changes

## NFR Design 작업 체크리스트

- [x] UOW-010 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## Review Result

- Q1-Q10은 모두 A로 확정되었습니다.
- 답변 간 충돌은 없습니다.
- follow-up 질문은 필요하지 않습니다.
- 확정 방향은 작은 Python CDK v2 앱, shared/worker stack 분리, dataclass 기반 config 검증, deterministic naming/tagging, stateful destroy 명시 opt-in, S3/RDS 기본 hardening, Secrets Manager injection, least-privilege IAM, no-NAT 네트워크 기본값, CloudWatch Logs + task failure alarm, CDK assertions + `cdk synth`입니다.
- 산출물 생성 후 UOW-010 NFR Design Review 단계에서 사용자 승인을 대기합니다.

## NFR Design Questions

### Question 1. CDK Project Layout

CDK 프로젝트는 어떤 구조로 둘까요?

A) (권장) `infra/cdk` 아래에 Python CDK v2 앱을 두고, `requirements.txt`, `app.py`, `stacks/`, `config/`, `tests/`만 만든다. 스크래퍼 런타임 패키지는 import하지 않고 컨테이너 계약만 문자열/env로 연결한다.

추천 사유: CDK와 스크래퍼 런타임 의존성을 분리하면 synth/test가 가볍고, 인프라 코드가 파서/수집 로직 변경에 끌려가지 않습니다.

B) 기존 Python 패키지 안에 CDK 모듈을 넣고 런타임 모델도 직접 import한다.

C) TypeScript CDK 앱으로 별도 작성한다.

X) 기타

[Answer]: A

### Question 2. Stack And Construct Boundary

스택과 construct 경계는 어떻게 나눌까요?

A) (권장) `SharedInfraStack`과 `WorkerStack`을 분리하고, 공통 props/config dataclass 정도만 둔다. Worker stack은 `site_id`, image, command/env, schedule, shared infra refs를 입력으로 받는다.

추천 사유: 지금 필요한 재사용성만 확보하면서, 미래 플랫폼용 registry/queue 같은 리소스는 만들지 않을 수 있습니다.

B) 여러 계층의 base stack, construct factory, worker plugin abstraction을 미리 만든다.

C) 모든 리소스를 하나의 monolithic stack에 둔다.

X) 기타

[Answer]: A

### Question 3. Environment Config Validation

환경별 설정 파일은 어떻게 읽고 검증할까요?

A) (권장) `infra/cdk/config/{env}.yaml`을 작은 loader가 읽고, dataclass 기반 검증으로 필수 값과 금지된 secret value를 확인한다. YAML parser 외의 검증 프레임워크는 추가하지 않는다.

추천 사유: 설정은 리뷰 가능해야 하지만, CDK용 설정 검증에 별도 모델 프레임워크까지 넣을 필요는 아직 없습니다.

B) Pydantic 모델을 사용해 환경 config를 강하게 검증한다.

C) dict 그대로 읽고 각 stack에서 필요한 값을 직접 꺼낸다.

X) 기타

[Answer]: A

### Question 4. Naming And Tagging Pattern

리소스 이름과 태그는 어떻게 구성할까요?

A) (권장) `name_prefix`, `environment`, `site_id`를 조합한 deterministic name helper를 사용하고, 모든 리소스에 `Project`, `Environment`, `ManagedBy`, `SiteId` 태그를 적용한다. 상태 저장 리소스 이름은 config override를 허용한다.

추천 사유: 운영자가 리소스를 찾기 쉽고, S3/RDS처럼 이름 충돌과 보존이 중요한 리소스는 명시 override가 필요할 수 있습니다.

B) CDK가 생성하는 기본 logical/physical name에 맡긴다.

C) 모든 리소스 이름을 config에 수동으로 전부 적는다.

X) 기타

[Answer]: A

### Question 5. Stateful Resource Safety Pattern

S3와 RDS 같은 상태 저장 리소스의 삭제 안전장치는 어떻게 둘까요?

A) (권장) env별 removal policy profile을 둔다. prod는 retain 기본, dev는 disposable 리소스만 destroy 허용, stateful destroy는 `allow_destroy_stateful` 같은 명시 플래그가 있을 때만 가능하게 한다.

추천 사유: dev 비용 정리는 가능해야 하지만, 실수로 운영 데이터가 삭제되는 경로는 명시적으로 잠가야 합니다.

B) dev/staging은 모든 리소스 destroy, prod만 retain으로 단순화한다.

C) 모든 환경에서 stateful 리소스를 retain한다.

X) 기타

[Answer]: A

### Question 6. Storage And Database Hardening Pattern

S3와 RDS의 기본 보안/보존 설정은 어떻게 구현할까요?

A) (권장) S3는 block public access, server-side encryption, lifecycle disabled 기본값을 적용한다. RDS는 PostgreSQL, storage encryption, private subnet placement, env별 backup retention/Multi-AZ config를 적용한다.

추천 사유: 작은 기본값을 유지하면서도 데이터 노출과 실수 삭제 리스크는 낮출 수 있습니다.

B) 기본 설정을 최소화하고 S3/RDS 보안 옵션은 운영자가 콘솔에서 설정한다.

C) prod급 RDS Multi-AZ와 긴 backup retention을 모든 환경에 강제한다.

X) 기타

[Answer]: A

### Question 7. Secrets Injection Pattern

Secrets Manager와 ECS task secret injection은 어떤 패턴으로 둘까요?

A) (권장) config에는 secret name/ARN만 저장하고, CDK가 Secret reference를 만든 뒤 ECS container secret으로 주입한다. RDS generated secret은 그대로 연결하고, proxy/S3 호환 secret은 운영자 제공 secret reference를 받는다.

추천 사유: plaintext secret을 피하면서도 자동 rotation이나 secret 생성 정책을 과하게 만들지 않습니다.

B) 모든 secret을 CDK에서 새로 생성하고 rotation까지 기본 구성한다.

C) secret value를 CDK context 또는 env config 파일로 받아 task env에 평문 주입한다.

X) 기타

[Answer]: A

### Question 8. IAM Policy Pattern

Worker task role 권한은 어떻게 작성할까요?

A) (권장) CDK grant helper와 최소 inline policy를 조합해 S3 bucket/prefix, 필요한 secret read, CloudWatch logging, 필요한 ECS/RDS 관련 권한만 부여한다. broad wildcard는 execution role의 AWS managed policy처럼 필요한 경우로 제한한다.

추천 사유: 여러 worker가 공유 인프라를 쓰는 구조라 task role의 blast radius를 줄여야 합니다.

B) 구현 편의를 위해 worker task role에 넓은 S3/Secrets/Logs 권한을 준다.

C) IAM은 일단 role만 만들고 세부 policy는 운영자가 나중에 붙인다.

X) 기타

[Answer]: A

### Question 9. Network Pattern

no-NAT 기본 네트워크는 어떻게 구현할까요?

A) (권장) VPC는 public subnet과 isolated/private DB subnet을 만들고 NAT Gateway는 0개로 둔다. Worker task는 public subnet에서 public IP를 받아 outbound 요청을 수행하고, RDS는 isolated/private subnet에 두며 security group은 worker -> RDS PostgreSQL만 허용한다.

추천 사유: 초기 비용을 줄이면서도 DB는 외부에 노출하지 않는 요구사항과 맞습니다.

B) Worker도 private subnet에 두고 NAT Gateway를 기본 생성한다.

C) 새 VPC를 만들지 않고 기존 VPC/subnet/security group import만 지원한다.

X) 기타

[Answer]: A

### Question 10. Observability And Verification Pattern

관측성과 검증은 어떤 구현 패턴으로 둘까요?

A) (권장) 명시 LogGroup과 retention을 만들고, ECS task failure는 EventBridge task state change 기반 metric/alarm 또는 알림 hook으로 잡는다. 기본 검증은 pytest CDK assertions와 `cdk synth`로 리소스 종류, secret 미노출, IAM/네트워크 주요 속성을 확인한다.

추천 사유: one-shot task에는 로그와 실패 감지가 핵심이고, 기본 CI는 AWS 배포 권한 없이 template 수준에서 빠르게 검증되는 편이 좋습니다.

B) CloudWatch dashboard와 custom metric까지 기본 구현하고, deploy/destroy smoke를 기본 gate로 둔다.

C) `cdk synth`만 수행하고 template assertions와 failure alarm은 생략한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-010 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.
