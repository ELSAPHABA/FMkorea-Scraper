# Requirement Verification Questions

`docs\FMKorea-Scraper_Function_Specification.md`와 `DCinside-Scraper`의 완성된 구조를 기준으로, FMKorea 스크래퍼 구현 전에 확인해야 할 차이점만 정리한 질문지입니다.

DCinside-Scraper에서 이미 확정된 공통 결정은 기본 계승으로 봅니다. 각 질문의 `[Answer]:` 뒤에 선택지 문자만 적어 주세요. 선택지가 맞지 않으면 마지막 `X) Other`를 고르고 설명을 적어 주세요.

## Question 1
DCinside-Scraper의 기능/유닛/구조를 어느 정도까지 계승할까요?

A) (권장) 전체 계승. UOW-001~UOW-010, CLI, 마법사, 컨테이너, MCP, parser-failure retry, CDK 구조를 유지하고 site-specific 구현만 FMKorea에 맞게 교체

권장 사유: 이미 DCinside-Scraper에서 검증한 구조를 재사용하므로, FMKorea 전용 URL/query/parser에만 집중할 수 있습니다.

B) 핵심만 계승. models, HTTP runtime, parser, CLI까지만 먼저 만들고 container/MCP/CDK는 후속 UOW로 분리

C) 문서 구조만 참고. FMKorea 구현은 새 구조로 다시 설계

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
프로젝트 식별자와 실행 이름은 어떻게 둘까요?

A) (권장) `site_id=fmkorea`, package=`fmkorea_scraper`, console script=`fmkorea-scraper`, env prefix=`FMKOREA_`

권장 사유: 저장소 namespace, Python import, CLI 실행, 환경변수 prefix가 서로 명확히 대응해 운영 중 혼동을 줄입니다.

B) 디렉터리명에 맞춰 package=`fmkorea_scraper`, console script=`fmkorea-scraper`만 고정하고 나머지는 construction 단계에서 확정

C) 기존 DCinside 이름을 최대한 유지하고 site adapter만 FMKorea로 분리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
1차 구현 범위는 어디까지로 잡을까요?

A) (권장) 전체 계승 범위 구현. direct-post, board-search, integrated-search, deep-search, no-keyword-range, realtime, comments, media, storage, retry, CLI/wizard, container, MCP, CDK까지 포함

권장 사유: 후속 커뮤니티 스크래퍼 표준으로 쓰려면 기능 표면을 처음부터 맞추는 편이 문서/테스트/운영 계약을 단순하게 유지합니다.

B) 로컬 CLI + 라이브러리 + parser/storage까지 먼저 구현하고 container/MCP/CDK는 다음 개발 사이클로 분리

C) parser와 JSONL 저장만 먼저 구현하고 JobRunner/멀티워커는 이후 구현

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
FMKorea의 노키워드 기간/글번호 범위 수집은 어떻게 구현할까요?

A) (권장) 목록 페이지를 순차 탐색하면서 상세/후보 메타데이터의 작성일과 `document_srl` 범위로 필터링한다. 전용 날짜 이동 API가 확인되면 UOW-003에서 추가

권장 사유: 지금 확인된 정보만으로 구현 가능하고, 전용 날짜 이동 API가 없어도 기능을 제공할 수 있습니다.

B) 전용 기간 이동 API를 먼저 추가 조사할 때까지 no-keyword-range 구현을 보류한다

C) FMKorea 1차 구현에서 no-keyword-range 기능은 제외한다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
통합 검색과 심층검색의 페이지 제한/종료 조건은 어떻게 둘까요?

A) (권장) 검색 결과 없음 또는 다음 페이지 없음까지 탐색하되, 안전장치로 configurable max page를 둔다. 심층검색은 통합검색으로 board 후보를 만든 뒤 board-search를 반복

권장 사유: 사이트별 실제 페이지 제한을 과하게 가정하지 않으면서도 무한 탐색 위험은 max page로 막을 수 있습니다.

B) 통합검색은 보수적으로 120페이지까지만 탐색하고, 심층검색도 같은 상한을 둔다

C) integrated-search만 구현하고 deep-search는 후속 개발로 분리한다

X) Other (please describe after [Answer]: tag below)

[Answer]: A, 단 default는 검색 결과 없음 또는 다음 페이지 없음까지 탐색

## Question 6
댓글과 답글 수집은 1차 구현에서 어떻게 다룰까요?

A) (권장) 기본 포함. 게시글 수집 시 댓글/답글을 함께 수집하되 CLI 옵션으로 끌 수 있게 한다

권장 사유: 댓글은 게시글 분석 가치가 크고, 옵션으로 비활성화할 수 있으면 속도와 저장량도 사용자가 조절할 수 있습니다.

B) 옵션을 켰을 때만 댓글/답글을 수집한다

C) 1차 구현에서는 댓글/답글을 제외하고 게시글 본문 수집을 먼저 완성한다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
본문 콘텐츠와 미디어 수집 범위는 어떻게 둘까요?

