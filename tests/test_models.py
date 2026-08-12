from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmkorea_scraper.core.errors import CaptchaDetectedError, ErrorMapper
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.comment import AuthorInfo, Comment, ReactionInfo
from fmkorea_scraper.models.enums import CheckpointStatus, JobType, StopReason
from fmkorea_scraper.models.job import JobConfig, RangeFilter
from fmkorea_scraper.models.post import PostResult


def _job(source: dict, job_type: str | None = None) -> JobConfig:
    source_type = job_type or source["type"]
    return JobConfig(job_id="job-1", job_type=JobType(source_type), source=source)


@pytest.mark.parametrize(
    "source",
    [
        {"type": "direct_post", "urls": ["https://www.fmkorea.com/best/10195585295"]},
        {"type": "board_list", "board_id": "best"},
        {"type": "board_search", "board_id": "best", "keyword": "test", "search_target": "title_content"},
        {"type": "integrated_search", "keyword": "test", "search_target": "title_content"},
        {
            "type": "deep_search",
            "keyword": "test",
            "seed_search_target": "title_content",
            "range_filter": {"date_from": "2026-01-01"},
        },
        {"type": "no_keyword_range", "board_id": "best", "range_filter": {"min_document_srl": 1}},
        {"type": "realtime_keyword", "keyword": "test", "termination": {"duration_seconds": 60}},
        {"type": "realtime_all", "board_id": "best", "termination": {"duration_seconds": 60}},
        {"type": "parser_failure_retry", "failure_input": {"failure_path": "failures.jsonl"}},
    ],
)
def test_valid_minimal_job_config_per_source(source: dict) -> None:
    job = _job(source)
    assert job.site_id == "fmkorea"
    assert job.source.type == source["type"]


def test_job_type_must_match_source_type() -> None:
    with pytest.raises(ValidationError):
        _job({"type": "board_list", "board_id": "best"}, "direct_post")


@pytest.mark.parametrize(
    "source",
    [
        {"type": "deep_search", "keyword": "test", "seed_search_target": "title_content", "range_filter": {}},
        {"type": "no_keyword_range", "board_id": "best", "range_filter": {}},
        {"type": "board_list", "board_id": "best", "page_start": 3, "page_end": 2},
        {
            "type": "realtime_keyword",
            "keyword": "test",
            "termination": {"duration_seconds": 60, "end_at": "2026-01-01T00:00:00Z"},
        },
    ],
)
def test_invalid_source_constraints(source: dict) -> None:
    with pytest.raises(ValidationError):
        _job(source)


def test_range_order_constraints() -> None:
    with pytest.raises(ValidationError):
        RangeFilter(date_from="2026-01-02", date_to="2026-01-01")
    with pytest.raises(ValidationError):
        RangeFilter(min_document_srl=2, max_document_srl=1)


def test_checkpoint_stop_reason_constraints() -> None:
    job = _job({"type": "board_list", "board_id": "best"})
    with pytest.raises(ValidationError):
        Checkpoint(job_id="job-1", status=CheckpointStatus.STOPPED, job_config=job)
    with pytest.raises(ValidationError):
        Checkpoint(job_id="job-1", status=CheckpointStatus.RUNNING, reason=StopReason.CAPTCHA, job_config=job)


def test_best_comment_and_reaction_consistency() -> None:
    comment = Comment(source_order=0, is_best=True, reactions={"up_count": 4, "down_count": 1})
    assert "BEST" in comment.badges
    assert comment.reactions.score == 3
    with pytest.raises(ValidationError):
        ReactionInfo(up_count=1, down_count=0, score=2)


def test_fmkorea_post_schema_has_no_repost_fields() -> None:
    post = PostResult(
        document_id_raw="10195585295",
        canonical_url="https://www.fmkorea.com/best/10195585295",
        title="sample",
        author=AuthorInfo(nickname="user"),
    )
    assert "is_repost" not in post.model_dump()
    with pytest.raises(ValidationError):
        PostResult(
            document_id_raw="10195585295",
            canonical_url="https://www.fmkorea.com/best/10195585295",
            title="sample",
            author=AuthorInfo(nickname="user"),
            is_repost=False,
        )


def test_error_redaction_keeps_safe_details_only() -> None:
    error = ErrorMapper.map(
        CaptchaDetectedError(
            "captcha",
            details={"stage": "post", "password": "plain", "reason": "token=abc"},
        )
    )
    assert error.code == "captcha_detected"
    assert error.retryable is True
    assert "password" not in error.details
    assert error.details["reason"] == "[REDACTED]"


def test_package_import_has_no_filesystem_side_effects(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    subprocess.run(
        [sys.executable, "-c", "import fmkorea_scraper"],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "user-agents.txt").exists()
