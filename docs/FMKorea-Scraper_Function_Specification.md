# FMKorea Scraper Function Specification

에펨코리아 게시판 게시글 및 댓글 스크래퍼 상세 가이드

이 문서는 2026-09-04 현재 `Scrapling-Refactoring` 브랜치에 구현된 `FMkorea-Scraper`의 기능 기준 문서다. 향후 개발자가 이 문서만 보고 현재 프로젝트와 같은 기능, 실행 형태, 데이터 계약을 재구현할 수 있도록 실제 구현 상태를 함께 기록한다.

## 1. 프로젝트 개요
- **목표**
  - 에펨코리아 게시판/검색/게시글/댓글을 수집해 게시글 단위 JSONL로 저장
  - 게시판 검색, 통합 검색, 심층검색, 실시간 수집, 실패 재처리 기능 제공
  - 향후 통합 커뮤니티 스크래핑 시스템에서 개별 커뮤니티 워커로 재사용
- **기술 스택**: `scrapling`, `httpx`, `playwright`(선택적 fallback), `user-agents`, `json`, `polars`
  - **스크래핑**: Scrapling `Selector` + httpx 기반 비동기 요청, 목록/검색/상세 필수 DOM 누락 시 일반 Playwright 렌더링 fallback
  - **데이터 저장**: 로컬 JSONL/미디어 파일, 컨테이너 환경의 S3 호환 객체 저장소, PostgreSQL 체크포인트
  - **운영 보조**: `.env` Proxy, `user-agents.txt`, 요청 속도 제어, parser-stage 실패 재처리

### 1.1. 사용 형태
- 단독 실행형 스크래퍼
  - CLI 또는 설정 파일 기반으로 에펨코리아 게시글/댓글 수집
  - UI는 우선 터미널 기반으로 구성하고, GUI/Web UI는 향후 개선 사항으로 분리
  - 명령형 실행과 선택형 터미널 마법사를 같은 CLI 진입점에서 제공 가능
- Python 라이브러리
  - 다른 Python 코드에서 게시판 검색, 통합 검색, 게시글 수집, 댓글 수집 함수를 import하여 사용
  - CLI/Docker/MCP는 같은 core service를 호출하고, 입출력 어댑터만 분리
- 워커 컨테이너
  - 향후 통합 커뮤니티 스크래핑 시스템에서 에펨코리아 전용 수집 워커로 실행
  - 외부 오케스트레이터가 RabbitMQ 같은 Job Queue를 소비한 뒤 `JobConfig`를 환경 변수 또는 실행 인자로 전달해 one-shot worker 컨테이너 실행
  - JSONL/미디어는 S3 호환 저장소에 저장하고 체크포인트는 PostgreSQL에 저장
- MCP 도구
  - 외부 에이전트/자동화 시스템이 에펨코리아 검색, 게시글 수집, 댓글 수집 기능을 호출할 수 있도록 제공
  - MCP 구현은 별도 wrapper로 두고, 스크래퍼 core 로직을 중복 구현하지 않음

### 1.2. 현재 구현 완료 상태
- AI-DLC 진행 상태
  - UOW-001부터 UOW-010까지 구현 및 Build/Test 승인 완료
  - UOW-011 `Scrapling Runtime Refactor` 구현 및 Build/Test 승인 완료
  - UOW-011에서 BeautifulSoup 기반 파싱을 Scrapling `Selector` 기반으로 전환하고, HTTP-first 요청 뒤 필수 DOM 누락 시에만 일반 Playwright 렌더링 fallback을 수행하도록 정리함
  - UOW-012 `Scrapling Spider PoC/planning`은 Functional Design Questions 단계로 시작됨
  - UOW-012 질문지 파일은 `aidlc-docs/construction/plans/uow-012-scrapling-spider-poc-functional-design-plan.md`
  - 현재 확인된 답변은 Q2=`B`이며, 나머지 질문은 확정 전 상태
  - UOW-012는 production Spider 리팩토링이 아니라 도입 가치와 migration 조건을 검토하는 planning 단위
- 최근 검증 기준
  - `py -3.12 -m pytest tests -q --tb=short`: `168 passed, 3 skipped, 31 warnings`
  - Python compile 검증 통과
  - wheel build 통과: `dist/fmkorea_scraper-0.1.0-py3-none-any.whl`
  - 깨끗한 임시 venv에서 wheel 설치 후 `pip check` 통과
- 현재 구현된 핵심 기능
  - Pydantic 기반 `JobConfig`, 게시글/댓글/본문/미디어/체크포인트/실패/리포트 모델
  - `httpx.AsyncClient` 기반 HTTP 런타임, 요청 간격, retry/backoff, timeout, User-Agent rotation, Proxy, in-memory cookie lifecycle
  - Scrapling `Selector` 기반 목록/검색/상세/본문/댓글 파싱
  - 정상 HTTP 응답에 필수 DOM이 없을 때만 Scrapling `DynamicFetcher`의 일반 Playwright 렌더링 fallback
  - browser fallback은 `HttpClient` 인스턴스 내부 `asyncio.Lock`으로 직렬화
  - 목록/검색 링크 수집기 1개 + 게시글 워커 N개 + 미디어 다운로드 동시성 제한 구조
  - 로컬 JSONL/미디어 저장, S3 호환 저장소 저장, PostgreSQL 체크포인트 저장
  - CLI, 터미널 마법사, Docker one-shot worker, MCP tool handler, Python import API
  - parser-stage 실패 게시글만 골라 direct-post 경로로 재처리하는 기능
  - AWS CDK 기반 VPC, S3, RDS PostgreSQL, ECS Fargate worker, CloudWatch/EventBridge 인프라 코드
- 현재 구현하지 않는 기능
  - CAPTCHA 자동 우회, stealth/anti-detect 모드
  - 사용자 cookie 파일 입력/저장/재사용
  - 스크래퍼 내부 RabbitMQ/SQS consumer
  - 장기 실행 실시간 polling loop
  - production Scrapling Spider 실행 엔진
  - fallback 전용 저장소, dashboard, custom metric
- 구현 기준 패키지 구조
  - application code는 `src/fmkorea_scraper/` 아래에 둔다.
  - public API는 `src/fmkorea_scraper/core/api.py`가 제공한다.
  - CLI는 `src/fmkorea_scraper/adapters/cli.py`, Docker entrypoint는 `src/fmkorea_scraper/adapters/container.py`, MCP는 `src/fmkorea_scraper/adapters/mcp.py`가 담당한다.
  - 파서는 `collect/`와 `parse/`, 실행 orchestration은 `runner/`, 저장소는 `outputs/`, 실패 재처리는 `retry/`가 담당한다.

## 2. 주요 기능

### 2.1. 수집 범위

#### 2.1.1. 수집 내용
- 게시판
  - `board_id`: URL의 `mid`
  - `board_name`: 페이지/목록에서 확인 가능한 게시판명
- 글 번호
  - `document_srl`
- 말머리
  - `category.category_id`: URL 또는 말머리 링크의 `category`
  - `category.name`: 목록/상세 페이지에 표시되는 말머리명
  - `category.url`: 말머리 링크 URL을 알 수 있으면 저장
- 제목
- 글쓴이
  - 닉네임
  - 회원 번호: 작성자 링크/클래스의 `member_<member_srl>`에서 파싱 가능한 경우 저장
  - 레벨: 작성자 아이콘 `img.level[alt]`, `img.level[title]`에서 파싱 가능한 경우 저장
- 조회수
- 추천/비추천
  - 저장 필드는 공통 `ReactionInfo`인 `reactions.up_count`, `reactions.down_count`, `reactions.score`를 사용한다.
  - 상세 페이지 상단의 `추천 수` 또는 UI의 포텐 계열 값은 `up_count`로 저장한다.
  - 비추천/방출 계열 값이 페이지에 없거나 빈 값이면 `down_count=0`으로 저장한다.
  - `score`는 항상 `up_count - down_count`다.
- 댓글 수
- 작성일
- 원본 URL
  - 입력 URL과 `.document_address a.a` 또는 canonical URL을 함께 정규화
- 본문 콘텐츠
  - `content.text`: 검색/미리보기/Polars 분석용 순수 텍스트
  - `content.blocks`: 원문 순서를 보존한 텍스트, 이미지, 펨코 자체 동영상, YouTube, X, 일반 링크
- 첨부파일
  - `.rd_file a[data-href]`의 파일명, `file_srl`, 다운로드 URL, 크기/다운로드 수 텍스트
- 댓글 + 덧글
  - `comment_srl`, `comment_id_raw`
  - `parent_comment_srl`, `parent_comment_id_raw`
  - `depth`
  - `source_dom_id`
  - `source_order`
  - `is_best`
  - `badges`
  - `author`, `created_at`, `created_at_raw`, `content`, `reactions`, `permalink`

#### 2.1.2. 수집 방식
- 목록/검색 단계
  - 게시글 후보 링크와 후보 메타데이터만 수집한다.
  - 최종 저장용 제목, 말머리, 글쓴이, 작성일, 조회수, 추천수, 댓글 수, 본문, 댓글은 게시글 상세 페이지에서 다시 파싱한다.
  - 목록 단계의 제목/말머리/작성일/조회수/추천수는 필터링, 중복 제거, 진단 로그용 `PostCandidate.metadata`로만 사용한다.
- 상세 페이지 단계
  - `document_srl` 상세 URL을 열어 최종 게시글 JSON을 생성한다.
  - 본문과 미디어는 `#bd_capture .rd_body article > .xe_content` 또는 `.rd_body .xe_content`를 기준 컨테이너로 파싱한다.
- 멀티 워커 구조
  - 단일 링크 수집 워커가 목록/검색 페이지를 순회하며 수집 범위 내 게시글 후보 링크를 큐에 넣는다.
  - 다수의 게시글 워커가 큐에서 링크 단위로 작업을 가져와 상세 페이지를 병렬 비동기로 수집한다.
  - 큐 단위는 Job이 아니라 게시글 링크 1개다.
  - 저장 성공 후 체크포인트를 갱신한다.
