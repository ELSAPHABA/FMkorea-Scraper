# Infrastructure Design 계획 - UOW-008 Container, MCP, And Test Harness

이 계획은 `UOW-008 Container, MCP, And Test Harness`의 논리 컴포넌트를 실제 컨테이너/MCP/저장소/테스트 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-008 Container, MCP, And Test Harness
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: worker container image, container entrypoint, runtime env injection, PostgreSQL checkpoint endpoint, Garage/S3-compatible object storage endpoint, MCP server entrypoint, optional smoke infrastructure, test markers
- **Likely Infrastructure Scope**: Dockerfile, optional smoke compose contract, env-var contract, storage/network boundary documentation, shared infrastructure notes for Garage/PostgreSQL/MCP
- **Out Of Scope**: production Kubernetes deployment, managed cloud provisioning, distributed queue, background scheduler, GUI/Web UI, CAPTCHA bypass

## Infrastructure Design 작업 체크리스트

- [x] UOW-008 Functional Design 승인 확인
- [x] UOW-008 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Worker Container Artifact

worker container 이미지는 어떻게 구성할까요?

A) (권장) 단일 `Dockerfile`과 `.dockerignore`를 만들고 Python 3.11+ slim 계열 이미지에 `pip install .[s3,postgres]`로 설치한다. `.dockerignore`는 local state, cache, output, `.env` secret 후보, 문서 산출물을 build context에서 제외한다. 루트에 `docker-entrypoint.sh`를 생성하고 Dockerfile `ENTRYPOINT`는 이 스크립트를 호출한다. 스크립트는 전달받은 argv를 유지한 채 `python -m fmkorea_scraper.adapters.container "$@"`로 위임한다.

추천 사유: UOW-008의 worker는 one-shot container입니다. 여러 이미지 target이나 복잡한 build stage는 아직 필요하지 않고, 기준 구조 계승에 가장 가깝습니다.

B) multi-stage Dockerfile과 worker/mcp/test용 target 이미지를 모두 만든다.

C) Dockerfile은 만들지 않고 문서에 실행 방법만 남긴다.

X) 기타

[Answer]: A

### Question 2. MCP Runtime Artifact

MCP 서버 실행 산출물은 어떻게 둘까요?

A) (권장) MCP는 별도 entrypoint `python -m fmkorea_scraper.adapters.mcp` 또는 console script로 실행하고, 설치 환경에서 `.[mcp]` extra를 명시적으로 설치한다. worker container 기본 이미지에는 MCP extra를 넣지 않는다.

추천 사유: MCP는 모든 worker 실행에 필요한 런타임이 아닙니다. optional extra와 별도 entrypoint가 설치/이미지 크기와 보안 경계를 작게 유지합니다.

B) worker container 이미지에 MCP 서버도 항상 포함하고 같은 컨테이너에서 실행한다.

C) MCP는 인프라 설계에서 제외한다.

X) 기타

[Answer]: A

### Question 3. MCP Transport Boundary

MCP transport는 1차로 어떻게 둘까요?

A) (권장) 기본 MCP transport는 local agent 연동에 적합한 stdio 기반으로 두고, HTTP/SSE 같은 네트워크 노출형 transport는 후속 배포 단계로 미룬다.

추천 사유: stdio는 포트/인증/네트워크 노출이 없어 1차 MCP adapter에 가장 작고 안전합니다.

B) HTTP/SSE MCP 서버를 기본으로 열고 포트를 문서화한다.

C) transport는 구현자가 나중에 임의로 선택하게 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 4. Optional Compose Smoke Stack

Garage/PostgreSQL smoke 테스트용 compose는 어떻게 둘까요?

A) (권장) 기본 테스트 gate에는 포함하지 않고, optional smoke용 compose 계약만 둔다. 필요하면 `docker-compose.smoke.yml` 또는 문서화된 compose 예시로 PostgreSQL, Garage, worker를 띄운다.

추천 사유: 외부 서비스가 기본 테스트를 불안정하게 만들지 않으면서, 실제 통합 확인 경로는 남길 수 있습니다.

B) 기본 테스트에서 항상 compose로 PostgreSQL과 Garage를 띄운다.

C) compose smoke 경로도 만들지 않는다.

X) 기타

[Answer]: A

운영 제한: compose는 local/smoke 테스트용 계약으로만 사용한다. 운영 시 PostgreSQL/Garage는 공통 인프라로 분리하고, FMKorea scraper 및 향후 타 커뮤니티 scraper 컨테이너는 환경변수로 해당 공통 저장소에 접속한다. 스크래퍼 컨테이너가 저장소 컨테이너의 생명주기를 소유하지 않는다.

### Question 5. Secret And Environment Injection

컨테이너 secret/env 주입은 어떻게 둘까요?

A) (권장) `docker run --env` 또는 `--env-file`로 런타임에 주입하고, 이미지에는 DB/S3/Proxy credential을 절대 bake하지 않는다. entrypoint는 documented allow-list env만 읽는다.

