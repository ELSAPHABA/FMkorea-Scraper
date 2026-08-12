"""Post detail parser service."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from bs4 import Tag

from fmkorea_scraper.models.content import FmkVideoBlock, ImageBlock, XBlock, YouTubeBlock
from fmkorea_scraper.models.comment import Comment
from fmkorea_scraper.models.enums import ContentBlockType
from fmkorea_scraper.models.job import PostCandidate, PostRequest
from fmkorea_scraper.models.media import MediaItem
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.parse.comments import CommentParser
from fmkorea_scraper.parse.content import ContentParser
from fmkorea_scraper.parse.media import AttachmentParser
from fmkorea_scraper.parse.metadata import MetadataParser
from fmkorea_scraper.parse.models import DetailParseContext, ParserOptions
from fmkorea_scraper.parse.warnings import ParseWarningCollector


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise TypeError("HTTP response must provide text")


class PostDetailService:
    def __init__(
        self,
        http: Any | None = None,
        *,
        options: ParserOptions | None = None,
        metadata_parser: MetadataParser | None = None,
        attachment_parser: AttachmentParser | None = None,
        content_parser: ContentParser | None = None,
        comment_parser: CommentParser | None = None,
    ) -> None:
        self.http = http
        self.options = options or ParserOptions()
        self.metadata_parser = metadata_parser or MetadataParser()
        self.attachment_parser = attachment_parser or AttachmentParser()
        self.content_parser = content_parser or ContentParser()
        self.comment_parser = comment_parser or CommentParser()

    async def parse(self, candidate_or_request: PostCandidate | PostRequest) -> PostResult:
        if self.http is None:
            raise TypeError("http client is required for parse()")
        url = self._source_url(candidate_or_request)
        html = _response_text(await self.http.get(url))
        post = self.parse_html(html, candidate_or_request)
        if self.options.max_comment_pages is None:
            return post

        context = self._context(candidate_or_request)
        soup = BeautifulSoup(html, "html.parser")
        comments, warnings = await self._fetch_extra_comments(soup, context, post.comments)
        if not comments and not warnings:
            return post

        metadata = dict(post.metadata)
        if warnings:
            metadata["parse_warnings"] = [*metadata.get("parse_warnings", []), *warnings]
        return post.model_copy(update={"comments": self._dedupe_comments([*post.comments, *comments]), "metadata": metadata})

    def parse_html(self, html: str, candidate_or_request: PostCandidate | PostRequest) -> PostResult:
        context = self._context(candidate_or_request)
        warnings = ParseWarningCollector()
        soup = BeautifulSoup(html, "html.parser")

        metadata = self.metadata_parser.parse(soup, context, warnings)
        attachments = self.attachment_parser.parse(soup, base_url=context.base_url)
        content = self.content_parser.parse(soup, attachments, warnings, options=self.options)
        comments, _ = self.comment_parser.parse(soup, warnings, max_comments=self.options.max_comments)
        media = self._media_summary(content.blocks)
        post_metadata = {}
        if len(warnings):
            post_metadata["parse_warnings"] = warnings.to_metadata()

        return PostResult(
            board_id=metadata.board_id,
            board_name=metadata.board_name,
            document_srl=metadata.document_srl,
            document_id_raw=metadata.document_id_raw,
            canonical_url=metadata.canonical_url,
            category=metadata.category,
            title=metadata.title,
            author=metadata.author,
            created_at=metadata.created_at,
            created_at_raw=metadata.created_at_raw,
            views=metadata.views,
            reactions=metadata.reactions,
            comment_count=metadata.comment_count,
            content=content,
            attachments=attachments,
            media=media,
            comments=comments,
            metadata=post_metadata,
        )

    def _source_url(self, candidate_or_request: PostCandidate | PostRequest) -> str:
        return candidate_or_request.url

    def _context(self, candidate_or_request: PostCandidate | PostRequest) -> DetailParseContext:
        source_url = self._source_url(candidate_or_request)
        parts = urlsplit(source_url)
        base_url = urlunsplit((parts.scheme or "https", parts.netloc or "www.fmkorea.com", "", "", ""))
        return DetailParseContext(
            source_url=source_url,
            base_url=base_url,
            candidate=candidate_or_request if isinstance(candidate_or_request, PostCandidate) else None,
            post_request=candidate_or_request if isinstance(candidate_or_request, PostRequest) else None,
            board_id_hint=candidate_or_request.board_id,
            document_id_hint=candidate_or_request.document_id_raw or (
                str(candidate_or_request.document_srl) if candidate_or_request.document_srl is not None else None
            ),
        )

    def _media_summary(self, blocks: list) -> list[MediaItem]:
        items: list[MediaItem] = []
        for block in blocks:
            if isinstance(block, ImageBlock):
                items.append(
                    MediaItem(
                        media_id=block.file_srl,
                        media_type=ContentBlockType.IMAGE,
                        source_block_order=block.order,
                        url=block.url,
                        file_srl=block.file_srl,
                    )
                )
            elif isinstance(block, FmkVideoBlock) and block.video_url:
                items.append(
                    MediaItem(
                        media_id=block.file_srl,
                        media_type=ContentBlockType.FMK_VIDEO,
                        source_block_order=block.order,
                        url=block.video_url,
                        description=block.description,
                        file_srl=block.file_srl,
                    )
                )
            elif isinstance(block, YouTubeBlock):
                items.append(
                    MediaItem(
                        media_id=block.video_id,
                        media_type=ContentBlockType.YOUTUBE,
                        source_block_order=block.order,
                        url=block.url,
                        provider="youtube",
                        embed_url=block.embed_url,
                    )
                )
            elif isinstance(block, XBlock):
                items.append(
                    MediaItem(
                        media_id=block.tweet_id or block.status_id,
                        media_type=ContentBlockType.X,
                        source_block_order=block.order,
                        url=block.url,
                        provider="x",
                        embed_url=block.embed_url,
                    )
                )
        return items

    async def _fetch_extra_comments(
        self,
        soup: BeautifulSoup,
        context: DetailParseContext,
        existing: list[Comment],
    ) -> tuple[list[Comment], list[dict]]:
        warnings = ParseWarningCollector()
        comments: list[Comment] = []
        order = len(existing)
        for page, url in enumerate(self._comment_page_urls(soup, context), start=1):
            if self.options.max_comment_pages is not None and page > self.options.max_comment_pages:
                warnings.add(
                    code="max_comment_pages_exceeded",
                    stage="comments",
                    reason="comment page guardrail exceeded",
                )
                break
            remaining = None if self.options.max_comments is None else self.options.max_comments - len(existing) - len(comments)
            if remaining is not None and remaining <= 0:
                warnings.add(code="max_comments_exceeded", stage="comments", reason="comment guardrail exceeded", order=order)
                break
            page_soup = BeautifulSoup(_response_text(await self.http.get(url)), "html.parser")
            parsed, order = self.comment_parser.parse(page_soup, warnings, start_order=order, max_comments=remaining)
            comments.extend(parsed)
        return comments, warnings.to_metadata()

    def _comment_page_urls(self, soup: BeautifulSoup, context: DetailParseContext) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        current = self._without_fragment(context.source_url)
        for link in soup.select("a[href]"):
            if not self._is_comment_page_link(link):
                continue
            url = self._without_fragment(urljoin(context.source_url, str(link.get("href"))))
            if url == current or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _is_comment_page_link(self, link: Tag) -> bool:
        href = str(link.get("href") or "")
        if href.startswith("#"):
            return False
        text = " ".join([href, " ".join(link.get("class") or []), link.get_text(" ", strip=True)]).lower()
        return any(marker in text for marker in ("cpage", "comment_page", "commentpage", "comment"))

    def _without_fragment(self, url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))

    def _dedupe_comments(self, comments: list[Comment]) -> list[Comment]:
        deduped: list[Comment] = []
        seen: set[str] = set()
        for comment in comments:
            key = str(comment.comment_srl) if comment.comment_srl is not None else comment.source_dom_id
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(comment)
        return deduped
