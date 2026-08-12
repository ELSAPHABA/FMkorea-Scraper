# Unit Of Work Story Map

## Story To Unit Map

| Story | Title | Primary UOW | Supporting UOWs |
|---|---|---|---|
| US-001 | CLI와 터미널 마법사에서 수집 Job을 생성한다 | UOW-007 | UOW-001, UOW-005 |
| US-002 | User-Agent, Proxy, cookie 파일을 안전하게 적용한다 | UOW-002 | UOW-001, UOW-007, UOW-008 |
| US-003 | 요청 속도와 worker 수를 조절한다 | UOW-002 | UOW-001, UOW-005, UOW-007 |
| US-004 | 게시글 URL과 게시판/검색 결과에서 후보 링크를 수집한다 | UOW-003 | UOW-001, UOW-002 |
| US-005 | 통합 검색과 심층검색으로 후보 게시판과 게시글을 수집한다 | UOW-003 | UOW-001, UOW-002, UOW-005 |
| US-006 | 노키워드 범위 수집과 실시간 수집을 실행한다 | UOW-003 | UOW-005, UOW-007 |
| US-007 | 게시글 상세 메타데이터와 본문을 수집한다 | UOW-004 | UOW-001, UOW-002 |
| US-008 | 본문 콘텐츠와 미디어를 Polars-friendly content block으로 저장한다 | UOW-004 | UOW-001, UOW-006 |
| US-009 | 댓글과 답글을 flat list로 수집한다 | UOW-004 | UOW-001, UOW-006 |
| US-010 | Job별 원본 JSONL과 실패 기록을 저장한다 | UOW-006 | UOW-001, UOW-005 |
| US-011 | 원본 JSONL을 공통 분석 스키마로 정규화할 수 있게 한다 | UOW-006 | UOW-001, UOW-004 |
| US-012 | CAPTCHA 또는 차단 감지 시 checkpoint를 저장하고 중단한다 | UOW-005 | UOW-002, UOW-006 |
| US-013 | 중단한 Job을 재개한다 | UOW-005 | UOW-001, UOW-006, UOW-007, UOW-008 |
| US-014 | Parser-stage 실패 게시글만 재처리한다 | UOW-009 | UOW-005, UOW-006, UOW-007 |
| US-015 | Python 라이브러리 API를 제공한다 | UOW-001 | UOW-003, UOW-004, UOW-005, UOW-009 |
| US-016 | 워커 컨테이너와 공유 저장소를 사용한다 | UOW-008 | UOW-006, UOW-005 |
| US-017 | MCP tool 인터페이스를 제공한다 | UOW-008 | UOW-001, UOW-005, UOW-009 |
| US-018 | AWS CDK로 선택 배포 인프라를 정의한다 | UOW-010 | UOW-008 |

## Unit To Story Coverage

### UOW-001. Core Models And Config

- Primary: US-015
- Supporting: US-001, US-002, US-003, US-004, US-005, US-007, US-008, US-009, US-010, US-011, US-013, US-017
- Coverage: shared Pydantic models, core public contracts, validation, BEST comment fields, storage/checkpoint/failure contracts.

### UOW-002. HTTP Runtime Policy

- Primary: US-002, US-003
- Supporting: US-004, US-005, US-007, US-012
- Coverage: request delay, User-Agent, proxy, optional cookie file, timeout/retry, CAPTCHA/block response classification.

### UOW-003. Search And Link Collection

- Primary: US-004, US-005, US-006
- Supporting: US-015
- Coverage: direct URL candidates, board/list/search, integrated search, deep search, no-keyword range, realtime link discovery.

### UOW-004. Post Detail And Content Parsing

- Primary: US-007, US-008, US-009
- Supporting: US-011, US-015
- Coverage: detail metadata, content blocks, FMKorea video, YouTube/X/link/image/attachment blocks, comments/replies, BEST comment fields.

### UOW-005. Job Runner And Checkpoint

- Primary: US-012, US-013
- Supporting: US-001, US-003, US-005, US-006, US-010, US-014, US-015, US-016, US-017
- Coverage: queue orchestration, worker lifecycle, stop/resume, checkpoint ordering, completed key dedupe, realtime termination integration.

### UOW-006. Output And Storage

- Primary: US-010, US-011
- Supporting: US-008, US-009, US-012, US-013, US-014, US-016
- Coverage: JSONL, media, failures, reports, local checkpoint port, S3-compatible output, Garage default, Polars-friendly source preservation.

### UOW-007. CLI Adapter

- Primary: US-001
- Supporting: US-002, US-003, US-006, US-013, US-014
- Coverage: command options, terminal wizard, resume, retry command, runtime option mapping.

### UOW-008. Container, MCP, And Test Harness

- Primary: US-016, US-017
- Supporting: US-002, US-010, US-012, US-013, US-015
- Coverage: one-shot container, PostgreSQL checkpoint, S3-compatible env contract, MCP tools, fixture/PBT/live smoke harness.

### UOW-009. Parser Failure Retry Reprocessor

- Primary: US-014
- Supporting: US-015, US-017
- Coverage: parser-stage failure selection, direct-post retry batch, retry report, optional existing-success skip.

### UOW-010. AWS CDK Infrastructure IaC

- Primary: US-018
- Supporting: US-016
- Coverage: AWS deployable infrastructure path, environment configuration, synth/deploy documentation, no hardcoded secrets.

## Requirements Coverage Summary

| Requirement Area | Covered By |
|---|---|
| CLI, terminal wizard, import API | UOW-001, UOW-007 |
| User-Agent, proxy, cookie, rate limit | UOW-002, UOW-007, UOW-008 |
| Board/search/integrated/deep/no-keyword/realtime link collection | UOW-003, UOW-005 |
| Detail metadata/content/media parsing | UOW-004 |
| Comments, replies, BEST comment fields, reactions | UOW-001, UOW-004, UOW-006 |
| JSONL/media/failure/report storage | UOW-006 |
| Checkpoint/resume/CAPTCHA stop | UOW-002, UOW-005, UOW-006 |
| Parser-stage retry | UOW-009 |
| Container/shared storage/MCP | UOW-008 |
| AWS CDK IaC | UOW-010 |
| Polars normalization readiness | UOW-001, UOW-004, UOW-006 |

## Validation

- Every user story US-001 through US-018 is assigned to at least one primary UOW.
- Every UOW has at least one primary story.
- Cross-cutting security, resiliency, and property-based testing requirements are carried into the relevant UOWs.
