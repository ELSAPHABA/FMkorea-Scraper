"""Async HTTP runtime policy for FMKorea requests."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
from dotenv import dotenv_values

from fmkorea_scraper.core.errors import (
    BlockedResponseError,
    CaptchaDetectedError,
    NetworkFailureError,
    ScraperError,
    UnavailableContentError,
)
from fmkorea_scraper.core.ports import LoggerPort

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)
BODY_SAMPLE_BYTES = 4096

Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class TimeoutConfig:
    connect_seconds: float = 10.0
    read_seconds: float = 30.0
    write_seconds: float = 30.0
    pool_seconds: float = 10.0

    def __post_init__(self) -> None:
        for name in ("connect_seconds", "read_seconds", "write_seconds", "pool_seconds"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")

    def to_httpx_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_seconds,
            read=self.read_seconds,
            write=self.write_seconds,
            pool=self.pool_seconds,
        )


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_base_seconds: float = 0.25
    backoff_max_seconds: float = 5.0
    retry_status_codes: frozenset[int] = field(default_factory=lambda: frozenset({429, 500, 502, 503, 504}))
    retry_on_network_error: bool = True
    retry_on_timeout: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_base_seconds < 0:
            raise ValueError("backoff_base_seconds must be >= 0")
        if self.backoff_max_seconds < 0:
            raise ValueError("backoff_max_seconds must be >= 0")


@dataclass(frozen=True)
class UserAgentConfig:
    explicit_file_path: str | Path | None = None
    fallback_file_name: str = "user-agents.txt"
    default_user_agent: str = DEFAULT_USER_AGENT
    rotation_interval_requests: int = 10

    def __post_init__(self) -> None:
        if self.rotation_interval_requests < 1:
            raise ValueError("rotation_interval_requests must be >= 1")
        if not self.default_user_agent.strip():
            raise ValueError("default_user_agent must not be blank")


@dataclass(frozen=True)
class ProxyConfig:
    enabled: bool = False
    source: str = "disabled"
    host: str | None = None
    username: str | None = None
    password: str | None = None

    @classmethod
    def disabled(cls) -> "ProxyConfig":
        return cls()

    @classmethod
    def from_values(
        cls,
        *,
        host: str | None,
        username: str | None = None,
        password: str | None = None,
        source: str = "explicit",
    ) -> "ProxyConfig":
        host = host.strip() if host else None
        if not host:
            return cls.disabled()
        return cls(
            enabled=True,
            source=source,
            host=host,
            username=(username or None),
            password=(password or None),
        )

    @property
    def safe_label(self) -> str:
        if not self.enabled or not self.host:
            return "disabled"
        parts = urlsplit(_ensure_scheme(self.host))
        host = parts.hostname or self.host.rsplit("@", 1)[-1]
        return f"{host}:{parts.port}" if parts.port else host

    def to_httpx_proxy(self) -> str | None:
        if not self.enabled or not self.host:
            return None
        parts = urlsplit(_ensure_scheme(self.host))
        if not self.username:
            return urlunsplit((parts.scheme or "http", parts.netloc, "", "", ""))

        netloc = quote(self.username, safe="")
        if self.password is not None:
            netloc += f":{quote(self.password, safe='')}"
        netloc += "@"
        netloc += parts.hostname or ""
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme or "http", netloc, "", "", ""))


@dataclass(frozen=True)
class HttpRuntimeConfig:
    request_interval_seconds: float = 1.0
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    user_agent: UserAgentConfig = field(default_factory=UserAgentConfig)
    proxy: ProxyConfig | None = None
    proxy_env_path: str | Path | None = None
    execution_dir: str | Path | None = None
    default_headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.request_interval_seconds < 0:
            raise ValueError("request_interval_seconds must be >= 0")

    @property
    def base_dir(self) -> Path:
        return Path(self.execution_dir) if self.execution_dir is not None else Path.cwd()


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    url: str
    headers: dict[str, str]
    text: str
    content: bytes
    elapsed_seconds: float

    @classmethod
    def from_httpx(cls, response: httpx.Response) -> "HttpResponse":
        try:
            elapsed = response.elapsed.total_seconds()
        except RuntimeError:
            elapsed = 0.0
        return cls(
            status_code=response.status_code,
            url=str(response.url),
            headers=dict(response.headers),
            text=response.text,
            content=response.content,
            elapsed_seconds=elapsed,
        )


class ClassificationKind(str, Enum):
    SUCCESS = "success"
    RETRYABLE = "retryable"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    NETWORK_ERROR = "network_error"


@dataclass(frozen=True)
class ResponseClassification:
    kind: ClassificationKind
    retryable: bool = False
    safe_reason: str = ""


class BackoffCalculator:
    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy

    def delay_for_attempt(self, failed_attempt_number: int) -> float:
        if self._policy.backoff_base_seconds == 0:
            return 0.0
        delay = self._policy.backoff_base_seconds * (2 ** max(failed_attempt_number - 1, 0))
        return min(delay, self._policy.backoff_max_seconds)


class RequestRateLimiter:
    def __init__(
        self,
        request_interval_seconds: float,
        *,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        if request_interval_seconds < 0:
            raise ValueError("request_interval_seconds must be >= 0")
        self._interval = request_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._lock = asyncio.Lock()
        self._last_request_started_at: float | None = None

    async def wait(self) -> None:
        async with self._lock:
            now = self._clock()
            if self._last_request_started_at is not None:
                wait_seconds = self._interval - (now - self._last_request_started_at)
                if wait_seconds > 0:
                    await self._sleeper(wait_seconds)
                    now = max(self._clock(), self._last_request_started_at + self._interval)
            self._last_request_started_at = now


class UserAgentProvider:
    def __init__(self, config: UserAgentConfig | None = None, *, execution_dir: str | Path | None = None) -> None:
        self._config = config or UserAgentConfig()
        self._execution_dir = Path(execution_dir) if execution_dir is not None else Path.cwd()
        self.agents = self._load_agents()
        self.rotation_interval_requests = self._config.rotation_interval_requests
        self.request_count = 0
        self.current_index: int | None = None

    def next_for_request(self) -> tuple[str, bool]:
        self.request_count += 1
        next_index = ((self.request_count - 1) // self.rotation_interval_requests) % len(self.agents)
        changed = self.current_index is not None and self.current_index != next_index
        self.current_index = next_index
        return self.agents[next_index], changed

    def _load_agents(self) -> list[str]:
        path = self._select_path()
        if path and path.exists():
            agents = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if agents:
                return agents
        return [self._config.default_user_agent.strip()]

    def _select_path(self) -> Path | None:
        if self._config.explicit_file_path is not None:
            return Path(self._config.explicit_file_path)
        return self._execution_dir / self._config.fallback_file_name


class DotenvProxyLoader:
    def load(self, path: str | Path) -> ProxyConfig:
        values = dotenv_values(path)
        return ProxyConfig.from_values(
            host=values.get("FMKOREA_PROXY_HOST"),
            username=values.get("FMKOREA_PROXY_ID"),
            password=values.get("FMKOREA_PROXY_PW"),
            source="env_file",
        )


class ProxyProvider:
    def __init__(
        self,
        *,
        explicit_proxy: ProxyConfig | None = None,
        env_path: str | Path | None = None,
        execution_dir: str | Path | None = None,
        loader: DotenvProxyLoader | None = None,
    ) -> None:
        self._explicit_proxy = explicit_proxy
        self._env_path = Path(env_path) if env_path is not None else None
        self._execution_dir = Path(execution_dir) if execution_dir is not None else Path.cwd()
        self._loader = loader or DotenvProxyLoader()

    def resolve(self) -> ProxyConfig:
        if self._explicit_proxy and self._explicit_proxy.enabled:
            return self._explicit_proxy
        env_path = self._env_path or (self._execution_dir / ".env")
        if env_path.exists():
            proxy = self._loader.load(env_path)
            if proxy.enabled:
                return proxy
        return ProxyConfig.disabled()


class HeaderBuilder:
    @staticmethod
    def build(
        *,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str,
        caller_headers: Mapping[str, str] | None = None,
        referer: str | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        headers.update(default_headers or {})
        headers["User-Agent"] = user_agent
        headers.update(caller_headers or {})
        if referer is not None:
            headers["Referer"] = referer
        return headers


class ResponseClassifier:
    captcha_markers = ("captcha", "자동입력", "자동 입력", "보안문자")
    blocked_markers = ("blocked", "abnormal access", "비정상적인 접근", "접근이 제한", "차단되었습니다")
    unavailable_markers = (
        "deleted",
        "unavailable",
        "삭제된 게시글",
        "삭제된 게시물",
        "존재하지 않는 게시글",
        "존재하지 않는 게시물",
        "권한이 없습니다",
        "열람할 수 없습니다",
    )

    def __init__(self, retry_status_codes: set[int] | frozenset[int] | None = None) -> None:
        self._retry_status_codes = retry_status_codes or frozenset({429, 500, 502, 503, 504})

    def classify_response(
        self,
        *,
        status_code: int,
        final_url: str,
        headers: Mapping[str, str] | httpx.Headers | None = None,
        body_sample: str = "",
    ) -> ResponseClassification:
        sample = body_sample[:BODY_SAMPLE_BYTES].lower()
        url = final_url.lower()
        if any(marker in sample for marker in self.captcha_markers) or "captcha" in url:
            return ResponseClassification(ClassificationKind.CAPTCHA, safe_reason="captcha detected")
        if status_code == 403 or any(marker in sample for marker in self.blocked_markers):
            return ResponseClassification(ClassificationKind.BLOCKED, safe_reason="blocked response")
        if status_code in {404, 410} or any(marker in sample for marker in self.unavailable_markers):
            return ResponseClassification(ClassificationKind.UNAVAILABLE, safe_reason="unavailable content")
        if status_code in self._retry_status_codes:
            return ResponseClassification(ClassificationKind.RETRYABLE, retryable=True, safe_reason="retryable status")
        if 200 <= status_code < 400:
            return ResponseClassification(ClassificationKind.SUCCESS, safe_reason="success")
        return ResponseClassification(ClassificationKind.UNAVAILABLE, safe_reason="unsupported response")


class SafeHttpEventBuilder:
    @classmethod
    def build(cls, event: str, *, url: str | None = None, proxy: ProxyConfig | None = None, **fields: Any) -> dict[str, Any]:
        safe = {"event": event}
        if url is not None:
            safe["url"] = cls.redact_url(url)
        if proxy is not None:
            safe["proxy_enabled"] = proxy.enabled
            safe["proxy_source"] = proxy.source
            safe["proxy"] = proxy.safe_label
        for key, value in fields.items():
            if key.lower() in {"headers", "body", "content", "cookie", "cookies", "password", "raw_env"}:
                continue
            safe[key] = value
        return safe

    @staticmethod
    def redact_url(url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class NullLogger:
    def debug(self, message: str, **fields: Any) -> None:
        return None

    def info(self, message: str, **fields: Any) -> None:
        return None

    def warning(self, message: str, **fields: Any) -> None:
        return None

    def error(self, message: str, **fields: Any) -> None:
        return None


class HttpClient:
    def __init__(
        self,
        config: HttpRuntimeConfig | None = None,
        *,
        logger: LoggerPort | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        self.config = config or HttpRuntimeConfig()
        self.logger = logger or NullLogger()
        self.user_agents = UserAgentProvider(self.config.user_agent, execution_dir=self.config.base_dir)
        self.proxy = ProxyProvider(
            explicit_proxy=self.config.proxy,
            env_path=self.config.proxy_env_path,
            execution_dir=self.config.base_dir,
        ).resolve()
        self.limiter = RequestRateLimiter(self.config.request_interval_seconds, clock=clock, sleeper=sleeper)
        self.backoff = BackoffCalculator(self.config.retry_policy)
        self.classifier = ResponseClassifier(self.config.retry_policy.retry_status_codes)
        self._sleeper = sleeper
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout.to_httpx_timeout(),
            proxy=self.proxy.to_httpx_proxy(),
            trust_env=False,
            follow_redirects=True,
            transport=transport,
        )

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
    ) -> HttpResponse:
        return await self.request("GET", url, headers=headers, params=params, referer=referer)

    async def post(
        self,
        url: str,
        *,
        data: Any = None,
        headers: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> HttpResponse:
        return await self.request("POST", url, headers=headers, data=data, referer=referer)

    async def download(self, url: str, *, headers: dict[str, str] | None = None) -> bytes:
        return (await self.get(url, headers=headers)).content

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> HttpResponse:
        last_error: Exception | None = None
        policy = self.config.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            user_agent, changed = self.user_agents.next_for_request()
            if changed:
                self._client.cookies.clear()
                self._log("info", "http_user_agent_rotated", url=url)
            request_headers = HeaderBuilder.build(
                default_headers=self.config.default_headers,
                user_agent=user_agent,
                caller_headers=headers,
                referer=referer,
            )
            await self.limiter.wait()
            self._log("debug", "http_request_start", url=url, method=method, attempt=attempt)
            try:
                response = await self._client.request(method, url, params=params, data=data, headers=request_headers)
            except asyncio.CancelledError:
                await self.close()
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                if policy.retry_on_timeout and attempt < policy.max_attempts:
                    await self._retry_sleep(attempt, url=url, reason="timeout")
                    continue
                await self.close()
                raise NetworkFailureError("request timeout", details={"reason": "timeout"}) from exc
            except httpx.RequestError as exc:
                last_error = exc
                if policy.retry_on_network_error and attempt < policy.max_attempts:
                    await self._retry_sleep(attempt, url=url, reason="network_error")
                    continue
                await self.close()
                raise NetworkFailureError("network failure", details={"reason": "network_error"}) from exc

            body_sample = response.text[:BODY_SAMPLE_BYTES]
            classification = self.classifier.classify_response(
                status_code=response.status_code,
                final_url=str(response.url),
                headers=response.headers,
                body_sample=body_sample,
            )
            self._log(
                "debug",
                "http_request_end",
                url=str(response.url),
                method=method,
                attempt=attempt,
                status_code=response.status_code,
                classification=classification.kind.value,
            )
            if classification.kind == ClassificationKind.SUCCESS:
                return HttpResponse.from_httpx(response)
            if classification.kind == ClassificationKind.RETRYABLE and attempt < policy.max_attempts:
                await self._retry_sleep(attempt, url=str(response.url), reason=classification.safe_reason)
                continue

            if classification.kind in {ClassificationKind.CAPTCHA, ClassificationKind.BLOCKED}:
                await self.close()
            raise self._classified_exception(classification, response.status_code)

        await self.close()
        raise NetworkFailureError(
            "network failure",
            details={"reason": last_error.__class__.__name__ if last_error else "exhausted"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _retry_sleep(self, failed_attempt: int, *, url: str, reason: str) -> None:
        delay = self.backoff.delay_for_attempt(failed_attempt)
        self._log("warning", "http_retry", url=url, attempt=failed_attempt, reason=reason, delay_seconds=delay)
        if delay > 0:
            await self._sleeper(delay)

    def _log(self, level: str, event: str, *, url: str, **fields: Any) -> None:
        safe = SafeHttpEventBuilder.build(event, url=url, proxy=self.proxy, **fields)
        getattr(self.logger, level)(event, **safe)

    @staticmethod
    def _classified_exception(classification: ResponseClassification, status_code: int) -> ScraperError:
        details = {"reason": classification.safe_reason}
        if classification.kind == ClassificationKind.CAPTCHA:
            return CaptchaDetectedError("captcha detected", details=details)
        if classification.kind == ClassificationKind.BLOCKED:
            return BlockedResponseError("blocked response", details=details)
        if classification.kind == ClassificationKind.UNAVAILABLE:
            return UnavailableContentError("unavailable content", details=details)
        return NetworkFailureError("retry attempts exhausted", details={"reason": f"http_{status_code}"})


class RuntimePolicyService:
    def create_client(
        self,
        config: HttpRuntimeConfig | None = None,
        *,
        logger: LoggerPort | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = asyncio.sleep,
    ) -> HttpClient:
        return HttpClient(config, logger=logger, transport=transport, clock=clock, sleeper=sleeper)


def _ensure_scheme(host: str) -> str:
    return host if "://" in host else f"http://{host}"
