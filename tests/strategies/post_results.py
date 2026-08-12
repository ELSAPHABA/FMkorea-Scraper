from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.comment import AuthorInfo
from fmkorea_scraper.models.post import PostResult


post_results = st.builds(
    PostResult,
    document_id_raw=st.integers(min_value=1, max_value=10**12).map(str),
    canonical_url=st.integers(min_value=1, max_value=10**12).map(lambda n: f"https://www.fmkorea.com/best/{n}"),
    title=st.text(min_size=1, max_size=100),
    author=st.builds(AuthorInfo, nickname=st.text(min_size=1, max_size=20)),
)
