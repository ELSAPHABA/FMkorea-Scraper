# NFR Design 계획 - UOW-004 Post Detail And Content Parsing

이 계획은 `UOW-004 Post Detail And Content Parsing`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-004 Post Detail And Content Parsing
- **NFR Requirements**: 승인됨
- **Scope**: detail parser package layout, HTTP handoff, metadata parser, content traversal, media/attachment parser, comment parser, warning model, model extension, safe observability, deterministic test harness
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 상세 게시글 파싱 구조를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: list/search traversal, worker queue lifecycle, checkpoint persistence, JSONL/Garage/PostgreSQL storage, media file download, CLI wizard, container entrypoint, MCP tools, cloud infrastructure

## NFR Design 작업 체크리스트

- [x] UOW-004 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Detail parser package layout

UOW-004 상세 파싱 컴포넌트는 어떤 모듈 구조로 나눌까요?

A) (권장) `src/fmkorea_scraper/parse/` 아래에 `models.py`, `metadata.py`, `content.py`, `media.py`, `comments.py`, `warnings.py`, `service.py`를 둔다.

추천 사유: 기존 상세 파싱 계층 분리를 계승하면서 파일 수를 과하게 늘리지 않습니다. 메타데이터, 본문, 미디어, 댓글, warning, 서비스 오케스트레이션만 나누면 테스트 단위도 충분히 작습니다.

B) 모든 상세 파싱 로직을 `parse/service.py` 하나에 모은다.

C) 미디어 타입과 댓글 타입마다 별도 package와 abstract interface를 만든다.

[Answer]: A

### Question 2. Detail parser output shape

상세 파싱 결과는 어떤 형태로 노출할까요?

A) (권장) 기본 API는 `PostCandidate` 또는 `PostRequest`를 받아 최종 `PostResult`를 반환한다. parser 내부 중간 결과는 public API로 노출하지 않고, 테스트에는 작은 parser 함수들을 직접 검증한다.

추천 사유: 후속 UOW-005 워커가 링크 단위로 `PostResult`만 받으면 되고, 중간 DTO를 public contract로 늘릴 필요가 없습니다.

B) 메타데이터, 본문, 미디어, 댓글을 모두 별도 public result로 반환하고 caller가 합친다.

C) UOW-004 내부에서 JSONL 직렬화 문자열까지 반환한다.

[Answer]: A

### Question 3. HTTP integration pattern

UOW-002 HTTP runtime과는 어떻게 연결할까요?

A) (권장) `PostDetailService`는 caller가 주입한 UOW-002 `HttpClient` 또는 `HttpPort`만 사용하고, 직접 `httpx.AsyncClient`를 만들거나 닫지 않는다.

추천 사유: HTTP 생명주기, 프록시, User-Agent, 쿠키, rate limit, retry, CAPTCHA/차단 분류를 UOW-002 한 곳에 유지할 수 있습니다.

B) UOW-004가 상세/댓글 요청마다 자체 `httpx.AsyncClient`를 생성한다.

C) 테스트 편의를 위해 `requests` 기반 동기 HTTP 경로도 함께 만든다.

[Answer]: A

### Question 4. Metadata parser pattern

상세 페이지 메타데이터 파서는 어떤 방식으로 구성할까요?

A) (권장) `MetadataParser`가 `#bd_capture`를 기준으로 제목, 작성자, 작성일, 카운터, 말머리, canonical URL을 파싱하고, 후보 메타데이터 fallback은 누락값에만 적용한다.

추천 사유: 검색/목록 단계 값은 진단용 힌트이고 최종 저장값은 상세 페이지에서 다시 수집한다는 명세와 맞습니다.

B) 목록/검색 후보 메타데이터를 최종 저장값으로 우선 사용하고 상세 페이지 값은 fallback으로 둔다.

C) 상세 메타데이터 파서를 만들지 않고 content parser에서 같이 처리한다.

[Answer]: A

### Question 5. Content traversal pattern

본문 컨텐츠 파싱은 어떤 방식으로 구현할까요?

A) (권장) `ContentParser`가 scoped `.xe_content` 컨테이너를 한 번 찾고 child DOM을 선형 순회하며 `text`, `image`, `fmk_video`, `youtube`, `x`, `link`, `attachment`, `unknown_embed` block을 순서대로 만든다.

