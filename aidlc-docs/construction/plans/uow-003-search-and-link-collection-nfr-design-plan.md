# NFR Design 계획 - UOW-003 Search And Link Collection

이 계획은 `UOW-003 Search And Link Collection`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-003 Search And Link Collection
- **NFR Requirements**: 승인됨
- **Scope**: collector package layout, URL builder pattern, parser failure isolation, bounded traversal, range filter policy, dedupe policy, deep-search expansion, safe observability, deterministic test harness
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 링크 수집 구조를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: post detail parsing, comment/media parsing, queue ownership, checkpoint persistence, JSONL/Garage/PostgreSQL storage, CLI wizard, container entrypoint, MCP tools, cloud infrastructure

## NFR Design 작업 체크리스트

- [x] UOW-003 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Collector package layout

UOW-003 링크 수집 컴포넌트는 어떤 모듈 구조로 나눌까요?

A) (권장) `src/fmkorea_scraper/collect/` 아래에 `models.py`, `urls.py`, `parsers.py`, `policies.py`, `service.py`를 둔다.

추천 사유: 디시인사이드 스크래퍼의 수집 계층 분리를 계승하면서 파일 수를 과하게 늘리지 않습니다. URL 생성, DOM 파싱, 순수 정책, 서비스 오케스트레이션만 나누면 테스트 단위도 충분히 작습니다.

B) 모든 링크 수집 로직을 `collect/service.py` 하나에 모은다.

C) 수집 모드마다 별도 package와 abstract interface를 만든다.

[Answer]: A

### Question 2. Collector output shape

수집 결과는 어떤 형태로 노출할까요?

A) (권장) 기본 API는 `async for`로 소비 가능한 async iterator를 제공하고, 테스트와 작은 작업용으로만 `collect_all()` convenience helper가 list를 만든다.

추천 사유: 이후 UOW-005가 큐에 링크를 넣을 때 전체 링크를 항상 메모리에 쌓지 않아도 됩니다. 동시에 단위 테스트와 단독 실행에서는 list helper로 단순하게 검증할 수 있습니다.

B) 모든 collector가 항상 `list[PostCandidate]` 전체를 반환한다.

C) UOW-003 내부에서 직접 `asyncio.Queue`에 넣는다.

[Answer]: A

### Question 3. HTTP integration pattern

UOW-002 HTTP runtime과는 어떻게 연결할까요?

A) (권장) collector/service는 caller가 주입한 UOW-002 `HttpClient` 또는 `HttpPort`만 사용하고, 직접 `httpx.AsyncClient`를 만들거나 닫지 않는다.

추천 사유: HTTP 생명주기, 프록시, User-Agent, 쿠키, rate limit, retry, CAPTCHA/차단 분류를 UOW-002 한 곳에 유지할 수 있습니다.

B) UOW-003 collector가 필요한 순간마다 자체 `httpx.AsyncClient`를 생성한다.

C) URL builder/parser 테스트 편의를 위해 `requests` 기반 동기 HTTP 경로도 함께 만든다.

[Answer]: A

### Question 4. Traversal state pattern

페이지 탐색 상태는 어떤 방식으로 관리할까요?

A) (권장) 작은 `SearchTraversalState` value object에 mode, board_id, page, current_url, stop reason을 담고, checkpoint 저장은 하지 않는다.

추천 사유: UOW-003은 현재 탐색 판단에 필요한 상태만 갖고, 영속 checkpoint는 UOW-005에 맡기는 기존 구조를 계승합니다.

B) UOW-003에서 파일 기반 checkpoint까지 직접 저장한다.

C) page 숫자만 지역 변수로 두고 summary/final state를 남기지 않는다.

[Answer]: A

### Question 5. Parser failure isolation pattern

목록/검색 HTML에서 일부 row 또는 item 파싱이 실패하면 어떻게 처리할까요?

A) (권장) row/item 단위 실패는 safe `CollectorFailure`에 기록하고 계속 진행한다. 단, CAPTCHA/차단/로그인 필요 분류는 그대로 전파한다.

추천 사유: 한 게시글 후보 파싱 실패 때문에 전체 페이지 수집이 중단되면 손실이 큽니다. 반대로 차단 신호는 작업 중단과 checkpoint가 필요하므로 UOW-005까지 올라가야 합니다.

