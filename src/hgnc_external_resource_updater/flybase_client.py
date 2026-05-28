"""FlyBase feed client for fetching group feed data.

Retrieves raw TSV feed content from a configurable URL using httpx.
Also provides directory-listing-based discovery of the latest FlyBase
HGNC gene group file from s3ftp.flybase.org.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from hgnc_external_resource_updater.exceptions import FetchError

logger = logging.getLogger(__name__)

_BASE_HOST = "s3ftp.flybase.org"
_BASE_PATH = "/releases/current/precomputed_files/genes/"
_FILE_PATTERN = re.compile(
    r"gene_groups_HGNC_fb_(\d{4})_(\d{2})\.tsv\.gz"
)


@dataclass
class FlyBaseFileEntry:
    """A discovered FlyBase gene group file.

    Attributes:
        filename: The filename on the remote server.
        year: The year extracted from the filename.
        month: The month extracted from the filename.
    """

    filename: str
    year: int
    month: int


class FlyBaseDiscoveryClient:
    """Discover and select the latest FlyBase HGNC gene group file.

    Connects to ``s3ftp.flybase.org``, fetches the directory listing
    for the precomputed gene files path, parses out all files matching
    the ``gene_groups_HGNC_fb_YYYY_MM.tsv.gz`` pattern, and selects
    the one with the latest year/month.

    Args:
        base_url: Optional override for the base HTTPS URL.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or f"https://{_BASE_HOST}{_BASE_PATH}"

    def discover_latest(self) -> FlyBaseFileEntry | None:
        """Fetch the directory listing and return the latest file entry.

        Returns:
            A ``FlyBaseFileEntry`` for the most recent file, or ``None``
            if no matching files are found.

        Raises:
            FetchError: If the directory listing cannot be retrieved.
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self._base_url)
                response.raise_for_status()
                html = response.text
        except Exception as exc:
            raise FetchError(
                f"Failed to fetch FlyBase directory listing from "
                f"{self._base_url}: {exc}"
            ) from exc

        return self._parse_directory_listing(html)

    def _parse_directory_listing(self, html: str) -> FlyBaseFileEntry | None:
        """Parse HTML directory listing and return the latest matching file.

        Args:
            html: The raw HTML of the directory listing page.

        Returns:
            The latest ``FlyBaseFileEntry``, or ``None`` if no matches.
        """
        matches: list[FlyBaseFileEntry] = []
        for match in _FILE_PATTERN.finditer(html):
            year = int(match.group(1))
            month = int(match.group(2))
            filename = match.group(0)
            matches.append(
                FlyBaseFileEntry(filename=filename, year=year, month=month)
            )

        if not matches:
            logger.warning("No FlyBase gene group files found in listing")
            return None

        matches.sort(key=lambda e: (e.year, e.month), reverse=True)
        latest = matches[0]
        logger.info(
            "flybase_discover_latest",
            extra={
                "event": "flybase_discover_latest",
                "filename": latest.filename,
                "year": latest.year,
                "month": latest.month,
            },
        )
        return latest

    def _extract_version(self, filename: str) -> str:
        """Extract the version string (YYYY_MM) from a filename.

        Args:
            filename: A FlyBase gene group filename.

        Returns:
            The version string, e.g. ``"2024_11"``.
        """
        match = _FILE_PATTERN.search(filename)
        if match:
            return f"{match.group(1)}_{match.group(2)}"
        return ""

    def _build_file_url(self, filename: str) -> str:
        """Construct the full download URL for a given filename.

        Args:
            filename: The filename on the remote server.

        Returns:
            The full HTTPS URL.
        """
        return f"https://{_BASE_HOST}{_BASE_PATH}{filename}"


class FlyBaseClient:
    """Fetch raw FlyBase group feed content from a remote URL.

    Args:
        feed_url: The URL of the FlyBase TSV feed.
    """

    def __init__(self, feed_url: str) -> None:
        self._feed_url = feed_url

    def fetch(self) -> str:
        """Fetch the raw feed content from the configured URL.

        Returns:
            The raw TSV content as a string.

        Raises:
            FetchError: If the HTTP request fails.
        """
        try:
            with httpx.Client() as client:
                response = client.get(self._feed_url)
                response.raise_for_status()
                return response.text
        except Exception as exc:
            raise FetchError(
                f"Failed to fetch FlyBase feed from {self._feed_url}: {exc}"
            ) from exc
