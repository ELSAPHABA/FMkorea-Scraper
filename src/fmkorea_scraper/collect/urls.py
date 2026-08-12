"""URL builders and direct post URL normalization."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

from fmkorea_scraper.core.errors import ValidationFailure
from fmkorea_scraper.models.job import PostCandidate

FMKOREA_BASE_URL = "https://www.fmkorea.com"
INTEGRATED_MAX_PAGE = 1000
_DOCUMENT_RE = re.compile(r"(?<!\d)(\d{3,})(?!\d)")


def _require_page(page: int) -> int:
    if page < 1:
        raise ValueError("page must be >= 1")
    return page


def _document_from_text(value: str) -> tuple[int, str] | None:
    match = _DOCUMENT_RE.search(value)
    if not match:
        return None
    raw = match.group(1)
    return int(raw), raw


def safe_url_label(url: str) -> str:
    parts = urlsplit(urljoin(FMKOREA_BASE_URL, url))
    query = parse_qs(parts.query)
    page = query.get("page", [None])[0]
    suffix = f"?page={page}" if page else ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, suffix.removeprefix("?"), ""))


class DirectPostUrlNormalizer:
    def normalize(self, url: str) -> PostCandidate:
        absolute = urljoin(FMKOREA_BASE_URL, url)
        parts = urlsplit(absolute)
        if parts.netloc not in {"www.fmkorea.com", "fmkorea.com"}:
            raise ValidationFailure("unsupported FMKorea URL", details={"reason": "unsupported_host"})

        query = parse_qs(parts.query)
        raw_document = query.get("document_srl", [None])[0]
        parsed = _document_from_text(raw_document or parts.path)
        if not parsed:
            raise ValidationFailure("document_srl not found", details={"reason": "missing_document_srl"})

        document_srl, document_id_raw = parsed
        board_id = query.get("mid", [None])[0]
        normalized_url = urlunsplit((parts.scheme or "https", "www.fmkorea.com", parts.path, parts.query, ""))
        return PostCandidate(
            board_id=board_id,
            document_srl=document_srl,
            document_id_raw=document_id_raw,
            url=normalized_url,
        )


class BoardUrlBuilder:
    def build_list_url(self, board_id: str, page: int = 1, category_id: str | None = None) -> str:
        params: dict[str, str | int] = {"page": _require_page(page)}
        if category_id:
            params["category"] = category_id
        return f"{FMKOREA_BASE_URL}/{board_id}?{urlencode(params)}"

    def build_search_url(
        self,
        board_id: str,
        keyword: str,
        search_target: str,
        page: int = 1,
        category_id: str | None = None,
    ) -> str:
        params: dict[str, str | int] = {
            "mid": board_id,
            "search_target": search_target,
            "search_keyword": keyword,
            "page": _require_page(page),
        }
        if category_id:
            params["category"] = category_id
        return f"{FMKOREA_BASE_URL}/search.php?{urlencode(params)}"

    def safe_label(self, url: str) -> str:
        return safe_url_label(url)


class IntegratedSearchUrlBuilder:
    def clamp_page(self, page: int) -> int:
        return min(_require_page(page), INTEGRATED_MAX_PAGE)

    def build_search_url(
        self,
        keyword: str,
        search_target: str,
        page: int = 1,
        sort: str | None = None,
    ) -> str:
        params: dict[str, str | int] = {
            "act": "IS",
            "is_keyword": keyword,
            "where": "document",
            "search_target": search_target,
            "page": self.clamp_page(page),
        }
        if sort:
            params["sph_sort"] = sort
        return f"{FMKOREA_BASE_URL}/search.php?{urlencode(params)}"

    def safe_label(self, url: str) -> str:
        return safe_url_label(url)


def extract_document_from_url(url: str) -> tuple[int, str] | None:
    parts = urlsplit(urljoin(FMKOREA_BASE_URL, url))
    query = parse_qs(parts.query)
    raw_document = query.get("document_srl", [None])[0]
    return _document_from_text(raw_document or parts.path)


def extract_board_id_from_url(url: str) -> str | None:
    parts = urlsplit(urljoin(FMKOREA_BASE_URL, url))
    query = parse_qs(parts.query)
    if query.get("mid", [None])[0]:
        return query["mid"][0]
    path = parts.path.strip("/")
    return path.split("/", 1)[0] if path and not path.isdigit() else None
