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

from ..target_size_execution.persistence import fsync_parent_directory
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
STORAGE_RESTORE_JOURNAL_SCHEMA = "mdstats.mlff-storage-restore-journal.v1"

#: Durable storage-control schemas this build understands.  Anything else is
#: rejected and retained rather than reinterpreted: an unsupported archive or
#: journal format is a compatibility question for a future migration, never a
#: licence to guess at what old bytes meant.
SUPPORTED_JOURNAL_SCHEMAS = frozenset({STORAGE_RESTORE_JOURNAL_SCHEMA})
SUPPORTED_CATALOG_SCHEMAS = frozenset({STORAGE_CATALOG_ENTRY_SCHEMA})

#: Catalog fields that are create-once for one representation identity.  A
#: later publication may refresh only operational status; rewriting any of
#: these would silently repoint a retained archive.
IMMUTABLE_CATALOG_FIELDS = (
    "archive_identity",
    "archive_locator",
    "manifest_locator",
    "archive_sha256",
    "archive_size_bytes",
    "member_count",
    "total_expanded_bytes",
    "representation_identity",
    "logical_identity",
)

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
        """Materialize the control-plane directories.

        Only an explicitly authorized consequential invocation may call this.
        Read-only inspection uses :func:`open_storage_control_plane_readonly`,
        which never creates anything: a `storage report` that had to create
        `.mdstats/storage` in order to say no storage control plane exists
        would have changed the campaign to describe it.
        """

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

    @property
    def exists(self) -> bool:
        return self.root.is_dir()

    # -- restore journal lifecycle ---------------------------------------

    def journal_path_for_name(self, name: str) -> Path:
        return self.journal_root / f"{name}.json"

    def journal_states(self) -> tuple[tuple[str, bool], ...]:
        """``(identity, is_terminal)`` for every restore journal on disk."""

        if not self.journal_root.is_dir():
            return ()
        states: list[tuple[str, bool]] = []
        for path in sorted(self.journal_root.glob("*.json")):
            states.append((path.stem, self._journal_is_terminal(path)))
        return tuple(states)

    def journal_is_nonterminal(self, name: str) -> bool:
        path = self.journal_path_for_name(name)
        return path.is_file() and not self._journal_is_terminal(path)

    def _journal_is_terminal(self, path: Path) -> bool:
        """Whether one restore journal has reached its verified terminal state.

        An unreadable or unsupported journal is treated as *nonterminal*: that
        is the direction that retains recovery authority, and an unsupported
        durable schema must be rejected and kept rather than reinterpreted.
        """

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if payload.get("schema") not in SUPPORTED_JOURNAL_SCHEMAS:
            return False
        return str(payload.get("state")) == "terminal"

    def retirable_terminal_journals(self, *, keep: int) -> tuple[str, ...]:
        """Terminal journals beyond the retention bound, oldest first.

        Retiring one removes bounded diagnostic evidence only; the archive
        catalog, manifest, and blob it refers to are never touched.
        """

        terminal = [name for name, done in self.journal_states() if done]
        if len(terminal) <= max(0, int(keep)):
            return ()
        ordered = sorted(
            terminal,
            key=lambda name: (
                self.journal_path_for_name(name).stat().st_mtime
                if self.journal_path_for_name(name).is_file()
                else 0.0
            ),
        )
        return tuple(ordered[: len(ordered) - max(0, int(keep))])

    # -- archive publication residue -------------------------------------

    def uncataloged_archive_residue(self) -> tuple[str, ...]:
        """Archive files under the archive root that no catalog entry claims.

        An archive blob or manifest without a catalog entry authorizes nothing:
        it cannot justify a hot deletion and cannot be restored from. Once no
        live operation holds the storage lease, it is storage-owned scratch.
        Anything a retained catalog entry names is excluded by construction.
        """

        if not self.archive_root.is_dir():
            return ()
        claimed: set[str] = set()
        for entry in self._safe_catalog_entries():
            identity = str(entry.get("archive_identity", ""))
            locator = str(entry.get("archive_locator", ""))
            manifest = str(entry.get("manifest_locator", ""))
            if locator:
                claimed.add(locator)
            if manifest:
                claimed.add(manifest)
            if identity:
                claimed.add(f"{identity}.manifest.json")
        residue: list[str] = []
        for path in sorted(self.archive_root.iterdir()):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name in claimed:
                continue
            residue.append(path.name)
        return tuple(residue)

    def _safe_catalog_entries(self) -> tuple[dict[str, Any], ...]:
        """Catalog entries that parse, without failing the whole enumeration.

        An unreadable entry is not silently dropped: it keeps the archive root
        conservatively claimed so nothing beneath it is treated as residue.
        """

        if not self.catalog_root.is_dir():
            return ()
        entries: list[dict[str, Any]] = []
        for path in sorted(self.catalog_root.glob("*.json")):
            try:
                entries.append(self.read_catalog_entry(path.stem))
            except StorageControlPlaneError:
                # Claim everything rather than risk calling live authority residue.
                return tuple(
                    [{"archive_locator": item.name} for item in self.archive_root.iterdir()]
                    if self.archive_root.is_dir()
                    else []
                )
        return tuple(entries)

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

    def require_operation_lease(self, operation: str) -> None:
        """Refuse to change retained archive state outside the storage lease.

        Reclaim and restore reauthenticate the exact retained representation
        immediately before consuming it. That is only race-closed if every
        supported writer of that state is serialized against the reader, so the
        control plane enforces the lease here rather than trusting each call
        site to be reachable only from an executor.
        """

        from .lease import storage_operation_lease_is_held

        if not storage_operation_lease_is_held():
            raise StorageControlPlaneError(
                f"Refusing to {operation} without the storage-operation lease: "
                "retained archive authority is only changed by a serialized "
                "consequential storage operation."
            )

    def publish_catalog_entry(self, entry: Mapping[str, Any]) -> Path:
        """Durably publish one identity-keyed archive catalog entry.

        Create-once for the fields that locate and authenticate a retained
        representation, update-allowed for operational status. Republishing the
        same identity with a different blob digest, locator, or member identity
        is refused, so a retained archive can never be silently repointed at
        different bytes; the old entry stays independently verifiable.
        """

        self.require_operation_lease("publish an archive catalog entry")
        identity = _validated_identity(entry.get("archive_identity", ""))
        payload = dict(entry)
        payload["schema"] = STORAGE_CATALOG_ENTRY_SCHEMA
        payload.pop("entry_digest", None)

        destination = self.catalog_entry_path(identity)
        if destination.is_file():
            existing = self.read_catalog_entry(identity)
            conflicts = [
                field
                for field in IMMUTABLE_CATALOG_FIELDS
                if field in existing
                and field in payload
                and existing[field] != payload[field]
            ]
            if conflicts:
                raise StorageControlPlaneError(
                    f"Archive catalog entry {identity[:12]}... already exists with "
                    f"different immutable field(s) {sorted(conflicts)}; a retained "
                    "representation is never rewritten in place."
                )
            # Carry forward any immutable field the caller did not restate, so a
            # status refresh cannot drop locating authority.
            for field in IMMUTABLE_CATALOG_FIELDS:
                if field in existing and field not in payload:
                    payload[field] = existing[field]

        payload["entry_digest"] = canonical_digest(payload)
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
        if payload.get("schema") not in SUPPORTED_CATALOG_SCHEMAS:
            raise StorageControlPlaneError(
                f"Unsupported storage catalog entry schema {payload.get('schema')!r} at "
                f"{path}; it is retained and rejected rather than reinterpreted."
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
        self.require_operation_lease("publish a storage audit record")
        record = dict(payload)
        record["schema"] = STORAGE_AUDIT_SCHEMA
        self.audit_root.mkdir(parents=True, exist_ok=True)
        return durable_append_jsonl(self.audit_path, record)

    def read_audit(self) -> tuple[dict[str, Any], ...]:
        """Every well-formed audit record, newest last.

        A malformed or truncated line is skipped rather than raised: the audit
        is diagnostic evidence, and one unreadable tail must not make the whole
        stream unreadable. :meth:`audit_stream_integrity` is what a caller asks
        before doing anything destructive with the stream.
        """

        records, _problems = self._read_audit_stream()
        return records

    def _read_audit_stream(self) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
        """``(records, problems)`` after validating framing, schema, and digest."""

        if not self.audit_path.is_file():
            return (), ()
        records: list[dict[str, Any]] = []
        problems: list[str] = []
        for number, line in enumerate(
            self.audit_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                problems.append(f"line {number} is not a complete JSON record")
                continue
            if not isinstance(record, Mapping):
                problems.append(f"line {number} is not an audit record object")
                continue
            if record.get("schema") != STORAGE_AUDIT_SCHEMA:
                problems.append(f"line {number} carries an unsupported audit schema")
                continue
            body = {k: v for k, v in dict(record).items() if k != "event_digest"}
            if str(record.get("event_digest", "")) != canonical_digest(body):
                problems.append(f"line {number} does not authenticate against its digest")
                continue
            records.append(dict(record))
        return tuple(records), tuple(problems)

    def audit_stream_integrity(self) -> tuple[str, ...]:
        """Framing/schema/digest problems in the audit stream, if any."""

        _records, problems = self._read_audit_stream()
        return problems

    def prune_audit(self, *, keep: int) -> int:
        """Bound audit retention without ever touching catalog/journal state.

        Audit records are diagnostic evidence.  Losing an old one cannot
        invalidate scientific currentness, and this never removes the catalog
        or journal an existing cold representation still needs.

        Two properties matter here beyond "delete the old ones".

        *It is serialized with appends.*  Retention reads the whole stream and
        replaces it; another operation appending in between would have its
        freshly published record thrown away by a stale rewrite.  The
        storage-operation lease is what makes the read-modify-replace atomic
        with respect to every supported storage operation, so it is required.

        *It never rewrites over damage.*  A truncated or unauthenticated line is
        a diagnostic problem to surface, not licence to replace the stream with
        the subset this process happened to be able to parse.
        """

        self.require_operation_lease("apply storage audit retention")
        records, problems = self._read_audit_stream()
        if problems:
            raise StorageControlPlaneError(
                "Refusing to apply audit retention over a damaged audit stream: "
                f"{problems[:3]}. The stream is diagnostic evidence and is left "
                "exactly as it is until the damage is understood."
            )
        keep = max(0, int(keep))
        if len(records) <= keep:
            return 0
        retained = records[len(records) - keep :] if keep else ()
        temporary = self.audit_path.with_suffix(".jsonl.pruning")
        temporary.unlink(missing_ok=True)
        try:
            for record in retained:
                durable_append_jsonl(
                    temporary, {k: v for k, v in record.items() if k != "event_digest"}
                )
            # Validate the staged stream before it replaces the real one, so a
            # failed rewrite leaves the last valid stream in place.
            staged = [
                line
                for line in temporary.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ] if temporary.is_file() else []
            if len(staged) != len(retained):
                raise StorageControlPlaneError(
                    "the staged retained audit stream is incomplete; the existing "
                    "stream is kept"
                )
            os.replace(temporary, self.audit_path)
            fsync_parent_directory(self.audit_path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
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


def _locate_storage_control_plane(workspace_or_paths: Any) -> StorageControlPlane:
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
    return StorageControlPlane(
        workspace=Path(os.path.abspath(os.fspath(workspace))),
        root=Path(os.path.abspath(os.fspath(internal))) / STORAGE_CONTROL_ROOT_NAME,
    )


def open_storage_control_plane_readonly(workspace_or_paths: Any) -> StorageControlPlane:
    """Locate the control plane without creating any of it.

    Reporting, listing, verifying, and planning all use this. A campaign with no
    storage control plane must still be reportable, and reporting it must not be
    what brings it into existence.
    """

    return _locate_storage_control_plane(workspace_or_paths)


def open_storage_control_plane(workspace_or_paths: Any) -> StorageControlPlane:
    """Open and create the campaign-owned storage control plane.

    Reserved for an explicitly authorized consequential invocation.
    """

    return _locate_storage_control_plane(workspace_or_paths).ensure()


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
    "IMMUTABLE_CATALOG_FIELDS",
    "STORAGE_CONTROL_ROOT_NAME",
    "STORAGE_RESTORE_JOURNAL_SCHEMA",
    "SUPPORTED_CATALOG_SCHEMAS",
    "SUPPORTED_JOURNAL_SCHEMAS",
    "StorageControlPlane",
    "StorageControlPlaneError",
    "authenticate_file",
    "open_storage_control_plane",
    "open_storage_control_plane_readonly",
    "resolve_inside_root",
]
