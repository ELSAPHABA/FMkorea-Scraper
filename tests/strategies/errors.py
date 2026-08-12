from __future__ import annotations

from hypothesis import strategies as st


secret_details = st.fixed_dictionaries(
    {
        "stage": st.sampled_from(["search", "post", "comment"]),
        "password": st.text(min_size=1, max_size=20),
        "reason": st.sampled_from(["ok", "token=hidden"]),
    }
)
