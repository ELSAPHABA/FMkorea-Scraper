# FMKorea Scraper Function Specification

에펨코리아 게시판 게시글 및 댓글 스크래퍼 상세 가이드

## 1. 프로젝트 개요
- **목표**
  - 에펨코리아 게시판/검색/게시글/댓글을 수집해 게시글 단위 JSONL로 저장
  - 게시판 검색, 통합 검색, 심층검색, 실시간 수집, 실패 재처리 기능 제공
  - 향후 통합 커뮤니티 스크래핑 시스템에서 개별 커뮤니티 워커로 재사용
- **기술 스택**: `beautifulsoup`, `httpx`, `user-agents`, `json`, `polars`
  - **스크래핑**: BeautifulSoup + httpx 기반 비동기 요청
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
  - 외부 Job Queue로부터 수집 요청을 받아 처리
  - JSONL/미디어는 S3 호환 저장소에 저장하고 체크포인트는 PostgreSQL에 저장
- MCP 도구
  - 외부 에이전트/자동화 시스템이 에펨코리아 검색, 게시글 수집, 댓글 수집 기능을 호출할 수 있도록 제공
  - MCP 구현은 별도 wrapper로 두고, 스크래퍼 core 로직을 중복 구현하지 않음

## 2. 주요 기능

### 2.1. 수집 범위

#### 2.1.1. 수집 내용
- 게시판
  - `board_id`: URL의 `mid`
  - `board_name`: 페이지/목록에서 확인 가능한 게시판명
- 글 번호
  - `document_srl`
- 말머리
  - `category.id`: URL 또는 말머리 링크의 `category`
  - `category.name`: 목록/상세 페이지에 표시되는 말머리명
- 제목
- 글쓴이
  - 닉네임
  - 회원 번호: 작성자 링크/클래스의 `member_<member_srl>`에서 파싱 가능한 경우 저장
  - 레벨: 작성자 아이콘 `img.level[alt]`, `img.level[title]`에서 파싱 가능한 경우 저장
- 조회수
- 추천/비추천
  - 에펨코리아 UI 명칭 기준으로 `포텐`, `방출`을 저장
  - 상세 페이지 상단의 `추천 수`는 `poten_count`로 저장
  - `방출` 수가 페이지에 표시되지 않거나 숨김 처리된 경우 `blame_count=null`
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
  - 댓글 번호
  - 부모 댓글 번호
  - depth
  - 원본 DOM id
  - 원본 페이지 내 순서
  - BEST 댓글 여부
  - BEST 등 댓글 배지
  - 글쓴이, 작성일, 내용, 추천/비추천/추천-비추천 점수

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
    - 상세 페이지에서 최종 작성일을 다시 확인한다.
  - 특정 글번호 범위 수집
    - `document_srl` 범위로 필터링
  - 노키워드 기간/글번호 범위 수집
    - 검색 키워드 없이 게시판 목록을 페이지 단위로 순회하며 기간/글번호 조건으로 필터링
  - 실시간 키워드 수집
    - 환경변수로 활성화
    - 지정 키워드의 최신 검색 결과를 반복 확인해 새 게시글만 수집
  - 실시간 전체 수집
    - 환경변수로 활성화
    - 지정 게시판 최신 목록을 반복 확인해 새 게시글만 수집
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
- 본문 미디어 수집 옵션
  - 이미지/동영상 URL 및 메타데이터만 저장
  - 이미지/동영상 파일 저장
  - 이미지/동영상 URL 및 파일 모두 저장
  - YouTube, X 등 외부 임베드는 다운로드하지 않고 URL, provider, id, embed_url만 저장