- 현재 구현 흐름
  - `CollectorService.collect(source)`가 source별 URL을 만들고 `PostCandidate`를 yield한다.
  - `JobRunner`가 내부 `asyncio.Queue[PostCandidate]`에 후보를 넣는다.
  - `PostWorkerPool`이 `post_worker_count`만큼 실행되어 후보 1개씩 상세 페이지를 처리한다.
  - `CompletedKeyTracker`가 `(site_id, board_id, document_id_raw)` 기준으로 이미 완료된 게시글과 진행 중 게시글을 중복 처리하지 않는다.
  - `MediaDownloadCoordinator`는 `media_mode=url_only`이면 메타데이터만 저장하고, `media_mode=download`이면 `media_worker_count` 세마포어로 다운로드 동시성을 제한한다.
  - 각 게시글은 `PostDetailService`가 상세 HTML을 열고 `MetadataParser`, `ContentParser`, `CommentParser` 결과를 합쳐 `PostResult`로 만든다.
  - 저장은 `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, `CheckpointStorePort`를 통해서만 수행한다.

#### 2.1.3. 수집 옵션
- 게시글 수집 옵션
  - 특정 게시글 수집
    - `document_srl` 단독 입력
    - `board_id` + `document_srl` 입력
  - 게시판 전체 수집
  - 게시판 말머리 수집
    - `category=<category_id>`를 사용
    - 없는 말머리이거나 해당 게시판에서 유효하지 않으면 실패 처리
  - 특정 기간 수집
    - 링크 수집 중 후보 작성일을 확인해 지정 기간 밖으로 벗어나면 수집 종료
    - 현재 구현 기준 필터링은 목록/검색 단계에서 파싱한 후보 작성일과 후보 `document_srl`을 기준으로 수행한다.
    - 상세 페이지의 최종 작성일은 JSON 저장값으로 다시 파싱하지만, 상세 파싱 후 기간 범위를 재검증해 제외하는 후처리 필터는 아직 적용하지 않는다.
  - 특정 글번호 범위 수집
    - `document_srl` 범위로 필터링
  - 노키워드 기간/글번호 범위 수집
    - 검색 키워드 없이 게시판 목록을 페이지 단위로 순회하며 기간/글번호 조건으로 필터링
  - 실시간 키워드 수집
    - 환경변수로 활성화
    - `RealtimeKeywordSource`, `RealtimeTermination` 모델과 환경변수 조립 계약은 존재한다.
    - 현재 구현의 `JobRunner`는 전달받은 collector를 1회 실행하는 one-shot 구조이므로, 지정 키워드의 최신 검색 결과를 장기 반복 확인하는 polling loop는 아직 production 구현이 아니다.
  - 실시간 전체 수집
    - 환경변수로 활성화
    - `RealtimeAllSource`, `RealtimeTermination` 모델과 환경변수 조립 계약은 존재한다.
    - 현재 구현의 `JobRunner`는 지정 게시판 최신 목록을 장기 반복 확인하지 않고 collector 1회 실행 후 종료하는 구조다.
  - 심층검색
    - 통합 검색으로 키워드가 발견되는 게시판 목록을 먼저 만들고, 각 게시판에서 게시판 내 키워드 검색을 수행
    - 통합 검색 페이지 제한을 보완하기 위한 수집 모드
    - 글번호 범위 또는 기간 범위 중 하나 이상을 반드시 입력
  - 파싱 실패 게시글 재처리
    - 전체 Job을 다시 실행하지 않고 기존 `failures.jsonl`의 parser-stage 실패 게시글만 재수집
- 댓글 수집 옵션
  - 댓글 미수집
  - 전체 댓글 수집
  - BEST 댓글만 수집
- 파서 제한 옵션
  - `max_comment_pages`: 추가 댓글 페이지 요청 상한. 값이 없으면 상세 HTML에 포함된 댓글만 파싱한다.
  - `max_comments`: 댓글 저장 개수 상한. 값이 없으면 발견된 정상 댓글을 모두 저장한다.
  - `max_content_blocks`: 본문 content block 저장 개수 상한. 값이 없으면 발견된 정상 block을 모두 저장한다.
  - 위 제한값은 `JobConfig.scrape_options`에 저장해 체크포인트 재개와 parser-stage 실패 재처리에서 동일하게 재현한다.
- 본문 미디어 수집 옵션
  - 이미지/동영상 URL 및 메타데이터만 저장
  - 이미지/동영상 파일 저장
  - 이미지/동영상 URL 및 파일 모두 저장
  - YouTube, X 등 외부 임베드는 다운로드하지 않고 URL, provider, id, embed_url만 저장
- 실시간 종료 조건
  - 아래 값은 현재 모델/CLI/Docker 환경변수 조립 계약이다.
  - 실제 장기 실행 polling loop와 종료 조건 도달 시점까지의 반복 실행 제어는 향후 구현 대상이다.
  - 환경변수
    - `FMKOREA_REALTIME_ENABLED=true`
    - `FMKOREA_REALTIME_MODE=keyword|all`
    - `FMKOREA_REALTIME_KEYWORD=<검색어>` (`keyword` 모드에서 필수)
    - `FMKOREA_REALTIME_DURATION_SECONDS=<실행_초>`
    - `FMKOREA_REALTIME_END_AT=<UTC_ISO-8601_종료시각>`
    - `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS=<반복_주기_초>` (없으면 30초 기본값 사용)
  - 타이머 `실행_초`와 종료 시각 중 하나만 입력받는다.
  - `FMKOREA_REALTIME_DURATION_SECONDS`와 `FMKOREA_REALTIME_END_AT` 중 정확히 하나만 입력한다.
  - 둘 다 없거나 둘 다 있으면 실시간 Job 시작 실패로 처리한다.
  - 종료 조건 도달 시 `status="completed"`로 최종 체크포인트 저장 후 종료한다.
  - 수동 중단, 오류, CAPTCHA 감지 시 기존 중단 처리와 동일하게 `status="stopped"` 저장 후 종료한다.

#### 2.1.4. 수집 주기
- 수집 주기는 사용자가 설정 가능하다.
- 현재 구현된 수집 주기 제어는 HTTP 요청 사이의 `request_interval_seconds`, retry/backoff, worker 동시성 제한이다.
- 실시간 모드가 지정 interval마다 최신 목록/검색 결과를 계속 확인하는 동작은 설계 계약으로 남겨두며, 현재 production runner는 one-shot Job을 실행한다.
- 새 게시글만 상세 수집하도록 `(site_id, board_id, document_srl)` 기준 중복을 제거한다.

### 2.2. 사이트 API

#### 2.2.1. 게시글 상세 페이지
- 표준 URL
  - `https://www.fmkorea.com/index.php?mid=<board_id>&document_srl=<document_srl>`
- 단축 URL
  - `https://www.fmkorea.com/<document_srl>`
  - `https://www.fmkorea.com/best/<document_srl>`
- 상세 페이지 요청 후 canonical URL, `.document_address a.a`, 현재 URL을 비교해 `canonical_url`을 정규화한다.
- `board_id`가 URL에 없는 단축 URL은 페이지 내부 링크, canonical, 목록 후보 메타데이터 중 가능한 값을 사용한다.

#### 2.2.2. 게시판 목록 API
- 기본 URL
  - `https://www.fmkorea.com/<board_id>?page=<page>`
  - 또는 `https://www.fmkorea.com/index.php?mid=<board_id>&page=<page>`
- 말머리 필터
  - `category=<category_id>`
- 목록 행 파싱
  - 목록 테이블은 게시판 스킨별 id가 바뀌므로 고정 id보다 `div.bd table tbody tr` 범위에서 탐색한다.
  - 공지/광고 행은 `notice`, `ad_wrapper`, `naver_power_link_search_tr` 계열 클래스를 수집 제외한다.
  - 게시글 링크는 `a.hx[href]`, `td.title a[href]`에서 추출한다.
  - 링크는 최종적으로 `document_srl`이 있는 URL 또는 `/<document_srl>` 형태만 후보로 채택한다.
- 목록 단계 수집값
  - `document_srl`
  - 후보 URL
  - 후보 말머리
  - 후보 제목
  - 후보 댓글 수
  - 후보 작성일
  - 후보 조회수/추천수
  - 위 값은 필터링과 진단용이며 최종 저장값은 상세 페이지에서 다시 파싱한다.

#### 2.2.3. 게시판 내 검색 API
- 대상: 특정 게시판 내 검색
- 기본 링크: `https://www.fmkorea.com/search.php`
- 요청 파라미터
  - 게시판 ID: `mid=<board_id>`
  - 검색옵션: `search_target=<search_target>`
    - 제목 + 내용: `title_content`
    - 요약보기 검색: `title_content_summary`
    - 제목: `title`
    - 내용: `content`
    - 글쓴이: `nick_name`
    - 댓글: `comment`
  - 키워드: `search_keyword=<keyword>`
  - 페이지 번호: `page=<page>`
  - 말머리 필터: `category=<category_id>`
- 수집 순서
  - `page=1`부터 마지막 페이지까지 순차 수집한다.
  - 다음 페이지가 없거나 검색 결과 없음 표시가 나오면 종료한다.
- 게시글 후보 행 파싱
  - `div.bd table tbody tr` 하위에서 후보 행을 찾는다.
  - 공지/광고 행은 제외한다.
  - `a.hx[href]`, `td.title a[href]`의 링크에서 `document_srl`을 추출한다.
  - 검색 단계에서는 후보 링크만 큐에 넣고, 최종 저장용 게시글 필드는 상세 페이지에서 다시 수집한다.

#### 2.2.4. 통합 검색 API
- 대상: 전체 게시판 검색
- 기본 링크: `https://www.fmkorea.com/search.php?act=IS`
- 요청 파라미터
  - 검색 키워드: `is_keyword=<keyword>`
  - 검색 대상: `where=<where>`
    - 문서: `document`
    - 댓글: `comment`
  - 문서 검색옵션: `search_target=<search_target>`
    - 제목 + 내용: `title_content`
    - 제목: `title`
    - 내용: `content`
  - 페이지 번호: `page=<page>`
  - 정렬 옵션: `sph_sort=<sort>`
    - 날짜순: `date`
    - 정확도순: `relevance`
    - 현재 `IntegratedSearchUrlBuilder` 내부 확장 인자로만 존재하며, `IntegratedSearchSource`, CLI `run --source integrated-search`, Python public request 모델의 공식 입력 옵션으로는 노출하지 않는다.
    - 따라서 현 구현 재현 시 `sph_sort`는 내부 확장 여지 또는 향후 옵션으로 취급하고, 기본 public 계약에는 포함하지 않는다.
- 페이지 번호
  - 시작값: 1
  - 최대값: 1000
  - 다음 페이지가 검색 결과 없음 상태이거나 `noResult` 표시가 나오면 마지막 페이지로 판단한다.
- 통합 검색 결과도 후보 링크 수집 단계로만 취급한다.

### 2.3. 게시글 상세 페이지 파싱

#### 2.3.1. 메타데이터 파싱
- 기준 컨테이너: `#bd_capture`
- 작성일
  - `.rd_hd .date`
  - 예: `2026.08.10 21:40`
- 제목
  - `.rd_hd h1 .np_18px_span`
  - fallback: `.rd_hd h1`
- 작성자
  - `.rd_hd .member_plate`
  - 클래스의 `member_<member_srl>`에서 회원 번호를 추출한다.
  - `img.level[alt]`에서 `[레벨:24]` 형식의 레벨을 추출한다.
- 조회수/추천수/댓글 수
  - `.rd_hd .btm_area .side.fr span` 텍스트를 라벨 기준으로 파싱한다.
  - `조회 수 <b>...</b>`, `추천 수 <b>...</b>`, `댓글 <b>...</b>`
- 말머리
  - 상세 페이지 주변의 `a.category[href*="category="]`를 우선 사용한다.
  - 후보 목록에서 전달받은 category 힌트가 있으면 fallback으로 사용한다.
- 첨부파일
  - `.rd_file a[data-href]`
  - `data-href`에서 `file_srl`, `sid`, `mid`를 파싱한다.
  - `title`에서 파일 크기/다운로드 수를 가능한 범위에서 파싱한다.

#### 2.3.2. 본문 콘텐츠 및 미디어 수집
- 조사 기준
  - 이미지/텍스트 예시: `https://www.fmkorea.com/best/10195585295`
  - 펨코 자체 영상 예시: `https://www.fmkorea.com/search.php?mid=football_world&document_srl=10196696065`
  - X 예시: `https://www.fmkorea.com/index.php?mid=best&document_srl=8984251370`
  - YouTube 예시: `https://www.fmkorea.com/search.php?mid=lol&document_srl=10192764813`
- 기준 컨테이너
  - 1순위: `#bd_capture .rd_body article > .xe_content`
  - 2순위: `#bd_capture .rd_body .xe_content`
  - 전역 `.xe_content`는 광고/목록 영역에도 다수 존재할 수 있으므로 단독 기준으로 사용하지 않는다.
- 파싱 원칙
  - Scrapling `Selector`로 기준 컨테이너의 하위 노드를 DOM 순서대로 순회하여 `content.blocks` 배열에 저장한다.
  - 빈 `<p>`, 빈 `<div>`, `<br>`만 있는 노드는 저장하지 않는다.
  - `<!-- __LAZY__ -->`, `BeforeDocument`, `AfterDocument`, 플레이어 UI 텍스트, 첨부파일 표 텍스트는 본문 텍스트로 저장하지 않는다.
  - 각 블록은 공통으로 `order`, `type` 값을 가진다.
  - URL은 프로토콜 생략형 `//...`을 `https://...`로 정규화한다.
- `type="text"`
  - 일반 텍스트 문단 또는 텍스트만 있는 `p`, `div`, `span`
  - `text`에 공백 정규화된 문자열 저장
  - 이미지/동영상/외부 임베드 내부의 플레이어 대체 문구는 제외
