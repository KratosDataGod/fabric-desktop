"""The conservative Delta profile Fabric readers handle reliably.

Fabric's SQL analytics endpoint and Direct Lake read plain Delta well, but
tables from external writers can carry features they misread. V2 checkpoints
also stop the lakehouse from listing a table. See
https://learn.microsoft.com/fabric/fundamentals/delta-lake-interoperability
"""

from __future__ import annotations

from deltalake import DeltaTable

MAX_READER = 1
MAX_WRITER = 2

# Table properties that turn on features outside the profile.
_FORBIDDEN_CONFIG = {
    "delta.enableDeletionVectors": {"true"},
    "delta.columnMapping.mode": {"name", "id"},
    "delta.checkpointPolicy": {"v2"},
}


class ProfileViolation(ValueError):
    pass


def check_table(table: DeltaTable) -> None:
    problems: list[str] = []
    protocol = table.protocol()
    if protocol.min_reader_version > MAX_READER:
        problems.append(f"reader version {protocol.min_reader_version} > {MAX_READER}")
    if protocol.min_writer_version > MAX_WRITER:
        problems.append(f"writer version {protocol.min_writer_version} > {MAX_WRITER}")
    for features, kind in ((protocol.reader_features, "reader"), (protocol.writer_features, "writer")):
        if features:
            problems.append(f"{kind} features {sorted(features)}")
    config = table.metadata().configuration or {}
    for key, bad in _FORBIDDEN_CONFIG.items():
        if str(config.get(key, "")).lower() in bad:
            problems.append(f"{key}={config[key]}")
    if problems:
        raise ProfileViolation("Table is outside the Fabric-safe Delta profile: " + "; ".join(problems))