추천 사유: 본문 순서를 보존하면서도 전역 selector 반복 탐색과 브라우저 렌더링 비용을 피할 수 있습니다.

B) 미디어 타입별로 문서 전체를 따로 훑은 뒤 마지막에 임의 순서로 합친다.

C) `content.text`만 저장하고 block 구조는 만들지 않는다.

[Answer]: A

### Question 6. Media and attachment parser pattern

미디어/첨부 파싱은 어떤 컴포넌트 패턴으로 설계할까요?

A) (권장) `MediaBlockParser`와 `AttachmentParser`를 분리한다. content parser는 DOM 순서를 관리하고, media parser는 URL 정규화와 per-post dedupe key를 제공하며, attachment parser는 `.rd_file a[data-href]` lookup을 제공한다.

추천 사유: 본문 순서와 미디어 세부 추출을 분리하면 중복 저장을 줄이면서도 파일 수는 크게 늘지 않습니다.

B) 모든 미디어/첨부 로직을 content parser 안에 직접 작성한다.

C) 미디어 타입마다 class hierarchy와 plugin registry를 만든다.

[Answer]: A

### Question 7. Comment parser pattern

댓글/덧글 파싱은 어떤 방식으로 구성할까요?

A) (권장) `CommentParser`가 `.fdb_lst_ul > li`를 순회해 flat `Comment` list를 만들고, BEST 여부, badges, 추천/비추천, source_order, safe parent 정보를 채운다. 추가 댓글 페이지는 service가 순차 fetch 후 같은 parser에 넘긴다.

추천 사유: 기존 댓글 정규화 방향과 맞고, 댓글/덧글을 중첩 객체로 복잡하게 만들 필요가 없습니다.

B) 댓글과 덧글을 중첩 tree 구조로 저장한다.

C) BEST 댓글만 별도 배열로 분리하고 일반 댓글 배열과 중복 저장한다.

[Answer]: A

### Question 8. Parser warning pattern

recoverable parser warning은 어떤 구조로 관리할까요?

A) (권장) 작은 `ParseWarning` value object를 두고 `code`, `stage`, `selector`, `order`, `reason` 같은 safe field만 담아 `PostResult.metadata["parse_warnings"]`에 저장한다.

추천 사유: 후속 parser-stage retry와 운영 진단에 필요한 단서를 남기면서 raw HTML/본문/댓글 전문을 저장하지 않습니다.

B) warning은 문자열 리스트로만 저장한다.

C) warning payload에 raw HTML snippet과 원문 텍스트 일부를 저장한다.

[Answer]: A

### Question 9. Model extension pattern

UOW-001 모델 확장은 어떤 방식으로 적용할까요?

A) (권장) 기존 required field와 의미는 유지하고, 이미지/동영상/YouTube/X/첨부 세부값만 optional typed field로 추가한다. 불확실한 값은 `metadata`로 둔다.

추천 사유: 기존 코드와 후속 저장 유닛을 깨지 않으면서 Polars 정규화 가능한 안정 필드를 늘릴 수 있습니다.

B) `PostResult`를 UOW-004 전용 새 모델로 교체한다.

C) 새 필드를 typed field로 추가하지 않고 모두 `metadata` dict에만 넣는다.

[Answer]: A

### Question 10. Test harness pattern

UOW-004 테스트는 어떤 구조로 구성할까요?

A) (권장) BeautifulSoup parser는 `tests/fixtures/parse/`의 작은 HTML fixture/example test로 검증하고, URL 정규화, media dedupe, comment ID, reaction score, required-field validation, warning redaction은 pytest와 Hypothesis로 검증한다. live smoke는 `FMKOREA_LIVE_SMOKE_ENABLED=true`일 때만 선택 실행한다.

추천 사유: DOM selector는 fixture가 명확하고, 순수 정책은 PBT가 효과적입니다. 외부 사이트 상태에 따라 흔들리는 live smoke를 기본 CI gate로 두지 않습니다.

B) parser DOM까지 무작위 HTML을 생성해 전부 PBT로 검증한다.

C) live smoke 테스트만 두고 fixture 테스트는 만들지 않는다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-004 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-004 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T12:05:13Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper detail parsing design while keeping FMKorea-specific selectors, media parsing, attachment parsing, and BEST comment handling separate.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-004 Infrastructure Design`이다.
