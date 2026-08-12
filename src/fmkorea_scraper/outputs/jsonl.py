"""JSONL and atomic JSON file writers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from fmkorea_scraper.outputs.errors import StorageWriteError, safe_error_details


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def dumps_jsonl_record(value: Any) -> str:
    line = json.dumps(to_jsonable(value), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return line.replace("\u0085", "\\u0085").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


class JsonlWriter:
    def __init__(self, path: Path, *, fsync: bool = False) -> None:
        self.path = path
        self.fsync = fsync
        self._handle = None

    def append(self, value: Any) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self._handle is None:
                self._handle = self.path.open("a", encoding="utf-8", newline="\n")
            self._handle.write(dumps_jsonl_record(value))
            self._handle.write("\n")
            self._handle.flush()
            if self.fsync:
                os.fsync(self._handle.fileno())
        except Exception as exc:
            raise StorageWriteError(
                "failed to append JSONL record",
                details=safe_error_details(path=str(self.path), error=exc.__class__.__name__),
            ) from exc

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


class AtomicJsonWriter:
    def write(self, path: Path, value: Any) -> None:
        temp_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            temp_path = Path(raw_temp)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(to_jsonable(value), handle, ensure_ascii=False, allow_nan=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except Exception as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise StorageWriteError(
                "failed to write JSON document",
                details=safe_error_details(path=str(path), error=exc.__class__.__name__),
            ) from exc


__all__ = ["AtomicJsonWriter", "JsonlWriter", "dumps_jsonl_record", "to_jsonable"]
