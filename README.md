# FMkorea-Scraper

에펨코리아 게시판, 검색 결과, 게시글, 댓글, 본문 콘텐츠를 수집하는 Python 스크래퍼입니다.

로컬 CLI 프로그램으로 단독 실행할 수 있고, 컨테이너 워커로 실행해 S3 호환 저장소와 PostgreSQL 체크포인트 저장소를 사용할 수 있습니다. AWS CDK 기반 ECS Fargate 배포 경로도 포함합니다. 핵심 기능은 라이브러리로 import 할 수 있으며, MCP 도구 서버로 연결할 수 있도록 어댑터도 포함합니다.

현재 구현은 BeautifulSoup 기반 HTML 파싱과 `httpx.AsyncClient` 기반 비동기 요청을 사용합니다. Playwright 같은 브라우저 자동화는 런타임 의존성이 아닙니다.

주의: 기본 수집은 게시글/댓글/콘텐츠 메타데이터와 미디어 URL 중심입니다. `--media-mode download`를 사용하면 수집 Job 안에서 이미지와 에펨코리아 동영상 `MediaItem` 파일까지 저장합니다.

## 주요 기능

- 게시글 직접 수집: 에펨코리아 게시글 URL을 하나 이상 입력해 본문과 댓글을 수집합니다.
- 게시판 목록 수집: 특정 게시판의 목록 페이지를 순회하고 게시글을 수집합니다.
- 게시판 내 키워드 검색 수집: 특정 게시판에서 키워드 검색 결과를 순회하고 게시글을 수집합니다.
- 통합 검색 수집: 에펨코리아 검색 페이지 결과를 수집합니다.
- 심층 검색 수집: 통합 검색으로 관련 게시판을 찾은 뒤, 게시판별 키워드 검색을 다시 수행해 더 넓은 범위를 수집합니다.
- 노키워드 범위 수집: 날짜/글번호 범위를 이용해 특정 게시판의 기간 또는 글번호 범위 게시글을 수집합니다.
- 실시간 수집: 환경 변수로 실시간 키워드 또는 실시간 전체 수집을 활성화하고, 실행 시간 또는 종료 시각으로 종료 조건을 지정합니다.
- 댓글 및 답글 수집: 댓글과 답글을 flat list로 저장하고, `depth`, `parent_comment_srl`, `parent_comment_id_raw`로 관계를 보존합니다.
- BEST 댓글 처리: BEST 댓글을 별도 배열로 분리하지 않고 `comments` 안에 저장하며, `is_best`, `badges`, `reactions`로 특징을 보존합니다.
- 본문 콘텐츠 블록 저장: 텍스트, 이미지, 에펨코리아 동영상, YouTube, X, 링크, 첨부파일, 알 수 없는 임베드를 순서 있는 `content.blocks`로 저장합니다.
- User-Agent 교체: `user-agents.txt` 파일을 읽고 기본 요청 10회마다 User-Agent를 교체합니다.
- Proxy 사용: CLI 옵션 또는 `.env` 파일의 프록시 설정을 사용합니다.
- 속도 조절: 요청 간격, 게시글 워커 수, 미디어 다운로드 동시성, 큐 크기, 댓글/본문 최대 수집량을 조절합니다.
- 중단 및 재개: 체크포인트를 저장하고 `resume` 명령으로 중단 지점부터 재개합니다.
- CAPTCHA/차단 감지: CAPTCHA 또는 차단 신호가 보이면 자동 우회를 시도하지 않고 작업을 중단하며 체크포인트를 남깁니다.
- 파서 실패 재처리: `failures.jsonl`에서 parser-stage 실패만 골라 direct-post 경로로 재수집합니다.
- 로컬/컨테이너 저장: 로컬 JSONL 파일 또는 컨테이너 환경의 S3 호환 저장소와 PostgreSQL을 사용할 수 있습니다.
- AWS CDK 배포: `infra/cdk`에서 ECS Fargate 워커, AWS S3 출력 bucket, RDS PostgreSQL 체크포인트 저장소를 정의합니다.
- Polars 가공 준비: JSONL 출력과 향후 공통 스키마 정규화 흐름을 전제로 합니다.

## 프로젝트 구성

```text
.
├── main.py                         # 로컬 개발용 CLI 진입점
├── pyproject.toml                  # 패키지 메타데이터, 의존성, console script
├── requirements.lock               # 기본 런타임 + test extra 고정 의존성
├── Dockerfile                      # 컨테이너 워커 이미지
├── .dockerignore                   # Docker build context 제외 규칙
├── docker-entrypoint.sh            # 컨테이너 시작 스크립트
├── README.md
├── docs/
│   └── FMKorea-Scraper_Function_Specification.md
├── infra/cdk/                      # AWS CDK 기반 Fargate/S3/RDS 인프라
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   ├── config/                     # dev/staging/prod 환경 설정
│   ├── stacks/                     # SharedInfraStack, WorkerStack
│   └── tests/                      # CDK template 테스트
├── aidlc-docs/                     # AI-DLC 산출 문서
├── src/fmkorea_scraper/
│   ├── adapters/                   # CLI, 컨테이너, MCP 어댑터
│   ├── collect/                    # 게시판/검색 URL 빌더, 검색 파서, 링크 수집기
│   ├── core/                       # 포트, 예외, 공통 유스케이스 경계
│   ├── http/                       # httpx 기반 요청 런타임, UA/Proxy/Rate 정책
│   ├── models/                     # Pydantic 데이터 모델
│   ├── outputs/                    # 로컬/S3/PostgreSQL 출력과 체크포인트
│   ├── parse/                      # 게시글/댓글/본문 파서와 서비스
│   ├── retry/                      # parser-stage 실패 재처리
│   └── runner/                     # JobRunner, 체크포인트, 출력 orchestration
└── tests/                          # 단위/계약/선택적 smoke 테스트
```

