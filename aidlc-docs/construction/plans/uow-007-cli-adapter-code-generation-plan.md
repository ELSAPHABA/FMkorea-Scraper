# Code Generation Plan - UOW-007 CLI Adapter

이 문서는 `UOW-007 CLI Adapter` 코드 생성을 위한 단일 기준 계획입니다. 실제 코드 생성은 이 계획 승인 후 아래 순서대로만 진행합니다.

- **Plan Created At**: 2026-08-13T01:00:21Z
- **Plan Status**: Generated
- **Plan Approved At**: 2026-08-13T01:06:45Z
- **Code Generated At**: 2026-08-13T01:20:08Z
- **Validation**: $env:PYTHONPATH='src'; python -m pytest tests -q --tb=short -> 118 passed, 2 skipped; $env:PYTHONPATH='src'; python -m compileall -q src tests -> passed

## Unit Context

- **Unit**: UOW-007 CLI Adapter
- **Project Type**: Greenfield Python package with existing UOW-001 to UOW-006 and UOW-005 runtime code
- **Workspace Root**: `D:\HongDev\ELSAPHABA\FMkorea-Scraper`
- **Code Location**: workspace root의 `src/`, `tests/`, `pyproject.toml`, `.gitignore`
- **Documentation Location**: `aidlc-docs/construction/uow-007-cli-adapter/code/`
- **Primary Stories**: US-001
- **Supporting Stories**: US-002, US-003, US-006, US-013, US-014
- **Supporting Role**: 사용자가 로컬 터미널에서 Job 생성, 실행, 재개, 설정 파일 관리, 향후 parser-failure retry 명령을 사용할 수 있게 하는 어댑터 제공

## Dependencies

| Dependency | Status |
|---|---|
| UOW-001 Core Models And Config | Implemented and approved |
| UOW-002 HTTP Runtime Policy | Implemented and approved |
| UOW-003 Search And Link Collection | Implemented and approved |
| UOW-004 Post Detail And Content Parsing | Implemented and approved |
| UOW-006 Output And Storage | Implemented and approved |
| UOW-005 Job Runner And Checkpoint | Implemented and approved |
| Functional Design | Approved |
| NFR Requirements | Approved |
| NFR Design | Approved |
| Infrastructure Design | Approved |

## Scope

UOW-007 implements:

- import-safe adapter package `src/fmkorea_scraper/adapters/`
- stdlib `argparse` CLI entrypoint
- console script `fmkorea-scraper`
- `python -m fmkorea_scraper.adapters.cli`
- `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard` subcommands
- command dict normalization shared by CLI and wizard
- `JobConfig`, `ResumeRequest`, and `RetryRequest` builders
- realtime environment source mapping with exactly-one termination validation
- runtime options mapping for comments, media, request interval, timeout, worker count, queue size, User-Agent, Proxy, and output path
- local runtime assembly using existing HTTP, collector, parser, storage factory, and runner components
- explicit CLI `run_id` generation and storage/runner alignment
- safe terminal start/report/error output
- first Ctrl+C graceful stop and second Ctrl+C forced interrupt boundary
- atomic User-Agent import to `<cwd>/user-agents.txt`
- plaintext Proxy `.env` update for `FMKOREA_PROXY_*` keys only
- default no-live-network tests and pure property tests
- public contract and code generation summary docs

UOW-007 does not implement:

- FMKorea URL/query parsing logic
- BeautifulSoup detail parsing
- worker queue internals
- JSONL/media/checkpoint layout rules
- parser-failure retry selection or reprocessing engine
- Docker entrypoint
- PostgreSQL checkpoint adapter
- MCP server
- GUI/Web UI
- AWS CDK
- root `main.py`

## Expected Interfaces And Contracts

