from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "quality"


def read_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (FIXTURE_DIR / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def test_quality_post_fixture_has_required_shape() -> None:
    posts = read_jsonl("posts.jsonl")

    assert posts
    for post in posts:
        assert post["schema_version"] == "fmkorea.post.v1"
        assert post["site_id"] == "fmkorea"
        assert post["document_id_raw"]
        assert post["canonical_url"].startswith("https://www.fmkorea.com/")
        assert post["title"]
        assert "author" in post
        assert isinstance(post["content"]["text"], str)
        assert all("type" in block and "order" in block for block in post["content"]["blocks"])
        assert all("media_type" in item and "source_block_order" in item and "url" in item for item in post["media"])


def test_quality_post_fixture_models_best_comment_schema() -> None:
    comments = read_jsonl("posts.jsonl")[0]["comments"]
    best_comments = [comment for comment in comments if comment["is_best"]]

    assert best_comments
    assert best_comments[0]["badges"] == ["BEST"]
    assert best_comments[0]["reactions"]["up_count"] == 10
    assert best_comments[0]["reactions"]["down_count"] == 1
    assert best_comments[0]["reactions"]["score"] == 9


def test_quality_failure_fixture_is_safe_to_log() -> None:
    failures = read_jsonl("failures.jsonl")

    assert failures
    for failure in failures:
        assert failure["schema_version"] == "fmkorea.failure.v1"
        assert failure["safe_message"]
        text = json.dumps(failure, ensure_ascii=False)
        assert "password" not in text.lower()
        assert "cookie" not in text.lower()
        assert "raw_html" not in text.lower()


def test_quality_report_counts_match_fixture() -> None:
    report = json.loads((FIXTURE_DIR / "report.json").read_text(encoding="utf-8"))

    assert report["schema_version"] == "fmkorea.job_report.v1"
    assert report["status"] == "completed"
    assert report["collected_count"] == report["stored_count"] == 1
    assert report["failure_count"] == 1


def test_quality_posts_fixture_is_polars_readable_when_available() -> None:
    pl = pytest.importorskip("polars")

    frame = pl.read_ndjson(FIXTURE_DIR / "posts.jsonl")

    assert frame.height == 1
    assert "document_id_raw" in frame.columns
