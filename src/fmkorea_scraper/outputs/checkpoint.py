"""Local checkpoint file storage."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.job import utc_now
from fmkorea_scraper.outputs.errors import StorageReadError, safe_error_details
from fmkorea_scraper.outputs.jsonl import AtomicJsonWriter
from fmkorea_scraper.outputs.layout import OutputRunLayout


class LocalCheckpointDocument:
    schema_version = "fmkorea.local_checkpoint.v1"

    def __init__(self, *, updated_at: datetime | None = None, checkpoints: dict[str, Checkpoint] | None = None) -> None:
        self.updated_at = updated_at or utc_now()
        self.checkpoints = checkpoints or {}

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "updated_at": self.updated_at.isoformat(),
            "checkpoints": {job_id: checkpoint.model_dump(mode=mode) for job_id, checkpoint in self.checkpoints.items()},
        }

    @classmethod
    def from_path(cls, path: Path) -> "LocalCheckpointDocument":
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("schema_version") != cls.schema_version:
                raise ValueError("unsupported local checkpoint schema")
            checkpoints = {
                job_id: Checkpoint.model_validate(payload)
                for job_id, payload in raw.get("checkpoints", {}).items()
            }
            updated_at = datetime.fromisoformat(str(raw["updated_at"]))
            return cls(updated_at=updated_at, checkpoints=checkpoints)
        except Exception as exc:
            raise StorageReadError(
                "failed to read local checkpoint",
                details=safe_error_details(path=str(path), error=exc.__class__.__name__),
            ) from exc


class LocalCheckpointStore:
    def __init__(self, layout: OutputRunLayout) -> None:
        self.layout = layout
        self.path = layout.checkpoint_path
        self._json = AtomicJsonWriter()
        self._lock = threading.Lock()

    async def save(self, checkpoint: Checkpoint) -> None:
        with self._lock:
            document = LocalCheckpointDocument.from_path(self.path)
            document.checkpoints[checkpoint.job_id] = checkpoint
            document.updated_at = utc_now()
            self._json.write(self.path, document.model_dump(mode="json"))

    async def load(self, job_id: str) -> Checkpoint | None:
        with self._lock:
            return LocalCheckpointDocument.from_path(self.path).checkpoints.get(job_id)

    async def load_latest(self) -> Checkpoint | None:
        with self._lock:
            checkpoints = LocalCheckpointDocument.from_path(self.path).checkpoints.values()
            return max(checkpoints, key=lambda checkpoint: checkpoint.updated_at, default=None)


__all__ = ["LocalCheckpointDocument", "LocalCheckpointStore"]
