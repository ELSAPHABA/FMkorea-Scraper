"""Comment parser."""

from __future__ import annotations

import re
from datetime import datetime

from fmkorea_scraper.dom import Node, attr, classes, first, has_ancestor_class, text
from fmkorea_scraper.models.comment import AuthorInfo, Comment, ReactionInfo
from fmkorea_scraper.parse.warnings import ParseWarningCollector

COMMENT_RE = re.compile(r"comment_(\d+)")
MEMBER_RE = re.compile(r"member_(\d+)")


class CommentParser:
    def parse(
        self,
        page: Node,
        warnings: ParseWarningCollector,
        *,
        start_order: int = 0,
        max_comments: int | None = None,
    ) -> tuple[list[Comment], int]:
        comments: list[Comment] = []
        order = start_order
        for item in page.css(".fdb_lst_ul > li"):
            if max_comments is not None and len(comments) >= max_comments:
                warnings.add(code="max_comments_exceeded", stage="comments", reason="comment guardrail exceeded", order=order)
                break
            try:
                comments.append(self._parse_item(item, order))
            except Exception as exc:
                warnings.add(code="comment_parse_failed", stage="comments", reason=exc.__class__.__name__, order=order)
            order += 1
        return comments, order

    def _parse_item(self, item: Node, order: int) -> Comment:
        dom_id = attr(item, "id")
        comment_srl = self._comment_srl(dom_id)
        item_classes = classes(item)
        best = "comment_best" in item_classes or self._has_best_badge(item)
        up, down = self._reactions(item)
        return Comment(
            comment_srl=comment_srl,
            comment_id_raw=str(comment_srl) if comment_srl is not None else None,
            source_dom_id=dom_id,
            source_order=order,
            parent_comment_srl=self._parent_srl(item),
            depth=1 if self._parent_srl(item) is not None or "reply" in item_classes else 0,
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

    def _parent_srl(self, item: Node) -> int | None:
        raw = attr(item, "data-parent") or attr(item, "data-parent-comment-srl")
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def _has_best_badge(self, item: Node) -> bool:
        return any(text(node).upper() == "BEST" for node in item.css(".icon-hit"))

    def _author(self, item: Node) -> AuthorInfo:
        node = first(item, ".meta .member_plate, .member_plate")
        if node is None:
            return AuthorInfo()
        member = MEMBER_RE.search(" ".join(classes(node)))
        return AuthorInfo(nickname=text(node), member_srl=member.group(1) if member else None)

    def _date_text(self, item: Node) -> str | None:
        node = first(item, ".meta .date, .date")
        return text(node) or None

    def _created_at(self, item: Node) -> datetime | None:
        raw = self._date_text(item)
        if not raw:
            return None
        match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})\s+(\d{1,2}):(\d{1,2})", raw)
        if not match:
            return None
        year, month, day, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute)

    def _content(self, item: Node) -> str:
        node = first(item, ".xe_content, .comment_content, .comment-content")
        if node is None:
            return ""
        body_text = " ".join(
            text(text_node)
            for text_node in node.xpath(".//text()")
            if not has_ancestor_class(text_node, "imagecon-buy-icon") and text(text_node)
        )
        image_alts = [value for img in node.css("img[alt]") if (value := (attr(img, "alt") or "").strip())]
        parts = [body_text, *image_alts]
        return " ".join(part for part in parts if part)

    def _reactions(self, item: Node) -> tuple[int, int]:
        up_node = first(item, 'a[title="추천"] .voted_count, .voted_count')
        down_node = first(item, 'a[title="비추천"] .blamed_count, .blamed_count')
        return self._int_text(up_node), self._int_text(down_node)

    def _int_text(self, node: Node | None) -> int:
        if node is None:
            return 0
        match = re.search(r"([\d,]+)", text(node))
        return int(match.group(1).replace(",", "")) if match else 0
