"""Postgres repository for FlyBase external resource operations.

Implements the ExternalResourceRepository ABC using psycopg v3
with parameterized SQL for all operations.
"""

from __future__ import annotations

import logging
from typing import Any

from hgnc_external_resource_updater.exceptions import PersistenceError
from hgnc_external_resource_updater.models import (
    ExternalResource,
    FamilyExternalResourceLink,
)
from hgnc_external_resource_updater.repositories.external_resource_repository import (
    ExternalResourceRepository,
)

logger = logging.getLogger(__name__)

_SELECT_BY_SOURCE = (
    "SELECT source_db, resource_id, hgnc_id, display_name, url "
    "FROM external_resource WHERE source_db = %s"
)

_UPSERT_RESOURCE = (
    "INSERT INTO external_resource (source_db, resource_id, hgnc_id, display_name, url) "
    "VALUES (%s, %s, %s, %s, %s) "
    "ON CONFLICT (source_db, resource_id) DO UPDATE SET "
    "hgnc_id = EXCLUDED.hgnc_id, "
    "display_name = EXCLUDED.display_name, "
    "url = EXCLUDED.url"
)

_DELETE_RESOURCE = (
    "DELETE FROM external_resource WHERE source_db = %s AND resource_id = ANY(%s)"
)

_UPSERT_FAMILY_LINK = (
    "INSERT INTO family_has_external_resource (hgnc_id, resource_id, source_db) "
    "VALUES (%s, %s, %s) "
    "ON CONFLICT (hgnc_id, resource_id, source_db) DO NOTHING"
)

_DELETE_FAMILY_LINKS = (
    "DELETE FROM family_has_external_resource "
    "WHERE source_db = %s AND resource_id = ANY(%s)"
)


class PostgresExternalResourceRepository(ExternalResourceRepository):
    """Concrete Postgres repository for FlyBase external resource sync.

    Uses psycopg v3 with parameterized SQL for all operations. Maps
    database errors to PersistenceError for service-layer consumption.

    Args:
        connection: A psycopg v3 connection instance.
    """

    def __init__(self, connection: Any) -> None:
        self._conn = connection

    def get_existing_by_source(self, source_db: str) -> list[ExternalResource]:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_SELECT_BY_SOURCE, (source_db,))
                rows = cur.fetchall()
                return [
                    ExternalResource(
                        source_db=row[0],
                        resource_id=row[1],
                        hgnc_id=row[2],
                        display_name=row[3],
                        url=row[4],
                    )
                    for row in rows
                ]
        except Exception as exc:
            raise PersistenceError(
                f"Failed to query external_resource for source {source_db!r}: {exc}"
            ) from exc

    def upsert_external_resources(self, records: list[ExternalResource]) -> int:
        if not records:
            return 0
        try:
            params = [
                (r.source_db, r.resource_id, r.hgnc_id, r.display_name, r.url)
                for r in records
            ]
            with self._conn.cursor() as cur:
                cur.executemany(_UPSERT_RESOURCE, params)
                return cur.rowcount
        except Exception as exc:
            raise PersistenceError(
                f"Failed to upsert {len(records)} external_resource records: {exc}"
            ) from exc

    def delete_external_resources(self, source_db: str, resource_ids: list[str]) -> int:
        if not resource_ids:
            return 0
        try:
            with self._conn.cursor() as cur:
                cur.execute(_DELETE_RESOURCE, (source_db, resource_ids))
                return cur.rowcount
        except Exception as exc:
            raise PersistenceError(
                f"Failed to delete external_resource records for source {source_db!r}: {exc}"
            ) from exc

    def upsert_family_links(self, links: list[FamilyExternalResourceLink]) -> int:
        if not links:
            return 0
        try:
            params = [(l.hgnc_id, l.resource_id, l.source_db) for l in links]
            with self._conn.cursor() as cur:
                cur.executemany(_UPSERT_FAMILY_LINK, params)
                return cur.rowcount
        except Exception as exc:
            raise PersistenceError(
                f"Failed to upsert {len(links)} family links: {exc}"
            ) from exc

    def delete_family_links(self, source_db: str, resource_ids: list[str]) -> int:
        if not resource_ids:
            return 0
        try:
            with self._conn.cursor() as cur:
                cur.execute(_DELETE_FAMILY_LINKS, (source_db, resource_ids))
                return cur.rowcount
        except Exception as exc:
            raise PersistenceError(
                f"Failed to delete family links for source {source_db!r}: {exc}"
            ) from exc
