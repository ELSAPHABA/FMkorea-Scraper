# NFR Requirements 계획 - UOW-004 Post Detail And Content Parsing

이 계획은 `UOW-004 Post Detail And Content Parsing`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-004 Post Detail And Content Parsing
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection
- **Primary Stories**: US-004, US-005, US-006, US-006A, US-007
- **Scope**: detail HTML fetch handoff, final metadata parsing, ordered body content parsing, media metadata extraction, attachment parsing, comment/reply parsing, BEST comment fields, parser warnings
- **Security Focus**: safe parser logs, no raw HTML/body dump, no cookie/proxy leakage, no persisted user-provided cookie content
- **Resiliency Focus**: required-field failure boundary, optional block/comment failure isolation, comment page bounds, CAPTCHA/block propagation
- **PBT Focus**: URL normalization, content block order, media dedupe, comment ID parsing, reaction score, required-field validation
- **Out Of Scope**: list/search traversal, worker queue lifecycle, checkpoint persistence, JSONL/storage writes, media file download, CLI prompt UX, container/MCP hosting

## NFR Requirements 작업 체크리스트

- [x] UOW-004 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-requirements/tech-stack-decisions.md` 생성

## NFR Requirements Questions

### Question 1. Parser Strictness Boundary

상세 페이지 파싱 실패 기준은 어떻게 둘까요?

A) (권장) `document_srl` 또는 원시 문서 ID, canonical/detail URL, title이 없으면 post-level parser failure로 처리한다. 작성자 세부값, 말머리, 카운터, 첨부, 미디어, 댓글의 일부 파싱 실패는 safe warning으로 기록하고 가능한 나머지 결과를 반환한다.

추천 사유: 기존 스크래퍼의 parser-stage 실패 경계를 계승하면서, 한 댓글/이미지 실패 때문에 게시글 전체를 버리지 않게 합니다.

B) 제목, 작성자, 작성일, 조회수, 추천수, 댓글 수 중 하나라도 없으면 게시글 전체를 실패 처리한다.

C) 필수 필드가 없어도 모두 `null`로 저장하고 성공 처리한다.

X) 기타

[Answer]: A

### Question 2. Parser Fixture Coverage

UOW-004 parser fixture 테스트 범위는 어디까지 둘까요?

A) (권장) 상세 메타데이터, 텍스트+이미지 본문, 자체 동영상, YouTube, X/Twitter, 첨부파일, 일반 댓글/덧글, BEST 댓글, 선택 필드 누락/깨진 블록 fixture를 최소 1개씩 둔다.

추천 사유: 상세 파서는 DOM 변형이 많아 live 테스트보다 작은 fixture가 빠르고 재현성이 좋습니다.

B) 메타데이터와 텍스트+이미지 fixture만 둔다.

C) fixture 없이 live smoke 테스트로만 검증한다.

X) 기타

[Answer]: A

### Question 3. Content Traversal Performance

본문 파싱 성능 요구사항은 어떻게 둘까요?

A) (권장) BeautifulSoup으로 기준 컨테이너를 한 번 찾고, 하위 DOM을 선형 순회해 `content.blocks`를 만든다. 브라우저 렌더링, 반복적인 전역 selector 전체 탐색, 중복 다운로드 검사는 하지 않는다.

추천 사유: 상세 페이지 1건 파싱에는 선형 DOM 순회면 충분하고, Playwright 같은 브라우저 비용을 넣을 필요가 없습니다.

B) 모든 미디어/임베드 정확도를 위해 기본적으로 브라우저 렌더링 후 파싱한다.

C) 각 미디어 타입마다 문서 전체를 별도 재탐색한다.

X) 기타

[Answer]: A

### Question 4. Media Dedupe Policy

미디어 중복 방지는 어떤 수준으로 둘까요?

A) (권장) 한 게시글 안에서 `type`, 정규화 URL, `file_srl` 중 사용 가능한 키로 logical media block을 dedupe한다. 자체 동영상은 여러 `source`가 있어도 1개 `fmk_video` block으로 emit한다.

추천 사유: 기능명세서의 JSONL 구조를 지키면서 같은 파일/동영상이 여러 태그로 반복 저장되는 것을 막을 수 있습니다.

B) 중복 방지를 하지 않고 DOM에 보이는 모든 media/link를 저장한다.

C) 저장소 단위 전역 dedupe를 UOW-004에서 처리한다.

X) 기타

[Answer]: A

### Question 5. Comment Collection Bound

댓글 페이지/프래그먼트 수집 제한은 어떻게 둘까요?

A) (권장) 초기 상세 HTML 댓글을 먼저 파싱하고, 발견 가능한 댓글 페이지/프래그먼트 링크만 UOW-002 HTTP로 순차 요청한다. optional `max_comment_pages` guardrail을 두고, 중복 comment ID는 한 번만 저장한다.

추천 사유: 기존 워커 구조를 계승하면서 댓글 수집이 무한 페이지 탐색으로 번지지 않게 막습니다.

B) 댓글 페이지 수 제한 없이 더 이상 링크가 없을 때까지 계속 요청한다.

C) UOW-004에서는 첫 페이지 댓글만 파싱하고 추가 댓글 페이지는 지원하지 않는다.

X) 기타

[Answer]: A

### Question 6. Comment Failure Isolation

댓글 파싱 실패는 어떻게 처리할까요?

A) (권장) 개별 댓글/덧글 파싱 실패는 safe warning으로 기록하고 나머지 댓글은 계속 파싱한다. 단, 댓글 영역 전체가 CAPTCHA/block/unavailable 응답이면 UOW-002 오류를 그대로 전파한다.

추천 사유: 댓글 하나의 깨진 DOM 때문에 게시글 본문과 다른 댓글을 잃지 않게 하되, 차단 상태는 체크포인트 중단으로 넘겨야 합니다.

B) 댓글 하나라도 실패하면 게시글 전체를 실패 처리한다.

C) 댓글 파싱 실패는 기록하지 않고 조용히 무시한다.

X) 기타

[Answer]: A

### Question 7. Safe Logging And Warning Payload

UOW-004 로그와 parser warning payload는 어디까지 남길까요?

A) (권장) site_id, board_id, document_srl, safe stage, selector/key, warning code, block/comment order, safe reason만 남긴다. raw HTML, raw 본문 전문, raw 댓글 전문, cookie, proxy, user-provided cookie path/content는 남기지 않는다.

추천 사유: parser 문제를 추적할 최소 정보는 남기면서 개인정보/인증정보와 큰 HTML 덤프를 피합니다.

B) 디버깅 편의를 위해 raw HTML과 본문/댓글 전문을 debug log에 남긴다.

C) warning과 structured log를 만들지 않는다.

X) 기타

[Answer]: A

### Question 8. Property-Based Test Targets

UOW-004에서 PBT 대상으로 삼을 속성은 무엇으로 할까요?

A) (권장) URL 정규화, content block order uniqueness, media dedupe idempotence, comment ID 추출, reaction score 계산, required-field validation, warning payload redaction을 PBT 대상으로 둔다. BeautifulSoup DOM selector 정확도는 fixture/example 테스트로 둔다.

추천 사유: PBT는 순수 규칙 검증에 잘 맞고, DOM selector는 사람이 만든 fixture가 더 명확합니다.

B) BeautifulSoup DOM 전체를 랜덤 생성해 모든 parser를 PBT로 검증한다.

C) UOW-004에서는 PBT를 생략한다.

X) 기타

[Answer]: A

### Question 9. Live Smoke Test Policy

UOW-004의 live smoke test는 어떤 기준으로 둘까요?

A) (권장) 기본 unit test와 CI 필수 gate에서는 제외한다. `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 공개 상세 페이지 1건 수준의 선택적 smoke test를 허용하고, 저장/다운로드 없이 파싱 성공과 핵심 필드 존재만 확인한다.

