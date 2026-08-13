# Functional Design 계획 - UOW-007 CLI Adapter

이 계획은 `UOW-007 CLI Adapter`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-007 CLI Adapter
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage
- **Primary Stories**: US-001
- **Related Stories**: US-002, US-003, US-006, US-013, US-014, US-015
- **Scope**: CLI entrypoint, argument parsing, terminal wizard, `JobConfig`/`ResumeRequest`/`RetryRequest` creation, local dependency assembly, local output/checkpoint wiring, User-Agent import flow, Proxy `.env` flow, resume command, parser-failure retry command shell, safe terminal messages
- **Out Of Scope**: FMKorea HTML selector logic, search traversal internals, post parser internals, worker queue internals, container entrypoint, PostgreSQL checkpoint adapter, Garage provisioning, MCP tools, GUI/Web UI, AWS CDK

## Scope Notes

- UOW-007는 `fmkorea-scraper` console script와 `fmkorea_scraper.adapters.cli` 모듈을 제공한다.
- 터미널 마법사는 이번 UOW-007 1차 구현 범위에 포함한다.
- 별도 `python main.py` 루트 스크립트는 UOW-007 당시 필수 범위로 두지 않았다. 이후 기준 프로젝트 정렬을 위해 루트 `main.py` 호환 wrapper를 추가했다.
- CLI는 core scraping 로직을 새로 구현하지 않고 UOW-001~UOW-006의 public API와 service를 연결한다.
- 질문지의 A 선택지는 기준 프로젝트 구조를 최대한 계승하는 권장안이다.

## Functional Design 작업 체크리스트

- [x] UOW-005 Build and Test 승인 확인
- [x] UOW-007 범위 확인
- [x] UOW-001~UOW-006 계약 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-007-cli-adapter/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-007-cli-adapter/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-007-cli-adapter/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. CLI Entrypoint

CLI 진입점은 어디에 둘까요?

A) (권장) `fmkorea_scraper.adapters.cli`에 `main(argv: list[str] | None = None) -> int`를 두고, `pyproject.toml` console script `fmkorea-scraper`가 이 함수를 호출한다. import만으로 실행, 파일 생성, 환경변수 읽기, 네트워크 요청은 하지 않는다.

추천 사유: 기준 구조의 import-safe adapter 방식을 그대로 계승하면서, 테스트에서 `main([...])`을 직접 호출할 수 있습니다.

B) `fmkorea_scraper.core.api`에 CLI parsing까지 넣는다.

C) 프로젝트 루트에 독립 실행 스크립트만 둔다.

X) 기타

[Answer]: A

### Question 2. Command Shape

CLI 명령 구조는 어떻게 둘까요?

