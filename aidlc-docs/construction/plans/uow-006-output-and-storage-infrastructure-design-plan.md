# Infrastructure Design 계획 - UOW-006 Output And Storage

이 계획은 `UOW-006 Output And Storage`의 논리 컴포넌트를 실제 실행/검증 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-006 Output And Storage
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: local JSONL/media/report/checkpoint output, S3-compatible object storage adapter boundary, optional Garage smoke contract, optional Polars smoke environment, storage factory/config contract
- **Likely Infrastructure Scope**: standalone deployment 없음, local filesystem과 S3-compatible storage 접점, env-gated smoke test 경계만 해당
- **Baseline Inheritance**: `A)` 선택지는 디시인사이드 스크래퍼의 출력/저장소 인프라 경계를 최대한 계승하는 권장안으로 작성한다.
- **Out Of Scope**: link collection traversal, post worker topology, HTTP media download, PostgreSQL checkpoint adapter, queue/DLQ ownership, CLI wizard, container entrypoint, MCP server hosting, AWS CDK resources

## Infrastructure Design 작업 체크리스트

- [x] UOW-006 Functional Design 승인 확인
- [x] UOW-006 NFR Requirements 승인 확인
- [x] UOW-006 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-006-output-and-storage/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-006-output-and-storage/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-006 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-006은 import 가능한 output/storage library이며, 독립 서비스/컨테이너 배포는 N/A로 문서화한다.

추천 사유: 이 unit은 수집 결과를 파일 또는 S3-compatible storage에 쓰는 내부 계층입니다. 실제 CLI 실행, worker container, MCP hosting, CDK 배포는 후속 unit에서 다루는 편이 책임이 작고 기존 구조 계승에 맞습니다.

B) local 개발/검증용 Python 실행 환경만 Infrastructure Design에 포함한다.

C) scraper worker/container 배포 환경까지 UOW-006에서 미리 정의한다.

X) 기타

[Answer]: A

### Question 2. Local Output Layout

local filesystem 출력 경로는 어떻게 정의할까요?

A) (권장) `StorageConfig.base_output_path`를 기준으로 `outputs/<job_id>/<run_id>/` 아래에 JSONL, media, report, checkpoint 파일을 둔다. 값이 없으면 실행 시점의 working directory를 기준으로 삼는다.

추천 사유: 기존 스토리지 설정을 그대로 사용하면서도 Job/run 단위 파일 충돌을 피할 수 있습니다. Windows CLI, container volume mount, test temp directory에 모두 같은 규칙을 적용할 수 있습니다.

B) 항상 repository root의 `outputs/`에 저장한다.

C) 날짜 기준 경로만 사용하고 `job_id`, `run_id`는 파일명에만 둔다.

X) 기타

[Answer]: A

### Question 3. Local Checkpoint Infrastructure

checkpoint 저장소는 UOW-006에서 어디까지 정의할까요?

A) (권장) local file checkpoint만 UOW-006에 포함한다. PostgreSQL checkpoint adapter는 후속 unit에서 별도로 구현한다고 문서화한다.

추천 사유: JobRunner가 곧바로 사용할 최소 checkpoint는 파일 하나로 충분합니다. PostgreSQL까지 섞으면 출력 저장소와 운영 DB 책임이 한 unit에 합쳐집니다.

B) local file과 PostgreSQL checkpoint adapter를 함께 설계한다.

C) checkpoint는 저장하지 않고 report 파일만 남긴다.

X) 기타

[Answer]: A

### Question 4. S3-Compatible Object Storage Boundary

S3-compatible storage 인프라는 어디까지 정의할까요?

A) (권장) Garage를 기본 대상 예시로 두되, UOW-006은 bucket/endpoint/prefix/region 설정 계약과 object key layout만 정의한다. Garage 서버 생성, bucket 생성, policy 설정은 하지 않는다.

추천 사유: 기능명세서는 Garage 우선, SeaweedFS 확장 가능성을 요구합니다. 코드는 S3-compatible contract에 맞추고, 실제 서버 구성은 운영/배포 단계에서 분리하는 것이 덜 묶입니다.

B) local 개발용 Garage docker-compose까지 UOW-006에서 정의한다.

C) Garage 전용 설정으로 고정하고 다른 S3-compatible storage는 고려하지 않는다.

X) 기타

[Answer]: A

### Question 5. S3 Credentials And Secrets

S3-compatible storage credentials는 어떻게 다룰까요?

A) (권장) credentials는 runtime env/config로 주입받고, UOW-006은 S3 mode 선택 시 필수값 존재만 검증한다. access key, secret key, endpoint credential fragment는 JSONL/checkpoint/report/log에 기록하지 않는다.

