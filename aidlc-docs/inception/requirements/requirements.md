# 요구사항

## 의도 분석

- **사용자 요청**: `FMkorea-Scraper`를 AI-DLC 절차로 개발하되, `DCinside-Scraper`의 기능, 유닛, 구조, 문서를 가능한 한 계승한다.
- **요청 유형**: 신규 프로젝트 및 구조 마이그레이션
- **프로젝트 유형**: Greenfield
- **주요 요구사항 출처**: `docs\FMKorea-Scraper_Function_Specification.md`
- **상속 기준선**: `D:\HongDev\ELSAPHABA\DCinside-Scraper`
- **범위 추정**: 시스템 전체
- **복잡도 추정**: 복잡함
- **주요 사용 사례**: 통합 커뮤니티 스크래핑 시스템에서 FMKorea 전용 워커로 사용
- **1차 구현 목표**: CLI, 터미널 마법사, Python 라이브러리 API, 비동기 멀티 워커 수집, 워커 컨테이너, MCP 도구, parser-stage 실패 재처리, AWS CDK IaC

## 결정 요약

- DCinside-Scraper의 UOW-001~UOW-010 구조를 전체 계승한다.
- `site_id=fmkorea`, package=`fmkorea_scraper`, console script=`fmkorea-scraper`, env prefix=`FMKOREA_`를 사용한다.
- 공통 런타임, 저장소, checkpoint, CLI, container, MCP, CDK 구조는 계승하고, FMKorea URL/query/parser만 site-specific으로 교체한다.
- FMKorea 원본 JSON 스키마에서는 재게시/공유/인용/펌 필드인 `is_repost`, `repost`를 제거한다. 단, 공통 분석 스키마 정규화 단계에서는 필요 시 `is_repost=false`, `repost=null` 값을 합성할 수 있다.
- 사용자가 제공하는 cookie 파일은 지원하지 않는다. 서버가 내려준 임시 cookie는 현재 `HttpClient` 생명주기 안에서만 메모리로 유지하고 로그/출력/checkpoint에 저장하지 않는다.
- Security Baseline, Resiliency Baseline, Property-Based Testing을 모두 적용한다.

## 기능 요구사항

### FR-001. 지원 실행 방식

시스템은 다음 실행 방식을 지원해야 합니다.

- 터미널 기반 CLI
- 선택형 터미널 마법사
- Python 라이브러리 import API
- 비동기 멀티 워커 스크래퍼 런타임
- 통합 커뮤니티 스크래핑 시스템용 워커 컨테이너
- MCP 도구 인터페이스
- AWS CDK 기반 선택 배포 경로

GUI 또는 Web UI는 1차 구현 범위가 아닙니다.

### FR-002. 프로젝트 식별자

프로젝트는 다음 식별자를 사용해야 합니다.

- `site_id`: `fmkorea`
- Python package: `fmkorea_scraper`
- Console script: `fmkorea-scraper`
- 환경변수 prefix: `FMKOREA_`

### FR-003. 공개 콘텐츠 수집 범위

스크래퍼는 FMKorea의 공개 게시글과 댓글을 수집해야 합니다.

1차 구현에서 제외하는 범위:

- 자동 로그인
- 계정 생성 또는 세션 획득 자동화
- CAPTCHA 우회 또는 자동 CAPTCHA 풀이
- 삭제되었거나 접근할 수 없는 게시글 복구

사용자 제공 cookie 파일은 지원하지 않습니다. 서버가 내려준 임시 cookie만 현재 HTTP client 생명주기 안에서 메모리로 유지할 수 있으며, 인증 우회/자동 로그인/비공개 콘텐츠 접근 자동화를 의미하지 않습니다.

### FR-004. 수집 진입점

스크래퍼는 다음 수집 진입점을 지원해야 합니다.

