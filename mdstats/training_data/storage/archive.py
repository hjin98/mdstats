"""Cold archive v2: bounded, identity-keyed, crash-durable representation change.

Archive is a *reversible representation change* for owner-declared historical
reproducibility bulk.  It is never currentness promotion, never lossy pruning,
and never a transparent virtual filesystem: no P1-P7 loader is given an
implicit "if missing, read the storage archive" fallback by this package, so an
artifact a current public resolver dereferences hot is simply not
hot-removable.

Three properties are load-bearing.

*Containment.*  A manifest carries an identity-owned relative locator, not a
filesystem path.  It is resolved only against the storage owner's authorized
archive root, and an absolute locator, ``..``, a normalization alias, or a
symlink escape is rejected.  Validating the outer locator does not replace
member validation, which is enforced separately.

*Boundedness.*  Archive bytes are authenticated-but-untrusted until every check
passes.  Member count, total expansion, per-member size during streaming,
cumulative extracted bytes, and a compressed-to-expanded ratio are all bounded
*before and during* extraction, so a corrupt or tampered archive cannot consume
disk or time before rejection.

*Durability ordering.*  A terminal catalog or restore receipt is published only
after the bytes and directory entries it authenticates have reached the
repository's durable-publication boundary.  Archive bytes without an
authenticated catalog never authorize hot deletion, and an authenticated
catalog may truthfully coexist with still-hot members after an interruption.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence

from .admission import admit_storage_operation
from .control_plane import (
    StorageControlPlane,
    StorageControlPlaneError,
    authenticate_file,
    resolve_inside_root,
)
from .durability import (
    DIGEST_CHUNK_BYTES,
    canonical_digest,
    parallel_digests,
    durable_publish_bytes,
    durable_publish_json,
    durable_unlink,
    sha256_file,
)
from .lease import owner_mutation_barrier, storage_operation_lease
from .policy import CODEC_GZIP, CODEC_STORE, StoragePolicy

COLD_ARCHIVE_MANIFEST_SCHEMA = "mdstats.mlff-storage-cold-archive-manifest.v2"
COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA = "mdstats.mlff-storage-cold-archive-restore.v2"
COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA = "mdstats.mlff-storage-restore-journal.v1"

SUPPORTED_MANIFEST_SCHEMAS = frozenset({COLD_ARCHIVE_MANIFEST_SCHEMA})
SUPPORTED_CODECS = {CODEC_GZIP: "r:gz", CODEC_STORE: "r:"}
_WRITE_MODES = {CODEC_GZIP: "w:gz", CODEC_STORE: "w:"}


class StorageArchiveError(RuntimeError):
    """An archive operation refused to proceed, or an archive failed a check."""


#: Named publication boundaries.  Tests inject failures here to prove the
#: ordering contract without simulating real power loss.
BOUNDARY_BEFORE_BLOB = "before_archive_blob_publication"
BOUNDARY_AFTER_BLOB = "after_archive_blob_publication"
BOUNDARY_AFTER_MANIFEST = "after_manifest_before_catalog"
BOUNDARY_AFTER_CATALOG = "after_catalog_before_reclamation"
BOUNDARY_DURING_RECLAMATION = "during_hot_reclamation"
BOUNDARY_AFTER_STAGING = "after_staging_before_install"
BOUNDARY_DURING_INSTALL = "during_restore_install"
BOUNDARY_BEFORE_RECEIPT = "after_install_before_receipt"

Failpoint = Callable[[str], None]


def _no_failpoint(_name: str) -> None:
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Member collection
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    """One canonical workspace-relative archive member."""

    path: str
    kind: str
    mode: int
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "mode": int(self.mode),
        }
        if self.kind == "file":
            payload["size_bytes"] = int(self.size_bytes)
            payload["sha256"] = self.sha256
        return payload


def canonical_member_path(workspace: Path, path: Path) -> str:
    """Workspace-relative POSIX locator, rejecting anything non-canonical."""

    absolute = Path(os.path.abspath(os.fspath(path)))
    root = Path(os.path.abspath(os.fspath(workspace)))
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise StorageArchiveError(f"archive member escapes the workspace: {path}") from exc
    text = relative.as_posix()
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise StorageArchiveError(f"non-canonical archive member path: {path}")
    return text


def collect_members(
    workspace: Path, roots: Sequence[Path], *, boundary: Any, io_workers: int = 1
) -> tuple[ArchiveMember, ...]:
    """Collect a complete, symlink-free, campaign-owned member inventory.

    Member digests are computed with bounded I/O concurrency and may reuse the
    campaign's SHA-256 receipt cache, because these are owner-declared immutable
    artifacts.  A stale receipt cannot produce a wrong archive: the published
    blob is independently read back and authenticated against this manifest
    before any catalog entry exists.
    """

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    members: list[ArchiveMember] = []
    seen: set[str] = set()
    pending_files: list[tuple[str, Path, int, int]] = []
    for root in _normalized_roots(roots):
        if root.is_symlink():
            raise StorageArchiveError(f"refusing to archive a symlink root: {root}")
        authorized, detail = boundary.traversal_authorization(root)
        if not authorized:
            raise StorageArchiveError(f"archive root is not campaign-owned: {detail}: {root}")
        if root.is_file():
            scan: Iterable[Path] = (root,)
        elif root.is_dir():
            scan = (root, *sorted(root.rglob("*")))
        else:
            raise StorageArchiveError(f"unsupported archive root type: {root}")
        for candidate in scan:
            if candidate.is_symlink():
                raise StorageArchiveError(f"refusing to archive a symlink member: {candidate}")
            authorized, detail = boundary.destructive_authorization(candidate)
            if not authorized:
                raise StorageArchiveError(
                    f"archive member is not campaign-owned: {detail}: {candidate}"
                )
            stats = candidate.lstat()
            relative = canonical_member_path(workspace, candidate)
            if relative in seen:
                raise StorageArchiveError(f"duplicate archive member: {relative}")
            seen.add(relative)
            if stat.S_ISDIR(stats.st_mode):
                members.append(
                    ArchiveMember(relative, "directory", stat.S_IMODE(stats.st_mode), 0, "")
                )
            elif stat.S_ISREG(stats.st_mode):
                pending_files.append(
                    (relative, candidate, stat.S_IMODE(stats.st_mode), int(stats.st_size))
                )
            else:
                raise StorageArchiveError(
                    f"unsupported archive member type (only regular files and "
                    f"directories are archived): {candidate}"
                )
    digests = parallel_digests(
        [item[1] for item in pending_files], workers=io_workers, accelerated=True
    )
    for relative, candidate, mode, size in pending_files:
        members.append(
            ArchiveMember(relative, "file", mode, size, digests[os.fspath(candidate)])
        )
    members.sort(key=lambda item: (item.path, item.kind))
    return tuple(members)


def _normalized_roots(paths: Sequence[Path]) -> tuple[Path, ...]:
    unique = sorted(
        {Path(os.path.abspath(os.fspath(item))) for item in paths if item is not None},
        key=lambda item: (len(item.parts), str(item)),
    )
    kept: list[Path] = []
    for candidate in unique:
        if any(candidate == parent or parent in candidate.parents for parent in kept):
            continue
        kept.append(candidate)
    return tuple(kept)


# ---------------------------------------------------------------------------
# Manifest identity
# ---------------------------------------------------------------------------


def build_manifest(
    *,
    members: Sequence[ArchiveMember],
    lineage: Mapping[str, Any],
    policy: StoragePolicy,
    plan_identity: str,
    control_plane: StorageControlPlane,
) -> dict[str, Any]:
    """Assemble the manifest body, minus the fields only publication can fill."""

    inventory = {
        "workspace_layout_version": 2,
        "members": [item.to_dict() for item in members],
        "lineage": dict(lineage),
    }
    archive_identity = canonical_digest(inventory)[:32]
    suffix = ".tar.gz" if policy.archive_codec == CODEC_GZIP else ".tar"
    return {
        "schema": COLD_ARCHIVE_MANIFEST_SCHEMA,
        "archive_identity": archive_identity,
        "archive_locator": control_plane.archive_blob_locator(
            archive_identity, suffix=suffix
        ),
        "codec": policy.archive_codec,
        "compression_level": int(policy.archive_compression_level),
        "workspace_layout_version": 2,
        "lineage": dict(lineage),
        "source_plan_identity": str(plan_identity),
        "policy_identity": policy.policy_identity,
        "members": [item.to_dict() for item in members],
        "member_count": len(members),
        "total_expanded_bytes": sum(
            int(item.size_bytes) for item in members if item.kind == "file"
        ),
    }


def _seal_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in dict(manifest).items() if k != "manifest_content_digest"}
    body["manifest_content_digest"] = canonical_digest(body)
    return body


def _validate_manifest_body(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") not in SUPPORTED_MANIFEST_SCHEMAS:
        raise StorageArchiveError(
            f"unsupported cold-archive manifest schema: {manifest.get('schema')!r}"
        )
    if manifest.get("codec") not in SUPPORTED_CODECS:
        raise StorageArchiveError(f"unsupported archive codec: {manifest.get('codec')!r}")
    expected = manifest.get("manifest_content_digest")
    observed = canonical_digest(
        {k: v for k, v in dict(manifest).items() if k != "manifest_content_digest"}
    )
    if expected != observed:
        raise StorageArchiveError("cold-archive manifest content digest mismatch")
    return dict(manifest)


# ---------------------------------------------------------------------------
# Bounded verification
# ---------------------------------------------------------------------------


def _expected_member_map(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for item in manifest.get("members", ()):
        name = str(item.get("path", ""))
        normalized = _canonical_archive_name(name)
        if normalized in expected:
            raise StorageArchiveError(f"duplicate manifest member after normalization: {name}")
        expected[normalized] = dict(item)
    return expected


def _canonical_archive_name(name: str) -> str:
    """Reject any member name that is not already its own canonical form."""

    text = str(name).rstrip("/")
    if not text or text != text.strip():
        raise StorageArchiveError(f"empty or ambiguous archive member name: {name!r}")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or text.startswith("/") or text.startswith("\\"):
        raise StorageArchiveError(f"absolute archive member path is never extracted: {name!r}")
    parts = candidate.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise StorageArchiveError(f"unsafe archive member path component in {name!r}")
    if os.path.normpath(text) != text or "\\" in text:
        raise StorageArchiveError(f"non-canonical archive member path alias: {name!r}")
    return text


def _admit_expansion(manifest: Mapping[str, Any], policy: StoragePolicy, blob_size: int) -> None:
    """Bound member count, total expansion, and decompression amplification."""

    member_count = int(manifest.get("member_count", 0))
    expanded = int(manifest.get("total_expanded_bytes", 0))
    if member_count != len(manifest.get("members", ())):
        raise StorageArchiveError("manifest member count disagrees with its member list")
    if member_count > int(policy.archive_member_limit):
        raise StorageArchiveError(
            f"archive declares {member_count} members, beyond the admitted limit "
            f"{policy.archive_member_limit}"
        )
    declared = sum(
        int(item.get("size_bytes", 0))
        for item in manifest.get("members", ())
        if item.get("kind") == "file"
    )
    if declared != expanded:
        raise StorageArchiveError(
            "manifest total_expanded_bytes disagrees with its declared member sizes"
        )
    if expanded > int(policy.archive_expanded_bytes_limit):
        raise StorageArchiveError(
            f"archive declares {expanded} expanded bytes, beyond the admitted limit "
            f"{policy.archive_expanded_bytes_limit}"
        )
    if blob_size > 0:
        ratio = float(expanded) / float(blob_size)
        if ratio > float(policy.archive_expansion_ratio_limit):
            raise StorageArchiveError(
                f"archive expansion ratio {ratio:.1f} exceeds the admitted limit "
                f"{policy.archive_expansion_ratio_limit:.1f}; a decompression-amplification "
                "archive is rejected before any extraction"
            )


def _reject_unsupported_member(member: tarfile.TarInfo) -> None:
    if member.issym() or member.islnk():
        raise StorageArchiveError(f"symlink/hard-link archive member rejected: {member.name!r}")
    if member.ischr() or member.isblk() or member.isfifo() or member.isdev():
        raise StorageArchiveError(f"special-device archive member rejected: {member.name!r}")
    if not (member.isfile() or member.isdir()):
        raise StorageArchiveError(f"unsupported archive member type: {member.name!r}")


def _stream_member(
    tar: tarfile.TarFile,
    member: tarfile.TarInfo,
    expected_size: int,
    *,
    sink: Any | None,
) -> tuple[str, int]:
    """Read one member with a hard per-member size bound while streaming.

    Nothing is ever read or written past the manifest-declared size: a member
    whose content is longer than its declaration is rejected at the moment the
    bound is crossed, not after the whole thing has been expanded.
    """

    import hashlib

    stream = tar.extractfile(member)
    if stream is None:
        raise StorageArchiveError(f"cannot read archive member: {member.name!r}")
    hasher = hashlib.sha256()
    written = 0
    limit = int(expected_size)
    while True:
        chunk = stream.read(min(DIGEST_CHUNK_BYTES, max(1, limit - written + 1)))
        if not chunk:
            break
        written += len(chunk)
        if written > limit:
            raise StorageArchiveError(
                f"archive member {member.name!r} is longer than its manifest size "
                f"({limit} bytes); extraction is aborted at the bound"
            )
        hasher.update(chunk)
        if sink is not None:
            sink.write(chunk)
    if written != limit:
        raise StorageArchiveError(
            f"archive member {member.name!r} is {written} bytes but the manifest "
            f"declares {limit}"
        )
    return hasher.hexdigest(), written


def verify_cold_archive(
    control_plane: StorageControlPlane,
    archive_identity: str,
    policy: StoragePolicy,
) -> dict[str, Any]:
    """Authenticate one cataloged archive end to end, bounded throughout."""

    entry = control_plane.read_catalog_entry(archive_identity)
    manifest_path = control_plane.manifest_path(archive_identity)
    if not manifest_path.is_file():
        raise StorageArchiveError(
            f"cold-archive manifest is missing for {archive_identity[:12]}..."
        )
    manifest = _validate_manifest_body(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    if str(manifest.get("archive_identity")) != str(entry["archive_identity"]):
        raise StorageArchiveError(
            "the manifest does not bind the archive identity its catalog entry claims"
        )
    if str(manifest.get("archive_locator")) != str(entry.get("archive_locator")):
        raise StorageArchiveError(
            "the manifest archive locator disagrees with the catalog entry"
        )
    try:
        blob = control_plane.resolve_archive_blob(str(manifest["archive_locator"]))
    except StorageControlPlaneError as exc:
        raise StorageArchiveError(str(exc)) from exc
    if not blob.is_file():
        raise StorageArchiveError(f"cold archive blob is missing: {blob}")
    authenticate_file(
        blob,
        expected_sha256=str(manifest["archive_sha256"]),
        expected_size=int(manifest["archive_size_bytes"]),
    )
    _admit_expansion(manifest, policy, int(manifest["archive_size_bytes"]))

    expected = _expected_member_map(manifest)
    observed: set[str] = set()
    cumulative = 0
    ceiling = int(manifest["total_expanded_bytes"])
    with tarfile.open(blob, mode=SUPPORTED_CODECS[str(manifest["codec"])]) as tar:
        for member in tar:
            _reject_unsupported_member(member)
            name = _canonical_archive_name(member.name)
            if name in observed:
                raise StorageArchiveError(f"duplicate archive member: {name}")
            observed.add(name)
            item = expected.get(name)
            if item is None:
                raise StorageArchiveError(f"archive contains an unlisted member: {name}")
            if (member.mode & 0o7777) != int(item["mode"]):
                raise StorageArchiveError(f"archive member mode mismatch for {name}")
            if member.isdir():
                if item["kind"] != "directory":
                    raise StorageArchiveError(f"archive member kind mismatch for {name}")
                continue
            if item["kind"] != "file":
                raise StorageArchiveError(f"archive member kind mismatch for {name}")
            digest, size = _stream_member(tar, member, int(item["size_bytes"]), sink=None)
            cumulative += size
            if cumulative > ceiling:
                raise StorageArchiveError(
                    "cumulative extracted bytes exceeded the manifest expansion bound"
                )
            if digest != str(item["sha256"]):
                raise StorageArchiveError(f"archive member content digest mismatch for {name}")
    missing = sorted(set(expected) - observed)
    if missing:
        raise StorageArchiveError(f"archive is missing declared members: {missing[:5]}")
    return manifest


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


@dataclass
class ArchiveCreationResult:
    archive_identity: str
    manifest: Mapping[str, Any]
    catalog_path: Path
    reclaimed_paths: tuple[str, ...]
    remaining_hot_paths: tuple[str, ...]
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.mlff-storage-archive-result.v1",
            "archive_identity": self.archive_identity,
            "archive_locator": self.manifest.get("archive_locator"),
            "manifest_content_digest": self.manifest.get("manifest_content_digest"),
            "member_count": self.manifest.get("member_count"),
            "total_expanded_bytes": self.manifest.get("total_expanded_bytes"),
            "catalog_entry": str(self.catalog_path),
            "reclaimed_hot_paths": list(self.reclaimed_paths),
            "remaining_hot_paths": list(self.remaining_hot_paths),
            "status": self.status,
            "detail": self.detail,
            "grants_scientific_authority": False,
        }


def create_cold_archive(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    roots: Sequence[Path],
    lineage: Mapping[str, Any],
    plan_identity: str,
    paths: Any,
    generations: Sequence[int] = (),
    reclaim_hot: bool = True,
    failpoint: Failpoint = _no_failpoint,
) -> ArchiveCreationResult:
    """Create, authenticate, catalog, and only then reclaim hot bytes.

    The ordering is the contract: archive bytes without an authenticated
    catalog never authorize hot deletion, and the terminal catalog record is
    published only after the blob and the manifest have reached the durable
    publication boundary and the published bytes have been re-authenticated
    from their canonical paths.
    """

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    control_plane.ensure()
    members = collect_members(
        workspace, roots, boundary=boundary, io_workers=policy.io_worker_limit
    )
    if not members:
        raise StorageArchiveError("no eligible hot artifacts were found for cold archival")
    manifest = build_manifest(
        members=members,
        lineage=lineage,
        policy=policy,
        plan_identity=plan_identity,
        control_plane=control_plane,
    )
    identity = str(manifest["archive_identity"])
    blob = control_plane.resolve_archive_blob(str(manifest["archive_locator"]))
    manifest_path = control_plane.manifest_path(identity)

    hot_bytes = int(manifest["total_expanded_bytes"])
    admit_storage_operation(
        control_plane.archive_root,
        policy,
        # Peak amplification: the whole archive can be as large as its members
        # before any hot byte is reclaimed.
        required_peak_bytes=hot_bytes,
        required_inodes=2,
    )

    with storage_operation_lease(
        control_plane, timeout_seconds=policy.operation_lease_timeout_seconds
    ):
        with owner_mutation_barrier(paths, tuple(generations)):
            failpoint(BOUNDARY_BEFORE_BLOB)
            archive_sha, archive_size = _publish_archive_blob(
                blob, workspace, members, policy
            )
            failpoint(BOUNDARY_AFTER_BLOB)

            sealed = _seal_manifest(
                {
                    **manifest,
                    "archive_sha256": archive_sha,
                    "archive_size_bytes": archive_size,
                    "created_utc": _utc_now(),
                }
            )
            durable_publish_json(manifest_path, sealed)
            failpoint(BOUNDARY_AFTER_MANIFEST)

            # Independent read-back over the *published* bytes, through the same
            # bounded verifier a restore uses.  Only after this does a catalog
            # entry - the record that authorizes hot deletion - exist.
            _verify_published_pair(control_plane, sealed, policy)
            catalog_path = control_plane.publish_catalog_entry(
                {
                    "archive_identity": identity,
                    "archive_locator": sealed["archive_locator"],
                    "manifest_locator": manifest_path.name,
                    "archive_sha256": archive_sha,
                    "archive_size_bytes": archive_size,
                    "member_count": int(sealed["member_count"]),
                    "total_expanded_bytes": int(sealed["total_expanded_bytes"]),
                    "created_utc": _utc_now(),
                    "hot_reclamation_state": "pending" if reclaim_hot else "not_requested",
                }
            )
            failpoint(BOUNDARY_AFTER_CATALOG)

            reclaimed: list[str] = []
            remaining: list[str] = []
            if reclaim_hot:
                reclaimed, remaining = _reclaim_hot_members(
                    workspace, members, boundary=boundary, failpoint=failpoint
                )
            else:
                # Directories are never reclamation units, so the truthful
                # "still hot" account lists only file members.
                remaining = [item.path for item in members if item.kind == "file"]

            state = (
                "complete"
                if reclaim_hot and not remaining
                else ("not_requested" if not reclaim_hot else "partial")
            )
            control_plane.publish_catalog_entry(
                {
                    "archive_identity": identity,
                    "archive_locator": sealed["archive_locator"],
                    "manifest_locator": manifest_path.name,
                    "archive_sha256": archive_sha,
                    "archive_size_bytes": archive_size,
                    "member_count": int(sealed["member_count"]),
                    "total_expanded_bytes": int(sealed["total_expanded_bytes"]),
                    "created_utc": _utc_now(),
                    "hot_reclamation_state": state,
                    "remaining_hot_members": sorted(remaining),
                }
            )
    return ArchiveCreationResult(
        archive_identity=identity,
        manifest=sealed,
        catalog_path=catalog_path,
        reclaimed_paths=tuple(sorted(reclaimed)),
        remaining_hot_paths=tuple(sorted(remaining)),
        status="archive_authenticated",
        detail=(
            "the archive is authenticated and cataloged; "
            + (
                "every represented hot member was reclaimed"
                if reclaim_hot and not remaining
                else "some hot members remain and are described truthfully"
            )
        ),
    )


def _publish_archive_blob(
    blob: Path, workspace: Path, members: Sequence[ArchiveMember], policy: StoragePolicy
) -> tuple[str, int]:
    mode = _WRITE_MODES[policy.archive_codec]

    def _write(stream: Any) -> None:
        kwargs: dict[str, Any] = {"fileobj": stream, "mode": mode}
        if policy.archive_codec == CODEC_GZIP:
            kwargs["compresslevel"] = int(policy.archive_compression_level)
        # Campaign-internal hardlinks are dereferenced so the archive stays
        # self-contained after the hot links and the content store are gone.
        with tarfile.open(dereference=True, **kwargs) as tar:
            for item in members:
                source = workspace / item.path
                info = tar.gettarinfo(str(source), arcname=item.path)
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                if item.kind == "directory":
                    tar.addfile(info)
                else:
                    with source.open("rb") as handle:
                        tar.addfile(info, handle)

    return durable_publish_bytes(blob, _write)


def _verify_published_pair(
    control_plane: StorageControlPlane, manifest: Mapping[str, Any], policy: StoragePolicy
) -> None:
    """Authenticate the published blob against the published manifest.

    This runs before any catalog entry exists, so it cannot use the
    catalog-driven verifier; it repeats the same bounded checks directly.
    """

    blob = control_plane.resolve_archive_blob(str(manifest["archive_locator"]))
    authenticate_file(
        blob,
        expected_sha256=str(manifest["archive_sha256"]),
        expected_size=int(manifest["archive_size_bytes"]),
    )
    _admit_expansion(manifest, policy, int(manifest["archive_size_bytes"]))
    expected = _expected_member_map(manifest)
    observed: set[str] = set()
    cumulative = 0
    with tarfile.open(blob, mode=SUPPORTED_CODECS[str(manifest["codec"])]) as tar:
        for member in tar:
            _reject_unsupported_member(member)
            name = _canonical_archive_name(member.name)
            item = expected.get(name)
            if item is None or name in observed:
                raise StorageArchiveError(f"published archive member set mismatch: {name}")
            observed.add(name)
            if member.isdir():
                continue
            digest, size = _stream_member(tar, member, int(item["size_bytes"]), sink=None)
            cumulative += size
            if digest != str(item["sha256"]):
                raise StorageArchiveError(
                    f"published archive member digest mismatch for {name}"
                )
    if observed != set(expected):
        raise StorageArchiveError("published archive does not contain its declared members")


def _reclaim_hot_members(
    workspace: Path,
    members: Sequence[ArchiveMember],
    *,
    boundary: Any,
    failpoint: Failpoint,
) -> tuple[list[str], list[str]]:
    """Remove only still-authorized hot members, under a fresh authorization.

    Reclamation is idempotent and resumable: a member that is already gone is
    simply reported as reclaimed, and a member whose authorization no longer
    holds stays hot and is reported truthfully.
    """

    reclaimed: list[str] = []
    remaining: list[str] = []
    files = [item for item in members if item.kind == "file"]
    for index, item in enumerate(files):
        if index:
            failpoint(BOUNDARY_DURING_RECLAMATION)
        target = workspace / item.path
        if not target.exists() and not target.is_symlink():
            reclaimed.append(item.path)
            continue
        authorized, _detail = boundary.destructive_authorization(target)
        if not authorized or target.is_symlink() or not target.is_file():
            remaining.append(item.path)
            continue
        if int(target.stat().st_size) != int(item.size_bytes) or sha256_file(
            target, limit_bytes=int(item.size_bytes)
        ) != item.sha256:
            remaining.append(item.path)
            continue
        durable_unlink(target)
        reclaimed.append(item.path)
    # Directories are left in place: an empty campaign-owned directory costs an
    # inode, and removing one could race an owner that is about to write into it.
    return reclaimed, remaining


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


@dataclass
class ArchiveRestoreResult:
    archive_identity: str
    restored_files: int
    already_present_files: int
    verified_member_count: int
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA,
            "archive_identity": self.archive_identity,
            "restored_files": int(self.restored_files),
            "already_present_files": int(self.already_present_files),
            "verified_member_count": int(self.verified_member_count),
            "status": self.status,
            "detail": self.detail,
            "promotes_currentness": False,
            "grants_scientific_authority": False,
        }


def restore_cold_archive(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    archive_identity: str,
    paths: Any,
    generations: Sequence[int] = (),
    failpoint: Failpoint = _no_failpoint,
) -> ArchiveRestoreResult:
    """Restore one cataloged archive: staged, bounded, authenticated, terminal.

    Restoring bytes never promotes historical evidence to current.  The
    receipt says so explicitly, and no currentness pointer is written by this
    path.
    """

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    manifest = verify_cold_archive(control_plane, archive_identity, policy)
    identity = str(manifest["archive_identity"])
    blob = control_plane.resolve_archive_blob(str(manifest["archive_locator"]))
    expected = _expected_member_map(manifest)
    staging = control_plane.staging_root_for(identity)
    journal = control_plane.journal_path(identity)

    authorized, detail = boundary.destructive_authorization(staging)
    if not authorized:
        raise StorageArchiveError(f"restore staging root is not campaign-owned: {detail}")

    admit_storage_operation(
        workspace,
        policy,
        # Peak: the staged copy plus the installed copy coexist briefly.
        required_peak_bytes=2 * int(manifest["total_expanded_bytes"]),
        required_inodes=int(manifest["member_count"]),
    )

    with storage_operation_lease(
        control_plane, timeout_seconds=policy.operation_lease_timeout_seconds
    ):
        with owner_mutation_barrier(paths, tuple(generations)):
            durable_publish_json(
                journal,
                {
                    "schema": COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA,
                    "archive_identity": identity,
                    "opened_utc": _utc_now(),
                    "state": "staging",
                    "member_count": int(manifest["member_count"]),
                },
            )
            shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True, exist_ok=True)
            try:
                _stage_members(blob, manifest, expected, staging)
                failpoint(BOUNDARY_AFTER_STAGING)
                _refuse_conflicting_destinations(workspace, expected, boundary=boundary)
                restored, reused = _install_members(
                    workspace, expected, staging, failpoint=failpoint
                )
                _authenticate_installed(workspace, expected)
                failpoint(BOUNDARY_BEFORE_RECEIPT)
                receipt = ArchiveRestoreResult(
                    archive_identity=identity,
                    restored_files=restored,
                    already_present_files=reused,
                    verified_member_count=len(expected),
                    status="complete",
                    detail=(
                        "every canonical byte was authenticated after installation; "
                        "restored evidence remains historical"
                    ),
                )
                durable_publish_json(
                    journal,
                    {
                        "schema": COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA,
                        "archive_identity": identity,
                        "closed_utc": _utc_now(),
                        "state": "terminal",
                        "receipt": receipt.to_dict(),
                    },
                )
                return receipt
            finally:
                shutil.rmtree(staging, ignore_errors=True)


def _stage_members(
    blob: Path,
    manifest: Mapping[str, Any],
    expected: Mapping[str, Mapping[str, Any]],
    staging: Path,
) -> None:
    """Extract into campaign-owned staging under every bound, then authenticate."""

    cumulative = 0
    ceiling = int(manifest["total_expanded_bytes"])
    seen: set[str] = set()
    with tarfile.open(blob, mode=SUPPORTED_CODECS[str(manifest["codec"])]) as tar:
        for member in tar:
            _reject_unsupported_member(member)
            name = _canonical_archive_name(member.name)
            if name in seen:
                raise StorageArchiveError(f"duplicate archive member: {name}")
            seen.add(name)
            item = expected.get(name)
            if item is None:
                raise StorageArchiveError(f"archive contains an unlisted member: {name}")
            # The staging destination is resolved through the same containment
            # primitive as an archive locator, so no archive-created directory
            # or alias can move it outside the campaign-owned staging root.
            destination = resolve_inside_root(staging, name, what="archive member path")
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                os.chmod(destination, int(item["mode"]))
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as sink:
                digest, size = _stream_member(tar, member, int(item["size_bytes"]), sink=sink)
            os.chmod(destination, int(item["mode"]))
            cumulative += size
            if cumulative > ceiling:
                raise StorageArchiveError(
                    "cumulative restored bytes exceeded the manifest expansion bound"
                )
            if digest != str(item["sha256"]):
                raise StorageArchiveError(f"staged member failed authentication: {name}")
    if seen != set(expected):
        raise StorageArchiveError("the archive does not contain its declared member set")


def _refuse_conflicting_destinations(
    workspace: Path, expected: Mapping[str, Mapping[str, Any]], *, boundary: Any
) -> None:
    for name, item in expected.items():
        destination = workspace / name
        authorized, detail = boundary.destructive_authorization(destination)
        if not authorized:
            raise StorageArchiveError(
                f"restore destination is not campaign-owned: {detail}: {destination}"
            )
        if item["kind"] == "directory":
            if destination.exists() and not destination.is_dir():
                raise StorageArchiveError(
                    f"restore destination conflicts with a non-directory: {destination}"
                )
            continue
        if not destination.exists():
            continue
        if destination.is_symlink() or not destination.is_file():
            raise StorageArchiveError(
                f"restore destination conflicts with a non-file: {destination}"
            )
        if int(destination.stat().st_size) != int(item["size_bytes"]) or sha256_file(
            destination, limit_bytes=int(item["size_bytes"])
        ) != str(item["sha256"]):
            raise StorageArchiveError(
                "restore destination already exists with different authoritative "
                f"content; nothing is overwritten implicitly: {destination}"
            )


def _install_members(
    workspace: Path,
    expected: Mapping[str, Mapping[str, Any]],
    staging: Path,
    *,
    failpoint: Failpoint,
) -> tuple[int, int]:
    from ..target_size_execution.persistence import fsync_parent_directory

    directories = sorted(
        (item for item in expected.values() if item["kind"] == "directory"),
        key=lambda item: len(PurePosixPath(str(item["path"])).parts),
    )
    for item in directories:
        destination = workspace / str(item["path"])
        destination.mkdir(parents=True, exist_ok=True)
        os.chmod(destination, int(item["mode"]))
    restored = 0
    reused = 0
    for index, (name, item) in enumerate(sorted(expected.items())):
        if item["kind"] != "file":
            continue
        if index:
            failpoint(BOUNDARY_DURING_INSTALL)
        destination = workspace / name
        if destination.exists():
            reused += 1
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging / name, destination)
        fsync_parent_directory(destination)
        restored += 1
    return restored, reused


def _authenticate_installed(workspace: Path, expected: Mapping[str, Mapping[str, Any]]) -> None:
    for name, item in expected.items():
        if item["kind"] != "file":
            continue
        destination = workspace / name
        authenticate_file(
            destination,
            expected_sha256=str(item["sha256"]),
            expected_size=int(item["size_bytes"]),
        )


def read_restore_journal(
    control_plane: StorageControlPlane, archive_identity: str
) -> dict[str, Any] | None:
    """The storage owner's own account of an in-flight or finished restore."""

    path = control_plane.journal_path(archive_identity)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA:
        raise StorageArchiveError(f"unsupported restore journal schema at {path}")
    return payload


