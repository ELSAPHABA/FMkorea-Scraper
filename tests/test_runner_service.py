from __future__ import annotations

import asyncio
from pathlib import Path

from fmkorea_scraper.core.api import run_job
from fmkorea_scraper.models.checkpoint import Checkpoint
from fmkorea_scraper.models.comment import AuthorInfo
from fmkorea_scraper.models.enums import CheckpointStatus, JobReportStatus, JobType
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey, ResumeRequest, WorkerConfig
from fmkorea_scraper.models.post import PostResult
from fmkorea_scraper.models.report import JobReport
from fmkorea_scraper.runner import JobRunDependencies, JobRunner


def run(coro):
    return asyncio.run(coro)


def candidate(raw: str) -> PostCandidate:
    return PostCandidate(
        board_id="best",
        document_srl=int(raw),
        document_id_raw=raw,
        url=f"https://www.fmkorea.com/best/{raw}",
    )


def post(raw: str) -> PostResult:
    return PostResult(
        board_id="best",
        document_srl=int(raw),
        document_id_raw=raw,
        canonical_url=f"https://www.fmkorea.com/best/{raw}",
        title=f"title {raw}",
        author=AuthorInfo(nickname="user"),
    )


def job_config(*, worker_config: WorkerConfig | None = None) -> JobConfig:
    return JobConfig(
        job_id="job-1",
        job_type=JobType.BOARD_LIST,
        source={"type": "board_list", "board_id": "best"},
        worker_config=worker_config or WorkerConfig(post_worker_count=1),
    )


class FakeCollector:
    def __init__(self, candidates: list[PostCandidate]) -> None:
        self.candidates = candidates

    async def collect(self, source):
        _ = source
        for item in self.candidates:
            yield item


class FakeDetailService:
    def __init__(self) -> None:
        self.requested: list[str] = []

    async def parse(self, item: PostCandidate) -> PostResult:
        self.requested.append(item.document_id_raw)
        return post(item.document_id_raw)


class FakeOutputStore:
    def __init__(self) -> None:
        self.posts: list[PostResult] = []
        self.reports: list[JobReport] = []
        self.finalized = False

    async def append_post(self, value: PostResult):
        from fmkorea_scraper.models.enums import StorageMode
        from fmkorea_scraper.models.report import StoredObjectRef

        self.posts.append(value)
        return StoredObjectRef(storage_mode=StorageMode.LOCAL, path=str(Path("posts.jsonl")))

    async def write_report(self, report: JobReport):
        from fmkorea_scraper.models.enums import StorageMode
        from fmkorea_scraper.models.report import StoredObjectRef

        self.reports.append(report)
        return StoredObjectRef(storage_mode=StorageMode.LOCAL, path=str(Path("report.json")))

    async def finalize(self):
        self.finalized = True


class FakeFailureStore:
    def __init__(self) -> None:
        self.failures = []
        self.finalized = False

    async def write_failure(self, failure):
        from fmkorea_scraper.models.enums import StorageMode
        from fmkorea_scraper.models.report import StoredObjectRef

        self.failures.append(failure)
        return StoredObjectRef(storage_mode=StorageMode.LOCAL, path=str(Path("failures.jsonl")))

    async def read_failures(self, failure_input):
        return []

    async def finalize(self):
        self.finalized = True


class FakeMediaStore:
    async def save_media(self, item, content: bytes):
        return item.model_copy(update={"file_path": f"media/{len(content)}"})

    async def save_metadata_only(self, item):
        return item


class FakeCheckpointStore:
    def __init__(self, checkpoint: Checkpoint | None = None) -> None:
        self.checkpoint = checkpoint
        self.saved: list[Checkpoint] = []

    async def save(self, checkpoint: Checkpoint) -> None:
        self.saved.append(checkpoint)
        self.checkpoint = checkpoint

    async def load(self, job_id: str) -> Checkpoint | None:
        return self.checkpoint if self.checkpoint and self.checkpoint.job_id == job_id else None

    async def load_latest(self) -> Checkpoint | None:
        return self.checkpoint


def dependencies(
    *,
    candidates: list[PostCandidate],
    detail: FakeDetailService | None = None,
    checkpoint_store: FakeCheckpointStore | None = None,
):
    output = FakeOutputStore()
    failure = FakeFailureStore()
    deps = JobRunDependencies(
        collector=FakeCollector(candidates),
        detail_service=detail or FakeDetailService(),
        output_store=output,
        failure_store=failure,
        media_store=FakeMediaStore(),
        checkpoint_store=checkpoint_store or FakeCheckpointStore(),
    )
    return deps, output, failure, deps.detail_service, deps.checkpoint_store


def test_runner_completes_and_writes_report_checkpoint_and_output() -> None:
    deps, output, failure, detail, checkpoints = dependencies(candidates=[candidate(str(100 + i)) for i in range(10)])

    result = run(JobRunner(deps).run(job_config()))

    assert result.status == JobReportStatus.COMPLETED
    assert result.stored_count == 10
    assert output.finalized is True
    assert failure.finalized is True
    assert len(output.posts) == 10
    assert len(detail.requested) == 10
    assert [checkpoint.status for checkpoint in checkpoints.saved] == [
        CheckpointStatus.RUNNING,
        CheckpointStatus.COMPLETED,
    ]
    assert output.reports[-1].stored_count == 10


def test_resume_skips_completed_queued_link_and_uses_new_run_result() -> None:
    completed = PostKey(board_id="best", document_srl=101, document_id_raw="101")
    checkpoint = Checkpoint(
        job_id="job-1",
        job_config=job_config(),
        completed_keys=[completed],
        queued_links=[candidate("101"), candidate("102")],
    )
    deps, output, _, detail, _ = dependencies(candidates=[], checkpoint_store=FakeCheckpointStore(checkpoint))
    runner = JobRunner(deps)

    result = run(runner.resume(ResumeRequest(job_id="job-1")))

    assert result.run_id.startswith("run-")
    assert result.skipped_count == 1
    assert [item.document_id_raw for item in output.posts] == ["102"]
    assert detail.requested == ["102"]


def test_core_api_unwraps_job_run_result_report() -> None:
    deps, _, _, _, _ = dependencies(candidates=[candidate("101")])

    report = run(run_job(job_config(), runner=JobRunner(deps)))

    assert report.job_id == "job-1"
    assert report.status == JobReportStatus.COMPLETED
