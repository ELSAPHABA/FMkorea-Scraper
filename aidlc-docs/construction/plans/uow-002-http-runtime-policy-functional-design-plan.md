# UOW-002 HTTP Runtime Policy Functional Design Plan

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-002 HTTP Runtime Policy
- **Goal**: 모든 외부 HTTP 요청에 timeout, retry, 요청 간격, User-Agent rotation, Proxy, 임시 cookie 메모리 처리, CAPTCHA/차단 분류 정책을 일관되게 적용한다.
- **Primary Stories**: US-002, US-003
- **Supporting Stories**: US-004, US-005, US-007, US-012
- **Depends On**: UOW-001 Core Models And Config
- **Boundaries**:
  - FMKorea URL/query 생성은 UOW-003에서 구현한다.
  - 게시글/댓글/본문 HTML 파싱은 UOW-004에서 구현한다.
  - Job runner, checkpoint 저장, worker queue lifecycle은 UOW-005에서 구현한다.
  - CLI 마법사와 `.env` 생성/편집 flow는 UOW-007에서 구현한다.
  - 컨테이너 entrypoint의 env 주입 flow는 UOW-008에서 구현한다.

## Functional Design 작업 체크리스트

- [x] Unit of Work 산출물 확인
- [x] Application Design 산출물 확인
- [x] 기능 명세서의 HTTP/User-Agent/Proxy/Cookie/속도제어/CAPTCHA 정책 확인
- [x] Functional Design 질문 생성
- [x] 모든 `[Answer]:` 답변 확인
- [x] 답변 모호함 및 충돌 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `domain-entities.md` 생성
- [x] `business-rules.md` 생성
- [x] `business-logic-model.md` 생성
- [x] Functional Design review gate 생성

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T03:50:05Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper structure as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## Functional Design 질문

### Question 1. HttpClient 생명주기

`httpx.AsyncClient`는 어떤 단위로 만들고 닫을까요?

A) (권장) Job 실행 단위로 `HttpClient` 1개를 만들고, 링크 수집 워커와 게시글 워커가 공유한 뒤 Job 종료 시 명시적으로 닫는다.

추천 사유: connection pool을 재사용하면서도 Job별 proxy/cookie/User-Agent 정책을 분리할 수 있습니다. 요청 1회마다 client를 만들면 connection 재사용 이점이 사라지고, process 전역 singleton은 Job별 설정 충돌이 생깁니다.

B) 게시글 상세 요청 1건마다 `HttpClient`를 새로 만들고 닫는다.

C) 프로세스 전역 singleton `HttpClient`를 사용한다.

[Answer]: A

### Question 2. 요청 속도 제한 범위

요청 간격 제한은 어떤 범위에 적용할까요?

A) (권장) 프로세스 내부 Job 단위의 공용 async rate limiter를 두고, 목록/검색/상세/댓글/미디어 다운로드 모든 외부 요청 전에 동일하게 적용한다.

추천 사유: 기능 명세서가 모든 요청에 동일한 속도 조절을 요구하고, 멀티 워커 환경에서는 워커별 제한보다 Job 단위 공용 제한이 실제 요청량을 예측하기 쉽습니다.

B) 워커별로 독립 rate limiter를 둔다.

C) 목록/검색/상세 요청에만 적용하고 미디어 다운로드에는 적용하지 않는다.

[Answer]: A

### Question 3. Retry 대상과 backoff

자동 retry는 어떤 응답/오류에 적용할까요?

A) (권장) network error, timeout, 5xx, 429만 제한 횟수 retry하고 exponential backoff + 작은 jitter를 적용한다. CAPTCHA, 차단, 404, 로그인 필요, 삭제/비공개 등은 retry하지 않고 분류 결과를 반환하거나 typed error로 처리한다.

추천 사유: 일시 장애는 회복 가능하지만 CAPTCHA/차단/삭제/권한 문제를 반복 요청하면 차단 위험과 낭비가 커집니다.

B) retry 없이 첫 실패를 그대로 반환한다.

C) 모든 non-200 응답을 동일하게 retry한다.

[Answer]: A

### Question 4. 응답 분류 반환 방식

CAPTCHA/차단/로그인 필요/삭제/서버 오류 같은 상태는 `HttpClient`가 어떻게 전달할까요?

A) (권장) `HttpResponse` value object에 `status_code`, `headers`, `text/bytes`, `final_url`, `kind: ResponseKind`를 담아 반환하고, checkpoint 중단 여부는 상위 service/job runner가 결정한다.

추천 사유: HTTP 계층은 사이트 응답을 분류만 하고 checkpoint를 직접 알지 않는 편이 경계가 단순합니다. 검색/상세/parser 계층은 같은 응답 객체를 보고 각자 필요한 결정을 할 수 있습니다.

B) `HttpClient`가 CAPTCHA/차단 감지 즉시 typed exception을 던진다.