- `type="image"`
  - 이미지 후보: 기준 컨테이너 내부 `img[src]`
  - 제외: 펨코 자체 영상 플레이어의 포스터 이미지 `.mejs__poster-img`, `video` 내부 UI 이미지
  - URL 우선순위: 부모 `a.highslide[href]` -> `src`
  - 저장 필드
    - `url`: 정규화된 이미지 URL
    - `original_url`: 부모 `a.highslide[href]`가 있을 경우 원본 이미지 URL
    - `file_srl`: `data-file-srl`
    - `alt`
    - `width`, `height`
    - `download_url`: `.rd_file a[data-href]`에서 같은 `file_srl`로 매칭되는 경우 저장
    - `download`, `file_path`, `object_key`: 모델 필드는 존재하지만 현재 다운로드 결과는 `media[]` 항목에만 반영한다.
- `type="fmk_video"`
  - 펨코 자체 업로드 동영상 후보: `.auto_media_wrapper`, `video.mediaelement_video`, `video > source[type="video/mp4"]`
  - 정적 HTML에 `source src`, `poster`, schema.org `meta itemprop` 값이 포함되므로 기본 Scrapling 파서만으로 수집 가능하다.
  - 저장 필드
    - `video_url`: `source[src]` 또는 `meta[itemprop="contentURL"]`
    - `poster_url`: `video[poster]` 또는 `meta[itemprop="thumbnailUrl"]`
    - `file_srl`: `.auto_media_wrapper[data-file-download-url]`에서 파싱
    - `download_url`: `.auto_media_wrapper[data-file-download-url]`
    - `name`: `meta[itemprop="name"]`
    - `upload_date`: `meta[itemprop="uploadDate"]`
    - `description`: `meta[itemprop="description"]`, 없거나 빈 값이면 `null`
    - `width`, `height`
    - `download`, `file_path`, `object_key`: 모델 필드는 존재하지만 현재 다운로드 결과는 `media[]` 항목에만 반영한다.
  - 같은 `video`의 하위 `source`는 별도 블록으로 중복 저장하지 않는다.
- `type="youtube"`
  - 정적 HTML 후보
    - 본문 텍스트/링크의 `youtube.com/watch`, `youtu.be/<video_id>`
  - 렌더링 후 후보
    - `iframe[src*="youtube.com/embed"]`
  - Scrapling 기본 구현은 정적 HTML의 YouTube URL을 파싱해 `embed_url`을 직접 생성한다.
  - 저장 필드
    - `video_id`
    - `url`
    - `embed_url`
    - `title`
    - `start_seconds`: `t`, `start` 파라미터가 있으면 초 단위 저장
  - 외부 영상 파일은 다운로드하지 않는다.
- `type="x"`
  - 정적 HTML 후보
    - 본문 텍스트/링크의 `https://x.com/<user>/status/<tweet_id>`
    - `https://twitter.com/<user>/status/<tweet_id>`
  - 렌더링 후 후보
    - `iframe[src*="platform.twitter.com/embed/Tweet.html"]`
  - Scrapling 기본 구현은 정적 HTML에 남아 있는 X URL을 우선 수집한다.
  - 렌더링된 iframe을 참고할 수 있는 환경에서는 `embed_url`도 저장한다.
  - 저장 필드
    - `username`
    - `status_id`
    - `tweet_id`
    - `url`
    - `embed_url`
    - `text`
  - X 첨부 미디어 원본 파일은 다운로드하지 않는다.
- `type="link"`
  - 일반 링크: 기준 컨테이너 내부 `a[href]` 또는 본문 텍스트의 bare URL
  - 단, 이미지 highslide 링크, 펨코 동영상 다운로드 링크, YouTube, X는 별도 타입으로 저장하고 `link` 블록으로 중복 저장하지 않는다.
  - 저장 필드
    - `text`
    - `url`
    - `title`: 링크 미리보기 또는 링크 노드에서 확인 가능한 제목. 없으면 `null`
- `type="attachment"`
  - 첨부파일 목록의 파일을 본문 흐름 안에서 보존해야 할 때 사용하는 block 타입이다.
  - 현재 첨부파일의 기본 저장 위치는 top-level `attachments[]`이며, 본문 DOM 순서에 파일 링크가 명확히 등장하는 경우에만 `AttachmentBlock`으로 표현한다.
  - 저장 필드
    - `attachment`: `file_name`, `url`, `size_text`, `file_srl`, `sid`, `mid`, `download_text`, `file_path`, `object_key`를 가진 `Attachment` 객체
- `type="unknown_embed"`
  - YouTube, X, 펨코 자체 영상, 일반 링크로 분류하지 못한 외부 임베드를 보존하기 위한 fallback block 타입이다.
  - 임베드 내용을 억지로 텍스트로 병합하지 않고, 추후 파서 보강이 가능하도록 안전한 범위의 정보만 저장한다.
  - 저장 필드
    - `provider`: 식별 가능한 provider 명. 모르면 `null`
    - `url`: iframe, embed, object, 링크 등에서 추출 가능한 대표 URL. 없으면 `null`
    - `safe_text`: 스크립트, 광고, UI 문구를 제외하고 안전하게 보존 가능한 대체 텍스트. 없으면 `null`
- `content.text`
  - `content.blocks` 중 텍스트성 블록을 합쳐 저장한다.
  - 포함 대상: `text`, `link.text`, 텍스트만 있는 bare URL
  - 제외 대상: 조회수/추천수/댓글 수/첨부파일 목록/플레이어 UI/광고 텍스트
- top-level `media`
  - `content.blocks`의 `image`, `fmk_video`, `youtube`, `x` 블록만 뽑은 호환/요약 필드로 취급한다.
  - `link`, `attachment`, `unknown_embed`는 기본적으로 top-level `media[]`로 승격하지 않는다.
  - `MediaItem` 필드는 `media_id`, `media_type`, `source_block_order`, `url`, `file_path`, `object_key`, `description`, `provider`, `embed_url`, `file_srl`이다.
- 미디어 파일명
  - 로컬/S3 공통 상대 경로는 `media/<board_id>/<document_srl>/<media_type>/<order>-<filename_from_url>` 형태를 사용한다.
  - 저장소 전체 기준 로컬 경로는 `<base_output_path>/outputs/<job_id>/<run_id>/media/<board_id>/<document_srl>/<media_type>/<order>-<filename_from_url>`이다.
  - S3 object key는 `<S3_PREFIX>/<job_id>/<run_id>/media/<board_id>/<document_srl>/<media_type>/<order>-<filename_from_url>`이다.

#### 2.3.3. 댓글 수집
- 기준 컨테이너: `.fdb_lst_ul`
- 댓글 항목: `.fdb_lst_ul > li`
- 댓글 번호
  - `li[id^="comment_"]`에서 숫자 추출
  - BEST 댓글의 id는 `comment_<comment_srl>_`처럼 끝에 `_`가 붙을 수 있으므로 숫자만 파싱한다.
  - 원본 DOM id는 `source_dom_id`에 별도 저장한다.
- 원본 순서
  - 현재 댓글 페이지/DOM에서 등장한 순서를 `source_order`로 저장한다.
  - Polars 분석 시에는 배열 순서에 의존하지 않고 `created_at`, `comment_srl`, `source_order` 기준으로 명시 정렬한다.
- BEST 댓글 여부
  - `li.comment_best` 또는 내부 `.icon-hit` 텍스트 `BEST`
  - BEST 댓글도 일반 댓글과 동일하게 `comments` 배열에 저장하고 별도 `best_comments` 배열을 만들지 않는다.
  - `is_best=true`로 저장한다.
  - 원문 표시 보존을 위해 `badges=["BEST"]`로 저장한다.
- 작성자
  - `.meta .member_plate`
  - `data-comment_srl`은 댓글 번호 후보로 사용 가능
  - 클래스 `member_<member_srl>`에서 작성자 회원 번호 추출
- 작성일
  - `.meta .date`
  - 상대 시간과 절대 시간이 섞일 수 있으므로 원문 문자열과 정규화 결과를 함께 저장한다.
- 내용
  - 댓글 본문 영역은 `.xe_content`, `.comment_content`, `.comment-content` 순으로 찾는다.
  - 댓글 본문 영역의 텍스트를 저장한다.
  - 이미지콘 구매 아이콘 등 장식 텍스트는 제외한다.
  - 댓글 내부 이미지의 `alt`가 있으면 텍스트 내용 뒤에 함께 보존한다.
  - 작성자/날짜/추천/비추천/주소복사/댓글로 가기 UI 텍스트는 제외
- 추천/비추천
  - 기준 컨테이너: `li[id^="comment_"] > div.fdb_nav.img_tx span.vote`
  - 추천 수: `a[title="추천"] .voted_count`
  - 비추천 수: `a[title="비추천"] .blamed_count`
  - 값이 빈 문자열이면 `0`으로 정규화한다.
  - `reactions.up_count`, `reactions.down_count`, `reactions.score=up_count-down_count`로 저장한다.
- 덧글
  - `data-parent` 또는 `data-parent-comment-srl`이 있으면 `parent_comment_srl`로 저장한다.
  - 부모 댓글 번호가 있거나 `li` class에 `reply`가 있으면 `depth=1`로 저장한다.
  - 명확한 부모를 찾지 못한 댓글은 `depth=0`, `parent_comment_srl=null`로 저장한다.
  - 별도 원본 class 필드는 두지 않고, 필요 시 공통 `metadata` 확장 필드에 제한된 JSON 값으로 보존한다.
- 댓글 추가 페이지
  - 상세 HTML에 포함된 댓글은 항상 먼저 파싱한다.
  - `max_comment_pages`가 `null`이면 추가 댓글 페이지 요청을 하지 않는다.
  - `max_comment_pages`가 지정되면 `.fdb_nav.comment_page a[href]`, `.comment_page a[href]`, `.comment-page a[href]`에서 댓글 페이지 링크를 찾는다.
  - 링크 텍스트, class, href 중 `cpage`, `comment_page`, `commentpage` 표식이 있는 링크만 추가 댓글 페이지 후보로 사용한다.
  - 현재 게시글과 다른 `document_srl`로 이동하는 링크는 제외한다.
  - 이미 파싱한 댓글과 추가 페이지 댓글은 `comment_srl` 또는 `source_dom_id` 기준으로 중복 제거한다.

### 2.4. 데이터 저장 JSONL
- 수집된 게시글 데이터는 Job당 하나의 JSONL 파일로 저장한다.
- 게시글 하나는 JSON 객체 한 줄로 append한다.
- Job 실행 조건과 요약 정보는 별도 metadata JSON 파일로 저장 가능하다.
- 이미지/동영상 파일은 별도의 `media/` 폴더 또는 S3 호환 객체 저장소에 저장한다.
- 컨테이너 운영 시 JSONL과 미디어는 S3 호환 객체 저장소에 저장하고 체크포인트는 PostgreSQL에 저장한다.
- 기본 S3 호환 저장소는 Garage로 확장하되, SeaweedFS로 바꿀 수 있게 S3 호환 설정만 사용한다.
- 파일명
  - `job_YYYYMMDD_HHMMSS.jsonl`
  - 예: `job_20260811_120000.jsonl`
- 현재 로컬 출력 구조
  - `<base_output_path>/outputs/<job_id>/<run_id>/posts.jsonl`
  - `<base_output_path>/outputs/<job_id>/<run_id>/failures.jsonl`
  - `<base_output_path>/outputs/<job_id>/<run_id>/report.json`
  - `<base_output_path>/outputs/<job_id>/<run_id>/media/...`
  - `<base_output_path>/Checkpoint.json`
- 현재 S3 호환 출력 구조
  - `<S3_PREFIX>/<job_id>/<run_id>/posts.jsonl`
  - `<S3_PREFIX>/<job_id>/<run_id>/failures.jsonl`
  - `<S3_PREFIX>/<job_id>/<run_id>/report.json`
  - `<S3_PREFIX>/<job_id>/<run_id>/media/...`
  - `S3_PREFIX`가 없으면 `fmkorea` prefix를 기본 운영 예시로 사용한다.
