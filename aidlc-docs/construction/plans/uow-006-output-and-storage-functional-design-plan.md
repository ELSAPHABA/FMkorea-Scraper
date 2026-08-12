# Functional Design 계획 - UOW-006 Output And Storage

이 계획은 `UOW-006 Output And Storage`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-006 Output And Storage
- **Depends On**: UOW-001 Core Models And Config
- **Consumes**: UOW-004 `PostResult`, `Comment`, content/media/attachment models
- **Primary Stories**: US-010, US-011
- **Supporting Stories**: US-008, US-009, US-012, US-013, US-014, US-016
- **Scope**: Job JSONL output, failure records, Job reports, local media storage, S3-compatible output/media storage with Garage as default, local checkpoint store, Polars-friendly source JSONL verification
- **Baseline Inheritance**: `A)` 선택지는 기준 스크래퍼의 storage/output/checkpoint 경계를 최대한 계승하되, FMKorea 원본 JSONL 스키마와 BEST comment 필드 구조를 반영하는 권장안으로 작성한다.
- **Out Of Scope**: link collection, post detail parsing, worker queue lifecycle, retry scheduling, CAPTCHA stop orchestration, CLI prompts, PostgreSQL checkpoint adapter, container/MCP hosting, AWS CDK

## Functional Design 작업 체크리스트

- [x] UOW-004 Build and Test 승인 확인
- [x] UOW-006이 UOW-005보다 먼저 실행되어야 하는 의존성 확인
- [x] `docs/FMKorea-Scraper_Function_Specification.md`의 JSONL, Garage, checkpoint, failure record 요구사항 확인
- [x] UOW-001 `PostResult`, `FailureRecord`, `JobReport`, `StoredObjectRef`, `Checkpoint` 모델 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-006-output-and-storage/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-006-output-and-storage/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-006-output-and-storage/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. Storage Service Boundary

UOW-006의 저장소 API 경계는 어떻게 둘까요?

A) (권장) `OutputStore`, `MediaStore`, `FailureStore`, `CheckpointStore` 포트를 각각 구현하고, 저장 성공 시 `StoredObjectRef` 또는 갱신된 `MediaItem`을 반환한다. Job 실행 순서, retry, checkpoint commit 호출 시점은 UOW-005가 담당한다.

추천 사유: 기준 스크래퍼처럼 저장소는 저장만 책임지고, 워커/체크포인트 순서는 JobRunner가 책임지는 경계가 작고 명확합니다.

B) 하나의 `StorageService`가 post 저장, media 다운로드, failure 기록, checkpoint advance 순서까지 모두 직접 관리한다.

C) JSONL writer 함수만 만들고 failure/report/media/checkpoint는 후속 unit으로 미룬다.

X) 기타

[Answer]: A`r`n
### Question 2. JSONL File Naming And Resume

Job JSONL 파일 이름과 resume 시 파일 생성 규칙은 어떻게 둘까요?

A) (권장) `outputs/<job_id>/<run_id>/posts.jsonl`을 기본으로 만들고, resume은 같은 `job_id` 아래 새 `run_id` 디렉터리의 새 `posts.jsonl`에 기록한다.

추천 사유: Job 단위 추적과 resume 시 기존 JSONL에 이어 쓰지 않는 요구사항을 동시에 만족합니다. run별 실패/리포트 파일도 같은 디렉터리에 둘 수 있습니다.

B) 실행 파일 옆에 `<job_id>.jsonl` 하나만 만들고 resume 때도 같은 파일에 append한다.

C) 게시글마다 별도 JSON 파일을 만든다.

X) 기타

[Answer]: A`r`n
### Question 3. PostResult JSON Serialization Shape

`PostResult`를 JSONL 한 줄로 직렬화할 때 어떤 규칙을 적용할까요?

A) (권장) Pydantic `model_dump(mode="json")` 기반으로 top-level scalar와 nested `content`, `attachments`, `media`, `comments` 구조를 그대로 저장하고, 선택 필드는 `null`을 유지한다. FMKorea 원본 JSONL에는 `is_repost`, `repost`를 추가하지 않는다.

추천 사유: 원본 JSONL은 수집 원자료 보존이 우선입니다. Polars는 nested struct/list를 읽을 수 있고, 댓글 별도 테이블 분리는 후속 정규화 단계가 더 적절합니다.

B) 저장 시점에 게시글, 댓글, 미디어를 각각 별도 JSONL 파일로 분리한다.

