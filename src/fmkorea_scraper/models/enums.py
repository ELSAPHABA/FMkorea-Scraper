"""Shared enum contracts."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class JobType(StrEnum):
    DIRECT_POST = "direct_post"
    BOARD_LIST = "board_list"
    BOARD_SEARCH = "board_search"
    INTEGRATED_SEARCH = "integrated_search"
    DEEP_SEARCH = "deep_search"
    NO_KEYWORD_RANGE = "no_keyword_range"
    REALTIME_KEYWORD = "realtime_keyword"
    REALTIME_ALL = "realtime_all"
    PARSER_FAILURE_RETRY = "parser_failure_retry"


class ContentBlockType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    FMK_VIDEO = "fmk_video"
    YOUTUBE = "youtube"
    X = "x"
    LINK = "link"
    ATTACHMENT = "attachment"
    UNKNOWN_EMBED = "unknown_embed"


class CommentMode(StrEnum):
    NONE = "none"
    ALL = "all"
    BEST_ONLY = "best_only"


class MediaMode(StrEnum):
    URL_ONLY = "url_only"
    DOWNLOAD = "download"


class StorageMode(StrEnum):
    LOCAL = "local"
    S3_COMPATIBLE = "s3_compatible"


class CheckpointMode(StrEnum):
    LOCAL = "local"
    POSTGRES = "postgres"


class CheckpointStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"


class StopReason(StrEnum):
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    MANUAL_STOP = "manual_stop"
    ERROR = "error"
    TIMEOUT = "timeout"
    LEASE_EXPIRED = "lease_expired"


class ResponseKind(StrEnum):
    OK = "ok"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"


class JobReportStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
