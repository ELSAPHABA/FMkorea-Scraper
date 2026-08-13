# Infrastructure Design 계획 - UOW-007 CLI Adapter

이 계획은 `UOW-007 CLI Adapter`의 논리 CLI 컴포넌트를 실제 로컬 실행/검증 인프라 접점에 어떻게 매핑할지 확정하기 위한 질문지입니다.

답변 방법: 모든 `[Answer]:` 항목을 채워 주세요. 선택지는 하나를 고르거나, `X)`로 구체적인 방식을 적어도 됩니다.

## Unit Context

- **Unit**: UOW-007 CLI Adapter
- **Functional Design**: 승인됨
- **NFR Requirements**: 승인됨
- **NFR Design**: 승인됨
- **Scope**: local terminal execution, package console script, `python -m` execution, virtualenv/editable install behavior, local output/config file boundaries, Ctrl+C runtime boundary, default adapter tests
- **Likely Infrastructure Scope**: standalone service 없음, local Python environment와 filesystem 접점만 해당
- **Out Of Scope**: Docker worker entrypoint, MCP server hosting, Garage/PostgreSQL provisioning, distributed queue, GUI/Web UI, external terminal UI framework, AWS CDK

## Infrastructure Design 작업 체크리스트

- [x] UOW-007 Functional Design 승인 확인
- [x] UOW-007 NFR Design 승인 확인
- [x] Functional/NFR 산출물 확인
- [x] logical components의 인프라 필요 여부 분석
- [x] Infrastructure Design 질문 생성
- [x] Infrastructure Design 질문 답변 완료 확인
- [x] 답변의 모호함 또는 충돌 여부 분석
- [x] follow-up 질문 필요 여부 확인
- [x] `aidlc-docs/construction/uow-007-cli-adapter/infrastructure-design/infrastructure-design.md` 생성
- [x] `aidlc-docs/construction/uow-007-cli-adapter/infrastructure-design/deployment-architecture.md` 생성
- [x] shared infrastructure 산출물 필요 여부 확인

## Infrastructure Design Questions

### Question 1. Deployment Environment

UOW-007 자체를 배포 가능한 런타임으로 볼까요?

A) (권장) 아니요. UOW-007은 import 가능한 package CLI adapter이며, 독립 서비스/컨테이너 배포는 N/A로 문서화한다. 실제 worker container와 MCP 배포는 UOW-008에서 다룬다.

추천 사유: 이번 unit은 로컬 터미널 어댑터입니다. 서버/컨테이너 인프라를 지금 만들면 범위를 넘습니다.

B) 로컬 CLI 실행 환경만 Infrastructure Design에 포함한다.

C) Docker image와 MCP server 배포까지 UOW-007에서 확정한다.

X) 기타

[Answer]: A

### Question 2. Official Local Entrypoints

로컬 실행 진입점은 어떻게 문서화할까요?

A) (권장) `python -m fmkorea_scraper.adapters.cli ...`와 console script `fmkorea-scraper ...`를 공식 지원한다. 두 진입점은 같은 `fmkorea_scraper.adapters.cli.main`을 호출해야 한다. 루트 `main.py`는 만들지 않는다.

추천 사유: UOW-007 NFR Design의 Q11 A 결정을 그대로 반영하고, 실행 로직 중복을 막을 수 있습니다.

B) console script만 공식 지원한다.

C) root `python main.py`만 공식 지원한다.

X) 기타

[Answer]: A

### Question 3. Virtualenv And PATH Boundary

console script 실행 환경은 어떻게 안내할까요?

A) (권장) 개발/로컬 실행은 가상환경 활성화 후 `pip install -e .`를 기준으로 한다. console script는 가상환경 `Scripts/` 또는 `bin/`에 생성되며, Windows 시스템 환경변수 수동 편집은 필수로 하지 않는다.

추천 사유: Windows 환경변수 혼동을 줄이고, 전역 설치 오염을 피합니다.

B) Windows 시스템 PATH에 직접 추가하는 방식을 기본으로 문서화한다.

C) console script는 문서화하지 않는다.

X) 기타

[Answer]: A

### Question 4. Local Execution Directory

CLI의 실행 기준 디렉터리는 어떻게 정할까요?

A) (권장) 기본 실행 기준은 현재 작업 디렉터리(`Path.cwd()`)로 둔다. `--output-path`가 있으면 수집 output base만 바꾸고, `user-agents.txt`와 `.env` 기본 위치는 현재 작업 디렉터리를 따른다.

추천 사유: Python 패키지 설치 위치와 사용자의 작업 위치를 분리할 수 있습니다.

B) 항상 패키지 설치 디렉터리를 기준으로 파일을 읽고 쓴다.

