# Infrastructure Design Plan - UOW-011 Scrapling Runtime Refactor

이 계획은 `UOW-011 Scrapling Runtime Refactor`의 논리 컴포넌트를 실제 실행/컨테이너/CDK 인프라 경계에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-011 Scrapling Runtime Refactor
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: existing worker container image, optional browser dependency packaging, ECS/Fargate config compatibility, safe log/checkpoint/report boundary, external Job Queue boundary, Spider UOW boundary
- **Likely Infrastructure Scope**: current Dockerfile includes `browser` extra and Chromium, existing CDK worker task can run the same image, existing S3/PostgreSQL/CloudWatch resources are reused, no new network port, no new storage backend, no internal queue broker
- **Out Of Scope**: new RabbitMQ/SQS broker, new DLQ resource, browser debugging endpoint, separate browser worker image, new PostgreSQL schema, CDK-managed Docker build, Scrapling Spider implementation

## Infrastructure Design 작업 체크리스트

- [x] UOW-011 Functional Design 승인 확인
- [x] UOW-011 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 변경 필요 여부 확인

## Review Result

- Q1은 비어 있었지만 사용자가 질문지 답변 확정을 명시했으므로 권장 A로 확정 처리했습니다.
- Q2-Q8은 모두 A로 확정되었습니다.
- 답변 간 충돌은 없습니다.
- follow-up 질문은 필요하지 않습니다.
- 확정 방향은 새 인프라 없음, 단일 worker image 유지, 기존 Fargate CPU/memory 기본값 유지, browser 관련 inbound/debug port 미노출, 기존 output/failure/report/checkpoint 저장소 재사용, fallback 전용 metric/dashboard 미구현, Job Queue 인프라 외부화, 검증은 Code Generation/Build-Test 단계에서 수행입니다.
- shared infrastructure 문서 변경은 필요하지 않습니다.
- 산출물 생성 후 UOW-011 Infrastructure Design Review 단계에서 사용자 승인을 대기합니다.

## Infrastructure Design Questions

### Question 1. Infrastructure Footprint

UOW-011은 새 인프라 리소스를 만들까요?

A) (권장) 새 서버, 새 저장소, 새 queue/broker, 새 DB schema를 만들지 않는다. 기존 CLI/Docker/MCP, worker container, CDK Fargate task, S3/Garage output, PostgreSQL checkpoint, CloudWatch log 경계를 그대로 재사용한다.

추천 사유: UOW-011은 런타임 리팩토링입니다. Scrapling과 browser fallback 때문에 새 운영 리소스를 만들 필요는 없고, 기존 one-shot worker 경계가 그대로 맞습니다.

B) browser fallback 전용 worker image와 task definition을 새로 만든다.

C) fallback 실패 처리를 위해 queue/DLQ와 별도 retry worker 인프라를 함께 만든다.

X) 기타

[Answer]:

### Question 2. Docker Image Boundary

Docker 이미지는 어떻게 유지할까요?

A) (권장) 현재 단일 worker image에 `.[s3,postgres,browser]`와 Chromium을 포함한다. 별도 image split은 하지 않는다.

추천 사유: 운영자는 Job별로 이미지를 고르지 않아도 됩니다. HTTP-first 경로에서는 브라우저가 실행되지 않으므로 단일 이미지가 가장 단순합니다.

B) HTTP-only image와 browser-fallback image를 분리한다.

C) Docker image에서는 browser dependency를 빼고 로컬 CLI에서만 fallback을 지원한다.

X) 기타

[Answer]: A

### Question 3. ECS/Fargate Resource Sizing

브라우저 fallback 가능성을 고려한 ECS/Fargate CPU/memory 기본값은 어떻게 둘까요?

A) (권장) 기존 CDK config 구조와 기본값(`cpu: 512`, `memory_mib: 1024`)은 유지한다. browser fallback이 자주 발생하는 운영 Job은 환경별 config에서 memory/cpu를 올리도록 문서화한다.

