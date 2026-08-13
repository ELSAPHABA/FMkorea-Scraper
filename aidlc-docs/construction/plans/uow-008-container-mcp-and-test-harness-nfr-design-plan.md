# NFR Design 계획 - UOW-008 Container, MCP, And Test Harness

이 계획은 `UOW-008 Container, MCP, And Test Harness`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-008 Container, MCP, And Test Harness
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-001 Core Models And Config, UOW-002 HTTP Runtime Policy, UOW-003 Search And Link Collection, UOW-004 Post Detail And Content Parsing, UOW-005 Job Runner And Checkpoint, UOW-006 Output And Storage, UOW-007 CLI Adapter
- **Scope**: one-shot container entrypoint, `docker-entrypoint.sh`, `.dockerignore`, env validation, PostgreSQL checkpoint adapter, S3/Garage output adapter, MCP tool adapter, quality fixture harness, optional smoke hooks
- **Out Of Scope**: parser-failure retry execution engine, distributed scheduler, background MCP job registry, production Kubernetes manifests, CAPTCHA bypass, GUI/Web UI, scraper parser redesign

## NFR Design 작업 체크리스트

- [x] UOW-008 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-008-container-mcp-and-test-harness/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Adapter Module Layout

UOW-008 구현 파일은 어떻게 나눌까요?

A) (권장) `src/fmkorea_scraper/adapters/container.py`, `src/fmkorea_scraper/adapters/mcp.py`, `src/fmkorea_scraper/outputs/s3_output.py`, `src/fmkorea_scraper/outputs/postgres_checkpoint.py`, `tests/test_container_adapter.py`, `tests/test_mcp_adapter.py`, `tests/test_quality_harness.py` 정도로만 나눈다.

추천 사유: 컨테이너/MCP/storage adapter 경계가 다르므로 파일은 나누되, 한 기능 안에서 과도한 하위 패키지는 만들지 않습니다. DCinside 구조 계승에도 가장 가깝습니다.

B) `adapters/container/`, `adapters/mcp/`, `outputs/s3_output/`, `outputs/postgres/` 하위 패키지를 각각 만들고 세부 컴포넌트를 모두 분리한다.

C) `adapters/cli.py`에 컨테이너와 MCP도 같이 넣는다.

X) 기타

[Answer]: A

### Question 2. Container Runtime Assembly Pattern

컨테이너 runtime assembly는 어떤 패턴으로 둘까요?

A) (권장) `build_container_runtime(config, env_config)` 함수가 기존 `HttpClient`, collector/detail services, `S3OutputStore`, `PostgresCheckpointStore`, `JobRunner`를 조립한다. 별도 factory class는 만들지 않는다.

추천 사유: UOW-007과 같은 얇은 adapter 패턴입니다. 한 번 쓰는 factory class는 불필요하고, DCinside와 같은 구조를 유지할 수 있습니다.

B) `ContainerRuntimeFactory` 클래스를 만든다.

C) `main()` 함수 안에서 모든 객체를 직접 만든다.

X) 기타

[Answer]: A

### Question 3. Env Config Pattern

환경변수 mapping은 어떤 구조로 둘까요?

A) (권장) `ContainerEnvConfig.from_env(env: Mapping[str, str])` 같은 작은 dataclass/Pydantic-free helper를 두고, 필수값 누락은 `ValidationFailure`로 반환한다. secret 값은 `repr`/로그에 노출하지 않는다.

추천 사유: 환경변수는 adapter 입력입니다. UOW-001 도메인 모델에 컨테이너 전용 모델을 섞지 않고, 기준 구조처럼 명시적 helper로 충분합니다.

B) UOW-001 모델에 컨테이너 전용 EnvConfig Pydantic 모델을 추가한다.

C) `os.environ[...]` 접근을 사용하는 위치마다 직접 한다.

X) 기타

[Answer]: A

### Question 4. PostgreSQL Adapter Pattern

`PostgresCheckpointStore`는 어떤 구현 패턴으로 둘까요?

A) (권장) sync `psycopg` 연결을 사용하고, async port 메서드 안에서는 짧은 DB 작업을 `anyio.to_thread.run_sync()`로 감싼다. 테스트는 fake connection 또는 monkeypatch 가능한 connection factory로 검증한다.

추천 사유: 기존 port는 async지만 DB 작업은 짧습니다. asyncpg를 추가하지 않고 optional psycopg만 쓰는 NFR 결정과 맞습니다.

B) asyncpg 기반 완전 async adapter로 만든다.

