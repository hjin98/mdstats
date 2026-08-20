"""Exact locality-oriented MVSEL2 Phase-A scoring kernel.

This module changes execution representation only.  It preserves the frozen
Phase-A lexicographic policy while avoiding PAR1 Python threading, per-candidate
score dictionaries, per-candidate Python family-gain tuples, and unconditional
widening of persisted uint32 CSR witness rows to int64.

Broad all-family coverage scoring is transposed to family-major traversal so
one mapped family is consumed at a time.  A dense FP64 contender-by-family
scratch matrix replaces millions of Python float/tuple objects; the matrix is
bounded by candidate_count * family_count and is released after each choice.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ._common import TrainingDataInputError
from .target_multi_view_selector_v2 import (
    TargetMultiViewCandidateScoreV2,
    TargetMultiViewForwardStateV2,
    TargetMultiViewPhaseAChoiceV2,
    TargetMultiViewPhaseATelemetryV2,
)


def _native_row(values: Any) -> np.ndarray:
    """Return one CSR row without changing its authenticated integer dtype."""
    row = np.asarray(values)
    if row.ndim != 1 or row.dtype.kind not in "iu":
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 CSR row is not an integer vector.")
    return row


def _hard_gain(candidate: int, forward_domain: Any, state: TargetMultiViewForwardStateV2) -> int:
    gain = 0
    for obligation_index in _native_row(
        forward_domain.candidate_obligation_indices(candidate)
    ):
        index = int(obligation_index)
        obligation = forward_domain.obligations[index]
        if (
            obligation.required
            and int(state.obligation_counts[index])
            < int(obligation.minimum_selected_frames)
        ):
            gain += 1
    return gain


def _family_coverage_gain(
    candidate: int,
    family_index: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    family = forward_domain.families[family_index]
    family_state = state.family_states[family_index]
    witnesses = _native_row(family.candidate_witness_indices(candidate))
    if witnesses.size == 0:
        return 0.0, 0
    multiplicity = family_state.multiplicity[witnesses]
    weights = family_state.weights[witnesses]
    return (
        float(np.sum(weights[multiplicity == 0], dtype=np.float64)),
        int(witnesses.size),
    )


def _representative_gain(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    gain = 0.0
    edges = 0
    for family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = _native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses]
        gain += float(
            np.sum(
                family_state.weights[witnesses]
                / (multiplicity.astype(np.float64) + 1.0),
                dtype=np.float64,
            )
        )
        edges += int(witnesses.size)
    return gain, edges


def _diversity_gain(
    candidate: int,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> tuple[float, int]:
    values: list[float] = []
    edges = 0
    for family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = _native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses]
        values.append(
            float(
                np.mean(
                    1.0 / (multiplicity.astype(np.float64) + 1.0),
                    dtype=np.float64,
                )
            )
        )
        edges += int(witnesses.size)
    return (
        0.0 if not values else float(np.mean(values, dtype=np.float64)),
        edges,
    )


def _best_relative(
    candidates: np.ndarray,
    values: np.ndarray,
    epsilon: float,
) -> np.ndarray:
    if candidates.size <= 1:
        return candidates
    selected_values = values[candidates]
    best = float(np.max(selected_values))
    return candidates[selected_values >= best - float(epsilon)]


def choose_target_multi_view_phase_a_candidate_v2_kernel(
    reference_domain: Any,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    *,
    coverage_threshold: float = 0.95,
    epsilon: float = 1.0e-14,
    batch_size: int = 256,
    workers: int = 1,
) -> TargetMultiViewPhaseAChoiceV2:
    """Execute exact Phase A with one locality-oriented scoring authority.

    ``batch_size`` and ``workers`` remain accepted execution-compatibility
    parameters.  PAR1 worker threading is intentionally not used.
    """

    epsilon = float(epsilon)
    batch_size = int(batch_size)
    workers = int(workers)
    if batch_size < 1 or workers < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 batch/worker settings must be positive."
        )

    candidate_count = int(forward_domain.candidate_count)
    available = np.flatnonzero(state.available).astype(np.int64, copy=False)
    if available.size == 0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 exhausted the candidate pool.")

    hard_pending = int(state.unsatisfied_required_obligation_count) > 0
    coverage_pending = any(
        item.coverage_mass < float(coverage_threshold) - epsilon
        for item in state.family_states
    )
    if not hard_pending and not coverage_pending:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL2 Phase A is already complete.")

    hard_gains = np.zeros(candidate_count, dtype=np.int32)
    if hard_pending:
        for candidate in available:
            hard_gains[int(candidate)] = _hard_gain(
                int(candidate), forward_domain, state
            )
        maximum = int(np.max(hard_gains[available]))
        candidates = available[hard_gains[available] == maximum]
    else:
        candidates = available
    eligible_count = int(candidates.size)

    ratios = np.asarray(
        [item.coverage_mass / float(coverage_threshold) for item in state.family_states],
        dtype=np.float64,
    )
    minimum = float(np.min(ratios))
    bottleneck_index = int(np.flatnonzero(ratios <= minimum + epsilon)[0])

    bottleneck_values = np.full(candidate_count, -np.inf, dtype=np.float64)
    bottleneck_edges = 0
    for candidate in candidates:
        value, edges = _family_coverage_gain(
            int(candidate), bottleneck_index, forward_domain, state
        )
        bottleneck_values[int(candidate)] = value
        bottleneck_edges += edges
    candidates = _best_relative(candidates, bottleneck_values, epsilon)
    bottleneck_width = int(candidates.size)

    # Family-major traversal keeps one family mapping hot at a time.  The dense
    # scratch replaces one Python tuple of 165 boxed floats per contender and
    # permits the authoritative total to use NumPy's FP64 row reduction.
    family_count = len(forward_domain.families)
    coverage_matrix = np.zeros((candidates.size, family_count), dtype=np.float64)
    total_coverage_edges = 0
    for family_index in range(family_count):
        for local_index, candidate in enumerate(candidates):
            value, edges = _family_coverage_gain(
                int(candidate), family_index, forward_domain, state
            )
            coverage_matrix[local_index, family_index] = value
            total_coverage_edges += edges
    total_local = np.sum(coverage_matrix, axis=1, dtype=np.float64)
    best_total = float(np.max(total_local))
    total_mask = total_local >= best_total - epsilon
    total_candidates = candidates[total_mask]
    total_coverage_width = int(total_candidates.size)

    minimum_unit_count = min(
        int(
            state.correlation_unit_counts[
                int(forward_domain.candidate_correlation_unit_codes[int(candidate)])
            ]
        )
        for candidate in total_candidates
    )
    candidates = np.asarray(
        [
            int(candidate)
            for candidate in total_candidates
            if int(
                state.correlation_unit_counts[
                    int(forward_domain.candidate_correlation_unit_codes[int(candidate)])
                ]
            )
            == minimum_unit_count
        ],
        dtype=np.int64,
    )
    correlation_width = int(candidates.size)

    representative_values = np.full(candidate_count, -np.inf, dtype=np.float64)
    representative_edges = 0
    for candidate in candidates:
        value, edges = _representative_gain(int(candidate), forward_domain, state)
        representative_values[int(candidate)] = value
        representative_edges += edges
    candidates = _best_relative(candidates, representative_values, epsilon)
    representative_width = int(candidates.size)

    diversity_values = np.full(candidate_count, -np.inf, dtype=np.float64)
    diversity_edges = 0
    for candidate in candidates:
        value, edges = _diversity_gain(int(candidate), forward_domain, state)
        diversity_values[int(candidate)] = value
        diversity_edges += edges
    candidates = _best_relative(candidates, diversity_values, epsilon)

    chosen = min(
        (int(candidate) for candidate in candidates),
        key=lambda candidate: reference_domain.frame_uids[candidate],
    )

    chosen_local = int(np.flatnonzero(total_candidates == chosen)[0])
    total_matrix_rows = np.flatnonzero(total_mask)
    source_local = int(total_matrix_rows[chosen_local])
    family_gains = tuple(float(value) for value in coverage_matrix[source_local])
    total_coverage = float(total_local[source_local])
    representative = float(representative_values[chosen])
    if not np.isfinite(representative):
        representative, edges = _representative_gain(chosen, forward_domain, state)
        representative_edges += edges
    diversity = float(diversity_values[chosen])
    if not np.isfinite(diversity):
        diversity, edges = _diversity_gain(chosen, forward_domain, state)
        diversity_edges += edges

    return TargetMultiViewPhaseAChoiceV2(
        candidate_index=chosen,
        bottleneck_family_id=forward_domain.families[bottleneck_index].family_id,
        score=TargetMultiViewCandidateScoreV2(
            candidate_index=chosen,
            family_coverage_gains=family_gains,
            total_coverage_gain=total_coverage,
            representative_gain=representative,
            sparse_diversity=diversity,
            hard_obligation_gain=int(hard_gains[chosen]),
        ),
        telemetry=TargetMultiViewPhaseATelemetryV2(
            eligible_count=eligible_count,
            bottleneck_contender_count=bottleneck_width,
            total_coverage_contender_count=total_coverage_width,
            correlation_contender_count=correlation_width,
            representative_contender_count=representative_width,
            final_contender_count=int(candidates.size),
            bottleneck_evaluation_edges=int(bottleneck_edges),
            total_coverage_evaluation_edges=int(total_coverage_edges),
            representative_evaluation_edges=int(representative_edges),
            diversity_evaluation_edges=int(diversity_edges),
        ),
    )
