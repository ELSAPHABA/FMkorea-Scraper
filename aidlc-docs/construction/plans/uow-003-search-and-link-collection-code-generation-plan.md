# Code Generation Plan - UOW-003 Search And Link Collection

이 문서는 `UOW-003 Search And Link Collection` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Approved At**: 2026-08-12T05:40:39Z
- **Code Generated At**: 2026-08-12T05:40:39Z
- **Validation**: `$env:PYTHONPATH='src'; python -m pytest tests` -> 62 passed

## Unit Context

- **Unit**: UOW-003 Search And Link Collection
- **Project Type**: Greenfield Python package
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`
- **Documentation Location**: `aidlc-docs/construction/uow-003-search-and-link-collection/code/`
- **Primary Stories**: US-004, US-005, US-006
- **Supporting Story**: US-015
- **Supporting Role**: UOW-004/UOW-005가 사용할 `PostCandidate` 링크 수집 계층 제공

## Dependencies

| Dependency | Status |
|---|---|
| Prior unit dependency | UOW-001 and UOW-002 approved and implemented |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-003 implements:

- direct FMKorea post URL normalization
- board list URL builder and traversal
- board keyword search URL builder and traversal
- integrated search URL builder and traversal
- no-keyword range collector
- deep search board discovery and sequential per-board keyword search
- realtime keyword/all one-cycle collection
- BeautifulSoup list/search parsers
- range filtering
- candidate and board dedupe
- safe collector summary and row/item parser failure records
- fixture, example, and property-based tests

UOW-003 does not implement:

- post detail metadata/body parsing
- comment/media parsing
- queue ownership
- checkpoint persistence
- JSONL/media/failure storage
- CLI commands or terminal wizard
- container entrypoint
- MCP tools
- Docker, Terraform, AWS CDK, Garage, PostgreSQL, SQS, or monitoring infrastructure

## File Layout Decision

Implement the collector package as:

- `src/fmkorea_scraper/collect/__init__.py`
- `src/fmkorea_scraper/collect/models.py`
- `src/fmkorea_scraper/collect/urls.py`
- `src/fmkorea_scraper/collect/parsers.py`
- `src/fmkorea_scraper/collect/policies.py`
- `src/fmkorea_scraper/collect/service.py`

Reason:

- matches the approved NFR Design
- keeps URL logic, DOM parsing, pure policies, and orchestration separate
- avoids per-mode package/interface ceremony before there is a maintenance need

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Parser dependency | `pyproject.toml` |
| Public collector exports | `src/fmkorea_scraper/collect/__init__.py` |
| Collector value objects | `src/fmkorea_scraper/collect/models.py` |
| URL builders and normalizers | `src/fmkorea_scraper/collect/urls.py` |
| BeautifulSoup parsers | `src/fmkorea_scraper/collect/parsers.py` |
| Range/dedupe/traversal policies | `src/fmkorea_scraper/collect/policies.py` |
| Collector services | `src/fmkorea_scraper/collect/service.py` |
| Top-level convenience exports if appropriate | `src/fmkorea_scraper/__init__.py` |
| URL/policy property tests | `tests/test_collect_properties.py` |
| URL tests | `tests/test_collect_urls.py` |
| Parser fixture tests | `tests/test_collect_parsers.py` |
| Service/fake HTTP tests | `tests/test_collect_service.py` |
| PBT strategies | `tests/strategies/collect.py` |
| Parser fixtures | `tests/fixtures/collect/` |
| Public contract documentation | `aidlc-docs/construction/uow-003-search-and-link-collection/code/public-contracts.md` |
| Code generation summary | `aidlc-docs/construction/uow-003-search-and-link-collection/code/code-generation-summary.md` |

## Database Entities

No database entities or migration scripts are owned by UOW-003.

## Step Sequence

### Step 1. Dependency Update

- [x] Add `beautifulsoup4>=4,<5` if missing.
- [x] Do not add browser automation, scraping framework, URL builder, queue, storage, or database dependency.

### Step 2. Collector Package Setup

- [x] Create `src/fmkorea_scraper/collect/`.
- [x] Create import-safe public exports.
- [x] Avoid network, file, env, prompt, storage, queue, or HTTP client creation at import time.

### Step 3. Collector Models

- [x] Implement `SearchTraversalState`.
- [x] Implement `BoardCandidate`.
- [x] Implement `CollectorFailure`.
- [x] Implement `CollectorSummary`.
- [x] Implement `CollectorRun`.
- [x] Keep failure and summary payloads safe by construction.

### Step 4. URL Builders And Normalizers

- [x] Implement `DirectPostUrlNormalizer`.
- [x] Implement `BoardUrlBuilder`.
- [x] Implement `IntegratedSearchUrlBuilder`.
- [x] Implement safe URL label helpers that exclude full query strings and raw keywords.
- [x] Use `urllib.parse`, not ad hoc query string concatenation.

### Step 5. Policy Components

- [x] Implement `RangeFilterEvaluator`.
- [x] Implement candidate include/skip/stop/detail-validation decisions.
- [x] Implement `CandidateDeduper`.
- [x] Implement `BoardCandidateDeduper`.
- [x] Implement integrated search page clamp at 1000.

### Step 6. Parser Components

- [x] Implement `BoardPageParser` with BeautifulSoup.
- [x] Implement `IntegratedSearchParser` with BeautifulSoup.
- [x] Extract `PostCandidate` values and board candidates.
- [x] Isolate row/item failures into safe `CollectorFailure` records.
- [x] Propagate page-level unknown structures and UOW-002 block/CAPTCHA errors.

### Step 7. Collector Services

- [x] Implement `LinkCollectorService` dispatch.
- [x] Implement `DirectPostCollector`.
- [x] Implement `BoardListCollector`.
- [x] Implement `BoardSearchCollector`.
- [x] Implement `IntegratedSearchCollector`.
- [x] Implement `NoKeywordRangeCollector`.
- [x] Implement `DeepSearchCollector` with sequential per-board search.
- [x] Implement `RealtimeCollectionCycle` as one-cycle collection only.
- [x] Provide async iterator API and `collect_all()` helper.

### Step 8. Testing

- [x] Add direct URL normalization tests.
- [x] Add board and integrated URL builder tests.
- [x] Add parser fixture tests for board list/search, integrated search, no-result, and malformed row/item isolation.
- [x] Add service tests with fake HTTP port.
- [x] Add PBT tests for URL determinism, page clamp, range monotonicity, candidate dedupe idempotence, realtime dedupe exclusion, and deep-search board dedupe.
- [x] Keep live FMKorea network tests out of the default test path.

### Step 9. Documentation

- [x] Generate public contract documentation.
- [x] Generate code generation summary.
- [x] Record no deployment artifacts for this unit.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-004 | direct URL, board list/search, candidate extraction, dedupe, range filter |
| US-005 | integrated search, board discovery, deep search sequential board expansion |
| US-006 | no-keyword range and realtime keyword/all one-cycle link discovery |
| US-015 | importable library API for link collection |

## Completion Criteria

- [x] UOW-003 source files exist under `src/fmkorea_scraper/collect/`.
- [x] `beautifulsoup4` dependency exists if needed.
- [x] Tests for UOW-003 URL, policy, parser, and service behavior exist under `tests/`.
- [x] Documentation summary exists under `aidlc-docs/construction/uow-003-search-and-link-collection/code/`.
- [x] No runtime infrastructure artifact is created for UOW-003.
- [x] `$env:PYTHONPATH='src'; python -m pytest tests` passes.