## 유닛 구성

이 프로젝트는 AI-DLC의 Unit of Work 단위로 구현됩니다. 각 유닛의 역할은 아래와 같습니다.

| UOW | 이름 | 역할 |
| --- | --- | --- |
| UOW-001 | Core Models and Config | Pydantic 모델, enum, 작업 설정, 저장 설정, 출력 스키마 정의 |
| UOW-002 | HTTP Runtime Policy | `httpx.AsyncClient`, 요청 간격, 재시도, User-Agent 교체, Proxy, CAPTCHA/차단 감지 |
| UOW-003 | Search and Link Collection | direct URL, 게시판 목록/검색, 통합 검색, 노키워드 범위 검색, 심층 검색, 실시간 후보 링크 수집 |
| UOW-004 | Post Detail and Content Parsing | 게시글 메타데이터, 본문 콘텐츠 블록, 댓글/답글, BEST 댓글, 미디어/첨부파일 파싱 |
| UOW-005 | Job Runner and Checkpoint | 단일 링크 수집 워커와 다중 게시글 워커, 큐, 중단/재개, 체크포인트 |
| UOW-006 | Output and Storage | 로컬 JSONL/리포트/실패 파일, 로컬 체크포인트, S3 호환 저장소, PostgreSQL 체크포인트 |
| UOW-007 | CLI Adapter | `run`, `resume`, User-Agent import, Proxy 설정, 터미널 마법사 |
| UOW-008 | Container, MCP, and Test Harness | 컨테이너 엔트리포인트, MCP 도구 핸들러, 선택적 통합 테스트 구조 |
| UOW-009 | Parser Failure Retry Reprocessor | 파싱 실패 게시글 실패 파일 선별, direct-post 재처리, 재처리 결과 리포트 |
| UOW-010 | AWS CDK Infrastructure IaC | AWS CDK 기반 배포 인프라 정의, 환경 분리, synth/deploy 문서화 |

## 설치

Python 3.11 이상이 필요합니다.

Windows PowerShell 예시:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

고정된 의존성으로 실행 환경을 맞추려면 `requirements.lock`을 사용할 수 있습니다.

```powershell
python -m pip install -r requirements.lock
python -m pip install -e .
```

선택 기능을 함께 설치하려면 extra를 붙입니다.

```powershell
# 테스트
python -m pip install -e ".[test]"

# S3 호환 저장소와 PostgreSQL 체크포인트
python -m pip install -e ".[s3,postgres]"

# MCP 서버
python -m pip install -e ".[mcp]"

# Polars 분석
python -m pip install -e ".[analysis]"

# 전부 설치
python -m pip install -e ".[test,s3,postgres,mcp,analysis]"
```

AWS CDK 인프라 작업은 별도 디렉터리에서 의존성을 설치합니다.

```powershell
cd infra\cdk
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

설치 후 아래 세 가지 방식으로 CLI를 실행할 수 있습니다.

```powershell
fmkorea-scraper --help
python -m fmkorea_scraper.adapters.cli --help
python main.py --help
```

`fmkorea-scraper`는 `pyproject.toml`에 등록된 console script입니다. 가상환경이 활성화되어 있으면 별도 Windows 환경 변수 등록 없이 사용할 수 있습니다.

## 빠른 시작

게시글 URL을 직접 수집:

```powershell
fmkorea-scraper run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295"
```

댓글 없이 게시글만 수집:

```powershell
fmkorea-scraper run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295" `
  --comment-mode none
```

출력 경로를 지정:

```powershell
fmkorea-scraper run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295" `
  --output-path ".\outputs"
```

중단된 작업 재개:

```powershell
fmkorea-scraper resume --job-id "job-20260809-001"
```

대화형 마법사 실행:

```powershell
fmkorea-scraper wizard
```

## CLI 명령

### `run`

새 스크래핑 작업을 실행합니다.

```powershell
fmkorea-scraper run --source <source> [source 옵션] [공통 옵션]
```

지원하는 `--source` 값:

| 값 | 의미 |
| --- | --- |
| `direct-post` | 게시글 URL을 직접 지정 |
| `board-list` | 특정 게시판 목록 페이지 수집 |
| `board-search` | 특정 게시판 내 키워드 검색 |
| `integrated-search` | 에펨코리아 통합 검색 |
| `deep-search` | 통합 검색으로 게시판을 찾은 뒤 게시판별 키워드 검색 |
| `no-keyword-range` | 키워드 없이 기간/글번호 범위로 게시판 수집 |

### `resume`

체크포인트를 읽어 중단된 작업을 재개합니다.

```powershell
fmkorea-scraper resume --job-id <job-id>
```

`--job-id`를 생략하면 로컬 체크포인트 저장소에서 최신 작업을 찾는 흐름을 사용합니다.

### `retry-parser-failures`

기존 `failures.jsonl`에서 parser-stage 실패만 골라 새 direct-post 재처리 작업으로 실행합니다.

```powershell
fmkorea-scraper retry-parser-failures `
  --failure-path ".\outputs\job-a\run-1\failures.jsonl"
```

