# 유저 스토리

## 작성 기준

- 구성 방식: 사용자 여정 기반
- 세분화 수준: 에픽 아래 중간 크기 스토리
- 범위: 1차 구현 중심, 향후 확장은 마지막 섹션에만 기록
- 인수조건 형식: 기본 체크리스트, 위험한 워크플로는 Given/When/Then 추가
- 테스트 반영: fixture test, Hypothesis PBT, 선택적 live smoke, Polars read 검증 메모 포함

## 공통 원칙

- 모든 스토리는 공개 콘텐츠 수집만 다룹니다.
- CAPTCHA 우회, 자동 로그인, 계정 생성 자동화, 삭제글 복구는 제외합니다.
- 사용자 제공 cookie 파일은 지원하지 않습니다. 서버가 내려준 임시 cookie는 현재 `HttpClient` 생명주기 안에서만 메모리로 유지하고, raw cookie는 로그, output, checkpoint, report, failure record에 저장하지 않습니다.
- 런타임 스크래핑은 `httpx`, `asyncio`, Scrapling `Selector`, 표준 `json` 기반이며, 목록/검색/상세 필수 DOM 누락 시에만 일반 Playwright fallback을 사용합니다.
- Playwright 또는 브라우저 자동화는 조사 도구로만 사용할 수 있으며, 스크래퍼 런타임 의존성으로 포함하지 않습니다.
- CLI, 라이브러리, 워커 컨테이너, MCP는 같은 core library 함수를 공유합니다.
- FMKorea 원본 JSON 스키마에는 `is_repost`, `repost` 필드를 저장하지 않습니다.

## 에픽 1. 작업 설정과 실행 준비

### US-001. CLI와 터미널 마법사에서 수집 Job을 생성한다

**페르소나**: P-001 터미널 수집 사용자

**User Story**: 터미널 수집 사용자로서, direct-post, board-search, integrated-search, deep-search, no-keyword-range, realtime 수집 중 하나를 선택해 Job을 만들고 싶다. 그래서 같은 도구로 FMKorea의 여러 수집 방식을 실행할 수 있다.

**요구사항 추적**: FR-001, FR-002, FR-004

**인수조건**

- [ ] CLI는 `fmkorea-scraper` console script로 실행할 수 있다.
- [ ] Python module 실행 경로는 `python -m fmkorea_scraper.adapters.cli`를 지원한다.
- [ ] 터미널 마법사는 같은 core Job config를 생성한다.
- [ ] CLI는 게시글 URL, 게시판 ID, 검색어, 날짜 범위, 글번호 범위, 댓글 옵션, 미디어 옵션을 validation한다.
- [ ] `site_id=fmkorea`와 `FMKOREA_` 환경변수 prefix를 사용한다.
- [ ] import만으로 CLI prompt, 네트워크 요청, 파일 생성이 발생하지 않는다.

**검증 메모**

- CLI argument/config validation 단위 테스트로 검증한다.
- import side-effect 테스트를 둔다.

### US-002. User-Agent, Proxy, 임시 cookie를 안전하게 적용한다

**페르소나**: P-001 터미널 수집 사용자, P-003 워커 컨테이너 운영자

**User Story**: 터미널 수집 사용자로서, User-Agent와 Proxy를 명시적으로 설정하고 싶다. 그래서 차단 위험과 공개 페이지 접근 조건을 제어하면서도 민감정보와 임시 cookie를 결과에 남기지 않을 수 있다.

**요구사항 추적**: FR-003, FR-025, FR-026, FR-027, NFR-004

**인수조건**

