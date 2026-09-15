"""Optimized exact MVSEL2 execution kernels and native worker preflight.

Restored from the final accepted execution lineage at carrier ``3937881e``
(``mvsel2_phase_a_kernel`` blob, ``mvsel2_phase_b_kernel`` blob ``3ccb48e9`` and
``mvsel2_native_preflight`` blob ``7241210c``).  These kernels change execution
representation only and must reproduce :mod:`selector` choices at every rank:

* Phase A: family-major traversal with a bounded dense FP64 contender-by-family
  scratch; with ``workers > 1`` the representative and diversity row sums use
  the qualified native/OpenMP reduction (identical element sequences, bitwise
  exact) while coverage gains, lexicographic filtering, canonical family
  accumulation and the choice stay in the canonical masked reduction.
* Phase B: one reconstructible FP64 witness term ``w/(n+1)`` per witness,
  updated only for witnesses touched by newly selected candidates; exact
  all-candidate rebase; conservative outward-rounded lazy bounds; bounded stale
  refresh batches through the native row scorer; certification, balance,
  diversity, UID and mutation in canonical Python control.
* Preflight: deterministic real-MVIDX row sample, widths ``1, 2, 4, ...`` plus
  the exact budget endpoint, bitwise FP64 parity, parallel activation at
  ``>= 1.05x`` speedup and the smallest width within 5% of the best.

The witness-term cache lives on the state object it was derived from, so a
reconstructed post-repair state can never consume a pre-repair cache.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
import time
from typing import Any

import numpy as np

from .._common import TrainingDataInputError
from .native import mvsel2_execution_backend, qualify_mvsel2_native_backend, score_family_candidate_batch
from .selector import (
    Choice,
    LazyFrontier,
    TargetMultiViewCandidateScore,
    TargetMultiViewForwardState,
    TargetMultiViewSelectorPolicy,
    bottleneck_family_index,
    certify_phase_b_contenders,
    family_coverage_gain,
    native_row,
    phase_a_active,
    record_refreshed_score,
    representative_gain,
    sparse_diversity,
    valid_heap_top,
)


def _native_family_scores(family: Any, terms: np.ndarray, candidates: np.ndarray, *, workers: int) -> tuple[np.ndarray, int]:
    return score_family_candidate_batch(
        np.asarray(family.candidate_offsets),
        np.asarray(family.candidate_witnesses),
        np.ascontiguousarray(terms, dtype=np.float64),
        np.asarray(candidates, dtype=np.uint32),
        workers=int(workers),
    )


def _best_relative(candidates: np.ndarray, values: np.ndarray, epsilon: float) -> np.ndarray:
    if candidates.size <= 1:
        return candidates
    selected = values[candidates]
    return candidates[selected >= float(np.max(selected)) - float(epsilon)]


def choose_phase_a(
    reference: Any,
    forward: Any,
    state: TargetMultiViewForwardState,
    policy: TargetMultiViewSelectorPolicy,
    *,
    workers: int = 1,
) -> Choice:
    """Exact Phase A with one locality-oriented scoring authority."""

    epsilon = float(policy.gain_tie_tolerance)
    native_parallel = mvsel2_execution_backend(workers) == "native-openmp"
    candidate_count = int(forward.candidate_count)
    available = np.flatnonzero(state.available).astype(np.int64, copy=False)
    if available.size == 0:
        raise TrainingDataInputError("MVSEL2 exhausted the candidate pool.")
    if not phase_a_active(state, policy):
        raise TrainingDataInputError("MVSEL2 Phase A is already complete.")
    hard_gains = np.zeros(candidate_count, dtype=np.int32)
    if state.unsatisfied_required_obligation_count > 0:
        for candidate in available:
            candidate = int(candidate)
            gain = 0
            for index in native_row(forward.candidate_obligation_indices(candidate)):
                if int(state.obligation_counts[int(index)]) < int(forward.obligations[int(index)].minimum_selected_frames):
                    gain += 1
            hard_gains[candidate] = gain
        candidates = available[hard_gains[available] == int(np.max(hard_gains[available]))]
    else:
        candidates = available
    bottleneck = bottleneck_family_index(state, policy)
    edges = 0
    # Coverage gains always use the canonical masked reduction over uncovered
    # witnesses.  A native full-row sum with zeros for covered witnesses
    # associates differently in NumPy's pairwise summation for rows of eight
    # or more witnesses, so it is not bitwise equal to the D2 reference and
    # would let execution width perturb accumulated coverage masses.
    bottleneck_values = np.full(candidate_count, -np.inf, dtype=np.float64)
    for candidate in candidates:
        value, count = family_coverage_gain(int(candidate), bottleneck, forward, state)
        bottleneck_values[int(candidate)] = value
        edges += count
    candidates = _best_relative(candidates, bottleneck_values, epsilon)
    family_count = len(forward.families)
    coverage = np.zeros((candidates.size, family_count), dtype=np.float64)
    for family_index in range(family_count):
        for local, candidate in enumerate(candidates):
            value, count = family_coverage_gain(int(candidate), family_index, forward, state)
            coverage[local, family_index] = value
            edges += count
    totals = np.sum(coverage, axis=1, dtype=np.float64)
    total_mask = totals >= float(np.max(totals)) - epsilon
    total_candidates = candidates[total_mask]
    minimum_unit = min(
        int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[int(c)])]) for c in total_candidates
    )
    candidates = np.asarray(
        [
            int(c)
            for c in total_candidates
            if int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[int(c)])]) == minimum_unit
        ],
        dtype=np.int64,
    )
    representative = np.full(candidate_count, -np.inf, dtype=np.float64)
    if native_parallel:
        scores = np.zeros(len(candidates), dtype=np.float64)
        for family, family_state in zip(forward.families, state.family_states, strict=True):
            terms = np.divide(family_state.weights, family_state.multiplicity.astype(np.float64) + 1.0, dtype=np.float64)
            values, count = _native_family_scores(family, terms, candidates, workers=workers)
            for position, value in enumerate(values):
                scores[position] += float(value)
            edges += count
        representative[candidates] = scores
    else:
        for candidate in candidates:
            value, count = representative_gain(int(candidate), forward, state)
            representative[int(candidate)] = value
            edges += count
    candidates = _best_relative(candidates, representative, epsilon)
    diversity = np.full(candidate_count, -np.inf, dtype=np.float64)
    if native_parallel:
        matrix = np.full((len(candidates), family_count), np.nan, dtype=np.float64)
        for family_index, (family, family_state) in enumerate(zip(forward.families, state.family_states, strict=True)):
            terms = np.divide(1.0, family_state.multiplicity.astype(np.float64) + 1.0, dtype=np.float64)
            sums, count = _native_family_scores(family, terms, candidates, workers=workers)
            offsets = np.asarray(family.candidate_offsets)
            for position, candidate in enumerate(candidates):
                rows = int(offsets[int(candidate) + 1] - offsets[int(candidate)])
                if rows:
                    matrix[position, family_index] = float(sums[position]) / rows
            edges += count
        for position, candidate in enumerate(candidates):
            finite = matrix[position, np.isfinite(matrix[position])]
            diversity[int(candidate)] = float(np.mean(finite, dtype=np.float64)) if finite.size else 0.0
    else:
        for candidate in candidates:
            value, count = sparse_diversity(int(candidate), forward, state)
            diversity[int(candidate)] = value
            edges += count
    candidates = _best_relative(candidates, diversity, epsilon)
    chosen = min((int(c) for c in candidates), key=lambda c: reference.frame_uids[c])
    source = int(np.flatnonzero(total_mask)[int(np.flatnonzero(total_candidates == chosen)[0])])
    return Choice(
        candidate_index=chosen,
        bottleneck_family_id=forward.families[bottleneck].family_id,
        score=TargetMultiViewCandidateScore(
            candidate_index=chosen,
            family_coverage_gains=tuple(float(v) for v in coverage[source]),
            total_coverage_gain=float(totals[source]),
            representative_gain=float(representative[chosen]),
            sparse_diversity=float(diversity[chosen]),
            hard_obligation_gain=int(hard_gains[chosen]),
        ),
        contender_width=int(candidates.size),
        evaluation_edges=int(edges),
    )


@dataclass(slots=True)
class _WitnessTermCache:
    generation: int
    terms: tuple[np.ndarray, ...]


def _build_terms(state: TargetMultiViewForwardState) -> tuple[np.ndarray, ...]:
    return tuple(
        np.divide(item.weights, item.multiplicity.astype(np.float64) + 1.0, dtype=np.float64)
        for item in state.family_states
    )


def witness_term_cache(forward: Any, state: TargetMultiViewForwardState) -> _WitnessTermCache:
    """Return this state's cache synchronized to its current selected prefix."""

    cache = state.execution_cache
    generation = state.selected_count
    if not isinstance(cache, _WitnessTermCache) or cache.generation > generation:
        cache = _WitnessTermCache(generation=generation, terms=_build_terms(state))
        state.execution_cache = cache
        return cache
    if cache.generation == generation:
        return cache
    for family, family_state, terms in zip(forward.families, state.family_states, cache.terms, strict=True):
        touched = [native_row(family.candidate_witness_indices(int(c))) for c in state.selected_order[cache.generation:generation]]
        touched = [row for row in touched if row.size]
        if not touched:
            continue
        witnesses = touched[0] if len(touched) == 1 else np.unique(np.concatenate(touched))
        terms[witnesses] = np.divide(
            family_state.weights[witnesses], family_state.multiplicity[witnesses].astype(np.float64) + 1.0, dtype=np.float64
        )
    cache.generation = generation
    return cache


