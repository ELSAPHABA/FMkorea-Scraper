# Deployment Architecture - UOW-007 CLI Adapter

## Architecture Classification

UOW-007 has no standalone deployed service architecture.

It is a local CLI adapter inside the Python package.

```text
User terminal
    |
    +-- python -m fmkorea_scraper.adapters.cli ...
    +-- fmkorea-scraper ...
    |
    v
fmkorea_scraper.adapters.cli.main
    |
    +-- command parser
    +-- wizard session
    +-- model builders
    +-- local runtime assembly
    |
    v
UOW-001..UOW-006 package components
    |
    +-- FMKorea HTTP through UOW-002
    +-- local filesystem through UOW-006
```

## Environment Topology

| Environment | UOW-007 Role | Infrastructure |
|---|---|---|
| Local development | run CLI and wizard from source checkout | Python venv, local filesystem |
| Editable install | expose console script | active environment `Scripts/` or `bin/` |
| CI/default tests | validate adapter behavior | pytest, fakes, injected streams, tmp dirs |
| Optional console smoke | verify installed command invocation | editable install environment |
| Container/MCP runtime | not owned by UOW-007 | deferred to UOW-008 |

## Runtime Boundaries

UOW-007 import must not:

- read environment variables
- read `.env`
- read `user-agents.txt`
- read cookie files
- create output directories
- create `Checkpoint.json`
- prompt the terminal
- start network I/O
- start a scraper Job

At explicit command runtime, UOW-007 may:

- parse arguments
- prompt in wizard mode
- create/update `.env`
- create/update `user-agents.txt`
- assemble local runtime services
- call `run_job`
- call `resume_job`
- build `RetryRequest`
- print safe summaries and debug traceback

## Entrypoint Deployment Shape

### `python -m`

```powershell
python -m fmkorea_scraper.adapters.cli run --source board-search ...
python -m fmkorea_scraper.adapters.cli wizard
```

Requires:

- source checkout with `src` on Python path, or installed package

### Console Script

```powershell
pip install -e .
fmkorea-scraper run --source board-search ...
fmkorea-scraper wizard
```

Creates command in active Python environment.

On Windows virtualenv:

```text
.venv\Scripts\fmkorea-scraper.exe
```

No Windows system PATH editing is required when the virtualenv is activated.

## Local Filesystem Deployment Shape

Default current working directory shape:

```text
working-directory/
  .env
  user-agents.txt
  outputs/
  Checkpoint.json
```

Ownership:

| Path | Owner |
|---|---|
| `.env` | UOW-007 Proxy configure |
| `user-agents.txt` | UOW-007 User-Agent import |
| `outputs/` | UOW-006 storage |
| `Checkpoint.json` | UOW-006 checkpoint store |
| media files | UOW-006 media store |

When `--output-path` is set, only UOW-006 output/checkpoint base changes.

`.env` and `user-agents.txt` remain current-working-directory defaults.

## Process Architecture

```text
CLI process
    |
    +-- parse command or wizard answers
    +-- build JobConfig / ResumeRequest / RetryRequest
    +-- generate run_id for run/resume
    +-- create HttpClient
    +-- create LinkCollectorService
    +-- create PostDetailService
    +-- create UOW-006 storage bundle
    +-- create JobRunner
    +-- run or resume one Job
    +-- close HttpClient
    +-- exit with code 0, 1, or 2
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | success |
| 1 | runtime stop/error/CAPTCHA/forced interrupt |
| 2 | validation error |

## Ctrl+C Architecture

```text
Foreground terminal Ctrl+C
    |
    +-- first interrupt -> JobRunner.stop(StopReason.MANUAL_STOP)
    |       |
    |       +-- UOW-005 saves final stopped checkpoint/report
    |
    +-- second interrupt -> best-effort cleanup -> exit 1
```

Scope:

- foreground terminal only
- Python signal/KeyboardInterrupt boundary
- Windows/Linux best effort

Not covered:

- Docker stop signal
- Windows Service
- systemd
- background scheduler

## Test Architecture

Default tests:

```text
pytest / Hypothesis
    |
    +-- tests/test_cli_adapter.py
    +-- tests/test_cli_properties.py
    +-- tests/strategies/cli.py
    |
    +-- fake runner
    +-- fake input/output streams
    +-- deterministic run id factory
    +-- tmp_path for .env/user-agents.txt
    +-- no live network
```

Optional console smoke:

```text
activated venv
pip install -e .
fmkorea-scraper --help
python -m fmkorea_scraper.adapters.cli --help
```

The optional smoke is not part of the default pytest gate.

## External Services

| Service Type | Status | Reason |
|---|---|---|
| FMKorea HTTP | used indirectly during real `run`/`resume` | through UOW-002 HTTP runtime |
| Local filesystem | required | `.env`, `user-agents.txt`, local outputs/checkpoint |
| Garage/S3 | not owned | output backend/provisioning deferred |
| PostgreSQL | not owned | checkpoint adapter deferred |
| MCP server | not owned | UOW-008 |
| Queue/scheduler | not owned | not part of local CLI adapter |
| AWS resources | not owned | UOW-010 |

## Security Boundary

Required behavior at deployment boundary:

- do not print proxy password
- do not print raw `.env`
- do not print cookies/tokens/raw headers/raw body
- keep `.env` out of version control
- keep output/media/checkpoint files out of version control
- keep console script and `python -m` behavior identical

## Infrastructure Handoff

UOW-007 hands off to UOW-008 for deployed runtime concerns:

- worker container entrypoint
- environment variable contract for container
- PostgreSQL checkpoint persistence
- Garage/S3 deployment wiring
- MCP tool hosting
- service/container signal handling
- shared infrastructure artifacts

UOW-007 hands off to UOW-010 for AWS CDK infrastructure.
