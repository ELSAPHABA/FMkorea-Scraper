# NFR Requirements 계획 - UOW-008 Container, MCP, And Test Harness

이 계획은 `UOW-008 Container, MCP, And Test Harness`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-008 Container, MCP, And Test Harness
- **Functional Design**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter
- **Primary Stories**: US-016, US-017
- **Supporting Stories**: US-002, US-010, US-012, US-013, US-015
- **Scope**: one-shot worker container, `docker-entrypoint.sh`, `.dockerignore`, PostgreSQL checkpoint adapter, S3-compatible/Garage output wiring, MCP tool adapter, result quality fixture harness, optional smoke hooks
- **Security Focus**: database/S3/MCP credential redaction, Proxy/cookie secret redaction, no raw env/body/header/content leakage, safe adapter errors, import safety
- **Resiliency Focus**: container one-shot exit codes, checkpoint load/save reliability, S3 durable upload before checkpoint progress, Docker build context hygiene, optional smoke isolation
- **PBT Focus**: env-to-config mapping, checkpoint serialization round trip, MCP input/output JSON safety, S3 key/path generation, quality fixture invariants, secret redaction allow-list
- **Out Of Scope**: parser-failure retry execution engine, distributed scheduler, background MCP job registry, production Kubernetes manifests, CAPTCHA bypass, GUI/Web UI

## NFR Requirements 작업 체크리스트

