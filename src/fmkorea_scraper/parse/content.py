"""Post body content parser."""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

from fmkorea_scraper.models.content import AttachmentBlock, BodyContent, LinkBlock, TextBlock, UnknownEmbedBlock
from fmkorea_scraper.models.media import Attachment
from fmkorea_scraper.parse.media import MediaBlockParser, MediaDeduper, normalize_url
from fmkorea_scraper.parse.models import ParserOptions
from fmkorea_scraper.parse.warnings import ParseWarningCollector


class TextNormalizer:
    ignored_parent_names = {"script", "style", "video", "source", "iframe"}

    def normalize(self, text: str) -> str:
        return " ".join(text.split())

    def should_skip(self, node: NavigableString) -> bool:
        parent = node.parent
        if not isinstance(parent, Tag):
            return True
        if parent.name in self.ignored_parent_names or parent.find_parent(["a", "video", "iframe"]):
            return True
        text = self.normalize(str(node))
        return not text or text in {"BeforeDocument", "AfterDocument", "__LAZY__"} or text.startswith("serverLog:")


class ContentParser:
    def __init__(self, *, media_parser: MediaBlockParser | None = None) -> None:
        self.media_parser = media_parser or MediaBlockParser()
        self.text = TextNormalizer()

    def parse(
        self,
        soup: BeautifulSoup,
        attachments: list[Attachment],
        warnings: ParseWarningCollector,
        *,
        options: ParserOptions | None = None,
    ) -> BodyContent:
        container = self._container(soup)
        if container is None:
            warnings.add(code="missing_content_container", stage="content", selector=".xe_content", reason="content container missing")
            return BodyContent()

        blocks = []
        order = 0
        deduper = MediaDeduper()
        attachments_by_file = {attachment.file_srl: attachment for attachment in attachments if attachment.file_srl}
        emitted_attachments: set[str] = set()

        for node in container.descendants:
            if options and options.max_content_blocks and len(blocks) >= options.max_content_blocks:
                warnings.add(code="max_content_blocks_exceeded", stage="content", reason="content block guardrail exceeded", order=order)
                break
            try:
                block = None
                if isinstance(node, NavigableString) and not self.text.should_skip(node):
                    text = self.text.normalize(str(node))
                    block = TextBlock(order=order, text=text)
                elif isinstance(node, Tag):
                    block = self._tag_block(node, order, attachments_by_file, deduper, emitted_attachments)
                if block is not None:
                    blocks.append(block)
                    order += 1
            except Exception as exc:
                warnings.add(code="content_block_parse_failed", stage="content", reason=exc.__class__.__name__, order=order)

        return BodyContent(text=self._content_text(blocks), blocks=blocks)

    def _container(self, soup: BeautifulSoup) -> Tag | None:
        return soup.select_one("#bd_capture .rd_body article > .xe_content") or soup.select_one("#bd_capture .rd_body .xe_content")

    def _tag_block(
        self,
        node: Tag,
        order: int,
        attachments_by_file: dict[str, Attachment],
        deduper: MediaDeduper,
        emitted_attachments: set[str],
    ):
        if node.name == "img":
            block = self.media_parser.parse_image(node, order=order, attachments_by_file_srl=attachments_by_file)
            if block and deduper.is_new("image", file_srl=block.file_srl, url=block.url):
                return block
        if node.name == "video":
            block = self.media_parser.parse_video(node, order=order)
            if block and deduper.is_new("fmk_video", file_srl=block.file_srl, url=block.video_url):
                return block
        if node.name == "iframe":
            src = node.get("src")
            block = self.media_parser.parse_youtube(src or "", order=order) or self.media_parser.parse_x(src or "", order=order)
            if block and deduper.is_new(block.type, url=block.url):
                return block
            return UnknownEmbedBlock(order=order, provider="iframe", url=normalize_url(src, self.media_parser.base_url))
        if node.name == "a":
            href = normalize_url(node.get("href"), self.media_parser.base_url)
            if not href:
                return None
            if "highslide" in (node.get("class") or []):
                return None
            if node.get("data-href"):
                file_srl = self._file_srl(href)
                attachment = attachments_by_file.get(file_srl or "")
                if attachment and attachment.url not in emitted_attachments:
                    emitted_attachments.add(attachment.url)
                    return AttachmentBlock(order=order, attachment=attachment)
            dedicated = self.media_parser.parse_youtube(href, order=order, text=node.get_text(" ", strip=True))
            dedicated = dedicated or self.media_parser.parse_x(href, order=order, text=node.get_text(" ", strip=True))
            if dedicated and deduper.is_new(dedicated.type, url=dedicated.url):
                return dedicated
            return LinkBlock(order=order, url=href, text=node.get_text(" ", strip=True) or None)
        return None

    def _content_text(self, blocks: list) -> str:
        parts = []
        for block in blocks:
            if isinstance(block, TextBlock):
                parts.append(block.text)
            elif isinstance(block, LinkBlock) and block.text:
                parts.append(block.text)
        return "\n".join(parts)

    def _file_srl(self, url: str) -> str | None:
        from urllib.parse import parse_qs, urlsplit

        values = parse_qs(urlsplit(url).query).get("file_srl")
        return values[0] if values else None
