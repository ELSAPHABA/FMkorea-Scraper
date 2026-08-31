# Business Rules - UOW-011 Scrapling Runtime Refactor

## Parser Rules

- BeautifulSoup은 신규 파서 런타임으로 사용하지 않습니다.
- 목록, 검색, 상세, 댓글, 본문, 미디어 파싱은 Scrapling `Selector` 기반으로 수행합니다.
- 본문 콘텐츠 블록은 DOM 순서를 보존해야 합니다.
- 파서 컴포넌트는 네트워크 요청과 저장소 쓰기를 직접 수행하지 않습니다.

## Browser Fallback Rules

- CLI/Docker 실행에서는 browser fallback을 기본 활성화합니다.
- CLI 사용자는 `--no-browser-fallback`으로 fallback을 끌 수 있습니다.
- Docker 사용자는 `FMKOREA_BROWSER_FALLBACK=false`로 fallback을 끌 수 있습니다.
- fallback은 성공 HTTP 응답에서 필수 DOM이 누락된 경우에만 실행합니다.
- 목록/게시판 검색은 `div.bd`, 통합 검색은 `.searchResult, .search_result`, 게시글 상세는 `#bd_capture`를 필수 DOM으로 봅니다.
- CAPTCHA, HTTP 430, 명확한 차단 응답에는 browser fallback을 실행하지 않습니다.
- browser fallback 실패 또는 fallback 후 필수 DOM 누락은 terminal checkpoint 저장 후 Job 실패로 처리합니다.

## Job Queue Rules

- RabbitMQ 같은 Job Queue 소비는 스크래퍼 내부 책임이 아닙니다.
- 향후 통합 플랫폼의 외부 오케스트레이터가 큐를 소비하고 one-shot worker 컨테이너를 실행합니다.
- 큐 메시지 단위는 게시글 링크가 아니라 Job 단위입니다.
- Job 내부 링크 수집과 게시글 병렬 처리는 기존 `asyncio.Queue`와 worker pool이 담당합니다.

## Spider Rules

- UOW-011은 Scrapling Spider를 구현하지 않습니다.
- Spider 전환은 실행 엔진 교체로 취급합니다.
- Spider 도입은 향후 별도 AI-DLC UOW에서만 결정합니다.

## Compatibility Rules

- CLI, Docker, MCP, library public contract는 기존 명령/모델을 유지합니다.
- fallback 기본값 변경은 CLI/Docker runtime config 조립에만 적용합니다.
- `HttpRuntimeConfig` 자체의 library 기본값은 명시적 설정을 우선하도록 유지합니다.
