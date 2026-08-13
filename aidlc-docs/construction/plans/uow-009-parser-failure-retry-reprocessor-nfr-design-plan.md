# NFR Design Plan - UOW-009 Parser Failure Retry Reprocessor

이 계획은 `UOW-009 Parser Failure Retry Reprocessor`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-009 Parser Failure Retry Reprocessor
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter, UOW-008 Container/MCP/Storage Adapters
- **Scope**: retry service layout, input ref resolution, streaming JSONL selection, fakeable S3/Garage reads, direct-post retry assembly, option restoration, retry report counters, safe CLI/MCP summary, default tests and PBT
- **Out Of Scope**: distributed DLQ, background scheduler, CAPTCHA bypass, parser selector changes, new S3 SDK, SQLite staging, production infrastructure changes

## NFR Design 작업 체크리스트

- [x] UOW-009 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Module Layout

UOW-009 구현 파일은 어떻게 나눌까요?

A) (권장) `src/fmkorea_scraper/retry/parser_failures.py`에 service, selector, input reader, summary helper를 두고, CLI/MCP는 기존 adapter 파일의 `retry-parser-failures`/`retry_parser_failures` 경로만 service 호출로 연결한다. 테스트는 `tests/test_parser_failure_retry.py`와 property test 파일 정도로 둔다.

추천 사유: 기능이 작고 기존 CLI/MCP adapter를 재사용합니다. 여러 하위 패키지로 쪼개면 현재 범위보다 구조가 커집니다.

B) `src/fmkorea_scraper/retry/` 하위에 `service.py`, `selector.py`, `readers.py`, `reports.py`, `adapters.py`를 모두 분리한다.

C) 기존 `runner/service.py` 안에 retry selector까지 넣는다.

X) 기타

[Answer]: A

### Question 2. Input Reader Boundary

local/S3 failure input reader는 어떤 경계로 만들까요?

A) (권장) `FailureInputReader` 프로토콜과 `LocalFailureInputReader`, `S3FailureInputReader`의 작은 구현을 둔다. service는 line iterator만 받아 selection을 수행한다.

추천 사유: S3는 optional extra라 fake로 대체하기 쉬워야 합니다. service를 파일/S3 구현에서 분리하면 테스트가 작아집니다.

B) service 안에서 path/URI 종류를 직접 분기해 파일과 S3를 모두 읽는다.

C) S3 input은 adapter에서 임시 파일로 다운로드한 뒤 service에는 local path만 넘긴다.

X) 기타

[Answer]: A

### Question 3. Streaming Selector Pattern

failure selection은 어떤 구현 패턴으로 둘까요?

A) (권장) line iterator를 받아 `RetrySelectionSummary`와 deduped `RetryCandidate` list를 반환하는 순수 함수/작은 클래스로 둔다. invalid/ineligible raw line은 보관하지 않고 카운터만 올린다.

추천 사유: 핵심 로직이 I/O 없이 테스트 가능해지고, PBT 적용이 쉽습니다.

B) selection 중간 결과를 모두 dataclass list로 보관한 뒤 마지막에 필터링한다.

C) selection과 Job 실행을 한 함수에서 처리한다.

X) 기타

[Answer]: A

### Question 4. Existing Success Index Pattern

기존 성공 `posts.jsonl` skip index는 어떻게 만들까요?

A) (권장) 성공 JSONL도 streaming으로 읽고 `(site_id, board_id, document_srl, document_id_raw)` set만 유지한다. invalid post line은 카운터만 올리고 skip index에는 넣지 않는다.

추천 사유: 전체 post body를 메모리에 둘 필요가 없습니다. skip에는 key만 필요합니다.

B) 기존 posts 전체를 Pydantic `PostResult` list로 모두 로드한다.

C) 기존 성공 skip은 CLI adapter에서만 처리하고 service에서는 모르게 한다.

X) 기타

[Answer]: A

### Question 5. Option Restoration Pattern

`--from-report`/`--from-checkpoint` 옵션 복원은 어디에서 처리할까요?

