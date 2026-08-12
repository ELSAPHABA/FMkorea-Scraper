from __future__ import annotations

from hypothesis import strategies as st

from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.enums import CheckpointStatus, JobType, StopReason
from fmkorea_scraper.models.job import JobConfig


_job = JobConfig(job_id="job-1", job_type=JobType.BOARD_LIST, source={"type": "board_list", "board_id": "best"})

checkpoints = st.one_of(
    st.builds(Checkpoint, job_id=st.just("job-1"), status=st.just(CheckpointStatus.RUNNING), job_config=st.just(_job)),
    st.builds(
        Checkpoint,
        job_id=st.just("job-1"),
        status=st.just(CheckpointStatus.STOPPED),
        reason=st.sampled_from(list(StopReason)),
        job_config=st.just(_job),
    ),
)
