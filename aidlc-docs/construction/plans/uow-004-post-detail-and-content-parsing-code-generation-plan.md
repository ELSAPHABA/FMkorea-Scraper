# Code Generation Plan - UOW-004 Post Detail And Content Parsing

이 문서는 `UOW-004 Post Detail And Content Parsing` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

## Unit Context

- **Unit**: UOW-004 Post Detail And Content Parsing
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-003 code
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`
- **Documentation Location**: `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/code/`
- **Primary Stories**: US-004, US-005, US-006, US-007
- **Supporting Story**: US-015
- **Supporting Role**: UOW-005/UOW-006이 사용할 post detail parser 계층 제공

## Dependencies

| Dependency | Status |
|---|---|
| Prior unit dependency | UOW-001, UOW-002, and UOW-003 approved and implemented |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-004 implements:

- detail parser package under `src/fmkorea_scraper/parse/`
- `PostDetailService` with injected UOW-002 HTTP boundary
- final detail metadata parsing from scoped detail page HTML
- scoped content traversal preserving DOM order
- image, FMKorea video, YouTube, X/Twitter, link, attachment, and unknown embed blocks
- media and attachment URL normalization and per-post dedupe
- comment/reply parsing with BEST comment fields
- safe parser warning collection and redaction
- backward-compatible optional model extensions for documented media/attachment fields
- fixture, example, and property-based tests

UOW-004 does not implement:

- list/search traversal
- queue ownership
- checkpoint persistence
- JSONL/media/failure storage
- media file downloads
- CLI commands or terminal wizard
- container entrypoint
- MCP tools
- Docker, Terraform, AWS CDK, Garage, PostgreSQL, SQS, or monitoring infrastructure

## File Layout Decision

Implement the parser package as:

- `src/fmkorea_scraper/parse/__init__.py`
- `src/fmkorea_scraper/parse/models.py`
- `src/fmkorea_scraper/parse/metadata.py`
- `src/fmkorea_scraper/parse/content.py`
- `src/fmkorea_scraper/parse/media.py`
- `src/fmkorea_scraper/parse/comments.py`
- `src/fmkorea_scraper/parse/warnings.py`
- `src/fmkorea_scraper/parse/service.py`

Extend existing model files only where needed:

- `src/fmkorea_scraper/models/content.py`
- `src/fmkorea_scraper/models/media.py`
- `src/fmkorea_scraper/models/__init__.py`

Reason:

- matches the approved NFR Design
- keeps parser responsibilities separated without plugin registries or abstract interface ceremony
- preserves existing UOW-001 model package layout

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Public parser exports | `src/fmkorea_scraper/parse/__init__.py` |
| Parser value objects/options | `src/fmkorea_scraper/parse/models.py` |
| Metadata parser | `src/fmkorea_scraper/parse/metadata.py` |
| Content parser | `src/fmkorea_scraper/parse/content.py` |
| Media/attachment parser | `src/fmkorea_scraper/parse/media.py` |
| Comment parser | `src/fmkorea_scraper/parse/comments.py` |
| Safe parser warnings | `src/fmkorea_scraper/parse/warnings.py` |
| Detail parser service | `src/fmkorea_scraper/parse/service.py` |
| Optional content/media model fields | `src/fmkorea_scraper/models/content.py`, `src/fmkorea_scraper/models/media.py` |
| Parser fixture tests | `tests/test_parse_*.py` |
| Parser PBT tests | `tests/test_parse_properties.py` |
| PBT strategies | `tests/strategies/parse.py` |
| Parser fixtures | `tests/fixtures/parse/` |
| Public contract documentation | `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/code/public-contracts.md` |
| Code generation summary | `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/code/code-generation-summary.md` |

## Database Entities

No database entities or migration scripts are owned by UOW-004.

## Step Sequence

### Step 1. Dependency Check

- [ ] Reuse existing `beautifulsoup4>=4,<5`.
- [ ] Do not add browser automation, scraping framework, queue, storage, database, or media downloader dependency.

### Step 2. Model Extension

- [ ] Add typed optional fields for documented image/video/YouTube/X/attachment metadata.
- [ ] Preserve existing required fields and validation behavior.
- [ ] Avoid raw HTML fields.
- [ ] Keep Polars-friendly scalar/list/dict output shapes.

### Step 3. Parser Package Setup

- [ ] Create `src/fmkorea_scraper/parse/`.
- [ ] Create import-safe public exports.
- [ ] Avoid network, file, env, prompt, storage, queue, or HTTP client creation at import time.

### Step 4. Parser Models And Warnings

- [ ] Implement `ParserOptions`.
- [ ] Implement `DetailParseContext`.
- [ ] Implement `ParseWarning`.
- [ ] Implement `ParseWarningCollector`.
- [ ] Implement redaction helpers that reject raw HTML, cookies, proxy data, and full text payloads.

### Step 5. Metadata Parser

- [ ] Parse `#bd_capture` scoped detail metadata.
- [ ] Parse title, author, date, counters, category, canonical URL, board ID, and document ID.
- [ ] Apply UOW-003 candidate fallback only to missing fields.
- [ ] Raise post-level parser failure when document identity, URL, or title is missing.