A) (권장) 표준 라이브러리 `argparse` 기반으로 `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, `wizard` subcommand를 둔다. `run`은 `--source direct-post|board-list|board-search|integrated-search|deep-search|no-keyword-range`를 받는다.

추천 사유: 새 CLI 의존성을 추가하지 않고, 실행/재개/재처리/설정/마법사 책임을 분리할 수 있습니다.

B) subcommand 없이 하나의 명령에 모든 옵션을 flat하게 둔다.

C) 모든 입력을 대화형 prompt로만 받는다.

X) 기타

[Answer]: A

### Question 3. JobConfig Mapping

CLI 인자를 `JobConfig`, `ResumeRequest`, `RetryRequest`로 바꾸는 로직은 어디에 둘까요?

A) (권장) `build_job_config(args) -> JobConfig`, `build_resume_request(args) -> ResumeRequest`, `build_retry_request(args) -> RetryRequest` 같은 순수 변환 함수를 두고, Pydantic validation 오류를 CLI가 안전한 메시지와 exit code로 변환한다.

추천 사유: validation은 UOW-001 모델이 이미 담당합니다. CLI는 raw input을 dict/model로 조립하고 메시지를 바꾸는 얇은 계층이면 충분합니다.

B) `main()` 안에서 raw dict를 만들고 바로 runner에 넘긴다.

C) `JobRunner`가 `argparse.Namespace`를 직접 해석하게 한다.

X) 기타

[Answer]: A

### Question 4. Source Option Mapping

수집 source별 CLI 옵션은 어떻게 매핑할까요?

A) (권장) UOW-001 source 모델 이름을 그대로 따른다. `direct-post`는 `--url` 반복 또는 파일 입력, `board-list`/`board-search`/`no-keyword-range`는 `--board-id`, `--category-id`, page/range 옵션, `integrated-search`/`deep-search`는 keyword/search-target/range 옵션을 받아 기존 source 모델로 변환한다.

추천 사유: CLI 전용 source 개념을 새로 만들지 않고, 이미 검증된 `JobSource` union에 바로 매핑할 수 있습니다.

B) CLI 사용성을 위해 source 이름과 옵션명을 모델과 다르게 새로 설계한다.

C) 1차 CLI는 direct-post만 지원하고 나머지는 후속으로 미룬다.

X) 기타

[Answer]: A

### Question 5. Realtime Env Flow

실시간 수집 옵션은 CLI에서 어떻게 다룰까요?

A) (권장) 확정 요구사항대로 `FMKOREA_REALTIME_*` 환경변수를 읽어 `RealtimeKeywordSource` 또는 `RealtimeAllSource`를 만든다. `FMKOREA_REALTIME_DURATION_SECONDS`와 `FMKOREA_REALTIME_END_AT`은 정확히 하나만 허용하고, realtime이 활성화된 상태에서 일반 `--source`와 충돌하면 validation 오류로 중단한다.

추천 사유: 실시간 수집은 환경변수 기반으로 확정되어 있습니다. 같은 기능에 CLI flag 입력 경로를 하나 더 만들면 충돌 규칙이 늘어납니다.

B) 실시간 수집도 `run --source realtime-keyword|realtime-all` 플래그로만 받는다.

C) 실시간 수집은 UOW-008 container 전용으로 미루고 CLI에서는 지원하지 않는다.

X) 기타

[Answer]: A

### Question 6. Run ID And Storage Assembly

현재 `JobRunner`는 `run_id`를 내부에서 생성하고, UOW-006 `StorageFactory`는 `run_id`를 받아 저장소를 만듭니다. CLI 조립 단계에서 이 접점은 어떻게 정리할까요?

A) (권장) UOW-007에서 `JobRunner.run(..., run_id=None)`과 `JobRunner.resume(..., run_id=None)` 같은 backward-compatible 선택 인자를 추가한다. CLI는 먼저 `run_id`를 생성해 `StorageFactory`와 `JobRunner`에 같은 값을 넘기고, 기존 테스트/라이브러리 사용자는 생략 시 내부 생성 동작을 유지한다.

추천 사유: 새 factory layer를 만들지 않고 UOW-005/UOW-006의 불일치만 최소 변경으로 해결합니다. resume이 새 `run_id`를 가져야 한다는 기존 규칙도 유지됩니다.

B) UOW-007에서 storage를 fake/in-memory로 우회하고 실제 local output은 UOW-008로 미룬다.

C) `StorageFactory`를 `run_id` 없이 만들 수 있도록 UOW-006 저장소 구조를 크게 바꾼다.

X) 기타

[Answer]: A

### Question 7. Runtime Dependency Assembly

CLI는 코어 실행 의존성을 어디까지 직접 조립할까요?

A) (권장) CLI가 `HttpClient`, collector, detail parser/service, `StorageFactory`, `JobRunner`, `JobRunDependencies`를 생성하고 `core.api.run_job()` 또는 `core.api.resume_job()`에 주입한다. 검색/파싱/저장 순서 자체는 CLI에 넣지 않는다.

추천 사유: UOW-007은 adapter입니다. 이미 구현된 core/service/storage를 연결하는 선에서 끝내는 것이 가장 작고 기준 구조와도 맞습니다.

B) CLI가 검색, 게시글 수집, 저장 순서를 직접 실행한다.

C) CLI는 config 파일만 생성하고 실행은 하지 않는다.

X) 기타

[Answer]: A

### Question 8. Output And Checkpoint Location

로컬 실행의 출력 경로와 checkpoint 경로는 어떻게 정할까요?

A) (권장) `--output-path`를 `StorageConfig.base_output_path`에 매핑하고, 생략하면 현재 작업 디렉터리를 사용한다. `Checkpoint.json`과 `outputs/<job_id>/<run_id>/...` 레이아웃은 UOW-006 `OutputRunLayout` 규칙을 그대로 따른다.

추천 사유: 저장소 레이아웃은 이미 UOW-006에서 확정됐습니다. CLI가 파일 경로 규칙을 다시 구현할 필요가 없습니다.

B) 항상 실행 파일이 있는 디렉터리에 저장한다.

C) 항상 사용자 홈 디렉터리에 저장한다.

X) 기타

[Answer]: A

### Question 9. User-Agent, Proxy, Cookie Setup

User-Agent 파일, Proxy, cookie flow는 어떻게 둘까요?

A) (권장) `--user-agent-file`, `--user-agent-rotate-every`는 현재 실행에 적용한다. `import-user-agents`는 선택한 파일을 실행 기준 디렉터리의 `user-agents.txt`로 복사한다. `configure-proxy`는 host, ID, PW를 입력받아 평문 `.env`에 `FMKOREA_PROXY_*`로 저장하되 저장 전 보안 경고를 출력한다. 실행 시 Proxy는 명시 옵션, `.env`, 비활성 순서로 적용한다. 사용자 제공 cookie 파일 옵션은 만들지 않고, 서버 임시 cookie는 UOW-002 `HttpClient` 메모리 정책을 따른다.

추천 사유: 기준 프로젝트와 동일하게 User-Agent/Proxy만 CLI 입력으로 다루고, cookie 파일 입력 경로를 만들지 않아 secret 노출면을 줄일 수 있습니다.

B) CLI에서는 User-Agent/Proxy/cookie 설정을 다루지 않고 파일이 있으면 자동 사용만 한다.

C) 매 실행마다 Proxy, User-Agent, cookie 경로를 모두 prompt로 묻는다.

X) 기타

[Answer]: A

### Question 10. Scrape And Worker Options

본문/댓글/미디어/요청 간격/worker 수 같은 실행 옵션은 어떤 CLI 옵션으로 둘까요?

A) (권장) `--comment-mode`, `--media-mode`, `--include-attachments/--no-attachments`, `--request-interval-seconds`, `--max-post-retries`, `--max-comment-pages`, `--max-content-blocks`, `--max-comments`, `--post-worker-count`, `--media-worker-count`, `--queue-max-size`, `--timeout-seconds`를 둔다. 수집/파서/워커 값은 `ScrapeOptions`, `WorkerConfig`에 저장하고, timeout/User-Agent/Proxy 같은 실행값은 `JobConfig`에 저장하지 않고 `HttpRuntimeConfig`로 직접 조립한다.

추천 사유: 이미 모델 필드가 있으므로 CLI 옵션명만 얇게 붙이면 됩니다. FMKorea에 없는 site-specific 옵션은 만들지 않습니다.

B) 우선 기본값만 사용하고 CLI 옵션은 후속 unit으로 미룬다.

C) 옵션 파일로만 받는다.

X) 기타

[Answer]: A

### Question 11. Terminal Wizard

터미널 마법사는 어떤 범위로 만들까요?

A) (권장) `fmkorea-scraper wizard`에서 번호 입력식 메뉴를 제공한다. 메뉴는 `1. 스크래핑 시작`, `2. 재개`, `3. Parser 실패 재처리`, `4. User-Agent 가져오기`, `5. Proxy 설정`, `6. 종료` 정도로 시작하고, 내부에서는 명령형 CLI와 같은 builder 함수를 재사용한다.

추천 사유: 사용자가 요청한 번호 입력식 흐름을 제공하면서도 별도 실행 로직을 만들지 않습니다.

B) 마법사는 `run` 명령 옵션을 생성해 보여주기만 하고 실행하지 않는다.

C) 마법사는 이번 UOW에서 제외한다.

X) 기타

[Answer]: A

### Question 12. Terminal Output And Exit Codes

터미널 출력과 종료 코드는 어떻게 정할까요?

A) (권장) 시작 시 `job_id`, `run_id`, output path, source summary, worker count, request interval을 출력하고, 종료 시 report summary와 resume command를 출력한다. 성공은 exit code `0`, validation/usage 오류는 `2`, 수집 중단/CAPTCHA/block/runtime 오류는 `1`로 둔다. Proxy password, raw `.env`, cookie, raw HTML, raw traceback은 기본 출력하지 않고 `--debug`에서만 traceback을 허용한다.

추천 사유: 사람이 필요한 정보와 shell 자동화에 필요한 실패 구분은 제공하면서, secret과 raw response 노출을 피할 수 있습니다.

B) 전체 config와 exception traceback을 항상 출력한다.

C) 기본 출력은 없고 파일 report만 남긴다.

X) 기타

[Answer]: A

### Question 13. Test Scope

UOW-007 기본 테스트 범위는 어디까지 둘까요?

A) (권장) live network 없이 `argparse` parsing, builder 함수, realtime env validation, run_id/storage assembly, User-Agent import copy, Proxy `.env` writer redaction, wizard input flow, import side-effect 없음, fake runner/core API 호출을 단위 테스트한다.

추천 사유: CLI adapter의 핵심은 입력 변환과 의존성 조립입니다. 실제 FMKorea 접속은 선택적 smoke test로 남기는 편이 안정적입니다.

B) 실제 FMKorea 페이지를 호출하는 CLI 통합 테스트를 기본 테스트로 둔다.

C) CLI는 수동 테스트만 하고 자동 테스트는 UOW-008로 미룬다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-007 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-007 NFR Requirements로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-007 Functional Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q13 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Key Implementation Note**: Q6 requires a small backward-compatible runner API change so CLI can create one `run_id` and pass it to both `StorageFactory` and `JobRunner`. Existing `JobRunner.run(config)` and `JobRunner.resume(request)` behavior remains valid when the optional `run_id` is omitted.