이미 성공한 게시글을 제외하려면 성공 JSONL을 지정합니다.

```powershell
fmkorea-scraper retry-parser-failures `
  --failure-path ".\outputs\job-a\run-1\failures.jsonl" `
  --existing-success-path ".\outputs\job-b\run-2\posts.jsonl"
```

`--from-report`, `--from-checkpoint`는 기존 작업의 보고서나 체크포인트에서 재처리에 필요한 값을 복원할 때 사용합니다. 둘은 동시에 사용할 수 없습니다.

### `import-user-agents`

UTF-8 User-Agent 목록 파일을 현재 실행 위치의 `user-agents.txt`로 복사합니다.

```powershell
fmkorea-scraper import-user-agents ".\my-user-agents.txt"
```

파일은 한 줄에 하나의 User-Agent를 적습니다. 빈 파일은 거부됩니다.

### `configure-proxy`

프록시 정보를 현재 실행 위치의 `.env`에 평문으로 저장합니다.

```powershell
fmkorea-scraper configure-proxy `
  --host "http://proxy.example.com:8080" `
  --id "username" `
  --password "password"
```

`--id`, `--password`는 선택입니다. 비밀번호를 생략하면 터미널에서 입력받습니다.

### `wizard`

번호 선택 방식의 터미널 마법사를 실행합니다.

```powershell
fmkorea-scraper wizard
```

마법사는 source, 게시판 ID, 키워드, 범위, 출력 경로 같은 주요 옵션을 질문하고 내부적으로 `run`, `resume`, `retry-parser-failures` 또는 보조 명령을 실행합니다.

## Source별 사용법

### 1. 게시글 직접 수집

하나 이상의 게시글 URL을 반복해서 지정할 수 있습니다.

```powershell
fmkorea-scraper run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295" `
  --url "https://www.fmkorea.com/index.php?mid=best&document_srl=8984251370"
```

URL은 `fmkorea.com` 게시글 URL이어야 합니다. `/best/<document_srl>` 형태와 `index.php?mid=<board_id>&document_srl=<document_srl>` 형태를 모두 사용할 수 있습니다.

### 2. 게시판 목록 수집

```powershell
fmkorea-scraper run `
  --source board-list `
  --board-id "stock" `
  --page-start 1 `
  --page-end 3
```

주요 옵션:

| 옵션 | 설명 |
| --- | --- |
| `--board-id` | URL의 게시판 ID. 예: `stock`, `football_world`, `lol`, `best` |
| `--category-id` | 게시판 category 값이 필요할 때 지정 |
| `--page-start` | 시작 페이지. 기본값 `1` |
| `--page-end` | 종료 페이지. 생략하면 수집기가 다음 페이지 존재 여부에 따라 진행 |
| `--date-from`, `--date-to` | 작성일 범위 필터. `YYYY-MM-DD` |
| `--min-document-srl`, `--max-document-srl` | 글번호 범위 필터 |

검색/목록 단계에서 얻은 제목이나 날짜는 후보 필터링과 진단용 힌트입니다. category, 제목, 작성자, 작성일, 조회수, 추천수 같은 최종 저장 메타데이터는 게시글 상세 페이지를 열어 다시 파싱합니다.

### 3. 게시판 내 키워드 검색

```powershell
fmkorea-scraper run `
  --source board-search `
  --board-id "stock" `
  --keyword "삼전" `
  --search-target "title_content" `
  --page-start 1 `
  --page-end 5
```

주요 옵션:

| 옵션 | 설명 |
| --- | --- |
| `--board-id` | 검색할 게시판 ID |
| `--keyword` | 검색어 |
| `--search-target` | 검색 대상. 기본값 `title_content` |
| `--category-id` | 특정 category 안에서 검색할 때 지정 |
| `--page-start`, `--page-end` | 검색 결과 페이지 범위 |

### 4. 통합 검색

```powershell
fmkorea-scraper run `
  --source integrated-search `
  --keyword "삼전" `
  --search-target "title_content" `
  --page-start 1 `
  --page-end 10
```

옵션:

| 옵션 | 설명 |
| --- | --- |
| `--keyword` | 통합 검색어 |
| `--search-target` | 검색 대상. 기본값 `title_content` |
| `--page-start` | 시작 페이지 |
| `--page-end` | 종료 페이지 |
| `--date-from`, `--date-to` | 작성일 범위 필터 |
| `--min-document-srl`, `--max-document-srl` | 글번호 범위 필터 |

### 5. 심층 검색

통합 검색으로 검색 결과가 있는 게시판을 먼저 찾고, 발견한 게시판별로 다시 게시판 내 키워드 검색을 수행합니다.

