"""Operations the desktop UI calls, shared by the stdio server and the CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .auth import Authenticator
from .fabric_api import FabricClient
from .jobs import Job, run_local
from .onelake import TableCatalog
from .publish import run_job


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "FabricDesktop"


class Service:
    def __init__(self, client_id: str | None = None, root: Path | None = None):
        self._client_id = client_id or os.environ.get("FABRIC_DESKTOP_CLIENT_ID", "")
        self.root = root or data_dir()
        self._auth: Authenticator | None = None

    @property
    def auth(self) -> Authenticator:
        if self._auth is None:
            self._auth = Authenticator(self._client_id)
        return self._auth

    @property
    def fabric(self) -> FabricClient:
        return FabricClient(self.auth.fabric_token)

    @property
    def history_file(self) -> Path:
        return self.root / "history.jsonl"

    # Each public method is one UI action.

    def sign_in(self) -> dict[str, Any]:
        self.auth.fabric_token()
        self.auth.storage_token()
        return {"user": self.auth.signed_in_user()}

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self.fabric.list_workspaces()

    def list_lakehouses(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.fabric.list_lakehouses(workspace_id)

    def create_lakehouse(self, workspace_id: str, name: str) -> dict[str, Any]:
        return self.fabric.create_lakehouse(workspace_id, name)

    def list_tables(self, workspace_id: str, lakehouse_id: str) -> dict[str, list[str]]:
        catalog = TableCatalog(self.auth.storage_token)
        return {s: catalog.list_tables(workspace_id, lakehouse_id, s)
                for s in catalog.list_schemas(workspace_id, lakehouse_id)}

    def preview_job(self, path: str, limit: int = 100) -> dict[str, Any]:
        data = run_local(Job.load(path))
        return {"rows": data.num_rows, "columns": data.schema.names,
                "sample": data.slice(0, limit).to_pylist()}

    def run_job(self, path: str) -> dict[str, Any]:
        record = run_job(Job.load(path), self.fabric, self.auth.storage_token,
                         work_dir=self.root, history_file=self.history_file)
        return record.__dict__

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []
        lines = self.history_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:]][::-1]
