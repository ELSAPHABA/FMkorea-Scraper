# 유저 스토리 생성 계획

이 계획은 `aidlc-docs/inception/requirements/requirements.md`의 요구사항을 바탕으로 FMKorea-Scraper의 페르소나와 유저 스토리를 생성하는 방법을 정의합니다.

DCinside-Scraper의 스토리 구조는 기준선으로 사용하되, FMKorea 전용 요구사항과 예외 결정은 새 스토리에 반영합니다.

스토리 생성을 시작하기 전에 아래 모든 `[Answer]:` 항목을 채워 주세요.

## 계획 질문

## Question 1
유저 스토리를 어떤 방식으로 구성할까요?

A) (권장) 사용자 여정 기반: CLI 작업 설정, 검색/링크 수집, 게시글 상세 수집, 댓글/미디어 수집, 저장/검증, 중단/재개, 외부 통합 흐름

권장 사유: 실제 사용 흐름과 DCinside의 기존 스토리 구조를 가장 잘 계승하면서 FMKorea 차이를 자연스럽게 반영할 수 있습니다.

B) 기능 기반: 검색, 게시글 상세, 댓글, 미디어, 저장, checkpoint, Proxy/User-Agent, cookie, worker, MCP, CDK

C) 페르소나 기반: CLI 사용자, 라이브러리 개발자, 워커 운영자, MCP 클라이언트, 유지보수자, 데이터 검토자별로 구성

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
어떤 페르소나 구성을 사용할까요?

A) (권장) 전체 구성: CLI 사용자, Python 라이브러리 개발자, 워커 컨테이너 운영자, MCP 클라이언트, 유지보수자, Polars 데이터 검토자

권장 사유: 요구사항의 모든 실행 형태와 JSONL/Polars 검증 흐름을 빠짐없이 커버합니다.

B) 최소 구성: CLI 사용자, Python 라이브러리 개발자, 워커 컨테이너 운영자

C) 운영 중심 구성: 워커 운영자, 유지보수자, 데이터 검토자를 중심으로 작성

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
스토리의 세분화 수준은 어떻게 할까요?

A) (권장) 에픽 아래 중간 크기 스토리. 각 스토리는 하나의 사용자 가치와 명확한 acceptance criteria를 가진다

권장 사유: UOW 설계로 연결하기 충분히 구체적이면서도 구현 task 수준으로 과하게 쪼개지 않습니다.

B) 큰 에픽 중심. 각 에픽에 주요 인수조건만 포함

C) 구현 작업으로 바로 나눌 수 있을 정도의 세부 스토리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
인수조건 형식은 어떻게 할까요?

A) (권장) 기본은 체크리스트로 작성하고, 위험한 워크플로에만 Given/When/Then을 추가

권장 사유: 문서는 읽기 쉽게 유지하면서 checkpoint, CAPTCHA, 중복 제거, 재처리 같은 위험 흐름은 명확히 검증할 수 있습니다.

B) 모든 스토리를 Given/When/Then 형식으로 작성

C) 체크리스트 형식만 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
FMKorea 원본 JSON에서 `is_repost`와 `repost`를 제외한 결정을 스토리에 어떻게 표현할까요?

A) (권장) FMKorea 원본 JSON 스토리에는 제외 조건을 명시하고, 공통 정규화 스토리에서만 기본값 합성을 언급한다

권장 사유: Q8 결정과 공통 커뮤니티 분석 스키마 호환성을 동시에 보존합니다.

B) 스토리에서는 언급하지 않고 데이터 요구사항에만 남긴다

C) 공통 스키마 호환을 위해 스토리에서는 `is_repost=false`, `repost=null` 저장을 요구한다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
테스트와 검증 메모는 유저 스토리에 어떻게 반영할까요?

A) (권장) 각 주요 스토리에 fixture test, Hypothesis PBT, 선택적 live smoke, Polars read 검증 메모를 필요한 만큼 붙인다

권장 사유: 이 프로젝트는 파서와 JSONL shape가 핵심이라, 스토리 단계에서 검증 방향을 남겨야 이후 UOW 테스트 설계가 흔들리지 않습니다.

B) acceptance criteria에서 테스트 가능성만 언급한다

C) 테스트 전용 스토리를 별도로 만든다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## 스토리 작성 체크리스트

- [x] 계획 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] `aidlc-docs/inception/user-stories/personas.md` 생성
- [x] `aidlc-docs/inception/user-stories/stories.md` 생성
- [x] 스토리가 INVEST 기준을 따르는지 확인
- [x] 모든 스토리에 acceptance criteria 포함
- [x] 페르소나와 관련 유저 스토리 연결
- [x] Security, Resiliency, PBT 관련 인수조건 포함
- [x] FMKorea-specific 예외인 `is_repost`/`repost` 제외와 사용자 제공 cookie 파일 미지원 반영
- [x] Polars 가공 가능한 JSONL/content block 검증 흐름 반영
- [x] 완료한 항목은 즉시 체크리스트에 반영

## 답변 확정 요약

- 스토리 구성 방식: 사용자 여정 기반
- 페르소나 구성: CLI 사용자, Python 라이브러리 개발자, 워커 컨테이너 운영자, MCP 클라이언트, 유지보수자, Polars 데이터 검토자
- 스토리 세분화 수준: 에픽 아래 중간 크기 스토리
- 인수조건 형식: 기본 체크리스트 + 위험한 워크플로는 Given/When/Then 추가
- `is_repost`/`repost` 처리: FMKorea 원본 JSON 스토리에는 제외 조건을 명시하고, 공통 정규화 스토리에서만 기본값 합성을 언급
- 테스트 반영: fixture test, Hypothesis PBT, 선택적 live smoke, Polars read 검증 메모 포함
- 모호성/충돌 검토 결과: 추가 clarification 불필요

## 스토리 분해 방식 후보

### 사용자 여정 기반

작업 설정, 검색, 게시글 상세 수집, 저장, 복구처럼 사용자의 실제 흐름을 따라 스토리를 구성합니다.

### 기능 기반

스크래퍼 기능 단위로 스토리를 구성합니다.

### 페르소나 기반

사용자 유형별로 스토리를 구성합니다.

### 도메인 기반

검색, 게시글 상세, 댓글, 미디어, 저장, 운영 같은 도메인 개념으로 스토리를 구성합니다.

### 에픽 기반

상위 에픽 아래에 하위 스토리를 구성합니다.

## 필수 산출물

- `aidlc-docs/inception/user-stories/personas.md`
- `aidlc-docs/inception/user-stories/stories.md`

## 확장 규칙 반영 메모

- Security Baseline: 입력 검증, 민감정보 로그 금지, 평문 Proxy `.env` 경고, 임시 cookie 메모리 제한을 관련 acceptance criteria에 포함합니다.
- Resiliency Baseline: 중단점 저장/복구, 실패 처리, 로컬/컨테이너/AWS 선택 운영 범위를 관련 acceptance criteria에 포함합니다.
- Property-Based Testing: URL/query, parser, 직렬화, 중복 제거, checkpoint, content block shape의 테스트 가능성을 관련 검증 메모에 반영합니다.
