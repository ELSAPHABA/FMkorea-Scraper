# Unit Of Work Plan

이 계획은 Application Design 산출물을 바탕으로 구현 단위를 나누기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Units Generation 작업 체크리스트

- [x] Application Design 승인 확인
- [x] 요구사항, 유저 스토리, Application Design 산출물 확인
- [x] 단위 분해 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] 사용자 요청을 Unit of Work 계획 승인으로 기록
- [x] `aidlc-docs/inception/application-design/unit-of-work.md` 생성
- [x] `aidlc-docs/inception/application-design/unit-of-work-dependency.md` 생성
- [x] `aidlc-docs/inception/application-design/unit-of-work-story-map.md` 생성
- [x] Greenfield code organization strategy를 `unit-of-work.md`에 기록
- [x] 모든 스토리의 unit 배정 검증

## 설계 전제

- 단일 Python 패키지 `fmkorea_scraper`를 사용합니다.
- CLI, library, container, MCP는 같은 core API를 호출합니다.
- JobRunner 중심 orchestration과 최소 ports/adapters 경계를 적용합니다.
- FMKorea URL/query/parser는 site-specific으로 구현합니다.
- 컨테이너 JSONL/media 출력은 S3 호환 저장소를 사용하고 Garage를 기본값으로 둡니다.
- PostgreSQL checkpoint adapter는 컨테이너/공유 저장소 흐름에서 사용합니다.
- BEST 댓글은 일반 댓글과 같은 `comments` flat list에 저장합니다.

## 단위 분해 질문

### Question 1. 구현 단위 크기

전체 구현을 어떤 크기의 Unit of Work로 나눌까요?

A) (권장) 기준 프로젝트와 같은 10개 UOW를 계승한다: core models/config, HTTP runtime, search/link collection, post detail/content parsing, output/storage, job runner/checkpoint, CLI, container/MCP/test harness, parser failure retry, AWS CDK.

추천 사유: FMKorea 스크래퍼는 기능 범위가 기준 프로젝트와 거의 같습니다. 같은 UOW 구조를 쓰면 문서, 테스트, 코드 생성 순서를 재사용하기 쉽고, FMKorea-specific 차이는 각 UOW 내부에서 처리할 수 있습니다.

B) 6개 내외의 더 큰 UOW로 묶는다: core/runtime, search, detail, storage/job, adapters, infrastructure.

C) MVP 우선 단일 UOW로 두고 구현 단계에서 내부 task만 나눈다.

X) 기타

[Answer]: A

### Question 2. Parser 단위 분리

HTML parser와 URL/query builder를 어떤 단위로 묶을까요?

A) (권장) 검색/link parser는 UOW-003, 게시글 metadata/content/comment/BEST/media parser는 UOW-004에 둔다.

추천 사유: 검색 수집과 상세 수집은 입력 HTML, 실패 양상, fixture가 다릅니다. 댓글/BEST/미디어는 게시글 상세 결과를 완성하는 하위 흐름이라 UOW-004 안에서 함께 다루는 편이 자연스럽습니다.

B) 검색, 게시글 metadata, 댓글/BEST, media parser를 각각 별도 UOW로 나눈다.

C) 모든 parser를 하나의 parser UOW로 묶는다.

X) 기타

[Answer]: A

### Question 3. BEST 댓글 스키마 배치

BEST 댓글 관련 모델/파싱/저장 책임은 어떻게 배치할까요?

A) (권장) UOW-001이 `Comment` 모델 필드를 정의하고, UOW-004가 DOM에서 `is_best`, `badges`, `reactions`를 채우며, UOW-006은 받은 모델을 그대로 JSONL에 저장한다.

추천 사유: 모델, parser, storage 책임이 섞이지 않습니다. BEST 댓글을 별도 저장소 기능으로 만들 필요도 없습니다.

B) UOW-004에서 parser와 임시 dict만 만들고, UOW-006에서 저장 직전 BEST 댓글 스키마를 조립한다.

C) BEST 댓글을 별도 `best_comments` 저장 구조로 분리하는 UOW를 둔다.

X) 기타

[Answer]: A

### Question 4. Storage 단위 범위

저장소 구현 UOW에는 어디까지 포함할까요?

A) (권장) UOW-006에 local JSONL/media, failure records, S3-compatible output port, Garage 기본 object storage, local checkpoint port를 포함하고, PostgreSQL checkpoint는 UOW-008 container/test harness에서 다룬다.

추천 사유: local/S3 output은 Job 결과 저장이라는 같은 경계입니다. PostgreSQL checkpoint는 컨테이너 실행 계약과 함께 검증하는 편이 구현 순서가 단순합니다.

B) 모든 output, media, local checkpoint, PostgreSQL checkpoint를 UOW-006에 포함한다.

