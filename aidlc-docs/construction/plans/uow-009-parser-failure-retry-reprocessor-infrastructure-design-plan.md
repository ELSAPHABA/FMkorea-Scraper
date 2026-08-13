# Infrastructure Design 계획 - UOW-009 Parser Failure Retry Reprocessor

이 계획은 `UOW-009 Parser Failure Retry Reprocessor`의 논리 컴포넌트를 실제 실행/저장소/컨테이너/MCP 인프라 경계에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-009 Parser Failure Retry Reprocessor
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: retry CLI/container/MCP execution boundary, local failure input refs, S3/Garage failure input refs, existing success input refs, output/checkpoint reuse, optional retry smoke markers
- **Likely Infrastructure Scope**: existing worker container command, existing MCP tool binding, S3/Garage input read contract, local filesystem input contract, no new PostgreSQL schema, no new inbound network port, no dedicated retry daemon
- **Out Of Scope**: production Kubernetes/cloud provisioning, AWS CDK, SQS/DLQ, scheduler, database staging table, S3 prefix auto-discovery, CAPTCHA bypass

## Infrastructure Design 작업 체크리스트

- [x] UOW-009 Functional Design 승인 확인
- [x] UOW-009 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-009-parser-failure-retry-reprocessor/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 변경 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Infrastructure Footprint

UOW-009는 별도 인프라를 만들까요?

A) (권장) 새 컨테이너 이미지, 새 서버, 새 저장소, 새 큐를 만들지 않는다. 기존 worker container, CLI, MCP, Garage/S3 output, PostgreSQL checkpoint, `JobRunner` 실행 경계를 그대로 재사용한다.

추천 사유: UOW-009는 재처리 경로이지 독립 서비스가 아닙니다. 기존 실행/저장 인프라를 재사용하는 편이 가장 작고 기준 구조 계승에 맞습니다.

B) retry 전용 worker container image와 entrypoint를 별도로 만든다.

C) retry 전용 queue/DLQ worker 인프라를 함께 설계한다.

X) 기타

[Answer]: A

### Question 2. CLI And Container Invocation Boundary

컨테이너에서 retry는 어떻게 실행할까요?

A) (권장) 기존 container entrypoint가 전달받은 argv를 유지하므로, retry도 기존 CLI command `retry-parser-failures`를 container argv로 실행한다. 별도 retry shell script나 interactive wizard는 만들지 않는다.

추천 사유: 이미 worker container는 one-shot command 실행 구조입니다. retry만 별도 entrypoint로 빼면 운영 경로가 늘어납니다.

B) `docker-entrypoint-retry.sh`를 별도로 만든다.

C) 컨테이너에서는 retry를 지원하지 않고 로컬 CLI에서만 지원한다.

X) 기타

[Answer]: A

### Question 3. Failure Input Reference Contract

실패 JSONL input은 어떤 ref만 지원할까요?

A) (권장) 명시적으로 전달된 local path, `file://` ref, `s3://bucket/key`, 또는 설정된 bucket 기준 object key만 지원한다. output root나 S3 prefix 자동 탐색은 하지 않는다.

추천 사유: 재시도 대상이 명확해야 partial retry가 안전합니다. 자동 탐색은 편하지만 이번 유닛 범위를 크게 늘립니다.

B) local output root와 S3 prefix를 스캔해 최신 `failures.jsonl`을 자동 발견한다.

C) PostgreSQL checkpoint/report 정보를 기준으로 실패 input을 자동 찾는다.

X) 기타

[Answer]: A

### Question 4. Existing Success Input Contract

기존 성공 `posts.jsonl` skip input은 어떻게 받을까요?

A) (권장) optional explicit ref로만 받는다. local path, `file://`, `s3://bucket/key`, object key를 failure input과 같은 reader 경계로 읽는다.

추천 사유: 성공 skip은 편의 기능입니다. 명시 ref만 받으면 자동 발견 인프라 없이도 동작이 예측 가능합니다.

B) 이전 run report에서 output ref를 읽어 자동으로 성공 input을 찾는다.

C) PostgreSQL checkpoint에서 마지막 output 위치를 찾아 자동으로 성공 input을 찾는다.

X) 기타

[Answer]: A

### Question 5. S3/Garage Access Boundary

S3/Garage input read에 필요한 credential/env는 어떻게 다룰까요?

A) (권장) UOW-008의 기존 S3/Garage storage config와 env 주입 계약을 재사용한다. credential은 이미지에 bake하지 않고 `docker run --env` 또는 `--env-file`로 주입한다.

