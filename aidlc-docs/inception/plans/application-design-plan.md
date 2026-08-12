# Application Design Plan

이 계획은 `requirements.md`, `stories.md`, `execution-plan.md`, `docs/FMKorea-Scraper_Function_Specification.md`를 바탕으로 Application Design 산출물을 생성하기 위한 질문지입니다.

답변 방법: 아래 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## 설계 범위 요약

- Greenfield Python project
- 기준 패키지: `fmkorea_scraper`
- 1차 실행 방식: CLI, 터미널 마법사, Python library API, worker container, MCP tool
- 핵심 런타임: `httpx`, `asyncio`, BeautifulSoup, 표준 `json`, Polars
- 핵심 흐름: Job 설정, 검색/링크 수집, 게시글 상세 수집, 댓글/답글 수집, JSONL 저장, checkpoint 재개, parser-stage 실패 재처리
- 주요 제약: Playwright 런타임 의존 금지, CAPTCHA 우회 금지, 공개 콘텐츠만 수집
- 상속 기준: `DCinside-Scraper`의 UOW, storage, checkpoint, CLI/container/MCP/CDK 구조를 최대한 계승하고 FMKorea URL/query/parser만 교체

## 최신 명세 반영 메모

- FMKorea 원본 JSONL에는 `is_repost`, `repost` 필드를 저장하지 않는다.
- 댓글은 게시글 하위 `comments` flat list로 저장한다.
- BEST 댓글은 별도 `best_comments` 배열로 분리하지 않고 `is_best=true`, `badges=["BEST"]`로 저장한다.
- 댓글 추천/비추천은 `reactions.up_count`, `reactions.down_count`, `reactions.score`로 저장한다.
- Polars 정규화 단계에서는 게시글/댓글/미디어 테이블을 분리한다.

## Application Design 작업 체크리스트

