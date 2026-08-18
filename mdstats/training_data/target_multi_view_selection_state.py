"""Authenticated reconstructible MVSEL sparse execution state for MVSTATE-REUSE1.

The objects in this module are execution caches, not scientific authority.  They
bind exact MVSEL/MVIDX identities and preserve the mutable sparse arrays needed
by REPAIR1 so a pure selector rung can be restored without replaying every
selection update from rank zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .target_coverage import _coverage_array_reference, _validate_array_reference

TARGET_MULTI_VIEW_SELECTION_STATE_FAMILY_SCHEMA = "mdstats.target-multi-view-selection-state-family.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_CHECKPOINT_SCHEMA = "mdstats.target-multi-view-selection-state-checkpoint.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_DOMAIN_SCHEMA = "mdstats.target-multi-view-selection-state-domain.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_SCHEMA = "mdstats.target-multi-view-selection-state-cache.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_VERSION = "mdstats.target-data2c-mvstate-reuse1.selector-state-cache.2026-08.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION = "mdstats.target-data2c-mvstate-reuse1.native-arrays.2026-08.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_KERNEL_SCHEMA = "mdstats.target-data2c-mvstate-reuse1.sparse-kernel.v1"


def _ro(array: np.ndarray, *, dtype: Any | None = None) -> np.ndarray:
    value = np.ascontiguousarray(array if dtype is None else np.asarray(array, dtype=dtype))
    value.setflags(write=False)
    return value


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionFamilyStateCheckpoint:
    family_id: str
    coverage_mass: float
    covered: np.ndarray
    multiplicity: np.ndarray
    coverage_gain: np.ndarray
    representative_gain: np.ndarray
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.family_id:
            raise TrainingDataInputError("MVSTATE-REUSE1 family_id cannot be empty.")
        covered = _ro(self.covered, dtype=np.bool_)
        multiplicity = _ro(self.multiplicity, dtype=np.int32)
        coverage_gain = _ro(self.coverage_gain, dtype=np.float64)
        representative_gain = _ro(self.representative_gain, dtype=np.float64)
        if covered.ndim != 1 or multiplicity.shape != covered.shape:
            raise TrainingDataInputError("MVSTATE-REUSE1 family witness arrays disagree.")
        if coverage_gain.ndim != 1 or representative_gain.shape != coverage_gain.shape:
            raise TrainingDataInputError("MVSTATE-REUSE1 family candidate gain arrays disagree.")
        object.__setattr__(self, "covered", covered)
        object.__setattr__(self, "multiplicity", multiplicity)
        object.__setattr__(self, "coverage_gain", coverage_gain)
        object.__setattr__(self, "representative_gain", representative_gain)
        object.__setattr__(self, "coverage_mass", float(self.coverage_mass))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_STATE_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "coverage_mass": self.coverage_mass,
            "covered": _coverage_array_reference(self.covered),
            "multiplicity": _coverage_array_reference(self.multiplicity),
            "coverage_gain": _coverage_array_reference(self.coverage_gain),
            "representative_gain": _coverage_array_reference(self.representative_gain),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def metadata_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "content_digest": self.content_digest}


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionStateCheckpoint:
    target_size: int
    selected_prefix_digest: str
    representative_utility: float
    available: np.ndarray
    families: tuple[TargetMultiViewSelectionFamilyStateCheckpoint, ...]
    total_coverage_gain: np.ndarray
    total_representative_gain: np.ndarray
    hard_gain: np.ndarray
    obligation_counts: np.ndarray
    required_obligation_mask: np.ndarray
    unsatisfied_required_obligation_count: int
    unit_counts: np.ndarray
    _family_by_id: Mapping[str, TargetMultiViewSelectionFamilyStateCheckpoint] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if int(self.target_size) < 1:
            raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint target_size must be positive.")
        object.__setattr__(self, "target_size", int(self.target_size))
        object.__setattr__(self, "selected_prefix_digest", validate_digest(self.selected_prefix_digest, name="selected_prefix_digest"))
        object.__setattr__(self, "representative_utility", float(self.representative_utility))
        arrays = {
            "available": _ro(self.available, dtype=np.bool_),
            "total_coverage_gain": _ro(self.total_coverage_gain, dtype=np.float64),
            "total_representative_gain": _ro(self.total_representative_gain, dtype=np.float64),
            "hard_gain": _ro(self.hard_gain, dtype=np.int32),
            "obligation_counts": _ro(self.obligation_counts, dtype=np.int32),
            "required_obligation_mask": _ro(self.required_obligation_mask, dtype=np.bool_),
            "unit_counts": _ro(self.unit_counts, dtype=np.int32),
        }
        n = arrays["available"].size
        if any(arr.ndim != 1 for arr in arrays.values()):
            raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint arrays must be one-dimensional.")
        if arrays["total_coverage_gain"].size != n or arrays["total_representative_gain"].size != n or arrays["hard_gain"].size != n:
            raise TrainingDataInputError("MVSTATE-REUSE1 candidate state cardinality mismatch.")
        if arrays["obligation_counts"].shape != arrays["required_obligation_mask"].shape:
            raise TrainingDataInputError("MVSTATE-REUSE1 obligation state cardinality mismatch.")
        for name, value in arrays.items():
            object.__setattr__(self, name, value)
        families = tuple(self.families)
        if not families or len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("MVSTATE-REUSE1 requires unique family checkpoints.")
        if any(item.coverage_gain.size != n for item in families):
            raise TrainingDataInputError("MVSTATE-REUSE1 family candidate cardinality mismatch.")
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})
        object.__setattr__(self, "unsatisfied_required_obligation_count", int(self.unsatisfied_required_obligation_count))

    def family(self, family_id: str) -> TargetMultiViewSelectionFamilyStateCheckpoint:
        try:
            return self._family_by_id[family_id]
        except KeyError:
            raise KeyError(family_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_STATE_CHECKPOINT_SCHEMA,
            "target_size": self.target_size,
            "selected_prefix_digest": self.selected_prefix_digest,
            "representative_utility": self.representative_utility,
            "available": _coverage_array_reference(self.available),
            "family_digests": [item.content_digest for item in self.families],
            "total_coverage_gain": _coverage_array_reference(self.total_coverage_gain),
            "total_representative_gain": _coverage_array_reference(self.total_representative_gain),
            "hard_gain": _coverage_array_reference(self.hard_gain),
            "obligation_counts": _coverage_array_reference(self.obligation_counts),
            "required_obligation_mask": _coverage_array_reference(self.required_obligation_mask),
            "unsatisfied_required_obligation_count": self.unsatisfied_required_obligation_count,
            "unit_counts": _coverage_array_reference(self.unit_counts),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def metadata_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "families": [item.metadata_dict() for item in self.families], "content_digest": self.content_digest}


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionDomainStateCache:
    label_domain_id: str
    reference_domain_digest: str
    sparse_domain_digest: str
    selection_domain_digest: str
    candidate_count: int
    checkpoints: tuple[TargetMultiViewSelectionStateCheckpoint, ...]
    _checkpoint_by_size: Mapping[int, TargetMultiViewSelectionStateCheckpoint] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_domain_digest", validate_digest(self.reference_domain_digest, name="reference_domain_digest"))
        object.__setattr__(self, "sparse_domain_digest", validate_digest(self.sparse_domain_digest, name="sparse_domain_digest"))
        object.__setattr__(self, "selection_domain_digest", validate_digest(self.selection_domain_digest, name="selection_domain_digest"))
        checkpoints = tuple(sorted(self.checkpoints, key=lambda item: item.target_size))
        if not checkpoints or len({item.target_size for item in checkpoints}) != len(checkpoints):
            raise TrainingDataInputError("MVSTATE-REUSE1 requires unique checkpoint sizes.")
        if any(item.available.size != int(self.candidate_count) for item in checkpoints):
            raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint/domain candidate cardinality mismatch.")
        object.__setattr__(self, "candidate_count", int(self.candidate_count))
        object.__setattr__(self, "checkpoints", checkpoints)
        object.__setattr__(self, "_checkpoint_by_size", {item.target_size: item for item in checkpoints})

    def checkpoint(self, target_size: int) -> TargetMultiViewSelectionStateCheckpoint:
        try:
            return self._checkpoint_by_size[int(target_size)]
        except KeyError:
            raise KeyError(int(target_size)) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_STATE_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "sparse_domain_digest": self.sparse_domain_digest,
            "selection_domain_digest": self.selection_domain_digest,
            "candidate_count": self.candidate_count,
            "checkpoint_digests": [item.content_digest for item in self.checkpoints],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def metadata_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "checkpoints": [item.metadata_dict() for item in self.checkpoints], "content_digest": self.content_digest}


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionStateCache:
    dataset_id: str
    target_coverage_reference_digest: str
    target_coverage_sparse_index_digest: str
    target_multi_view_selection_digest: str
    selector_policy_digest: str
    domains: tuple[TargetMultiViewSelectionDomainStateCache, ...]
    sparse_kernel_schema: str = TARGET_MULTI_VIEW_SELECTION_STATE_KERNEL_SCHEMA
    authority_version: str = TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_VERSION
    persistence_version: str = TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION
    _domain_by_id: Mapping[str, TargetMultiViewSelectionDomainStateCache] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise TrainingDataInputError("MVSTATE-REUSE1 dataset_id cannot be empty.")
        for name in ("target_coverage_reference_digest", "target_coverage_sparse_index_digest", "target_multi_view_selection_digest", "selector_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("MVSTATE-REUSE1 requires unique domain caches.")
        if self.sparse_kernel_schema != TARGET_MULTI_VIEW_SELECTION_STATE_KERNEL_SCHEMA:
            raise TrainingDataInputError("Unsupported MVSTATE-REUSE1 sparse-kernel schema.")
        if self.authority_version != TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_VERSION:
            raise TrainingDataInputError("Unsupported MVSTATE-REUSE1 cache authority version.")
        if self.persistence_version != TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION:
            raise TrainingDataInputError("Unsupported MVSTATE-REUSE1 persistence version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewSelectionDomainStateCache:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest": self.target_coverage_sparse_index_digest,
            "target_multi_view_selection_digest": self.target_multi_view_selection_digest,
            "selector_policy_digest": self.selector_policy_digest,
            "domain_digests": [item.content_digest for item in self.domains],
            "sparse_kernel_schema": self.sparse_kernel_schema,
            "authority_version": self.authority_version,
            "persistence_version": self.persistence_version,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def metadata_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "domains": [item.metadata_dict() for item in self.domains], "content_digest": self.content_digest}


def selected_prefix_digest(frame_uids: Sequence[str]) -> str:
    return digest({"schema": "mdstats.target-multi-view-selection-state-prefix.v1", "frame_uids": [str(v) for v in frame_uids]})


def checkpoint_from_domain_state(
    state: Any,
    *,
    target_size: int,
    selected_frame_uids: Sequence[str],
    representative_utility: float,
) -> TargetMultiViewSelectionStateCheckpoint:
    families = tuple(
        TargetMultiViewSelectionFamilyStateCheckpoint(
            family_id=item.family_id,
            coverage_mass=float(item.coverage_mass),
            covered=np.array(item.covered, copy=True),
            multiplicity=np.array(item.multiplicity, copy=True),
            coverage_gain=np.array(item.coverage_gain, copy=True),
            representative_gain=np.array(item.representative_gain, copy=True),
        )
        for item in state.family_states
    )
    return TargetMultiViewSelectionStateCheckpoint(
        target_size=int(target_size),
        selected_prefix_digest=selected_prefix_digest(selected_frame_uids),
        representative_utility=float(representative_utility),
        available=np.array(state.available, copy=True),
        families=families,
        total_coverage_gain=np.array(state.total_coverage_gain, copy=True),
        total_representative_gain=np.array(state.total_representative_gain, copy=True),
        hard_gain=np.array(state.hard_gain, copy=True),
        obligation_counts=np.array(state.obligation_counts, copy=True),
        required_obligation_mask=np.array(state.required_obligation_mask, copy=True),
        unsatisfied_required_obligation_count=int(state.unsatisfied_required_obligation_count),
        unit_counts=np.array(state.unit_counts, copy=True),
    )


def restore_domain_state(checkpoint: TargetMultiViewSelectionStateCheckpoint, reference_domain: Any, sparse_domain: Any) -> Any:
    """Return a writable selector state exactly cloned from one checkpoint."""
    from . import target_multi_view_selector as selector

    if checkpoint.available.size != int(sparse_domain.candidate_count):
        raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint candidate cardinality changed.")
    family_states = []
    for sparse_family in sparse_domain.families:
        cached = checkpoint.family(sparse_family.family_id)
        family = reference_domain.family(sparse_family.family_id)
        if cached.covered.size != int(sparse_family.witness_count):
            raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint witness cardinality changed.")
        family_states.append(selector._FamilyState(
            family_id=cached.family_id,
            weights=np.asarray(family.weights, dtype=np.float64),
            covered=np.array(cached.covered, copy=True),
            multiplicity=np.array(cached.multiplicity, copy=True),
            coverage_gain=np.array(cached.coverage_gain, copy=True),
            representative_gain=np.array(cached.representative_gain, copy=True),
            coverage_mass=float(cached.coverage_mass),
        ))
    return selector._DomainSelectorState(
        available=np.array(checkpoint.available, copy=True),
        family_states=family_states,
        total_coverage_gain=np.array(checkpoint.total_coverage_gain, copy=True),
        total_representative_gain=np.array(checkpoint.total_representative_gain, copy=True),
        hard_gain=np.array(checkpoint.hard_gain, copy=True),
        obligation_counts=np.array(checkpoint.obligation_counts, copy=True),
        required_obligation_mask=np.array(checkpoint.required_obligation_mask, copy=True),
        unsatisfied_required_obligation_count=int(checkpoint.unsatisfied_required_obligation_count),
        unit_counts=np.array(checkpoint.unit_counts, copy=True),
    )


def validate_target_multi_view_selection_state_cache(
    cache: TargetMultiViewSelectionStateCache,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_multi_view_selection: Any,
    verify_state_replay: bool = False,
) -> None:
    if cache.dataset_id != target_coverage_reference.dataset_id or cache.dataset_id != target_coverage_sparse_index.dataset_id:
        raise TrainingDataInputError("MVSTATE-REUSE1 dataset identity mismatch.")
    if cache.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("MVSTATE-REUSE1 reference digest mismatch.")
    if cache.target_coverage_sparse_index_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("MVSTATE-REUSE1 sparse-index digest mismatch.")
    if cache.target_multi_view_selection_digest != target_multi_view_selection.content_digest:
        raise TrainingDataInputError("MVSTATE-REUSE1 selection digest mismatch.")
    if cache.selector_policy_digest != target_multi_view_selection.policy.policy_digest:
        raise TrainingDataInputError("MVSTATE-REUSE1 selector policy digest mismatch.")
    for selection_domain in target_multi_view_selection.domains:
        reference_domain = target_coverage_reference.domain(selection_domain.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(selection_domain.label_domain_id)
        domain = cache.domain(selection_domain.label_domain_id)
        if domain.reference_domain_digest != reference_domain.content_digest or domain.sparse_domain_digest != sparse_domain.content_digest:
            raise TrainingDataInputError("MVSTATE-REUSE1 domain lineage mismatch.")
        if domain.selection_domain_digest != selection_domain.content_digest:
            raise TrainingDataInputError("MVSTATE-REUSE1 selection-domain digest mismatch.")
        materializable = [r for r in selection_domain.rungs if r.materializable]
        if [item.target_size for item in domain.checkpoints] != [r.target_size for r in materializable]:
            raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint sizes disagree with MVSEL rungs.")
        for checkpoint, rung in zip(domain.checkpoints, materializable, strict=True):
            if checkpoint.selected_prefix_digest != selected_prefix_digest(rung.frame_uids):
                raise TrainingDataInputError("MVSTATE-REUSE1 selected-prefix digest mismatch.")
            restored = restore_domain_state(checkpoint, reference_domain, sparse_domain)
            if int(np.count_nonzero(~restored.available)) != checkpoint.target_size:
                raise TrainingDataInputError("MVSTATE-REUSE1 checkpoint selected cardinality mismatch.")
        if verify_state_replay:
            from . import target_multi_view_selector as selector
            uid_to_candidate = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
            replay = selector._build_domain_state(reference_domain, sparse_domain)
            representative_utility = 0.0
            checkpoint_by_size = {item.target_size: item for item in domain.checkpoints}
            for rank, entry in enumerate(selection_domain.master_order, start=1):
                candidate = uid_to_candidate[entry.frame_uid]
                representative_utility += float(replay.total_representative_gain[candidate])
                selector._select_and_update(candidate, sparse_domain, replay)
                checkpoint = checkpoint_by_size.get(rank)
                if checkpoint is None:
                    continue
                restored = restore_domain_state(checkpoint, reference_domain, sparse_domain)
                if not selector._states_exactly_equal(replay, restored):
                    raise TrainingDataInputError(f"MVSTATE-REUSE1 checkpoint n{rank} differs from exact MVSEL replay.")
                if representative_utility != float(checkpoint.representative_utility):
                    raise TrainingDataInputError(f"MVSTATE-REUSE1 representative utility at n{rank} differs from exact replay.")


__all__ = [
    "TARGET_MULTI_VIEW_SELECTION_STATE_FAMILY_SCHEMA",
    "TARGET_MULTI_VIEW_SELECTION_STATE_CHECKPOINT_SCHEMA",
    "TARGET_MULTI_VIEW_SELECTION_STATE_DOMAIN_SCHEMA",
    "TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_SCHEMA",
    "TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_VERSION",
    "TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION",
    "TARGET_MULTI_VIEW_SELECTION_STATE_KERNEL_SCHEMA",
    "TargetMultiViewSelectionFamilyStateCheckpoint",
    "TargetMultiViewSelectionStateCheckpoint",
    "TargetMultiViewSelectionDomainStateCache",
    "TargetMultiViewSelectionStateCache",
    "selected_prefix_digest",
    "checkpoint_from_domain_state",
    "restore_domain_state",
    "validate_target_multi_view_selection_state_cache",
]
