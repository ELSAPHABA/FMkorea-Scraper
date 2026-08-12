# Services Design

## Service Layer Overview

Application Design 단계의 service는 orchestration 경계만 정의합니다. URL selector, HTML 파싱 세부, retry 조건, checkpoint edge case는 각 UOW Functional Design에서 확정합니다.

## ScraperFacade

- **Responsibility**: library, CLI, container, MCP가 공유하는 최상위 API.
- **Collaborators**: `JobConfigValidator`, `JobRunner`, `LinkCollector`, `PostDetailService`, `ParserFailureRetryService`.
- **Interactions**:
  - 단건 API는 필요한 parser/service만 호출한다.
  - Job API는 `JobRunner`에 위임한다.
  - retry API는 `ParserFailureRetryService`에 위임한다.

## RuntimePolicyService

- **Responsibility**: HTTP runtime policy 구성.
- **Collaborators**: `UserAgentProvider`, `ProxyProvider`, `HttpClient`.
- **Rules**:
  - global request interval 기본값은 1초다.
  - User-Agent 기본 교체 주기는 요청 10회마다 1회다.
  - 명시 proxy option이 `.env`보다 우선한다.
  - optional cookie file은 명시 입력일 때만 사용한다.
  - secret, raw cookie, proxy password는 log/output/checkpoint/failure에 남기지 않는다.

## SearchCollectionService

- **Responsibility**: 게시글 후보 URL을 순차적으로 수집해 worker queue에 넣음.
- **Collaborators**: `HttpClient`, `FmkoreaUrlBuilder`, `BoardSearchParser`, `IntegratedSearchParser`, `JobConfig`, `Checkpoint`.
- **Supported Modes**:
  - direct post URL
  - board list
  - board search
  - integrated search
  - deep search
  - no-keyword range
  - realtime keyword
  - realtime all
- **Rules**:
  - Job당 한 collector만 실행한다.
  - 후보는 `(site_id, board_id, document_srl)` 기준으로 dedupe한다.
  - 목록/검색 단계 값은 candidate metadata로만 쓰고, 최종 저장값은 상세 페이지에서 다시 파싱한다.

## PostDetailService

- **Responsibility**: 게시글 상세 1건을 `PostResult`로 수집.
- **Collaborators**: `HttpClient`, `PostMetadataParser`, `ContentBlockParser`, `CommentService`, `MediaService`.
- **Flow**:
  1. 상세 HTML fetch.
  2. 접근 불가, 삭제, 로그인 필요, CAPTCHA, 차단 응답 분류.
  3. metadata와 body content blocks 파싱.
  4. 댓글 수집 옵션이 켜져 있으면 `CommentService` 호출.
  5. media 다운로드 옵션에 따라 URL only 또는 file save 처리.
  6. `PostResult` 반환.
- **Rules**:
  - FMKorea 원본 JSONL에는 `is_repost`, `repost`를 저장하지 않는다.
  - 핵심 metadata 파싱 실패는 게시글 parser-stage 실패로 기록한다.
  - 댓글/media 하위 실패는 가능한 경우 safe failure metadata로 기록하고 게시글 결과를 보존한다.

## CommentService

- **Responsibility**: 댓글/답글 DOM 파싱과 댓글 모델 생성.
- **Collaborators**: `CommentParser`, `HttpClient` where comment pagination/subfetch is required.
- **Rules**:
  - 댓글은 `comments` flat list로 저장한다.
  - BEST 댓글은 `is_best=true`, `badges=["BEST"]`로 표시한다.
  - `reactions.up_count`, `reactions.down_count`, `reactions.score`를 저장한다.
  - 댓글 정렬은 저장 배열 순서가 아니라 `date`, `comment_srl`, `source_order` 기준으로 분석 단계에서 수행한다.

## MediaService

- **Responsibility**: 본문 media metadata 추출과 선택적 다운로드.
- **Collaborators**: `ContentBlockParser`, `HttpClient`, `MediaStorePort`.
- **Rules**:
  - 기본은 URL metadata 저장이다.
  - YouTube와 X 외부 임베드는 다운로드하지 않는다.
  - 다운로드 실패는 게시글 실패가 아니라 media failure로 기록한다.
  - 컨테이너에서는 S3-compatible store를 사용하고 Garage 전용 API에 묶이지 않는다.

