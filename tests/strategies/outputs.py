from __future__ import annotations

from hypothesis import strategies as st


path_segments = st.text(min_size=0, max_size=80)

failure_details = st.dictionaries(
    keys=st.sampled_from(["http_status", "request_url", "password", "raw_html", "parser_stage", "token"]),
    values=st.one_of(st.integers(min_value=0, max_value=999), st.text(max_size=80)),
    max_size=6,
)