C) 항상 프로젝트 루트를 기준으로 한다.

X) 기타

[Answer]: A

### Question 5. Generated Local Files

CLI가 생성/수정할 수 있는 로컬 파일 경계는 어떻게 둘까요?

A) (권장) UOW-007은 현재 작업 디렉터리의 `.env`, `user-agents.txt`만 직접 생성/수정한다. 수집 결과, `outputs/`, `Checkpoint.json`, media는 UOW-006 store가 생성한다.

추천 사유: CLI adapter가 저장소 레이아웃을 다시 구현하지 않게 됩니다.

B) CLI가 `outputs/`와 `Checkpoint.json`까지 직접 만든다.

C) CLI는 어떤 파일도 만들 수 없다.

X) 기타

[Answer]: A

### Question 6. Runtime Process Boundary

CLI 실행 프로세스의 lifecycle은 어떻게 둘까요?

A) (권장) one-shot process로 실행한다. `run`/`resume`/`wizard`가 선택한 작업을 수행하고 종료한다. 장기 daemon, background service, job scheduler는 만들지 않는다.

추천 사유: realtime Job도 runner lifecycle 안에서 처리하면 됩니다. 별도 daemon은 UOW-008 이후 필요할 때 설계합니다.

B) CLI를 상주 daemon으로 만들어 여러 Job을 계속 받는다.

C) OS scheduler 등록까지 UOW-007에서 지원한다.

X) 기타

[Answer]: A

### Question 7. Ctrl+C Infrastructure Boundary

Ctrl+C 처리의 OS 경계는 어떻게 문서화할까요?

A) (권장) foreground terminal process에서만 graceful stop을 보장한다. Windows/Linux 모두 Python `KeyboardInterrupt`/`signal` 경계에서 처리하고, service manager나 container signal handling은 UOW-008로 둔다.

추천 사유: UOW-007은 로컬 터미널 CLI입니다. 컨테이너 signal 정책은 별도 배포 단위입니다.

B) systemd, Windows Service, Docker signal까지 모두 UOW-007에서 문서화한다.

C) Ctrl+C는 인프라 문서에서 제외한다.

X) 기타

[Answer]: A

### Question 8. Adapter Test Infrastructure

UOW-007 테스트 실행 인프라는 어떻게 구성할까요?

A) (권장) 기본 pytest는 fake runner, fake input/output stream, deterministic run id factory, tmp_path를 사용하고 live network 없이 실행한다. console script smoke는 editable install 환경에서 선택적으로 확인할 수 있게 문서화한다.

추천 사유: 기본 테스트는 빠르고 재현 가능해야 합니다. console script 설치 검증은 환경 의존성이 있습니다.

B) 기본 pytest에서 실제 `pip install -e .` 후 console script를 항상 실행한다.

C) CLI 테스트는 모두 수동으로만 한다.

X) 기타

[Answer]: A

### Question 9. Shared Infrastructure Artifact

UOW-007에서 shared infrastructure 산출물이 필요할까요?

A) (권장) 필요하지 않다. UOW-007은 local CLI adapter이며 shared infra는 UOW-008의 container/MCP/Garage/PostgreSQL 단계와 UOW-010 CDK 단계에서 작성한다.

추천 사유: 지금 shared infra를 만들면 아직 배포하지 않는 구성까지 추측하게 됩니다.

B) CLI 전용 shared infrastructure 문서를 만든다.

C) UOW-007에서 Docker/MCP/Garage/PostgreSQL 전체 shared infra 문서를 만든다.

X) 기타

[Answer]: A

## 답변 후 진행 방식

답변이 모두 채워지면 다음을 수행합니다.

1. 답변의 모호함과 충돌 여부를 검토합니다.
2. 모호한 답변이 있으면 follow-up 질문을 추가합니다.
3. 답변이 명확하면 UOW-007 Infrastructure Design 산출물 2개를 생성합니다.
4. shared infrastructure 산출물 필요 여부를 기록합니다.
5. 산출물 생성 후 사용자 승인 전에는 Code Generation으로 넘어가지 않습니다.

## Approval Gate

질문지를 확정해 주세요.

확정 후 다음 단계는 `UOW-007 Infrastructure Design` 산출물 생성이다.

## Answer Analysis

- **Confirmed Answers**: Q1-Q9 were A.
- **Ambiguity Review**: No ambiguity or conflicts found.
- **Follow-up Questions**: Not required.
- **Shared Infrastructure Artifact**: Not required for UOW-007. Shared infrastructure remains deferred to UOW-008 container/MCP/Garage/PostgreSQL work and UOW-010 CDK.
