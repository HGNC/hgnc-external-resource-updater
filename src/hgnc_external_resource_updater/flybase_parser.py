"""FlyBase feed parser, decompressor, and normalizer.

Parses raw TSV content from FlyBase gene group feeds into FlyBaseRecord
models, handles double-gzip decompression, and normalizes records into
ExternalResource entities matching the actual genew4 schema.
"""

from __future__ import annotations

import gzip
import logging
import re

from hgnc_external_resource_updater.exceptions import ParseError
from hgnc_external_resource_updater.models import (
    ExternalResource,
    FamilyLink,
    FlyBaseRecord,
)

logger = logging.getLogger(__name__)

_GZIP_MAGIC = b"\x1f\x8b"

_HGNC_ID_FIX: dict[int, int] = {
    19082: 283,
}


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

    Handles header skipping, malformed rows, and the HGNC ID
    correction (19082 → 283).
    """

    HEADER_LINES = 9

    def parse(self, raw: str) -> list[FlyBaseRecord]:
        """Parse raw TSV content into a list of FlyBaseRecord models.

        Args:
            raw: The decompressed TSV content from the FlyBase feed.

        Returns:
            A list of validated FlyBaseRecord instances.

        Raises:
            ParseError: If the feed is empty or entirely unparseable.
        """
        if not raw or not raw.strip():
            raise ParseError("FlyBase feed is empty")

        records: list[FlyBaseRecord] = []
        skipped = 0

        for line_no, line in enumerate(raw.strip().splitlines(), start=1):
            if line_no <= self.HEADER_LINES:
                continue

            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 4:
                logger.warning("Skipping malformed row %d: %s", line_no, line)
                skipped += 1
                continue

            try:
                hgnc_id = int(parts[3].strip())
                hgnc_id = _HGNC_ID_FIX.get(hgnc_id, hgnc_id)
                records.append(
                    FlyBaseRecord(
                        group_id=parts[0].strip(),
                        symbol=parts[1].strip(),
                        name=parts[2].strip(),
                        family_id=hgnc_id,
                    )
                )
            except (ValueError, IndexError):
                logger.warning("Skipping invalid row %d: %s", line_no, line)
                skipped += 1

        if not records and skipped > 0:
            raise ParseError(
                f"All {skipped} rows were malformed or invalid"
            )

        return records


def normalize_to_resource(record: FlyBaseRecord, ext_id: int) -> ExternalResource:
    """Convert a FlyBaseRecord to an ExternalResource with constructed URL.

    Args:
        record: The parsed FlyBase record.
        ext_id: The external resource ID to assign.

    Returns:
        An ExternalResource ready for persistence.
    """
    url = f"http://flybase.org/reports/{record.group_id}.html"
    name = f"FlyBase gene group: {record.name}"
    return ExternalResource(ext_id=ext_id, name=name, url=url)


def normalize_to_link(record: FlyBaseRecord, ext_id: int) -> FamilyLink:
    """Convert a FlyBaseRecord to a FamilyLink.

    Args:
        record: The parsed FlyBase record.
        ext_id: The external resource ID to link.

    Returns:
        A FamilyLink ready for persistence.
    """
    return FamilyLink(family_id=record.family_id, ext_id=ext_id)
