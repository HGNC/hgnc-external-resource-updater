"""Abstract repository interface for FlyBase external resource operations.

Defines the contract that concrete Postgres repository implementations
must fulfil for upserting, deleting, and querying external_resource
and family_has_external_resource records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hgnc_external_resource_updater.models import (
    ExternalResource,
    FamilyExternalResourceLink,
)


class ExternalResourceRepository(ABC):
    """Define the persistence contract for FlyBase external resource sync.

    All methods are batch-oriented to minimise round-trips. Implementations
    must ensure idempotency: re-running with the same input yields no net
    changes to the database.
    """

    @abstractmethod
    def get_existing_by_source(
        self, source_db: str
    ) -> list[ExternalResource]:
        """Return all external_resource records for the given source.

        Args:
            source_db: The external database source identifier.

        Returns:
            A list of existing ExternalResource records.
        """

    @abstractmethod
    def upsert_external_resources(
        self, records: list[ExternalResource]
    ) -> int:
        """Insert or update external_resource records.

        Args:
            records: The records to upsert.

        Returns:
            The number of rows affected.
        """

    @abstractmethod
    def delete_external_resources(
        self, source_db: str, resource_ids: list[str]
    ) -> int:
        """Delete external_resource records by source and resource IDs.

        Args:
            source_db: The external database source identifier.
            resource_ids: The resource IDs to delete.

        Returns:
            The number of rows deleted.
        """

    @abstractmethod
    def upsert_family_links(
        self, links: list[FamilyExternalResourceLink]
    ) -> int:
        """Insert or update family_has_external_resource links.

        Args:
            links: The link records to upsert.

        Returns:
            The number of rows affected.
        """

    @abstractmethod
    def delete_family_links(
        self, source_db: str, resource_ids: list[str]
    ) -> int:
        """Delete family_has_external_resource links by source and resource IDs.

        Args:
            source_db: The external database source identifier.
            resource_ids: The resource IDs whose links should be deleted.

        Returns:
            The number of rows deleted.
        """