추천 사유: 저장소 연결은 필요하지만 secret 저장소 구현은 이 unit의 책임이 아닙니다. 지금 필요한 것은 쓰기 실패 없이 연결하고 민감정보를 남기지 않는 경계입니다.

B) `.env` 파일 생성과 저장까지 UOW-006이 처리한다.

C) credentials를 checkpoint에 저장해 retry 실행을 단순화한다.

X) 기타

[Answer]: A

### Question 6. Optional S3 Smoke Test Infrastructure

S3-compatible storage smoke test는 어떻게 둘까요?

A) (권장) 기본 test에서는 skip하고, `FMKOREA_S3_SMOKE_ENABLED=true`와 endpoint/bucket/credential 설정이 있을 때만 작은 JSONL object 1개 쓰기/읽기/삭제 검증을 수행한다고 문서화한다.

추천 사유: 외부 object storage 의존성을 기본 테스트에 넣으면 개발 환경이 무거워집니다. env-gated smoke test면 Garage 실연결 검증은 가능하면서도 기본 검증은 가볍게 유지됩니다.

B) 모든 CI에서 S3 smoke test를 필수로 실행한다.

C) S3 smoke test 경로를 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 7. Polars Smoke Environment

Polars 가공 가능성 검증은 인프라 관점에서 어떻게 둘까요?

A) (권장) 별도 인프라는 만들지 않고, optional `analysis` extra가 설치된 환경에서 JSONL sample을 `polars.read_ndjson`로 읽는 smoke test만 둔다. 기본 test는 Polars가 없으면 skip한다.

추천 사유: UOW-006의 책임은 Polars-friendly JSONL을 쓰는 것입니다. 분석 플랫폼이나 notebook runtime을 지금 만들 필요는 없습니다.

B) Polars를 core dependency로 고정하고 모든 test에서 필수 실행한다.

C) Polars 검증은 문서에서만 언급하고 테스트하지 않는다.

X) 기타

[Answer]: A

### Question 8. Generated Output Safety

runtime output 파일은 repository와 어떻게 분리할까요?

A) (권장) 생성 파일은 `StorageConfig.base_output_path` 아래에만 쓰고, tests는 temp directory를 사용한다. 문서에는 `outputs/`, `*.jsonl`, media download 결과, checkpoint/report 파일이 generated artifact라고 명시한다.

추천 사유: 실제 smoke test와 개발 실행이 repository 문서/소스와 섞이지 않아야 합니다. base path 하나만 기준으로 두면 CLI와 container에서도 같은 규칙을 쓸 수 있습니다.

B) repository root에 output을 쓰고 사용자가 직접 정리한다.

C) 모든 generated output을 package directory 내부에 저장한다.

X) 기타

[Answer]: A

### Question 9. Storage Factory And Configuration Boundary

storage factory는 설정과 환경변수를 어떻게 받을까요?

A) (권장) `StorageFactory`는 이미 구성된 `StorageConfig`를 받아 local 또는 S3-compatible store를 만든다. 환경변수 읽기와 CLI/container mapping은 adapter 계층에서 처리한다.

추천 사유: core library가 환경변수를 직접 읽으면 import 재사용과 테스트가 지저분해집니다. 설정 객체를 경계로 두면 CLI, container, MCP가 같은 storage 코드를 공유할 수 있습니다.

B) `StorageFactory`가 직접 환경변수를 읽고 store를 만든다.

C) CLI adapter만 storage를 만들고 library factory는 두지 않는다.

X) 기타

[Answer]: A

### Question 10. Deployment Architecture Documentation

UOW-006의 deployment architecture 문서는 어떤 수준으로 작성할까요?

A) (권장) 배포 리소스는 N/A로 두고, local filesystem layout, S3-compatible object layout, optional smoke test 실행 조건, 후속 container/CDK 연결 지점만 문서화한다.

추천 사유: 이 단계에서 Docker, Compose, CDK, queue를 만들면 저장소 라이브러리보다 운영 설계가 커집니다. 후속 unit이 붙을 수 있는 경계만 확정하면 충분합니다.

B) Docker Compose 기반 local Garage/PostgreSQL 구성을 함께 문서화한다.

C) AWS CDK 리소스 초안을 UOW-006에서 바로 작성한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-006 Infrastructure Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T13:44:29Z
- **Selected Options**: Q1-Q10 were A.
- **Inheritance Note**: All selected A options follow the baseline scraper output/storage infrastructure boundary as far as it fits FMKorea.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure**: No shared infrastructure artifact is required for UOW-006. Garage provisioning, PostgreSQL checkpoint storage, SQS/DLQ, container entrypoints, and AWS CDK resources remain deferred.

## Infrastructure Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-006-output-and-storage/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/uow-006-output-and-storage/infrastructure-design/deployment-architecture.md`

승인 후 다음 단계는 `UOW-006 Code Generation`이다.
