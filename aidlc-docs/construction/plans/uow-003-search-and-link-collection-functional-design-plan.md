# Functional Design 계획 - UOW-003 Search And Link Collection

이 계획은 `UOW-003 Search And Link Collection`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-003 Search And Link Collection
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy
- **Primary Stories**: US-004, US-005, US-006, US-006A, US-006B
- **Scope**: direct URL normalization, board list/search, integrated search, deep search, no-keyword range, realtime link discovery cycle, candidate dedupe, range filtering
- **Out Of Scope**: post detail parsing, comments, media download, output storage, checkpoint persistence, CLI prompt UX, container/MCP hosting

## Functional Design 작업 체크리스트

- [x] UOW-002 Build and Test 승인 확인
- [x] UOW-003 범위 확인
- [x] `docs/FMKorea-Scraper_Function_Specification.md` 검색/링크 수집 항목 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. Collector Output Contract

UOW-003의 링크 수집 결과는 어떤 형태로 후속 unit에 넘길까요?

A) (권장) UOW-003 내부 collector는 `PostCandidate`를 순차 생성하는 async iterator/list API를 제공하고, 실제 `asyncio.Queue` 투입은 UOW-005 JobRunner에서 담당한다.

추천 사유: UOW-003는 검색과 후보 생성만 검증하면 됩니다. Queue lifecycle까지 넣으면 UOW-005 책임이 앞당겨집니다.

B) UOW-003가 직접 `asyncio.Queue`를 인자로 받아 후보를 넣는다.

C) UOW-003는 HTML parser만 제공하고 수집 흐름은 전부 UOW-005로 미룬다.

X) 기타

[Answer]: A

### Question 2. Direct URL Normalization

직접 게시글 URL은 어떻게 정규화할까요?

A) (권장) `https://www.fmkorea.com/<document_srl>`, `/best/<document_srl>`, `index.php?mid=<board_id>&document_srl=<document_srl>`, `search.php?mid=<board_id>&document_srl=<document_srl>`를 모두 허용하고, 가능한 경우 `board_id`, `document_srl`, `document_id_raw`, canonical 후보 URL을 담은 `PostCandidate`로 정규화한다.

추천 사유: 기능명세서의 URL 형태를 모두 포함하고, 최종 `board_id`/canonical은 UOW-004 상세 페이지에서 다시 확정할 수 있습니다.

B) `index.php?mid=...&document_srl=...` 형태만 허용한다.

C) URL 정규화는 하지 않고 사용자가 입력한 URL 문자열을 그대로 후보로 넘긴다.

X) 기타

[Answer]: A

### Question 3. Board List And Board Search URL Builder

게시판 목록/게시판 내 검색 URL 생성은 어떻게 둘까요?

A) (권장) `BoardListSource`는 `https://www.fmkorea.com/<board_id>?page=<page>`를 기본으로 만들고, `category=<category_id>`를 옵션으로 붙인다. `BoardSearchSource`는 `https://www.fmkorea.com/search.php?mid=<board_id>&search_target=<target>&search_keyword=<keyword>&page=<page>`를 만들고, category가 있으면 함께 붙인다.

추천 사유: 기능명세서의 기본 URL과 검색 파라미터를 그대로 따르며, URL 생성 책임을 parser와 분리할 수 있습니다.

B) 모든 URL은 `index.php?mid=<board_id>` 형태만 사용한다.

C) URL builder를 만들지 않고 사용자가 완성 URL을 직접 넘긴다.

X) 기타

[Answer]: A

### Question 4. Board Row Parser Boundary

게시판 목록/검색 HTML 파싱은 어디까지 UOW-003에서 처리할까요?

A) (권장) BeautifulSoup 기반 parser가 `div.bd table tbody tr`에서 게시글 후보 행을 찾고, 공지/광고 행을 제외한 뒤 `a.hx[href]`, `td.title a[href]`에서 후보 URL과 `document_srl`을 추출한다. 목록의 제목/말머리/작성일/조회수/추천수/댓글 수는 `PostCandidate.metadata`에 진단/필터 힌트로만 저장한다.

추천 사유: 상세 본문 파싱은 UOW-004지만, 링크 단계에서 범위 필터와 dedupe에 필요한 후보 정보는 UOW-003가 알아야 합니다.

B) UOW-003는 상세 URL만 추출하고 나머지 목록 metadata는 버린다.

C) 목록 HTML 전체를 UOW-004 parser로 넘긴다.

X) 기타

[Answer]: A

### Question 5. Integrated Search URL And Parser

통합 검색 URL 생성과 파싱은 어떻게 둘까요?

A) (권장) `https://www.fmkorea.com/search.php?act=IS&is_keyword=<keyword>&where=document&search_target=<target>&page=<page>&sph_sort=<sort>`를 만들고, 결과에서 `PostCandidate`와 후보 `board_id` 목록을 함께 추출한다. `page_end`가 없으면 최대 1000페이지 또는 검색 결과 없음/다음 페이지 없음에서 종료한다.

추천 사유: 기능명세서의 통합 검색 API와 페이지 제한을 반영하며, 심층검색의 seed board 목록도 같은 parser에서 얻을 수 있습니다.