- [ ] `user-agents.txt`가 있으면 한 줄당 User-Agent 하나로 읽고 빈 줄은 무시한다.
- [ ] 기본 User-Agent 교체 주기는 요청 10회마다 1회다.
- [ ] Proxy는 `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW`를 사용한다.
- [ ] 사용자가 Proxy 옵션을 켠 경우 명시 입력값을 최우선으로 적용한다.
- [ ] Proxy 옵션이 없고 `.env`가 있으면 `.env`의 FMKorea Proxy 변수를 자동 사용한다.
- [ ] 사용자 제공 cookie 파일 옵션은 제공하지 않는다.
- [ ] 서버가 내려준 임시 cookie는 현재 `HttpClient` 생명주기 안에서만 메모리로 유지한다.
- [ ] User-Agent 교체 또는 `HttpClient` 종료 시 cookie jar를 reset한다.
- [ ] raw cookie, Proxy password, token, credential은 로그, checkpoint, JSONL, report, failure record에 저장하지 않는다.
- [ ] `.env`, output, checkpoint는 `.gitignore` 보호 대상이다.

**Given/When/Then**

- Given 서버가 응답에서 `Set-Cookie`를 내려줬을 때
- When 같은 `HttpClient` 생명주기 안에서 후속 요청이 실행되면
- Then 임시 cookie는 메모리 안에서만 사용될 수 있고 어떤 출력 파일에도 기록되지 않는다.

**검증 메모**

- 로그 캡처 테스트에서 raw cookie와 Proxy password가 없는지 확인한다.
- User-Agent 교체 시 in-memory cookie가 reset되는지 확인한다.
- 파일 파싱 테스트는 빈 줄, 잘못된 User-Agent, 누락 Proxy 변수를 포함한다.

### US-003. 요청 속도와 worker 수를 조절한다

**페르소나**: P-001 터미널 수집 사용자, P-003 워커 컨테이너 운영자

**User Story**: 운영자로서, 요청 간격과 게시글 worker 수를 조절하고 싶다. 그래서 차단 위험과 처리량 사이의 균형을 Job마다 정할 수 있다.

**요구사항 추적**: FR-017, FR-024, NFR-003

**인수조건**

- [ ] 기본 전역 요청 간격은 1초다.
- [ ] 사용자는 CLI 옵션으로 전역 요청 간격을 변경할 수 있다.
- [ ] 요청 지연은 게시판 목록, 게시판 검색, 통합 검색, 게시글 상세, 댓글, 이미지/동영상 다운로드에 적용된다.
- [ ] 링크 수집은 Job마다 단일 순차 worker로 동작한다.
- [ ] 게시글 상세 수집은 `asyncio.Queue` 기반 멀티 worker로 동작한다.
- [ ] worker 수는 1 이상의 정수로 validation된다.

**검증 메모**

- fake clock 또는 작은 interval로 rate limiter를 검증한다.
- worker 수 validation은 property-based test 대상이다.

## 에픽 2. 검색 및 링크 수집

### US-004. 게시글 URL과 게시판/검색 결과에서 후보 링크를 수집한다

**페르소나**: P-001 터미널 수집 사용자, P-005 유지보수자

**User Story**: 터미널 수집 사용자로서, 게시글 URL이나 게시판 검색 조건을 입력해 게시글 후보를 모으고 싶다. 그래서 수동으로 FMKorea 페이지를 넘기지 않아도 된다.

**요구사항 추적**: FR-006, FR-012, FR-017, FR-018

**인수조건**

- [ ] direct-post URL에서 `document_srl`, 가능한 경우 `board_id`를 추출한다.
- [ ] 단축 URL과 `index.php?mid=<board_id>&document_srl=<document_srl>` 형식을 모두 후보로 변환한다.
- [ ] 게시판 내 검색은 `search.php`, `mid`, `search_target`, `search_keyword`, `page`, 선택적 `category`를 사용한다.
- [ ] 목록/검색 단계에서는 후보 링크와 진단용 후보 메타데이터만 수집한다.
- [ ] 최종 저장용 제목, 작성자, 작성일, 조회수, 댓글 수, 본문은 상세 페이지에서 다시 파싱한다.
- [ ] 공지/광고/비게시글 행은 후보에서 제외한다.
- [ ] 중복 제거 기준은 `(site_id, board_id, document_srl)`이다.