```powershell
fmkorea-scraper run `
  --source deep-search `
  --keyword "삼전" `
  --search-target "title_content" `
  --seed-page-limit 20 `
  --date-from "2026-08-01" `
  --date-to "2026-08-14"
```

심층 검색은 반드시 날짜 또는 글번호 범위 중 하나 이상이 필요합니다. 범위가 없으면 너무 넓은 검색이 되기 때문입니다.

게시판 후보를 직접 제한할 수도 있습니다.

```powershell
fmkorea-scraper run `
  --source deep-search `
  --keyword "삼전" `
  --board-candidate "stock" `
  --board-candidate "coin" `
  --date-from "2026-08-01" `
  --date-to "2026-08-14"
```

### 6. 노키워드 범위 수집

특정 게시판에서 키워드 없이 기간 또는 글번호 범위를 기준으로 게시글을 수집합니다.

```powershell
fmkorea-scraper run `
  --source no-keyword-range `
  --board-id "stock" `
  --date-from "2026-08-01" `
  --date-to "2026-08-14"
```

날짜 범위 대신 글번호 범위를 사용할 수 있습니다.

```powershell
fmkorea-scraper run `
  --source no-keyword-range `
  --board-id "stock" `
  --min-document-srl 10190000000 `
  --max-document-srl 10200000000
```

이 모드는 `deep-search`와 마찬가지로 날짜 또는 글번호 범위가 하나 이상 필요합니다.

## 실시간 수집

실시간 수집은 `--source`로 직접 선택하지 않고 환경 변수로 활성화합니다.

공통 환경 변수:

| 환경 변수 | 설명 |
| --- | --- |
| `FMKOREA_REALTIME_ENABLED` | `true`이면 실시간 수집 활성화 |
| `FMKOREA_REALTIME_MODE` | `keyword` 또는 `all` |
| `FMKOREA_REALTIME_KEYWORD` | 키워드 모드 검색어 |
| `FMKOREA_REALTIME_DURATION_SECONDS` | 실행 시간, 초 단위 |
| `FMKOREA_REALTIME_END_AT` | 종료 시각. ISO datetime 문자열 |
| `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS` | 폴링 간격. 기본값 `30`초 |

종료 조건은 `FMKOREA_REALTIME_DURATION_SECONDS`와 `FMKOREA_REALTIME_END_AT` 중 정확히 하나만 설정해야 합니다. 둘 다 설정하거나 둘 다 생략하면 설정 오류입니다.

실시간 키워드 수집:

```powershell
$env:FMKOREA_REALTIME_ENABLED = "true"
$env:FMKOREA_REALTIME_MODE = "keyword"
$env:FMKOREA_REALTIME_KEYWORD = "삼전"
$env:FMKOREA_REALTIME_DURATION_SECONDS = "3600"

fmkorea-scraper run --job-id "realtime-keyword-001"
```

특정 게시판에서 실시간 키워드 수집:

```powershell
$env:FMKOREA_REALTIME_ENABLED = "true"
$env:FMKOREA_REALTIME_MODE = "keyword"
$env:FMKOREA_REALTIME_KEYWORD = "삼전"
$env:FMKOREA_REALTIME_DURATION_SECONDS = "3600"

fmkorea-scraper run `
  --job-id "realtime-board-keyword-001" `
  --board-id "stock"
```

실시간 전체 수집:

```powershell
$env:FMKOREA_REALTIME_ENABLED = "true"
$env:FMKOREA_REALTIME_MODE = "all"
$env:FMKOREA_REALTIME_DURATION_SECONDS = "3600"

fmkorea-scraper run `
  --job-id "realtime-all-001" `
  --board-id "stock"
```

## 공통 실행 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--job-id` | 자동 생성 | 작업 ID. 출력 경로와 체크포인트 키에 사용됩니다. |
| `--output-path` | 현재 실행 위치 | 로컬 출력 기본 경로. 실제 run 출력은 `<output-path>/outputs/<job_id>/<run_id>/` 아래에 생성됩니다. |
| `--comment-mode` | `all` | 댓글 수집 정책. `none`, `all`, `best_only` |
| `--media-mode` | `url_only` | 미디어 처리 정책. `url_only` 또는 `download` |
| `--include-attachments` | 기본 포함 | 첨부파일 메타데이터 포함 |
| `--no-attachments` | - | 첨부파일 메타데이터 제외 |
| `--request-interval-seconds` | `1.0` | 요청 간 최소 대기 시간 |
| `--max-post-retries` | `3` | 게시글 요청/처리 재시도 횟수 |
| `--post-worker-count` | `1` | 게시글 상세 수집 워커 수 |
| `--media-worker-count` | `1` | `--media-mode download`일 때 미디어 다운로드 동시성 상한 |
| `--queue-max-size` | 제한 없음 | 링크 수집기와 게시글 워커 사이의 큐 최대 크기 |
| `--timeout-seconds` | `30.0` | HTTP connect/read/write/pool timeout |
| `--max-comment-pages` | 제한 없음 | 게시글당 댓글 최대 페이지 수 |
| `--max-comments` | 제한 없음 | 게시글당 댓글 최대 개수 |
| `--max-content-blocks` | 제한 없음 | 게시글당 본문 content block 최대 개수 |
| `--user-agent-file` | `user-agents.txt` 자동 탐색 | User-Agent 목록 파일 |
| `--user-agent-rotate-every` | `10` | 요청 몇 회마다 User-Agent를 교체할지 |
| `--proxy-host` | `.env` 자동 탐색 | 요청에 사용할 프록시 host |
| `--proxy-id` | `.env` 자동 탐색 | 프록시 사용자 ID |
| `--proxy-pw` | `.env` 자동 탐색 | 프록시 비밀번호 |