B) 통합 검색 URL은 사용자가 입력한 URL만 받아 그대로 호출한다.

C) 통합 검색은 1차 구현에서 제외한다.

X) 기타

[Answer]: A

### Question 6. Range Filter And Early Termination

글번호/작성일 범위 필터와 종료 조건은 어디에서 적용할까요?

A) (권장) UOW-003 collector가 `RangeFilter`를 사용해 후보 추가 여부를 결정하고, 목록 정렬상 더 이상 범위에 들어올 수 없다고 판단되면 해당 탐색을 종료한다. 단, 목록 메타데이터는 힌트이므로 UOW-004 상세 파싱 후 최종 범위 검증 여지를 남긴다.

추천 사유: 링크 단계에서 불필요한 상세 fetch를 줄이되, 최종 저장 전 정확성은 상세 페이지 기준으로 보강할 수 있습니다.

B) 모든 후보를 후속 단계에 넘기고 게시글 상세 파싱 후에만 범위 필터링한다.

C) 범위 필터는 CLI validation만 하고 collector에서는 적용하지 않는다.

X) 기타

[Answer]: A

### Question 7. No-Keyword Range Search

노키워드 기간/글번호 범위 수집은 어떻게 구현할까요?

A) (권장) 키워드 검색 API를 억지로 쓰지 않고, `BoardListSource`와 같은 게시판 목록 페이지 순회를 재사용한다. `range_filter`의 작성일/글번호 조건으로 후보를 필터링하고, category가 있으면 `category=<category_id>`를 붙인다.

추천 사유: FMKorea 명세의 노키워드 수집은 게시판 목록 순회 기반입니다. 사이트에 없는 빠른 이동 API를 가정하지 않는 편이 작고 안정적입니다.

B) `search.php`에 빈 키워드를 넣어 검색 결과처럼 처리한다.

C) 노키워드 수집은 글번호 범위만 지원하고 날짜 범위는 제외한다.

X) 기타

[Answer]: A

### Question 8. Deep Search Flow

심층검색은 어떤 흐름으로 설계할까요?

A) (권장) 1단계 통합 검색으로 후보 `board_id` 목록을 만들고, `(board_id)` 기준으로 dedupe한 뒤, 각 게시판에서 같은 키워드로 게시판 내 검색을 순차 수행한다. 통합 검색 seed 결과 자체는 최종 큐에 직접 넣지 않고, per-board 검색 결과를 최종 후보로 사용한다.

추천 사유: 사용자가 정의한 심층검색 목적은 통합 검색의 결과 제한을 보완하기 위해 게시판별 검색으로 확장하는 것입니다. seed 결과를 바로 큐에 넣으면 중복 처리만 늘어납니다.

B) 통합 검색 seed 결과도 최종 후보에 넣고, 게시판별 검색 결과와 dedupe한다.

C) 후보 게시판 검색을 모두 병렬 실행한다.

X) 기타

[Answer]: A

### Question 9. Realtime Collection Boundary

실시간 키워드/전체 수집은 UOW-003에서 어디까지 담당할까요?

A) (권장) UOW-003는 한 번의 최신 목록/검색 확인을 수행하는 reusable collection cycle과 dedupe set 적용만 제공한다. 반복 타이머, 종료시각, checkpoint 저장은 UOW-005 JobRunner가 소유한다.

추천 사유: 실시간 반복은 lifecycle 문제입니다. UOW-003는 각 cycle에서 새 후보를 찾는 역할만 맡는 편이 작고 테스트하기 쉽습니다.

B) UOW-003가 실시간 while loop, 종료 조건, checkpoint 저장까지 모두 담당한다.

C) 실시간 수집은 UOW-007 CLI에서만 구현한다.

X) 기타

[Answer]: A

### Question 10. Dedupe Key And Candidate Ordering

후보 중복 제거와 순서는 어떻게 관리할까요?

A) (권장) dedupe key는 `(site_id, board_id, document_id_raw)`를 우선 사용하고, `board_id`를 모르면 `(site_id, document_id_raw)`를 fallback으로 사용한다. 후보 순서는 수집 페이지/DOM 순서를 유지하며, 최종 저장 순서는 UOW-005 worker 처리 결과에 맡긴다.

추천 사유: FMKorea 단축 URL은 board가 없는 경우가 있어 fallback이 필요합니다. 링크 수집 단계에서 무리하게 최종 정렬을 보장하지 않는 것이 기존 멀티 워커 구조와 맞습니다.

B) `document_srl` 하나만 dedupe key로 사용한다.

C) dedupe는 하지 않고 UOW-006 저장 단계에서만 처리한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-003 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-003 NFR Requirements로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T05:00:23Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper collector boundary while using FMKorea-specific URLs, parameters, parsers, and dedupe keys.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## Functional Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/business-logic-model.md`
- `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/business-rules.md`
- `aidlc-docs/construction/uow-003-search-and-link-collection/functional-design/domain-entities.md`

승인 후 다음 단계는 `UOW-003 NFR Requirements`이다.
