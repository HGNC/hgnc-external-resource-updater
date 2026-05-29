"""Tests for FlyBasePipelineService end-to-end orchestration.

Validates the pipeline: discovery → version check → download →
decompress → parse → sync → record version. Uses mocked dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_external_resource_updater.flybase_client import FlyBaseFileEntry
from hgnc_external_resource_updater.models import FlyBaseRecord
from hgnc_external_resource_updater.services.flybase_pipeline_service import (
    FlyBasePipelineService,
)


def _make_service(
    version_tracker: MagicMock | None = None,
) -> tuple[FlyBasePipelineService, MagicMock, MagicMock]:
    discovery = MagicMock()
    sync = MagicMock()
    logger = MagicMock()
    svc = FlyBasePipelineService(
        discovery_client=discovery,
        sync_service=sync,
        logger=logger,
        version_tracker=version_tracker,
    )
    return svc, discovery, sync


class TestFlyBasePipelineService:
    """Test FlyBasePipelineService orchestration."""

    def test_skips_when_no_file_found(self) -> None:
        svc, discovery, sync = _make_service()
        discovery.discover_latest.return_value = None

        svc.run()

        sync.run_sync.assert_not_called()

    def test_downloads_and_syncs_when_version_is_fresh(self) -> None:
        svc, discovery, sync = _make_service()
        entry = FlyBaseFileEntry(filename="gene_groups_HGNC_fb_2024_11.tsv.gz", year=2024, month=11)
        discovery.discover_latest.return_value = entry
        discovery._build_file_url.return_value = "https://example.com/file.gz"

        records = [FlyBaseRecord(group_id="FBgg1", symbol="s", name="n", family_id=1)]
        sync.run_sync.return_value = MagicMock(fetched=1)

        with patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseClient") as mock_client_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseDecompressor") as mock_decomp_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseParser") as mock_parser_cls:

            mock_client = MagicMock()
            mock_client.fetch.return_value = "raw text"
            mock_client_cls.return_value = mock_client

            mock_decomp = MagicMock()
            mock_decomp.decompress.return_value = "decompressed"
            mock_decomp_cls.return_value = mock_decomp

            mock_parser = MagicMock()
            mock_parser.parse.return_value = records
            mock_parser_cls.return_value = mock_parser

            svc.run()

        sync.run_sync.assert_called_once_with(records)

    def test_skips_when_version_is_unchanged(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = True

        svc, discovery, sync = _make_service(version_tracker=tracker)
        entry = FlyBaseFileEntry(filename="gene_groups_HGNC_fb_2024_11.tsv.gz", year=2024, month=11)
        discovery.discover_latest.return_value = entry

        svc.run()

        tracker.should_skip.assert_called_once_with("external_resource_fbgg", "2024_11")
        sync.run_sync.assert_not_called()

    def test_records_version_after_successful_sync(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = False

        svc, discovery, sync = _make_service(version_tracker=tracker)
        entry = FlyBaseFileEntry(filename="gene_groups_HGNC_fb_2024_11.tsv.gz", year=2024, month=11)
        discovery.discover_latest.return_value = entry
        discovery._build_file_url.return_value = "https://example.com/file.gz"

        records = [FlyBaseRecord(group_id="FBgg1", symbol="s", name="n", family_id=1)]
        sync.run_sync.return_value = MagicMock(fetched=1)

        with patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseClient") as mock_client_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseDecompressor") as mock_decomp_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseParser") as mock_parser_cls:

            mock_client = MagicMock()
            mock_client.fetch.return_value = "raw text"
            mock_client_cls.return_value = mock_client

            mock_decomp = MagicMock()
            mock_decomp.decompress.return_value = "decompressed"
            mock_decomp_cls.return_value = mock_decomp

            mock_parser = MagicMock()
            mock_parser.parse.return_value = records
            mock_parser_cls.return_value = mock_parser

            svc.run()

        tracker.record_version.assert_called_once_with("external_resource_fbgg", "2024_11")

    def test_does_not_record_version_when_skipped(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = True

        svc, discovery, sync = _make_service(version_tracker=tracker)
        entry = FlyBaseFileEntry(filename="gene_groups_HGNC_fb_2024_11.tsv.gz", year=2024, month=11)
        discovery.discover_latest.return_value = entry

        svc.run()

        tracker.record_version.assert_not_called()

    def test_no_tracker_means_no_skip(self) -> None:
        svc, discovery, sync = _make_service(version_tracker=None)
        entry = FlyBaseFileEntry(filename="gene_groups_HGNC_fb_2024_11.tsv.gz", year=2024, month=11)
        discovery.discover_latest.return_value = entry
        discovery._build_file_url.return_value = "https://example.com/file.gz"

        records = [FlyBaseRecord(group_id="FBgg1", symbol="s", name="n", family_id=1)]
        sync.run_sync.return_value = MagicMock(fetched=1)

        with patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseClient") as mock_client_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseDecompressor") as mock_decomp_cls, \
             patch("hgnc_external_resource_updater.services.flybase_pipeline_service.FlyBaseParser") as mock_parser_cls:

            mock_client = MagicMock()
            mock_client.fetch.return_value = "raw text"
            mock_client_cls.return_value = mock_client

            mock_decomp = MagicMock()
            mock_decomp.decompress.return_value = "decompressed"
            mock_decomp_cls.return_value = mock_decomp

            mock_parser = MagicMock()
            mock_parser.parse.return_value = records
            mock_parser_cls.return_value = mock_parser

            svc.run()

        sync.run_sync.assert_called_once()
