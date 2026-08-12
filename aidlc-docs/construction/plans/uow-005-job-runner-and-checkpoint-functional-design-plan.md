# Functional Design 계획 - UOW-005 Job Runner And Checkpoint

이 계획은 `UOW-005 Job Runner And Checkpoint`의 기능 설계를 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-005 Job Runner And Checkpoint
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-006 Output And Storage
- **Primary Stories**: US-012, US-013
- **Supporting Stories**: US-001, US-003, US-005, US-006, US-010, US-014, US-015, US-016, US-017
- **Scope**: Job lifecycle orchestration, single collector task, post candidate queue, async post worker pool, media download orchestration, storage success ordering, checkpoint save/load/resume, stop/cancel/fail-closed handling, realtime termination integration, safe run report generation
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 JobRunner/checkpoint 구조를 최대한 계승하되, FMKorea-specific collector/parser/storage 컴포넌트를 조립하는 권장안으로 작성한다.
- **Out Of Scope**: CLI prompt UX, container entrypoint, PostgreSQL checkpoint adapter, MCP hosting, parser-stage retry reprocessor implementation, SQS/DLQ, Docker, AWS CDK, centralized platform scheduler

## Functional Design 작업 체크리스트

- [x] UOW-006 Build and Test 승인 확인
- [x] UOW-005 범위 확인
- [x] `docs/FMKorea-Scraper_Function_Specification.md` worker/checkpoint/realtime 항목 확인
- [x] UOW-001 `JobConfig`, `Checkpoint`, `JobReport`, port 계약 확인
- [x] UOW-003 collector, UOW-004 detail parser, UOW-006 storage 경계 확인
- [x] Functional Design 질문 생성
- [x] Functional Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/business-logic-model.md` 생성
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/business-rules.md` 생성
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/domain-entities.md` 생성

## Functional Design Questions

### Question 1. JobRunner Boundary

UOW-005의 JobRunner는 어떤 입력/출력 경계를 가질까요?

A) (권장) `JobConfig`와 주입된 UOW-002/003/004/006 의존성을 받아 하나의 Job을 실행하고 `JobReport`를 반환한다. CLI, container, MCP는 후속 adapter에서 이 API를 호출한다.

추천 사유: 기준 구조의 core orchestration 경계를 계승합니다. UOW-005는 실행 흐름만 책임지고 사용자 입력, 환경변수 매핑, 배포 런타임은 뒤 단계로 남길 수 있습니다.

B) JobRunner가 CLI 인자와 환경변수를 직접 읽고 실행한다.

C) JobRunner 없이 CLI adapter가 collector/parser/storage를 직접 조립한다.

X) 기타

[Answer]: A

### Question 2. Queue Unit And Topology

post worker queue에는 어떤 단위가 들어가야 할까요?

A) (권장) 큐 단위는 `PostCandidate` 1개다. Job당 단일 collector task가 후보 링크를 수집해 `asyncio.Queue`에 넣고, 여러 post worker가 후보를 소비한다.

추천 사유: 기능명세서가 큐 단위를 게시글 링크 1개로 확정했습니다. Job 단위 큐는 후속 SQS/platform에서 다루고, UOW-005 내부 큐는 게시글 fan-out에 집중하는 편이 단순합니다.

B) 큐 단위는 JobConfig 1개로 두고 worker가 수집/파싱/저장을 모두 수행한다.

C) 큐를 두지 않고 collector가 후보를 찾는 즉시 상세 파서를 순차 호출한다.

X) 기타

[Answer]: A

### Question 3. Worker Count And Backpressure

post worker 수와 queue backpressure는 어떻게 적용할까요?

A) (권장) `WorkerConfig.post_worker_count`만큼 post worker를 만들고, `queue_max_size`가 있으면 bounded `asyncio.Queue`로 backpressure를 건다. `media_worker_count`는 UOW-005에서 별도 media worker pool을 만들지 않고 media download 동시성 제한값으로만 사용한다.

추천 사유: 기준 구조를 계승하면서도 UOW-005 구현을 불필요하게 쪼개지 않습니다. media download는 post 처리 중 필요한 경우만 UOW-002 download와 UOW-006 media store로 연결하면 충분합니다.

B) post worker와 media worker를 완전히 별도 queue/pool로 나눈다.

C) worker 수 설정을 무시하고 항상 단일 worker로 실행한다.

X) 기타

[Answer]: A

### Question 4. Storage Success And Checkpoint Advance

게시글 성공 처리와 checkpoint advance 순서는 어떻게 보장할까요?

A) (권장) 상세 파싱, 선택적 미디어 저장, `append_post` 성공 이후에만 completed key를 추가하고 checkpoint를 저장한다. 저장 실패 시 completed key를 advance하지 않고 failure/report에 안전하게 반영한다.

추천 사유: 사용자가 요구한 “저장 성공 후 checkpoint 갱신” 규칙입니다. 재개 시 누락보다 중복 방지가 쉬우며, UOW-006의 durable write boundary와 맞습니다.

B) 상세 파싱만 성공하면 저장 전에 checkpoint를 advance한다.

C) checkpoint는 Job 종료 시 한 번만 저장한다.

X) 기타

[Answer]: A

### Question 5. Checkpoint Save Cadence

정상 실행 중 checkpoint 저장 주기는 어떻게 둘까요?

A) (권장) 게시글 저장 성공 10개마다 running checkpoint를 저장하고, manual stop/error/CAPTCHA/block/timeout/normal completion 때 즉시 최종 checkpoint를 저장한다. 10개 값은 UOW-001 모델 변경 없이 내부 기본값으로 둔다.

추천 사유: 기능명세서 기본값을 만족하면서 새 설정 모델을 늘리지 않습니다. 나중 CLI 옵션이 필요해지면 UOW-007에서 명시 설정으로 승격하면 됩니다.

B) 모든 게시글 저장 성공마다 checkpoint를 저장한다.

C) 실행 중 checkpoint는 저장하지 않고 중단/완료 때만 저장한다.

X) 기타

[Answer]: A

### Question 6. Resume Semantics

checkpoint 기반 재개는 어떤 범위까지 복원할까요?

A) (권장) checkpoint의 `job_config`, `collector_cursor`, `completed_keys`, `queued_links`를 복원하고 새 `run_id`로 출력한다. in-flight 요청의 정확한 복원은 보장하지 않으며 completed key dedupe로 중복 저장을 막는다.

추천 사유: 기존 설계의 checkpoint 정밀도와 일치합니다. 정확한 in-flight 복원은 비용이 크고, 현재 요구사항은 중단점 이후부터 안전하게 이어가는 것입니다.

B) in-flight 요청까지 정확히 복원하도록 worker별 상태를 저장한다.

C) 재개 시 Job 설정만 복원하고 completed key는 사용하지 않는다.

X) 기타

[Answer]: A

### Question 7. Stop And Cancellation Policy

수동 중단, timeout, CAPTCHA, 차단, 예외 발생 시 어떻게 멈출까요?

A) (권장) stop event를 세우고 collector를 중단시킨 뒤 queue drain/worker cancel을 수행한다. CAPTCHA/block은 fail-closed로 즉시 중단하고 `status=stopped`, `reason`을 저장한다. 자동 우회는 시도하지 않는다.

추천 사유: 요구사항의 CAPTCHA/차단 처리 원칙과 맞습니다. 중단 시 checkpoint를 남기는 것이 우선이며, 우회 로직은 범위 밖입니다.

B) CAPTCHA/block도 retry 가능한 일반 네트워크 오류로 보고 계속 진행한다.

C) 모든 예외를 무시하고 가능한 worker만 계속 실행한다.

X) 기타

[Answer]: A

### Question 8. Failure Recording Scope

UOW-005가 어떤 실패를 `FailureRecord`로 저장할까요?

A) (권장) post detail parse 실패, content/comment/parser-stage 실패, media download 실패, storage 실패, checkpoint 실패를 safe `FailureRecord`로 기록한다. CAPTCHA/block/manual stop 계열은 재처리 대상이 아님을 stage/reason으로 구분한다.

추천 사유: UOW-009 parser-stage retry가 failures.jsonl을 입력으로 사용합니다. 단, retry 선택 정책 자체는 UOW-009에 두고 UOW-005는 안전한 실패 기록만 남깁니다.

B) parser-stage 실패만 기록하고 다른 실패는 report count에만 반영한다.

C) 실패 기록은 남기지 않고 exception만 전파한다.

X) 기타

[Answer]: A

### Question 9. Media Download Orchestration

`MediaMode.DOWNLOAD`일 때 미디어 다운로드는 어디서 조정할까요?

A) (권장) UOW-005 post worker가 UOW-004 `PostResult.media`를 보고 UOW-002 `download`를 호출한 뒤 UOW-006 `MediaStorePort`에 저장한다. `URL_ONLY`일 때는 `save_metadata_only`만 호출하거나 저장을 생략한다.

추천 사유: UOW-004는 metadata만 만들고 UOW-006은 bytes 저장만 합니다. HTTP download와 저장을 연결하는 위치는 worker orchestration인 UOW-005가 가장 작습니다.

B) UOW-004 parser가 media 파일을 직접 다운로드한다.

C) UOW-006 media store가 URL을 받아 직접 HTTP 다운로드한다.

X) 기타

[Answer]: A

### Question 10. Realtime Termination

실시간 수집 종료 조건은 어떻게 평가할까요?

A) (권장) `RealtimeTermination`의 `duration_seconds` 또는 `end_at` 중 하나만 유효하다고 보고, collector polling loop가 조건 도달 시 새 후보 수집을 멈춘다. queue에 이미 들어간 후보 처리는 완료한 뒤 `status=completed` checkpoint/report를 저장한다.

추천 사유: 기능명세서의 “타이머와 종료 시각 중 하나만” 규칙을 유지합니다. 이미 큐에 들어간 후보를 저장 완료하면 결과와 checkpoint가 덜 흔들립니다.

B) 종료 조건이 오면 in-flight worker를 즉시 취소하고 queued 후보도 버린다.

C) 실시간 종료 조건은 CLI에서만 처리하고 JobRunner는 알지 않는다.

X) 기타

[Answer]: A

### Question 11. Report Generation

JobReport는 어떤 시점과 기준으로 생성할까요?

A) (권장) Job 시작 시 카운터를 누적하고, 정상 완료/중단/실패 시 최종 `JobReport`를 UOW-006 output store에 쓴다. collected, stored, failure count와 output refs를 포함하고, raw HTML/cookie/secret은 넣지 않는다.

추천 사유: report는 adapter와 운영자가 Job 결과를 확인하는 최소 요약입니다. 상세 실패 원인은 failures.jsonl에 두고 report는 안전한 집계 중심으로 유지합니다.

B) report는 만들지 않고 checkpoint만 결과로 반환한다.

C) 모든 실패 상세와 원본 HTML 일부를 report에 넣는다.

X) 기타

[Answer]: A

### Question 12. Public API Surface

UOW-005 구현 후 공개 API는 어떻게 노출할까요?

A) (권장) `JobRunner`, `JobRunDependencies`, `JobRunResult` 같은 최소 실행 객체를 `fmkorea_scraper.runner` 패키지에 두고, 기존 `core.api.run_job`, `resume_job`은 후속 adapter wiring 전까지 명확한 내부 의존성 주입 경로를 사용하도록 연결하거나 문서화한다.

추천 사유: 라이브러리 사용자는 JobRunner를 직접 조립할 수 있어야 하고, CLI/container/MCP는 같은 core runner를 호출해야 합니다. 단, 아직 adapter가 없으므로 환경변수/터미널 입력은 노출하지 않습니다.

B) public API를 추가하지 않고 tests에서만 내부 클래스를 사용한다.

C) `main.py` 중심 실행 함수만 만들고 패키지 API는 만들지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-005 Functional Design 산출물 3개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 NFR Requirements로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T17:03:58Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper JobRunner/checkpoint orchestration boundary as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.
- **Key Decision**: UOW-005 is a core runner/orchestration layer. It does not own CLI prompts, container runtime, MCP hosting, PostgreSQL checkpoint adapter, SQS/DLQ, or parser-stage retry reprocessor implementation.

## Functional Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/business-logic-model.md`
- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/business-rules.md`
- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/functional-design/domain-entities.md`

승인 후 다음 단계는 `UOW-005 NFR Requirements`이다.
