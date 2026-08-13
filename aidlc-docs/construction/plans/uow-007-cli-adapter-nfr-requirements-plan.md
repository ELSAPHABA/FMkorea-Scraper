# NFR Requirements 계획 - UOW-007 CLI Adapter

이 계획은 `UOW-007 CLI Adapter`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-007 CLI Adapter
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage
- **Primary Stories**: US-001
- **Related Stories**: US-002, US-003, US-006, US-013, US-014, US-015
- **Scope**: terminal command UX, terminal wizard UX, safe error/debug traceback output, import side-effect safety, Proxy/User-Agent/cookie file operations, runtime dependency lifecycle, Ctrl+C stop handling, run id/storage alignment, adapter tests
- **Security Focus**: proxy credential input, `.env` plaintext warning, debug traceback redaction boundary, no raw cookie/header/body/env output, import safety
- **Resiliency Focus**: graceful interrupt, final checkpoint preservation through UOW-005, dependency cleanup, file write safety for `user-agents.txt` and `.env`
- **PBT Focus**: CLI argument/wizard answer to model mapping, realtime env validation, exit code mapping, safe output redaction, path/filename handling for local config files
- **Out Of Scope**: scraper parsing correctness, HTTP retry policy internals, worker queue scheduling, storage layout internals, Docker entrypoint, MCP adapter, GUI/Web UI, AWS CDK

## NFR Requirements 작업 체크리스트

- [x] UOW-007 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-007-cli-adapter/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-007-cli-adapter/nfr-requirements/tech-stack-decisions.md` 생성

## NFR Requirements Questions

### Question 1. CLI Dependency Policy

CLI 구현 의존성은 어떻게 둘까요?

A) (권장) 표준 라이브러리 `argparse`, `getpass`, `shutil`, `traceback`, `signal`, `uuid`, `input`만 사용하고 Click/Typer/Rich 같은 새 CLI/TUI 의존성은 추가하지 않는다.

추천 사유: 명령형 CLI와 번호 입력식 마법사는 표준 라이브러리로 충분합니다. 새 의존성 없이 테스트하기도 쉽습니다.

B) Typer 또는 Click을 기본 의존성으로 추가한다.

C) Rich를 추가해 progress bar와 색상 UI를 만든다.

X) 기타

[Answer]: A

### Question 2. Debug Traceback And Safe Error Output

Functional Design에서 확정한 `--debug` traceback 출력은 어떤 안전 규칙으로 제한할까요?

A) (권장) 오류 발생 시 항상 safe summary를 먼저 출력하고, `--debug`가 있을 때만 `traceback.format_exception()` 수준의 traceback을 출력한다. locals/config dump/raw exception details 출력은 금지한다.

추천 사유: 디버깅 경로는 열어 두되, proxy password, raw `.env`, cookie, raw header/body/html이 기본 출력될 가능성을 줄일 수 있습니다.

B) Python 기본 예외 traceback을 항상 그대로 터미널에 흘린다.

C) traceback은 절대 출력하지 않는다.

X) 기타

[Answer]: A

### Question 3. Proxy Credential Input Safety

`configure-proxy`의 credential 입력은 어떻게 처리할까요?

A) (권장) host와 ID는 일반 입력으로 받고, password는 `getpass.getpass()`로 echo 없이 입력받는다. 저장 전 평문 `.env` 경고를 출력하고, 저장 후에도 password는 출력하지 않는다.

추천 사유: `.env` 평문 저장은 요구사항상 허용되지만, 터미널 입력 echo와 로그 노출은 줄일 수 있습니다.

B) host, ID, password를 모두 일반 `input()`으로 받는다.

C) 터미널 입력 없이 CLI 인자로만 받는다.

X) 기타

[Answer]: A

### Question 4. `.env` Write Policy

`configure-proxy`가 기존 `.env` 파일을 만났을 때 어떻게 쓸까요?

A) (권장) 기존 `.env`가 있으면 `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, `FMKOREA_PROXY_PW`만 갱신하고 나머지 줄은 보존한다. 없으면 새로 만든다.

추천 사유: 사용자가 편집 가능한 평문 파일이므로 전체 덮어쓰기는 불필요한 데이터 손실 위험이 있습니다.

B) 기존 `.env` 전체를 Proxy 세 줄로 덮어쓴다.

C) 기존 `.env`가 있으면 실패하고 사용자가 직접 수정하게 한다.

X) 기타

[Answer]: A

### Question 5. User-Agent Import Safety

`import-user-agents`는 어떤 파일 안전 규칙을 적용할까요?

A) (권장) source file이 읽을 수 있는 일반 파일인지 확인하고, 실행 기준 디렉터리의 `user-agents.txt`로 복사한다. 복사 전 UTF-8 텍스트로 읽어 빈 줄 제외 최소 1개 항목이 있는지만 확인한다.

추천 사유: 런타임이 세부 User-Agent validation과 fallback을 담당하므로 import command는 파일 안전성과 빈 파일 방지만 처리하면 충분합니다.

