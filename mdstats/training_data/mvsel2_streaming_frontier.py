"""Memory-bounded exact MVSEL2 Phase-B frontier reconstruction.

The scientific operation is identical to ``build_target_multi_view_lazy_frontier_v2``:
for every available candidate, accumulate the FP64 representative marginal in
canonical family order and seed the exact conservative lazy frontier.  The
execution order is transposed family-major so each family's mmap pages can be
released before the next family is scanned.  Per-candidate FP64 addition order
is unchanged.
"""
from __future__ import annotations

import heapq
from typing import Any

import numpy as np

from .target_multi_view_selector_v2 import (
    TargetMultiViewForwardStateV2,
    TargetMultiViewLazyFrontierV2,
    _drop_file_backed_pages_v2,
)


def build_target_multi_view_lazy_frontier_v2_streaming(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
) -> TargetMultiViewLazyFrontierV2:
    """Run the deterministic exact Phase-B rebase one family mmap at a time."""

    generation = int(state.selected_count)
    candidate_count = int(forward_domain.candidate_count)
    available = tuple(int(value) for value in np.flatnonzero(state.available))

    # Python float is an IEEE-754 double.  Keeping one scalar per candidate and
    # updating families in canonical order reproduces the original
    # ``gain += float(np.sum(..., dtype=float64))`` accumulation sequence.
    scores = [0.0] * candidate_count
    for family, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        for candidate in available:
            witnesses = np.asarray(
                family.candidate_witness_indices(candidate), dtype=np.int64
            )
            if witnesses.size == 0:
                continue
            family_gain = float(
                np.sum(
                    family_state.weights[witnesses]
                    / (
                        family_state.multiplicity[witnesses].astype(np.float64)
                        + 1.0
                    ),
                    dtype=np.float64,
                )
            )
            scores[candidate] += family_gain

        # The next family is independent.  Release the just-scanned file-backed
        # pages now instead of retaining the complete 9.5-billion-edge working
        # set until the end of the rebase.
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
