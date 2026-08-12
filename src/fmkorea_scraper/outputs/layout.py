"""Output run path and object-key layout."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from fmkorea_scraper.models.enums import ContentBlockType
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.outputs.errors import PathTraversalError, safe_error_details

_UNSAFE_SEGMENT_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_RESERVED_SEGMENTS = {"", ".", ".."}


def sanitize_path_segment(value: object, fallback: str = "unknown", *, max_length: int = 160) -> str:
    text = str(value or "").strip().strip(". ")
    text = _UNSAFE_SEGMENT_CHARS.sub("_", text)
    text = text.strip("._ ")
    if text in _RESERVED_SEGMENTS:
        text = fallback
    return text[:max_length] or fallback


def ensure_under_base(base: Path, target: Path) -> Path:
    base_resolved = base.resolve(strict=False)
    target_resolved = target.resolve(strict=False)
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise PathTraversalError(
            "output path escapes base directory",
            details=safe_error_details(base=str(base_resolved), target=str(target_resolved)),
        ) from exc
    return target_resolved


def filename_from_url(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    name = unquote(Path(parsed.path).name)
    return sanitize_path_segment(name, fallback=fallback, max_length=220)


class OutputRunLayout:
    """Derive local paths and S3 keys for one job run."""

    def __init__(
        self,
        job_id: str,
        run_id: str,
        *,
        base_output_path: str | Path | None = None,
        s3_prefix: str | None = None,
    ) -> None:
        self.job_id = sanitize_path_segment(job_id, fallback="job")
        self.run_id = sanitize_path_segment(run_id, fallback="run")
        self.base_path = Path(base_output_path) if base_output_path is not None else Path.cwd()
        self.base_path = self.base_path.resolve(strict=False)
        self.s3_prefix = self._sanitize_prefix(s3_prefix)
        self.run_relative_parts = ("outputs", self.job_id, self.run_id)

    @property
    def run_dir(self) -> Path:
        return self.path_for(*self.run_relative_parts)

    @property
    def posts_path(self) -> Path:
        return self.path_for(*self.run_relative_parts, "posts.jsonl")

    @property
    def failures_path(self) -> Path:
        return self.path_for(*self.run_relative_parts, "failures.jsonl")

    @property
    def report_path(self) -> Path:
        return self.path_for(*self.run_relative_parts, "report.json")

    @property
    def checkpoint_path(self) -> Path:
        return self.path_for("Checkpoint.json")

    @property
    def posts_key(self) -> str:
        return self.key_for(*self.run_relative_parts, "posts.jsonl")

    @property
    def failures_key(self) -> str:
        return self.key_for(*self.run_relative_parts, "failures.jsonl")

    @property
    def report_key(self) -> str:
        return self.key_for(*self.run_relative_parts, "report.json")

    def path_for(self, *parts: object) -> Path:
        target = self.base_path.joinpath(*(sanitize_path_segment(part) for part in parts))
        return ensure_under_base(self.base_path, target)

    def key_for(self, *parts: object) -> str:
        safe_parts = [sanitize_path_segment(part) for part in parts]
        key = PurePosixPath(*safe_parts).as_posix()
        if self.s3_prefix:
            return f"{self.s3_prefix}/{key}"
        return key

    def media_path(self, item: MediaItem, *, board_id: str | None = None, document_id_raw: str | None = None) -> Path:
        return self.path_for(*self._media_parts(item, board_id=board_id, document_id_raw=document_id_raw))

    def media_key(self, item: MediaItem, *, board_id: str | None = None, document_id_raw: str | None = None) -> str:
        return self.key_for(*self._media_parts(item, board_id=board_id, document_id_raw=document_id_raw))

    def relative_object_key(self, path: Path) -> str:
        safe_path = ensure_under_base(self.base_path, path)
        return PurePosixPath(*safe_path.relative_to(self.base_path).parts).as_posix()

    def _media_parts(
        self,
        item: MediaItem,
        *,
        board_id: str | None,
        document_id_raw: str | None,
    ) -> tuple[str, ...]:
        metadata = item.metadata or {}
        safe_board = board_id or metadata.get("board_id") or "unknown_board"
        safe_doc = document_id_raw or metadata.get("document_id_raw") or item.media_id or "unknown_post"
        media_type = item.media_type.value if isinstance(item.media_type, ContentBlockType) else str(item.media_type)
        fallback = f"{item.source_block_order}-{media_type}.bin"
        filename = f"{item.source_block_order}-{filename_from_url(item.url, fallback)}"
        return (*self.run_relative_parts, "media", safe_board, safe_doc, media_type, filename)

    @staticmethod
    def _sanitize_prefix(prefix: str | None) -> str | None:
        if not prefix:
            return None
        parts = [sanitize_path_segment(part) for part in prefix.replace("\\", "/").split("/") if part]
        return PurePosixPath(*parts).as_posix() if parts else None


__all__ = ["OutputRunLayout", "ensure_under_base", "filename_from_url", "sanitize_path_segment"]
