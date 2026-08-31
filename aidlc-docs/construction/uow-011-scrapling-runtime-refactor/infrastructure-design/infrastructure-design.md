# Infrastructure Design - UOW-011 Scrapling Runtime Refactor

## Purpose

UOW-011 does not introduce new infrastructure resources. It maps the Scrapling runtime refactor and browser fallback behavior onto the existing one-shot worker, Docker, CDK, storage, checkpoint, and log boundaries.

## Confirmed Infrastructure Answers

| Question | Answer | Infrastructure Decision |
|---|---|---|
| Q1 | A | Reuse existing CLI/Docker/MCP, worker container, CDK Fargate task, S3/Garage output, PostgreSQL checkpoint, and CloudWatch log boundaries. |
| Q2 | A | Keep one worker Docker image containing `.[s3,postgres,browser]` and Chromium. |
| Q3 | A | Keep existing CDK CPU/memory defaults and document scaling through environment config. |
| Q4 | A | Do not expose browser debugging, VNC, remote debugging, or any new inbound port. |
| Q5 | A | Reuse existing output, failure, report, and checkpoint stores; no fallback-specific storage. |
| Q6 | A | Reuse existing structured logs and task failure visibility; no new fallback metric/dashboard/alarm. |
| Q7 | A | Keep Job Queue infrastructure outside UOW-011 and outside this scraper repository. |
| Q8 | A | Defer infra/code verification to Code Generation and Build/Test; this stage only fixes the infrastructure boundary. |

Q1 was blank in the plan file, but the user confirmed the questionnaire. It is defaulted to recommended A because it matches the approved NFR Design and current implementation.

## Infrastructure Footprint

No new infrastructure is added.

Reused boundaries:

- local CLI execution
- existing Docker worker image
- existing `docker-entrypoint.sh`
- existing ECS Fargate one-shot task definition from CDK
- existing S3/Garage-compatible output storage
- existing PostgreSQL checkpoint storage
- existing failure/report JSONL output
- existing CloudWatch stdout/stderr log path
- existing MCP adapter boundary

Not added:

- RabbitMQ broker
- SQS queue or DLQ
- browser fallback service
- browser fallback worker image
- fallback-specific PostgreSQL table
- rendered HTML or screenshot bucket/prefix
- browser debugging port

## Docker Image Boundary

The existing Dockerfile remains the runtime image boundary:

```text
python:3.11-slim
  -> pip install ".[s3,postgres,browser]"
  -> scrapling install
  -> docker-entrypoint.sh
  -> python -m fmkorea_scraper.adapters.container
```

Rules:

- The single worker image supports HTTP-only jobs and browser fallback jobs.
- HTTP-first scraping does not launch Chromium unless required DOM is missing and fallback is enabled.
- Operators do not need to choose between an HTTP image and a browser image.
- CDK continues to reference a prebuilt image URI/tag and does not build the image.

## ECS/Fargate Resource Sizing

Existing CDK config remains valid:

```yaml
ecs:
  cpu: 512
  memory_mib: 1024
  ephemeral_storage_gib:
```

Rules:

- Defaults are not increased for every environment.
- If browser fallback becomes frequent in production jobs, operators should increase `cpu` and `memory_mib` in the environment config.
- No browser-specific task profile is created in UOW-011.
- No automatic scaling policy is added in UOW-011.

## Network Design

Browser fallback is an internal headless process inside the worker container.

Rules:

- No inbound port is opened.
- No browser remote debugging endpoint is exposed.
- No VNC or browser UI access is added.
- Existing outbound-only worker network design remains unchanged.
- Existing proxy support remains environment/config driven.

## Storage And Checkpoint Design

Fallback success and failure use existing storage contracts.

Rules:

- Successful fallback returns HTML to the same parser path.
- Parsed posts/media/comments are stored through existing output stores.
- Fallback failures are represented through existing failure/report/checkpoint paths.
- No fallback-specific DB schema is created.
- No raw rendered HTML, screenshot, header dump, or cookie dump storage is created.

## Observability Design

Fallback observability starts with existing safe logs:

- `browser_fallback_start`
- `browser_fallback_end`
- existing terminal error/report/checkpoint output

Rules:

- No new custom metric is created.
- No fallback-specific dashboard is created.
- Existing ECS task failure visibility remains enough for UOW-011.
- Fallback counters can be added later after real operations data proves the need.

## External Job Queue Boundary

This scraper repository remains a one-shot worker.

Queue infrastructure belongs outside UOW-011:

- RabbitMQ or SQS broker
- queue consumer
- ack/nack handling
- lease and visibility timeout handling
- DLQ
- autoscaling
- central scheduler

Future orchestration platform flow:

```text
Job Queue
  -> external orchestrator
  -> start one-shot worker container with JobConfig/env/argv
  -> worker writes output/failure/report/checkpoint
```

## Shared Infrastructure Impact

No shared infrastructure document change is required for UOW-011.

The existing shared storage, checkpoint, logging, and CDK worker-stack contracts remain sufficient.

## Verification Boundary

Infrastructure Design does not run verification commands.

Verification moves to later gates:

- Code Generation: implement the `HttpClient` fallback lock and unit test it.
- Build/Test: run full pytest, compileall, pip check, and targeted Docker/Chromium smoke when needed.
- Live site smoke remains opt-in.

## Acceptance Criteria

- UOW-011 does not create new infrastructure resources.
- Existing Docker worker image remains the only runtime image.
- Existing ECS/Fargate config remains compatible with browser fallback.
- No browser debugging or inbound access is exposed.
- Existing output/failure/report/checkpoint stores remain authoritative.
- Queue infrastructure remains external to this repository.
- Infrastructure verification is deferred to Code Generation and Build/Test where code changes actually occur.
