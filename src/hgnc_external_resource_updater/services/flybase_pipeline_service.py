"""FlyBase end-to-end pipeline service.

Orchestrates discovery, download, decompression, parsing, sync, and
version tracking into a single workflow. The pipeline:

1. Discover the latest FlyBase gene group file
2. Extract the version string (YYYY_MM)
3. Check version staleness via version_tracker
4. If fresh: download, decompress, parse, sync
5. Record the new version after successful sync

If version_tracker indicates the version is unchanged, the pipeline
skips the download and sync steps entirely.
"""

from __future__ import annotations

import logging

from hgnc_external_resource_updater.exceptions import FetchError
from hgnc_external_resource_updater.flybase_client import (
    FlyBaseClient,
    FlyBaseDiscoveryClient,
)
from hgnc_external_resource_updater.flybase_parser import (
    FlyBaseDecompressor,
    FlyBaseParser,
)
from hgnc_external_resource_updater.services.flybase_sync_service import (
    FlyBaseSyncService,
)


class FlyBasePipelineService:
    """Orchestrate the full FlyBase discovery-to-sync pipeline.

    Args:
        discovery_client: Client for discovering the latest FlyBase file.
        sync_service: Service for syncing parsed records to the database.
        logger: Logger for structured output.
        version_tracker: Optional version tracker for staleness checks.
    """

    _TABLE_NAME = "external_resource_fbgg"

    def __init__(
        self,
        discovery_client: FlyBaseDiscoveryClient,
        sync_service: FlyBaseSyncService,
        logger: logging.Logger,
        version_tracker: object | None = None,
    ) -> None:
        self._discovery = discovery_client
        self._sync = sync_service
        self._logger = logger
        self._version_tracker = version_tracker

    def run(self) -> None:
        """Execute the full FlyBase pipeline.

        Discovers the latest file, checks version staleness, downloads,
        decompresses, parses, and syncs. Records version on success.

        Raises:
            FetchError: If discovery or download fails.
        """
        entry = self._discovery.discover_latest()
        if entry is None:
            self._logger.warning("flybase_pipeline_no_file_found")
            return

        version = f"{entry.year}_{entry.month:02d}"

        if self._should_skip(version):
            self._logger.info(
                "flybase_pipeline_skipped",
                extra={"version": version},
            )
            return

        file_url = self._discovery._build_file_url(entry.filename)
        client = FlyBaseClient(feed_url=file_url)
        raw_text = client.fetch()

        decompressor = FlyBaseDecompressor()
        decompressed = decompressor.decompress(raw_text.encode("utf-8"))

        parser = FlyBaseParser()
        records = parser.parse(decompressed)

        self._sync.run_sync(records)
        self._record_version(version)

        self._logger.info(
            "flybase_pipeline_complete",
            extra={"version": version, "records": len(records)},
        )

    def _should_skip(self, version: str) -> bool:
        """Check whether the pipeline should skip due to unchanged version.

        Args:
            version: The version string to check.

        Returns:
            True if the version is unchanged and the run should be skipped.
        """
        if self._version_tracker is None:
            return False
        return self._version_tracker.should_skip(self._TABLE_NAME, version)

    def _record_version(self, version: str) -> None:
        """Record the new version after a successful sync.

        Args:
            version: The version string to record.
        """
        if self._version_tracker is None:
            return
        self._version_tracker.record_version(self._TABLE_NAME, version)
