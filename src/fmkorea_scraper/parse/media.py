"""Media and attachment parsers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from fmkorea_scraper.dom import Node, attr, classes, find_ancestor, first, text
from fmkorea_scraper.models.content import FmkVideoBlock, ImageBlock, XBlock, YouTubeBlock
from fmkorea_scraper.models.media import Attachment


YOUTUBE_RE = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/)([A-Za-z0-9_-]+)")
X_RE = re.compile(r"(?:x|twitter)\.com/([^/\s]+)/status/(\d+)")


def normalize_url(url: str | None, base_url: str = "https://www.fmkorea.com") -> str | None:
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    return urljoin(base_url, url)


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


class AttachmentParser:
    def parse(self, root: Node, *, base_url: str = "https://www.fmkorea.com") -> list[Attachment]:
        attachments: list[Attachment] = []
        for link in root.css(".rd_file a[data-href]"):
            href = normalize_url(attr(link, "data-href") or attr(link, "href"), base_url)
            if not href:
                continue
            query = parse_qs(urlsplit(href).query)
            file_srl = _first(query, "file_srl")
            attachments.append(
                Attachment(
                    file_name=text(link) or attr(link, "title"),
                    url=href,
                    size_text=attr(link, "title"),
                    file_srl=file_srl,
                    sid=_first(query, "sid"),
                    mid=_first(query, "mid"),
                    download_text=attr(link, "title"),
                )
            )
        return attachments

    @staticmethod
    def by_file_srl(attachments: list[Attachment]) -> dict[str, Attachment]:
        return {attachment.file_srl: attachment for attachment in attachments if attachment.file_srl}


class MediaDeduper:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def is_new(self, media_type: str, *, file_srl: str | None = None, url: str | None = None) -> bool:
        key_value = file_srl or url
        if not key_value:
            return True
        key = (media_type, key_value)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class MediaBlockParser:
    def __init__(self, *, base_url: str = "https://www.fmkorea.com") -> None:
        self.base_url = base_url

    def parse_image(
        self,
        img: Node,
        *,
        order: int,
        attachments_by_file_srl: dict[str, Attachment] | None = None,
    ) -> ImageBlock | None:
        if "mejs__poster-img" in classes(img):
            return None
        parent_link = find_ancestor(img, tag="a", class_name="highslide")
        original_url = normalize_url(attr(parent_link, "href"), self.base_url)
        url = original_url or normalize_url(attr(img, "src"), self.base_url)
        if not url:
            return None
        file_srl = attr(img, "data-file-srl") or attr(img, "file_srl")
        attachment = (attachments_by_file_srl or {}).get(file_srl or "")
        return ImageBlock(
            order=order,
            url=url,
            original_url=original_url,
            alt=attr(img, "alt"),
            file_srl=file_srl,
            width=_int_or_none(attr(img, "width")),
            height=_int_or_none(attr(img, "height")),
            download_url=attachment.url if attachment else None,
        )

    def parse_video(self, video: Node, *, order: int) -> FmkVideoBlock | None:
        source = first(video, "source[src]")
        video_url = normalize_url(attr(source, "src") or attr(video, "src"), self.base_url)
        if not video_url:
            return None
        parent = video.parent or video
        description_node = first(parent, ".video_infobox .box div")
        return FmkVideoBlock(
            order=order,
            video_url=video_url,
            poster_url=normalize_url(attr(video, "poster"), self.base_url),
            description=text(description_node) or None,
            file_srl=attr(video, "data-file-srl"),
            download_url=video_url,
            name=_meta_content(parent, "name"),
            upload_date=_meta_content(parent, "uploadDate"),
            width=_int_or_none(_meta_content(parent, "width")),
            height=_int_or_none(_meta_content(parent, "height")),
        )

    def parse_youtube(self, url: str, *, order: int, text: str | None = None) -> YouTubeBlock | None:
        normalized = normalize_url(url, self.base_url)
        if not normalized:
            return None
        match = YOUTUBE_RE.search(normalized)
        if not match:
            return None
        video_id = match.group(1)
        query = parse_qs(urlsplit(normalized).query)
        start = _int_or_none(_first(query, "t") or _first(query, "start"))
        return YouTubeBlock(
            order=order,
            url=normalized,
            video_id=video_id,
            embed_url=f"https://www.youtube.com/embed/{video_id}",
            title=text,
            start_seconds=start,
        )

    def parse_x(self, url: str, *, order: int, text: str | None = None) -> XBlock | None:
        normalized = normalize_url(url, self.base_url)
        if not normalized:
            return None
        match = X_RE.search(normalized)
        if not match:
            return None
        username, tweet_id = match.groups()
        return XBlock(
            order=order,
            url=normalized,
            username=username,
            status_id=tweet_id,
            tweet_id=tweet_id,
            embed_url=f"https://platform.twitter.com/embed/Tweet.html?id={tweet_id}",
            text=text,
        )


def _first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def _meta_content(root: Node, itemprop: str) -> str | None:
    return attr(first(root, f'meta[itemprop="{itemprop}"][content]'), "content")