def reclaim_archived_hot_members(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    archive_identity: str,
    paths: Any,
    generations: Sequence[int] = (),
    failpoint: Failpoint = _no_failpoint,
) -> ArchiveCreationResult:
    """Resume hot reclamation for an already authenticated, cataloged archive.

    Retry never assumes the previous remaining set.  The archive is
    re-authenticated first, then each still-hot member is re-authorized against
    a fresh ownership boundary and re-matched byte-for-byte before removal, so
    an interrupted reclamation completes safely or reports truthfully.
    """

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    manifest = verify_cold_archive(control_plane, archive_identity, policy)
    identity = str(manifest["archive_identity"])
    members = tuple(
        ArchiveMember(
            path=str(item["path"]),
            kind=str(item["kind"]),
            mode=int(item["mode"]),
            size_bytes=int(item.get("size_bytes", 0)),
            sha256=str(item.get("sha256", "")),
        )
        for item in manifest["members"]
    )
    with storage_operation_lease(
        control_plane, timeout_seconds=policy.operation_lease_timeout_seconds
    ):
        with owner_mutation_barrier(paths, tuple(generations)):
            reclaimed, remaining = _reclaim_hot_members(
                workspace, members, boundary=boundary, failpoint=failpoint
            )
            entry = control_plane.read_catalog_entry(identity)
            catalog_path = control_plane.publish_catalog_entry(
                {
                    **{
                        key: entry[key]
                        for key in (
                            "archive_identity",
                            "archive_locator",
                            "manifest_locator",
                            "archive_sha256",
                            "archive_size_bytes",
                            "member_count",
                            "total_expanded_bytes",
                            "created_utc",
                        )
                    },
                    "hot_reclamation_state": "complete" if not remaining else "partial",
                    "remaining_hot_members": sorted(remaining),
                }
            )
    return ArchiveCreationResult(
        archive_identity=identity,
        manifest=manifest,
        catalog_path=catalog_path,
        reclaimed_paths=tuple(sorted(reclaimed)),
        remaining_hot_paths=tuple(sorted(remaining)),
        status="archive_authenticated",
        detail=(
            "resumed hot reclamation against a freshly authenticated archive"
            if not remaining
            else "some hot members remain authorized-hot and are reported truthfully"
        ),
    )


