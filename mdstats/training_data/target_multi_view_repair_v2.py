"""REPAIR2 exact active-shell repair over compact MVSTATE2 forward state."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from threading import local
import time
from typing import Any, Callable

import numpy as np

from ._common import TrainingDataInputError, digest
from .target_multi_view_repair import TargetMultiViewRepairRung, TargetMultiViewRepairSwap
from .target_multi_view_selector_v2 import (
    TargetMultiViewForwardStateV2,
    TargetMultiViewSelectionPlanV2,
    build_target_multi_view_forward_state_v2,
    deselect_target_multi_view_candidate_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from .progress_timing import format_progress_time
from .resources import StageResourceScope
from .work_queue import DeterministicWorkQueue


TARGET_MULTI_VIEW_REPAIR_V2_VERSION = "mdstats.target-data2c-repair2.forward-state.2026-08.v1"
TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA = "mdstats.target-multi-view-repair-plan.v2"
TARGET_MULTI_VIEW_REPAIR_POLICY_V2_SCHEMA = "mdstats.target-multi-view-repair-policy.v2"
_DEFAULT_UNIQUE_TOLERANCE = 1.0e-14
_DEFAULT_GAIN_TOLERANCE = 1.0e-14


def _resource_snapshot() -> tuple[int, int, int, int] | None:
    """Return cheap process-fault/I/O counters for opt-in REPAIR2 telemetry."""

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
    except (ImportError, AttributeError, OSError):
        return None
    return (
        int(getattr(usage, "ru_minflt", 0)),
        int(getattr(usage, "ru_majflt", 0)),
        int(getattr(usage, "ru_inblock", 0)),
        int(getattr(usage, "ru_oublock", 0)),
    )


def _resource_delta(
    before: tuple[int, int, int, int] | None,
    after: tuple[int, int, int, int] | None,
) -> dict[str, int] | None:
    if before is None or after is None:
        return None
    return {
        "minor_faults": after[0] - before[0],
        "major_faults": after[1] - before[1],
        "filesystem_inputs": after[2] - before[2],
        "filesystem_outputs": after[3] - before[3],
    }


def _emit_telemetry(callback: Any | None, payload: dict[str, Any]) -> None:
    if callback is not None:
        callback(payload)


def _new_state_telemetry() -> dict[str, Any]:
    return {
        "representative_objective_wall_seconds": 0.0,
        "proposal_frontier_state_invariant_wall_seconds": 0.0,
        "removed_witness_mark_wall_seconds": 0.0,
        "unit_filter_wall_seconds": 0.0,
        "removal_dependent_representative_diversity_wall_seconds": 0.0,
        "frontier_build_count": 0,
        "proposal_evaluation_count": 0,
        "frontier_coverage_gain_candidate_family_rows": 0,
        "frontier_coverage_gain_forward_edges": 0,
        "proposal_final_coverage_candidate_family_rows": 0,
        "proposal_final_coverage_forward_edges": 0,
        "candidates_after_hard_filter_total": 0,
        "candidates_after_bottleneck_filter_total": 0,
        "candidates_after_total_coverage_filter_total": 0,
        "candidates_after_unit_filter_total": 0,
        "candidates_after_representative_filter_total": 0,
        "candidates_after_diversity_filter_total": 0,
    }


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPolicyV2:
    """REPAIR2 policy mirror of the frozen REPAIR1 scientific policy."""

    unique_coverage_tolerance: float = _DEFAULT_UNIQUE_TOLERANCE
    gain_tie_tolerance: float = _DEFAULT_GAIN_TOLERANCE
    max_passes_per_shell: int = 2
    max_swaps_per_shell: int = 32
    removal_shortlist_limit: int = 64
    active_shell_only: bool = True
    replacement_rank_inheritance: bool = True
    strict_no_coverage_regression: bool = True
    clustering_score_authority: str = "diagnostic_only"
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_V2_VERSION

    def __post_init__(self) -> None:
        unique_tol = float(self.unique_coverage_tolerance)
        gain_tol = float(self.gain_tie_tolerance)
        if not np.isfinite(unique_tol) or unique_tol <= 0.0 or unique_tol > 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 unique_coverage_tolerance is invalid.")
        if not np.isfinite(gain_tol) or gain_tol <= 0.0 or gain_tol > 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 gain_tie_tolerance is invalid.")
        if int(self.max_passes_per_shell) < 1 or int(self.max_passes_per_shell) > 16:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 max_passes_per_shell is invalid.")
        if int(self.max_swaps_per_shell) < 1 or int(self.max_swaps_per_shell) > 1024:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 max_swaps_per_shell is invalid.")
        if int(self.removal_shortlist_limit) < 1 or int(self.removal_shortlist_limit) > 4096:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 removal_shortlist_limit is invalid.")
        if not self.active_shell_only or not self.replacement_rank_inheritance or not self.strict_no_coverage_regression:
            raise TrainingDataInputError(
                "TARGET-DATA2C-REPAIR2 freezes active-shell/rank-inheritance/non-regression behavior."
            )
        if self.clustering_score_authority != "diagnostic_only":
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 clustering score cannot become scientific authority.")
        if self.authority_version != TARGET_MULTI_VIEW_REPAIR_V2_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 policy version.")
        object.__setattr__(self, "unique_coverage_tolerance", unique_tol)
        object.__setattr__(self, "gain_tie_tolerance", gain_tol)
        object.__setattr__(self, "max_passes_per_shell", int(self.max_passes_per_shell))
        object.__setattr__(self, "max_swaps_per_shell", int(self.max_swaps_per_shell))
        object.__setattr__(self, "removal_shortlist_limit", int(self.removal_shortlist_limit))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_POLICY_V2_SCHEMA,
            "unique_coverage_tolerance": self.unique_coverage_tolerance,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "max_passes_per_shell": self.max_passes_per_shell,
            "max_swaps_per_shell": self.max_swaps_per_shell,
            "removal_shortlist_limit": self.removal_shortlist_limit,
            "active_shell_only": self.active_shell_only,
            "replacement_rank_inheritance": self.replacement_rank_inheritance,
            "strict_no_coverage_regression": self.strict_no_coverage_regression,
            "clustering_score_authority": self.clustering_score_authority,
            "authority_version": self.authority_version,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairPolicyV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_POLICY_V2_SCHEMA:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 policy schema.")
        result = cls(
            unique_coverage_tolerance=float(payload["unique_coverage_tolerance"]),
            gain_tie_tolerance=float(payload["gain_tie_tolerance"]),
            max_passes_per_shell=int(payload["max_passes_per_shell"]),
            max_swaps_per_shell=int(payload["max_swaps_per_shell"]),
            removal_shortlist_limit=int(payload["removal_shortlist_limit"]),
            active_shell_only=bool(payload["active_shell_only"]),
            replacement_rank_inheritance=bool(payload["replacement_rank_inheritance"]),
            strict_no_coverage_regression=bool(payload["strict_no_coverage_regression"]),
            clustering_score_authority=str(payload["clustering_score_authority"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") != result.policy_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairDomainPlanV2:
    label_domain_id: str
    reference_domain_digest: str
    mvidx1_domain_digest: str
    selection_domain_digest: str
    candidate_count: int
    repaired_master_order: tuple[str, ...]
    rungs: tuple[TargetMultiViewRepairRung, ...]
    total_swaps: int

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": "mdstats.target-multi-view-repair-domain.v2",
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "mvidx1_domain_digest": self.mvidx1_domain_digest,
            "selection_domain_digest": self.selection_domain_digest,
            "candidate_count": self.candidate_count,
            "repaired_master_order": self.repaired_master_order,
            "rungs": [item.to_dict() for item in self.rungs],
            "total_swaps": self.total_swaps,
        }
        return {**payload, "content_digest": digest(payload)} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairDomainPlanV2":
        if payload.get("schema") != "mdstats.target-multi-view-repair-domain.v2":
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            mvidx1_domain_digest=str(payload["mvidx1_domain_digest"]),
            selection_domain_digest=str(payload["selection_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            repaired_master_order=tuple(str(value) for value in payload["repaired_master_order"]),
            rungs=tuple(TargetMultiViewRepairRung.from_dict(item) for item in payload["rungs"]),
            total_swaps=int(payload["total_swaps"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPlanV2:
    dataset_id: str
    target_coverage_reference_digest: str
    mvidx1_content_digest: str
    target_multi_view_selection_v2_digest: str
    policy: TargetMultiViewRepairPolicyV2
    domains: tuple[TargetMultiViewRepairDomainPlanV2, ...]
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_V2_VERSION
    _domain_by_id: dict[str, TargetMultiViewRepairDomainPlanV2] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewRepairDomainPlanV2:
        return self._domain_by_id[label_domain_id]

    @property
    def target_coverage_sparse_index_digest(self) -> str:
        return self.mvidx1_content_digest

    @property
    def target_multi_view_selection_digest(self) -> str:
        return self.target_multi_view_selection_v2_digest

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_domains=False, include_digest=False))

    def to_dict(self, *, include_domains: bool = True, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "mvidx1_content_digest": self.mvidx1_content_digest,
            "target_multi_view_selection_v2_digest": self.target_multi_view_selection_v2_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }
        if include_domains:
            payload["domains"] = [item.to_dict() for item in self.domains]
        return (
            {**payload, "content_digest": digest({key: value for key, value in payload.items() if key != "domains"})}
            if include_digest
            else payload
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairPlanV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            mvidx1_content_digest=str(payload["mvidx1_content_digest"]),
            target_multi_view_selection_v2_digest=str(payload["target_multi_view_selection_v2_digest"]),
            policy=TargetMultiViewRepairPolicyV2.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewRepairDomainPlanV2.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 plan digest mismatch.")
        return result


class _RepairProposalScratchV2:
    """Reusable epoch/stamp membership for no-copy repair hypotheticals."""

    __slots__ = ("_marks", "_epoch")

    def __init__(self, forward_domain: Any) -> None:
        self._marks = tuple(
            np.zeros(int(family.witness_count), dtype=np.uint32)
            for family in forward_domain.families
        )
        self._epoch = np.uint32(0)

    def mark_removed(
        self,
        forward_domain: Any,
        removed: int,
        *,
        perf_scan: list[int] | None = None,
    ) -> None:
        next_epoch = int(self._epoch) + 1
        if next_epoch >= np.iinfo(np.uint32).max:
            for marks in self._marks:
                marks.fill(0)
            next_epoch = 1
        self._epoch = np.uint32(next_epoch)
        for marks, family in zip(self._marks, forward_domain.families, strict=True):
            witnesses = np.asarray(family.candidate_witness_indices(removed), dtype=np.int64)
            if perf_scan is not None:
                perf_scan[0] += 1
                perf_scan[1] += int(witnesses.size)
            if witnesses.size:
                marks[witnesses] = self._epoch

    def shared_mask(self, family_index: int, witnesses: np.ndarray) -> np.ndarray:
        if witnesses.size == 0:
            return np.zeros(0, dtype=np.bool_)
        return self._marks[int(family_index)][witnesses] == self._epoch


@dataclass(frozen=True, slots=True)
class _RepairProposalFrontierContextV2:
    """O(candidate_count) pre-removal frontier shared by one unchanged repair state."""

    representative_before: float
    before: tuple[int, float, float, float, int] | None
    hard_pending: bool
    bottleneck: int
    candidates: tuple[int, ...]
    proposal_possible: bool


def _hard_deficit(forward_domain: Any, state: TargetMultiViewForwardStateV2) -> int:
    return int(sum(
        max(0, int(item.minimum_selected_frames) - int(state.obligation_counts[index]))
        for index, item in enumerate(forward_domain.obligations)
        if item.required
    ))


def _unit_balance(state: TargetMultiViewForwardStateV2) -> int:
    counts = state.correlation_unit_counts.astype(np.int64)
    return -int(np.dot(counts, counts))


def _representative_utility(state: TargetMultiViewForwardStateV2) -> float:
    """Reproduce REPAIR1's historical harmonic scalar authority exactly."""

    total = 0.0
    for family_state in state.family_states:
        multiplicity = np.asarray(family_state.multiplicity, dtype=np.int64)
        if multiplicity.size == 0:
            continue
        max_n = int(np.max(multiplicity))
        harmonic = np.zeros(max_n + 1, dtype=np.float64)
        if max_n:
            harmonic[1:] = np.cumsum(
                1.0 / np.arange(1, max_n + 1, dtype=np.float64), dtype=np.float64
            )
        total += float(np.sum(family_state.weights * harmonic[multiplicity], dtype=np.float64))
    return total


