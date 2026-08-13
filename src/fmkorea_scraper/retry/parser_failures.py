"""Retry parser-stage post failures through the existing direct-post runner."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from pydantic import ValidationError

from fmkorea_scraper.collect.urls import DirectPostUrlNormalizer
from fmkorea_scraper.core.errors import ScraperError, StorageFailureError, ValidationFailure
from fmkorea_scraper.models.enums import JobReportStatus, JobType
from fmkorea_scraper.models.failure import FailureRecord
from fmkorea_scraper.models.job import DirectPostSource, JobConfig, PostKey, RetryRequest, ScrapeOptions, StorageConfig, WorkerConfig
from fmkorea_scraper.models.report import JobReport, RetryReport

RetryKey = tuple[str, str | None, int | None, str]

_DEFAULT_SITE_ID = "fmkorea"
_RETRY_REASON_FRAGMENTS = (
    "parse_failure",
    "parse failure",
    "post title missing",
    "post author missing",
    "post identity missing",
    "metadata parse",
    "metadata failure",
    "content parse",
    "content failure",
    "comment parse",
)
_EXCLUDED_REASON_FRAGMENTS = (
    "captcha",
    "block",
    "network",
    "storage",
    "checkpoint",
    "manual",
    "cancel",
    "media",
    "output",
)


class FailureInputReader(Protocol):
    def iter_lines(self, ref: str) -> Iterable[str]:
        ...


class LocalFailureInputReader:
    def iter_lines(self, ref: str) -> Iterable[str]:
        path = _local_path(ref)
        if not path.is_file():
            raise ValidationFailure("input file not found", details={"reason": "file_not_found"})
        try:
            with path.open("r", encoding="utf-8") as file:
                yield from file
        except OSError as exc:
            raise StorageFailureError("input file read failed", details={"stage": "retry_input", "reason": exc.__class__.__name__}) from exc


class S3FailureInputReader:
    def __init__(
        self,
        client: Any | None = None,
        *,
        default_bucket: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        force_path_style: bool = False,
    ) -> None:
        self._client = client
        self.default_bucket = default_bucket
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.force_path_style = force_path_style

    def iter_lines(self, ref: str) -> Iterable[str]:
        bucket, key = self._bucket_key(ref)
        try:
            response = self._get_client().get_object(Bucket=bucket, Key=key)
            body = response["Body"]
            if hasattr(body, "iter_lines"):
                for raw_line in body.iter_lines():
                    yield raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
                return
            raw = body.read() if hasattr(body, "read") else body
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            yield from text.splitlines()
        except Exception as exc:
            raise StorageFailureError("s3 input read failed", details={"stage": "retry_input", "reason": exc.__class__.__name__}) from exc

    def _bucket_key(self, ref: str) -> tuple[str, str]:
        parsed = urlparse(str(ref))
        if parsed.scheme == "s3":
            if not parsed.netloc or not parsed.path.strip("/"):
                raise ValidationFailure("invalid s3 input ref", details={"reason": "invalid_s3_ref"})
            return parsed.netloc, unquote(parsed.path.lstrip("/"))
        if not self.default_bucket:
            raise ValidationFailure("s3 bucket is required for object key refs", details={"reason": "missing_s3_bucket"})
        return self.default_bucket, str(ref).lstrip("/")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise StorageFailureError("s3 extra is required", details={"stage": "retry_input", "reason": "missing_s3_dependency"}) from exc
        kwargs: dict[str, Any] = {}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.region_name:
            kwargs["region_name"] = self.region_name
        if self.access_key_id:
            kwargs["aws_access_key_id"] = self.access_key_id
        if self.secret_access_key:
            kwargs["aws_secret_access_key"] = self.secret_access_key
        if self.force_path_style:
            try:
                from botocore.config import Config
            except ImportError as exc:
                raise StorageFailureError("s3 extra is required", details={"stage": "retry_input", "reason": "missing_s3_dependency"}) from exc
            kwargs["config"] = Config(s3={"addressing_style": "path"})
        self._client = boto3.client("s3", **kwargs)
        return self._client


class CompositeFailureInputReader:
    def __init__(
        self,
        *,
        local: FailureInputReader | None = None,
        s3: FailureInputReader | None = None,
        prefer_s3_object_keys: bool = False,
    ) -> None:
        self.local = local or LocalFailureInputReader()
        self.s3 = s3 or S3FailureInputReader()
        self.prefer_s3_object_keys = prefer_s3_object_keys

    def iter_lines(self, ref: str) -> Iterable[str]:
        text = str(ref)
        if text.startswith("s3://"):
            return self.s3.iter_lines(text)
        if self.prefer_s3_object_keys and not text.startswith("file://") and not _looks_like_local_path(text):
            return self.s3.iter_lines(text)
        return self.local.iter_lines(text)


@dataclass(frozen=True)
class RetryCandidate:
    key: RetryKey
    url: str
    board_id: str | None = None
    document_srl: int | None = None
    document_id_raw: str = ""
    last_failure_reason: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class ExistingSuccessIndex:
    keys: frozenset[RetryKey] = field(default_factory=frozenset)
    invalid_record_count: int = 0
    refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrySelectionSummary:
    retry_source_failure_refs: tuple[str, ...] = ()
    initial_failure_count: int = 0
    invalid_failure_record_count: int = 0
    ineligible_failure_count: int = 0
    selected_count: int = 0
    deduped_failure_count: int = 0
    skipped_existing_count: int = 0
    existing_success_invalid_record_count: int = 0

    def to_metadata(self) -> dict[str, Any]:
        return {
            "retry_source_failure_refs": list(self.retry_source_failure_refs),
            "initial_failure_count": self.initial_failure_count,
            "invalid_failure_record_count": self.invalid_failure_record_count,
            "ineligible_failure_count": self.ineligible_failure_count,
            "selected_count": self.selected_count,
            "deduped_failure_count": self.deduped_failure_count,
            "skipped_existing_count": self.skipped_existing_count,
            "existing_success_invalid_record_count": self.existing_success_invalid_record_count,
        }


class ParserFailureRetryService:
    def __init__(
        self,
        reader: FailureInputReader | None = None,
        *,
        execute_job: Callable[[JobConfig], Awaitable[JobReport]] | None = None,
        scrape_options: ScrapeOptions | None = None,
        worker_config: WorkerConfig | None = None,
        storage_config: StorageConfig | None = None,
    ) -> None:
        self.reader = reader or CompositeFailureInputReader()
        self.execute_job = execute_job
        self.scrape_options = scrape_options or ScrapeOptions()
        self.worker_config = worker_config or WorkerConfig()
        self.storage_config = storage_config or StorageConfig()

    async def run(self, request: RetryRequest) -> RetryReport:
        return await self.retry(request, execute_job=self.execute_job)

    async def retry(
        self,
        request: RetryRequest,
        *,
        execute_job: Callable[[JobConfig], Awaitable[JobReport]] | None,
    ) -> RetryReport:
        if execute_job is None:
            raise ValidationFailure("retry runner is required", details={"reason": "missing_retry_runner"})
        existing = self.build_existing_success_index(request.existing_success_path)
        failure_lines = {request.failure_input.failure_path: self.reader.iter_lines(request.failure_input.failure_path)}
        candidates, summary = select_parser_failure_retries(
            failure_lines,
            job_id=request.failure_input.job_id,
            stage_allowlist=request.failure_input.stage_allowlist,
            existing_keys=existing.keys if request.skip_existing_success else (),
            existing_success_invalid_record_count=existing.invalid_record_count,
        )
        if not candidates:
            return _empty_retry_report(request, summary)
        config = self._job_config_for_retry(request, candidates, summary)
        report = await execute_job(config)
        return _retry_report_from_job_report(report, summary)

    def build_existing_success_index(self, ref: str | None = None) -> ExistingSuccessIndex:
        if not ref:
            return ExistingSuccessIndex()
        keys: set[RetryKey] = set()
        invalid_count = 0
        for line in self.reader.iter_lines(ref):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                key = _post_key_from_raw(raw)
            except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
                invalid_count += 1
                continue
            if key is None:
                invalid_count += 1
                continue
            keys.add(key)
        return ExistingSuccessIndex(frozenset(keys), invalid_count, (ref,))

    def _job_config_for_retry(
        self,
        request: RetryRequest,
        candidates: list[RetryCandidate],
        summary: RetrySelectionSummary,
    ) -> JobConfig:
        return JobConfig(
            job_id=request.retry_job_id or request.failure_input.job_id or "retry-parser-failures",
            job_type=JobType.DIRECT_POST,
            source=DirectPostSource(urls=[candidate.url for candidate in candidates]),
            scrape_options=self.scrape_options,
            worker_config=self.worker_config,
            storage_config=self.storage_config,
            metadata={"parser_failure_retry": summary.to_metadata()},
        )


def select_parser_failure_retries(
    failure_lines_by_ref: Mapping[str, Iterable[str]],
    *,
    job_id: str | None = None,
    stage_allowlist: Iterable[str] = ("post",),
    existing_keys: Iterable[RetryKey] = (),
    existing_success_invalid_record_count: int = 0,
) -> tuple[list[RetryCandidate], RetrySelectionSummary]:
    allowed_stages = set(stage_allowlist)
    existing = set(existing_keys)
    candidates: dict[RetryKey, RetryCandidate] = {}
    initial_count = 0
    invalid_count = 0
    ineligible_count = 0
    deduped_count = 0

    for source_ref, lines in failure_lines_by_ref.items():
        for line in lines:
            if not line.strip():
                continue
            initial_count += 1
            try:
                raw = json.loads(line)
                failure = FailureRecord.model_validate(raw)
                if job_id and failure.job_id != job_id:
                    ineligible_count += 1
                    continue
                if failure.stage not in allowed_stages:
                    ineligible_count += 1
                    continue
                if not _is_retryable_parser_failure(failure):
                    ineligible_count += 1
                    continue
                candidate = _candidate_from_failure(failure, source_ref=source_ref)
            except (json.JSONDecodeError, ValidationError, ValidationFailure, ScraperError, ValueError, TypeError):
                invalid_count += 1
                continue
            if candidate.key in candidates:
                deduped_count += 1
                del candidates[candidate.key]
            candidates[candidate.key] = candidate

    selected: list[RetryCandidate] = []
    skipped_existing = 0
    for candidate in candidates.values():
        if candidate.key in existing:
            skipped_existing += 1
            continue
        selected.append(candidate)

    return selected, RetrySelectionSummary(
        retry_source_failure_refs=tuple(failure_lines_by_ref.keys()),
        initial_failure_count=initial_count,
        invalid_failure_record_count=invalid_count,
        ineligible_failure_count=ineligible_count,
        selected_count=len(selected),
        deduped_failure_count=deduped_count,
        skipped_existing_count=skipped_existing,
        existing_success_invalid_record_count=existing_success_invalid_record_count,
    )


def retry_safe_summary(report: RetryReport) -> dict[str, Any]:
    return {
        "selected": report.selected_count,
        "skipped": report.skipped_count,
        "stored": report.stored_count,
        "remaining_failure": report.failure_count,
        "report": _report_ref(report),
    }


def _candidate_from_failure(failure: FailureRecord, *, source_ref: str) -> RetryCandidate:
    if not failure.url:
        raise ValidationFailure("failure record lacks retry URL", details={"reason": "missing_url"})
    normalized = DirectPostUrlNormalizer().normalize(failure.url)
    key = _key_from_parts(failure.post_key, normalized.board_id, normalized.document_srl, normalized.document_id_raw)
    return RetryCandidate(
        key=key,
        url=normalized.url,
        board_id=key[1],
        document_srl=key[2],
        document_id_raw=key[3],
        last_failure_reason=failure.reason,
        source_ref=source_ref,
    )


def _is_retryable_parser_failure(failure: FailureRecord) -> bool:
    if failure.stage != "post":
        return False
    reason = failure.reason.lower()
    if any(fragment in reason for fragment in _EXCLUDED_REASON_FRAGMENTS):
        return False
    return any(fragment in reason for fragment in _RETRY_REASON_FRAGMENTS)


def _post_key_from_raw(raw: Mapping[str, Any]) -> RetryKey | None:
    post_key = raw.get("post_key")
    if isinstance(post_key, Mapping):
        try:
            return _key_from_parts(PostKey.model_validate(post_key), None, None, None)
        except ValidationError:
            return None
    document_id_raw = raw.get("document_id_raw")
    if not document_id_raw:
        return None
    return (
        str(raw.get("site_id") or _DEFAULT_SITE_ID),
        str(raw["board_id"]) if raw.get("board_id") is not None else None,
        _int_or_none(raw.get("document_srl")),
        str(document_id_raw),
    )


def _key_from_parts(
    post_key: PostKey | None,
    board_id: str | None,
    document_srl: int | None,
    document_id_raw: str | None,
) -> RetryKey:
    raw = document_id_raw or (post_key.document_id_raw if post_key else None)
    if not raw:
        raise ValidationFailure("post identity is required", details={"reason": "missing_post_identity"})
    return (
        post_key.site_id if post_key else _DEFAULT_SITE_ID,
        post_key.board_id if post_key and post_key.board_id is not None else board_id,
        post_key.document_srl if post_key and post_key.document_srl is not None else document_srl,
        raw,
    )


def _empty_retry_report(request: RetryRequest, summary: RetrySelectionSummary) -> RetryReport:
    metadata = summary.to_metadata()
    metadata["remaining_failure_count"] = 0
    return RetryReport(
        job_id=request.retry_job_id or request.failure_input.job_id or "retry-parser-failures",
        status=JobReportStatus.COMPLETED,
        selected_count=0,
        skipped_count=summary.skipped_existing_count,
        metadata={"parser_failure_retry": metadata},
    )


def _retry_report_from_job_report(report: JobReport, summary: RetrySelectionSummary) -> RetryReport:
    metadata = dict(report.metadata)
    retry_metadata = summary.to_metadata()
    retry_metadata["remaining_failure_count"] = report.failure_count
    metadata["parser_failure_retry"] = retry_metadata
    return RetryReport(
        job_id=report.job_id,
        status=report.status,
        started_at=report.started_at,
        finished_at=report.finished_at,
        collected_count=report.collected_count,
        stored_count=report.stored_count,
        failure_count=report.failure_count,
        output_refs=report.output_refs,
        selected_count=summary.selected_count,
        skipped_count=summary.skipped_existing_count,
        metadata=metadata,
    )


def _report_ref(report: RetryReport) -> str | None:
    for ref in report.output_refs:
        label = ref.path or ref.object_key or ref.bucket
        if label:
            return label
    return None


def _local_path(ref: str) -> Path:
    if _is_windows_drive_path(ref):
        return Path(ref).resolve(strict=False)
    parsed = urlparse(str(ref))
    if parsed.scheme == "file":
        return Path(url2pathname(parsed.path)).resolve(strict=False)
    if parsed.scheme:
        raise ValidationFailure("unsupported input ref", details={"reason": "unsupported_input_ref"})
    return Path(ref).resolve(strict=False)


def _looks_like_local_path(ref: str) -> bool:
    if _is_windows_drive_path(ref) or ref.startswith(("file://", ".", "/", "\\")):
        return True
    return Path(ref).exists()


def _is_windows_drive_path(ref: str) -> bool:
    return len(ref) >= 3 and ref[1] == ":" and ref[0].isalpha() and ref[2] in {"\\", "/"}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