추천 사유: fallback은 예외 경로이고 이미 config로 리소스를 조절할 수 있습니다. 기본값을 바로 키우면 모든 Job의 비용이 올라갑니다.

B) 모든 환경의 기본값을 `cpu: 1024`, `memory_mib: 2048` 이상으로 올린다.

C) browser fallback 전용 ECS task profile을 별도로 만든다.

X) 기타

[Answer]: A

### Question 4. Network And Browser Exposure

브라우저 fallback을 위해 네트워크나 포트를 새로 열까요?

A) (권장) 새 inbound port, browser debugging port, VNC, remote debugging endpoint를 열지 않는다. 기존 outbound-only worker 네트워크를 그대로 쓴다.

추천 사유: fallback은 컨테이너 내부 headless 실행입니다. 외부에서 브라우저에 접속할 이유가 없고, 포트를 열면 보안 표면만 커집니다.

B) 디버깅을 위해 remote debugging port를 선택적으로 열 수 있게 한다.

C) fallback 컨테이너에 VNC/browser UI 접근 경로를 추가한다.

X) 기타

[Answer]: A

### Question 5. Storage And Checkpoint Infrastructure

fallback 성공/실패 관리를 위해 저장소 인프라를 추가할까요?

A) (권장) 기존 output/failure/report/checkpoint 저장소를 그대로 사용한다. fallback 전용 table, bucket, prefix, raw dump 저장소는 만들지 않는다.

추천 사유: fallback 결과는 최종 HTML 파싱 성공/실패로 귀결됩니다. 별도 저장소를 만들면 운영 경로와 보안 검토만 늘어납니다.

B) fallback 실패 전용 PostgreSQL table을 추가한다.

C) rendered HTML/screenshot 저장 전용 bucket/prefix를 추가한다.

X) 기타

[Answer]: A

### Question 6. Observability Infrastructure

fallback 관측성을 위해 새 모니터링 인프라를 만들까요?

A) (권장) 새 metric/dashboard/alarm은 만들지 않는다. 기존 structured log와 ECS task failure 관측성으로 시작하고, fallback 카운터가 필요해지면 후속 운영 UOW에서 추가한다.

추천 사유: 현재 요구사항은 safe log와 terminal checkpoint입니다. custom metric은 실제 운영 데이터가 쌓인 뒤 추가해도 늦지 않습니다.

B) browser fallback start/end 카운터용 CloudWatch custom metric을 추가한다.

C) fallback 전용 dashboard와 alarm을 기본 생성한다.

X) 기타

[Answer]: A

### Question 7. External Job Queue Boundary

향후 Job Queue 인프라는 어디서 다룰까요?

A) (권장) UOW-011에서는 queue 인프라를 만들지 않는다. RabbitMQ/SQS, DLQ, lease, autoscaling은 향후 통합 플랫폼 또는 별도 orchestration UOW에서 다룬다.

추천 사유: 스크래퍼 컨테이너는 one-shot worker로 유지하는 결정이 이미 확정되었습니다. 큐 인프라는 여러 scraper를 묶는 플랫폼에서 한 번만 설계해야 합니다.

B) 이 저장소 CDK에 SQS/DLQ만 미리 추가한다.

C) RabbitMQ broker를 Docker Compose/CDK에 추가한다.

X) 기타

[Answer]: A

### Question 8. Infrastructure Verification Gate

UOW-011 Infrastructure Design 이후 검증은 어디까지 기본으로 둘까요?

A) (권장) infra 코드 변경이 없으면 기존 CDK synth/template test 재실행은 Code Generation 또는 Build/Test 단계에서 수행한다. 이 단계에서는 문서상 경계만 확정한다.

추천 사유: 아직 코드를 바꾸는 단계가 아닙니다. 실제 lock 구현 이후 전체 테스트와 필요한 Docker smoke를 실행하는 편이 중복이 적습니다.

B) Infrastructure Design 단계에서 즉시 CDK synth와 Docker build를 다시 수행한다.

C) Docker/infra 검증은 모두 수동으로만 남긴다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-011 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.
