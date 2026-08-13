# Infrastructure Design 계획 - UOW-005 Job Runner And Checkpoint

이 계획은 `UOW-005 Job Runner And Checkpoint`의 논리 컴포넌트를 실제 실행/검증 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-005 Job Runner And Checkpoint
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-006 Output And Storage
- **Scope**: import 가능한 JobRunner library, local/CI fake dependency tests, optional local output temp directory, UOW-002/003/004/006 dependency injection boundary, no standalone runtime infrastructure
- **Likely Infrastructure Scope**: standalone deployment 없음, local/CI 검증 인프라와 adapter 연결 경계만 해당
- **Baseline Inheritance**: `A)` 선택지는 기준 스크래퍼의 JobRunner/checkpoint 인프라 경계를 최대한 계승하되, FMKorea package/port 계약에 맞춘 권장안으로 작성한다.
- **Out Of Scope**: CLI wizard, container entrypoint, MCP server hosting, PostgreSQL checkpoint adapter, parser-stage retry reprocessor, SQS/DLQ, Docker Compose, AWS CDK resources, centralized platform scheduler

## Infrastructure Design 작업 체크리스트

- [x] UOW-005 Functional Design 승인 확인
- [x] UOW-005 NFR Requirements 승인 확인
- [x] UOW-005 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-005 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-005는 import 가능한 JobRunner library이며, 독립 서비스/컨테이너 배포는 N/A로 문서화한다.

추천 사유: 이 unit은 이미 구현된 collector/parser/storage를 한 프로세스 안에서 조율하는 내부 계층입니다. 실제 CLI 실행, worker container, MCP hosting은 후속 adapter unit에서 다루는 편이 책임이 작고 기존 구조 계승에 맞습니다.

B) local 개발/검증용 Python 실행 환경만 Infrastructure Design에 포함한다.

C) scraper worker/container 배포 환경까지 UOW-005에서 미리 정의한다.

X) 기타

[Answer]: A

### Question 2. Compute Infrastructure

UOW-005의 compute 인프라는 어디까지 정의할까요?

A) (권장) persistent compute는 없음. local 개발 환경과 CI test runner에서 `asyncio` runner, fake dependency, PBT 테스트를 실행한다고 문서화한다.

추천 사유: JobRunner는 배포 리소스가 아니라 Python library입니다. 프로세스 수, 컨테이너 크기, 플랫폼 스케줄러는 후속 runtime/operations 단계에서 결정해도 충분합니다.

B) 개발용 Docker container만 정의한다.

C) ECS/EKS, worker replica, autoscaling 정책까지 지금 확정한다.

X) 기타

[Answer]: A

### Question 3. Storage Infrastructure

UOW-005에서 저장소 인프라를 정의할까요?

A) (권장) 저장소 인프라는 새로 정의하지 않는다. UOW-005는 UOW-006 `OutputStorePort`, `FailureStorePort`, `MediaStorePort`, `CheckpointStorePort`를 주입받아 호출한다고만 문서화한다.

추천 사유: local/S3-compatible storage와 checkpoint 파일 구조는 UOW-006 책임입니다. UOW-005는 저장 성공 순서와 checkpoint timing만 책임지는 편이 단순합니다.

B) local output path와 S3-compatible bucket layout을 UOW-005에서도 다시 정의한다.

C) PostgreSQL checkpoint adapter까지 UOW-005에서 정의한다.

X) 기타

[Answer]: A

### Question 4. Messaging And Queue Infrastructure

UOW-005에서 queue 또는 messaging infrastructure를 어디까지 정의할까요?

A) (권장) 외부 messaging 인프라는 정의하지 않는다. UOW-005는 한 Job 내부에서만 `asyncio.Queue[PostCandidate]`를 사용하고, SQS/DLQ/lease는 후속 platform unit으로 미룬다.

추천 사유: 현재 필요한 큐는 post candidate fan-out용 in-process queue입니다. 외부 Job queue를 지금 섞으면 단일 실행 라이브러리와 플랫폼 실행 책임이 합쳐집니다.

B) local in-memory Job queue도 함께 정의한다.

C) SQS queue, DLQ, visibility timeout, lease protocol까지 지금 확정한다.

X) 기타

[Answer]: A

### Question 5. Networking Infrastructure

UOW-005의 네트워크 인프라는 어디까지 정의할까요?

A) (권장) 별도 네트워크 인프라는 없음. 상세 페이지/미디어 요청은 caller가 주입한 UOW-002 `HttpPort`를 통해 나간다고만 문서화한다.

추천 사유: proxy, User-Agent, cookie, rate limit, timeout, block detection은 UOW-002 책임입니다. UOW-005가 네트워크 토폴로지를 알 필요가 없습니다.

