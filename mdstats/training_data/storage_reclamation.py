from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any

FILESYSTEM_IDENTITY_SCHEMA = "mdstats.mlff-filesystem-identity.v1"


def filesystem_identity(path: str | Path, *, hash_regular_file_limit_bytes: int = 16 * 1024 * 1024) -> dict[str, Any]:
    """Return a bounded pre-deletion filesystem identity without following symlinks."""

    candidate = Path(path)
    st = candidate.lstat()
    mode = st.st_mode
    if stat.S_ISLNK(mode):
        kind = "symlink"
    elif stat.S_ISREG(mode):
        kind = "file"
    elif stat.S_ISDIR(mode):
        kind = "directory"
    else:
        kind = "other"
    payload: dict[str, Any] = {
        "schema": FILESYSTEM_IDENTITY_SCHEMA,
        "kind": kind,
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
        "mode": int(mode),
        "size_bytes": int(st.st_size),
        "allocated_bytes": int(getattr(st, "st_blocks", 0)) * 512,
        "mtime_ns": int(st.st_mtime_ns),
    }
    if kind == "symlink":
        payload["link_target"] = os.readlink(candidate)
    elif kind == "file" and int(st.st_size) <= int(hash_regular_file_limit_bytes):
        digest = hashlib.sha256()
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        payload["sha256"] = digest.hexdigest()
    return payload
