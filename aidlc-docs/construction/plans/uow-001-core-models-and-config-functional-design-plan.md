# UOW-001 Core Models And Config Functional Design Plan

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-001 Core Models And Config
- **Goal**: Pydantic 모델, Job 설정, validation, public API request/result schema, port protocol을 정의한다.
- **Boundaries**: HTTP 요청, 검색 URL 조립, HTML 파싱, 저장소 구현, CLI 구현은 이후 UOW에서 다룬다.
- **FMKorea-specific model rule**: 원본 JSONL에는 `site_id="fmkorea"`를 사용하고, 댓글/BEST 댓글 필드는 같은 `comments` 배열 안에서 표현한다.

## Functional Design 작업 체크리스트

- [x] Unit of Work 산출물 확인
- [x] Application Design 산출물 확인
- [x] 기능 명세서의 JSONL/comment/content/checkpoint 방향 확인
- [x] Functional Design 질문 생성
- [x] 모든 `[Answer]:` 답변 확인
- [x] 답변 모호함 및 충돌 분석
- [x] follow-up 질문 불필요 확인
- [x] `domain-entities.md` 생성
- [x] `business-rules.md` 생성
- [x] `business-logic-model.md` 생성
- [x] Functional Design review gate 생성

## Functional Design 질문

### Question 1. Pydantic 버전

Pydantic 모델은 어떤 버전을 기준으로 설계할까요?

A) (권장) Pydantic v2를 기준으로 설계한다.

추천 사유: Application Design에서 `model_dump(mode="json")`을 이미 전제로 두었고, 신규 프로젝트라 v1 호환 비용을 들일 이유가 작습니다.

B) Pydantic v1/v2 호환 계층을 둔다.

C) Pydantic 없이 dataclass와 수동 validation으로 시작한다.

[Answer]: A

### Question 2. 모델 extra field 정책

입력/config 모델과 수집 결과 모델에서 문서화되지 않은 필드는 어떻게 처리할까요?

A) (권장) public input/config 모델과 scrape result 모델은 `extra="forbid"`로 시작하고, 확장 필드는 명시적 `metadata` dict에만 넣는다.

추천 사유: CLI/MCP/container 입력은 엄격해야 하고, JSONL 분석 스키마도 예측 가능해야 합니다. 사이트 구조 변화 대응은 아무 필드나 허용하기보다 `metadata`에 격리하는 편이 안전합니다.

B) 모든 모델에서 extra field를 허용한다.

C) 결과 모델에서는 extra를 허용하고 config 모델만 금지한다.

[Answer]: A

### Question 3. JobConfig 구조

수집 진입점별 Job 설정은 어떻게 모델링할까요?

A) (권장) 공통 `JobConfig`에 `job_type`을 두고, `source` 필드를 discriminated union으로 둔다.

추천 사유: direct URL, board search, integrated search, deep search, no-keyword range, realtime은 source별 필수 값이 다릅니다. discriminated union이면 validation 오류가 명확하고 adapter 입력도 단순합니다.

B) 수집 방식마다 별도 `JobConfig` 모델을 만든다.

C) 하나의 `JobConfig`에 모든 optional field를 넣고 validator로 조합을 검사한다.

[Answer]: A

### Question 4. ContentBlock 구조

본문의 텍스트, 이미지, 자체 동영상, YouTube, X/Twitter, 일반 링크, 첨부파일은 어떻게 표현할까요?

A) (권장) `ContentBlock`을 discriminated union으로 두고 `type` 값별 전용 payload 모델을 둔다.

추천 사유: 원문 순서는 보존해야 하지만 block마다 필요한 필드가 다릅니다. type별 payload가 있으면 JSONL 검증, parser 테스트, Polars 정규화 준비가 쉬워집니다.

B) 하나의 `ContentBlock` 모델에 모든 optional field를 둔다.

C) `content.blocks`는 검증하지 않는 `dict` 목록으로 둔다.

[Answer]: A

### Question 5. 식별자 타입

게시글 번호, 댓글 번호, 게시판 ID 같은 식별자는 어떤 타입으로 저장할까요?

