from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.job import PostCandidate, PostKey
from fmkorea_scraper.runner.models import RunnerCounters


document_ids = st.integers(min_value=1, max_value=10**9)
board_ids = st.none() | st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
)

post_keys = st.builds(
    PostKey,
    board_id=board_ids,
    document_srl=st.none() | document_ids,
    document_id_raw=document_ids.map(str),
)

post_candidates = st.builds(
    PostCandidate,
    board_id=board_ids,
    document_srl=st.none() | document_ids,
    document_id_raw=document_ids.map(str),
    url=document_ids.map(lambda value: f"https://www.fmkorea.com/best/{value}"),
)

runner_counters = st.builds(
    RunnerCounters,
    collected_count=st.integers(min_value=0, max_value=500),
    queued_count=st.integers(min_value=0, max_value=500),
    skipped_completed_count=st.integers(min_value=0, max_value=500),
    stored_count=st.integers(min_value=0, max_value=500),
    failure_count=st.integers(min_value=0, max_value=500),
    media_stored_count=st.integers(min_value=0, max_value=500),
)
