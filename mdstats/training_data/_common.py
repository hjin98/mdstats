"""Shared immutable-record helpers for the MLFF training-data branch."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from functools import lru_cache
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np


class TrainingDataError(ValueError):
    """Base error for MLFF training-data records and policies."""


class TrainingDataInputError(TrainingDataError):
    """Raised when a training-data input violates a declared contract."""


class TrainingDataSerializationError(TrainingDataError):
    """Raised when a serialized record is malformed or has been modified."""


def json_value(value: Any) -> Any:
    """Convert supported values to deterministic JSON-compatible objects."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise TrainingDataInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return {
            str(key): json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    raise TrainingDataInputError(
        f"Unsupported metadata value {type(value).__name__}."
    )


def tuple_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(tuple_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            (str(key), tuple_value(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        json_value(value),
        # ``json_value`` already sorts every mapping recursively. Avoid the
        # encoder's second complete key sort while preserving byte-identical
        # canonical JSON.
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()



@lru_cache(maxsize=8192)
def _sha256_file_for_identity(
    path_text: str,
    device: int,
    inode: int,
    size: int,
    mtime_ns: int,
    ctime_ns: int,
) -> str:
    """Hash immutable-looking file bytes once per in-process stat identity."""

    del device, inode, size, mtime_ns, ctime_ns  # cache-key evidence only
    hasher = hashlib.sha256()
    with Path(path_text).open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()




_SHA256_RECEIPT_LOCK = threading.RLock()
_SHA256_RECEIPT_PATH: Path | None = None
_SHA256_RECEIPT_LOCAL = threading.local()
_SHA256_RECEIPT_SCHEMA = "mdstats.sha256-file-receipts.v1"
_VALIDATION_RECEIPT_SCHEMA = "mdstats.completed-validation-receipts.v1"
_SHA256_HASHED_IN_PROCESS: set[tuple[str, int, int, int, int, int]] = set()


def configure_sha256_receipt_store(path: str | Path | None) -> None:
    """Configure an optional durable SHA-256 receipt database.

    Receipts are keyed by resolved path plus device/inode/size/mtime/ctime.  They
    are only a restart optimization: a stat-identity mismatch always forces a
    fresh byte hash, and any database failure falls back to the in-process cache.
    """

    global _SHA256_RECEIPT_PATH
    target = None if path is None else Path(path).expanduser().resolve()
    with _SHA256_RECEIPT_LOCK:
        previous = _SHA256_RECEIPT_PATH
        _SHA256_RECEIPT_PATH = target
        if previous != target:
            connection = getattr(_SHA256_RECEIPT_LOCAL, "connection", None)
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
                _SHA256_RECEIPT_LOCAL.connection = None
                _SHA256_RECEIPT_LOCAL.connection_path = None


def _sha256_receipt_connection() -> sqlite3.Connection | None:
    path = _SHA256_RECEIPT_PATH
    if path is None:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = getattr(_SHA256_RECEIPT_LOCAL, "connection", None)
        connection_path = getattr(_SHA256_RECEIPT_LOCAL, "connection_path", None)
        if connection is not None and connection_path == str(path):
            return connection
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        connection = sqlite3.connect(path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                path TEXT NOT NULL,
                device INTEGER NOT NULL,
                inode INTEGER NOT NULL,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                ctime_ns INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                PRIMARY KEY(path, device, inode, size, mtime_ns, ctime_ns)
            )
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
            ("schema", _SHA256_RECEIPT_SCHEMA),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_receipts (
                namespace TEXT NOT NULL,
                identity_digest TEXT NOT NULL,
                value_digest TEXT NOT NULL,
                PRIMARY KEY(namespace, identity_digest)
            )
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
            ("validation_receipt_schema", _VALIDATION_RECEIPT_SCHEMA),
        )
        connection.commit()
        _SHA256_RECEIPT_LOCAL.connection = connection
        _SHA256_RECEIPT_LOCAL.connection_path = str(path)
        return connection
    except Exception:
        return None


def _read_sha256_receipt(key: tuple[str, int, int, int, int, int]) -> str | None:
    connection = _sha256_receipt_connection()
    if connection is None:
        return None
    try:
        row = connection.execute(
            "SELECT sha256 FROM receipts WHERE path=? AND device=? AND inode=? AND size=? AND mtime_ns=? AND ctime_ns=?",
            key,
        ).fetchone()
        if row is None:
            return None
        value = str(row[0])
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            return None
        return value
    except Exception:
        return None


def _write_sha256_receipt(key: tuple[str, int, int, int, int, int], value: str) -> None:
    connection = _sha256_receipt_connection()
    if connection is None:
        return
    try:
        connection.execute(
            "INSERT OR REPLACE INTO receipts(path,device,inode,size,mtime_ns,ctime_ns,sha256) VALUES (?,?,?,?,?,?,?)",
            (*key, value),
        )
        connection.commit()
    except Exception:
        pass


def read_validation_receipt(namespace: str, identity_digest: str) -> str | None:
    """Read trusted-local evidence that a compound artifact was fully validated."""

    if not namespace or len(identity_digest) != 64:
        return None
    connection = _sha256_receipt_connection()
    if connection is None:
        return None
    try:
        row = connection.execute(
            "SELECT value_digest FROM validation_receipts WHERE namespace=? AND identity_digest=?",
            (namespace, identity_digest),
        ).fetchone()
        if row is None:
            return None
        value = str(row[0])
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            return None
        return value
    except Exception:
        return None


def write_validation_receipt(namespace: str, identity_digest: str, value_digest: str) -> None:
    """Record completed validation; database failures remain an optimization miss."""

    if (
        not namespace
        or len(identity_digest) != 64
        or len(value_digest) != 64
        or any(ch not in "0123456789abcdef" for ch in identity_digest + value_digest)
    ):
        return
    connection = _sha256_receipt_connection()
    if connection is None:
        return
    try:
        connection.execute(
            "INSERT OR REPLACE INTO validation_receipts(namespace,identity_digest,value_digest) VALUES (?,?,?)",
            (namespace, identity_digest, value_digest),
        )
        connection.commit()
    except Exception:
        pass


def prune_sha256_receipts(*, maximum_rows: int = 100_000) -> None:
    """Bound the optional durable receipt table without affecting correctness."""

    connection = _sha256_receipt_connection()
    if connection is None:
        return
    limit = max(1000, int(maximum_rows))
    try:
        count = int(connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
        if count <= limit:
            return
        # No access timestamp is needed for correctness.  Retain the newest
        # rowids, which naturally favors recently authenticated artifacts.
        connection.execute(
            "DELETE FROM receipts WHERE rowid NOT IN (SELECT rowid FROM receipts ORDER BY rowid DESC LIMIT ?)",
            (limit,),
        )
        connection.commit()
    except Exception:
        pass

def sha256_file_cached(path: str | Path) -> str:
    """Return SHA-256 while avoiding repeated full reads of unchanged files.

    The cache is process-local and keyed by resolved path plus device, inode,
    size, mtime, and ctime.  A post-hash stat closes the ordinary write-race:
    if any identity field changed while hashing, the operation retries under
    the new identity.  Integrity semantics are unchanged; only repeated reads
    of an already authenticated immutable artifact are removed.
    """

    source = Path(path).resolve()
    for _ in range(3):
        before = source.stat()
        key = (
            str(source),
            int(before.st_dev),
            int(before.st_ino),
            int(before.st_size),
            int(before.st_mtime_ns),
            int(before.st_ctime_ns),
        )
        if key in _SHA256_HASHED_IN_PROCESS:
            value = _sha256_file_for_identity(*key)
        else:
            value = _read_sha256_receipt(key)
            if value is None:
                value = _sha256_file_for_identity(*key)
                _SHA256_HASHED_IN_PROCESS.add(key)
        after = source.stat()
        after_key = (
            str(source),
            int(after.st_dev),
            int(after.st_ino),
            int(after.st_size),
            int(after.st_mtime_ns),
            int(after.st_ctime_ns),
        )
        if after_key == key:
            _write_sha256_receipt(key, value)
            return value
    raise TrainingDataInputError(
        f"File changed repeatedly while hashing: {source!s}."
    )

def validate_serialized_digest(
    payload: Mapping[str, Any],
    *,
    digest_field: str,
    current_digest: str,
    error_message: str,
    legacy_digests: tuple[str, ...] = (),
) -> bool:
    """Verify current or exact legacy serialized identity.

    Schema migrations may add constructor defaults while preserving an older
    record byte-for-byte.  Reconstructing the current object then changes its
    canonical digest.  This helper accepts either the current canonical digest
    or the SHA-256 of the exact serialized mapping with only its digest field
    removed.  The latter remains fail-closed for accidental modification and
    allows nested legacy records to migrate without weakening schema checks.

    Returns ``True`` when a digest-valid legacy identity was used.
    """

    stored = payload.get(digest_field)
    if stored is None:
        return False
    stored_text = validate_digest(str(stored), name=digest_field)
    current_text = validate_digest(str(current_digest), name=f"current_{digest_field}")
    serialized_payload = {
        str(key): value for key, value in payload.items() if str(key) != digest_field
    }
    serialized_digest = digest(serialized_payload)
    accepted = {current_text, serialized_digest}
    accepted.update(
        validate_digest(str(value), name=f"legacy_{digest_field}")
        for value in legacy_digests
    )
    if stored_text not in accepted:
        raise TrainingDataSerializationError(error_message)
    return stored_text != current_text


def validate_digest(value: str, *, name: str) -> str:
    result = str(value)
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise TrainingDataInputError(f"{name} must be a lowercase SHA-256 digest.")
    return result


def read_mapping_file(path: str | Path) -> Mapping[str, Any]:
    """Read JSON, or YAML when PyYAML is available."""

    source = Path(path)
    if not source.is_file():
        raise TrainingDataInputError(f"Manifest does not exist: {source!s}.")
    text = source.read_text(encoding="utf-8")
    suffix = source.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise TrainingDataInputError(
                "YAML manifest support requires PyYAML; use JSON or install PyYAML."
            ) from exc
        payload = yaml.safe_load(text)
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TrainingDataInputError(
                "Unknown manifest suffix and content is not valid JSON."
            ) from exc
    if not isinstance(payload, Mapping):
        raise TrainingDataInputError("Manifest root must be a mapping.")
    return payload