- 게시글 URL 직접 입력 수집
- 게시판 목록 기반 수집
- 게시판 내 검색 결과 기반 수집
- 통합 검색 결과 기반 수집
- 심층검색 기반 수집
- 노키워드 기간 및 글번호 범위 수집
- 실시간 키워드 수집
- 실시간 전체 수집
- parser-stage 실패 게시글 재처리

### FR-005. HTTP 및 파싱 런타임

스크래퍼는 다음을 사용해야 합니다.

- 비동기 HTTP 요청과 멀티 워커 수집을 위한 `httpx`와 `asyncio`
- HTML 파싱을 위한 BeautifulSoup
- JSON/JSONL 저장을 위한 표준 `json`
- JSONL 가공 및 검증을 위한 Polars

스크래퍼 런타임은 Playwright에 의존하면 안 됩니다.

### FR-006. 게시글 후보 수집

목록/검색 단계에서는 게시글 후보 링크와 후보 메타데이터만 수집해야 합니다.

최종 저장용 제목, 말머리, 글쓴이, 작성일, 조회수, 추천수, 댓글 수, 본문, 댓글은 게시글 상세 페이지에서 다시 파싱해야 합니다.

목록 단계에서 수집한 값은 필터링, 중복 제거, 진단 로그용 `PostCandidate.metadata`로만 사용해야 합니다.

### FR-007. 게시글 상세 수집

게시글 상세 수집은 다음을 파싱해야 합니다.

- `site_id`
- `board_id`
- `board_name`
- `document_srl`
- canonical URL
- 말머리/category
- 제목
- 작성자 닉네임
- 작성자 회원 번호
- 작성자 레벨
- 작성일
- 조회수
- 포텐/방출 또는 이에 대응하는 반응 수
- 댓글 수
- 본문 텍스트
- 본문 content blocks
- 첨부파일
- 댓글/답글

### FR-008. 본문 콘텐츠와 미디어 수집

본문은 Polars 가공이 가능한 content block 구조로 저장해야 합니다.

필수 block type:

- `text`
- `image`
- `fmk_video`
- `youtube`
- `x`
- `link`
- `attachment`

각 block은 최소한 다음 공통 필드를 가져야 합니다.

- `order`
- `type`
- `url`
- `text`
- `provider`
- `metadata`

타입별 특수 필드는 가능한 한 `metadata` 또는 타입별 nullable field에 보존해야 합니다. Polars에서 `explode`/`unnest` 가능한 list-of-struct 구조를 유지해야 합니다.

외부 임베드 영상은 다운로드하지 않고 URL, provider, id, embed_url 등 메타데이터만 저장해야 합니다.

### FR-009. FMKorea 자체 동영상 수집

FMKorea 자체 업로드 동영상은 다음 정보를 수집해야 합니다.

- video URL
- poster URL
- file identifier
- download URL
- name
- upload date
- description
- width
- height
- 다운로드 상태

설명이 없거나 빈 값이면 `null`로 저장해야 합니다.

### FR-010. 댓글과 답글 수집

댓글과 답글 수집은 기본 포함이어야 합니다.

CLI 옵션으로 댓글 수집을 끌 수 있어야 합니다.

댓글은 flat list로 저장해야 하며 다음 필드를 포함해야 합니다.

- 댓글 ID
- 부모 댓글 ID
- depth
- BEST 댓글 여부
- 작성자 정보
- 작성일 원문
- 정규화 작성일
- 내용
- 추천/비추천 또는 이에 대응하는 반응 수

### FR-011. 재게시/공유/인용/펌 필드

FMKorea 원본 JSON 스키마는 `is_repost`, `repost` 필드를 포함하지 않아야 합니다.

이 결정은 FMKorea에서 해당 기능이 명확히 확인되지 않은 상태의 site-specific 원본 스키마 결정입니다.

향후 FMKorea에 재게시/공유/인용/펌 성격의 기능이 확인되면 별도 AI-DLC 변경으로 site-specific parser와 schema를 추가해야 합니다.