**검증 메모**

- URL/query builder round trip PBT를 적용한다.
- 게시판 검색 fixture로 후보 링크, 공지 제외, category 보존을 테스트한다.

### US-005. 통합 검색과 심층검색으로 후보 게시판과 게시글을 수집한다

**페르소나**: P-001 터미널 수집 사용자, P-006 Polars 데이터 검토자

**User Story**: 데이터 검토자로서, 통합 검색 결과와 심층검색 결과를 함께 수집하고 싶다. 그래서 특정 키워드가 여러 게시판에 흩어진 경우에도 조건 범위 안에서 누락을 줄일 수 있다.

**요구사항 추적**: FR-013, FR-014

**인수조건**

- [ ] 통합 검색은 검색 결과 없음 또는 다음 페이지 없음까지 탐색한다.
- [ ] 통합 검색에는 configurable max page 안전장치를 둔다.
- [ ] 심층검색은 키워드를 필수로 입력받는다.
- [ ] 심층검색은 글번호 범위 또는 기간 범위 중 하나 이상이 없으면 validation 오류를 반환한다.
- [ ] 심층검색 1단계는 통합 검색 결과에서 게시판 후보를 만든다.
- [ ] 심층검색 2단계는 후보 게시판별로 같은 키워드의 게시판 내 검색을 수행한다.
- [ ] 일부 후보 게시판 검색 실패는 전체 Job 실패가 아니라 failure record에 남긴다.
- [ ] Job metadata에는 심층검색 모드, 키워드, 범위 조건, 발견한 게시판 후보 수를 기록한다.

**Given/When/Then**

- Given 키워드와 기간 범위 또는 글번호 범위가 입력됐을 때
- When 심층검색 Job이 실행되면
- Then 통합 검색에서 게시판 후보를 만들고, 후보 게시판별 검색 결과를 중복 제거해 Queue에 넣는다.

**검증 메모**

- 통합 검색 fixture로 paging 종료 조건과 후보 게시판 dedupe를 검증한다.
- 범위 조건이 없는 심층검색 입력은 validation 오류로 검증한다.

### US-006. 노키워드 범위 수집과 실시간 수집을 실행한다

**페르소나**: P-001 터미널 수집 사용자, P-003 워커 컨테이너 운영자

**User Story**: 터미널 수집 사용자로서, 키워드 없이 기간/글번호 범위로 수집하거나 실시간으로 새 글을 수집하고 싶다. 그래서 검색어가 없는 범위 수집과 장시간 모니터링 수집을 같은 런타임에서 처리할 수 있다.

**요구사항 추적**: FR-015, FR-016, FR-018

**인수조건**

- [ ] 노키워드 범위 수집은 게시판 목록 페이지를 순차 탐색한다.
- [ ] 후보 작성일과 `document_srl` 범위로 게시글 후보를 필터링한다.
- [ ] 전용 날짜 이동 API가 확인되면 UOW-003에서 site-specific 최적화로 추가할 수 있다.
- [ ] 실시간 수집은 `FMKOREA_REALTIME_ENABLED=true`일 때만 활성화된다.
- [ ] `FMKOREA_REALTIME_MODE`는 `keyword` 또는 `all`만 허용한다.
- [ ] `keyword` 모드는 `FMKOREA_REALTIME_KEYWORD`가 없으면 validation 오류를 반환한다.
- [ ] 실시간 수집은 `FMKOREA_REALTIME_DURATION_SECONDS` 또는 `FMKOREA_REALTIME_END_AT` 중 정확히 하나만 입력받는다.
- [ ] 실시간 반복은 이미 처리한 `(site_id, board_id, document_srl)`를 다시 Queue에 넣지 않는다.
- [ ] 종료 조건 도달 시 `status="completed"` checkpoint를 저장한다.

**검증 메모**

- 환경변수 fixture로 실시간 옵션 validation을 검증한다.
- dedupe idempotence는 PBT 대상이다.

