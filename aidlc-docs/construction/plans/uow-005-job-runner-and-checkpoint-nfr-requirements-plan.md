# NFR Requirements 계획 - UOW-005 Job Runner And Checkpoint

이 계획은 `UOW-005 Job Runner And Checkpoint`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-005 Job Runner And Checkpoint
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-006 Output And Storage
- **Primary Stories**: US-012, US-013
- **Supporting Stories**: US-001, US-003, US-005, US-006, US-010, US-014, US-015, US-016, US-017
- **Scope**: async Job lifecycle, collector/post-worker queue orchestration, checkpoint save/load/resume, durable output-before-checkpoint ordering, fail-closed stop behavior, realtime termination, safe failure/report output
- **Security Focus**: no secret/raw payload in checkpoint/failure/report/logs, CAPTCHA/block fail-closed, explicit dependency injection, no env/CLI reads in core runner
- **Resiliency Focus**: worker cancellation, store finalization, stop-class checkpoint, resume dedupe, storage-before-checkpoint ordering, bounded queue backpressure
- **PBT Focus**: completed-key dedupe, checkpoint cadence, resume skip behavior, stop reason mapping, report counter consistency
- **Baseline Inheritance**: `A)` 선택지는 기준 스크래퍼의 JobRunner/checkpoint NFR 경계를 최대한 계승하되, FMKorea collector/parser/storage 조립 구조를 반영하는 권장안으로 작성한다.
- **Out Of Scope**: CLI prompt UX, container entrypoint, PostgreSQL checkpoint adapter, MCP hosting, parser-stage retry reprocessor implementation, SQS/DLQ, Docker, AWS CDK, centralized platform scheduler

## NFR Requirements 작업 체크리스트

