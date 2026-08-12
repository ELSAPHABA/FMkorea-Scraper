# Functional Design 계획 - UOW-004 Post Detail And Content Parsing

이 계획은 `UOW-004 Post Detail And Content Parsing`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-004 Post Detail And Content Parsing
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection
- **Primary Stories**: US-007, US-008, US-009
- **Supporting Stories**: US-011, US-015
- **Scope**: post detail metadata parsing, canonical URL resolution, ordered content block parsing, image/FM Korea video/YouTube/X/link/attachment metadata extraction, comment/reply parsing, BEST comment fields, post-level parser errors
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 상세 게시글 파서 구조를 최대한 계승하되, FMKorea-specific DOM selector와 미디어/comment 구조를 반영하는 권장안으로 작성한다.
- **Out Of Scope**: link collection, queue ownership, worker lifecycle, checkpoint persistence, JSONL/Garage/PostgreSQL storage, media file download/write, CLI prompt UX, container/MCP hosting

## Functional Design 작업 체크리스트

- [x] UOW-003 Build and Test 승인 확인
- [x] UOW-004 범위 확인
- [x] `docs/FMKorea-Scraper_Function_Specification.md` 상세/본문/댓글 항목 확인
- [x] UOW-001 `PostResult`, `BodyContent`, `MediaItem`, `Comment` 모델 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. Post Detail Service Boundary

UOW-004의 상세 게시글 수집 서비스는 어떤 입력/출력 경계를 가질까요?

A) (권장) `PostCandidate` 또는 `PostRequest`를 받아 caller가 주입한 UOW-002 `HttpClient`/`HttpPort`로 상세 HTML을 가져오고, 최종 `PostResult`를 반환한다. Queue 투입, checkpoint, 저장소 쓰기는 UOW-005/UOW-006에 둔다.

추천 사유: 디시인사이드 스크래퍼의 “링크 수집 → 상세 파서 → 저장/체크포인트” 경계를 계승합니다. UOW-004는 게시글 1개를 최종 JSON 모델로 만드는 일에 집중할 수 있습니다.

B) UOW-004가 `asyncio.Queue`에서 후보를 직접 소비하고 저장소까지 호출한다.

C) UOW-004는 HTML 문자열 parser만 제공하고 HTTP fetch는 전부 UOW-005에서 처리한다.

X) 기타

[Answer]: A

### Question 2. Model Schema Extension

기능명세서에 있지만 현재 UOW-001 모델에 빠져 있는 미디어/첨부 필드는 어떻게 처리할까요?

A) (권장) Code Generation에서 기존 UOW-001 모델을 backward-compatible하게 확장한다. 예: image `file_srl`, `width`, `height`, `download_url`, fmk_video `file_srl`, `download_url`, `name`, `upload_date`, `width`, `height`, YouTube `start_seconds`, X `tweet_id`/`embed_url`, attachment `file_srl`/`sid`/`mid`/download text. 알 수 없는 값만 `metadata`에 둔다.

추천 사유: 명세서의 JSONL 필드는 Polars 가공 대상입니다. 안정 필드를 `metadata`에 숨기면 분석 스키마가 약해집니다. 기존 모델에는 optional 필드만 추가하면 기존 테스트와 JSON 호환성을 유지할 수 있습니다.

B) 기존 모델은 수정하지 않고 모든 추가 값을 각 block/media/attachment의 `metadata`에 저장한다.

C) UOW-004 전용 별도 post result 모델을 새로 만든다.

X) 기타

[Answer]: A

### Question 3. Final Metadata Parsing

상세 페이지의 최종 메타데이터는 어떻게 확정할까요?

A) (권장) `#bd_capture` 내부에서 제목, 작성자, 작성일, 조회수, 추천 수, 댓글 수, 말머리, 첨부파일, canonical URL을 다시 파싱한다. UOW-003 candidate metadata는 상세 페이지 값이 없을 때만 fallback으로 사용한다.

추천 사유: 기능명세서가 목록/검색 단계 값은 힌트로만 사용한다고 정했습니다. 최종 저장값은 상세 페이지 기준이어야 합니다.

B) 후보 목록의 metadata를 최종값으로 우선 사용하고 상세 페이지는 본문만 파싱한다.

C) 제목과 URL만 필수로 파싱하고 작성자/조회수/추천수/댓글수는 저장하지 않는다.