| Contract | Target Path |
|---|---|
| Adapter package export | `src/fmkorea_scraper/adapters/__init__.py` |
| CLI adapter implementation | `src/fmkorea_scraper/adapters/cli.py` |
| Console script | `pyproject.toml` |
| Optional runtime ignore entries | `.gitignore` |
| CLI example tests | `tests/test_cli_adapter.py` |
| CLI property tests | `tests/test_cli_properties.py` |
| CLI PBT strategies | `tests/strategies/cli.py` |
| Public contract documentation | `aidlc-docs/construction/uow-007-cli-adapter/code/public-contracts.md` |
| Code generation summary | `aidlc-docs/construction/uow-007-cli-adapter/code/code-generation-summary.md` |

## Database Entities

No database entities or migration scripts are owned by UOW-007.

PostgreSQL checkpoint storage remains deferred to UOW-008.

## Step Sequence

### Step 1. Adapter Package Setup

- [x] Create `src/fmkorea_scraper/adapters/__init__.py`.
- [x] Create `src/fmkorea_scraper/adapters/cli.py`.
- [x] Keep imports side-effect free.
- [x] Do not read files, environment variables, prompt, or start network I/O at import time.

### Step 2. Entrypoints And Parser

- [x] Add `[project.scripts] fmkorea-scraper = "fmkorea_scraper.adapters.cli:main"` to `pyproject.toml`.
- [x] Implement `build_parser()`.
- [x] Implement `main(argv: list[str] | None = None) -> int`.
- [x] Support `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, and `wizard`.
- [x] Support `python -m fmkorea_scraper.adapters.cli`.
- [x] Do not create root `main.py`.

### Step 3. Command Normalization And Model Builders

- [x] Implement `normalize_command`.
- [x] Implement `normalize_source_name`.
- [x] Implement `build_job_config`.
- [x] Implement `build_resume_request`.
- [x] Implement `build_retry_request`.
- [x] Map CLI source names to existing UOW-001 source models.
- [x] Build `ScrapeOptions`, `WorkerConfig`, and `StorageConfig` from command fields.
- [x] Keep timeout, User-Agent, and Proxy command fields out of `JobConfig`; map them directly to `HttpRuntimeConfig` during local runtime assembly.

### Step 4. Realtime Environment Mapping

- [x] Read realtime environment only inside builder execution.
- [x] Support `FMKOREA_REALTIME_ENABLED=true`.
- [x] Support `FMKOREA_REALTIME_MODE=keyword|all`.
- [x] Support `FMKOREA_REALTIME_DURATION_SECONDS` and `FMKOREA_REALTIME_END_AT`.
- [x] Reject missing or duplicated realtime termination conditions.
- [x] Reject combining realtime environment with non-realtime `--source`.

### Step 5. Run ID Alignment

- [x] Add backward-compatible optional `run_id` handling to `JobRunner.run`.
- [x] Add backward-compatible optional `run_id` handling to `JobRunner.resume`.
- [x] Add optional `run_id` passthrough to `core.api.run_job`.
- [x] Add optional `run_id` passthrough to `core.api.resume_job`.
- [x] Keep existing runner behavior when `run_id` is omitted.
- [x] Make CLI generate one run id and pass it to both `StorageFactory` and runner execution.

### Step 6. Local Runtime Assembly

- [x] Implement a small `build_local_runtime` helper.
- [x] Create `HttpRuntimeConfig` and `HttpClient`.
- [x] Create `LinkCollectorService`.
- [x] Create `PostDetailService`.
- [x] Create `StorageFactory` bundle with `job_id` and `run_id`.
- [x] Create `JobRunDependencies`.
- [x] Create `JobRunner`.
- [x] Ensure `HttpClient` is closed with `try/finally`.

### Step 7. Command Execution Helpers

- [x] Implement `run_scrape_command_async`.
- [x] Implement `resume_scrape_command_async`.
- [x] Implement `retry_parser_failures_command_async`.
- [x] Keep UOW-009 retry execution unsupported with a safe message until UOW-009 exists.
- [x] Print safe start summary.
- [x] Print final report summary and resume command.
- [x] Map report status to exit codes.

### Step 8. Config File Helpers

- [x] Implement `import_user_agents`.
- [x] Reject missing, non-file, invalid UTF-8, and all-blank source files.
- [x] Write destination atomically.
- [x] Implement `update_proxy_env`.
- [x] Preserve unrelated `.env` lines.
- [x] Replace only `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, and `FMKOREA_PROXY_PW`.
- [x] Use `getpass.getpass()` for proxy password prompts.

