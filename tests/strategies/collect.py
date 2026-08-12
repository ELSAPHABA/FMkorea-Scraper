from __future__ import annotations

from datetime import datetime

from hypothesis import strategies as st

from fmkorea_scraper.models.job import PostCandidate, RangeFilter


document_ids = st.integers(min_value=1, max_value=1_000_000)
board_ids = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
)

post_candidates = st.builds(
    PostCandidate,
    board_id=st.none() | board_ids,
    document_srl=document_ids,
    document_id_raw=document_ids.map(str),
    url=document_ids.map(lambda value: f"https://www.fmkorea.com/{value}"),
    candidate_created_at=st.none() | st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)),
)

bounded_range_filters = st.builds(
    RangeFilter,
    min_document_srl=st.integers(min_value=1, max_value=500_000),
    max_document_srl=st.integers(min_value=500_001, max_value=1_000_000),
)
