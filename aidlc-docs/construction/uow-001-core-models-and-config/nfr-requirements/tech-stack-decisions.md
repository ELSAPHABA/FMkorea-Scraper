# Tech Stack Decisions - UOW-001 Core Models And Config

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Modern typing support and async runtime compatibility |
| Packaging | `pyproject.toml` | Standard Python packaging entry point |
| Source layout | `src/fmkorea_scraper/` | Prevents accidental imports from project root |

## Model And Validation

| Decision | Selection | Rationale |
|---|---|---|
| Model framework | Pydantic v2 | Strong validation, discriminated unions, `model_dump(mode="json")` |
| Extra fields | `extra="forbid"` | Stable schema and explicit validation |
| Extension field | `metadata: dict[str, Any]` with bounds | Controlled future extension without arbitrary top-level fields |
| Job source model | discriminated union | Clear source-specific validation |
| Content block model | discriminated union | Ordered body blocks with type-safe payloads |
| Comment model | one flat `Comment` model | Normal, reply, and BEST comments remain Polars-normalization friendly |
| Error model | typed exceptions plus `ErrorResult` at adapter boundary | Pythonic core flow and safe external errors |

## Dependency Management

| Decision | Selection | Rationale |
|---|---|---|
| Dependency version policy | compatible ranges in `pyproject.toml` plus lock file exact versions | Library-friendly metadata and reproducible execution |
| Lock file | Required | SECURITY-10 supply chain requirement |
| Dependency source | official Python package index or verified private registry | Avoid unvetted dependencies |
| Unused dependency policy | prohibited | Keep model unit small and auditable |

Initial dependencies expected for this unit:

- `pydantic>=2,<3`
- `pytest` for example tests
- `hypothesis` for property-based tests

Exact versions are fixed by the lock file during code generation.

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example test runner | pytest | Standard Python test runner |
| Property-based testing | Hypothesis | Supports custom generators, shrinking, and seed reproducibility |
| PBT generator style | domain-specific strategies | Required for meaningful model invariants |
| Serialization test target | Pydantic JSON mode | Matches JSONL/checkpoint/failure/report output boundary |

Required PBT categories:

- JSON round trip
- Job source discriminator invariants
- range and realtime termination invariants
- content order invariants
- BEST comment invariants
- checkpoint status/reason invariants

## Schema Versioning

| Schema | Initial Version |
|---|---|
| Post JSONL | `fmkorea.post.v1` |
| Checkpoint | `fmkorea.checkpoint.v1` |
| Failure record | `fmkorea.failure.v1` |
| Job report | `fmkorea.job_report.v1` |

Compatibility rules:

- same major version forbids field deletion
- same major version forbids existing field type changes
- same major version forbids required field additions
- same major version allows nullable field additions
- breaking changes require a new schema version and migration note

## Security Decisions

| Area | Decision |
|---|---|
| Input validation | all public input/config models include type, format, length/count constraints |
| Metadata | JSON-serializable only, bounded depth and serialized byte size |
| Error output | no raw validation input in adapter-facing `ErrorResult.details` by default |
| Secret handling | proxy password, cookie, token, `.env`, and raw credential data are forbidden in error details and logs |
| Deserialization | only safe JSON/Pydantic deserialization, no dynamic object loading |
| Import behavior | no network, file, env, or terminal side effects on import |

## Performance Decisions

No fixed millisecond SLA is set for UOW-001 alone.

Performance target:

- validation and serialization must not be the dominant bottleneck for normal post fixtures
- concrete thresholds are measured later during UOW-004/UOW-005 integration
- validation must bound recursive or large metadata structures to avoid runaway CPU/memory use

## Maintainability Decisions

| Area | Decision |
|---|---|
| Public model docs | docstrings and markdown contract required |
| Enum changes | require migration note if they affect persisted data |
| Schema changes | require version policy review |
| Downstream consumers | CLI, container, MCP, Polars normalizer, and future RAG pipelines must use the same model contract |
| Source schema boundary | FMKorea source JSONL keeps FMKorea-native fields; cross-community fields belong in later normalization |

## Deferred Decisions

These are intentionally not decided in UOW-001:

- exact HTTP timeout/retry values
- concrete parser selector fallback order
- final local/S3/PostgreSQL storage implementation details
- container base image and deployment topology
- exact performance threshold for full Job throughput
- S3-compatible object store implementation details
- MCP server deployment mode
