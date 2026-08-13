# Domain Entities - UOW-007 CLI Adapter

## Existing Contract Entities

UOW-007 reuses the UOW-001 through UOW-006 contracts below.

| Entity | Source | Role |
|---|---|---|
| `JobConfig` | `models/job.py` | validated Job payload built from CLI arguments |
| `ResumeRequest` | `models/job.py` | resume request built from CLI arguments |
| `RetryRequest` | `models/job.py` | parser-failure retry request built from CLI arguments |
| `DirectPostSource` | `models/job.py` | direct post URL source |
| `BoardListSource` | `models/job.py` | board list source |
| `BoardSearchSource` | `models/job.py` | board search source |
| `IntegratedSearchSource` | `models/job.py` | integrated search source |
| `DeepSearchSource` | `models/job.py` | deep search source |
| `NoKeywordRangeSource` | `models/job.py` | no-keyword range source |
| `RealtimeKeywordSource` | `models/job.py` | realtime keyword source built from environment variables |
| `RealtimeAllSource` | `models/job.py` | realtime all source built from environment variables |
| `ScrapeOptions` | `models/job.py` | comments, media, attachment, delay, retry, and parser guardrail options |
| `WorkerConfig` | `models/job.py` | post worker count, media worker count, and queue max size |
| `StorageConfig` | `models/job.py` | output base path and storage backend selection |
| `HttpRuntimeConfig` | `http/runtime.py` | request delay, timeout, retry, User-Agent, Proxy, and execution directory |
| `UserAgentConfig` | `http/runtime.py` | User-Agent file and rotation settings |
| `ProxyConfig` | `http/runtime.py` | resolved explicit Proxy candidate |
| `HttpClient` | `http/runtime.py` | HTTP runtime client used by collectors, detail service, and media downloads |
| `LinkCollectorService` | `collect/service.py` | source-specific link collection facade |
| `PostDetailService` | `parse/service.py` | post/comment/detail fetch and parse facade |
| `StorageFactory` | `outputs/factory.py` | creates output, failure, media, and checkpoint stores |
| `StorageBundle` | `outputs/factory.py` | concrete local/S3-compatible store bundle |
| `JobRunDependencies` | `runner/models.py` | dependency bundle passed to `JobRunner` |
| `JobRunner` | `runner/service.py` | Job lifecycle orchestration |
| `JobRunResult` | `runner/models.py` | in-memory runner result for adapters |
| `JobReport` | `models/report.py` | final report printed by CLI |
| `ScraperError` subclasses | `core/errors.py` | safe exception classes mapped to CLI exit codes |

## CLI Components

### CliMain

Top-level function `main(argv: list[str] | None = None) -> int`.

Responsibilities:

- build the argument parser
- dispatch subcommands
- call command handlers
- convert exceptions into safe output and exit codes
- return an integer exit code

Non-responsibilities:

- scrape pages
- parse HTML
- write checkpoint ordering directly
- perform work on import

### ArgumentParserFactory

Factory for the stdlib `argparse.ArgumentParser`.

Responsibilities:

- define `run`
- define `resume`
- define `retry-parser-failures`
- define `import-user-agents`
- define `configure-proxy`
- define `wizard`
- keep source-specific options grouped and validated through model builders

### JobConfigBuilder

Pure helper that converts parsed CLI arguments and realtime environment into `JobConfig`.

Responsibilities:

- choose the source variant
- build range filters
- build scrape options
- build worker config
- build runtime config
- build storage config
- call Pydantic validation

### ResumeRequestBuilder

Pure helper that converts parsed CLI arguments into `ResumeRequest`.

Responsibilities:

- accept explicit `job_id`
- allow omitted `job_id` so local checkpoint lookup can load latest
- call Pydantic validation

### RetryRequestBuilder

Pure helper that converts parsed CLI arguments into `RetryRequest`.

Responsibilities:

- accept failure input path
- accept optional job ID
- accept skip-existing-success option
- call Pydantic validation
- avoid implementing UOW-009 retry filtering logic

### RealtimeEnvReader

Reads only `FMKOREA_REALTIME_*` variables.

Responsibilities:

