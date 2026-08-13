# Component Methods

상세 business rule은 각 UOW의 Functional Design에서 고정합니다. 여기서는 component boundary와 method contract만 정의합니다.

## Core

### PublicApi

| Method | Input | Output | Purpose |
|---|---|---|---|
| `search_board` | `BoardSearchRequest` | `SearchPage` | 게시판 목록/검색 결과 한 페이지 또는 한 구간 조회 |
| `search_integrated` | `IntegratedSearchRequest` | `IntegratedSearchPage` | 통합 검색 결과 한 페이지 조회 |
| `fetch_post` | `PostRequest` | `PostResult` | 게시글 상세 1건 수집 |
| `fetch_comments` | `CommentRequest` | `list[Comment]` | 댓글/답글만 수집 |
| `run_job` | `JobConfig` | `JobReport` | Job 전체 실행 |
| `resume_job` | `ResumeRequest` | `JobReport` | checkpoint에서 Job 재개 |
| `retry_parser_failures` | `RetryRequest` | `RetryReport` | parser-stage 실패 게시글만 재처리 |

### JobConfigValidator

| Method | Input | Output | Purpose |
|---|---|---|---|
| `validate_job_config` | `Mapping[str, Any]` | `JobConfig` | 모든 adapter 입력을 공통 Job 설정으로 변환 |
| `validate_scrape_options` | `Mapping[str, Any]` | `ScrapeOptions` | 댓글, media, request delay, worker 옵션 검증 |
| `validate_realtime_options` | `Mapping[str, str]` | `RealtimeOptions` | realtime env 조합 검증 |
| `validate_storage_config` | `Mapping[str, str]` | `StorageConfig` | local, PostgreSQL, S3-compatible 설정 검증 |
| `validate_resume_request` | `job_id: str | None` | `ResumeRequest` | 재개 요청 검증 |

## Models

### Pydantic Result Models

| Model | Key Fields | Purpose |
|---|---|---|
| `PostResult` | `site_id`, `board_id`, `document_srl`, `title`, `author`, `content`, `attachments`, `media`, `comments` | JSONL 한 줄 |
| `ContentBlock` | `order`, `type`, `text`, `url`, `provider`, `metadata` | 본문 텍스트/미디어 순서 보존 |
| `Comment` | `comment_srl`, `source_dom_id`, `parent_comment_srl`, `depth`, `source_order`, `is_best`, `badges`, `reactions` | 댓글/답글/BEST 댓글 구조 |
| `ReactionInfo` | `up_count`, `down_count`, `score` | 게시글 또는 댓글 반응 수 |
| `Checkpoint` | `job_id`, `status`, `reason`, `collector_cursor`, `completed_keys`, `queued_links`, `updated_at` | 중단점 저장/재개 |
| `FailureRecord` | `stage`, `reason`, `retryable`, `url`, `post_key`, `safe_message` | 실패 기록과 retry 입력 |

## HTTP

### HttpClient

| Method | Input | Output | Purpose |
|---|---|---|---|
| `get` | `url: str, headers: Mapping[str, str] | None` | `HttpResponse` | GET 요청 |
| `post` | `url: str, data: Mapping[str, Any] | None, headers: Mapping[str, str] | None` | `HttpResponse` | POST 요청 |
| `download` | `url: str` | `bytes` | media 다운로드 |
| `classify_response` | `HttpResponse` | `ResponseKind` | 정상/CAPTCHA/차단/오류 분류 |
| `close` | None | `None` | async client 종료 |

### UserAgentProvider

| Method | Input | Output | Purpose |
|---|---|---|---|
| `load` | `path: Path` | `UserAgentProvider` | `user-agents.txt` 로드 |
| `next_user_agent` | None | `str` | 요청 카운터 기반 User-Agent 선택 |

### ProxyProvider

| Method | Input | Output | Purpose |
|---|---|---|---|
| `load_from_options_or_env` | `options: ProxyOptions, env: Mapping[str, str]` | `ProxyConfig | None` | proxy 우선순위 적용 |
| `to_httpx_config` | `ProxyConfig` | `dict[str, Any]` | httpx proxy 설정 변환 |

## Search

### FmkoreaUrlBuilder

| Method | Input | Output | Purpose |
|---|---|---|---|
| `build_post_url` | `board_id: str | None, document_srl: int` | `str` | 상세 URL 생성 |
| `parse_post_url` | `url: str` | `PostIdentity` | 단축/표준 URL에서 식별자 추출 |
| `build_board_url` | `BoardListRequest` | `str` | 게시판 목록 URL 생성 |
| `build_board_search_url` | `BoardSearchRequest` | `str` | 게시판 내 검색 URL 생성 |
| `build_integrated_search_url` | `IntegratedSearchRequest` | `str` | 통합 검색 URL 생성 |