공통 분석 스키마 정규화 단계에서는 필요 시 누락 필드를 `is_repost=false`, `repost=null`로 합성할 수 있습니다.

### FR-012. 게시판 내 검색

게시판 내 검색은 FMKorea의 `search.php` 기반 query와 게시판별 `mid`를 사용해야 합니다.

지원 검색 대상:

- 제목 + 내용
- 요약보기 검색
- 제목
- 내용
- 글쓴이
- 댓글

검색 결과 단계에서는 후보 링크만 큐에 넣고, 최종 게시글 필드는 상세 페이지에서 다시 수집해야 합니다.

### FR-013. 통합 검색

통합 검색은 FMKorea 전체 검색 결과에서 게시글 후보를 수집해야 합니다.

기본 종료 조건:

- 검색 결과 없음
- 다음 페이지 없음

안전장치로 configurable max page를 둬야 합니다.

### FR-014. 심층검색

심층검색은 다음 순서로 수행해야 합니다.

1. 키워드로 통합 검색을 수행한다.
2. 통합 검색 결과에서 게시판 후보 목록을 만든다.
3. 후보 게시판별로 같은 키워드의 게시판 내 검색을 수행한다.
4. 조건에 맞는 게시글 링크를 게시글 수집 Queue에 추가한다.

심층검색 Job은 키워드가 필수입니다.

심층검색 Job은 글번호 범위 또는 기간 범위 중 하나 이상을 반드시 입력받아야 합니다.

### FR-015. 노키워드 기간 및 글번호 범위 수집

노키워드 범위 수집은 게시판 목록 페이지를 순차 탐색하며 후보 작성일과 `document_srl` 범위로 필터링해야 합니다.

전용 날짜 이동 API가 확인되기 전까지는 목록 순차 탐색을 기본 구현으로 합니다.

전용 날짜 이동 API가 확인되면 UOW-003에서 site-specific 최적화로 추가할 수 있습니다.

### FR-016. 실시간 수집

스크래퍼는 환경변수 기반 실시간 수집을 지원해야 합니다.

필수 환경변수:

- `FMKOREA_REALTIME_ENABLED=true`
- `FMKOREA_REALTIME_MODE=keyword|all`
- `FMKOREA_REALTIME_KEYWORD=<검색어>`
- `FMKOREA_REALTIME_DURATION_SECONDS=<실행 초>`
- `FMKOREA_REALTIME_END_AT=<UTC ISO-8601 종료 시각>`
- `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS=<반복 주기 초>`

`FMKOREA_REALTIME_DURATION_SECONDS`와 `FMKOREA_REALTIME_END_AT` 중 정확히 하나만 입력해야 합니다.

### FR-017. 멀티 워커 수집

Job마다 단일 링크 수집 워커가 목록/검색 페이지를 순회해야 합니다.

다수의 게시글 워커가 `asyncio.Queue`에서 게시글 후보 링크 단위로 작업을 가져와 상세 페이지를 병렬 비동기로 수집해야 합니다.

큐 단위는 Job이 아니라 게시글 후보 1개입니다.

### FR-018. 중복 제거

중복 제거 기준은 `(site_id, board_id, document_srl)`입니다.

상세 URL 문자열은 보조 진단 정보로만 사용합니다.

### FR-019. JSONL Job 출력

기본 결과 저장 방식은 Job당 하나의 JSONL 파일이어야 합니다.

게시글 하나는 JSON 객체 한 줄로 append되어야 합니다.

체크포인트에서 재개한 Job은 기존 JSONL 파일에 이어 쓰지 않고 새 JSONL 파일을 생성해야 합니다.

로컬 환경에서는 Job JSONL 파일을 실행 위치 하위 output 경로에 저장해야 합니다.

컨테이너 환경에서는 Job JSONL 파일과 다운로드 미디어를 Garage 기반 S3 호환 객체 저장소에 저장해야 합니다.

