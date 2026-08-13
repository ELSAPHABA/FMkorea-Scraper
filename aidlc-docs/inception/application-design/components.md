# Application Components

## Package Boundary

1차 구현은 단일 Python 패키지 `fmkorea_scraper` 안에서 하위 모듈을 나눕니다. CLI, container, MCP는 같은 core library를 호출하는 얇은 adapter입니다.

| Module | Responsibility |
|---|---|
| `models` | Pydantic request/result/content/comment/checkpoint/failure models |
| `core` | public async API, config validation, ports, typed errors |
| `http` | request delay, retry, timeout, User-Agent, proxy, in-memory temporary cookie lifecycle, block/CAPTCHA classification |
| `search` | FMKorea URL/query builders, board/list/search/integrated/deep/realtime link collection |
| `post_detail` | FMKorea post metadata, content/media, attachment, comment/reply parsing |
| `storage` | local JSONL/media, S3-compatible object storage, failure records, checkpoint ports |
| `jobs` | Job lifecycle, link collector plus post worker queue orchestration |
| `retry` | parser-stage failure reprocessor |
| `adapters` | CLI, terminal wizard, container entrypoint, MCP tools |
| `infra` | AWS CDK IaC path and deployment docs |

## Core Components

### PublicApi

- **Purpose**: Python import 사용자를 위한 async API 진입점.
- **Responsibilities**: `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, `retry_parser_failures` 노출.
- **Interface**: async functions returning Pydantic models.

### JobConfigValidator

- **Purpose**: CLI, wizard, container, MCP, library 입력을 같은 기준으로 검증.
- **Responsibilities**: collection mode, URL, board ID, keyword, category, date/post range, realtime termination, worker count, storage config validation.
- **Interface**: raw mapping 또는 typed request를 `JobConfig`로 변환.

### Ports

- **Purpose**: 외부 I/O 경계의 최소 protocol 정의.
- **Responsibilities**: HTTP, output, media, failure, checkpoint, clock, logger 포트 제공.
- **Constraint**: parser/service 전체를 interface로 감싸지 않고 외부 I/O 경계만 포트로 둔다.

## Model Components

### SourceJsonModels

- **Purpose**: FMKorea 원본 JSONL 스키마 정의.
- **Responsibilities**: `PostResult`, `AuthorInfo`, `CategoryInfo`, `ContentBlock`, `MediaItem`, `Attachment`, `Comment`, `ReactionInfo`, `FailureRecord`, `JobReport`.
- **Rules**:
  - `site_id="fmkorea"`를 사용한다.
  - 원본 JSONL에는 `is_repost`, `repost`를 저장하지 않는다.
  - `model_dump(mode="json")`으로 JSONL 직렬화한다.

### CommentModels

- **Purpose**: 댓글/답글과 BEST 댓글을 하나의 flat list 모델로 표현.
- **Responsibilities**: `comment_srl`, `source_dom_id`, `parent_comment_srl`, `depth`, `source_order`, `is_best`, `badges`, `author`, `date_raw`, `date`, `content`, `reactions`, `permalink`, `metadata.classes`.
- **Rules**:
  - BEST 댓글도 `comments` 배열에 저장한다.
  - `best_comments` 별도 배열은 만들지 않는다.
  - 빈 추천/비추천 값은 `0`으로 정규화한다.

### JobModels

- **Purpose**: Job 실행 입력과 저장 가능한 수집 옵션 모델 정의.
- **Responsibilities**: `JobConfig`, `ScrapeOptions`, `RangeFilter`, `RealtimeOptions`, `StorageConfig`, `WorkerConfig`, `ResumeRequest`.
- **Rules**:
  - realtime 종료 조건은 duration 또는 end_at 중 정확히 하나만 허용한다.
  - queue 단위는 게시글 링크 1개다.

### CheckpointModels

- **Purpose**: 공통 checkpoint/status schema 정의.
- **Responsibilities**: `Checkpoint`, `CheckpointStatus`, `StopReason`, collector cursor, completed key set, optional queued links snapshot.
- **Rules**:
  - in-flight 요청의 완전 복원은 보장하지 않는다.
  - 결과 저장 성공 후 checkpoint를 advance한다.

## HTTP Components

### HttpClient

- **Purpose**: 모든 외부 HTTP 요청 정책의 단일 적용 지점.
- **Responsibilities**: global delay, retry, timeout, User-Agent rotation, proxy, in-memory temporary cookie lifecycle, secret masking, CAPTCHA/block classification.
- **Interface**: async `get`, `post`, `download`, `close`.

### UserAgentProvider

- **Purpose**: `user-agents.txt` 로딩과 요청 10회 기본 교체.
- **Responsibilities**: one-line parsing, blank line skip, default fallback, request counter.

### ProxyProvider

- **Purpose**: proxy 설정 우선순위 적용.
- **Responsibilities**: explicit option priority, `.env` auto-load, container env injection compatibility, secret masking.

## Search Components

### FmkoreaUrlBuilder

- **Purpose**: FMKorea URL/query 생성과 정규화.
- **Responsibilities**: direct post URL, board list URL, board search URL, integrated search URL, category query, pagination query.

### BoardSearchParser

- **Purpose**: 게시판 목록/검색 HTML에서 게시글 후보 추출.
- **Responsibilities**: `document_srl`, board/category hint, candidate URL, candidate metadata, notice/ad exclusion, next-page detection.
- **Interface**: `parse(html, base_url) -> SearchPage`.

### IntegratedSearchParser

- **Purpose**: 통합 검색 HTML에서 게시글 후보와 deep-search board 후보 추출.
- **Responsibilities**: result rows, board candidate extraction, no-result detection, pagination guard.

### LinkCollector

- **Purpose**: Job당 단일 순차 링크 탐색.
- **Responsibilities**: direct URL, board list/search, integrated search, deep search, no-keyword range, realtime keyword/all, range filter, dedupe.

## Post Detail Components

### PostMetadataParser

- **Purpose**: 상세 HTML에서 최종 게시글 metadata 추출.
- **Responsibilities**: board, category, title, author, date, views, poten/blame count, comment count, canonical URL, attachments.

### ContentBlockParser

- **Purpose**: 본문 DOM을 순서 보존 content block으로 변환.
- **Responsibilities**: text, image, FMKorea video, YouTube, X/Twitter, link, attachment block 생성.

### CommentParser

- **Purpose**: FMKorea 댓글 DOM을 flat `Comment` list로 변환.
- **Responsibilities**: comment ID numeric extraction, BEST detection, badges, author/level/member parsing, date text, content text, recommendation/downvote parsing, reply parent mapping.

### PostDetailService

- **Purpose**: 게시글 상세 1건을 `PostResult`로 수집.
- **Responsibilities**: detail fetch, metadata parse, body parse, comments parse, media metadata/download coordination.

## Storage Components

### OutputStore

- **Purpose**: posts JSONL and report output.
- **Responsibilities**: local JSONL append, S3-compatible object write, idempotent post key handling, report finalize.

### MediaStore

- **Purpose**: image/video file output.
- **Responsibilities**: metadata-only mode, local file save, S3-compatible media save, failed media record.

### FailureStore

- **Purpose**: failure JSONL/report output.
- **Responsibilities**: parser-stage failure records, network/storage/checkpoint failure records, retry input compatibility.

### CheckpointStore

- **Purpose**: checkpoint persistence.
- **Responsibilities**: local checkpoint file, PostgreSQL checkpoint adapter, latest checkpoint lookup, atomic write.

## Job Components

### JobRunner

- **Purpose**: 전체 Job lifecycle 조율.
- **Responsibilities**: config validation, collector start, worker queue, output commit, checkpoint tick, stop handling, final report.

### PostWorkerPool

- **Purpose**: 게시글 상세 병렬 수집.
- **Responsibilities**: `asyncio.Queue` 소비, `PostDetailService` 호출, output/failure/checkpoint coordination.

## Retry Component

### ParserFailureRetryService

- **Purpose**: parser-stage 실패 게시글만 direct-post 경로로 재처리.
- **Responsibilities**: failure allowlist filtering, excluded failure counting, retry job creation, retry report generation, optional existing success skip.

## Adapter Components

### CliAdapter

- **Purpose**: 명령형 CLI와 터미널 마법사.
- **Responsibilities**: option parsing, wizard prompts, JobConfig 생성, resume/retry commands.

### ContainerAdapter

- **Purpose**: one-shot worker container runtime contract.
- **Responsibilities**: env/config loading, storage env validation, resume env support, structured stdout logs.

### McpAdapter

- **Purpose**: MCP tool 호출을 core API로 위임.
- **Responsibilities**: `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, `retry_parser_failures`.

### CdkApp

- **Purpose**: AWS CDK 기반 선택 배포 경로.
- **Responsibilities**: scraper container, storage/checkpoint/logging configuration, synth/deploy documentation.
