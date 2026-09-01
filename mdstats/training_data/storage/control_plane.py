"""Storage's own durable control-plane state, owned explicitly.

The renewed subsystem produces state that no P1-P7 owner can classify for it:
an archive catalog and its manifests, a restore journal, execution audits, and
the operation-serialization lease.  Without an explicit owner, storage could
recursively reclaim its own recovery authority, so this module is the single
locator/retention authority for that state.

Nothing here is scientific authority.  A control-plane record can say where a
cold representation lives and whether an operation finished; it can never make
a historical owner artifact current, and it never carries secrets or
machine-specific credentials.

Layout, all inside the campaign-owned workspace::

    .mdstats/storage/
        catalog/                 durable archive catalog entries (identity-keyed)
        archives/                archive blobs and their manifests
        journal/                 restore journals until a verified terminal result
        audit/                   bounded cleanup/dedup/archive execution audit
        locks/                   operation-serialization lease state
        staging/                 bounded restore staging, attempt-scoped
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from .durability import (
    canonical_digest,
    durable_append_jsonl,
    durable_publish_json,
    sha256_file,
)

STORAGE_CONTROL_ROOT_NAME = "storage"
CATALOG_DIRECTORY = "catalog"
ARCHIVE_DIRECTORY = "archives"
JOURNAL_DIRECTORY = "journal"
AUDIT_DIRECTORY = "audit"
LOCK_DIRECTORY = "locks"
STAGING_DIRECTORY = "staging"

STORAGE_AUDIT_SCHEMA = "mdstats.mlff-storage-audit.v1"
STORAGE_CATALOG_ENTRY_SCHEMA = "mdstats.mlff-storage-archive-catalog-entry.v1"

#: Control-plane subdirectories that no storage action may delete or archive
#: while any archive they describe is retained.
RECOVERY_CRITICAL_DIRECTORIES = (CATALOG_DIRECTORY, ARCHIVE_DIRECTORY, JOURNAL_DIRECTORY)


class StorageControlPlaneError(RuntimeError):
    """The storage control plane is unusable or was asked to break its contract."""


@dataclass(frozen=True, slots=True)
class StorageControlPlane:
    """Locator authority for storage-native durable state."""

    workspace: Path
    root: Path

    @property
    def catalog_root(self) -> Path:
        return self.root / CATALOG_DIRECTORY

    @property
    def archive_root(self) -> Path:
        return self.root / ARCHIVE_DIRECTORY

    @property
    def journal_root(self) -> Path:
        return self.root / JOURNAL_DIRECTORY

    @property
    def audit_root(self) -> Path:
        return self.root / AUDIT_DIRECTORY

    @property
    def lock_root(self) -> Path:
        return self.root / LOCK_DIRECTORY

    @property
    def staging_root(self) -> Path:
        return self.root / STAGING_DIRECTORY

    @property
    def audit_path(self) -> Path:
        return self.audit_root / "storage-operations.jsonl"

    def ensure(self) -> "StorageControlPlane":
        for directory in (
            self.catalog_root,
            self.archive_root,
            self.journal_root,
            self.audit_root,
            self.lock_root,
            self.staging_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    # -- archive locator containment (R11-1) -----------------------------

    def catalog_entry_path(self, archive_identity: str) -> Path:
        return self.catalog_root / f"{_validated_identity(archive_identity)}.json"

    def archive_blob_locator(self, archive_identity: str, *, suffix: str) -> str:
        """The canonical identity-owned relative locator for one archive blob.

        A manifest never carries an arbitrary filesystem path: it carries this
        locator, which is resolved only against the authorized archive root.
        """

        return f"{_validated_identity(archive_identity)}{suffix}"

    def resolve_archive_blob(self, locator: str) -> Path:
        """Resolve a manifest-supplied archive locator inside the archive root.

        Absolute paths, ``..``, empty or alias-normalizing components, and any
        symlink escape are rejected: an archive locator identifies a member of
        the storage owner's catalog, never an arbitrary external file whose
        bytes happen to satisfy a supplied digest.
        """

        return resolve_inside_root(self.archive_root, locator, what="archive locator")

    def manifest_path(self, archive_identity: str) -> Path:
        identity = _validated_identity(archive_identity)
        return self.archive_root / f"{identity}.manifest.json"

    def staging_root_for(self, operation_identity: str) -> Path:
        return self.staging_root / _validated_identity(operation_identity)

    def journal_path(self, operation_identity: str) -> Path:
        return self.journal_root / f"{_validated_identity(operation_identity)}.json"

    # -- durable records --------------------------------------------------

    def publish_catalog_entry(self, entry: Mapping[str, Any]) -> Path:
        """Durably publish one identity-keyed archive catalog entry."""

        identity = _validated_identity(entry.get("archive_identity", ""))
        payload = dict(entry)
        payload["schema"] = STORAGE_CATALOG_ENTRY_SCHEMA
        payload.pop("entry_digest", None)
        payload["entry_digest"] = canonical_digest(payload)
        destination = self.catalog_entry_path(identity)
        self.catalog_root.mkdir(parents=True, exist_ok=True)
        durable_publish_json(destination, payload)
        return destination

    def read_catalog_entry(self, archive_identity: str) -> dict[str, Any]:
        path = self.catalog_entry_path(archive_identity)
        if not path.is_file():
            raise StorageControlPlaneError(
                f"No storage archive catalog entry for identity {archive_identity[:12]}..."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != STORAGE_CATALOG_ENTRY_SCHEMA:
            raise StorageControlPlaneError(
                f"Unsupported storage catalog entry schema at {path}."
            )
        expected = payload.get("entry_digest")
        observed = canonical_digest({k: v for k, v in payload.items() if k != "entry_digest"})
        if expected != observed:
            raise StorageControlPlaneError(
                f"Storage catalog entry digest mismatch at {path}."
            )
        if str(payload.get("archive_identity")) != _validated_identity(archive_identity):
            raise StorageControlPlaneError(
                f"Storage catalog entry at {path} binds a different archive identity."
            )
        return payload

    def iter_catalog_entries(self) -> Iterator[dict[str, Any]]:
        if not self.catalog_root.is_dir():
            return iter(())

        def _generate() -> Iterator[dict[str, Any]]:
            for path in sorted(self.catalog_root.glob("*.json")):
                yield self.read_catalog_entry(path.stem)

        return _generate()

    def append_audit(self, payload: Mapping[str, Any]) -> str:
        record = dict(payload)
        record["schema"] = STORAGE_AUDIT_SCHEMA
        self.audit_root.mkdir(parents=True, exist_ok=True)
        return durable_append_jsonl(self.audit_path, record)

    def read_audit(self) -> tuple[dict[str, Any], ...]:
        if not self.audit_path.is_file():
            return ()
        records: list[dict[str, Any]] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return tuple(records)

    def prune_audit(self, *, keep: int) -> int:
        """Bound audit retention without ever touching catalog/journal state.

        Audit records are diagnostic evidence.  Losing an old one cannot
        invalidate scientific currentness, and this never removes the catalog
        or journal an existing cold representation still needs.
        """

        records = self.read_audit()
        keep = max(0, int(keep))
        if len(records) <= keep:
            return 0
        retained = records[len(records) - keep :] if keep else ()
        temporary = self.audit_path.with_suffix(".jsonl.pruning")
        temporary.unlink(missing_ok=True)
        for record in retained:
            durable_append_jsonl(temporary, {k: v for k, v in record.items() if k != "event_digest"})
        os.replace(temporary, self.audit_path)
        return len(records) - len(retained)

    def clear_staging(self, operation_identity: str) -> None:
        shutil.rmtree(self.staging_root_for(operation_identity), ignore_errors=True)

    def retained_archive_paths(self) -> frozenset[str]:
        """Every path a retained cold representation still needs to exist.

        Cleanup consults this so pruning old audit/plan records can never
        remove the catalog, manifest, or blob a retained archive depends on.
        """

        retained: set[str] = set()
        if not self.catalog_root.is_dir():
            return frozenset()
        for path in sorted(self.catalog_root.glob("*.json")):
            retained.add(str(path))
            try:
                entry = self.read_catalog_entry(path.stem)
            except StorageControlPlaneError:
                # An unreadable catalog entry is the least safe moment to
                # reclaim anything it might describe.
                retained.add(str(self.archive_root))
                continue
            retained.add(str(self.manifest_path(entry["archive_identity"])))
            locator = str(entry.get("archive_locator", ""))
            if locator:
                try:
                    retained.add(str(self.resolve_archive_blob(locator)))
                except StorageControlPlaneError:
                    retained.add(str(self.archive_root))
        return frozenset(retained)


def _validated_identity(value: Any) -> str:
    token = str(value)
    if len(token) != 32 or not all(character in "0123456789abcdef" for character in token):
        raise StorageControlPlaneError(
            f"A storage control-plane identity must be 32 lowercase hex characters, got {value!r}."
        )
    return token


def resolve_inside_root(root: Path, locator: str, *, what: str) -> Path:
    """Resolve one relative locator strictly inside ``root``.

    This is the single containment primitive for manifest-supplied locators and
    archive member paths.  It rejects absolute paths, ``..``, empty components,
    normalization aliases, and any symlink that would take the resolved path
    outside the authorized root.
    """

    text = str(locator)
    if not text or text != text.strip():
        raise StorageControlPlaneError(f"Empty or ambiguous {what}: {locator!r}")
    candidate = Path(text)
    if candidate.is_absolute() or (os.name == "nt" and candidate.drive):
        raise StorageControlPlaneError(f"Absolute {what} is never authorized: {locator!r}")
    parts = candidate.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise StorageControlPlaneError(f"Unsafe {what} component in {locator!r}")
    if candidate.as_posix() != text.replace(os.sep, "/"):
        raise StorageControlPlaneError(f"Non-canonical {what}: {locator!r}")
    root_absolute = Path(os.path.abspath(os.fspath(root)))
    resolved_root = _resolve(root_absolute)
    target = root_absolute / candidate
    # Lexical containment first, then a real-path check so an intermediate
    # symlink cannot smuggle the target outside the authorized root.
    try:
        target.relative_to(root_absolute)
    except ValueError as exc:
        raise StorageControlPlaneError(f"{what} escapes its authorized root: {locator!r}") from exc
    probe = target
    while True:
        if probe.is_symlink():
            raise StorageControlPlaneError(
                f"{what} traverses a symlink and is not authorized: {locator!r}"
            )
        if probe == root_absolute:
            break
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    resolved = _resolve(target)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise StorageControlPlaneError(
            f"resolved {what} escapes its authorized root: {locator!r}"
        ) from exc
    return target


def _resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return Path(os.path.abspath(os.fspath(path)))


def open_storage_control_plane(workspace_or_paths: Any) -> StorageControlPlane:
    """Open (and create) the campaign-owned storage control plane."""

    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    workspace = (
        Path(workspace_or_paths.workspace)
        if hasattr(workspace_or_paths, "workspace")
        else Path(workspace_or_paths)
    )
    plane = StorageControlPlane(
        workspace=Path(os.path.abspath(os.fspath(workspace))),
        root=Path(os.path.abspath(os.fspath(internal))) / STORAGE_CONTROL_ROOT_NAME,
    )
    return plane.ensure()


def authenticate_file(path: Path, *, expected_sha256: str, expected_size: int) -> None:
    """Fail closed unless the canonical bytes match the expected identity."""

    if not path.is_file() or path.is_symlink():
        raise StorageControlPlaneError(f"Expected a regular file at {path}.")
    observed_size = int(path.stat().st_size)
    if observed_size != int(expected_size):
        raise StorageControlPlaneError(
            f"Size mismatch for {path}: expected {expected_size}, observed {observed_size}."
        )
    observed = sha256_file(path, limit_bytes=int(expected_size))
    if observed != str(expected_sha256):
        raise StorageControlPlaneError(f"Digest mismatch for {path}.")


__all__ = [
    "ARCHIVE_DIRECTORY",
    "AUDIT_DIRECTORY",
    "CATALOG_DIRECTORY",
    "JOURNAL_DIRECTORY",
    "LOCK_DIRECTORY",
    "RECOVERY_CRITICAL_DIRECTORIES",
    "STAGING_DIRECTORY",
    "STORAGE_AUDIT_SCHEMA",
    "STORAGE_CATALOG_ENTRY_SCHEMA",
    "STORAGE_CONTROL_ROOT_NAME",
    "StorageControlPlane",
    "StorageControlPlaneError",
    "authenticate_file",
    "open_storage_control_plane",
    "resolve_inside_root",
]
