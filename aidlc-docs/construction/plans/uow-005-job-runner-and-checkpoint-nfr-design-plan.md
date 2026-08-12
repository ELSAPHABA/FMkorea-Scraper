# NFR Design 계획 - UOW-005 Job Runner And Checkpoint

이 계획은 `UOW-005 Job Runner And Checkpoint`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-005 Job Runner And Checkpoint
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-006 Output And Storage
- **Scope**: `asyncio` runner package, candidate queue lifecycle, post worker pool, media download concurrency, checkpoint coordination, resume dedupe, stop-class handling, safe failure/report builders, deterministic tests
- **Baseline Inheritance**: `A)` 선택지는 기준 스크래퍼의 JobRunner/checkpoint 구조를 최대한 계승하되, FMKorea collector/parser/storage 계약에 맞춘 권장안으로 작성한다.
- **Out Of Scope**: CLI prompt UX, container entrypoint, PostgreSQL checkpoint adapter, MCP tools, parser-stage retry reprocessor, SQS/DLQ, Docker/CDK/platform scheduler

## NFR Design 작업 체크리스트

- [x] UOW-005 Functional Design 승인 확인
- [x] UOW-005 NFR Requirements 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 판단
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Runner Package Layout

UOW-005 러너 컴포넌트는 어떤 모듈 구조로 나눌까요?

A) (권장) `src/fmkorea_scraper/runner/` 아래에 `__init__.py`, `models.py`, `policies.py`, `checkpointing.py`, `workers.py`, `service.py`를 둔다.

추천 사유: 기준 스크래퍼의 러너 경계를 계승하면서 파일 수를 필요한 책임 단위로만 제한합니다.

B) 모든 러너 로직을 `runner.py` 하나에 모은다.

C) collector, parser, storage, media, checkpoint마다 별도 adapter interface hierarchy와 registry를 만든다.

X) 기타

[Answer]: A

### Question 2. Task Lifecycle Pattern

Job task 생명주기는 어떤 방식으로 관리할까요?

A) (권장) `JobRunner`가 collector task 1개와 post worker task N개를 직접 생성하고, 공유 `asyncio.Event` stop flag와 sentinel item으로 종료를 조율한다. stop-class 오류에서는 stop flag를 세우고 남은 task를 정리한다.

추천 사유: 표준 `asyncio`만으로 충분하고, 외부 worker framework 없이도 종료/재개 테스트가 단순합니다.

B) `asyncio.gather` 하나에 모든 coroutine을 넣고 task별 종료 상태를 따로 추적하지 않는다.

C) 외부 worker queue framework를 도입해 task 생명주기를 위임한다.

X) 기타

[Answer]: A

### Question 3. Queue Item And Sentinel Pattern

내부 큐 item과 종료 신호는 어떻게 표현할까요?

A) (권장) 큐 item은 `PostCandidate`만 사용하고, collector 완료 후 worker 수만큼 내부 sentinel 값을 넣는다. bounded queue에서는 stop-aware enqueue helper가 backpressure와 중단을 함께 처리한다.

추천 사유: 명세의 post 링크 단위 큐 구조와 맞고, Job 단위 외부 큐를 UOW-005에 섞지 않습니다.

B) 큐 item에 Job, candidate, retry, checkpoint command를 모두 넣는다.

C) sentinel 없이 queue empty polling으로 worker 종료를 판단한다.

X) 기타

[Answer]: A

### Question 4. Completed-Key Policy Pattern

완료 key dedupe와 advancement는 어디에서 처리할까요?

A) (권장) `policies.py`에 `build_post_key`, `should_skip_completed`, `mark_completed_after_output` 같은 순수 helper를 두고, 실제 completed set 갱신은 output 성공 이후에만 수행한다.

추천 사유: output-before-checkpoint 규칙을 작은 순수 정책으로 검증할 수 있고 resume 중복 방지도 한 곳에 모입니다.

B) 각 worker가 문자열 key를 직접 만들고 set을 직접 수정한다.

C) JSONL 파일을 다시 읽어 완료 여부를 매번 판별한다.

X) 기타

[Answer]: A

### Question 5. Checkpoint Coordinator Pattern

checkpoint 저장 시점과 snapshot 구성은 어떤 컴포넌트가 담당할까요?

A) (권장) `CheckpointCoordinator`가 running/terminal checkpoint snapshot을 만들고, 10-success cadence와 terminal immediate save를 담당한다. 실제 저장은 UOW-006 `CheckpointStorePort`에 위임한다.

추천 사유: checkpoint 파일 포맷은 저장소가 숨기고, 러너는 저장 시점과 안전한 payload만 관리하면 됩니다.

B) post worker마다 checkpoint store를 직접 호출한다.

C) Job 종료 시점에만 checkpoint를 저장한다.

X) 기타

[Answer]: A

### Question 6. Resume Pattern

checkpoint resume은 어떤 방식으로 구현할까요?

A) (권장) `resume_from_checkpoint`가 `job_config`, `collector_cursor`, `completed_keys`, 선택적 `queued_links`를 복원하고 새 `run_id`로 일반 run flow를 다시 시작한다. 정확한 in-flight 복원은 하지 않는다.