- [x] UOW-008 Functional Design 승인 확인
- [x] Functional Design 산출물 확인
- [x] Security Baseline 적용 항목 확인
- [x] Resiliency Baseline 적용 항목 확인
- [x] Property-Based Testing 적용 항목 확인
- [x] NFR Requirements 질문 생성
- [x] NFR Requirements 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/nfr-requirements/tech-stack-decisions.md` 생성

## NFR Requirements Questions

### Question 1. PostgreSQL Driver Dependency

PostgreSQL checkpoint adapter 의존성은 어떻게 둘까요?

A) (권장) `postgres` optional extra에 `psycopg[binary]>=3,<4`를 추가하고, 컨테이너 이미지는 `.[postgres,s3]` 또는 동등한 extra 조합으로 설치한다. 기본 local/library 설치에는 PostgreSQL driver를 넣지 않는다.

추천 사유: DCinside 구조를 계승하면서 PostgreSQL을 컨테이너 모드 전용 선택 의존성으로 유지할 수 있습니다. 기본 설치를 가볍게 유지하고, 공식 driver를 사용합니다.

B) `asyncpg`를 기본 런타임 의존성으로 추가한다.

C) PostgreSQL adapter 구현을 후속 unit으로 미룬다.

X) 기타

[Answer]: A

### Question 2. S3/Garage Dependency Policy

S3-compatible output 의존성은 어떻게 둘까요?

A) (권장) 기존 `s3` optional extra의 `boto3` 경계를 재사용하고, S3-compatible/Garage output도 이 경계를 사용한다. `aioboto3`/`aiobotocore` 같은 추가 async S3 의존성은 넣지 않는다.

추천 사유: DCinside와 같은 저장소 경계를 계승합니다. S3 write는 게시글 HTTP 요청보다 병목 우선순위가 낮고, 추가 async SDK는 의존성 비용이 큽니다.

B) `aioboto3` 또는 `aiobotocore`를 추가해 S3 업로드도 async 전용으로 만든다.

C) 컨테이너에서도 local output만 사용하고 S3/Garage output은 미룬다.

X) 기타

[Answer]: A

### Question 3. Container Image Strategy

컨테이너 이미지는 어떤 빌드 전략으로 둘까요?

A) (권장) 단일 Dockerfile을 두고 Python 3.11+ slim 계열 이미지에서 `pip install .[s3,postgres]`로 설치한다. Dockerfile `ENTRYPOINT`는 `/app/docker-entrypoint.sh`를 호출하고, 이 스크립트가 `python -m fmkorea_scraper.adapters.container "$@"`로 위임한다.

추천 사유: DCinside의 worker container 구조를 그대로 계승합니다. 단일 one-shot worker 이미지면 현재 요구에 충분합니다.

B) builder/runtime multi-stage Dockerfile과 여러 target 이미지를 만든다.

C) Dockerfile은 만들지 않고 문서로만 실행 방법을 남긴다.

X) 기타

[Answer]: A

### Question 4. Docker Build Context Hygiene

`.dockerignore`와 shell script 줄바꿈 관리는 어떻게 할까요?

A) (권장) `.dockerignore`로 `.git`, 가상환경, 캐시, 출력물, `.env` secret 후보, docs, AI-DLC workflow, build 산출물을 제외한다. `docker-entrypoint.sh`는 LF 줄바꿈과 실행 권한을 보장한다.

추천 사유: DCinside에서 검증한 Docker build context hygiene을 계승합니다. Windows 개발 환경에서도 Linux container shell script 실행 실패를 줄입니다.

B) `.dockerignore` 없이 Dockerfile의 명시적 `COPY`만 신뢰한다.

C) `COPY . .`를 사용하고 이미지 내부에서 불필요 파일을 삭제한다.

X) 기타

[Answer]: A

### Question 5. Container Environment Validation

컨테이너 환경변수 validation과 secret 처리는 어떻게 할까요?

A) (권장) container entrypoint 실행 시점에만 `os.environ`을 읽고, 필수 env 누락은 validation error exit code `2`로 반환한다. 로그와 오류에는 secret 값을 절대 출력하지 않고 key 이름과 safe reason만 출력한다.

추천 사유: import safety를 지키고, 컨테이너 배포 실수를 빠르게 발견하면서 secret leak 위험을 줄입니다.

B) import 시점에 환경변수를 읽어 전역 config로 저장한다.

C) 누락 env는 런타임 중 실패할 때까지 검증하지 않는다.

X) 기타

[Answer]: A

### Question 6. PostgreSQL Schema Management

PostgreSQL checkpoint table 생성은 어떻게 처리할까요?

A) (권장) adapter가 시작 시 또는 첫 save/load 전에 `CREATE TABLE IF NOT EXISTS fmkorea_checkpoints (...)`를 idempotent하게 실행한다. 별도 migration framework는 도입하지 않는다.

추천 사유: 테이블이 하나이고 JSON 저장 구조라 migration framework는 과합니다. DCinside와 같은 단순 checkpoint store 경계를 계승합니다.

B) Alembic 같은 migration framework를 추가한다.

C) DB schema는 사용자가 수동으로 만들어야 하며 adapter는 생성하지 않는다.

X) 기타

[Answer]: A

### Question 7. S3 Spool Durability

S3 JSONL append를 위한 local spool 파일은 어떻게 다룰까요?

A) (권장) process-local temp spool을 사용하고, append마다 전체 JSONL object를 업로드한 뒤 성공을 반환한다. Job 종료 후 spool은 best-effort로 삭제한다. resume은 이전 spool을 재사용하지 않고 새 run object를 만든다.

추천 사유: S3는 append가 없고, UOW-005는 resume 시 새 run output을 만듭니다. DCinside와 같은 durable-before-checkpoint 계약을 계승합니다.

B) spool을 영구 볼륨에 보존하고 resume 때 기존 spool을 이어 쓴다.

C) spool 없이 게시글마다 별도 S3 object를 만든다.

X) 기타

[Answer]: A

### Question 8. Cookie And Proxy Secret Safety

Proxy와 cookie 관련 secret은 어떻게 보호할까요?

A) (권장) Proxy password, raw `.env`, cookie header, raw request/response header는 logs, failures, reports, MCP errors에 절대 남기지 않는다. 사용자 제공 cookie file은 지원하지 않고, 서버 임시 cookie는 `HttpClient` 메모리 안에서만 유지한다.

추천 사유: 기준 프로젝트와 같은 정책입니다. cookie 파일 입력 경로를 만들지 않는 편이 더 작고 안전하며, 임시 cookie 유출 방지만 검증하면 됩니다.

B) debug 모드에서는 cookie/header 내용을 출력할 수 있게 한다.

C) cookie와 proxy는 사용자가 넣은 값이므로 redaction 대상에서 제외한다.

X) 기타

[Answer]: A

### Question 9. MCP Dependency And Packaging

MCP server/tool 구현 의존성은 어떻게 둘까요?

A) (권장) MCP 관련 package는 `mcp` optional extra로 분리하고, 기본 scraper/runtime/container 설치에는 넣지 않는다. MCP adapter는 import side-effect 없이 tool 함수와 server entrypoint를 제공한다.

추천 사유: MCP는 모든 실행 환경에 필요한 기능이 아닙니다. DCinside와 같이 optional extra로 분리하면 컨테이너와 CLI 설치가 가벼워집니다.

B) MCP package를 기본 런타임 의존성으로 추가한다.

C) MCP server는 구현하지 않고 tool schema 문서만 만든다.

X) 기타

[Answer]: A

### Question 10. MCP Execution Safety

MCP tool 실행의 안전 경계는 어떻게 둘까요?

A) (권장) tool 호출은 one-shot으로 실행하고, 입력 validation 실패와 runtime 실패는 `ErrorMapper` 기반 JSON error로 반환한다. stack trace, proxy password, cookie, raw env, raw HTTP body/header/content는 반환하지 않는다.

추천 사유: Functional Design에서 background registry를 미루기로 했습니다. one-shot + safe error가 가장 작은 안전 경계입니다.

B) MCP 응답에 디버깅 편의를 위해 traceback을 포함한다.

C) MCP tool 오류는 모두 서버 exception으로 throw한다.

X) 기타

[Answer]: A

### Question 11. Result Quality And Polars Dependency

결과 품질 검토와 Polars 의존성은 어떻게 둘까요?

A) (권장) 기본 품질 테스트는 stdlib `json`으로 JSONL/report/failure fixture를 검증하고, Polars read check는 `analysis` 또는 `test-analysis` optional extra가 설치된 경우에만 실행한다. BEST 댓글 shape는 stdlib fixture 검사에 포함한다.

추천 사유: Polars는 분석/검토용입니다. FMKorea의 BEST 댓글 스키마는 런타임 의존성 없이 fixture로 검증할 수 있습니다.

B) Polars를 기본 런타임 의존성으로 추가하고 모든 품질 테스트를 Polars로 실행한다.

C) Polars 검증과 BEST 댓글 fixture 검증을 모두 제외한다.

X) 기타

[Answer]: A

### Question 12. Default Test Gate And Optional Smoke

UOW-008 기본 테스트와 optional smoke gate는 어떻게 나눌까요?

A) (권장) 기본 gate는 Docker/Garage/PostgreSQL/live FMKorea 없이 fake/mocked services, static fixtures, PBT로 실행한다. Docker, Garage, PostgreSQL, MCP server, live FMKorea smoke는 pytest marker와 env flag가 있을 때만 실행한다.

추천 사유: 기본 테스트는 빠르고 재현 가능해야 합니다. 외부 서비스 smoke는 별도 gate로 두는 편이 로컬/CI 안정성이 높습니다.

B) 기본 테스트에서 Docker compose로 모든 서비스를 항상 띄운다.

C) UOW-008은 자동 테스트 없이 수동 smoke만 진행한다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-008 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 UOW-008 NFR Design으로 넘어가지 않습니다.
