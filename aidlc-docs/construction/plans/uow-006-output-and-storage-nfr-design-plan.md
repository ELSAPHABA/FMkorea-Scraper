# NFR Design 계획 - UOW-006 Output And Storage

이 계획은 `UOW-006 Output And Storage`의 NFR 요구사항을 구현 패턴과 논리 컴포넌트로 구체화하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-006 Output And Storage
- **NFR Requirements**: 승인됨
- **Depends On**: UOW-001 Core Models And Config
- **Scope**: append-only JSONL, atomic checkpoint/report writes, path sanitization, safe failure redaction, local media storage, S3-compatible object key/upload boundary, S3 JSONL spool, optional Garage smoke tests, optional Polars smoke tests
- **Baseline Inheritance**: `A)` 선택지는 기준 스크래퍼의 output/storage 설계를 최대한 계승하되, FMKorea source JSONL과 optional `s3`/`analysis` extra 정책을 반영하는 권장안으로 작성한다.
- **Out Of Scope**: worker queue lifecycle, retry scheduling, HTTP media download, PostgreSQL checkpoint adapter, CLI prompt UX, container/MCP hosting, AWS CDK

## NFR Design 작업 체크리스트

- [x] UOW-006 NFR Requirements 승인 확인
- [x] NFR Requirements 산출물 확인
- [x] NFR Design 질문 생성
- [x] NFR Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-006-output-and-storage/nfr-design/nfr-design-patterns.md` 생성
- [x] `aidlc-docs/construction/uow-006-output-and-storage/nfr-design/logical-components.md` 생성
- [x] Security/Resiliency/PBT compliance 확인

## NFR Design Questions

### Question 1. Output Package Layout

저장 구현 컴포넌트는 어떤 모듈 구조로 나눌까요?

A) (권장) `src/fmkorea_scraper/outputs/` 아래에 `layout.py`, `jsonl.py`, `local.py`, `s3.py`, `redaction.py`, `checkpoint.py`, `factory.py`를 둔다. local/S3/checkpoint 구현은 분리하되 공통 path/key 계산은 `layout.py`가 담당한다.

추천 사유: 기준 스크래퍼의 outputs 패키지 경계를 계승하면서, UOW-006의 책임별 테스트 단위를 충분히 작게 유지합니다.

B) 하나의 `storage.py` 파일에 output, media, failure, checkpoint, S3 로직을 모두 넣는다.

C) output, media, failure, checkpoint, S3, Polars, locking마다 별도 package와 abstract hierarchy를 만든다.

X) 기타

[Answer]: A

### Question 2. JSONL Writer Pattern

JSONL writer는 어떤 방식으로 구현할까요?

A) (권장) 작은 `JsonlWriter`가 `model_dump(mode="json")`, stdlib `json.dumps(ensure_ascii=False)`, append, newline, flush를 처리한다. `fsync`는 writer 옵션으로만 둔다.

추천 사유: JSONL 라이브러리 없이 충분합니다. 내구성 옵션도 한 곳에서만 다루면 됩니다.

B) 외부 JSONL 전용 라이브러리를 추가한다.

C) 각 저장 메서드에서 직접 `json.dumps`와 파일 append를 반복 작성한다.

X) 기타

[Answer]: A

### Question 3. Path Sanitization Pattern

path segment sanitization은 어떤 패턴으로 둘까요?

A) (권장) `sanitize_path_segment(value, fallback)` 순수 함수가 허용 문자 `[A-Za-z0-9._-]`만 보존하고 나머지는 `_`로 치환한다. 빈 결과는 fallback을 쓰고, 최종 local path는 base directory 하위인지 검증한다.

추천 사유: 단순하고 테스트하기 쉽습니다. OS별 금지 문자를 모두 직접 관리하는 것보다 allow-list가 안전합니다.

B) `pathlib`이 처리하도록 입력값을 그대로 사용한다.

C) URL encoding으로 파일명을 만든다.

X) 기타

[Answer]: A

### Question 4. OutputRunLayout Pattern

run 경로와 object key 계산은 어떤 구조로 둘까요?

A) (권장) `OutputRunLayout` value object가 `job_id`, `run_id`, base path/prefix를 받아 posts/failures/report/media 상대 경로와 로컬 절대 경로, S3 object key를 모두 생성한다.

추천 사유: local과 S3가 같은 상대 layout을 공유해야 합니다. 계산을 한 곳에 두면 checkpoint와 storage 테스트가 단순해집니다.

B) local store와 S3 store가 각각 별도 방식으로 path/key를 직접 계산한다.

C) caller가 모든 경로와 object key를 문자열로 직접 넘긴다.

X) 기타

[Answer]: A

### Question 5. Failure Redaction Pattern

safe failure context는 어디에서 만들까요?

A) (권장) `sanitize_failure_context`가 allow-list 필드만 받아 `FailureRecord.details` 또는 safe dict로 병합한다. unknown field는 기본 drop한다.

추천 사유: credential을 빼려면 call site마다 dict를 만들지 않는 편이 안전합니다. 함수 하나면 충분하고 class hierarchy는 필요 없습니다.

B) 각 실패 기록 call site가 직접 민감 필드를 제거한다.

C) 실패 원본 context를 모두 저장하고 나중에 로그에서만 숨긴다.

X) 기타

[Answer]: A

### Question 6. Atomic File Writer Pattern

`Checkpoint.json`과 `report.json` atomic replace는 어떤 컴포넌트가 담당할까요?

A) (권장) `AtomicJsonWriter` 같은 작은 helper가 같은 디렉터리에 temp file을 만들고, JSON write/flush 후 `os.replace`를 수행한다. JSONL append에는 사용하지 않는다.

추천 사유: 원자적 단일 문서 쓰기는 중복되므로 helper 하나면 충분합니다. JSONL 전체 rewrite는 피합니다.

B) checkpoint store와 report writer가 각각 temp/replace 코드를 직접 작성한다.

C) atomic replace 없이 일반 overwrite만 사용한다.

X) 기타

[Answer]: A

### Question 7. S3 Store Loading Pattern

S3-compatible 저장소 의존성은 코드에서 어떻게 로드할까요?

A) (권장) `S3ObjectStore` 안에서 `boto3`를 lazy import하고, 설치되지 않은 상태에서 S3 mode를 쓰면 명확한 설정 오류를 낸다. local mode import는 S3 의존성이 없어도 성공해야 한다.

추천 사유: 기본 로컬 사용자를 가볍게 유지하고, optional extra 경계를 테스트할 수 있습니다.

B) package import 시점에 항상 S3 client를 import한다.

C) 직접 HTTP 서명 구현으로 외부 S3 client를 쓰지 않는다.

X) 기타

[Answer]: A

### Question 8. S3 JSONL Spool Pattern

S3-compatible JSONL spool은 어떤 컴포넌트로 둘까요?

A) (권장) `S3JsonlSpool` 또는 `SpoolingJsonlUploader`가 local temp/spool file에 append하고, 성공 후 같은 object key로 `put_object`를 호출한다. fake S3 client로 same-key upload를 테스트한다.

추천 사유: S3 native append가 없으므로 간단한 spool helper가 필요합니다. 이 helper를 분리하면 local JSONL writer와 S3 upload 책임이 섞이지 않습니다.

B) S3 store가 모든 JSONL 문자열을 메모리에 보관했다가 매번 업로드한다.

C) 게시글마다 별도 object를 쓰고 report에서만 묶는다.

X) 기타

[Answer]: A

### Question 9. Local Checkpoint Document Pattern

`Checkpoint.json` 문서 처리는 어떤 컴포넌트가 담당할까요?

A) (권장) `LocalCheckpointStore`가 process-local lock, `LocalCheckpointDocument` load/validate, job_id별 replace, `load_latest()` 정렬을 담당한다.

추천 사유: checkpoint 파일은 저장소 내부 포맷입니다. JobRunner는 포트만 호출하고 파일 구조를 알 필요가 없습니다.

B) JobRunner가 checkpoint map을 만들고 storage는 파일 write만 한다.

C) 매 checkpoint를 별도 파일로 저장한다.

X) 기타

[Answer]: A

### Question 10. Polars Smoke Test Pattern

Polars source JSONL smoke test는 어떻게 구성할까요?

A) (권장) `tests/test_outputs_polars_smoke.py` 같은 optional test가 Polars import 가능 여부를 확인하고, 없으면 skip한다. 작은 `PostResult` fixture를 JSONL로 쓴 뒤 `read_ndjson`, comments explode, content/media projection만 확인한다.

추천 사유: 원본 JSONL의 분석 가능성만 확인하면 됩니다. production 정규화 pipeline을 지금 만들 필요는 없습니다.

B) Polars 정규화 모듈을 UOW-006 application code로 만든다.

C) Polars 관련 테스트를 만들지 않는다.

X) 기타

[Answer]: A

### Question 11. Test Organization

UOW-006 테스트 파일은 어떻게 구성할까요?

A) (권장) 예제 테스트는 `tests/test_outputs_storage.py`, PBT는 `tests/test_outputs_properties.py`, strategy는 `tests/strategies/outputs.py`에 둔다. S3/Garage smoke와 Polars smoke는 별도 env/optional-gated test로 둔다.

추천 사유: 기존 UOW-003/UOW-004 테스트 구조와 맞고, 기본 테스트와 외부/optional 테스트를 분리할 수 있습니다.

B) 모든 테스트를 하나의 큰 `tests/test_storage.py`에 둔다.

C) PBT와 smoke를 만들지 않고 예제 테스트만 둔다.

X) 기타

[Answer]: A

### Question 12. Garage Smoke Boundary

선택적 Garage/S3 smoke test는 어떤 조건으로 실행할까요?

A) (권장) `FMKOREA_S3_SMOKE_ENABLED=true`일 때만 실행하고, endpoint/bucket/access key/secret env가 모두 있을 때 작은 object put/get/delete 수준만 검증한다. 기본 pytest에서는 skip한다.

추천 사유: 외부 서비스 의존성을 기본 gate에 넣지 않으면서 S3 호환성 확인 경로는 남깁니다. env prefix는 프로젝트명에 맞춰 FMKOREA를 사용합니다.

B) 기본 pytest에서 항상 Garage smoke를 실행한다.

C) S3/Garage smoke test는 만들지 않는다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-006 NFR Design 산출물 2개를 생성합니다.
4. 산출물 생성 후 사용자 승인 전에는 Infrastructure Design 또는 Code Generation으로 넘어가지 않습니다.

## NFR Design Review Gate

검토 대상:

- `aidlc-docs/construction/uow-006-output-and-storage/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/uow-006-output-and-storage/nfr-design/logical-components.md`

승인 후 다음 단계는 `UOW-006 Infrastructure Design`이다.

## Answer Analysis

- **Answers Confirmed At**: 2026-08-12T13:32:07Z
- **Selected Options**: Q1-Q12 were A.
- **Inheritance Note**: All selected A options preserve the baseline scraper output/storage design while using FMKorea-specific package names, env prefix, source JSONL shape, S3 spool, and optional Polars smoke boundary.
- **Ambiguity Review**: No vague answers, missing answers, or conflicts found.
- **Compliance Note**: The design keeps Security/Resiliency/PBT requirements mapped to concrete patterns without adding PostgreSQL, CLI, container, MCP, or CDK scope to UOW-006.
- **Follow-up Questions**: Not required.