def list_archives(control_plane: StorageControlPlane) -> tuple[dict[str, Any], ...]:
    """Every retained cold representation, identity-keyed.

    There is no ``latest`` authority here: the catalog is identity-keyed, and a
    convenience pointer would be exactly the kind of implicit currentness this
    package refuses to create.
    """

    return tuple(control_plane.iter_catalog_entries())


__all__ = [
    "BOUNDARY_AFTER_BLOB",
    "BOUNDARY_AFTER_CATALOG",
    "BOUNDARY_AFTER_MANIFEST",
    "BOUNDARY_AFTER_STAGING",
    "BOUNDARY_BEFORE_BLOB",
    "BOUNDARY_BEFORE_RECEIPT",
    "BOUNDARY_DURING_INSTALL",
    "BOUNDARY_DURING_RECLAMATION",
    "COLD_ARCHIVE_MANIFEST_SCHEMA",
    "COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA",
    "COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA",
    "ArchiveCreationResult",
    "ArchiveMember",
    "ArchiveRestoreResult",
    "StorageArchiveError",
    "canonical_member_path",
    "collect_members",
    "create_cold_archive",
    "list_archives",
    "reclaim_archived_hot_members",
    "read_restore_journal",
    "restore_cold_archive",
    "verify_cold_archive",
]
