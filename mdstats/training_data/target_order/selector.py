"""MVSEL2 exact scientific primitives, reference oracle and plan records.

Restored from TARGET-DATA2C-MVSEL2 (carrier ``3937881e`` blob ``2e5af029``)
and rebound to one exact ``P_train`` domain, canonical obligations and the
current configured ladder.  Scores are evaluated on demand from forward CSR
rows against compact state; there are no candidate marginal arrays and no
inverse adjacency.

This module owns D2 section 8 semantics: candidate primitives ``H``, ``G_m``,
``G``, ``R`` and ``D``; the Phase-A lexicographic contender filter with the
first canonical bottleneck family; Phase B by representative gain,
correlation balance, sparse diversity and UID; binary64 arithmetic with the
inclusive ``value >= best - 1e-14`` rule.  The sequential Phase-A reference,
the full-forward Phase-B oracle and the reference lazy frontier stay here as
the independent oracle; production rank loops use :mod:`kernels` and
:mod:`engine`, which must reproduce these choices exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest

MVSEL2_VERSION = "mdstats.target-order.mvsel2.forward-lazy.v1"
MVSEL2_POLICY_SCHEMA = "mdstats.target-multi-view-selector-policy.v3"
SELECTION_ENTRY_SCHEMA = "mdstats.target-multi-view-selection-entry.v2"
SELECTION_RUNG_SCHEMA = "mdstats.target-multi-view-selection-rung.v2"
SELECTION_PLAN_SCHEMA = "mdstats.target-multi-view-selection-plan.v3"

PHASE_HARD_COVERAGE = "hard_coverage"
PHASE_REPRESENTATIVE_FILL = "representative_fill"
MONOTONICITY_GUARD = 5.0e-13


def native_row(values: Any) -> np.ndarray:
    """One authenticated CSR row without widening/copying its dtype."""

    row = np.asarray(values)
    if row.ndim != 1 or row.dtype.kind not in "iu":
        raise TrainingDataInputError("MVSEL2 CSR row is not an integer vector.")
    return row


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectorPolicy:
    """Frozen MVSEL2 policy; configured sizes are rung boundaries only."""

    coverage_threshold: float = 0.95
    gain_tie_tolerance: float = 1.0e-14
    authority_version: str = MVSEL2_VERSION

    def __post_init__(self) -> None:
        if float(self.coverage_threshold) != 0.95:
            raise TrainingDataInputError("MVSEL2 freezes the coverage threshold at 0.95.")
        if float(self.gain_tie_tolerance) != 1.0e-14:
            raise TrainingDataInputError("MVSEL2 freezes the contender tolerance at 1e-14.")
        if self.authority_version != MVSEL2_VERSION:
            raise TrainingDataInputError("Unsupported MVSEL2 policy version.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": MVSEL2_POLICY_SCHEMA,
            "coverage_threshold": self.coverage_threshold,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "representative_gain": "harmonic_witness_multiplicity",
            "provenance_balance": "least_selected_correlation_unit",
            "diversity_tie_break": "sparse_neighborhood_inverse_multiplicity",
            "lazy_phase_b": "certified_outward_rounded_upper_bounds",
            "authority_version": self.authority_version,
        }
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectorPolicy":
        if payload.get("schema") != MVSEL2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVSEL2 policy schema.")
        result = cls(
            coverage_threshold=float(payload["coverage_threshold"]),
            gain_tie_tolerance=float(payload["gain_tie_tolerance"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") != result.policy_digest:
            raise TrainingDataSerializationError("MVSEL2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionEntry:
    rank: int
    frame_uid: str
    phase: str
    primary_reason: str
    bottleneck_family_id: str | None
    hard_obligation_gain: int
    bottleneck_coverage_gain: float
    total_coverage_gain: float
    representative_gain: float
    normalized_diversity: float
    correlation_unit_code: int

    def __post_init__(self) -> None:
        if int(self.rank) < 0 or int(self.hard_obligation_gain) < 0 or int(self.correlation_unit_code) < 0:
            raise TrainingDataInputError("MVSEL2 entry integer fields are invalid.")
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        if self.phase not in {PHASE_HARD_COVERAGE, PHASE_REPRESENTATIVE_FILL}:
            raise TrainingDataInputError("MVSEL2 entry phase is invalid.")
        for name in ("bottleneck_coverage_gain", "total_coverage_gain", "representative_gain", "normalized_diversity"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < -1.0e-12:
                raise TrainingDataInputError(f"MVSEL2 entry {name} is invalid.")
            object.__setattr__(self, name, max(0.0, value))
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(self, "hard_obligation_gain", int(self.hard_obligation_gain))
        object.__setattr__(self, "correlation_unit_code", int(self.correlation_unit_code))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SELECTION_ENTRY_SCHEMA,
            "rank": self.rank,
            "frame_uid": self.frame_uid,
            "phase": self.phase,
            "primary_reason": self.primary_reason,
            "bottleneck_family_id": self.bottleneck_family_id,
            "hard_obligation_gain": self.hard_obligation_gain,
            "bottleneck_coverage_gain": self.bottleneck_coverage_gain,
            "total_coverage_gain": self.total_coverage_gain,
            "representative_gain": self.representative_gain,
            "normalized_diversity": self.normalized_diversity,
            "correlation_unit_code": self.correlation_unit_code,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionEntry":
        if payload.get("schema") != SELECTION_ENTRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVSEL2 entry schema.")
        return cls(
            rank=int(payload["rank"]),
            frame_uid=str(payload["frame_uid"]),
            phase=str(payload["phase"]),
            primary_reason=str(payload["primary_reason"]),
            bottleneck_family_id=None if payload.get("bottleneck_family_id") is None else str(payload["bottleneck_family_id"]),
            hard_obligation_gain=int(payload["hard_obligation_gain"]),
            bottleneck_coverage_gain=float(payload["bottleneck_coverage_gain"]),
            total_coverage_gain=float(payload["total_coverage_gain"]),
            representative_gain=float(payload["representative_gain"]),
            normalized_diversity=float(payload["normalized_diversity"]),
            correlation_unit_code=int(payload["correlation_unit_code"]),
        )


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionRung:
    target_size: int
    frame_uids_digest: str
    family_coverage: tuple[tuple[str, float], ...]
    unsatisfied_obligation_ids: tuple[str, ...]
    phase_at_boundary: str
    shell_coverage_gain: float
    shell_representative_gain: float

    @property
    def hard_obligations_passed(self) -> bool:
        return not self.unsatisfied_obligation_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SELECTION_RUNG_SCHEMA,
            "target_size": int(self.target_size),
            "frame_uids_digest": self.frame_uids_digest,
            "family_coverage": [[k, float(v)] for k, v in self.family_coverage],
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "phase_at_boundary": self.phase_at_boundary,
            "shell_coverage_gain": float(self.shell_coverage_gain),
            "shell_representative_gain": float(self.shell_representative_gain),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionRung":
        if payload.get("schema") != SELECTION_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVSEL2 rung schema.")
        return cls(
            target_size=int(payload["target_size"]),
            frame_uids_digest=str(payload["frame_uids_digest"]),
            family_coverage=tuple((str(v[0]), float(v[1])) for v in payload["family_coverage"]),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload["unsatisfied_obligation_ids"]),
            phase_at_boundary=str(payload["phase_at_boundary"]),
            shell_coverage_gain=float(payload["shell_coverage_gain"]),
            shell_representative_gain=float(payload["shell_representative_gain"]),
        )


def prefix_digest(frame_uids: Sequence[str]) -> str:
    return digest({"schema": "mdstats.target-order-prefix.v1", "frame_uids": list(frame_uids)})


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionPlan:
    """The pure MVSEL2 master order through the configured ceiling."""

    target_coverage_reference_digest: str
    mvidx_content_digest: str
    policy: TargetMultiViewSelectorPolicy
    configured_sizes: tuple[int, ...]
    entries: tuple[TargetMultiViewSelectionEntry, ...]
    rungs: tuple[TargetMultiViewSelectionRung, ...]
    phase_a_completed_at: int | None

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.configured_sizes)
        if not sizes or sizes != tuple(sorted(set(sizes))) or len(self.entries) != sizes[-1]:
            raise TrainingDataInputError("MVSEL2 plan must order exactly through the configured ceiling.")
        if any(entry.rank != index for index, entry in enumerate(self.entries)):
            raise TrainingDataInputError("MVSEL2 plan ranks are not contiguous.")
        if tuple(item.target_size for item in self.rungs) != sizes:
            raise TrainingDataInputError("MVSEL2 plan rungs do not match the configured ladder.")
        object.__setattr__(self, "configured_sizes", sizes)

    @property
    def master_order(self) -> tuple[str, ...]:
        return tuple(entry.frame_uid for entry in self.entries)

    def rung(self, target_size: int) -> TargetMultiViewSelectionRung:
        for item in self.rungs:
            if item.target_size == int(target_size):
                return item
        raise KeyError(target_size)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": SELECTION_PLAN_SCHEMA,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "mvidx_content_digest": self.mvidx_content_digest,
            "policy": self.policy.to_dict(),
            "configured_sizes": list(self.configured_sizes),
            "entries": [item.to_dict() for item in self.entries],
            "rungs": [item.to_dict() for item in self.rungs],
            "phase_a_completed_at": self.phase_a_completed_at,
        }
        return {**payload, "content_digest": digest(payload)}

    @property
    def content_digest(self) -> str:
        return str(self.to_dict()["content_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionPlan":
        if payload.get("schema") != SELECTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVSEL2 plan schema.")
        result = cls(
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            mvidx_content_digest=str(payload["mvidx_content_digest"]),
            policy=TargetMultiViewSelectorPolicy.from_dict(payload["policy"]),
            configured_sizes=tuple(int(v) for v in payload["configured_sizes"]),
            entries=tuple(TargetMultiViewSelectionEntry.from_dict(v) for v in payload["entries"]),
            rungs=tuple(TargetMultiViewSelectionRung.from_dict(v) for v in payload["rungs"]),
            phase_a_completed_at=None if payload.get("phase_a_completed_at") is None else int(payload["phase_a_completed_at"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("MVSEL2 plan digest mismatch.")
        return result


# --- forward state ----------------------------------------------------------


@dataclass(slots=True)
class TargetMultiViewForwardFamilyState:
    family_id: str
    weights: np.ndarray
    multiplicity: np.ndarray
    coverage_mass: float = 0.0


@dataclass(slots=True)
class TargetMultiViewForwardState:
    available: np.ndarray
    selected_order: list[int]
    family_states: list[TargetMultiViewForwardFamilyState]
    obligation_counts: np.ndarray
    unsatisfied_required_obligation_count: int
    correlation_unit_counts: np.ndarray
    representative_utility: float = 0.0
    #: Reconstructible execution cache owned by this exact state object.  A
    #: reconstructed or restored state always starts without one, so no cache
    #: derived from a different (e.g. pre-repair) prefix can be consumed.
    execution_cache: Any = field(default=None, repr=False, compare=False)

    @property
    def selected_count(self) -> int:
        return len(self.selected_order)


@dataclass(frozen=True, slots=True)
class TargetMultiViewCandidateScore:
    candidate_index: int
    family_coverage_gains: tuple[float, ...]
    total_coverage_gain: float
    representative_gain: float
    sparse_diversity: float
    hard_obligation_gain: int


def validate_forward_problem(reference: Any, forward: Any, *, coverage_threshold: float, epsilon: float) -> None:
    """Fail closed when complete ``P_train`` cannot satisfy the method."""

    candidate_count = int(forward.candidate_count)
    if len(reference.frame_uids) != candidate_count or forward.frame_domain_digest != reference.frame_domain_digest:
        raise TrainingDataInputError("MVSEL2 candidate/UID identity is invalid.")
    if tuple(item.family_id for item in reference.families) != tuple(item.family_id for item in forward.families):
        raise TrainingDataInputError("MVSEL2 canonical family order/identity is invalid.")
    for family in forward.families:
        weights = np.asarray(reference.family(family.family_id).weights, dtype=np.float64)
        if weights.shape != (family.witness_count,):
            raise TrainingDataInputError("MVSEL2 family weight/index cardinality mismatch.")
        reachable = np.zeros(family.witness_count, dtype=np.bool_)
        reachable[np.asarray(family.candidate_witnesses, dtype=np.int64)] = True
        if float(np.sum(weights[reachable], dtype=np.float64)) < coverage_threshold - epsilon:
            raise TrainingDataInputError(
                f"MVSEL2 family {family.family_id} cannot reach the coverage threshold on exact P_train."
            )
    counts = np.bincount(np.asarray(forward.candidate_obligations, dtype=np.int64), minlength=len(forward.obligations))
    for index, obligation in enumerate(forward.obligations):
        if int(counts[index]) < int(obligation.minimum_selected_frames):
            raise TrainingDataInputError(f"MVSEL2 obligation {obligation.obligation_id} is infeasible on exact P_train.")


def build_forward_state(reference: Any, forward: Any, *, validate: bool = True) -> TargetMultiViewForwardState:
    if validate:
        validate_forward_problem(reference, forward, coverage_threshold=0.95, epsilon=1.0e-14)
    return TargetMultiViewForwardState(
        available=np.ones(forward.candidate_count, dtype=np.bool_),
        selected_order=[],
        family_states=[
            TargetMultiViewForwardFamilyState(
                family_id=family.family_id,
                weights=np.asarray(reference.family(family.family_id).weights, dtype=np.float64),
                multiplicity=np.zeros(family.witness_count, dtype=np.int32),
            )
            for family in forward.families
        ],
        obligation_counts=np.zeros(len(forward.obligations), dtype=np.int32),
        unsatisfied_required_obligation_count=len(forward.obligations),
        correlation_unit_counts=np.zeros(len(forward.correlation_unit_ids), dtype=np.int32),
    )


def phase_a_active(state: TargetMultiViewForwardState, policy: TargetMultiViewSelectorPolicy) -> bool:
    return state.unsatisfied_required_obligation_count > 0 or any(
        item.coverage_mass < policy.coverage_threshold - policy.gain_tie_tolerance for item in state.family_states
    )


def score_candidate(candidate_index: int, forward: Any, state: TargetMultiViewForwardState) -> TargetMultiViewCandidateScore:
    candidate = int(candidate_index)
    if not bool(state.available[candidate]):
        raise TrainingDataInputError("MVSEL2 cannot score an unavailable candidate.")
    coverage: list[float] = []
    representative = 0.0
    diversity: list[float] = []
    for family, family_state in zip(forward.families, state.family_states, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            coverage.append(0.0)
            continue
        multiplicity = family_state.multiplicity[witnesses]
        weights = family_state.weights[witnesses]
        coverage.append(float(np.sum(weights[multiplicity == 0], dtype=np.float64)))
        representative += float(np.sum(weights / (multiplicity.astype(np.float64) + 1.0), dtype=np.float64))
        diversity.append(float(np.mean(1.0 / (multiplicity.astype(np.float64) + 1.0), dtype=np.float64)))
    return TargetMultiViewCandidateScore(
        candidate_index=candidate,
        family_coverage_gains=tuple(coverage),
        total_coverage_gain=float(np.sum(coverage, dtype=np.float64)),
        representative_gain=representative,
        sparse_diversity=0.0 if not diversity else float(np.mean(diversity, dtype=np.float64)),
        hard_obligation_gain=hard_gain(candidate, forward, state),
    )


def filter_best_relative(candidates: tuple[int, ...], values: Mapping[int, float], epsilon: float) -> tuple[int, ...]:
    if len(candidates) <= 1:
        return candidates
    best = max(float(values[candidate]) for candidate in candidates)
    return tuple(candidate for candidate in candidates if float(values[candidate]) >= best - epsilon)


def hard_gain(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> int:
    gain = 0
    for index in native_row(forward.candidate_obligation_indices(candidate)):
        obligation = forward.obligations[int(index)]
        if int(state.obligation_counts[int(index)]) < int(obligation.minimum_selected_frames):
            gain += 1
    return gain


def family_coverage_gain(candidate: int, family_index: int, forward: Any, state: TargetMultiViewForwardState) -> tuple[float, int]:
    family_state = state.family_states[family_index]
    witnesses = native_row(forward.families[family_index].candidate_witness_indices(candidate))
    if witnesses.size == 0:
        return 0.0, 0
    uncovered = family_state.multiplicity[witnesses] == 0
    return float(np.sum(family_state.weights[witnesses][uncovered], dtype=np.float64)), int(witnesses.size)


def total_coverage_gain(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> tuple[tuple[float, ...], float, int]:
    gains: list[float] = []
    edges = 0
    for family_index in range(len(forward.families)):
        gain, family_edges = family_coverage_gain(candidate, family_index, forward, state)
        gains.append(gain)
        edges += family_edges
    return tuple(gains), float(np.sum(gains, dtype=np.float64)), edges


def representative_gain(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> tuple[float, int]:
    gain = 0.0
    edges = 0
    for family, family_state in zip(forward.families, state.family_states, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        gain += float(
            np.sum(
                family_state.weights[witnesses] / (family_state.multiplicity[witnesses].astype(np.float64) + 1.0),
                dtype=np.float64,
            )
        )
        edges += int(witnesses.size)
    return gain, edges


def sparse_diversity(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> tuple[float, int]:
    values: list[float] = []
    edges = 0
    for family, family_state in zip(forward.families, state.family_states, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        values.append(float(np.mean(1.0 / (family_state.multiplicity[witnesses].astype(np.float64) + 1.0), dtype=np.float64)))
        edges += int(witnesses.size)
    return (0.0 if not values else float(np.mean(values, dtype=np.float64))), edges


def bottleneck_family_index(state: TargetMultiViewForwardState, policy: TargetMultiViewSelectorPolicy) -> int:
    ratios = np.asarray([item.coverage_mass / float(policy.coverage_threshold) for item in state.family_states], dtype=np.float64)
    minimum = float(np.min(ratios))
    return int(np.flatnonzero(ratios <= minimum + policy.gain_tie_tolerance)[0])


@dataclass(frozen=True, slots=True)
class Choice:
    candidate_index: int
    bottleneck_family_id: str | None
    score: TargetMultiViewCandidateScore
    contender_width: int
    evaluation_edges: int
    rescoring_count: int = 0
    heap_entries: int = 0
    fallback_used: bool = False


def choose_phase_a_reference(
    reference: Any, forward: Any, state: TargetMultiViewForwardState, policy: TargetMultiViewSelectorPolicy
) -> Choice:
    """Exact sequential Phase-A reference (D2 section 8.2)."""

    epsilon = policy.gain_tie_tolerance
    available = tuple(int(value) for value in np.flatnonzero(state.available))
    if not available:
        raise TrainingDataInputError("MVSEL2 exhausted the candidate pool.")
    if not phase_a_active(state, policy):
        raise TrainingDataInputError("MVSEL2 Phase A is already complete.")
    hard = {candidate: hard_gain(candidate, forward, state) for candidate in available}
    candidates = available
    if state.unsatisfied_required_obligation_count > 0:
        maximum = max(hard.values())
        candidates = tuple(candidate for candidate in candidates if hard[candidate] == maximum)
    bottleneck = bottleneck_family_index(state, policy)
    edges = 0
    bottleneck_values: dict[int, float] = {}
    for candidate in candidates:
        bottleneck_values[candidate], count = family_coverage_gain(candidate, bottleneck, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, bottleneck_values, epsilon)
    totals: dict[int, float] = {}
    for candidate in candidates:
        _, totals[candidate], count = total_coverage_gain(candidate, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, totals, epsilon)
    minimum_unit = min(int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) for c in candidates)
    candidates = tuple(
        c for c in candidates if int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) == minimum_unit
    )
    representative: dict[int, float] = {}
    for candidate in candidates:
        representative[candidate], count = representative_gain(candidate, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, representative, epsilon)
    diversity: dict[int, float] = {}
    for candidate in candidates:
        diversity[candidate], count = sparse_diversity(candidate, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, diversity, epsilon)
    chosen = min(candidates, key=lambda candidate: reference.frame_uids[candidate])
    return Choice(
        candidate_index=chosen,
        bottleneck_family_id=forward.families[bottleneck].family_id,
        score=score_candidate(chosen, forward, state),
        contender_width=len(candidates),
        evaluation_edges=edges,
    )


def choose_phase_b_full_forward(
    reference: Any, forward: Any, state: TargetMultiViewForwardState, policy: TargetMultiViewSelectorPolicy
) -> Choice:
    """Bounded exact full-forward Phase-B oracle and emergency fallback."""

    epsilon = policy.gain_tie_tolerance
    candidates = tuple(int(value) for value in np.flatnonzero(state.available))
    edges = 0
    representative: dict[int, float] = {}
    for candidate in candidates:
        representative[candidate], count = representative_gain(candidate, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, representative, epsilon)
    minimum_unit = min(int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) for c in candidates)
    candidates = tuple(
        c for c in candidates if int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) == minimum_unit
    )
    diversity: dict[int, float] = {}
    for candidate in candidates:
        diversity[candidate], count = sparse_diversity(candidate, forward, state)
        edges += count
    candidates = filter_best_relative(candidates, diversity, epsilon)
    chosen = min(candidates, key=lambda candidate: reference.frame_uids[candidate])
    return Choice(
        candidate_index=chosen,
        bottleneck_family_id=None,
        score=score_candidate(chosen, forward, state),
        contender_width=len(candidates),
        evaluation_edges=edges,
        rescoring_count=len(representative),
        fallback_used=True,
    )


@dataclass(slots=True)
class LazyFrontier:
    """Certified Phase-B queue; reconstructible execution state only."""

    generation: int
    heap: list[tuple[float, int, int]]
    exact_scores: np.ndarray
    exact_generations: np.ndarray


def valid_heap_top(frontier: LazyFrontier, state: TargetMultiViewForwardState) -> tuple[float, int, int, int] | None:
    discarded = 0
    while frontier.heap:
        negative_upper, candidate, generation = frontier.heap[0]
        if not bool(state.available[candidate]):
            heapq.heappop(frontier.heap)
            discarded += 1
            continue
        return -float(negative_upper), int(candidate), int(generation), discarded
    return None


def certify_phase_b_contenders(
    reference: Any,
    forward: Any,
    state: TargetMultiViewForwardState,
    frontier: LazyFrontier,
    exact_candidates: set[int],
    best_exact: float,
    policy: TargetMultiViewSelectorPolicy,
    *,
    rescoring_count: int,
    evaluation_edges: int,
) -> Choice:
    """Apply balance/diversity/UID to the certified exact contender set."""

    epsilon = policy.gain_tie_tolerance
    contenders = tuple(sorted(c for c in exact_candidates if float(frontier.exact_scores[c]) >= best_exact - epsilon))
    if not contenders:
        raise TrainingDataInputError("MVSEL2 failed to certify a Phase-B contender.")
    minimum_unit = min(int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) for c in contenders)
    contenders = tuple(
        c for c in contenders if int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[c])]) == minimum_unit
    )
    diversity: dict[int, float] = {}
    for candidate in contenders:
        diversity[candidate], count = sparse_diversity(candidate, forward, state)
        evaluation_edges += count
    contenders = filter_best_relative(contenders, diversity, epsilon)
    chosen = min(contenders, key=lambda candidate: reference.frame_uids[candidate])
    for candidate in exact_candidates:
        conservative = float(np.nextafter(frontier.exact_scores[candidate], np.float64(np.inf)))
        heapq.heappush(frontier.heap, (-conservative, candidate, state.selected_count))
    family_gains, total, _ = total_coverage_gain(chosen, forward, state)
    return Choice(
        candidate_index=chosen,
        bottleneck_family_id=None,
        score=TargetMultiViewCandidateScore(
            candidate_index=chosen,
            family_coverage_gains=family_gains,
            total_coverage_gain=total,
            representative_gain=float(frontier.exact_scores[chosen]),
            sparse_diversity=diversity[chosen],
            hard_obligation_gain=0,
        ),
        contender_width=len(exact_candidates),
        evaluation_edges=evaluation_edges,
        rescoring_count=rescoring_count,
        heap_entries=len(frontier.heap),
    )


def record_refreshed_score(frontier: LazyFrontier, candidate: int, exact: float, generation: int) -> None:
    """Install one exact refresh; enforce monotone non-increasing gains."""

    old = float(frontier.exact_scores[candidate])
    if np.isfinite(old) and exact > old + MONOTONICITY_GUARD:
        raise TrainingDataInputError("MVSEL2 representative bound increased after selection.")
    frontier.exact_scores[candidate] = exact
    frontier.exact_generations[candidate] = generation
    conservative = float(np.nextafter(np.float64(exact), np.float64(np.inf)))
    if conservative + MONOTONICITY_GUARD < exact:
        raise TrainingDataInputError("MVSEL2 representative upper bound is not conservative.")
    heapq.heappush(frontier.heap, (-conservative, candidate, generation))


def build_lazy_frontier_reference(forward: Any, state: TargetMultiViewForwardState) -> LazyFrontier:
    """Exact all-candidate Phase-B rebase (reference form)."""

    generation = state.selected_count
    exact_scores = np.full(forward.candidate_count, np.nan, dtype=np.float64)
    exact_generations = np.full(forward.candidate_count, -1, dtype=np.int64)
    heap: list[tuple[float, int, int]] = []
    for candidate in np.flatnonzero(state.available):
        candidate = int(candidate)
        score, _ = representative_gain(candidate, forward, state)
        exact_scores[candidate] = score
        exact_generations[candidate] = generation
        heap.append((-float(np.nextafter(np.float64(score), np.float64(np.inf))), candidate, generation))
    heapq.heapify(heap)
    return LazyFrontier(generation, heap, exact_scores, exact_generations)


def choose_phase_b_lazy_reference(
    reference: Any, forward: Any, state: TargetMultiViewForwardState, frontier: LazyFrontier, policy: TargetMultiViewSelectorPolicy
) -> Choice:
    """Certified lazy Phase B with one exact refresh at a time (reference form)."""

    generation = state.selected_count
    frontier.generation = generation
    exact_candidates: set[int] = set()
    best_exact = -math.inf
    rescoring = 0
    edges = 0
    while True:
        top = valid_heap_top(frontier, state)
        if top is None:
            if exact_candidates:
                break
            raise TrainingDataInputError("MVSEL2 lazy frontier is empty.")
        upper, candidate, entry_generation, _ = top
        if best_exact > -math.inf and upper < best_exact - policy.gain_tie_tolerance:
            break
        heapq.heappop(frontier.heap)
        if entry_generation != generation:
            exact, count = representative_gain(candidate, forward, state)
            record_refreshed_score(frontier, candidate, exact, generation)
            rescoring += 1
            edges += count
            continue
        exact_candidates.add(candidate)
        best_exact = max(best_exact, float(frontier.exact_scores[candidate]))
    return certify_phase_b_contenders(
        reference, forward, state, frontier, exact_candidates, best_exact, policy,
        rescoring_count=rescoring, evaluation_edges=edges,
    )


def select_candidate(candidate_index: int, forward: Any, state: TargetMultiViewForwardState, *, score: TargetMultiViewCandidateScore | None = None) -> None:
    """Select one candidate by mutating only its forward incidence rows."""

    candidate = int(candidate_index)
    if not bool(state.available[candidate]):
        raise TrainingDataInputError("MVSEL2 candidate is already selected.")
    if score is None:
        score = score_candidate(candidate, forward, state)
    elif score.candidate_index != candidate:
        raise TrainingDataInputError("MVSEL2 supplied score belongs to another candidate.")
    for family_index, (family, family_state) in enumerate(zip(forward.families, state.family_states, strict=True)):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        family_state.coverage_mass += score.family_coverage_gains[family_index]
        family_state.multiplicity[witnesses] += 1
    for index in native_row(forward.candidate_obligation_indices(candidate)):
        index = int(index)
        before = int(state.obligation_counts[index])
        state.obligation_counts[index] = before + 1
        if before < forward.obligations[index].minimum_selected_frames <= before + 1:
            state.unsatisfied_required_obligation_count -= 1
    state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[candidate])] += 1
    state.representative_utility += score.representative_gain
    state.available[candidate] = False
    state.selected_order.append(candidate)


def deselect_candidate(candidate_index: int, forward: Any, state: TargetMultiViewForwardState) -> None:
    """Deselect one candidate by reversing only its forward incidence rows."""

    candidate = int(candidate_index)
    if bool(state.available[candidate]):
        raise TrainingDataInputError("MVSEL2 candidate is not selected.")
    representative_decrement = 0.0
    for family, family_state in zip(forward.families, state.family_states, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses]
        if np.any(multiplicity <= 0):
            raise TrainingDataInputError("MVSEL2 witness multiplicity underflow.")
        weights = family_state.weights[witnesses]
        representative_decrement += float(np.sum(weights / multiplicity.astype(np.float64), dtype=np.float64))
        family_state.coverage_mass -= float(np.sum(weights[multiplicity == 1], dtype=np.float64))
        if abs(family_state.coverage_mass) <= MONOTONICITY_GUARD:
            family_state.coverage_mass = 0.0
        if family_state.coverage_mass < -MONOTONICITY_GUARD:
            raise TrainingDataInputError("MVSEL2 coverage mass became negative.")
        family_state.multiplicity[witnesses] -= 1
    for index in native_row(forward.candidate_obligation_indices(candidate)):
        index = int(index)
        before = int(state.obligation_counts[index])
        if before <= 0:
            raise TrainingDataInputError("MVSEL2 obligation count underflow.")
        state.obligation_counts[index] = before - 1
        if before >= forward.obligations[index].minimum_selected_frames > before - 1:
            state.unsatisfied_required_obligation_count += 1
    unit = int(forward.candidate_correlation_unit_codes[candidate])
    if int(state.correlation_unit_counts[unit]) <= 0:
        raise TrainingDataInputError("MVSEL2 correlation count underflow.")
    state.correlation_unit_counts[unit] -= 1
    state.representative_utility -= representative_decrement
    if abs(state.representative_utility) <= MONOTONICITY_GUARD:
        state.representative_utility = 0.0
    if state.representative_utility < -MONOTONICITY_GUARD:
        raise TrainingDataInputError("MVSEL2 representative utility became negative.")
    state.available[candidate] = True
    state.selected_order.remove(candidate)


def reconstruct_forward_state(reference: Any, forward: Any, prefix: Sequence[int]) -> TargetMultiViewForwardState:
    """Cold primitive replay of an exact (repaired) prefix (D2 section 9.5)."""

    state = build_forward_state(reference, forward, validate=False)
    for candidate in prefix:
        select_candidate(int(candidate), forward, state)
    return state


def entry_from_choice(reference: Any, forward: Any, choice: Choice, *, rank: int, phase_a: bool) -> TargetMultiViewSelectionEntry:
    score = choice.score
    bottleneck_gain = 0.0
    if choice.bottleneck_family_id is not None:
        position = next(i for i, family in enumerate(forward.families) if family.family_id == choice.bottleneck_family_id)
        bottleneck_gain = float(score.family_coverage_gains[position])
    return TargetMultiViewSelectionEntry(
        rank=int(rank),
        frame_uid=reference.frame_uids[score.candidate_index],
        phase=PHASE_HARD_COVERAGE if phase_a else PHASE_REPRESENTATIVE_FILL,
        primary_reason=(
            "hard_obligation_gain" if score.hard_obligation_gain > 0
            else "worst_view_coverage" if phase_a else "density_aware_representative_fill"
        ),
        bottleneck_family_id=choice.bottleneck_family_id,
        hard_obligation_gain=score.hard_obligation_gain,
        bottleneck_coverage_gain=bottleneck_gain,
        total_coverage_gain=score.total_coverage_gain,
        representative_gain=score.representative_gain,
        normalized_diversity=score.sparse_diversity,
        correlation_unit_code=int(forward.candidate_correlation_unit_codes[score.candidate_index]),
    )


def unsatisfied_obligation_ids(forward: Any, state: TargetMultiViewForwardState) -> tuple[str, ...]:
    return tuple(
        sorted(
            item.obligation_id
            for index, item in enumerate(forward.obligations)
            if int(state.obligation_counts[index]) < int(item.minimum_selected_frames)
        )
    )


def materialized_rung(
    reference: Any, forward: Any, state: TargetMultiViewForwardState, entries: Sequence[TargetMultiViewSelectionEntry], *, target_size: int, previous_size: int
) -> TargetMultiViewSelectionRung:
    shell = entries[previous_size:target_size]
    return TargetMultiViewSelectionRung(
        target_size=int(target_size),
        frame_uids_digest=prefix_digest([entry.frame_uid for entry in entries[:target_size]]),
        family_coverage=tuple((item.family_id, min(1.0, max(0.0, item.coverage_mass))) for item in state.family_states),
        unsatisfied_obligation_ids=unsatisfied_obligation_ids(forward, state),
        phase_at_boundary=entries[target_size - 1].phase,
        shell_coverage_gain=float(np.sum([item.total_coverage_gain for item in shell], dtype=np.float64)),
        shell_representative_gain=float(np.sum([item.representative_gain for item in shell], dtype=np.float64)),
    )


__all__ = [
    "Choice",
    "LazyFrontier",
    "MVSEL2_VERSION",
    "PHASE_HARD_COVERAGE",
    "PHASE_REPRESENTATIVE_FILL",
    "TargetMultiViewCandidateScore",
    "TargetMultiViewForwardFamilyState",
    "TargetMultiViewForwardState",
    "TargetMultiViewSelectionEntry",
    "TargetMultiViewSelectionPlan",
    "TargetMultiViewSelectionRung",
    "TargetMultiViewSelectorPolicy",
    "bottleneck_family_index",
    "build_forward_state",
    "build_lazy_frontier_reference",
    "choose_phase_a_reference",
    "choose_phase_b_full_forward",
    "choose_phase_b_lazy_reference",
    "deselect_candidate",
    "entry_from_choice",
    "hard_gain",
    "materialized_rung",
    "phase_a_active",
    "prefix_digest",
    "reconstruct_forward_state",
    "representative_gain",
    "score_candidate",
    "select_candidate",
    "sparse_diversity",
    "total_coverage_gain",
    "unsatisfied_obligation_ids",
    "validate_forward_problem",
]
