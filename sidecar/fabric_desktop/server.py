"""JSON-lines RPC over stdin/stdout, used by the Tauri shell.

Request:  {"id": 1, "method": "list_workspaces", "params": {}}
Response: {"id": 1, "result": [...]}  or  {"id": 1, "error": "message"}
"""

from __future__ import annotations

import json
import sys
from typing import IO

from .service import Service

METHODS = {"sign_in", "list_workspaces", "list_lakehouses", "create_lakehouse",
           "list_tables", "preview_job", "run_job", "history"}


def handle(service: Service, line: str) -> dict:
    try:
        req = json.loads(line)
    except json.JSONDecodeError as exc:
        return {"id": None, "error": f"invalid JSON: {exc}"}
    req_id, method = req.get("id"), req.get("method")
    if method not in METHODS:
        return {"id": req_id, "error": f"unknown method {method!r}"}
    try:
        return {"id": req_id, "result": getattr(service, method)(**req.get("params", {}))}
    except Exception as exc:  # report every failure to the UI rather than dying
        return {"id": req_id, "error": f"{type(exc).__name__}: {exc}"}


def serve(service: Service | None = None, stdin: IO[str] = sys.stdin, stdout: IO[str] = sys.stdout) -> None:
    service = service or Service()
    for line in stdin:
        if line.strip():
            stdout.write(json.dumps(handle(service, line), default=str) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
