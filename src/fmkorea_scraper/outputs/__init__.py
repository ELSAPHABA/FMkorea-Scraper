"""Output and storage package."""

from fmkorea_scraper.outputs.checkpoint import LocalCheckpointDocument, LocalCheckpointStore
from fmkorea_scraper.outputs.errors import (
    OutputStorageError,
    PathTraversalError,
    StorageConfigurationError,
    StorageReadError,
    StorageWriteError,
)
from fmkorea_scraper.outputs.factory import StorageBundle, StorageFactory
from fmkorea_scraper.outputs.jsonl import AtomicJsonWriter, JsonlWriter
from fmkorea_scraper.outputs.layout import OutputRunLayout, ensure_under_base, sanitize_path_segment
from fmkorea_scraper.outputs.local import LocalFailureStore, LocalMediaStore, LocalOutputStore
from fmkorea_scraper.outputs.postgres_checkpoint import PostgresCheckpointStore
from fmkorea_scraper.outputs.redaction import sanitize_failure_context
from fmkorea_scraper.outputs.s3 import S3JsonlSpool, S3ObjectStore
from fmkorea_scraper.outputs.s3_output import S3OutputStore, S3Spool

__all__ = [
    "AtomicJsonWriter",
    "JsonlWriter",
    "LocalCheckpointDocument",
    "LocalCheckpointStore",
    "LocalFailureStore",
    "LocalMediaStore",
    "LocalOutputStore",
    "OutputRunLayout",
    "OutputStorageError",
    "PathTraversalError",
    "PostgresCheckpointStore",
    "S3JsonlSpool",
    "S3ObjectStore",
    "S3OutputStore",
    "S3Spool",
    "StorageBundle",
    "StorageConfigurationError",
    "StorageFactory",
    "StorageReadError",
    "StorageWriteError",
    "ensure_under_base",
    "sanitize_failure_context",
    "sanitize_path_segment",
]
