"""Storage factory from configured job storage settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fmkorea_scraper.models.enums import CheckpointMode, StorageMode
from fmkorea_scraper.models.job import StorageConfig
from fmkorea_scraper.outputs.checkpoint import LocalCheckpointStore
from fmkorea_scraper.outputs.errors import StorageConfigurationError
from fmkorea_scraper.outputs.layout import OutputRunLayout
from fmkorea_scraper.outputs.local import LocalFailureStore, LocalMediaStore, LocalOutputStore
from fmkorea_scraper.outputs.s3 import S3ObjectStore


@dataclass(frozen=True)
class StorageBundle:
    output_store: Any
    failure_store: Any
    media_store: Any
    checkpoint_store: Any
    layout: OutputRunLayout


class StorageFactory:
    @classmethod
    def create(
        cls,
        config: StorageConfig,
        *,
        job_id: str,
        run_id: str,
        s3_client: Any | None = None,
    ) -> StorageBundle:
        layout = OutputRunLayout(
            job_id,
            run_id,
            base_output_path=config.base_output_path,
            s3_prefix=config.s3.prefix if config.s3 else None,
        )
        checkpoint_store = cls._checkpoint_store(config, layout)
        if config.output_mode == StorageMode.LOCAL:
            return StorageBundle(
                output_store=LocalOutputStore(layout),
                failure_store=LocalFailureStore(layout),
                media_store=LocalMediaStore(layout),
                checkpoint_store=checkpoint_store,
                layout=layout,
            )
        if config.output_mode == StorageMode.S3_COMPATIBLE:
            if config.s3 is None:
                raise StorageConfigurationError("s3 config is required when output_mode is s3_compatible")
            s3_store = S3ObjectStore(layout, config.s3, client=s3_client)
            return StorageBundle(
                output_store=s3_store,
                failure_store=s3_store,
                media_store=s3_store,
                checkpoint_store=checkpoint_store,
                layout=layout,
            )
        raise StorageConfigurationError(f"unsupported output mode: {config.output_mode}")

    @staticmethod
    def _checkpoint_store(config: StorageConfig, layout: OutputRunLayout) -> LocalCheckpointStore:
        if config.checkpoint_mode == CheckpointMode.LOCAL:
            return LocalCheckpointStore(layout)
        raise StorageConfigurationError("postgres checkpoint storage is deferred beyond UOW-006")


__all__ = ["StorageBundle", "StorageFactory"]
