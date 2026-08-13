"""PostgreSQL-backed checkpoint store."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import anyio

from fmkorea_scraper.core.errors import CheckpointFailureError
from fmkorea_scraper.models.checkpoint import Checkpoint

ConnectionFactory = Callable[[str], Any]


class PostgresCheckpointStore:
    def __init__(self, dsn: str, *, connection_factory: ConnectionFactory | None = None) -> None:
        self.dsn = dsn
        self._connection_factory = connection_factory or _connect

    async def save(self, checkpoint: Checkpoint) -> None:
        await anyio.to_thread.run_sync(self._save_sync, checkpoint)

    async def load(self, job_id: str) -> Checkpoint | None:
        return await anyio.to_thread.run_sync(self._load_sync, job_id)

    async def load_latest(self) -> Checkpoint | None:
        return await anyio.to_thread.run_sync(self._load_latest_sync)

    def _save_sync(self, checkpoint: Checkpoint) -> None:
        document = json.dumps(checkpoint.model_dump(mode="json"), ensure_ascii=False, allow_nan=False)
        self._execute(
            """
            insert into fmkorea_checkpoints (job_id, updated_at, checkpoint_json)
            values (%s, %s, %s::jsonb)
            on conflict (job_id) do update set
              updated_at = excluded.updated_at,
              checkpoint_json = excluded.checkpoint_json
            """,
            (checkpoint.job_id, checkpoint.updated_at, document),
        )

    def _load_sync(self, job_id: str) -> Checkpoint | None:
        row = self._fetchone("select checkpoint_json from fmkorea_checkpoints where job_id = %s", (job_id,))
        return _checkpoint_from_row(row)

    def _load_latest_sync(self) -> Checkpoint | None:
        row = self._fetchone("select checkpoint_json from fmkorea_checkpoints order by updated_at desc limit 1", ())
        return _checkpoint_from_row(row)

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        try:
            with self._connection_factory(self.dsn) as connection:
                self._ensure_schema(connection)
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
        except Exception as exc:
            raise CheckpointFailureError(
                "postgres checkpoint write failed",
                details={"stage": "checkpoint", "reason": exc.__class__.__name__},
            ) from exc

    def _fetchone(self, sql: str, params: tuple[Any, ...]) -> Any | None:
        try:
            with self._connection_factory(self.dsn) as connection:
                self._ensure_schema(connection)
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchone()
        except Exception as exc:
            raise CheckpointFailureError(
                "postgres checkpoint load failed",
                details={"stage": "checkpoint", "reason": exc.__class__.__name__},
            ) from exc

    @staticmethod
    def _ensure_schema(connection: Any) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                create table if not exists fmkorea_checkpoints (
                  job_id text primary key,
                  updated_at timestamptz not null,
                  checkpoint_json jsonb not null
                )
                """
            )


def _connect(dsn: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise CheckpointFailureError(
            "postgres extra is required",
            details={"stage": "checkpoint", "reason": "missing_postgres_dependency"},
        ) from exc
    return psycopg.connect(dsn)


def _checkpoint_from_row(row: Any | None) -> Checkpoint | None:
    if row is None:
        return None
    raw = row[0] if isinstance(row, (tuple, list)) else row
    if isinstance(raw, str):
        raw = json.loads(raw)
    return Checkpoint.model_validate(raw)