B) 아무 파일이나 그대로 복사한다.

C) 모든 User-Agent 문자열의 브라우저/OS 문법을 엄격히 검증한다.

X) 기타

[Answer]: A

### Question 6. Ctrl+C And Manual Stop

사용자가 수집 중 Ctrl+C를 누르면 어떻게 처리할까요?

A) (권장) 첫 Ctrl+C는 `JobRunner.stop(StopReason.MANUAL_STOP)`으로 graceful stop을 요청하고 최종 checkpoint/report 생성을 기다린다. 두 번째 Ctrl+C는 best-effort cleanup 후 exit code `1`로 종료한다.

추천 사유: UOW-005가 이미 manual stop checkpoint 경계를 제공합니다. CLI는 이를 터미널 signal에 연결하면 됩니다.

B) Ctrl+C는 즉시 프로세스를 종료한다.

C) Ctrl+C를 무시하고 Job이 끝날 때까지 계속 실행한다.

X) 기타

[Answer]: A

### Question 7. Runtime Cleanup

CLI 실행 중 오류나 중단이 발생했을 때 runtime cleanup은 어디까지 보장할까요?

A) (권장) `HttpClient`는 async context 또는 `try/finally`로 닫고, output/checkpoint store는 기존 UOW-006 원자적/append 규칙에 맡긴다. cleanup 실패는 safe warning만 출력한다.

추천 사유: HTTP 연결과 쿠키는 명시적으로 닫아야 하고, 저장소는 이미 각 unit의 쓰기 규칙을 갖고 있습니다.

B) cleanup을 별도로 처리하지 않고 프로세스 종료에 맡긴다.

C) 모든 실패에서 output 디렉터리를 삭제해 정리한다.

X) 기타

[Answer]: A

### Question 8. Run ID Generation And Testability

CLI가 `StorageFactory`와 `JobRunner`에 넘길 `run_id`는 어떻게 생성하고 테스트할까요?

A) (권장) 기본 생성은 표준 라이브러리 `uuid.uuid4().hex` 기반 `run-<hex>`를 사용하고, 테스트에서는 run id factory를 주입해 deterministic 값을 사용한다.

추천 사유: 저장소 경로 충돌을 피하면서도 테스트에서 `run_id` 정합성을 쉽게 검증할 수 있습니다.

B) 현재 timestamp 문자열만 사용한다.

C) 사용자가 매번 `--run-id`를 직접 입력하게 한다.

X) 기타

[Answer]: A

### Question 9. Wizard UX Boundary

마법사 메뉴의 UX 범위는 어디까지 둘까요?

A) (권장) 번호 입력식 텍스트 메뉴만 제공한다. 각 단계에서 기본값을 표시하고, 잘못된 입력은 안전한 메시지 후 다시 입력받는다. `q` 또는 빈 필수값 취소로 이전 메뉴/종료가 가능해야 하며, input/output stream은 테스트에서 주입 가능하게 한다.

추천 사유: 사용성은 확보하면서도 TUI 프레임워크나 복잡한 상태 머신 없이 구현할 수 있습니다.

B) 잘못된 입력이 있으면 즉시 exit code `2`로 종료한다.

C) progress bar, 색상, 키보드 네비게이션을 포함한 TUI로 만든다.

X) 기타

[Answer]: A

### Question 10. CLI Test Gate

UOW-007 기본 test gate는 어디까지 둘까요?

A) (권장) live network 없이 import side-effect, argparse parsing, wizard input/output flow, `build_job_config`, `build_resume_request`, `build_retry_request`, realtime env validation, exit code mapping, run id/storage alignment, fake runner invocation, Ctrl+C graceful stop hook, User-Agent import, Proxy `.env` writer를 테스트한다.

추천 사유: CLI adapter의 핵심은 입력 변환과 조립입니다. 실제 FMKorea 접속은 기본 gate에 넣으면 느리고 불안정합니다.

B) 기본 테스트에서 실제 FMKorea 수집을 실행한다.

C) CLI는 수동 테스트만 하고 자동 테스트는 UOW-008로 미룬다.

X) 기타

[Answer]: A

### Question 11. Property-Based Test Scope

UOW-007에서 Property-Based Test는 어디에 적용할까요?

A) (권장) source별 CLI args/wizard answers to `JobConfig` mapping, realtime env exactly-one 종료 조건, exit code mapping, safe error field redaction, config file path handling 같은 순수 변환에만 적용한다.

추천 사유: PBT는 순수 함수에 잘 맞습니다. 실제 terminal prompt, signal, live network는 example test가 더 안정적입니다.

B) terminal prompt와 Ctrl+C signal까지 PBT로 무작위 생성한다.

C) UOW-007에서는 PBT를 생략한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-007 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-007 NFR Design으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-007 NFR Requirements` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q11 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Key Implementation Note**: UOW-007 must remain dependency-light. CLI and wizard use standard library primitives; default tests use fake runner/runtime wiring and no live FMKorea network.
