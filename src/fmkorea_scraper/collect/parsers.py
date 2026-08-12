"""BeautifulSoup parsers for list and search result pages."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from fmkorea_scraper.collect.models import BoardCandidate, CollectorFailure
from fmkorea_scraper.collect.urls import (
    FMKOREA_BASE_URL,
    extract_board_id_from_url,
    extract_document_from_url,
    safe_url_label,
)
from fmkorea_scraper.models.job import IntegratedSearchPage, PostCandidate, SearchPage

_DATE_PATTERNS = (
    ("%Y.%m.%d %H:%M", re.compile(r"\b\d{4}\.\d{1,2}\.\d{1,2}\s+\d{1,2}:\d{2}\b")),
    ("%Y-%m-%d %H:%M", re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}\b")),
    ("%Y.%m.%d", re.compile(r"\b\d{4}\.\d{1,2}\.\d{1,2}\b")),
    ("%Y-%m-%d", re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b")),
)


def parse_candidate_date(text: str) -> datetime | None:
    for fmt, pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(0), fmt)
        except ValueError:
            continue
    return None


def _text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _looks_ignored_row(row: Tag) -> bool:
    classes = " ".join(row.get("class", []))
    text = _text(row).lower()
    return any(marker in classes.lower() for marker in ("notice", "ad", "power")) or any(
        marker in text for marker in ("공지", "광고")
    )


def _has_next_page(soup: BeautifulSoup, current_page: int) -> bool:
    for link in soup.select("a[href*='page=']"):
        query = parse_qs(urlsplit(str(link.get("href", ""))).query)
        try:
            page = int(query.get("page", ["0"])[0])
        except ValueError:
            continue
        if page > current_page:
            return True
    return False


class BoardPageParser:
    def parse(
        self,
        html: str,
        *,
        board_id: str | None,
        base_url: str = FMKOREA_BASE_URL,
        request_url: str = FMKOREA_BASE_URL,
        page: int = 1,
    ) -> tuple[SearchPage, list[CollectorFailure]]:
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[PostCandidate] = []
        failures: list[CollectorFailure] = []
        rows = soup.select("div.bd table tbody tr") or soup.select("tbody tr")

        for row in rows:
            if _looks_ignored_row(row):
                continue
            link = row.select_one("a.hx[href]") or row.select_one("td.title a[href]") or row.select_one("a[href]")
            if link is None:
                continue
            try:
                candidate = self._candidate_from_link(link, row, board_id=board_id, base_url=base_url)
            except Exception as exc:
                failures.append(
                    CollectorFailure(
                        stage="board_row",
                        board_id=board_id,
                        safe_url_label=safe_url_label(request_url),
                        reason=exc.__class__.__name__,
                        retryable=False,
                    )
                )
                continue
            candidates.append(candidate)

        has_next = _has_next_page(soup, page)
        return SearchPage(board_id=board_id, page=page, candidates=candidates, has_next=has_next), failures

    def _candidate_from_link(self, link: Tag, row: Tag, *, board_id: str | None, base_url: str) -> PostCandidate:
        href = str(link["href"])
        absolute = urljoin(base_url, href)
        parsed_document = extract_document_from_url(absolute)
        if parsed_document is None:
            raise ValueError("missing document_srl")
        document_srl, document_id_raw = parsed_document
        resolved_board_id = extract_board_id_from_url(absolute) or board_id
        metadata = {
            "source": "board_page",
            "candidate_text": _text(row)[:1000],
        }
        return PostCandidate(
            board_id=resolved_board_id,
            document_srl=document_srl,
            document_id_raw=document_id_raw,
            url=absolute,
            candidate_title=_text(link) or None,
            candidate_created_at=parse_candidate_date(_text(row)),
            metadata=metadata,
        )


class IntegratedSearchParser:
    def parse(
        self,
        html: str,
        *,
        keyword: str,
        base_url: str = FMKOREA_BASE_URL,
        request_url: str = FMKOREA_BASE_URL,
        page: int = 1,
    ) -> tuple[IntegratedSearchPage, list[BoardCandidate], list[CollectorFailure]]:
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[PostCandidate] = []
        boards: list[BoardCandidate] = []
        failures: list[CollectorFailure] = []
        items = soup.select(".searchResult li, .search_result li, ul li") or soup.select("article, tr")

        for item in items:
            link = self._document_link(item)
            if link is None:
                continue
            try:
                candidate = self._candidate_from_item(link, item, base_url=base_url)
            except Exception as exc:
                failures.append(
                    CollectorFailure(
                        stage="integrated_item",
                        safe_url_label=safe_url_label(request_url),
                        reason=exc.__class__.__name__,
                        retryable=False,
                    )
                )
                continue
            candidates.append(candidate)
            board = self._board_candidate(item, candidate.board_id, base_url=base_url)
            if board is not None:
                boards.append(board)

        board_ids = [board.board_id for board in boards]
        has_next = _has_next_page(soup, page)
        page_model = IntegratedSearchPage(
            keyword=keyword,
            page=page,
            candidates=candidates,
            board_ids=board_ids,
            has_next=has_next,
        )
        return page_model, boards, failures

    def _document_link(self, item: Tag) -> Tag | None:
        for link in item.select("a[href]"):
            href = str(link.get("href", ""))
            if extract_document_from_url(href):
                return link
        return None

    def _candidate_from_item(self, link: Tag, item: Tag, *, base_url: str) -> PostCandidate:
        absolute = urljoin(base_url, str(link["href"]))
        parsed_document = extract_document_from_url(absolute)
        if parsed_document is None:
            raise ValueError("missing document_srl")
        document_srl, document_id_raw = parsed_document
        board_id = extract_board_id_from_url(absolute)
        return PostCandidate(
            board_id=board_id,
            document_srl=document_srl,
            document_id_raw=document_id_raw,
            url=absolute,
            candidate_title=_text(link) or None,
            candidate_created_at=parse_candidate_date(_text(item)),
            metadata={"source": "integrated_search", "candidate_text": _text(item)[:1000]},
        )

    def _board_candidate(self, item: Tag, fallback_board_id: str | None, *, base_url: str) -> BoardCandidate | None:
        board_link: Tag | None = None
        for link in item.select("a[href]"):
            href = str(link.get("href", ""))
            board_id = extract_board_id_from_url(href)
            if board_id and not extract_document_from_url(href):
                board_link = link
                break
        board_id = extract_board_id_from_url(str(board_link.get("href"))) if board_link else fallback_board_id
        if not board_id:
            return None
        board_url = urljoin(base_url, str(board_link.get("href"))) if board_link else None
        return BoardCandidate(board_id=board_id, board_name=_text(board_link) if board_link else None, board_url=board_url)
