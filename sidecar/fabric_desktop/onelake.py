"""OneLake addressing for schema-enabled lakehouses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import requests

DFS_HOST = "onelake.dfs.fabric.microsoft.com"
TABLE_API = "https://onelake.table.fabric.microsoft.com/delta"

# Characters Fabric does not allow in table names.
_BAD_NAME = re.compile(r"[\"'#%+:?`/\\]")


def check_name(kind: str, name: str) -> str:
    if not name or _BAD_NAME.search(name) or name != name.strip():
        raise ValueError(f"Invalid {kind} name {name!r}: avoid quotes, # % + : ? ` / \\ and edge spaces.")
    return name


@dataclass(frozen=True)
class TableRef:
    """A Delta table in a schema-enabled lakehouse, addressed by GUIDs."""

    workspace_id: str
    lakehouse_id: str
    schema: str
    table: str

    def __post_init__(self):
        check_name("schema", self.schema)
        check_name("table", self.table)

    @property
    def uri(self) -> str:
        # GUIDs avoid ABFS failures on workspace names with spaces.
        return f"abfss://{self.workspace_id}@{DFS_HOST}/{self.lakehouse_id}/Tables/{self.schema}/{self.table}"


def storage_options(token: str) -> dict[str, str]:
    """delta-rs / object_store options for OneLake with a user bearer token."""
    return {"bearer_token": token, "use_fabric_endpoint": "true"}


class TableCatalog:
    """Read-only listing through the OneLake Delta table API (Unity Catalog compatible)."""

    def __init__(self, token_provider: Callable[[], str], session: requests.Session | None = None):
        self._token = token_provider
        self._http = session or requests.Session()

    def _get(self, url: str, **params) -> dict[str, Any]:
        resp = self._http.get(url, params=params, headers={"Authorization": f"Bearer {self._token()}"}, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def list_schemas(self, workspace_id: str, lakehouse_id: str) -> list[str]:
        url = f"{TABLE_API}/{workspace_id}/{lakehouse_id}/api/2.1/unity-catalog/schemas"
        return [s["name"] for s in self._get(url, catalog_name=lakehouse_id).get("schemas", [])]

    def list_tables(self, workspace_id: str, lakehouse_id: str, schema: str) -> list[str]:
        url = f"{TABLE_API}/{workspace_id}/{lakehouse_id}/api/2.1/unity-catalog/tables"
        body = self._get(url, catalog_name=lakehouse_id, schema_name=schema)
        return [t["name"] for t in body.get("tables", [])]