SeaweedFS는 대량 미디어/소파일 저장, FUSE, Iceberg 요구가 생길 때 대체 저장소로 검토할 수 있어야 합니다.

### FR-020. Polars 가공 가능성

원본 JSONL은 Polars `read_ndjson`으로 읽을 수 있어야 합니다.

`content.blocks`, `comments`, `attachments`, `media`는 list-of-struct 형태로 저장해 `explode`와 `unnest`가 가능해야 합니다.

공통 분석 스키마 정규화 단계에서는 다음 테이블로 분리할 수 있어야 합니다.

- posts
- comments
- content_blocks
- media
- links
- failures

### FR-021. 중단점 저장

스크래퍼는 작업 상태와 체크포인트를 모든 커뮤니티 스크래퍼가 공유할 수 있는 공통 JSON 스키마로 저장해야 합니다.

스크래퍼는 다음 상황에서 체크포인트를 저장해야 합니다.

- Job 시작
- 게시글 10개 처리 완료마다
- 수동 중단
- 복구 불가능한 오류
- CAPTCHA 또는 차단 의심 응답
- 정상 완료

게시글 결과 저장이 성공한 후에만 체크포인트의 마지막 완료 위치를 갱신해야 합니다.

### FR-022. 재개 처리

로컬 환경에서는 `Checkpoint.json` 또는 checkpoint 저장소를 사용해 수집을 재개할 수 있어야 합니다.

컨테이너 환경에서는 `RESUME=true`, `JOB_ID=<checkpoint job_id>` 환경변수로 재개할 수 있어야 합니다.

공유 저장소 운영에서는 `JOB_ID` 명시 resume을 원칙으로 합니다.

### FR-023. CAPTCHA 및 차단 감지

CAPTCHA 또는 차단 의심 응답이 감지되면 스크래퍼는 다음을 수행해야 합니다.

- 현재 Job 즉시 중단
- `status="stopped"`로 변경
- 최종 체크포인트 저장
- 저장한 checkpoint `job_id`를 터미널과 로그에 출력
- CAPTCHA 자동 우회는 시도하지 않음

### FR-024. 요청 속도 조절

기본 요청 간격은 전역 1초여야 합니다.

터미널 옵션에서 전역 요청 간격을 변경할 수 있어야 합니다.

요청 지연은 다음 요청에 적용되어야 합니다.

- 게시판 목록
- 게시판 내 검색
- 통합 검색
- 게시글 상세
- 댓글
- 이미지/동영상 다운로드

### FR-025. User-Agent Mixer

실행 위치에 `user-agents.txt`가 있으면 스크래퍼는 이를 자동 사용해야 합니다.

파일이 없거나 유효한 항목이 없으면 기본 User-Agent를 사용해야 합니다.

기본 교체 주기는 요청 10회마다 1회입니다.

터미널 옵션으로 파일 경로와 교체 주기를 변경할 수 있어야 합니다.

컨테이너 이미지에는 `user-agents.txt`를 포함해야 합니다.

### FR-026. Proxy 설정

Proxy 설정은 실행 위치의 `.env` 파일로 저장해야 합니다.

FMKorea Proxy 환경변수:

- `FMKOREA_PROXY_HOST`
- `FMKOREA_PROXY_ID`
- `FMKOREA_PROXY_PW`

사용자가 터미널에서 Proxy 옵션을 켠 경우 해당 입력값을 최우선으로 사용해야 합니다.

사용자가 Proxy 옵션을 켜지 않았고 `.env`가 있으면 `.env`의 Proxy 변수를 자동 사용해야 합니다.

`.env`는 평문 저장 보안 예외로 허용하되 `.gitignore` 포함과 터미널 경고가 필수입니다.

### FR-027. 임시 Cookie 메모리 처리

사용자가 명시적으로 제공한 cookie 파일은 지원하지 않아야 합니다.

Cookie 처리 요구사항:

