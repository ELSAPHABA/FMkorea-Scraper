from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.content import BodyContent, TextBlock


body_contents = st.lists(
    st.text(max_size=50),
    min_size=0,
    max_size=10,
).map(lambda texts: BodyContent(blocks=[TextBlock(order=i, text=text) for i, text in enumerate(texts)]))