## User-Agent 설정

User-Agent 파일은 UTF-8 텍스트 파일이며 한 줄에 하나씩 User-Agent를 적습니다.

```text
Mozilla/5.0 ...
Mozilla/5.0 ...
```

사용 순서:

1. `--user-agent-file`을 지정하면 해당 파일을 사용합니다.
2. 지정하지 않았고 실행 위치에 `user-agents.txt`가 있으면 자동 사용합니다.
3. 파일이 없으면 기본 HTTP 클라이언트 설정을 사용합니다.

기본 교체 주기는 요청 10회마다 1회입니다.

```powershell
fmkorea-scraper run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295" `
  --user-agent-file ".\user-agents.txt" `
  --user-agent-rotate-every 10
```

기존 파일을 프로젝트 실행 위치의 `user-agents.txt`로 가져오기:

```powershell
fmkorea-scraper import-user-agents ".\downloaded-user-agents.txt"
```

## Proxy 설정

Proxy 사용 우선순위:

1. 실행 옵션으로 `--proxy-host`를 지정하면 해당 값을 우선 사용합니다.
2. 실행 위치에 `.env`가 있고 `FMKOREA_PROXY_HOST`가 있으면 자동 사용합니다.
3. 둘 다 없으면 프록시 없이 요청합니다.

`.env` 키:

```dotenv
FMKOREA_PROXY_HOST=http://proxy.example.com:8080
FMKOREA_PROXY_ID=username
FMKOREA_PROXY_PW=password
```

CLI로 `.env` 생성 또는 갱신:

```powershell
fmkorea-scraper configure-proxy `
  --host "http://proxy.example.com:8080" `
  --id "username" `
  --password "password"
```

`.env`는 유저가 직접 편집할 수 있도록 평문으로 저장됩니다. 저장소에 커밋하지 마세요.

## 요청 속도와 워커

기본 구조는 링크 수집기 1개와 게시글 상세 수집 워커 N개입니다.

```text
검색/목록 수집기 1개
  -> PostCandidate 큐
  -> 게시글 상세 워커 N개
  -> JSONL/실패/체크포인트 저장
```

예시:

```powershell
fmkorea-scraper run `
  --source board-search `
  --board-id "stock" `
  --keyword "삼전" `
  --request-interval-seconds 2.0 `
  --post-worker-count 3 `
  --queue-max-size 100
```

운영 권장값:

- 처음 실행할 때는 `--post-worker-count 1`과 기본 요청 간격 `1.0`초로 시작하세요.
- 미디어 파일 저장을 켤 때는 `--media-mode download --media-worker-count 1`로 시작한 뒤 차단/부하 상황을 보고 늘리세요.
- CAPTCHA나 차단이 자주 발생하면 워커 수를 줄이고 `--request-interval-seconds`를 늘리세요.
- 큐는 게시글 링크 단위로 들어갑니다. Job 하나가 큐에 들어가는 것이 아니라, Job 안에서 발견한 게시글 후보 링크들이 큐에 쌓이고 워커가 하나씩 처리합니다.

## 출력 파일

로컬 실행 기본 출력 구조:

```text
<output-path>/
├── Checkpoint.json
└── outputs/
    └── <job_id>/
        └── <run_id>/
            ├── posts.jsonl
            ├── failures.jsonl
            ├── report.json
            └── media/
```

`--output-path`를 생략하면 현재 실행 위치가 기준 경로입니다.

파일 설명:

| 파일 | 설명 |
| --- | --- |
| `posts.jsonl` | 게시글 단위 JSON 객체를 한 줄씩 append |
| `failures.jsonl` | 게시글별 실패 기록 |
| `report.json` | 작업 결과 요약 |
| `media/` | `--media-mode download`일 때 미디어 파일 저장 위치 |
| `Checkpoint.json` | 작업 재개를 위한 체크포인트 |

JSONL은 한 줄이 하나의 게시글입니다. Polars로 읽을 때는 아래처럼 사용할 수 있습니다.

```python
import polars as pl