C) DB adapter는 blocking sync 메서드를 그대로 async 함수 안에서 호출한다.

X) 기타

[Answer]: A

### Question 5. S3OutputStore Upload Pattern

`S3OutputStore`의 boto3 업로드는 어떤 방식으로 async port와 연결할까요?

A) (권장) 기존 `S3ObjectStore.put_bytes()` 또는 boto3 호출을 `anyio.to_thread.run_sync()`로 감싸 async port에서 block을 줄인다. local spool append는 작은 sync 파일 쓰기로 유지한다.

추천 사유: `aioboto3`를 추가하지 않으면서 event loop blocking을 줄일 수 있습니다. 기준 프로젝트의 단순 S3 경계와도 맞습니다.

B) boto3 호출을 async 함수 안에서 그대로 직접 호출한다.

C) S3 upload queue/background task를 만들어 비동기 fire-and-forget으로 처리한다.

X) 기타

[Answer]: A

### Question 6. Local Spool Cleanup Pattern

S3 spool cleanup은 어떻게 처리할까요?

A) (권장) `tempfile.TemporaryDirectory()` 또는 job/run별 temp dir을 context로 만들고, Job 종료 시 best-effort 삭제한다. 삭제 실패는 safe warning으로만 남긴다.

추천 사유: resume은 새 run object를 만들기로 했으므로 spool 장기 보존은 필요하지 않습니다.

B) spool 파일을 영구 output directory에 남긴다.

C) append마다 spool 파일을 삭제하고 다음 append 때 S3에서 다시 내려받는다.

X) 기타

[Answer]: A

### Question 7. MCP Tool Implementation Pattern

MCP tool 구현은 어떤 구조로 둘까요?

A) (권장) tool 함수는 `async def` wrapper로 두고, 입력 dict를 shared model/builder로 검증한 뒤 core API를 호출한다. MCP server binding은 얇은 등록 함수로 분리하고, tool 함수는 MCP runtime 없이도 단위 테스트 가능하게 한다.

추천 사유: MCP package가 없어도 core tool logic을 테스트할 수 있고, optional extra 경계를 지킬 수 있습니다.

B) MCP server 객체 안에 모든 tool logic을 직접 구현한다.

C) MCP tool은 shell로 CLI command를 실행한다.

X) 기타

[Answer]: A

### Question 8. Safe Error Payload Pattern

MCP/container safe error payload는 어떻게 만들까요?

A) (권장) 공통 `safe_error_payload(exc, stage=None)` helper가 `ErrorMapper.map()` 결과를 JSON dict로 변환한다. container는 이 dict를 로그로 출력하고, MCP는 response error로 반환한다.

추천 사유: 기존 ErrorMapper를 재사용하고 container/MCP의 redaction 정책을 하나로 맞출 수 있습니다.

B) container와 MCP가 각각 별도 error mapping을 구현한다.

C) 모든 오류를 문자열 하나로만 반환한다.

X) 기타

[Answer]: A

### Question 9. Quality Harness Pattern

품질 하네스는 어디에 둘까요?

A) (권장) 런타임 코드가 아니라 `tests/quality/` 또는 `tests/test_quality_harness.py` 안에 fixture validator helper를 둔다. 필요 시 `tests/fixtures/quality/`에 작은 JSONL/report fixture를 둔다.

추천 사유: 품질 검증은 테스트 하네스입니다. 런타임 package에 분석용 코드를 넣을 필요가 없습니다.

B) `src/fmkorea_scraper/quality/` 런타임 패키지로 만든다.

C) 품질 하네스는 문서만 남기고 테스트 코드는 만들지 않는다.

X) 기타

[Answer]: A

### Question 10. Optional Smoke Marker Pattern

optional smoke test는 어떻게 스킵/실행하게 할까요?

A) (권장) pytest marker를 `docker`, `garage`, `postgres`, `mcp`, `live`로 나누고, 각 테스트는 대응 env flag가 없으면 `pytest.skip()`한다. 기본 `pytest`에서는 외부 서비스가 없어도 통과해야 한다.

추천 사유: smoke 원인을 분리해 실행할 수 있고, 기본 gate가 안정적입니다.

B) `live` marker 하나로 모든 optional smoke를 묶는다.

C) smoke 테스트 파일은 만들되 skip 조건 없이 실패하게 둔다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-008 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-008 NFR Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q10 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Key Implementation Note**: UOW-008 keeps the baseline flat adapter/storage layout, thin container runtime builder, optional MCP boundary, PostgreSQL/S3 adapter isolation, and test-only quality harness.
