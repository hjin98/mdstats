"""Public policy layer for exact periodic neighbor search.

The scientific neighbor contract remains owned by :mod:`mdstats.analysis._neighbors`.
This module selects an exact execution backend, resolves stateful cache use from
explicit frame semantics, optionally owns a persistent Verlet session, and records
deterministic diagnostics.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike

from ..collection import AtomisticFrameCollection
from ._cell_list import build_cell_list_neighbor_list_with_diagnostics
from ._neighbors import (
    CellListComplexityError,
    CellListOptions,
    NeighborListResult,
    NeighborSearchBackend,
    PairCounting,
    UnsafeNeighborCutoffError,
    build_neighbor_list,
)
from ._verlet_cache import NeighborSearchSession, VerletCacheOptions
from .cutoffs import PairCutoff

RequestedBackend = Literal["auto", "dense", "cell_list"]
CacheMode = Literal["auto", "none", "verlet"]
ResolvedFrameSemantics = Literal["single_frame", "trajectory", "ensemble"]

NEIGHBOR_SEARCH_DIAGNOSTIC_SCHEMA = "mdstats.periodic-neighbor-search.v2"
NEIGHBOR_SEARCH_REQUEST_SCHEMA = "mdstats.periodic-neighbor-request.v2"


@dataclass(frozen=True, slots=True)
class NeighborSearchOptions:
    """Stable high-level options for exact neighbor-search execution.

    ``backend='auto'`` uses the deterministic dense-pair-work threshold.
    ``cache_mode='auto'`` permits Verlet reuse only for multi-frame collections
    with explicit trajectory semantics. Independent ensembles remain stateless
    unless the caller explicitly requests ``cache_mode='verlet'``.
    """

    backend: RequestedBackend = "auto"
    cache_mode: CacheMode = "auto"
    skin: float = 0.5
    deformation_aware: bool = True
    dense_pair_threshold: int = 32_768
    minimum_cache_frames: int = 2
    max_consecutive_zero_reuse_rebuilds: int = 3
    safety_tolerance: float = 1.0e-12
    max_cell_condition_number: float = 1.0e12
    fallback_to_dense: bool = True
    cell_list_options: CellListOptions = field(default_factory=CellListOptions)

    def __post_init__(self) -> None:
        backend = str(self.backend)
        cache_mode = str(self.cache_mode)
        if backend not in {"auto", "dense", "cell_list"}:
            raise ValueError("backend must be 'auto', 'dense', or 'cell_list'.")
        if cache_mode not in {"auto", "none", "verlet"}:
            raise ValueError("cache_mode must be 'auto', 'none', or 'verlet'.")
        if not isinstance(self.deformation_aware, (bool, np.bool_)):
            raise TypeError("deformation_aware must be boolean.")
        if not isinstance(self.fallback_to_dense, (bool, np.bool_)):
            raise TypeError("fallback_to_dense must be boolean.")
        for name in (
            "dense_pair_threshold",
            "minimum_cache_frames",
            "max_consecutive_zero_reuse_rebuilds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise TypeError(f"{name} must be an integer.")
            if int(value) <= 0:
                raise ValueError(f"{name} must be positive.")
            object.__setattr__(self, name, int(value))
        skin = float(self.skin)
        tolerance = float(self.safety_tolerance)
        condition_limit = float(self.max_cell_condition_number)
        if not np.isfinite(skin) or skin <= 0.0:
            raise ValueError("skin must be positive and finite.")
        if not np.isfinite(tolerance) or tolerance < 0.0 or tolerance >= skin:
            raise ValueError(
                "safety_tolerance must be finite and satisfy 0 <= value < skin."
            )
        if not np.isfinite(condition_limit) or condition_limit <= 1.0:
            raise ValueError(
                "max_cell_condition_number must be finite and larger than one."
            )
        if not isinstance(self.cell_list_options, CellListOptions):
            raise TypeError("cell_list_options must be a CellListOptions instance.")
        object.__setattr__(self, "backend", backend)
        object.__setattr__(self, "cache_mode", cache_mode)
        object.__setattr__(self, "skin", skin)
        object.__setattr__(self, "deformation_aware", bool(self.deformation_aware))
        object.__setattr__(self, "safety_tolerance", tolerance)
        object.__setattr__(self, "max_cell_condition_number", condition_limit)
        object.__setattr__(self, "fallback_to_dense", bool(self.fallback_to_dense))

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "cache_mode": self.cache_mode,
            "skin": self.skin,
            "deformation_aware": self.deformation_aware,
            "dense_pair_threshold": self.dense_pair_threshold,
            "minimum_cache_frames": self.minimum_cache_frames,
            "max_consecutive_zero_reuse_rebuilds": (
                self.max_consecutive_zero_reuse_rebuilds
            ),
            "safety_tolerance": self.safety_tolerance,
            "max_cell_condition_number": self.max_cell_condition_number,
            "fallback_to_dense": self.fallback_to_dense,
            "cell_list_options": asdict(self.cell_list_options),
        }

    def to_verlet_options(self) -> VerletCacheOptions:
        return VerletCacheOptions(
            skin=self.skin,
            safety_tolerance=self.safety_tolerance,
            deformation_aware=self.deformation_aware,
            max_cell_condition_number=self.max_cell_condition_number,
            cell_list_options=self.cell_list_options,
        )


@dataclass(frozen=True, slots=True)
class NeighborRequestDiagnostics:
    request_digest: str
    estimated_dense_pair_work: int
    policy_backend: str
    frame_semantics: str
    cache_mode_requested: str
    cache_mode_selected: str
    cache_resolution_reason: str
    cache_disabled_during_run: bool
    cache_disable_reason: str | None
    consecutive_zero_reuse_rebuilds: int
    zero_reuse_rebuild_limit: int
    evaluations: int
    backend_counts: tuple[tuple[str, int], ...]
    candidate_pair_evaluations: int
    accepted_pairs: int
    fallback_events: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_digest": self.request_digest,
            "estimated_dense_pair_work": self.estimated_dense_pair_work,
            "policy_backend": self.policy_backend,
            "frame_semantics": self.frame_semantics,
            "cache_mode_requested": self.cache_mode_requested,
            "cache_mode_selected": self.cache_mode_selected,
            "cache_resolution_reason": self.cache_resolution_reason,
            "cache_disabled_during_run": self.cache_disabled_during_run,
            "cache_disable_reason": self.cache_disable_reason,
            "consecutive_zero_reuse_rebuilds": (self.consecutive_zero_reuse_rebuilds),
            "zero_reuse_rebuild_limit": self.zero_reuse_rebuild_limit,
            "evaluations": self.evaluations,
            "backend_counts": dict(self.backend_counts),
            "candidate_pair_evaluations": self.candidate_pair_evaluations,
            "accepted_pairs": self.accepted_pairs,
            "candidate_efficiency": (
                0.0
                if self.candidate_pair_evaluations == 0
                else self.accepted_pairs / self.candidate_pair_evaluations
            ),
            "fallback_events": dict(self.fallback_events),
        }


@dataclass(frozen=True, slots=True)
class NeighborSearchDiagnostics:
    options: NeighborSearchOptions
    selected_frame_count: int
    frame_semantics: ResolvedFrameSemantics
    requests: tuple[NeighborRequestDiagnostics, ...]
    cache_statistics: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        backend_counts: Counter[str] = Counter()
        fallback_events: Counter[str] = Counter()
        resolution_reasons: Counter[str] = Counter()
        disable_reasons: Counter[str] = Counter()
        candidates = 0
        accepted = 0
        evaluations = 0
        for request in self.requests:
            backend_counts.update(dict(request.backend_counts))
            fallback_events.update(dict(request.fallback_events))
            resolution_reasons[request.cache_resolution_reason] += 1
            if request.cache_disable_reason is not None:
                disable_reasons[request.cache_disable_reason] += 1
            candidates += request.candidate_pair_evaluations
            accepted += request.accepted_pairs
            evaluations += request.evaluations
        policy_values = sorted({request.policy_backend for request in self.requests})
        backend_policy = (
            policy_values[0]
            if len(policy_values) == 1
            else ("mixed" if policy_values else "none")
        )
        actual_values = sorted(
            {
                "cell_list"
                if name == NeighborSearchBackend.VERLET_CACHE.value
                else name
                for name, count in backend_counts.items()
                if count
            }
        )
        backend_selected = (
            actual_values[0]
            if len(actual_values) == 1
            else ("mixed" if actual_values else "none")
        )
        cache_selected_values = sorted({r.cache_mode_selected for r in self.requests})
        cache_selected = (
            cache_selected_values[0]
            if len(cache_selected_values) == 1
            else ("mixed" if cache_selected_values else "none")
        )
        payload: dict[str, Any] = {
            "schema": NEIGHBOR_SEARCH_DIAGNOSTIC_SCHEMA,
            "frame_semantics": self.frame_semantics,
            "backend_requested": self.options.backend,
            "backend_policy": backend_policy,
            "backend_selected": backend_selected,
            "cache_mode_requested": self.options.cache_mode,
            "cache_mode_selected": cache_selected,
            "cache_resolution_reasons": dict(sorted(resolution_reasons.items())),
            "cache_disabled_during_run": any(
                request.cache_disabled_during_run for request in self.requests
            ),
            "cache_disable_reasons": dict(sorted(disable_reasons.items())),
            "zero_reuse_rebuild_limit": (
                self.options.max_consecutive_zero_reuse_rebuilds
            ),
            "skin": self.options.skin,
            "selected_frame_count": self.selected_frame_count,
            "evaluations": evaluations,
            "request_digests": [request.request_digest for request in self.requests],
            "backend_counts": dict(sorted(backend_counts.items())),
            "candidate_pair_evaluations": candidates,
            "accepted_pairs": accepted,
            "candidate_efficiency": 0.0 if candidates == 0 else accepted / candidates,
            "fallback_events": dict(sorted(fallback_events.items())),
            "options": self.options.to_dict(),
            "requests": [request.to_dict() for request in self.requests],
            "cache_statistics": self.cache_statistics,
        }
        if self.cache_statistics is not None:
            payload.update(
                {
                    "cell_list_rebuild_count": self.cache_statistics["rebuilds"],
                    "cache_reuse_frame_count": self.cache_statistics[
                        "reuse_evaluations"
                    ],
                    "mean_frames_per_rebuild": self.cache_statistics[
                        "mean_evaluations_per_rebuild"
                    ],
                    "median_frames_per_rebuild": self.cache_statistics[
                        "median_evaluations_per_rebuild"
                    ],
                    "rebuild_reason_counts": self.cache_statistics["rebuild_reasons"],
                    "minimum_safety_margin_by_rebuild_interval": [
                        item["minimum_safety_margin"]
                        for item in self.cache_statistics["rebuild_intervals"]
                    ],
                    "minimum_singular_value_by_rebuild_interval": [
                        item["minimum_singular_value"]
                        for item in self.cache_statistics["rebuild_intervals"]
                    ],
                }
            )
        else:
            payload.update(
                {
                    "cell_list_rebuild_count": 0,
                    "cache_reuse_frame_count": 0,
                    "mean_frames_per_rebuild": 0.0,
                    "median_frames_per_rebuild": 0.0,
                    "rebuild_reason_counts": {},
                    "minimum_safety_margin_by_rebuild_interval": [],
                    "minimum_singular_value_by_rebuild_interval": [],
                }
            )
        return payload


@dataclass(slots=True)
class _MutableRequestDiagnostics:
    request_digest: str
    estimated_dense_pair_work: int
    policy_backend: str
    frame_semantics: ResolvedFrameSemantics
    cache_mode_requested: str
    cache_mode_selected: str
    cache_resolution_reason: str
    zero_reuse_rebuild_limit: int
    evaluations: int = 0
    backend_counts: Counter[str] = field(default_factory=Counter)
    candidate_pair_evaluations: int = 0
    accepted_pairs: int = 0
    fallback_events: Counter[str] = field(default_factory=Counter)
    cache_disabled_during_run: bool = False
    cache_disable_reason: str | None = None
    consecutive_zero_reuse_rebuilds: int = 0
    cache_interval_active: bool = False
    current_interval_had_reuse: bool = False

    def snapshot(self) -> NeighborRequestDiagnostics:
        return NeighborRequestDiagnostics(
            request_digest=self.request_digest,
            estimated_dense_pair_work=self.estimated_dense_pair_work,
            policy_backend=self.policy_backend,
            frame_semantics=self.frame_semantics,
            cache_mode_requested=self.cache_mode_requested,
            cache_mode_selected=self.cache_mode_selected,
            cache_resolution_reason=self.cache_resolution_reason,
            cache_disabled_during_run=self.cache_disabled_during_run,
            cache_disable_reason=self.cache_disable_reason,
            consecutive_zero_reuse_rebuilds=(self.consecutive_zero_reuse_rebuilds),
            zero_reuse_rebuild_limit=self.zero_reuse_rebuild_limit,
            evaluations=self.evaluations,
            backend_counts=tuple(sorted(self.backend_counts.items())),
            candidate_pair_evaluations=self.candidate_pair_evaluations,
            accepted_pairs=self.accepted_pairs,
            fallback_events=tuple(sorted(self.fallback_events.items())),
        )


class _NeighborSearchExecutor:
    """One analysis-local exact backend selector and optional cache owner."""

    def __init__(
        self,
        collection: AtomisticFrameCollection,
        *,
        options: NeighborSearchOptions | None,
        selected_frame_count: int,
    ) -> None:
        if not isinstance(collection, AtomisticFrameCollection):
            raise TypeError("collection must be an AtomisticFrameCollection.")
        self.collection = collection
        self.options = NeighborSearchOptions() if options is None else options
        if not isinstance(self.options, NeighborSearchOptions):
            raise TypeError(
                "neighbor_search_options must be a NeighborSearchOptions instance."
            )
        self.selected_frame_count = int(selected_frame_count)
        if self.selected_frame_count <= 0:
            raise ValueError("selected_frame_count must be positive.")
        self.frame_semantics = _resolved_frame_semantics(
            collection, selected_frame_count=self.selected_frame_count
        )
        self._session = NeighborSearchSession(
            collection, self.options.to_verlet_options()
        )
        self._records: dict[str, _MutableRequestDiagnostics] = {}
        self._dense_fallback_requests: set[str] = set()

    def build_neighbor_list(
        self,
        *,
        frame_index: int,
        center_indices: ArrayLike,
        candidate_neighbor_indices: ArrayLike,
        cutoff: float | PairCutoff,
        pair_counting: PairCounting = PairCounting.DIRECTED,
        block_size: int = 256,
    ) -> NeighborListResult:
        centers = np.asarray(center_indices, dtype=np.int64)
        candidates = np.asarray(candidate_neighbor_indices, dtype=np.int64)
        mode = PairCounting(pair_counting)
        work = _dense_pair_work(centers, candidates, mode)
        radius = float(cutoff.radius if isinstance(cutoff, PairCutoff) else cutoff)
        policy_backend = self._select_policy_backend(work)
        cache_selected, resolution_reason = self._resolve_cache_mode(policy_backend)
        digest = _policy_request_digest(
            centers=centers,
            candidates=candidates,
            pair_counting=mode,
            cutoff=radius,
            options=self.options,
            frame_semantics=self.frame_semantics,
        )
        record = self._records.setdefault(
            digest,
            _MutableRequestDiagnostics(
                request_digest=digest,
                estimated_dense_pair_work=work,
                policy_backend=policy_backend,
                frame_semantics=self.frame_semantics,
                cache_mode_requested=self.options.cache_mode,
                cache_mode_selected=cache_selected,
                cache_resolution_reason=resolution_reason,
                zero_reuse_rebuild_limit=(
                    self.options.max_consecutive_zero_reuse_rebuilds
                ),
            ),
        )
        if record.cache_disabled_during_run:
            cache_selected = "none"
        if digest in self._dense_fallback_requests:
            return self._evaluate_dense(
                record,
                frame_index=frame_index,
                centers=centers,
                candidates=candidates,
                cutoff=cutoff,
                mode=mode,
                block_size=block_size,
            )
        if policy_backend == "dense":
            return self._evaluate_dense(
                record,
                frame_index=frame_index,
                centers=centers,
                candidates=candidates,
                cutoff=cutoff,
                mode=mode,
                block_size=block_size,
            )
        try:
            if cache_selected == "verlet":
                before = self._session.statistics()
                result = self._session.build_neighbor_list(
                    frame_index=frame_index,
                    center_indices=centers,
                    candidate_neighbor_indices=candidates,
                    cutoff=cutoff,
                    pair_counting=mode,
                )
                after = self._session.statistics()
                record.candidate_pair_evaluations += (
                    after.candidate_pair_evaluations - before.candidate_pair_evaluations
                )
                record.accepted_pairs += after.accepted_pairs - before.accepted_pairs
                record.backend_counts[NeighborSearchBackend.VERLET_CACHE.value] += 1
                self._update_cache_reuse_state(record, before=before, after=after)
            else:
                result, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
                    self.collection,
                    frame_index=frame_index,
                    center_indices=centers,
                    candidate_neighbor_indices=candidates,
                    cutoff=cutoff,
                    pair_counting=mode,
                    options=self.options.cell_list_options,
                )
                record.candidate_pair_evaluations += diagnostics.exact_pair_evaluations
                record.accepted_pairs += diagnostics.accepted_pairs
                record.backend_counts[NeighborSearchBackend.CELL_LIST.value] += 1
            record.evaluations += 1
            return result
        except UnsafeNeighborCutoffError:
            if cache_selected != "verlet":
                raise
            self._disable_cache(
                record,
                reason="unsafe_list_radius",
                fallback_event="verlet_list_radius_unsafe_to_stateless",
            )
            result, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
                self.collection,
                frame_index=frame_index,
                center_indices=centers,
                candidate_neighbor_indices=candidates,
                cutoff=cutoff,
                pair_counting=mode,
                options=self.options.cell_list_options,
            )
            record.evaluations += 1
            record.backend_counts[NeighborSearchBackend.CELL_LIST.value] += 1
            record.candidate_pair_evaluations += diagnostics.exact_pair_evaluations
            record.accepted_pairs += diagnostics.accepted_pairs
            return result
        except CellListComplexityError:
            if self.options.backend != "auto" or not self.options.fallback_to_dense:
                raise
            self._dense_fallback_requests.add(digest)
            record.fallback_events["cell_list_complexity_to_dense"] += 1
            if record.backend_counts[NeighborSearchBackend.VERLET_CACHE.value] > 0:
                record.cache_mode_selected = "verlet_then_none"
            else:
                record.cache_mode_selected = "none"
            return self._evaluate_dense(
                record,
                frame_index=frame_index,
                centers=centers,
                candidates=candidates,
                cutoff=cutoff,
                mode=mode,
                block_size=block_size,
            )

    def diagnostics(self) -> NeighborSearchDiagnostics:
        cache_stats = self._session.statistics().to_dict()
        cache_payload = None if cache_stats["evaluations"] == 0 else cache_stats
        return NeighborSearchDiagnostics(
            options=self.options,
            selected_frame_count=self.selected_frame_count,
            frame_semantics=self.frame_semantics,
            requests=tuple(
                self._records[key].snapshot() for key in sorted(self._records)
            ),
            cache_statistics=cache_payload,
        )

    def _select_policy_backend(self, dense_pair_work: int) -> str:
        if self.options.backend == "dense":
            return "dense"
        if self.options.backend == "cell_list":
            return "cell_list"
        return (
            "dense"
            if dense_pair_work < self.options.dense_pair_threshold
            else "cell_list"
        )

    def _resolve_cache_mode(self, policy_backend: str) -> tuple[str, str]:
        if policy_backend != "cell_list":
            return "none", "backend_not_cell_list"
        if self.selected_frame_count == 1:
            return "none", "single_frame_stateless"
        if self.selected_frame_count < self.options.minimum_cache_frames:
            return "none", "insufficient_frames"
        if self.options.cache_mode == "none":
            return "none", "explicit_cache_disabled"
        if self.options.cache_mode == "verlet":
            return "verlet", "explicit_verlet_request"
        if self.frame_semantics == "trajectory":
            return "verlet", "trajectory_cache_eligible"
        return "none", "ensemble_default_stateless"

    def _update_cache_reuse_state(
        self,
        record: _MutableRequestDiagnostics,
        *,
        before: Any,
        after: Any,
    ) -> None:
        rebuild_delta = after.rebuilds - before.rebuilds
        reuse_delta = after.reuse_evaluations - before.reuse_evaluations
        if rebuild_delta not in {0, 1} or reuse_delta not in {0, 1}:
            raise RuntimeError(
                "One neighbor evaluation changed cache statistics invalidly."
            )
        if rebuild_delta == 1:
            if record.cache_interval_active:
                if record.current_interval_had_reuse:
                    record.consecutive_zero_reuse_rebuilds = 0
                else:
                    record.consecutive_zero_reuse_rebuilds += 1
            record.cache_interval_active = True
            record.current_interval_had_reuse = False
        elif reuse_delta == 1:
            record.current_interval_had_reuse = True
            record.consecutive_zero_reuse_rebuilds = 0
        else:
            raise RuntimeError("A Verlet evaluation was neither a rebuild nor a reuse.")

        if record.consecutive_zero_reuse_rebuilds >= record.zero_reuse_rebuild_limit:
            self._disable_cache(
                record,
                reason="repeated_zero_reuse",
                fallback_event="repeated_zero_reuse_to_stateless",
            )

    @staticmethod
    def _disable_cache(
        record: _MutableRequestDiagnostics,
        *,
        reason: str,
        fallback_event: str,
    ) -> None:
        if record.cache_disabled_during_run:
            return
        record.cache_disabled_during_run = True
        record.cache_disable_reason = reason
        record.fallback_events[fallback_event] += 1
        if record.backend_counts[NeighborSearchBackend.VERLET_CACHE.value] > 0:
            record.cache_mode_selected = "verlet_then_none"
        else:
            record.cache_mode_selected = "none"

    def _evaluate_dense(
        self,
        record: _MutableRequestDiagnostics,
        *,
        frame_index: int,
        centers: np.ndarray,
        candidates: np.ndarray,
        cutoff: float | PairCutoff,
        mode: PairCounting,
        block_size: int,
    ) -> NeighborListResult:
        result = build_neighbor_list(
            self.collection,
            frame_index=frame_index,
            center_indices=centers,
            candidate_neighbor_indices=candidates,
            cutoff=cutoff,
            pair_counting=mode,
            backend=NeighborSearchBackend.DENSE,
            block_size=block_size,
        )
        record.evaluations += 1
        record.backend_counts[NeighborSearchBackend.DENSE.value] += 1
        record.candidate_pair_evaluations += record.estimated_dense_pair_work
        record.accepted_pairs += result.n_pairs
        return result


def _resolved_frame_semantics(
    collection: AtomisticFrameCollection,
    *,
    selected_frame_count: int,
) -> ResolvedFrameSemantics:
    if selected_frame_count == 1:
        return "single_frame"
    if collection.is_trajectory:
        return "trajectory"
    return "ensemble"


def _dense_pair_work(
    centers: np.ndarray, candidates: np.ndarray, mode: PairCounting
) -> int:
    if mode is PairCounting.UNORDERED_IDENTICAL:
        n = int(centers.size)
        return n * (n - 1) // 2
    return int(centers.size * candidates.size)


def _policy_request_digest(
    *,
    centers: np.ndarray,
    candidates: np.ndarray,
    pair_counting: PairCounting,
    cutoff: float,
    options: NeighborSearchOptions,
    frame_semantics: ResolvedFrameSemantics,
) -> str:
    payload = {
        "schema": NEIGHBOR_SEARCH_REQUEST_SCHEMA,
        "centers": centers.tolist(),
        "candidates": candidates.tolist(),
        "pair_counting": pair_counting.value,
        "cutoff": float(cutoff).hex(),
        "frame_semantics": frame_semantics,
        "options": options.to_dict(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CacheMode",
    "NEIGHBOR_SEARCH_DIAGNOSTIC_SCHEMA",
    "NeighborRequestDiagnostics",
    "NeighborSearchDiagnostics",
    "NeighborSearchOptions",
    "RequestedBackend",
]
