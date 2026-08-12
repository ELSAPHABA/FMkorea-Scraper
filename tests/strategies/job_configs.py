from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.enums import JobType
from fmkorea_scraper.models.job import JobConfig, RangeFilter, RealtimeTermination


range_filters = st.builds(
    RangeFilter,
    min_document_srl=st.none() | st.integers(min_value=0, max_value=1000),
    max_document_srl=st.none() | st.integers(min_value=1001, max_value=2000),
)

realtime_terminations = st.one_of(
    st.builds(RealtimeTermination, duration_seconds=st.integers(min_value=1, max_value=3600)),
    st.builds(RealtimeTermination, end_at=st.datetimes(timezones=st.just(__import__("datetime").timezone.utc))),
)

job_configs = st.builds(
    JobConfig,
    job_id=st.text(min_size=1, max_size=20),
    job_type=st.just(JobType.BOARD_LIST),
    source=st.just({"type": "board_list", "board_id": "best"}),
)
