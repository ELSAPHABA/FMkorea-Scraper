from __future__ import annotations

from hypothesis import given, strategies as st

from fmkorea_scraper.runner.policies import (
    completed_key_map,
    post_key_from_candidate,
    post_key_token,
    report_counter_consistency,
    should_save_running_checkpoint,
)
from tests.strategies.runner import post_candidates, post_keys, runner_counters


@given(post_candidates)
def test_candidate_key_token_is_deterministic(candidate) -> None:
    assert post_key_token(post_key_from_candidate(candidate)) == post_key_token(post_key_from_candidate(candidate))


@given(post_keys)
def test_completed_key_map_is_idempotent(key) -> None:
    assert completed_key_map([key, key]) == completed_key_map([key])


@given(runner_counters)
def test_report_counter_consistency_never_accepts_impossible_success_counts(counters) -> None:
    expected = counters.collected_count >= counters.stored_count + counters.skipped_completed_count
    assert report_counter_consistency(counters) is expected


@given(stored_count=st.integers(min_value=0, max_value=500), last=st.integers(min_value=0, max_value=500))
def test_checkpoint_cadence_matches_interval_delta(stored_count: int, last: int) -> None:
    assert should_save_running_checkpoint(stored_count, last) is (stored_count > 0 and stored_count - last >= 10)