C) 본문과 댓글을 문자열로 합쳐 flat JSON만 저장한다.

X) 기타

[Answer]: A`r`n
### Question 4. Local Output Write Policy

로컬 JSONL과 report 파일 쓰기는 어떤 정책으로 처리할까요?

A) (권장) `posts.jsonl`과 `failures.jsonl`은 append 후 flush 가능한 writer로 유지하고, `report.json`과 checkpoint는 임시 파일 작성 후 atomic replace로 쓴다. 저장 디렉터리는 필요할 때 생성한다.

추천 사유: JSONL은 append 로그라 매번 전체 파일을 rewrite할 필요가 없습니다. 반면 report/checkpoint는 부분 쓰기 파일이 남으면 재개 판단이 깨질 수 있어 atomic replace가 맞습니다.

B) 모든 파일을 매 record마다 전체 rewrite한다.

C) 모든 파일을 프로세스 종료 시점에만 한 번 쓴다.

X) 기타

[Answer]: A`r`n
### Question 5. Media Storage Contract

이미지, FMKorea video, 첨부파일 같은 미디어 파일 저장은 어디까지 UOW-006에서 담당할까요?

A) (권장) UOW-006은 이미 다운로드된 bytes를 받아 `media/<job_id>/<board_id>/<document_srl>/<media_type>/<filename>`에 저장하고 `MediaItem`의 `file_path` 또는 `object_key`를 채워 반환한다. HTTP 다운로드 여부와 대상 선택은 UOW-005/adapter 옵션이 결정한다.

추천 사유: 저장소가 HTTP를 알면 UOW-002 정책과 책임이 섞입니다. 저장소는 bytes 저장만 맡는 쪽이 단순하고 테스트도 쉽습니다.

B) UOW-006이 URL을 받아 직접 HTTP 다운로드까지 수행한다.

C) 1차 구현에서는 미디어 저장을 제외하고 URL만 JSONL에 남긴다.

X) 기타

[Answer]: A`r`n
### Question 6. Failure Records And Reports

실패 기록과 Job report는 어떻게 저장할까요?

A) (권장) 같은 `outputs/<job_id>/<run_id>/` 아래 `failures.jsonl`과 `report.json`을 둔다. 실패 기록은 safe reason, stage, retryable, post key, URL 정도만 포함하고 raw HTML, cookie, proxy credential, token, password는 저장하지 않는다.

추천 사유: 성공/실패/요약을 한 run 디렉터리에 두면 수집 결과 검토와 재시도가 쉽고, 보안 요구사항도 지킬 수 있습니다.

B) 실패 기록을 `posts.jsonl` 안에 성공 결과와 섞어 저장한다.

C) 실패 기록은 로그에만 남기고 파일로 저장하지 않는다.

X) 기타

[Answer]: A`r`n
### Question 7. Local Checkpoint Store

로컬 `Checkpoint.json`은 어떤 구조로 저장할까요?

A) (권장) `StorageConfig.base_output_path` 기준 위치에 `Checkpoint.json` 하나를 두고, 내부에는 여러 `job_id`의 최신 checkpoint를 map 형태로 저장한다. `load(job_id)`와 `load_latest()`를 지원하고, 쓰기는 임시 파일 작성 후 atomic replace로 처리한다.

추천 사유: 요구사항의 `Checkpoint.json` 파일명을 유지하면서도 여러 Job과 가장 최근 checkpoint 조회를 지원할 수 있습니다.

B) Job마다 `Checkpoint-<job_id>.json` 파일을 만든다.

C) 항상 단일 checkpoint만 저장하고 이전 Job checkpoint는 덮어쓴다.

X) 기타

[Answer]: A`r`n
### Question 8. Garage/S3-Compatible Storage

Garage 기반 S3 호환 저장소는 어떤 경계로 구현할까요?

A) (권장) `S3ObjectStore`는 S3-compatible port 구현으로 두고, endpoint, bucket, credentials, region은 config로 받는다. Garage 전용 API에 묶이지 않고, boto3 계열 의존성은 기존 `s3` extra를 사용한다.

추천 사유: Garage와 SeaweedFS 모두 S3 호환 경계로 유지할 수 있습니다. S3 서명을 직접 구현하는 것은 유지보수 비용이 큽니다.

B) Garage HTTP API에 직접 맞춘 전용 클라이언트를 만든다.

