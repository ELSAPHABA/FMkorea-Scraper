# Infrastructure Design 계획 - UOW-002 HTTP Runtime Policy

이 계획은 `UOW-002 HTTP Runtime Policy`의 논리 컴포넌트를 실제 실행/검증 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-002 HTTP Runtime Policy
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: import 가능한 HTTP runtime, local/CI test runner, execution-location `.env`, `user-agents.txt`, outbound proxy configuration, optional live smoke test
- **Likely Infrastructure Scope**: standalone deployment 없음, local/CI 검증 인프라와 runtime file/env boundary만 해당
- **Out Of Scope**: search/post parser worker topology, Garage/PostgreSQL adapter, container entrypoint implementation, scheduler/queue, MCP server hosting

## Infrastructure Design 작업 체크리스트

- [x] UOW-002 Functional Design 승인 확인
- [x] UOW-002 NFR Requirements 승인 확인
- [x] UOW-002 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-002 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-002는 import 가능한 HTTP runtime 라이브러리이며, 독립 서비스/컨테이너 배포는 N/A로 문서화한다.

추천 사유: 이 unit은 HTTP 정책만 구현합니다. 실제 worker container, CLI 실행, MCP hosting은 후속 unit에서 다루는 편이 책임이 작고, 기존 스크래퍼 구조도 이 경계를 유지합니다.

B) local 개발/검증용 Python 실행 환경만 Infrastructure Design에 포함한다.

C) scraper worker/container 배포 환경까지 UOW-002에서 미리 정의한다.

X) 기타

[Answer]: A

### Question 2. Compute Infrastructure

UOW-002의 compute 인프라는 어디까지 정의할까요?

A) (권장) persistent compute는 없음. local 개발 환경과 CI test runner에서 unit/PBT/fake transport 테스트를 실행한다고 문서화한다.

추천 사유: HTTP runtime은 worker process 안에서 사용되는 라이브러리입니다. scale-out, worker count, queue consumer는 JobRunner/worker unit 책임으로 남기는 것이 기존 구조 계승에 맞습니다.

B) 개발용 Docker container만 정의한다.

C) 멀티 워커 container sizing과 scale-out 정책까지 정의한다.

X) 기타

[Answer]: A

### Question 3. Runtime File Location

`.env`와 `user-agents.txt`의 실행 위치는 어떻게 정의할까요?

A) (권장) explicit path가 있으면 우선 사용하고, 없으면 execution location의 `.env`와 `user-agents.txt`를 runtime creation 시점에만 읽는다. 파일 생성/편집 UX는 후속 CLI/container unit으로 미룬다.

추천 사유: UOW-002는 파일을 읽는 경계만 갖고, 파일 생성과 터미널 안내는 adapter가 처리해야 import side effect를 피할 수 있습니다.

B) UOW-002가 실행 파일 위치를 직접 판단하고 누락 파일을 생성한다.

C) `.env`와 `user-agents.txt`를 패키지 내부 resource로 고정한다.

X) 기타

[Answer]: A

### Question 4. Networking And Proxy Infrastructure

outbound proxy/networking 인프라는 어디까지 정의할까요?

A) (권장) concrete proxy gateway, VPC, NAT는 정의하지 않는다. UOW-002는 `httpx.AsyncClient(proxy=..., trust_env=False)` 설정과 redacted proxy label만 문서화한다.

추천 사유: 사용자의 proxy는 host/ID/PW 입력 또는 `.env`에서 오는 runtime 설정입니다. 네트워크 토폴로지는 container/운영 배포 unit에서 결정해야 정확합니다.

B) local proxy gateway 사용 가능성만 참고사항으로 기록한다.

C) proxy pool, NAT gateway, egress topology를 지금 정의한다.

X) 기타

[Answer]: A

### Question 5. Secret And Configuration Storage

Proxy secret 저장 인프라는 어떻게 볼까요?

A) (권장) UOW-002에서는 plaintext `.env`를 문서화된 local/container 예외로 인정하되, secret manager는 도입하지 않는다. raw `.env`와 password는 logging/error boundary에서 redaction한다.

추천 사유: 기능명세서가 평문 `.env` 저장을 요구합니다. 이 unit에서는 저장소를 바꾸기보다 노출 경계를 막는 것이 실제 책임입니다.

B) local은 `.env`, container는 secret manager 사용을 UOW-002에서 필수화한다.

C) proxy secret을 암호화 파일로 저장하도록 UOW-002에서 변경한다.

X) 기타

[Answer]: A

### Question 6. Monitoring Infrastructure

관측성 인프라는 어디까지 정의할까요?

A) (권장) 외부 monitoring stack은 N/A로 둔다. UOW-001 `LoggerPort`로 safe structured event를 내보내는 계약만 문서화한다.

추천 사유: 아직 실행 중인 worker service가 없습니다. Prometheus/OpenTelemetry 같은 수집 인프라는 실제 runtime 배포 unit에서 붙이면 충분합니다.

B) local JSON log 파일 위치만 정한다.

C) OpenTelemetry, Prometheus, alerting까지 지금 정의한다.

X) 기타

[Answer]: A

### Question 7. Live Smoke Test Infrastructure

FMKorea live smoke test는 인프라 관점에서 어떻게 둘까요?

A) (권장) 기본 CI와 unit test에서는 제외하고, `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 별도 marker로 단일 HEAD/GET 수준 테스트를 실행한다고 문서화한다.

추천 사유: 외부 사이트 상태와 차단 정책에 따른 flaky test를 기본 검증 경로에서 분리할 수 있습니다.

B) 모든 CI에서 live smoke test를 필수로 실행한다.

C) live smoke test 경로를 아예 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 8. Shared Infrastructure

UOW-002에서 Garage, PostgreSQL, queue 같은 shared infrastructure를 확정할까요?

A) (권장) 확정하지 않는다. UOW-002는 HTTP runtime만 제공하고, Garage/PostgreSQL/queue는 저장소/JobRunner/container unit에서 매핑한다.

추천 사유: 이 unit은 저장, 체크포인트, 작업 분산을 구현하지 않습니다. 지금 shared infrastructure를 잡으면 후속 unit 책임을 앞당기게 됩니다.

B) Garage output storage와 PostgreSQL checkpoint storage를 참고사항으로만 기록한다.

C) 통합 커뮤니티 플랫폼까지 고려한 shared infrastructure를 지금 설계한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-002 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T04:27:47Z
- **Selected Options**: Q1-Q8 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper HTTP runtime infrastructure boundary as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure**: No shared infrastructure artifact is required for UOW-002.

## Infrastructure Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-002-http-runtime-policy/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/uow-002-http-runtime-policy/infrastructure-design/deployment-architecture.md`

승인 후 다음 단계는 `UOW-002 Code Generation`이다.