### Step 9. Wizard

- [x] Implement `WizardSession`.
- [x] Use injectable input/output streams.
- [x] Present numbered actions.
- [x] Collect run, resume, retry, User-Agent import, Proxy configure, and exit commands.
- [x] Convert answers to the same command dict shape as argparse.
- [x] Provide cancel/exit behavior without side effects.

### Step 10. Error And Interrupt Handling

- [x] Implement `print_error`.
- [x] Print safe mapped error summary by default.
- [x] Print traceback only with `--debug`.
- [x] Implement `InterruptController`.
- [x] First Ctrl+C calls `runner.stop(StopReason.MANUAL_STOP)`.
- [x] Second Ctrl+C raises `KeyboardInterrupt`.
- [x] Restore previous signal handler after command execution.

### Step 11. Runtime Ignore Entries

- [x] Add only missing runtime-generated entries to `.gitignore`.
- [x] Ignore `outputs/`, `Checkpoint.json`, and user-provided `user-agents.txt` if not already ignored.
- [x] Do not ignore source, tests, docs, or fixture files.

### Step 12. Example Tests

- [x] Add `tests/test_cli_adapter.py`.
- [x] Cover parser subcommands.
- [x] Cover source-to-model builders.
- [x] Cover resume and retry request builders.
- [x] Cover realtime environment validation.
- [x] Cover injected fake runner execution without network.
- [x] Cover run id/storage/runner alignment.
- [x] Cover wizard mapping.
- [x] Cover config file helpers.
- [x] Cover safe error and Ctrl+C handling.
- [x] Cover import side-effect safety.

### Step 13. Property Tests

- [x] Add `tests/strategies/cli.py`.
- [x] Add `tests/test_cli_properties.py`.
- [x] Cover direct-post command mapping.
- [x] Cover realtime keyword env mapping.
- [x] Cover pure command normalization invariants.
- [x] Keep PBT away from live network, prompts, and OS signal timing.

### Step 14. Documentation

- [x] Create `aidlc-docs/construction/uow-007-cli-adapter/code/public-contracts.md`.
- [x] Create `aidlc-docs/construction/uow-007-cli-adapter/code/code-generation-summary.md`.
- [x] Record generated files, public functions, commands, and deferred boundaries.

### Step 15. Validation

- [x] Run focused CLI tests.
- [x] Run full default tests.
- [x] Run compile check for `src` and `tests`.
- [x] Record validation command results in code generation summary.

## Story Traceability

| Story | Coverage In This Unit |
|---|---|
| US-001 | CLI and wizard create validated scraping Jobs |
| US-002 | User-Agent import, Proxy `.env`, cookie redaction, and safe terminal handling |
| US-003 | request interval, worker count, queue size, retry, timeout, and media/comment mode options |
| US-006 | no-keyword range and realtime source command/environment mapping |
| US-013 | resume command and latest/explicit checkpoint request mapping |
| US-014 | parser-failure retry command shape and validated request boundary |

## Completion Criteria

- [x] UOW-007 adapter package exists and is import-safe.
- [x] `fmkorea-scraper` console script is configured.
- [x] `python -m fmkorea_scraper.adapters.cli --help` works with `PYTHONPATH=src`.
- [x] Confirmed subcommands parse.
- [x] CLI and wizard share the same builders.
- [x] CLI can execute with fake runner in tests without live network.
- [x] CLI-generated run id is shared by storage and runner.
- [x] Config helper tests verify safe file behavior.
- [x] Code docs exist under `aidlc-docs/construction/uow-007-cli-adapter/code/`.
- [x] Default tests and compile check pass after implementation.

## Approval Gate

UOW-007 Code Generation 계획이 생성되었습니다.

승인 후 실제 코드 생성 단계로 진행한다.