A) (권장) 원본 식별자는 문자열로 보존하고, 숫자 비교가 필요한 `document_srl`, `comment_srl`은 정규화된 int 필드를 함께 둔다.

추천 사유: URL/DOM에서 나온 원본값을 그대로 보존하면서도 범위 필터, 정렬, dedupe에는 숫자 필드를 안정적으로 쓸 수 있습니다.

B) 모든 식별자를 문자열로만 저장한다.

C) 숫자로 보이는 식별자는 모두 int로만 저장한다.

[Answer]: A

### Question 6. 댓글/BEST 댓글 모델

일반 댓글, 대댓글, BEST 댓글은 어떤 스키마로 저장할까요?

A) (권장) 하나의 `Comment` 모델에 `source_dom_id`, `source_order`, `parent_comment_srl`, `depth`, `is_best`, `badges`, `reactions`를 모두 둔다.

추천 사유: 기능 명세서에서 BEST 댓글도 `comments` 배열에 저장하기로 했고, Polars 정규화 시 별도 comments 테이블로 펼치기 쉽습니다.

B) 일반 댓글은 `comments`, BEST 댓글은 `best_comments`로 분리한다.

C) BEST 여부와 추천/비추천 정보는 `metadata`에만 저장한다.

[Answer]: A

### Question 7. Public API 오류 모델

library, CLI, container, MCP가 공유할 오류는 어떻게 표현할까요?

A) (권장) 내부 예외는 typed exception으로 두고, adapter 경계에서는 `ErrorResult(code, message, details)` 모델로 변환한다.

추천 사유: core 내부에서는 예외가 흐름 제어에 편하고, 외부 경계에서는 secret이 제거된 구조화 오류가 필요합니다.

B) 모든 API가 예외만 던지게 한다.

C) 모든 API가 성공/실패 union result만 반환하고 예외는 사용하지 않는다.

[Answer]: A

### Question 8. Schema versioning

JSONL, checkpoint, failure, report schema version은 어떻게 관리할까요?

A) (권장) top-level `PostResult`, `Checkpoint`, `FailureRecord`, `JobReport`에 `schema_version`을 넣고 1차 값은 `"fmkorea.v1"`, `"checkpoint.v1"`처럼 명시한다.

추천 사유: 향후 공통 분석 schema와 다른 커뮤니티 scraper가 추가됩니다. 지금 version 필드를 넣어두면 migration과 normalizer가 단순해집니다.

B) schema version은 파일명이나 metadata 파일에만 둔다.

C) v1 단계에서는 version field를 생략한다.

[Answer]: A

### Question 9. Port protocol 범위

UOW-001에서 정의할 protocol은 어디까지로 제한할까요?

A) (권장) 외부 I/O 경계인 HTTP, output, media, failure, checkpoint, clock, logger port만 최소 protocol로 정의한다.

추천 사유: Application Design에서 parser/service 전체를 interface로 감싸지 않기로 했습니다. I/O 경계만 protocol로 두면 테스트 가능성은 확보하면서 추상화 비용은 줄일 수 있습니다.

B) service, parser, collector까지 모두 protocol로 정의한다.

C) UOW-001에서는 protocol을 만들지 않고 concrete class만 둔다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌을 확인합니다.
2. 추가 확인이 필요하면 follow-up 질문 파일을 만듭니다.
3. 문제가 없으면 UOW-001 Functional Design 산출물 3개를 생성합니다.
4. 생성 후 review gate에서 멈춥니다.

## Answer Analysis

- Q1은 답변란이 비어 있었지만, 사용자가 질문지 답변 확정을 요청했고 나머지 답변이 모두 권장안 A였으므로 권장안 A로 확정 처리했다.
- Q2-Q9는 모두 A로 확정되었다.
- 답변 간 충돌은 없다.
- follow-up 질문은 필요하지 않다.

## Functional Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-001-core-models-and-config/functional-design/domain-entities.md`
- `aidlc-docs/construction/uow-001-core-models-and-config/functional-design/business-rules.md`
- `aidlc-docs/construction/uow-001-core-models-and-config/functional-design/business-logic-model.md`

승인 후 다음 단계는 `UOW-001 NFR Requirements`다.
