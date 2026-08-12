from __future__ import annotations

import json
from pathlib import Path

from fmkorea_scraper.core.schema import (
    SchemaChangeClass,
    SchemaCompatibilityChecker,
    default_schema_registry,
)


def test_default_schema_registry_versions() -> None:
    snapshots = {snapshot.name: snapshot.version for snapshot in default_schema_registry().snapshots()}
    assert snapshots == {
        "checkpoint": "fmkorea.checkpoint.v1",
        "failure": "fmkorea.failure.v1",
        "job_report": "fmkorea.job_report.v1",
        "post": "fmkorea.post.v1",
    }


def test_identical_schema_is_compatible() -> None:
    snapshot = default_schema_registry().snapshot("post")
    result = SchemaCompatibilityChecker.compare(snapshot, snapshot)
    assert result.change_class == SchemaChangeClass.COMPATIBLE


def test_schema_snapshot_file_matches_current_models() -> None:
    expected = json.loads(Path("tests/snapshots/schema_versions.json").read_text(encoding="utf-8"))
    current = {
        "schemas": [
            {"name": snapshot.name, "schema_hash": snapshot.schema_hash, "version": snapshot.version}
            for snapshot in default_schema_registry().snapshots()
        ]
    }
    assert current == expected