- 경로 및 object key 정규화 규칙
  - `job_id`, `run_id`, `board_id`, `document_srl`, `media_type`, 파일명, `S3_PREFIX`의 각 세그먼트는 파일 시스템과 S3 key에서 안전하게 사용할 수 있도록 정규화한다.
  - 허용 문자는 영문 대소문자, 숫자, `.`, `_`, `-`이며, 그 외 문자는 `_`로 치환한다.
  - 세그먼트 앞뒤의 `.`, `_`, 공백은 제거한다.
  - 빈 문자열, `.`, `..`은 fallback 값으로 대체한다.
  - 세그먼트 길이는 기본 160자, 파일명은 220자 이내로 제한한다.
  - 로컬 저장 시 최종 경로가 `base_output_path` 밖으로 벗어나면 저장소 오류로 처리해 path traversal을 차단한다.
  - URL에서 파일명을 얻지 못하면 `media.bin`을 fallback 파일명으로 사용한다.
- S3 JSONL 저장 동작
  - `S3OutputStore`는 로컬 임시 spool 파일에 `posts.jsonl`과 `failures.jsonl`을 append한 뒤, append 시점마다 같은 object key로 다시 업로드한다.
  - S3 object append API에 의존하지 않는다.
  - `finalize()`는 spool writer를 닫고 임시 디렉토리를 정리한다.
- 미디어 다운로드 저장 동작
  - `media_mode="url_only"`이면 `media[]`의 URL/메타데이터만 남기고 파일 다운로드는 수행하지 않는다.
  - `media_mode="download"`이면 `media[]` 항목별로 `HttpPort.download()`를 호출하고, 로컬 저장은 `file_path`, S3 저장은 `object_key`를 `media[]` 항목에 반영한다.
  - 현재 구현은 저장 결과를 `content.blocks[]`에 다시 전파하지 않는다. `content.blocks[]`는 본문 DOM에서 파싱한 원본 순서/URL/메타데이터 보존용이고, 실제 저장 결과 확인은 `media[]`를 기준으로 한다.
- 현재 게시글 JSONL schema
  - `schema_version="fmkorea.post.v1"`
  - Pydantic 모델 기준 최상위 타입은 `PostResult`
  - `MetadataModel`을 상속한 모든 객체는 `metadata` 필드를 가진다.
  - JSONL writer는 `model_dump(mode="json")` 결과를 기록하므로 `null`, 빈 배열, 기본값 필드를 임의로 제외하지 않는다.
  - 아래 JSON 예시는 읽기 쉬운 대표 구조이며, 실제 구현 기준은 각 Pydantic 모델 필드 전체다.
  - 시간 필드는 `scraped_at`, `created_at`, `created_at_raw`를 사용한다.
  - 글 번호는 `document_srl` 숫자와 `document_id_raw` 문자열을 함께 저장한다.
  - 추천/비추천은 공통 `ReactionInfo` 구조인 `up_count`, `down_count`, `score`로 저장한다. UI의 포텐은 `up_count`, 방출은 `down_count`에 대응한다.
  - FMKorea 원본 JSON에는 `is_repost`, `repost` 필드를 두지 않는다. 향후 공통 정규화 단계에서 필요한 경우 `null` 또는 기본값으로 보강한다.

#### 2.4.1. JobConfig 예시
```json
{
  "job_id": "job_20260811_120000",
  "site_id": "fmkorea",
  "job_type": "board_search",
  "source": {
    "type": "board_search",
    "board_id": "football_world",
    "category_id": "233499071",
    "keyword": "검색 키워드",
    "search_target": "title_content",
    "page_start": 1,
    "page_end": 5,
    "range_filter": {
      "date_from": "2026-08-01",
      "date_to": "2026-08-11",
      "min_document_srl": 10190000000,
      "max_document_srl": 10199999999
    }
  },
  "scrape_options": {
    "comment_mode": "all",
    "media_mode": "url_only",
    "include_attachments": true,
    "request_interval_seconds": 1.0,
    "max_post_retries": 3,
    "max_comment_pages": 3,
    "max_content_blocks": null,
    "max_comments": null
  },
  "worker_config": {
    "post_worker_count": 2,
    "media_worker_count": 2,
    "queue_max_size": null
  },
  "storage_config": {
    "output_mode": "local",
    "checkpoint_mode": "local",
    "base_output_path": ".",
    "s3": null,
    "postgres": null
  },
  "created_at": "2026-08-11T12:00:00+09:00"
}
```

#### 2.4.2. JobConfig.source 모드별 예시
아래 예시는 `JobConfig.source` 필드에 들어가는 실제 discriminated union 구조다.

```json
{
  "type": "direct_post",
  "urls": [
    "https://www.fmkorea.com/best/10195585295",
    "https://www.fmkorea.com/index.php?mid=stock&document_srl=10197961451"
  ]
}
```

```json
{
  "type": "board_list",
  "board_id": "stock",
  "category_id": null,
  "page_start": 1,
  "page_end": 5,
  "range_filter": null
}
```

```json
{
  "type": "board_search",
  "board_id": "stock",
  "category_id": null,
  "keyword": "삼전",
  "search_target": "title_content",
  "page_start": 1,
  "page_end": 5,
  "range_filter": {
    "date_from": "2026-08-01",
    "date_to": "2026-08-11",
    "min_document_srl": null,
    "max_document_srl": null
  }
}
```

```json
{
  "type": "integrated_search",
  "keyword": "삼전",
  "search_target": "title_content",
  "page_start": 1,
  "page_end": 10,
  "range_filter": null
}
```

```json
{
  "type": "deep_search",
  "keyword": "삼전",
  "seed_search_target": "title_content",
  "seed_page_limit": 20,
  "board_ids": null,
  "range_filter": {
    "date_from": "2026-08-01",
    "date_to": "2026-08-11",
    "min_document_srl": null,
    "max_document_srl": null
  }
}
```

```json
{
  "type": "no_keyword_range",
  "board_id": "stock",
  "category_id": null,
  "range_filter": {
    "date_from": "2026-08-01",
    "date_to": "2026-08-11",
    "min_document_srl": null,
    "max_document_srl": null
  }
}
```

```json
{
  "type": "realtime_keyword",
  "scope": "board",
  "board_id": "stock",
  "keyword": "삼전",
  "poll_interval_seconds": 30.0,
  "termination": {
    "duration_seconds": 3600,
    "end_at": null
  }
}
```

```json
{
  "type": "realtime_all",
  "board_id": "stock",
  "category_id": null,
  "poll_interval_seconds": 30.0,
  "termination": {
    "duration_seconds": null,
    "end_at": "2026-08-11T18:00:00+09:00"
  }
}
```

```json
{
  "type": "parser_failure_retry",
  "failure_input": {
    "failure_path": ".\\outputs\\job-a\\run-1\\failures.jsonl",
    "job_id": "job-a",
    "stage_allowlist": ["post"]
  },
  "skip_existing_success": true
}
```

#### 2.4.3. 게시글 JSONL 한 줄 예시
```json
{
  "schema_version": "fmkorea.post.v1",
  "scraped_at": "2026-08-11T12:00:30+09:00",
  "site_id": "fmkorea",
  "board_id": "football_world",
  "board_name": "해외축구",
  "document_srl": 10196696065,
  "document_id_raw": "10196696065",
  "canonical_url": "https://www.fmkorea.com/10196696065",
  "category": {
    "category_id": "233499071",
    "name": "레알 마드리드",
    "url": "https://www.fmkorea.com/football_world?category=233499071"
  },
  "title": "[ESPN] 어제자 레알 선수단 훈련 영상",
  "author": {
    "nickname": "유느님좋아",
    "member_srl": "534126900",
    "level": "32",
    "profile_url": "https://www.fmkorea.com/index.php?mid=football_world&act=dispMemberInfo&member_srl=534126900"
  },
  "created_at": "2026-08-11T08:03:00+09:00",
  "created_at_raw": "2026.08.11 08:03",
  "views": 361,
  "reactions": {
    "up_count": 5,
    "down_count": 0,
    "score": 5
  },
  "comment_count": 0,
  "content": {
    "text": "이 게임 쵸비한테 바치겠습니다\n쵸비가 거절하면 제카한테 바치겠습니다 ㅇㅈㄹ ㅋㅋㅋㅋ",
    "blocks": [
      {
        "order": 0,
        "type": "fmk_video",
        "video_url": "https://mediak5jvqbd.fmkorea.com/files/attach/new5/20260811/10196696065_33854530_e095651ae51e9d1f50fa497abbf0a147.mp4",
        "poster_url": "https://image.fmkorea.com/files/attach/new5/20260811/10196696065_33854530_e095651ae51e9d1f50fa497abbf0a147.mp4.thumb.webp",
        "file_srl": "10196696177",
        "download_url": "https://www.fmkorea.com/?module=file&act=procFileDownload&file_srl=10196696177&sid=...",
        "name": "SnapInsta.to_example.mp4",
        "upload_date": "2026-08-11T08:03:22+09:00",
        "description": "[ESPN] 어제자 레알 선수단 훈련 영상",
        "width": 720,
        "height": 1280,
        "download": null,
        "file_path": null,
        "object_key": null
      },
      {
        "order": 1,
        "type": "youtube",
        "video_id": "IKyeLpRZaZE",
        "url": "https://youtu.be/IKyeLpRZaZE?t=456",
        "embed_url": "https://www.youtube.com/embed/IKyeLpRZaZE",
        "title": null,
        "start_seconds": 456
      },
      {
        "order": 2,
        "type": "x",
        "username": "elonmusk",
        "status_id": "1973529989002989733",
        "tweet_id": "1973529989002989733",
        "url": "https://x.com/elonmusk/status/1973529989002989733",
        "embed_url": "https://platform.twitter.com/embed/Tweet.html?id=1973529989002989733",
        "text": null
      },
      {
        "order": 3,
        "type": "image",
        "url": "https://image.fmkorea.com/files/attach/new5/20260810/example.jpg",
        "file_srl": "10195587886",
        "alt": "example.jpg",
        "width": 1280,
        "height": 960,
        "download_url": "https://www.fmkorea.com/?module=file&act=procFileDownload&file_srl=10195587886&sid=...",
        "download": null,
        "file_path": null,
        "object_key": null
      },
      {
        "order": 4,
        "type": "text",
        "text": "일반 텍스트 본문"
      },
      {
        "order": 5,
        "type": "link",
        "text": "https://m.fmkorea.com/8978626151",
        "url": "https://m.fmkorea.com/8978626151"
      }
    ]
  },
  "attachments": [
    {
      "file_name": "example.jpg",
      "url": "https://www.fmkorea.com/?module=file&act=procFileDownload&file_srl=10195587886&sid=...",
      "file_srl": "10195587886",
      "sid": "...",
      "mid": "football_world",
      "size_text": "186.5KB",
      "download_text": "다운로드 1"
    }
  ],
  "media": [
    {
      "media_id": "10196696177",
      "media_type": "fmk_video",
      "source_block_order": 0,
      "url": "https://mediak5jvqbd.fmkorea.com/files/attach/new5/20260811/example.mp4",
      "file_path": null,
      "object_key": null,
      "description": "[ESPN] 어제자 레알 선수단 훈련 영상",
      "provider": null,
      "embed_url": null,
      "file_srl": "10196696177"
    },
    {
      "media_id": "10195587886",
      "media_type": "image",
      "source_block_order": 3,
      "url": "https://image.fmkorea.com/files/attach/new5/20260810/example.jpg",
      "file_path": "media/fmkorea/football_world/10196696065/3_image.jpg",
      "object_key": null,
      "description": null,
      "provider": null,
      "embed_url": null,
      "file_srl": "10195587886"
    }
  ],
  "comments": [
    {
      "comment_srl": 10197230200,
      "comment_id_raw": "10197230200",
      "source_dom_id": "comment_10197230200_",
      "parent_comment_srl": null,
      "parent_comment_id_raw": null,
      "depth": 0,
      "source_order": 0,
      "is_best": true,
      "badges": ["BEST"],
      "author": {
        "nickname": "V5_Faker",
        "member_srl": "1324753328",
        "level": "27"
      },
      "created_at_raw": "4 시간 전",
      "created_at": null,
      "content": "댓글 내용",
      "reactions": {
        "up_count": 375,
        "down_count": 0,
        "score": 375
      },
      "permalink": "https://www.fmkorea.com/10196696065/10197230200#comment_10197230200"
    }
  ]
}
```

