from __future__ import annotations

from hypothesis import strategies as st

job_ids = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=30)
document_ids = st.integers(min_value=1_000, max_value=10_000_000_000)


@st.composite
def direct_post_commands(draw):
    document_id = draw(document_ids)
    job_id = draw(job_ids)
    return {
        "subcommand": "run",
        "source": "direct-post",
        "job_id": job_id,
        "urls": [f"https://www.fmkorea.com/best/{document_id}"],
    }


@st.composite
def realtime_keyword_envs(draw):
    duration = draw(st.integers(min_value=1, max_value=86_400))
    keyword = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=30))
    return {
        "FMKOREA_REALTIME_ENABLED": "true",
        "FMKOREA_REALTIME_MODE": "keyword",
        "FMKOREA_REALTIME_KEYWORD": keyword,
        "FMKOREA_REALTIME_DURATION_SECONDS": str(duration),
    }
