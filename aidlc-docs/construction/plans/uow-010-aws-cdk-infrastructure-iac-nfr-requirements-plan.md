# NFR Requirements Plan - UOW-010 AWS CDK Infrastructure IaC

이 계획은 `UOW-010 AWS CDK Infrastructure IaC`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-010 AWS CDK Infrastructure IaC
- **Functional Design**: 승인됨
- **Depends On**: UOW-006 Output And Storage, UOW-008 Container, MCP, And Test Harness, UOW-009 Parser Failure Retry Reprocessor
- **Primary Story**: US-020
- **Related Stories**: US-012, US-013, US-015, US-016A, US-018, US-019
- **Scope**: Python CDK v2 app under `infra/cdk`, shared infra stack, reusable worker stack pattern, ECS Fargate one-shot worker, AWS S3/RDS/Secrets/CloudWatch, environment separation, synth/template verification
- **Security Focus**: least privilege IAM, secret injection through Secrets Manager, no plaintext secrets in source/template/logs, private RDS, no inbound worker ports
- **Resiliency Focus**: stateful resource retention, backup defaults, task failure visibility, explicit environment separation, safe destroy behavior
- **Cost Focus**: small default footprint, no NAT Gateway by default, no always-on worker service, scheduled/manual one-shot tasks
- **Out Of Scope**: EKS/Kubernetes, SQS worker queue, centralized multi-community management platform, dashboard, production incident automation, scraper runtime changes

## NFR Requirements 작업 체크리스트