### 2.5. 작업 상태 및 체크포인트 저장
- 체크포인트 모델
  - 최상위 타입은 `Checkpoint`다.
  - `schema_version="fmkorea.checkpoint.v1"`를 저장한다.
  - `job_id`: 체크포인트 대상 Job ID
  - `status`: `running`, `stopped`, `completed`
  - `reason`: `stopped`일 때만 저장하며 `captcha`, `blocked`, `manual_stop`, `error`, `timeout`, `lease_expired` 중 하나다.
  - `job_config`: 재개에 필요한 원본 `JobConfig`
  - `collector_cursor`: 링크 수집기의 현재 위치
  - `completed_keys`: 저장 완료된 게시글 키 목록
  - `queued_links`: 중단 시 아직 처리되지 않은 후보 링크 목록. 없으면 `null`
  - `updated_at`: 체크포인트 갱신 시각
- `collector_cursor` 모델
  - `source_type`: 수집 source type
  - `page`: 목록/검색 수집 중 마지막으로 처리 중이던 페이지
  - `board_id`: 현재 처리 중인 게시판
  - `last_document_srl`: 마지막으로 확인한 글 번호
  - `last_url`: 마지막으로 확인한 URL
- 저장 위치
  - 로컬 체크포인트는 `<base_output_path>/Checkpoint.json` 하나에 저장한다.
  - 로컬 체크포인트 파일의 wrapper schema는 `fmkorea.local_checkpoint.v1`이고, 내부 `checkpoints` 객체가 `job_id`별 `Checkpoint`를 가진다.
  - PostgreSQL 모드에서는 `PostgresCheckpointStore`가 `DATABASE_URL`로 연결한 DB에 `job_id`별 체크포인트를 저장한다.
  - JSONL 결과 파일과 달리 로컬 체크포인트는 run 폴더 안에 두지 않는다.
- 저장 시점
  - 게시글 저장 성공 10건마다 `status="running"` 체크포인트를 저장한다.
  - 게시글 저장 성공 후 해당 게시글의 `PostKey(site_id, board_id, document_srl, document_id_raw)`를 `completed_keys`에 반영한다.
  - 수동 중단, 복구 불가능한 오류, CAPTCHA, 차단, timeout, lease 만료 시 `status="stopped"`와 `reason`을 저장한다.
  - Queue가 비고 모든 워커가 정상 종료되면 `status="completed"`를 저장한다.
- 재개 처리
  - CLI는 `fmkorea-scraper resume --job-id <job_id>`로 재개한다.
  - 로컬 재개에서 `--job-id`가 없으면 `<base_output_path>/Checkpoint.json`의 최신 체크포인트를 사용한다.
  - 컨테이너 환경은 `RESUME=true`, `JOB_ID=<checkpoint job_id>`로 재개한다.
  - 재개 시 기존 JSONL 파일에 이어 쓰지 않고 새 run을 만들며, `completed_keys` 기준으로 이미 저장된 게시글을 중복 저장하지 않는다.
  - 중복 기준은 `(site_id, board_id, document_id_raw)`를 우선 사용한다.
- 체크포인트에 저장되는 `JobConfig`
  - `JobConfig`는 수집 대상, 수집 옵션, 워커 옵션, 저장소 옵션만 저장한다.
  - `ScrapeOptions`에는 댓글/미디어 모드, 첨부파일 포함 여부, 요청 간격, 게시글 재시도 횟수, 파서 제한값(`max_comment_pages`, `max_comments`, `max_content_blocks`)을 저장한다.
  - User-Agent 파일 경로, User-Agent 교체 주기, Proxy, timeout 같은 HTTP 실행값은 `JobConfig`에 저장하지 않는다.
  - 일반 Playwright fallback 활성화 여부도 실행 환경 값이며 `JobConfig`에 저장하지 않는다.
  - 위 HTTP 실행값은 CLI, 터미널 마법사, 컨테이너, MCP, 라이브러리 adapter가 실행 시점에 `HttpRuntimeConfig`로 조립한다.
  - 과거 체크포인트에 `job_config.runtime_config`가 남아 있으면 로드 시 해당 legacy 필드만 버리고 재개한다.

### 2.6. 차단 대응, Proxy, User-Agent, 속도 제어
- CAPTCHA/차단 포착
  - CAPTCHA 또는 명백한 차단 페이지를 감지하면 자동 우회를 시도하지 않는다.
  - 현재 작업을 중단하고 체크포인트와 중단 사유를 저장한다.
  - 체크포인트 저장 후 터미널과 로그에 저장된 `job_id`를 출력한다.
  - HTTP 응답 본문 판정은 앞부분 4096 byte 샘플을 기준으로 수행한다.
  - CAPTCHA 판정 문자열은 `captcha`, `자동입력`, `자동 입력`, `보안문자`이며, 최종 URL에 `captcha`가 포함되어도 CAPTCHA로 본다.
  - 차단 판정 status code는 `403`, `430`이다.
  - 차단 판정 문자열은 `blocked`, `abnormal access`, `비정상적인 접근`, `접근이 제한`, `차단되었습니다`, `에펨코리아 보안 시스템`이다.
  - 삭제/비공개/권한 없음 판정 status code는 `404`, `410`이다.
  - 삭제/비공개/권한 없음 판정 문자열은 `deleted`, `unavailable`, `삭제된 게시글`, `삭제된 게시물`, `존재하지 않는 게시글`, `존재하지 않는 게시물`, `권한이 없습니다`, `열람할 수 없습니다`이다.
  - retry 대상 status code는 기본 `{429,500,502,503,504}`다.
- Scrapling 및 브라우저 렌더링 fallback
  - 목록, 검색, 상세 HTML은 Scrapling `Selector`로 파싱한다.
  - 기본 요청 경로는 `httpx.AsyncClient`이며 브라우저를 실행하지 않는다.
  - CLI/Docker 실행에서는 기본 활성화한다.
  - CLI에서는 `--no-browser-fallback`, 컨테이너에서는 `FMKOREA_BROWSER_FALLBACK=false`로 비활성화할 수 있다.
  - 로컬에서 브라우저 fallback을 사용하려면 `scrapling[fetchers]` optional dependency와 Playwright browser 설치가 필요하다.
  - Docker image는 `.[s3,postgres,browser]`를 설치하고 `scrapling install`을 수행하므로 브라우저 fallback 실행 준비를 image build 단계에서 끝낸다.
  - HTTP 응답이 성공으로 분류됐지만 목록/검색/상세 필수 DOM이 없을 때만 일반 Playwright 기반 Scrapling `DynamicFetcher`를 한 번 사용한다.
  - 목록/게시판 검색 필수 DOM은 `div.bd`, 통합 검색 필수 DOM은 `.searchResult, .search_result`, 게시글 상세 필수 DOM은 `#bd_capture`를 기준으로 한다.
  - `DynamicFetcher` 호출은 `headless=true`, `google_search=false`, `load_dom=true`, `wait_selector=<required_selector>`, `timeout=<read_timeout_ms>`로 수행한다.
  - 호출자 header가 있으면 `extra_headers`로 넘기고, Proxy가 활성화되어 있으면 브라우저 proxy 설정에도 전달한다.
  - CAPTCHA, HTTP 430, 보안 시스템 문구, 명백한 차단 응답에는 브라우저 fallback을 실행하지 않고 즉시 체크포인트를 저장한 뒤 중단한다.
  - 브라우저 의존성이 설치되지 않은 환경에서 fallback이 필요해지면 `browser_dependency_missing` 사유의 `BrowserFallbackError`로 처리한다.
  - 브라우저 응답에서도 필수 DOM이 없거나 브라우저 실행이 실패하면 `browser_fallback_failed`로 기록하고 terminal checkpoint를 저장한 뒤 Job을 종료한다.
  - Scrapling `StealthyFetcher`와 CAPTCHA/차단 자동 우회 기능은 사용하지 않는다.
- User-Agent Mixer
  - 차단 완화를 위해 요청 시 사용할 User-Agent를 주기적으로 교체한다.
  - User-Agent 목록 파일명은 `user-agents.txt`로 통일한다.
  - 로컬 실행 시 실행 파일과 같은 위치의 `user-agents.txt`를 자동 로드한다.
  - 터미널 옵션에서 파일 탐색기 창을 열어 User-Agent 목록 파일을 불러오고, 실행 파일과 같은 위치의 `user-agents.txt`로 저장/교체 가능하다.
  - `user-agents.txt`는 사용자가 직접 편집할 수 있도록 비인코딩 평문으로 저장한다.
  - 파일 포맷은 한 줄에 User-Agent 하나다.
  - 빈 줄은 무시한다.
  - 파일이 없거나 유효한 User-Agent가 없으면 기본 User-Agent 하나만 사용한다.
  - 기본 교체 주기는 요청 10회마다 1회다.
  - CLI 옵션으로 파일 경로와 교체 주기를 변경할 수 있다.
  - CLI 옵션명은 `--user-agent-file`, `--user-agent-rotate-every`다.
  - 비동기 멀티 워커 실행 시에도 컨테이너/프로세스 내부 공용 요청 카운터 기준으로 교체한다.
  - 현재 Dockerfile은 `user-agents.txt`를 이미지에 복사하지 않는다.
  - 컨테이너에서 별도 User-Agent 파일을 쓰려면 파일을 마운트한 뒤 `FMKOREA_USER_AGENT_FILE=<컨테이너 내부 경로>`를 지정한다.
  - 컨테이너에서 `FMKOREA_USER_AGENT_FILE`이 없으면 기본 User-Agent 하나를 사용한다.
  - 컨테이너 간 User-Agent 교체 카운터는 공유하지 않는다.
- Proxy
  - Proxy를 통해 httpx 요청을 전송한다.
  - `httpx.AsyncClient`는 `trust_env=False`로 생성하므로 운영체제/쉘의 `HTTP_PROXY`, `HTTPS_PROXY` 같은 시스템 환경변수는 자동 사용하지 않는다.
  - Proxy는 CLI/마법사에서 명시 입력한 값 또는 실행 위치의 `.env` 파일 값만 사용한다.
  - Proxy 설정은 실행 파일과 같은 위치의 `.env` 파일에 저장한다.
  - `.env`는 사용자가 직접 편집할 수 있도록 비인코딩 평문으로 저장한다.
  - 저장 변수
    - `FMKOREA_PROXY_HOST=<host:port 또는 proxy URL>`
    - `FMKOREA_PROXY_ID=<proxy ID>`
    - `FMKOREA_PROXY_PW=<proxy password>`
  - 로컬 실행 Flow
    - 사용자가 터미널에서 Proxy 옵션을 켠 경우 이를 최우선으로 처리한다.
    - Proxy 옵션을 켜면 host, ID, PW를 터미널에서 입력받고, 입력한 값을 `.env`에 저장한 뒤 현재 실행에 사용한다.
    - 사용자가 Proxy 옵션을 켜지 않았고 실행 파일과 같은 위치에 `.env`가 있으면 `.env`의 Proxy 변수를 자동 사용한다.
    - `.env`가 없거나 유효한 Proxy 변수가 없으면 Proxy를 비활성화한다.
  - 컨테이너 실행 Flow
    - 컨테이너 이미지는 `docker-entrypoint.sh`를 포함한다.
    - `.dockerignore`는 `.git`, 가상환경, 테스트 캐시, 출력물, `.env` 계열 secret 후보, 문서 산출물, CDK synth 산출물을 Docker build context에서 제외한다.
    - `docker run` 시 환경변수로 `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW`를 입력 가능하다.
    - Docker `--env-file`을 통해 `.env` 형식 파일을 환경변수로 주입하는 방식도 허용한다.
    - `docker-entrypoint.sh`는 Docker 전용 시작 스크립트이며, 전달받은 argv를 유지한 채 `python -m fmkorea_scraper.adapters.container "$@"`로 실행을 위임한다.
    - 컨테이너 내부 프로그램은 Docker가 주입한 환경변수를 직접 읽어 Proxy를 적용한다.
  - `.env`는 문서화된 보안 예외로 평문 저장을 허용하되, `.gitignore` 포함과 터미널 경고를 필수로 한다.
  - 로그에는 Proxy password, raw `.env` 내용, 인증정보를 남기지 않는다.