## 에픽 3. 게시글 상세, 댓글, 미디어 수집

### US-007. 게시글 상세 메타데이터와 본문을 수집한다

**페르소나**: P-002 Python 라이브러리 개발자, P-005 유지보수자

**User Story**: 라이브러리 개발자로서, 게시글 후보 하나에서 표준 메타데이터와 본문을 얻고 싶다. 그래서 검색 경로와 무관하게 같은 게시글 JSON을 만들 수 있다.

**요구사항 추적**: FR-007, FR-011

**인수조건**

- [ ] 상세 페이지에서 `site_id`, `board_id`, `board_name`, `document_srl`, canonical URL을 수집한다.
- [ ] 말머리/category, 제목, 작성자 닉네임, 회원 번호, 레벨을 수집한다.
- [ ] 작성일, 조회수, 포텐/방출 또는 대응 반응 수, 댓글 수를 수집한다.
- [ ] 본문 기준 컨테이너는 기능명세서의 FMKorea selector 우선순위를 따른다.
- [ ] FMKorea 원본 JSON에는 `is_repost`, `repost`를 저장하지 않는다.
- [ ] 접근 불가, 삭제, 로그인 필요, 차단 의심 페이지는 실패 사유로 기록한다.

**검증 메모**

- 실제 HTML fixture로 메타데이터와 본문 추출을 테스트한다.
- `is_repost`/`repost` 부재는 JSON schema fixture로 검증한다.

### US-008. 본문 콘텐츠와 미디어를 Polars-friendly content block으로 저장한다

**페르소나**: P-002 Python 라이브러리 개발자, P-006 Polars 데이터 검토자

**User Story**: 데이터 검토자로서, 본문 텍스트, 이미지, 자체 동영상, YouTube, X, 링크, 첨부파일이 원문 순서대로 저장되길 원한다. 그래서 Polars로 block 단위 분석과 원문 재구성이 가능하다.

**요구사항 추적**: FR-008, FR-009, FR-020, DR-002

**인수조건**

- [ ] `content.blocks`는 list-of-struct 형태로 저장한다.
- [ ] 모든 block은 `order`, `type`, `url`, `text`, `provider`, `metadata` 공통 필드를 가진다.
- [ ] `order`는 게시글 안에서 중복되지 않는다.
- [ ] 지원 block type은 `text`, `image`, `fmk_video`, `youtube`, `x`, `link`, `attachment`다.
- [ ] FMKorea 자체 동영상은 video URL, poster URL, file identifier, download URL, name, upload date, description, width, height를 저장한다.
- [ ] 동영상 description이 없거나 빈 값이면 `null`로 저장한다.
- [ ] YouTube와 X는 외부 원본 파일을 다운로드하지 않고 URL/provider/id/embed_url 메타데이터만 저장한다.
- [ ] 미디어 다운로드 실패는 게시글 전체 실패가 아니라 media failure로 기록한다.

**Given/When/Then**

- Given 텍스트, 이미지, FMKorea 동영상, YouTube URL, X URL이 섞인 게시글이 있을 때
- When 상세 parser가 본문을 처리하면
- Then `content.blocks`는 DOM 순서와 block type을 보존하고 Polars에서 `explode`/`unnest` 가능해야 한다.

**검증 메모**

- 이미지/동영상/YouTube/X fixture를 분리해 parser regression test를 둔다.
- content block order uniqueness와 JSON round trip은 PBT 대상이다.
- 작은 JSONL fixture를 Polars `read_ndjson`, `explode`, `unnest`로 읽는 smoke test를 둔다.

### US-009. 댓글과 답글을 flat list로 수집한다

**페르소나**: P-002 Python 라이브러리 개발자, P-006 Polars 데이터 검토자

**User Story**: 라이브러리 개발자로서, 게시글의 댓글과 답글을 안정적인 flat list로 받고 싶다. 그래서 분석자가 부모 댓글과 하위 답글 관계를 유지할 수 있다.