- detect realtime enabled state
- build `RealtimeKeywordSource` or `RealtimeAllSource`
- combine realtime environment with CLI board scope options when a realtime source requires board ID
- enforce exactly one termination condition through model validation
- report safe validation errors

### RunIdFactory

Small value generator for CLI-owned `run_id`.

Responsibilities:

- generate a unique run id for each run or resume attempt
- pass the value to `StorageFactory`
- pass the same value to `JobRunner`

### LocalRuntimeFactory

Small composition component for local runs.

Responsibilities:

- build `HttpRuntimeConfig`
- create one `HttpClient`
- create `LinkCollectorService`
- create `PostDetailService`
- create `StorageBundle` through `StorageFactory`
- create `JobRunDependencies`
- create `JobRunner`

This component wires existing services. It does not introduce another scraping abstraction.

### UserAgentImportCommand

Command handler for `import-user-agents`.

Responsibilities:

- validate source file readability
- copy source file to `user-agents.txt`
- preserve plaintext
- print safe success/failure messages

### ProxyConfigureCommand

Command handler for `configure-proxy`.

Responsibilities:

- warn about plaintext credential storage
- collect host, ID, and password
- write `.env` with documented keys
- avoid printing raw password or raw `.env`

### TerminalReporter

Formats human terminal output.

Responsibilities:

- print start summary
- print final report summary
- print resume command
- print safe error summary
- print traceback only in debug mode
- preserve redaction rules

### WizardCommandHandler

Interactive numbered menu handler.

Responsibilities:

- show the main wizard menu
- collect source and option answers for a new scrape
- collect resume `job_id` when needed
- collect parser-failure retry input when needed
- delegate User-Agent import and Proxy configure choices to existing command handlers
- convert answers to the same command entities used by command mode
- return without side effects when the user chooses exit

## Command Entities

### RunCommand

Represents parsed `run` command intent.

Fields:

- source type
- source-specific identifiers and ranges
- output path
- User-Agent file and rotation interval
- Proxy option values
- scrape options
- worker options
- debug flag

Maps to:

- `JobConfig`
- `HttpRuntimeConfig`
- `JobRunner` invocation

### ResumeCommand

Represents parsed `resume` command intent.

Fields:

- optional `job_id`
- output path
- User-Agent, Proxy, and worker/runtime options where applicable
- debug flag

Maps to:

- `ResumeRequest`
- local runtime dependencies
- `JobRunner.resume`

### RetryParserFailuresCommand

Represents parsed parser-failure retry command intent.

Fields:

- failure input path
- optional job ID
- skip existing success flag
- output path
- debug flag

Maps to:

- `RetryRequest`
- UOW-009 retry service when available

### ImportUserAgentsCommand

Represents parsed `import-user-agents` command intent.

Fields:

- source file path
- execution directory

Maps to:

- file copy to `user-agents.txt`

### ConfigureProxyCommand

Represents parsed `configure-proxy` command intent.

Fields:

- proxy host
- proxy ID
- proxy password
- execution directory

Maps to:

- plaintext `.env`
- later `ProxyConfig` via UOW-002 loading rules

### WizardCommand

Represents interactive numbered menu intent.

Fields:

- selected menu action
- collected command answers
- execution directory

Maps to:

- `RunCommand`
- `ResumeCommand`
- `RetryParserFailuresCommand`
- `ImportUserAgentsCommand`
- `ConfigureProxyCommand`

## Exit Code Entity

### CliExitCode

Logical constants:

| Name | Value | Meaning |
|---|---:|---|
| `SUCCESS` | `0` | Job completed successfully or command completed successfully |
| `RUNTIME_ERROR` | `1` | stopped, CAPTCHA, blocked, storage, network, parse, or unexpected runtime failure |
| `VALIDATION_ERROR` | `2` | CLI argument, environment, or Pydantic validation failure |

## Entity Boundaries

- CLI command entities are adapter input shapes, not domain storage records.
- `JobConfig` remains the canonical scrape request model.
- `HttpRuntimeConfig` remains the canonical HTTP runtime model; `JobConfig` does not persist adapter runtime inputs.
- `StorageFactory` and `OutputRunLayout` remain the canonical output layout boundary.
- Terminal output is operational feedback, not JSONL data.
- Proxy credentials and server-set temporary cookie content must not become domain data.
