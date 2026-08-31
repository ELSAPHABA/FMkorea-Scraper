from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest

from fmkorea_scraper.core.errors import BrowserFallbackError, BlockedResponseError, CaptchaDetectedError, UnavailableContentError
from fmkorea_scraper.http import (
    HttpClient,
    HttpResponse,
    HttpRuntimeConfig,
    ProxyConfig,
    RetryPolicy,
    SafeHttpEventBuilder,
    UserAgentConfig,
)
from fmkorea_scraper.http.runtime import DotenvProxyLoader


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def run(coro):
    return asyncio.run(coro)


def test_dotenv_loader_reads_allowlist_without_mutating_environment(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "FMKOREA_PROXY_HOST=proxy.example.com:8080\n"
        "FMKOREA_PROXY_ID=user\n"
        "FMKOREA_PROXY_PW=secret\n"
        "IGNORED=value\n",
        encoding="utf-8",
    )
    before = dict(os.environ)

    proxy = DotenvProxyLoader().load(env_path)

    assert proxy.enabled is True
    assert proxy.source == "env_file"
    assert proxy.safe_label == "proxy.example.com:8080"
    assert os.environ == before


def test_explicit_proxy_wins_over_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FMKOREA_PROXY_HOST=env.example.com:8080\n", encoding="utf-8")
    config = HttpRuntimeConfig(
        request_interval_seconds=0,
        execution_dir=tmp_path,
        proxy=ProxyConfig.from_values(host="explicit.example.com:9000", source="explicit"),
    )
    client = HttpClient(config, transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok")))

    assert client.proxy.safe_label == "explicit.example.com:9000"
    run(client.close())


def test_user_agent_rotation_clears_in_memory_cookies(tmp_path: Path) -> None:
    ua_path = tmp_path / "user-agents.txt"
    ua_path.write_text("ua-one\nua-two\n", encoding="utf-8")
    seen_cookie_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_cookie_headers.append(request.headers.get("cookie"))
        return httpx.Response(200, text="ok", headers={"set-cookie": "sid=1; Path=/"})

    config = HttpRuntimeConfig(
        request_interval_seconds=0,
        user_agent=UserAgentConfig(explicit_file_path=ua_path, rotation_interval_requests=2),
    )

    async def scenario() -> None:
        async with HttpClient(config, transport=httpx.MockTransport(handler)) as client:
            await client.get("https://www.fmkorea.com/best/1")
            await client.get("https://www.fmkorea.com/best/2")
            await client.get("https://www.fmkorea.com/best/3")

    run(scenario())

    assert seen_cookie_headers == [None, "sid=1", None]


def test_retry_attempts_pass_through_limiter() -> None:
    calls = 0
    sleep_calls = []
    clock = FakeClock()

    async def sleeper(seconds: float) -> None:
        sleep_calls.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, text="temporary failure")
        return httpx.Response(200, text="ok")

    config = HttpRuntimeConfig(
        request_interval_seconds=1.0,
        retry_policy=RetryPolicy(max_attempts=2, backoff_base_seconds=0),
    )

    async def scenario() -> None:
        async with HttpClient(config, transport=httpx.MockTransport(handler), clock=clock, sleeper=sleeper) as client:
            response = await client.get("https://www.fmkorea.com/best/1")
            assert response.status_code == 200

    run(scenario())

    assert calls == 2
    assert 1.0 in sleep_calls


def test_captcha_response_is_not_retried_and_closes_client() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="자동입력 방지")

    config = HttpRuntimeConfig(request_interval_seconds=0, retry_policy=RetryPolicy(max_attempts=3))
    client = HttpClient(config, transport=httpx.MockTransport(handler))

    with pytest.raises(CaptchaDetectedError):
        run(client.get("https://www.fmkorea.com/best/1"))

    assert calls == 1
    assert client.is_closed is True


def test_unavailable_response_does_not_close_shared_client() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, text="삭제된 게시글")
        return httpx.Response(200, text="ok")

    client = HttpClient(HttpRuntimeConfig(request_interval_seconds=0), transport=httpx.MockTransport(handler))

    with pytest.raises(UnavailableContentError):
        run(client.get("https://www.fmkorea.com/best/1"))
    response = run(client.get("https://www.fmkorea.com/best/2"))
    run(client.close())

    assert response.text == "ok"
    assert calls == 2


