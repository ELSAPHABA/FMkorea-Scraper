# Code Generation Summary - UOW-004 Post Detail And Content Parsing

## Generated At

2026-08-12T12:42:49Z

## Created Application Files

- `src/fmkorea_scraper/parse/__init__.py`
- `src/fmkorea_scraper/parse/models.py`
- `src/fmkorea_scraper/parse/metadata.py`
- `src/fmkorea_scraper/parse/content.py`
- `src/fmkorea_scraper/parse/media.py`
- `src/fmkorea_scraper/parse/comments.py`
- `src/fmkorea_scraper/parse/warnings.py`
- `src/fmkorea_scraper/parse/service.py`

## Modified Application Files

- `src/fmkorea_scraper/models/content.py`
- `src/fmkorea_scraper/models/media.py`
- `src/fmkorea_scraper/core/api.py`
- `tests/snapshots/schema_versions.json`

## Created Tests

- `tests/test_parse_service.py`
- `tests/test_parse_properties.py`
- `tests/strategies/parse.py`
- `tests/fixtures/parse/detail_full.html`
- `tests/fixtures/parse/detail_missing_required.html`
- `tests/fixtures/parse/comment_page.html`

## Implemented Scope

- detail metadata parsing from scoped detail HTML
- candidate/request fallback for missing metadata hints
- ordered content traversal
- image, FMKorea video, YouTube, X/Twitter, link, attachment, and unknown embed blocks
- attachment query metadata extraction
- URL normalization with the standard library
- per-post media dedupe
- comment parsing with BEST status, badges, reactions, and score
- bounded sequential extra comment page fetch through injected HTTP
- duplicate comment ID suppression across comment pages
- public `core.api.fetch_post()` and `core.api.fetch_comments()` parser bridge
- safe parser warning collection and redaction
- optional model extensions for media/attachment metadata
- schema snapshot update for the extended `post` model

## Excluded Scope

- list/search traversal
- queue ownership
- checkpoint persistence
- JSONL/media/failure storage
- media file downloads
- CLI adapter
- terminal wizard
- container entrypoint
- MCP tools
- cloud infrastructure

## Validation

Commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests -q --tb=short
$env:PYTHONPATH='src'; python -m compileall -q src tests
```

Result:

```text
72 passed
compileall passed
```

## Deployment Artifacts

No deployment artifacts were generated for UOW-004.