- 실시간 종료 조건
  - 환경변수
    - `FMKOREA_REALTIME_ENABLED=true`
    - `FMKOREA_REALTIME_MODE=keyword|all`
    - `FMKOREA_REALTIME_KEYWORD=<검색어>` (`keyword` 모드에서 필수)
    - `FMKOREA_REALTIME_DURATION_SECONDS=<실행_초>`
    - `FMKOREA_REALTIME_END_AT=<UTC_ISO-8601_종료시각>`
    - `FMKOREA_REALTIME_POLL_INTERVAL_SECONDS=<반복_주기_초>` (없으면 전역 요청 간격 사용)
  - 타이머 `실행_초`와 종료 시각 중 하나만 입력받는다.
  - `FMKOREA_REALTIME_DURATION_SECONDS`와 `FMKOREA_REALTIME_END_AT` 중 정확히 하나만 입력한다.
  - 둘 다 없거나 둘 다 있으면 실시간 Job 시작 실패로 처리한다.
  - 종료 조건 도달 시 `status="completed"`로 최종 체크포인트 저장 후 종료한다.
  - 수동 중단, 오류, CAPTCHA 감지 시 기존 중단 처리와 동일하게 `status="stopped"` 저장 후 종료한다.

#### 2.1.4. 수집 주기
- 수집 주기는 사용자가 설정 가능하다.
- 실시간 모드는 지정 interval마다 최신 목록/검색 결과를 확인한다.
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
  - BeautifulSoup으로 기준 컨테이너의 하위 노드를 DOM 순서대로 순회하여 `content.blocks` 배열에 저장한다.
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
    - `file_srl`: `data-file-srl`
    - `alt`
    - `width`, `height`
    - `download_url`: `.rd_file a[data-href]`에서 같은 `file_srl`로 매칭되는 경우 저장
    - `download`
- `type="fmk_video"`
  - 펨코 자체 업로드 동영상 후보: `.auto_media_wrapper`, `video.mediaelement_video`, `video > source[type="video/mp4"]`
  - 정적 HTML에 `source src`, `poster`, schema.org `meta itemprop` 값이 포함되므로 BeautifulSoup만으로 수집 가능하다.
  - 저장 필드
    - `video_url`: `source[src]` 또는 `meta[itemprop="contentURL"]`
    - `poster_url`: `video[poster]` 또는 `meta[itemprop="thumbnailUrl"]`
    - `file_srl`: `.auto_media_wrapper[data-file-download-url]`에서 파싱
    - `download_url`: `.auto_media_wrapper[data-file-download-url]`
    - `name`: `meta[itemprop="name"]`
    - `upload_date`: `meta[itemprop="uploadDate"]`
    - `description`: `meta[itemprop="description"]`, 없거나 빈 값이면 `null`
    - `width`, `height`
    - `download`
  - 같은 `video`의 하위 `source`는 별도 블록으로 중복 저장하지 않는다.
- `type="youtube"`
  - 정적 HTML 후보
    - 본문 텍스트/링크의 `youtube.com/watch`, `youtu.be/<video_id>`
  - 렌더링 후 후보
    - `iframe[src*="youtube.com/embed"]`
  - BeautifulSoup 기본 구현은 정적 HTML의 YouTube URL을 파싱해 `embed_url`을 직접 생성한다.
  - 저장 필드
    - `provider="youtube"`
    - `video_id`
    - `url`
    - `embed_url`
    - `start_seconds`: `t`, `start` 파라미터가 있으면 초 단위 저장
  - 외부 영상 파일은 다운로드하지 않는다.
- `type="x"`
  - 정적 HTML 후보
    - 본문 텍스트/링크의 `https://x.com/<user>/status/<tweet_id>`
    - `https://twitter.com/<user>/status/<tweet_id>`
  - 렌더링 후 후보
    - `iframe[src*="platform.twitter.com/embed/Tweet.html"]`
  - BeautifulSoup 기본 구현은 정적 HTML에 남아 있는 X URL을 우선 수집한다.
  - 렌더링된 iframe을 참고할 수 있는 환경에서는 `embed_url`도 저장한다.
  - 저장 필드
    - `provider="x"`
    - `tweet_id`
    - `url`
    - `embed_url`: 알 수 없으면 `null`
  - X 첨부 미디어 원본 파일은 다운로드하지 않는다.