- Cookie
  - 사용자가 만든 cookie 파일을 읽거나 HTTP 요청에 적용하는 기능은 제공하지 않는다.
  - CLI, 터미널 마법사, 컨테이너, MCP에는 사용자 cookie 파일 경로 입력 옵션을 두지 않는다.
  - 서버가 응답으로 내려준 임시 cookie는 현재 `HttpClient` 생명주기 안에서만 메모리로 유지할 수 있다.
  - User-Agent 교체 또는 `HttpClient` 종료 시 in-memory cookie jar를 reset한다.
  - Job 재시작, resume, Proxy 변경 이후에는 이전 cookie를 재사용하지 않는다.
  - raw cookie는 로그, checkpoint, output JSONL, report, failure record에 저장하지 않는다.
- 스크래핑 속도 조절
  - 요청 사이의 대기 시간을 사용자가 설정 가능하다.
  - 기본값은 안정성을 우선하여 너무 빠른 연속 요청을 피하도록 설정한다.
  - 게시판 목록, 게시판 내 검색, 통합 검색, 게시글 상세, 댓글, 이미지/동영상 다운로드 요청에 동일하게 적용한다.
  - 전역 요청 간격, 게시글 상세 요청 동시성, 미디어 다운로드 동시성, 실패 시 backoff를 설정 가능하게 한다.
  - 429, 500, 502, 503, 504 응답은 retry/backoff 대상이다.
  - 403, 430, CAPTCHA, 보안 시스템 문구, 명백한 차단 응답은 자동 우회하지 않고 중단 사유를 저장한다.

### 2.7. 실패 기록 및 재처리
- 실패는 `failures.jsonl`에 저장한다.
- parser-stage 실패는 추후 재처리 유닛에서 direct-post 경로로 재수집한다.
- 네트워크, CAPTCHA, 차단, 저장소 실패는 재처리 유닛 대상에서 제외하고 기존 retry/checkpoint/운영 대응 절차에서 처리한다.
- 실패 기록 필드
  - `schema_version="fmkorea.failure.v1"`
  - `job_id`
  - `stage`
  - `reason`
  - `retryable`
  - `url`
  - `post_key`
    - `site_id`
    - `board_id`
    - `document_srl`
    - `document_id_raw`
  - `safe_message`
  - `details`
  - `created_at`
- 실패 JSONL 한 줄 예시
```json
{
  "schema_version": "fmkorea.failure.v1",
  "job_id": "job-a",
  "stage": "post",
  "reason": "ParseFailureError",
  "retryable": true,
  "url": "https://www.fmkorea.com/best/10195585295",
  "post_key": {
    "site_id": "fmkorea",
    "board_id": "best",
    "document_srl": 10195585295,
    "document_id_raw": "10195585295"
  },
  "safe_message": "required detail metadata missing",
  "details": {
    "job_id": "job-a",
    "stage": "post",
    "reason": "ParseFailureError",
    "retryable": true,
    "url": "https://www.fmkorea.com/best/10195585295",
    "post_key": {
      "site_id": "fmkorea",
      "board_id": "best",
      "document_srl": 10195585295,
      "document_id_raw": "10195585295"
    }
  },
  "created_at": "2026-08-11T12:05:00+09:00",
  "metadata": {}
}
```
- 현재 재처리 계약
  - CLI 명령: `fmkorea-scraper retry-parser-failures --failure-path <failures.jsonl>`
  - `--existing-success-path <posts.jsonl>`를 지정하면 이미 성공한 게시글은 제외한다.
  - `--from-report`, `--from-checkpoint`는 재처리 입력 복원을 돕는 옵션이며 동시에 사용할 수 없다.
  - `RetryRequest`는 `failure_input`, `skip_existing_success`, `existing_success_path`, `from_report_path`, `from_checkpoint_path`, `retry_job_id`를 가진다.
  - 재처리는 기존 `PostDetailService`와 `JobRunner` direct-post 경로를 재사용한다.

### 2.8. 현재 public 실행 계약
- Python import API
  - `search_board(request, http_client=...)`
  - `search_integrated(request, http_client=...)`
  - `fetch_post(request, http_client=...)`
  - `fetch_comments(request, http_client=...)`
  - `run_job(config, runner=..., run_id=None)`
  - `resume_job(request, runner=..., run_id=None)`
  - `retry_parser_failures(request, retry_service=None)`
  - `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`는 호출자가 `http_client`를 주입해야 한다. MCP wrapper는 필요 시 기본 `HttpClient(HttpRuntimeConfig())`를 생성해 호출한다.
  - `fetch_comments`의 public `CommentRequest`는 `url`, `board_id`, `document_srl`, `comment_mode`만 받는다. `max_comment_pages`를 직접 받지 않으므로 기본 호출은 상세 HTML에 포함된 댓글 중심으로 반환한다.
  - 추가 댓글 페이지까지 포함하려면 `fetch_post(PostRequest(..., scrape_options=ScrapeOptions(max_comment_pages=N)))` 또는 Job 실행 경로를 사용한다.
  - `run_job`, `resume_job`는 core API 자체가 runner를 생성하지 않는다. CLI/Docker adapter 또는 library caller가 `JobRunner`와 저장소/HTTP/parser dependency를 조립해 `runner`로 주입해야 한다.
  - `retry_parser_failures`는 `retry_service`를 주입하지 않으면 기본 `ParserFailureRetryService`를 사용한다.
- CLI 진입점
  - `python main.py ...`
  - `python -m fmkorea_scraper.adapters.cli ...`
  - 설치 후 `fmkorea-scraper ...`
- CLI 공통 옵션
  - 범위 옵션: `--date-from`, `--date-to`, `--min-document-srl`, `--max-document-srl`
  - 글번호 alias: `--min-post-number`는 `--min-document-srl`, `--max-post-number`는 `--max-document-srl`로 처리한다.
  - 저장 위치: `--output-path`
  - 수집 옵션: `--comment-mode`, `--media-mode`, `--include-attachments`, `--no-attachments`, `--max-comment-pages`, `--max-comments`, `--max-content-blocks`
  - 실행 옵션: `--request-interval-seconds`, `--max-post-retries`, `--post-worker-count`, `--media-worker-count`, `--queue-max-size`, `--timeout-seconds`
  - User-Agent/Proxy 옵션: `--user-agent-file`, `--user-agent-rotate-every`, `--proxy-host`, `--proxy-id`, `--proxy-pw`
  - browser fallback 옵션: `--browser-fallback`, `--no-browser-fallback`
- CLI subcommand
  - `run`
  - `resume`
  - `retry-parser-failures`
  - `import-user-agents`
  - `configure-proxy`
  - `wizard`
- `run --source` 값
  - `direct-post`
  - `board-list`
  - `board-search`
  - `integrated-search`
  - `deep-search`
  - `no-keyword-range`
- `run` source별 주요 옵션
  - `direct-post`: `--url`을 1회 이상 입력한다.
  - `board-list`: `--board-id`, `--category-id`, `--page-start`, `--page-end`, 범위 옵션을 사용한다.
  - `board-search`: `--board-id`, `--keyword`, `--search-target`, `--category-id`, `--page-start`, `--page-end`, 범위 옵션을 사용한다.
  - `integrated-search`: `--keyword`, `--search-target`, `--page-start`, `--page-end`, 범위 옵션을 사용한다.
  - `deep-search`: `--keyword`, `--search-target`, `--seed-page-limit`, `--board-candidate`, 범위 옵션을 사용한다. `--board-candidate`는 통합 검색 seed에서 발견한 게시판 외에 사용자가 직접 추가할 게시판 ID를 반복 입력하는 옵션이다.
  - `no-keyword-range`: `--board-id`, `--category-id`, 범위 옵션을 사용한다.
- `retry-parser-failures` 주요 옵션
  - 필수: `--failure-path`
  - 선택: `--existing-success-path`, `--from-report`, `--from-checkpoint`, `--retry-job-id`, `--job-id`, `--stage`
  - `--stage`를 생략하면 `post` stage만 재처리 대상으로 삼는다.
  - 기본값은 `--skip-existing-success`이며, `--no-skip-existing-success`로 기존 성공 결과 중복 제외를 끌 수 있다.
  - `--from-report`와 `--from-checkpoint`는 동시에 사용할 수 없다.
- MCP tool
  - `search_board`
  - `search_integrated`
  - `fetch_post`
  - `fetch_comments`
  - `run_job`
  - `resume_job`
  - `retry_parser_failures`
  - 모든 MCP tool은 성공 시 `{"ok": true, "data": ...}`를 반환한다.
  - 실패 시 `{"ok": false, "error": <safe_error_payload>}`를 반환한다.
  - MCP error payload에는 stage, reason, retryable 여부, safe message만 포함하고 secret, cookie, raw header, raw body는 포함하지 않는다.