def test_security_system_response_is_blocked_and_closes_client() -> None:
    client = HttpClient(
        HttpRuntimeConfig(request_interval_seconds=0),
        transport=httpx.MockTransport(lambda request: httpx.Response(430, text="에펨코리아 보안 시스템")),
    )

    with pytest.raises(BlockedResponseError):
        run(client.get("https://www.fmkorea.com/search.php?mid=stock"))

    assert client.is_closed is True


def test_missing_required_dom_uses_browser_fallback() -> None:
    calls = []

    async def browser_fetcher(url: str, **kwargs) -> HttpResponse:
        calls.append((url, kwargs["required_selector"]))
        html = '<main id="bd_capture">rendered</main>'
        return HttpResponse(200, url, {}, html, html.encode(), 0.0)

    client = HttpClient(
        HttpRuntimeConfig(request_interval_seconds=0, browser_fallback_enabled=True),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<main>loading</main>")),
        browser_fetcher=browser_fetcher,
    )

    response = run(client.get("https://www.fmkorea.com/best/1", required_selector="#bd_capture"))
    run(client.close())

    assert "rendered" in response.text
    assert calls == [("https://www.fmkorea.com/best/1", "#bd_capture")]


def test_browser_fallback_is_serialized_per_client() -> None:
    active = 0
    max_active = 0

    async def browser_fetcher(url: str, **kwargs) -> HttpResponse:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        html = '<main id="bd_capture">rendered</main>'
        return HttpResponse(200, url, {}, html, html.encode(), 0.0)

    async def scenario() -> None:
        async with HttpClient(
            HttpRuntimeConfig(request_interval_seconds=0, browser_fallback_enabled=True),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<main>loading</main>")),
            browser_fetcher=browser_fetcher,
        ) as client:
            responses = await asyncio.gather(
                client.get("https://www.fmkorea.com/best/1", required_selector="#bd_capture"),
                client.get("https://www.fmkorea.com/best/2", required_selector="#bd_capture"),
            )
            assert [response.status_code for response in responses] == [200, 200]

    run(scenario())

    assert max_active == 1


def test_blocked_response_never_uses_browser_fallback() -> None:
    calls = []

    async def browser_fetcher(url: str, **kwargs) -> HttpResponse:
        calls.append((url, kwargs))
        raise AssertionError("browser must not run for a blocked response")

    client = HttpClient(
        HttpRuntimeConfig(request_interval_seconds=0, browser_fallback_enabled=True),
        transport=httpx.MockTransport(lambda request: httpx.Response(430, text="에펨코리아 보안 시스템")),
        browser_fetcher=browser_fetcher,
    )

    with pytest.raises(BlockedResponseError):
        run(client.get("https://www.fmkorea.com/best/1", required_selector="#bd_capture"))

    assert calls == []


def test_browser_fallback_missing_required_dom_is_terminal_error() -> None:
    async def browser_fetcher(url: str, **kwargs) -> HttpResponse:
        _ = kwargs
        html = "<main>still loading</main>"
        return HttpResponse(200, url, {}, html, html.encode(), 0.0)

    client = HttpClient(
        HttpRuntimeConfig(request_interval_seconds=0, browser_fallback_enabled=True),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<main>loading</main>")),
        browser_fetcher=browser_fetcher,
    )

    with pytest.raises(BrowserFallbackError):
        run(client.get("https://www.fmkorea.com/best/1", required_selector="#bd_capture"))

    assert client.is_closed is True


def test_cancelled_request_closes_client() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(10)
        return httpx.Response(200, text="late")

    async def scenario() -> HttpClient:
        client = HttpClient(
            HttpRuntimeConfig(request_interval_seconds=0),
            transport=httpx.MockTransport(handler),
        )
        task = asyncio.create_task(client.get("https://www.fmkorea.com/best/1"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return client

    client = run(scenario())

    assert client.is_closed is True


def test_safe_http_event_builder_redacts_query_and_proxy_secret() -> None:
    proxy = ProxyConfig.from_values(host="proxy.example.com:8080", username="user", password="secret")

    event = SafeHttpEventBuilder.build(
        "http_request_start",
        url="https://www.fmkorea.com/search.php?mid=best&token=secret",
        proxy=proxy,
        headers={"cookie": "sid=1"},
        password="secret",
    )

    assert event["url"] == "https://www.fmkorea.com/search.php"
    assert event["proxy"] == "proxy.example.com:8080"
    assert "secret" not in repr(event)
    assert "headers" not in event
