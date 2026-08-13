"""Optional MCP adapter handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from pydantic import BaseModel

from fmkorea_scraper.adapters.safe_errors import safe_error_payload
from fmkorea_scraper.core.api import (
    fetch_comments as api_fetch_comments,
    fetch_post as api_fetch_post,
    resume_job as api_resume_job,
    retry_parser_failures as api_retry_parser_failures,
    run_job as api_run_job,
    search_board as api_search_board,
    search_integrated as api_search_integrated,
)
from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig
from fmkorea_scraper.models.job import (
    BoardSearchRequest,
    CommentRequest,
    IntegratedSearchRequest,
    JobConfig,
    PostRequest,
    ResumeRequest,
    RetryRequest,
)

HttpClientFactory = Callable[[], Any]


class McpToolHandlers:
    def __init__(self, *, http_client_factory: HttpClientFactory | None = None) -> None:
        self.http_client_factory = http_client_factory or (lambda: HttpClient(HttpRuntimeConfig()))

    async def search_board(self, payload: Mapping[str, Any], *, http_client: Any | None = None) -> dict[str, Any]:
        return await self._with_http(
            "search_board",
            http_client,
            lambda client: api_search_board(BoardSearchRequest.model_validate(payload), http_client=client),
        )

    async def search_integrated(self, payload: Mapping[str, Any], *, http_client: Any | None = None) -> dict[str, Any]:
        return await self._with_http(
            "search_integrated",
            http_client,
            lambda client: api_search_integrated(IntegratedSearchRequest.model_validate(payload), http_client=client),
        )

    async def fetch_post(self, payload: Mapping[str, Any], *, http_client: Any | None = None) -> dict[str, Any]:
        return await self._with_http(
            "fetch_post",
            http_client,
            lambda client: api_fetch_post(PostRequest.model_validate(payload), http_client=client),
        )

    async def fetch_comments(self, payload: Mapping[str, Any], *, http_client: Any | None = None) -> dict[str, Any]:
        return await self._with_http(
            "fetch_comments",
            http_client,
            lambda client: api_fetch_comments(CommentRequest.model_validate(payload), http_client=client),
        )

    async def run_job(self, payload: Mapping[str, Any], *, runner: Any | None = None) -> dict[str, Any]:
        return await _safe_call("run_job", lambda: api_run_job(JobConfig.model_validate(payload), runner=runner))

    async def resume_job(self, payload: Mapping[str, Any], *, runner: Any | None = None) -> dict[str, Any]:
        return await _safe_call("resume_job", lambda: api_resume_job(ResumeRequest.model_validate(payload), runner=runner))

    async def retry_parser_failures(self, payload: Mapping[str, Any], *, retry_service: Any | None = None) -> dict[str, Any]:
        return await _safe_call(
            "retry_parser_failures",
            lambda: api_retry_parser_failures(RetryRequest.model_validate(payload), retry_service=retry_service),
        )

    async def _with_http(
        self,
        stage: str,
        http_client: Any | None,
        call: Callable[[Any], Awaitable[Any]],
    ) -> dict[str, Any]:
        created = http_client is None
        client = http_client or self.http_client_factory()
        try:
            return await _safe_call(stage, lambda: call(client))
        finally:
            if created and hasattr(client, "close"):
                await client.close()


async def _safe_call(stage: str, call: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
    try:
        return {"ok": True, "data": _jsonable(await call())}
    except Exception as exc:
        return {"ok": False, "error": safe_error_payload(exc, stage=stage)}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def create_mcp_server(handlers: McpToolHandlers | None = None) -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise ValidationFailure("mcp extra is required", details={"reason": "missing_mcp_dependency"}) from exc

    handlers = handlers or McpToolHandlers()
    server = FastMCP("fmkorea-scraper")

    @server.tool()
    async def search_board(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.search_board(payload)

    @server.tool()
    async def search_integrated(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.search_integrated(payload)

    @server.tool()
    async def fetch_post(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.fetch_post(payload)

    @server.tool()
    async def fetch_comments(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.fetch_comments(payload)

    @server.tool()
    async def run_job(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.run_job(payload)

    @server.tool()
    async def resume_job(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.resume_job(payload)

    @server.tool()
    async def retry_parser_failures(payload: dict[str, Any]) -> dict[str, Any]:
        return await handlers.retry_parser_failures(payload)

    return server


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()
