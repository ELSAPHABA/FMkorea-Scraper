# NFR Requirements 계획 - UOW-003 Search And Link Collection

이 계획은 `UOW-003 Search And Link Collection`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-003 Search And Link Collection
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy
- **Primary Stories**: US-004, US-005, US-006, US-006A, US-006B
- **Scope**: direct URL normalization, board list/search URL generation, BeautifulSoup parser correctness, traversal bounds, dedupe, range filtering, deep search discovery, realtime collection cycle
- **Security Focus**: safe URL logging, no raw HTML/body dump, no cookie/proxy leakage, CAPTCHA/block propagation
- **Resiliency Focus**: bounded traversal, partial deep-search failure handling, parser failure isolation, deterministic handoff state
- **PBT Focus**: URL/query round trip, integrated search page limit, dedupe idempotence, range filter invariants, realtime dedupe
- **Out Of Scope**: post detail parsing, result storage, checkpoint persistence, queue lifecycle, CLI prompt UX, container/MCP hosting

## NFR Requirements 작업 체크리스트

- [x] UOW-003 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-requirements/tech-stack-decisions.md` 생성

## NFR Requirements Questions

### Question 1. Traversal Bound Guardrail

게시판 목록, 게시판 검색, 통합 검색, 심층검색 탐색 제한은 어떻게 둘까요?

A) (권장) `page_end`가 있으면 이를 우선 적용하고, 없으면 통합 검색은 최대 1000페이지 guardrail을 둔다. 게시판 목록/검색은 no-result, page end, valid row 없음, range termination을 기본 종료 조건으로 두되 optional `max_pages` guardrail을 둘 수 있게 한다.

추천 사유: 기능명세서의 통합 검색 최대 1000페이지와 맞고, 게시판 탐색은 사이트 페이지 구조에 맞춰 종료하되 설정 실수로 무한 탐색하지 않게 막을 수 있습니다.

B) 모든 수집 모드를 항상 120페이지까지만 탐색한다.

C) 모든 탐색 제한은 후속 JobRunner에서만 처리한다.

X) 기타

[Answer]: A

### Question 2. Parser Fixture Coverage

BeautifulSoup parser fixture 테스트 범위는 어디까지 둘까요?

A) (권장) UOW-003 code generation에서 direct URL, board list, board search, integrated search, no-result page, deep-search board discovery fixture를 최소 1개씩 둔다.

추천 사유: UOW-003의 주된 리스크는 DOM/URL 파싱입니다. live 요청보다 작은 fixture가 빠르고 재현성이 좋습니다.

B) parser fixture는 board list와 integrated search만 둔다.

C) fixture 없이 PBT만 사용한다.

X) 기타

[Answer]: A

### Question 3. Parser Failure Handling

파서가 일부 행을 파싱하지 못할 때 실패 기준은 어떻게 둘까요?

A) (권장) 개별 row/item 파싱 실패는 safe `CollectorFailure`로 기록하고 나머지 row/item은 계속 처리한다. 단, 페이지 구조 자체가 검색 결과로 인식되지 않거나 CAPTCHA/block은 UOW-002 오류를 그대로 전파한다.

추천 사유: 한 행의 깨진 HTML 때문에 전체 Job을 멈추면 수집 손실이 큽니다. CAPTCHA/block은 중단점 저장이 필요하므로 삼키면 안 됩니다.

B) 한 row라도 파싱 실패하면 페이지 전체를 실패 처리한다.

C) 파싱 실패는 전부 무시하고 기록하지 않는다.

X) 기타

[Answer]: A

### Question 4. Dedupe Memory Bound

후보 dedupe set은 어떤 수준으로 제한할까요?

A) (권장) UOW-003에서는 in-memory set을 기본으로 쓰고, optional `max_seen_candidates` 초과 시 안전하게 중단/오류 처리한다. 대용량 영속 dedupe는 UOW-006 저장소/idempotency로 미룬다.

추천 사유: UOW-003 단독에서 DB나 bloom filter를 넣을 필요는 없습니다. 하지만 장시간 realtime/deep-search에서 unbounded set은 위험합니다.

B) SQLite 기반 영속 dedupe를 UOW-003에서 구현한다.

C) dedupe memory 제한은 두지 않는다.

X) 기타

[Answer]: A

### Question 5. Range Filter Accuracy

작성일/글번호 범위 필터의 정확도 요구사항은 어떻게 둘까요?

A) (권장) `document_srl` 범위는 숫자 파싱 성공 시 강하게 적용하고, 작성일 범위는 목록 날짜가 절대 날짜로 파싱될 때만 강하게 적용한다. 상대/모호 날짜는 포함하되 후속 상세 파싱에서 재검증 가능하게 metadata에 표시한다.

추천 사유: 목록 날짜 형식은 상대/절대 표기가 섞일 수 있습니다. 링크 단계에서 모호 날짜를 과감히 버리면 누락 위험이 큽니다.

B) 날짜 파싱이 실패하면 후보를 항상 제외한다.

C) 날짜/글번호 범위 필터는 UOW-003에서 적용하지 않는다.

X) 기타

[Answer]: A

### Question 6. Observability Scope

UOW-003의 structured logging 요구사항은 어디까지 둘까요?

A) (권장) collector start/end, page fetched, candidate accepted/skipped/deduped count, range termination, deep-search per-board failure를 safe structured event로 남긴다. raw HTML, raw cookie, proxy credential, full query URL은 로그에 남기지 않는다.

추천 사유: 검색 탐색 문제를 추적하려면 카운트와 상태가 필요하지만, raw HTML/전체 URL은 크고 민감할 수 있습니다.

B) 디버깅 편의를 위해 raw HTML과 전체 URL/query를 debug log에 남긴다.

C) UOW-003에서는 logging을 하지 않는다.

X) 기타

[Answer]: A

### Question 7. Property-Based Test Targets

UOW-003에서 PBT 대상으로 삼을 속성은 무엇으로 할까요?

A) (권장) board URL round trip, integrated search query determinism, integrated max page clamp, candidate dedupe idempotence, range filter monotonicity, realtime dedupe exclusion, deep-search board dedupe를 PBT 대상으로 둔다. BeautifulSoup DOM 파싱은 fixture/example 테스트로 둔다.

추천 사유: PBT는 순수 URL/정책 로직에 잘 맞고, DOM parser는 사람이 만든 fixture가 더 명확합니다.

B) BeautifulSoup fixture DOM까지 전부 랜덤 생성해 PBT로 검증한다.

C) UOW-003에서는 PBT를 생략한다.

X) 기타

[Answer]: A

### Question 8. Live Smoke Test Policy

UOW-003의 FMKorea live smoke test는 어떤 기준으로 둘까요?

A) (권장) 기본 unit test와 CI 필수 gate에서는 제외한다. `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 게시판 목록 1페이지 또는 통합 검색 1페이지 수준의 선택적 smoke test를 허용한다.