**요구사항 추적**: FR-010, DR-003

**인수조건**

- [ ] 댓글 수집은 기본 활성화된다.
- [ ] CLI 옵션으로 댓글 수집을 비활성화할 수 있다.
- [ ] 댓글은 `comment_srl`, `parent_comment_srl`, `depth`, `is_best`를 포함한다.
- [ ] 댓글 작성자, 작성일 원문, 정규화 작성일, 내용, 반응 수를 저장한다.
- [ ] 답글은 가능한 경우 `parent_comment_srl`로 부모 댓글과 연결한다.
- [ ] 삭제/블라인드/비정상 댓글은 가능한 범위에서 상태를 metadata에 보존한다.

**검증 메모**

- 댓글 fixture에는 일반 댓글, BEST 댓글, 답글, 삭제/비정상 댓글을 포함한다.
- 댓글 JSONL을 Polars에서 explode해 별도 comment table로 만들 수 있는지 검증한다.

## 에픽 4. 결과 저장과 데이터 검증

### US-010. Job별 원본 JSONL과 실패 기록을 저장한다

**페르소나**: P-006 Polars 데이터 검토자, P-003 워커 컨테이너 운영자

**User Story**: 데이터 검토자로서, Job 하나의 결과가 JSONL 파일 하나에 게시글 단위로 append되길 원한다. 그래서 수집 조건별로 결과를 검증하고 재처리 입력을 추적할 수 있다.

**요구사항 추적**: FR-019, DR-001, DR-004

**인수조건**

- [ ] 기본 저장 방식은 Job당 JSONL 파일 하나다.
- [ ] 게시글 하나는 JSON 객체 한 줄로 append된다.
- [ ] resume은 기존 JSONL에 이어 쓰지 않고 새 run의 JSONL을 생성한다.
- [ ] 로컬 output과 S3 호환 output은 같은 logical layout을 따른다.
- [ ] 실패 기록은 `failures.jsonl`에 저장한다.
- [ ] 실패 기록에는 `job_id`, `run_id`, `site_id`, `board_id`, `document_srl`, `url`, `stage`, `reason`, `attempt`, `retryable`을 포함한다.
- [ ] 실패 기록에는 raw cookie, Proxy password, token, authorization header를 저장하지 않는다.
- [ ] FMKorea 원본 게시글 JSON에는 `is_repost`, `repost`를 저장하지 않는다.

**검증 메모**

- JSON serialization round trip PBT를 적용한다.
- failure redaction 테스트를 둔다.

### US-011. 원본 JSONL을 공통 분석 스키마로 정규화할 수 있게 한다

**페르소나**: P-006 Polars 데이터 검토자

**User Story**: 데이터 검토자로서, FMKorea 원본 JSONL을 공통 분석 테이블로 변환하고 싶다. 그래서 다른 커뮤니티 스크래퍼 결과와 함께 분석할 수 있다.

**요구사항 추적**: FR-020, DR-001, DR-002, DR-003

**인수조건**

- [ ] 원본 JSONL은 수정하지 않고 보존한다.
- [ ] 정규화 단계에서 posts, comments, content_blocks, media, links, failures table로 분리할 수 있다.
- [ ] 원본에 없는 `is_repost`, `repost`는 공통 정규화 단계에서만 `false`/`null` 기본값을 합성할 수 있다.
- [ ] `content.blocks`, `comments`, `attachments`, `media`는 Polars `explode`/`unnest`가 가능해야 한다.
- [ ] 정규화 결과에는 `site_id`, `job_id`, `run_id`, source object key를 추적할 수 있어야 한다.

**검증 메모**

- 작은 JSONL fixture로 Polars projection smoke test를 작성한다.
- common schema mapping은 fixture 기반 예제로 검증한다.

## 에픽 5. 중단, 재개, 실패 재처리

### US-012. CAPTCHA 또는 차단 감지 시 checkpoint를 저장하고 중단한다