## StorageService

- **Responsibility**: 결과, 실패 기록, checkpoint 저장 흐름 조정.
- **Collaborators**: `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, `CheckpointStorePort`.
- **Implementations**:
  - local JSONL and local media
  - local checkpoint file
  - S3-compatible object storage with Garage as default
  - PostgreSQL checkpoint
- **Rules**:
  - JSONL 결과 저장이 성공한 뒤 checkpoint completed key를 갱신한다.
  - resume Job은 기존 JSONL에 append하지 않고 새 run output을 만든다.
  - common Polars schema normalization은 원본 JSONL을 변경하지 않는 후속 변환으로 둔다.

## JobRunner

- **Responsibility**: Job lifecycle orchestration.
- **Collaborators**: `SearchCollectionService`, `PostWorkerPool`, `StorageService`, `CheckpointStorePort`, `LoggerPort`.
- **Flow**:
  1. `JobConfig` 검증.
  2. checkpoint 생성 또는 resume checkpoint 로드.
  3. link collector 시작.
  4. post worker pool 시작.
  5. 게시글 저장 성공 후 completed key와 checkpoint 갱신.
  6. CAPTCHA, block, 오류, 수동 중단 시 `status="stopped"` checkpoint 저장.
  7. 정상 완료 시 `status="completed"` checkpoint와 Job report 저장.

## PostWorkerPool

- **Responsibility**: 큐의 게시글 후보를 병렬로 상세 수집.
- **Collaborators**: `PostDetailService`, `StorageService`, `CheckpointStorePort`.
- **Rules**:
  - queue item은 게시글 링크 1개다.
  - worker 수는 `WorkerConfig`로 제한한다.
  - in-flight 작업의 완전 복원은 보장하지 않고 completed key dedupe로 중복 저장을 막는다.

## ParserFailureRetryService

- **Responsibility**: parser-stage 실패 게시글만 재수집.
- **Collaborators**: `FailureStorePort`, `JobRunner`, `OutputStorePort`.
- **Rules**:
  - parser-stage post/comment/content 실패만 retry 대상으로 선택한다.
  - CAPTCHA, block, network, storage, checkpoint, manual stop 실패는 제외한다.
  - retry 결과는 원본 failure file을 수정하지 않고 새 run에 저장한다.

## CliRuntimeService

- **Responsibility**: 터미널 실행을 core Job으로 변환.
- **Collaborators**: `JobConfigValidator`, `ScraperFacade`.
- **Rules**:
  - terminal prompt는 adapter 내부에만 둔다.
  - core package import 시 prompt, network request, file write side effect가 없어야 한다.

## ContainerRuntimeService

- **Responsibility**: one-shot worker container 실행 계약 처리.
- **Collaborators**: `JobConfigValidator`, `ScraperFacade`, `StorageService`.
- **Rules**:
  - env/config로 Job 또는 resume request를 받는다.
  - `RESUME=true`와 `JOB_ID`를 지원한다.
  - JSONL/media는 S3-compatible store, checkpoint는 PostgreSQL adapter를 사용할 수 있다.

## McpRuntimeService

- **Responsibility**: MCP tool을 core API로 위임.
- **Collaborators**: `ScraperFacade`, `JobConfigValidator`.
- **Tools**:
  - `search_board`
  - `search_integrated`
  - `fetch_post`
  - `fetch_comments`
  - `run_job`
  - `resume_job`
  - `retry_parser_failures`
- **Rules**:
  - MCP는 별도 scraper logic을 가지지 않는다.
  - 오류 응답은 secret, raw credential, raw cookie, internal stack trace를 숨긴다.

## CdkRuntimeDesign

- **Responsibility**: 선택 배포 경로의 인프라 경계를 정의.
- **Collaborators**: `ContainerAdapter`, `StorageService`, AWS CDK stacks.
- **Rules**:
  - 1차는 one-shot worker 실행 인프라를 기준으로 한다.
  - future queue daemon, SQS 소비, 통합 플랫폼 scheduler는 후속 확장으로 둔다.