- `type="link"`
  - 일반 링크: 기준 컨테이너 내부 `a[href]` 또는 본문 텍스트의 bare URL
  - 단, 이미지 highslide 링크, 펨코 동영상 다운로드 링크, YouTube, X는 별도 타입으로 저장하고 `link` 블록으로 중복 저장하지 않는다.
  - 저장 필드
    - `text`
    - `url`
- `content.text`
  - `content.blocks` 중 텍스트성 블록을 합쳐 저장한다.
  - 포함 대상: `text`, `link.text`, 텍스트만 있는 bare URL
  - 제외 대상: 조회수/추천수/댓글 수/첨부파일 목록/플레이어 UI/광고 텍스트
- top-level `media`
  - `content.blocks`의 `image`, `fmk_video`, `youtube`, `x` 블록만 뽑은 호환/요약 필드로 취급한다.
- 미디어 파일명
  - `media/fmkorea/<board_id>/<document_srl>/<order>_<type>.<ext>`

#### 2.3.3. 댓글 수집
- 기준 컨테이너: `.fdb_lst_ul`
- 댓글 항목: `.fdb_lst_ul > li`
- 댓글 번호
  - `li[id^="comment_"]`에서 숫자 추출
  - BEST 댓글의 id는 `comment_<comment_srl>_`처럼 끝에 `_`가 붙을 수 있으므로 숫자만 파싱한다.
  - 원본 DOM id는 `source_dom_id`에 별도 저장한다.
- 원본 순서
  - 현재 댓글 페이지/DOM에서 등장한 순서를 `source_order`로 저장한다.
  - Polars 분석 시에는 배열 순서에 의존하지 않고 `date`, `comment_srl`, `source_order` 기준으로 명시 정렬한다.
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
  - 댓글 본문 영역의 텍스트
  - 작성자/날짜/추천/비추천/주소복사/댓글로 가기 UI 텍스트는 제외
- 추천/비추천
  - 기준 컨테이너: `li[id^="comment_"] > div.fdb_nav.img_tx span.vote`
  - 추천 수: `a[title="추천"] .voted_count`
  - 비추천 수: `a[title="비추천"] .blamed_count`
  - 값이 빈 문자열이면 `0`으로 정규화한다.
  - `reactions.up_count`, `reactions.down_count`, `reactions.score=up_count-down_count`로 저장한다.
- 덧글
  - 댓글 항목 클래스 또는 DOM depth로 구분 가능한 경우 `depth=1`, `parent_comment_id=<상위 댓글 번호>`로 저장한다.
  - 명확한 부모를 찾지 못하면 `depth=null`, `parent_comment_id=null`로 저장하고 원본 class를 `raw_class`에 남긴다.

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

#### 2.4.1. Job 메타데이터 예시
```json
{
  "job_id": "job_20260811_120000",
  "site_id": "fmkorea",
  "board_id": "football_world",
  "collection_mode": "board_search",
  "post_id_range": [10190000000, 10199999999],
  "post_date_range": ["2026-08-01T00:00:00+09:00", "2026-08-11T23:59:59+09:00"],
  "category_filter": {
    "enabled": true,
    "id": 233499071,
    "name": "레알 마드리드"
  },
  "search_target": "title_content",
  "search_keyword": "검색 키워드",
  "scrap_start_timestamp": "2026-08-11T12:00:00+09:00",
  "output_file": "job_20260811_120000.jsonl"
}
```