**페르소나**: P-001 터미널 수집 사용자, P-003 워커 컨테이너 운영자

**User Story**: 터미널 수집 사용자로서, CAPTCHA나 차단이 감지되면 자동 우회 대신 현재 상태가 저장되길 원한다. 그래서 수집 상태를 잃지 않고 나중에 재개할 수 있다.

**요구사항 추적**: FR-021, FR-023, NFR-002, NFR-005

**인수조건**

- [ ] CAPTCHA 또는 차단 의심 응답이 감지되면 현재 Job을 즉시 중단한다.
- [ ] CAPTCHA 자동 우회 또는 자동 풀이를 시도하지 않는다.
- [ ] 정상 수집 중에는 `status=running` checkpoint를 기록한다.
- [ ] 게시글 10개 처리 완료마다 checkpoint를 저장한다.
- [ ] 중단 시 `status=stopped`와 reason을 저장한다.
- [ ] 정상 완료 시 `status=completed`를 저장한다.
- [ ] checkpoint advance는 게시글 결과 저장 성공 후에만 수행한다.
- [ ] raw cookie와 secret은 checkpoint에 저장하지 않는다.

**Given/When/Then**

- Given 게시글 worker가 CAPTCHA 의심 HTML 또는 차단 응답을 받았을 때
- When HTTP runtime이 응답을 분류하면
- Then Job은 fail closed로 멈추고 checkpoint와 재개 안내를 남긴다.

**검증 메모**

- CAPTCHA/차단 fixture로 감지와 중단 동작을 테스트한다.
- checkpoint 직렬화 round trip PBT를 적용한다.

### US-013. 중단한 Job을 재개한다

**페르소나**: P-001 터미널 수집 사용자, P-003 워커 컨테이너 운영자

**User Story**: 터미널 수집 사용자로서, 중단한 Job을 checkpoint에서 재개하고 싶다. 그래서 긴 수집 작업을 처음부터 다시 시작하지 않아도 된다.

**요구사항 추적**: FR-021, FR-022

**인수조건**

- [ ] 로컬 재개는 checkpoint `job_id`를 입력받을 수 있다.
- [ ] 컨테이너 재개는 `RESUME=true`, `JOB_ID=<checkpoint job_id>`를 사용할 수 있다.
- [ ] 공유 저장소 운영에서는 `JOB_ID` 명시 resume을 원칙으로 한다.
- [ ] 재개 시 기존 Job 유형, 검색 조건, 수집 옵션을 복원한다.
- [ ] 재개 시 새 run output을 생성한다.
- [ ] 이미 성공 저장된 `(site_id, board_id, document_srl)`은 중복 저장하지 않는다.
- [ ] checkpoint schema가 맞지 않으면 validation 오류를 반환한다.

**검증 메모**

- checkpoint fixture로 저장/불러오기 round trip을 테스트한다.
- completed key skip은 PBT 대상이다.

### US-014. Parser-stage 실패 게시글만 재처리한다

**페르소나**: P-005 유지보수자, P-002 Python 라이브러리 개발자

**User Story**: 유지보수자로서, parser 수정 이후 전체 수집 Job을 다시 실행하지 않고 파싱 실패한 게시글만 재처리하고 싶다. 그래서 요청 수를 줄이고 이미 성공한 결과를 보존하면서 누락분을 회수할 수 있다.

**요구사항 추적**: FR-031, DR-004

**인수조건**

- [ ] 하나 이상의 `failures.jsonl`에서 parser-stage 게시글 실패만 선별한다.
- [ ] CAPTCHA, 차단, 네트워크, 저장소, checkpoint, 수동 중단 실패는 재처리 대상에서 제외한다.
- [ ] 실패 URL은 direct-post 경로로 재수집한다.
- [ ] 재처리 결과는 원본 실패 파일을 수정하지 않고 새 run에 저장한다.
- [ ] 재처리 report에는 입력 failure 수, 제외 수, 선택 수, 성공 수, 남은 실패 수를 포함한다.
- [ ] 기존 성공 posts 입력이 있으면 이미 회수된 게시글을 건너뛸 수 있다.