### Step 6. Media And Attachment Parser

- [ ] Implement URL normalization with `urllib.parse`.
- [ ] Parse `.rd_file a[data-href]` attachments and lookup by `file_srl`.
- [ ] Parse image blocks with highslide/original URL priority.
- [ ] Parse one logical FMKorea video block per video wrapper/source set.
- [ ] Parse YouTube URLs and existing embed URLs.
- [ ] Parse X/Twitter status and existing embed URLs.
- [ ] Implement per-post media dedupe.

### Step 7. Content Parser

- [ ] Locate scoped `.xe_content` container.
- [ ] Traverse child DOM in order.
- [ ] Emit text, media, link, attachment, and unknown embed blocks.
- [ ] Assign unique block order.
- [ ] Build `content.text` from meaningful text/link blocks only.
- [ ] Record recoverable block warnings without failing the post.

### Step 8. Comment Parser

- [ ] Parse `.fdb_lst_ul > li`.
- [ ] Extract numeric comment IDs and raw DOM IDs.
- [ ] Assign `source_order`.
- [ ] Parse author, date, content, up/down reactions, and score.
- [ ] Detect BEST comments as `is_best=true` and `badges=["BEST"]`.
- [ ] Preserve flat comment list.
- [ ] Isolate individual comment parse failures as safe warnings.

### Step 9. Detail Service

- [ ] Implement `PostDetailService`.
- [ ] Use injected UOW-002 HTTP client/port only.
- [ ] Implement `parse(candidate_or_request) -> PostResult`.
- [ ] Implement `parse_html(html, candidate_or_request) -> PostResult`.
- [ ] Fetch additional comment pages sequentially only when discovered and bounded.
- [ ] Propagate UOW-002 CAPTCHA/block/unavailable classifications.

### Step 10. Testing

- [ ] Add detail metadata fixture tests.
- [ ] Add text/image content fixture tests.
- [ ] Add FMKorea video fixture tests.
- [ ] Add YouTube fixture tests.
- [ ] Add X/Twitter fixture tests.
- [ ] Add attachment fixture tests.
- [ ] Add normal comment/reply fixture tests.
- [ ] Add BEST comment fixture tests.
- [ ] Add malformed optional block/comment warning tests.
- [ ] Add required field failure tests.
- [ ] Add service tests with fake UOW-002 HTTP port.
- [ ] Add PBT tests for URL normalization, block order uniqueness, media dedupe idempotence, comment ID extraction, reaction score, required-field validation, and warning redaction.

### Step 11. Documentation

- [ ] Generate public contract documentation.
- [ ] Generate code generation summary.
- [ ] Record no deployment artifacts for this unit.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-004 | detail page metadata, body, media, comments, and final `PostResult` parsing |
| US-005 | integrated/deep search candidates can be parsed through the same detail service |
| US-006 | realtime candidates can be parsed through the same detail service |
| US-007 | comment/reply and BEST comment parsing |
| US-015 | importable library API for detail parsing |

## Completion Criteria

- [ ] UOW-004 source files exist under `src/fmkorea_scraper/parse/`.
- [ ] Existing UOW-001-compatible models are extended without breaking prior tests.
- [ ] Tests for UOW-004 metadata, content, media, comments, service behavior, and PBT policies exist under `tests/`.
- [ ] Documentation summary exists under `aidlc-docs/construction/uow-004-post-detail-and-content-parsing/code/`.
- [ ] No runtime infrastructure artifact is created for UOW-004.
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests` passes.
