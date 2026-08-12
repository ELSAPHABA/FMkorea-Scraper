# NFR Requirements 계획 - UOW-001 Core Models And Config

이 계획은 `UOW-001 Core Models And Config`의 비기능 요구사항과 기술 선택을 확정하기 위한 질문지입니다. 답변이 확정되기 전에는 NFR Requirements 산출물을 생성하지 않습니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-001 Core Models And Config
- **Functional Design**: 승인됨
- **Scope**: Pydantic v2 모델, strict validation, schema versioning, typed errors, port protocols
- **Relevant Extensions**: Security Baseline, Resiliency Baseline, Property-Based Testing
- **Out Of Scope**: HTTP runtime, parser selectors, storage implementation, container infrastructure

## NFR Requirements 작업 체크리스트

- [x] UOW-001 Functional Design 승인 확인
- [x] Security, Resiliency, PBT extension 적용 여부 확인
- [x] NFR 질문 생성
- [x] NFR 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 불필요 확인
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/nfr-requirements/nfr-requirements.md` 생성
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/nfr-requirements/tech-stack-decisions.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Questions

### Question 1. Dependency Pinning

Pydantic v2와 테스트 관련 dependency는 어떻게 pinning할까요?

A) (권장) `pyproject.toml`에는 compatible range를 두고 lock file로 exact version을 고정한다.

추천 사유: 라이브러리 개발과 앱 실행 양쪽에 맞습니다. 패키지 metadata는 지나치게 좁히지 않고, 재현 가능한 실행은 lock file이 담당합니다.

B) `pyproject.toml`에서 모든 dependency를 exact version으로 고정한다.

C) 1차 구현에서는 버전 범위를 느슨하게 두고 lock file을 만들지 않는다.

[Answer]: A

### Question 2. Input Size Bounds

모델 validation의 문자열/배열 크기 제한은 어느 수준으로 둘까요?

A) (권장) 모든 public input/config에는 명시적 max length/count를 두고, parser result 내부 모델에는 합리적인 상한만 둔다.

추천 사유: CLI/MCP/container 입력은 보안 경계입니다. 결과 모델은 실제 게시글이 길 수 있으므로 너무 작은 제한은 데이터 손실을 만들 수 있습니다.

B) 모든 문자열/배열에 엄격한 작은 상한을 둔다.

C) 길이 제한은 구현하지 않고 타입과 형식만 검증한다.

[Answer]: A

### Question 3. Metadata Size Policy

확장 필드 `metadata`는 어느 정도까지 허용할까요?

A) (권장) `metadata`는 JSON-serializable primitive/list/dict만 허용하고, depth와 serialized byte size에 상한을 둔다.

추천 사유: `metadata`가 우회 확장 통로가 되면 스키마 안정성과 로그 안전성이 깨질 수 있습니다. 크기와 depth 제한은 runaway payload를 막습니다.

B) JSON-serializable이면 크기 제한 없이 허용한다.

C) 1차 구현에서는 `metadata`를 빈 dict로만 허용한다.

[Answer]: A

### Question 4. Error Redaction

`ErrorResult.details`에는 어떤 정보를 허용할까요?

A) (권장) error code, field path, safe reason, retryable 여부만 허용하고 원본 입력값은 기본적으로 포함하지 않는다.

추천 사유: Proxy password, cookie, URL query, 환경변수 값이 섞일 가능성을 줄입니다. 디버깅에 필요한 위치 정보는 field path로 충분합니다.

B) 안전하다고 판단되는 입력값 일부는 details에 포함한다.

C) 개발 편의를 위해 raw validation error 전체를 포함한다.

[Answer]: A

### Question 5. Schema Compatibility Policy

`fmkorea.post.v1`, `fmkorea.checkpoint.v1`, `fmkorea.failure.v1`, `fmkorea.job_report.v1`의 변경 정책은 어떻게 둘까요?

A) (권장) 같은 major version에서는 필드 삭제/타입 변경 금지, nullable 필드 추가만 허용한다.

추천 사유: JSONL, checkpoint, failure, report는 나중에 Polars/RAG/normalizer에서 재사용됩니다. breaking change는 version bump로 분리해야 합니다.

B) 1차 구현 중에는 자유롭게 breaking change를 허용한다.

C) 모든 변경을 새 schema version으로 처리한다.

[Answer]: A

### Question 6. PBT Scope

UOW-001에서 Property-Based Testing은 어디까지 필수로 둘까요?

A) (권장) JSON round trip, JobConfig discriminator validation, range/realtime invariant, content order invariant, BEST comment invariant, checkpoint status/reason invariant를 필수 PBT로 둔다.

추천 사유: 이 unit은 parser보다 모델 불변 조건이 핵심입니다. PBT가 가장 효과적인 부분은 직렬화와 validation invariant입니다.

B) JSON round trip만 PBT로 두고 나머지는 example test로 검증한다.

C) 모든 Pydantic model에 대해 자동 생성 기반 PBT를 적용한다.

[Answer]: A

### Question 7. Performance Target

모델 validation/serialization 성능 목표는 어떻게 둘까요?

A) (권장) 단일 `PostResult` validation/serialization은 일반 게시글 fixture 기준으로 병목이 아니어야 하며, 정확한 ms SLA는 UOW-004/UOW-005 통합 후 측정한다.

추천 사유: 이 unit 단독에서 성능 숫자를 정하면 임의값이 됩니다. 모델은 간결하게 유지하고, 실제 병목은 게시글/댓글 파싱과 저장 통합에서 측정하는 편이 정확합니다.

B) 지금부터 단일 모델 validation 10ms 이하 같은 수치 목표를 둔다.

C) 성능 요구사항은 전혀 두지 않는다.

[Answer]: A

### Question 8. Maintainability Contract

모델 문서화와 public API 안정성은 어떻게 관리할까요?

A) (권장) public model과 enum은 docstring/markdown contract를 유지하고, 변경 시 schema version과 migration note를 함께 갱신한다.

추천 사유: CLI, container, MCP, Polars/RAG 가공이 모두 같은 모델에 의존합니다. 변경 기록 없이 모델이 바뀌면 downstream이 깨집니다.

B) 코드 타입 힌트만 source of truth로 둔다.

C) markdown 문서만 source of truth로 두고 코드 문서화는 최소화한다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-001 NFR Requirements 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 NFR Design으로 넘어가지 않습니다.

## Answer Analysis

- Q1-Q8은 모두 A로 확정되었다.
- 답변 간 충돌은 없다.
- follow-up 질문은 필요하지 않다.

## NFR Requirements Review Gate

검토 대상:

- `aidlc-docs/construction/uow-001-core-models-and-config/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/uow-001-core-models-and-config/nfr-requirements/tech-stack-decisions.md`

승인 후 다음 단계는 `UOW-001 NFR Design`이다.
