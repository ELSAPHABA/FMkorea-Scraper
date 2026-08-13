from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from fmkorea_scraper.retry import select_parser_failure_retries


safe_ids = st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")), min_size=1, max_size=8)


def _failure_line(board_id: str, document_id_raw: str, reason: str = "post title missing") -> str:
    document_srl = int(document_id_raw) if document_id_raw.isdigit() else 1
    return json.dumps(
        {
            "job_id": "job-1",
            "stage": "post",
            "reason": reason,
            "retryable": True,
            "url": f"https://www.fmkorea.com/best/{document_srl}",
            "post_key": {"board_id": board_id, "document_srl": document_srl, "document_id_raw": document_id_raw},
            "safe_message": "safe parser failure",
        },
        ensure_ascii=False,
    )


@given(st.lists(st.tuples(safe_ids, safe_ids), min_size=1, max_size=30))
@settings(max_examples=30)
def test_dedupe_never_selects_more_than_unique_keys(pairs: list[tuple[str, str]]) -> None:
    lines = [_failure_line(board_id, document_id_raw) for board_id, document_id_raw in pairs]
    candidates, summary = select_parser_failure_retries({"failures.jsonl": lines})

    assert len(candidates) <= len(set(pairs))
    assert summary.selected_count == len(candidates)


@given(st.lists(st.tuples(safe_ids, safe_ids), min_size=1, max_size=30))
@settings(max_examples=30)
def test_existing_success_skip_never_increases_selection(pairs: list[tuple[str, str]]) -> None:
    lines = [_failure_line(board_id, document_id_raw) for board_id, document_id_raw in pairs]
    candidates_without_skip, _ = select_parser_failure_retries({"failures.jsonl": lines})
    existing = {candidate.key for candidate in candidates_without_skip[: len(candidates_without_skip) // 2]}

    candidates_with_skip, _ = select_parser_failure_retries({"failures.jsonl": lines}, existing_keys=existing)

    assert len(candidates_with_skip) <= len(candidates_without_skip)
