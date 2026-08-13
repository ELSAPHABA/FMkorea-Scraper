# 페르소나

## 작성 기준

- 출처: `aidlc-docs/inception/requirements/requirements.md`
- 범위: FMKorea 공개 게시글/댓글 스크래퍼의 1차 구현
- 구성: CLI 사용자, Python 라이브러리 개발자, 워커 컨테이너 운영자, MCP 클라이언트, 유지보수자, Polars 데이터 검토자

## P-001. 터미널 수집 사용자

**설명**: 로컬 PC나 서버 터미널에서 게시글 URL, 게시판, 검색어, 수집 범위, 저장 옵션을 입력해 데이터를 수집하는 사용자입니다.

**목표**

- 게시글 URL 직접 입력, 게시판 검색, 통합 검색, 심층검색, 노키워드 범위 수집, 실시간 수집 중 필요한 방식으로 Job을 실행합니다.
- 댓글, 미디어 다운로드, Proxy, User-Agent, 요청 속도 옵션을 실행 전에 제어합니다.
- CAPTCHA나 차단이 발생하면 중단점을 저장하고 나중에 재개합니다.

**불편한 점**

- FMKorea의 `mid`, `document_srl`, `search.php` query를 직접 다루기 어렵습니다.
- 장시간 수집 중 중단되면 어디까지 저장됐는지 추적하기 어렵습니다.
- cookie, Proxy, User-Agent 설정이 잘못되면 차단이나 보안 문제가 생길 수 있습니다.

**관련 스토리**: US-001, US-002, US-003, US-004, US-005, US-006, US-012, US-013

## P-002. Python 라이브러리 개발자

**설명**: FMKorea 스크래퍼를 다른 Python 코드에서 import해 검색, 게시글 수집, 댓글 수집, Job 실행 기능을 직접 호출하려는 개발자입니다.

**목표**

- CLI 없이 core API로 검색과 수집 기능을 호출합니다.
- 결과 모델을 안정적인 JSON 구조로 직렬화합니다.
- import 시 네트워크 요청, 파일 생성, 터미널 prompt 같은 부작용이 발생하지 않게 합니다.

**불편한 점**

- CLI 전용 코드에 수집 로직이 묶이면 재사용과 테스트가 어렵습니다.
- 반환 스키마가 흔들리면 downstream 분석 코드와 MCP wrapper가 쉽게 깨집니다.

**관련 스토리**: US-007, US-008, US-009, US-010, US-014, US-015

## P-003. 워커 컨테이너 운영자

**설명**: 통합 커뮤니티 스크래핑 시스템 또는 단독 Docker 환경에서 FMKorea 전용 워커 컨테이너를 실행하고 관찰하는 운영자입니다.

**목표**

- 컨테이너가 단일 Job을 안정적으로 수행하고 JSONL, 실패 기록, checkpoint를 남깁니다.
- S3 호환 저장소와 PostgreSQL checkpoint 저장소를 공유 규약에 맞춰 사용합니다.
- structured logging으로 Job ID, run ID, stage, worker 상태를 확인합니다.

**불편한 점**

- 로컬 전용 상대 경로나 상태 파일이 컨테이너에서 깨질 수 있습니다.
- 로그에 Proxy 비밀번호, raw cookie, credential이 남으면 운영 위험이 커집니다.
- 여러 커뮤니티 스크래퍼가 같은 저장소를 공유할 때 namespace 충돌이 생길 수 있습니다.

**관련 스토리**: US-002, US-003, US-010, US-012, US-013, US-016, US-018

## P-004. MCP 클라이언트 사용자

**설명**: AI agent나 외부 자동화 도구에서 MCP tool 호출로 FMKorea 수집 기능을 사용하려는 사용자입니다.

**목표**

- 게시판 검색, 통합 검색, 게시글 fetch, 댓글 fetch, Job 실행, resume을 MCP tool로 호출합니다.
- CLI와 같은 core library 동작을 일관된 입력/출력 스키마로 사용합니다.
- 잘못된 입력은 명확한 validation 오류로 받습니다.

**불편한 점**

- MCP 계층이 별도 수집 로직을 가지면 CLI와 결과가 달라질 수 있습니다.
- 오류 메시지가 내부 stack trace나 secret을 노출하면 안 됩니다.

**관련 스토리**: US-015, US-017

## P-005. 유지보수자

**설명**: FMKorea URL/query, 검색 HTML, 게시글 DOM, 댓글 구조, 미디어 구조 변화에 맞춰 parser와 테스트를 유지하는 개발자입니다.

**목표**

- HTML fixture와 PBT로 parser 회귀를 빠르게 발견합니다.
- site-specific 코드를 URL/query builder, pagination, parser, response classifier에 한정합니다.
- DCinside에서 계승한 core runtime과 storage 구조를 불필요하게 다시 만들지 않습니다.

**불편한 점**

- 파싱 규칙이 문서와 테스트에 남지 않으면 구조 변경 때 원인을 찾기 어렵습니다.
- 스크래퍼 런타임에 브라우저 자동화 의존성이 들어오면 실행 환경과 테스트 비용이 커집니다.

**관련 스토리**: US-004, US-005, US-007, US-008, US-009, US-010, US-014, US-018

## P-006. Polars 데이터 검토자

**설명**: Job별 JSONL 결과를 Polars DataFrame으로 불러와 누락, 중복, 스키마 안정성, content block 구조, 댓글 분리 가능성을 검증하는 사용자입니다.

**목표**

- Job 하나의 결과가 JSONL 파일 하나에 게시글 단위로 append되어 저장됩니다.
- `content.blocks`, `comments`, `attachments`, `media`를 `explode`/`unnest`로 가공합니다.
- FMKorea 원본 JSON에는 `is_repost`/`repost`가 없고, 공통 정규화 단계에서만 기본값이 합성됨을 명확히 구분합니다.

**불편한 점**

- block type마다 필드가 너무 제각각이면 Polars에서 안정적으로 펼치기 어렵습니다.
- Job 간 결과가 한 파일에 섞이면 수집 조건별 검증이 어렵습니다.
- 원본 스키마와 공통 분석 스키마가 섞이면 정규화 로직이 불명확해집니다.

**관련 스토리**: US-010, US-011, US-014

## 페르소나-여정 매핑

| 여정 | 주요 페르소나 | 보조 페르소나 |
|---|---|---|
| 작업 설정과 실행 준비 | P-001 | P-003, P-005 |
| 검색 및 링크 수집 | P-001 | P-005, P-006 |
| 게시글 상세와 콘텐츠 수집 | P-002 | P-001, P-005 |
| 댓글과 미디어 수집 | P-002 | P-006, P-005 |
| 결과 저장과 Polars 검증 | P-006 | P-001, P-002 |
| 중단, 재개, 실패 재처리 | P-001 | P-003, P-005 |
| 라이브러리, 컨테이너, MCP, CDK 통합 | P-002 | P-003, P-004, P-005 |