### BoardSearchParser

| Method | Input | Output | Purpose |
|---|---|---|---|
| `parse` | `html: str, base_url: str` | `SearchPage` | 목록/검색 HTML 파싱 |
| `parse_rows` | `soup: BeautifulSoup` | `list[PostCandidate]` | 게시글 후보 행 추출 |
| `parse_paging` | `soup: BeautifulSoup` | `PagingInfo` | 다음 페이지/종료 상태 추출 |
| `parse_category_hint` | `row: Tag` | `CategoryInfo | None` | 후보 말머리 추출 |

### IntegratedSearchParser

| Method | Input | Output | Purpose |
|---|---|---|---|
| `parse` | `html: str, base_url: str` | `IntegratedSearchPage` | 통합 검색 page 파싱 |
| `parse_results` | `soup: BeautifulSoup` | `list[PostCandidate]` | 결과 게시글 후보 추출 |
| `extract_board_candidates` | `candidates: list[PostCandidate]` | `list[BoardCandidate]` | 심층검색용 게시판 후보 생성 |
| `is_no_result` | `soup: BeautifulSoup` | `bool` | 검색 결과 없음 판단 |

### LinkCollector

| Method | Input | Output | Purpose |
|---|---|---|---|
| `collect` | `JobConfig, Queue[PostCandidate]` | `CollectorSummary` | Job mode별 링크 수집 |
| `collect_direct_posts` | `DirectPostConfig, Queue` | `CollectorSummary` | 직접 URL 후보 enqueue |
| `collect_board_search` | `BoardSearchConfig, Queue` | `CollectorSummary` | 게시판 목록/검색 수집 |
| `collect_integrated_search` | `IntegratedSearchConfig, Queue` | `CollectorSummary` | 통합 검색 수집 |
| `collect_deep_search` | `DeepSearchConfig, Queue` | `CollectorSummary` | 통합 검색 후보 게시판별 재검색 |
| `collect_no_keyword_range` | `NoKeywordRangeConfig, Queue` | `CollectorSummary` | 키워드 없는 기간/글번호 범위 수집 |
| `collect_realtime` | `RealtimeConfig, Queue` | `CollectorSummary` | 실시간 keyword/all 반복 수집 |

## Post Detail

### PostMetadataParser

| Method | Input | Output | Purpose |
|---|---|---|---|
| `parse` | `html: str, url: str` | `PostMetadata` | 상세 HTML metadata 파싱 |
| `parse_author` | `soup: BeautifulSoup` | `AuthorInfo` | 작성자 닉네임/member/level 추출 |
| `parse_stats` | `soup: BeautifulSoup` | `PostStats` | 조회수/추천수/댓글 수 추출 |
| `parse_attachments` | `soup: BeautifulSoup` | `list[Attachment]` | 첨부파일 metadata 추출 |
| `classify_unavailable` | `html: str, status_code: int` | `UnavailableReason | None` | 삭제/로그인/CAPTCHA 등 분류 |

### ContentBlockParser

| Method | Input | Output | Purpose |
|---|---|---|---|
| `parse_content_blocks` | `container: Tag` | `list[ContentBlock]` | 본문 순서 보존 block 추출 |
| `extract_text` | `node: Tag` | `ContentBlock | None` | 텍스트 block 추출 |
| `extract_image` | `node: Tag` | `ContentBlock | None` | 이미지 block 추출 |
| `extract_fmk_video` | `node: Tag` | `ContentBlock | None` | FMKorea video block 추출 |
| `extract_youtube` | `node: Tag | str` | `ContentBlock | None` | YouTube block 추출 |
| `extract_x` | `node: Tag | str` | `ContentBlock | None` | X/Twitter block 추출 |
| `extract_link` | `node: Tag | str` | `ContentBlock | None` | 일반 link block 추출 |

### CommentParser

| Method | Input | Output | Purpose |
|---|---|---|---|
| `parse` | `html: str` | `list[Comment]` | 댓글 DOM 파싱 |
| `parse_comment_node` | `node: Tag, source_order: int` | `Comment` | 댓글 1개 변환 |
| `parse_reactions` | `node: Tag` | `ReactionInfo` | 추천/비추천/score 추출 |
| `detect_best` | `node: Tag` | `tuple[bool, list[str]]` | BEST 여부와 badges 추출 |
| `link_replies` | `comments: list[Comment]` | `list[Comment]` | 가능한 경우 parent mapping 보정 |