posts = pl.read_ndjson("outputs/job-1/run-1/posts.jsonl")
```

## 게시글 JSON 구조

게시글 출력의 최상위 모델은 `fmkorea.post.v1`입니다.

주요 필드:

| 필드 | 설명 |
| --- | --- |
| `schema_version` | 현재 `fmkorea.post.v1` |
| `scraped_at` | 수집 시각 |
| `site_id` | `fmkorea` |
| `board_id` | 게시판 ID |
| `board_name` | 게시판 이름 |
| `document_srl` | 숫자 게시글 ID |
| `document_id_raw` | 원본 게시글 ID 문자열 |
| `canonical_url` | 정규화된 게시글 URL |
| `category` | category ID, 이름, URL |
| `title` | 게시글 제목 |
| `author` | 작성자 정보 |
| `created_at` | 작성일 |
| `created_at_raw` | 원본 작성일 문자열 |
| `views` | 조회수 |
| `reactions` | 추천/비추천/점수 정보 |
| `comment_count` | 댓글 수 |
| `content` | 본문 텍스트와 순서 있는 본문 블록 |
| `attachments` | 첨부파일 목록 |
| `media` | 수집 또는 다운로드 대상 미디어 목록 |
| `comments` | 댓글과 답글 목록 |

`content.blocks` 타입:

| 타입 | 설명 |
| --- | --- |
| `text` | 일반 본문 텍스트 |
| `image` | 이미지 URL, 원본 URL, alt, 크기, 파일 식별자, 저장 경로 또는 object key |
| `fmk_video` | 에펨코리아 동영상 URL, poster, 설명, 길이, 파일 식별자, 저장 경로 또는 object key |
| `youtube` | YouTube URL, video ID, embed URL, 제목, 시작 초 |
| `x` | X/Twitter URL, 사용자명, status/tweet ID, embed URL, 텍스트 |
| `link` | 일반 링크 URL, 텍스트, 제목 |
| `attachment` | 첨부파일 메타데이터 |
| `unknown_embed` | 아직 분류하지 못한 임베드 |

`content.text`에는 본문 일반 텍스트를 저장하고, `content.blocks`에는 원문 순서를 보존한 블록들을 저장합니다.

댓글은 중첩 객체가 아니라 flat list입니다.

| 댓글 필드 | 설명 |
| --- | --- |
| `comment_srl` | 숫자 댓글 ID |
| `comment_id_raw` | 원본 댓글 ID 문자열 |
| `source_dom_id` | HTML DOM ID |
| `source_order` | 원본 댓글 배열 내 순서 |
| `parent_comment_srl` | 답글이면 부모 댓글 ID |
| `parent_comment_id_raw` | 답글이면 부모 댓글 원본 ID 문자열 |
| `depth` | 루트 댓글 `0`, 답글 `1` 이상 |
| `is_best` | BEST 댓글 여부 |
| `badges` | `BEST` 같은 댓글 배지 |
| `author` | 댓글 작성자 정보 |
| `created_at` | 댓글 작성 시각 |
| `created_at_raw` | 원본 댓글 작성일 문자열 |
| `content` | 댓글 본문 |
| `reactions` | 댓글 추천/비추천/점수 정보 |
| `permalink` | 댓글 permalink |

BEST 댓글도 같은 `comments` 배열에 저장합니다. 분석 단계에서는 `is_best=true` 또는 `badges`에 `BEST`가 있는 행으로 필터링하면 됩니다.

## 실패와 중단 처리

작업은 아래 상황에서 중단되거나 실패 기록을 남깁니다.

- CAPTCHA 감지
- 차단 페이지 또는 비정상 응답 감지
- 저장소 쓰기 실패
- 체크포인트 저장 실패
- 게시글 단위 파싱 실패
- 사용자의 Ctrl+C 또는 종료 신호

CAPTCHA는 자동 우회하지 않습니다. 감지되면 작업을 중단하고 체크포인트를 저장하는 것이 기본 정책입니다.

게시글 하나의 파싱 실패는 가능한 경우 `failures.jsonl`에 기록하고 다음 게시글로 진행합니다. 작업 전체 중단이 필요한 오류는 `report.json`과 체크포인트에 반영됩니다.

파싱 실패한 게시글만 별도로 재시도하려면 `retry-parser-failures`를 사용합니다. 원본 `failures.jsonl`은 수정하지 않고, 재시도 결과는 새 run의 `posts.jsonl`, `failures.jsonl`, `report.json`으로 저장됩니다.

```powershell
fmkorea-scraper retry-parser-failures `
  --failure-path ".\outputs\job-a\run-1\failures.jsonl" `
  --existing-success-path ".\outputs\job-b\run-2\posts.jsonl"