추천 사유: 외부 사이트 DOM과 차단 정책은 바뀔 수 있으므로 기본 테스트는 fixture로 안정화하는 편이 안전합니다.

B) 모든 CI에서 상세 페이지 live smoke를 필수 실행한다.

C) live smoke 경로를 만들지 않는다.

X) 기타

[Answer]: A

### Question 10. Dependency Policy

UOW-004 구현에 새 런타임 의존성을 추가할까요?

A) (권장) 새 런타임 의존성은 추가하지 않는다. HTML 파싱은 기존 BeautifulSoup, URL 처리는 `urllib.parse`, 간단한 ID 추출은 `re`를 사용한다. HTTP는 UOW-002를 주입받는다.

추천 사유: 상세 파싱은 이미 선택한 BeautifulSoup과 표준 라이브러리로 충분하며, 별도 scraping/browser framework는 현재 범위에 비해 큽니다.

B) embed 처리 정확도를 위해 Playwright를 런타임 의존성으로 추가한다.

C) 미디어/댓글 파싱용 별도 scraping framework를 추가한다.

X) 기타

[Answer]: A

### Question 11. Model Compatibility

UOW-004에서 UOW-001 모델을 확장할 때 호환성 기준은 어떻게 둘까요?

A) (권장) 기존 필드 의미와 required 여부는 유지하고, 미디어/첨부 세부 필드는 typed optional field로만 추가한다. raw HTML 저장용 필드는 추가하지 않고, Polars 정규화가 필요한 값은 안정적인 scalar/list/dict 구조로 둔다.

추천 사유: 기존 테스트와 후속 저장/정규화 유닛을 깨지 않으면서 미디어 세부값을 담을 수 있습니다.

B) UOW-004에서 `PostResult` 스키마를 새 상세 전용 모델로 교체한다.

C) 모든 새 값을 `metadata` dict에만 넣고 typed field는 추가하지 않는다.

X) 기타

[Answer]: A

### Question 12. Parser Output Size Guardrail

비정상적으로 큰 게시글/댓글에 대한 출력 크기 제한은 어떻게 둘까요?

A) (권장) 기본 구현은 모든 정상 block/comment를 보존하되 optional `max_content_blocks`, `max_comments` guardrail을 둘 수 있게 한다. guardrail 초과 시 safe bounded-resource failure 또는 warning으로 남기고 상위 UOW가 정책을 결정하게 한다.

추천 사유: 일반 게시글은 손실 없이 저장하고, 비정상 대형 페이지에서 메모리 폭주를 막을 수 있습니다.

B) 항상 고정 최대 block/comment 수를 적용해 초과분은 조용히 버린다.

C) 크기 제한을 전혀 두지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-004 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-004 NFR Design으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T11:49:51Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper detail parser NFR boundary while using FMKorea-specific selectors, media types, attachments, and BEST comment fields.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Dependency Note**: UOW-004 uses existing BeautifulSoup and Python standard library helpers only. No browser automation, scraping framework, queue, storage, database, or media downloader dependency is added.
- **Follow-up Questions**: Not required.

## NFR Requirements Review Gate

검토 대상:

- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-requirements/tech-stack-decisions.md`

승인 후 다음 단계는 `UOW-004 NFR Design`이다.
