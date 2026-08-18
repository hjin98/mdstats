"""MVSEL2 exact forward-state scoring and mutation primitives.

The v2 kernel deliberately owns no witness-to-candidate adjacency and no
complete candidate marginal arrays.  Candidate scores are evaluated on demand
from forward CSR rows and current witness multiplicity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
import mmap
import time
from typing import Any, Iterable

import numpy as np

from ._common import TrainingDataInputError, digest
from .target_multi_view_selector import TargetMultiViewSelectionEntry, TargetMultiViewSelectionRung
from .progress_timing import format_progress_fraction, format_progress_time
from .target_coverage_sparse_forward_view import TargetCoverageSparseForwardDomainView


TARGET_MULTI_VIEW_SELECTOR_V2_VERSION = "mdstats.target-data2c-mvsel2.forward-lazy.2026-08.v1"
TARGET_MULTI_VIEW_SELECTION_PLAN_V2_SCHEMA = "mdstats.target-multi-view-selection-plan.v2"


def _drop_file_backed_pages_v2(array: np.ndarray) -> None:
    """Release fully scanned mmap pages without changing array identity."""

    root: Any = array
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    mapped = getattr(root, "_mmap", None)
    advice = getattr(mmap, "MADV_DONTNEED", None)
    if mapped is not None and advice is not None and hasattr(mapped, "madvise"):
        try:
            mapped.madvise(advice)
        except (BufferError, OSError, ValueError):
            pass


def release_target_multi_view_forward_pages_v2(
    forward_domain: TargetCoverageSparseForwardDomainView,
) -> None:
    """Best-effort release of scanned forward CSR file pages."""

    for family in forward_domain.families:
        _drop_file_backed_pages_v2(np.asarray(family.candidate_offsets))
        _drop_file_backed_pages_v2(np.asarray(family.candidate_witnesses))


@dataclass(frozen=True, slots=True)
class TargetMultiViewCandidateScoreV2:
    candidate_index: int
    family_coverage_gains: tuple[float, ...]
    total_coverage_gain: float
    representative_gain: float
    sparse_diversity: float
    hard_obligation_gain: int


@dataclass(frozen=True, slots=True)
class TargetMultiViewPhaseATelemetryV2:
    eligible_count: int
    bottleneck_contender_count: int
    total_coverage_contender_count: int
    correlation_contender_count: int
    representative_contender_count: int
    final_contender_count: int
    bottleneck_evaluation_edges: int
    total_coverage_evaluation_edges: int
    representative_evaluation_edges: int
    diversity_evaluation_edges: int

    @property
    def candidate_evaluation_forward_edges(self) -> int:
        return (
            self.bottleneck_evaluation_edges
            + self.total_coverage_evaluation_edges
            + self.representative_evaluation_edges
            + self.diversity_evaluation_edges
        )


@dataclass(frozen=True, slots=True)
class TargetMultiViewPhaseAChoiceV2:
    candidate_index: int
    bottleneck_family_id: str
    score: TargetMultiViewCandidateScoreV2
    telemetry: TargetMultiViewPhaseATelemetryV2


@dataclass(frozen=True, slots=True)
class TargetMultiViewPhaseBTelemetryV2:
    certified_frontier_width: int
    rescoring_count: int
    representative_evaluation_edges: int
    diversity_evaluation_edges: int
    stale_entries_discarded: int
    heap_entries: int
    fallback_used: bool = False


@dataclass(frozen=True, slots=True)
class TargetMultiViewPhaseBChoiceV2:
    candidate_index: int
    score: TargetMultiViewCandidateScoreV2
    telemetry: TargetMultiViewPhaseBTelemetryV2


@dataclass(slots=True)
class TargetMultiViewLazyFrontierV2:
    """One global certified Phase-B queue with reconstructible heap state."""

    generation: int
    heap: list[tuple[float, int, int]]
    exact_scores: np.ndarray
    exact_generations: np.ndarray
    rebase_count: int = 1


def build_target_multi_view_lazy_frontier_v2(
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> TargetMultiViewLazyFrontierV2:
    """Run the deterministic exact Phase-B rebase over all available candidates."""

    generation = state.selected_count
    candidate_count = forward_domain.candidate_count
    exact_scores = np.full(candidate_count, np.nan, dtype=np.float64)
    exact_generations = np.full(candidate_count, -1, dtype=np.int64)
    heap: list[tuple[float, int, int]] = []
    for candidate in np.flatnonzero(state.available):
        candidate = int(candidate)
        score, _ = _representative_gain_v2(candidate, forward_domain, state)
        exact_scores[candidate] = score
        exact_generations[candidate] = generation
        upper = float(np.nextafter(np.float64(score), np.float64(np.inf)))
        heap.append((-upper, candidate, generation))
    heapq.heapify(heap)
    release_target_multi_view_forward_pages_v2(forward_domain)
    return TargetMultiViewLazyFrontierV2(
        generation=generation,
        heap=heap,
        exact_scores=exact_scores,
        exact_generations=exact_generations,
    )


def _valid_heap_top_v2(
    frontier: TargetMultiViewLazyFrontierV2,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int, int, int] | None:
    discarded = 0
    while frontier.heap:
        negative_upper, candidate, entry_generation = frontier.heap[0]
        if not bool(state.available[candidate]):
            heapq.heappop(frontier.heap)
            discarded += 1
            continue
        return -float(negative_upper), int(candidate), int(entry_generation), discarded
    return None


def choose_target_multi_view_phase_b_full_forward_v2(
    reference_domain: Any,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
    *,
    epsilon: float = 1.0e-14,
) -> TargetMultiViewPhaseBChoiceV2:
    """Bounded exact full-forward Phase-B oracle and emergency fallback."""

    candidates = tuple(int(value) for value in np.flatnonzero(state.available))
    representative: dict[int, float] = {}
    representative_edges = 0
    for candidate in candidates:
        representative[candidate], edges = _representative_gain_v2(
            candidate, forward_domain, state
        )
        representative_edges += edges
    candidates = _filter_best_relative_v2(candidates, representative, float(epsilon))
    minimum_unit_count = min(
        int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        for candidate in candidates
    )
    candidates = tuple(
        candidate for candidate in candidates
        if int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        == minimum_unit_count
    )
    diversity: dict[int, float] = {}
    diversity_edges = 0
    for candidate in candidates:
        diversity[candidate], edges = _sparse_diversity_v2(
            candidate, forward_domain, state
        )
        diversity_edges += edges
    candidates = _filter_best_relative_v2(candidates, diversity, float(epsilon))
    chosen = min(candidates, key=lambda candidate: reference_domain.frame_uids[candidate])
    family_gains, total_coverage, _ = _total_coverage_gain_v2(
        chosen, forward_domain, state
    )
    return TargetMultiViewPhaseBChoiceV2(
        candidate_index=chosen,
        score=TargetMultiViewCandidateScoreV2(
            candidate_index=chosen,
            family_coverage_gains=family_gains,
            total_coverage_gain=total_coverage,
            representative_gain=representative[chosen],
            sparse_diversity=diversity[chosen],
            hard_obligation_gain=0,
        ),
        telemetry=TargetMultiViewPhaseBTelemetryV2(
            certified_frontier_width=len(candidates),
            rescoring_count=len(representative),
            representative_evaluation_edges=representative_edges,
            diversity_evaluation_edges=diversity_edges,
            stale_entries_discarded=0,
            heap_entries=0,
            fallback_used=True,
        ),
    )


def choose_target_multi_view_phase_b_candidate_v2(
    reference_domain: Any,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
    frontier: TargetMultiViewLazyFrontierV2,
    *,
    epsilon: float = 1.0e-14,
) -> TargetMultiViewPhaseBChoiceV2:
    """Certify the complete exact representative contender set lazily."""

    generation = state.selected_count
    frontier.generation = generation
    exact_candidates: set[int] = set()
    best_exact = -math.inf
    rescoring_count = 0
    representative_edges = 0
    stale_discarded = 0

    while True:
        top = _valid_heap_top_v2(frontier, state)
        if top is None:
            if exact_candidates:
                break
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 lazy frontier is empty.")
        upper, candidate, entry_generation, discarded = top
        stale_discarded += discarded
        if best_exact > -math.inf and upper < best_exact - float(epsilon):
            break
        heapq.heappop(frontier.heap)
        if entry_generation != generation:
            exact, edges = _representative_gain_v2(candidate, forward_domain, state)
            old_exact = float(frontier.exact_scores[candidate])
            if np.isfinite(old_exact) and exact > old_exact + 5.0e-13:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 representative bound increased after selection."
                )
            frontier.exact_scores[candidate] = exact
            frontier.exact_generations[candidate] = generation
            conservative = float(np.nextafter(np.float64(exact), np.float64(np.inf)))
            if conservative + 5.0e-13 < exact:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 representative upper bound is not conservative."
                )
            heapq.heappush(frontier.heap, (-conservative, candidate, generation))
            rescoring_count += 1
            representative_edges += edges
            continue
        exact = float(frontier.exact_scores[candidate])
        exact_candidates.add(candidate)
        best_exact = max(best_exact, exact)

    contenders = tuple(
        sorted(
            candidate for candidate in exact_candidates
            if float(frontier.exact_scores[candidate]) >= best_exact - float(epsilon)
        )
    )
    if not contenders:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 failed to certify a Phase-B contender.")
    minimum_unit_count = min(
        int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        for candidate in contenders
    )
    contenders = tuple(
        candidate for candidate in contenders
        if int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        == minimum_unit_count
    )
    diversity: dict[int, float] = {}
    diversity_edges = 0
    for candidate in contenders:
        diversity[candidate], edges = _sparse_diversity_v2(candidate, forward_domain, state)
        diversity_edges += edges
    contenders = _filter_best_relative_v2(contenders, diversity, float(epsilon))
    chosen = min(contenders, key=lambda candidate: reference_domain.frame_uids[candidate])

    # Reinsert exact candidates so their conservative bounds remain available
    # when this choice is inspected or rebuilt before mutation.
    for candidate in exact_candidates:
        conservative = float(
            np.nextafter(frontier.exact_scores[candidate], np.float64(np.inf))
        )
        heapq.heappush(frontier.heap, (-conservative, candidate, generation))
    family_gains, total_coverage, _ = _total_coverage_gain_v2(
        chosen, forward_domain, state
    )
    return TargetMultiViewPhaseBChoiceV2(
        candidate_index=chosen,
        score=TargetMultiViewCandidateScoreV2(
            candidate_index=chosen,
            family_coverage_gains=family_gains,
            total_coverage_gain=total_coverage,
            representative_gain=float(frontier.exact_scores[chosen]),
            sparse_diversity=diversity[chosen],
            hard_obligation_gain=0,
        ),
        telemetry=TargetMultiViewPhaseBTelemetryV2(
            certified_frontier_width=len(exact_candidates),
            rescoring_count=rescoring_count,
            representative_evaluation_edges=representative_edges,
            diversity_evaluation_edges=diversity_edges,
            stale_entries_discarded=stale_discarded,
            heap_entries=len(frontier.heap),
        ),
    )


@dataclass(slots=True)
class TargetMultiViewForwardFamilyStateV2:
    family_id: str
    weights: np.ndarray
    multiplicity: np.ndarray
    coverage_mass: float = 0.0


@dataclass(slots=True)
class TargetMultiViewForwardStateV2:
    available: np.ndarray
    selected_order: list[int]
    family_states: list[TargetMultiViewForwardFamilyStateV2]
    obligation_counts: np.ndarray
    unsatisfied_required_obligation_count: int
    correlation_unit_counts: np.ndarray
    representative_utility: float = 0.0

    @property
    def selected_count(self) -> int:
        return len(self.selected_order)


def _validate_forward_problem(
    reference_domain: Any,
    forward_domain: TargetCoverageSparseForwardDomainView,
    *,
    coverage_threshold: float,
    epsilon: float,
    requested_cardinality: int | None,
) -> None:
    candidate_count = int(forward_domain.candidate_count)
    frame_uids = tuple(str(value) for value in reference_domain.frame_uids)
    if len(frame_uids) != candidate_count or len(set(frame_uids)) != candidate_count:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 candidate/UID identity is invalid.")
    if requested_cardinality is not None and not 1 <= int(requested_cardinality) <= candidate_count:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 requested cardinality exceeds the candidate pool.")
    if not math.isfinite(coverage_threshold) or not 0.0 < coverage_threshold <= 1.0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 coverage threshold is invalid.")
    if not math.isfinite(epsilon) or epsilon <= 0.0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 gain tolerance is invalid.")
    reference_family_ids = tuple(sorted(str(item.family_id) for item in reference_domain.families))
    forward_family_ids = tuple(item.family_id for item in forward_domain.families)
    if reference_family_ids != forward_family_ids:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 canonical family order/identity is invalid.")

    for forward_family in forward_domain.families:
        reference_family = reference_domain.family(forward_family.family_id)
        weights = np.asarray(reference_family.weights, dtype=np.float64)
        if weights.shape != (forward_family.witness_count,):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 family weight/index cardinality mismatch.")
        if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 witness weights must be finite and nonnegative.")
        reachable = np.zeros(forward_family.witness_count, dtype=np.bool_)
        for candidate in range(candidate_count):
            row = np.asarray(forward_family.candidate_witness_indices(candidate), dtype=np.int64)
            if row.size:
                reachable[row] = True
        capacity = float(np.sum(weights[reachable], dtype=np.float64))
        _drop_file_backed_pages_v2(np.asarray(forward_family.candidate_witnesses))
        if capacity < coverage_threshold - epsilon:
            raise TrainingDataInputError(
                f"TARGET-DATA2C-MVSEL2 family {forward_family.family_id} cannot reach the coverage threshold."
            )

    obligation_capacity = np.zeros(len(forward_domain.obligations), dtype=np.int64)
    for candidate in range(candidate_count):
        obligation_capacity[np.asarray(
            forward_domain.candidate_obligation_indices(candidate), dtype=np.int64
        )] += 1
    for obligation_index, obligation in enumerate(forward_domain.obligations):
        if obligation.required and int(obligation_capacity[obligation_index]) < int(obligation.minimum_selected_frames):
            raise TrainingDataInputError(
                f"TARGET-DATA2C-MVSEL2 required obligation {obligation.obligation_id} is infeasible."
            )


def build_target_multi_view_forward_state_v2(
    reference_domain: Any,
    forward_domain: TargetCoverageSparseForwardDomainView,
    *,
    coverage_threshold: float = 0.95,
    epsilon: float = 1.0e-14,
    requested_cardinality: int | None = None,
) -> TargetMultiViewForwardStateV2:
    """Validate one domain and allocate exact compact forward mutable state."""

    _validate_forward_problem(
        reference_domain,
        forward_domain,
        coverage_threshold=float(coverage_threshold),
        epsilon=float(epsilon),
        requested_cardinality=requested_cardinality,
    )
    family_states = [
        TargetMultiViewForwardFamilyStateV2(
            family_id=forward_family.family_id,
            weights=np.asarray(
                reference_domain.family(forward_family.family_id).weights,
                dtype=np.float64,
            ),
            multiplicity=np.zeros(forward_family.witness_count, dtype=np.int32),
        )
        for forward_family in forward_domain.families
    ]
    required = np.asarray(
        [bool(obligation.required) for obligation in forward_domain.obligations],
        dtype=np.bool_,
    )
    return TargetMultiViewForwardStateV2(
        available=np.ones(forward_domain.candidate_count, dtype=np.bool_),
        selected_order=[],
        family_states=family_states,
        obligation_counts=np.zeros(len(forward_domain.obligations), dtype=np.int32),
        unsatisfied_required_obligation_count=int(np.count_nonzero(required)),
        correlation_unit_counts=np.zeros(len(forward_domain.correlation_unit_ids), dtype=np.int32),
    )


def score_target_multi_view_candidate_v2(
    candidate_index: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> TargetMultiViewCandidateScoreV2:
    """Compute one candidate's exact scores directly from forward rows."""

    candidate = int(candidate_index)
    if candidate < 0 or candidate >= forward_domain.candidate_count:
        raise IndexError(candidate)
    if not bool(state.available[candidate]):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 cannot score an unavailable candidate.")
    family_coverage: list[float] = []
    representative = 0.0
    diversity_by_family: list[float] = []
    for forward_family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = np.asarray(
            forward_family.candidate_witness_indices(candidate), dtype=np.int64
        )
        if witnesses.size == 0:
            family_coverage.append(0.0)
            continue
        multiplicity = family_state.multiplicity[witnesses]
        weights = family_state.weights[witnesses]
        family_coverage.append(
            float(np.sum(weights[multiplicity == 0], dtype=np.float64))
        )
        representative += float(
            np.sum(weights / (multiplicity.astype(np.float64) + 1.0), dtype=np.float64)
        )
        diversity_by_family.append(
            float(
                np.mean(
                    1.0 / (multiplicity.astype(np.float64) + 1.0),
                    dtype=np.float64,
                )
            )
        )
    hard_gain = 0
    for obligation_index in np.asarray(
        forward_domain.candidate_obligation_indices(candidate), dtype=np.int64
    ):
        obligation = forward_domain.obligations[int(obligation_index)]
        if (
            obligation.required
            and int(state.obligation_counts[obligation_index])
            < int(obligation.minimum_selected_frames)
        ):
            hard_gain += 1
    return TargetMultiViewCandidateScoreV2(
        candidate_index=candidate,
        family_coverage_gains=tuple(family_coverage),
        total_coverage_gain=float(np.sum(family_coverage, dtype=np.float64)),
        representative_gain=representative,
        sparse_diversity=(
            0.0
            if not diversity_by_family
            else float(np.mean(diversity_by_family, dtype=np.float64))
        ),
        hard_obligation_gain=hard_gain,
    )


