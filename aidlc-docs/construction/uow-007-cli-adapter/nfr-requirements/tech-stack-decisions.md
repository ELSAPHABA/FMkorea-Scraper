# Tech Stack Decisions - UOW-007 CLI Adapter

## Runtime And Language

| Decision | Selection | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches existing package baseline. |
| CLI parser | stdlib `argparse` | Confirmed by Functional Design and Q1. |
| Wizard input | stdlib `input`-style stream reads | Numbered menu does not need a TUI dependency. |
| Password input | stdlib `getpass` | Prevents terminal echo for proxy password. |
| File copy | stdlib `shutil` and `pathlib` | Enough for `user-agents.txt` import. |
| Traceback output | stdlib `traceback` | Used only for `--debug` traceback. |
| Signal handling | stdlib `signal` plus `JobRunner.stop(StopReason.MANUAL_STOP)` | Maps terminal Ctrl+C to UOW-005 manual stop. |
| Run ID generation | stdlib `uuid.uuid4().hex` | Avoids an extra dependency and provides low collision risk. |

## Dependency Decisions

| Dependency | Selection | Scope |
|---|---|---|
| Click | Not added | `argparse` covers required command mode. |
| Typer | Not added | Adds dependency and typing layer without current need. |
| Rich | Not added | Progress/color UI is out of scope. |
| prompt-toolkit | Not added | Wizard is a simple numbered text menu. |
| Pydantic | existing dependency | Existing `JobConfig`/`ResumeRequest`/`RetryRequest` validation. |
| Hypothesis | existing test extra | Used for pure mapping and redaction PBT. |
| pytest | existing test extra | Used for adapter example tests. |

## CLI UX Strategy

| Area | Decision |
|---|---|
| Command mode | `run`, `resume`, `retry-parser-failures`, `import-user-agents`, `configure-proxy`, `wizard` |
| Wizard mode | numbered text menu |
| Wizard defaults | show default values where available |
| Invalid wizard input | safe message and retry current prompt |
| Wizard cancel | `q`, back, or empty required input cancellation |
| Stream handling | injectable input/output streams for tests |
| Debug output | safe summary always, traceback only with `--debug` |

## Runtime Strategy

| Area | Decision |
|---|---|
| New Job | build `JobConfig`, generate `run_id`, assemble local dependencies, call `core.api.run_job()` |
| Resume | build `ResumeRequest`, generate new `run_id`, assemble local dependencies, call `core.api.resume_job()` |
| HTTP lifecycle | async context or `try/finally` close |
| First Ctrl+C | call `JobRunner.stop(StopReason.MANUAL_STOP)` |
| Second Ctrl+C | best-effort cleanup and exit code `1` |
| Output layout | delegated to UOW-006 stores through `StorageFactory` |
| Worker orchestration | delegated to UOW-005 runner |
| Parser retry | command shell and `RetryRequest`; execution stays with UOW-009 |

## Configuration File Strategy

| File | Decision |
|---|---|
| `user-agents.txt` | import only readable UTF-8 regular files with at least one non-blank line |
| `.env` | preserve unrelated lines and update only `FMKOREA_PROXY_*` keys |
| Proxy password | collect with `getpass.getpass()` |
| Proxy warning | print plaintext storage warning before write |
| Cookie file | explicit path only; never copy or print raw cookie content |
| Environment mutation | do not call `load_dotenv()`; do not mutate `os.environ` for Proxy loading |

## Security Strategy

| Area | Decision |
|---|---|
| Error summary | safe summary first |
| Traceback | `--debug` only, no locals/config/raw details dump |
| Proxy password | never echoed or printed |
| Raw `.env` | never printed |
| Raw HTTP data | cookies, headers, HTML/body/content forbidden in output |
| Command side effects | import/config commands do not start scraper network activity |

## Testing Stack

| Decision | Selection | Rationale |
|---|---|---|
| Example tests | pytest | Existing test runner. |
| PBT | Hypothesis | Existing project choice. |
| CLI runner tests | direct `main(argv)` and helper calls | Avoid shelling out for most tests. |
| Wizard tests | injected input/output streams | No real terminal required. |
| Network tests | excluded from default gate | Keeps tests deterministic. |
| Signal tests | fake runner/handler hooks | Avoid OS-specific signal flakiness. |
| Run ID tests | injected deterministic factory | Verifies storage/runner alignment without relying on UUID randomness. |

Required default test categories:

- import side-effect safety
- command parsing
- command builder mapping
- wizard answer mapping
- realtime env validation
- safe error/debug traceback boundary
- exit code mapping
- run id and storage alignment
- fake runner invocation
- Ctrl+C graceful stop hook
- User-Agent import file validation
- Proxy `.env` update and password output safety
- cookie file path validation
- pure function PBT

## Deferred Decisions

These are intentionally left for later units or later product work:

- GUI/Web UI
- Rich/progress TUI
- Docker entrypoint UX
- MCP adapter UX
- AWS CDK deployment UX
- live FMKorea CLI smoke tests as default gate
