# NFR Design 계획 - UOW-001 Core Models And Config

이 계획은 `UOW-001 Core Models And Config`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-001 Core Models And Config
- **NFR Requirements**: 승인됨
- **Scope**: validation pattern, metadata bounds, error redaction, schema compatibility, test strategy, logical components
- **Out Of Scope**: concrete HTTP client, parser selector fallback, storage adapter, container infrastructure, MCP server registration

## NFR Design 작업 체크리스트

- [x] UOW-001 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 불필요 확인
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-001-core-models-and-config/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Validation Component Pattern

Pydantic validation 로직은 어디에 배치할까요?

A) (권장) 가능한 제약은 Pydantic field/model validators에 두고, adapter 입력 조합 검증은 `JobConfigValidator` facade에 둔다.

추천 사유: 단일 모델 내부 불변식은 모델에 가까이 두고, 여러 모델이나 실행 모드 조합 검증은 facade에 두면 책임이 작고 테스트 범위가 명확합니다.

B) 모든 validation을 `JobConfigValidator`에 모아 모델은 구조만 정의한다.

C) 모든 validation을 Pydantic 모델 validator에 넣고 별도 validator facade를 두지 않는다.

[Answer]: A

### Question 2. Metadata Bounds Pattern

`metadata` depth와 byte size 제한은 어떤 컴포넌트로 처리할까요?

A) (권장) 공통 `MetadataValidator` helper를 두고 모든 모델의 `metadata` validator에서 재사용한다.

추천 사유: metadata 정책은 모든 모델에 반복됩니다. 공통 helper로 두면 제한값 변경과 테스트가 단순합니다.

B) 각 모델마다 metadata validation을 직접 구현한다.

C) metadata는 문서에만 제한을 기록하고 코드에서는 검사하지 않는다.

[Answer]: A

### Question 3. Error Redaction Pattern

typed exception을 `ErrorResult`로 바꿀 때 redaction은 어떻게 설계할까요?

A) (권장) `ErrorMapper`와 `SecretRedactor`를 분리한다. `ErrorMapper`는 code/message/details를 만들고, `SecretRedactor`가 allowlist 기반으로 details를 정리한다.

추천 사유: 오류 mapping과 secret 제거는 책임이 다릅니다. allowlist redaction을 분리해야 CLI/MCP/container adapter가 같은 안전 정책을 재사용할 수 있습니다.

B) 각 adapter가 직접 exception을 잡아 redaction까지 처리한다.

C) exception class가 직접 `to_error_result()`를 구현하고 redaction도 내부에서 처리한다.

[Answer]: A

### Question 4. Schema Compatibility Checker

schema version 변경과 호환성 검사는 어떤 수준으로 설계할까요?

A) (권장) code generation 단계에서 `schema_snapshot` fixture와 compatibility check helper를 만든다.

추천 사유: 지금부터 복잡한 migration framework는 과합니다. 하지만 persisted schema가 깨지는지는 snapshot으로 잡아야 합니다.

B) 별도 migration registry와 schema diff tool을 1차 구현에 포함한다.

C) 문서 규칙만 두고 자동 검사는 만들지 않는다.

[Answer]: A

### Question 5. PBT Generator Organization

Hypothesis generator는 어디에 둘까요?

A) (권장) `tests/strategies/`에 domain-specific strategy를 두고 UOW-001 모델 테스트에서 재사용한다.

추천 사유: generator가 테스트 파일마다 흩어지면 constraints가 달라집니다. 재사용 가능한 strategy가 PBT-07에 맞습니다.

B) 각 테스트 파일 안에 필요한 generator를 인라인으로 둔다.

C) production code 안에 generator를 둔다.

[Answer]: A

### Question 6. Performance Guard Pattern

모델 validation/serialization 성능은 어떤 방식으로 지키면 좋을까요?

A) (권장) 1차에서는 benchmark를 CI gate로 두지 않고, 대표 fixture 기반 smoke benchmark를 선택 실행으로 둔다.

추천 사유: 아직 실제 게시글 크기와 JobRunner 통합이 확정되지 않았습니다. 임의 기준으로 CI를 깨는 것보다, 측정 경로만 마련하는 편이 낫습니다.

B) UOW-001부터 validation/serialization benchmark를 CI 필수 gate로 둔다.

C) 성능 측정 코드는 만들지 않는다.

[Answer]: A

### Question 7. Port Protocol Shape

port protocol은 어느 정도로 세분화할까요?

A) (권장) `HttpPort`, `OutputStorePort`, `MediaStorePort`, `FailureStorePort`, `CheckpointStorePort`, `ClockPort`, `LoggerPort`만 1차 port로 둔다.

추천 사유: 필요한 외부 의존성 경계는 충분히 포함합니다. request type이나 storage 구현별로 port를 더 쪼개면 구현량만 늘어납니다.

B) request type별로 `BoardHttpPort`, `CommentHttpPort`, `MediaHttpPort`처럼 세분화한다.

C) storage도 local/S3/PostgreSQL별 port를 별도로 둔다.

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-001 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## Answer Analysis

- Q1-Q7은 모두 A로 확정되었다.
- 답변 간 충돌은 없다.
- follow-up 질문은 필요하지 않다.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-001-core-models-and-config/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-001-core-models-and-config/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-001 Infrastructure Design`이다.
