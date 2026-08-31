# Business Logic Model - UOW-011 Scrapling Runtime Refactor

## Purpose

UOW-011 documents and validates the Scrapling runtime refactor that happened after the original UOW-010 completion.

It applies only the questionnaire-driven code deltas:

- CLI/Docker browser fallback defaults to enabled
- list/search pages also provide required DOM selectors for fallback triggering
- internal RabbitMQ consumer code stays removed
- Scrapling Spider remains future work

## HTTP And Fallback Flow

```text
request URL
  |
  v
httpx.AsyncClient
  |
  v
response classifier
  |
  +-- CAPTCHA / 430 / blocked -> close client, terminal failure, checkpoint
  |
  +-- retryable -> retry policy
  |
  +-- success -> required DOM selector check
                    |
                    +-- selector exists -> return HTTP response
                    |
                    +-- selector missing and fallback disabled -> return HTTP response
                    |
                    +-- selector missing and fallback enabled -> DynamicFetcher
                                                             |
                                                             +-- selector exists -> return rendered response
                                                             |
                                                             +-- selector missing/error -> terminal failure, checkpoint
```

## Required Selector Mapping

| Request type | Required selector |
|---|---|
| Board list | `div.bd` |
| Board search | `div.bd` |
| No-keyword range | `div.bd` |
| Realtime board cycle | `div.bd` |
| Integrated search | `.searchResult, .search_result` |
| Deep search seed | `.searchResult, .search_result` |
| Realtime integrated cycle | `.searchResult, .search_result` |
| Post detail | `#bd_capture` |

## Adapter Flow

CLI:

```text
python main.py run ...
  -> build JobConfig
  -> build HttpRuntimeConfig(browser_fallback_enabled=True unless --no-browser-fallback)
  -> JobRunner
```

Docker:

```text
docker run ...
  -> docker-entrypoint.sh
  -> adapters.container
  -> ContainerEnvConfig(FMKOREA_BROWSER_FALLBACK defaults true)
  -> JobRunner
```

External platform:

```text
RabbitMQ or other Job Queue
  -> external orchestrator
  -> one-shot scraper worker container
  -> JobRunner
```

The scraper repository does not own the external queue consumer.

## Future Spider Migration

Spider migration is deferred because it changes the execution engine:

- request scheduling
- pause/resume
- checkpoint timing
- failure recording
- parser retry mapping
- worker lifecycle

The current code stays on the existing `JobRunner` model.