C) UOW-006에서는 S3 port만 정의하고 구현은 UOW-008로 미룬다.

X) 기타

[Answer]: A`r`n
### Question 9. Idempotency Boundary

중복 저장 방지는 어디에서 처리할까요?

A) (권장) UOW-006은 append-only 저장소로 두고, `(site_id, board_id, document_srl)` 중복 여부 판단은 UOW-005 checkpoint/completed key가 담당한다. 단, 저장된 JSONL record에는 중복 판정에 필요한 key를 항상 포함한다.

추천 사유: JSONL append 저장소가 파일 전체를 매번 스캔해 dedupe하면 느리고 복잡합니다. 중복 방지는 JobRunner 상태에서 처리하는 편이 작습니다.

B) `OutputStore`가 JSONL 파일을 읽어 이미 저장된 post key를 검사한 뒤 append한다.

C) 중복 저장은 허용하고 후처리에서 제거한다.

X) 기타

[Answer]: A`r`n
### Question 10. Polars And Common Schema Readiness

Polars 가공 및 향후 공통 분석 스키마 정규화는 UOW-006에서 어디까지 다룰까요?

A) (권장) UOW-006은 원본 JSONL을 그대로 보존하고, 작은 fixture로 Polars `read_ndjson`, nested `comments` explode, content/media projection이 가능한지만 smoke test한다. 공통 분석 스키마로 정규화하는 production pipeline은 후속 플랫폼 단계 참고사항으로 둔다.

추천 사유: 지금 필요한 것은 저장된 원본이 분석 가능한 구조인지 검증하는 것입니다. 공통 플랫폼용 정규화 파이프라인을 이 스크래퍼 내부에 미리 크게 만들 필요는 없습니다.

B) UOW-006에서 posts/comments/media 공통 분석 테이블 JSONL까지 모두 생성한다.

C) Polars 검증은 하지 않고 원본 JSONL만 저장한다.

X) 기타

[Answer]: A`r`n
### Question 11. Optional Dependency Handling

S3/Garage와 Polars 관련 의존성은 어떻게 사용할까요?

A) (권장) 기본 local 저장은 기본 의존성만 사용한다. S3-compatible 저장 테스트/구현은 `.[s3]`, Polars smoke는 `.[analysis]` optional extra가 설치된 경우 실행하고, 설치되지 않으면 명시적으로 skip한다.

추천 사유: 로컬 JSONL 저장만 쓰는 사용자가 S3/Polars 의존성을 항상 설치할 필요는 없습니다. 이미 pyproject에 optional extra가 나뉘어 있어 그대로 쓰면 됩니다.

B) boto3와 Polars를 기본 dependencies로 올린다.

C) S3와 Polars 기능을 전부 후속 unit으로 미룬다.

X) 기타

[Answer]: A`r`n
### Question 12. PostgreSQL Checkpoint Scope

PostgreSQL checkpoint adapter는 UOW-006에서 구현할까요?

A) (권장) 아니요. UOW-006은 local checkpoint store와 checkpoint port 계약 검증까지만 담당한다. PostgreSQL checkpoint adapter는 container/shared-store 실행 계약을 다루는 UOW-008에서 구현한다.

추천 사유: inception에서 이미 PostgreSQL checkpoint는 컨테이너/공유 저장소 흐름과 함께 검증하기로 정했습니다. UOW-006에 넣으면 저장소 범위가 커지고 UOW-008 책임과 겹칩니다.

B) UOW-006에서 PostgreSQL checkpoint adapter까지 구현한다.

C) checkpoint 저장을 모두 UOW-005로 옮긴다.

X) 기타

[Answer]: A`r`n
## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-006 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-006 NFR Requirements로 넘어가지 않습니다.

## Functional Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-006-output-and-storage/functional-design/business-logic-model.md`
- `aidlc-docs/construction/uow-006-output-and-storage/functional-design/business-rules.md`
- `aidlc-docs/construction/uow-006-output-and-storage/functional-design/domain-entities.md`

승인 후 다음 단계는 `UOW-006 NFR Requirements`이다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T13:01:16Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options preserve the baseline scraper output/storage/checkpoint boundaries while using FMKorea source JSONL keys and excluding non-FMKorea fields such as `is_repost` and `repost`.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Scope Note**: PostgreSQL checkpoint remains deferred to UOW-008; UOW-006 owns local checkpoint and output/storage ports.
- **Follow-up Questions**: Not required.