추천 사유: secret을 이미지에 넣지 않는 것이 기본 보안 경계입니다. allow-list env는 오류와 로그 redaction도 단순하게 만듭니다.

B) Dockerfile build arg로 credential을 넣어 이미지에 포함한다.

C) 컨테이너 내부 `.env` 파일만 사용하고 `docker run --env`는 지원하지 않는다.

X) 기타

[Answer]: A

### Question 6. Network Boundary

worker와 MCP의 네트워크 경계는 어떻게 문서화할까요?

A) (권장) worker container는 inbound port를 열지 않는다. outbound만 FMKorea, PostgreSQL, Garage/S3 endpoint로 필요하다. MCP stdio mode는 inbound port가 없고, HTTP transport는 후속 단계에서 별도 인증/노출 설계를 한다.

추천 사유: one-shot worker는 서버가 아닙니다. 기본 inbound surface를 0으로 두는 편이 가장 안전합니다.

B) worker도 health check/API port를 기본으로 연다.

C) 네트워크 경계는 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 7. Persistent Storage Boundary

영속 저장소와 volume 경계는 어떻게 둘까요?

A) (권장) worker container 자체는 영속 볼륨을 요구하지 않는다. JSONL/media는 Garage/S3, checkpoint는 PostgreSQL에 저장한다. optional compose에서는 PostgreSQL/Garage에만 named volume을 둔다.

추천 사유: worker spool은 임시 파일이고 resume은 새 run object를 만듭니다. 영속성은 외부 저장소가 담당해야 합니다.

B) worker container에도 output/spool 영속 볼륨을 기본으로 붙인다.

C) 모든 데이터를 worker local filesystem에 저장한다.

X) 기타

[Answer]: A

### Question 8. PostgreSQL Schema Initialization

PostgreSQL schema 초기화는 인프라에서 어떻게 다룰까요?

A) (권장) adapter가 `CREATE TABLE IF NOT EXISTS`를 실행하므로 별도 migration container나 init SQL은 필수로 두지 않는다. optional smoke compose는 빈 PostgreSQL을 제공하면 된다.

추천 사유: checkpoint table 하나는 adapter idempotent init으로 충분합니다. init container/migration framework는 과합니다.

B) compose에 init SQL 파일을 반드시 마운트한다.

C) 사용자가 수동으로 DB schema를 만든 뒤에만 worker를 실행하게 한다.

X) 기타

[Answer]: A

운영 제한: PostgreSQL schema 초기화는 adapter의 idempotent init 책임이며, compose init SQL에 의존하지 않는다. compose가 있다면 빈 PostgreSQL/Garage를 띄우는 smoke 보조 수단이다.

### Question 9. Container Signal And Exit Boundary

컨테이너 종료 signal과 exit code 경계는 어떻게 둘까요?

A) (권장) SIGTERM/KeyboardInterrupt는 가능한 경우 `JobRunner.request_stop()` 또는 기존 stop API에 연결해 graceful checkpoint/report 경로를 탄다. 종료 코드는 완료 `0`, validation `2`, 중단/실행 오류 `1`을 유지한다.

추천 사유: Docker stop과 로컬 Ctrl+C 모두 "중단점 저장 후 종료"라는 같은 계약을 따라야 합니다.

B) SIGTERM은 즉시 프로세스를 종료한다.

C) signal 처리는 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 10. Shared Infrastructure Artifact

UOW-008에서 shared infrastructure 산출물이 필요할까요?

A) (권장) 필요하다. UOW-008은 worker container, Garage/S3, PostgreSQL, MCP entrypoint, optional smoke contract를 묶는 첫 배포 단위이므로 shared infrastructure 내용을 Infrastructure Design 문서에 env, 네트워크, volume, smoke gate 요약으로 포함한다. 단, production Kubernetes/cloud provisioning은 제외한다.

추천 사유: UOW-008부터 여러 외부 런타임이 연결됩니다. 운영자가 볼 수 있는 shared infra 요약이 필요하지만 별도 대규모 배포 산출물까지는 아직 과합니다.

B) 필요하지 않다. 기존 unit별 infrastructure 문서만 둔다.

C) Kubernetes/managed cloud production 설계까지 shared infra에 포함한다.

X) 기타

[Answer]: A

운영 제한: shared infrastructure 문서는 공통 PostgreSQL/Garage, 네트워크, volume, env 계약을 요약한다. 특정 scraper 전용 저장소 묶음이나 production Kubernetes/cloud provisioning은 포함하지 않는다.

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-008 Infrastructure Design 산출물 2개를 생성합니다.
4. shared infrastructure 산출물 필요 여부를 기록합니다.
5. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-008 Infrastructure Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q10 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure Note**: Shared infrastructure is documented inside UOW-008 Infrastructure Design as a common PostgreSQL/Garage/env/network/volume/smoke contract, not as production Kubernetes or managed cloud provisioning.
- **Operational Boundary**: Compose remains local/smoke only. Scraper worker containers connect to common PostgreSQL/Garage endpoints through runtime env and do not own storage service lifecycle.
