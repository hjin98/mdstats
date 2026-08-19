"""Authenticated compact checkpoint persistence for MVSTATE2.

MVSTATE2 stores only exact continuation state.  Candidate marginal arrays and
the reconstructible lazy heap are intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import numpy as np

from ._common import canonical_json, digest, sha256_file_cached
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .target_multi_view_selector_v2 import (
    TARGET_MULTI_VIEW_SELECTOR_V2_VERSION,
    TargetMultiViewForwardFamilyStateV2,
    TargetMultiViewForwardStateV2,
)


MVSTATE2_SCHEMA = "mdstats.target-data2c-mvstate2.checkpoint.v1"
MVSTATE2_POINTER_SCHEMA = "mdstats.target-data2c-mvstate2.pointer.v1"
MVSTATE2_PERSISTENCE_VERSION = "mdstats.target-data2c-mvstate2.native-arrays.2026-08.v1"


class TargetMultiViewSelectionStateV2StoreError(RuntimeError):
    """MVSTATE2 is incomplete, modified, stale, or unsupported."""


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionIdentityV2:
    dataset_id: str
    label_domain_id: str
    reference_domain_digest: str
    mvidx1_content_digest: str
    candidate_uid_order_digest: str
    family_order_digest: str
    witness_weight_digest: str
    obligation_digest: str
    correlation_unit_digest: str
    selector_policy_digest: str
    selector_version: str = TARGET_MULTI_VIEW_SELECTOR_V2_VERSION

    def metadata_dict(self) -> dict[str, str]:
        return {name: str(getattr(self, name)) for name in self.__dataclass_fields__}

    @property
    def content_digest(self) -> str:
        return digest(self.metadata_dict())


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionCheckpointV2:
    identity: TargetMultiViewSelectionIdentityV2
    selected_order: np.ndarray
    family_multiplicity: tuple[np.ndarray, ...]
    family_coverage_mass: tuple[float, ...]
    obligation_counts: np.ndarray
    unsatisfied_required_obligation_count: int
    correlation_unit_counts: np.ndarray
    representative_utility: float

    @property
    def selected_count(self) -> int:
        return int(self.selected_order.size)


def build_target_multi_view_selection_identity_v2(
    reference_domain: Any,
    forward_domain: Any,
    *,
    dataset_id: str,
    selector_policy: Mapping[str, Any],
) -> TargetMultiViewSelectionIdentityV2:
    """Bind all scientific authorities while excluding execution settings."""

    family_ids = tuple(family.family_id for family in forward_domain.families)
    return TargetMultiViewSelectionIdentityV2(
        dataset_id=str(dataset_id),
        label_domain_id=str(forward_domain.label_domain_id),
        reference_domain_digest=str(reference_domain.content_digest),
        mvidx1_content_digest=str(forward_domain.mvidx1_domain_digest),
        candidate_uid_order_digest=digest(tuple(reference_domain.frame_uids)),
        family_order_digest=digest(family_ids),
        witness_weight_digest=digest(tuple(
            (family_id, _coverage_array_reference(np.asarray(reference_domain.family(family_id).weights, dtype=np.float64)))
            for family_id in family_ids
        )),
        obligation_digest=digest(tuple(
            (item.obligation_id, int(item.minimum_selected_frames), bool(item.required))
            for item in forward_domain.obligations
        )),
        correlation_unit_digest=digest({
            "ids": tuple(forward_domain.correlation_unit_ids),
            "codes": _coverage_array_reference(np.asarray(forward_domain.candidate_correlation_unit_codes)),
        }),
        selector_policy_digest=digest(selector_policy),
    )


def checkpoint_target_multi_view_forward_state_v2(
    state: TargetMultiViewForwardStateV2,
    identity: TargetMultiViewSelectionIdentityV2,
) -> TargetMultiViewSelectionCheckpointV2:
    return TargetMultiViewSelectionCheckpointV2(
        identity=identity,
        selected_order=np.ascontiguousarray(state.selected_order, dtype=np.int64),
        family_multiplicity=tuple(
            np.ascontiguousarray(item.multiplicity, dtype=np.int32)
            for item in state.family_states
        ),
        family_coverage_mass=tuple(float(item.coverage_mass) for item in state.family_states),
        obligation_counts=np.ascontiguousarray(state.obligation_counts, dtype=np.int32),
        unsatisfied_required_obligation_count=int(state.unsatisfied_required_obligation_count),
        correlation_unit_counts=np.ascontiguousarray(state.correlation_unit_counts, dtype=np.int32),
        representative_utility=float(state.representative_utility),
    )


def restore_target_multi_view_forward_state_v2(
    checkpoint: TargetMultiViewSelectionCheckpointV2,
    reference_domain: Any,
    forward_domain: Any,
    *,
    expected_identity: TargetMultiViewSelectionIdentityV2,
) -> TargetMultiViewForwardStateV2:
    """Validate continuation state against its authorities and restore it."""

    if checkpoint.identity != expected_identity:
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 scientific identity mismatch; rebuild required.")
    candidate_count = int(forward_domain.candidate_count)
    selected = np.asarray(checkpoint.selected_order, dtype=np.int64)
    if selected.ndim != 1 or np.any(selected < 0) or np.any(selected >= candidate_count) or np.unique(selected).size != selected.size:
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 selected prefix is invalid.")
    if len(checkpoint.family_multiplicity) != len(forward_domain.families):
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 family cardinality mismatch.")
    available = np.ones(candidate_count, dtype=np.bool_)
    available[selected] = False
    family_states: list[TargetMultiViewForwardFamilyStateV2] = []
    expected_representative_utility = 0.0
    for family_index, (family, stored, stored_mass) in enumerate(zip(
        forward_domain.families,
        checkpoint.family_multiplicity,
        checkpoint.family_coverage_mass,
        strict=True,
    )):
        multiplicity = np.asarray(stored, dtype=np.int32)
        if multiplicity.shape != (int(family.witness_count),) or np.any(multiplicity < 0):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 witness multiplicity is invalid.")
        expected = np.zeros_like(multiplicity)
        for candidate in selected:
            expected[np.asarray(family.candidate_witness_indices(int(candidate)), dtype=np.int64)] += 1
        if not np.array_equal(multiplicity, expected):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 witness multiplicity disagrees with selected prefix.")
        weights = np.asarray(reference_domain.family(family.family_id).weights, dtype=np.float64)
        expected_mass = float(np.sum(weights[multiplicity > 0], dtype=np.float64))
        if not np.isclose(float(stored_mass), expected_mass, rtol=0.0, atol=5.0e-13):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 family coverage mass is invalid.")
        family_states.append(TargetMultiViewForwardFamilyStateV2(
            family_id=family.family_id,
            weights=weights,
            multiplicity=np.array(multiplicity, copy=True),
            coverage_mass=expected_mass,
        ))
        maximum = int(np.max(multiplicity)) if multiplicity.size else 0
        harmonic = np.zeros(maximum + 1, dtype=np.float64)
        if maximum:
            harmonic[1:] = np.cumsum(1.0 / np.arange(1, maximum + 1, dtype=np.float64), dtype=np.float64)
        expected_representative_utility += float(np.sum(weights * harmonic[multiplicity], dtype=np.float64))
    obligation_counts = np.zeros(len(forward_domain.obligations), dtype=np.int32)
    unit_counts = np.zeros(len(forward_domain.correlation_unit_ids), dtype=np.int32)
    for candidate in selected:
        obligation_counts[np.asarray(forward_domain.candidate_obligation_indices(int(candidate)), dtype=np.int64)] += 1
        unit_counts[int(forward_domain.candidate_correlation_unit_codes[int(candidate)])] += 1
    if not np.array_equal(obligation_counts, checkpoint.obligation_counts):
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 obligation counts are invalid.")
    if not np.array_equal(unit_counts, checkpoint.correlation_unit_counts):
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 correlation counts are invalid.")
    unsatisfied = sum(
        item.required and int(obligation_counts[index]) < int(item.minimum_selected_frames)
        for index, item in enumerate(forward_domain.obligations)
    )
    if int(checkpoint.unsatisfied_required_obligation_count) != int(unsatisfied):
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 required-obligation state is invalid.")
    if not np.isclose(float(checkpoint.representative_utility), expected_representative_utility, rtol=0.0, atol=5.0e-12):
        raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 representative utility is invalid.")
    return TargetMultiViewForwardStateV2(
        available=available,
        selected_order=[int(value) for value in selected],
        family_states=family_states,
        obligation_counts=obligation_counts,
        unsatisfied_required_obligation_count=int(unsatisfied),
        correlation_unit_counts=unit_counts,
        representative_utility=expected_representative_utility,
    )


def _array_descriptor(key: str, value: np.ndarray) -> dict[str, Any]:
    return {"bundle_key": key, "array_reference": _coverage_array_reference(np.ascontiguousarray(value))}


def write_target_multi_view_selection_checkpoint_v2(
    checkpoint: TargetMultiViewSelectionCheckpointV2,
    records_root: str | Path,
) -> dict[str, Any]:
    """Transactionally publish one immutable MVSTATE2 checkpoint."""

    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {
        "selected_order": checkpoint.selected_order,
        "obligation_counts": checkpoint.obligation_counts,
        "correlation_unit_counts": checkpoint.correlation_unit_counts,
    }
    arrays.update({f"family_{index:04d}_multiplicity": value for index, value in enumerate(checkpoint.family_multiplicity)})
    descriptors = {key: _array_descriptor(key, value) for key, value in arrays.items()}
    scientific = {
        "schema": MVSTATE2_SCHEMA,
        "persistence_version": MVSTATE2_PERSISTENCE_VERSION,
        "identity": checkpoint.identity.metadata_dict(),
        "identity_digest": checkpoint.identity.content_digest,
        "selected_count": checkpoint.selected_count,
        "family_coverage_mass": checkpoint.family_coverage_mass,
        "unsatisfied_required_obligation_count": checkpoint.unsatisfied_required_obligation_count,
        "representative_utility": checkpoint.representative_utility,
        "arrays": descriptors,
    }
    content_digest = digest(scientific)
    destination = root / f"target-multi-view-selection-state-v2-{content_digest}"
    temporary = Path(tempfile.mkdtemp(prefix="mvstate2-write-", dir=root))
    try:
        bundle = temporary / "arrays.npz"
        np.savez(bundle, **arrays)
        with bundle.open("rb") as handle:
            os.fsync(handle.fileno())
        manifest = {**scientific, "content_digest": content_digest,
                    "array_bundle": {"relative_path": bundle.name, "size_bytes": bundle.stat().st_size, "sha256": sha256_file_cached(bundle)}}
        manifest["manifest_digest"] = digest(manifest)
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
        with manifest_path.open("rb") as handle:
            os.fsync(handle.fileno())
        if destination.exists():
            existing_manifest = destination / "manifest.json"
            existing_pointer = {
                "schema": MVSTATE2_POINTER_SCHEMA,
                "persistence_version": MVSTATE2_PERSISTENCE_VERSION,
                "relative_path": str(existing_manifest.relative_to(root.parent)),
                "sha256": sha256_file_cached(existing_manifest) if existing_manifest.is_file() else "",
                "content_digest": content_digest,
            }
            existing_pointer["pointer_digest"] = digest(existing_pointer)
            try:
                existing = read_target_multi_view_selection_checkpoint_v2(existing_pointer, root.parent)
                if existing.identity != checkpoint.identity or existing.selected_count != checkpoint.selected_count:
                    raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 existing record identity mismatch.")
            except Exception:
                # This content-addressed reconstructible cache entry is corrupt
                # or interrupted; replace only that exact resolved destination.
                shutil.rmtree(destination)
                os.replace(temporary, destination)
            else:
                shutil.rmtree(temporary)
        else:
            os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        pointer = {
            "schema": MVSTATE2_POINTER_SCHEMA,
            "persistence_version": MVSTATE2_PERSISTENCE_VERSION,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": sha256_file_cached(manifest_path),
            "content_digest": content_digest,
        }
        return {**pointer, "pointer_digest": digest(pointer)}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def read_target_multi_view_selection_checkpoint_v2(
    pointer: Mapping[str, Any],
    campaign_root: str | Path,
) -> TargetMultiViewSelectionCheckpointV2:
    """Authenticate and read one MVSTATE2 checkpoint without pickle."""

    try:
        if pointer.get("schema") != MVSTATE2_POINTER_SCHEMA or pointer.get("persistence_version") != MVSTATE2_PERSISTENCE_VERSION:
            raise TargetMultiViewSelectionStateV2StoreError("Unsupported checkpoint schema (MVSTATE1 is not MVSTATE2).")
        if pointer.get("pointer_digest") != digest({key: value for key, value in pointer.items() if key != "pointer_digest"}):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 pointer digest mismatch.")
        root = Path(campaign_root).resolve()
        relative = Path(str(pointer.get("relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 pointer escapes campaign root.")
        manifest_path = (root / relative).resolve()
        if root not in manifest_path.parents or not manifest_path.is_file() or sha256_file_cached(manifest_path) != pointer.get("sha256"):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 manifest is missing or modified.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != MVSTATE2_SCHEMA or manifest.get("persistence_version") != MVSTATE2_PERSISTENCE_VERSION:
            raise TargetMultiViewSelectionStateV2StoreError("Unsupported MVSTATE2 manifest schema.")
        if manifest.get("manifest_digest") != digest({key: value for key, value in manifest.items() if key != "manifest_digest"}):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 manifest digest mismatch.")
        if manifest.get("content_digest") != pointer.get("content_digest"):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 content digest mismatch.")
        bundle_info = manifest["array_bundle"]
        bundle_path = (manifest_path.parent / str(bundle_info["relative_path"])).resolve()
        if manifest_path.parent != bundle_path.parent or not bundle_path.is_file() or bundle_path.stat().st_size != int(bundle_info["size_bytes"]) or sha256_file_cached(bundle_path) != bundle_info["sha256"]:
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 array bundle is missing, truncated, or modified.")
        identity = TargetMultiViewSelectionIdentityV2(**manifest["identity"])
        if identity.content_digest != manifest.get("identity_digest"):
            raise TargetMultiViewSelectionStateV2StoreError("MVSTATE2 identity digest mismatch.")
        with np.load(bundle_path, allow_pickle=False) as bundle:
            restored: dict[str, np.ndarray] = {}
            for key, descriptor in manifest["arrays"].items():
                bundle_key = str(descriptor["bundle_key"])
                if bundle_key not in bundle.files:
                    raise TargetMultiViewSelectionStateV2StoreError(f"Missing MVSTATE2 array {key}.")
                value = np.asarray(bundle[bundle_key])
                _validate_array_reference(descriptor["array_reference"], value, name=key)
                restored[key] = np.ascontiguousarray(value)
        family_values = tuple(restored[f"family_{index:04d}_multiplicity"] for index in range(len(manifest["family_coverage_mass"])))
        return TargetMultiViewSelectionCheckpointV2(
            identity=identity,
            selected_order=restored["selected_order"],
            family_multiplicity=family_values,
            family_coverage_mass=tuple(float(value) for value in manifest["family_coverage_mass"]),
            obligation_counts=restored["obligation_counts"],
            unsatisfied_required_obligation_count=int(manifest["unsatisfied_required_obligation_count"]),
            correlation_unit_counts=restored["correlation_unit_counts"],
            representative_utility=float(manifest["representative_utility"]),
        )
    except TargetMultiViewSelectionStateV2StoreError:
        raise
    except Exception as exc:
        raise TargetMultiViewSelectionStateV2StoreError("Cannot restore MVSTATE2 checkpoint.") from exc