- [x] 요구사항, 유저 스토리, 실행 계획 확인
- [x] 최신 기능명세서 변경 사항 확인
- [x] 설계 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/inception/application-design/components.md` 생성
- [x] `aidlc-docs/inception/application-design/component-methods.md` 생성
- [x] `aidlc-docs/inception/application-design/services.md` 생성
- [x] `aidlc-docs/inception/application-design/component-dependency.md` 생성
- [x] `aidlc-docs/inception/application-design/application-design.md` 생성
- [x] 설계 완전성과 일관성 검증
- [x] 완료한 항목은 즉시 체크리스트에 반영

## 답변 분석 결과

- 모든 `[Answer]:` 항목이 채워졌다.
- 모든 답변은 `A`로, 권장 선택지와 일치한다.
- 답변 간 충돌은 없다.
- follow-up 질문은 필요하지 않다.
- Application Design 산출물 생성 후 Units Generation으로는 진행하지 않고 review gate에서 멈춘다.

## 설계 질문

### Question 1. 패키지와 컴포넌트 경계

Python 패키지 구조를 어떻게 나눌까요?

A) (권장) 단일 패키지 `fmkorea_scraper` 안에 `models`, `core`, `http`, `search`, `post_detail`, `storage`, `jobs`, `retry`, `adapters`, `infra` 하위 모듈을 둔다.

추천 사유: 기준 프로젝트의 구조를 가장 잘 계승하면서도 여러 Python package로 쪼개는 관리 비용을 피할 수 있습니다. CLI, container, MCP는 얇은 adapter로 두고 core library를 공유하기 좋습니다.

B) CLI, core library, MCP, container, CDK를 별도 Python package로 분리한다.

C) 1차 구현은 적은 수의 파일로 시작하고, 커질 때 하위 모듈을 분리한다.

X) 기타

[Answer]: A

### Question 2. 데이터 모델과 JSON 직렬화 방식

게시글, 댓글, content block, checkpoint, failure report 같은 모델을 어떤 방식으로 정의할까요?

A) (권장) Pydantic 모델을 사용하고, JSONL 저장 시 `model_dump(mode="json")` 기반으로 직렬화한다.

추천 사유: 기준 프로젝트가 Pydantic 모델 기반이고, FMKorea도 댓글 BEST/reactions/content block처럼 nested schema가 많습니다. 입력 validation과 JSONL 직렬화를 같은 모델 경계에서 처리하는 편이 안전합니다.

B) 표준 `dataclasses`를 사용하고, JSONL 저장 직전에 dict로 변환한다.

C) 별도 모델 없이 plain dict 중심으로 구현한다.

X) 기타

[Answer]: A

### Question 3. Public API 형태

Python library API는 async/sync 중 어떤 형태를 기본으로 할까요?

A) (권장) `async` API를 기본으로 제공하고, CLI/마법사는 내부에서 `asyncio.run()`으로 실행한다.

추천 사유: 요구사항의 핵심이 `httpx`와 `asyncio` 기반 멀티 워커입니다. public API도 async를 기본으로 두면 내부 구조와 맞고, sync wrapper는 실제 필요가 생겼을 때 추가해도 늦지 않습니다.

B) sync API를 기본으로 제공하고 내부에서 async 처리를 숨긴다.

C) async API와 sync wrapper를 모두 public API로 제공한다.

X) 기타

[Answer]: A

### Question 4. HTTP 요청 정책 경계

요청 속도, retry, timeout, User-Agent, Proxy, optional cookie file 적용을 어디에서 담당하게 할까요?

A) (권장) 단일 `HttpClient` 또는 `HttpPort` 구현이 모든 외부 요청 정책을 담당한다.

추천 사유: 목록, 검색, 게시글 상세, 댓글, 이미지/동영상 요청에 같은 차단 대응과 secret masking 규칙이 적용되어야 합니다. 한 경계에 모아야 누락이 줄어듭니다.

B) search/detail/media/comment 서비스가 직접 `httpx` 요청 옵션을 관리한다.

C) 요청 종류별로 `SearchClient`, `PostClient`, `CommentClient`, `MediaClient`를 완전히 분리한다.

X) 기타

[Answer]: A

### Question 5. FMKorea site-specific 파서 경계

FMKorea URL/query builder와 HTML parser를 공통 구조와 어떻게 분리할까요?

A) (권장) `search`와 `post_detail` 안에 FMKorea 전용 collector/parser를 두고, 공통 모델과 포트만 공유한다.

추천 사유: 지금 필요한 것은 FMKorea 스크래퍼입니다. 후속 커뮤니티용 generic plugin framework를 지금 만들면 구현량이 커집니다. 공통화는 모델/포트/저장소 규약까지만 유지하는 편이 적절합니다.

B) 처음부터 커뮤니티 plugin registry를 만들고 FMKorea를 하나의 plugin으로 구현한다.

C) 모든 parser를 하나의 큰 `parser.py`에 둔다.

X) 기타

[Answer]: A

### Question 6. 댓글/BEST 댓글 모델

FMKorea 댓글과 BEST 댓글은 어떤 저장 모델을 사용할까요?

A) (권장) 모든 댓글을 `comments` flat list에 저장하고, BEST 댓글은 `is_best`, `badges`, `reactions` 필드로 표시한다.

추천 사유: BEST 댓글도 실제로는 `li.comment_best` 클래스가 붙은 댓글입니다. 별도 배열로 분리하면 중복과 정규화 복잡도가 생깁니다. flat list는 Polars에서 `explode` 후 필터링하기 쉽습니다.

B) `comments`와 `best_comments`를 별도 배열로 저장한다.

C) BEST 댓글은 일반 댓글로만 저장하고 BEST 여부는 버린다.

X) 기타

[Answer]: A

### Question 7. Job 오케스트레이션 구조

검색 페이지 탐색과 게시글 worker 병렬 수집을 어떤 서비스가 조율하게 할까요?

A) (권장) `JobRunner`가 단일 link collector와 `asyncio.Queue` 기반 post worker pool을 조율한다.

추천 사유: 큐 단위가 게시글 링크 1개라는 요구와 잘 맞습니다. CLI/container/MCP가 orchestration을 직접 가지지 않게 되어 재사용성과 테스트가 좋아집니다.

B) CLI가 직접 link collector와 post worker를 조율한다.

C) entry point별 `BoardSearchJob`, `IntegratedSearchJob`, `DirectPostJob`이 각각 전체 흐름을 소유한다.

X) 기타

[Answer]: A

### Question 8. 저장소와 checkpoint 경계

JSONL, 미디어, 실패 기록, checkpoint 저장을 어떻게 나눌까요?

A) (권장) `OutputStore`, `MediaStore`, `FailureStore`, `CheckpointStore` 포트를 두고 local, S3-compatible, PostgreSQL adapter를 붙인다.

추천 사유: 로컬 실행과 컨테이너 실행의 저장소가 다릅니다. 포트는 필요하지만, adapter 수는 요구된 local/Garage/PostgreSQL 경계로만 제한하면 충분합니다.

B) `JobRunner`가 모든 파일과 checkpoint 쓰기를 직접 담당한다.

C) 1차 구현은 local file만 만들고 S3/PostgreSQL은 후속으로 미룬다.

X) 기타

[Answer]: A

### Question 9. Checkpoint 정밀도

중단점은 어느 수준까지 복원하도록 설계할까요?

A) (권장) Job 설정, collector cursor, 완료 key 집합, 가능한 남은 link queue를 저장한다. in-flight 요청의 정확한 복원은 보장하지 않는다.

추천 사유: 중단 후 재개에 충분한 정보를 저장하면서 worker별 in-flight 상태까지 복원하는 복잡도를 피할 수 있습니다. 이미 저장된 게시글은 dedupe로 건너뛰면 됩니다.

B) worker별 in-flight 요청까지 정확히 저장해 거의 완전한 queue 복원을 목표로 한다.

C) 마지막 처리 게시글만 저장하고 재개 시 처음부터 다시 탐색한다.

X) 기타

[Answer]: A

### Question 10. Container와 MCP adapter 범위

1차 container와 MCP는 어느 수준까지 제공할까요?

A) (권장) container는 one-shot Job 실행을 기본으로 하고, MCP는 core public API의 thin wrapper로 `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, `retry_parser_failures`를 제공한다.

추천 사유: 요구사항의 실행 형태를 모두 만족하면서도 adapter는 core를 감싸는 정도로 유지합니다. long-running queue daemon은 통합 플랫폼 구체화 후 추가하는 편이 안전합니다.

B) container는 long-running worker daemon으로 만들고, MCP도 Job queue 제어까지 담당한다.

C) container와 MCP는 설계만 하고 1차 코드 구현에서는 제외한다.

X) 기타

[Answer]: A

### Question 11. 설계 패턴과 추상화 수준

컴포넌트 설계에서 어느 정도의 추상화를 허용할까요?

A) (권장) concrete class/function 중심으로 시작하고, HTTP/storage/checkpoint/logger 같은 외부 경계에만 최소 protocol을 둔다.

추천 사유: FMKorea 전용 구현이 1차 목표입니다. 모든 parser와 service를 plugin framework로 만들면 코드가 불필요하게 커집니다. 외부 I/O 경계만 protocol로 두면 테스트와 adapter 교체에는 충분합니다.

B) ports/adapters 구조를 엄격히 적용해 모든 컴포넌트를 interface로 감싼다.

C) 커뮤니티 plugin framework를 전제로 parser, storage, adapter를 모두 확장 가능하게 설계한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 Application Design 산출물 5개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Units Generation으로 넘어가지 않습니다.