X) 기타

[Answer]: A

### Question 4. Content Container And DOM Traversal

본문 콘텐츠는 어떤 기준으로 파싱할까요?

A) (권장) `#bd_capture .rd_body article > .xe_content`를 1순위, `#bd_capture .rd_body .xe_content`를 2순위로 사용하고, 기준 컨테이너 하위 노드를 DOM 순서대로 순회해 `content.blocks`를 만든다. 전역 `.xe_content` 단독 선택자는 사용하지 않는다.

추천 사유: 기능명세서의 광고/목록 영역 오인식을 피하는 기준입니다. DOM 순서 보존은 이미지, 텍스트, 영상, 링크가 혼재된 게시글을 재구성하는 데 필요합니다.

B) 전역 `.xe_content` 중 첫 번째를 사용한다.

C) 본문 전체 텍스트만 추출하고 block 순서는 저장하지 않는다.

X) 기타

[Answer]: A

### Question 5. Text And Link Block Rules

본문 텍스트와 일반 링크는 어떻게 저장할까요?

A) (권장) 빈 노드, `<br>`만 있는 노드, 플레이어 UI, `BeforeDocument`/`AfterDocument`, 첨부파일 표 텍스트를 제외한다. 일반 텍스트는 `text` block으로, 일반 링크와 bare URL은 `link` block으로 저장하되 이미지 highslide, FMKorea video download, YouTube, X 링크는 전용 block과 중복 저장하지 않는다.

추천 사유: 원문 의미 있는 텍스트만 `content.text`와 block에 남기면서, 미디어 전용 URL 중복을 줄일 수 있습니다.

B) 기준 컨테이너의 모든 텍스트와 모든 링크를 그대로 저장한다.

C) 일반 링크는 모두 무시하고 텍스트만 저장한다.

X) 기타

[Answer]: A

### Question 6. Image And Attachment Parsing

이미지와 첨부파일은 어떻게 연결할까요?

A) (권장) 이미지 URL은 부모 `a.highslide[href]`를 `img[src]`보다 우선하고, `data-file-srl`이 있으면 `.rd_file a[data-href]`의 같은 `file_srl` 첨부/다운로드 URL과 매칭한다. 첨부파일은 `attachments`와 필요 시 `attachment` block으로 별도 보존한다.

추천 사유: 에펨코리아는 본문 이미지와 첨부 다운로드 정보가 분리될 수 있습니다. `file_srl` 매칭이 있으면 나중 미디어 저장/분석이 안정적입니다.

B) 이미지는 `img[src]`만 저장하고 첨부파일은 무시한다.

C) 첨부파일만 저장하고 본문 이미지 block은 만들지 않는다.

X) 기타

[Answer]: A

### Question 7. FMKorea Video Parsing

펨코 자체 업로드 동영상은 어떻게 파싱할까요?

A) (권장) `.auto_media_wrapper`, `video.mediaelement_video`, `video > source[type="video/mp4"]`, schema.org `meta[itemprop]`를 BeautifulSoup으로 파싱해 `fmk_video` block을 하나만 만든다. `source` 하위 노드는 중복 block으로 저장하지 않고, description이 없으면 `null`로 둔다.

추천 사유: 기능명세서상 정적 HTML만으로 동영상 URL, 포스터, 설명, 업로드일 등을 얻을 수 있습니다. 별도 브라우저 렌더링은 기본 구현에 필요하지 않습니다.

B) 동영상은 poster 이미지만 image block으로 저장한다.

C) Playwright 렌더링 후 video player 상태를 읽어야만 저장한다.

X) 기타

[Answer]: A

### Question 8. YouTube And X Embed Parsing

YouTube와 X/Twitter 임베드는 어떻게 처리할까요?

A) (권장) BeautifulSoup 기본 구현은 정적 HTML의 `youtube.com/watch`, `youtu.be`, `x.com/.../status/...`, `twitter.com/.../status/...` URL을 파싱해 provider ID와 embed URL을 만든다. HTML에 iframe이 이미 있으면 참고하지만, 렌더링 전용 iframe 수집은 optional로 둔다.

추천 사유: 사용자가 Playwright를 기본으로 쓰고 싶지 않다고 했고, 기능명세서도 BeautifulSoup 기반 기본 구현을 전제로 합니다.

