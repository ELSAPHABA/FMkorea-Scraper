# UOW-011 Scrapling Runtime Refactor - Functional Design Plan

## 목적

이 문서는 이미 수행된 Scrapling 기반 런타임 리팩토링을 AI-DLC 흐름에 맞춰 역정리하고, 코드에 추가 반영할 수 있는 애매한 결정만 질문으로 남깁니다.

당연한 사실은 질문하지 않습니다.

- BeautifulSoup 파서 런타임은 Scrapling `Selector`로 교체됨
- 기본 HTTP 경로는 `httpx.AsyncClient` 유지
- CAPTCHA/차단 자동 우회는 구현하지 않음
- RabbitMQ 같은 Job Queue 소비는 스크래퍼 내부가 아니라 향후 통합 플랫폼의 외부 오케스트레이터 책임
- Scrapling Spider 전환은 현재 구현 범위가 아니라 향후 별도 AI-DLC 단위

## 현재 코드 기준

- 정적 파싱: Scrapling `Selector`
- 브라우저 fallback: CLI/Docker에서 기본 활성화, 명시적으로 비활성화 가능
- fallback trigger: 성공 응답이지만 목록/검색/상세 필수 DOM 누락
- fail-closed: CAPTCHA, HTTP 430, 명확한 차단 응답은 브라우저 fallback 없이 terminal checkpoint
- Job Queue: 스크래퍼 내부 consumer 없음. 외부 오케스트레이터가 Job Queue를 소비하고 one-shot worker 컨테이너를 실행
- Spider: 미사용

## 질문지

### Q1. 브라우저 fallback 기본값

브라우저 fallback은 기본적으로 어떤 실행 환경에서 활성화해야 하나요?

A) 비활성 기본값 유지 `(권장)`

권장 사유: 현재 scraper는 HTTP 수집이 기본이고, 브라우저는 비용과 차단 표면이 큽니다. 필요한 Job에서만 `--browser-fallback` 또는 `FMKOREA_BROWSER_FALLBACK=true`로 켜는 편이 운영 예측성이 높습니다.

B) Docker 컨테이너에서만 기본 활성화

컨테이너 smoke와 운영 Job에서 DOM 누락 대응은 쉬워지지만, 모든 컨테이너 Job이 브라우저 비용을 가질 수 있습니다.

C) CLI/Docker 모두 기본 활성화

초기 사용성은 좋아질 수 있지만, 사이트 차단과 실행 비용이 커지고 HTTP-only 경로 검증이 흐려집니다.

[Answer]: C

### Q2. 브라우저 fallback 적용 범위

브라우저 fallback은 어떤 페이지/응답 상황까지 적용해야 하나요?

A) 게시글 상세 성공 응답의 필수 DOM 누락에만 적용 `(권장)`

권장 사유: 현재 문제는 상세 페이지 본문 DOM 누락에 한정되어 있습니다. 목록/검색까지 fallback을 넓히면 크롤링 속도와 차단 위험이 크게 증가합니다.

B) 목록/검색 페이지의 필수 DOM 누락에도 적용

검색 결과가 JS 렌더링으로 바뀌는 경우에 대응할 수 있지만, link collection 단계가 무거워집니다.

C) CAPTCHA/차단 의심 응답에도 fallback 시도

우회처럼 동작할 수 있어 현재 보안/운영 원칙과 충돌합니다.

[Answer]: B

### Q3. Job Queue 소비 책임

RabbitMQ 같은 Job Queue 소비는 어느 컴포넌트가 책임져야 하나요?

A) 외부 오케스트레이터가 큐를 소비하고 스크래퍼는 one-shot worker만 유지 `(권장)`

권장 사유: 현재 스크래퍼는 단일 Job 실행과 checkpoint 저장에 집중하는 편이 작습니다. RabbitMQ consumer, ack/nack, DLQ, lease, autoscaling은 통합 플랫폼에서 한 번만 소유하는 구조가 맞습니다.

B) 스크래퍼에 JobConfig 한 건을 소비하는 one-shot RabbitMQ 어댑터 추가

운영 실험은 쉬워지지만 외부 오케스트레이터와 책임이 겹칩니다.

C) 스크래퍼 안에 장기 실행 RabbitMQ worker 구현

실제 플랫폼 worker에 가까워지지만 DLQ, lease, graceful shutdown, observability까지 같이 설계해야 합니다.

[Answer]: A

### Q4. Docker 이미지의 브라우저 의존성 포함 방식

Docker worker 이미지는 Scrapling browser fallback에 필요한 Playwright/Chromium 의존성을 어떤 방식으로 포함해야 하나요?

A) 현재 worker 이미지에 browser extra, Playwright, Chromium 포함 `(권장)`

권장 사유: 브라우저 fallback을 켜는 Job과 끄는 Job이 같은 이미지를 사용할 수 있어 배포가 단순합니다. 기본 HTTP 경로에서는 브라우저가 실행되지 않습니다.

B) browser fallback 전용 별도 이미지 분리

이미지 크기는 줄일 수 있지만 운영자가 Job마다 이미지를 골라야 합니다.

C) 컨테이너에서는 browser fallback 미지원

이미지는 작아지지만 운영 환경에서 DOM 누락 복구 수단이 없어집니다.

[Answer]: A

### Q5. Scrapling Spider 전환 계획

Scrapling Spider 기반 실행 엔진 전환은 언제 어떤 범위로 다뤄야 하나요?

A) 향후 별도 AI-DLC UOW로 계획만 기록 `(권장)`

권장 사유: Spider 전환은 파서 교체가 아니라 실행 엔진 교체입니다. 현재 `JobRunner`, checkpoint, retry, report가 안정화된 상태이므로 별도 설계 없이 섞으면 회귀 위험이 큽니다.

B) 현재 리팩토링 안에 Spider PoC만 추가

학습에는 도움이 되지만, 사용하지 않는 실험 코드가 남을 수 있습니다.

C) 지금 Spider 기반으로 즉시 재리팩토링

장기 엔진 통일에는 가까워지지만 현재 변경 범위가 크게 늘어납니다.

[Answer]: A

## 다음 단계

사용자가 위 질문을 확정하면 답변과 현재 코드의 차이만 비교합니다.

- 답변이 현재 코드와 같으면 문서만 확정합니다.
- 답변이 현재 코드와 다르면 해당 변경 사항만 코드에 반영합니다.
- Spider 선택지가 A이면 향후 계획으로만 유지하고 현재 코드에는 Spider를 추가하지 않습니다.

## 답변 검증 결과

검증일: 2026-08-31

| 항목 | 답변 | 현재 코드와 차이 | 검증 결과 |
|---|---|---|---|
| Q1 | C | 있음 | CLI/Docker 모두 browser fallback 기본 활성화로 코드 변경 적용 |
| Q2 | B | 있음 | 목록/검색 페이지 필수 DOM 누락에도 fallback을 적용하도록 코드 변경 적용 |
| Q3 | A | 없음 | 내부 RabbitMQ consumer/adapter 제거 상태와 일치 |
| Q4 | A | 없음 | 단일 worker 이미지에 browser extra, Playwright, Chromium 포함 상태와 일치 |
| Q5 | A | 없음 | Spider 전환을 향후 별도 AI-DLC UOW로만 기록한 상태와 일치 |

처리:

- Q1/Q2 코드 차이를 반영한다.
- Q3/Q4/Q5는 현재 코드 및 문서 방향과 일치한다.
- UOW-011 Functional Design 산출물을 생성하고 review required 상태로 전환한다.