추천 사유: 외부 사이트 DOM과 차단 정책은 바뀔 수 있습니다. 기본 테스트는 fixture로 안정화하고, live smoke는 수동 검증 경로로 두는 편이 낫습니다.

B) 모든 CI에서 board list와 integrated search live smoke를 필수 실행한다.

C) live smoke 경로를 아예 만들지 않는다.

X) 기타

[Answer]: A

### Question 9. Dependency Policy

UOW-003에서 HTML 파싱/URL 처리를 위해 새 의존성을 추가할까요?

A) (권장) 새 런타임 의존성은 추가하지 않는다. HTML 파싱은 기존 명세의 BeautifulSoup을 사용하고, URL 생성/파싱은 Python 표준 라이브러리 `urllib.parse`를 사용한다.

추천 사유: UOW-003 기능은 표준 URL API와 BeautifulSoup으로 충분합니다. 추가 URL builder나 scraping framework는 지금 불필요합니다.

B) URL builder 라이브러리를 추가한다.

C) scraping framework를 추가한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-003 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-003 NFR Design으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T05:13:22Z
- **Selected Options**: Q1-Q9 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper collector NFR boundary while using FMKorea-specific URLs, page limits, parser fixtures, and live smoke env names.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Dependency Note**: BeautifulSoup is already selected by the function specification. UOW-003 may add `beautifulsoup4` if it is missing, but no additional runtime dependency is introduced beyond that parser dependency.
- **Follow-up Questions**: Not required.

## NFR Requirements Review Gate

검토 대상:

- `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-requirements/tech-stack-decisions.md`

승인 후 다음 단계는 `UOW-003 NFR Design`이다.
