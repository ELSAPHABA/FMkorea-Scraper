# NFR Requirements Plan - UOW-011 Scrapling Runtime Refactor

이 계획은 `UOW-011 Scrapling Runtime Refactor`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-011 Scrapling Runtime Refactor
- **Functional Design**: 승인됨
- **Depends On**: UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-007 CLI Adapter, UOW-008 Container/MCP/Test Harness, UOW-009 Parser Failure Retry Reprocessor
- **Primary Goal**: BeautifulSoup 기반 파싱을 Scrapling `Selector` 기반으로 전환한 현재 구현을 비기능 요구사항 기준으로 확정
- **Scope**: Scrapling selector runtime, HTTP-first request flow, list/search/detail required-DOM browser fallback, CLI/Docker fallback defaults, Docker browser dependency packaging, safe logs, default test gates, external Job Queue boundary, future Spider boundary
- **Security Focus**: CAPTCHA/차단 자동 우회 금지, raw HTML/header/cookie/proxy secret 미노출, 일반 Playwright fallback만 허용, stealth/anti-detect 추가 금지
- **Resiliency Focus**: required DOM 누락 감지, browser fallback 실패 시 terminal checkpoint, 기존 retry/checkpoint/report 경계 유지, 외부 queue consumer 미포함
- **Performance Focus**: HTTP-first 경로 유지, browser fallback 비용 제한, 기존 요청 간격과 worker 설정 재사용, Docker 이미지 크기와 실행 비용 인지
- **Test Focus**: fixture 기반 selector 회귀 테스트, fake browser fetcher 테스트, Docker/Chromium smoke, live site smoke는 명시 opt-in
- **Out Of Scope**: CAPTCHA 우회, stealth mode, Scrapling Spider 구현, RabbitMQ consumer/ack/nack/DLQ 구현, 중앙 오케스트레이터 구현, 사이트 API 재조사

## NFR Requirements 작업 체크리스트

