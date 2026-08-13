# Unit Of Work

## Decomposition Decision

확정 답변에 따라 기준 프로젝트와 같은 10개 Unit of Work를 계승합니다. 단일 Python 패키지 `fmkorea_scraper` 안에서 구현하며, CLI, library, container, MCP는 같은 core API를 호출합니다.

FMKorea-specific URL/query/parser는 UOW-003과 UOW-004에서 구현하고, 공통 runtime, storage, checkpoint, retry, CDK 구조는 기준 프로젝트의 경계를 최대한 유지합니다.

## Units

| Unit | Name | Responsibility | Primary Owner Boundary |
|---|---|---|---|
| UOW-001 | Core Models And Config | Pydantic 모델, Job 설정, validation, public API request/result schema, port protocol | models/config |
| UOW-002 | HTTP Runtime Policy | `httpx` client, request delay, retry, timeout, User-Agent rotation, Proxy, in-memory cookie lifecycle, block/CAPTCHA response classification | runtime |
| UOW-003 | Search And Link Collection | direct URL, board list/search, integrated search, deep search, no-keyword range, realtime link discovery, dedupe, range filter | search |
| UOW-004 | Post Detail And Content Parsing | post metadata/body, comments/replies, BEST comment fields, media/content blocks, attachments, FMKorea video, YouTube/X/link parsing | detail |
| UOW-005 | Job Runner And Checkpoint | `JobRunner`, `asyncio.Queue`, worker pool, lifecycle state, stop/resume, checkpoint update ordering | runtime/detail integration |
| UOW-006 | Output And Storage | local JSONL/media, failure records, S3-compatible output port, Garage default object storage, local checkpoint port | storage |
| UOW-007 | CLI Adapter | command options, terminal wizard, Job creation, resume/retry command, Proxy/User-Agent option flow | adapters |
| UOW-008 | Container, MCP, And Test Harness | one-shot container contract, PostgreSQL checkpoint adapter, MCP tools, fixture tests, PBT, smoke test wiring | adapters/tests |
| UOW-009 | Parser Failure Retry Reprocessor | parser-stage failure records ingestion, direct-post retry batch creation, retry output/report generation, optional existing-success skip | retry/adapters |
| UOW-010 | AWS CDK Infrastructure IaC | AWS CDK app/stacks for deployable scraper infrastructure, environment configuration, synth/deploy documentation | infrastructure |

## Code Organization Strategy

Greenfield code should use this package layout:

```text
src/
  fmkorea_scraper/
    __init__.py
    core/
      api.py
      config.py
      errors.py
      ports.py
    models/
      job.py
      post.py
      comment.py
      content.py
      media.py
      checkpoint.py
      failure.py
      report.py
    http/
      client.py
      user_agent.py
      proxy.py
      rate_limit.py
    search/
      urls.py
      board.py
      integrated.py
      collectors.py
    post_detail/
      metadata.py
      content.py
      comments.py
      service.py
    storage/
      jsonl.py
      media_store.py
      failure_store.py
      checkpoint_store.py
      s3_store.py
    jobs/
      runner.py
      workers.py
      checkpointing.py
    retry/
      parser_failures.py
    adapters/
      cli.py
      container.py
      mcp.py
    infra/
      cdk/
tests/
  fixtures/
  test_*.py
```

## Implementation Order

1. UOW-001 Core Models And Config
2. UOW-002 HTTP Runtime Policy
3. UOW-003 Search And Link Collection
4. UOW-004 Post Detail And Content Parsing
5. UOW-006 Output And Storage
6. UOW-005 Job Runner And Checkpoint
7. UOW-007 CLI Adapter
8. UOW-008 Container, MCP, And Test Harness
9. UOW-009 Parser Failure Retry Reprocessor
10. UOW-010 AWS CDK Infrastructure IaC

Storage is implemented before `JobRunner` integration so result writes and checkpoint commits have concrete ports available.

## Unit Details

### UOW-001. Core Models And Config

- Defines Pydantic models for Job config, requests, post results, content blocks, comments, media, attachments, checkpoint, reports, and failure records.
- Defines `Comment` fields for FMKorea BEST comments: `source_dom_id`, `source_order`, `is_best`, `badges`, `reactions`.
- Defines common enums: Job type, media mode, checkpoint status, stop reason, response kind, storage mode.
- Defines strict input validation shared by CLI, library, container, and MCP.
- Defines minimal port protocols for HTTP, output, media, failure, checkpoint, clock, and logger.
- Excludes `is_repost` and `repost` from the FMKorea source JSON model.

### UOW-002. HTTP Runtime Policy