- [x] UOW-005 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-requirements/tech-stack-decisions.md` 생성

## NFR Requirements Questions

### Question 1. Async Runtime Dependency

JobRunner의 async orchestration은 어떤 런타임 의존성을 사용할까요?

A) (권장) Python 표준 `asyncio`만 사용한다. `asyncio.Queue`, task group/cancel 패턴, semaphore를 사용하고 `anyio`, Celery, Dramatiq, SQS client 같은 새 의존성은 추가하지 않는다.

추천 사유: 기존 설계와 기능명세서가 `asyncio` 기반 멀티 워커를 전제로 합니다. UOW-005는 프로세스 내부 orchestration이므로 표준 라이브러리로 충분합니다.

B) `anyio`를 추가해 runner를 backend-neutral하게 만든다.

C) 외부 queue/worker framework를 도입한다.

X) 기타

[Answer]: A

### Question 2. Queue Backpressure Reliability

후보 큐가 많아질 때 안정성 요구사항은 어떻게 둘까요?

A) (권장) `queue_max_size`가 있으면 bounded `asyncio.Queue`로 collector enqueue를 대기시킨다. 후보를 조용히 버리지 않고, stop event 발생 시 enqueue 대기를 빠져나올 수 있어야 한다.

추천 사유: 데이터 손실 없이 메모리 증가를 제한할 수 있습니다. 큐 overflow 시 drop 정책은 수집 누락으로 이어지기 쉽습니다.

B) 큐가 가득 차면 새 후보를 버리고 warning만 남긴다.

C) 항상 unbounded queue를 사용한다.

X) 기타

[Answer]: A

### Question 3. Worker Cancellation And Finalization

취소/중단 시 worker와 저장소 finalization은 어떻게 보장할까요?

A) (권장) stop-class event에서 collector를 멈추고 worker task를 drain 또는 cancel한 뒤, output/failure stores의 `finalize`를 best-effort로 호출한다. finalization 실패는 safe failure/report에 반영한다.

추천 사유: 긴 수집 중단 시 파일 handle, S3 spool, report 상태를 가능한 한 정리해야 합니다. 단, finalization이 실패해도 raw secret이나 payload를 남기지 않아야 합니다.

B) 취소되면 즉시 프로세스를 종료하고 finalize를 시도하지 않는다.

C) worker가 자연 종료할 때까지 무기한 기다린다.

X) 기타

[Answer]: A

### Question 4. Checkpoint Durability Boundary

checkpoint 저장 내구성은 어떤 경계에 맞출까요?

A) (권장) UOW-006 저장소 호출이 성공한 뒤에만 completed key를 추가하고 checkpoint를 저장한다. checkpoint 저장 실패는 runner failure로 간주하고 safe failure/report에 반영한다.

추천 사유: 저장되지 않은 게시글을 완료 처리하면 재개 시 누락이 발생합니다. 실패 시 중복 재시도 가능성을 남기는 편이 데이터 손실보다 낫습니다.

B) parser 성공 직후 completed key를 추가하고 checkpoint를 먼저 저장한다.

C) checkpoint 저장 실패는 무시하고 계속 진행한다.

X) 기타

[Answer]: A

### Question 5. Checkpoint Cadence And Overhead

실행 중 checkpoint 저장 빈도는 성능/내구성 관점에서 어떻게 둘까요?

A) (권장) 기본값은 저장 성공 10개마다 running checkpoint 저장이다. stop/error/CAPTCHA/block/timeout/completion에서는 즉시 저장한다. 이 값은 UOW-005 내부 상수로 시작한다.

추천 사유: 매 게시글 checkpoint보다 I/O 부담이 작고, 10개 단위 손실 한계는 기능명세서와 일치합니다. 설정 노출은 CLI 단계에서 필요해질 때 추가하면 됩니다.

B) 매 게시글마다 checkpoint를 저장한다.

C) 정상 실행 중에는 checkpoint를 전혀 저장하지 않는다.

X) 기타

[Answer]: A

### Question 6. Resume Idempotency

resume 중 중복 저장 방지는 어떤 수준으로 보장할까요?

A) (권장) checkpoint의 `completed_keys`를 set처럼 사용해 이미 저장 성공한 후보는 detail fetch 전에 skip한다. resume은 새 `run_id`를 쓰고 이전 run JSONL을 수정하지 않는다.

추천 사유: 정확한 in-flight 복원 없이도 중복 저장을 줄일 수 있습니다. 원본 run을 수정하지 않으면 감사와 재처리 입력도 명확합니다.

B) 기존 JSONL을 읽어 dedupe하고 같은 파일에 이어 쓴다.

C) resume에서는 dedupe를 하지 않고 모두 다시 저장한다.

X) 기타

[Answer]: A

### Question 7. Stop-Class Error Handling

CAPTCHA, 차단, timeout, manual stop은 어떤 비기능 정책으로 처리할까요?

A) (권장) fail-closed로 즉시 새 작업 수집을 멈추고 stopped checkpoint를 저장한다. CAPTCHA 자동 우회/풀이/브라우저 조작은 금지한다.

추천 사유: 요구사항과 안전 정책 모두 자동 우회가 아니라 상태 보존 후 중단을 요구합니다.

B) CAPTCHA/block도 retry를 반복해 최대한 계속 수집한다.

C) CAPTCHA/block 감지는 로그만 남기고 worker를 계속 유지한다.

X) 기타

[Answer]: A

### Question 8. Safe Failure And Log Payload

runner의 failure/report/log payload는 어떤 redaction 기준을 적용할까요?

A) (권장) allow-list 기반 safe context만 남긴다. job_id, run_id, stage, reason, retryable, post key, URL, response kind, counter, stop reason은 허용하고 raw HTML/body/content, headers, cookie, proxy password, token, S3 credentials는 금지한다.

추천 사유: runner는 여러 하위 계층의 예외를 모으므로 민감정보가 섞일 가능성이 큽니다. allow-list가 가장 작은 안전장치입니다.

B) 알려진 secret 키워드만 masking하고 나머지 context는 모두 저장한다.

C) 디버깅 편의를 위해 원본 exception details를 모두 저장한다.

X) 기타

[Answer]: A

### Question 9. Media Download Resource Guard

`MediaMode.DOWNLOAD`의 리소스 제한은 어떻게 둘까요?

A) (권장) media download는 post worker 내부에서 `media_worker_count` 기반 semaphore로 동시성을 제한한다. 개별 다운로드는 UOW-002 timeout/retry 정책을 따르고, media store는 bytes만 받는다.

추천 사유: 별도 media queue/pool을 만들지 않아도 동시 요청 수를 제한할 수 있습니다. 다운로드 정책은 이미 UOW-002에 있으므로 중복 구현하지 않습니다.

B) 모든 media download를 제한 없이 동시에 실행한다.

C) 별도 media worker queue를 반드시 만든다.

X) 기타

[Answer]: A

### Question 10. Realtime Termination Determinism

실시간 종료 조건은 테스트 가능성과 결정성을 어떻게 보장할까요?

A) (권장) runner는 주입된 clock을 사용해 `duration_seconds`와 `end_at`을 평가하고, 테스트에서는 fake clock을 사용한다. 종료 도달 후 새 후보 수집을 멈추고 queued work drain 후 completed 처리한다.

추천 사유: 실제 시간에 의존한 테스트는 불안정합니다. clock 주입은 작은 비용으로 realtime 종료를 결정적으로 검증할 수 있습니다.

B) 항상 실제 wall-clock을 직접 읽고 테스트는 sleep으로 검증한다.

C) 실시간 종료 조건 테스트는 생략한다.

X) 기타

[Answer]: A

### Question 11. Test Strategy

UOW-005 기본 테스트는 어떤 범위로 둘까요?

A) (권장) fake collector/detail/http/storage/clock으로 default tests를 구성한다. queue fan-out, completed-key skip, storage-before-checkpoint, checkpoint cadence, stop-class checkpoint, resume, media download semaphore, report counters를 검증한다. live network/storage는 사용하지 않는다.

추천 사유: JobRunner는 orchestration 계층이므로 fake dependency로 결정적 테스트를 만드는 것이 빠르고 안정적입니다.

B) 실제 FMKorea HTTP와 실제 local/S3 저장소를 모두 사용해 통합 테스트 위주로 검증한다.

C) runner는 수동 smoke만 하고 자동 테스트는 생략한다.

X) 기타

[Answer]: A

### Question 12. Property-Based Test Scope

Property-Based Test는 어떤 runner 규칙에 적용할까요?

A) (권장) completed-key dedupe idempotence, checkpoint cadence calculation, stop reason mapping, report counter consistency, resume skip set behavior 같은 순수 정책에 적용한다. 실제 async task scheduling 랜덤화는 example tests로 제한한다.

추천 사유: PBT는 순수 정책에 적합합니다. async scheduling 전체를 PBT로 흔들면 느리고 불안정해집니다.

B) 모든 worker scheduling interleaving을 PBT로 생성한다.

C) UOW-005에서는 PBT를 생략한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-005 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-005 NFR Design으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T17:12:54Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper JobRunner/checkpoint NFR boundary while applying FMKorea collector/parser/storage integration.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Dependency Note**: UOW-005 uses only Python standard `asyncio` for orchestration and fake dependencies for default tests. SQS/DLQ, PostgreSQL checkpoint, container runtime, MCP, and CDK remain deferred.
- **Follow-up Questions**: Not required.

## NFR Requirements Review Gate

검토 대상:

- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/uow-005-job-runner-and-checkpoint/nfr-requirements/tech-stack-decisions.md`

승인 후 다음 단계는 `UOW-005 NFR Design`이다.
