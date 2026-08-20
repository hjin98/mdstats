"""Exact production MVSEL2 Phase-B kernel with witness-side representative terms.

The scientific Phase-B policy remains the certified lazy frontier implemented by
``target_multi_view_selector_v2``. This module changes only execution:

* one FP64 representative term is cached per witness,
  ``weight / (multiplicity + 1)``;
* the cache is updated only on forward rows selected since the previous Phase-B
  evaluation;
* stale heap entries are rescored in small deterministic batches traversed
  family-major, so one family's mmap pages are active at a time;
* each scanned family mapping is released after the batch;
* the exact Phase-B rebase remains family-major and forward-only.

No candidate marginal array, inverse adjacency, or additional persistent state
is introduced. The cache is reconstructible from MVSTATE2 witness
multiplicities and is therefore execution state only.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Any

import numpy as np

from ._common import TrainingDataInputError
from .target_multi_view_selector_v2 import (
    TargetMultiViewForwardStateV2,
    TargetMultiViewLazyFrontierV2,
    TargetMultiViewPhaseBChoiceV2,
    TargetMultiViewPhaseBTelemetryV2,
    TargetMultiViewCandidateScoreV2,
    _drop_file_backed_pages_v2,
    _filter_best_relative_v2,
    _sparse_diversity_v2,
    _total_coverage_gain_v2,
)


_PHASE_B_RESCORING_BATCH_SIZE = 128


@dataclass(slots=True)
class _RepresentativeTermCacheV2:
    """Reconstructible per-witness execution cache for one live selector state."""

    state: TargetMultiViewForwardStateV2
    generation: int
    terms: tuple[np.ndarray, ...]


# A production process normally owns one live MVSEL2 state per domain. Keeping a
# strong state reference prevents Python id reuse from aliasing caches. This is
# execution-only state and is never serialized or included in scientific digests.
_CACHE_BY_STATE_ID: dict[int, _RepresentativeTermCacheV2] = {}


def _native_row(values: Any) -> np.ndarray:
    row = np.asarray(values)
    if row.ndim != 1 or row.dtype.kind not in "iu":
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 CSR row is not an integer vector."
        )
    return row


def _build_terms(state: TargetMultiViewForwardStateV2) -> tuple[np.ndarray, ...]:
    result: list[np.ndarray] = []
    for family_state in state.family_states:
        denominator = family_state.multiplicity.astype(np.float64) + 1.0
        result.append(
            np.divide(
                family_state.weights,
                denominator,
                dtype=np.float64,
            )
        )
    return tuple(result)


def _cache_for_state(
    state: TargetMultiViewForwardStateV2,
) -> _RepresentativeTermCacheV2:
    key = id(state)
    cached = _CACHE_BY_STATE_ID.get(key)
    if cached is not None:
        if cached.state is not state:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 Phase-B execution cache state identity collided."
            )
        return cached
    cached = _RepresentativeTermCacheV2(
        state=state,
        generation=int(state.selected_count),
        terms=_build_terms(state),
    )
    _CACHE_BY_STATE_ID[key] = cached
    return cached


def _sync_terms(
    cache: _RepresentativeTermCacheV2,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> None:
    """Advance witness terms to the current selected prefix using forward rows."""

    if cache.state is not state:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 Phase-B cache belongs to another selector state."
        )
    generation = int(state.selected_count)
    if generation < cache.generation:
        # Deselect/repair is not part of the production Phase-B selector loop.
        # Reconstruct rather than trying to infer an arbitrary reverse history.
        cache.terms = _build_terms(state)
        cache.generation = generation
        return
    if generation == cache.generation:
        return

    for family, family_state, terms in zip(
        forward_domain.families,
        state.family_states,
        cache.terms,
        strict=True,
    ):
        touched: list[np.ndarray] = []
        for candidate in state.selected_order[cache.generation:generation]:
            row = _native_row(family.candidate_witness_indices(int(candidate)))
            if row.size:
                touched.append(row)
        if not touched:
            continue
        # The normal selector advances one rank at a time, so this fast path is
        # almost always a single native CSR row. Concatenate only if execution
        # advanced by multiple ranks between Phase-B calls.
        if len(touched) == 1:
            witnesses = touched[0]
        else:
            witnesses = np.unique(np.concatenate(touched))
        terms[witnesses] = np.divide(
            family_state.weights[witnesses],
            family_state.multiplicity[witnesses].astype(np.float64) + 1.0,
            dtype=np.float64,
        )
    cache.generation = generation


def _representative_gain_cached_batch(
    candidates: tuple[int, ...],
    forward_domain: Any,
    cache: _RepresentativeTermCacheV2,
) -> tuple[dict[int, float], int]:
    """Score stale candidates exactly while traversing MVIDX family-major.

    Candidate processing order within a family is sorted for CSR locality. Each
    candidate still receives one FP64 family subtotal in canonical family order,
    matching the scalar scientific accumulation sequence.
    """

    if not candidates:
        return {}, 0
    ordered = tuple(sorted(set(int(candidate) for candidate in candidates)))
    scores = [0.0] * len(ordered)
    edges = 0
    for family, terms in zip(
        forward_domain.families,
        cache.terms,
        strict=True,
    ):
        for position, candidate in enumerate(ordered):
            witnesses = _native_row(family.candidate_witness_indices(candidate))
            if witnesses.size == 0:
                continue
            scores[position] += float(
                np.sum(terms[witnesses], dtype=np.float64)
            )
            edges += int(witnesses.size)

        # Bound the mapped working set. The next family is independent and all
        # candidate scores retain their completed family subtotal in RAM.
        _drop_file_backed_pages_v2(np.asarray(family.candidate_offsets))
        _drop_file_backed_pages_v2(np.asarray(family.candidate_witnesses))

    return {
        candidate: float(scores[position])
        for position, candidate in enumerate(ordered)
    }, edges


def build_target_multi_view_lazy_frontier_v2_kernel(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> TargetMultiViewLazyFrontierV2:
    """Build one exact Phase-B frontier from cached per-witness terms."""

    cache = _cache_for_state(state)
    _sync_terms(cache, forward_domain, state)
    generation = int(state.selected_count)
    candidate_count = int(forward_domain.candidate_count)
    available = tuple(int(value) for value in np.flatnonzero(state.available))

    # Family-major traversal preserves canonical per-candidate FP64 family
    # accumulation while keeping only one family's MVIDX pages active at once.
    scores = [0.0] * candidate_count
    for family, terms in zip(
        forward_domain.families,
        cache.terms,
        strict=True,
    ):
        for candidate in available:
            witnesses = _native_row(family.candidate_witness_indices(candidate))
            if witnesses.size:
                scores[candidate] += float(
                    np.sum(terms[witnesses], dtype=np.float64)
                )
        _drop_file_backed_pages_v2(np.asarray(family.candidate_offsets))
        _drop_file_backed_pages_v2(np.asarray(family.candidate_witnesses))

    exact_scores = np.full(candidate_count, np.nan, dtype=np.float64)
    exact_generations = np.full(candidate_count, -1, dtype=np.int64)
    heap: list[tuple[float, int, int]] = []
    for candidate in available:
        score = float(scores[candidate])
        exact_scores[candidate] = score
        exact_generations[candidate] = generation
        upper = float(np.nextafter(np.float64(score), np.float64(np.inf)))
        heap.append((-upper, candidate, generation))
    heapq.heapify(heap)

    return TargetMultiViewLazyFrontierV2(
        generation=generation,
        heap=heap,
        exact_scores=exact_scores,
        exact_generations=exact_generations,
    )


def _valid_heap_top(
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
        return (
            -float(negative_upper),
            int(candidate),
            int(entry_generation),
            discarded,
        )
    return None


def _pop_stale_batch(
    frontier: TargetMultiViewLazyFrontierV2,
    state: TargetMultiViewForwardStateV2,
    *,
    generation: int,
    best_exact: float,
    epsilon: float,
) -> tuple[tuple[int, ...], int]:
    """Pop a bounded top-of-heap batch of stale candidates.

    Stop before a current-generation exact entry or a bound already below the
    established exact threshold. Extra stale entries inside the bounded batch
    may be refreshed earlier than the scalar loop would require; that changes
    only reconstructible execution state, never the certified comparator.
    """

    batch: list[int] = []
    seen: set[int] = set()
    discarded = 0
    while len(batch) < _PHASE_B_RESCORING_BATCH_SIZE:
        top = _valid_heap_top(frontier, state)
        if top is None:
            break
        upper, candidate, entry_generation, removed = top
        discarded += removed
        if best_exact > -math.inf and upper < best_exact - float(epsilon):
            break
        if entry_generation == generation:
            break
        heapq.heappop(frontier.heap)
        if candidate in seen:
            continue
        seen.add(candidate)
        batch.append(candidate)
    return tuple(batch), discarded


def choose_target_multi_view_phase_b_candidate_v2_kernel(
    reference_domain: Any,
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    frontier: TargetMultiViewLazyFrontierV2,
    *,
    epsilon: float = 1.0e-14,
) -> TargetMultiViewPhaseBChoiceV2:
    """Certify the exact Phase-B contender set with batched stale rescoring."""

    cache = _cache_for_state(state)
    _sync_terms(cache, forward_domain, state)
    generation = int(state.selected_count)
    frontier.generation = generation
    exact_candidates: set[int] = set()
    best_exact = -math.inf
    rescoring_count = 0
    representative_edges = 0
    stale_discarded = 0

    while True:
        top = _valid_heap_top(frontier, state)
        if top is None:
            if exact_candidates:
                break
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 lazy frontier is empty."
            )
        upper, candidate, entry_generation, discarded = top
        stale_discarded += discarded
        if best_exact > -math.inf and upper < best_exact - float(epsilon):
            break

        if entry_generation != generation:
            batch, removed = _pop_stale_batch(
                frontier,
                state,
                generation=generation,
                best_exact=best_exact,
                epsilon=float(epsilon),
            )
            stale_discarded += removed
            if not batch:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 failed to form a stale Phase-B batch."
                )
            exact_by_candidate, edges = _representative_gain_cached_batch(
                batch,
                forward_domain,
                cache,
            )
            representative_edges += int(edges)
            rescoring_count += len(batch)
            for refreshed in batch:
                exact = float(exact_by_candidate[refreshed])
                old_exact = float(frontier.exact_scores[refreshed])
                if np.isfinite(old_exact) and exact > old_exact + 5.0e-13:
                    raise TrainingDataInputError(
                        "TARGET-DATA2C-MVSEL2 representative bound increased after selection."
                    )
                frontier.exact_scores[refreshed] = exact
                frontier.exact_generations[refreshed] = generation
                conservative = float(
                    np.nextafter(np.float64(exact), np.float64(np.inf))
                )
                if conservative + 5.0e-13 < exact:
                    raise TrainingDataInputError(
                        "TARGET-DATA2C-MVSEL2 representative upper bound is not conservative."
                    )
                heapq.heappush(
                    frontier.heap,
                    (-conservative, refreshed, generation),
                )
            continue

        heapq.heappop(frontier.heap)
        exact = float(frontier.exact_scores[candidate])
        exact_candidates.add(candidate)
        best_exact = max(best_exact, exact)

    contenders = tuple(
        sorted(
            candidate
            for candidate in exact_candidates
            if float(frontier.exact_scores[candidate])
            >= best_exact - float(epsilon)
        )
    )
    if not contenders:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 failed to certify a Phase-B contender."
        )
    minimum_unit_count = min(
        int(
            state.correlation_unit_counts[
                int(forward_domain.candidate_correlation_unit_codes[candidate])
            ]
        )
        for candidate in contenders
    )
    contenders = tuple(
        candidate
        for candidate in contenders
        if int(
            state.correlation_unit_counts[
                int(forward_domain.candidate_correlation_unit_codes[candidate])
            ]
        )
        == minimum_unit_count
    )
    diversity: dict[int, float] = {}
    diversity_edges = 0
    for candidate in contenders:
        diversity[candidate], edges = _sparse_diversity_v2(
            candidate,
            forward_domain,
            state,
        )
        diversity_edges += edges
    contenders = _filter_best_relative_v2(
        contenders,
        diversity,
        float(epsilon),
    )
    chosen = min(
        contenders,
        key=lambda candidate: reference_domain.frame_uids[candidate],
    )

    for candidate in exact_candidates:
        conservative = float(
            np.nextafter(frontier.exact_scores[candidate], np.float64(np.inf))
        )
        heapq.heappush(
            frontier.heap,
            (-conservative, candidate, generation),
        )
    family_gains, total_coverage, _ = _total_coverage_gain_v2(
        chosen,
        forward_domain,
        state,
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
