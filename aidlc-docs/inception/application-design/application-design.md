# Application Design

## Summary

FMKorea-Scraper uses one Python package, `fmkorea_scraper`, with site-specific URL/query/parser logic and shared runtime boundaries inherited from the baseline scraper. The design favors concrete services and minimal ports only at external I/O boundaries.

## Approved Design Decisions

| Question | Decision |
|---|---|
| Package boundary | Single package `fmkorea_scraper` with submodules |
| Models | Pydantic models with `model_dump(mode="json")` |
| Public API | async-first API |
| HTTP policy | Single `HttpClient`/`HttpPort` boundary |
| Site parser boundary | FMKorea-specific collectors/parsers in `search` and `post_detail` |
| Comments | Flat `comments` list; BEST represented by fields |
| Job orchestration | `JobRunner` with one link collector and `asyncio.Queue` post workers |
| Storage | Output, media, failure, checkpoint ports with local/S3/PostgreSQL adapters |
| Checkpoint precision | Job config, collector cursor, completed keys, optional queue snapshot; no exact in-flight restore |
| Container/MCP | one-shot container; MCP thin wrappers around core API |
| Abstraction level | concrete class/function 중심, 외부 I/O 경계만 minimal protocol |

## Artifact Index

- `components.md`: package modules, component responsibilities, and high-level interfaces.
- `component-methods.md`: public method contracts and model contracts.
- `services.md`: orchestration services and service-level rules.
- `component-dependency.md`: dependency matrix, runtime flow, storage flow, data ownership.

## Core Architecture

The runtime path is:

1. Adapter receives CLI, wizard, container, MCP, or library input.
2. `JobConfigValidator` creates typed config/request models.
3. `ScraperFacade` dispatches to direct APIs, `JobRunner`, or retry service.
4. `JobRunner` coordinates a single sequential link collector and a bounded post worker pool.
5. `PostDetailService` fetches and parses final post data from detail pages.
6. `StorageService` writes posts, media, failures, and checkpoints through ports.

## FMKorea-Specific Boundaries

- URL/query builders are FMKorea-specific.
- Board/list/search/integrated/deep-search parsing is FMKorea-specific.
- Post metadata/content/comment parsing is FMKorea-specific.
- BEST comment handling is native to the FMKorea `Comment` model.
- No generic community plugin framework is introduced in this implementation.

## JSONL And Polars Direction

- Source JSONL stores one post per line.
- `comments` remains nested under the post in source JSONL.
- BEST comments are not duplicated in a separate array.
- Polars normalization later separates posts, comments, and media into common tables.
- Original JSONL remains immutable source data.

## Review Gate

This Application Design is ready for review. After approval, the workflow proceeds to Units Generation.
