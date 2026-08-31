# Domain Entities - UOW-011 Scrapling Runtime Refactor

## `ScraplingSelectorDocument`

Scrapling `Selector`로 파싱한 HTML DOM 문서입니다.

속성:

- `html`
- `url`
- `root`

규칙:

- 목록, 검색, 상세, 댓글, 본문, 미디어 파서는 이 DOM 문서를 기준으로 동작합니다.
- 파서는 네트워크 요청이나 저장소 쓰기를 수행하지 않습니다.

## `RequiredDomSelector`

브라우저 fallback 여부를 판단하는 최소 DOM 기준입니다.

값:

- board list/search: `div.bd`
- integrated search: `.searchResult, .search_result`
- post detail: `#bd_capture`

규칙:

- HTTP 응답이 성공으로 분류된 뒤에만 검사합니다.
- selector가 없고 browser fallback이 활성화되어 있으면 `DynamicFetcher`로 한 번 렌더링합니다.
- CAPTCHA, HTTP 430, 명확한 차단 응답은 검사 전에 fail-closed 처리합니다.

## `BrowserFallbackConfig`

일반 Playwright 기반 Scrapling `DynamicFetcher` fallback 설정입니다.

속성:

- `enabled`
- `required_selector`
- `timeout`
- `headers`
- `proxy`

규칙:

- CLI/Docker 실행에서는 기본 활성화합니다.
- CLI는 `--no-browser-fallback`, Docker는 `FMKOREA_BROWSER_FALLBACK=false`로 비활성화할 수 있습니다.
- fallback 실패 또는 렌더링 후 필수 DOM 누락은 terminal failure입니다.

## `ExternalJobQueueBoundary`

향후 통합 플랫폼의 Job Queue 소비 경계입니다.

규칙:

- 이 스크래퍼는 RabbitMQ consumer를 구현하지 않습니다.
- 외부 오케스트레이터가 Job Queue를 소비하고 one-shot worker 컨테이너를 실행합니다.
- 스크래퍼 내부 게시글 링크 병렬 처리는 기존 프로세스 내부 큐가 담당합니다.

## `FutureSpiderMigration`

Scrapling Spider 기반 실행 엔진 전환 계획입니다.

규칙:

- 현재 UOW-011에서는 Spider를 사용하지 않습니다.
- Spider 전환은 향후 별도 AI-DLC UOW에서 `JobRunner`, checkpoint, retry, report, worker queue를 함께 재설계합니다.