def _filter_best_relative_v2(
    candidates: tuple[int, ...], values: dict[int, float], epsilon: float
) -> tuple[int, ...]:
    if len(candidates) <= 1:
        return candidates
    best = max(float(values[candidate]) for candidate in candidates)
    return tuple(
        candidate
        for candidate in candidates
        if float(values[candidate]) >= best - epsilon
    )


def _hard_gain_v2(
    candidate: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> int:
    gain = 0
    for obligation_index in np.asarray(
        forward_domain.candidate_obligation_indices(candidate), dtype=np.int64
    ):
        obligation = forward_domain.obligations[int(obligation_index)]
        if (
            obligation.required
            and int(state.obligation_counts[obligation_index])
            < int(obligation.minimum_selected_frames)
        ):
            gain += 1
    return gain


def _family_coverage_gain_v2(
    candidate: int,
    family_index: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    family = forward_domain.families[family_index]
    family_state = state.family_states[family_index]
    witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
    if witnesses.size == 0:
        return 0.0, 0
    uncovered = family_state.multiplicity[witnesses] == 0
    return (
        float(np.sum(family_state.weights[witnesses][uncovered], dtype=np.float64)),
        int(witnesses.size),
    )


def _total_coverage_gain_v2(
    candidate: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> tuple[tuple[float, ...], float, int]:
    gains: list[float] = []
    edges = 0
    for family_index in range(len(forward_domain.families)):
        gain, family_edges = _family_coverage_gain_v2(
            candidate, family_index, forward_domain, state
        )
        gains.append(gain)
        edges += family_edges
    return tuple(gains), float(np.sum(gains, dtype=np.float64)), edges


def _representative_gain_v2(
    candidate: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    gain = 0.0
    edges = 0
    for family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        gain += float(
            np.sum(
                family_state.weights[witnesses]
                / (family_state.multiplicity[witnesses].astype(np.float64) + 1.0),
                dtype=np.float64,
            )
        )
        edges += int(witnesses.size)
    return gain, edges


def _sparse_diversity_v2(
    candidate: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    values: list[float] = []
    edges = 0
    for family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        values.append(
            float(
                np.mean(
                    1.0
                    / (
                        family_state.multiplicity[witnesses].astype(np.float64)
                        + 1.0
                    ),
                    dtype=np.float64,
                )
            )
        )
        edges += int(witnesses.size)
    return (0.0 if not values else float(np.mean(values, dtype=np.float64))), edges


def choose_target_multi_view_phase_a_candidate_v2(
    reference_domain: Any,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
    *,
    coverage_threshold: float = 0.95,
    epsilon: float = 1.0e-14,
    batch_size: int = 256,
    workers: int = 1,
) -> TargetMultiViewPhaseAChoiceV2:
    """Execute the frozen staged exact Phase-A contender pipeline."""

    epsilon = float(epsilon)
    if int(batch_size) < 1 or int(workers) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 batch/worker settings must be positive.")
    available = tuple(int(value) for value in np.flatnonzero(state.available))
    if not available:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 exhausted the candidate pool.")
    hard_pending = int(state.unsatisfied_required_obligation_count) > 0
    coverage_pending = any(
        family_state.coverage_mass < float(coverage_threshold) - epsilon
        for family_state in state.family_states
    )
    if not hard_pending and not coverage_pending:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 Phase A is already complete.")

    hard_gains = {candidate: _hard_gain_v2(candidate, forward_domain, state) for candidate in available}
    candidates = available
    if hard_pending:
        maximum = max(hard_gains.values())
        candidates = tuple(
            candidate for candidate in candidates if hard_gains[candidate] == maximum
        )
    eligible_count = len(candidates)

    ratios = np.asarray(
        [family_state.coverage_mass / float(coverage_threshold) for family_state in state.family_states],
        dtype=np.float64,
    )
    minimum = float(np.min(ratios))
    bottleneck_index = int(np.flatnonzero(ratios <= minimum + epsilon)[0])
    bottleneck_values: dict[int, float] = {}
    bottleneck_edges = 0
    for candidate in candidates:
        value, edges = _family_coverage_gain_v2(
            candidate, bottleneck_index, forward_domain, state
        )
        bottleneck_values[candidate] = value
        bottleneck_edges += edges
    candidates = _filter_best_relative_v2(candidates, bottleneck_values, epsilon)
    bottleneck_width = len(candidates)

    family_gains: dict[int, tuple[float, ...]] = {}
    total_coverage_values: dict[int, float] = {}
    total_coverage_edges = 0
    for candidate in candidates:
        gains, total, edges = _total_coverage_gain_v2(candidate, forward_domain, state)
        family_gains[candidate] = gains
        total_coverage_values[candidate] = total
        total_coverage_edges += edges
    candidates = _filter_best_relative_v2(
        candidates, total_coverage_values, epsilon
    )
    total_coverage_width = len(candidates)

    minimum_unit_count = min(
        int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        for candidate in candidates
    )
    candidates = tuple(
        candidate
        for candidate in candidates
        if int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])])
        == minimum_unit_count
    )
    correlation_width = len(candidates)

    representative_values: dict[int, float] = {}
    representative_edges = 0
    for candidate in candidates:
        value, edges = _representative_gain_v2(candidate, forward_domain, state)
        representative_values[candidate] = value
        representative_edges += edges
    candidates = _filter_best_relative_v2(
        candidates, representative_values, epsilon
    )
    representative_width = len(candidates)

    diversity_values: dict[int, float] = {}
    diversity_edges = 0
    if len(candidates) > 1:
        for candidate in candidates:
            value, edges = _sparse_diversity_v2(candidate, forward_domain, state)
            diversity_values[candidate] = value
            diversity_edges += edges
        candidates = _filter_best_relative_v2(candidates, diversity_values, epsilon)
    else:
        candidate = candidates[0]
        value, edges = _sparse_diversity_v2(candidate, forward_domain, state)
        diversity_values[candidate] = value
        diversity_edges += edges

    chosen = min(candidates, key=lambda candidate: reference_domain.frame_uids[candidate])
    if chosen not in family_gains:
        gains, total, edges = _total_coverage_gain_v2(chosen, forward_domain, state)
        family_gains[chosen] = gains
        total_coverage_values[chosen] = total
        total_coverage_edges += edges
    if chosen not in representative_values:
        value, edges = _representative_gain_v2(chosen, forward_domain, state)
        representative_values[chosen] = value
        representative_edges += edges
    score = TargetMultiViewCandidateScoreV2(
        candidate_index=chosen,
        family_coverage_gains=family_gains[chosen],
        total_coverage_gain=total_coverage_values[chosen],
        representative_gain=representative_values[chosen],
        sparse_diversity=diversity_values[chosen],
        hard_obligation_gain=hard_gains[chosen],
    )
    return TargetMultiViewPhaseAChoiceV2(
        candidate_index=chosen,
        bottleneck_family_id=forward_domain.families[bottleneck_index].family_id,
        score=score,
        telemetry=TargetMultiViewPhaseATelemetryV2(
            eligible_count=eligible_count,
            bottleneck_contender_count=bottleneck_width,
            total_coverage_contender_count=total_coverage_width,
            correlation_contender_count=correlation_width,
            representative_contender_count=representative_width,
            final_contender_count=len(candidates),
            bottleneck_evaluation_edges=bottleneck_edges,
            total_coverage_evaluation_edges=total_coverage_edges,
            representative_evaluation_edges=representative_edges,
            diversity_evaluation_edges=diversity_edges,
        ),
    )


def score_target_multi_view_candidates_v2(
    candidates: Iterable[int],
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
    *,
    batch_size: int = 256,
    workers: int = 1,
) -> tuple[TargetMultiViewCandidateScoreV2, ...]:
    """Score candidates in canonical order with execution-only batching.

    G1 keeps one canonical scalar authority.  ``workers`` is accepted as an
    execution setting but does not alter numerical reduction or result order.
    """

    if int(batch_size) < 1 or int(workers) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 batch/worker settings must be positive.")
    ordered = tuple(sorted(int(candidate) for candidate in candidates))
    if len(set(ordered)) != len(ordered):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 candidate score request contains duplicates.")
    result: list[TargetMultiViewCandidateScoreV2] = []
    for start in range(0, len(ordered), int(batch_size)):
        for candidate in ordered[start : start + int(batch_size)]:
            result.append(
                score_target_multi_view_candidate_v2(candidate, forward_domain, state)
            )
    return tuple(result)


def select_target_multi_view_candidate_v2(
    candidate_index: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
    *,
    score: TargetMultiViewCandidateScoreV2 | None = None,
) -> None:
    """Select one candidate by mutating only its forward incidence rows."""

    candidate = int(candidate_index)
    if candidate < 0 or candidate >= forward_domain.candidate_count:
        raise IndexError(candidate)
    if not bool(state.available[candidate]):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 candidate is already selected.")
    if score is None:
        score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
    elif score.candidate_index != candidate:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 supplied score belongs to another candidate.")
    for family_index, (forward_family, family_state) in enumerate(
        zip(forward_domain.families, state.family_states, strict=True)
    ):
        witnesses = np.asarray(
            forward_family.candidate_witness_indices(candidate), dtype=np.int64
        )
        if witnesses.size == 0:
            continue
        family_state.coverage_mass += score.family_coverage_gains[family_index]
        family_state.multiplicity[witnesses] += 1
    for obligation_index in np.asarray(
        forward_domain.candidate_obligation_indices(candidate), dtype=np.int64
    ):
        obligation = forward_domain.obligations[int(obligation_index)]
        before = int(state.obligation_counts[obligation_index])
        state.obligation_counts[obligation_index] = before + 1
        if obligation.required and before < obligation.minimum_selected_frames <= before + 1:
            state.unsatisfied_required_obligation_count -= 1
    unit_code = int(forward_domain.candidate_correlation_unit_codes[candidate])
    state.correlation_unit_counts[unit_code] += 1
    state.representative_utility += score.representative_gain
    state.available[candidate] = False
    state.selected_order.append(candidate)


def deselect_target_multi_view_candidate_v2(
    candidate_index: int,
    forward_domain: TargetCoverageSparseForwardDomainView,
    state: TargetMultiViewForwardStateV2,
) -> None:
    """Deselect one candidate by reversing only its forward incidence rows."""

    candidate = int(candidate_index)
    if candidate < 0 or candidate >= forward_domain.candidate_count:
        raise IndexError(candidate)
    if bool(state.available[candidate]):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 candidate is not selected.")
    representative_decrement = 0.0
    for forward_family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = np.asarray(
            forward_family.candidate_witness_indices(candidate), dtype=np.int64
        )
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses]
        if np.any(multiplicity <= 0):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 witness multiplicity underflow.")
        weights = family_state.weights[witnesses]
        representative_decrement += float(
            np.sum(weights / multiplicity.astype(np.float64), dtype=np.float64)
        )
        uniquely_covered = multiplicity == 1
        family_state.coverage_mass -= float(
            np.sum(weights[uniquely_covered], dtype=np.float64)
        )
        if abs(family_state.coverage_mass) <= 5.0e-13:
            family_state.coverage_mass = 0.0
        if family_state.coverage_mass < -5.0e-13:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 coverage mass became negative.")
        family_state.multiplicity[witnesses] -= 1
    for obligation_index in np.asarray(
        forward_domain.candidate_obligation_indices(candidate), dtype=np.int64
    ):
        obligation = forward_domain.obligations[int(obligation_index)]
        before = int(state.obligation_counts[obligation_index])
        if before <= 0:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 obligation count underflow.")
        state.obligation_counts[obligation_index] = before - 1
        if obligation.required and before >= obligation.minimum_selected_frames > before - 1:
            state.unsatisfied_required_obligation_count += 1
    unit_code = int(forward_domain.candidate_correlation_unit_codes[candidate])
    if int(state.correlation_unit_counts[unit_code]) <= 0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 correlation count underflow.")
    state.correlation_unit_counts[unit_code] -= 1
    state.representative_utility -= representative_decrement
    if abs(state.representative_utility) <= 5.0e-13:
        state.representative_utility = 0.0
    if state.representative_utility < -5.0e-13:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 representative utility became negative.")
    state.available[candidate] = True
    state.selected_order.remove(candidate)


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectorPolicyV2:
    target_sizes: tuple[int, ...] = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    coverage_threshold: float = 0.95
    gain_tie_tolerance: float = 1.0e-14
    authority_version: str = TARGET_MULTI_VIEW_SELECTOR_V2_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(value) for value in self.target_sizes)
        if not sizes or sizes != tuple(sorted(set(sizes))) or sizes[0] < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 target sizes are invalid.")
        if self.coverage_threshold != 0.95:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 freezes coverage threshold at 0.95.")
        if not math.isfinite(self.gain_tie_tolerance) or not 0.0 < self.gain_tie_tolerance <= 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 gain tolerance is invalid.")
        if self.authority_version != TARGET_MULTI_VIEW_SELECTOR_V2_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL2 policy version.")
        object.__setattr__(self, "target_sizes", sizes)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "mdstats.target-multi-view-selector-policy.v2",
            "target_sizes": self.target_sizes,
            "coverage_threshold": self.coverage_threshold,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "representative_gain": "harmonic_witness_multiplicity",
            "provenance_balance": "least_selected_correlation_unit",
            "diversity_tie_break": "sparse_neighborhood_inverse_multiplicity",
            "authority_version": self.authority_version,
        }
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewSelectorPolicyV2":
        if payload.get("schema") != "mdstats.target-multi-view-selector-policy.v2":
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL2 policy schema.")
        result = cls(
            target_sizes=tuple(int(value) for value in payload["target_sizes"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            gain_tie_tolerance=float(payload["gain_tie_tolerance"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") != result.policy_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionDomainPlanV2:
    label_domain_id: str
    reference_domain_digest: str
    mvidx1_domain_digest: str
    candidate_count: int
    master_order: tuple[TargetMultiViewSelectionEntry, ...]
    rungs: tuple[TargetMultiViewSelectionRung, ...]
    phase_a_completed_at: int | None

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": "mdstats.target-multi-view-selection-domain.v2",
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "mvidx1_domain_digest": self.mvidx1_domain_digest,
            "candidate_count": self.candidate_count,
            "master_order": [item.to_dict() for item in self.master_order],
            "rungs": [item.to_dict() for item in self.rungs],
            "phase_a_completed_at": self.phase_a_completed_at,
        }
        return {**payload, "content_digest": digest(payload)} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewSelectionDomainPlanV2":
        if payload.get("schema") != "mdstats.target-multi-view-selection-domain.v2":
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL2 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            mvidx1_domain_digest=str(payload["mvidx1_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            master_order=tuple(TargetMultiViewSelectionEntry.from_dict(item) for item in payload["master_order"]),
            rungs=tuple(TargetMultiViewSelectionRung.from_dict(item) for item in payload["rungs"]),
            phase_a_completed_at=None if payload.get("phase_a_completed_at") is None else int(payload["phase_a_completed_at"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionPlanV2:
    dataset_id: str
    target_coverage_reference_digest: str
    mvidx1_content_digest: str
    policy: TargetMultiViewSelectorPolicyV2
    domains: tuple[TargetMultiViewSelectionDomainPlanV2, ...]
    authority_version: str = TARGET_MULTI_VIEW_SELECTOR_V2_VERSION
    _domain_by_id: dict[str, TargetMultiViewSelectionDomainPlanV2] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 plan domains are invalid.")
        if self.authority_version != TARGET_MULTI_VIEW_SELECTOR_V2_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL2 plan version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewSelectionDomainPlanV2:
        return self._domain_by_id[label_domain_id]

    @property
    def target_coverage_sparse_index_digest(self) -> str:
        """Compatibility spelling for downstream v1-readable consumers."""
        return self.mvidx1_content_digest

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_domains=False, include_digest=False))

    def to_dict(self, *, include_domains: bool = True, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_SELECTION_PLAN_V2_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "mvidx1_content_digest": self.mvidx1_content_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }
        if include_domains:
            payload["domains"] = [item.to_dict() for item in self.domains]
        return {**payload, "content_digest": digest({key: value for key, value in payload.items() if key != "domains"})} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewSelectionPlanV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTION_PLAN_V2_SCHEMA:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL2 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            mvidx1_content_digest=str(payload["mvidx1_content_digest"]),
            policy=TargetMultiViewSelectorPolicyV2.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewSelectionDomainPlanV2.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 plan digest mismatch.")
        return result


def build_target_multi_view_selection_plan_v2(
    target_coverage_reference: Any,
    target_coverage_forward_index: Any,
    *,
    policy: TargetMultiViewSelectorPolicyV2 | None = None,
    batch_size: int = 256,
    workers: int = 1,
    frontier_rebuild_interval: int = 0,
    checkpoint_callback: Any | None = None,
    progress_callback: Any | None = None,
    progress_interval_seconds: float = 30.0,
) -> TargetMultiViewSelectionPlanV2:
    """Build exact nested MVSEL2 rungs from the forward-only MVIDX1 view."""

    policy = policy or TargetMultiViewSelectorPolicyV2()
    if not math.isfinite(progress_interval_seconds) or progress_interval_seconds <= 0.0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 progress interval must be positive.")
    if target_coverage_reference.dataset_id != target_coverage_forward_index.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 dataset identity mismatch.")
    domains: list[TargetMultiViewSelectionDomainPlanV2] = []
    for reference_domain in target_coverage_reference.domains:
        forward_domain = target_coverage_forward_index.domain(reference_domain.label_domain_id)
        materializable = tuple(size for size in policy.target_sizes if size <= forward_domain.candidate_count)
        if not materializable:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 candidate pool is smaller than every target size.")
        limit = materializable[-1]
        state = build_target_multi_view_forward_state_v2(
            reference_domain, forward_domain,
            coverage_threshold=policy.coverage_threshold,
            epsilon=policy.gain_tie_tolerance,
            requested_cardinality=limit,
        )
        entries: list[TargetMultiViewSelectionEntry] = []
        rung_by_size: dict[int, TargetMultiViewSelectionRung] = {}
        phase_a_completed_at: int | None = None
        frontier: TargetMultiViewLazyFrontierV2 | None = None
        previous_rung = 0
        started = time.monotonic()
        last_progress = started
        cumulative_evaluation_edges = 0
        cumulative_mutation_edges = 0
        fallback_count = 0
        if progress_callback is not None:
            progress_callback(
                f"status=selecting; progress={format_progress_fraction(0, limit)}; "
                f"elapsed={format_progress_time(0.0)}; eta=--:--:--; phase=hard_coverage; "
                f"domain={reference_domain.label_domain_id}"
            )
        for rank in range(limit):
            phase_a = state.unsatisfied_required_obligation_count > 0 or any(
                item.coverage_mass < policy.coverage_threshold - policy.gain_tie_tolerance
                for item in state.family_states
            )
            if phase_a:
                choice = choose_target_multi_view_phase_a_candidate_v2(
                    reference_domain, forward_domain, state,
                    coverage_threshold=policy.coverage_threshold,
                    epsilon=policy.gain_tie_tolerance,
                    batch_size=batch_size, workers=workers,
                )
                bottleneck_id = choice.bottleneck_family_id
                phase = "hard_coverage"
                evaluation_edges = choice.telemetry.candidate_evaluation_forward_edges
                contender_width = choice.telemetry.final_contender_count
                rescoring_count = 0
                heap_entries = 0
            else:
                if frontier is None or (frontier_rebuild_interval > 0 and rank % frontier_rebuild_interval == 0):
                    frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, state)
                choice = choose_target_multi_view_phase_b_candidate_v2(
                    reference_domain, forward_domain, state, frontier,
                    epsilon=policy.gain_tie_tolerance,
                )
                bottleneck_id = None
                phase = "representative_fill"
                evaluation_edges = choice.telemetry.representative_evaluation_edges + choice.telemetry.diversity_evaluation_edges
                contender_width = choice.telemetry.certified_frontier_width
                rescoring_count = choice.telemetry.rescoring_count
                heap_entries = choice.telemetry.heap_entries
                fallback_count += int(choice.telemetry.fallback_used)
            score = choice.score
            bottleneck_gain = 0.0 if bottleneck_id is None else score.family_coverage_gains[
                next(index for index, family in enumerate(forward_domain.families) if family.family_id == bottleneck_id)
            ]
            entries.append(TargetMultiViewSelectionEntry(
                rank=rank,
                frame_uid=reference_domain.frame_uids[score.candidate_index],
                phase=phase,
                primary_reason=("hard_obligation_gain" if score.hard_obligation_gain > 0 else
                                "worst_view_coverage" if phase_a else "density_aware_representative_fill"),
                bottleneck_family_id=bottleneck_id,
                hard_obligation_gain=score.hard_obligation_gain,
                bottleneck_coverage_gain=bottleneck_gain,
                total_coverage_gain=score.total_coverage_gain,
                representative_gain=score.representative_gain,
                normalized_diversity=score.sparse_diversity,
                correlation_unit_code=int(forward_domain.candidate_correlation_unit_codes[score.candidate_index]),
            ))
            select_target_multi_view_candidate_v2(score.candidate_index, forward_domain, state, score=score)
            mutation_edges = sum(
                len(family.candidate_witness_indices(score.candidate_index))
                for family in forward_domain.families
            ) + len(forward_domain.candidate_obligation_indices(score.candidate_index))
            cumulative_evaluation_edges += int(evaluation_edges)
            cumulative_mutation_edges += int(mutation_edges)
            if phase_a_completed_at is None and state.unsatisfied_required_obligation_count == 0 and all(
                item.coverage_mass >= policy.coverage_threshold - policy.gain_tie_tolerance for item in state.family_states
            ):
                phase_a_completed_at = rank + 1
            size = rank + 1
            if size in materializable:
                unsatisfied = tuple(sorted(
                    item.obligation_id for index, item in enumerate(forward_domain.obligations)
                    if item.required and int(state.obligation_counts[index]) < int(item.minimum_selected_frames)
                ))
                coverage = tuple((item.family_id, min(1.0, max(0.0, item.coverage_mass))) for item in state.family_states)
                shell = entries[previous_rung:size]
                rung_by_size[size] = TargetMultiViewSelectionRung(
                    target_size=size, materializable=True,
                    frame_uids=tuple(item.frame_uid for item in entries),
                    family_coverage=coverage,
                    hard_obligations_passed=not unsatisfied,
                    unsatisfied_obligation_ids=unsatisfied,
                    hard_coverage_qualified=not unsatisfied and all(value >= policy.coverage_threshold - policy.gain_tie_tolerance for _, value in coverage),
                    phase_at_boundary=entries[-1].phase,
                    shell_coverage_gain=float(np.sum([item.total_coverage_gain for item in shell], dtype=np.float64)),
                    shell_representative_gain=float(np.sum([item.representative_gain for item in shell], dtype=np.float64)),
                )
                previous_rung = size
                if checkpoint_callback is not None:
                    checkpoint_callback(reference_domain, forward_domain, state, size)
            now = time.monotonic()
            if progress_callback is not None and (
                size == limit or size in materializable or now - last_progress >= progress_interval_seconds
            ):
                elapsed = now - started
                throughput = size / elapsed if elapsed > 0.0 else 0.0
                eta = (limit - size) / throughput if throughput > 0.0 else None
                progress_callback(
                    f"status=selecting; progress={format_progress_fraction(size, limit)}; "
                    f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                    f"throughput={throughput:.3f} ranks/s; phase={phase}; rank={rank}; "
                    f"mutation_forward_edges={mutation_edges}; candidate_evaluation_forward_edges={evaluation_edges}; "
                    f"cumulative_mutation_edges={cumulative_mutation_edges}; cumulative_evaluation_edges={cumulative_evaluation_edges}; "
                    f"contender_width={contender_width}; rescoring_count={rescoring_count}; "
                    f"heap_entries={heap_entries}; fallback_count={fallback_count}"
                )
                last_progress = now
        rungs = tuple(
            rung_by_size.get(size) or TargetMultiViewSelectionRung(
                target_size=size, materializable=False,
                unavailable_reason=f"authorized_pool_has_{forward_domain.candidate_count}_frames_below_required_{size}",
            )
            for size in policy.target_sizes
        )
        domains.append(TargetMultiViewSelectionDomainPlanV2(
            label_domain_id=reference_domain.label_domain_id,
            reference_domain_digest=reference_domain.content_digest,
            mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
            candidate_count=forward_domain.candidate_count,
            master_order=tuple(entries), rungs=rungs,
            phase_a_completed_at=phase_a_completed_at,
        ))
    return TargetMultiViewSelectionPlanV2(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        mvidx1_content_digest=target_coverage_forward_index.mvidx1_content_digest,
        policy=policy, domains=tuple(domains),
    )


def validate_target_multi_view_selection_authority_v2(
    plan: TargetMultiViewSelectionPlanV2,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    query_workers: int = 1,
) -> None:
    """Independently validate every materializable rung through DATA2B/MVIDX1."""

    from .target_coverage import score_target_subset_coverage
    from .target_coverage_sparse_index import indexed_family_covered_mass, indexed_obligation_selected_counts

    if plan.dataset_id != target_coverage_reference.dataset_id or plan.dataset_id != target_coverage_sparse_index.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 qualification dataset mismatch.")
    if plan.target_coverage_reference_digest != target_coverage_reference.content_digest or plan.mvidx1_content_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 qualification lineage mismatch.")
    for domain_plan in plan.domains:
        reference_domain = target_coverage_reference.domain(domain_plan.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(domain_plan.label_domain_id)
        uid_to_index = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
        prior: tuple[str, ...] = ()
        for rung in domain_plan.rungs:
            if not rung.materializable:
                continue
            if rung.frame_uids[:len(prior)] != prior or len(rung.frame_uids) != rung.target_size or len(set(rung.frame_uids)) != rung.target_size:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 rung cardinality/nesting failed.")
            if any(uid not in uid_to_index for uid in rung.frame_uids):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 rung contains an unknown UID.")
            selected = tuple(uid_to_index[uid] for uid in rung.frame_uids)
            indexed_coverage = tuple(
                (family.family_id, indexed_family_covered_mass(
                    sparse_domain.family(family.family_id), family.weights, selected
                )) for family in reference_domain.families
            )
            if not np.allclose([value for _, value in indexed_coverage], [value for _, value in rung.family_coverage], rtol=0.0, atol=5.0e-13):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 indexed rung coverage mismatch.")
            counts = indexed_obligation_selected_counts(sparse_domain, selected)
            unsatisfied = tuple(sorted(
                item.obligation_id for index, item in enumerate(sparse_domain.obligations)
                if item.required and int(counts[index]) < int(item.minimum_selected_frames)
            ))
            if unsatisfied != rung.unsatisfied_obligation_ids:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 rung obligation mismatch.")
            report = score_target_subset_coverage(
                target_coverage_reference, domain_plan.label_domain_id, rung.frame_uids,
                query_workers=query_workers,
            )
            report_mass = {item.family_id: item.covered_reference_mass for item in report.family_reports}
            if not np.allclose([report_mass[key] for key, _ in indexed_coverage], [value for _, value in indexed_coverage], rtol=0.0, atol=5.0e-13):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 DATA2B/indexed coverage disagreement.")
            prior = rung.frame_uids
