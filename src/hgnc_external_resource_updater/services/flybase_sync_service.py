"""FlyBase sync service orchestrating the fetch/parse/normalize/diff/apply lifecycle.

Coordinates the full sync flow: fetches the FlyBase feed, parses and
normalizes records, diffs against current DB state, computes upsert/delete
changesets, applies them, and emits structured summary metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from hgnc_external_resource_updater.flybase_parser import normalize_batch
from hgnc_external_resource_updater.models import ExternalResource
from hgnc_external_resource_updater.repositories.external_resource_repository import (
    ExternalResourceRepository,
)

if __name__ == "__main__":  # pragma: no cover
    pass
else:
    from hgnc_external_resource_updater.flybase_client import FlyBaseClient
    from hgnc_external_resource_updater.flybase_parser import FlyBaseParser


@dataclass
class SyncResult:
    """Structured summary of a FlyBase sync run.

    Attributes:
        fetched: Total records fetched from the feed.
        upserted: Records inserted or updated.
        deleted: Records removed from the database.
        unchanged: Records that matched existing data exactly.
    """

    fetched: int = 0
    upserted: int = 0
    deleted: int = 0
    unchanged: int = 0


class FlyBaseSyncService:
    """Orchestrate the FlyBase external resource sync lifecycle.

    Accepts a FlyBaseClient, FlyBaseParser, and ExternalResourceRepository
    via constructor injection. Computes deterministic changesets for upserts
    and deletes, ensuring idempotency.

    Args:
        client: FlyBase feed client for fetching raw data.
        parser: FlyBase parser for converting raw TSV to records.
        repository: Repository for querying and persisting external resources.
        logger: Logger for emitting structured metrics.
    """

    SOURCE_DB = "flybase"

    def __init__(
        self,
        client: FlyBaseClient,
        parser: FlyBaseParser,
        repository: ExternalResourceRepository,
        logger: logging.Logger,
    ) -> None:
        self._client = client
        self._parser = parser
        self._repository = repository
        self._logger = logger

    def run_sync(self) -> SyncResult:
        """Execute the full FlyBase sync lifecycle.

        Returns:
            A SyncResult with counts of fetched, upserted, deleted, and
            unchanged records.

        Raises:
            FetchError: If the feed cannot be fetched.
            ParseError: If the feed cannot be parsed.
            PersistenceError: If database operations fail.
        """
        self._logger.info(
            "sync_start",
            extra={"event": "sync_start", "source": self.SOURCE_DB},
        )

        start = time.monotonic()
        try:
            raw = self._client.fetch()
            parsed = self._parser.parse(raw)
            new_records = normalize_batch(parsed)
            existing = self._repository.get_existing_by_source(self.SOURCE_DB)
            result = self._compute_and_apply(new_records, existing)
        finally:
            elapsed = time.monotonic() - start

        self._logger.info(
            "sync_complete",
            extra={
                "event": "sync_complete",
                "source": self.SOURCE_DB,
                "fetched": result.fetched,
                "upserted": result.upserted,
                "deleted": result.deleted,
                "unchanged": result.unchanged,
                "duration_seconds": round(elapsed, 3),
            },
        )

        return result

    def _compute_and_apply(
        self,
        new_records: list[ExternalResource],
        existing: list[ExternalResource],
    ) -> SyncResult:
        """Compute the changeset between new and existing records and apply it.

        Args:
            new_records: Normalized records from the latest feed.
            existing: Current records from the database.

        Returns:
            A SyncResult summarising the changes applied.
        """
        new_ids = {r.resource_id for r in new_records}
        existing_ids = {r.resource_id for r in existing}

        to_upsert = [r for r in new_records if r.resource_id not in existing_ids]
        to_delete = [rid for rid in existing_ids if rid not in new_ids]
        unchanged_count = len(new_ids & existing_ids)

        if to_upsert:
            self._repository.upsert_external_resources(to_upsert)

        if to_delete:
            self._repository.delete_external_resources(self.SOURCE_DB, to_delete)

        return SyncResult(
            fetched=len(new_records),
            upserted=len(to_upsert),
            deleted=len(to_delete),
            unchanged=unchanged_count,
        )
