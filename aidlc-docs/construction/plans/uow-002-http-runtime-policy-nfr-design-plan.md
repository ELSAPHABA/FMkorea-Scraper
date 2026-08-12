# NFR Design 계획 - UOW-002 HTTP Runtime Policy

이 계획은 `UOW-002 HTTP Runtime Policy`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-002 HTTP Runtime Policy
- **NFR Requirements**: 승인됨
- **Scope**: HTTP client lifecycle pattern, retry/backoff pattern, rate limiter pattern, response classification pattern, secret masking pattern, safe logging pattern, deterministic test harness
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 HTTP runtime 구조를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: FMKorea URL/query builders, BeautifulSoup parsers, storage/checkpoint persistence, CLI wizard, container entrypoint, MCP tools, cloud observability backend

## NFR Design 작업 체크리스트

- [x] UOW-002 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. HTTP package component layout

HTTP runtime 컴포넌트는 어떤 모듈 구조로 나눌까요?

A) (권장) `src/fmkorea_scraper/http/` 아래에 `client.py`, `rate_limit.py`, `retry.py`, `user_agent.py`, `proxy.py`, `cookies.py`, `classify.py`, `logging.py`를 둔다.

추천 사유: 디시인사이드 스크래퍼의 HTTP 경계 분리 방식을 계승하면서 각 정책을 작은 파일로 격리할 수 있습니다. 하나의 거대한 client 파일보다 테스트와 변경이 쉽고, 과한 interface 계층은 만들지 않습니다.

B) 모든 HTTP runtime 로직을 `http/client.py` 하나에 모은다.

C) 각 정책마다 별도 package와 abstract interface를 만든다.

[Answer]: A

### Question 2. HttpClient construction pattern

`HttpClient` 생성은 어떤 패턴으로 처리할까요?

A) (권장) `HttpClient.from_job_config(job_config, *, env, logger, clock, transport=None)` 같은 factory classmethod를 두고, 내부에서 provider와 `httpx.AsyncClient` 설정을 조립한다.

추천 사유: 디시인사이드 스크래퍼의 JobConfig 중심 구성을 계승하면서, 테스트에서는 `MockTransport`를 주입하고 adapter는 env/proxy/cookie 값을 넘기기만 하면 됩니다.

B) adapter가 모든 provider를 직접 만들고 `HttpClient` 생성자에 전부 넘긴다.

C) `HttpClient`가 import 시 전역 설정을 읽어 자동 생성된다.

[Answer]: A

### Question 3. RateLimiter time source

RateLimiter의 시간 측정과 대기는 어떻게 주입할까요?

A) (권장) UOW-001 `ClockPort`를 사용하되, 코드 생성에서는 기본 `AsyncioClock` 구현과 테스트용 `FakeClock`만 둔다.

추천 사유: 기존 스크래퍼의 fake clock 기반 deterministic test 방향을 계승합니다. 실제 sleep을 테스트에서 기다리지 않아도 rate limit 로직을 검증할 수 있습니다.

B) `time.monotonic()`과 `asyncio.sleep()`을 RateLimiter 내부에서 직접 호출한다.

C) 외부 scheduler/rate-limit 서비스를 전제로 설계한다.

[Answer]: A

### Question 4. Retry/backoff component pattern

retry/backoff는 어떤 컴포넌트로 분리할까요?

A) (권장) 순수 함수/작은 value object인 `RetryPolicy`가 `should_retry(response_or_error)`와 `backoff_seconds(attempt)`를 제공하고, `HttpClient`는 실행 루프만 담당한다.

추천 사유: 디시인사이드 스크래퍼의 정책-실행 분리 구조를 계승합니다. retry predicate와 backoff는 PBT로 검증하기 쉽고, HTTP 실행 코드는 얇게 유지됩니다.

B) retry 판단과 backoff 계산을 `HttpClient.get()` 내부에 직접 작성한다.

C) 외부 retry 라이브러리를 도입한다.

[Answer]: A

### Question 5. ResponseClassifier extensibility

CAPTCHA/차단/로그인 필요 분류 로직은 어떻게 확장 가능하게 둘까요?

