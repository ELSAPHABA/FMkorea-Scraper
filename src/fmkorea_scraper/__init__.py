"""FMKorea scraper core contracts."""

from __future__ import annotations

from fmkorea_scraper.core.api import (
    fetch_comments,
    fetch_post,
    resume_job,
    retry_parser_failures,
    run_job,
    search_board,
    search_integrated,
)
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.comment import Comment
from fmkorea_scraper.models.job import JobConfig
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.http import HttpClient, HttpRuntimeConfig, ProxyConfig, RetryPolicy, UserAgentConfig
from fmkorea_scraper.collect import LinkCollectorService

__all__ = [
    "Checkpoint",
    "Comment",
    "JobConfig",
    "LinkCollectorService",
    "PostResult",
    "HttpClient",
    "HttpRuntimeConfig",
    "ProxyConfig",
    "RetryPolicy",
    "UserAgentConfig",
    "fetch_comments",
    "fetch_post",
    "resume_job",
    "retry_parser_failures",
    "run_job",
    "search_board",
    "search_integrated",
]

__version__ = "0.1.0"