A) (권장) 전체 수집. text, image, fmk_video, youtube, x, link, attachment를 content block으로 저장하고 외부 임베드는 메타데이터만 저장

권장 사유: FMKorea 게시글은 텍스트, 이미지, 자체 영상, 외부 임베드가 섞여 있어 block 구조로 저장해야 원문 순서와 분석 가능성을 보존할 수 있습니다.

B) text, image, fmk_video만 구현하고 YouTube/X/일반 링크는 후속 개발로 분리

C) text와 URL만 저장하고 파일 다운로드는 전부 제외

X) Other (please describe after [Answer]: tag below)

[Answer]: A, 단 Polars 가공에 최적화된 구조로 설계

## Question 8
FMKorea에 재게시/공유/인용/펌 성격의 기능이 명확히 확인되지 않은 경우 모델은 어떻게 둘까요?

A) (권장) 공통 필드는 유지하되 기본값은 `is_repost=false`, `repost=null`로 둔다. 추후 기능이 확인되면 site-specific parser를 추가

권장 사유: 공통 스키마 호환성을 유지하면서, 확인되지 않은 기능을 억지로 구현하지 않을 수 있습니다.

B) UOW-004 전에 agent-browser로 별도 조사하고, 기능 존재 여부를 확정한 뒤 모델을 결정한다

C) FMKorea 원본 JSON 스키마에서는 `is_repost`, `repost` 필드를 제거한다

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 9
쿠키와 세션 정책은 어떻게 둘까요?

A) (권장) persistent cookie는 저장하지 않는다. 공개 페이지/AJAX에 필요한 transient cookie만 Job 내부에서 사용하고 로그/출력에는 남기지 않는다

권장 사유: 공개 콘텐츠 수집 범위에 맞고, 쿠키 저장으로 인한 차단/보안/로그 유출 위험을 줄일 수 있습니다.

B) Job 단위 cookie jar를 유지하고 checkpoint에는 저장하지 않는다

C) 사용자가 제공한 cookie 파일을 지원한다

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 10
저장소와 인프라 방향은 어떻게 계승할까요?

A) (권장) DCinside와 동일하게 계승. 로컬 JSONL, Garage/S3 호환 출력, PostgreSQL checkpoint, 공유 저장소 규약, ECS Fargate CDK 패턴을 유지

권장 사유: 여러 커뮤니티 스크래퍼가 같은 저장소와 운영 플랫폼을 공유하려면 저장소/체크포인트/배포 계약을 맞추는 편이 가장 안전합니다.

B) 로컬 JSONL과 Checkpoint.json만 1차 구현하고 S3/PostgreSQL/CDK는 후속 개발로 분리

C) 컨테이너 환경만 목표로 하고 로컬 저장소는 smoke/test 용도로만 둔다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
코드 생성 방식은 어떻게 할까요?

A) (권장) DCinside-Scraper 구현을 구조 템플릿으로 복사/이름 변경한 뒤 site-specific URL/query/parser만 FMKorea용으로 교체한다

권장 사유: 검증된 런타임과 저장소 코드를 재사용하고, 실제 차이가 나는 FMKorea 파서와 URL 생성기만 새로 작성하면 됩니다.

B) DCinside 문서만 참고하고 코드는 FMKorea-Scraper에서 새로 작성한다

C) 먼저 `community_scraper_core` 공통 패키지를 분리한 뒤 FMKorea를 구현한다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12: Security Extensions
Security Baseline 확장 규칙을 이 프로젝트에 적용할까요?

A) (권장) 예. 프로덕션 수준 애플리케이션 기준의 SECURITY 규칙을 blocking constraint로 적용

권장 사유: Proxy, S3, PostgreSQL, 컨테이너 환경변수를 다루므로 민감정보 로그 방지와 입력 검증을 기본으로 두는 편이 안전합니다.

B) 아니요. PoC/개인 도구 수준으로 보고 SECURITY 규칙은 생략

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13: Resiliency Extensions
Resiliency Baseline 확장 규칙을 이 프로젝트에 적용할까요?

A) (권장) 예. 장애 허용, 복구, 관측성 관련 설계 지침을 적용

권장 사유: 장시간 수집, checkpoint/resume, parser 실패 재처리, 컨테이너 운영을 다루므로 복구성과 관측성을 처음부터 요구사항에 넣어야 합니다.

B) 아니요. PoC/개인 도구 수준으로 보고 resiliency baseline은 생략

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14: Property-Based Testing Extension
Property-Based Testing 규칙을 이 프로젝트에 적용할까요?

A) (권장) 예. 파싱, 직렬화, 상태 처리에 PBT 규칙을 적용

권장 사유: URL/query, JSONL 직렬화, checkpoint, content block 순서처럼 입력 변형이 많은 로직은 property-based test로 회귀를 잡기 좋습니다.

B) 부분 적용. 순수 함수와 JSON 직렬화 round-trip에만 적용

C) 아니요. 일반 fixture 기반 테스트만 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A