- 서버가 내려준 임시 cookie는 같은 `HttpClient` 생명주기 안에서만 메모리로 유지 가능
- User-Agent 교체 또는 `HttpClient` 종료 시 cookie jar reset
- Job 재시작, resume, Proxy 변경 이후 기존 cookie 재사용 금지
- checkpoint, output JSONL, report, failure record에 raw cookie 저장 금지
- 로그에 raw cookie 저장 금지

Cookie 처리는 CAPTCHA 우회, 자동 로그인, 비공개 콘텐츠 접근 자동화를 의미하지 않습니다.

### FR-028. Python 라이브러리 API

패키지는 최소한 다음을 노출해야 합니다.

- `search_board`
- `search_integrated`
- `fetch_post`
- `fetch_comments`
- `run_job`
- `resume_job`
- 설정 객체
- 결과 모델

패키지를 import하는 것만으로 스크래핑이 시작되면 안 됩니다.

### FR-029. 워커 컨테이너

1차 구현에는 워커 컨테이너 모드가 포함되어야 합니다.

컨테이너 환경에서는 체크포인트를 PostgreSQL에 저장해야 합니다.

컨테이너 환경에서는 Job JSONL 파일과 다운로드 미디어를 Garage 기반 S3 호환 객체 저장소에 저장해야 합니다.

컨테이너는 `RESUME`, `JOB_ID`, `DATABASE_URL`, S3 호환 접속 환경변수, `FMKOREA_` prefixed runtime env를 주입받을 수 있어야 합니다.

### FR-030. MCP 도구 인터페이스

1차 구현에는 핵심 스크래퍼 작업을 호출하는 MCP 도구가 포함되어야 합니다.

MCP 도구는 CLI와 워커 컨테이너가 사용하는 것과 동일한 core library 함수를 감싸야 합니다.

### FR-031. Parser-stage 실패 재처리

스크래퍼는 기존 `failures.jsonl`의 parser-stage 게시글 실패만 골라 direct-post 경로로 재수집할 수 있어야 합니다.

재처리 대상:

- `stage == "post"`
- 제목/작성자/게시글 식별자/metadata/content/comment 파싱 실패 계열

재처리 제외:

- CAPTCHA
- 차단
- 네트워크 오류
- 저장소 오류
- 체크포인트 오류
- 수동 중단

재처리 결과는 새 run에 `posts.jsonl`, `failures.jsonl`, `report.json`으로 기록해야 합니다.

### FR-032. AWS CDK IaC

DCinside-Scraper의 UOW-010 방향을 계승해 AWS CDK 기반 선택 배포 경로를 제공해야 합니다.

CDK는 다음을 구성해야 합니다.

- ECS Fargate one-shot worker task
- S3 output bucket
- RDS PostgreSQL checkpoint store
- CloudWatch Logs
- EventBridge 기반 실패 감지 또는 실행 트리거
- Secrets Manager 기반 secret injection

CDK는 중앙 Job Queue, 통합 운영 UI, Docker image build, EKS 배포를 포함하지 않습니다.

## 비기능 요구사항

### NFR-001. 유지보수성

핵심 스크래핑 로직은 CLI, 라이브러리 API, 워커 컨테이너, MCP 인터페이스가 공유해야 합니다.

CLI, 컨테이너, MCP 계층은 core library 위의 얇은 adapter여야 합니다.

FMKorea-specific 코드는 URL/query builder, pagination, parser, block detector, response classifier에 한정해야 합니다.

### NFR-002. 신뢰성

모든 외부 HTTP 및 파일 I/O 작업에는 명시적인 timeout과 오류 처리가 있어야 합니다.

실패한 게시글 fetch는 설정된 횟수까지 재시도해야 합니다.

CAPTCHA/차단 조건은 fail closed 방식으로 중단점 저장 후 중단해야 합니다.

### NFR-003. 성능

시스템은 게시글 상세 fetch를 비동기 멀티 워커로 처리해야 합니다.