**검증 메모**

- failure fixture로 parser-stage allowlist, 제외 reason, 기존 성공 skip, retry report 집계를 테스트한다.

## 에픽 6. 라이브러리, 컨테이너, MCP, CDK 통합

### US-015. Python 라이브러리 API를 제공한다

**페르소나**: P-002 Python 라이브러리 개발자, P-005 유지보수자

**User Story**: Python 라이브러리 개발자로서, core API를 import해 검색과 게시글 수집을 호출하고 싶다. 그래서 CLI 밖에서도 같은 FMKorea 스크래핑 기능을 재사용할 수 있다.

**요구사항 추적**: FR-028, NFR-001

**인수조건**

- [ ] 패키지는 `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`을 노출한다.
- [ ] 설정 객체와 결과 모델을 노출한다.
- [ ] import에는 네트워크 요청, 파일 생성, CLI prompt 부작용이 없다.
- [ ] CLI, container, MCP adapter는 같은 core 함수를 호출한다.
- [ ] 라이브러리 입력값은 CLI와 같은 기준으로 validation된다.

**검증 메모**

- import side-effect test를 둔다.
- public API smoke test는 mock transport 기반으로 실행한다.

### US-016. 워커 컨테이너와 공유 저장소를 사용한다

**페르소나**: P-003 워커 컨테이너 운영자

**User Story**: 워커 컨테이너 운영자로서, FMKorea 수집 worker를 독립 컨테이너로 실행하고 싶다. 그래서 통합 커뮤니티 스크래핑 시스템에 붙일 수 있다.

**요구사항 추적**: FR-029, NFR-004, NFR-005, NFR-008

**인수조건**

- [ ] 컨테이너 모드는 단일 Job 실행을 지원한다.
- [ ] 컨테이너는 core library를 호출하고 별도 parser logic을 가지지 않는다.
- [ ] checkpoint는 PostgreSQL에 저장할 수 있다.
- [ ] JSONL 결과와 다운로드 미디어는 Garage 기반 S3 호환 저장소에 저장할 수 있다.
- [ ] object key와 checkpoint key는 공유 저장소 규약에 따라 `site_id=fmkorea`, `job_id`, `run_id`로 분리한다.
- [ ] 컨테이너는 `RESUME`, `JOB_ID`, `DATABASE_URL`, S3 호환 접속 환경변수, `FMKOREA_` runtime env를 읽는다.
- [ ] structured logging은 stdout/stderr로 출력된다.
- [ ] secret과 raw cookie는 로그에 남지 않는다.

**검증 메모**

- container env validation test를 둔다.
- S3/PostgreSQL adapter는 fake 또는 optional smoke로 검증한다.

### US-017. MCP tool 인터페이스를 제공한다

**페르소나**: P-004 MCP 클라이언트 사용자, P-005 유지보수자

**User Story**: MCP 클라이언트 사용자로서, MCP tool 호출로 검색과 게시글 수집을 실행하고 싶다. 그래서 AI agent나 외부 도구가 같은 스크래퍼 기능을 안전하게 사용할 수 있다.

**요구사항 추적**: FR-030, NFR-001, NFR-004

**인수조건**

- [ ] MCP tool은 게시판 검색, 통합 검색, 게시글 fetch, 댓글 fetch, Job 실행, resume을 호출할 수 있다.
- [ ] MCP tool은 CLI와 같은 core library 함수를 감싼다.
- [ ] MCP 입력 스키마는 URL, board ID, document_srl, 검색어, 수집 옵션을 validation한다.
- [ ] MCP 오류 응답은 내부 stack trace, Proxy password, raw cookie, credential을 노출하지 않는다.
- [ ] MCP 반환값은 JSON 직렬화 가능한 구조여야 한다.

**검증 메모**