def _cached_representative(candidate: int, forward: Any, cache: _WitnessTermCache) -> tuple[float, int]:
    gain = 0.0
    edges = 0
    for family, terms in zip(forward.families, cache.terms, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        gain += float(np.sum(terms[witnesses], dtype=np.float64))
        edges += int(witnesses.size)
    return gain, edges


def _native_representative_batch(candidates: tuple[int, ...], forward: Any, cache: _WitnessTermCache, *, workers: int) -> tuple[dict[int, float], int]:
    ordered = tuple(sorted(set(int(c) for c in candidates)))
    array = np.asarray(ordered, dtype=np.uint32)
    scores = [0.0] * len(ordered)
    edges = 0
    for family, terms in zip(forward.families, cache.terms, strict=True):
        values, count = _native_family_scores(family, terms, array, workers=workers)
        # Canonical family accumulation order per candidate is preserved.
        for position, value in enumerate(values):
            scores[position] += float(value)
        edges += int(count)
    return {candidate: float(scores[position]) for position, candidate in enumerate(ordered)}, edges


def build_lazy_frontier(forward: Any, state: TargetMultiViewForwardState, *, workers: int = 1) -> LazyFrontier:
    """Exact all-candidate Phase-B rebase from cached witness terms."""

    cache = witness_term_cache(forward, state)
    generation = state.selected_count
    available = tuple(int(v) for v in np.flatnonzero(state.available))
    if mvsel2_execution_backend(workers) == "python-numpy":
        scores = [0.0] * int(forward.candidate_count)
        for family, terms in zip(forward.families, cache.terms, strict=True):
            for candidate in available:
                witnesses = native_row(family.candidate_witness_indices(candidate))
                if witnesses.size:
                    scores[candidate] += float(np.sum(terms[witnesses], dtype=np.float64))
        by_candidate = {candidate: float(scores[candidate]) for candidate in available}
    else:
        by_candidate, _ = _native_representative_batch(available, forward, cache, workers=workers)
    exact = np.full(int(forward.candidate_count), np.nan, dtype=np.float64)
    generations = np.full(int(forward.candidate_count), -1, dtype=np.int64)
    heap: list[tuple[float, int, int]] = []
    for candidate in available:
        exact[candidate] = by_candidate[candidate]
        generations[candidate] = generation
        heap.append((-float(np.nextafter(np.float64(by_candidate[candidate]), np.float64(np.inf))), candidate, generation))
    heapq.heapify(heap)
    return LazyFrontier(generation, heap, exact, generations)


def choose_phase_b(
    reference: Any,
    forward: Any,
    state: TargetMultiViewForwardState,
    frontier: LazyFrontier,
    policy: TargetMultiViewSelectorPolicy,
    *,
    workers: int = 1,
    batch_size: int = 256,
) -> Choice:
    """Certify the exact Phase-B contender set with qualified execution."""

    if int(batch_size) < 1:
        raise TrainingDataInputError("MVSEL2 Phase-B batch size must be positive.")
    backend = mvsel2_execution_backend(workers)
    cache = witness_term_cache(forward, state)
    generation = state.selected_count
    frontier.generation = generation
    epsilon = float(policy.gain_tie_tolerance)
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
        if best_exact > -math.inf and upper < best_exact - epsilon:
            break
        if entry_generation != generation:
            if backend == "python-numpy":
                heapq.heappop(frontier.heap)
                exact, count = _cached_representative(candidate, forward, cache)
                refreshed = {candidate: exact}
            else:
                batch: list[int] = []
                seen: set[int] = set()
                while len(batch) < int(batch_size):
                    item = valid_heap_top(frontier, state)
                    if item is None:
                        break
                    item_upper, item_candidate, item_generation, _ = item
                    if (best_exact > -math.inf and item_upper < best_exact - epsilon) or item_generation == generation:
                        break
                    heapq.heappop(frontier.heap)
                    if item_candidate not in seen:
                        seen.add(item_candidate)
                        batch.append(item_candidate)
                if not batch:
                    raise TrainingDataInputError("MVSEL2 failed to form a native stale batch.")
                refreshed, count = _native_representative_batch(tuple(batch), forward, cache, workers=workers)
            edges += int(count)
            rescoring += len(refreshed)
            for item_candidate in sorted(refreshed):
                record_refreshed_score(frontier, item_candidate, float(refreshed[item_candidate]), generation)
            continue
        heapq.heappop(frontier.heap)
        exact_candidates.add(candidate)
        best_exact = max(best_exact, float(frontier.exact_scores[candidate]))
    return certify_phase_b_contenders(
        reference, forward, state, frontier, exact_candidates, best_exact, policy,
        rescoring_count=rescoring, evaluation_edges=edges,
    )


@dataclass(frozen=True, slots=True)
class NativeWorkerMeter:
    workers: int
    elapsed_seconds: float
    forward_edges: int
    speedup_vs_one: float


@dataclass(frozen=True, slots=True)
class NativePreflight:
    requested_workers: int
    effective_workers: int
    sample_candidates: int
    forward_edges: int
    minimum_parallel_speedup: float
    best_parallel_speedup: float
    scaling_passed: bool
    meters: tuple[NativeWorkerMeter, ...]
    reason: str | None = None

    def summary(self) -> str:
        meters = ",".join(f"{m.workers}w:{m.elapsed_seconds:.3f}s/{m.speedup_vs_one:.2f}x" for m in self.meters)
        return (
            f"sample={self.sample_candidates}; edges={self.forward_edges}; meters={meters or 'none'}; "
            f"best_parallel_speedup={self.best_parallel_speedup:.2f}x; threshold={self.minimum_parallel_speedup:.2f}x; "
            f"scaling={'pass' if self.scaling_passed else 'fail'}; effective_workers={self.effective_workers}"
            + ("" if self.reason is None else f"; fallback_reason={self.reason}")
        )


def preflight_worker_counts(max_workers: int) -> tuple[int, ...]:
    maximum = max(1, int(max_workers))
    values = [1]
    value = 2
    while value < maximum:
        values.append(value)
        value *= 2
    if maximum > 1:
        values.append(maximum)
    return tuple(dict.fromkeys(values))


def preflight_native_workers(
    forward: Any,
    state: TargetMultiViewForwardState,
    *,
    max_workers: int,
    sample_size: int = 256,
    minimum_parallel_speedup: float = 1.05,
    economical_tolerance: float = 0.05,
) -> NativePreflight:
    """Meter exact native widths on real MVIDX rows (execution-only)."""

    max_workers = int(max_workers)
    if max_workers <= 1:
        return NativePreflight(1, 1, 0, 0, float(minimum_parallel_speedup), 1.0, False, (), "single-worker budget")
    status = qualify_mvsel2_native_backend()
    if not status.available or not status.qualified or not status.openmp:
        # The exact serial NumPy path is selected and the reason is reported;
        # backend availability never changes selection semantics.
        return NativePreflight(
            max_workers, 1, 0, 0, float(minimum_parallel_speedup), 1.0, False, (),
            status.reason or "native backend built without OpenMP",
        )
    available = np.flatnonzero(state.available)
    if available.size == 0:
        raise TrainingDataInputError("MVSEL2 native preflight has no available candidates.")
    size = min(int(sample_size), int(available.size))
    positions = np.linspace(0, int(available.size) - 1, num=size, dtype=np.int64)
    candidates = tuple(int(available[int(p)]) for p in positions) if size < available.size else tuple(int(v) for v in available)
    cache = witness_term_cache(forward, state)
    warm, expected_edges = _native_representative_batch(candidates, forward, cache, workers=1)
    reference_bits = np.asarray([warm[c] for c in candidates], dtype=np.float64).view(np.uint64)
    meters: list[NativeWorkerMeter] = []
    baseline = None
    for workers in preflight_worker_counts(max_workers):
        best = float("inf")
        for _ in range(2):
            started = time.perf_counter()
            scores, count = _native_representative_batch(candidates, forward, cache, workers=workers)
            elapsed = time.perf_counter() - started
            actual = np.asarray([scores[c] for c in candidates], dtype=np.float64)
            if int(count) != int(expected_edges) or not np.array_equal(actual.view(np.uint64), reference_bits):
                raise TrainingDataInputError("MVSEL2 native preflight changed exact FP64 scores across worker counts.")
            best = min(best, elapsed)
        if workers == 1:
            baseline = best
        meters.append(NativeWorkerMeter(workers, best, int(expected_edges), float(baseline) / best if best > 0 else 1.0))
    parallel = tuple(item for item in meters if item.workers > 1)
    best_meter = min(parallel, key=lambda item: (item.elapsed_seconds, item.workers))
    passed = best_meter.speedup_vs_one >= float(minimum_parallel_speedup)
    if passed:
        limit = best_meter.elapsed_seconds * (1.0 + float(economical_tolerance))
        effective = min(item.workers for item in parallel if item.elapsed_seconds <= limit)
    else:
        effective = 1
    return NativePreflight(
        requested_workers=max_workers,
        effective_workers=effective,
        sample_candidates=len(candidates),
        forward_edges=int(expected_edges),
        minimum_parallel_speedup=float(minimum_parallel_speedup),
        best_parallel_speedup=float(best_meter.speedup_vs_one),
        scaling_passed=passed,
        meters=tuple(meters),
    )


__all__ = [
    "NativePreflight",
    "NativeWorkerMeter",
    "build_lazy_frontier",
    "choose_phase_a",
    "choose_phase_b",
    "preflight_native_workers",
    "preflight_worker_counts",
    "witness_term_cache",
]
