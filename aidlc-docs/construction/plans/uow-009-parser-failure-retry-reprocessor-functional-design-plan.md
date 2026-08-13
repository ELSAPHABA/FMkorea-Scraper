# Functional Design Plan - UOW-009 Parser Failure Retry Reprocessor

이 계획은 `UOW-009 Parser Failure Retry Reprocessor`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-009 Parser Failure Retry Reprocessor
- **Depends On**: UOW-001 Core Models And Config, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter, UOW-008 Container/MCP/Storage Adapters
- **Primary Story**: US-014
- **Supporting Stories**: US-015, US-017
- **Scope**: failure records ingestion, parser-stage failure selection, direct-post retry batch creation, optional existing-success skip, retry output/report generation, CLI/API/MCP service boundary
- **Out Of Scope**: parser selector fixes, HTTP retry policy changes, CAPTCHA bypass, network/storage/checkpoint failure recovery, distributed DLQ/scheduler, original failure file mutation, AWS CDK

## Functional Design 작업 체크리스트

- [x] UOW-008 Build and Test 승인 확인
- [x] UOW-009 범위 확인
- [x] UOW-001/UOW-004/UOW-005/UOW-006/UOW-007/UOW-008 계약 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/functional-design/domain-entities.md` 생성

## Answer Validation Notes

- Q1-Q12 were A.
- No ambiguity or conflict found.
- The design follows the DCinside baseline where it fits, but uses FMKorea model keys: `site_id`, `board_id`, `document_srl`, and `document_id_raw`.
- The current `RetryRequest`/`FailureInput` shape is kept as the first implementation boundary. Multiple failure inputs can be added later if operational demand appears.
- Follow-up questions are not required before Functional Design artifact review.

## Functional Design Questions

### Question 1. Retry Input Source

재처리 대상 실패 기록은 어디에서 읽을까요?

A) (권장) local `failures.jsonl` 경로와 S3/Garage object URI를 모두 1차 구현에 포함한다. `FailureInput.failure_path` 하나를 기본 입력으로 두고, 저장소 adapter가 local path 또는 `s3://bucket/key`/object key를 해석한다.

추천 사유: UOW-008에서 S3-compatible output과 PostgreSQL checkpoint가 이미 구현되었습니다. 컨테이너 운영에서 실패 기록이 S3/Garage에 있을 수 있으므로, 기존 저장소 adapter 경계를 재사용하는 것이 디시인사이드 baseline 계승에 가장 가깝습니다.

B) local `failures.jsonl` 파일 경로만 입력받고 S3/Garage 읽기는 후속 확장으로 둔다.

C) 최근 Job output root만 입력받고 내부에서 `failures.jsonl`을 자동 탐색한다.

X) 기타

[Answer]: A

### Question 2. Retryable Failure Selection

어떤 failure record를 재처리 대상으로 볼까요?

A) (권장) `stage="post"`이면서 `reason="parse_failure"` 또는 parser/metadata 계열 allowlist에 들어가는 failure만 포함한다. CAPTCHA, block, network, media, output, storage, checkpoint, manual stop 실패는 제외한다.

추천 사유: 이번 유닛은 parser 수정 이후 실패 게시글만 회수하는 기능입니다. 네트워크/저장소 계열을 섞으면 UOW-002 HTTP retry와 UOW-005 checkpoint 책임이 흐려집니다.

B) `retryable=true`인 failure를 모두 포함한다.

C) 사용자가 reason 목록을 CLI/API 옵션으로 전부 지정해야 한다.

X) 기타

[Answer]: A

### Question 3. Failure Record URL And Key Requirements

재시도 대상 failure record가 URL 또는 post key를 일부 누락하면 어떻게 할까요?

A) (권장) retry 실행에는 `url`을 필수로 요구한다. dedupe/skip key는 `post_key`가 있으면 사용하고, 없으면 URL에서 document id를 추출해 `PostCandidate`를 만든다. URL도 없으면 해당 failure는 selected가 아니라 invalid/skipped로 집계한다.

