# Public Contracts - UOW-007 CLI Adapter

## Entrypoints

```powershell
python -m fmkorea_scraper.adapters.cli wizard
fmkorea-scraper wizard
```

Both delegate to:

```python
from fmkorea_scraper.adapters.cli import main

exit_code = main(["run", "--source", "direct-post", "--url", "https://www.fmkorea.com/best/101"])
```

Contract:

- importing `fmkorea_scraper.adapters.cli` has no runtime side effects
- `main(argv=None) -> int` returns `0`, `1`, or `2`
- root `main.py` is provided as a thin DCinside-compatible wrapper around `fmkorea_scraper.adapters.cli.main`

## Supported Commands

```powershell
fmkorea-scraper run --source direct-post --url "https://www.fmkorea.com/best/101"
fmkorea-scraper run --source board-search --board-id best --keyword "test"
fmkorea-scraper run --source integrated-search --keyword "test"
fmkorea-scraper resume --job-id job-1
fmkorea-scraper retry-parser-failures --failure-path .\outputs\job-1\run-1\failures.jsonl
fmkorea-scraper import-user-agents .\my-agents.txt
fmkorea-scraper configure-proxy --host proxy.local:8080 --id user
fmkorea-scraper wizard
```

`run --source` supports:

- `direct-post`
- `board-list`
- `board-search`
- `integrated-search`
- `deep-search`
- `no-keyword-range`

Realtime scraping is enabled by `FMKOREA_REALTIME_ENABLED=true` and builds `realtime_keyword` or `realtime_all` sources without a non-realtime `--source`.

## Model Builders

```python
from fmkorea_scraper.adapters.cli import build_job_config, build_resume_request, build_retry_request

job = build_job_config({"source": "board-search", "board_id": "best", "keyword": "test"})
resume = build_resume_request({"job_id": "job-1"})
retry = build_retry_request({"failure_path": "failures.jsonl"})
```

Contract:

- returns validated UOW-001 Pydantic models
- does not pass raw `argparse.Namespace` into the runner
- validation failures surface as `ValidationFailure` or Pydantic `ValidationError`

## Runtime Execution Helpers

```python
from fmkorea_scraper.adapters.cli import run_scrape_command_async, resume_scrape_command_async

await run_scrape_command_async(command)
await resume_scrape_command_async(command)
```

Contract:

- creates `HttpClient`, `LinkCollectorService`, `PostDetailService`, `StorageFactory` stores, `JobRunDependencies`, and `JobRunner`
- calls `core.api.run_job()` or `core.api.resume_job()`
- supports fake runner injection for tests
- passes one CLI-generated `run_id` to both storage factory and runner
- does not implement search pagination, HTML parsing, worker queue logic, or output layout rules

## User-Agent Import

```python
from fmkorea_scraper.adapters.cli import import_user_agents

import_user_agents("source.txt", "user-agents.txt")
```

Contract:

- source must be a regular UTF-8 text file
- all-blank files are rejected
- destination is written through temp-file replace
- command mode writes to `<cwd>/user-agents.txt`

## Proxy Env Update

```python
from fmkorea_scraper.adapters.cli import update_proxy_env

update_proxy_env(".env", {
    "FMKOREA_PROXY_HOST": "proxy.local:8080",
    "FMKOREA_PROXY_ID": "user",
    "FMKOREA_PROXY_PW": "password",
})
```

Contract:

- updates only `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, and `FMKOREA_PROXY_PW`
- preserves unrelated `.env` lines
- writes plaintext by explicit product requirement
- does not call `load_dotenv()` or mutate process environment

## Wizard

```python
from fmkorea_scraper.adapters.cli import WizardSession

command = WizardSession(input_stream, output_stream).collect_command()
```

Contract:

- presents a numbered menu
- returns the same internal command dict shape used by command mode
- does not scrape, parse HTML, write JSONL, or own separate validation logic

## Error And Interrupt Boundaries

```python
from fmkorea_scraper.adapters.cli import InterruptController, print_error
```

Contract:

- first Ctrl+C calls `JobRunner.stop(StopReason.MANUAL_STOP)`
- second Ctrl+C raises `KeyboardInterrupt`
- `print_error()` prints safe mapped summaries
- traceback output is debug-only

## Boundaries

UOW-007 does not implement Docker, PostgreSQL checkpointing, MCP, AWS CDK, parser-failure retry execution, or scraping/parsing internals.
