"""Detail metadata parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, Tag

from fmkorea_scraper.core.errors import ParseFailureError
from fmkorea_scraper.models.comment import AuthorInfo, ReactionInfo
from fmkorea_scraper.models.post import CategoryInfo
from fmkorea_scraper.parse.media import normalize_url
from fmkorea_scraper.parse.models import DetailParseContext
from fmkorea_scraper.parse.warnings import ParseWarningCollector


DOC_RE = re.compile(r"/(?:best/)?(\d+)(?:$|[/?#])")
MEMBER_RE = re.compile(r"member_(\d+)")


@dataclass(frozen=True)
class ParsedMetadata:
    board_id: str | None
    board_name: str | None
    document_srl: int | None
    document_id_raw: str
    canonical_url: str
    category: CategoryInfo | None
    title: str
    author: AuthorInfo
    created_at: datetime | None
    created_at_raw: str | None
    views: int | None
    reactions: ReactionInfo
    comment_count: int | None


class MetadataParser:
    def parse(self, soup: BeautifulSoup, context: DetailParseContext, warnings: ParseWarningCollector) -> ParsedMetadata:
        root = soup.select_one("#bd_capture")
        if root is None:
            root = soup
            warnings.add(code="missing_detail_root", stage="metadata", selector="#bd_capture", reason="detail root missing")

        canonical_url = self._canonical_url(soup, context)
        document_srl = self._document_srl(canonical_url, context)
        document_id_raw = str(document_srl or context.document_id_hint or "")
        title = self._title(root)
        if not document_id_raw or not canonical_url or not title:
            raise ParseFailureError("required detail metadata missing", details={"stage": "post", "reason": "required_metadata"})

        return ParsedMetadata(
            board_id=self._board_id(canonical_url, context),
            board_name=self._board_name(soup),
            document_srl=document_srl,
            document_id_raw=document_id_raw,
            canonical_url=canonical_url,
            category=self._category(root),
            title=title,
            author=self._author(root),
            created_at=self._created_at(root),
            created_at_raw=self._created_at_raw(root),
            views=self._counter(root, "조회 수"),
            reactions=ReactionInfo(up_count=self._counter(root, "추천 수") or 0),
            comment_count=self._counter(root, "댓글"),
        )

    def _canonical_url(self, soup: BeautifulSoup, context: DetailParseContext) -> str:
        node = soup.select_one('link[rel="canonical"][href], .document_address a.a[href]')
        return normalize_url(node.get("href") if node else context.source_url, context.base_url) or context.source_url

    def _document_srl(self, url: str, context: DetailParseContext) -> int | None:
        query_value = parse_qs(urlsplit(url).query).get("document_srl")
        raw = query_value[0] if query_value else None
        if raw is None:
            match = DOC_RE.search(urlsplit(url).path + "/")
            raw = match.group(1) if match else context.document_id_hint
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def _board_id(self, url: str, context: DetailParseContext) -> str | None:
        query_value = parse_qs(urlsplit(url).query).get("mid")
        return query_value[0] if query_value else context.board_id_hint

    def _board_name(self, soup: BeautifulSoup) -> str | None:
        node = soup.select_one(".bd_name, .board_name, h1 a")
        return node.get_text(" ", strip=True) if node else None

    def _title(self, root: Tag) -> str:
        node = root.select_one(".rd_hd h1 .np_18px_span") or root.select_one(".rd_hd h1")
        return node.get_text(" ", strip=True) if node else ""

    def _author(self, root: Tag) -> AuthorInfo:
        node = root.select_one(".rd_hd .member_plate")
        if node is None:
            return AuthorInfo()
        classes = " ".join(node.get("class") or [])
        member = MEMBER_RE.search(classes)
        level_img = node.select_one("img.level")
        return AuthorInfo(
            nickname=node.get_text(" ", strip=True),
            member_srl=member.group(1) if member else None,
            level=level_img.get("alt") or level_img.get("title") if level_img else None,
            profile_url=normalize_url(node.get("href"), "https://www.fmkorea.com") if node.name == "a" else None,
        )

    def _created_at_raw(self, root: Tag) -> str | None:
        node = root.select_one(".date, .regdate, .rd_hd .btm_area")
        return node.get_text(" ", strip=True) if node else None

    def _created_at(self, root: Tag) -> datetime | None:
        raw = self._created_at_raw(root)
        if not raw:
            return None
        match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})\s+(\d{1,2}):(\d{1,2})", raw)
        if not match:
            return None
        year, month, day, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute)

    def _counter(self, root: Tag, label: str) -> int | None:
        for span in root.select(".rd_hd .btm_area .side.fr span, .btm_area span, span"):
            text = span.get_text(" ", strip=True)
            if label in text:
                match = re.search(r"([\d,]+)", text)
                return int(match.group(1).replace(",", "")) if match else None
        return None

    def _category(self, root: Tag) -> CategoryInfo | None:
        node = root.select_one('a.category[href*="category="]')
        if node is None:
            return None
        href = normalize_url(node.get("href"), "https://www.fmkorea.com")
        category_id = None
        if href:
            values = parse_qs(urlsplit(href).query).get("category")
            category_id = values[0] if values else None
        return CategoryInfo(category_id=category_id, name=node.get_text(" ", strip=True) or None, url=href)