추천 사유: output 저장소와 input 읽기 저장소가 같은 S3-compatible 경계를 쓰면 추가 secret 경로가 생기지 않습니다.

B) retry input read 전용 S3 credential env를 새로 정의한다.

C) S3/Garage retry input은 인프라 설계에서 제외하고 local file만 지원한다.

X) 기타

[Answer]: A

### Question 6. PostgreSQL And Checkpoint Boundary

UOW-009에서 PostgreSQL schema나 checkpoint 인프라를 새로 만들까요?

A) (권장) 새 PostgreSQL table/schema를 만들지 않는다. retry 실행 중 checkpoint는 기존 `JobRunner`와 `PostgresCheckpointStore` 경계를 그대로 따른다.

추천 사유: retry selection에는 DB staging이 필요 없습니다. checkpoint는 이미 UOW-005/UOW-008 경계가 담당합니다.

B) retry candidate staging table을 PostgreSQL에 추가한다.

C) retry 전용 checkpoint table을 별도로 만든다.

X) 기타

[Answer]: A

### Question 7. Local Filesystem And Volume Boundary

retry 실행에 worker volume이 필요할까요?

A) (권장) worker container는 영속 volume을 요구하지 않는다. local input을 컨테이너에서 읽어야 하는 경우에만 사용자가 해당 파일/디렉터리를 read-only bind mount한다.

추천 사유: 기본 output/checkpoint는 Garage/S3와 PostgreSQL이 담당합니다. local failure input은 사용자가 명시적으로 넣는 예외 경로입니다.

B) worker container에 retry input/output용 persistent volume을 기본으로 붙인다.

C) 모든 retry input을 컨테이너 내부 작업 디렉터리에 복사해서 실행한다.

X) 기타

[Answer]: A

### Question 8. MCP Runtime Boundary

MCP에서 retry tool은 어떤 인프라 경계를 가질까요?

A) (권장) 기존 MCP stdio runtime과 `retry_parser_failures` tool binding을 재사용한다. MCP용 inbound network port나 HTTP/SSE transport는 이번 유닛에서 추가하지 않는다.

추천 사유: retry tool은 기존 MCP adapter의 도구 하나입니다. 네트워크 transport를 열면 인증/노출 설계가 새로 필요합니다.

B) retry 전용 HTTP MCP endpoint를 추가한다.

C) MCP에서는 retry tool을 제공하지 않는다.

X) 기타

[Answer]: A

### Question 9. Optional Smoke Infrastructure

UOW-009 smoke 테스트 인프라는 어떻게 둘까요?

A) (권장) 기본 테스트는 local fixture/fake runner만 사용한다. S3/Garage input read, MCP runtime, live retry smoke는 기존 marker/env gate를 재사용해 optional로 둔다.

추천 사유: 기본 테스트를 빠르고 안정적으로 유지하면서 실제 외부 인프라 확인 경로는 남길 수 있습니다.

B) S3/Garage와 MCP smoke를 기본 테스트에 포함한다.

C) smoke 테스트 경로를 만들지 않는다.

X) 기타

[Answer]: A

### Question 10. Future Queue/DLQ Boundary

향후 SQS/DLQ나 플랫폼 Job Queue 계획은 이번 인프라 설계에 포함할까요?

A) (권장) 이번 UOW-009 인프라에는 포함하지 않고 future work로만 기록한다. 현재는 사용자가 명시한 실패 input을 one-shot retry command로 처리한다.

추천 사유: DLQ/Queue는 통합 플랫폼 인프라 문제입니다. 지금 넣으면 retry selector 구현보다 배포 구조가 커집니다.

B) SQS/DLQ 리소스와 consumer contract를 이번 UOW-009 인프라에 포함한다.

C) local file 기반 DLQ 디렉터리를 이번에 만든다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-009 Infrastructure Design 산출물 2개를 생성합니다.
4. shared infrastructure 변경 필요 여부를 기록합니다.
5. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-009 Infrastructure Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q10 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure Note**: No shared infrastructure change is required. UOW-009 reuses the existing worker container, MCP stdio runtime, Garage/S3 storage config, PostgreSQL checkpoint store, and optional smoke marker contract.
- **Operational Boundary**: Retry remains a one-shot command over explicit failure/success input refs. Queue/DLQ, scheduler, S3 prefix discovery, and new database staging remain future platform work.