#### 2.4.2. 게시글 JSONL 한 줄 예시
```json
{
  "scrap_timestamp": "2026-08-11T12:00:30+09:00",
  "site_id": "fmkorea",
  "board_id": "football_world",
  "board_name": "해외축구",
  "document_srl": 10196696065,
  "url": "https://www.fmkorea.com/index.php?mid=football_world&document_srl=10196696065",
  "canonical_url": "https://www.fmkorea.com/10196696065",
  "category": {
    "id": 233499071,
    "name": "레알 마드리드"
  },
  "title": "[ESPN] 어제자 레알 선수단 훈련 영상",
  "author": {
    "nickname": "유느님좋아",
    "member_srl": "534126900",
    "level": 32,
    "raw": "[레벨:32] 유느님좋아"
  },
  "date": "2026-08-11T08:03:00+09:00",
  "views": 361,
  "reactions": {
    "poten_count": 5,
    "blame_count": null
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
        "download": {
          "enabled": false,
          "path": null,
          "status": "skipped"
        }
      },
      {
        "order": 1,
        "type": "youtube",
        "provider": "youtube",
        "video_id": "IKyeLpRZaZE",
        "url": "https://youtu.be/IKyeLpRZaZE?t=456",
        "embed_url": "https://www.youtube.com/embed/IKyeLpRZaZE?start=456",
        "start_seconds": 456
      },
      {
        "order": 2,
        "type": "x",
        "provider": "x",
        "tweet_id": "1973529989002989733",
        "url": "https://x.com/elonmusk/status/1973529989002989733",
        "embed_url": null
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
        "download": {
          "enabled": true,
          "path": "media/fmkorea/football_world/10196696065/3_image.jpg",
          "status": "saved"
        }
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
      "file_srl": "10195587886",
      "name": "example.jpg",
      "download_url": "https://www.fmkorea.com/?module=file&act=procFileDownload&file_srl=10195587886&sid=...",
      "size_text": "186.5KB",
      "download_count": 1
    }
  ],
  "media": [
    {
      "order": 0,
      "type": "fmk_video",
      "url": "https://mediak5jvqbd.fmkorea.com/files/attach/new5/20260811/example.mp4",
      "path": null
    },
    {
      "order": 3,
      "type": "image",
      "url": "https://image.fmkorea.com/files/attach/new5/20260810/example.jpg",
      "path": "media/fmkorea/football_world/10196696065/3_image.jpg"
    }
  ],
  "comments": [
    {
      "comment_srl": 10197230200,
      "source_dom_id": "comment_10197230200_",
      "parent_comment_srl": null,
      "depth": 0,
      "source_order": 0,
      "is_best": true,
      "badges": ["BEST"],
      "author": {
        "nickname": "V5_Faker",
        "member_srl": "1324753328",
        "level": 27
      },
      "date_raw": "4 시간 전",
      "date": null,
      "content": "댓글 내용",
      "reactions": {
        "up_count": 375,
        "down_count": 0,
        "score": 375
      },
      "permalink": "https://www.fmkorea.com/10196696065/10197230200#comment_10197230200",
      "metadata": {
        "classes": ["fdb_itm", "clear", "comment_best", "comment-2"]
      }
    }
  ],
  "raw": {
    "candidate_metadata": {
      "source": "board_search",
      "page": 1
    }
  }
}
```

### 2.5. 작업 상태 및 체크포인트 저장
- 상태 및 체크포인트 JSON은 커뮤니티 스크래퍼 공통 스키마로 관리한다.
- 게시글 본문 JSONL 스키마는 커뮤니티별로 독립 확장 가능하다.
- 저장 시점
  - 각 게시글 스크래핑 및 JSONL 저장 완료 후 메모리상의 진행 상태 갱신
  - 게시글 10개 처리 완료마다 체크포인트 저장
  - 수동 중단, 정상 종료, 복구 불가능한 오류, CAPTCHA 또는 차단 감지 시 즉시 체크포인트 저장
- 저장 순서
  - 게시글 결과를 먼저 멱등하게 저장
  - 게시글 저장 성공 후 `last_completed_post_id`, `last_completed_url`, `scraping_processed_count` 갱신
  - 체크포인트 저장은 원자적으로 처리
- 상태 값
  - `running`: 정상 수집 진행 중
  - `stopped`: 수동 중단, 오류, CAPTCHA, timeout, lease 만료 등으로 중단
  - `completed`: Queue가 비고 모든 워커가 정상 종료
- 중단 사유 `reason`
  - `captcha`
  - `blocked`
  - `manual_stop`
  - `error`
  - `timeout`
  - `lease_expired`
