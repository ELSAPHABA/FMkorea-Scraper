from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from fmkorea_scraper.models.comment import AuthorInfo  # noqa: E402
from fmkorea_scraper.models.job import StorageConfig  # noqa: E402
from fmkorea_scraper.models.post import PostResult  # noqa: E402
from fmkorea_scraper.outputs import StorageFactory  # noqa: E402

pytestmark = pytest.mark.polars_smoke


def test_posts_jsonl_is_polars_readable(tmp_path: Path) -> None:
    bundle = StorageFactory.create(StorageConfig(base_output_path=str(tmp_path)), job_id="job-1", run_id="run-1")
    post = PostResult(
        document_id_raw="101",
        canonical_url="https://www.fmkorea.com/best/101",
        title="sample",
        author=AuthorInfo(nickname="user"),
    )

    asyncio.run(bundle.output_store.append_post(post))
    asyncio.run(bundle.output_store.finalize())

    frame = pl.read_ndjson(str(bundle.layout.posts_path))
    assert frame.select("document_id_raw").item() == "101"
    assert "comments" in frame.columns
    assert "content" in frame.columns
