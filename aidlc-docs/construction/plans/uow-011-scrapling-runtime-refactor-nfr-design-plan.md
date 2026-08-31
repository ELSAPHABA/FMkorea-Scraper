# NFR Design Plan - UOW-011 Scrapling Runtime Refactor

이 계획은 `UOW-011 Scrapling Runtime Refactor`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-011 Scrapling Runtime Refactor
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-007 CLI Adapter, UOW-008 Container/MCP/Test Harness, UOW-009 Parser Failure Retry Reprocessor
- **Scope**: browser fallback serialization pattern, timeout reuse pattern, safe logging/error pattern, dependency/test gate pattern, external orchestration boundary, next Spider PoC boundary
- **Out Of Scope**: CAPTCHA bypass, stealth mode, RabbitMQ consumer, Scrapling Spider implementation inside UOW-011, selector override config, new storage/checkpoint architecture

## NFR Design 작업 체크리스트

- [x] UOW-011 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## Review Result

- Q1-Q7은 모두 A로 확정되었습니다.
- 답변 간 충돌은 없습니다.
- follow-up 질문은 필요하지 않습니다.
- 확정 방향은 `HttpClient` 인스턴스 내부 `asyncio.Lock`, lock wait 허용, 기존 `HttpResponse` 유지, 기존 `BrowserFallbackError` 유지, raw debug dump 미구현, fake async browser fetcher 기반 테스트, UOW-011 완료 후 별도 UOW-012 Spider PoC/planning입니다.
- 산출물 생성 후 UOW-011 NFR Design Review 단계에서 사용자 승인을 대기합니다.

## NFR Design Questions

### Question 1. Browser Fallback Serialization Pattern

browser fallback 직렬화는 어디에 둘까요?

A) (권장) `HttpClient` 인스턴스 내부에 `asyncio.Lock`을 두고 `_render_with_browser()` 전체를 보호한다.

추천 사유: 현재 runner는 Job 실행 중 하나의 `HttpClient`를 공유합니다. 인스턴스 lock이면 전역 상태 없이 한 Job 내부 browser fallback 동시 실행을 막을 수 있습니다.

B) 모듈 전역 lock으로 같은 Python 프로세스의 모든 `HttpClient` fallback을 막는다.

C) `HttpRuntimeConfig.browser_fallback_concurrency`와 semaphore를 추가한다.

X) 기타

[Answer]: A

### Question 2. Browser Fallback Lock Wait Pattern

다른 요청이 browser fallback을 실행 중일 때 다음 fallback 요청은 어떻게 처리할까요?

A) (권장) lock이 풀릴 때까지 기다리고, 실제 browser fetch timeout은 기존 `timeout.read_seconds`를 그대로 사용한다.

추천 사유: fallback은 예외 경로이고 보통 드뭅니다. lock 대기용 별도 timeout이나 fail-fast 정책을 추가하지 않아도 기존 작업 취소와 browser timeout으로 충분합니다.

B) fallback이 이미 실행 중이면 즉시 `BrowserFallbackError`로 실패시킨다.

C) lock 대기 timeout을 별도 설정으로 추가한다.

X) 기타

[Answer]: A

### Question 3. Browser Fallback Result Metadata

browser fallback이 성공한 응답에는 별도 metadata를 추가할까요?

A) (권장) `HttpResponse` 구조는 그대로 유지하고, `browser_fallback_start/end` safe log만 남긴다.

추천 사유: 저장 JSONL과 parser 입력은 HTML 응답이면 충분합니다. 응답 모델을 늘리면 downstream 변경만 커집니다.

B) `HttpResponse`에 `rendered_by_browser` 같은 필드를 추가한다.

C) 저장 JSONL metadata에 fallback 사용 여부를 기록한다.

X) 기타

[Answer]: A

### Question 4. Browser Fallback Error Pattern

browser fallback 실패 에러는 어떻게 모델링할까요?

A) (권장) 기존 `BrowserFallbackError` 하나를 유지하고, `details.reason`으로 `required_selector_missing`, dependency/runtime 오류 등을 구분한다.

추천 사유: 현재 stop reason, failure record, safe error mapping이 이미 단일 fallback error를 처리합니다. 새 예외 계층은 실제 분기 필요가 생길 때 추가해도 됩니다.

B) `BrowserRuntimeError`, `RequiredDomMissingError`처럼 세부 예외를 추가한다.

C) fallback 실패를 `NetworkFailureError`로 통합한다.

X) 기타

[Answer]: A

### Question 5. Safe Debug Pattern

fallback 또는 Scrapling parsing 실패 조사 자료는 어떻게 다룰까요?

A) (권장) 기본 구현에는 raw dump 저장 기능을 추가하지 않는다. 필요 시 사용자가 직접 opt-in live smoke 또는 로컬 fixture를 만든다.

추천 사유: raw HTML/header/cookie/screenshot 저장은 보안 위험이 크고, 현재 NFR은 safe log만 요구합니다.

B) `--debug-dump-html` 로컬 전용 옵션을 추가한다.

C) 실패 시 rendered HTML과 screenshot을 기본 저장한다.

X) 기타

[Answer]: A

### Question 6. Verification Pattern

browser fallback 직렬화와 required DOM fallback은 어떻게 검증할까요?

A) (권장) fake `browser_fetcher`와 async barrier/counter 기반 단위 테스트로 직렬화를 검증하고, Chromium/Docker/live smoke는 기본 게이트 밖에 둔다.

추천 사유: 동시성 요구사항은 fake fetcher로 빠르고 결정적으로 검증할 수 있습니다. 실제 브라우저와 원격 사이트는 느리고 외부 상태에 취약합니다.

B) 실제 Chromium을 띄우는 테스트를 기본 pytest에 포함한다.

C) 수동 Docker smoke만 문서화하고 자동 테스트는 추가하지 않는다.

X) 기타

[Answer]: A

### Question 7. Spider PoC Boundary

Q9=B에 따른 Scrapling Spider PoC는 언제 시작할까요?

A) (권장) UOW-011 Build/Test 승인 후, 별도 UOW-012로 Functional Design 질문지부터 시작한다.

추천 사유: Spider는 실행 엔진 변경입니다. UOW-011의 browser fallback 안정화와 섞지 않으면 회귀 범위가 작고 승인 게이트도 명확합니다.

B) UOW-011 Code Generation 전에 Spider PoC 질문지를 병렬로 만든다.

C) UOW-011 Code Generation에 Spider PoC 코드를 함께 넣는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-011 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.
