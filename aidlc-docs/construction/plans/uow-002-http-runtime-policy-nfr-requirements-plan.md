# NFR Requirements 계획 - UOW-002 HTTP Runtime Policy

이 계획은 `UOW-002 HTTP Runtime Policy`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다. 답변이 확정되기 전에는 NFR Requirements 산출물을 생성하지 않습니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-002 HTTP Runtime Policy
- **Functional Design**: 승인됨
- **Scope**: `httpx.AsyncClient`, Job-scoped rate limiting, retry/backoff, timeout, User-Agent rotation, proxy/cookie policy, response classification, safe logging
- **Relevant Extensions**: Security Baseline, Resiliency Baseline, Property-Based Testing
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 HTTP runtime 경계를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: FMKorea URL/query builders, BeautifulSoup parsers, storage/checkpoint persistence, CLI wizard, container entrypoint, MCP tools

## NFR Requirements 작업 체크리스트

- [x] UOW-002 Functional Design 승인 확인
- [x] Security, Resiliency, PBT extension 적용 여부 확인
- [x] NFR 질문 생성
- [x] NFR 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-requirements/tech-stack-decisions.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Questions

### Question 1. HTTP dependency policy

HTTP runtime dependency는 어떻게 둘까요?

A) (권장) `httpx>=0.27,<1`을 runtime dependency로 추가하고, User-Agent/proxy/cookie 처리는 별도 패키지 없이 stdlib와 httpx 설정만 사용한다.

추천 사유: 디시인사이드 스크래퍼의 핵심 구조인 `httpx.AsyncClient` 중심 경계를 계승하면서, UA 파일 읽기/순환이나 proxy URL 조립은 별도 dependency가 필요 없습니다. 의존성 표면을 줄이면 보안/빌드 관리도 단순합니다.

B) `httpx`와 별도 User-Agent parsing/rotation 라이브러리를 함께 사용한다.

C) `aiohttp`로 HTTP runtime을 구현한다.

[Answer]: A

### Question 2. timeout defaults

기본 timeout 값은 어떻게 설정할까요?

A) (권장) page/comment 요청 기본 timeout은 adapter가 만든 `HttpRuntimeConfig.timeout`의 30초를 사용하고, media download는 별도 기본 120초를 둔다. timeout은 CLI/container/MCP/library adapter 입력으로 override 가능하게 한다.

추천 사유: 디시인사이드 스크래퍼의 명시 timeout 정책을 계승하면서, HTML 페이지와 대용량 미디어 다운로드의 특성을 분리할 수 있습니다.

B) 모든 요청에 동일하게 30초 timeout만 사용한다.

C) timeout을 설정하지 않고 httpx 기본값에 맡긴다.

[Answer]: A

### Question 3. retry and backoff defaults

retry/backoff 기본값은 어떻게 둘까요?

A) (권장) 최대 3회 attempt, base backoff 1초, max backoff 30초, 작은 jitter를 기본값으로 둔다. retry 대상은 network error, timeout, 429, 5xx로 제한한다.

추천 사유: 기존 스크래퍼 계승 방향인 “일시 장애만 재시도하고 차단/CAPTCHA는 반복하지 않음”을 지키면서 과도한 요청 폭주를 막습니다.

B) 최대 1회 retry만 허용하고 backoff는 고정 1초로 둔다.

C) 최대 5회 이상 retry하고 backoff를 길게 둔다.

[Answer]: A

### Question 4. rate limiter implementation quality

Job-scoped rate limiter는 어떤 품질 기준으로 설계할까요?

A) (권장) `asyncio.Lock` 기반으로 Job 내부 요청 간격을 직렬화하고, 시간 측정/대기는 `ClockPort` 또는 fake clock으로 주입 가능하게 한다.

추천 사유: 디시인사이드 스크래퍼의 Job 단위 공용 제한 구조를 계승하면서, 멀티 워커 경쟁 조건과 테스트 flakiness를 줄일 수 있습니다.

B) lock 없이 각 요청이 독립적으로 `asyncio.sleep()`만 호출한다.

C) 외부 rate-limit 라이브러리를 추가한다.

[Answer]: A

### Question 5. connection pool limits

`httpx.AsyncClient` connection pool은 어떻게 제한할까요?

A) (권장) Job의 worker 설정을 기준으로 bounded pool을 만들고, 기본은 `post_worker_count + media_worker_count + 2` 수준의 최대 연결 수를 사용한다. 최종 수치는 설정으로 override 가능하게 한다.

