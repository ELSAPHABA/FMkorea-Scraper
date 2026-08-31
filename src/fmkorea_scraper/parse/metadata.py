"""Detail metadata parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

from fmkorea_scraper.core.errors import ParseFailureError
from fmkorea_scraper.dom import Node, attr, classes, first, text
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
    def parse(self, page: Node, context: DetailParseContext, warnings: ParseWarningCollector) -> ParsedMetadata:
        root = first(page, "#bd_capture")
        if root is None:
            root = page
            warnings.add(code="missing_detail_root", stage="metadata", selector="#bd_capture", reason="detail root missing")

        canonical_url = self._canonical_url(page, context)
        document_srl = self._document_srl(canonical_url, context)
        document_id_raw = str(document_srl or context.document_id_hint or "")
        title = self._title(root)
        if not document_id_raw or not canonical_url or not title:
            raise ParseFailureError("required detail metadata missing", details={"stage": "post", "reason": "required_metadata"})

        return ParsedMetadata(
            board_id=self._board_id(canonical_url, context),
            board_name=self._board_name(page),
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

    def _canonical_url(self, page: Node, context: DetailParseContext) -> str:
        node = first(page, 'link[rel="canonical"][href], .document_address a.a[href]')
        return normalize_url(attr(node, "href") or context.source_url, context.base_url) or context.source_url

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

    def _board_name(self, page: Node) -> str | None:
        node = first(page, ".bd_name, .board_name, h1 a")
        return text(node) or None

    def _title(self, root: Node) -> str:
        node = first(root, ".rd_hd h1 .np_18px_span") or first(root, ".rd_hd h1")
        return text(node)

    def _author(self, root: Node) -> AuthorInfo:
        node = first(root, ".rd_hd .member_plate")
        if node is None:
            return AuthorInfo()
        member = MEMBER_RE.search(" ".join(classes(node)))
        level_img = first(node, "img.level")
        return AuthorInfo(
            nickname=text(node),
            member_srl=member.group(1) if member else None,
            level=(attr(level_img, "alt") or attr(level_img, "title")) if level_img else None,
            profile_url=normalize_url(attr(node, "href"), "https://www.fmkorea.com") if node.tag == "a" else None,
        )

    def _created_at_raw(self, root: Node) -> str | None:
        node = first(root, ".date, .regdate, .rd_hd .btm_area")
        return text(node) or None

    def _created_at(self, root: Node) -> datetime | None:
        raw = self._created_at_raw(root)
        if not raw:
            return None
        match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})\s+(\d{1,2}):(\d{1,2})", raw)
        if not match:
            return None
        year, month, day, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute)

    def _counter(self, root: Node, label: str) -> int | None:
        for span in root.css(".rd_hd .btm_area .side.fr span, .btm_area span, span"):
            value = text(span)
            if label in value:
                match = re.search(r"([\d,]+)", value)
                return int(match.group(1).replace(",", "")) if match else None
        return None

    def _category(self, root: Node) -> CategoryInfo | None:
        node = first(root, 'a.category[href*="category="]')
        if node is None:
            return None
        href = normalize_url(attr(node, "href"), "https://www.fmkorea.com")
        category_id = None
        if href:
            values = parse_qs(urlsplit(href).query).get("category")
            category_id = values[0] if values else None
        return CategoryInfo(category_id=category_id, name=text(node) or None, url=href)
