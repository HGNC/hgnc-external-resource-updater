"""FlyBase sync service orchestrating the fetch/parse/sync lifecycle.

Coordinates the full sync flow matching the Perl FlyBase.pm behaviour:
fetches the FlyBase feed, decompresses, parses, syncs external_resource
and family_has_external_resource tables, and cleans up retired groups.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

from hgnc_external_resource_updater.flybase_parser import (
    FlyBaseParser,
    normalize_to_link,
    normalize_to_resource,
)
from hgnc_external_resource_updater.models import FlyBaseRecord
from hgnc_external_resource_updater.repositories.external_resource_repository import (
    ExternalResourceRepository,
)

_FBGG_PATTERN = re.compile(r"(FBgg\d+)")


@dataclass
class SyncResult:
    """Structured summary of a FlyBase sync run.

    Attributes:
        fetched: Total records parsed from the feed.
        upserted: External resources inserted or updated.
        deleted: External resources removed (retired groups).
        linked: Family links created.
    """

    fetched: int = 0
    upserted: int = 0
    deleted: int = 0
    linked: int = 0


class FlyBaseSyncService:
    """Orchestrate the FlyBase external resource sync lifecycle.

    Accepts a repository via constructor injection. Implements the
    same algorithm as the Perl FlyBase.pm: for each parsed record,
    checks if the URL already exists, updates or inserts as needed,
    re-creates the family link, and then removes retired FlyBase
    groups no longer present in the feed.

    Args:
        repository: Repository for querying and persisting external resources.
        logger: Logger for emitting structured metrics.
    """

    SOURCE_DB = "flybase"

    def __init__(
        self,
        repository: ExternalResourceRepository,
        logger: logging.Logger,
    ) -> None:
        self._repository = repository
        self._logger = logger

    def run_sync(self, records: list[FlyBaseRecord]) -> SyncResult:
        """Execute the full FlyBase sync lifecycle.

        Args:
            records: Parsed and validated FlyBase records.

        Returns:
            A SyncResult with counts of upserted, deleted, and linked records.
        """
        self._logger.info(
            "sync_start",
            extra={"event": "sync_start", "source": self.SOURCE_DB},
        )

        start = time.monotonic()
        try:
            result = self._sync_records(records)
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
                "linked": result.linked,
                "duration_seconds": round(elapsed, 3),
            },
        )

        return result

    def _sync_records(self, records: list[FlyBaseRecord]) -> SyncResult:
        """Sync records against the database, matching Perl behaviour.

        Args:
            records: Parsed FlyBase records.

        Returns:
            A SyncResult summarising the changes.
        """
        new_fb_ids: set[str] = set()
        upserted = 0
        linked = 0

        next_id = self._repository.get_max_ext_id() + 1

        for record in records:
            new_fb_ids.add(record.group_id)
            resource = normalize_to_resource(record, 0)
            link = normalize_to_link(record, 0)

            existing_id = self._repository.find_by_url(resource.url)
            if existing_id is not None:
                self._repository.update_name(existing_id, resource.name)
                self._repository.delete_family_links(existing_id)
                ext_id = existing_id
            else:
                ext_id = next_id
                next_id += 1
                self._repository.insert_resource(
                    ext_id, resource.name, resource.url
                )
                upserted += 1

            self._repository.insert_family_link(record.family_id, ext_id)
            linked += 1

        deleted = self._remove_retired_groups(new_fb_ids)

        return SyncResult(
            fetched=len(records),
            upserted=upserted,
            deleted=deleted,
            linked=linked,
        )

    def _remove_retired_groups(self, current_ids: set[str]) -> int:
        """Remove FlyBase external resources no longer in the feed.

        Args:
            current_ids: Set of FBgg IDs present in the current feed.

        Returns:
            The number of retired groups deleted.
        """
        deleted = 0
        flybase_rows = self._repository.get_all_flybase_urls()

        for ext_id, url in flybase_rows:
            match = _FBGG_PATTERN.search(url)
            if match is None:
                continue
            fb_id = match.group(1)
            if fb_id not in current_ids:
                self._logger.info(
                    "retire_flybase_group",
                    extra={
                        "event": "retire_flybase_group",
                        "fb_id": fb_id,
                        "ext_id": ext_id,
                    },
                )
                self._repository.delete_family_links(ext_id)
                self._repository.delete_resource(ext_id)
                deleted += 1

        return deleted