- 재개 처리
  - 로컬 환경은 터미널 옵션으로 체크포인트 `job_id`를 입력받아 재개
  - 컨테이너 환경은 `docker run` 환경변수 `RESUME=true`, `JOB_ID=<checkpoint job_id>`로 재개
  - 재개 요청 시 `JOB_ID`가 없으면 가장 최근 체크포인트를 자동 선택
  - 재개 시 기존 JSONL 파일에 이어 쓰지 않고 새 JSONL 파일을 생성해 중단점 이후부터 기록
  - 이미 저장된 게시글은 `(site_id, board_id, document_srl)` 기준으로 중복 저장되지 않도록 처리
- 체크포인트에 저장되는 `JobConfig`
  - `JobConfig`는 수집 대상, 수집 옵션, 워커 옵션, 저장소 옵션만 저장한다.
  - User-Agent 파일 경로, User-Agent 교체 주기, Proxy, timeout 같은 HTTP 실행값은 `JobConfig`에 저장하지 않는다.
  - 위 HTTP 실행값은 CLI, 터미널 마법사, 컨테이너, MCP, 라이브러리 adapter가 실행 시점에 `HttpRuntimeConfig`로 조립한다.
  - 과거 체크포인트에 `job_config.runtime_config`가 남아 있으면 로드 시 해당 legacy 필드만 버리고 재개한다.

### 2.6. 차단 대응, Proxy, User-Agent, 속도 제어
- CAPTCHA/차단 포착
  - CAPTCHA 또는 명백한 차단 페이지를 감지하면 자동 우회를 시도하지 않는다.
  - 현재 작업을 중단하고 체크포인트와 중단 사유를 저장한다.
  - 체크포인트 저장 후 터미널과 로그에 저장된 `job_id`를 출력한다.
- User-Agent Mixer
  - 차단 완화를 위해 요청 시 사용할 User-Agent를 주기적으로 교체한다.
  - User-Agent 목록 파일명은 `user-agents.txt`로 통일한다.
  - 컨테이너 이미지 생성 시 `user-agents.txt`를 포함한다.
  - 로컬 실행 시 실행 파일과 같은 위치의 `user-agents.txt`를 자동 로드한다.
  - 터미널 옵션에서 파일 탐색기 창을 열어 User-Agent 목록 파일을 불러오고, 실행 파일과 같은 위치의 `user-agents.txt`로 저장/교체 가능하다.
  - `user-agents.txt`는 사용자가 직접 편집할 수 있도록 비인코딩 평문으로 저장한다.
  - 파일 포맷은 한 줄에 User-Agent 하나다.
  - 빈 줄은 무시한다.
  - 파일이 없거나 유효한 User-Agent가 없으면 기본 User-Agent 하나만 사용한다.
  - 기본 교체 주기는 요청 10회마다 1회다.
  - CLI 옵션으로 파일 경로와 교체 주기를 변경할 수 있다.
  - 비동기 멀티 워커 실행 시에도 컨테이너/프로세스 내부 공용 요청 카운터 기준으로 교체한다.
  - 컨테이너 간 User-Agent 교체 카운터는 공유하지 않는다.
- Proxy
  - Proxy를 통해 httpx 요청을 전송한다.
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
    - `docker run` 시 환경변수로 `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW`를 입력 가능하다.
    - `docker-entrypoint.sh`는 전달받은 Proxy 환경변수를 컨테이너 내부 `.env` 파일로 생성한다.
    - 컨테이너에 `.env` 파일을 직접 주입하는 방식도 허용한다.
    - 컨테이너 내부 프로그램은 로컬 실행과 동일하게 `.env`를 읽어 Proxy를 적용한다.
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
  - 429/403/차단 의심 응답 발생 시 즉시 속도를 낮추거나 중단한다.

### 2.7. 실패 기록 및 재처리
- 실패는 `failures.jsonl`에 저장한다.
- parser-stage 실패는 추후 재처리 유닛에서 direct-post 경로로 재수집한다.
- 네트워크, CAPTCHA, 차단, 저장소 실패는 재처리 유닛 대상에서 제외하고 기존 retry/checkpoint/운영 대응 절차에서 처리한다.
- 실패 기록 필드
  - `job_id`
  - `site_id`
  - `board_id`
  - `document_srl`
  - `url`
  - `stage`
  - `reason`
  - `error_message`
  - `attempt`
  - `created_at`

