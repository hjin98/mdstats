"""MVSTATE2: authenticated compact continuation state for ``prepare``.

Restored from the MVSTATE2 checkpoint lineage (carrier ``3937881e``) as
subordinate prepare-owned reconstructible build state.  A checkpoint stores
only exact continuation quantities -- selected prefix, witness multiplicities,
family coverage masses, canonical obligation counts, correlation-unit counts
and representative utility -- plus, for the configured prefix, the already
authorized rank history so resume need not rescore the prefix.  Lazy heaps,
witness-term caches and native scratch are never persisted.

A checkpoint is admissible only under the exact prospective identity it was
written for: exact ``P_train``/reference, MVIDX (NEIGHBOR1 + canonical
obligations), MVSEL2 policy, configured ladder and -- for post-repair
continuation -- the repair plan that fixed the repaired prefix.  Restore
re-derives multiplicities, masses, counts and utility from the prefix and
fails closed on any disagreement; the authenticated stored FP history is then
retained so continuation is bit-identical to the uninterrupted run.  It never
becomes CampaignStore currentness or downstream evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, digest
from .artifact_store import (
    PublishedArtifact,
    TargetOrderArtifactStoreError,
    close_memmap,
    packed_slice,
    publish_artifact_directory,
    read_manifest,
    read_npy,
    read_packed,
    write_npy,
    write_packed,
)
from .selector import (
    TargetMultiViewForwardFamilyState,
    TargetMultiViewForwardState,
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionRung,
)

MVSTATE2_SCHEMA = "mdstats.target-order.mvstate2.checkpoint.v1"
MVSTATE2_IDENTITY_SCHEMA = "mdstats.target-order.mvstate2.identity.v1"


def selection_identity(
    *,
    reference_digest: str,
    mvidx_digest: str,
    selector_policy_digest: str,
    configured_sizes: Sequence[int],
    repair_plan_digest: str | None = None,
) -> str:
    """Deterministic prospective continuation identity (execution state excluded)."""

    return digest(
        {
            "schema": MVSTATE2_IDENTITY_SCHEMA,
            "target_coverage_reference_digest": reference_digest,
            "mvidx_content_digest": mvidx_digest,
            "selector_policy_digest": selector_policy_digest,
            "configured_sizes": [int(v) for v in configured_sizes],
            "repair_plan_digest": repair_plan_digest,
        }
    )


@dataclass(frozen=True, slots=True)
class SelectionCheckpoint:
    identity: str
    state: TargetMultiViewForwardState
    entries: tuple[TargetMultiViewSelectionEntry, ...]
    rungs: tuple[TargetMultiViewSelectionRung, ...]
    phase_a_completed_at: int | None


def _state_payload(state: TargetMultiViewForwardState) -> dict[str, Any]:
    return {
        "selected_count": state.selected_count,
        "family_coverage_mass": [float(item.coverage_mass) for item in state.family_states],
        "unsatisfied_required_obligation_count": int(state.unsatisfied_required_obligation_count),
        "representative_utility": float(state.representative_utility),
    }


def write_selection_checkpoint(
    directory: Path,
    *,
    identity: str,
    state: TargetMultiViewForwardState,
    entries: Sequence[TargetMultiViewSelectionEntry] = (),
    rungs: Sequence[TargetMultiViewSelectionRung] = (),
    phase_a_completed_at: int | None = None,
) -> PublishedArtifact:
    """Publish one immutable checkpoint at a crash-safe boundary."""

    selected = np.ascontiguousarray(state.selected_order, dtype="<i8")
    scientific = {
        "identity": identity,
        "selected_order_digest": digest(selected.tolist()),
        **_state_payload(state),
        "obligation_counts": np.asarray(state.obligation_counts, dtype=np.int64).tolist(),
        "correlation_unit_counts": np.asarray(state.correlation_unit_counts, dtype=np.int64).tolist(),
        "entries": [item.to_dict() for item in entries],
        "rungs": [item.to_dict() for item in rungs],
        "phase_a_completed_at": phase_a_completed_at,
    }
    content_digest = digest(scientific)
    destination = Path(directory) / f"state-{state.selected_count:09d}-{content_digest[:24]}"

    def write(target: Path) -> Mapping[str, Any]:
        packed, slices = write_packed(
            target, "multiplicity.npy", [np.asarray(item.multiplicity, dtype="<i4") for item in state.family_states], dtype="<i4"
        )
        return {
            "schema": MVSTATE2_SCHEMA,
            "content_digest": content_digest,
            **scientific,
            "arrays": {"selected_order": write_npy(target, "selected-order.npy", selected)},
            "packed_multiplicity": packed,
            "multiplicity_slices": slices,
        }

    return publish_artifact_directory(
        destination, schema=MVSTATE2_SCHEMA, write=write, verify_existing=lambda path, _m: None
    )


def restore_selection_checkpoint(
    directory: Path, reference: Any, forward: Any, *, expected_identity: str
) -> SelectionCheckpoint:
    """Authenticate one checkpoint against exact identity and primitive evidence."""

    manifest = read_manifest(Path(directory), schema=MVSTATE2_SCHEMA)
    if manifest.get("identity") != expected_identity:
        raise TargetOrderArtifactStoreError("MVSTATE2 scientific identity mismatch; the checkpoint is stale.")
    selected = np.asarray(read_npy(Path(directory), manifest["arrays"]["selected_order"], label="MVSTATE2 selected order"), dtype=np.int64)
    candidate_count = int(forward.candidate_count)
    if (
        selected.ndim != 1
        or selected.size != int(manifest["selected_count"])
        or (selected.size and (int(selected.min()) < 0 or int(selected.max()) >= candidate_count))
        or np.unique(selected).size != selected.size
        or digest(selected.tolist()) != manifest["selected_order_digest"]
    ):
        raise TargetOrderArtifactStoreError("MVSTATE2 selected prefix is invalid.")
    root = read_packed(Path(directory), manifest["packed_multiplicity"], label="MVSTATE2 multiplicity")
    try:
        cursor = 0
        stored: list[np.ndarray] = []
        for descriptor in manifest["multiplicity_slices"]:
            stored.append(np.array(packed_slice(root, descriptor, label="MVSTATE2 multiplicity", cursor=cursor), dtype=np.int32))
            cursor = int(descriptor["stop"])
    finally:
        close_memmap(root)
    if len(stored) != len(forward.families):
        raise TargetOrderArtifactStoreError("MVSTATE2 family cardinality mismatch.")
    family_states: list[TargetMultiViewForwardFamilyState] = []
    utility = 0.0
    for family, multiplicity, mass in zip(forward.families, stored, manifest["family_coverage_mass"], strict=True):
        expected = np.zeros(family.witness_count, dtype=np.int32)
        for candidate in selected:
            expected[np.asarray(family.candidate_witness_indices(int(candidate)), dtype=np.int64)] += 1
        if multiplicity.shape != expected.shape or not np.array_equal(multiplicity, expected):
            raise TargetOrderArtifactStoreError("MVSTATE2 witness multiplicity disagrees with the selected prefix.")
        weights = np.asarray(reference.family(family.family_id).weights, dtype=np.float64)
        derived_mass = float(np.sum(weights[multiplicity > 0], dtype=np.float64))
        if not np.isclose(float(mass), derived_mass, rtol=0.0, atol=5.0e-13):
            raise TargetOrderArtifactStoreError("MVSTATE2 family coverage mass is invalid.")
        maximum = int(np.max(multiplicity)) if multiplicity.size else 0
        harmonic = np.zeros(maximum + 1, dtype=np.float64)
        if maximum:
            harmonic[1:] = np.cumsum(1.0 / np.arange(1, maximum + 1, dtype=np.float64), dtype=np.float64)
        utility += float(np.sum(weights * harmonic[multiplicity], dtype=np.float64))
        # Structural validation passed; retain the authenticated stored FP64
        # history because recomputation can change last bits at a tie.
        family_states.append(TargetMultiViewForwardFamilyState(family.family_id, weights, multiplicity, float(mass)))
    obligation_counts = np.zeros(len(forward.obligations), dtype=np.int32)
    unit_counts = np.zeros(len(forward.correlation_unit_ids), dtype=np.int32)
    for candidate in selected:
        obligation_counts[np.asarray(forward.candidate_obligation_indices(int(candidate)), dtype=np.int64)] += 1
        unit_counts[int(forward.candidate_correlation_unit_codes[int(candidate)])] += 1
    if obligation_counts.tolist() != [int(v) for v in manifest["obligation_counts"]]:
        raise TargetOrderArtifactStoreError("MVSTATE2 obligation counts are invalid.")
    if unit_counts.tolist() != [int(v) for v in manifest["correlation_unit_counts"]]:
        raise TargetOrderArtifactStoreError("MVSTATE2 correlation counts are invalid.")
    unsatisfied = sum(
        int(obligation_counts[index]) < int(item.minimum_selected_frames) for index, item in enumerate(forward.obligations)
    )
    if unsatisfied != int(manifest["unsatisfied_required_obligation_count"]):
        raise TargetOrderArtifactStoreError("MVSTATE2 obligation state is invalid.")
    if not np.isclose(float(manifest["representative_utility"]), utility, rtol=0.0, atol=5.0e-12):
        raise TargetOrderArtifactStoreError("MVSTATE2 representative utility is invalid.")
    available = np.ones(candidate_count, dtype=np.bool_)
    available[selected] = False
    entries = tuple(TargetMultiViewSelectionEntry.from_dict(item) for item in manifest["entries"])
    if entries and tuple(entry.frame_uid for entry in entries) != tuple(reference.frame_uids[int(c)] for c in selected[: len(entries)]):
        raise TargetOrderArtifactStoreError("MVSTATE2 rank history disagrees with the selected prefix.")
    return SelectionCheckpoint(
        identity=expected_identity,
        state=TargetMultiViewForwardState(
            available=available,
            selected_order=[int(v) for v in selected],
            family_states=family_states,
            obligation_counts=obligation_counts,
            unsatisfied_required_obligation_count=int(unsatisfied),
            correlation_unit_counts=unit_counts,
            representative_utility=float(manifest["representative_utility"]),
        ),
        entries=entries,
        rungs=tuple(TargetMultiViewSelectionRung.from_dict(item) for item in manifest["rungs"]),
        phase_a_completed_at=None if manifest.get("phase_a_completed_at") is None else int(manifest["phase_a_completed_at"]),
    )


def list_checkpoints(directory: Path) -> tuple[tuple[int, Path], ...]:
    """Candidate checkpoint directories, highest selected count first."""

    root = Path(directory)
    if not root.is_dir():
        return ()
    rows: list[tuple[int, Path]] = []
    for child in root.iterdir():
        if not child.is_dir() or not child.name.startswith("state-"):
            continue
        try:
            rows.append((int(child.name.split("-")[1]), child))
        except (IndexError, ValueError):
            continue
    return tuple(sorted(rows, key=lambda item: (-item[0], item[1].name)))


def restore_latest_checkpoint(
    directory: Path, reference: Any, forward: Any, *, expected_identity: str, maximum_selected: int | None = None
) -> SelectionCheckpoint | None:
    """Highest valid checkpoint; stale/corrupt ones are discarded as reconstructible."""

    for count, path in list_checkpoints(directory):
        if maximum_selected is not None and count > int(maximum_selected):
            continue
        try:
            return restore_selection_checkpoint(path, reference, forward, expected_identity=expected_identity)
        except (TargetOrderArtifactStoreError, TrainingDataInputError, KeyError, ValueError, OSError):
            shutil.rmtree(path, ignore_errors=True)
    return None


def prune_checkpoints(directory: Path, *, keep: Path) -> None:
    """Retain only the newest checkpoint of one build identity (bounded journal)."""

    for _count, path in list_checkpoints(directory):
        if path.resolve() != Path(keep).resolve():
            shutil.rmtree(path, ignore_errors=True)


__all__ = [
    "SelectionCheckpoint",
    "list_checkpoints",
    "prune_checkpoints",
    "restore_latest_checkpoint",
    "restore_selection_checkpoint",
    "selection_identity",
    "write_selection_checkpoint",
]
