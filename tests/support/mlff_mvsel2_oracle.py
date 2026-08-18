"""Independent exact forward oracle for bounded MVSEL2 qualification graphs.

This test-only implementation intentionally does not import selector runtime
code or maintain candidate marginal arrays.  It recomputes every candidate
score directly from forward candidate-to-witness rows and current witness
multiplicity at each accepted rank.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class OracleObligation:
    obligation_id: str
    minimum_selected_frames: int
    candidate_indices: tuple[int, ...]
    required: bool = True


@dataclass(frozen=True, slots=True)
class OracleProblem:
    frame_uids: tuple[str, ...]
    family_ids: tuple[str, ...]
    family_weights: tuple[tuple[float, ...], ...]
    forward_rows: tuple[tuple[tuple[int, ...], ...], ...]
    correlation_unit_codes: tuple[int, ...]
    obligations: tuple[OracleObligation, ...] = ()
    coverage_threshold: float = 0.95
    epsilon: float = 1.0e-14


@dataclass(frozen=True, slots=True)
class OracleSelection:
    candidate_index: int
    frame_uid: str
    phase: str
    bottleneck_family_id: str | None
    hard_gain: int
    bottleneck_coverage_gain: float
    total_coverage_gain: float
    representative_gain: float
    diversity: float


def best_relative_contenders(
    values: Sequence[float], candidates: Sequence[int], epsilon: float
) -> tuple[int, ...]:
    """Apply the frozen ``best - epsilon`` contender rule exactly once."""

    candidate_tuple = tuple(int(value) for value in candidates)
    if len(candidate_tuple) <= 1:
        return candidate_tuple
    array = np.asarray(values, dtype=np.float64)
    best = max(float(array[candidate]) for candidate in candidate_tuple)
    return tuple(
        candidate
        for candidate in candidate_tuple
        if float(array[candidate]) >= best - float(epsilon)
    )


def _validate_problem(problem: OracleProblem, target_size: int) -> None:
    candidate_count = len(problem.frame_uids)
    if candidate_count < 1 or len(set(problem.frame_uids)) != candidate_count:
        raise ValueError("frame_uids must be non-empty and unique")
    if target_size < 1 or target_size > candidate_count:
        raise ValueError("target_size exceeds the candidate pool")
    if not problem.family_ids or len(set(problem.family_ids)) != len(problem.family_ids):
        raise ValueError("family_ids must be non-empty and unique")
    if len(problem.family_weights) != len(problem.family_ids) or len(problem.forward_rows) != len(problem.family_ids):
        raise ValueError("family arrays do not match canonical family order")
    if not math.isfinite(problem.coverage_threshold) or not 0.0 < problem.coverage_threshold <= 1.0:
        raise ValueError("coverage_threshold must be finite and in (0, 1]")
    if not math.isfinite(problem.epsilon) or problem.epsilon <= 0.0:
        raise ValueError("epsilon must be positive and finite")
    if len(problem.correlation_unit_codes) != candidate_count:
        raise ValueError("correlation codes do not match the candidate pool")
    if any(code < 0 for code in problem.correlation_unit_codes):
        raise ValueError("correlation codes must be nonnegative")

    for family_id, raw_weights, candidate_rows in zip(
        problem.family_ids,
        problem.family_weights,
        problem.forward_rows,
        strict=True,
    ):
        weights = np.asarray(raw_weights, dtype=np.float64)
        if weights.ndim != 1 or weights.size < 1:
            raise ValueError(f"family {family_id} must contain witnesses")
        if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError(f"family {family_id} has invalid witness weights")
        if len(candidate_rows) != candidate_count:
            raise ValueError(f"family {family_id} rows do not match the candidate pool")
        covered_capacity = np.zeros(weights.size, dtype=np.bool_)
        for row in candidate_rows:
            normalized = tuple(int(witness) for witness in row)
            if normalized != tuple(sorted(set(normalized))):
                raise ValueError(f"family {family_id} rows must be strictly sorted and unique")
            if any(witness < 0 or witness >= weights.size for witness in normalized):
                raise ValueError(f"family {family_id} row contains an out-of-range witness")
            if normalized:
                covered_capacity[np.asarray(normalized, dtype=np.int64)] = True
        capacity = float(np.sum(weights[covered_capacity], dtype=np.float64))
        if capacity < problem.coverage_threshold - problem.epsilon:
            raise ValueError(f"family {family_id} cannot reach the coverage threshold")

    for obligation in problem.obligations:
        if not obligation.obligation_id:
            raise ValueError("obligation_id cannot be empty")
        candidates = tuple(int(candidate) for candidate in obligation.candidate_indices)
        if candidates != tuple(sorted(set(candidates))):
            raise ValueError("obligation incidence must be strictly sorted and unique")
        if any(candidate < 0 or candidate >= candidate_count for candidate in candidates):
            raise ValueError("obligation incidence contains an out-of-range candidate")
        if obligation.minimum_selected_frames < 1:
            raise ValueError("obligation minimum must be positive")
        if obligation.required and len(candidates) < obligation.minimum_selected_frames:
            raise ValueError("required obligation is infeasible")


def _candidate_scores(
    problem: OracleProblem,
    multiplicities: list[np.ndarray],
    candidate: int,
) -> tuple[np.ndarray, float, float, float]:
    coverage = np.zeros(len(problem.family_ids), dtype=np.float64)
    representative = 0.0
    diversity_by_family: list[float] = []
    for family_index, (raw_weights, candidate_rows) in enumerate(
        zip(problem.family_weights, problem.forward_rows, strict=True)
    ):
        row = candidate_rows[candidate]
        if not row:
            continue
        witnesses = np.asarray(row, dtype=np.int64)
        weights = np.asarray(raw_weights, dtype=np.float64)
        multiplicity = multiplicities[family_index][witnesses]
        coverage[family_index] = float(
            np.sum(weights[witnesses][multiplicity == 0], dtype=np.float64)
        )
        representative += float(
            np.sum(weights[witnesses] / (multiplicity + 1.0), dtype=np.float64)
        )
        diversity_by_family.append(
            float(np.mean(1.0 / (multiplicity + 1.0), dtype=np.float64))
        )
    total_coverage = float(np.sum(coverage, dtype=np.float64))
    diversity = (
        0.0
        if not diversity_by_family
        else float(np.mean(np.asarray(diversity_by_family), dtype=np.float64))
    )
    return coverage, total_coverage, representative, diversity


def exact_forward_order(problem: OracleProblem, target_size: int) -> tuple[OracleSelection, ...]:
    """Return an exact order by full forward rescoring at every rank."""

    _validate_problem(problem, target_size)
    candidate_count = len(problem.frame_uids)
    multiplicities = [
        np.zeros(len(weights), dtype=np.int64) for weights in problem.family_weights
    ]
    coverage_mass = np.zeros(len(problem.family_ids), dtype=np.float64)
    obligation_counts = np.zeros(len(problem.obligations), dtype=np.int64)
    unit_count_size = max(problem.correlation_unit_codes, default=0) + 1
    unit_counts = np.zeros(unit_count_size, dtype=np.int64)
    available = np.ones(candidate_count, dtype=np.bool_)
    incidence = [set(item.candidate_indices) for item in problem.obligations]
    selections: list[OracleSelection] = []

    for _rank in range(target_size):
        candidates = tuple(int(value) for value in np.flatnonzero(available))
        hard_pending = any(
            obligation.required
            and int(obligation_counts[index]) < obligation.minimum_selected_frames
            for index, obligation in enumerate(problem.obligations)
        )
        coverage_pending = bool(
            np.any(coverage_mass < problem.coverage_threshold - problem.epsilon)
        )
        phase = "hard_coverage" if hard_pending or coverage_pending else "representative_fill"

        hard_gains = np.zeros(candidate_count, dtype=np.int64)
        if hard_pending:
            for index, obligation in enumerate(problem.obligations):
                if not obligation.required or int(obligation_counts[index]) >= obligation.minimum_selected_frames:
                    continue
                for candidate in incidence[index]:
                    hard_gains[candidate] += 1
            best_hard = max(int(hard_gains[candidate]) for candidate in candidates)
            candidates = tuple(
                candidate for candidate in candidates if int(hard_gains[candidate]) == best_hard
            )

        scores = {
            candidate: _candidate_scores(problem, multiplicities, candidate)
            for candidate in candidates
        }
        bottleneck_index: int | None = None
        if phase == "hard_coverage":
            ratios = coverage_mass / problem.coverage_threshold
            minimum = float(np.min(ratios))
            bottleneck_index = int(
                np.flatnonzero(ratios <= minimum + problem.epsilon)[0]
            )
            family_values = np.zeros(candidate_count, dtype=np.float64)
            for candidate in candidates:
                family_values[candidate] = scores[candidate][0][bottleneck_index]
            candidates = best_relative_contenders(
                family_values, candidates, problem.epsilon
            )
            total_coverage_values = np.zeros(candidate_count, dtype=np.float64)
            for candidate in candidates:
                total_coverage_values[candidate] = scores[candidate][1]
            candidates = best_relative_contenders(
                total_coverage_values, candidates, problem.epsilon
            )
        else:
            representative_values = np.zeros(candidate_count, dtype=np.float64)
            for candidate in candidates:
                representative_values[candidate] = scores[candidate][2]
            candidates = best_relative_contenders(
                representative_values, candidates, problem.epsilon
            )

        minimum_unit_count = min(
            int(unit_counts[problem.correlation_unit_codes[candidate]])
            for candidate in candidates
        )
        candidates = tuple(
            candidate
            for candidate in candidates
            if int(unit_counts[problem.correlation_unit_codes[candidate]]) == minimum_unit_count
        )

        if phase == "hard_coverage":
            representative_values = np.zeros(candidate_count, dtype=np.float64)
            for candidate in candidates:
                representative_values[candidate] = scores[candidate][2]
            candidates = best_relative_contenders(
                representative_values, candidates, problem.epsilon
            )

        diversity_values = np.zeros(candidate_count, dtype=np.float64)
        for candidate in candidates:
            diversity_values[candidate] = scores[candidate][3]
        candidates = best_relative_contenders(
            diversity_values, candidates, problem.epsilon
        )
        chosen = min(candidates, key=lambda candidate: problem.frame_uids[candidate])
        chosen_scores = scores[chosen]
        selections.append(
            OracleSelection(
                candidate_index=chosen,
                frame_uid=problem.frame_uids[chosen],
                phase=phase,
                bottleneck_family_id=(
                    None
                    if bottleneck_index is None
                    else problem.family_ids[bottleneck_index]
                ),
                hard_gain=int(hard_gains[chosen]),
                bottleneck_coverage_gain=(
                    0.0
                    if bottleneck_index is None
                    else float(chosen_scores[0][bottleneck_index])
                ),
                total_coverage_gain=float(chosen_scores[1]),
                representative_gain=float(chosen_scores[2]),
                diversity=float(chosen_scores[3]),
            )
        )

        available[chosen] = False
        for family_index, candidate_rows in enumerate(problem.forward_rows):
            row = candidate_rows[chosen]
            if not row:
                continue
            witnesses = np.asarray(row, dtype=np.int64)
            weights = np.asarray(problem.family_weights[family_index], dtype=np.float64)
            newly_covered = multiplicities[family_index][witnesses] == 0
            coverage_mass[family_index] += float(
                np.sum(weights[witnesses][newly_covered], dtype=np.float64)
            )
            multiplicities[family_index][witnesses] += 1
        for index, obligation_candidates in enumerate(incidence):
            if chosen in obligation_candidates:
                obligation_counts[index] += 1
        unit_counts[problem.correlation_unit_codes[chosen]] += 1

    return tuple(selections)
