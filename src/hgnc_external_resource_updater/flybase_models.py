"""Pydantic models representing raw FlyBase feed records.

These models mirror the raw TSV schema of the FlyBase group feed
before normalisation into domain entities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FlyBaseRawRecord(BaseModel):
    """Represent a single raw record from a FlyBase group feed.

    Attributes:
        flybase_id: FlyBase identifier (e.g. "FBgn0001234").
        hgnc_id: HGNC identifier (e.g. "HGNC:12345").
        gene_symbol: Human-readable gene symbol (e.g. "BRCA1").
        url: URL to the FlyBase record page.
    """

    flybase_id: str = Field(min_length=1)
    hgnc_id: str = Field(min_length=1)
    gene_symbol: str = Field(default="")
    url: str = Field(default="")
