# Deployment Architecture - UOW-011 Scrapling Runtime Refactor

## Overview

UOW-011 keeps the deployment architecture unchanged. The runtime now uses Scrapling parsing and optional browser fallback inside the existing one-shot worker boundary.

```text
Operator / CI / External Orchestrator
  |
  | JobConfig, env, argv
  v
One-shot worker container
  |
  +-- httpx request path
  |
  +-- Scrapling Selector parsing
  |
  +-- optional DynamicFetcher fallback inside same container
  |
  +-- output/failure/report writes
  |
  +-- checkpoint writes
```

## Local CLI Deployment

```text
python main.py run ...
  -> adapters.cli
  -> JobRunner
  -> HttpClient
  -> output/checkpoint stores
```

Notes:

- Browser fallback is available only when the local environment has the `browser` extra and Playwright/Chromium installed.
- No local browser service or port is opened.
- `--no-browser-fallback` disables fallback.

## Docker Worker Deployment

```text
docker run ...
  -> docker-entrypoint.sh
  -> python -m fmkorea_scraper.adapters.container
  -> JobRunner
  -> HttpClient
  -> optional DynamicFetcher fallback
```

The worker image includes:

- base scraper package
- S3-compatible storage dependency
- PostgreSQL checkpoint dependency
- browser fallback dependency
- Chromium installed by `scrapling install`

The same image runs both HTTP-only and fallback-capable jobs.

## ECS Fargate Deployment

Existing CDK worker stack remains valid:

```text
ECS Fargate task definition
  |
  +-- worker container image URI/tag
  +-- command/env
  +-- Secrets Manager injected secrets
  +-- CloudWatch Logs
  +-- S3 output permissions
  +-- PostgreSQL checkpoint connectivity
```

Default resource config remains:

```yaml
cpu: 512
memory_mib: 1024
ephemeral_storage_gib: null
```

For fallback-heavy jobs, operators may increase CPU/memory through the existing CDK environment config.

## Network Architecture

```text
Internet
  |
  v
Outbound-only worker container
  |
  +-- normal HTTP requests
  +-- optional headless browser requests
  |
  v
Target website

Worker container
  |
  v
Private PostgreSQL checkpoint endpoint

Worker container
  |
  v
S3/Garage-compatible object storage
```

No new inbound path is introduced:

- no browser debugging port
- no VNC
- no browser UI
- no API listener

## Storage Architecture

Fallback does not create a separate storage path.

```text
HTTP or browser-rendered HTML
  -> same parser path
  -> posts.jsonl / media / failures.jsonl / report.json
  -> checkpoint
```

Rules:

- rendered HTML is not stored as raw debug data
- screenshots are not stored
- cookies and headers are not stored
- fallback errors use existing failure/report/checkpoint paths

## Observability Architecture

Existing observability remains:

```text
worker stdout/stderr
  -> CloudWatch Logs or terminal

terminal fallback failure
  -> existing report/checkpoint

ECS task failed/stopped
  -> existing task failure visibility
```

Fallback-specific logs are safe structured events only.

No custom fallback metric or dashboard is created in UOW-011.

## External Orchestrator Architecture

Future platform-owned queue flow:

```text
RabbitMQ/SQS/other Job Queue
  -> external platform orchestrator
  -> start one-shot worker container
  -> scraper runs one Job
  -> scraper exits
```

This repository does not deploy or run:

- queue broker
- queue consumer
- DLQ
- lease manager
- autoscaler
- platform scheduler

## Failure Flow

```text
HTTP success but required DOM missing
  -> browser fallback enabled?
      no  -> return original response to caller
      yes -> wait per-HttpClient fallback lock
             -> run DynamicFetcher
             -> required DOM exists?
                 yes -> parse/store normally
                 no  -> BrowserFallbackError
                         -> terminal checkpoint/report
```

Confirmed CAPTCHA/block responses bypass this flow and fail closed before browser fallback.

## Deployment Constraints

- CDK does not build or push Docker images.
- The worker image must be built and pushed before ECS deployment uses a new version.
- Browser fallback adds image size and runtime memory pressure, but no new infrastructure service.
- Live site validation remains separate from default infrastructure validation.
