from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.comment import Comment, ReactionInfo


reactions = st.builds(
    ReactionInfo,
    up_count=st.integers(min_value=0, max_value=1000),
    down_count=st.integers(min_value=0, max_value=1000),
)

comments = st.builds(
    Comment,
    source_order=st.integers(min_value=0, max_value=1000),
    is_best=st.booleans(),
    reactions=reactions,
)