B) 하나라도 파싱에 실패하면 해당 페이지 전체를 실패 처리한다.

C) 파싱 실패는 모두 조용히 무시하고 기록하지 않는다.

[Answer]: A

### Question 6. Range filter pattern

기간/글번호 범위 필터는 어떤 컴포넌트로 설계할까요?

A) (권장) 순수 `RangeFilterEvaluator`가 `include`, `skip_continue`, `stop_traversal` 결과를 반환하고 collector loop는 그 결과만 따른다.

추천 사유: 범위 판단은 HTTP나 DOM과 독립적인 정책입니다. 순수 함수/작은 객체로 두면 PBT로 단조성, 경계값, 조기 종료를 검증하기 쉽습니다.

B) 각 collector loop 내부에 범위 조건문을 직접 작성한다.

C) 링크 수집 단계에서는 범위 필터를 적용하지 않고 UOW-004 이후에만 검증한다.

[Answer]: A

### Question 7. Deduplication pattern

후보 게시글 중복 제거는 어떤 방식으로 처리할까요?

A) (권장) collection run 단위의 in-memory set으로 `(site_id, board_id, document_id_raw)`를 우선 사용하고, `board_id`가 없으면 `(site_id, document_id_raw)` fallback key를 사용한다.

추천 사유: 디시인사이드 스크래퍼의 후보 dedupe 방식을 계승하면서, UOW-003 범위에서는 외부 저장소나 Bloom filter 없이 충분히 동작합니다. Job 간 최종 중복 제어는 UOW-006 저장 단계에서 다룹니다.

B) dedupe를 하지 않고 모든 후보를 downstream으로 넘긴다.

C) UOW-003에서 PostgreSQL 또는 S3를 조회해 전역 dedupe를 수행한다.

[Answer]: A

### Question 8. Deep search expansion pattern

심층검색의 갤러리/게시판 확장 방식은 어떻게 설계할까요?

A) (권장) 통합검색으로 board_id 후보를 수집해 중복 제거한 뒤, board별 검색은 UOW-003 내부에서 순차 실행하고 partial failure만 summary에 기록한다.

추천 사유: 현재 요구는 안정적인 링크 수집이며, board 단위 병렬화는 Job runner의 concurrency 정책이 있어야 안전합니다. 순차 실행은 차단 위험과 상태 복잡도를 낮춥니다.

B) UOW-003에서 board별 검색을 자체 병렬 실행한다.

C) 통합검색 seed 결과도 최종 후보로 저장하고 board별 검색 결과와 합친다.

[Answer]: A

### Question 9. Safe observability pattern

수집 로그와 summary에는 어떤 정보를 남길까요?

A) (권장) mode, board_id, page, candidate_count, skipped_count, deduped_count, stop_reason, safe failure reason만 남기고 raw HTML, 쿠키, 프록시, 민감 query 전체는 남기지 않는다.

추천 사유: 운영에 필요한 집계와 디버깅 단서는 남기되, 민감 정보와 대형 HTML이 로그/에러로 새는 위험을 줄입니다.

B) 디버깅 편의를 위해 요청 URL 전체와 HTML 일부를 summary에 포함한다.

C) UOW-003에서는 로그와 summary를 만들지 않는다.

[Answer]: A

### Question 10. Test harness pattern

UOW-003 테스트는 어떤 구조로 구성할까요?

A) (권장) URL/range/dedupe는 pytest와 Hypothesis로 검증하고, BeautifulSoup DOM parser는 `tests/fixtures/`의 작은 HTML fixture/example test로 검증한다. live smoke는 `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 선택 실행한다.

추천 사유: PBT는 순수 정책에 적합하고, DOM 구조는 실제 fixture가 더 안정적입니다. 외부 사이트 상태에 따라 흔들리는 live smoke를 기본 CI gate로 두지 않습니다.

B) parser DOM까지 무작위 HTML을 생성해 전부 PBT로 검증한다.

C) live smoke 테스트만 두고 fixture 테스트는 만들지 않는다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-003 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-003 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T05:26:09Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper link collection design while keeping FMKorea-specific URL builders and BeautifulSoup parser fixtures separate.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-003-search-and-link-collection/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-003 Infrastructure Design`이다.
