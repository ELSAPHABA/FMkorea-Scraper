# Unit Of Work Dependency

## Implementation Sequence

| Order | Unit | Depends On | Reason |
|---|---|---|---|
| 1 | UOW-001 Core Models And Config | None | Defines shared schemas, validation, and ports |
| 2 | UOW-002 HTTP Runtime Policy | UOW-001 | Uses config, errors, logger/clock ports |
| 3 | UOW-003 Search And Link Collection | UOW-001, UOW-002 | Uses request models and HTTP client |
| 4 | UOW-004 Post Detail And Content Parsing | UOW-001, UOW-002 | Uses post/comment/content models and HTTP client |
| 5 | UOW-006 Output And Storage | UOW-001 | Uses result/failure/checkpoint models and storage ports |
| 6 | UOW-005 Job Runner And Checkpoint | UOW-001, UOW-002, UOW-003, UOW-004, UOW-006 | Orchestrates collectors, parsers, output, checkpoint |
| 7 | UOW-007 CLI Adapter | UOW-001, UOW-005 | Builds configs and calls core Job APIs |
| 8 | UOW-008 Container, MCP, And Test Harness | UOW-001 through UOW-007 | Wraps stable core and adds integration harnesses |
| 9 | UOW-009 Parser Failure Retry Reprocessor | UOW-001, UOW-005, UOW-006, UOW-007 | Reads failures and composes direct-post retry path |
| 10 | UOW-010 AWS CDK Infrastructure IaC | UOW-008, UOW-009 | Uses finalized container/storage/checkpoint contracts |

## Dependency Matrix

| Unit | UOW-001 | UOW-002 | UOW-003 | UOW-004 | UOW-006 | UOW-005 | UOW-007 | UOW-008 | UOW-009 | UOW-010 |
|---|---|---|---|---|---|---|---|---|---|---|
| UOW-001 | - | - | - | - | - | - | - | - | - | - |
| UOW-002 | Required | - | - | - | - | - | - | - | - | - |
| UOW-003 | Required | Required | - | - | - | - | - | - | - | - |
| UOW-004 | Required | Required | - | - | - | - | - | - | - | - |
| UOW-006 | Required | - | - | - | - | - | - | - | - | - |
| UOW-005 | Required | Required | Required | Required | Required | - | - | - | - | - |
| UOW-007 | Required | - | - | - | - | Required | - | - | - | - |
| UOW-008 | Required | Required | Required | Required | Required | Required | Required | - | - | - |
| UOW-009 | Required | - | - | - | Required | Required | Required | - | - | - |
| UOW-010 | Required | - | - | - | Required | Required | - | Required | Required | - |

## Critical Path

1. UOW-001 establishes the shared contracts.
2. UOW-002 enables all live/fake HTTP flows.
3. UOW-003 and UOW-004 can be designed after UOW-002 and may be implemented in sequence for simpler fixture reuse.
4. UOW-006 must precede UOW-005 so checkpoint update ordering can be verified against real output ports.
5. UOW-007 validates user-facing local execution.
6. UOW-008 adds container/MCP/shared checkpoint integration after CLI/core behavior stabilizes.
7. UOW-009 composes existing failure/output/job paths.
8. UOW-010 is last because it depends on stable container and storage contracts.

## Cross-Unit Contracts

| Contract | Producer | Consumer |
|---|---|---|
| `JobConfig`, `ScrapeOptions`, `WorkerConfig` | UOW-001 | UOW-003, UOW-005, UOW-007, UOW-008 |
| `PostCandidate` | UOW-001/UOW-003 | UOW-005 |
| `PostResult` | UOW-001/UOW-004 | UOW-006, UOW-005, UOW-009 |
| `Comment` with BEST fields | UOW-001/UOW-004 | UOW-006, Polars normalization |
| `FailureRecord` | UOW-001/UOW-005/UOW-006 | UOW-009 |
| `Checkpoint` | UOW-001/UOW-005 | UOW-006, UOW-008 |
| `HttpPort` | UOW-001/UOW-002 | UOW-003, UOW-004 |
| `OutputStorePort`, `FailureStorePort`, `CheckpointStorePort` | UOW-001/UOW-006 | UOW-005, UOW-008, UOW-009 |
| CLI/container/MCP request contract | UOW-001/UOW-007 | UOW-008, UOW-010 |

## Integration Checkpoints

| After Unit | Integration Check |
|---|---|
| UOW-001 | Models serialize with `model_dump(mode="json")`; import has no side effects |
| UOW-002 | HTTP client applies delay, UA, proxy, cookie, timeout, safe response classification |
| UOW-003 | Search/link collectors return deduped candidates without scraping final post metadata |
| UOW-004 | Detail parser returns final metadata, content blocks, comments, BEST fields |
| UOW-006 | JSONL/failure/checkpoint ports can persist model outputs |
| UOW-005 | JobRunner stores post before checkpoint advance and resumes with dedupe |
| UOW-007 | CLI/wizard creates valid `JobConfig` and calls core APIs |
| UOW-008 | Container/MCP wraps same core APIs; PostgreSQL checkpoint adapter works |
| UOW-009 | Parser-stage retry reuses direct-post path and writes a new run |
| UOW-010 | CDK synth validates deployable template without hardcoded secrets |

## Parallelization Notes

- UOW-003 and UOW-004 share HTTP/model contracts but touch different parser fixtures. They may be worked on by separate owners after UOW-002, but sequential execution remains the default.
- UOW-006 can proceed after UOW-001 because it does not require real parser behavior.
- UOW-010 should not start before UOW-008 contracts stabilize.

## Risk Hotspots

- FMKorea HTML selector drift affects UOW-003 and UOW-004.
- BEST 댓글 duplication risk is controlled by keeping one `comments` list and an `is_best` flag.
- Checkpoint correctness depends on UOW-006 output writes finishing before UOW-005 checkpoint advance.
- Cookie/proxy secrets must be masked consistently across UOW-002, UOW-006, UOW-007, UOW-008, and UOW-009.
