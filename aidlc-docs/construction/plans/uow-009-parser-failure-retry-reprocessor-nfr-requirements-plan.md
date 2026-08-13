# NFR Requirements Plan - UOW-009 Parser Failure Retry Reprocessor

이 계획은 `UOW-009 Parser Failure Retry Reprocessor`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-009 Parser Failure Retry Reprocessor
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter, UOW-008 Container/MCP/Storage Adapters
- **Primary Story**: US-014
- **Supporting Stories**: US-015, US-017
- **Scope**: local/S3 failure input reads, parser-stage failure selection, existing success skip, direct-post retry Job creation, retry report counters, CLI/library/MCP execution boundary
- **Security Focus**: read-only source failure inputs, safe error output, secret redaction, no raw HTML/header/env leakage, S3 credential isolation
- **Resiliency Focus**: malformed line tolerance, inaccessible input handling, no source mutation, existing checkpoint/stop behavior reuse, safe partial retry reporting
- **PBT Focus**: failure selection allowlist, dedupe last-wins behavior, existing success skip, option precedence, input reference validation
- **Out Of Scope**: CAPTCHA bypass, network/storage/checkpoint failure retry, distributed DLQ, background scheduler, parser selector changes, S3 prefix auto-discovery, AWS CDK

## NFR Requirements 작업 체크리스트

