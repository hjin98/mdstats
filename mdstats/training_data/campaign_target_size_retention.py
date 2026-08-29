"""Storage retention fence protecting active and reconcilable P3 evidence.

Once P3 execution evidence becomes production campaign state, storage
reclamation can encounter it in a window where the campaign database does not
yet reference it: P3 publishes immutable evidence and commits its head before
the campaign store adopts that head, and those are deliberately separate
transactions.  Deleting a valid head, batch, or its required ancestry inside
that window would destroy work the current generation can still legitimately
adopt, so the absence of a SQLite reference is never treated as proof that a
current-generation artifact is orphaned.

This module therefore derives protection from the **filesystem evidence graph
itself**, not from what the campaign database happens to have adopted.  Every
head, batch, cell completion, and progress record present in the campaign-owned
execution root seeds a reachability closure; anything that closure can reach
stays protected.  Only an artifact in a known content-addressed subdirectory
whose digest no reachable record mentions is released as provably unreachable
campaign-owned residue, which keeps the fence from permanently pinning proven
garbage.

The closure is deliberately an over-approximation: it follows every
content-digest token appearing in a reachable record rather than a fixed field
list.  A safety fence should fail toward retention, and this also keeps the
fence correct if the P3 evidence schemas gain fields.

The fence only ever **reduces** deletion authority.  It never grants it, so
external paths, symlink escapes, ambiguous ownership, and configured user
inputs remain denied by the existing ownership boundary regardless of what the
closure contains.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os
import re
import time

from .campaign_target_size_state import (
    TargetSizeCampaignRevision,
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_revision,
)

#: P3 content-addressed subdirectories whose members are named by digest.  An
#: artifact here can be proven unreachable by digest; anything else under the
#: execution root is retained because its reachability is not decidable this way.
CONTENT_ADDRESSED_SUBDIRECTORIES: frozenset[str] = frozenset(
    {
        "trajectories",
        "materializations",
        "evaluation_artifacts",
        "roles",
        "predictions",
        "metrics",
        "snapshots",
        "continuations",
        "planned_rungs",
        "failures",
        "batches",
        "heads",
    }
)

#: Subdirectories holding logically-addressed evidence.  These always seed the
#: closure and are never released by the fence.
SEED_SUBDIRECTORIES: tuple[str, ...] = (
    "heads",
    "batches",
    "completions",
    "progress",
)

_DIGEST_TOKEN = re.compile(r"\b[0-9a-f]{64}\b")

#: Shortest identity prefix a bulk directory name may use before the fence
#: stops trying to prove it unreachable.
_MINIMUM_IDENTITY_PREFIX = 12

_REACHABLE_REASON = (
    "target-size evidence is reachable from a published head, batch, completion, "
    "or progress record and may still be adopted"
)

_PROTECTED_ACTIVE_LIFECYCLES = frozenset(
    {
        TargetSizeLifecycle.AWAITING_AUTHORITIES,
        TargetSizeLifecycle.AUTHORITIES_BOUND,
        TargetSizeLifecycle.SCREEN_ACTIVE,
        TargetSizeLifecycle.TERMINAL_SELECTED,
        TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
    }
)


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _absolute(path: str | os.PathLike[str]) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _digest_tokens(payload: Any) -> set[str]:
    """Every content-digest token appearing anywhere in one record."""

    return set(_DIGEST_TOKEN.findall(json.dumps(payload, sort_keys=True, default=str)))


@dataclass
class TargetSizeRetentionFence:
    """Deletion-authority reduction for campaign-owned P3 execution evidence.

    ``execution_root`` is the campaign-owned durable root for the current
    canonical generation.  ``protect_everything`` means the reconciliation
    frontier is unresolved and no artifact under the root may be reclaimed.
    Otherwise the fence releases only content-addressed artifacts proven
    unreachable from every head, batch, completion, and progress record present
    in the root.
    """

    execution_root: Path | None
    generation: int | None
    reason: str
    protect_everything: bool = True
    #: Publication of an artifact and the record that references it are
    #: separate filesystem operations, so an artifact younger than this window
    #: may be a reference that has not landed yet.  Releasing it would let
    #: cleanup race publication, so recent evidence is always retained.
    publication_window_seconds: float = 6.0 * 3600.0
    _reachable: frozenset[str] | None = field(default=None, repr=False)

    @property
    def is_active(self) -> bool:
        return self.execution_root is not None

    def _reachable_digests(self) -> frozenset[str]:
        if self._reachable is not None:
            return self._reachable
        root = self.execution_root
        if root is None:
            self._reachable = frozenset()
            return self._reachable

        by_digest: dict[str, Path] = {}
        for subdirectory in CONTENT_ADDRESSED_SUBDIRECTORIES:
            directory = root / subdirectory
            if not directory.is_dir():
                continue
            for entry in directory.rglob("*.json"):
                by_digest.setdefault(entry.stem, entry)

        pending: list[Path] = []
        for subdirectory in SEED_SUBDIRECTORIES:
            directory = root / subdirectory
            if directory.is_dir():
                pending.extend(sorted(directory.rglob("*.json")))

        reachable: set[str] = set()
        visited: set[Path] = set()
        while pending:
            path = pending.pop()
            if path in visited:
                continue
            visited.add(path)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # An unreadable record is exactly the case where guessing is
                # unsafe: keep its own digest reachable so it is retained for
                # the reconciler to classify.
                reachable.add(path.stem)
                continue
            reachable.add(path.stem)
            for token in _digest_tokens(payload):
                if token in reachable:
                    continue
                reachable.add(token)
                successor = by_digest.get(token)
                if successor is not None:
                    pending.append(successor)
        self._reachable = frozenset(reachable)
        return self._reachable

    def protects(self, path: str | os.PathLike[str]) -> tuple[bool, str]:
        """Return ``(protected, reason)`` for one destructive candidate."""

        root = self.execution_root
        if root is None:
            return False, ""
        candidate = _absolute(path)
        if not (_is_within(candidate, root) or _is_within(root, candidate)):
            return False, ""
        if _is_within(root, candidate) and candidate != root:
            # Deleting an ancestor of the execution root would remove it.
            return True, (
                "path contains the campaign-owned target-size execution root for "
                f"canonical generation {self.generation}: {self.reason}"
            )
        if self.protect_everything:
            return True, (
                "campaign-owned target-size execution root is protected for "
                f"canonical generation {self.generation}: {self.reason}"
            )
        relative = candidate.relative_to(root)
        parts = relative.parts
        if not parts:
            return True, (
                "campaign-owned target-size execution root itself is never reclaimable "
                f"while canonical generation {self.generation} is current"
            )
        if parts[0] not in CONTENT_ADDRESSED_SUBDIRECTORIES:
            return True, (
                "target-size evidence outside the content-addressed subdirectories "
                "cannot be proven unreachable; it is retained for reconciliation"
            )
        if len(parts) == 1:
            return True, (
                "a whole target-size content-addressed subdirectory is never a "
                "reclamation unit"
            )
        try:
            age = time.time() - candidate.stat().st_mtime
        except OSError:
            age = None
        if age is not None and age < self.publication_window_seconds:
            return True, (
                "target-size evidence was published too recently to be proven "
                "unreachable; releasing it would race publication and adoption"
            )
        # Some families are a single ``<digest>.json`` file and others are a
        # ``<digest>/`` directory holding bulk evidence, so reachability is
        # always decided by the identity component directly under the family
        # directory, never by a leaf filename.  Bulk directories may be named by
        # a shortened identity, so a short component is matched as a prefix and
        # an ambiguously short one is simply retained.
        stem = parts[1].split(".")[0]
        reachable = self._reachable_digests()
        if len(stem) == 64:
            if stem in reachable:
                return True, _REACHABLE_REASON
        elif len(stem) < _MINIMUM_IDENTITY_PREFIX:
            return True, (
                "target-size evidence is not named by a resolvable content identity, "
                "so it cannot be proven unreachable"
            )
        elif any(known.startswith(stem) for known in reachable):
            return True, _REACHABLE_REASON
        return False, ""


def _no_fence(reason: str) -> TargetSizeRetentionFence:
    return TargetSizeRetentionFence(
        execution_root=None, generation=None, reason=reason, protect_everything=False
    )


def build_target_size_retention_fence(
    store: Any,
    workspace: str | os.PathLike[str],
    *,
    publication_window_seconds: float | None = None,
) -> TargetSizeRetentionFence:
    """Derive the retention fence from durable campaign state.

    Protection is tied to the current/restartable generation, never to whether
    SQLite already adopted a head.  A campaign with no current target-size
    generation produces an inert fence, so nothing is pinned once the
    generation is gone.
    """

    try:
        revision = load_target_size_campaign_revision(store)
    except Exception:
        # An unreadable campaign state is the least safe moment to authorize
        # destruction of execution evidence.
        return TargetSizeRetentionFence(
            execution_root=_absolute(workspace),
            generation=None,
            reason="campaign target-size state could not be authenticated",
            protect_everything=True,
        )
    return retention_fence_for_revision(
        revision, workspace, publication_window_seconds=publication_window_seconds
    )


from .campaign_target_size_paths import target_size_execution_root


def retention_fence_for_revision(
    revision: TargetSizeCampaignRevision | None,
    workspace: str | os.PathLike[str],
    *,
    publication_window_seconds: float | None = None,
) -> TargetSizeRetentionFence:
    if revision is None or revision.state.regime is TargetSizeRegime.LEGACY:
        return _no_fence("campaign has no current target-size generation")
    state = revision.state
    if state.execution_root is not None:
        root = _absolute(Path(workspace) / state.execution_root)
    elif state.generation is not None and state.lifecycle in _PROTECTED_ACTIVE_LIFECYCLES:
        root = _absolute(target_size_execution_root(workspace, state.generation))
    else:
        return _no_fence(
            "current target-size generation owns no durable execution root yet"
        )
    if state.regime is TargetSizeRegime.TRANSITIONING:
        return TargetSizeRetentionFence(
            execution_root=root,
            generation=state.generation,
            reason="a destructive target-size cutover owns this campaign",
            protect_everything=True,
        )
    if state.lifecycle not in _PROTECTED_ACTIVE_LIFECYCLES:
        return _no_fence(
            "current target-size generation has no active or restartable execution root"
        )
    fence = TargetSizeRetentionFence(
        execution_root=root,
        generation=state.generation,
        reason=(
            "the current target-size generation is active, restartable, or awaiting "
            "authenticated adoption of published P3 evidence"
        ),
        protect_everything=False,
    )
    if publication_window_seconds is not None:
        fence.publication_window_seconds = float(publication_window_seconds)
    return fence


__all__ = [
    "CONTENT_ADDRESSED_SUBDIRECTORIES",
    "SEED_SUBDIRECTORIES",
    "TargetSizeRetentionFence",
    "build_target_size_retention_fence",
    "retention_fence_for_revision",
]