추천 사유: 기존 JSONL에 append하지 않아 내구성 경계가 단순하고, completed-key dedupe로 중복 저장을 막습니다.

B) 이전 run의 JSONL에 이어쓰기하며 in-flight 요청도 최대한 복원한다.

C) checkpoint는 stop reason만 읽고 모든 후보를 처음부터 다시 수집한다.

X) 기타

[Answer]: A

### Question 7. Stop Reason And Failure Mapping

CAPTCHA, block, timeout, manual stop, parser/storage 오류는 어떻게 상태로 매핑할까요?

A) (권장) pure mapper가 예외/이벤트를 `StopReason`, report status, failure category로 변환한다. CAPTCHA/block은 retry loop 없이 fail-closed stopped 상태로 처리한다.

추천 사유: 자동 우회 없이 멈춘다는 보안 요구사항을 유지하면서 report/checkpoint 상태를 일관되게 만들 수 있습니다.

B) 모든 예외를 `failed` 하나로 처리한다.

C) CAPTCHA/block을 네트워크 오류처럼 재시도한다.

X) 기타

[Answer]: A

### Question 8. Media Download Coordination Pattern

post worker 내부의 media download concurrency는 어떻게 제한할까요?

A) (권장) `MediaDownloadCoordinator`가 공유 `asyncio.Semaphore(media_worker_count)`를 사용한다. `MediaMode.URL_ONLY`는 다운로드를 건너뛰고, `MediaMode.DOWNLOAD`만 UOW-002 download와 UOW-006 media store를 호출한다.

추천 사유: 별도 media queue 없이도 요청량을 제어할 수 있고, post worker 흐름을 크게 늘리지 않습니다.

B) media마다 새 task를 무제한 생성한다.

C) media 전용 queue와 worker pool을 별도로 만든다.

X) 기타

[Answer]: A

### Question 9. Failure And Report Builder Pattern

runner가 만드는 failure/report payload는 어떤 방식으로 안전하게 만들까요?

A) (권장) `FailureRecorder`와 `ReportBuilder`가 allow-list safe field만 받는다. UOW-006 redaction은 최종 저장 boundary로 남긴다.

추천 사유: 호출부마다 민감정보 제거를 반복하지 않고, checkpoint/report/log 누출 위험을 줄입니다.

B) 실패 원본 exception/context를 그대로 저장하고 UI에서만 숨긴다.

C) failure record를 만들지 않고 report counter만 증가시킨다.

X) 기타

[Answer]: A

### Question 10. Deterministic Time Pattern

realtime 종료와 timeout 테스트는 어떤 시간 경계로 검증할까요?

A) (권장) 작은 clock dependency를 주입하고, production 기본값은 real clock, 테스트는 fake clock/fake sleeper를 사용한다. unit test에서는 실제 sleep에 의존하지 않는다.

추천 사유: realtime 기능을 빠르고 결정적으로 검증할 수 있으며 새 scheduling dependency가 필요 없습니다.

B) unit test에서도 짧은 `asyncio.sleep`으로 실제 시간을 기다린다.

C) realtime 종료는 통합 테스트에서만 확인한다.

X) 기타

[Answer]: A

### Question 11. Test Organization

UOW-005 테스트 파일은 어떻게 구성할까요?

A) (권장) 예제 테스트는 `tests/test_runner_service.py`, `tests/test_runner_workers.py`, `tests/test_runner_checkpointing.py`, 순수 정책/PBT는 `tests/test_runner_policies.py`, `tests/test_runner_properties.py`, strategy는 `tests/strategies/runner.py`에 둔다. 기본 테스트는 fake dependency만 사용한다.

추천 사유: 기존 UOW 테스트 구조와 맞고, async orchestration 테스트와 순수 정책 테스트를 분리할 수 있습니다.

B) 모든 테스트를 하나의 큰 `tests/test_runner.py`에 둔다.

C) async worker 테스트만 작성하고 정책/PBT는 생략한다.

X) 기타

[Answer]: A

### Question 12. Public API Boundary

library caller와 future CLI/container/MCP adapter가 사용할 public API는 어떻게 둘까요?

A) (권장) `fmkorea_scraper.runner`에서 `JobRunner`, `JobRunDependencies`, `JobRunResult`를 노출한다. core API가 필요하면 이 객체를 얇게 감싸되, 환경변수/터미널 입력/구체 저장소 생성은 하지 않는다.

추천 사유: 단독 라이브러리와 후속 adapter가 같은 러너를 재사용할 수 있고, UOW-005가 runtime 설정 책임을 떠안지 않습니다.

B) CLI 실행 함수만 public API로 두고 library caller는 내부 모듈을 직접 import한다.

C) import 시점에 환경변수를 읽어 기본 runner와 저장소를 자동 생성한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-005 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-005 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-005 Infrastructure Design`이다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T17:21:25Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options preserve the baseline scraper JobRunner/checkpoint design while using FMKorea-specific collector, parser, output, media, and checkpoint contracts.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Compliance Note**: The design keeps Security/Resiliency/PBT requirements mapped to concrete patterns without adding CLI, container, MCP, PostgreSQL, parser-stage retry, SQS/DLQ, Docker, CDK, or platform scheduler scope to UOW-005.
- **Follow-up Questions**: Not required.