A) (권장) `ResponseClassifier`에 status/header 기반 기본 분류와 bounded body marker 검사 함수를 두고, FMKorea-specific marker 목록은 상수/설정으로 주입 가능하게 한다.

추천 사유: 디시인사이드 스크래퍼의 “HTTP 계층은 분류 hook만 제공하고 사이트 marker는 나중 fixture로 보강”하는 구조를 계승합니다.

B) 모든 marker를 `HttpClient` 내부 if문에 직접 하드코딩한다.

C) response classification을 UOW-003/UOW-004 parser에 전부 맡긴다.

[Answer]: A

### Question 6. Secret masking pattern

Proxy/cookie secret masking은 어떤 방식으로 구현할까요?

A) (권장) `SecretStr`와 safe `__repr__`/`to_safe_dict()`를 가진 `ProxyConfig`, `CookieConfig`를 두고, log/error 변환은 allowlist 기반 sanitizer를 한 번 더 통과시킨다.

추천 사유: 기존 스크래퍼의 중복 방어 방식을 계승합니다. 객체 표현에서 한 번, 로그/오류 출력에서 한 번 막으면 실수로 원문이 새는 가능성이 줄어듭니다.

B) 로그 작성 함수에서만 마스킹한다.

C) 개발 중에는 마스킹하지 않고 운영 전에 추가한다.

[Answer]: A

### Question 7. Safe log sanitizer pattern

URL과 HTTP event를 안전하게 로그로 바꾸는 로직은 어디에 둘까요?

A) (권장) `logging.py`에 `sanitize_url_for_log(url)`와 `HttpLogEvent` builder를 두고, raw query/body/header secret은 구조적으로 버린다.

추천 사유: 로그 sanitize 규칙이 `HttpClient` 곳곳에 흩어지지 않고, PBT로 “query가 절대 포함되지 않는다” 같은 속성을 검증하기 쉽습니다.

B) 각 요청 메서드에서 필요한 만큼 문자열 split으로 처리한다.

C) logger adapter가 URL 전체를 받은 뒤 알아서 마스킹한다.

[Answer]: A

### Question 8. Connection limit pattern

connection pool limit 계산은 어디서 처리할까요?

A) (권장) `HttpClientConfig` value object가 `WorkerConfig`와 override 값을 받아 `max_connections`, `max_keepalive_connections`를 계산하고, `HttpClient`는 그 결과만 사용한다.

추천 사유: 기존 스크래퍼의 worker 수 기반 제한을 계승하면서도 계산식을 한 곳에 두어 테스트하기 쉽습니다.

B) `HttpClient` 생성자 내부에서 worker count를 직접 읽고 계산한다.

C) connection limit 계산을 하지 않고 httpx 기본값만 사용한다.

[Answer]: A

### Question 9. Test harness component design

HTTP 정책 테스트용 fake/mock 컴포넌트는 어디까지 만들까요?

A) (권장) `tests/http/` 또는 기존 `tests/` 하위에 `FakeClock`, `FakeLogger`, `MockTransport` helper를 두고, production code에는 테스트 전용 helper를 넣지 않는다.

추천 사유: 디시인사이드 스크래퍼의 production/test 경계 분리 방향을 계승합니다. 테스트 helper가 runtime package에 들어가면 사용 API가 불필요하게 넓어집니다.

B) production package 안에 테스트 helper도 함께 제공한다.

C) helper 없이 각 테스트 함수에서 전부 inline으로 만든다.

[Answer]: A

### Question 10. Circuit breaker scope

UOW-002에 circuit breaker를 포함할까요?

A) (권장) UOW-002에는 circuit breaker를 구현하지 않고, timeout/retry/rate-limit/response classification까지만 둔다. 연속 차단/실패에 따른 Job 중단 판단은 UOW-005에서 처리한다.

추천 사유: 기존 스크래퍼의 단순 HTTP 정책 경계를 계승합니다. 아직 Job runner와 checkpoint가 없기 때문에 circuit breaker를 지금 넣으면 상태 관리가 과해집니다.

B) UOW-002에서 host별 circuit breaker를 구현한다.

C) 외부 circuit breaker 라이브러리를 도입한다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-002 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T04:15:06Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper HTTP runtime structure as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-002-http-runtime-policy/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-002 Infrastructure Design`이다.
