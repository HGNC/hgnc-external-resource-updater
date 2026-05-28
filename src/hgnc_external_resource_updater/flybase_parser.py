"""FlyBase feed parser and normalizer.

Parses raw TSV content from FlyBase group feeds into FlyBaseRawRecord
models, then normalizes them into domain ExternalResource entities.
"""

from __future__ import annotations

import logging

from hgnc_external_resource_updater.exceptions import ParseError
from hgnc_external_resource_updater.flybase_models import FlyBaseRawRecord
from hgnc_external_resource_updater.models import ExternalResource

logger = logging.getLogger(__name__)


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