B) FMKorea host별 egress 정책만 참고사항으로 기록한다.

C) VPC/NAT/proxy gateway topology를 지금 정의한다.

X) 기타

[Answer]: A

### Question 6. Runtime Configuration Boundary

worker count, queue size, media mode, checkpoint mode 같은 runtime 설정은 어디에서 들어오나요?

A) (권장) UOW-005는 이미 구성된 `JobConfig`와 explicit dependencies만 받는다. 환경변수, `.env`, user-agent file, terminal input mapping은 CLI/container adapter가 처리한다.

추천 사유: core runner가 환경을 읽지 않으면 library import, unit test, MCP/CLI/container 재사용이 단순합니다.

B) `JobRunner`가 환경변수와 `.env`를 직접 읽어 기본 설정을 만든다.

C) interactive terminal wizard를 UOW-005 public API에 포함한다.

X) 기타

[Answer]: A

### Question 7. Checkpoint Infrastructure Boundary

checkpoint 인프라는 UOW-005에서 어디까지 정의할까요?

A) (권장) UOW-005는 checkpoint save/load 호출 시점과 payload 안전 규칙만 정의한다. local file checkpoint는 UOW-006 구현을 사용하고, PostgreSQL checkpoint adapter는 후속 unit으로 둔다.

추천 사유: checkpoint timing은 JobRunner 책임이지만 checkpoint 저장 백엔드는 storage 책임입니다. PostgreSQL까지 지금 넣으면 구현 범위가 커집니다.

B) local file checkpoint와 PostgreSQL checkpoint adapter를 모두 UOW-005에서 정의한다.

C) checkpoint 저장은 하지 않고 report 파일만 남긴다.

X) 기타

[Answer]: A

### Question 8. Observability Infrastructure

관측성 인프라는 어디까지 정의할까요?

A) (권장) 외부 monitoring stack은 N/A로 둔다. UOW-001 `LoggerPort`로 safe runner events, counters, stop reason, checkpoint save summary를 내보내는 계약만 문서화한다.

추천 사유: 아직 배포되는 worker service가 없습니다. Prometheus/OpenTelemetry, alerting, log shipping은 runtime 배포 unit에서 붙이면 충분합니다.

B) local JSON log 파일 위치만 정한다.

C) OpenTelemetry, Prometheus, alerting까지 지금 정의한다.

X) 기타

[Answer]: A

### Question 9. Live Smoke Test Infrastructure

UOW-005 live smoke test는 인프라 관점에서 어떻게 둘까요?

A) (권장) 기본 CI와 unit test에서는 제외한다. UOW-005는 fake collector/parser/storage로 검증하고, live smoke는 후속 CLI/container adapter가 실제 Job 실행 경로를 제공할 때 다룬다.

추천 사유: runner는 조율 계층이라 live site 의존성이 없어도 핵심 순서와 실패 처리를 검증할 수 있습니다. 실제 공개 페이지 수집 smoke는 실행 adapter가 생긴 뒤 한 번에 검증하는 편이 덜 흔들립니다.

B) UOW-005에서 공개 페이지 1건을 실제 수집하는 env-gated smoke를 만든다.

C) live smoke를 모든 CI에서 필수 실행한다.

X) 기타

[Answer]: A

### Question 10. Shared Infrastructure

UOW-005에서 Garage, PostgreSQL, SQS/DLQ 같은 shared infrastructure를 확정할까요?

A) (권장) 확정하지 않는다. UOW-005는 shared infrastructure를 직접 만들거나 소유하지 않고, 후속 storage/runtime/platform/CDK unit에서 매핑할 연결 지점만 문서화한다.

추천 사유: 이 unit은 in-process Job orchestration입니다. 공유 저장소와 큐 인프라는 여러 커뮤니티 스크래퍼가 공유할 수 있어 후속 공통 플랫폼 설계에서 다루는 편이 맞습니다.

B) Garage output storage와 PostgreSQL checkpoint storage를 참고사항으로만 기록한다.

C) 통합 커뮤니티 플랫폼까지 고려한 shared infrastructure를 지금 설계한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-005 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T17:30:12Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options preserve the baseline scraper JobRunner/checkpoint infrastructure boundary while using FMKorea package, port, and adapter handoff names.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure**: No shared infrastructure artifact is required for UOW-005. CLI wizard, container entrypoint, MCP hosting, PostgreSQL checkpoint adapter, parser-stage retry reprocessor, SQS/DLQ, Docker Compose, AWS CDK, and centralized platform scheduling remain deferred.

## Infrastructure Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/infrastructure-design/deployment-architecture.md`

승인 후 다음 단계는 `UOW-005 Code Generation`이다.
