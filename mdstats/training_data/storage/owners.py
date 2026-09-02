"""Owner views: what every current P1-P7 owner says about its own artifacts.

Storage is never a second authority for scientific identity.  It therefore
never classifies an artifact by its pathname; it asks the owning API what the
artifact is, whether the owner still needs it, and what else depends on it.
This module is the adapter layer that turns each accepted current owner into a
uniform :class:`OwnerArtifactView`, including the **dependency edges** the
inventory needs to compute cross-owner retention closure.

The census behind these adapters, against the bound intake baseline:

``campaign_store``
    ``.mdstats/campaign.sqlite3`` is authoritative currentness/state.
    ``.mdstats/records/`` holds externalized large record payloads referenced
    by that database.  ``.mdstats/hash-receipts.sqlite3`` is *not* state: it is
    a stat-keyed SHA-256 acceleration cache whose loss only forces rehashing.

``P1``
    ``.mdstats/frame-cache`` normalized VASP arrays, bound to the DATA2
    source-catalog digest and each run's source identity/control signature.
    The campaign rebuilds it on demand from the authenticated external training
    root, which is the only positive exact-reconstruction seam in the census.

``P2``
    Resolved target-size policy, ``U_size``/``P_train``/``pi_*``/``M1-M3``,
    exact ``T_N``, qualification state, and reducer definition live inside the
    campaign store as records, not as a separate file family.  Storage reports
    them through the store owner and never infers them from P3 paths.

``P3``
    ``.mdstats/target-size/g<gen>`` execution/reconciliation/head evidence,
    fenced by the accepted filesystem evidence-graph retention owner.

``P4``
    Current selected/current-terminal authority, published in the campaign
    store.  Its canonical loader re-reads P3 evidence, so it *pins* the P3
    execution root of its generation.

``P5``
    ``.mdstats/post-selection/g<gen>`` with ``objects/`` immutable evidence and
    ``runs/<run>/`` execution bulk.  The current final publication names exact
    representative checkpoints under those run roots.

``P7``
    ``.mdstats/qualification/g<gen>`` with ``objects/`` durable release
    evidence, ``attempts/<identity>`` scratch, and reveal state.  Its current
    publication is a read-only descendant of P5 and re-authenticates the P5
    member bytes at their canonical hot paths.

``storage``
    ``.mdstats/storage`` control plane (see :mod:`.control_plane`).
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .control_plane import (
    StorageControlPlane,
    open_storage_control_plane_readonly,
)


class ArtifactClass(str, Enum):
    """The storage-facing meaning of one material persistent artifact."""

    AUTHORITATIVE_EXTERNAL_INPUT = "authoritative_external_input"
    DURABLE_SCIENTIFIC_EVIDENCE = "durable_scientific_evidence"
    CURRENTNESS_STATE = "currentness_state"
    RESTART_STATE = "restart_state"
    REPRODUCIBILITY_BULK = "reproducibility_bulk"
    REUSABLE_CACHE_INDEX = "reusable_cache_index"
    TEMPORARY_SCRATCH = "temporary_scratch"
    DIAGNOSTIC_EVIDENCE = "diagnostic_evidence"
    ARCHIVE_REPRESENTATION = "archive_representation"
    STORAGE_CONTROL_PLANE = "storage_control_plane"


#: Owner identifiers.  These name real current owners, not lifecycle stages.
OWNER_EXTERNAL = "external_input"
OWNER_CAMPAIGN_STORE = "campaign_store"
OWNER_P1 = "p1"
OWNER_P2 = "p2"
OWNER_P3 = "p3"
OWNER_P4 = "p4"
OWNER_P5 = "p5"
OWNER_P7 = "p7"
OWNER_STORAGE = "storage_control_plane"


class SubtreeCoverage(str, Enum):
    """How far down a directory artifact the owner's certification reaches.

    Lexical containment beneath an owner path is never by itself semantic
    ownership.  A directory view must say which of these it is, and a
    consequential recursive action may only recurse destructively through
    ``CLOSED``.

    ``CLOSED``
        The owner certifies, from its own authenticated records or layout
        contract, that every traversable descendant belongs to this artifact.
        Recursive collection, deletion, and dedup enumeration are permitted,
        and an unexpected descendant contradicts the certification.

    ``CONTAINER``
        The directory is owner-known but its descendants are not certified as
        a set.  Only individually owner-certified descendants may be acted on;
        every other child is ambiguous and retained.

    ``NOT_APPLICABLE``
        The artifact is a single file or is never a recursion target.
    """

    CLOSED = "closed_subtree"
    CONTAINER = "container_open_subtree"
    NOT_APPLICABLE = "not_applicable"


class OwnerViewError(RuntimeError):
    """An owner could not be interrogated, so its artifacts stay retained."""


class OwnerGraphError(RuntimeError):
    """The owner graph is not a valid basis for consequential planning."""


#: Names the P7 owner's own released-attempt authorizer.  The common inventory
#: delegates to it instead of re-deriving authority from a pathname walk.
P7_RELEASED_ATTEMPT_AUTHORIZER = "p7:released_attempt"

NODE_FILE = "file"
NODE_DIRECTORY = "directory"
NODE_SYMLINK = "symlink"
NODE_OTHER = "other"
NODE_ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class CertifiedNode:
    """One node an owner recorded as its own: a canonical path *and* a kind."""

    path: str
    kind: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "kind": self.kind}


def crosses_mount_boundary_at(parent_fd: int, name: str, display: Path):
    """Re-exported so the P7 owner has one mount-boundary authority, not two."""

    from .trust import crosses_mount_boundary_at as _at

    return _at(parent_fd, name, display)


def observed_node_identity(path: Path) -> dict[str, int] | None:
    """The filesystem identity of ``path`` itself, never of a symlink target."""

    try:
        stats = os.lstat(path)
    except OSError:
        return None
    return {"device": int(stats.st_dev), "inode": int(stats.st_ino)}


def observed_node_kind(path: Path) -> str:
    """Classify one path without ever following a symlink.

    ``lstat`` is the whole point. Anything that resolves a link before
    classifying would let a symlink substituted at a recorded member name
    present its *target's* kind, and the comparison against the owner's proof
    would then pass on bytes the owner never wrote.
    """

    try:
        stats = os.lstat(path)
    except OSError:
        return NODE_ABSENT
    if stat.S_ISLNK(stats.st_mode):
        return NODE_SYMLINK
    if stat.S_ISDIR(stats.st_mode):
        return NODE_DIRECTORY
    if stat.S_ISREG(stats.st_mode):
        return NODE_FILE
    return NODE_OTHER


def read_owner_record_bytes(path: Path) -> bytes | None:
    """Read one owner authority file, refusing anything but a real regular file.

    An owner proof that can be redirected is not a proof. ``O_NOFOLLOW`` refuses
    a symlink at the final component in the same syscall that opens it, and
    ``fstat`` on the resulting descriptor - not a second ``lstat`` on the name -
    is what proves the bytes being parsed came from the regular file that was
    checked. An ``lstat`` followed by an ordinary read is a race, not a check.
    """

    if not hasattr(os, "O_NOFOLLOW"):
        # Without O_NOFOLLOW there is no way to refuse a symlink in the same
        # syscall that opens the name, and an lstat/open pair is a race rather
        # than a check. This package's supported target is POSIX with
        # O_NOFOLLOW; anywhere else, an owner authority record simply cannot be
        # authenticated and grants nothing.
        return None
    # ``O_NONBLOCK`` because opening a planted FIFO for reading would otherwise
    # block until a writer appeared. The kind is decided by ``fstat`` below; a
    # special node must be refused, not waited on.
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        handle = os.open(path, flags)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(handle, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError:
        return None
    finally:
        os.close(handle)


@dataclass(frozen=True, slots=True)
class OwnerArtifactView:
    """One owner's own statement about one artifact it owns.

    ``requires`` names the artifact identities this artifact needs in order to
    remain valid.  Edges point from dependent to dependency, which is what lets
    the inventory compute a protection closure without any owner having to know
    about storage policy.

    ``state_identity`` is the owner's own canonical identity for the state this
    view describes - a head digest, a pointer digest, a revision. It is derived
    from real owner records and is never a storage-authored reconstruction of
    scientific state. Its only job is to make same-generation owner advancement
    visible to plan revalidation.
    """

    owner: str
    artifact_id: str
    path: Path
    artifact_class: ArtifactClass
    detail: str
    generation: int | None = None
    current: bool = False
    restart_required: bool = False
    immutable: bool = False
    #: A current public resolver dereferences this canonical hot path directly.
    #: Such an artifact is never hot-removable by archive.
    hot_path_required: bool = False
    #: Owner-certified exact reconstruction: eviction costs only recomputation.
    cache_reconstructible: bool = False
    #: The cache tier may actually evict this artifact.  Reconstructibility is
    #: necessary but not sufficient: an acceleration cache the running storage
    #: operation is itself writing to is reconstructible and still not a
    #: sensible eviction target.
    cache_evictable: bool = False
    #: Owner-approved cold-replaceable reproducibility bulk.
    archive_eligible: bool = False
    #: Owner-certified immutable content *and* metadata contract for hardlink
    #: deduplication.
    dedup_eligible: bool = False
    #: Owner-required filesystem metadata semantics for a dedup candidate.
    metadata_contract: str = "mode_only"
    #: Zero-capability-loss reclamation the owner has positively released.
    safe_reclaimable: bool = False
    #: The artifact root itself must survive, but what it contains is decided
    #: per child.  Without this, a container view would blanket-protect members
    #: its owner has positively released.
    container_only: bool = False
    #: How far the owner's certification reaches below a directory artifact.
    coverage: SubtreeCoverage = SubtreeCoverage.NOT_APPLICABLE
    #: Exactly the descendants the owner releases for action, relative to
    #: ``path``, **with their recorded node kind**.  A path string alone is not
    #: enough authority: a regular file replaced by a directory at the same
    #: relative name - or the reverse - is an ownership contradiction, and a
    #: comparison that had already discarded the kind could not see it.
    certified_nodes: tuple[CertifiedNode, ...] = ()
    #: The same set as bare relative paths.  Derived display/compatibility
    #: surface only; recursive disappearance is never authorized from it.
    certified_members: tuple[str, ...] = ()
    #: Descendants the owner knows about and never releases - its own record
    #: and lock files.  They are neither members nor contradictions: archiving
    #: or removing them would destroy the certification itself.
    retained_members: tuple[str, ...] = ()
    #: The owner-specific authorizer that must decide this view's recursive
    #: members, when a generic pathname walk would lose the identity the
    #: certification was performed against.  Empty means the common typed walk
    #: is a faithful representation of the accepted authority.
    exact_authorizer: str = ""
    #: The ``(device, inode)`` of the *authority* root the owner certified
    #: against - for a released P7 attempt member that is the attempt directory,
    #: not this view's own path.  The owner-specific authorizer proves it is
    #: still looking at the same directory it was granted authority over.
    root_identity: Mapping[str, int] | None = None
    #: The ``(device, inode)`` of ``path`` itself as observed while the view was
    #: built.  The final recursive removal re-observes it immediately before
    #: entry, so a container replaced after certification is refused rather than
    #: entered under the authority granted to the original.
    path_identity: Mapping[str, int] | None = None
    #: This owner is the exclusive writer of the whole subtree by construction,
    #: so every descendant is its own.  Reserved for a private scratch/control
    #: area no other component writes into - storage's own staging, for
    #: instance - where enumerating a member set would be circular and the
    #: exclusivity is the real ownership statement.  It is never a substitute
    #: for a recorded member set on a directory another component writes into.
    owner_exclusive: bool = False
    #: The owner's canonical identity for the state this view describes.
    state_identity: str = ""
    requires: tuple[str, ...] = ()
    reconstruction: str = ""

    def __post_init__(self) -> None:
        if self.certified_nodes and not self.certified_members:
            object.__setattr__(
                self,
                "certified_members",
                tuple(item.path for item in self.certified_nodes),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "artifact_id": self.artifact_id,
            "path": str(self.path),
            "artifact_class": self.artifact_class.value,
            "detail": self.detail,
            "generation": self.generation,
            "current": bool(self.current),
            "restart_required": bool(self.restart_required),
            "immutable": bool(self.immutable),
            "hot_path_required": bool(self.hot_path_required),
            "cache_reconstructible": bool(self.cache_reconstructible),
            "cache_evictable": bool(self.cache_evictable),
            "archive_eligible": bool(self.archive_eligible),
            "dedup_eligible": bool(self.dedup_eligible),
            "metadata_contract": self.metadata_contract,
            "safe_reclaimable": bool(self.safe_reclaimable),
            "container_only": bool(self.container_only),
            "coverage": self.coverage.value,
            "certified_nodes": [item.to_dict() for item in self.certified_nodes],
            "certified_members": list(self.certified_members),
            "retained_members": list(self.retained_members),
            "state_identity": self.state_identity,
            "requires": list(self.requires),
            "reconstruction": self.reconstruction,
        }


@dataclass
class OwnerViewSet:
    """Every owner view plus the unresolved-owner facts storage must respect."""

    views: tuple[OwnerArtifactView, ...] = ()
    #: Owners that could not be authenticated.  Each entry retains its subtree.
    unresolved: tuple[tuple[str, str], ...] = ()
    current_generation: int | None = None
    #: Graph integrity problems: duplicate identities, or dependency edges that
    #: resolve to no owner view.  A non-empty list makes the protection closure
    #: incomplete and fails consequential planning closed.
    integrity_failures: tuple[str, ...] = ()

    def by_id(self) -> dict[str, OwnerArtifactView]:
        return {view.artifact_id: view for view in self.views}

    @property
    def is_consequentially_planable(self) -> bool:
        return not self.integrity_failures


def validate_owner_graph(views: Sequence[OwnerArtifactView]) -> tuple[str, ...]:
    """Uniqueness and dependency-resolution integrity of one owner graph.

    An incomplete dependency graph cannot establish deletion, archive, or dedup
    authority: a `requires` edge naming an artifact nobody reported is a hole in
    the protection closure, and a duplicate identity means one owner's statement
    silently replaced another's.  Both are reported rather than repaired, and
    neither is papered over with a synthetic path or a guessed owner.
    """

    failures: list[str] = []
    seen: dict[str, OwnerArtifactView] = {}
    for view in views:
        previous = seen.get(view.artifact_id)
        if previous is not None:
            failures.append(
                f"duplicate owner artifact identity {view.artifact_id!r} reported by "
                f"{previous.owner!r} ({previous.path}) and {view.owner!r} ({view.path})"
            )
            continue
        seen[view.artifact_id] = view
    for view in views:
        for dependency in view.requires:
            if dependency not in seen:
                failures.append(
                    f"owner artifact {view.artifact_id!r} requires {dependency!r}, which "
                    "no owner view reported; the protection closure is incomplete"
                )
    return tuple(sorted(set(failures)))


def _absolute(path: Any) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _readonly_trainer() -> Any:
    """A trainer placeholder that fails loudly if a read-only path uses it."""

    class _RefusesToTrain:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
            raise OwnerViewError(
                "Storage inventory resolved an owner context read-only; it never trains."
            )

    return _RefusesToTrain()


# ---------------------------------------------------------------------------
# CampaignStore / P2 / receipt-cache owner
# ---------------------------------------------------------------------------


def _campaign_writer_lock_path(paths: Any) -> Path:
    from .._campaign_cli_core import CAMPAIGN_WRITER_LOCK_SUFFIX

    return Path(str(_absolute(paths.state_db)) + CAMPAIGN_WRITER_LOCK_SUFFIX)


def campaign_store_views(
    cfg: Mapping[str, Any], paths: Any, store: Any
) -> list[OwnerArtifactView]:
    """CampaignStore authoritative state, external records, and receipt cache.

    F7 correction: the SHA-256 receipt database is accounted as reusable cache
    and never grouped with authoritative state.  Its loss forces rehashing and
    nothing else, and no storage action treats a receipt as proof of validity.
    """

    internal = _absolute(paths.internal)
    views = [
        OwnerArtifactView(
            owner=OWNER_CAMPAIGN_STORE,
            artifact_id="campaign_store:state",
            path=_absolute(paths.state_db),
            artifact_class=ArtifactClass.CURRENTNESS_STATE,
            detail=(
                "authoritative campaign state, current pointers, and the P2 "
                "statistical/reducer authorities"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
        ),
        OwnerArtifactView(
            owner=OWNER_CAMPAIGN_STORE,
            artifact_id="campaign_store:external_records",
            path=internal / "records",
            artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
            detail=(
                "root of the externalized large record payloads referenced by "
                "campaign state; individual payloads are classified per child"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
            container_only=True,
            requires=("campaign_store:state",),
        ),
        OwnerArtifactView(
            owner=OWNER_CAMPAIGN_STORE,
            artifact_id="campaign_store:hash_receipts",
            path=internal / "hash-receipts.sqlite3",
            artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
            detail=(
                "stat-keyed SHA-256 acceleration receipts; loss or eviction only "
                "forces a fresh byte hash and never establishes validity. Retained "
                "by both tiers in this successor: it is the acceleration cache the "
                "running storage operation is itself writing to, so evicting it "
                "mid-operation costs work and gains nothing"
            ),
            cache_reconstructible=True,
            cache_evictable=False,
            reconstruction="rehash on the next stat-identity miss",
        ),
        OwnerArtifactView(
            owner=OWNER_CAMPAIGN_STORE,
            artifact_id="campaign_store:writer_lock",
            path=_campaign_writer_lock_path(paths),
            artifact_class=ArtifactClass.STORAGE_CONTROL_PLANE,
            detail=(
                "the advisory lock every campaign-state writer takes before "
                "mutating. Coordination infrastructure, never scientific "
                "authority, cache, or reclaimable scratch: unlinking a held "
                "advisory-lock pathname would split the serialization domain "
                "between the old inode and a freshly created one, so it is never "
                "a cleanup, archive, or dedup target"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
            requires=("campaign_store:state",),
        ),
    ]
    views.append(
        OwnerArtifactView(
            owner=OWNER_P2,
            artifact_id="p2:statistical_authorities",
            path=_absolute(paths.state_db),
            artifact_class=ArtifactClass.CURRENTNESS_STATE,
            detail=(
                "resolved target-size policy, U_size, P_train/M3, pi_train/pi_eval, "
                "M1-M3, exact T_N, qualification state, and the reducer definition. "
                "These are campaign-store records, never inferred from P3 files or "
                "path names"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
            container_only=True,
            requires=("campaign_store:state",),
        )
    )
    views.extend(_orphan_external_record_views(cfg, store))
    for name in ("data7-cache", "data8-fixed-cache", "evaluation-graphs"):
        candidate = internal / name
        if candidate.exists():
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P1,
                    artifact_id=f"p1:{name}",
                    path=candidate,
                    artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
                    detail=(
                        f"{name} historical derived cache with no current owner-certified "
                        "reconstruction seam; retained"
                    ),
                )
            )
    return views


# ---------------------------------------------------------------------------
# P1 frame cache: the one positive exact-reconstruction seam in the census
# ---------------------------------------------------------------------------


FRAME_CACHE_DIRECTORY = "frame-cache"


def frame_cache_view(paths: Any, store: Any) -> OwnerArtifactView | None:
    """Classify the normalized frame cache through its real owner contract.

    The cache is exactly reconstructible only when its owner can still prove
    the reconstruction: the DATA2 source catalog must be resolvable, the cache
    manifest must belong to that exact catalog digest, and every per-run source
    identity/control signature must still match.  If any of that is missing the
    cache is retained, because an unprovable rebuild is a capability loss.
    """

    root = _absolute(paths.internal) / FRAME_CACHE_DIRECTORY
    if not root.exists():
        return None
    detail = (
        "normalized frame arrays; retained by every tier because P1 exposes no "
        "consumer/builder liveness seam that could prove concurrent non-use"
    )
    reconstructible = False
    reconstruction = ""
    try:
        import json

        manifest_path = root / "frame-cache.json"
        catalog = _resolve_source_catalog(store)
        if catalog is None:
            detail += "; DATA2 source catalog is not resolvable, so rebuild is unprovable"
        elif not manifest_path.is_file():
            detail += "; cache manifest is absent"
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("source_catalog_digest") != catalog.content_digest:
                detail += "; cache belongs to another DATA2 catalog"
            else:
                by_run = {source.run_id: source for source in catalog.sources}
                records = {
                    str(item["run_id"]): item for item in manifest.get("records", ())
                }
                if set(records) != set(by_run):
                    detail += "; cache does not cover the DATA2 runs exactly"
                elif all(
                    records[run].get("source_identity_signature")
                    == by_run[run].source_identity_signature
                    and records[run].get("source_control_bundle_signature")
                    == by_run[run].source_control_bundle_signature
                    for run in by_run
                ):
                    reconstructible = True
                    reconstruction = (
                        "one source read per DATA2 run from the authenticated external "
                        "training root, then finalize_frame_data_cache"
                    )
                    detail += (
                        "; owner-certified exactly reconstructible from the authenticated "
                        "DATA2 source catalog"
                    )
                else:
                    detail += "; cached source identity/controls no longer match DATA2"
    except Exception as exc:  # fail toward retention
        detail += f"; owner certification failed ({exc})"
        reconstructible = False
    return OwnerArtifactView(
        owner=OWNER_P1,
        artifact_id="p1:frame_cache",
        path=root,
        artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
        detail=detail,
        cache_reconstructible=reconstructible,
        # Reconstructibility proves capability recovery, not concurrent non-use.
        # P1 exposes no consumer/builder liveness seam: the cache is opened
        # mmap-backed and its handles can outlive the helper call that made
        # them, so nothing here can prove no reader or builder is active. Until
        # such a seam exists, the cache tier reports this family and evicts
        # nothing, which is a legitimate no-op rather than a guess.
        cache_evictable=False,
        reconstruction=reconstruction,
    )


def _orphan_external_record_views(
    cfg: Mapping[str, Any], store: Any
) -> list[OwnerArtifactView]:
    """External record payloads the CampaignStore owner no longer references.

    The reference set comes from the store's own ``storage_references`` API, not
    from a pathname convention.  Publication of a payload and the state row that
    references it are separate operations, so a payload younger than the
    configured publication window is retained: releasing it would race the
    reference that has not landed yet.
    """

    import time

    if store is None:
        return []
    try:
        root = Path(store.external_record_directory)
        references = set(store.storage_references())
    except Exception:
        return []
    if not root.is_dir():
        return []
    resolved_root = root.resolve()
    keep: set[Path] = set()
    for reference in references:
        try:
            relative = Path(reference).relative_to(resolved_root)
        except ValueError:
            continue
        if relative.parts:
            keep.add((root / relative.parts[0]).resolve())
    window_hours = 6.0
    section = cfg.get("cleanup", {}) if isinstance(cfg, Mapping) else {}
    if isinstance(section, Mapping):
        window_hours = float(section.get("stale_age_hours", window_hours))
    stale_before = time.time() - max(0.25, window_hours) * 3600.0
    views: list[OwnerArtifactView] = []
    for child in sorted(root.iterdir()):
        try:
            resolved = child.resolve()
            recent = child.lstat().st_mtime > stale_before
        except OSError:
            continue
        if resolved in keep:
            views.append(
                OwnerArtifactView(
                    owner=OWNER_CAMPAIGN_STORE,
                    artifact_id=f"campaign_store:record:{child.name}",
                    path=_absolute(child),
                    artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                    detail="external record payload a campaign state row references",
                    current=True,
                    restart_required=True,
                    hot_path_required=True,
                    requires=("campaign_store:state",),
                )
            )
            continue
        certified, certification, nodes = store.certify_closed_external_record(child)
        views.append(
            OwnerArtifactView(
                owner=OWNER_CAMPAIGN_STORE,
                artifact_id=f"campaign_store:orphan_record:{child.name}",
                path=_absolute(child),
                artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                detail=(
                    "external record payload retained inside the publication window"
                    if recent
                    else f"external record payload no campaign state row references; "
                    f"{certification}"
                ),
                current=recent,
                restart_required=recent,
                safe_reclaimable=not recent and certified,
                coverage=(
                    SubtreeCoverage.CLOSED
                    if certified and child.is_dir()
                    else SubtreeCoverage.CONTAINER
                    if child.is_dir()
                    else SubtreeCoverage.NOT_APPLICABLE
                ),
                certified_nodes=tuple(
                    CertifiedNode(path=path, kind=kind) for path, kind in nodes
                )
                if certified
                else (),
                container_only=child.is_dir() and not certified,
            )
        )
    return views


def _resolve_source_catalog(store: Any) -> Any | None:
    if store is None:
        return None
    try:
        import mdstats

        return store.get_record_optional(
            "source_catalog", mdstats.TrainingDataSourceCatalog
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# P3 / P4
# ---------------------------------------------------------------------------


def target_size_views(
    paths: Any, store: Any
) -> tuple[list[OwnerArtifactView], int | None, tuple[tuple[str, str], ...]]:
    """P3 execution evidence and the P4 current authority that pins it.

    The third return value carries unresolved-owner facts.  When the P3/P4
    authority cannot be read at all, ``current_generation`` is unknown - and an
    unknown current generation must never be read as "every generation is
    historical".  That is the difference between a campaign with no selection
    and a campaign whose selection authority is broken, and only the second one
    is a reason to refuse.
    """

    from ..campaign_target_size_paths import (
        TARGET_SIZE_EXECUTION_ROOT_NAME,
        target_size_execution_root,
    )
    from ..campaign_target_size_retention import certify_closed_execution_root
    from ..campaign_target_size_state import (
        TargetSizeRegime,
        load_target_size_campaign_revision,
    )

    internal = _absolute(paths.internal)
    family_root = internal / TARGET_SIZE_EXECUTION_ROOT_NAME
    views: list[OwnerArtifactView] = []
    unresolved: list[tuple[str, str]] = []
    current_generation: int | None = None
    revision_identity = ""
    try:
        revision = load_target_size_campaign_revision(store)
    except Exception as exc:
        unresolved.append((OWNER_P3, f"target-size campaign revision unreadable: {exc}"))
        unresolved.append(
            (
                OWNER_P4,
                "the selected/current-terminal authority cannot be established while "
                "the target-size revision is unreadable",
            )
        )
        unresolved.append(
            (
                OWNER_P5,
                "downstream post-selection classification is unresolved because its "
                "upstream selected authority is unreadable",
            )
        )
        unresolved.append(
            (
                OWNER_P7,
                "downstream qualification classification is unresolved because its "
                "upstream selected authority is unreadable",
            )
        )
        return views, None, tuple(unresolved)
    if revision is not None and revision.state.regime is not TargetSizeRegime.LEGACY:
        current_generation = revision.state.generation
        revision_identity = "|".join(
            str(value)
            for value in (
                revision.state_revision,
                revision.state.regime.value,
                revision.state.lifecycle.value,
                revision.state.adopted_execution_head_digest,
                revision.state.screen_window_digest,
                revision.state.experiment_definition_digest,
                revision.state.terminal,
            )
        )

    if current_generation is not None:
        root = _absolute(target_size_execution_root(paths, current_generation))
        views.append(
            OwnerArtifactView(
                owner=OWNER_P3,
                artifact_id=f"p3:execution_root:g{current_generation}",
                path=root,
                artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                detail=(
                    "current target-size execution/reconciliation/head evidence, fenced "
                    "by the accepted P3 filesystem evidence-graph retention owner"
                ),
                generation=current_generation,
                current=True,
                restart_required=True,
                hot_path_required=True,
                immutable=False,
                coverage=SubtreeCoverage.CONTAINER,
                state_identity=revision_identity,
            )
        )
        views.append(
            OwnerArtifactView(
                owner=OWNER_P4,
                artifact_id=f"p4:current_selected:g{current_generation}",
                path=_absolute(paths.state_db),
                artifact_class=ArtifactClass.CURRENTNESS_STATE,
                detail=(
                    "current selected/current-terminal authority; its canonical loader "
                    "re-reads the P3 evidence closure of this generation"
                ),
                generation=current_generation,
                current=True,
                restart_required=True,
                hot_path_required=True,
                container_only=True,
                state_identity=revision_identity,
                requires=(
                    f"p3:execution_root:g{current_generation}",
                    "campaign_store:state",
                ),
            )
        )

    for root in _generation_roots(family_root):
        generation = _generation_of(root)
        if generation is None or generation == current_generation:
            continue
        layout_ok, why = certify_closed_execution_root(root)
        views.append(
            OwnerArtifactView(
                owner=OWNER_P3,
                artifact_id=f"p3:execution_root:g{generation}",
                path=root,
                artifact_class=ArtifactClass.REPRODUCIBILITY_BULK,
                detail=(
                    "historical target-size execution evidence for a superseded "
                    f"generation; {why}. P3 records no per-run member manifest, so "
                    "this root stays an open container: storage reports it and acts "
                    "on nothing inside it"
                ),
                generation=generation,
                immutable=False,
                # A closed-subtree certification needs an explicit owner-recorded
                # member set. P3 has a layout contract but no member manifest, so
                # no descendant here is individually authorized.
                archive_eligible=False,
                dedup_eligible=False,
                metadata_contract="mode_only",
                coverage=SubtreeCoverage.CONTAINER,
                container_only=True,
                state_identity=revision_identity,
            )
        )
        del layout_ok
    return views, current_generation, tuple(unresolved)


# ---------------------------------------------------------------------------
# P5
# ---------------------------------------------------------------------------


def post_selection_views(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    current_generation: int | None,
    certify: bool = True,
) -> tuple[list[OwnerArtifactView], tuple[tuple[str, str], ...]]:
    """P5 objects, run bulk, and the exact current publication member pins.

    The current publication's representative checkpoints are the cross-owner
    dependency that matters most: the current P7 publication is a read-only
    descendant that re-authenticates those exact P5 bytes at their canonical
    hot paths, and it does so *after* its attempt retention reference is
    released.  They are therefore pinned by the publication itself, not by an
    attempt lease.
    """

    from ..campaign_post_selection_runtime import (
        certified_post_selection_run_nodes,
        certify_closed_post_selection_run_root,
        post_selection_run_is_complete,
    )
    from ..post_selection_store import POST_SELECTION_ROOT_NAME, post_selection_root

    internal = _absolute(paths.internal)
    family_root = internal / POST_SELECTION_ROOT_NAME
    views: list[OwnerArtifactView] = []
    unresolved: list[tuple[str, str]] = []

    if current_generation is None and _generation_roots(family_root):
        # An unknown current generation is not the same as "nothing is current".
        # Classifying every P5 generation as historical on that basis would be a
        # semantic guess, so the family is recorded unresolved and retained.
        unresolved.append(
            (
                OWNER_P5,
                "no current target-size generation is established, so no post-selection "
                "generation can be classified as historical",
            )
        )

    for root in _generation_roots(family_root):
        generation = _generation_of(root)
        if generation is None:
            continue
        historical = current_generation is not None and generation != current_generation
        if (root / "objects").is_dir():
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P5,
                    artifact_id=f"p5:objects:g{generation}",
                    path=root / "objects",
                    artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                    detail=(
                        "immutable post-selection evidence: CV plan/acceptance, final "
                        "plan, publication decision, and predecessor reclosure"
                    ),
                    generation=generation,
                    current=not historical,
                    restart_required=not historical,
                    immutable=True,
                    hot_path_required=not historical,
                    coverage=SubtreeCoverage.CONTAINER,
                )
            )
        runs_root = root / "runs"
        if runs_root.is_dir():
            # The runs root is a container: P5 owns it, but each run root is the
            # unit the owner can actually certify. A run that is still executing,
            # or that carries a descendant P5 did not write, is never eligible.
            certified: list[str] = []
            for run_root in sorted(
                child for child in runs_root.iterdir() if child.is_dir()
            ):
                if certify:
                    closed, why = certify_closed_post_selection_run_root(run_root)
                else:
                    # Reporting must stay bounded, so it asks the owner's own
                    # O(1) completion question - is there a valid compact
                    # completion anchor? - and leaves the O(member-count)
                    # topology comparison to consequential planning. It is the
                    # same completion authority, so a run whose terminal
                    # evidence has legitimately gone cold still reports as
                    # finished.
                    closed, why = post_selection_run_is_complete(run_root)
                eligible = bool(historical and closed)
                recorded = (
                    tuple(
                        CertifiedNode(path=path, kind=kind)
                        for path, kind in certified_post_selection_run_nodes(run_root)
                    )
                    if (closed and certify)
                    else ()
                )
                if eligible:
                    certified.append(run_root.name)
                views.append(
                    OwnerArtifactView(
                        owner=OWNER_P5,
                        artifact_id=f"p5:run:g{generation}:{run_root.name}",
                        path=run_root,
                        artifact_class=ArtifactClass.REPRODUCIBILITY_BULK,
                        detail=(
                            "post-selection run evidence, materializations, and "
                            f"checkpoints; {why}"
                        ),
                        generation=generation,
                        current=not historical,
                        restart_required=not historical,
                        archive_eligible=eligible,
                        immutable=eligible,
                        dedup_eligible=eligible,
                        metadata_contract="mode_only",
                        coverage=(
                            SubtreeCoverage.CLOSED
                            if (closed and certify)
                            else SubtreeCoverage.CONTAINER
                        ),
                        certified_nodes=recorded,
                        retained_members=_run_infrastructure_members(run_root),
                        requires=(f"p5:objects:g{generation}",)
                        if (root / "objects").is_dir()
                        else (),
                    )
                )
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P5,
                    artifact_id=f"p5:runs:g{generation}",
                    path=runs_root,
                    artifact_class=ArtifactClass.REPRODUCIBILITY_BULK,
                    detail=(
                        "post-selection run container; each run root is certified "
                        "individually and an uncertified child is never acted on"
                    ),
                    generation=generation,
                    current=not historical,
                    restart_required=not historical,
                    container_only=True,
                    coverage=SubtreeCoverage.CONTAINER,
                    certified_nodes=tuple(
                        CertifiedNode(path=name, kind=NODE_DIRECTORY)
                        for name in certified
                    ),
                    requires=(f"p5:objects:g{generation}",)
                    if (root / "objects").is_dir()
                    else (),
                )
            )

    if current_generation is None:
        return views, tuple(unresolved)

    publication_id = f"p5:publication:g{current_generation}"
    if not selection_is_expected(store):
        # The campaign has not selected a target size yet, so there is no current
        # publication to resolve and nothing downstream to be unresolved about.
        return views, tuple(unresolved)
    try:
        context = _read_only_post_selection_context(cfg, paths, store)
    except Exception as exc:
        unresolved.append((OWNER_P5, f"current selected authority unresolved: {exc}"))
        return views, tuple(unresolved)
    if context is None:
        return views, tuple(unresolved)

    try:
        from ..post_selection_publication import (
            resolve_current_final_production_publication,
        )

        decision = resolve_current_final_production_publication(context)
    except Exception as exc:
        unresolved.append(
            (OWNER_P5, f"current final publication could not be authenticated: {exc}")
        )
        return views, tuple(unresolved)
    if decision is None:
        return views, tuple(unresolved)

    member_ids: list[str] = []
    for item in decision.published_seed_evidence:
        path = (
            _absolute(post_selection_root(paths, current_generation))
            / "runs"
            / item.run_identity
            / "checkpoints"
            / item.checkpoint_relative_path
        )
        artifact_id = f"p5:member_checkpoint:{item.run_identity}:{item.checkpoint_relative_path}"
        member_ids.append(artifact_id)
        views.append(
            OwnerArtifactView(
                owner=OWNER_P5,
                artifact_id=artifact_id,
                path=path,
                artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                detail=(
                    "frozen representative checkpoint of a published production member; "
                    "the current P7 publication re-authenticates these exact bytes at "
                    "this canonical hot path"
                ),
                generation=current_generation,
                current=True,
                restart_required=True,
                immutable=True,
                hot_path_required=True,
                requires=(f"p5:objects:g{current_generation}",),
            )
        )
    reported = {view.artifact_id for view in views}
    requires = [item for item in member_ids]
    for candidate in (
        f"p5:objects:g{current_generation}",
        f"p4:current_selected:g{current_generation}",
    ):
        if candidate in reported or candidate.startswith("p4:"):
            requires.append(candidate)
    views.append(
        OwnerArtifactView(
            owner=OWNER_P5,
            artifact_id=publication_id,
            path=_absolute(post_selection_root(paths, current_generation)),
            artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
            detail="current authenticated final-production publication",
            generation=current_generation,
            current=True,
            restart_required=True,
            immutable=True,
            hot_path_required=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
            # The publication's own identity: a same-generation republication
            # changes this even when every path and byte stays the same.
            state_identity="|".join(
                str(value)
                for value in (
                    decision.content_digest,
                    decision.member_digest,
                    decision.completion_digest,
                    decision.final_plan_digest,
                )
            ),
            requires=tuple(requires),
        )
    )
    return views, tuple(unresolved)


def selection_is_expected(store: Any) -> bool:
    """Whether the target-size owner says a current selected binding should exist.

    "No selection yet" and "the selection authority is broken" produce the same
    exception from the downstream resolver, but they are opposite facts for
    storage: the first is an ordinary campaign state, the second must retain
    every downstream artifact. The target-size owner's own lifecycle is what
    separates them.
    """

    from ..campaign_target_size_state import (
        TargetSizeLifecycle,
        load_target_size_campaign_revision,
    )

    try:
        revision = load_target_size_campaign_revision(store)
    except Exception:
        return False
    if revision is None:
        return False
    return revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED


def _run_infrastructure_members(run_root: Path) -> tuple[str, ...]:
    """P5's own certification record and locks inside one run root.

    These sit at known top-level names, so this is a handful of ``stat`` calls
    rather than a subtree walk: building an inventory must stay bounded
    independently of how much bulk a run holds.
    """

    from ..campaign_post_selection_runtime import (
        RUN_COMPLETION_INFRASTRUCTURE_NAMES,
    )

    names = sorted(RUN_COMPLETION_INFRASTRUCTURE_NAMES)
    return tuple(name for name in names if (run_root / name).is_file())


def _read_only_post_selection_context(
    cfg: Mapping[str, Any], paths: Any, store: Any
) -> Any | None:
    from ..campaign_post_selection_runtime import build_post_selection_context

    return build_post_selection_context(cfg, paths, store, trainer=_readonly_trainer())


# ---------------------------------------------------------------------------
# P7
# ---------------------------------------------------------------------------


def qualification_views(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    current_generation: int | None,
    publication_present: bool,
    certify: bool = True,
) -> tuple[list[OwnerArtifactView], tuple[tuple[str, str], ...], tuple[str, ...]]:
    """P7 durable evidence, attempt scratch, and the P5 dependency it carries.

    ``certify`` is off for reporting and on for planning, exactly as it is for
    P5: exact per-node certification of released scratch is what authorizes a
    mutation, and it is also what would make a report scale with attempt bulk.

    Returns the views, unresolved owners, and any attempt states that could not
    be authenticated. The last is not a warning: an active attempt's references
    can pin exact P5 checkpoints, so an unreadable state is an unknown
    cross-owner retention edge and a consequential-planning blocker.
    """

    from ..qualification.store import (
        LOCKED_REVEAL_DIRECTORY,
        QUALIFICATION_ROOT_NAME,
        observe_qualification_namespace,
        qualification_root,
    )

    internal = _absolute(paths.internal)
    family_root = internal / QUALIFICATION_ROOT_NAME
    views: list[OwnerArtifactView] = []
    unresolved: list[tuple[str, str]] = []

    reveal_root = family_root / LOCKED_REVEAL_DIRECTORY
    if reveal_root.is_dir():
        views.append(
            OwnerArtifactView(
                owner=OWNER_P7,
                artifact_id="p7:locked_reveal",
                path=reveal_root,
                artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                detail="locked-cohort reveal evidence; never reconstructible scratch",
                current=True,
                restart_required=True,
                immutable=True,
                hot_path_required=True,
                coverage=SubtreeCoverage.CONTAINER,
            )
        )

    active_reference_paths: set[str] = set()
    integrity_failures: list[str] = []
    # One strict authority for every storage-facing P7 decision below: the
    # census, the active-reference collection, and the per-attempt release
    # classification all read the same authenticated result, so the owner graph
    # and the local classifier can never disagree about whether an attempt is
    # released.
    # One descriptor-bound observation for every P7 decision below: generation
    # facts, attempt state, released-scratch topology, and exact certification
    # all come from the same authenticated descent. Re-listing the
    # generation/attempts/attempt hierarchy by pathname afterwards would be a
    # second namespace resolution, and it would happily enumerate whatever a
    # substituted ancestor points at now.
    try:
        snapshot = observe_qualification_namespace(paths, certify=certify)
        generations = snapshot.generations
        authorities = snapshot.authorities
    except Exception as exc:
        generations = ()
        authorities = (
            _UnresolvedAttemptAuthority(family_root, f"attempt census failed: {exc}"),
        )
    attempts_by_generation: dict[int, list[Any]] = {}
    for item in authorities:
        if item.generation is not None:
            attempts_by_generation.setdefault(int(item.generation), []).append(item)
    for item in authorities:
        if item.state is not None and item.state.is_active:
            active_reference_paths.update(item.state.referenced_paths)
    for state_path, reason in (
        (str(item.attempt_root), item.reason) for item in authorities if not item.resolved
    ):
        # Reported truthfully *and* propagated as an integrity failure: the
        # references this attempt would have protected are unknowable, and
        # guessing them is exactly what must not happen.
        unresolved.append((OWNER_P7, f"{state_path}: {reason}"))
        integrity_failures.append(
            f"qualification attempt state cannot be authenticated ({state_path}: "
            f"{reason}); its referenced artifacts are unknown, so consequential "
            "storage planning is unavailable until it is repaired"
        )
        active_reference_paths.add(str(family_root))

    for facts in generations:
        generation = facts.generation
        root = facts.root
        historical = generation != current_generation
        objects_id = f"p7:objects:g{generation}"
        if facts.has_objects:
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P7,
                    artifact_id=objects_id,
                    path=root / "objects",
                    artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                    detail=(
                        "immutable qualification/release evidence; durable by owner "
                        "declaration and never an orphan-collection target"
                    ),
                    generation=generation,
                    current=not historical,
                    restart_required=not historical,
                    immutable=True,
                    hot_path_required=not historical,
                    coverage=SubtreeCoverage.CONTAINER,
                )
            )
        for authority in sorted(
            attempts_by_generation.get(generation, ()),
            key=lambda item: item.attempt_root.name,
        ):
            attempt = authority.attempt_root
            released, why, state = _attempt_release_state(
                authority.state, attempt, active_reference_paths
            )
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P7,
                    artifact_id=f"p7:attempt:{generation}:{attempt.name}",
                    path=attempt,
                    artifact_class=ArtifactClass.TEMPORARY_SCRATCH
                    if released
                    else ArtifactClass.RESTART_STATE,
                    detail=why,
                    generation=generation,
                    current=True,
                    restart_required=True,
                    # The attempt record itself stays: its terminality is
                    # monotonic, and losing it would let a late retry reopen a
                    # completed attempt and reintroduce released references.
                    container_only=released,
                    requires=(objects_id,),
                )
            )
            if not released:
                continue
            if not certify:
                # Bounded reporting: say the attempt is released and that exact
                # reclaimability still has to be certified, without enumerating
                # children or parsing the O(node-count) proof. Released scratch
                # is reported as a retained container, so a report never scales
                # with attempt bulk and never implies that deletion authority
                # has already been established.
                views.append(
                    OwnerArtifactView(
                        owner=OWNER_P7,
                        artifact_id=f"p7:attempt_scratch:{generation}:{attempt.name}",
                        path=attempt,
                        artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                        detail=(
                            f"{why}; released attempt-local bulk is potentially "
                            "reclaimable and needs exact certification before any "
                            "mutation"
                            + (
                                ""
                                if authority.proof_present
                                else "; no released-attempt proof is present"
                            )
                        ),
                        generation=generation,
                        container_only=True,
                        coverage=SubtreeCoverage.CONTAINER,
                        requires=(objects_id,),
                    )
                )
                continue
            # Certified during the same authenticated descent, against the same
            # open attempt directory the state was read from.
            certified = authority.certified
            member_why = authority.certification_reason
            nodes = authority.certified_nodes
            recorded = {path: kind for path, kind in nodes}
            attempt_identity = authority.root_identity
            for member_name, kind in authority.top_level_nodes:
                member = attempt / member_name
                if not certified or recorded.get(member_name) != kind:
                    # Every top-level node has to be one the proof recorded, of
                    # the recorded kind, before it can be exposed as reclaimable
                    # at all. Otherwise it is reported and retained.
                    views.append(
                        OwnerArtifactView(
                            owner=OWNER_P7,
                            artifact_id=(
                                f"p7:attempt_scratch:{generation}:{attempt.name}:"
                                f"{member_name}"
                            ),
                            path=member,
                            artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                            detail=(
                                f"{why}; retained because the released-attempt proof "
                                f"does not certify this node: {member_why}"
                            ),
                            generation=generation,
                            container_only=kind == NODE_DIRECTORY,
                            coverage=(
                                SubtreeCoverage.CONTAINER
                                if kind == NODE_DIRECTORY
                                else SubtreeCoverage.NOT_APPLICABLE
                            ),
                            requires=(objects_id,),
                        )
                    )
                    continue
                prefix = f"{member_name}/"
                inside = tuple(
                    CertifiedNode(path=path[len(prefix) :], kind=node_kind)
                    for path, node_kind in nodes
                    if path.startswith(prefix)
                )
                views.append(
                    OwnerArtifactView(
                        owner=OWNER_P7,
                        artifact_id=(
                            f"p7:attempt_scratch:{generation}:{attempt.name}:{member_name}"
                        ),
                        path=member,
                        artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                        detail=(
                            f"{why}; attempt-local bulk of a released attempt is "
                            f"disposable while the attempt record itself is retained; "
                            f"{member_why}"
                        ),
                        generation=generation,
                        # Containment beneath a released attempt is not
                        # authorship: only what this owner recorded may be acted
                        # on, and an uncertified tree is reported and retained.
                        safe_reclaimable=True,
                        coverage=(
                            SubtreeCoverage.CLOSED
                            if kind == NODE_DIRECTORY
                            else SubtreeCoverage.NOT_APPLICABLE
                        ),
                        certified_nodes=inside,
                        # Typed names alone do not say which directory they were
                        # certified beneath, so this view carries the owner's own
                        # authorizer, the authority root the owner certified
                        # against, and this container's own identity.
                        exact_authorizer=P7_RELEASED_ATTEMPT_AUTHORIZER,
                        root_identity=attempt_identity,
                        path_identity=observed_node_identity(member),
                        # The exact released authority this action is planned
                        # against, carried by the ordinary owner-state binding.
                        # A state and proof resealed to a different but equally
                        # valid release would expose the same names and kinds;
                        # only this makes the old plan go stale.
                        state_identity=authority.release_authority,
                        requires=(objects_id,),
                    )
                )

    if current_generation is None:
        return views, tuple(unresolved), tuple(integrity_failures)

    # The current P7 record - including a truthful `waiting_for_reference` -
    # keeps the whole predecessor lineage pinned after its attempt reference
    # has been released.  This edge is exactly the post-terminal cross-owner
    # dependency that per-owner classification would lose.
    record_state = _current_qualification_state(cfg, paths, store)
    if record_state is None:
        return views, tuple(unresolved), tuple(integrity_failures)
    verdict, detail, record_identity = record_state
    reported = {view.artifact_id for view in views}
    requires = [
        item
        for item in (f"p7:objects:g{current_generation}",)
        if item in reported
    ]
    if publication_present:
        requires.append(f"p5:publication:g{current_generation}")
    views.append(
        OwnerArtifactView(
            owner=OWNER_P7,
            artifact_id=f"p7:current_record:g{current_generation}",
            path=_absolute(qualification_root(paths, current_generation)),
            artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
            detail=detail,
            generation=current_generation,
            current=True,
            restart_required=True,
            immutable=True,
            hot_path_required=True,
            # The generation root must survive, but attempt-local scratch inside
            # it is classified per attempt by the P7 owner itself.
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
            state_identity=record_identity,
            requires=tuple(requires),
        )
    )
    if verdict == "waiting_for_reference":
        views.append(
            OwnerArtifactView(
                owner=OWNER_P7,
                artifact_id=f"p7:waiting_for_reference:g{current_generation}",
                path=_absolute(qualification_root(paths, current_generation)),
                artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                detail=(
                    "qualification is truthfully waiting for independent external "
                    "reference evidence; the exact request/publication/binding lineage "
                    "required to resume it is product state, not scratch"
                ),
                generation=current_generation,
                current=True,
                restart_required=True,
                immutable=True,
                hot_path_required=True,
                container_only=True,
                coverage=SubtreeCoverage.CONTAINER,
                state_identity=record_identity,
                requires=tuple(requires),
            )
        )
        reference_root = _reference_request_root(cfg, paths)
        if reference_root is not None and reference_root.is_dir():
            views.append(
                OwnerArtifactView(
                    owner=OWNER_P7,
                    artifact_id=f"p7:reference_request:g{current_generation}",
                    path=reference_root,
                    artifact_class=ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
                    detail=(
                        "the exact frozen external-reference request a waiting "
                        "qualification must resume against; losing it would change "
                        "the frozen qualification lineage"
                    ),
                    generation=current_generation,
                    current=True,
                    restart_required=True,
                    immutable=True,
                    hot_path_required=True,
                    coverage=SubtreeCoverage.CONTAINER,
                )
            )
    return views, tuple(unresolved), tuple(integrity_failures)


def _reference_request_root(cfg: Mapping[str, Any], paths: Any) -> Path | None:
    """Where the P7 owner publishes its external-reference requests."""

    try:
        from ..qualification.runtime import _reference_root

        return _absolute(_reference_root(cfg, paths))
    except Exception:
        return None


@dataclass(frozen=True, slots=True)
class _UnresolvedAttemptAuthority:
    """A census failure that never carried an authenticated state."""

    attempt_root: Path
    reason: str
    state: Any = None
    root_identity: Any = None
    release_authority: str = ""

    @property
    def resolved(self) -> bool:
        return False


def _attempt_release_state(
    state: Any, attempt_root: Path, active_reference_paths: set[str]
) -> tuple[bool, str, Any]:
    """Whether this attempt's scratch is genuinely released.

    The state is supplied by the single strict authority rather than re-read
    here. Re-reading would be a second, independently fallible opinion about the
    same record, and a local classifier that disagreed with the owner graph is
    exactly how released authority could survive an unresolved census.
    """

    from ..qualification.store import ATTEMPT_ACTIVE

    if state is None:
        return False, (
            "attempt scratch without authenticated owner state is never proven "
            "disposable"
        ), None
    if state.state == ATTEMPT_ACTIVE:
        return False, (
            "an in-flight qualification attempt still references this scratch"
        ), state
    for value in active_reference_paths:
        referenced = Path(value)
        if referenced == attempt_root or _within(referenced, attempt_root) or _within(
            attempt_root, referenced
        ):
            return False, (
                "another active attempt still references this path"
            ), state
    return True, (
        f"attempt is {state.state}; the P7 owner released its retention references and "
        "no durable record requires this attempt-local scratch"
    ), state


def _current_qualification_state(
    cfg: Mapping[str, Any], paths: Any, store: Any
) -> tuple[str, str, str] | None:
    """Ask the P7 owner whether a current record exists, and what it says.

    Retention only needs to know that a P7 record is published for the current
    selected binding and whether it is truthfully waiting for external
    reference evidence.  Both facts come from the P7 owner's own pointer and
    object-store APIs, which authenticate the object's content digest.  A full
    session rebuild is deliberately not performed here: it would re-execute the
    exposure boundary for a read-only inventory, and a record that later proves
    historical would only ever *reduce* protection, so resolving conservatively
    is both cheaper and safer.
    """

    if not selection_is_expected(store):
        return None
    try:
        from ..campaign_post_selection import load_current_selected_training_context

        selected = load_current_selected_training_context(cfg, paths, store)
    except Exception:
        return (
            "unresolved",
            "the current selected authority could not be authenticated; the P7 "
            "predecessor lineage stays pinned until ownership is repaired",
            "unresolved",
        )
    try:
        from ..qualification.record import ProductionQualificationRecord
        from ..qualification.store import (
            POINTER_QUALIFICATION_RECORD,
            QualificationEvidenceStore,
            qualification_root,
            read_current_qualification_pointer,
        )

        pointer = read_current_qualification_pointer(
            store, binding=selected.binding, kind=POINTER_QUALIFICATION_RECORD
        )
        if pointer is None:
            return None
        # Constructed directly rather than through ``open_qualification_store``:
        # a read-only inventory must not create the owner's generation root.
        evidence = QualificationEvidenceStore(
            root=qualification_root(paths, selected.binding.campaign_generation)
        )
        record = evidence.get(pointer, ProductionQualificationRecord.from_dict)
    except Exception:
        return (
            "unresolved",
            "a current qualification pointer exists but its record could not be "
            "authenticated; the predecessor lineage stays pinned",
            "unresolved",
        )
    verdict = str(getattr(getattr(record, "verdict", None), "value", getattr(record, "verdict", "")))
    # The pointer digest is P7's own identity for what is current: republishing a
    # different record under the same binding changes it, which is exactly the
    # same-generation advancement a plan must notice.
    identity = "|".join((str(pointer), verdict))
    return verdict, f"current qualification record (verdict={verdict or 'unknown'})", identity


# ---------------------------------------------------------------------------
# Storage control plane
# ---------------------------------------------------------------------------


def control_plane_views(
    control_plane: StorageControlPlane, *, policy_journal_retention: int = 64
) -> list[OwnerArtifactView]:
    """Storage-native state, owned explicitly so it cannot reclaim itself.

    Three lifetimes live here and must not be confused. A *cataloged* archive is
    durable recovery authority for as long as it is retained. A *nonterminal*
    restore journal is recovery state. Everything else the subsystem writes -
    terminal journals, abandoned staging, uncataloged publication residue, the
    execution audit - is bounded operational evidence that must not grow without
    limit and must never become scientific authority.
    """

    views = [
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:catalog",
            path=control_plane.catalog_root,
            artifact_class=ArtifactClass.STORAGE_CONTROL_PLANE,
            detail=(
                "identity-keyed archive catalog: the durable authority that says which "
                "cold representations are retained"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:archives",
            path=control_plane.archive_root,
            artifact_class=ArtifactClass.ARCHIVE_REPRESENTATION,
            detail=(
                "archive blobs and manifests; a cataloged pair is durable authority "
                "while uncataloged residue is bounded storage-owned scratch"
            ),
            current=True,
            restart_required=True,
            hot_path_required=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:journal",
            path=control_plane.journal_root,
            artifact_class=ArtifactClass.STORAGE_CONTROL_PLANE,
            detail=(
                "restore journals; a nonterminal journal is recovery authority and a "
                "terminal one is bounded diagnostic evidence"
            ),
            current=True,
            restart_required=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:audit",
            path=control_plane.audit_root,
            artifact_class=ArtifactClass.DIAGNOSTIC_EVIDENCE,
            detail=(
                "bounded storage execution audit; losing an old record cannot "
                "invalidate scientific currentness"
            ),
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:locks",
            path=control_plane.lock_root,
            artifact_class=ArtifactClass.STORAGE_CONTROL_PLANE,
            detail="operational liveness only; never scientific currentness",
            current=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
        OwnerArtifactView(
            owner=OWNER_STORAGE,
            artifact_id="storage:staging",
            path=control_plane.staging_root,
            artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
            detail="restore staging container; each staging tree is judged individually",
            current=True,
            container_only=True,
            coverage=SubtreeCoverage.CONTAINER,
        ),
    ]

    # Restore staging with no journal is abandoned; with a journal it is either
    # live recovery state or, once terminal, bounded evidence.
    if control_plane.staging_root.is_dir():
        for stale in sorted(
            item for item in control_plane.staging_root.iterdir() if item.is_dir()
        ):
            journal = control_plane.journal_path_for_name(stale.name)
            open_journal = control_plane.journal_is_nonterminal(stale.name)
            views.append(
                OwnerArtifactView(
                    owner=OWNER_STORAGE,
                    artifact_id=f"storage:staging:{stale.name}",
                    path=stale,
                    artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                    detail=(
                        "restore staging for an open restore journal"
                        if open_journal
                        else "restore staging without an open journal is abandoned scratch"
                    ),
                    current=open_journal,
                    restart_required=open_journal,
                    safe_reclaimable=not open_journal,
                    coverage=SubtreeCoverage.CLOSED,
                    # `.mdstats/storage/staging` is this owner's own scratch
                    # area under the control-plane exclusive-writer contract:
                    # nothing else in the product writes there, so every
                    # descendant is storage's. Whether an entry is abandoned is
                    # decided by the storage-operation lease plus the journal
                    # above, never by a PID, an age, or a pathname.
                    owner_exclusive=True,
                )
            )
            del journal

    # Terminal restore journals beyond the retention bound are bounded evidence.
    for name, terminal in control_plane.journal_states():
        if not terminal:
            views.append(
                OwnerArtifactView(
                    owner=OWNER_STORAGE,
                    artifact_id=f"storage:journal:{name}",
                    path=control_plane.journal_path_for_name(name),
                    artifact_class=ArtifactClass.STORAGE_CONTROL_PLANE,
                    detail=(
                        "nonterminal restore journal: recovery authority until the "
                        "restore reaches a verified terminal result"
                    ),
                    current=True,
                    restart_required=True,
                    hot_path_required=True,
                )
            )
    retirable = control_plane.retirable_terminal_journals(
        keep=int(policy_journal_retention)
    )
    for name in retirable:
        views.append(
            OwnerArtifactView(
                owner=OWNER_STORAGE,
                artifact_id=f"storage:journal:{name}",
                path=control_plane.journal_path_for_name(name),
                artifact_class=ArtifactClass.DIAGNOSTIC_EVIDENCE,
                detail=(
                    "terminal restore journal beyond the retention bound; the archive "
                    "catalog, manifest, and blob it refers to are untouched"
                ),
                safe_reclaimable=True,
            )
        )

    # Archive blob/manifest pairs with no catalog entry are publication residue.
    for name in control_plane.uncataloged_archive_residue():
        views.append(
            OwnerArtifactView(
                owner=OWNER_STORAGE,
                artifact_id=f"storage:archive_residue:{name}",
                path=control_plane.archive_root / name,
                artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                detail=(
                    "archive publication residue with no catalog entry: it authorizes "
                    "nothing, and no live operation still references it"
                ),
                safe_reclaimable=True,
            )
        )
    return views


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def workspace_family_views(paths: Any, control_plane: StorageControlPlane) -> list[OwnerArtifactView]:
    """Every other known campaign family, plus whatever is unrecognized.

    A family that no owner adapter mentions is not thereby reclaimable; it is
    invisible, which is worse.  This closes the census: the known campaign roots
    are reported as their real owners' diagnostic or production evidence, and
    anything else in the workspace is reported as ambiguous and retained rather
    than quietly treated as campaign-owned scratch.
    """

    workspace = _absolute(paths.workspace)
    internal = _absolute(paths.internal)
    known: dict[Path, tuple[str, ArtifactClass, str]] = {
        _absolute(paths.results): (
            "campaign_store:results",
            ArtifactClass.DIAGNOSTIC_EVIDENCE,
            "operator-facing summaries and reports; restart/currentness neutral",
        ),
        _absolute(paths.models): (
            "campaign_store:models",
            ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
            "current production model evidence",
        ),
        _absolute(paths.runs): (
            "campaign_store:runs",
            ArtifactClass.DIAGNOSTIC_EVIDENCE,
            "historical training run tree retained by the campaign owner",
        ),
        _absolute(paths.data): (
            "campaign_store:data",
            ArtifactClass.REPRODUCIBILITY_BULK,
            "materialized training inputs",
        ),
        _absolute(paths.manifest): (
            "campaign_store:manifest",
            ArtifactClass.DURABLE_SCIENTIFIC_EVIDENCE,
            "approved campaign source manifest",
        ),
    }
    views: list[OwnerArtifactView] = []
    for path, (artifact_id, artifact_class, detail) in known.items():
        if not path.exists() and not path.is_symlink():
            continue
        views.append(
            OwnerArtifactView(
                owner=OWNER_CAMPAIGN_STORE,
                artifact_id=artifact_id,
                path=path,
                artifact_class=artifact_class,
                detail=detail,
                current=True,
                restart_required=True,
                container_only=True,
                coverage=SubtreeCoverage.CONTAINER,
            )
        )

    # Anything else directly under the workspace or `.mdstats` is unrecognized.
    accounted = set(known) | {internal, control_plane.root}
    for parent, prefix in ((workspace, "workspace"), (internal, "internal")):
        if not parent.is_dir():
            continue
        for child in sorted(parent.iterdir()):
            absolute = _absolute(child)
            if absolute in accounted or _is_recognized_internal(child, internal):
                continue
            views.append(
                OwnerArtifactView(
                    owner=OWNER_EXTERNAL,
                    artifact_id=f"unclassified:{prefix}:{child.name}",
                    path=absolute,
                    artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
                    detail=(
                        "no current owner claims this path; it is reported so it is "
                        "visible and retained so it is never a candidate"
                    ),
                    current=True,
                    restart_required=True,
                    coverage=SubtreeCoverage.CONTAINER,
                )
            )
    return views


#: Internal families a dedicated owner adapter already reports.
_RECOGNIZED_INTERNAL_NAMES = frozenset(
    {
        "campaign.sqlite3",
        "campaign.sqlite3-wal",
        "campaign.sqlite3-shm",
        "records",
        "hash-receipts.sqlite3",
        "frame-cache",
        "target-size",
        "post-selection",
        "qualification",
        "storage",
        "data7-cache",
        "data8-fixed-cache",
        "evaluation-graphs",
    }
)


def _is_recognized_internal(child: Path, internal: Path) -> bool:
    from .._campaign_cli_core import CAMPAIGN_WRITER_LOCK_SUFFIX

    try:
        relative = _absolute(child).relative_to(internal)
    except ValueError:
        return False
    if not relative.parts:
        return False
    head = relative.parts[0]
    # The campaign-state writer lock is this owner's coordination
    # infrastructure, not an unclassified stray internal file.
    if head.endswith(CAMPAIGN_WRITER_LOCK_SUFFIX):
        return True
    return head in _RECOGNIZED_INTERNAL_NAMES


def build_owner_views(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    control_plane: StorageControlPlane | None = None,
    journal_retention_records: int = 64,
    certify: bool = True,
) -> OwnerViewSet:
    """Interrogate every current owner and compose one owner view set.

    This is read-only with respect to managed campaign state: it opens the
    control plane without creating it, resolves owner state through
    non-creating readers, and never materializes a generation root, cache, or
    receipt merely to describe what exists.
    """

    plane = control_plane or open_storage_control_plane_readonly(paths)
    views: list[OwnerArtifactView] = []
    unresolved: list[tuple[str, str]] = []

    views.extend(campaign_store_views(cfg, paths, store))
    frame_cache = frame_cache_view(paths, store)
    if frame_cache is not None:
        views.append(frame_cache)

    try:
        target_views, current_generation, target_unresolved = target_size_views(paths, store)
        views.extend(target_views)
        unresolved.extend(target_unresolved)
    except Exception as exc:
        unresolved.append((OWNER_P3, f"target-size owner state unreadable: {exc}"))
        unresolved.append(
            (
                OWNER_P5,
                "downstream post-selection classification is unresolved because its "
                "upstream selected authority is unreadable",
            )
        )
        unresolved.append(
            (
                OWNER_P7,
                "downstream qualification classification is unresolved because its "
                "upstream selected authority is unreadable",
            )
        )
        current_generation = None

    publication_present = False
    try:
        p5_views, p5_unresolved = post_selection_views(
            cfg,
            paths,
            store,
            current_generation=current_generation,
            certify=certify,
        )
        views.extend(p5_views)
        unresolved.extend(p5_unresolved)
        publication_present = any(
            view.artifact_id == f"p5:publication:g{current_generation}" for view in p5_views
        )
    except Exception as exc:
        unresolved.append((OWNER_P5, f"post-selection owner state unreadable: {exc}"))

    owner_integrity: list[str] = []
    try:
        p7_views, p7_unresolved, p7_integrity = qualification_views(
            cfg,
            paths,
            store,
            current_generation=current_generation,
            publication_present=publication_present,
            certify=certify,
        )
        views.extend(p7_views)
        unresolved.extend(p7_unresolved)
        owner_integrity.extend(p7_integrity)
    except Exception as exc:
        unresolved.append((OWNER_P7, f"qualification owner state unreadable: {exc}"))
        owner_integrity.append(
            f"qualification owner state could not be censused ({exc}); the artifacts "
            "an active attempt references are unknown, so consequential storage "
            "planning is unavailable"
        )

    views.extend(
        control_plane_views(plane, policy_journal_retention=journal_retention_records)
    )
    views.extend(workspace_family_views(paths, plane))
    return OwnerViewSet(
        views=tuple(views),
        unresolved=tuple(unresolved),
        current_generation=current_generation,
        integrity_failures=(*validate_owner_graph(views), *owner_integrity),
    )


def _generation_roots(family_root: Path) -> list[Path]:
    """Generation roots that actually hold owner evidence.

    Several accepted owner APIs create their generation root as a side effect
    of being asked a question.  An empty root is not evidence, and treating one
    as an artifact would make a read-only inventory change the very owner state
    the next inventory observes - which would then refuse every plan as
    "owner advanced".  Empty roots are therefore ignored.
    """

    if not family_root.is_dir():
        return []
    roots: list[Path] = []
    for path in sorted(family_root.glob("g*")):
        if not path.is_dir():
            continue
        try:
            if next(path.iterdir(), None) is None:
                continue
        except OSError:
            continue
        roots.append(path)
    return roots


def _generation_of(root: Path) -> int | None:
    name = root.name
    if not name.startswith("g"):
        return None
    try:
        return int(name[1:])
    except ValueError:
        return None


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = [
    "ArtifactClass",
    "OwnerGraphError",
    "SubtreeCoverage",
    "OWNER_CAMPAIGN_STORE",
    "OWNER_EXTERNAL",
    "OWNER_P1",
    "OWNER_P2",
    "OWNER_P3",
    "OWNER_P4",
    "OWNER_P5",
    "OWNER_P7",
    "OWNER_STORAGE",
    "OwnerArtifactView",
    "OwnerViewError",
    "CertifiedNode",
    "P7_RELEASED_ATTEMPT_AUTHORIZER",
    "crosses_mount_boundary_at",
    "observed_node_identity",
    "NODE_ABSENT",
    "NODE_DIRECTORY",
    "NODE_FILE",
    "NODE_OTHER",
    "NODE_SYMLINK",
    "OwnerViewSet",
    "build_owner_views",
    "observed_node_kind",
    "read_owner_record_bytes",
    "campaign_store_views",
    "control_plane_views",
    "frame_cache_view",
    "post_selection_views",
    "selection_is_expected",
    "qualification_views",
    "target_size_views",
    "validate_owner_graph",
    "workspace_family_views",
]
