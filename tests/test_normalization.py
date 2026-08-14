from __future__ import annotations

from fmkorea_scraper.core.normalization import normalize_checkpoint, normalize_job_report
from fmkorea_scraper.models.checkpoint import Checkpoint, CollectorCursor
from fmkorea_scraper.models.enums import CheckpointStatus, JobReportStatus, JobType, StopReason, StorageMode
from fmkorea_scraper.models.job import JobConfig, PostCandidate, PostKey
from fmkorea_scraper.models.report import JobReport, StoredObjectRef


def _job() -> JobConfig:
    return JobConfig(
        job_id="job-1",
        job_type=JobType.BOARD_SEARCH,
        source={
            "type": "board_search",
            "board_id": "stock",
            "keyword": "test",
            "search_target": "title_content",
        },
    )


def test_normalize_job_report_maps_fmkorea_counts() -> None:
    report = JobReport(
        job_id="job-1",
        status=JobReportStatus.COMPLETED,
        collected_count=8,
        stored_count=5,
        failure_count=2,
        output_refs=[
            StoredObjectRef(
                storage_mode=StorageMode.LOCAL,
                path="D:/tmp/outputs/job-1/run-8/report.json",
                object_key="outputs/job-1/run-8/report.json",
            )
        ],
    )

    normalized = normalize_job_report(report, scraper_id="worker-a")

    assert normalized.schema_version == "community.run_report.v1"
    assert normalized.scraper_id == "worker-a"
    assert normalized.site_id == "fmkorea"
    assert normalized.run_id == "run-8"
    assert normalized.candidate_seen_count == 8
    assert normalized.candidate_collected_count == 8
    assert normalized.post_stored_count == 5
    assert normalized.failure_count == 2
    assert normalized.duplicate_skipped_count is None
    assert normalized.range_filtered_count is None
    assert normalized.output_ref_count == 1
    assert normalized.native_report["schema_version"] == "fmkorea.job_report.v1"


def test_normalize_checkpoint_splits_completed_and_pending_rows() -> None:
    checkpoint = Checkpoint(
        job_id="job-1",
        status=CheckpointStatus.STOPPED,
        reason=StopReason.MANUAL_STOP,
        job_config=_job(),
        collector_cursor=CollectorCursor(
            source_type=JobType.BOARD_SEARCH,
            page=4,
            board_id="stock",
            last_document_srl=100,
        ),
        completed_keys=[PostKey(board_id="stock", document_srl=100, document_id_raw="100")],
        queued_links=[
            PostCandidate(
                board_id="stock",
                document_srl=101,
                document_id_raw="101",
                url="https://www.fmkorea.com/101",
            )
        ],
    )

    bundle = normalize_checkpoint(checkpoint)

    assert bundle.checkpoint.schema_version == "community.checkpoint.v1"
    assert bundle.checkpoint.collector_page == 4
    assert bundle.checkpoint.collector_board_id == "stock"
    assert bundle.checkpoint.collector_cursor_value == "100"
    assert bundle.checkpoint.last_completed_post_key == "fmkorea:stock:100"
    assert bundle.checkpoint.processed_count == 1
    assert bundle.checkpoint.worker_id is None
    assert bundle.completed_posts[0].post_key == "fmkorea:stock:100"
    assert bundle.pending_queue[0].queue_order == 0
    assert bundle.pending_queue[0].post_id == "101"
    assert bundle.pending_queue[0].candidate_payload["board_id"] == "stock"