A) (권장) CLI/API request builder 단계에서 allowlist된 설정만 복원해 `RetryRequest` 또는 service input을 완성한다. service는 이미 확정된 request/options만 받는다.

추천 사유: 복원은 입력 편의 기능입니다. service 내부는 재처리 로직에 집중하는 편이 작고 명확합니다.

B) service가 report/checkpoint ref를 직접 읽어 복원한다.

C) 복원 옵션마다 별도 service class를 만든다.

X) 기타

[Answer]: A

### Question 6. Report Counter Pattern

retry counters를 기존 report 계열에 어떻게 담을까요?

A) (권장) 기존 `RetryReport.selected_count`와 `RetryReport.skipped_count`를 우선 사용하고, 추가 진단은 `JobReport` 또는 `RetryReport`에 작은 optional `metadata: dict[str, Any]` 필드를 추가해 `metadata["parser_failure_retry"]` 아래에 넣는다.

추천 사유: 기존 report 필드 의미를 바꾸지 않고, 향후 다른 adapter metadata도 같은 구조를 쓸 수 있습니다. 별도 report 파일은 필요 없습니다.

B) `ParserFailureRetryReport` 독립 모델과 별도 JSON 파일을 만든다.

C) counters는 stdout/MCP 응답에만 출력하고 report에는 남기지 않는다.

X) 기타

[Answer]: A

### Question 7. DirectPost Job Assembly Pattern

retry batch를 `JobRunner`로 넘기는 방식은 어떻게 할까요?

A) (권장) deduped candidate URL list로 `DirectPostSource`를 만들고, 기존 `JobConfig` + `run_job` 경로를 그대로 사용한다. fake runner 주입 지점을 둬 테스트한다.

추천 사유: 기존 worker/checkpoint/output/HTTP 정책을 재사용하면서 테스트도 단순해집니다.

B) `PostDetailService`를 service에서 직접 반복 호출한다.

C) retry 전용 worker queue를 새로 구현한다.

X) 기타

[Answer]: A

### Question 8. Adapter Summary Pattern

CLI/MCP 결과 출력은 어떻게 구성할까요?

A) (권장) 완료 후 safe summary로 `selected`, `skipped`, `stored`, `remaining_failure`, `report` 위치만 출력/반환한다. invalid line 원문이나 raw exception은 출력하지 않는다.

추천 사유: 운영자는 복구 결과 숫자와 report 위치가 필요합니다. 상세 원문 출력은 보안/가독성 모두에 불리합니다.

B) 선택/제외된 모든 failure record를 stdout/MCP response에 출력한다.

C) 아무 출력 없이 exit code/report 파일만 남긴다.

X) 기타

[Answer]: A

### Question 9. Property-Based Test Pattern

PBT는 어떤 단위에 적용할까요?

A) (권장) I/O 없는 selector 함수에 집중한다. dedupe last-wins, allowlist filtering, existing success skip, explicit option precedence를 검증한다.

추천 사유: PBT는 순수 로직에서 가장 효과적입니다. 파일/S3/runner까지 섞으면 느리고 불안정해집니다.

B) S3 fake reader와 runner orchestration까지 PBT로 모두 생성한다.

C) UOW-009는 example test만 두고 PBT는 생략한다.

X) 기타

[Answer]: A

### Question 10. Optional Smoke Pattern

UOW-009 optional smoke는 어디까지 둘까요?

A) (권장) local fixture retry smoke는 기본 테스트에 포함하고, S3/Garage input read, MCP runtime, live post retry smoke는 env/marker gated optional로 둔다.

추천 사유: 기본 gate는 안정적으로 유지하면서 실제 저장소/MCP/라이브 사이트 확인은 필요할 때만 실행할 수 있습니다.

B) live post retry smoke를 기본 테스트에 포함한다.

C) optional smoke는 만들지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-009 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-009 NFR Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q10 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Key Implementation Note**: UOW-009 keeps parser-failure retry as one focused service module, streams local/S3 failure inputs, keeps selection pure and testable, restores options in adapters, and reuses `DirectPostSource` plus the existing `JobRunner`.
