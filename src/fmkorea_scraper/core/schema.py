"""Schema snapshot and compatibility helpers."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from fmkorea_scraper.models.base import StrictBaseModel
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport


class SchemaChangeClass(str, Enum):
    COMPATIBLE = "compatible"
    MIGRATION_NOTE_REQUIRED = "migration_note_required"
    BREAKING = "breaking"


class SchemaSnapshot(StrictBaseModel):
    name: str
    version: str
    schema_data: dict[str, Any] = Field(alias="schema")
    schema_hash: str

    @classmethod
    def from_model(cls, *, name: str, version: str, model: type[BaseModel]) -> "SchemaSnapshot":
        schema = model.model_json_schema()
        payload = json.dumps(schema, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return cls(
            name=name,
            version=version,
            schema=schema,
            schema_hash=hashlib.sha256(payload).hexdigest(),
        )


class SchemaDiffResult(StrictBaseModel):
    change_class: SchemaChangeClass
    messages: list[str] = Field(default_factory=list)


class SchemaRegistry:
    def __init__(self) -> None:
        self._models: dict[str, tuple[str, type[BaseModel]]] = {}

    def register(self, name: str, version: str, model: type[BaseModel]) -> None:
        self._models[name] = (version, model)

    def snapshot(self, name: str) -> SchemaSnapshot:
        version, model = self._models[name]
        return SchemaSnapshot.from_model(name=name, version=version, model=model)

    def snapshots(self) -> list[SchemaSnapshot]:
        return [self.snapshot(name) for name in sorted(self._models)]


class SchemaSnapshotWriter:
    """Write deterministic persisted-schema snapshots."""

    @staticmethod
    def write_versions(path: Path, snapshots: list[SchemaSnapshot]) -> None:
        payload = {
            "schemas": [
                {"name": item.name, "version": item.version, "schema_hash": item.schema_hash}
                for item in sorted(snapshots, key=lambda snapshot: snapshot.name)
            ]
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SchemaCompatibilityChecker:
    """Small compatibility checker for top-level persisted models."""

    @staticmethod
    def compare(old: SchemaSnapshot, current: SchemaSnapshot) -> SchemaDiffResult:
        if old.schema_hash == current.schema_hash:
            return SchemaDiffResult(change_class=SchemaChangeClass.COMPATIBLE)

        old_props = old.schema_data.get("properties", {})
        new_props = current.schema_data.get("properties", {})
        old_required = set(old.schema_data.get("required", []))
        new_required = set(current.schema_data.get("required", []))
        messages: list[str] = []
        breaking = False
        migration_note = False

        for field in sorted(set(old_props) - set(new_props)):
            messages.append(f"field removed: {field}")
            breaking = True

        for field in sorted(new_required - old_required):
            messages.append(f"required field added: {field}")
            breaking = True

        for field in sorted(set(old_props) & set(new_props)):
            if _schema_shape(old_props[field]) != _schema_shape(new_props[field]):
                messages.append(f"field type changed: {field}")
                breaking = True
            if _enum_added(old_props[field], new_props[field]):
                messages.append(f"enum value added: {field}")
                migration_note = True

        if breaking:
            return SchemaDiffResult(change_class=SchemaChangeClass.BREAKING, messages=messages)
        if migration_note:
            return SchemaDiffResult(
                change_class=SchemaChangeClass.MIGRATION_NOTE_REQUIRED,
                messages=messages,
            )
        return SchemaDiffResult(change_class=SchemaChangeClass.COMPATIBLE, messages=messages)


def default_schema_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    registry.register("post", "fmkorea.post.v1", PostResult)
    registry.register("checkpoint", "fmkorea.checkpoint.v1", Checkpoint)
    registry.register("failure", "fmkorea.failure.v1", FailureRecord)
    registry.register("job_report", "fmkorea.job_report.v1", JobReport)
    return registry


def _schema_shape(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return f"ref:{schema['$ref']}"
    if "type" in schema:
        return json.dumps(schema["type"], sort_keys=True)
    if "anyOf" in schema:
        return "anyOf:" + json.dumps([_schema_shape(item) for item in schema["anyOf"]], sort_keys=True)
    return json.dumps(schema, sort_keys=True)


def _enum_added(old: dict[str, Any], current: dict[str, Any]) -> bool:
    old_enum = old.get("enum")
    new_enum = current.get("enum")
    return isinstance(old_enum, list) and isinstance(new_enum, list) and set(old_enum) < set(new_enum)