- MCP adapter 테스트는 core function을 mock해 입력 validation과 오류 masking을 확인한다.

### US-018. AWS CDK로 선택 배포 인프라를 정의한다

**페르소나**: P-003 워커 컨테이너 운영자, P-005 유지보수자

**User Story**: 운영자로서, 스크래퍼 워커와 저장소, checkpoint, 로그 인프라를 AWS CDK로 재현 가능하게 정의하고 싶다. 그래서 로컬 smoke 이후 AWS 환경 배포를 코드로 관리할 수 있다.

**요구사항 추적**: FR-032, NFR-004, NFR-005

**인수조건**

- [ ] CDK는 ECS Fargate one-shot worker task를 정의한다.
- [ ] CDK는 S3 output bucket과 RDS PostgreSQL checkpoint store를 정의한다.
- [ ] CDK는 CloudWatch Logs와 실패 감지 또는 실행 트리거 구성을 포함한다.
- [ ] CDK는 Secrets Manager 기반 secret injection을 사용한다.
- [ ] CDK source에는 secret 값을 평문 저장하지 않는다.
- [ ] CDK는 중앙 Job Queue, 통합 운영 UI, Docker image build, EKS 배포를 포함하지 않는다.
- [ ] `cdk synth` 또는 template test로 기본 검증이 가능해야 한다.

**검증 메모**

- CDK stack은 synth test와 template assertion으로 검증한다.

## 향후 확장 범위

- GUI 또는 Web UI는 터미널 UI가 안정화된 뒤 별도 설계한다.
- FMKorea에 재게시/공유/인용/펌 기능이 확인되면 원본 JSON 스키마와 parser를 별도 AI-DLC 변경으로 확장한다.
- 중앙 Job Queue와 통합 운영 UI는 통합 플랫폼 단계에서 별도 UOW로 진행한다.
- SeaweedFS는 대량 미디어/소파일 저장, FUSE, Iceberg 요구가 생길 때 S3 호환 저장소 대체 후보로 검토한다.

## INVEST 확인

| 항목 | 확인 결과 |
|---|---|
| Independent | 각 스토리는 독립적으로 구현/검증 가능한 사용자 가치 단위로 분리했다. |
| Negotiable | 인수조건은 결과와 제약을 고정하고 구현 세부는 다음 설계 단계에 남겼다. |
| Valuable | 각 스토리는 최소 하나 이상의 페르소나 목표에 직접 연결된다. |
| Estimable | 요구사항 ID와 site-specific 경계가 있어 구현 규모를 추정할 수 있다. |
| Small | 에픽보다 작고 구현 task보다는 큰 단위로 유지했다. |
| Testable | 모든 스토리에 acceptance criteria와 검증 메모를 포함했다. |

## 요구사항-스토리 추적

| 요구사항 | 주요 스토리 |
|---|---|
| FR-001, FR-002, FR-004 | US-001 |
| FR-003, FR-025, FR-026, FR-027 | US-002 |
| FR-017, FR-024 | US-003 |
| FR-006, FR-012, FR-018 | US-004 |
| FR-013, FR-014 | US-005 |
| FR-015, FR-016 | US-006 |
| FR-007, FR-011 | US-007 |
| FR-008, FR-009, FR-020 | US-008 |
| FR-010 | US-009 |
| FR-019, DR-001, DR-004 | US-010 |
| FR-020, DR-002, DR-003 | US-011 |
| FR-021, FR-023 | US-012 |
| FR-022 | US-013 |
| FR-031 | US-014 |
| FR-028 | US-015 |
| FR-029 | US-016 |
| FR-030 | US-017 |
| FR-032 | US-018 |
| NFR-004 | US-002, US-010, US-016, US-017, US-018 |
| NFR-005 | US-012, US-013, US-016, US-018 |
| NFR-006, NFR-007 | US-004, US-005, US-006, US-008, US-010, US-011, US-013 |
| NFR-008 | US-012, US-016 |