B) 렌더링 후 iframe만 신뢰하고 정적 URL은 무시한다.

C) 외부 임베드는 전부 일반 link block으로만 저장한다.

X) 기타

[Answer]: A

### Question 9. Media Download Boundary

미디어 파일 다운로드는 UOW-004에서 수행할까요?

A) (권장) 아니요. UOW-004는 image/fmk_video/youtube/x/link/attachment metadata와 download candidate만 만든다. 실제 파일 다운로드, 로컬 path/object key 저장, media mode 적용은 UOW-006 또는 worker/storage 통합 단계에서 처리한다.

추천 사유: UOW-004가 파일 저장까지 하면 parser와 storage 책임이 섞입니다. 상세 파서는 URL과 metadata만 안정적으로 뽑으면 됩니다.

B) 이미지와 동영상 파일 다운로드까지 UOW-004에서 수행한다.

C) media mode가 URL_ONLY면 파싱도 생략한다.

X) 기타

[Answer]: A

### Question 10. Comment Collection Scope

댓글 수집은 UOW-004에서 어디까지 담당할까요?

A) (권장) UOW-004는 상세 HTML의 `.fdb_lst_ul` 댓글과, 같은 상세 페이지에서 발견 가능한 댓글 page/fragment URL이 있으면 injected HTTP로 순차 fetch해 파싱한다. 반복 Job lifecycle, checkpoint, 저장은 UOW-005/UOW-006에 둔다. 추가 댓글 URL을 발견하지 못하면 현재 HTML의 댓글만 반환하고 safe warning을 남긴다.

추천 사유: 댓글은 게시글 상세 수집의 일부지만, worker/checkpoint/storage는 별도 unit 책임입니다. 발견 가능한 범위만 순차 수집하면 차단 위험과 구현 복잡도를 낮출 수 있습니다.

B) UOW-004는 최초 상세 HTML에 포함된 댓글만 파싱하고 추가 댓글 페이지는 지원하지 않는다.

C) 댓글 수집은 UOW-005 JobRunner에서 직접 구현한다.

X) 기타

[Answer]: A

### Question 11. Comment Shape, BEST, And Reactions

댓글/덧글과 BEST 댓글은 어떤 스키마로 저장할까요?

A) (권장) 모든 댓글은 하나의 flat `comments` list에 저장한다. BEST 댓글도 별도 배열을 만들지 않고 `is_best=true`, `badges=["BEST"]`를 설정한다. `source_dom_id`, `source_order`, `depth`, `parent_comment_srl`, `reactions.up_count`, `reactions.down_count`, `reactions.score`를 채운다.

추천 사유: UOW-001 모델과 기능명세서가 이미 flat comment list와 BEST badge 방식을 확정했습니다. Polars 정규화도 이 구조가 단순합니다.

B) BEST 댓글은 `best_comments` 배열로 분리한다.

C) 댓글은 원본 HTML 문자열만 저장하고 구조화하지 않는다.

X) 기타

[Answer]: A

### Question 12. Parser Failure Policy

상세 페이지 파싱 실패는 어떻게 처리할까요?

A) (권장) `document_srl`/canonical URL/title처럼 게시글 식별과 최소 저장에 필요한 필드가 없으면 post-level `ParseFailureError`로 실패한다. 선택 필드, 개별 content block, 개별 media, 개별 comment 파싱 실패는 safe parse warning으로 `PostResult.metadata`에 남기고 가능한 나머지 결과는 반환한다.

추천 사유: 필수 식별 실패는 나중 재처리 대상이 되어야 하지만, 선택 미디어 하나 때문에 게시글 전체를 버리면 손실이 큽니다.

B) 하나의 content block이나 comment라도 실패하면 게시글 전체를 실패 처리한다.

C) 모든 parser 실패를 조용히 무시하고 기록하지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-004 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-004 NFR Requirements로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T11:37:50Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper detail parser boundary while using FMKorea-specific selectors, content block types, media metadata, and BEST comment fields.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Model Note**: UOW-004 Code Generation may extend existing UOW-001 models with optional fields for documented media/attachment values while preserving backward compatibility.
- **Follow-up Questions**: Not required.

## Functional Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/business-logic-model.md`
- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/business-rules.md`
- `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/functional-design/domain-entities.md`

승인 후 다음 단계는 `UOW-004 NFR Requirements`이다.
