# Functional Design Plan - UOW-008 Container, MCP, And Test Harness

이 계획은 `UOW-008 Container, MCP, And Test Harness`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-008 Container, MCP, And Test Harness
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter
- **Primary Stories**: US-016, US-017
- **Supporting Stories**: US-002, US-010, US-012, US-013, US-015
- **Scope**: one-shot worker container entrypoint, container environment mapping, PostgreSQL checkpoint adapter, S3-compatible/Garage output wiring, MCP tool adapter, fixture/PBT/live-smoke test harness
- **Out Of Scope**: scraper parsing logic, HTTP retry policy internals, worker queue internals, CLI wizard UX, parser-failure retry execution engine, CAPTCHA bypass, GUI/Web UI, distributed scheduler, AWS CDK

## Functional Design 작업 체크리스트

- [x] UOW-007 Build and Test 승인 확인
- [x] UOW-008 범위 확인
- [x] UOW-001~UOW-007 계약 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. Container Entrypoint Shape

컨테이너 실행 진입점은 어떻게 둘까요?

A) (권장) 루트에 `docker-entrypoint.sh`와 `.dockerignore`를 생성하고 Dockerfile `ENTRYPOINT`가 이 스크립트를 호출한다. `.dockerignore`는 `.git`, 가상환경, 테스트 캐시, 출력물, `.env` 계열 secret 후보, 문서 산출물을 build context에서 제외한다. 스크립트는 전달받은 argv를 유지한 채 `python -m fmkorea_scraper.adapters.container "$@"`로 위임하고, `fmkorea_scraper.adapters.container.main()`이 실제 실행을 담당한다. 새 Job 설정은 UOW-007 CLI와 같은 command dict/builders를 재사용하고, container 전용 저장소/재개 설정은 환경변수로 주입한다.

추천 사유: UOW-007에서 이미 검증된 `JobConfig` 변환 경로가 있습니다. 컨테이너가 별도 설정 문법을 만들면 같은 validation을 두 번 유지해야 합니다.

B) 컨테이너는 `JOB_CONFIG_JSON` 환경변수 하나만 읽고 CLI 인자 형태는 받지 않는다.

C) 별도 container adapter 없이 Docker entrypoint가 `fmkorea-scraper` CLI를 그대로 실행한다.

X) 기타

[Answer]: A

### Question 2. Container Job Options

컨테이너의 Job 옵션 입력은 어떤 구조로 둘까요?

A) (권장) Job source/options는 container argv로 받고, 의미는 UOW-007 `run` 명령 옵션과 동일하게 둔다. 환경변수는 저장소, 재개, secret, realtime 종료 조건처럼 container/runtime에 가까운 값만 맡는다.

추천 사유: 사용자가 로컬 CLI와 컨테이너에서 같은 Job 옵션을 사용할 수 있고, 환경변수는 secret/runtime 값에 집중됩니다.

B) 모든 Job 옵션과 저장소 옵션을 환경변수로만 받는다.

C) 모든 Job 옵션을 JSON 파일 마운트로만 받는다.

X) 기타

[Answer]: A

### Question 3. Container Resume Flow

컨테이너 재개 flow는 어떻게 둘까요?

A) (권장) `RESUME=true`이면 `JOB_ID`가 있을 때 해당 checkpoint를, 없으면 PostgreSQL checkpoint store의 최신 checkpoint를 재개한다. `RESUME`이 true가 아니면 새 Job을 실행한다.

추천 사유: UOW-005 `ResumeRequest(job_id=None)` 계약과 기존 요구사항의 최신 checkpoint 재개 요구가 그대로 맞습니다.

B) 재개 시 항상 `JOB_ID`를 필수로 요구한다.

C) 컨테이너 재개는 UOW-008에서 제외하고 CLI resume만 지원한다.

X) 기타

[Answer]: A

### Question 4. Container Storage Boundary