C) local output, S3 output, PostgreSQL checkpoint를 각각 별도 UOW로 나눈다.

X) 기타

[Answer]: A

### Question 5. JobRunner와 Output 구현 순서

`Output/Storage`와 `JobRunner/Checkpoint` 중 무엇을 먼저 구현할까요?

A) (권장) UOW-006 Output And Storage를 UOW-005 Job Runner And Checkpoint보다 먼저 구현한다.

추천 사유: JobRunner는 저장 성공 후 checkpoint를 advance해야 합니다. 저장 포트가 먼저 있어야 checkpoint ordering을 실제 코드로 검증하기 쉽습니다.

B) UOW-005 Job Runner를 먼저 만들고 저장소는 fake/in-memory로 대체한다.

C) UOW-005와 UOW-006을 하나로 합친다.

X) 기타

[Answer]: A

### Question 6. Realtime, Deep Search, No-keyword 배치

실시간 수집, 심층검색, 노키워드 범위 수집은 어느 UOW에 배치할까요?

A) (권장) 후보 링크 수집 전략은 UOW-003에 포함하고, 종료 조건/checkpoint/resume 검증은 UOW-005와 통합 테스트로 다룬다.

추천 사유: 세 기능 모두 게시글 후보를 queue에 넣는 link collection 전략입니다. 다만 실시간 종료와 checkpoint는 JobRunner 책임이 강하므로 경계 통합 검증이 필요합니다.

B) 실시간 수집, 심층검색, 노키워드 수집을 각각 별도 UOW로 나눈다.

C) 1차 구현에서는 일반 검색만 만들고 세 기능은 후속 UOW로 미룬다.

X) 기타

[Answer]: A

### Question 7. Adapter 구현 순서

CLI, container, MCP adapter는 어떤 순서로 구현할까요?

A) (권장) UOW-007에서 CLI와 터미널 마법사를 먼저 구현하고, UOW-008에서 container, PostgreSQL checkpoint, MCP, fixture/smoke harness를 구현한다.

추천 사유: CLI가 Job 설정과 실행 흐름을 가장 빨리 검증합니다. container/MCP는 core API가 안정된 뒤 얇은 wrapper로 붙이는 편이 수정 비용이 낮습니다.

B) CLI, container, MCP를 하나의 adapter UOW에서 같이 구현한다.

C) MCP를 먼저 구현해 agent 호출 흐름을 우선 검증한다.

X) 기타

[Answer]: A

### Question 8. AWS CDK UOW 위치

AWS CDK IaC는 어느 시점의 UOW로 둘까요?

A) (권장) UOW-009 parser failure retry 이후 UOW-010으로 둔다.

추천 사유: CDK는 scraper runtime/container/storage/checkpoint 계약이 확정된 뒤 작성해야 합니다. 먼저 만들면 이후 runtime 변경을 IaC에 반복 반영해야 합니다.

B) container가 생기는 UOW-008과 함께 CDK를 구현한다.

C) CDK는 이번 AI-DLC 구현 범위에서 제외한다.

X) 기타

[Answer]: A

### Question 9. 팀/소유권 기준

향후 여러 사람이 작업한다면 UOW 소유권은 어떻게 잡을까요?

A) (권장) 기능 경계별 소유로 둔다: core/runtime/search/detail/storage/job/adapters/retry/infra.

추천 사유: 현재는 개인 프로젝트에 가깝지만, 향후 후속 커뮤니티 스크래퍼와 통합 플랫폼으로 확장할 계획이 있습니다. 기능 경계별 소유가 나중에 병렬 작업하기 쉽습니다.

B) 레이어별 소유로 둔다: models/parsers/jobs/outputs/adapters.

C) 별도 소유권 기준은 지금 문서화하지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 Unit of Work 계획 승인을 요청합니다.
4. 승인 후 `unit-of-work.md`, `unit-of-work-dependency.md`, `unit-of-work-story-map.md`를 생성합니다.

## 답변 분석 결과

- 모든 `[Answer]:` 항목이 채워졌다.
- 모든 답변은 `A`로, 권장 선택지와 일치한다.
- 답변 간 충돌은 없다.
- "depends", "혼합", "나중에", "모름" 같은 모호한 답변은 없다.
- follow-up 질문은 필요하지 않다.
- Units Generation Part 2 산출물 생성 전 사용자 승인이 필요하다.

## 승인 요청

Unit of Work 계획이 완료되었습니다. `aidlc-docs/inception/plans/unit-of-work-plan.md`의 분해 계획을 검토해 주세요.

승인하면 다음 산출물을 생성합니다.

- `aidlc-docs/inception/application-design/unit-of-work.md`
- `aidlc-docs/inception/application-design/unit-of-work-dependency.md`
- `aidlc-docs/inception/application-design/unit-of-work-story-map.md`
