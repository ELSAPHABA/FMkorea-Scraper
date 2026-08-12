"""Comment parser."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from fmkorea_scraper.models.comment import AuthorInfo, Comment, ReactionInfo
from fmkorea_scraper.parse.warnings import ParseWarningCollector

COMMENT_RE = re.compile(r"comment_(\d+)")
MEMBER_RE = re.compile(r"member_(\d+)")


class CommentParser:
    def parse(
        self,
        soup: BeautifulSoup,
        warnings: ParseWarningCollector,
        *,
        start_order: int = 0,
        max_comments: int | None = None,
    ) -> tuple[list[Comment], int]:
        comments: list[Comment] = []
        order = start_order
        for item in soup.select(".fdb_lst_ul > li"):
            if max_comments is not None and len(comments) >= max_comments:
                warnings.add(code="max_comments_exceeded", stage="comments", reason="comment guardrail exceeded", order=order)
                break
            try:
                comments.append(self._parse_item(item, order))
            except Exception as exc:
                warnings.add(code="comment_parse_failed", stage="comments", reason=exc.__class__.__name__, order=order)
            order += 1
        return comments, order

    def _parse_item(self, item: Tag, order: int) -> Comment:
        dom_id = item.get("id")
        comment_srl = self._comment_srl(dom_id)
        classes = set(item.get("class") or [])
        best = "comment_best" in classes or self._has_best_badge(item)
        up, down = self._reactions(item)
        return Comment(
            comment_srl=comment_srl,
            comment_id_raw=str(comment_srl) if comment_srl is not None else None,
            source_dom_id=dom_id,
            source_order=order,
            parent_comment_srl=self._parent_srl(item),
            depth=1 if self._parent_srl(item) is not None or "reply" in classes else 0,
            is_best=best,
            badges=["BEST"] if best else [],
            author=self._author(item),
            created_at=self._created_at(item),
            created_at_raw=self._date_text(item),
            content=self._content(item),
            reactions=ReactionInfo(up_count=up, down_count=down),
        )

    def _comment_srl(self, dom_id: str | None) -> int | None:
        match = COMMENT_RE.search(dom_id or "")
        return int(match.group(1)) if match else None

    def _parent_srl(self, item: Tag) -> int | None:
        raw = item.get("data-parent") or item.get("data-parent-comment-srl")
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def _has_best_badge(self, item: Tag) -> bool:
        return any(node.get_text(" ", strip=True).upper() == "BEST" for node in item.select(".icon-hit"))

    def _author(self, item: Tag) -> AuthorInfo:
        node = item.select_one(".meta .member_plate, .member_plate")
        if node is None:
            return AuthorInfo()
        member = MEMBER_RE.search(" ".join(node.get("class") or []))
        return AuthorInfo(nickname=node.get_text(" ", strip=True), member_srl=member.group(1) if member else None)

    def _date_text(self, item: Tag) -> str | None:
        node = item.select_one(".meta .date, .date")
        return node.get_text(" ", strip=True) if node else None

    def _created_at(self, item: Tag) -> datetime | None:
        raw = self._date_text(item)
        if not raw:
            return None
        match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})\s+(\d{1,2}):(\d{1,2})", raw)
        if not match:
            return None
        year, month, day, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute)

    def _content(self, item: Tag) -> str:
        node = item.select_one(".xe_content, .comment_content, .comment-content")
        return node.get_text(" ", strip=True) if node else ""

    def _reactions(self, item: Tag) -> tuple[int, int]:
        up_node = item.select_one('a[title="추천"] .voted_count, .voted_count')
        down_node = item.select_one('a[title="비추천"] .blamed_count, .blamed_count')
        return self._int_text(up_node), self._int_text(down_node)

    def _int_text(self, node: Tag | None) -> int:
        if node is None:
            return 0
        match = re.search(r"([\d,]+)", node.get_text(" ", strip=True))
        return int(match.group(1).replace(",", "")) if match else 0
