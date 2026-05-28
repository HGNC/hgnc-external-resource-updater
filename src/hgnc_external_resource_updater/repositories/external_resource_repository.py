"""Abstract repository interface for FlyBase external resource operations.

Defines the contract for the real genew4 schema:
external_resource(id, name, url) and
family_has_external_resource(family_id, ext_id).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hgnc_external_resource_updater.models import (
    ExternalResource,
    FamilyLink,
    FlyBaseRecord,
)


class ExternalResourceRepository(ABC):
    """Define the persistence contract for FlyBase external resource sync.

    All methods are batch-oriented. Implementations must ensure
    idempotency: re-running with the same input yields no net changes.
    """

    @abstractmethod
    def get_max_ext_id(self) -> int:
        """Return the current maximum external_resource ID.

        Returns:
            The MAX(id) from external_resource, or 0 if empty.
        """

    @abstractmethod
    def find_by_url(self, url: str) -> int | None:
        """Find an external_resource ID by its URL.

        Args:
            url: The URL to look up.

        Returns:
            The external_resource ID, or None if not found.
        """

    @abstractmethod
    def update_name(self, ext_id: int, name: str) -> None:
        """Update the name of an existing external_resource.

        Args:
            ext_id: The external resource ID.
            name: The new name value.
        """

    @abstractmethod
    def insert_resource(self, ext_id: int, name: str, url: str) -> None:
        """Insert a new external_resource row.

        Args:
            ext_id: The ID to assign.
            name: The display name.
            url: The URL.
        """

    @abstractmethod
    def delete_family_links(self, ext_id: int) -> None:
        """Delete all family_has_external_resource rows for an ext_id.

        Args:
            ext_id: The external resource ID.
        """

    @abstractmethod
    def insert_family_link(self, family_id: int, ext_id: int) -> None:
        """Insert a family_has_external_resource link.

        Args:
            family_id: The HGNC gene family ID.
            ext_id: The external resource ID.
        """

    @abstractmethod
    def get_all_flybase_urls(self) -> list[tuple[int, str]]:
        """Return all external_resource rows with flybase.org URLs.

        Returns:
            A list of (ext_id, url) tuples.
        """

    @abstractmethod
    def delete_resource(self, ext_id: int) -> None:
        """Delete an external_resource row by ID.

        Args:
            ext_id: The external resource ID to delete.
        """