## 3. 기술 스택
- Proxy를 통한 httpx 요청 전송
- `.env` 파일 기반 Proxy 환경변수 로드
- 서버가 내려준 임시 cookie는 `HttpClient` 생명주기 안에서만 메모리로 유지하고, User-Agent 교체 또는 client 종료 시 reset
- BeautifulSoup 기반 HTML 파싱
- httpx 기반 동기/비동기 HTTP 요청
- asyncio 기반 링크 수집 워커 + 게시글 수집 워커 분리
- json 기반 JSONL 저장
- Polars 기반 JSONL 가공 및 분석
- `user-agents.txt` 기반 User-Agent 주기적 교체
- 로컬 체크포인트는 `Checkpoint.json`
- 컨테이너 체크포인트는 PostgreSQL
- 컨테이너 JSONL/미디어 출력은 Garage 기반 S3 호환 객체 저장소
- AWS CDK를 활용한 ECS Fargate, AWS S3, RDS PostgreSQL 기반 선택 배포 경로는 공통 스크래퍼 인프라 패턴을 계승해 별도 구성 가능
- SeaweedFS는 대량 미디어/소파일 저장, FUSE, Iceberg 요구가 생길 때 확장 후보로 유지

## 4. 디렉토리 구조
```
FMKorea-Scraper/
├── main.py
├── fmkorea_scraper/
│   ├── __init__.py
│   ├── domain/
│   │   ├── models.py
│   │   └── jobs.py
│   ├── services/
│   │   ├── board_scraper.py
│   │   ├── search_scraper.py
│   │   ├── post_scraper.py
│   │   ├── comment_scraper.py
│   │   └── parser_retry.py
│   ├── adapters/
│   │   ├── cli.py
│   │   ├── wizard.py
│   │   ├── storage_local.py
│   │   ├── storage_s3.py
│   │   └── checkpoint_postgres.py
│   ├── http/
│   │   ├── client.py
│   │   ├── proxy.py
│   │   ├── rate_limit.py
│   │   └── user_agent.py
│   └── config/
│       └── settings.py
├── infra/
│   └── cdk/
├── docs/
│   └── FMKorea-Scraper_Function_Specification.md
├── user-agents.txt
├── .env
├── docker-entrypoint.sh
├── Checkpoint.json
├── pyproject.toml
└── README.md
```

## 5. 실행 형태
- CLI 직접 실행
  - 명령형 실행: `python -m fmkorea_scraper.adapters.cli run ...`
  - 터미널 마법사 실행은 같은 CLI 엔트리에서 선택형 UI로 제공 가능
- 라이브러리 import
  - 설정 객체와 Job 객체를 코드에서 생성해 수집기를 직접 호출할 수 있게 구성
- Docker 워커 컨테이너
  - 환경변수로 Job 옵션, 저장소, Proxy, 실시간 종료 조건을 주입
  - JSONL/미디어는 S3 호환 저장소로 출력
  - 체크포인트는 PostgreSQL에 저장
- 향후 MCP
  - 같은 core service를 MCP tool wrapper에서 호출한다.

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
- 향후 통합 플랫폼에서 마스터 컨테이너 - 워커 컨테이너 구조 기반으로 여러 커뮤니티 스크래퍼를 관리
- 작업 컨테이너 스케줄링 및 모니터링 기능
- 작업 상태 시각화 및 알림 기능
- 작업 실패 시 재시도 및 오류 로그 관리
- SQS 기반 작업 큐, lease 갱신, lease 만료 시 `reason="lease_expired"` 체크포인트 저장

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
  - 통합 플랫폼에서 Job Queue를 소비하는 실행 단위
  - 컨테이너별 Proxy/User-Agent/속도 설정을 환경변수로 주입
- KubeRay
  - 대규모 분산 수집/분석이 필요해질 때 검토
  - 초기 구현 범위에는 포함하지 않음