```

복원 보조 옵션:

| 옵션 | 설명 |
| --- | --- |
| `--from-report` | 기존 `report.json`에서 재처리 기본값 복원 |
| `--from-checkpoint` | 기존 `Checkpoint.json`에서 재처리 기본값 복원 |
| `--retry-job-id` | 재처리 작업 ID 지정 |
| `--stage` | 재처리 대상 stage allowlist. 기본값 `post` |
| `--no-skip-existing-success` | 기존 성공 게시글도 다시 시도 |

## 컨테이너 실행

컨테이너는 로컬 파일 저장 대신 S3 호환 저장소와 PostgreSQL 체크포인트 저장소를 사용하는 워커 모드입니다. S3 호환 저장소는 Garage를 우선 대상으로 두고, 향후 SeaweedFS로 확장할 수 있는 구조를 전제로 합니다.

이미지 빌드:

```powershell
docker build -t fmkorea-scraper-worker .
```

필수 환경 변수:

| 환경 변수 | 설명 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL DSN |
| `S3_ENDPOINT_URL` | Garage/S3 호환 endpoint |
| `S3_BUCKET` | 저장 bucket |
| `S3_ACCESS_KEY_ID` | S3 access key |
| `S3_SECRET_ACCESS_KEY` | S3 secret key |

선택 환경 변수:

| 환경 변수 | 설명 |
| --- | --- |
| `S3_REGION` | S3 region |
| `S3_PREFIX` | object key prefix |
| `S3_FORCE_PATH_STYLE` | path style 강제 여부 |
| `RESUME` | `true`이면 resume 모드 |
| `JOB_ID` | resume 또는 작업 ID 지정 |
| `FMKOREA_USER_AGENT_FILE` | 컨테이너 내부 User-Agent 파일 경로 |
| `FMKOREA_USER_AGENT_ROTATE_EVERY` | User-Agent 교체 주기 |
| `FMKOREA_PROXY_HOST` | Proxy host |
| `FMKOREA_PROXY_ID` | Proxy ID |
| `FMKOREA_PROXY_PW` | Proxy password |
| `FMKOREA_REALTIME_*` | 실시간 수집 설정 |

예시 `.env.container`:

```dotenv
DATABASE_URL=postgresql://scraper:password@postgres:5432/scraper
S3_ENDPOINT_URL=http://garage:3900
S3_BUCKET=fmkorea-scraper
S3_ACCESS_KEY_ID=access-key
S3_SECRET_ACCESS_KEY=secret-key
S3_REGION=garage
S3_FORCE_PATH_STYLE=true
S3_PREFIX=outputs/dev/fmkorea
```

컨테이너 실행:

```powershell
docker run --rm `
  --env-file .\.env.container `
  fmkorea-scraper-worker `
  run `
  --source direct-post `
  --url "https://www.fmkorea.com/best/10195585295"
```

컨테이너 resume:

```powershell
docker run --rm `
  --env-file .\.env.container `
  -e RESUME=true `
  -e JOB_ID=job-20260809-001 `
  fmkorea-scraper-worker
```

컨테이너에서 local failure 파일을 재시도할 때는 host output을 read-only로 mount한 뒤 컨테이너 내부 경로를 입력합니다.

```powershell
docker run --rm `
  --env-file .\.env.container `
  -v D:\scraper-outputs:/inputs:ro `
  fmkorea-scraper-worker `
  retry-parser-failures `
  --failure-path /inputs/job-a/run-1/failures.jsonl
```

저장소 컨테이너와 스크래퍼 컨테이너는 반드시 하나의 Docker Compose 파일에 강하게 묶을 필요가 없습니다. 향후 여러 커뮤니티 스크래퍼를 함께 운영할 계획이라면 Garage/PostgreSQL은 공유 인프라로 별도 운영하고, 각 스크래퍼 워커는 환경 변수로 접속 정보를 주입하는 구성이 더 적합합니다.

## AWS CDK 배포

AWS 배포 코드는 `infra/cdk`에 있습니다. CDK는 워커 이미지를 빌드하지 않고, 이미 ECR 또는 외부 registry에 push된 image URI/tag를 참조합니다.

구성 범위:

- `SharedInfraStack`: VPC, AWS S3 output bucket, RDS PostgreSQL, ECS cluster
- `WorkerStack`: ECS Fargate task definition, task/execution role, worker security group, CloudWatch log group, EventBridge 실패 감지 rule, CloudWatch alarm, 선택적 schedule

환경별 설정 파일:

```text
infra/cdk/config/dev.yaml
infra/cdk/config/staging.yaml
infra/cdk/config/prod.yaml
```

배포 전 최소 수정 항목:

- `account`, `region`
- worker `image_uri`, `image_tag`
- `DATABASE_URL`을 주입할 Secrets Manager secret 이름 또는 ARN
- worker 환경 변수와 schedule 사용 여부

검증:

```powershell
cd infra\cdk
.\.venv\Scripts\python.exe -m pytest tests -q
cdk synth -c env=dev
```

실제 배포:

```powershell
cd infra\cdk
cdk deploy -c env=dev -c use_config_account=true
```

기본 `cdk synth -c env=dev`는 account-agnostic template 생성을 목표로 합니다. 실제 AWS 계정에 배포할 때만 `-c use_config_account=true`를 붙입니다.

CDK가 포함하지 않는 범위:

- Docker image build/push
- 중앙 Job Queue 또는 SQS 소비 구조
- 통합 운영 UI
- EKS 배포
- 커뮤니티별 API query/parser

## MCP 사용

MCP extra 설치:

```powershell
python -m pip install -e ".[mcp]"
```

MCP 서버 실행:

```powershell
python -m fmkorea_scraper.adapters.mcp
```

MCP 도구 핸들러는 아래 기능을 제공합니다.

| 도구 | 설명 |
| --- | --- |
| `search_board` | 게시판 검색/목록 페이지 파싱 |
| `search_integrated` | 통합 검색 페이지 파싱 |
| `fetch_post` | 게시글 상세 수집 |
| `fetch_comments` | 댓글 수집 |
| `run_job` | 작업 실행 |
| `resume_job` | 작업 재개 |
| `retry_parser_failures` | parser-stage 실패 재처리 |

응답은 성공 시 `{"ok": true, "data": ...}` 형태이고, 실패 시 오류 정보를 포함합니다.

## 라이브러리로 사용

설치 후 Python 코드에서 핵심 API를 import 할 수 있습니다.

게시판 검색 API 예시:

```python
import anyio