def _objective(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    representative_utility: float | None = None,
) -> tuple[int, float, float, float, int]:
    coverage = [float(item.coverage_mass) for item in state.family_states]
    rep = _representative_utility(state) if representative_utility is None else float(representative_utility)
    return (
        _hard_deficit(forward_domain, state),
        min(coverage),
        float(np.sum(coverage, dtype=np.float64)),
        rep,
        _unit_balance(state),
    )


def _strictly_better(
    before: tuple[int, float, float, float, int],
    after: tuple[int, float, float, float, int],
    tolerance: float,
) -> bool:
    if after[0] < before[0]:
        return True
    if after[0] > before[0]:
        return False
    for old, new in zip(before[1:4], after[1:4], strict=True):
        if new > old + tolerance:
            return True
        if new < old - tolerance:
            return False
    return after[4] > before[4]


def _removal_metrics(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    *,
    perf_scan: list[int] | None = None,
) -> tuple[float, float]:
    unique = 0.0
    loss = 0.0
    for family, family_state in zip(forward_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        if perf_scan is not None:
            perf_scan[0] += 1
            perf_scan[1] += int(witnesses.size)
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
        if np.any(multiplicity < 1.0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 selected witness multiplicity underflow.")
        weights = family_state.weights[witnesses]
        unique_mask = multiplicity == 1.0
        if np.any(unique_mask):
            unique += float(np.sum(weights[unique_mask], dtype=np.float64))
        loss += float(np.sum(weights / multiplicity, dtype=np.float64))
    return unique, loss


def _hard_safe(candidate: int, forward_domain: Any, state: TargetMultiViewForwardStateV2) -> bool:
    for index in np.asarray(forward_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        item = forward_domain.obligations[int(index)]
        if not item.required:
            continue
        before = int(state.obligation_counts[index])
        before_deficit = max(0, int(item.minimum_selected_frames) - before)
        after_deficit = max(0, int(item.minimum_selected_frames) - (before - 1))
        if after_deficit > before_deficit:
            return False
    return True


def _hard_gain(candidate: int, forward_domain: Any, state: TargetMultiViewForwardStateV2) -> int:
    gain = 0
    for index in np.asarray(forward_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        item = forward_domain.obligations[int(index)]
        if item.required and int(state.obligation_counts[index]) < int(item.minimum_selected_frames):
            gain += 1
    return gain


def _family_coverage_gain(
    candidate: int,
    family_index: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    *,
    perf_scan: list[int] | None = None,
) -> float:
    family = forward_domain.families[int(family_index)]
    family_state = state.family_states[int(family_index)]
    witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
    if perf_scan is not None:
        perf_scan[0] += 1
        perf_scan[1] += int(witnesses.size)
    if witnesses.size == 0:
        return 0.0
    multiplicity = family_state.multiplicity[witnesses]
    return float(np.sum(family_state.weights[witnesses][multiplicity == 0], dtype=np.float64))


def _total_coverage_gains(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    *,
    perf_scan: list[int] | None = None,
) -> tuple[tuple[float, ...], float]:
    gains = tuple(
        _family_coverage_gain(
            candidate,
            family_index,
            forward_domain,
            state,
            perf_scan=perf_scan,
        )
        for family_index in range(len(forward_domain.families))
    )
    return gains, float(np.sum(gains, dtype=np.float64))


def _pair_representative_gain(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    scratch: _RepairProposalScratchV2,
) -> float:
    total = 0.0
    for family_index, (family, family_state) in enumerate(
        zip(forward_domain.families, state.family_states, strict=True)
    ):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
        shared = scratch.shared_mask(family_index, witnesses)
        if np.any(shared) and np.any(multiplicity[shared] < 2.0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 zero-unique removal invariant failed.")
        hypothetical = multiplicity - shared.astype(np.float64)
        total += float(
            np.sum(family_state.weights[witnesses] / (hypothetical + 1.0), dtype=np.float64)
        )
    return total


def _pair_diversity(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    scratch: _RepairProposalScratchV2,
) -> float:
    values: list[float] = []
    for family_index, (family, family_state) in enumerate(
        zip(forward_domain.families, state.family_states, strict=True)
    ):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.int64, copy=True)
        shared = scratch.shared_mask(family_index, witnesses)
        multiplicity[shared] -= 1
        if np.any(multiplicity < 0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 diversity multiplicity underflow.")
        values.append(float(np.mean(1.0 / (1.0 + multiplicity), dtype=np.float64)))
    return 0.0 if not values else float(np.mean(values, dtype=np.float64))


def _filter(candidates: tuple[int, ...], values: dict[int, float], tolerance: float) -> tuple[int, ...]:
    best = max(values[candidate] for candidate in candidates)
    return tuple(candidate for candidate in candidates if values[candidate] >= best - tolerance)


def _proposal_reference(
    reference_domain: Any,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    removal: tuple[int, int, float, float],
    policy: TargetMultiViewRepairPolicyV2,
    scratch: _RepairProposalScratchV2,
    *,
    perf: dict[str, Any] | None = None,
    coverage_gain_scan: list[int] | None = None,
    removed_mark_scan: list[int] | None = None,
) -> dict[str, Any] | None:
    """Frozen R0 scalar proposal oracle; production code does not call it."""

    rank, removed, unique, loss = removal
    mark_started = time.perf_counter() if perf is not None else 0.0
    scratch.mark_removed(forward_domain, removed, perf_scan=removed_mark_scan)
    if perf is not None:
        perf["removed_witness_mark_wall_seconds"] += time.perf_counter() - mark_started

    frontier_started = time.perf_counter() if perf is not None else 0.0
    available = tuple(int(value) for value in np.flatnonzero(state.available) if int(value) != removed)
    if not available:
        if perf is not None:
            perf["proposal_frontier_state_invariant_wall_seconds"] += time.perf_counter() - frontier_started
        return None
    tolerance = policy.gain_tie_tolerance
    representative_started = time.perf_counter() if perf is not None else 0.0
    representative_before = _representative_utility(state)
    before = _objective(forward_domain, state, representative_before)
    if perf is not None:
        perf["representative_objective_wall_seconds"] += time.perf_counter() - representative_started
    hard_pending = before[0] > 0

    candidates = available
    hard_values = {candidate: _hard_gain(candidate, forward_domain, state) for candidate in candidates}
    if hard_pending:
        maximum = max(hard_values.values())
        candidates = tuple(candidate for candidate in candidates if hard_values[candidate] == maximum)
    if perf is not None:
        perf["candidates_after_hard_filter_total"] += len(candidates)

    masses = np.asarray([item.coverage_mass for item in state.family_states], dtype=np.float64)
    bottleneck = int(np.flatnonzero(masses <= float(np.min(masses)) + tolerance)[0])
    bottleneck_values = {
        candidate: _family_coverage_gain(
            candidate,
            bottleneck,
            forward_domain,
            state,
            perf_scan=coverage_gain_scan,
        )
        for candidate in candidates
    }
    candidates = _filter(candidates, bottleneck_values, tolerance)
    if perf is not None:
        perf["candidates_after_bottleneck_filter_total"] += len(candidates)

    family_gains: dict[int, tuple[float, ...]] = {}
    total_values: dict[int, float] = {}
    for candidate in candidates:
        gains, total = _total_coverage_gains(
            candidate,
            forward_domain,
            state,
            perf_scan=coverage_gain_scan,
        )
        family_gains[candidate] = gains
        total_values[candidate] = total
    candidates = _filter(candidates, total_values, tolerance)
    if perf is not None:
        perf["candidates_after_total_coverage_filter_total"] += len(candidates)
        perf["proposal_frontier_state_invariant_wall_seconds"] += time.perf_counter() - frontier_started
    if not hard_pending and max(total_values[candidate] for candidate in candidates) <= tolerance:
        return None

    unit_started = time.perf_counter() if perf is not None else 0.0
    removed_unit = int(forward_domain.candidate_correlation_unit_codes[removed])
    hypothetical_unit_counts: dict[int, int] = {}
    for candidate in candidates:
        unit = int(forward_domain.candidate_correlation_unit_codes[candidate])
        hypothetical_unit_counts[candidate] = int(state.correlation_unit_counts[unit]) - int(unit == removed_unit)
    minimum_unit = min(hypothetical_unit_counts.values())
    candidates = tuple(candidate for candidate in candidates if hypothetical_unit_counts[candidate] == minimum_unit)
    if perf is not None:
        perf["unit_filter_wall_seconds"] += time.perf_counter() - unit_started
        perf["candidates_after_unit_filter_total"] += len(candidates)

    pair_started = time.perf_counter() if perf is not None else 0.0
    representative_values = {
        candidate: _pair_representative_gain(candidate, forward_domain, state, scratch)
        for candidate in candidates
    }
    candidates = _filter(candidates, representative_values, tolerance)
    if perf is not None:
        perf["candidates_after_representative_filter_total"] += len(candidates)
    diversity_values = {
        candidate: _pair_diversity(candidate, forward_domain, state, scratch)
        for candidate in candidates
    }
    candidates = _filter(candidates, diversity_values, tolerance)
    if perf is not None:
        perf["removal_dependent_representative_diversity_wall_seconds"] += (
            time.perf_counter() - pair_started
        )
        perf["candidates_after_diversity_filter_total"] += len(candidates)
    replacement = min(candidates, key=lambda candidate: reference_domain.frame_uids[candidate])

    if replacement not in family_gains:
        gains, total = _total_coverage_gains(
            replacement,
            forward_domain,
            state,
            perf_scan=coverage_gain_scan,
        )
        family_gains[replacement] = gains
        total_values[replacement] = total
    coverage_after = [
        min(1.0, float(item.coverage_mass) + float(gain))
        for item, gain in zip(state.family_states, family_gains[replacement], strict=True)
    ]
    hard_after = max(0, before[0] - hard_values[replacement])
    representative_after = float(representative_before - loss + representative_values[replacement])
    replacement_unit = int(forward_domain.candidate_correlation_unit_codes[replacement])
    if replacement_unit == removed_unit:
        balance_after = before[4]
    else:
        removed_count = int(state.correlation_unit_counts[removed_unit])
        replacement_count = int(state.correlation_unit_counts[replacement_unit])
        balance_after = before[4] + 2 * (removed_count - replacement_count - 1)
    after = (
        hard_after,
        float(min(coverage_after)),
        float(sum(coverage_after)),
        representative_after,
        balance_after,
    )
    if policy.strict_no_coverage_regression and any(
        new + tolerance < float(old.coverage_mass)
        for old, new in zip(state.family_states, coverage_after, strict=True)
    ):
        return None
    if not _strictly_better(before, after, tolerance):
        return None
    return {
        "rank": rank,
        "removed": removed,
        "replacement": replacement,
        "unique": unique,
        "loss": loss,
        "before": before,
        "after": after,
        "bottleneck": state.family_states[bottleneck].family_id,
    }


def _build_proposal_frontier_context_v2(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    policy: TargetMultiViewRepairPolicyV2,
    *,
    perf: dict[str, Any] | None = None,
    coverage_gain_scan: list[int] | None = None,
) -> _RepairProposalFrontierContextV2:
    """Build the exact pre-removal proposal frontier once for an unchanged state."""

    total_started = time.perf_counter() if perf is not None else 0.0
    representative_wall = 0.0
    if perf is not None:
        perf["frontier_build_count"] += 1

    available = tuple(int(value) for value in np.flatnonzero(state.available))
    if not available:
        if perf is not None:
            perf["proposal_frontier_state_invariant_wall_seconds"] += time.perf_counter() - total_started
        return _RepairProposalFrontierContextV2(0.0, None, False, -1, (), False)

    tolerance = policy.gain_tie_tolerance
    representative_started = time.perf_counter() if perf is not None else 0.0
    representative_before = _representative_utility(state)
    before = _objective(forward_domain, state, representative_before)
    if perf is not None:
        representative_wall = time.perf_counter() - representative_started
        perf["representative_objective_wall_seconds"] += representative_wall
    hard_pending = before[0] > 0

    candidates = available
    hard_values = {candidate: _hard_gain(candidate, forward_domain, state) for candidate in candidates}
    if hard_pending:
        maximum = max(hard_values.values())
        candidates = tuple(candidate for candidate in candidates if hard_values[candidate] == maximum)
    if perf is not None:
        perf["candidates_after_hard_filter_total"] += len(candidates)

    masses = np.asarray([item.coverage_mass for item in state.family_states], dtype=np.float64)
    bottleneck = int(np.flatnonzero(masses <= float(np.min(masses)) + tolerance)[0])
    bottleneck_values = {
        candidate: _family_coverage_gain(
            candidate,
            bottleneck,
            forward_domain,
            state,
            perf_scan=coverage_gain_scan,
        )
        for candidate in candidates
    }
    candidates = _filter(candidates, bottleneck_values, tolerance)
    if perf is not None:
        perf["candidates_after_bottleneck_filter_total"] += len(candidates)

    total_values: dict[int, float] = {}
    for candidate in candidates:
        _, total = _total_coverage_gains(
            candidate,
            forward_domain,
            state,
            perf_scan=coverage_gain_scan,
        )
        total_values[candidate] = total
    candidates = _filter(candidates, total_values, tolerance)
    if perf is not None:
        perf["candidates_after_total_coverage_filter_total"] += len(candidates)
        perf["proposal_frontier_state_invariant_wall_seconds"] += max(
            0.0, time.perf_counter() - total_started - representative_wall
        )

    proposal_possible = hard_pending or max(total_values[candidate] for candidate in candidates) > tolerance
    return _RepairProposalFrontierContextV2(
        representative_before=representative_before,
        before=before,
        hard_pending=hard_pending,
        bottleneck=bottleneck,
        candidates=candidates,
        proposal_possible=proposal_possible,
    )


def _proposal_from_frontier_context_v2(
    reference_domain: Any,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    removal: tuple[int, int, float, float],
    policy: TargetMultiViewRepairPolicyV2,
    scratch: _RepairProposalScratchV2,
    context: _RepairProposalFrontierContextV2,
    *,
    perf: dict[str, Any] | None = None,
    final_coverage_gain_scan: list[int] | None = None,
    removed_mark_scan: list[int] | None = None,
) -> dict[str, Any] | None:
    """Evaluate only removal-dependent terms against a frozen state frontier."""

    if not context.proposal_possible:
        return None
    rank, removed, unique, loss = removal
    if bool(state.available[removed]):
        raise TrainingDataInputError(
            "TARGET-DATA2C-REPAIR2 removal shortlist candidate unexpectedly remained available."
        )
    before = context.before
    if before is None or context.bottleneck < 0 or not context.candidates:
        return None

    mark_started = time.perf_counter() if perf is not None else 0.0
    scratch.mark_removed(forward_domain, removed, perf_scan=removed_mark_scan)
    if perf is not None:
        perf["removed_witness_mark_wall_seconds"] += time.perf_counter() - mark_started
        perf["proposal_evaluation_count"] += 1

    tolerance = policy.gain_tie_tolerance
    candidates = context.candidates
    unit_started = time.perf_counter() if perf is not None else 0.0
    removed_unit = int(forward_domain.candidate_correlation_unit_codes[removed])
    hypothetical_unit_counts: dict[int, int] = {}
    for candidate in candidates:
        unit = int(forward_domain.candidate_correlation_unit_codes[candidate])
        hypothetical_unit_counts[candidate] = int(state.correlation_unit_counts[unit]) - int(unit == removed_unit)
    minimum_unit = min(hypothetical_unit_counts.values())
    candidates = tuple(candidate for candidate in candidates if hypothetical_unit_counts[candidate] == minimum_unit)
    if perf is not None:
        perf["unit_filter_wall_seconds"] += time.perf_counter() - unit_started
        perf["candidates_after_unit_filter_total"] += len(candidates)

    pair_started = time.perf_counter() if perf is not None else 0.0
    representative_values = {
        candidate: _pair_representative_gain(candidate, forward_domain, state, scratch)
        for candidate in candidates
    }
    candidates = _filter(candidates, representative_values, tolerance)
    if perf is not None:
        perf["candidates_after_representative_filter_total"] += len(candidates)
    diversity_values = {
        candidate: _pair_diversity(candidate, forward_domain, state, scratch)
        for candidate in candidates
    }
    candidates = _filter(candidates, diversity_values, tolerance)
    if perf is not None:
        perf["removal_dependent_representative_diversity_wall_seconds"] += (
            time.perf_counter() - pair_started
        )
        perf["candidates_after_diversity_filter_total"] += len(candidates)
    replacement = min(candidates, key=lambda candidate: reference_domain.frame_uids[candidate])

    gains, _ = _total_coverage_gains(
        replacement,
        forward_domain,
        state,
        perf_scan=final_coverage_gain_scan,
    )
    coverage_after = [
        min(1.0, float(item.coverage_mass) + float(gain))
        for item, gain in zip(state.family_states, gains, strict=True)
    ]
    hard_after = max(0, before[0] - _hard_gain(replacement, forward_domain, state))
    representative_after = float(context.representative_before - loss + representative_values[replacement])
    replacement_unit = int(forward_domain.candidate_correlation_unit_codes[replacement])
    if replacement_unit == removed_unit:
        balance_after = before[4]
    else:
        removed_count = int(state.correlation_unit_counts[removed_unit])
        replacement_count = int(state.correlation_unit_counts[replacement_unit])
        balance_after = before[4] + 2 * (removed_count - replacement_count - 1)
    after = (
        hard_after,
        float(min(coverage_after)),
        float(sum(coverage_after)),
        representative_after,
        balance_after,
    )
    if policy.strict_no_coverage_regression and any(
        new + tolerance < float(old.coverage_mass)
        for old, new in zip(state.family_states, coverage_after, strict=True)
    ):
        return None
    if not _strictly_better(before, after, tolerance):
        return None
    return {
        "rank": rank,
        "removed": removed,
        "replacement": replacement,
        "unique": unique,
        "loss": loss,
        "before": before,
        "after": after,
        "bottleneck": state.family_states[context.bottleneck].family_id,
    }


def _better(
    left: dict[str, Any] | None,
    right: dict[str, Any],
    reference_domain: Any,
    tolerance: float,
) -> dict[str, Any]:
    if left is None or _strictly_better(left["after"], right["after"], tolerance):
        return right
    if _strictly_better(right["after"], left["after"], tolerance):
        return left
    lkey = (
        left["loss"],
        left["rank"],
        reference_domain.frame_uids[left["removed"]],
        reference_domain.frame_uids[left["replacement"]],
    )
    rkey = (
        right["loss"],
        right["rank"],
        reference_domain.frame_uids[right["removed"]],
        reference_domain.frame_uids[right["replacement"]],
    )
    return left if lkey <= rkey else right




def _parallel_repair_proposals_v2(
    reference_domain: Any,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    shortlist: list[tuple[int, int, float, float]],
    policy: TargetMultiViewRepairPolicyV2,
    context: _RepairProposalFrontierContextV2,
    *,
    workers: int,
    resource_scope: StageResourceScope | None,
    state_perf: dict[str, Any] | None,
    final_coverage_scan: list[int] | None,
    removed_mark_scan: list[int] | None,
) -> dict[str, Any] | None:
    """Evaluate immutable REPAIR2 removal proposals in deterministic parallel order."""

    count = len(shortlist)
    worker_count = max(1, min(int(workers), count))
    if worker_count == 1:
        scratch = _RepairProposalScratchV2(forward_domain)
        best: dict[str, Any] | None = None
        for removal in shortlist:
            proposal = _proposal_from_frontier_context_v2(
                reference_domain,
                forward_domain,
                state,
                removal,
                policy,
                scratch,
                context,
                perf=state_perf,
                final_coverage_gain_scan=final_coverage_scan,
                removed_mark_scan=removed_mark_scan,
            )
            if proposal is not None:
                best = _better(best, proposal, reference_domain, policy.gain_tie_tolerance)
        return best

    owned_scope = resource_scope is None
    scope = resource_scope or StageResourceScope(
        stage_name="TARGET-DATA2C-REPAIR2/proposals",
        cpu_threads_available=worker_count,
        cpu_threads_budget=worker_count,
        python_workers=worker_count,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        native_openmp_threads=1,
        pytorch_cpu_workers=1,
    )
    # The queue must reflect the actual proposal width even when the caller's
    # stage scope authorizes a wider CPU budget than this shortlist can use.
    if int(scope.python_workers) != worker_count:
        scope = StageResourceScope(
            stage_name=f"{scope.stage_name}/proposals",
            cpu_threads_available=int(scope.cpu_threads_available),
            cpu_threads_budget=int(scope.cpu_threads_budget),
            python_workers=worker_count,
            structural_workers=1,
            tree_workers=1,
            blas_threads=1,
            native_openmp_threads=1,
            pytorch_cpu_workers=1,
            ram_budget_bytes=scope.ram_budget_bytes,
        )

    thread_scratch = local()

    def evaluate(position: int, removal: tuple[int, int, float, float]):
        scratch = getattr(thread_scratch, "repair2_scratch", None)
        if scratch is None:
            scratch = _RepairProposalScratchV2(forward_domain)
            thread_scratch.repair2_scratch = scratch
        local_perf = _new_state_telemetry() if state_perf is not None else None
        local_coverage = [0, 0] if final_coverage_scan is not None else None
        local_removed = [0, 0] if removed_mark_scan is not None else None
        proposal = _proposal_from_frontier_context_v2(
            reference_domain,
            forward_domain,
            state,
            removal,
            policy,
            scratch,
            context,
            perf=local_perf,
            final_coverage_gain_scan=local_coverage,
            removed_mark_scan=local_removed,
        )
        return position, proposal, local_perf, local_coverage, local_removed

    results: dict[int, tuple[Any, ...]] = {}
    scratch_bytes = worker_count * sum(
        int(family.witness_count) * np.dtype(np.uint32).itemsize
        for family in forward_domain.families
    )
    queue = DeterministicWorkQueue(
        scope,
        max_ready_tasks=max(count, 2 * worker_count),
        max_inflight_tasks=max(1, 2 * worker_count),
        max_completed_tasks=max(1, 2 * worker_count),
        thread_name_prefix="mdstats-repair2",
        manage_resource_scope=owned_scope,
    )
    with queue:
        if scratch_bytes:
            queue.reserve_memory("repair2-thread-scratch", scratch_bytes)
        finished_before = int(queue.snapshot().finished_tasks)
        for position, removal in enumerate(shortlist):
            queue.submit(
                task_id=f"repair2-proposal-{position:04d}-rank-{int(removal[0]):08d}",
                canonical_order=(position,),
                function=evaluate,
                args=(position, removal),
                task_kind="repair2-proposal",
                # Worker-local scratch is reserved once above for the whole
                # proposal pool. Do not charge it again per queued task.
                estimated_memory_bytes=0,
                locality_key=str(reference_domain.label_domain_id),
            )
        while int(queue.snapshot().finished_tasks) < finished_before + count:
            queue.wait_for_completion()
            for completion in queue.drain_completed():
                results[int(completion.canonical_order[0])] = completion.value
        for completion in queue.drain_completed():
            results[int(completion.canonical_order[0])] = completion.value
        if scratch_bytes:
            queue.release_memory("repair2-thread-scratch")

    best: dict[str, Any] | None = None
    for position in range(count):
        _, proposal, local_perf, local_coverage, local_removed = results[position]
        if state_perf is not None and local_perf is not None:
            for key, value in local_perf.items():
                state_perf[key] += value
        if final_coverage_scan is not None and local_coverage is not None:
            final_coverage_scan[0] += int(local_coverage[0])
            final_coverage_scan[1] += int(local_coverage[1])
        if removed_mark_scan is not None and local_removed is not None:
            removed_mark_scan[0] += int(local_removed[0])
            removed_mark_scan[1] += int(local_removed[1])
        if proposal is not None:
            best = _better(best, proposal, reference_domain, policy.gain_tie_tolerance)
    return best


def build_target_multi_view_repair_plan_v2(
    target_coverage_reference: Any,
    target_coverage_forward_index: Any,
    target_multi_view_selection: TargetMultiViewSelectionPlanV2,
    *,
    policy: TargetMultiViewRepairPolicyV2 | None = None,
    workers: int = 1,
    batch_size: int = 256,
    progress_callback: Any | None = None,
    initial_states: dict[str, TargetMultiViewForwardStateV2] | None = None,
    initial_state_sizes: dict[str, int] | None = None,
    initial_state_modes: dict[str, str] | None = None,
    checkpoint_state_provider: (
        Callable[[str, int], TargetMultiViewForwardStateV2 | None] | None
    ) = None,
    telemetry_callback: Any | None = None,
    resource_scope: StageResourceScope | None = None,
) -> TargetMultiViewRepairPlanV2:
    """Build REPAIR2 using exact forward-only state and no-copy proposals.

    ``checkpoint_state_provider`` is the execution-only MVSTATE2 continuation
    seam. Before repair divergence the canonical owner may restore the exact
    pure-selector state for the *current* materializable rung, then still
    repair that rung's active shell from the previous repaired rung boundary.
    Missing state falls back to exact selected-prefix forward replay. After the
    first accepted repair swap the repaired state is carried forward and the
    provider is never consulted again.

    ``initial_states``/``initial_state_sizes`` remain as a compatibility form
    of a single rung checkpoint per domain and obey the same rung-aware rules.

    ``telemetry_callback`` is execution-only profiling. It is excluded from all
    scientific policy, serialization, lineage, and digest calculations.
    """

    del batch_size  # execution-only; scalar authority is canonical
    if int(workers) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 workers must be positive.")
    policy = policy or TargetMultiViewRepairPolicyV2()
    initial_states = {} if initial_states is None else initial_states
    initial_state_sizes = {} if initial_state_sizes is None else initial_state_sizes
    initial_state_modes = {} if initial_state_modes is None else initial_state_modes
    repair_started = time.perf_counter() if telemetry_callback is not None else 0.0
    repair_resource_before = _resource_snapshot() if telemetry_callback is not None else None
    _emit_telemetry(telemetry_callback, {
        "kind": "repair_start",
        "workers": int(workers),
        "scalar_authority": True,
    })
    domains: list[TargetMultiViewRepairDomainPlanV2] = []
    for reference_domain in target_coverage_reference.domains:
        domain_started = time.monotonic()
        forward_domain = target_coverage_forward_index.domain(reference_domain.label_domain_id)
        selection_domain = target_multi_view_selection.domain(reference_domain.label_domain_id)
        uid_to_candidate = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
        order = [uid_to_candidate[item.frame_uid] for item in selection_domain.master_order]
        legacy_state = initial_states.get(reference_domain.label_domain_id)
        legacy_restored_size = int(initial_state_sizes.get(reference_domain.label_domain_id, 0))
        legacy_restore_mode = str(initial_state_modes.get(reference_domain.label_domain_id, "mvstate2"))
        if legacy_state is None:
            legacy_restored_size = 0
        elif (
            legacy_restored_size < 0
            or legacy_restored_size > len(order)
            or legacy_state.selected_count != legacy_restored_size
        ):
            raise TrainingDataInputError(
                "TARGET-DATA2C-REPAIR2 initial MVSTATE2 continuation size is invalid."
            )
        state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
        previous_size = 0
        rungs: list[TargetMultiViewRepairRung] = []
        diverged = False
        proposal_count = 0
        restore_count = 0
        for base_rung in selection_domain.rungs:
            rung_started = time.perf_counter() if telemetry_callback is not None else 0.0
            rung_resource_before = _resource_snapshot() if telemetry_callback is not None else None
            size = int(base_rung.target_size)
            if not base_rung.materializable:
                rungs.append(TargetMultiViewRepairRung(
                    target_size=size,
                    materializable=False,
                    active_shell_start=previous_size,
                    unavailable_reason=base_rung.unavailable_reason or "unavailable_in_mvsel2",
                ))
                if telemetry_callback is not None:
                    rung_wall = time.perf_counter() - rung_started
                    _emit_telemetry(telemetry_callback, {
                        "kind": "rung",
                        "domain": reference_domain.label_domain_id,
                        "target_size": size,
                        "materializable": False,
                        "rung_wall_seconds": rung_wall,
                        "rung_wall_hhmmss": format_progress_time(rung_wall),
                        "eta_hhmmss": "--:--:--",
                        "resource_delta": _resource_delta(rung_resource_before, _resource_snapshot()),
                    })
                continue
            shell_start = previous_size
            restore_mode = (
                "post_divergence_carried_state"
                if diverged
                else "selected_prefix_forward_replay"
            )
            restored_state = None
            if not diverged:
                if checkpoint_state_provider is not None:
                    restored_state = checkpoint_state_provider(
                        reference_domain.label_domain_id, size
                    )
                    if restored_state is not None:
                        restore_mode = "mvstate2"
                if (
                    restored_state is None
                    and legacy_state is not None
                    and size == legacy_restored_size
                ):
                    restored_state = legacy_state
                    restore_mode = legacy_restore_mode
                if restored_state is not None:
                    if (
                        restored_state.selected_count != size
                        or tuple(restored_state.selected_order) != tuple(order[:size])
                    ):
                        raise TrainingDataInputError(
                            "TARGET-DATA2C-REPAIR2 MVSTATE2 continuation does not "
                            "match the current selector prefix."
                        )
                    state = restored_state
                    restore_count += 1

            extension_started = time.perf_counter() if telemetry_callback is not None else 0.0
            if restored_state is None:
                for rank in range(previous_size, size):
                    candidate = order[rank]
                    score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
                    select_target_multi_view_candidate_v2(candidate, forward_domain, state, score=score)
            extension_wall = (
                time.perf_counter() - extension_started if telemetry_callback is not None else 0.0
            )
            shell_size = size - shell_start
            initial_scan = [0, 0] if telemetry_callback is not None else None
            initial_started = time.perf_counter() if telemetry_callback is not None else 0.0
            initial_zero = sum(
                _removal_metrics(
                    order[rank],
                    forward_domain,
                    state,
                    perf_scan=initial_scan,
                )[0] <= policy.unique_coverage_tolerance
                for rank in range(shell_start, size)
            )
            initial_wall = (
                time.perf_counter() - initial_started if telemetry_callback is not None else 0.0
            )
            accepted: list[TargetMultiViewRepairSwap] = []
            rung_proposal_start = proposal_count
            state_iteration = 0
            for pass_index in range(policy.max_passes_per_shell):
                changed = False
                while len(accepted) < policy.max_swaps_per_shell:
                    state_iteration += 1
                    state_resource_before = _resource_snapshot() if telemetry_callback is not None else None
                    state_perf = _new_state_telemetry() if telemetry_callback is not None else None
                    removal_scan = [0, 0] if telemetry_callback is not None else None
                    removal_started = time.perf_counter() if telemetry_callback is not None else 0.0
                    removals: list[tuple[int, int, float, float]] = []
                    for rank in range(shell_start, size):
                        candidate = order[rank]
                        unique, loss = _removal_metrics(
                            candidate,
                            forward_domain,
                            state,
                            perf_scan=removal_scan,
                        )
                        if unique <= policy.unique_coverage_tolerance and _hard_safe(candidate, forward_domain, state):
                            removals.append((rank, candidate, unique, loss))
                    removal_wall = (
                        time.perf_counter() - removal_started if telemetry_callback is not None else 0.0
                    )
                    removals.sort(key=lambda row: (
                        row[3],
                        -int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[row[1]])]),
                        reference_domain.frame_uids[row[1]],
                    ))
                    shortlist = removals[: policy.removal_shortlist_limit]
                    state_proposal_start = proposal_count
                    proposal_count += len(shortlist)
                    frontier_scan = [0, 0] if telemetry_callback is not None else None
                    final_coverage_scan = [0, 0] if telemetry_callback is not None else None
                    removed_mark_scan = [0, 0] if telemetry_callback is not None else None
                    best = None
                    if shortlist:
                        if any(bool(state.available[int(removal[1])]) for removal in shortlist):
                            raise TrainingDataInputError(
                                "TARGET-DATA2C-REPAIR2 removal shortlist contains an available candidate."
                            )
                        context = _build_proposal_frontier_context_v2(
                            forward_domain,
                            state,
                            policy,
                            perf=state_perf,
                            coverage_gain_scan=frontier_scan,
                        )
                        if context.proposal_possible:
                            best = _parallel_repair_proposals_v2(
                                reference_domain,
                                forward_domain,
                                state,
                                shortlist,
                                policy,
                                context,
                                workers=int(workers),
                                resource_scope=resource_scope,
                                state_perf=state_perf,
                                final_coverage_scan=final_coverage_scan,
                                removed_mark_scan=removed_mark_scan,
                            )
                    mutation_wall = 0.0
                    accepted_in_state = 0
                    if best is not None:
                        rank = int(best["rank"])
                        removed = int(best["removed"])
                        replacement = int(best["replacement"])
                        future = next((index for index in range(size, len(order)) if order[index] == replacement), -1)
                        displaced = None
                        if future >= size:
                            order[future] = removed
                            displaced = future
                        order[rank] = replacement

                        mutation_started = time.perf_counter() if telemetry_callback is not None else 0.0
                        deselect_target_multi_view_candidate_v2(removed, forward_domain, state)
                        accepted_score = score_target_multi_view_candidate_v2(replacement, forward_domain, state)
                        select_target_multi_view_candidate_v2(replacement, forward_domain, state, score=accepted_score)
                        mutation_wall = (
                            time.perf_counter() - mutation_started if telemetry_callback is not None else 0.0
                        )
                        diverged = True
                        before = best["before"]
                        after = best["after"]
                        accepted.append(TargetMultiViewRepairSwap(
                            target_size=size,
                            pass_index=pass_index,
                            swap_index=len(accepted),
                            rank=rank,
                            removed_frame_uid=reference_domain.frame_uids[removed],
                            replacement_frame_uid=reference_domain.frame_uids[replacement],
                            removed_unique_coverage=best["unique"],
                            removed_representative_loss=best["loss"],
                            hard_deficit_before=before[0],
                            hard_deficit_after=after[0],
                            minimum_coverage_before=before[1],
                            minimum_coverage_after=after[1],
                            total_coverage_before=before[2],
                            total_coverage_after=after[2],
                            representative_utility_before=before[3],
                            representative_utility_after=after[3],
                            unit_balance_before=before[4],
                            unit_balance_after=after[4],
                            bottleneck_family_id=best["bottleneck"],
                            displaced_future_rank=displaced,
                        ))
                        accepted_in_state = 1
                        changed = True
                    if telemetry_callback is not None:
                        assert state_perf is not None
                        assert removal_scan is not None
                        assert frontier_scan is not None
                        assert final_coverage_scan is not None
                        assert removed_mark_scan is not None
                        state_perf["frontier_coverage_gain_candidate_family_rows"] = int(frontier_scan[0])
                        state_perf["frontier_coverage_gain_forward_edges"] = int(frontier_scan[1])
                        state_perf["proposal_final_coverage_candidate_family_rows"] = int(final_coverage_scan[0])
                        state_perf["proposal_final_coverage_forward_edges"] = int(final_coverage_scan[1])
                        state_event = {
                            "kind": "repair_state",
                            "domain": reference_domain.label_domain_id,
                            "target_size": size,
                            "pass_index": pass_index,
                            "state_iteration": state_iteration,
                            "removal_metric_scan_wall_seconds": removal_wall,
                            "removal_metric_scan_wall_hhmmss": format_progress_time(removal_wall),
                            "removal_metric_candidate_family_rows": int(removal_scan[0]),
                            "removal_metric_forward_edges": int(removal_scan[1]),
                            "zero_unique_hard_safe_removals": len(removals),
                            "removal_shortlist_size": len(shortlist),
                            "proposal_count": proposal_count - state_proposal_start,
                            "rung_cumulative_proposal_count": proposal_count - rung_proposal_start,
                            "domain_cumulative_proposal_count": proposal_count,
                            "accepted_swaps": accepted_in_state,
                            "rung_cumulative_accepted_swaps": len(accepted),
                            "coverage_gain_candidate_family_rows": int(frontier_scan[0] + final_coverage_scan[0]),
                            "coverage_gain_forward_edges": int(frontier_scan[1] + final_coverage_scan[1]),
                            "removed_mark_candidate_family_rows": int(removed_mark_scan[0]),
                            "removed_mark_forward_edges": int(removed_mark_scan[1]),
                            "accepted_mutation_wall_seconds": mutation_wall,
                            "accepted_mutation_wall_hhmmss": format_progress_time(mutation_wall),
                            "eta_hhmmss": "--:--:--",
                            "resource_delta": _resource_delta(state_resource_before, _resource_snapshot()),
                        }
                        state_event.update(state_perf)
                        for key in (
                            "representative_objective_wall_seconds",
                            "proposal_frontier_state_invariant_wall_seconds",
                            "removed_witness_mark_wall_seconds",
                            "unit_filter_wall_seconds",
                            "removal_dependent_representative_diversity_wall_seconds",
                        ):
                            state_event[key.replace("_seconds", "_hhmmss")] = format_progress_time(
                                float(state_event[key])
                            )
                        _emit_telemetry(telemetry_callback, state_event)
                    if best is None:
                        break
                if not changed:
                    break
            coverage = tuple(
                (item.family_id, min(1.0, max(0.0, item.coverage_mass)))
                for item in state.family_states
            )
            unsatisfied = tuple(sorted(
                item.obligation_id
                for index, item in enumerate(forward_domain.obligations)
                if item.required and int(state.obligation_counts[index]) < int(item.minimum_selected_frames)
            ))
            for family_id, value in coverage:
                if value + policy.gain_tie_tolerance < dict(base_rung.family_coverage)[family_id]:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 same-N coverage regressed below MVSEL2.")
            if base_rung.hard_obligations_passed and unsatisfied:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 hard obligations regressed below MVSEL2.")
            rungs.append(TargetMultiViewRepairRung(
                target_size=size,
                materializable=True,
                active_shell_start=shell_start,
                frame_uids=tuple(reference_domain.frame_uids[candidate] for candidate in order[:size]),
                family_coverage=coverage,
                hard_obligations_passed=not unsatisfied,
                unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=(
                    not unsatisfied
                    and all(
                        value >= target_multi_view_selection.policy.coverage_threshold - policy.gain_tie_tolerance
                        for _, value in coverage
                    )
                ),
                swaps=tuple(accepted),
                zero_unique_shell_fraction=0.0 if not shell_size else initial_zero / shell_size,
            ))
            if progress_callback is not None:
                state_mode = "post_divergence_carried_state" if diverged else restore_mode
                progress_callback(
                    f"status=rung; progress={size}/{selection_domain.rungs[-1].target_size}; "
                    f"elapsed={format_progress_time(time.monotonic() - domain_started)}; eta=--:--:--; "
                    f"domain={reference_domain.label_domain_id}; target_size={size}; "
                    f"active_shell_start={shell_start}; swaps={len(accepted)}; "
                    f"proposals={proposal_count}; proposal_full_state_copies=0; "
                    f"selected_prefix_state_mode={state_mode}; "
                    f"rung_entry_state_mode={restore_mode}; "
                    f"mvstate2_restore_count={restore_count}; "
                    f"zero_unique_shell_fraction={0.0 if not shell_size else initial_zero / shell_size:.6f}; "
                    f"inverse_mutation=false"
                )
            if telemetry_callback is not None:
                rung_wall = time.perf_counter() - rung_started
                state_mode = "post_divergence_carried_state" if diverged else restore_mode
                _emit_telemetry(telemetry_callback, {
                    "kind": "rung",
                    "domain": reference_domain.label_domain_id,
                    "target_size": size,
                    "materializable": True,
                    "selected_prefix_extension_wall_seconds": extension_wall,
                    "selected_prefix_extension_wall_hhmmss": format_progress_time(extension_wall),
                    "initial_zero_unique_scan_wall_seconds": initial_wall,
                    "initial_zero_unique_scan_wall_hhmmss": format_progress_time(initial_wall),
                    "initial_zero_unique_candidate_family_rows": int(initial_scan[0]),
                    "initial_zero_unique_forward_edges": int(initial_scan[1]),
                    "initial_zero_unique_count": initial_zero,
                    "repair_state_iterations": state_iteration,
                    "rung_proposal_count": proposal_count - rung_proposal_start,
                    "domain_cumulative_proposal_count": proposal_count,
                    "accepted_swaps": len(accepted),
                    "selected_prefix_state_mode": state_mode,
                    "rung_entry_state_mode": restore_mode,
                    "mvstate2_restore_count": restore_count,
                    "rung_wall_seconds": rung_wall,
                    "rung_wall_hhmmss": format_progress_time(rung_wall),
                    "eta_hhmmss": "--:--:--",
                    "resource_delta": _resource_delta(rung_resource_before, _resource_snapshot()),
                })
            previous_size = size
        domains.append(TargetMultiViewRepairDomainPlanV2(
            label_domain_id=reference_domain.label_domain_id,
            reference_domain_digest=reference_domain.content_digest,
            mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
            selection_domain_digest=selection_domain.content_digest,
            candidate_count=forward_domain.candidate_count,
            repaired_master_order=tuple(reference_domain.frame_uids[candidate] for candidate in order),
            rungs=tuple(rungs),
            total_swaps=sum(len(rung.swaps) for rung in rungs),
        ))
    result = TargetMultiViewRepairPlanV2(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        mvidx1_content_digest=target_coverage_forward_index.mvidx1_content_digest,
        target_multi_view_selection_v2_digest=target_multi_view_selection.content_digest,
        policy=policy,
        domains=tuple(domains),
    )
    if telemetry_callback is not None:
        repair_wall = time.perf_counter() - repair_started
        _emit_telemetry(telemetry_callback, {
            "kind": "repair_complete",
            "wall_seconds": repair_wall,
            "wall_hhmmss": format_progress_time(repair_wall),
            "eta_hhmmss": "00:00:00",
            "resource_delta": _resource_delta(repair_resource_before, _resource_snapshot()),
            "content_digest": result.content_digest,
        })
    return result


def validate_target_multi_view_repair_authority_v2(
    plan: TargetMultiViewRepairPlanV2,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_multi_view_selection: TargetMultiViewSelectionPlanV2,
) -> None:
    """Recompute repaired rung coverage, obligations, nesting, and lineage."""

    from .target_coverage_sparse_index import (
        indexed_family_covered_mass,
        indexed_obligation_selected_counts,
    )

    if (
        plan.dataset_id != target_coverage_reference.dataset_id
        or plan.dataset_id != target_coverage_sparse_index.dataset_id
    ):
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 dataset lineage mismatch.")
    if (
        plan.target_coverage_reference_digest != target_coverage_reference.content_digest
        or plan.mvidx1_content_digest != target_coverage_sparse_index.content_digest
    ):
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 reference/MVIDX lineage mismatch.")
    if plan.target_multi_view_selection_v2_digest != target_multi_view_selection.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 selector lineage mismatch.")
    for domain_plan in plan.domains:
        reference_domain = target_coverage_reference.domain(domain_plan.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(domain_plan.label_domain_id)
        selection_domain = target_multi_view_selection.domain(domain_plan.label_domain_id)
        uid_to_candidate = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
        previous: tuple[str, ...] = ()
        for base, rung in zip(selection_domain.rungs, domain_plan.rungs, strict=True):
            if not rung.materializable:
                continue
            if rung.frame_uids[: len(previous)] != previous or len(rung.frame_uids) != rung.target_size:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 immutable-prefix/nesting check failed.")
            selected = tuple(uid_to_candidate[uid] for uid in rung.frame_uids)
            coverage = tuple(
                (
                    family.family_id,
                    indexed_family_covered_mass(
                        sparse_domain.family(family.family_id), family.weights, selected
                    ),
                )
                for family in reference_domain.families
            )
            if not np.allclose(
                [value for _, value in coverage],
                [value for _, value in rung.family_coverage],
                rtol=0.0,
                atol=5.0e-13,
            ):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 rung coverage mismatch.")
            if any(
                value + plan.policy.gain_tie_tolerance < dict(base.family_coverage)[family_id]
                for family_id, value in coverage
            ):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 same-N coverage regression.")
            counts = indexed_obligation_selected_counts(sparse_domain, selected)
            unsatisfied = tuple(sorted(
                item.obligation_id
                for index, item in enumerate(sparse_domain.obligations)
                if item.required and int(counts[index]) < int(item.minimum_selected_frames)
            ))
            if unsatisfied != rung.unsatisfied_obligation_ids or (base.hard_obligations_passed and unsatisfied):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 hard-obligation evidence mismatch.")
            for swap in rung.swaps:
                if (
                    not rung.active_shell_start <= swap.rank < rung.target_size
                    or rung.frame_uids[swap.rank] != swap.replacement_frame_uid
                ):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 swap rank inheritance is invalid.")
            previous = rung.frame_uids