- Wraps `httpx.AsyncClient`.
- Applies global request delay, retry, timeout, User-Agent, Proxy, and in-memory cookie lifecycle consistently.
- Loads `user-agents.txt`, defaults to rotation every 10 requests, and falls back to one default User-Agent.
- Applies Proxy priority: explicit option first, then `.env`, then disabled.
- Classifies CAPTCHA/block/unavailable responses without bypassing CAPTCHA.
- Ensures raw cookie, proxy password, and other secrets are not logged or persisted.

### UOW-003. Search And Link Collection

- Implements FMKorea direct post URL normalization.
- Parses board list/search pages and integrated search pages.
- Implements board list, board search, integrated search, deep search, no-keyword range, realtime keyword, and realtime all modes.
- Keeps one sequential link collector per Job.
- Applies `(site_id, board_id, document_srl)` dedupe and configured date/post number filters.
- Pushes `PostCandidate` values into the worker queue.
- Treats candidate metadata as filtering/diagnostic hints only; final metadata is parsed from detail pages.

### UOW-004. Post Detail And Content Parsing

- Parses post metadata, category, title, author/member/level, date, views, reactions, comment count, canonical URL, and attachments.
- Parses ordered content blocks for text, image, FMKorea video, YouTube, X/Twitter, general links, and attachments.
- Parses FMKorea video description when present and stores `null` when absent.
- Parses comments/replies as a flat list.
- Detects `li.comment_best` or `.icon-hit` text `BEST` and stores `is_best=true`, `badges=["BEST"]`.
- Parses comment recommendation/downvote values into `reactions.up_count`, `reactions.down_count`, and `reactions.score`.
- Keeps BEST comments inside the same `comments` list; it does not create `best_comments`.

### UOW-005. Job Runner And Checkpoint

- Owns `JobRunner`, queue orchestration, worker pool lifecycle, cancellation, and resume flow.
- Saves checkpoint every configured completed-post interval and immediately on manual stop, error, CAPTCHA/block, timeout, and normal completion.
- Updates checkpoint only after post result storage succeeds.
- Restores Job config, collector cursor, completed keys, and possible remaining queue snapshot.
- Does not guarantee exact restoration of in-flight requests.
- Validates realtime termination and checkpoint behavior with UOW-003.

### UOW-006. Output And Storage

- Writes one JSON object per post to one Job JSONL file.
- Creates a new JSONL file on resume instead of appending to an old Job output.
- Stores failure records and Job reports.
- Supports local media paths and S3-compatible media/object output.
- Uses Garage as the default S3-compatible object store.
- Keeps SeaweedFS as a future replacement through the same S3-compatible port.
- Stores `Comment` objects as received from UOW-004 without reshaping BEST comments.

### UOW-007. CLI Adapter

- Provides command-line execution and terminal wizard.
- Builds `JobConfig` through shared validation.
- Supports direct URL, board list/search, integrated search, deep search, no-keyword range, realtime modes, resume, parser-failure retry, media mode, request interval, worker count, User-Agent file, and Proxy options.
- Calls core async API through `asyncio.run()`.
- Keeps terminal prompts out of core imports.

### UOW-008. Container, MCP, And Test Harness

- Provides one-shot worker container entrypoint.
- Reads `RESUME`, `JOB_ID`, storage env, realtime env, and proxy env.
- Adds PostgreSQL checkpoint adapter for container/shared-store mode.
- Provides MCP tools for search, fetch, Job run, resume, and parser-failure retry.
- Adds parser fixture tests, Hypothesis PBT, import side-effect tests, adapter validation tests, and optional live smoke test hooks.

### UOW-009. Parser Failure Retry Reprocessor

- Reads one or more `failures.jsonl` files and selects only parser-stage post/comment/content failures that can be retried after parser fixes.
- Builds a retry batch from failed post URLs using the existing direct-post and `JobRunner` path.
- Writes retry results to a new output run instead of mutating the original failure file.
- Optionally reads existing `posts.jsonl` outputs to skip already recovered post IDs.
- Preserves CAPTCHA, block, network, storage, checkpoint, and manual stop failures outside this unit.

### UOW-010. AWS CDK Infrastructure IaC

- Provides AWS CDK infrastructure code after UOW-009 is complete.
- Defines deployable infrastructure for running scraper workers and their required storage/checkpoint/logging dependencies.
- Final AWS resource choices are decided in UOW-010 Functional Design and Infrastructure Design.
- Must avoid embedding secrets in source code and must document environment-specific deployment flow.

## Boundary Rules

- Parser components do not perform network or storage I/O.
- All network I/O goes through `HttpClient`.
- All result, media, failure, and checkpoint writes go through storage ports.
- Adapters do not contain scraping logic.
- Core import must not start a scrape, prompt the terminal, or create files.
- UOW-004 owns filling BEST comment fields; UOW-006 only serializes the model.
- UOW-009 must not duplicate post parsing, HTTP policy, or storage logic.
- UOW-010 must not change scraper runtime behavior; it only provisions and documents infrastructure around the existing container/core contracts.