- 컨테이너 계약
  - Docker entrypoint는 `docker-entrypoint.sh`다.
  - entrypoint는 전달받은 argv를 유지해 `python -m fmkorea_scraper.adapters.container "$@"`를 실행한다.
  - 컨테이너는 `run`, `retry-parser-failures`, `RESUME=true` 흐름을 지원한다.
  - 컨테이너 필수 환경변수: `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
  - 컨테이너 선택 환경변수: `S3_REGION`, `S3_PREFIX`, `S3_FORCE_PATH_STYLE`, `JOB_ID`, `RESUME`, `FMKOREA_USER_AGENT_FILE`, `FMKOREA_USER_AGENT_ROTATE_EVERY`, `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW`, `FMKOREA_BROWSER_FALLBACK`
  - CLI `resume`은 기본적으로 로컬 `Checkpoint.json`을 읽는 흐름이다.
  - 컨테이너 `resume`은 `RESUME=true`와 `JOB_ID=<checkpoint job_id>`를 환경변수로 받고 PostgreSQL checkpoint store에서 읽는 흐름이다.
  - 컨테이너 실행은 결과 JSONL/미디어를 S3 호환 저장소에 쓰고 체크포인트를 PostgreSQL에 쓰는 구성을 기본 계약으로 한다.

### 2.9. 현재 core model 및 port 계약
- 공통 모델 규칙
  - public contract는 Pydantic v2 모델로 정의한다.
  - 모든 public model은 `extra="forbid"`로 선언되지 않은 필드를 거부한다.
  - 확장이 필요한 모델은 공통 `metadata: dict[str, Any]` 필드를 가진다.
  - `metadata`는 JSON 직렬화 가능 값만 허용하고, 깊이와 byte 크기를 제한한다.
- `JobConfig`
  - 필드: `job_id`, `job_type`, `site_id`, `source`, `scrape_options`, `worker_config`, `storage_config`, `created_at`
  - `site_id`는 `"fmkorea"` 고정이다.
  - `job_type.value`는 `source.type`과 같아야 한다.
  - legacy checkpoint 호환을 위해 입력 dict에 `runtime_config`가 있으면 해당 필드만 버린다.
- source 모델
  - `DirectPostSource`: `type="direct_post"`, `urls`
  - `BoardListSource`: `type="board_list"`, `board_id`, `category_id`, `page_start`, `page_end`, `range_filter`
  - `BoardSearchSource`: `type="board_search"`, `board_id`, `category_id`, `keyword`, `search_target`, `page_start`, `page_end`, `range_filter`
  - `IntegratedSearchSource`: `type="integrated_search"`, `keyword`, `search_target`, `page_start`, `page_end`, `range_filter`
  - `DeepSearchSource`: `type="deep_search"`, `keyword`, `seed_search_target`, `seed_page_limit`, `board_ids`, `range_filter`
  - `NoKeywordRangeSource`: `type="no_keyword_range"`, `board_id`, `category_id`, `range_filter`
  - `RealtimeKeywordSource`: `type="realtime_keyword"`, `scope`, `board_id`, `keyword`, `poll_interval_seconds`, `termination`
  - `RealtimeAllSource`: `type="realtime_all"`, `board_id`, `category_id`, `poll_interval_seconds`, `termination`
  - `ParserFailureRetrySource`: `type="parser_failure_retry"`, `failure_input`, `skip_existing_success`
  - `deep_search`와 `no_keyword_range`는 기간 또는 글번호 범위 중 하나 이상을 요구한다.
  - realtime source의 `poll_interval_seconds` 기본값은 30.0초다.
  - realtime source의 종료 조건은 `duration_seconds` 또는 `end_at` 중 정확히 하나다.
  - realtime source 모델은 현재 환경변수 입력과 향후 polling runner 계약을 보존하기 위한 모델이다. 현재 production `JobRunner`는 source를 1회 collect하는 one-shot 실행 구조다.
- 실행 옵션 모델
  - `ScrapeOptions` 기본값: `comment_mode="all"`, `media_mode="url_only"`, `include_attachments=true`, `request_interval_seconds=1.0`, `max_post_retries=3`
  - `ScrapeOptions` 제한값: `max_comment_pages`, `max_content_blocks`, `max_comments`
  - `WorkerConfig` 기본값: `post_worker_count=1`, `media_worker_count=1`, `queue_max_size=null`
  - `RangeFilter`: `date_from`, `date_to`, `min_document_srl`, `max_document_srl`
- 저장소 모델
  - `StorageConfig`: `output_mode`, `checkpoint_mode`, `base_output_path`, `s3`, `postgres`
  - `output_mode="local"`이면 로컬 JSONL/미디어 저장소를 사용한다.
  - `output_mode="s3_compatible"`이면 `S3StorageConfig(endpoint_url, bucket, prefix, region)`가 필수다.
  - `checkpoint_mode="local"`이면 `<base_output_path>/Checkpoint.json`을 사용한다.
  - `checkpoint_mode="postgres"`이면 `PostgresCheckpointConfig(dsn)`이 필수다.
- HTTP 런타임 모델
  - `HttpRuntimeConfig`는 `JobConfig`에 저장하지 않는 실행 시점 설정이다.
  - 필드: `request_interval_seconds`, `timeout`, `retry_policy`, `user_agent`, `proxy`, `proxy_env_path`, `execution_dir`, `default_headers`, `browser_fallback_enabled`
  - `TimeoutConfig` 기본값: connect 10초, read/write 30초, pool 10초
  - `RetryPolicy` 기본값: max attempts 3, backoff base 0.25초, max 5초, retry status `{429,500,502,503,504}`
  - CLI/컨테이너는 `ScrapeOptions.max_post_retries + 1`을 HTTP max attempts로 변환한다.
- runner port
  - `HttpPort`: `get`, `post`, `download`, `close`
  - `OutputStorePort`: `append_post`, `write_report`, `finalize`
  - `MediaStorePort`: `save_media`, `save_metadata_only`
  - `FailureStorePort`: `write_failure`, `read_failures`
  - `CheckpointStorePort`: `save`, `load`, `load_latest`
  - `LoggerPort`: `debug`, `info`, `warning`, `error`
- report 모델
  - `JobReport`: `schema_version="fmkorea.job_report.v1"`, `job_id`, `status`, `started_at`, `finished_at`, `collected_count`, `stored_count`, `failure_count`, `output_refs`
  - `RetryReport`는 `selected_count`, `skipped_count`를 추가한다.
  - `StoredObjectRef`: `storage_mode`, `path`, `bucket`, `object_key`
- `JobReport` JSON 예시
```json
{
  "schema_version": "fmkorea.job_report.v1",
  "job_id": "job-a",
  "status": "completed",
  "started_at": "2026-08-11T12:00:00+09:00",
  "finished_at": "2026-08-11T12:10:00+09:00",
  "collected_count": 120,
  "stored_count": 118,
  "failure_count": 2,
  "output_refs": [
    {
      "storage_mode": "local",
      "path": "D:\\HongDev\\ELSAPHABA\\FMkorea-Scraper\\outputs\\job-a\\run-1\\posts.jsonl",
      "bucket": null,
      "object_key": "outputs/job-a/run-1/posts.jsonl",
      "metadata": {}
    },
    {
      "storage_mode": "local",
      "path": "D:\\HongDev\\ELSAPHABA\\FMkorea-Scraper\\outputs\\job-a\\run-1\\failures.jsonl",
      "bucket": null,
      "object_key": "outputs/job-a/run-1/failures.jsonl",
      "metadata": {}
    }
  ],
  "metadata": {}
}
```
- `RetryReport` JSON 예시
```json
{
  "schema_version": "fmkorea.job_report.v1",
  "job_id": "retry-job-a",
  "status": "completed",
  "started_at": "2026-08-11T13:00:00+09:00",
  "finished_at": "2026-08-11T13:05:00+09:00",
  "collected_count": 10,
  "stored_count": 9,
  "failure_count": 1,
  "output_refs": [],
  "selected_count": 10,
  "skipped_count": 3,
  "metadata": {}
}
```

## 3. 기술 스택
- Python
  - 지원 버전: Python `>=3.11`
  - 공식 검증에 사용한 버전: Python 3.12.10
  - 패키지 방식: `pyproject.toml` + hatchling
- 기본 의존성
  - `anyio>=4,<5`
  - `pydantic>=2,<3`
  - `httpx>=0.28,<1`
  - `python-dotenv>=1,<2`
  - `scrapling>=0.4.15,<0.5`
- 선택 extra
  - `s3`: `boto3>=1.34,<2`
  - `postgres`: `psycopg[binary]>=3,<4`
  - `mcp`: `mcp>=1,<2`
  - `analysis`: `polars>=1,<2`
  - `browser`: `scrapling[fetchers]>=0.4.15,<0.5`
  - `test`: `hypothesis>=6,<7`, `pytest>=8,<9`
- HTTP 런타임
  - `httpx.AsyncClient`를 기본 요청 경로로 사용한다.
  - Proxy는 `httpx` proxy 설정으로 주입한다.
  - `.env` 파일 기반 Proxy 환경변수 로드를 지원한다.
  - 서버가 내려준 임시 cookie는 `HttpClient` 생명주기 안에서만 메모리로 유지하고, User-Agent 교체 또는 client 종료 시 reset한다.
- 파싱 런타임
  - Scrapling `Selector` 기반 HTML 파싱
  - 공통 DOM helper: `src/fmkorea_scraper/dom.py`
  - 정상 HTTP 응답의 목록/검색/상세 필수 DOM 누락 시에만 Scrapling `DynamicFetcher`의 일반 Playwright 렌더링 사용
  - `DynamicFetcher` fallback은 `HttpClient` 인스턴스 내부 lock으로 직렬화한다.
- 병렬 실행
  - `asyncio` 기반 링크 수집 워커 + 게시글 수집 워커 분리
  - 내부 큐는 `asyncio.Queue`
  - 미디어 다운로드는 `asyncio.Semaphore(media_worker_count)`로 제한
- 저장 및 분석
  - 표준 `json` 기반 JSONL 저장
  - Polars 기반 JSONL 가공 및 분석
  - 로컬 체크포인트는 `Checkpoint.json`
  - 컨테이너 체크포인트는 PostgreSQL
  - 컨테이너 JSONL/미디어 출력은 S3 호환 객체 저장소
  - 기본 운영 방향은 Garage이며, SeaweedFS는 대량 미디어/소파일 저장, FUSE, Iceberg 요구가 생길 때 확장 후보로 유지
- 배포
  - Docker worker image는 `python:3.11-slim` 기반이다.
  - image build 시 `.[s3,postgres,browser]`를 설치하고 `scrapling install`로 Chromium을 설치한다.
  - AWS CDK는 VPC, S3 output bucket, RDS PostgreSQL, ECS Fargate worker, CloudWatch Logs/EventBridge 기반 실패 감지를 구성한다.
  - CDK는 Docker image build/push, 중앙 Job Queue, 통합 운영 UI, EKS 배포를 포함하지 않는다.

## 4. 디렉토리 구조
```
FMKorea-Scraper/
├── main.py
├── pyproject.toml
├── requirements.lock
├── Dockerfile
├── docker-entrypoint.sh
├── .dockerignore
├── README.md
├── docs/
│   └── FMKorea-Scraper_Function_Specification.md
├── aidlc-docs/
│   ├── aidlc-state.md
│   ├── audit.md
│   ├── inception/
│   └── construction/
├── infra/
│   └── cdk/
│       ├── app.py
│       ├── cdk.json
│       ├── requirements.txt
│       ├── config/
│       │   ├── dev.yaml
│       │   ├── staging.yaml
│       │   └── prod.yaml
│       ├── stacks/
│       │   ├── config.py
│       │   ├── naming.py
│       │   ├── shared_infra_stack.py
│       │   └── worker_stack.py
│       └── tests/
├── src/
│   └── fmkorea_scraper/
│       ├── __init__.py
│       ├── core/
│       │   ├── api.py
│       │   ├── errors.py
│       │   ├── normalization.py
│       │   ├── ports.py
│       │   ├── schema.py
│       │   └── validation.py
│       ├── models/
│       │   ├── base.py
│       │   ├── checkpoint.py
│       │   ├── comment.py
│       │   ├── content.py
│       │   ├── enums.py
│       │   ├── failure.py
│       │   ├── job.py
│       │   ├── media.py
│       │   ├── post.py
│       │   └── report.py
│       ├── http/
│       │   └── runtime.py
│       ├── collect/
│       │   ├── models.py
│       │   ├── parsers.py
│       │   ├── policies.py
│       │   ├── service.py
│       │   └── urls.py
│       ├── parse/
│       │   ├── comments.py
│       │   ├── content.py
│       │   ├── media.py
│       │   ├── metadata.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── warnings.py
│       ├── outputs/
│       │   ├── checkpoint.py
│       │   ├── errors.py
│       │   ├── factory.py
│       │   ├── jsonl.py
│       │   ├── layout.py
│       │   ├── local.py
│       │   ├── postgres_checkpoint.py
│       │   ├── redaction.py
│       │   ├── s3.py
│       │   └── s3_output.py
│       ├── runner/
│       │   ├── checkpointing.py
│       │   ├── models.py
│       │   ├── policies.py
│       │   ├── service.py
│       │   └── workers.py
│       ├── retry/
│       │   └── parser_failures.py
│       ├── adapters/
│       │   ├── cli.py
│       │   ├── container.py
│       │   ├── mcp.py
│       │   └── safe_errors.py
│       └── dom.py
├── tests/
│   ├── fixtures/
│   ├── snapshots/
│   ├── strategies/
│   └── test_*.py
├── user-agents.txt        # 실행 위치에 둘 수 있는 사용자 관리 파일
├── .env                   # 사용자 로컬 Proxy 설정 파일, 커밋 금지
├── outputs/               # 로컬 실행 결과, 커밋 금지
└── Checkpoint.json         # 로컬 체크포인트 예시, 커밋 금지
```

구현 주의:

- 실제 Python package는 `src/fmkorea_scraper` 아래에 있다.
- 루트 `main.py`는 `src` 경로를 추가한 뒤 CLI `main()`을 호출하는 호환 진입점이다.
- `.dockerignore`는 `.git`, 캐시, `.env`, 출력물, 문서, 테스트, CDK synth 결과를 Docker build context에서 제외한다.
- Docker image에는 `aidlc-docs`, `docs`, `tests`, `infra/cdk`를 복사하지 않는다.

## 5. 실행 형태
- CLI 직접 실행
  - 명령형 실행: `python -m fmkorea_scraper.adapters.cli run ...`
  - DCinside-Scraper와 같은 루트 호환 실행: `python main.py ...`
  - 설치 후 console script 실행: `fmkorea-scraper ...`
  - 터미널 마법사 실행: `fmkorea-scraper wizard`
  - CLI는 `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, `wizard`를 제공한다.
  - `run --source`는 `direct-post`, `board-list`, `board-search`, `integrated-search`, `deep-search`, `no-keyword-range`를 지원한다.
  - 실시간 수집은 별도 source 값이 아니라 `FMKOREA_REALTIME_ENABLED=true` 환경변수로 활성화한다.
