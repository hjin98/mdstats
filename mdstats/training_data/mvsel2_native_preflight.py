"""Bounded real-MVIDX worker preflight for the MVSEL2 native Phase-B backend.

The preflight is execution-only. It reuses the live Phase-B witness-term cache,
reads a deterministic sample of available candidate rows, verifies bitwise
worker-count parity on those real rows, and selects a parallel worker count only
when native shared-memory scaling is material.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np

from ._common import TrainingDataInputError
from .mvsel2_native_backend import qualify_mvsel2_native_backend_v2
from .mvsel2_phase_b_kernel import (
    _cache_for_state,
    _representative_gain_native_batch,
    _sync_terms,
)
from .target_multi_view_selector_v2 import TargetMultiViewForwardStateV2


@dataclass(frozen=True, slots=True)
class MVSEL2NativeWorkerMeterV2:
    workers: int
    elapsed_seconds: float
    forward_edges: int
    speedup_vs_one: float


@dataclass(frozen=True, slots=True)
class MVSEL2NativePreflightV2:
    requested_workers: int
    effective_workers: int
    sample_candidates: int
    forward_edges: int
    minimum_parallel_speedup: float
    best_parallel_speedup: float
    scaling_passed: bool
    meters: tuple[MVSEL2NativeWorkerMeterV2, ...]


def _candidate_sample(
    state: TargetMultiViewForwardStateV2,
    sample_size: int,
) -> tuple[int, ...]:
    available = np.flatnonzero(state.available)
    if available.size == 0:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native preflight has no available candidates."
        )
    size = min(int(sample_size), int(available.size))
    if size < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native preflight sample size must be positive."
        )
    if size == int(available.size):
        return tuple(int(value) for value in available)
    positions = np.linspace(
        0,
        int(available.size) - 1,
        num=size,
        dtype=np.int64,
    )
    return tuple(int(available[int(position)]) for position in positions)


def _score_vector(
    candidates: tuple[int, ...],
    scores: dict[int, float],
) -> np.ndarray:
    return np.asarray([scores[candidate] for candidate in candidates], dtype=np.float64)


def preflight_mvsel2_native_workers_v2(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    *,
    max_workers: int,
    sample_size: int = 256,
    minimum_parallel_speedup: float = 1.75,
) -> MVSEL2NativePreflightV2:
    """Meter 1/2/4/8/16 native workers on one deterministic real-graph sample."""

    max_workers = int(max_workers)
    if max_workers < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native preflight worker count must be positive."
        )
    if not np.isfinite(minimum_parallel_speedup) or minimum_parallel_speedup <= 1.0:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native preflight speedup threshold must exceed one."
        )
    if max_workers == 1:
        return MVSEL2NativePreflightV2(
            requested_workers=1,
            effective_workers=1,
            sample_candidates=0,
            forward_edges=0,
            minimum_parallel_speedup=float(minimum_parallel_speedup),
            best_parallel_speedup=1.0,
            scaling_passed=False,
            meters=(),
        )

    status = qualify_mvsel2_native_backend_v2()
    if not status.available or not status.qualified or not status.openmp:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native worker preflight requires a qualified "
            f"OpenMP backend; {status.reason or 'OpenMP unavailable'}."
        )

    worker_counts = tuple(
        value
        for value in (1, 2, 4, 8, 16)
        if value <= max_workers and value <= status.max_threads
    )
    if len(worker_counts) < 2:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native worker preflight has no qualified "
            "parallel worker count."
        )

    candidates = _candidate_sample(state, sample_size)
    cache = _cache_for_state(state)
    _sync_terms(cache, forward_domain, state)

    # Warm the exact sampled rows once so the worker comparison measures the
    # CPU/memory-parallel execution primitive rather than first-touch disk I/O.
    warm_scores, warm_edges = _representative_gain_native_batch(
        candidates,
        forward_domain,
        cache,
        workers=1,
    )
    reference = _score_vector(candidates, warm_scores)
    reference_bits = reference.view(np.uint64)

    meters: list[MVSEL2NativeWorkerMeterV2] = []
    baseline_elapsed: float | None = None
    expected_edges = int(warm_edges)
    for workers in worker_counts:
        best_elapsed = float("inf")
        for _ in range(2):
            started = time.perf_counter()
            scores, edges = _representative_gain_native_batch(
                candidates,
                forward_domain,
                cache,
                workers=workers,
            )
            elapsed = time.perf_counter() - started
            if int(edges) != expected_edges:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 native worker preflight edge count changed "
                    "across worker counts."
                )
            actual = _score_vector(candidates, scores)
            if not np.array_equal(actual.view(np.uint64), reference_bits):
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 native worker preflight changed exact "
                    "FP64 representative scores across worker counts."
                )
            best_elapsed = min(best_elapsed, elapsed)
        if workers == 1:
            baseline_elapsed = best_elapsed
        if baseline_elapsed is None:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 native worker preflight lost its serial baseline."
            )
        meters.append(
            MVSEL2NativeWorkerMeterV2(
                workers=workers,
                elapsed_seconds=best_elapsed,
                forward_edges=expected_edges,
                speedup_vs_one=baseline_elapsed / best_elapsed,
            )
        )

    parallel = tuple(item for item in meters if item.workers > 1)
    best = min(parallel, key=lambda item: (item.elapsed_seconds, item.workers))
    scaling_passed = best.speedup_vs_one >= float(minimum_parallel_speedup)
    effective = best.workers if scaling_passed else 1
    return MVSEL2NativePreflightV2(
        requested_workers=max_workers,
        effective_workers=effective,
        sample_candidates=len(candidates),
        forward_edges=expected_edges,
        minimum_parallel_speedup=float(minimum_parallel_speedup),
        best_parallel_speedup=float(best.speedup_vs_one),
        scaling_passed=scaling_passed,
        meters=tuple(meters),
    )


def format_mvsel2_native_preflight_v2(result: MVSEL2NativePreflightV2) -> str:
    meters = ",".join(
        f"{item.workers}w:{item.elapsed_seconds:.3f}s/{item.speedup_vs_one:.2f}x"
        for item in result.meters
    )
    return (
        f"sample={result.sample_candidates}; edges={result.forward_edges}; "
        f"meters={meters or 'none'}; best_parallel_speedup={result.best_parallel_speedup:.2f}x; "
        f"threshold={result.minimum_parallel_speedup:.2f}x; "
        f"scaling={'pass' if result.scaling_passed else 'fail'}; "
        f"effective_workers={result.effective_workers}"
    )
