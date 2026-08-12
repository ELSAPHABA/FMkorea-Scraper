"""Media and attachment parsers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import Tag

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
    def parse(self, root: Tag, *, base_url: str = "https://www.fmkorea.com") -> list[Attachment]:
        attachments: list[Attachment] = []
        for link in root.select(".rd_file a[data-href]"):
            href = normalize_url(link.get("data-href") or link.get("href"), base_url)
            if not href:
                continue
            query = parse_qs(urlsplit(href).query)
            file_srl = _first(query, "file_srl")
            attachments.append(
                Attachment(
                    file_name=link.get_text(" ", strip=True) or link.get("title"),
                    url=href,
                    size_text=link.get("title"),
                    file_srl=file_srl,
                    sid=_first(query, "sid"),
                    mid=_first(query, "mid"),
                    download_text=link.get("title"),
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
        img: Tag,
        *,
        order: int,
        attachments_by_file_srl: dict[str, Attachment] | None = None,
    ) -> ImageBlock | None:
        if "mejs__poster-img" in (img.get("class") or []):
            return None
        parent_link = img.find_parent("a", class_="highslide")
        original_url = normalize_url(parent_link.get("href") if parent_link else None, self.base_url)
        url = original_url or normalize_url(img.get("src"), self.base_url)
        if not url:
            return None
        file_srl = img.get("data-file-srl") or img.get("file_srl")
        attachment = (attachments_by_file_srl or {}).get(file_srl or "")
        return ImageBlock(
            order=order,
            url=url,
            original_url=original_url,
            alt=img.get("alt"),
            file_srl=file_srl,
            width=_int_or_none(img.get("width")),
            height=_int_or_none(img.get("height")),
            download_url=attachment.url if attachment else None,
        )

    def parse_video(self, video: Tag, *, order: int) -> FmkVideoBlock | None:
        source = video.select_one("source[src]")
        video_url = normalize_url(source.get("src") if source else video.get("src"), self.base_url)
        if not video_url:
            return None
        parent = video.parent if isinstance(video.parent, Tag) else video
        description_node = parent.select_one(".video_infobox .box div") if isinstance(parent, Tag) else None
        return FmkVideoBlock(
            order=order,
            video_url=video_url,
            poster_url=normalize_url(video.get("poster"), self.base_url),
            description=description_node.get_text(" ", strip=True) if description_node else None,
            file_srl=video.get("data-file-srl"),
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


def _meta_content(root: Tag, itemprop: str) -> str | None:
    node = root.select_one(f'meta[itemprop="{itemprop}"][content]')
    return node.get("content") if node else None