링크 탐색은 Job당 단일 순차 워커로 처리해야 합니다.

차단 위험을 줄이기 위해 전역 요청 간격 기본값은 1초입니다.

### NFR-004. 보안

Security Baseline을 적용합니다.

적용 요구사항:

- secret, proxy password, cookie, token, raw credential을 로그에 남기지 않음
- `.env`, `user-agents.txt`, `Checkpoint.json`, 출력 파일, 다운로드 미디어, 로컬 인증정보를 `.gitignore`에 포함
- 평문 Proxy credential을 가져오거나 감지하면 터미널에 경고 출력
- CLI, 라이브러리, 워커, MCP 입력값에 명시적 validation 적용
- 의존성은 정확한 버전 또는 lock file로 관리
- 사용하지 않는 의존성은 추가하지 않음
- 안전한 JSON 파싱 및 직렬화만 사용
- 예상치 못한 실패의 사용자 표시 오류 메시지는 내부 정보를 노출하지 않음

문서화된 보안 예외:

- `.env`는 사용자가 직접 편집할 수 있도록 Proxy credential을 평문 저장할 수 있으며, `.gitignore` 보호와 터미널 경고가 필수입니다.
- 사용자 제공 cookie 파일은 지원하지 않으며 raw cookie는 저장/로그/checkpoint에서 제외합니다.

### NFR-005. 회복성

Resiliency Baseline을 적용합니다.

DCinside-Scraper의 resiliency 방향을 계승합니다.

초기 운영 목표:

- 로컬 실행과 단일 컨테이너 실행 지원
- AWS CDK는 단일 스크래퍼용 선택 배포 경로 제공
- 향후 통합 플랫폼에서 여러 커뮤니티 워커를 관리

상태 및 체크포인트 저장소:

- 로컬 환경: `Checkpoint.json`과 Job JSONL 파일
- 컨테이너 환경: PostgreSQL checkpoint, Garage 기반 S3 호환 output
- AWS 환경: RDS PostgreSQL checkpoint, S3 output

향후 SQS 기반 통합 플랫폼에서는 작업 lease 설정, 주기적 lease 갱신, lease 만료 시 `reason="lease_expired"` 중단 처리를 지원할 수 있어야 합니다.

### NFR-006. 테스트

테스트에는 다음이 포함되어야 합니다.

- fixture 기반 parser test
- Hypothesis 기반 property-based test
- import side-effect test
- model validation test
- URL/query builder test
- JobRunner/checkpoint test
- storage adapter contract test
- CLI/wizard validation test
- container/MCP adapter test
- 선택적 FMKorea live smoke test

Live smoke test는 선택적이어야 하며 일반 unit test 실행에 필수여서는 안 됩니다.

### NFR-007. Property-Based Testing

Property-Based Testing을 적용합니다.

Python 로직에는 Hypothesis를 사용해야 합니다.

PBT 대상:

- URL/query parsing 및 formatting round trip
- search result parser invariant
- post detail parser invariant
- content block order uniqueness
- JSON serialization/deserialization round trip
- `(site_id, board_id, document_srl)` dedupe idempotence
- checkpoint serialization round trip
- status/reason enum validation
- Polars-friendly content block shape invariant

### NFR-008. 관측성

스크래퍼는 structured logging을 사용해야 합니다.

로그에는 다음이 포함되어야 합니다.

- timestamp
- log level
- job ID
- run ID
- stage 또는 worker name
- message

로그에는 다음이 포함되면 안 됩니다.

- Proxy password
- raw cookie
- secret token
- authorization header
- 전체 credential file

## 데이터 요구사항

### DR-001. 게시글 JSONL 형태

JSONL의 각 줄은 수집된 게시글 하나를 나타내야 합니다.

필수 top-level 필드:

- `schema_version`
- `scrap_timestamp`
- `site_id`
- `board_id`
- `board_name`
- `document_srl`
- `url`
- `canonical_url`
- `category`
- `title`
- `author`
- `date`
- `views`
- `reactions`
- `comment_count`
- `content`
- `attachments`
- `media`
- `comments`
- `raw`

FMKorea 원본 JSONL 필수 top-level 필드에는 `is_repost`, `repost`를 포함하지 않습니다.

### DR-002. Content Block 형태

`content.blocks`는 list-of-struct 형태여야 합니다.

공통 필드:

- `order`
- `type`
- `url`
- `text`
- `provider`
- `metadata`

규칙:

- `order`는 게시글 내에서 중복되지 않아야 합니다.
- DOM 원문 순서를 보존해야 합니다.
- 타입별 특수 필드는 nullable field 또는 `metadata`로 보존해야 합니다.
- Polars `explode`와 `unnest`로 block table을 만들 수 있어야 합니다.

### DR-003. 댓글 형태

댓글은 게시글 JSONL 안에 중첩 저장할 수 있습니다.

공통 분석 스키마 정규화 단계에서는 댓글을 별도 table로 분리할 수 있어야 합니다.

필수 댓글 필드:

- `comment_srl`
- `parent_comment_srl`
- `depth`
- `is_best`
- `author`
- `date_raw`
- `date`
- `content`
- `reactions`

### DR-004. Failure Record 형태

실패 기록은 `failures.jsonl`에 저장해야 합니다.

필수 필드:

- `job_id`
- `run_id`
- `site_id`
- `board_id`
- `document_srl`
- `url`
- `stage`
- `reason`
- `error_message`
- `attempt`
- `created_at`
- `retryable`

민감정보는 저장하면 안 됩니다.

## 범위 제외

- CAPTCHA 우회
- 자동 로그인
- 계정 생성 자동화
- 삭제글 복구
- 1차 구현에서 GUI/Web UI
- 1차 구현에서 중앙 Job Queue/통합 운영 UI 구현
- Playwright 의존 스크래퍼 런타임
- FMKorea 원본 JSON 스키마의 `is_repost`, `repost` 필드

## 추적성

| 요구사항 영역 | 출처 |
|---|---|
| 전체 구조 계승 | Q1, Q3, Q11 |
| 프로젝트 식별자 | Q2 |
| 노키워드 범위 수집 | Q4 |
| 통합 검색/심층검색 종료 조건 | Q5 |
| 댓글/답글 수집 | Q6 |
| 본문 콘텐츠와 미디어 | Q7 |
| 재게시/공유/인용/펌 필드 제외 | Q8 |
| 임시 Cookie 메모리 처리 | Q9 |
| 저장소/인프라 계승 | Q10 |
| Security Baseline | Q12 |
| Resiliency Baseline | Q13 |
| Property-Based Testing | Q14 |
| FMKorea 사이트 구조 | `docs\FMKorea-Scraper_Function_Specification.md` |
| 공통 저장소/구조 | DCinside-Scraper docs and implementation baseline |

## 준수 요약

### Security Baseline

- **상태**: 요구사항 단계 기준 준수
- **메모**: 입력 검증, 민감정보 로그 제한, 의존성 pinning, `.gitignore` 보호, 평문 `.env` Proxy 예외, 임시 cookie 메모리 제한을 요구사항에 포함했습니다.

### Resiliency Baseline

- **상태**: 요구사항 단계 기준 준수
- **메모**: DCinside-Scraper의 로컬/컨테이너/AWS CDK resiliency 방향을 계승하고, checkpoint/resume, fail-closed, 저장소 분리, 향후 lease 기반 운영을 요구사항에 포함했습니다.

### Property-Based Testing

- **상태**: 요구사항 단계 기준 준수
- **메모**: Hypothesis를 선택했고, URL/query, parser, 직렬화, dedupe, checkpoint, Polars-friendly block shape에 대한 PBT 대상을 식별했습니다.
