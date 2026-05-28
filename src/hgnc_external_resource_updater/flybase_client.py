"""FlyBase feed client for fetching group feed data.

Retrieves raw TSV feed content from a configurable URL using httpx.
"""

from __future__ import annotations

import logging

import httpx

from hgnc_external_resource_updater.exceptions import FetchError

logger = logging.getLogger(__name__)


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
