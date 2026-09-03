"""Cold archive v2: bounded, immutable, owner-bound, crash-durable.

Archive is a *reversible representation change* for owner-declared historical
reproducibility bulk.  It is never currentness promotion, never lossy pruning,
and never a transparent virtual filesystem: no P1-P7 loader is given an
implicit "if missing, read the storage archive" fallback by this package, so an
artifact a current public resolver dereferences hot is simply not
hot-removable.

Five properties carry the contract.

*Owner-bound intention.*  Create, hot reclamation, and restore all run from an
exact plan whose actions name owner artifacts, owner state identities, and
filesystem identities.  Cold bytes prove that an archive exists; they never
prove that removing or reinstalling the corresponding hot bytes is still
authorized.  Every consequential step is revalidated against a fresh owner
inventory inside the executor's synchronization.

*Closed-subtree collection.*  Members come from what the owner certifies, not
from what happens to sit beneath an authorized directory.  An unexpected
descendant is refused, never absorbed, and never removed as a side effect.

*Containment.*  A manifest carries an identity-owned relative locator, not a
filesystem path.  It resolves only against the storage owner's authorized
archive root; an absolute locator, ``..``, a normalization alias, or a symlink
escape is rejected.  Member path safety is enforced separately.

*Boundedness.*  Archive bytes are authenticated-but-untrusted until every check
passes.  Member count, total expansion, per-member size during streaming,
cumulative extracted bytes, and a compressed-to-expanded ratio are all bounded
before and during extraction, so a corrupt or tampered archive cannot consume
disk or time before rejection.

*Immutable representations and durable ordering.*  A representation identity
binds the logical member/lineage identity *and* the serialization that produced
it, so re-encoding the same content at another codec or level creates a
different representation instead of overwriting a retained one.  Blob, manifest,
and catalog are published in that order, each authenticated before the next, and
archive bytes without an authenticated catalog never authorize hot deletion.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from .admission import AdmissionObservation, admit_storage_operation
from .control_plane import (
    IMMUTABLE_CATALOG_FIELDS,
    STORAGE_RESTORE_JOURNAL_SCHEMA,
    SUPPORTED_JOURNAL_SCHEMAS,
    StorageControlPlane,
    StorageControlPlaneError,
    authenticate_file,
    resolve_inside_root,
)
from .durability import (
    DIGEST_CHUNK_BYTES,
    canonical_digest,
    durable_publish_bytes,
    durable_publish_json,
    durable_unlink,
    parallel_digests,
    sha256_file,
)
from .executor import StorageExecutionResult
from .inventory import StorageInventorySnapshot, archive_candidates
from .plan import (
    ACTION_ARCHIVE_MEMBER,
    ACTION_RECLAIM_MEMBER,
    ACTION_RESTORE_CONTAINER,
    ACTION_RESTORE_MEMBER,
    PlannedAction,
    StoragePlan,
    planned_action,
)
from .policy import CODEC_GZIP, CODEC_STORE, StoragePolicy
from .trust import crosses_mount_boundary

COLD_ARCHIVE_MANIFEST_SCHEMA = "mdstats.mlff-storage-cold-archive-manifest.v3"
COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA = "mdstats.mlff-storage-cold-archive-restore.v2"
COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA = STORAGE_RESTORE_JOURNAL_SCHEMA

SUPPORTED_MANIFEST_SCHEMAS = frozenset({COLD_ARCHIVE_MANIFEST_SCHEMA})
SUPPORTED_CODECS = {CODEC_GZIP: "r:gz", CODEC_STORE: "r:"}
_WRITE_MODES = {CODEC_GZIP: "w:gz", CODEC_STORE: "w:"}

#: A tar member costs a 512-byte header plus its content padded to 512, and the
#: archive ends with two zero blocks.  These are exact, not estimates, and they
#: are what makes a many-tiny-file archive far larger than the sum of its
#: payloads.
_TAR_BLOCK = 512
_TAR_TRAILER = 1024


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
# Members and owner mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    """One canonical workspace-relative archive member and its owner."""

    path: str
    kind: str
    mode: int
    size_bytes: int
    sha256: str
    #: Which owner artifact this member represents.  A member with no owner
    #: mapping cannot be reclaimed later, because nothing could re-establish
    #: whether removing it is still authorized.
    artifact_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "mode": int(self.mode),
            "artifact_id": self.artifact_id,
        }
        if self.kind == "file":
            payload["size_bytes"] = int(self.size_bytes)
            payload["sha256"] = self.sha256
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ArchiveMember":
        return cls(
            path=str(payload["path"]),
            kind=str(payload["kind"]),
            mode=int(payload["mode"]),
            size_bytes=int(payload.get("size_bytes", 0)),
            sha256=str(payload.get("sha256", "")),
            artifact_id=str(payload.get("artifact_id", "")),
        )


def canonical_member_path(workspace: Path, path: Path) -> str:
    """Workspace-relative POSIX locator, rejecting anything non-canonical."""

    absolute = Path(os.path.abspath(os.fspath(path)))
    root = Path(os.path.abspath(os.fspath(workspace)))
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise StorageArchiveError(f"archive member escapes the workspace: {path}") from exc
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise StorageArchiveError(f"non-canonical archive member path: {path}")
    return relative.as_posix()


def select_archive_roots(
    snapshot: StorageInventorySnapshot, requested: Sequence[str] | None
) -> tuple[tuple[Any, ...], tuple[str, ...]]:
    """Resolve operator-selected roots to owner-eligible artifacts.

    A request may name an eligible owner artifact exactly, or narrow *into* one.
    It may not name an ancestor of one: an eligible ``.../g1/runs/<run>`` does
    not make ``.../g1`` archivable, and accepting the parent would drag its
    sibling scientific evidence into the cold representation.
    """

    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    by_id = {item.artifact_id: item for item in eligible}
    refusals: list[str] = []
    if not requested:
        return tuple(eligible), ()

    chosen: list[Any] = []
    for value in requested:
        candidate = Path(os.path.abspath(os.fspath(Path(snapshot.workspace) / value)))
        exact = [item for item in eligible if item.path == candidate]
        if exact:
            chosen.extend(exact)
            continue
        inside = [item for item in eligible if _within(item.path, candidate)]
        if inside:
            # Narrowing into exactly one eligible artifact is fine; spanning
            # several is only fine if each of them is individually eligible,
            # which `inside` already establishes.
            chosen.extend(inside)
            continue
        widened = [item for item in eligible if _within(candidate, item.path)]
        if widened:
            refusals.append(
                f"{candidate} is an ancestor of owner-eligible artifact(s) "
                f"{sorted(item.artifact_id for item in widened)}; an eligible "
                "descendant never makes its parent archivable"
            )
            continue
        refusals.append(
            f"{candidate} is not owner-declared cold-replaceable; archive never "
            "removes hot bytes an owner still requires"
        )
    if refusals:
        raise StorageArchiveError("; ".join(refusals))
    del by_id
    # Deduplicate while preserving determinism.
    unique = {item.artifact_id: item for item in chosen}
    return tuple(unique[key] for key in sorted(unique)), ()


def collect_members(
    workspace: Path,
    snapshot: StorageInventorySnapshot,
    selected: Sequence[Any],
    *,
    boundary: Any,
    io_workers: int = 1,
    accelerated: bool = False,
) -> tuple[tuple[ArchiveMember, ...], tuple[str, ...]]:
    """Collect exactly the members the selected owners certify.

    Enumeration is delegated to the inventory's recursive-authorization rule, so
    only a closed owner-certified subtree is walked and an unexpected
    descendant, a symlink, or a nested mount is refused instead of collected.
    """

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    members: list[ArchiveMember] = []
    refusals: list[str] = []
    seen: set[str] = set()
    pending: list[tuple[str, Path, int, int, str]] = []

    for decision in selected:
        view = snapshot.view(decision.artifact_id)
        if view is None:
            raise StorageArchiveError(
                f"selected artifact {decision.artifact_id} is not in the inventory"
            )
        authorized, detail = boundary.traversal_authorization(view.path)
        if not authorized:
            raise StorageArchiveError(
                f"archive root is not campaign-owned: {detail}: {view.path}"
            )
        certified, member_refusals = snapshot.authorized_members(view)
        for path, why in member_refusals:
            refusals.append(f"{path}: {why}")
        if member_refusals:
            # An owner that cannot certify its whole subtree cannot have that
            # subtree archived: the manifest would claim members the owner
            # never vouched for.
            raise StorageArchiveError(
                f"{view.artifact_id} contains descendant(s) its owner did not certify: "
                + "; ".join(f"{path}: {why}" for path, why in member_refusals[:3])
            )
        # Directories are recorded so a restore can recreate the shape, but only
        # those on the certified members' own parent chains.
        directories: set[Path] = set()
        for path in certified:
            probe = path.parent
            while probe != view.path.parent and _within(view.path, probe):
                directories.add(probe)
                probe = probe.parent
        directories.add(view.path)
        for directory in sorted(directories):
            relative = canonical_member_path(workspace, directory)
            if relative in seen:
                continue
            seen.add(relative)
            members.append(
                ArchiveMember(
                    relative,
                    "directory",
                    stat.S_IMODE(directory.lstat().st_mode),
                    0,
                    "",
                    artifact_id=view.artifact_id,
                )
            )
        for path in certified:
            authorized, detail = boundary.destructive_authorization(path)
            if not authorized:
                raise StorageArchiveError(
                    f"archive member is not campaign-owned: {detail}: {path}"
                )
            stats = path.lstat()
            if not stat.S_ISREG(stats.st_mode):
                raise StorageArchiveError(
                    f"unsupported archive member type (only regular files and "
                    f"directories are archived): {path}"
                )
            relative = canonical_member_path(workspace, path)
            if relative in seen:
                raise StorageArchiveError(f"duplicate archive member: {relative}")
            seen.add(relative)
            pending.append(
                (
                    relative,
                    path,
                    stat.S_IMODE(stats.st_mode),
                    int(stats.st_size),
                    view.artifact_id,
                )
            )

    digests = parallel_digests(
        [item[1] for item in pending], workers=io_workers, accelerated=accelerated
    )
    for relative, path, mode, size, artifact_id in pending:
        members.append(
            ArchiveMember(
                relative, "file", mode, size, digests[os.fspath(path)], artifact_id
            )
        )
    members.sort(key=lambda item: (item.path, item.kind))
    return tuple(members), tuple(refusals)


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Conservative admission
# ---------------------------------------------------------------------------


def archive_container_bytes(members: Sequence[ArchiveMember]) -> int:
    """A conservative upper bound on the container this member set produces.

    Every member costs a header block plus its payload padded to a block, the
    archive ends with two zero blocks, and a codec that finds nothing to
    compress still adds framing. Optimistic compression is never admission
    evidence: a many-tiny-file archive is dominated by tar metadata and must be
    admitted as if compression saved nothing at all.
    """

    total = _TAR_TRAILER
    for member in members:
        payload = int(member.size_bytes) if member.kind == "file" else 0
        total += _TAR_BLOCK + ((payload + _TAR_BLOCK - 1) // _TAR_BLOCK) * _TAR_BLOCK
    # Deflate's worst case adds ~5 bytes per 16 KiB block plus a small header.
    return total + (total // 1000) + 4096


def archive_entry_count(members: Sequence[ArchiveMember]) -> int:
    """Directory entries and inodes a create/publish sequence consumes."""

    # blob + manifest + catalog entry, each staged through a temporary first.
    return 6


def restore_entry_count(members: Sequence[ArchiveMember]) -> int:
    """Staged plus installed entries that can coexist during a restore."""

    return 2 * len(members) + 8


# ---------------------------------------------------------------------------
# Manifest identity
# ---------------------------------------------------------------------------


def logical_identity(
    members: Sequence[ArchiveMember], lineage: Mapping[str, Any]
) -> str:
    """What this archive represents, independent of how it is serialized."""

    return canonical_digest(
        {
            "workspace_layout_version": 3,
            "members": [item.to_dict() for item in members],
            "lineage": dict(lineage),
        }
    )


def representation_identity(
    *, logical: str, codec: str, level: int, schema: str
) -> str:
    """What this archive *is on disk*, including how it was serialized.

    Two encodings of the same content are two representations. Keying blobs and
    manifests on this - rather than on logical content alone - is what stops a
    re-encode from replacing a retained archive's bytes in place.
    """

    return canonical_digest(
        {
            "schema": schema,
            "logical_identity": logical,
            "codec": codec,
            "compression_level": int(level),
        }
    )[:32]


def build_manifest(
    *,
    members: Sequence[ArchiveMember],
    lineage: Mapping[str, Any],
    policy: StoragePolicy,
    plan: StoragePlan,
    control_plane: StorageControlPlane,
) -> dict[str, Any]:
    """Assemble the self-contained manifest body.

    A retained archive must be enough, on its own, for a fresh process to
    verify it and to plan a current reclaim or restore. So the manifest carries
    the represented owner artifact identities, the lineage captured at creation,
    the selected roots, the member-to-owner mapping, and the exact action set of
    the plan that produced it - not a bare digest pointing at an advisory file
    that nothing promised to keep.
    """

    logical = logical_identity(members, lineage)
    identity = representation_identity(
        logical=logical,
        codec=policy.archive_codec,
        level=policy.archive_compression_level,
        schema=COLD_ARCHIVE_MANIFEST_SCHEMA,
    )
    suffix = ".tar.gz" if policy.archive_codec == CODEC_GZIP else ".tar"
    return {
        "schema": COLD_ARCHIVE_MANIFEST_SCHEMA,
        "archive_identity": identity,
        "representation_identity": identity,
        "logical_identity": logical,
        "archive_locator": control_plane.archive_blob_locator(identity, suffix=suffix),
        "codec": policy.archive_codec,
        "compression_level": int(policy.archive_compression_level),
        "workspace_layout_version": 3,
        "lineage": dict(lineage),
        "represented_artifact_ids": sorted(
            {item.artifact_id for item in members if item.artifact_id}
        ),
        "source_plan_identity": plan.plan_identity,
        "source_plan_actions": [item.to_dict() for item in plan.actions],
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
            f"unsupported cold-archive manifest schema: {manifest.get('schema')!r}; "
            "it is retained and rejected rather than reinterpreted"
        )
    if manifest.get("codec") not in SUPPORTED_CODECS:
        raise StorageArchiveError(f"unsupported archive codec: {manifest.get('codec')!r}")
    expected = manifest.get("manifest_content_digest")
    observed = canonical_digest(
        {k: v for k, v in dict(manifest).items() if k != "manifest_content_digest"}
    )
    if expected != observed:
        raise StorageArchiveError("cold-archive manifest content digest mismatch")
    declared = representation_identity(
        logical=str(manifest.get("logical_identity", "")),
        codec=str(manifest["codec"]),
        level=int(manifest.get("compression_level", 0)),
        schema=str(manifest["schema"]),
    )
    if declared != str(manifest.get("representation_identity")):
        raise StorageArchiveError(
            "the manifest representation identity does not reproduce from its own "
            "logical identity, codec, and level"
        )
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
    """Read one member with a hard per-member size bound while streaming."""

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


def read_manifest(
    control_plane: StorageControlPlane, archive_identity: str
) -> dict[str, Any]:
    """Load and structurally validate one retained manifest."""

    manifest_path = control_plane.manifest_path(archive_identity)
    if not manifest_path.is_file():
        raise StorageArchiveError(
            f"cold-archive manifest is missing for {archive_identity[:12]}..."
        )
    return _validate_manifest_body(json.loads(manifest_path.read_text(encoding="utf-8")))


def verify_cold_archive(
    control_plane: StorageControlPlane,
    archive_identity: str,
    policy: StoragePolicy,
) -> dict[str, Any]:
    """Authenticate one cataloged archive end to end, bounded throughout."""

    entry = control_plane.read_catalog_entry(archive_identity)
    manifest = read_manifest(control_plane, archive_identity)
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
    _verify_blob_against_manifest(blob, manifest, policy)
    return manifest


def _verify_blob_against_manifest(
    blob: Path, manifest: Mapping[str, Any], policy: StoragePolicy
) -> None:
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


# ---------------------------------------------------------------------------
# Archive creation
# ---------------------------------------------------------------------------


@dataclass
class ArchivePlanBundle:
    """An archive intention plus everything its engine needs to execute it."""

    members: tuple[ArchiveMember, ...]
    lineage: dict[str, Any]
    actions: list[PlannedAction] = field(default_factory=list)
    refusals: list[dict[str, Any]] = field(default_factory=list)
    admission: AdmissionObservation | None = None


def build_archive_plan_actions(
    *,
    workspace: Path,
    snapshot: StorageInventorySnapshot,
    selected: Sequence[Any],
    boundary: Any,
    policy: StoragePolicy,
    reclaim_hot: bool,
) -> ArchivePlanBundle:
    """Bind every collected member, and every hot removal, to an action.

    A plan with zero actions cannot bind anything; representing each member and
    each intended hot removal explicitly is what makes the later revalidation
    able to say *this exact byte range, of this exact owner artifact, in this
    exact owner state*.
    """

    members, refusal_notes = collect_members(
        workspace,
        snapshot,
        selected,
        boundary=boundary,
        io_workers=policy.io_worker_limit,
        # A dry-run never writes a SHA receipt: an observational command must
        # leave managed campaign state exactly as it found it.
        accelerated=bool(policy.apply),
    )
    if not members:
        raise StorageArchiveError("no eligible hot artifacts were found for cold archival")

    lineage = {
        "current_generation": snapshot.current_generation,
        "represented_artifact_ids": sorted({item.artifact_id for item in selected}),
        "owner_state_identities": {
            item.artifact_id: (
                snapshot.view(item.artifact_id).state_identity
                if snapshot.view(item.artifact_id) is not None
                else ""
            )
            for item in selected
        },
        "selected_roots": sorted(
            canonical_member_path(workspace, Path(item.path)) for item in selected
        ),
    }

    actions: list[PlannedAction] = []
    for member in members:
        if member.kind != "file":
            continue
        view = snapshot.view(member.artifact_id)
        actions.append(
            planned_action(
                action=ACTION_ARCHIVE_MEMBER,
                path=workspace / member.path,
                artifact_id=member.artifact_id,
                reason="owner-certified member of a cold-replaceable historical artifact",
                capability_cost="explicit_restore_required" if reclaim_hot else "none",
                owner_state_identity=view.state_identity if view is not None else "",
                binding={
                    "sha256": member.sha256,
                    "size_bytes": int(member.size_bytes),
                    "mode": int(member.mode),
                    "reclaim_hot": bool(reclaim_hot),
                },
            )
        )
    return ArchivePlanBundle(
        members=members,
        lineage=lineage,
        actions=actions,
        refusals=[{"path": note.split(":", 1)[0], "reason": note} for note in refusal_notes],
    )


def archive_create_engine(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    bundle: ArchivePlanBundle,
    reclaim_hot: bool,
    failpoint: Failpoint = _no_failpoint,
):
    """Build the engine that publishes and catalogs one archive.

    Ordering is the contract: blob, then manifest, then an independent bounded
    read-back of the *published* bytes, and only then the catalog entry that can
    authorize hot deletion. Hot reclamation follows, member by member, each one
    re-authorized against the fresh snapshot the executor revalidated.
    """

    def _engine(
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        control_plane.ensure()
        members = bundle.members
        manifest = build_manifest(
            members=members,
            lineage=bundle.lineage,
            policy=policy,
            plan=plan,
            control_plane=control_plane,
        )
        identity = str(manifest["archive_identity"])
        blob = control_plane.resolve_archive_blob(str(manifest["archive_locator"]))
        manifest_path = control_plane.manifest_path(identity)

        # An identical representation that is already cataloged is reused, never
        # rewritten: re-encoding must not disturb retained authority.
        if control_plane.catalog_entry_path(identity).is_file():
            existing = verify_cold_archive(control_plane, identity, policy)
            result.payload = {"archive_identity": identity, "reused_existing": True}
            manifest = existing
        else:
            # Publishing a retained representation is a serialized storage
            # mutation like any other change to retained archive authority.
            control_plane.require_operation_lease("publish an archive blob/manifest")
            failpoint(BOUNDARY_BEFORE_BLOB)
            archive_sha, archive_size = _publish_archive_blob(
                blob, workspace, members, policy
            )
            failpoint(BOUNDARY_AFTER_BLOB)
            manifest = _seal_manifest(
                {
                    **manifest,
                    "archive_sha256": archive_sha,
                    "archive_size_bytes": archive_size,
                    "created_utc": _utc_now(),
                }
            )
            result.mutated = True
            result.created_bytes += int(archive_size)
            result.payload = {
                "schema": "mdstats.mlff-storage-archive-result.v2",
                "archive_identity": identity,
                "representation_identity": identity,
                "logical_identity": str(manifest["logical_identity"]),
                "archive_locator": manifest["archive_locator"],
                "publication_phase": "blob_published",
                "member_count": int(manifest["member_count"]),
                "represented_artifact_ids": list(manifest["represented_artifact_ids"]),
                "reclaimed_hot_paths": [],
                "remaining_hot_paths": [item.path for item in members if item.kind == "file"],
                "hot_reclamation_state": "pending" if reclaim_hot else "not_requested",
                "grants_scientific_authority": False,
            }
            durable_publish_json(manifest_path, manifest)
            result.payload["publication_phase"] = "manifest_published"
            failpoint(BOUNDARY_AFTER_MANIFEST)
            _verify_blob_against_manifest(blob, manifest, policy)
            control_plane.publish_catalog_entry(
                {
                    "archive_identity": identity,
                    "representation_identity": identity,
                    "logical_identity": str(manifest["logical_identity"]),
                    "archive_locator": manifest["archive_locator"],
                    "manifest_locator": manifest_path.name,
                    "archive_sha256": archive_sha,
                    "archive_size_bytes": archive_size,
                    "member_count": int(manifest["member_count"]),
                    "total_expanded_bytes": int(manifest["total_expanded_bytes"]),
                    "created_utc": _utc_now(),
                    "hot_reclamation_state": "pending" if reclaim_hot else "not_requested",
                }
            )
            result.payload["publication_phase"] = "catalog_published"
        failpoint(BOUNDARY_AFTER_CATALOG)

        reclaimed: list[str] = []
        remaining: list[str] = []
        if reclaim_hot:
            reclaimed, remaining = _reclaim_planned_members(
                workspace,
                plan,
                snapshot,
                boundary=boundary,
                result=result,
                failpoint=failpoint,
            )
        else:
            remaining = [item.path for item in members if item.kind == "file"]
            for action in plan.actions:
                result.completed.append({**action.to_dict(), "archived": True})

        state = (
            "complete"
            if reclaim_hot and not remaining
            else ("not_requested" if not reclaim_hot else "partial")
        )
        control_plane.publish_catalog_entry(
            {
                "archive_identity": identity,
                "hot_reclamation_state": state,
                "remaining_hot_members": sorted(remaining),
                "updated_utc": _utc_now(),
            }
        )
        result.payload = {
            "schema": "mdstats.mlff-storage-archive-result.v2",
            "archive_identity": identity,
            "representation_identity": identity,
            "logical_identity": str(manifest["logical_identity"]),
            "archive_locator": manifest["archive_locator"],
            "member_count": int(manifest["member_count"]),
            "represented_artifact_ids": list(manifest["represented_artifact_ids"]),
            "reclaimed_hot_paths": sorted(reclaimed),
            "remaining_hot_paths": sorted(remaining),
            "hot_reclamation_state": state,
            "grants_scientific_authority": False,
        }

    return _engine


def _publish_archive_blob(
    blob: Path, workspace: Path, members: Sequence[ArchiveMember], policy: StoragePolicy
) -> tuple[str, int]:
    mode = _WRITE_MODES[policy.archive_codec]

    def _write(stream: Any) -> None:
        kwargs: dict[str, Any] = {"fileobj": stream, "mode": mode}
        if policy.archive_codec == CODEC_GZIP:
            kwargs["compresslevel"] = int(policy.archive_compression_level)
        # Campaign-internal hardlinks are dereferenced so the archive stays
        # self-contained after the hot links are gone.
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


def _reclaim_planned_members(
    workspace: Path,
    plan: StoragePlan,
    snapshot: StorageInventorySnapshot,
    *,
    boundary: Any,
    result: StorageExecutionResult,
    failpoint: Failpoint,
) -> tuple[list[str], list[str]]:
    """Remove only members that are still authorized, one at a time."""

    reclaimed: list[str] = []
    remaining: list[str] = []
    for index, action in enumerate(plan.actions):
        if index:
            failpoint(BOUNDARY_DURING_RECLAMATION)
        relative = canonical_member_path(workspace, action.path)
        if not action.path.exists() and not action.path.is_symlink():
            reclaimed.append(relative)
            result.completed.append({**action.to_dict(), "already_absent": True})
            continue
        protected, why = snapshot.path_protection(action.path)
        if protected:
            remaining.append(relative)
            result.refused.append({**action.to_dict(), "refusal": why})
            continue
        authorized, detail = boundary.destructive_authorization(action.path)
        if not authorized or action.path.is_symlink() or not action.path.is_file():
            remaining.append(relative)
            result.refused.append(
                {**action.to_dict(), "refusal": detail or "not a plain owned file"}
            )
            continue
        size = int(action.binding["size_bytes"])
        if int(action.path.stat().st_size) != size or sha256_file(
            action.path, limit_bytes=size
        ) != str(action.binding["sha256"]):
            remaining.append(relative)
            result.refused.append(
                {**action.to_dict(), "refusal": "hot bytes changed after archival"}
            )
            continue
        def _on_reclaimed() -> None:
            result.mutated = True
            reclaimed.append(relative)
            result.completed.append({**action.to_dict(), "reclaimed": True})
            result.reclaimed_bytes += size

        try:
            durable_unlink(action.path, missing_ok=False, on_unlinked=_on_reclaimed)
        except TypeError:
            durable_unlink(action.path)
            _on_reclaimed()
    return reclaimed, remaining


# ---------------------------------------------------------------------------
# Hot reclamation of an existing representation
# ---------------------------------------------------------------------------


def representation_authority(
    entry: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """The immutable identity of one retained cold representation.

    This is what a reclaim or restore plan binds. The ordinary owner views for
    ``storage:catalog`` and ``storage:archives`` describe the control plane as
    directories; they cannot say *which exact bytes* a plan intends to consume,
    so plan revalidation alone would not notice that the blob a reclaim is about
    to trust has been replaced or truncated since planning.

    Only create-once fields appear here. Operational catalog state - how much of
    the hot reclamation has finished, when it was last updated - legitimately
    changes between planning and apply and is not part of the identity.
    """

    return {
        "archive_identity": str(manifest["archive_identity"]),
        "representation_identity": str(manifest.get("representation_identity", "")),
        "logical_identity": str(manifest.get("logical_identity", "")),
        "archive_locator": str(manifest["archive_locator"]),
        "archive_sha256": str(manifest["archive_sha256"]),
        "archive_size_bytes": int(manifest["archive_size_bytes"]),
        "manifest_content_digest": str(manifest.get("manifest_content_digest", "")),
        "member_count": int(manifest.get("member_count", 0)),
        "catalog_immutable": {
            field: entry[field]
            for field in IMMUTABLE_CATALOG_FIELDS
            if field in entry
        },
    }


def bind_representation_authority(
    control_plane: StorageControlPlane, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Read the catalog entry beside a verified manifest and bind both."""

    entry = control_plane.read_catalog_entry(str(manifest["archive_identity"]))
    return representation_authority(entry, manifest)