- [x] UOW-010 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Cost Baseline 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-010-aws-cdk-infrastructure-iac/nfr-requirements/tech-stack-decisions.md` 생성

## Answer Validation Notes

- Q1-Q10 모두 A로 확정됨.
- 답변은 승인된 Functional Design과 충돌하지 않음.
- 확정 방향은 비용 최소화, dev/staging 비용 보수 기본값, prod 강화 가능성, S3 기본 보존, least-privilege IAM, Secrets Manager injection, RDS private subnet, worker public subnet outbound-only, CloudWatch Logs + task failure alarm, `cdk synth` + template tests, 미래 플랫폼 호환 입력 유지임.
- follow-up 질문은 필요하지 않음.

## NFR Requirements Questions

### Question 1. Cost Baseline

초기 AWS 배포의 비용 기준은 어떻게 둘까요?

A) (권장) 비용 최소화를 우선한다. ECS Fargate one-shot task, public-subnet outbound worker, NAT Gateway 없음, 작은 RDS 기본값, 선택 schedule, 최소 CloudWatch retention으로 시작한다.

추천 사유: 현재 목적은 운영 가능한 표준 CDK를 작게 시작하는 것입니다. 항상 켜진 서비스나 NAT Gateway를 기본값으로 넣으면 초기 비용이 커집니다.

B) 비용보다 운영 보안을 우선해 private subnet + NAT Gateway, 더 긴 로그 보존, 여유 RDS sizing을 기본값으로 둔다.

C) prod 수준 고가용성과 장기 보존을 dev/staging에도 동일하게 적용한다.

X) 기타

[Answer]: A

### Question 2. RDS Availability And Backup

RDS PostgreSQL의 초기 가용성과 백업 기준은 어떻게 둘까요?

A) (권장) dev/staging은 single-AZ와 짧은 backup retention, prod는 configurable Multi-AZ와 더 긴 backup retention을 지원하되 기본은 보수적으로 비용을 낮춘다.

추천 사유: 체크포인트는 중요하지만 초기 단계에서 모든 환경에 Multi-AZ를 강제하면 비용이 커집니다. prod만 강화 가능하게 두는 편이 균형이 좋습니다.

B) 모든 환경에서 Multi-AZ와 긴 backup retention을 기본값으로 둔다.

C) RDS backup은 CDK에서 다루지 않고 운영자가 수동 설정한다.

X) 기타

[Answer]: A

### Question 3. S3 Data Retention

S3 원본 JSONL, failures, reports, media 보존 정책은 어떻게 둘까요?

A) (권장) 기본 lifecycle은 비활성화하고, log/report/failure 원본 보존을 우선한다. 비용 압박이 확인된 뒤 media나 오래된 output lifecycle을 별도 설정으로 켠다.

추천 사유: 스크래핑 데이터는 재처리와 검증의 근거입니다. 초기부터 자동 삭제하면 디버깅과 재수집 근거가 사라질 수 있습니다.

B) media와 오래된 outputs를 일정 기간 후 자동 삭제하는 lifecycle을 기본 활성화한다.

C) prod는 영구 보존, dev/staging은 짧게 자동 삭제한다.

X) 기타

[Answer]: A

### Question 4. IAM Permission Depth

IAM 권한은 어느 정도로 제한할까요?

A) (권장) task role은 해당 environment bucket/prefix, 필요한 Secrets Manager secret, CloudWatch Logs, RDS 접속에 필요한 최소 권한만 받는다.

추천 사유: 여러 스크래퍼가 공유 인프라를 쓰므로 worker별 blast radius를 줄이는 것이 중요합니다.

B) 구현 단순화를 위해 task role에 넓은 S3/Secrets/Logs 권한을 준다.

C) IAM 세분화는 후속으로 미루고 CDK는 role만 생성한다.

X) 기타

[Answer]: A

### Question 5. Secret Rotation And Injection

Secrets Manager secret은 어떤 수준으로 관리할까요?

A) (권장) CDK는 secret placeholder/reference와 ECS secret injection만 정의한다. 자동 rotation은 기본 비활성화하고, RDS generated secret 또는 운영자가 만든 secret을 참조한다.

추천 사유: 자동 rotation은 애플리케이션 연결 문자열 갱신과 운영 검증이 필요합니다. 초기에는 plaintext 방지만 확실히 하고 rotation은 후속 운영 기준으로 분리하는 편이 작습니다.

B) RDS와 proxy secret 모두 자동 rotation을 기본 활성화한다.

C) secret은 SSM Parameter Store SecureString으로만 관리한다.

X) 기타

[Answer]: A

### Question 6. Network Security Baseline

네트워크 보안 기본값은 어떻게 둘까요?

A) (권장) RDS는 private subnet, worker는 public subnet outbound-only, worker security group에서 RDS PostgreSQL port로만 접근 허용, worker inbound는 없음으로 둔다.

추천 사유: scraper는 외부로 나가는 요청이 필요하고 inbound service가 없습니다. NAT Gateway 없이 시작하면서 RDS는 private로 보호하는 절충안입니다.

B) worker도 private subnet에 두고 NAT Gateway를 기본 생성한다.

C) 기존 VPC와 security group import만 허용하고 CDK는 네트워크를 만들지 않는다.

X) 기타

[Answer]: A

### Question 7. Observability And Alerting

기본 관측성과 알림은 어느 수준으로 둘까요?

A) (권장) CloudWatch Log Group, log retention, ECS task failure alarm만 기본 제공한다. dashboard와 custom metric은 후속으로 둔다.

추천 사유: one-shot worker의 1차 운영 판단에는 성공/실패와 stdout report가 핵심입니다. custom metric은 실제 운영 패턴이 쌓인 뒤 설계하는 편이 낫습니다.

B) CloudWatch dashboard와 custom metric까지 기본으로 만든다.

C) 로그 그룹만 만들고 alarm은 만들지 않는다.

X) 기타

[Answer]: A

### Question 8. Synth And Test Gate

CDK 기본 검증 gate는 어디까지 포함할까요?

A) (권장) 기본 gate는 `cdk synth`와 template-level unit/snapshot tests다. 실제 AWS deploy smoke는 optional gate로 둔다.

추천 사유: 기본 CI가 AWS 계정과 권한에 의존하면 개발 속도가 느려집니다. template 검증만으로도 resource category와 secret 노출 위험을 상당 부분 잡을 수 있습니다.

B) 기본 gate에 실제 AWS deploy/destroy smoke까지 포함한다.

C) `cdk synth`만 하고 template tests는 생략한다.

X) 기타

[Answer]: A

### Question 9. Environment Configuration Format

환경별 CDK 설정은 어떤 방식으로 관리할까요?

A) (권장) `infra/cdk/config/{env}.yaml` 같은 비밀 없는 config 파일과 CDK context를 조합한다. secret value는 파일에 넣지 않고 이름/ARN만 둔다.

추천 사유: 환경별 차이를 Git에서 리뷰할 수 있고, secret 평문 유출도 피할 수 있습니다.

B) 모든 설정을 CDK context CLI 인자로만 넣는다.

C) 환경별 설정 파일에 secret value까지 포함한다.

X) 기타

[Answer]: A

### Question 10. Future Platform Compatibility

향후 통합 커뮤니티 관리 플랫폼과의 호환성은 어디까지 반영할까요?

A) (권장) `site_id`, image URI/tag, command/env, schedule, shared infra refs를 명시 입력으로 두어 나중에 플랫폼이 같은 worker stack pattern을 호출할 수 있게 한다. 플랫폼 자체 리소스는 만들지 않는다.

추천 사유: 지금 필요한 것은 버려지지 않을 worker 배포 표준입니다. queue, registry, dashboard를 지금 넣지 않아도 나중에 상위 플랫폼이 같은 입력 모델을 재사용할 수 있습니다.

B) 이번 CDK에 SQS queue와 worker registry table까지 포함한다.

C) 미래 플랫폼 호환성은 고려하지 않고 현재 스크래퍼만 배포한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-010 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-010 NFR Design으로 넘어가지 않습니다.
