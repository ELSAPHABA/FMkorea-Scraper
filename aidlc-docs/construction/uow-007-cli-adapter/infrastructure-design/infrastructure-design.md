# Infrastructure Design - UOW-007 CLI Adapter

## Scope

UOW-007 is not a standalone service or container runtime. It defines local terminal entrypoints and local execution boundaries for the FMKorea scraper package.

In scope:

- local terminal execution
- package console script
- `python -m fmkorea_scraper.adapters.cli ...`
- virtualenv/editable install behavior
- current-working-directory config file boundary
- local output/config file handoff
- foreground Ctrl+C boundary
- default adapter test infrastructure

Out of scope:

- Docker worker entrypoint
- MCP server hosting
- Garage/PostgreSQL provisioning
- distributed queue
- GUI/Web UI
- external TUI framework
- AWS CDK

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | UOW-007 is an importable package CLI adapter, not a standalone service/container |
| Entrypoints | support `python -m fmkorea_scraper.adapters.cli ...` and console script `fmkorea-scraper ...`; both call `fmkorea_scraper.adapters.cli.main` |
| Root wrapper | root `main.py` is provided as a thin compatibility wrapper |
| Virtualenv/PATH | local development uses activated venv plus `pip install -e .`; no required Windows system PATH editing |
| Execution directory | default base is `Path.cwd()` |
| Output path | `--output-path` changes only UOW-006 output base |
| CLI-owned files | CLI directly creates/updates only `.env` and `user-agents.txt` in current working directory |
| Storage-owned files | `outputs/`, `Checkpoint.json`, and media are created by UOW-006 stores |
| Process lifecycle | one-shot foreground process; no daemon or scheduler |
| Ctrl+C boundary | graceful stop only for foreground terminal process; service/container signals are deferred |
| Test infrastructure | default pytest uses fakes, injected streams, deterministic run id factory, and `tmp_path`; no live network |
| Shared infrastructure | not required for UOW-007 |

## Local Runtime Environment

Required local environment:

- Python 3.11+
- project package import path or installed editable package
- local filesystem access to current working directory
- optional virtualenv

Recommended development setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
fmkorea-scraper wizard
```

The console script is created inside the active Python environment, such as:

```text
.venv/Scripts/fmkorea-scraper.exe
```

Windows system environment variable editing is not required when the virtualenv is activated.

## Entrypoint Boundary

Supported equivalent entrypoints:

```powershell
python -m fmkorea_scraper.adapters.cli wizard
fmkorea-scraper wizard
```

Both must delegate to:

```text
fmkorea_scraper.adapters.cli.main(argv=None) -> int
```

Root `main.py` is available as a compatibility wrapper and delegates to `fmkorea_scraper.adapters.cli.main`.

## Current Working Directory Boundary

The CLI execution directory is `Path.cwd()`.

Default local files:

```text
<cwd>/
  .env
  user-agents.txt
  outputs/              # created by UOW-006 when output base is cwd
  Checkpoint.json       # created by UOW-006 when output base is cwd
```

If `--output-path` is provided:

- `StorageConfig.base_output_path` uses that value
- `outputs/` and `Checkpoint.json` move under that output base
- `.env` and `user-agents.txt` still default to current working directory

The CLI must not use the package installation directory as the default runtime file location.

## Generated File Boundary

UOW-007 may directly create or update:

- `<cwd>/.env`
- `<cwd>/user-agents.txt`

UOW-007 must not directly create or manage:

- `outputs/`
- `Checkpoint.json`
- downloaded media files
- `posts.jsonl`
- `failures.jsonl`
- `report.json`

Those are owned by UOW-006 storage components.

## Process Lifecycle

UOW-007 runs as a one-shot foreground process.

Commands:

- `run`: run one configured Job and exit
- `resume`: resume one Job and exit
- `wizard`: collect one selected action, perform it, and exit or return to menu according to wizard flow
- `retry-parser-failures`: build parser failure retry input and delegate execution when UOW-009 is available
- `import-user-agents`: import file and exit
- `configure-proxy`: update `.env` and exit

UOW-007 does not create:

- daemon process
- background scheduler
- OS service
- distributed worker process

Realtime Jobs are still owned by the same foreground process while the Job is running.

## Ctrl+C Boundary

Foreground terminal Ctrl+C behavior:

- first Ctrl+C requests graceful stop through `JobRunner.stop(StopReason.MANUAL_STOP)`
- CLI waits for UOW-005 final checkpoint/report path
- second Ctrl+C performs best-effort cleanup and returns exit code `1`

Deferred to UOW-008:

- Docker signal policy
- container shutdown grace period
- service manager integration
- Windows Service/systemd behavior

## Test Infrastructure

Default tests use:

- pytest
- Hypothesis for pure properties
- fake runner/runtime helpers
- injected wizard input/output streams
- deterministic run id factory
- `tmp_path` for `.env` and `user-agents.txt`
- no live FMKorea access

Default tests must not require:

- `pip install -e .`
- console script existing on PATH
- real proxy
- real terminal
- Garage/S3
- PostgreSQL

Optional local smoke may verify console script after editable install, but it is not a default gate.

## Version Control Boundary

Runtime files should remain untracked:

- `.env`
- `user-agents.txt` when user-provided
- `outputs/`
- `Checkpoint.json`
- downloaded media

If `.gitignore` lacks required runtime entries during code generation, add only the minimal entries required to prevent credential/output commits.

## Shared Infrastructure

No shared infrastructure artifact is created by UOW-007.

Deferred shared infrastructure:

| Infrastructure | Target Unit |
|---|---|
| worker Docker entrypoint | UOW-008 |
| MCP server hosting | UOW-008 |
| Garage provisioning | UOW-008 |
| PostgreSQL checkpoint adapter/schema | UOW-008 |
| AWS CDK resources | UOW-010 |
| distributed queue/runtime scheduling | later platform unit |

## Implementation Impact

Code generation for UOW-007 may create:

- `src/fmkorea_scraper/adapters/__init__.py`
- `src/fmkorea_scraper/adapters/cli.py`
- console script entry in `pyproject.toml`
- CLI adapter tests
- CLI property tests
- CLI test strategies

Code generation for UOW-007 should not create:

- root `main.py`
- Dockerfile
- compose files
- MCP server process
- Garage config
- PostgreSQL migrations
- scheduler or daemon service
