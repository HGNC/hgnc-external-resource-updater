"""FlyBase feed parser and normalizer.

Parses raw TSV content from FlyBase group feeds into FlyBaseRawRecord
models, then normalizes them into domain ExternalResource entities.
"""

from __future__ import annotations

import gzip
import logging

from hgnc_external_resource_updater.exceptions import ParseError
from hgnc_external_resource_updater.flybase_models import FlyBaseRawRecord
from hgnc_external_resource_updater.models import ExternalResource

logger = logging.getLogger(__name__)

_GZIP_MAGIC = b"\x1f\x8b"


class FlyBaseDecompressor:
    """Decompress FlyBase feed data with double-gzip detection.

    Checks for gzip magic bytes at the start of data. If present,
    decompresses once and checks again for double-gzip. Returns
    UTF-8 decoded text.
    """

    @staticmethod
    def is_gzip(data: bytes) -> bool:
        """Check whether data starts with gzip magic bytes.

        Args:
            data: The raw bytes to inspect.

        Returns:
            True if the first two bytes are ``0x1f 0x8b``.
        """
        return len(data) >= 2 and data[:2] == _GZIP_MAGIC

    @staticmethod
    def decompress(data: bytes) -> str:
        """Decompress data, handling single or double gzip.

        Args:
            data: Raw bytes that may be gzip-compressed (once or twice)
                or plain text.

        Returns:
            The decompressed UTF-8 string.

        Raises:
            Exception: If gzip decompression fails on invalid data.
        """
        if not data:
            return ""

        if not FlyBaseDecompressor.is_gzip(data):
            return data.decode("utf-8")

        first_pass = gzip.decompress(data)

        if FlyBaseDecompressor.is_gzip(first_pass):
            second_pass = gzip.decompress(first_pass)
            return second_pass.decode("utf-8")

        return first_pass.decode("utf-8")


class FlyBaseParser:
    """Parse raw FlyBase TSV feed content into structured records.

    Handles malformed rows by logging a warning and skipping them.
    """

    def parse(self, raw: str) -> list[FlyBaseRawRecord]:
        """Parse raw TSV content into a list of FlyBaseRawRecord models.

        Args:
            raw: The raw TSV content from the FlyBase feed.

        Returns:
            A list of validated FlyBaseRawRecord instances.

        Raises:
            ParseError: If the feed is empty or entirely unparseable.
        """
        if not raw or not raw.strip():
            raise ParseError("FlyBase feed is empty")

        records: list[FlyBaseRawRecord] = []
        skipped = 0

        for line_no, line in enumerate(raw.strip().splitlines(), start=1):
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                logger.warning("Skipping malformed row %d: %s", line_no, line)
                skipped += 1
                continue

            try:
                record = FlyBaseRawRecord(
                    flybase_id=parts[0],
                    hgnc_id=parts[1],
                    gene_symbol=parts[2] if len(parts) > 2 else "",
                    url=parts[3] if len(parts) > 3 else "",
                )
                records.append(record)
            except Exception:
                logger.warning("Skipping invalid row %d: %s", line_no, line)
                skipped += 1

        if not records and skipped > 0:
            raise ParseError(
                f"All {skipped} rows were malformed or invalid"
            )

        return records


def normalize(raw: FlyBaseRawRecord) -> ExternalResource:
    """Normalize a raw FlyBase record into a domain ExternalResource.

    Args:
        raw: The raw FlyBase record.

    Returns:
        A normalized ExternalResource domain entity.
    """
    return ExternalResource(
        source_db="flybase",
        resource_id=raw.flybase_id,
        hgnc_id=raw.hgnc_id,
        display_name=raw.gene_symbol,
        url=raw.url,
    )


def normalize_batch(records: list[FlyBaseRawRecord]) -> list[ExternalResource]:
    """Normalize a batch of raw FlyBase records into domain entities.

    Args:
        records: The raw FlyBase records.

    Returns:
        A list of normalized ExternalResource domain entities.
    """
    return [normalize(r) for r in records]
