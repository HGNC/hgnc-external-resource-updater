"""Domain models for FlyBase external resource sync.

Defines Pydantic models for external_resource and
family_has_external_resource records consumed by the sync service
and repository layers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExternalResource(BaseModel):
    """Represent a single external_resource record from a FlyBase feed.

    Attributes:
        source_db: The external database source identifier (e.g. "flybase").
        resource_id: The external resource's unique identifier (e.g. "FBgn0001234").
        hgnc_id: The HGNC identifier linking this resource to a gene (e.g. "HGNC:12345").
        display_name: Human-readable display name for the resource link.
        url: URL to the external resource page.
    """

    source_db: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    hgnc_id: str = Field(min_length=1)
    display_name: str = Field(default="")
    url: str = Field(default="")


class FamilyExternalResourceLink(BaseModel):
    """Represent a family_has_external_resource link record.

    Attributes:
        hgnc_id: The HGNC identifier for the gene family.
        resource_id: The external resource identifier being linked.
        source_db: The external database source identifier.
    """

    hgnc_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    source_db: str = Field(min_length=1)
