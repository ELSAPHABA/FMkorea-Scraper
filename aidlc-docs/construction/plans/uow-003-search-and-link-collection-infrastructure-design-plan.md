# Infrastructure Design 계획 - UOW-003 Search And Link Collection

이 계획은 `UOW-003 Search And Link Collection`의 논리 컴포넌트를 실제 실행/검증 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-003 Search And Link Collection
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: import 가능한 link collection library, local/CI fixture tests, optional env-gated live smoke, UOW-002 HTTP dependency boundary
- **Likely Infrastructure Scope**: standalone deployment 없음, local/CI 검증 인프라와 optional live smoke 실행 경계만 해당
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 링크 수집 인프라 경계를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: post worker topology, queue ownership, checkpoint persistence, Garage/S3/PostgreSQL storage, container entrypoint, MCP server hosting, AWS CDK resources

## Infrastructure Design 작업 체크리스트

- [x] UOW-003 Functional Design 승인 확인
- [x] UOW-003 NFR Requirements 승인 확인
- [x] UOW-003 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-003 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-003은 import 가능한 link collection library이며, 독립 서비스/컨테이너 배포는 N/A로 문서화한다.

추천 사유: 이 unit은 검색/목록 링크 후보를 만드는 내부 계층입니다. 실제 CLI 실행, worker container, MCP hosting은 후속 unit에서 다루는 편이 책임이 작고 기존 구조 계승에 맞습니다.

B) local 개발/검증용 Python 실행 환경만 Infrastructure Design에 포함한다.

C) scraper worker/container 배포 환경까지 UOW-003에서 미리 정의한다.

X) 기타

[Answer]: A

### Question 2. Compute Infrastructure

UOW-003의 compute 인프라는 어디까지 정의할까요?

A) (권장) persistent compute는 없음. local 개발 환경과 CI test runner에서 unit/PBT/fixture 테스트를 실행한다고 문서화한다.

추천 사유: 링크 수집기는 JobRunner 프로세스 안에서 호출되는 라이브러리입니다. worker count, queue consumer, realtime loop는 UOW-005 책임으로 남기는 것이 기존 구조 계승에 맞습니다.

B) 개발용 Docker container만 정의한다.

C) 멀티 워커 container sizing과 scale-out 정책까지 정의한다.

X) 기타

[Answer]: A

### Question 3. Storage Infrastructure

UOW-003에서 저장소 인프라를 정의할까요?

A) (권장) 저장소 인프라는 정의하지 않는다. UOW-003은 후보 링크와 summary만 반환하고 JSONL/Garage/PostgreSQL 저장은 후속 unit에서 매핑한다.

추천 사유: 이 unit은 링크 수집 계층입니다. 저장소를 여기서 연결하면 후보 수집과 출력 idempotency 책임이 섞입니다.

B) local debug 파일 출력만 참고사항으로 정의한다.

C) Garage/S3와 PostgreSQL 저장 경로를 지금 확정한다.

X) 기타

[Answer]: A

### Question 4. Messaging And Queue Infrastructure

UOW-003에서 queue 또는 messaging infrastructure를 정의할까요?

A) (권장) 정의하지 않는다. UOW-003은 async iterator/list API만 제공하고, `asyncio.Queue`, SQS, worker queue ownership은 UOW-005 이후에 둔다.

추천 사유: 후보를 어떻게 큐에 넣고 몇 개 worker가 소비할지는 JobRunner의 실행 정책입니다. UOW-003은 후보 생성만 맡는 편이 단순합니다.

B) local `asyncio.Queue` 사용만 Infrastructure Design에 포함한다.

C) 향후 SQS Job Queue까지 UOW-003에서 미리 설계한다.

X) 기타

[Answer]: A

### Question 5. Networking Infrastructure

UOW-003의 네트워크 인프라는 어디까지 정의할까요?

A) (권장) 별도 네트워크 인프라는 없음. 모든 outbound request는 caller가 주입한 UOW-002 `HttpClient`를 통해 나간다고만 문서화한다.

추천 사유: proxy, User-Agent, cookie, timeout, retry, rate limit, CAPTCHA/차단 분류는 UOW-002 책임입니다. UOW-003이 네트워크 토폴로지를 알 필요가 없습니다.

B) FMKorea host별 egress 정책만 참고사항으로 기록한다.

C) VPC/NAT/proxy gateway topology를 지금 정의한다.

X) 기타

[Answer]: A

### Question 6. Monitoring Infrastructure

관측성 인프라는 어디까지 정의할까요?

A) (권장) 외부 monitoring stack은 N/A로 둔다. UOW-001 `LoggerPort`로 safe collector events와 summary를 내보내는 계약만 문서화한다.

추천 사유: 아직 실행 중인 worker service가 없습니다. Prometheus/OpenTelemetry 같은 수집 인프라는 runtime 배포 unit에서 붙이면 충분합니다.

B) local JSON log 파일 위치만 정한다.

C) OpenTelemetry, Prometheus, alerting까지 지금 정의한다.

X) 기타

[Answer]: A

### Question 7. Live Smoke Test Infrastructure

FMKorea live smoke test는 인프라 관점에서 어떻게 둘까요?

A) (권장) 기본 CI와 unit test에서는 제외하고, `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 별도 marker로 board list 1페이지 또는 integrated search 1페이지 수준 테스트를 실행한다고 문서화한다.

추천 사유: 외부 사이트 DOM과 차단 정책은 바뀔 수 있습니다. 기본 검증은 fixture로 고정하고 live smoke는 수동/선택 검증 경로로 두는 편이 안정적입니다.

B) 모든 CI에서 live smoke test를 필수로 실행한다.

C) live smoke test 경로를 아예 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 8. Shared Infrastructure

UOW-003에서 Garage, PostgreSQL, queue 같은 shared infrastructure를 확정할까요?

A) (권장) 확정하지 않는다. UOW-003은 link collection library만 제공하고, Garage/PostgreSQL/queue는 저장소/JobRunner/container/CDK unit에서 매핑한다.

추천 사유: 이 unit은 저장, 체크포인트, 작업 분산을 구현하지 않습니다. 지금 shared infrastructure를 잡으면 후속 unit 책임을 앞당기게 됩니다.

B) Garage output storage와 PostgreSQL checkpoint storage를 참고사항으로만 기록한다.

C) 통합 커뮤니티 플랫폼까지 고려한 shared infrastructure를 지금 설계한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-003 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T05:38:14Z
- **Selected Options**: Q1-Q8 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper link collection infrastructure boundary as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure**: No shared infrastructure artifact is required for UOW-003.

## Infrastructure Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-003-search-and-link-collection/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/uow-003-search-and-link-collection/infrastructure-design/deployment-architecture.md`

승인 후 다음 단계는 `UOW-003 Code Generation`이다.