컨테이너에서 결과와 checkpoint 저장소는 어떻게 조합할까요?

A) (권장) 컨테이너 기본값은 S3-compatible/Garage output + PostgreSQL checkpoint로 둔다. local filesystem은 S3 JSONL spool 같은 임시 작업 공간에만 사용한다.

추천 사유: 여러 scraper 컨테이너가 공유 저장소를 쓰는 향후 플랫폼 구조와 가장 잘 맞습니다. local volume 기반 checkpoint는 컨테이너 교체/재시작에 약합니다.

B) 컨테이너도 기본값을 local JSONL + local `Checkpoint.json`으로 둔다.

C) 컨테이너 실행마다 local/S3/PostgreSQL 조합을 모두 자유롭게 선택하게 한다.

X) 기타

[Answer]: A

### Question 5. PostgreSQL Checkpoint Store

PostgreSQL checkpoint adapter는 어떤 구조로 둘까요?

A) (권장) `PostgresCheckpointStore`를 UOW-006 checkpoint port 구현체로 추가하고, 단일 테이블 `fmkorea_checkpoints(job_id primary key, updated_at, checkpoint_json json/jsonb)`에 checkpoint 전체를 저장한다. `load_latest()`는 `updated_at desc` 기준으로 조회한다.

추천 사유: 기존 `Checkpoint` 모델을 그대로 저장하면 schema migration 범위가 작고, container resume 요구사항을 바로 만족합니다.

B) checkpoint 필드를 모두 PostgreSQL 컬럼으로 정규화한다.

C) UOW-008에서는 PostgreSQL adapter를 만들지 않고 local `Checkpoint.json`을 볼륨으로만 사용한다.

X) 기타

[Answer]: A

### Question 6. S3-Compatible/Garage Output Semantics

컨테이너에서 JSONL과 media를 S3-compatible/Garage 저장소에 쓰는 방식은 어떻게 둘까요?

A) (권장) 기존 UOW-006 S3-compatible output 구조를 container에서 사용하고, JSONL append는 local spool + durable object upload 성공을 기준으로 처리한다. media와 report도 저장 성공 후 `StoredObjectRef`를 반환한다.

추천 사유: S3 계열 저장소는 append가 없으므로 spool이 필요합니다. 동시에 checkpoint는 output 저장 성공 이후에만 전진한다는 UOW-005 계약을 지켜야 합니다.

B) 실행 중에는 local temp에만 쓰고 Job 종료 시 한 번에 S3로 업로드한다.

C) JSONL 대신 게시글마다 별도 JSON object를 저장한다.

X) 기타

[Answer]: A

### Question 7. Container Environment Variables

컨테이너가 읽을 환경변수 범위는 어디까지 둘까요?

A) (권장) 필수 저장소 env는 `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`로 두고, 선택 env는 `S3_REGION`, `S3_FORCE_PATH_STYLE`, `S3_PREFIX`, `RESUME`, `JOB_ID`, `FMKOREA_REALTIME_*`, `FMKOREA_PROXY_*`, User-Agent 파일 경로로 둔다. 사용자 제공 cookie 입력은 받지 않는다.

추천 사유: 저장소/secret은 컨테이너 환경변수와 잘 맞고, Job 옵션은 UOW-007 CLI 경로로 재사용할 수 있습니다. FMKorea 전용 env는 기존 prefix 정책과 일관됩니다.

B) 모든 Job 옵션과 저장소 옵션을 `FMKOREA_*` prefix 환경변수로만 받는다.

C) 컨테이너는 `.env` 파일만 읽고 `docker run -e` 환경변수는 직접 읽지 않는다.

X) 기타

[Answer]: A

### Question 8. Container Stop And Exit Codes

컨테이너 종료와 signal 처리는 어떻게 둘까요?

