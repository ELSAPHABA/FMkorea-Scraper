# Business Rules - UOW-008 Container, MCP, And Test Harness

## Adapter Boundary Rules

- UOW-008 adapters must call existing core APIs and services.
- UOW-008 must not duplicate source traversal, post parsing, comment parsing, retry, rate limit, or worker queue logic.
- Container and MCP adapters must pass validated `JobConfig`, `ResumeRequest`, `RetryRequest`, or request models into core APIs.
- Importing adapter modules must not start a Job, create files, connect to PostgreSQL, connect to S3, prompt a terminal, or perform HTTP requests.

## Docker Entrypoint Rules

- The repository root must contain `docker-entrypoint.sh`.
- Dockerfile `ENTRYPOINT` must call `/app/docker-entrypoint.sh`.
- `docker-entrypoint.sh` must preserve argv and delegate to `python -m fmkorea_scraper.adapters.container "$@"`.
- Docker-specific bootstrap belongs in `docker-entrypoint.sh`; scraper runtime behavior belongs in `fmkorea_scraper.adapters.container`.
- Shell script line endings must be Linux-compatible.

## Dockerignore Rules

- The repository root must contain `.dockerignore`.
- `.dockerignore` must exclude repository metadata, virtual environments, caches, local outputs, `.env` secret candidates, docs, AI-DLC workflow artifacts, and build outputs from Docker build context.
- `.dockerignore` must not exclude files explicitly required by Dockerfile runtime copies.
- Dockerfile must continue to copy explicit runtime inputs rather than using broad `COPY . .`.

## Container Entrypoint Rules

- Container adapter entrypoint must be `fmkorea_scraper.adapters.container.main()`.
- Container mode runs one Job or one resume request per process invocation.
- New container Jobs reuse UOW-007 command normalization and `build_job_config` semantics where possible.
- Container-specific storage and lifecycle configuration is read from environment variables.
- Container stdout/stderr output must be safe for container logs.
- Container rollback is operationally handled by redeploying a previous Git tag or image.

## Container Resume Rules

- `RESUME=true` enables resume mode.
- In resume mode, `JOB_ID` is optional.
- If `JOB_ID` is present, resume that checkpoint.
- If `JOB_ID` is absent, resume the latest checkpoint from PostgreSQL.
- If `RESUME` is not true, run a new Job.
- Resume must restore the original Job config from checkpoint.
- Resume must create new output objects for the resumed run according to output store rules.

## Environment Variable Rules

- Container mode requires `DATABASE_URL` for PostgreSQL checkpoint storage.
- Container mode requires `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY` for S3-compatible output storage.
- `S3_REGION`, `S3_FORCE_PATH_STYLE`, and `S3_PREFIX` are optional.
- `FMKOREA_REALTIME_*` variables keep the same semantics as UOW-007.
- Proxy settings use `FMKOREA_PROXY_HOST`, `FMKOREA_PROXY_ID`, and `FMKOREA_PROXY_PW`.
- User-Agent settings may come from documented environment variables or mounted file paths; user-provided cookie input is not supported.
- Secret values must not be printed in logs, errors, reports, failure records, or MCP responses.
- Container environment loading must read Docker-provided environment variables directly.
- Container environment loading must not create a second plaintext `.env` file inside the image.

## PostgreSQL Checkpoint Rules

- `PostgresCheckpointStore` must implement the existing checkpoint store port.
- Checkpoints are keyed by `job_id`.
- Checkpoint body is stored as validated JSON in `checkpoint_json`.
- `updated_at` is used for latest checkpoint selection.
- `save()` must upsert by `job_id`.
- `load()` must return `None` when a checkpoint does not exist.
- Loaded checkpoint JSON must validate through the shared `Checkpoint` model.
- Database connection errors are mapped to checkpoint/storage failure errors with safe details.

## S3/Garage Output Rules

- Container JSONL output and media output use S3-compatible object storage.
- Garage-specific APIs must not be required.
- SeaweedFS must remain possible later through the same S3-compatible boundary.
- JSONL append must return only after durable object upload succeeds.
- Local spool files are implementation detail and must not define public output locations.
- Checkpoint progress must not advance until the output store reports success.
- S3 credential values must never appear in `StoredObjectRef`, logs, failures, or error details.

## MCP Tool Rules

- MCP exposes `search_board`, `search_integrated`, `fetch_post`, `fetch_comments`, `run_job`, `resume_job`, and `retry_parser_failures`.
- Search/fetch tools call the existing public core API request functions.
- Job tools reuse existing `JobConfig` and `ResumeRequest` validation.
- `retry_parser_failures` must return safe unsupported until UOW-009 implements retry execution.
- MCP tool results must be JSON-serializable.
- MCP tool errors must be safe mapped error objects.
- MCP must not return Python traceback text to clients.
- UOW-008 MCP Job execution is one-shot and blocking for the tool call.
- Background job handles, progress polling, cancellation tools, and scheduling are out of scope.

## Result Quality Harness Rules

- Quality checks use small deterministic fixtures by default.
- JSONL fixture checks must verify required top-level fields.
- Content fixture checks must verify `content.text`, ordered `content.blocks`, media refs, and attachment refs.
- Comment fixture checks must verify flat comments, parent/depth fields, reaction shape, BEST comment `is_best=true`, and `badges`.
- Report fixture checks must validate success, failure, dedupe, and filtered counts.
- Failure fixtures must not include raw HTML, cookies, proxy credentials, tokens, raw headers, raw env, or raw content values.
- Polars checks are optional and must not make Polars a runtime dependency.

## Test Scope Rules

- Default tests must not require Docker, Garage, PostgreSQL, live FMKorea, or a running MCP server.
- Default tests may use fakes, static fixtures, property-based strategies, temporary files, and mock ports.
- Docker, Garage, PostgreSQL, MCP server, and live FMKorea smoke tests must be opt-in through environment variables or explicit test markers.
- Default tests must remain import-safe and deterministic.

## Error Rules

- Validation errors map to exit code `2` in container mode.
- Completed jobs map to exit code `0` in container mode.
- Stopped/runtime failures map to exit code `1` in container mode.
- MCP errors return JSON-safe error payloads.
- Error details must use allow-listed safe fields only.
- Proxy password, raw `.env`, cookies, raw headers, raw HTML/body/content, and tokens must be redacted or omitted.

## Out Of Scope Rules

- UOW-008 does not implement CAPTCHA solving or bypass.
- UOW-008 does not implement parser-failure retry execution.
- UOW-008 does not implement a distributed queue.
- UOW-008 does not implement production Kubernetes manifests.
- UOW-008 does not implement GUI/Web UI.
- UOW-008 does not redesign existing core APIs.