from fmkorea_scraper.core.api import search_board
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig
from fmkorea_scraper.models.job import BoardSearchRequest


async def main() -> None:
    async with HttpClient(HttpRuntimeConfig()) as http_client:
        page = await search_board(
            BoardSearchRequest(
                board_id="stock",
                keyword="삼전",
                search_target="title_content",
                page=1,
            ),
            http_client,
        )
        print(page.candidates)


anyio.run(main)
```

게시글 상세 수집 API 예시:

```python
import anyio

from fmkorea_scraper.core.api import fetch_post
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig
from fmkorea_scraper.models.job import PostRequest


async def main() -> None:
    async with HttpClient(HttpRuntimeConfig()) as http_client:
        post = await fetch_post(
            PostRequest(
                url="https://www.fmkorea.com/best/10195585295",
            ),
            http_client,
        )
        print(post.model_dump())


anyio.run(main)
```

라이브러리 사용 시에도 HTTP 클라이언트는 호출자가 주입합니다. 이렇게 해야 테스트, 프록시, User-Agent, 쿠키 정책, 저장소 정책을 실행 환경별로 분리할 수 있습니다.

## 데이터 가공과 정규화 방향

현재 저장은 에펨코리아 개별 JSON 스키마인 `fmkorea.post.v1` JSONL입니다. 향후 통합 커뮤니티 전략분석 플랫폼에서는 아래 흐름을 권장합니다.

1. 커뮤니티별 개별 JSON 스키마로 원본을 보존합니다.
2. Polars로 JSONL을 읽습니다.
3. 개별 스키마를 공통 스키마로 정규화합니다.
4. 게시글과 댓글을 별도 테이블로 분리합니다.
5. 이미지, 동영상, YouTube, X, 링크, 첨부파일 같은 콘텐츠 블록은 별도 content/media 테이블로 펼칩니다.

댓글은 수집 JSON 안에서는 게시글 하위에 들어가지만, 분석 단계에서는 `site_id`, `board_id`, `document_srl`, `comment_srl` 또는 정규화된 공통 키를 기준으로 게시글 테이블과 댓글 테이블을 분리하는 것을 전제로 합니다.

BEST 댓글 여부와 추천/비추천 수는 정규화 후에도 `is_best`, `badges`, `reaction_up`, `reaction_down`, `reaction_score` 컬럼으로 보존하는 것을 권장합니다.

## 테스트

테스트 extra 설치:

```powershell
python -m pip install -e ".[test]"
```

전체 테스트:

```powershell
python -m pytest -q
```

CDK template 테스트:

```powershell
cd infra\cdk
.\.venv\Scripts\python.exe -m pytest tests -q
cdk synth -c env=dev
```

선택적 smoke 테스트 marker:

| marker | 설명 |
| --- | --- |
| `live` | 실제 네트워크 요청 테스트 |
| `live_smoke` | 실제 HTTP smoke 테스트 |
| `docker` | Docker 이미지/컨테이너 smoke 테스트 |
| `garage` | Garage 또는 S3 호환 저장소 smoke 테스트 |
| `s3_smoke` | S3 호환 object storage smoke 테스트 |
| `postgres` | PostgreSQL 체크포인트 smoke 테스트 |
| `mcp` | MCP 서버/핸들러 smoke 테스트 |
| `polars_smoke` | Polars JSONL 읽기 smoke 테스트 |
| `benchmark_smoke` | 모델 검증/직렬화 간단 성능 smoke 테스트 |

예시:

```powershell
python -m pytest -q -m "not live and not live_smoke and not docker and not garage and not s3_smoke and not postgres and not mcp and not polars_smoke and not benchmark_smoke"
```

## 운영 주의사항

- 에펨코리아의 이용약관과 관련 법령을 준수하세요.
- 과도한 요청은 서비스에 부담을 줄 수 있고 차단될 수 있습니다.
- CAPTCHA 자동 우회 기능은 제공하지 않습니다.
- 사용자 cookie 파일 경로 입력 옵션은 제공하지 않습니다. 필요한 요청에 한해 같은 HTTP 클라이언트 생명주기 안에서 서버가 준 임시 cookie를 자연스럽게 사용할 수 있습니다.
- 프록시 비밀번호, S3 secret, DB 비밀번호가 들어간 `.env` 파일은 커밋하지 마세요.
- User-Agent 교체와 Proxy는 차단 회피를 보장하지 않습니다. 안정적인 수집을 위해 요청 간격과 워커 수를 보수적으로 설정하세요.

## 관련 문서

- 기능 명세서: `docs/FMKorea-Scraper_Function_Specification.md`
- AWS CDK 인프라: `infra/cdk/`
- AI-DLC 산출물: `aidlc-docs/`
- UOW 공개 계약 문서: `aidlc-docs/construction/*/code/public-contracts.md`
