from __future__ import annotations

from hypothesis import strategies as st


safe_urls = st.from_regex(r"https://www\.fmkorea\.com/[A-Za-z0-9_/?=&.-]+", fullmatch=True)
comment_ids = st.integers(min_value=0, max_value=10**12)
block_orders = st.lists(st.integers(min_value=0, max_value=10_000), unique=True, max_size=50)
