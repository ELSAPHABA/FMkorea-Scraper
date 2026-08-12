from __future__ import annotations

import pytest
from pydantic import ValidationError

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402

from fmkorea_scraper.models.content import BodyContent, TextBlock  # noqa: E402
from fmkorea_scraper.models.job import RangeFilter  # noqa: E402
from fmkorea_scraper.models.post import PostResult  # noqa: E402
from tests.strategies.checkpoints import checkpoints  # noqa: E402
from tests.strategies.comments import comments  # noqa: E402
from tests.strategies.content_blocks import body_contents  # noqa: E402
from tests.strategies.job_configs import range_filters, realtime_terminations  # noqa: E402
from tests.strategies.post_results import post_results  # noqa: E402


@given(post_results)
def test_post_result_json_round_trip(post: PostResult) -> None:
    restored = PostResult.model_validate_json(post.model_dump_json())
    assert restored.model_dump(mode="json") == post.model_dump(mode="json")


@given(range_filters)
def test_range_filter_keeps_order(range_filter: RangeFilter) -> None:
    if range_filter.min_document_srl is not None and range_filter.max_document_srl is not None:
        assert range_filter.min_document_srl <= range_filter.max_document_srl


@given(realtime_terminations)
def test_realtime_termination_has_exactly_one_stop_condition(termination) -> None:
    assert (termination.duration_seconds is None) != (termination.end_at is None)


@given(body_contents)
def test_content_block_orders_are_unique(content: BodyContent) -> None:
    orders = [block.order for block in content.blocks]
    assert len(orders) == len(set(orders))
    with pytest.raises(ValidationError):
        BodyContent(blocks=[TextBlock(order=0, text="a"), TextBlock(order=0, text="b")])


@given(comments)
def test_best_comment_and_score_invariants(comment) -> None:
    if comment.is_best:
        assert "BEST" in comment.badges
    assert comment.reactions.score == comment.reactions.up_count - comment.reactions.down_count


@given(checkpoints)
def test_checkpoint_status_reason_invariant(checkpoint) -> None:
    if checkpoint.status.value == "stopped":
        assert checkpoint.reason is not None
    else:
        assert checkpoint.reason is None


@given(post_results)
def test_schema_version_is_preserved(post: PostResult) -> None:
    assert PostResult.model_validate(post.model_dump()).schema_version == "fmkorea.post.v1"
