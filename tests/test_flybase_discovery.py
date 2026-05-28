"""Tests for FlyBase file discovery client (Task 37.2).

Verify that FlyBaseClient discovers the latest gene_groups file from
directory listing HTML, parses version from filename, and handles edge
cases like no matches or malformed filenames.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_external_resource_updater.flybase_client import FlyBaseDiscoveryClient


_SAMPLE_DIRECTORY_HTML = """
<html><body>
<a href="gene_groups_HGNC_fb_2024_01.tsv.gz">Jan 2024</a>
<a href="gene_groups_HGNC_fb_2024_06.tsv.gz">Jun 2024</a>
<a href="gene_groups_HGNC_fb_2023_12.tsv.gz">Dec 2023</a>
<a href="other_file.txt">Other</a>
</body></html>
"""

_SAMPLE_DIRECTORY_HTML_SINGLE = """
<html><body>
<a href="gene_groups_HGNC_fb_2025_03.tsv.gz">Mar 2025</a>
</body></html>
"""

_SAMPLE_DIRECTORY_HTML_NO_MATCH = """
<html><body>
<a href="something_else.txt">Other</a>
</body></html>
"""


class TestFlyBaseDiscoveryClient:
    """Test FlyBase file discovery and version extraction."""

    def test_selects_latest_file_from_multiple(self) -> None:
        client = FlyBaseDiscoveryClient()
        result = client._parse_directory_listing(_SAMPLE_DIRECTORY_HTML)
        assert result is not None
        assert result.filename == "gene_groups_HGNC_fb_2024_06.tsv.gz"
        assert result.year == 2024
        assert result.month == 6

    def test_selects_only_file_when_single_match(self) -> None:
        client = FlyBaseDiscoveryClient()
        result = client._parse_directory_listing(_SAMPLE_DIRECTORY_HTML_SINGLE)
        assert result is not None
        assert result.filename == "gene_groups_HGNC_fb_2025_03.tsv.gz"
        assert result.year == 2025
        assert result.month == 3

    def test_returns_none_when_no_matches(self) -> None:
        client = FlyBaseDiscoveryClient()
        result = client._parse_directory_listing(_SAMPLE_DIRECTORY_HTML_NO_MATCH)
        assert result is None

    def test_extracts_version_from_filename(self) -> None:
        client = FlyBaseDiscoveryClient()
        version = client._extract_version("gene_groups_HGNC_fb_2024_11.tsv.gz")
        assert version == "2024_11"

    def test_builds_correct_url(self) -> None:
        client = FlyBaseDiscoveryClient()
        url = client._build_file_url("gene_groups_HGNC_fb_2024_06.tsv.gz")
        assert "s3ftp.flybase.org" in url
        assert "gene_groups_HGNC_fb_2024_06.tsv.gz" in url
        assert url.startswith("https://")

    @patch("hgnc_external_resource_updater.flybase_client.httpx.Client")
    def test_discover_latest_calls_http_and_parses(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = _SAMPLE_DIRECTORY_HTML
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = FlyBaseDiscoveryClient()
        result = client.discover_latest()

        assert result is not None
        assert result.filename == "gene_groups_HGNC_fb_2024_06.tsv.gz"