- [x] UOW-009 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/nfr-requirements/tech-stack-decisions.md` 생성

## Answer Validation Notes

- Q1-Q10 were A.
- No ambiguity or conflict found.
- The decisions reuse UOW-008 S3/Garage boundaries, current retry CLI/MCP names, and existing runner/checkpoint behavior.
- Follow-up questions are not required before NFR Requirements artifact review.

## NFR Requirements Questions

### Question 1. Failure Input Scale

재처리 입력 규모는 어느 정도까지 1차 구현에서 보장할까요?

A) (권장) failure JSONL은 streaming으로 읽고, dedupe/skip key와 카운터만 메모리에 유지한다. 기본 목표는 수십만 line 수준이며, 전체 raw record를 메모리에 올리지 않는다.

추천 사유: 재처리 실패 파일은 보통 작지만 긴 Job에서는 커질 수 있습니다. streaming + key set이면 구현이 작고 메모리 위험도 낮습니다.

B) 모든 failure/post JSONL을 한 번에 list로 로드한다.

C) 대규모 처리를 위해 SQLite 임시 DB나 외부 queue를 1차 구현에 도입한다.

X) 기타

[Answer]: A

### Question 2. S3/Garage Read Dependency

S3/Garage failure input 읽기는 어떤 의존성 경계로 처리할까요?

A) (권장) UOW-008의 기존 `s3` optional extra와 S3-compatible object boundary를 재사용한다. `boto3` 외의 새 S3/async SDK는 추가하지 않는다.

추천 사유: 이미 S3-compatible output 경계가 있습니다. retry input read 때문에 별도 SDK를 추가하면 설치와 테스트 범위만 커집니다.

B) `aioboto3` 또는 `aiobotocore`를 추가해 S3 read를 async SDK로 구현한다.

C) S3/Garage input read는 문서화만 하고 코드 구현은 후속으로 미룬다.

X) 기타

[Answer]: A

### Question 3. Inaccessible Input Handling

failure input 또는 existing posts input이 없거나 접근할 수 없으면 어떻게 처리할까요?

A) (권장) retry Job 시작 전에 validation error로 전체 실행을 중단한다. 접근 가능한 일부 input만으로 조용히 실행하지 않는다.

추천 사유: 재처리 입력이 누락된 상태로 일부만 실행하면 운영자가 복구 범위를 잘못 이해할 수 있습니다. 실행 전 실패가 가장 명확합니다.

B) 접근 가능한 input만 처리하고 누락 input은 report warning으로 남긴다.

C) 누락 input은 무시한다.

X) 기타

[Answer]: A

### Question 4. Malformed JSONL Line Handling

failure JSONL 내부에 깨진 line이 있으면 어떻게 처리할까요?

A) (권장) line 단위 오류는 카운터로 기록하고 해당 line만 제외한다. 단, 입력 파일 자체를 열 수 없거나 전체가 JSONL로 볼 수 없는 경우는 validation error로 중단한다.

추천 사유: failure 파일 일부가 깨져도 복구 가능한 게시글은 재시도할 수 있어야 합니다. 동시에 파일 접근 오류는 운영 실수로 보고 빠르게 중단하는 편이 안전합니다.

B) 깨진 line이 하나라도 있으면 전체 retry를 중단한다.

C) 깨진 line을 stdout에 원문 그대로 출력하고 계속한다.

X) 기타

[Answer]: A

### Question 5. Retry Report Compatibility

retry 전용 집계 정보는 기존 `RetryReport`/`JobReport`와 어떻게 호환시킬까요?

A) (권장) 기존 report 필드는 의미를 유지하고, 현재 `RetryReport.selected_count`와 `RetryReport.skipped_count`를 우선 사용한다. 꼭 필요한 경우에만 작은 optional metadata/summary 필드를 추가한다.

추천 사유: 기존 report 소비자를 깨지 않으면서 UOW-009 집계를 담을 수 있습니다. retry 전용 별도 report 모델을 크게 만들 필요가 없습니다.

B) retry 전용 `ParserFailureRetryReport` JSON 파일만 만들고 기존 `report.json`은 사용하지 않는다.

C) 기존 report 필드 의미를 retry 기준으로 바꾼다.

X) 기타

[Answer]: A

### Question 6. Option Restoration Safety

`--from-report`, `--from-checkpoint` 옵션 복원은 어떤 안전 경계로 둘까요?

A) (권장) allowlist된 scrape/worker/storage 설정만 복원하고, explicit CLI/API 옵션이 항상 우선한다. `--from-report`와 `--from-checkpoint`를 동시에 주면 validation error로 중단한다.

추천 사유: 복원 기능은 입력을 줄이기 위한 보조 기능입니다. 두 원천을 섞으면 우선순위가 흐려지고 secret이나 불필요한 내부 상태까지 복원할 위험이 생깁니다.

B) checkpoint가 report보다 항상 우선하도록 두 입력을 동시에 허용한다.

C) 복원 기능은 구현하지 않고 모든 옵션을 매번 수동 입력하게 한다.

X) 기타

[Answer]: A

### Question 7. Import Safety And Side Effects

retry service와 adapter 모듈의 import safety는 어떻게 보장할까요?

A) (권장) import 시 파일/S3/env를 읽지 않고, service 생성과 command/tool 실행 시점에만 외부 I/O를 수행한다. 기본 import side-effect 테스트에 retry 모듈을 추가한다.

추천 사유: 이 프로젝트는 library, CLI, container, MCP 재사용을 전제로 합니다. import 시 I/O가 발생하면 재사용성과 테스트 안정성이 떨어집니다.

B) retry 모듈 import 시 기본 `.env`와 현재 디렉터리 failure 파일을 자동 탐색한다.

C) CLI에서만 import safety를 확인하고 library service는 제외한다.

X) 기타

[Answer]: A

### Question 8. Observability And User Feedback

retry 실행 결과는 어느 수준으로 사용자에게 보여줄까요?

A) (권장) stdout/MCP 응답에는 safe summary만 출력하고, 상세 집계는 `RetryReport`/`report.json`에 저장한다. summary에는 입력 수, 선택 수, skip 수, 성공 수, 잔여 실패 수를 포함한다.

추천 사유: 터미널과 MCP 응답에는 빠르게 판단할 수 있는 숫자만 필요합니다. 상세 정보는 파일로 남겨야 재현과 감사가 쉽습니다.

B) 모든 실패 record와 raw reason을 stdout/MCP 응답에 출력한다.

C) stdout/MCP summary 없이 report 파일만 남긴다.

X) 기타

[Answer]: A

### Question 9. Default Test Gate

UOW-009 기본 테스트는 어디까지 포함할까요?

A) (권장) 기본 gate는 local temp files, fake S3 object store, fake runner, static fixtures, PBT로 실행한다. Garage/S3/live network/MCP runtime smoke는 optional marker/env gate로만 실행한다.

추천 사유: retry selection/dedupe/skip/report logic은 외부 서비스 없이 충분히 검증 가능합니다. S3와 live smoke를 기본 gate에 넣으면 로컬/CI 안정성이 떨어집니다.

B) 기본 테스트에서 실제 Garage/S3 컨테이너를 항상 사용한다.

C) UOW-009는 수동 smoke만 수행하고 자동 테스트는 생략한다.

X) 기타

[Answer]: A

### Question 10. Performance And Rate Safety

retry batch 실행 속도는 어떤 기본값을 따를까요?

A) (권장) retry도 일반 direct-post `run`과 같은 request interval, worker count, User-Agent/Proxy 정책을 따른다. retry라는 이유로 기본 속도를 올리지 않는다.

추천 사유: 실패 복구 작업도 실제 게시글 요청입니다. 기존 차단 방지 정책을 우회하면 일시적 실패가 더 늘 수 있습니다.

B) retry는 실패 복구이므로 기본 worker count와 요청 속도를 더 높인다.

C) retry는 항상 단일 worker와 긴 고정 delay만 허용한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-009 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-009 NFR Design으로 넘어가지 않습니다.