추천 사유: 기존 `DirectPostSource` 경로를 재사용하려면 URL이 가장 확실합니다. 동시에 과거 failure record가 일부 key를 누락해도 URL만 있으면 복구할 수 있습니다.

B) `post_key`가 없는 failure는 모두 validation error로 처리해 전체 retry를 중단한다.

C) URL이 없어도 board/document id만 있으면 URL을 추정해 재시도한다.

X) 기타

[Answer]: A

### Question 4. Existing Success Skip

이미 다른 run에서 성공 저장된 게시글은 어떻게 처리할까요?

A) (권장) 선택적으로 기존 `posts.jsonl` 경로 또는 S3/Garage object URI를 받아 `(site_id, board_id, document_srl, document_id_raw)` 기준으로 skip한다. 입력하지 않으면 failure 파일의 재처리 대상 전체를 다시 시도한다.

추천 사유: 재시도 run을 여러 번 나눠도 중복 수집을 피할 수 있습니다. 하지만 단순 사용자는 failure 파일만으로 실행할 수 있어야 합니다.

B) 항상 같은 output root 아래의 모든 `posts.jsonl`을 자동 탐색해 skip한다.

C) skip 기능 없이 항상 모든 parser-stage failure를 재시도한다.

X) 기타

[Answer]: A

### Question 5. Duplicate Failure Records

여러 failure record에 같은 게시글이 중복으로 들어 있으면 어떻게 할까요?

A) (권장) retry batch 내부에서 `(site_id, board_id, document_srl, document_id_raw)` 기준으로 dedupe한다. 같은 key의 URL이 여러 개면 가장 마지막 failure record의 URL을 사용한다.

추천 사유: 여러 retry 결과를 합칠 때 같은 게시글이 반복될 수 있습니다. 한 번만 재시도하는 것이 요청 수와 결과 중복을 줄입니다.

B) failure record 줄 단위로 모두 재시도한다.

C) 중복이 발견되면 validation error로 전체 retry를 중단한다.

X) 기타

[Answer]: A

### Question 6. Retry Execution Path

실제 재처리는 어떤 실행 경로를 사용할까요?

A) (권장) 선택된 실패 URL을 `DirectPostSource`로 변환해 기존 `JobRunner`, `PostDetailService`, output/media/failure/checkpoint store를 그대로 호출한다.

추천 사유: 이미 검증된 worker, output, checkpoint, HTTP/User-Agent/Proxy 경로를 재사용할 수 있습니다. 별도 parser runner를 만들 필요가 없습니다.

B) `PostDetailService`를 직접 호출하는 전용 retry runner를 만든다.

C) HTML 원본을 저장해 두었다가 네트워크 요청 없이 재파싱한다.

X) 기타

[Answer]: A

### Question 7. Scrape Options For Retry

재처리 시 댓글, media, parser guardrail, worker 옵션은 어떻게 정할까요?

A) (권장) 기본값은 일반 `run`과 동일하게 두고, CLI/API에서 기존 옵션을 다시 받을 수 있게 한다. 추가로 `--from-report`, `--from-checkpoint` 같은 복원 helper를 제공하되, 사용자가 명시한 retry 옵션이 복원값보다 우선한다.

추천 사유: failure record만으로는 원 Job의 모든 옵션을 안정적으로 복원할 수 없습니다. 기존 옵션 재사용이 가장 작고, 복원 helper는 운영 편의만 보조합니다.

B) 항상 checkpoint 또는 report에서 원 Job 설정을 자동 복원하고 사용자가 덮어쓸 수 없게 한다.

C) retry는 항상 comments off, media url-only, worker 1개로 고정한다.

X) 기타

[Answer]: A

### Question 8. Retry Output Semantics

재처리 결과는 어디에 저장할까요?

