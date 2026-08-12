# Infrastructure Design 계획 - UOW-001 Core Models And Config

이 계획은 `UOW-001 Core Models And Config`의 논리 컴포넌트를 실제 인프라 선택지에 매핑할 필요가 있는지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-001 Core Models And Config
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: Pydantic 모델, validation, error redaction, schema compatibility, property-based tests, port protocol의 인프라 적용 여부
- **Likely Infrastructure Scope**: runtime 배포 인프라 없음, local/CI 검증 인프라만 해당
- **Out Of Scope**: concrete HTTP client, parser, scraper worker runtime, Garage/PostgreSQL adapter, container deployment, MCP server deployment

## Infrastructure Design 작업 체크리스트

- [x] UOW-001 Functional Design 승인 확인
- [x] UOW-001 NFR Requirements 승인 확인
- [x] UOW-001 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 불필요 확인
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 불필요 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-001 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-001은 import 가능한 모델/설정/포트 계약 패키지이며, 별도 배포 환경은 N/A로 문서화한다.

추천 사유: 이 unit은 네트워크 요청, 파싱, 저장, 워커 실행을 구현하지 않습니다. 배포 환경을 잡기 시작하면 후속 unit의 책임까지 앞당겨집니다.

B) local 개발/검증용 Python 패키지 실행 환경만 Infrastructure Design에 포함한다.

C) scraper worker/container 배포 환경까지 UOW-001에서 미리 매핑한다.

[Answer]: A

### Question 2. Compute Infrastructure

UOW-001의 compute 인프라는 어디까지 정의할까요?

A) (권장) persistent compute는 없음. local 개발 환경과 CI test runner에서만 모델 검증, PBT, schema diff를 실행한다고 문서화한다.

추천 사유: UOW-001은 순수 모델 계층입니다. worker container, queue consumer, scheduler는 후속 unit에서 결정하는 편이 책임이 작습니다.

B) 개발용 Docker container만 정의한다.

C) scraper worker container sizing과 scale-out 정책까지 정의한다.

[Answer]: A

### Question 3. Storage Infrastructure

schema snapshot과 migration note는 어디에 저장할까요?

A) (권장) repository 내부 fixture와 문서로 저장한다. 예: `tests/snapshots/`, `aidlc-docs/`, migration note 파일.

추천 사유: UOW-001의 persisted schema compatibility 검사는 코드 변경 검증용입니다. Garage/PostgreSQL 같은 외부 저장소는 실제 출력/체크포인트 adapter unit에서 다루면 충분합니다.

B) Garage 같은 S3-compatible object storage에 schema snapshot을 저장한다.

C) PostgreSQL schema registry를 둔다.

[Answer]: A

### Question 4. Messaging Infrastructure

UOW-001에서 queue, broker, event bus 같은 messaging 인프라를 정의할까요?

A) (권장) 정의하지 않는다. `WorkerConfig`와 port protocol만 두고, 실제 queue는 scraper runner/worker unit에서 결정한다.

추천 사유: UOW-001에는 producer/consumer 런타임이 없습니다. 지금 broker를 고르면 구현 전 가정만 늘어납니다.

B) in-memory queue 전제를 문서화한다.

C) Redis, SQS, RabbitMQ 같은 concrete broker 후보를 Infrastructure Design에 포함한다.

[Answer]: A

### Question 5. Networking Infrastructure

UOW-001에서 load balancer, API gateway, VPC, outbound proxy 같은 networking 인프라를 정의할까요?

A) (권장) networking 인프라는 N/A로 둔다. `HttpPort`는 계약만 정의하고, Proxy/User-Agent 실제 적용은 HTTP adapter unit에서 설계한다.

추천 사유: 이 unit은 네트워크를 호출하지 않습니다. proxy나 egress 정책은 실제 HTTP 구현 시점에 결정해야 정확합니다.

B) outbound proxy 사용 가능성만 deployment architecture에 참고사항으로 남긴다.

C) proxy gateway, VPC, NAT, rate-limit network topology를 지금 정의한다.

[Answer]: A

### Question 6. Monitoring Infrastructure

UOW-001에서 관측성 인프라는 어디까지 정의할까요?

A) (권장) 외부 monitoring stack은 N/A로 둔다. `LoggerPort`, safe error result, test output만 문서화한다.

추천 사유: 모델 unit에서 Prometheus/OpenTelemetry 같은 runtime 관측성을 붙이면 실제 scrape runtime 없이 빈 껍데기만 생깁니다.

B) local JSON log 파일 위치만 정한다.

C) OpenTelemetry, Prometheus, alerting까지 지금 정의한다.

[Answer]: A

### Question 7. Shared Infrastructure

UOW-001에서 Garage, PostgreSQL, shared credential store 같은 shared infrastructure를 확정할까요?

A) (권장) 확정하지 않는다. UOW-001은 `StorageConfig`와 port 계약만 provider-neutral하게 정의하고, Garage/PostgreSQL adapter는 후속 unit에서 매핑한다.

추천 사유: shared infrastructure는 실제 저장/체크포인트 구현이 있는 unit에서 결정해야 중복과 선행 설계를 줄일 수 있습니다.

B) Garage output storage와 PostgreSQL checkpoint storage를 shared infrastructure 초안으로만 기록한다.

C) 모든 후속 scraper/통합 플랫폼까지 고려해 multi-tenant shared infrastructure를 지금 설계한다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-001 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- Q1-Q7은 모두 A로 확정되었다.
- 답변 간 충돌은 없다.
- follow-up 질문은 필요하지 않다.
- shared infrastructure 산출물은 만들지 않는다.

## Infrastructure Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-001-core-models-and-config/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/uow-001-core-models-and-config/infrastructure-design/deployment-architecture.md`

승인 후 다음 단계는 `UOW-001 Code Generation`이다.