추천 사유: 기존 스크래퍼의 worker 수 기반 제어를 계승하면서, connection pool이 worker 수보다 과하게 커져 사이트나 로컬 리소스에 부담을 주는 상황을 막습니다.

B) httpx 기본 connection limit을 그대로 사용한다.

C) 매우 큰 고정 connection limit을 둔다.

[Answer]: A

### Question 6. response body handling

응답 본문은 메모리/보안 관점에서 어떻게 다룰까요?

A) (권장) page/comment 응답은 parser가 사용할 수 있도록 text를 반환하되, classification은 제한된 body sample만 검사하고 로그에는 body를 남기지 않는다. media download는 bytes를 반환하되 저장은 UOW-006이 담당한다.

추천 사유: BeautifulSoup 파싱을 위해 본문은 필요하지만, classification/logging에서 전체 본문을 다루면 메모리와 민감정보 노출 위험이 커집니다.

B) 모든 응답 본문 전체를 classification과 로그에 사용한다.

C) HTTP 계층은 본문을 반환하지 않고 status code만 반환한다.

[Answer]: A

### Question 7. secret handling and masking

Proxy/cookie/Authorization 계열 secret은 어떤 기준으로 보호할까요?

A) (권장) proxy password와 cookie 값은 `SecretStr` 또는 동등한 masked value로 보관하고, `repr`, log event, failure detail, error detail에 원문이 절대 나오지 않게 한다.

추천 사유: 디시인사이드 스크래퍼의 secret-safe logging 정책을 계승합니다. 평문 `.env` 저장은 adapter 운영 예외지만 core runtime은 secret을 노출하지 않아야 합니다.

B) 로그에는 마스킹하되 exception message에는 원문을 허용한다.

C) 개발 편의를 위해 debug 로그에서만 원문을 허용한다.

[Answer]: A

### Question 8. observability contract

UOW-002는 observability를 어디까지 제공할까요?

A) (권장) metric backend는 만들지 않고, `LoggerPort`로 안전한 structured event를 emit한다. event 필드는 method, host, path, status, kind, attempt, elapsed, request_kind로 제한한다.

추천 사유: 기존 스크래퍼처럼 core는 adapter-neutral로 유지하고, 중앙 로그/CloudWatch/컨테이너 로그 연결은 이후 adapter/infra UOW에서 담당하는 편이 경계가 깨끗합니다.

B) UOW-002에서 자체 metrics collector와 파일 로그 저장까지 구현한다.

C) HTTP runtime은 아무 로그도 남기지 않는다.

[Answer]: A

### Question 9. property-based test scope

UOW-002의 Property-Based Testing 범위는 어떻게 둘까요?

A) (권장) User-Agent rotation, retry predicate, bounded backoff, proxy masking, safe log URL sanitization, response classification invariant를 PBT 대상으로 둔다. 실제 HTTP 요청은 `httpx.MockTransport` example test로 검증한다.

추천 사유: HTTP runtime은 상태/정책 불변조건이 많아 PBT 효과가 큽니다. 반면 live network는 재현성이 낮으므로 기본 테스트에서 제외하는 기존 구조를 계승합니다.

B) PBT는 User-Agent rotation에만 적용한다.

C) UOW-002에서는 PBT를 사용하지 않는다.

[Answer]: A

### Question 10. default test environment

기본 테스트 환경은 어떻게 구성할까요?

A) (권장) live network 없이 `httpx.MockTransport`, fake clock/fake logger, pytest, Hypothesis로 결정적 테스트만 실행한다. 실제 FMKorea smoke test는 UOW-008 이후 opt-in hook으로 둔다.

추천 사유: 디시인사이드 스크래퍼의 “기본 테스트는 재현 가능하게, live smoke는 선택적으로”라는 방향을 계승합니다. HTTP 정책 단위 테스트는 외부 사이트 상태에 의존할 필요가 없습니다.

B) 매 테스트마다 실제 FMKorea 요청을 한 번 이상 수행한다.

C) HTTP 테스트는 전부 수동 smoke test로만 수행한다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-002 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 NFR Design으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T03:58:55Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper HTTP runtime structure as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## NFR Requirements Review Gate

검토 대상:

- `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-requirements/tech-stack-decisions.md`

승인 후 다음 단계는 `UOW-002 NFR Design`이다.