A) (권장) 원본 failure file/object는 수정하지 않고, 새 retry Job/run의 `posts.jsonl`, `failures.jsonl`, `report.json`으로 저장한다. retry report에는 원본 failure 입력, selected count, skipped count, stored count, remaining failure count를 기록한다.

추천 사유: 원본 증거를 보존하고, 재처리 결과를 감사하기 쉽습니다. JSONL을 직접 수정하는 방식보다 복구와 검증이 단순합니다.

B) 성공한 항목은 원본 failure file에서 제거하고 별도 성공 파일을 만든다.

C) 원본 Job의 기존 `posts.jsonl`에 append한다.

X) 기타

[Answer]: A

### Question 9. Retry Report Model

retry report는 현재 `RetryReport(JobReport)` 모델을 어떻게 사용할까요?

A) (권장) 기존 `RetryReport`의 `selected_count`, `skipped_count`와 상속된 `stored_count`, `failure_count`, `output_refs`를 우선 사용한다. 꼭 필요한 추가 집계만 `RetryReport` 필드로 최소 확장한다.

추천 사유: UOW-001 모델에 이미 retry report가 있습니다. 새 summary 모델을 늘리기보다 기존 모델을 보강하는 편이 호환성이 좋습니다.

B) retry 전용 `retry-summary.json` 모델을 새로 만들고 일반 `report.json`과 분리한다.

C) report 파일은 만들지 않고 stdout에만 요약을 출력한다.

X) 기타

[Answer]: A

### Question 10. CLI, Library, MCP Boundary

사용자는 이 기능을 어떻게 호출할까요?

A) (권장) import 가능한 `ParserFailureRetryService`, CLI `retry-parser-failures` 실행 구현, MCP `retry_parser_failures` tool 구현을 함께 제공한다. CLI/MCP는 service를 얇게 감싸는 adapter로 둔다.

추천 사유: UOW-007 CLI와 UOW-008 MCP tool shape가 이미 존재합니다. 실행 엔진은 하나만 만들고 adapter가 재사용하는 구조가 가장 작습니다.

B) CLI subcommand만 구현하고 library/MCP는 후속으로 둔다.

C) Python library API만 구현하고 CLI/MCP는 후속으로 둔다.

X) 기타

[Answer]: A

### Question 11. Stop Conditions

재처리 실행 중 CAPTCHA/차단/수동 중단이 발생하면 어떻게 처리할까요?

A) (권장) 기존 `JobRunner` stop/checkpoint 규칙을 그대로 따른다. CAPTCHA/차단은 즉시 중단하고 checkpoint를 저장하며, parser-stage 개별 실패만 계속 진행 가능한 실패로 기록한다.

추천 사유: 운영상 위험한 상태를 일반 parser retry와 섞지 않아야 합니다. 기존 중단점 저장 정책을 그대로 재사용할 수 있습니다.

B) CAPTCHA/차단도 failure로 기록하고 계속 진행한다.

C) retry unit에서는 checkpoint를 만들지 않고 실패 즉시 프로세스를 종료한다.

X) 기타

[Answer]: A

### Question 12. Validation And Test Fixtures

UOW-009 기본 검증은 어떻게 구성할까요?

A) (권장) 기본 테스트는 local fixture 기반 failure selection/dedupe/skip/build-retry-job/service orchestration 테스트로 둔다. S3/Garage, PostgreSQL, MCP runtime, live site smoke는 opt-in marker로만 실행한다.

추천 사유: parser failure retry는 입력 선별과 기존 JobRunner composition이 핵심입니다. 외부 서비스 의존 검증은 UOW-008처럼 명시적으로 켤 때만 실행하는 편이 안정적입니다.

B) 기본 테스트에서 Docker compose로 Garage/PostgreSQL을 항상 띄운다.

C) 기능 테스트 없이 문서와 수동 smoke만 둔다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-009 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-009 NFR Requirements로 넘어가지 않습니다.
