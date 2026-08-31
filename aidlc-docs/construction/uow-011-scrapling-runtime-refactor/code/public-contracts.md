# Public Contracts - UOW-011 Scrapling Runtime Refactor

## Runtime Contract

`HttpClient` keeps the existing public request API:

```python
await client.get(url, required_selector="#bd_capture")
```

The browser fallback behavior is internal:

- normal requests still use `httpx.AsyncClient`
- fallback runs only when a successful HTTP response is missing the supplied `required_selector`
- fallback is serialized per `HttpClient` instance
- `HttpResponse` is unchanged
- `BrowserFallbackError` is unchanged
- fallback timeout still uses `HttpRuntimeConfig.timeout.read_seconds`

## Adapter Contract

CLI and container fallback defaults remain unchanged:

- CLI enables fallback by default and disables it with `--no-browser-fallback`
- container enables fallback by default and disables it with `FMKOREA_BROWSER_FALLBACK=false`
- no browser worker-count option is added
- no separate browser timeout option is added

## Safety Contract

The runtime must not invoke browser fallback for confirmed CAPTCHA or block responses.

The following remain out of scope:

- CAPTCHA bypass
- stealth or anti-detect mode
- raw HTML, rendered DOM, screenshot, header, cookie, proxy secret, or environment dumps
- fallback-specific storage, metrics, dashboard, or infrastructure

## Platform Contract

This repository remains a one-shot scraper worker.

RabbitMQ, SQS, DLQ, queue consumer, lease handling, scheduling, autoscaling, and shared orchestration belong to a future external platform. Scrapling Spider remains a future separate UOW because it changes the runner/checkpoint execution engine.