- [x] UOW-011 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-011-scrapling-runtime-refactor/nfr-requirements/tech-stack-decisions.md` 생성

## Answer Validation Notes

- Q1-Q8은 A로 확정됨.
- Q9는 B로 확정됨.
- 답변 간 충돌은 없음.
- Q9=B는 UOW-011 안에 Spider 코드를 추가한다는 뜻이 아니라, UOW-011 이후 별도 UOW로 Spider PoC/planning을 진행한다는 결정으로 해석함.
- Q2=A는 현재 구현 대비 code generation 단계의 변경을 요구함. `HttpClient` 내부에서 browser fallback을 한 번에 하나만 실행하도록 직렬화해야 함.
- follow-up 질문은 필요하지 않음.

## NFR Requirements Questions

### Question 1. Browser Fallback Timeout

`DynamicFetcher` fallback의 timeout은 어떻게 관리할까요?

A) (권장) 기존 `HttpRuntimeConfig.timeout.read_seconds`를 그대로 재사용한다. 별도 browser timeout CLI/env 옵션은 추가하지 않는다.

권장 사유: 현재 HTTP timeout 설정이 이미 있고 fallback은 예외 경로입니다. 같은 timeout을 쓰면 설정 표면이 작고 CLI/Docker/library 동작이 일관됩니다.

B) browser fallback 전용 timeout을 별도 CLI/env/config 옵션으로 추가한다.

C) browser fallback timeout은 코드 내부 고정값으로 둔다.

X) 기타

[Answer]: A

### Question 2. Browser Fallback Concurrency

여러 post worker가 동시에 required DOM 누락을 만나면 browser fallback 동시 실행을 어떻게 제한할까요?

A) (권장) `HttpClient` 내부에서 browser fallback을 직렬화한다. 별도 사용자 옵션 없이 한 프로세스에서 fallback은 한 번에 하나만 실행한다.

권장 사유: fallback은 기본 활성화됐지만 비용이 큰 예외 경로입니다. 직렬화는 구현이 작고 Chromium 다중 실행으로 인한 메모리/차단 위험을 줄입니다.

B) 기존 worker 수와 요청 간격만 따르고 browser fallback 전용 제한은 두지 않는다.

C) `--browser-fallback-workers` 같은 별도 동시성 옵션을 추가한다.

X) 기타

[Answer]: A

### Question 3. Browser Fallback Failure Retryability

browser fallback이 실행 오류나 required DOM 누락으로 실패한 경우 failure retryability는 어떻게 둘까요?

A) (권장) 현재 Job에서는 terminal checkpoint로 중단하고, failure record는 기본 non-retryable로 둔다. 운영자는 checkpoint/resume 또는 별도 후속 retry 유닛에서 다룬다.

권장 사유: fallback 실패는 사이트 구조 변경, 차단, 브라우저 런타임 오류가 섞일 수 있습니다. 자동 retryable로 두면 같은 실패를 반복할 위험이 있습니다.

B) browser fallback 실패를 retryable failure로 기록해 일반 retry 흐름에서 다시 시도한다.

C) required DOM 누락만 retryable, 브라우저 실행 오류는 non-retryable로 구분한다.

X) 기타

[Answer]: A

### Question 4. Safe Logging And Debug Artifacts

fallback 및 Scrapling parsing 실패 시 디버깅 자료는 어느 수준까지 남길까요?

A) (권장) safe structured log와 failure details만 남긴다. raw HTML, headers, cookies, screenshot, rendered DOM dump는 저장하지 않는다.

권장 사유: 사용자 세션 쿠키, 보안 페이지, proxy 정보가 HTML/headers에 섞일 수 있습니다. 현재 프로젝트의 safe-log 원칙과 가장 잘 맞습니다.

B) 명시적 debug 옵션에서만 rendered HTML snapshot을 로컬 파일로 저장한다.

C) 실패 분석을 위해 raw HTML과 headers를 기본 저장한다.

X) 기타

[Answer]: A

### Question 5. Browser Dependency Packaging

Scrapling browser fallback 의존성은 어떤 설치 경계로 유지할까요?

A) (권장) library 기본 설치는 `scrapling`만 포함하고, browser dependency는 optional `browser` extra와 Docker worker 이미지에만 포함한다.

권장 사유: 라이브러리 사용자와 HTTP-only 실행은 가볍게 유지하고, 운영 Docker worker는 fallback을 바로 사용할 수 있습니다.

B) 모든 설치에 Playwright/Chromium까지 기본 포함한다.

C) Docker worker도 browser dependency를 제외하고 fallback Job 전용 이미지를 별도로 둔다.

X) 기타

[Answer]: A

### Question 6. Default Test Gate

UOW-011 이후 기본 테스트 게이트는 어디까지 포함할까요?

A) (권장) 기본 게이트는 전체 pytest, compileall, pip check, fixture/fake browser tests로 둔다. Docker/Chromium smoke는 release 또는 런타임 변경 시 수행하고, live site smoke는 opt-in으로 둔다.

권장 사유: browser와 live site를 매번 기본 테스트에 넣으면 느리고 불안정합니다. 파서/fallback 로직은 fixture와 fake fetcher로 대부분 검증할 수 있습니다.

B) 모든 로컬/CI 기본 테스트에서 Docker build와 Chromium smoke까지 항상 실행한다.

C) 단위 테스트만 실행하고 Docker/Chromium 검증은 수동 문서로만 남긴다.

X) 기타

[Answer]: A

### Question 7. Required Selector Maintenance

required DOM selector는 어떻게 유지보수할까요?

A) (권장) 코드 상수와 fixture 기반 회귀 테스트로 관리한다. 사용자 CLI/env override는 추가하지 않는다.

권장 사유: selector는 사이트별 파서 계약입니다. 사용자 설정으로 열어두면 실패 원인이 설정인지 사이트 변경인지 구분하기 어려워집니다.

B) CLI/env로 required selector override를 허용한다.

C) 외부 설정 파일에서 selector mapping을 읽도록 만든다.

X) 기타

[Answer]: A

### Question 8. External Job Queue Boundary

향후 RabbitMQ 같은 Job Queue와의 경계는 NFR 관점에서 어디까지 보장할까요?

A) (권장) 이 저장소는 one-shot worker 실행 계약만 보장한다. queue consume, ack/nack, lease, DLQ, autoscaling은 외부 오케스트레이터 책임으로 유지한다.

권장 사유: scraper는 JobConfig를 받아 실행하고 checkpoint/report를 남기는 단위에 집중해야 합니다. 큐 운영 책임은 여러 scraper를 묶는 플랫폼에서 한 번만 구현하는 편이 작습니다.

B) queue consumer 코드는 없지만 message schema 문서와 sample adapter stub은 이 저장소에 둔다.

C) 최소 RabbitMQ consume smoke adapter를 다시 추가한다.

X) 기타

[Answer]: A

### Question 9. Future Spider Migration Gate

Scrapling Spider 전환은 어떤 기준이 충족될 때 별도 UOW로 시작할까요?

A) (권장) 다수 커뮤니티 scraper에서 공통 crawl engine이 필요하거나 현재 `JobRunner`/checkpoint 모델이 병목으로 확인될 때 별도 UOW로 시작한다.

권장 사유: Spider는 파서 교체가 아니라 실행 엔진 교체입니다. 필요가 확인되기 전에는 현재 안정화된 one-shot runner를 유지하는 편이 작습니다.

B) 다음 UOW에서 바로 Spider PoC를 만든다.

C) Spider 전환 계획은 문서에서 제거하고 현재 구조만 유지한다.

X) 기타

[Answer]: B

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-011 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-011 NFR Design으로 넘어가지 않습니다.
