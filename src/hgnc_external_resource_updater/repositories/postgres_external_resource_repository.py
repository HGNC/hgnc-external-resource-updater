"""Postgres repository for FlyBase external resource operations.

Implements the ExternalResourceRepository ABC using psycopg v3
with parameterized SQL matching the actual genew4 schema.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from hgnc_external_resource_updater.exceptions import PersistenceError
from hgnc_external_resource_updater.repositories.external_resource_repository import (
    ExternalResourceRepository,
)

logger = logging.getLogger(__name__)

_GET_MAX_ID = "SELECT COALESCE(MAX(id), 0) FROM external_resource"

_FIND_BY_URL = "SELECT id FROM external_resource WHERE url = %s"

_UPDATE_NAME = "UPDATE external_resource SET name = %s WHERE id = %s"

_INSERT_RESOURCE = (
    "INSERT INTO external_resource (id, name, url) VALUES (%s, %s, %s)"
)

_DELETE_FAMILY_LINKS = (
    "DELETE FROM family_has_external_resource WHERE ext_id = %s"
)

_INSERT_FAMILY_LINK = (
    "INSERT INTO family_has_external_resource (family_id, ext_id) "
    "VALUES (%s, %s)"
)

_GET_ALL_FLYBASE = (
    "SELECT id, url FROM external_resource WHERE url LIKE '%flybase.org%'"
)

_DELETE_RESOURCE = "DELETE FROM external_resource WHERE id = %s"


class PostgresExternalResourceRepository(ExternalResourceRepository):
    """Concrete Postgres repository for FlyBase external resource sync.

    Uses psycopg v3 with parameterized SQL. Maps database errors
    to PersistenceError for service-layer consumption.

    Args:
        connection: A psycopg v3 connection instance.
    """

    def __init__(self, connection: Any) -> None:
        self._conn = connection

    def get_max_ext_id(self) -> int:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_GET_MAX_ID)
                row = cur.fetchone()
                return row[0] if row else 0
        except Exception as exc:
            raise PersistenceError(
                f"Failed to get MAX(id): {exc}"
            ) from exc

    def find_by_url(self, url: str) -> int | None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_FIND_BY_URL, (url,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as exc:
            raise PersistenceError(
                f"Failed to find resource by URL {url!r}: {exc}"
            ) from exc

    def update_name(self, ext_id: int, name: str) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_UPDATE_NAME, (name, ext_id))
        except Exception as exc:
            raise PersistenceError(
                f"Failed to update name for ext_id {ext_id}: {exc}"
            ) from exc

    def insert_resource(self, ext_id: int, name: str, url: str) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_INSERT_RESOURCE, (ext_id, name, url))
        except Exception as exc:
            raise PersistenceError(
                f"Failed to insert resource {ext_id}: {exc}"
            ) from exc

    def delete_family_links(self, ext_id: int) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_DELETE_FAMILY_LINKS, (ext_id,))
        except Exception as exc:
            raise PersistenceError(
                f"Failed to delete family links for ext_id {ext_id}: {exc}"
            ) from exc

    def insert_family_link(self, family_id: int, ext_id: int) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_INSERT_FAMILY_LINK, (family_id, ext_id))
        except Exception as exc:
            raise PersistenceError(
                f"Failed to insert family link ({family_id}, {ext_id}): {exc}"
            ) from exc

    def get_all_flybase_urls(self) -> list[tuple[int, str]]:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_GET_ALL_FLYBASE)
                return list(cur.fetchall())
        except Exception as exc:
            raise PersistenceError(
                f"Failed to get FlyBase URLs: {exc}"
            ) from exc

    def delete_resource(self, ext_id: int) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(_DELETE_RESOURCE, (ext_id,))
        except Exception as exc:
            raise PersistenceError(
                f"Failed to delete resource {ext_id}: {exc}"
            ) from exc