C) `httpx.Response`를 그대로 반환하고 분류는 각 parser/service가 직접 한다.

[Answer]: A

### Question 5. User-Agent rotation 규칙

User-Agent 교체 카운터는 어떤 방식으로 운영할까요?

A) (권장) Job 내부 공용 `UserAgentProvider`가 유효한 UA 목록을 순서대로 순환하고, 모든 외부 요청 attempt 기준으로 `user_agent_rotate_every`회마다 다음 UA로 교체한다. 파일이 없거나 비어 있으면 기본 UA 하나로 fallback한다.

추천 사유: 기능 명세서의 기본값인 10회마다 교체와 멀티 워커 공용 카운터 요구를 그대로 만족합니다. retry attempt도 실제 외부 요청이므로 카운터에 포함하는 편이 예측 가능합니다.

B) 워커별 독립 카운터로 교체한다.

C) 요청마다 무작위 UA를 선택한다.

[Answer]: A

### Question 6. Proxy 설정 책임

Proxy 설정 로드와 적용 책임은 어디에 둘까요?

A) (권장) UOW-002는 `ProxyProvider`가 explicit proxy 값 또는 env mapping을 받아 `httpx` 설정으로 변환하는 순수 로직만 가진다. `.env` 파일 생성/편집과 터미널 입력은 UOW-007/UOW-008 adapter가 담당한다.

추천 사유: core import side-effect safety를 지키면서도 CLI/컨테이너가 같은 proxy 변환 로직을 재사용할 수 있습니다.

B) UOW-002가 직접 `.env` 파일을 읽고 없으면 생성한다.

C) `httpx`의 기본 환경변수 proxy 처리에만 맡기고 별도 provider를 만들지 않는다.

[Answer]: A

### Question 7. Cookie 적용 방식

Cookie는 어떻게 사용할까요?

A) (권장) 사용자 제공 cookie 파일과 정적 `Cookie` header 입력은 지원하지 않는다. 서버가 내려준 `Set-Cookie`는 현재 `HttpClient` 메모리 안에서만 임시 유지하고, User-Agent 교체 또는 client 종료 시 reset한다.

추천 사유: 기준 프로젝트와 동일한 동작입니다. 공개 콘텐츠 수집 범위를 넘지 않으면서, 서버가 정상 흐름에서 요구하는 임시 cookie만 최소 범위로 처리할 수 있습니다.

B) `httpx` cookie jar를 Job 내내 유지하고 User-Agent 교체 시에도 유지한다.

C) 사용자가 제공한 cookie file을 읽어 정적 `Cookie` header로 붙인다.

[Answer]: A

### Question 8. 요청 로그와 secret masking

HTTP 요청/응답 로그는 어떤 수준으로 남길까요?

A) (권장) method, host, path, status, `ResponseKind`, attempt, elapsed time만 남기고, raw query, Cookie, Authorization, Proxy 인증정보, `.env` 값은 기록하지 않는다.

추천 사유: 장애 진단에는 요청 위치와 분류가 필요하지만, proxy/cookie 값은 로그나 failure/checkpoint에 남기면 안 됩니다.

B) Cookie/Authorization만 제거하고 raw query를 포함한 URL 전체를 로그에 남긴다.

C) HTTP 로그를 전혀 남기지 않는다.

[Answer]: A

### Question 9. 미디어 다운로드 요청 정책

이미지/동영상 파일 다운로드 요청은 어떤 HTTP 정책을 사용할까요?

A) (권장) 같은 `HttpClient`, rate limiter, timeout, User-Agent, Proxy 정책을 사용한다. 다만 다운로드 timeout은 설정으로 분리할 수 있게 하고, 파일 저장 자체는 UOW-006/UOW-004로 넘긴다.

추천 사유: 미디어 다운로드도 외부 요청이라 차단/속도 정책을 우회하면 안 됩니다. 저장 책임만 분리하면 UOW-002 범위를 넘지 않습니다.

B) 미디어 다운로드는 별도 raw `httpx` client를 사용한다.

C) UOW-002에서는 미디어 다운로드용 요청 함수를 제공하지 않는다.

[Answer]: A

### Question 10. UOW-002 테스트 방식

Functional Design 이후 코드 생성 단계의 테스트는 어떤 방식으로 설계할까요?

A) (권장) `httpx.MockTransport`와 fake clock을 사용해 live network 없이 timeout/retry/backoff/rate limiter/User-Agent/proxy/cookie/response classification을 검증한다.

추천 사유: HTTP 정책은 네트워크 없이도 결정적으로 테스트할 수 있습니다. live smoke는 UOW-008 이후 선택 hook으로 두는 편이 안정적입니다.

B) 실제 FMKorea live 요청을 기본 테스트로 둔다.

C) import 테스트만 두고 HTTP 정책 테스트는 UOW-003 이후로 미룬다.

[Answer]: A
