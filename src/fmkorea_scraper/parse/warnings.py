"""Safe parser warning records."""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from fmkorea_scraper.models.base import MetadataModel


class ParseWarning(MetadataModel):
    code: str = Field(min_length=1, max_length=100)
    stage: str = Field(min_length=1, max_length=100)
    selector: str | None = Field(default=None, max_length=300)
    order: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1, max_length=300)
    board_id: str | None = Field(default=None, max_length=100)
    document_srl: int | None = Field(default=None, ge=0)


class WarningRedactor:
    blocked_key = re.compile(r"(html|body|content|comment|cookie|proxy|password|secret|token|env)", re.I)
    blocked_value = re.compile(r"(<html|<!doctype|<body|cookie\s*[:=]|password\s*[:=]|token\s*[:=])", re.I)

    @classmethod
    def safe_text(cls, value: Any) -> str:
        text = str(value)
        if cls.blocked_value.search(text):
            return "[REDACTED]"
        return text[:300]

    @classmethod
    def safe_metadata(cls, values: dict[str, Any]) -> dict[str, Any]:
        return {
            key: cls.safe_text(value)
            for key, value in values.items()
            if not cls.blocked_key.search(key)
        }


class ParseWarningCollector:
    def __init__(self) -> None:
        self._warnings: list[ParseWarning] = []

    def add(
        self,
        *,
        code: str,
        stage: str,
        reason: Any,
        selector: str | None = None,
        order: int | None = None,
        board_id: str | None = None,
        document_srl: int | None = None,
    ) -> None:
        self._warnings.append(
            ParseWarning(
                code=code,
                stage=stage,
                selector=selector,
                order=order,
                reason=WarningRedactor.safe_text(reason),
                board_id=board_id,
                document_srl=document_srl,
            )
        )

    def extend(self, warnings: list[ParseWarning]) -> None:
        self._warnings.extend(warnings)

    def to_metadata(self) -> list[dict[str, Any]]:
        return [warning.model_dump(exclude_none=True) for warning in self._warnings]

    def __len__(self) -> int:
        return len(self._warnings)