### PostDetailService

| Method | Input | Output | Purpose |
|---|---|---|---|
| `fetch_post` | `PostRequest` | `PostResult` | 게시글 상세 1건 수집 |
| `fetch_comments` | `CommentRequest` | `list[Comment]` | 댓글/답글 수집 |
| `fetch_media` | `PostResult` | `PostResult` | media 옵션에 따른 저장 상태 반영 |

## Storage

### OutputStorePort

| Method | Input | Output | Purpose |
|---|---|---|---|
| `append_post` | `PostResult` | `StoredObjectRef` | posts JSONL에 게시글 한 줄 저장 |
| `write_report` | `JobReport` | `StoredObjectRef` | Job report 저장 |
| `finalize` | None | `None` | local flush 또는 remote upload 완료 |

### MediaStorePort

| Method | Input | Output | Purpose |
|---|---|---|---|
| `save_media` | `MediaItem, bytes` | `MediaSaveResult` | media 파일 저장 |
| `save_metadata_only` | `MediaItem` | `MediaSaveResult` | URL/meta만 기록 |

### FailureStorePort

| Method | Input | Output | Purpose |
|---|---|---|---|
| `write_failure` | `FailureRecord` | `StoredObjectRef` | 실패 기록 저장 |
| `read_failures` | `FailureInput` | `AsyncIterator[FailureRecord]` | retry 입력 failure 읽기 |

### CheckpointStorePort

| Method | Input | Output | Purpose |
|---|---|---|---|
| `save` | `Checkpoint` | `None` | 원자적 checkpoint 저장 |
| `load` | `job_id: str` | `Checkpoint` | 특정 checkpoint 로드 |
| `load_latest` | None | `Checkpoint | None` | 최신 checkpoint 로드 |

## Jobs And Retry

### JobRunner

| Method | Input | Output | Purpose |
|---|---|---|---|
| `run` | `JobConfig` | `JobReport` | Job 신규 실행 |
| `resume` | `ResumeRequest` | `JobReport` | checkpoint 기반 재개 |
| `stop` | `StopReason` | `Checkpoint` | 최종 checkpoint 저장 후 중단 |
| `record_success` | `PostResult` | `None` | 결과 저장 후 completed key/checkpoint 갱신 |
| `record_failure` | `FailureRecord` | `None` | 실패 기록 |

### PostWorkerPool

| Method | Input | Output | Purpose |
|---|---|---|---|
| `run` | `Queue[PostCandidate], worker_count: int` | `WorkerSummary` | 게시글 worker 병렬 실행 |
| `fetch_one` | `PostCandidate` | `PostResult` | 게시글 상세 1건 수집 |
| `handle_failure` | `PostCandidate, Exception` | `FailureRecord` | 실패 분류와 기록 생성 |

### ParserFailureRetryService

| Method | Input | Output | Purpose |
|---|---|---|---|
| `select_failures` | `RetryRequest` | `RetrySelection` | parser-stage 실패만 선택 |
| `build_retry_job` | `RetrySelection` | `JobConfig` | direct-post retry Job 생성 |
| `run` | `RetryRequest` | `RetryReport` | retry 실행과 report 생성 |

## Adapters

| Adapter | Method/Tool | Input | Output |
|---|---|---|---|
| `CliAdapter` | `main` | `argv: list[str]` | `int` |
| `CliAdapter` | `run_wizard` | None | `JobConfig` |
| `ContainerAdapter` | `main` | `env: Mapping[str, str]` | `int` |
| `ContainerAdapter` | `load_execution_config` | `env: Mapping[str, str]` | `JobConfig | ResumeRequest` |
| `McpAdapter` | `search_board` | `BoardSearchRequest` | `SearchPage` |
| `McpAdapter` | `search_integrated` | `IntegratedSearchRequest` | `IntegratedSearchPage` |
| `McpAdapter` | `fetch_post` | `PostRequest` | `PostResult` |
| `McpAdapter` | `fetch_comments` | `CommentRequest` | `list[Comment]` |
| `McpAdapter` | `run_job` | `JobConfig` | `JobReport` |
| `McpAdapter` | `resume_job` | `ResumeRequest` | `JobReport` |
| `McpAdapter` | `retry_parser_failures` | `RetryRequest` | `RetryReport` |
