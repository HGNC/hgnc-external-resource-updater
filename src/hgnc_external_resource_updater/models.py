"""Domain models for FlyBase external resource sync.

Defines data structures matching the actual genew4 schema used by
the Perl updater: external_resource(id, name, url) and
family_has_external_resource(family_id, ext_id).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FlyBaseRecord(BaseModel):
    """A parsed FlyBase gene group record.

    Attributes:
        group_id: FlyBase gene group identifier (e.g. FBgg00001).
        symbol: Gene group symbol.
        name: Gene group name.
        family_id: HGNC gene family ID (HGNC ID for the group).
    """

    group_id: str = Field(min_length=1)
    symbol: str = Field(default="")
    name: str = Field(default="")
    family_id: int = Field(gt=0)


class ExternalResource(BaseModel):
    """Represent a row in the external_resource table.

    Attributes:
        ext_id: The auto-incremented primary key.
        name: Display name for the resource.
        url: URL to the external resource page.
    """

    ext_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)


class FamilyLink(BaseModel):
    """Represent a row in family_has_external_resource.

    Attributes:
        family_id: HGNC gene family ID.
        ext_id: External resource ID.
    """

    family_id: int = Field(gt=0)
    ext_id: int = Field(gt=0)