- 라이브러리 import
  - 설정 객체와 Job 객체를 코드에서 생성해 수집기를 직접 호출할 수 있게 구성
  - 공개 함수는 `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, `retry_parser_failures`다.
  - import 시 스크래핑, 프롬프트, 파일 생성이 자동 실행되면 안 된다.
- Docker 워커 컨테이너
  - 환경변수로 Job 옵션, 저장소, Proxy, 실시간 종료 조건을 주입
  - JSONL/미디어는 S3 호환 저장소로 출력
  - 체크포인트는 PostgreSQL에 저장
  - Dockerfile은 `python:3.11-slim` 기반으로 `.[s3,postgres,browser]`를 설치하고 `scrapling install`을 수행한다.
  - `docker-entrypoint.sh`는 `python -m fmkorea_scraper.adapters.container "$@"`로 실행을 위임한다.
  - 컨테이너는 장기 실행 worker daemon이 아니라 전달받은 Job 하나를 수행하고 종료하는 one-shot worker다.
  - RabbitMQ/SQS 메시지 소비는 컨테이너 내부가 아니라 향후 외부 오케스트레이터가 담당한다.
- MCP
  - 같은 core service를 MCP tool wrapper에서 호출한다.
  - `python -m fmkorea_scraper.adapters.mcp`로 MCP server를 실행한다.
  - MCP tool은 safe error payload만 반환하며 secret, cookie, raw header를 노출하지 않는다.

대표 실행 예시:

```powershell
# 직접 게시글 수집
fmkorea-scraper run --source direct-post --url "https://www.fmkorea.com/best/10195585295"

# 게시판 내 검색
fmkorea-scraper run --source board-search --board-id "stock" --keyword "삼전" --search-target "title_content" --page-start 1 --page-end 5

# 통합 검색
fmkorea-scraper run --source integrated-search --keyword "삼전" --search-target "title_content" --page-start 1 --page-end 10

# 실패 재처리
fmkorea-scraper retry-parser-failures --failure-path ".\outputs\job-a\run-1\failures.jsonl"

# 체크포인트 재개
fmkorea-scraper resume --job-id "job-a"

# 터미널 마법사
fmkorea-scraper wizard
```

컨테이너 실행 예시:

```powershell
docker run --rm `
  -e DATABASE_URL="postgresql://user:pass@postgres/fmkorea" `
  -e S3_ENDPOINT_URL="http://garage:3900" `
  -e S3_BUCKET="scraper" `
  -e S3_ACCESS_KEY_ID="access" `
  -e S3_SECRET_ACCESS_KEY="secret" `
  -e S3_PREFIX="fmkorea" `
  fmkorea-scraper:latest `
  run --source board-search --board-id "stock" --keyword "삼전"
```

## 6. 향후 확장 계획

### 6.1. 데이터베이스 확장
- PostgreSQL 기반 Job 이력/실패 요약 테이블 확장
- S3 호환 객체 저장소 기반 JSONL/미디어 보존 정책 확장
- 임베딩 처리 및 벡터 유사도 검색
- Polars를 활용한 데이터 분석 및 시각화 기능 추가

### 6.2. 검색 기능 확장
- 검색 옵션 추가
  - 특정 키워드 포함/제외
  - 정규식 검색
  - 작성자/말머리/추천수/댓글 수 조건 조합
- 검색 결과 필터링 및 정렬 기능 강화

### 6.3. 작업 예약 및 알림 시스템
- 텔레그램 봇 또는 통합 운영 UI를 활용한 작업 예약 및 알림 시스템 구축
- 작업 상태 알림 및 결과 전송 기능
- 터미널에서 봇 토큰 또는 webhook URL 입력

### 6.4. 통합 작업 관리 시스템
- 단일 스크래퍼의 AWS 배포는 `infra/cdk`의 CDK 구성으로 관리 가능
- CDK는 VPC, S3 output bucket, RDS PostgreSQL, ECS cluster, Fargate worker task, CloudWatch Logs/EventBridge 기반 실패 감지를 구성
- CDK는 중앙 Job Queue, 통합 운영 UI, Docker image build, EKS 배포를 포함하지 않음
- RabbitMQ 같은 Job Queue는 스크래퍼 내부가 아니라 외부 오케스트레이터가 소비
- Queue 메시지는 게시글 링크 단위가 아니라 Job 단위이며, 외부 오케스트레이터가 `JobConfig`를 worker 컨테이너 환경 변수 또는 실행 인자로 변환
- Worker 컨테이너는 전달받은 Job 하나를 실행하고 종료하며, Job 내부 링크 큐는 기존 프로세스 내부 `asyncio.Queue`를 사용
- RabbitMQ broker, consumer, ack/nack, DLQ, lease, 중앙 retry/scheduler는 통합 플랫폼 단계에서 구현
- 향후 통합 플랫폼에서 마스터 컨테이너 - 워커 컨테이너 구조 기반으로 여러 커뮤니티 스크래퍼를 관리
- 작업 컨테이너 스케줄링 및 모니터링 기능
- 작업 상태 시각화 및 알림 기능
- 작업 실패 시 재시도 및 오류 로그 관리
- SQS 기반 작업 큐, lease 갱신, lease 만료 시 `reason="lease_expired"` 체크포인트 저장

### 6.4.1. Scrapling Spider 기반 실행 엔진 검토
- 현재 구현은 Scrapling `Selector`를 파서 런타임으로 사용하지만, Scrapling Spider는 사용하지 않는다.
- Spider 전환은 단순 파서 교체가 아니라 현재 `JobRunner`, 내부 게시글 큐, checkpoint, failure report, parser-failure retry, CLI/Docker/MCP 실행 경계를 바꾸는 실행 엔진 교체로 본다.
- 현재 AI-DLC 상태는 UOW-012 `Scrapling Spider PoC`의 Functional Design Questions 단계다.
- 현재 질문지 파일은 `aidlc-docs/construction/plans/uow-012-scrapling-spider-poc-functional-design-plan.md`다.
- 현재 확인된 답변은 Q2=`B`이며, 나머지 질문은 확정 전 상태로 남아 있다.
- UOW-012는 운영 코드 전환이 아니라 기존 public contract를 유지한 채 Spider가 실제로 단순화 효과를 내는지 검증하는 PoC/planning 단위다.
- 향후 여러 커뮤니티 스크래퍼의 크롤링 엔진을 하나의 Spider 표준으로 통일할 필요가 생기거나 현재 `JobRunner`/checkpoint 모델이 병목으로 확인될 경우, 별도 AI-DLC 단위에서 다음 항목을 검토한다.
  - Spider request scheduling과 기존 Job 단위 실행 모델의 매핑
  - Spider pause/resume과 PostgreSQL checkpoint의 매핑
  - Spider callback 실패와 `failures.jsonl`/parser retry의 매핑
  - HTTP 차단 감지 및 선택적 browser fallback 정책의 연결
  - 기존 CLI/Docker/MCP public contract 유지 여부
- PoC 결과가 현재 `JobRunner`보다 복잡도를 낮추지 못하면 Spider 리팩토링은 진행하지 않고 현재 구조를 유지한다.

### 6.5. 커뮤니티 통합 스크래퍼
- 통합 스크래핑 시스템의 에펨코리아용 워커 컨테이너로 스케줄링 및 스케일링
- 후속 커뮤니티별 스크래퍼를 추가할 때 각 커뮤니티의 원본 게시글 구조는 개별 JSON 스키마로 저장
- 개별 JSON 스키마는 수집 원본 보존을 우선하며, 커뮤니티별 특수 필드는 그대로 유지

### 6.6. 공통 분석 스키마 및 Polars 정규화
- 목적: 커뮤니티별 개별 JSON 스키마를 통합 커뮤니티 전략분석 플랫폼에서 함께 분석할 수 있는 Polars 가공용 공통 스키마로 변환
- 범위: 향후 개발 참고사항이며, 에펨코리아 원본 JSONL 저장 구조를 변경하지 않음
- 처리 위치
  - 스크래핑 단계: 커뮤니티별 개별 JSONL 저장
  - 정규화 단계: 개별 JSONL을 읽어 공통 분석 테이블로 변환
  - 분석 단계: Polars로 공통 테이블을 로드해 커뮤니티 간 비교/집계 수행
- 정규화 원칙
  - 원본 JSONL은 변경하지 않고 보존
  - 공통 스키마에 없는 커뮤니티별 특수 필드는 `extra` 또는 별도 확장 컬럼으로 보존
  - 커뮤니티에 없는 값은 `null`로 채움
  - 날짜, 숫자, 추천/비추천 수, 조회수, 작성자 식별자 등 분석 필드는 타입을 통일
- 공통 테이블 기본 구조
  - `posts`: 게시글 단위 테이블
  - `comments`: 댓글/덧글 단위 테이블
  - `media`: 이미지, 동영상, YouTube, X, 링크 등 본문 미디어 단위 테이블
- 댓글 정규화 규칙
  - 수집 JSON에서는 댓글을 게시글 하위에 중첩 저장할 수 있음
  - Polars 공통 스키마 정규화 시 게시글과 댓글을 별도 테이블로 분리
  - 일반 댓글은 `depth=0`, `parent_comment_id=null`
  - 덧글은 `depth=1`, `parent_comment_id=<상위 댓글 ID>`
  - BEST 댓글 여부와 추천/비추천 수는 `is_best`, `badges`, `reaction_up`, `reaction_down`, `reaction_score` 컬럼으로 보존
  - 댓글 정렬은 원본 배열 순서가 아니라 `created_at`, `comment_id`, `source_order` 중 사용 가능한 값을 기준으로 수행
- 정규화 출력 형식
  - `posts.jsonl`
  - `comments.jsonl`
  - `media.jsonl`
  - 대용량 분석이 필요해지면 Parquet 출력 추가 검토

### 6.7. Parser-stage 게시글 실패 재처리 유닛
- 목적: 전체 검색/수집 Job을 다시 실행하지 않고, 기존 실패 기록에서 parser-stage 게시글 실패만 골라 direct-post 경로로 재수집
- 대상 실패
  - `failures.jsonl`의 `stage == "post"`
  - 제목/작성자/게시글 식별자/metadata/content/comment 파싱 실패 계열
- 제외 실패
  - CAPTCHA, 차단, 네트워크, 저장소, 체크포인트, 수동 중단, 취소 계열 실패
- 출력
  - 새 run에 `posts.jsonl`, `failures.jsonl`, `report.json` 기록

## 7. 미들웨어 활용 계획
- MCP
  - 외부 에이전트가 게시판 검색, 통합 검색, 상세 게시글 수집, 실패 재처리를 호출하는 도구로 제공
  - MCP layer는 입력 검증과 권한/실행 제한만 담당하고 core 수집 로직은 재사용
- Python 라이브러리
  - 통합 플랫폼, 분석 파이프라인, 테스트 코드에서 직접 import해 사용할 수 있도록 공개 API를 유지
- 워커 컨테이너
  - 통합 플랫폼이 Job Queue를 소비한 뒤 실행시키는 one-shot Job 처리 단위
  - 컨테이너별 Proxy/User-Agent/속도 설정을 환경변수로 주입
- KubeRay
  - 대규모 분산 수집/분석이 필요해질 때 검토
  - 초기 구현 범위에는 포함하지 않음