def reauthenticate_representation(
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    bound: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-read and re-authenticate the exact representation the plan bound.

    Called inside the protected consequential window - after the storage lease
    and every owner seam are held - because that is the only point at which
    "this archive authenticates" and "this archive is about to authorize a
    deletion" are the same instant. Everything supported that could replace or
    retire a retained representation takes the same lease, so nothing can slip
    between this check and the mutation it authorizes.

    Any failure raises. A reclaim that cannot re-authenticate deletes nothing,
    and a restore that cannot re-authenticate installs nothing.
    """

    identity = str(bound["archive_identity"])
    manifest = verify_cold_archive(control_plane, identity, policy)
    observed = bind_representation_authority(control_plane, manifest)
    if observed != dict(bound):
        differing = sorted(
            key
            for key in set(observed) | set(dict(bound))
            if observed.get(key) != dict(bound).get(key)
        )
        raise StorageArchiveError(
            f"the retained cold representation {identity} is not the one this plan "
            f"bound (differing: {differing}); nothing was reclaimed or installed. "
            "Re-plan against current retained authority."
        )
    return manifest


def build_reclaim_plan_actions(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    archive_identity: str,
) -> tuple[list[PlannedAction], dict[str, Any], list[dict[str, Any]]]:
    """Reconstruct a *current* reclamation intention from retained authority.

    An old catalog proves only that cold bytes exist and authenticate. Whether
    removing the corresponding hot bytes is still allowed is a question about
    today's owners, so every still-hot member is re-mapped to its owner artifact
    and re-checked against a fresh inventory before it enters the plan.
    """

    manifest = verify_cold_archive(control_plane, archive_identity, policy)
    authority = bind_representation_authority(control_plane, manifest)
    actions: list[PlannedAction] = []
    refusals: list[dict[str, Any]] = []
    for payload in manifest["members"]:
        member = ArchiveMember.from_dict(payload)
        if member.kind != "file":
            continue
        target = workspace / member.path
        if not target.exists():
            continue
        if not member.artifact_id:
            refusals.append(
                {
                    "path": str(target),
                    "reason": "the manifest maps this member to no owner artifact",
                }
            )
            continue
        view = snapshot.view(member.artifact_id)
        if view is None or not view.archive_eligible:
            refusals.append(
                {
                    "path": str(target),
                    "reason": (
                        f"owner artifact {member.artifact_id} is no longer "
                        "cold-replaceable; the hot bytes stay"
                    ),
                }
            )
            continue
        protected, why = snapshot.path_protection(target)
        if protected:
            refusals.append({"path": str(target), "reason": why})
            continue
        actions.append(
            planned_action(
                action=ACTION_RECLAIM_MEMBER,
                path=target,
                artifact_id=member.artifact_id,
                reason="represented by an authenticated retained cold archive",
                capability_cost="explicit_restore_required",
                owner_state_identity=view.state_identity,
                binding={
                    "sha256": member.sha256,
                    "size_bytes": int(member.size_bytes),
                    "representation_authority": authority,
                },
            )
        )
    return actions, manifest, refusals


def archive_reclaim_engine(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
    failpoint: Failpoint = _no_failpoint,
):
    def _engine(
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        # Zero hot deletion happens until the retained representation this plan
        # bound re-authenticates from its canonical location, right here, under
        # the lease.
        try:
            manifest_now = reauthenticate_representation(
                control_plane, policy, authority
            )
        except (StorageArchiveError, StorageControlPlaneError) as exc:
            for action in plan.actions:
                result.refused.append({**action.to_dict(), "refusal": str(exc)})
            result.detail = (
                "the retained cold representation failed protected reauthentication; "
                f"no hot byte was removed: {exc}"
            )
            return
        identity = str(manifest_now["archive_identity"])
        reclaimed, remaining = _reclaim_planned_members(
            workspace,
            plan,
            snapshot,
            boundary=boundary,
            result=result,
            failpoint=failpoint,
        )
        still_hot = sorted(
            {
                str(item["path"])
                for item in manifest_now["members"]
                if item.get("kind") == "file" and (workspace / str(item["path"])).exists()
            }
        )
        control_plane.publish_catalog_entry(
            {
                "archive_identity": identity,
                "hot_reclamation_state": "complete" if not still_hot else "partial",
                "remaining_hot_members": still_hot,
                "updated_utc": _utc_now(),
            }
        )
        result.payload = {
            "schema": "mdstats.mlff-storage-archive-reclaim.v1",
            "archive_identity": identity,
            "reclaimed_hot_paths": sorted(reclaimed),
            "remaining_hot_paths": sorted(set(remaining) | set(still_hot)),
            "grants_scientific_authority": False,
        }

    return _engine


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


def _filesystem_node_identity(path: Path) -> dict[str, Any] | None:
    """``(device, inode, kind)`` of one existing path, or ``None`` if absent."""

    try:
        stats = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(stats.st_mode):
        kind = "symlink"
    elif stat.S_ISDIR(stats.st_mode):
        kind = "directory"
    elif stat.S_ISREG(stats.st_mode):
        kind = "file"
    else:
        kind = "other"
    return {
        "path": str(path),
        "device": int(stats.st_dev),
        "inode": int(stats.st_ino),
        "kind": kind,
    }


def parent_chain_identity(workspace: Path, destination: Path) -> list[dict[str, Any]]:
    """The exact identity of every existing ancestor this restore will use.

    A pathname is not a directory. Swapping a planned parent for a *different*
    ordinary directory at the same path - same mode, same type, not a symlink,
    same device - would otherwise pass every check and quietly redirect the
    installation into a container nobody authorized. Binding ``(device, inode,
    kind)`` for each existing ancestor makes that swap detectable.

    Ancestors that do not exist yet are deliberately omitted: this restore
    creates them itself and its own creation/postcondition chain validates them.
    """

    root = Path(os.path.abspath(os.fspath(workspace)))
    chain: list[dict[str, Any]] = []
    probe = Path(os.path.abspath(os.fspath(destination))).parent
    while True:
        identity = _filesystem_node_identity(probe)
        if identity is not None:
            chain.append(identity)
        if probe == root or probe.parent == probe:
            break
        probe = probe.parent
    return chain


def verify_parent_chain(chain: Sequence[Mapping[str, Any]]) -> None:
    """Refuse when any bound ancestor is no longer the same filesystem object."""

    for expected in chain:
        path = Path(str(expected["path"]))
        observed = _filesystem_node_identity(path)
        if observed is None:
            raise StorageArchiveError(
                f"a parent this restore planned through no longer exists: {path}"
            )
        if (
            observed["device"] != int(expected["device"])
            or observed["inode"] != int(expected["inode"])
            or observed["kind"] != str(expected["kind"])
        ):
            raise StorageArchiveError(
                f"the parent {path} is a different filesystem object than the one "
                "this restore planned through; re-plan before installing."
            )


def build_restore_plan_actions(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    archive_identity: str,
    boundary: Any,
) -> tuple[list[PlannedAction], dict[str, Any], list[dict[str, Any]]]:
    """The exact owner-bound restore intention, computed identically for dry-run.

    Each member binds its destination pre-state - absent, or exactly the same
    historical bytes - so apply can prove nothing changed underneath it. Each
    directory binds whether *this restore* would create it or reuse a
    pre-existing container, because a container that already exists belongs to
    whoever made it and its metadata is not the archive's to normalize.
    """

    manifest = verify_cold_archive(control_plane, archive_identity, policy)
    authority = bind_representation_authority(control_plane, manifest)
    actions: list[PlannedAction] = []
    conflicts: list[dict[str, Any]] = []

    for payload in sorted(
        manifest["members"], key=lambda item: (str(item["path"]).count("/"), str(item["path"]))
    ):
        member = ArchiveMember.from_dict(payload)
        destination = workspace / member.path
        authorized, detail = boundary.destructive_authorization(destination)
        if not authorized:
            conflicts.append({"path": str(destination), "reason": detail})
            continue
        crossed, why = crosses_mount_boundary(workspace, destination)
        if crossed:
            conflicts.append({"path": str(destination), "reason": why})
            continue
        view = snapshot.view(member.artifact_id) if member.artifact_id else None
        if view is not None and (view.current or view.restart_required):
            conflicts.append(
                {
                    "path": str(destination),
                    "reason": (
                        f"owner artifact {member.artifact_id} is current or "
                        "restart-required; a restore never overwrites live evidence"
                    ),
                }
            )
            continue

        if member.kind == "directory":
            preexisting = destination.is_dir()
            if destination.exists() and not preexisting:
                conflicts.append(
                    {
                        "path": str(destination),
                        "reason": "restore destination conflicts with a non-directory",
                    }
                )
                continue
            actions.append(
                planned_action(
                    action=ACTION_RESTORE_CONTAINER,
                    path=destination,
                    artifact_id=member.artifact_id,
                    reason=(
                        "pre-existing container reused without metadata change"
                        if preexisting
                        else "container created by this restore"
                    ),
                    capability_cost="none",
                    owner_state_identity=view.state_identity if view is not None else "",
                    binding={
                        "archived_mode": int(member.mode),
                        "preexisting": bool(preexisting),
                        "existing_mode": (
                            stat.S_IMODE(destination.lstat().st_mode)
                            if preexisting
                            else None
                        ),
                        "existing_identity": (
                            _filesystem_node_identity(destination)
                            if preexisting
                            else None
                        ),
                        "parent": str(destination.parent),
                        "parent_chain": parent_chain_identity(workspace, destination),
                        "representation_authority": authority,
                    },
                    size_bytes=0,
                )
            )
            continue

        if destination.exists():
            if destination.is_symlink() or not destination.is_file():
                conflicts.append(
                    {
                        "path": str(destination),
                        "reason": "restore destination conflicts with a non-file",
                    }
                )
                continue
            if int(destination.stat().st_size) != int(member.size_bytes) or sha256_file(
                destination, limit_bytes=int(member.size_bytes)
            ) != member.sha256:
                conflicts.append(
                    {
                        "path": str(destination),
                        "reason": (
                            "restore destination already exists with different "
                            "authoritative content; nothing is overwritten implicitly"
                        ),
                    }
                )
                continue
        actions.append(
            planned_action(
                action=ACTION_RESTORE_MEMBER,
                path=destination,
                artifact_id=member.artifact_id,
                reason="historical member reinstalled from an authenticated archive",
                capability_cost="none",
                owner_state_identity=view.state_identity if view is not None else "",
                binding={
                    "sha256": member.sha256,
                    "size_bytes": int(member.size_bytes),
                    "mode": int(member.mode),
                    "parent_chain": parent_chain_identity(workspace, destination),
                    "representation_authority": authority,
                },
                size_bytes=int(member.size_bytes),
            )
        )
    return actions, manifest, conflicts


def archive_restore_engine(
    *,
    workspace: Path,
    control_plane: StorageControlPlane,
    policy: StoragePolicy,
    boundary: Any,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
    failpoint: Failpoint = _no_failpoint,
):
    """Stage, install, authenticate, and only then publish a terminal receipt."""

    def _engine(
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        # Nothing is staged, installed, or journalled until the retained
        # representation this plan bound re-authenticates under the lease.
        try:
            manifest_now = reauthenticate_representation(
                control_plane, policy, authority
            )
        except (StorageArchiveError, StorageControlPlaneError) as exc:
            for action in plan.actions:
                result.refused.append({**action.to_dict(), "refusal": str(exc)})
            result.detail = (
                "the retained cold representation failed protected reauthentication; "
                f"nothing was staged, installed, or journalled: {exc}"
            )
            return
        control_plane.ensure()
        identity = str(manifest_now["archive_identity"])
        blob = control_plane.resolve_archive_blob(str(manifest_now["archive_locator"]))
        expected = _expected_member_map(manifest_now)
        staging = control_plane.staging_root_for(identity)
        journal = control_plane.journal_path(identity)

        authorized, detail = boundary.destructive_authorization(staging)
        if not authorized:
            raise StorageArchiveError(
                f"restore staging root is not campaign-owned: {detail}"
            )

        durable_publish_json(
            journal,
            {
                "schema": COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA,
                "archive_identity": identity,
                "opened_utc": _utc_now(),
                "state": "staging",
                "member_count": int(manifest_now["member_count"]),
            },
        )
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            _stage_members(blob, manifest_now, expected, staging)
            failpoint(BOUNDARY_AFTER_STAGING)

            restored = 0
            reused = 0
            created_containers = 0
            for index, action in enumerate(plan.actions):
                if index:
                    failpoint(BOUNDARY_DURING_INSTALL)
                if action.action == ACTION_RESTORE_CONTAINER:
                    created_containers += _install_container(action, result)
                    continue
                installed = _install_member(action, staging, workspace, result)
                if installed:
                    restored += 1
                    result.restored_bytes += int(action.binding["size_bytes"])
                else:
                    reused += 1

            _authenticate_installed(workspace, plan)
            failpoint(BOUNDARY_BEFORE_RECEIPT)
            receipt = {
                "schema": COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA,
                "archive_identity": identity,
                "restored_files": restored,
                "already_present_files": reused,
                "created_containers": created_containers,
                "verified_member_count": len(expected),
                "status": "complete",
                "detail": (
                    "every installed byte and required container postcondition was "
                    "authenticated; restored evidence remains historical"
                ),
                "promotes_currentness": False,
                "grants_scientific_authority": False,
            }
            durable_publish_json(
                journal,
                {
                    "schema": COLD_ARCHIVE_RESTORE_JOURNAL_SCHEMA,
                    "archive_identity": identity,
                    "closed_utc": _utc_now(),
                    "state": "terminal",
                    "receipt": receipt,
                },
            )
            result.payload = receipt
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return _engine


def _install_container(action: PlannedAction, result: StorageExecutionResult) -> int:
    """Create an archive-owned directory, or reuse a pre-existing one untouched.

    A directory this restore creates may carry the archived owner-certified
    mode. A directory that already existed belongs to whoever created it: it may
    be shared with unrelated retained artifacts, and an archive containing an
    entry with the same path is not authorization to normalize it.
    """

    destination = action.path
    verify_parent_chain(action.binding.get("parent_chain", ()))
    if bool(action.binding.get("preexisting")):
        if not destination.is_dir():
            raise StorageArchiveError(
                f"pre-existing container disappeared before installation: {destination}"
            )
        expected_identity = action.binding.get("existing_identity")
        if expected_identity is not None:
            verify_parent_chain((expected_identity,))
        observed = stat.S_IMODE(destination.lstat().st_mode)
        expected = action.binding.get("existing_mode")
        if expected is not None and observed != int(expected):
            raise StorageArchiveError(
                f"pre-existing container metadata changed after planning: {destination}"
            )
        result.completed.append(
            {**action.to_dict(), "reused_existing_container": True, "mode_changed": False}
        )
        return 0
    parent = destination.parent
    if not parent.is_dir():
        raise StorageArchiveError(
            f"restore parent path is missing or is not a directory: {parent}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    result.mutated = True
    result.completed.append({**action.to_dict(), "created_container": True})
    os.chmod(destination, int(action.binding["archived_mode"]))
    from ..target_size_execution.persistence import fsync_parent_directory

    fsync_parent_directory(destination)
    return 1


def _install_member(
    action: PlannedAction,
    staging: Path,
    workspace: Path,
    result: StorageExecutionResult,
) -> bool:
    from ..target_size_execution.persistence import fsync_parent_directory

    destination = action.path
    verify_parent_chain(action.binding.get("parent_chain", ()))
    relative = canonical_member_path(workspace, destination)
    if destination.exists():
        result.completed.append({**action.to_dict(), "already_present": True})
        return False
    parent = destination.parent
    if not parent.is_dir():
        raise StorageArchiveError(
            f"restore parent path is missing or is not a directory: {parent}"
        )
    if parent.is_symlink():
        raise StorageArchiveError(f"restore parent path became a symlink: {parent}")
    crossed, why = crosses_mount_boundary(workspace, destination)
    if crossed:
        raise StorageArchiveError(f"restore destination crosses a mount boundary: {why}")
    os.replace(staging / relative, destination)
    result.mutated = True
    result.completed.append({**action.to_dict(), "installed": True})
    os.chmod(destination, int(action.binding["mode"]))
    fsync_parent_directory(destination)
    return True


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


def _authenticate_installed(workspace: Path, plan: StoragePlan) -> None:
    """Final authentication over installed bytes *and* container postconditions."""

    for action in plan.actions:
        if action.action == ACTION_RESTORE_CONTAINER:
            if not action.path.is_dir():
                raise StorageArchiveError(
                    f"required restore container is missing: {action.path}"
                )
            if not bool(action.binding.get("preexisting")):
                observed = stat.S_IMODE(action.path.lstat().st_mode)
                if observed != int(action.binding["archived_mode"]):
                    raise StorageArchiveError(
                        f"restore-created container has unexpected metadata: {action.path}"
                    )
            continue
        authenticate_file(
            action.path,
            expected_sha256=str(action.binding["sha256"]),
            expected_size=int(action.binding["size_bytes"]),
        )
    del workspace


# ---------------------------------------------------------------------------
# Catalog / journal inspection
# ---------------------------------------------------------------------------


def read_restore_journal(
    control_plane: StorageControlPlane, archive_identity: str
) -> dict[str, Any] | None:
    """The storage owner's own account of an in-flight or finished restore."""

    path = control_plane.journal_path(archive_identity)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") not in SUPPORTED_JOURNAL_SCHEMAS:
        raise StorageArchiveError(
            f"unsupported restore journal schema at {path}; it is retained and "
            "rejected rather than reinterpreted"
        )
    return payload


def list_archives(control_plane: StorageControlPlane) -> tuple[dict[str, Any], ...]:
    """Every retained cold representation, identity-keyed.

    There is no ``latest`` authority here: the catalog is identity-keyed, and a
    convenience pointer would be exactly the kind of implicit currentness this
    package refuses to create.
    """

    return tuple(control_plane.iter_catalog_entries())


def archive_admission(
    location: Path, policy: StoragePolicy, members: Sequence[ArchiveMember]
) -> AdmissionObservation:
    return admit_storage_operation(
        location,
        policy,
        required_peak_bytes=archive_container_bytes(members),
        required_inodes=archive_entry_count(members),
    )


def restore_admission(
    location: Path, policy: StoragePolicy, manifest: Mapping[str, Any]
) -> AdmissionObservation:
    members = tuple(ArchiveMember.from_dict(item) for item in manifest["members"])
    expanded = int(manifest["total_expanded_bytes"])
    return admit_storage_operation(
        location,
        policy,
        # Staged and installed copies coexist until staging is cleared.
        required_peak_bytes=2 * expanded + archive_container_bytes(members),
        required_inodes=restore_entry_count(members),
    )


__all__ = [
    "bind_representation_authority",
    "parent_chain_identity",
    "reauthenticate_representation",
    "representation_authority",
    "verify_parent_chain",
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
    "ArchiveMember",
    "ArchivePlanBundle",
    "StorageArchiveError",
    "archive_admission",
    "archive_container_bytes",
    "archive_create_engine",
    "archive_reclaim_engine",
    "archive_restore_engine",
    "build_archive_plan_actions",
    "build_reclaim_plan_actions",
    "build_restore_plan_actions",
    "canonical_member_path",
    "collect_members",
    "list_archives",
    "logical_identity",
    "read_manifest",
    "read_restore_journal",
    "representation_identity",
    "restore_admission",
    "select_archive_roots",
    "verify_cold_archive",
]