A) (권장) `SIGTERM`/첫 `SIGINT`는 `JobRunner.stop(StopReason.MANUAL_STOP)`로 graceful stop을 요청하고, report status에 따라 exit code `0/1/2`를 반환한다. 두 번째 interrupt나 강제 종료는 best-effort cleanup 후 `1`로 둔다.

추천 사유: UOW-007 Ctrl+C 경계와 UOW-005 checkpoint 저장 흐름을 컨테이너 signal에도 그대로 적용할 수 있습니다.

B) 컨테이너 signal을 직접 처리하지 않고 프로세스 즉시 종료에 맡긴다.

C) 모든 stopped 상태도 성공 exit code `0`으로 처리한다.

X) 기타

[Answer]: A

### Question 9. MCP Tool Scope

MCP tool은 1차로 어디까지 제공할까요?

A) (권장) `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, `retry_parser_failures` tool shape를 제공한다. 단, `retry_parser_failures` 실행은 UOW-009 전까지 safe unsupported 응답으로 둔다.

추천 사유: MCP 인터페이스 이름은 미리 고정할 수 있지만, parser-failure retry 엔진을 UOW-008에서 앞당겨 만들 필요는 없습니다.

B) 조회성 tool인 search/fetch만 제공하고 Job run/resume/retry는 제외한다.

C) Job run/resume만 제공하고 search/fetch/retry는 제외한다.

X) 기타

[Answer]: A

### Question 10. MCP Job Execution Mode

MCP의 `run_job`/`resume_job`은 어떻게 실행할까요?

A) (권장) 1차 구현은 동기식 one-shot 호출로 두고, tool 호출이 끝나면 JSON-serializable `JobReport`를 반환한다. background Job registry, cancel tool, progress polling은 후속 플랫폼 단계로 둔다.

추천 사유: UOW-005 JobRunner는 이미 one-shot 실행을 지원합니다. 별도 scheduler를 만들면 UOW-008 범위가 커집니다.

B) MCP 서버 내부에 background job registry를 만들고 `run_job`은 즉시 job handle을 반환한다.

C) MCP에서는 Job 실행을 금지하고 단건 fetch/search만 허용한다.

X) 기타

[Answer]: A

### Question 11. Adapter Error Shape

컨테이너와 MCP 오류 응답은 어떻게 만들까요?

A) (권장) 모든 adapter 오류는 `ErrorMapper`를 사용해 safe code/message/details로 변환한다. 컨테이너는 exit code `0/1/2`, MCP는 JSON-serializable error object를 반환하며 stack trace, Proxy password, raw env, raw HTTP body는 노출하지 않는다.

추천 사유: UOW-001/UOW-007에서 이미 안전 오류 매핑 경계를 사용하고 있어 재사용 비용이 가장 작습니다.

B) container와 MCP에서 원본 exception 문자열과 traceback을 그대로 반환한다.

C) 모든 오류를 하나의 `"failed"` 메시지로만 반환한다.

X) 기타

[Answer]: A

### Question 12. Result Quality And Smoke Harness

결과 품질 검토와 smoke test는 어떻게 나눌까요?

A) (권장) 기본 테스트는 static JSONL/report/failure fixture, fake dependencies, PBT로 실행한다. 품질 검사는 필수 top-level 필드, content block/media/comment/BEST comment shape, optional/null 표현, failure/report count, safe failure context를 확인한다. Docker, Garage, PostgreSQL, MCP server, live FMKorea smoke는 env-gated optional smoke로 둔다.

추천 사유: 기본 테스트는 빠르고 재현 가능해야 합니다. 외부 서비스가 필요한 검증은 명시적으로 켤 때만 실행하는 편이 CI와 로컬 모두 안정적입니다.

B) 기본 테스트에서 Docker compose로 PostgreSQL과 Garage를 항상 띄운다.

C) 품질 검토와 smoke test는 문서로만 남기고 자동 테스트는 만들지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-008 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-008 NFR Requirements로 넘어가지 않습니다.
