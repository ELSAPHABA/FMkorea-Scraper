from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402

from fmkorea_scraper.outputs.jsonl import JsonlWriter  # noqa: E402
from fmkorea_scraper.outputs.layout import OutputRunLayout, sanitize_path_segment  # noqa: E402
from fmkorea_scraper.outputs.redaction import sanitize_failure_context  # noqa: E402
from tests.strategies.outputs import failure_details, path_segments  # noqa: E402
from tests.strategies.post_results import post_results  # noqa: E402


@given(path_segments)
def test_sanitize_path_segment_never_returns_traversal_segment(raw: str) -> None:
    segment = sanitize_path_segment(raw)

    assert segment
    assert segment not in {".", ".."}
    assert "/" not in segment
    assert "\\" not in segment


@given(path_segments, path_segments)
def test_output_key_generation_is_posix_and_deterministic(job_id: str, run_id: str) -> None:
    first = OutputRunLayout(job_id, run_id, s3_prefix="prefix").posts_key
    second = OutputRunLayout(job_id, run_id, s3_prefix="prefix").posts_key

    assert first == second
    assert "\\" not in first
    assert first.endswith("/posts.jsonl")


@given(failure_details)
def test_failure_context_redaction_is_idempotent(details: dict) -> None:
    once = sanitize_failure_context(details)
    twice = sanitize_failure_context(once)

    assert once == twice
    assert "password" not in once
    assert "raw_html" not in once
    assert "token" not in once


@given(post_results)
def test_jsonl_writer_writes_one_json_object_per_line(post) -> None:
    with tempfile.TemporaryDirectory() as raw_dir:
        path = Path(raw_dir) / "posts.jsonl"
        writer = JsonlWriter(path)

        writer.append(post)
        writer.close()

        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["document_id_raw"] == post.document_id_raw
