"""Request-keyed Verlet candidate caching for fixed and deforming cells.

This private module implements stages S2-S3 of the neighbor-search acceleration
plan.  A :class:`NeighborSearchSession` builds an exact candidate list with the
S1 triclinic cell-list backend at ``physical_cutoff + skin`` and reuses those
canonical atom pairs while a proven completeness bound remains valid.

Algorithmic provenance
----------------------
The buffered candidate-list foundation is Verlet (1967),
DOI 10.1103/PhysRev.159.98.  Automatic displacement-based list updating is
closely associated with Chialvo and Debenedetti (1990),
DOI 10.1016/0010-4655(90)90007-N.  General parallelepiped and dynamically
deforming cell-list methods provide related context in Cui, Sun, and Qu (2009),
DOI 10.1007/s11434-009-0197-0, and Dobson, Fox, and Saracino (2016),
DOI 10.1016/j.jcp.2016.03.056.

The request-keyed immutable cache organization and the complete S3 criterion
combining the smallest singular value with species-resolved nonaffine endpoint
bounds are mdstats-specific derivations.  No cited work is claimed to contain
that complete variable-cell validity theorem.

The default policy preserves the stage-S2 fixed-cell rule.  Deformation-aware
reuse is explicit through ``VerletCacheOptions(deformation_aware=True)`` and
uses a smallest-singular-value affine bound plus species-resolved nonaffine
displacement maxima.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from ..collection import AtomisticFrameCollection
from ._cell_list import build_cell_list_neighbor_list
from ._neighbors import (
    CellListOptions,
    CoincidentAtomsError,
    FloatArray,
    IntArray,
    InvalidCellGeometryError,
    NeighborListResult,
    NeighborSearchBackend,
    PairCounting,
    _validate_selection_relation,
    _validated_cell_and_pbc,
    _validated_indices,
    _validated_single_frame_index,
    minimum_image_geometry,
    validate_cutoff,
)
from .cutoffs import PairCutoff

VERLET_REQUEST_SCHEMA = "mdstats.verlet-request.v2"
VERLET_CACHE_SCHEMA = "mdstats.verlet-cache.v2"
VERLET_DIGEST_ALGORITHM = "sha256"


class VerletCacheError(RuntimeError):
    """Base class for Verlet-cache failures."""


class InvalidVerletCacheOptionsError(VerletCacheError, ValueError):
    """Raised when Verlet-cache options are malformed."""


class IncompatibleVerletCacheError(VerletCacheError):
    """Raised when stored cache state is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class VerletCacheOptions:
    """Configuration for exact fixed- or variable-cell candidate reuse.

    Parameters
    ----------
    skin
        Positive Cartesian safety margin added to the physical cutoff.
    safety_tolerance
        Nonnegative numerical margin subtracted from the available skin before
        applying the rebuild criterion.  Rebuild occurs when
        ``2 * d_max >= skin - safety_tolerance``.
    deformation_aware
        When ``False`` (default), any exact cell-matrix change rebuilds the
        cache.  When ``True``, variable-cell reuse is permitted only while the
        singular-value/nonaffine safety margin remains strictly larger than
        ``safety_tolerance``.
    max_cell_condition_number
        Largest accepted 2-norm condition number for reference and current
        cells when deformation-aware reuse is enabled.  Larger values are
        rejected explicitly as numerically ill-conditioned.
    cell_list_options
        Exact S1 cell-list configuration used only on rebuild frames.
    """

    skin: float = 0.5
    safety_tolerance: float = 1.0e-12
    deformation_aware: bool = False
    max_cell_condition_number: float = 1.0e12
    cell_list_options: CellListOptions = field(default_factory=CellListOptions)

    def __post_init__(self) -> None:
        skin = float(self.skin)
        tolerance = float(self.safety_tolerance)
        condition_limit = float(self.max_cell_condition_number)
        if not np.isfinite(skin) or skin <= 0.0:
            raise InvalidVerletCacheOptionsError(
                "Verlet skin must be positive and finite."
            )
        if not np.isfinite(tolerance) or tolerance < 0.0:
            raise InvalidVerletCacheOptionsError(
                "safety_tolerance must be finite and nonnegative."
            )
        if tolerance >= skin:
            raise InvalidVerletCacheOptionsError(
                "safety_tolerance must be smaller than the Verlet skin."
            )
        if not isinstance(self.deformation_aware, (bool, np.bool_)):
            raise TypeError("deformation_aware must be boolean.")
        if not np.isfinite(condition_limit) or condition_limit <= 1.0:
            raise InvalidVerletCacheOptionsError(
                "max_cell_condition_number must be finite and larger than one."
            )
        if not isinstance(self.cell_list_options, CellListOptions):
            raise TypeError("cell_list_options must be a CellListOptions instance.")
        object.__setattr__(self, "skin", skin)
        object.__setattr__(self, "safety_tolerance", tolerance)
        object.__setattr__(self, "deformation_aware", bool(self.deformation_aware))
        object.__setattr__(self, "max_cell_condition_number", condition_limit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skin": self.skin,
            "safety_tolerance": self.safety_tolerance,
            "deformation_aware": self.deformation_aware,
            "max_cell_condition_number": self.max_cell_condition_number,
            "cell_list_options": asdict(self.cell_list_options),
        }


@dataclass(frozen=True, slots=True)
class NeighborCacheIntervalStatistics:
    """One cache-reference interval and its conservative validity diagnostics."""

    request_digest: str
    reference_frame_index: int
    last_frame_index: int
    evaluations: int
    reuse_evaluations: int
    candidate_pairs: int
    minimum_safety_margin: float | None
    minimum_singular_value: float | None
    terminal_rebuild_reason: str | None = None

    def __post_init__(self) -> None:
        digest = str(self.request_digest)
        if len(digest) != 64:
            raise ValueError("request_digest must be a SHA-256 hex digest.")
        for name in (
            "reference_frame_index",
            "last_frame_index",
            "evaluations",
            "reuse_evaluations",
            "candidate_pairs",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise TypeError(f"{name} must be an integer.")
            value = int(value)
            if value < 0:
                raise ValueError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.last_frame_index < self.reference_frame_index:
            raise ValueError("last_frame_index cannot precede reference_frame_index.")
        if self.evaluations <= 0:
            raise ValueError("A cache interval must contain at least one evaluation.")
        if self.reuse_evaluations > self.evaluations - 1:
            raise ValueError(
                "reuse_evaluations is inconsistent with interval evaluations."
            )
        for name in ("minimum_safety_margin", "minimum_singular_value"):
            value = getattr(self, name)
            if value is not None:
                value = float(value)
                if not np.isfinite(value):
                    raise ValueError(f"{name} must be finite when present.")
                object.__setattr__(self, name, value)
        if (
            self.minimum_singular_value is not None
            and self.minimum_singular_value <= 0.0
        ):
            raise ValueError("minimum_singular_value must be positive when present.")
        object.__setattr__(self, "request_digest", digest)
        object.__setattr__(
            self,
            "terminal_rebuild_reason",
            None
            if self.terminal_rebuild_reason is None
            else str(self.terminal_rebuild_reason),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_digest": self.request_digest,
            "reference_frame_index": self.reference_frame_index,
            "last_frame_index": self.last_frame_index,
            "evaluations": self.evaluations,
            "reuse_evaluations": self.reuse_evaluations,
            "candidate_pairs": self.candidate_pairs,
            "minimum_safety_margin": self.minimum_safety_margin,
            "minimum_singular_value": self.minimum_singular_value,
            "terminal_rebuild_reason": self.terminal_rebuild_reason,
        }


@dataclass(frozen=True, slots=True)
class NeighborCacheStatistics:
    """Immutable diagnostic snapshot for one session or request cache."""

    evaluations: int
    rebuilds: int
    reuse_evaluations: int
    candidate_pair_evaluations: int
    accepted_pairs: int
    current_candidate_pairs: int
    rebuild_reasons: tuple[tuple[str, int], ...]
    rebuild_intervals: tuple[NeighborCacheIntervalStatistics, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "evaluations",
            "rebuilds",
            "reuse_evaluations",
            "candidate_pair_evaluations",
            "accepted_pairs",
            "current_candidate_pairs",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise TypeError(f"{name} must be an integer.")
            value = int(value)
            if value < 0:
                raise ValueError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        reasons = tuple((str(name), int(count)) for name, count in self.rebuild_reasons)
        if any(count <= 0 for _, count in reasons):
            raise ValueError("Every rebuild-reason count must be positive.")
        if tuple(sorted(reasons)) != reasons:
            raise ValueError("rebuild_reasons must be lexicographically sorted.")
        if sum(count for _, count in reasons) != self.rebuilds:
            raise ValueError("Rebuild-reason counts must sum to rebuilds.")
        if self.rebuilds + self.reuse_evaluations != self.evaluations:
            raise ValueError("evaluations must equal rebuilds + reuse_evaluations.")
        intervals = tuple(self.rebuild_intervals)
        if any(
            not isinstance(item, NeighborCacheIntervalStatistics) for item in intervals
        ):
            raise TypeError("rebuild_intervals must contain interval statistics.")
        if len(intervals) != self.rebuilds:
            raise ValueError("Every rebuild must own exactly one cache interval.")
        if sum(item.evaluations for item in intervals) != self.evaluations:
            raise ValueError("Cache-interval evaluations must sum to evaluations.")
        object.__setattr__(self, "rebuild_reasons", reasons)
        object.__setattr__(self, "rebuild_intervals", intervals)

    @property
    def mean_evaluations_per_rebuild(self) -> float:
        if self.rebuilds == 0:
            return 0.0
        return float(self.evaluations / self.rebuilds)

    @property
    def median_evaluations_per_rebuild(self) -> float:
        if self.rebuilds == 0:
            return 0.0
        return float(np.median([item.evaluations for item in self.rebuild_intervals]))

    @property
    def acceptance_ratio(self) -> float:
        if self.candidate_pair_evaluations == 0:
            return 0.0
        return float(self.accepted_pairs / self.candidate_pair_evaluations)

    @property
    def minimum_safety_margin(self) -> float | None:
        values = [
            item.minimum_safety_margin
            for item in self.rebuild_intervals
            if item.minimum_safety_margin is not None
        ]
        return None if not values else float(min(values))

    @property
    def minimum_singular_value(self) -> float | None:
        values = [
            item.minimum_singular_value
            for item in self.rebuild_intervals
            if item.minimum_singular_value is not None
        ]
        return None if not values else float(min(values))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluations": self.evaluations,
            "rebuilds": self.rebuilds,
            "reuse_evaluations": self.reuse_evaluations,
            "candidate_pair_evaluations": self.candidate_pair_evaluations,
            "accepted_pairs": self.accepted_pairs,
            "current_candidate_pairs": self.current_candidate_pairs,
            "rebuild_reasons": dict(self.rebuild_reasons),
            "mean_evaluations_per_rebuild": self.mean_evaluations_per_rebuild,
            "median_evaluations_per_rebuild": self.median_evaluations_per_rebuild,
            "acceptance_ratio": self.acceptance_ratio,
            "minimum_safety_margin": self.minimum_safety_margin,
            "minimum_singular_value": self.minimum_singular_value,
            "rebuild_intervals": [item.to_dict() for item in self.rebuild_intervals],
        }


@dataclass(frozen=True, slots=True)
class VerletPairCache:
    """Immutable candidate-pair cache for one normalized neighbor request."""

    request_digest: str
    reference_frame_index: int
    selected_atom_indices: IntArray
    reference_wrapped_positions: FloatArray
    reference_fractional_positions: FloatArray
    reference_cell: FloatArray
    active_pair_atomic_numbers: IntArray
    active_pair_cutoffs: FloatArray
    center_indices: IntArray
    candidate_neighbor_indices: IntArray
    candidate_offsets: IntArray
    physical_cutoff: float
    list_cutoff: float
    pair_counting: PairCounting
    skin: float
    canonical_schema_version: str = VERLET_CACHE_SCHEMA

    def __post_init__(self) -> None:
        digest = str(self.request_digest)
        selected = np.asarray(self.selected_atom_indices, dtype=np.int64).copy()
        reference_positions = np.asarray(
            self.reference_wrapped_positions, dtype=float
        ).copy()
        reference_fractional = np.asarray(
            self.reference_fractional_positions, dtype=float
        ).copy()
        cell = np.asarray(self.reference_cell, dtype=float).copy()
        active_pairs = np.asarray(
            self.active_pair_atomic_numbers, dtype=np.int64
        ).copy()
        active_cutoffs = np.asarray(self.active_pair_cutoffs, dtype=float).copy()
        centers = np.asarray(self.center_indices, dtype=np.int64).copy()
        neighbors = np.asarray(self.candidate_neighbor_indices, dtype=np.int64).copy()
        offsets = np.asarray(self.candidate_offsets, dtype=np.int64).copy()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise IncompatibleVerletCacheError(
                "request_digest must be a lowercase SHA-256 hex digest."
            )
        if selected.ndim != 1 or centers.ndim != 1 or neighbors.ndim != 1:
            raise IncompatibleVerletCacheError(
                "Cache atom-index arrays must be one-dimensional."
            )
        if selected.size == 0 or np.any(np.diff(selected) <= 0):
            raise IncompatibleVerletCacheError(
                "selected_atom_indices must be nonempty and strictly increasing."
            )
        if reference_positions.shape != (selected.size, 3):
            raise IncompatibleVerletCacheError(
                "reference_wrapped_positions must match selected_atom_indices."
            )
        if reference_fractional.shape != (selected.size, 3):
            raise IncompatibleVerletCacheError(
                "reference_fractional_positions must match selected_atom_indices."
            )
        if np.any(~np.isfinite(reference_positions)) or np.any(
            ~np.isfinite(reference_fractional)
        ):
            raise IncompatibleVerletCacheError("Reference coordinates must be finite.")
        if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
            raise IncompatibleVerletCacheError(
                "reference_cell must be finite with shape (3, 3)."
            )
        if active_pairs.ndim != 2 or active_pairs.shape[1:] != (2,):
            raise IncompatibleVerletCacheError(
                "active_pair_atomic_numbers must have shape (n_pair_types, 2)."
            )
        if np.any(active_pairs <= 0) or np.any(active_pairs[:, 0] > active_pairs[:, 1]):
            raise IncompatibleVerletCacheError(
                "Active species pairs must be positive canonical atomic-number pairs."
            )
        if active_pairs.shape[0] > 1:
            order = np.lexsort((active_pairs[:, 1], active_pairs[:, 0]))
            if not np.array_equal(order, np.arange(active_pairs.shape[0])):
                raise IncompatibleVerletCacheError(
                    "active_pair_atomic_numbers must be lexicographically sorted."
                )
            if np.any(np.all(np.diff(active_pairs, axis=0) == 0, axis=1)):
                raise IncompatibleVerletCacheError(
                    "active_pair_atomic_numbers must not contain duplicates."
                )
        if active_cutoffs.shape != (active_pairs.shape[0],):
            raise IncompatibleVerletCacheError(
                "active_pair_cutoffs must match active_pair_atomic_numbers."
            )
        if np.any(~np.isfinite(active_cutoffs)) or np.any(active_cutoffs <= 0.0):
            raise IncompatibleVerletCacheError(
                "active_pair_cutoffs must be positive and finite."
            )
        if offsets.shape != (centers.size + 1,):
            raise IncompatibleVerletCacheError(
                "candidate_offsets must have shape (n_centers + 1,)."
            )
        if offsets[0] != 0 or offsets[-1] != neighbors.size:
            raise IncompatibleVerletCacheError(
                "candidate_offsets must span all cached candidates."
            )
        if np.any(np.diff(offsets) < 0):
            raise IncompatibleVerletCacheError(
                "candidate_offsets must be nondecreasing."
            )
        physical = float(self.physical_cutoff)
        list_cutoff = float(self.list_cutoff)
        skin = float(self.skin)
        if not np.isfinite(physical) or physical <= 0.0:
            raise IncompatibleVerletCacheError(
                "physical_cutoff must be positive and finite."
            )
        if not np.isfinite(list_cutoff) or list_cutoff <= physical:
            raise IncompatibleVerletCacheError(
                "list_cutoff must be finite and larger than physical_cutoff."
            )
        if not np.isclose(list_cutoff - physical, skin, rtol=0.0, atol=1.0e-14):
            raise IncompatibleVerletCacheError(
                "list_cutoff - physical_cutoff must equal skin."
            )
        frame = int(self.reference_frame_index)
        if frame < 0:
            raise IncompatibleVerletCacheError(
                "reference_frame_index must be nonnegative."
            )
        if self.canonical_schema_version != VERLET_CACHE_SCHEMA:
            raise IncompatibleVerletCacheError("Unsupported Verlet-cache schema.")
        for array in (
            selected,
            reference_positions,
            reference_fractional,
            cell,
            active_pairs,
            active_cutoffs,
            centers,
            neighbors,
            offsets,
        ):
            array.setflags(write=False)
        object.__setattr__(self, "request_digest", digest)
        object.__setattr__(self, "reference_frame_index", frame)
        object.__setattr__(self, "selected_atom_indices", selected)
        object.__setattr__(self, "reference_wrapped_positions", reference_positions)
        object.__setattr__(self, "reference_fractional_positions", reference_fractional)
        object.__setattr__(self, "reference_cell", cell)
        object.__setattr__(self, "active_pair_atomic_numbers", active_pairs)
        object.__setattr__(self, "active_pair_cutoffs", active_cutoffs)
        object.__setattr__(self, "center_indices", centers)
        object.__setattr__(self, "candidate_neighbor_indices", neighbors)
        object.__setattr__(self, "candidate_offsets", offsets)
        object.__setattr__(self, "physical_cutoff", physical)
        object.__setattr__(self, "list_cutoff", list_cutoff)
        object.__setattr__(self, "pair_counting", PairCounting(self.pair_counting))
        object.__setattr__(self, "skin", skin)

    @property
    def n_candidate_pairs(self) -> int:
        return int(self.candidate_neighbor_indices.size)

    def summary(self) -> dict[str, Any]:
        return {
            "request_digest": self.request_digest,
            "reference_frame_index": self.reference_frame_index,
            "n_selected_atoms": int(self.selected_atom_indices.size),
            "n_active_pair_types": int(self.active_pair_atomic_numbers.shape[0]),
            "active_pair_atomic_numbers": self.active_pair_atomic_numbers.tolist(),
            "active_pair_cutoffs": self.active_pair_cutoffs.tolist(),
            "n_centers": int(self.center_indices.size),
            "n_candidate_pairs": self.n_candidate_pairs,
            "physical_cutoff": self.physical_cutoff,
            "list_cutoff": self.list_cutoff,
            "skin": self.skin,
            "pair_counting": self.pair_counting.value,
            "canonical_schema_version": self.canonical_schema_version,
        }


@dataclass(slots=True)
class _MutableInterval:
    request_digest: str
    reference_frame_index: int
    last_frame_index: int
    candidate_pairs: int
    evaluations: int = 0
    reuse_evaluations: int = 0
    minimum_safety_margin: float | None = None
    minimum_singular_value: float | None = None
    terminal_rebuild_reason: str | None = None

    def update_metrics(
        self, *, safety_margin: float | None, singular_value: float | None
    ) -> None:
        if safety_margin is not None and np.isfinite(safety_margin):
            value = float(safety_margin)
            self.minimum_safety_margin = (
                value
                if self.minimum_safety_margin is None
                else min(self.minimum_safety_margin, value)
            )
        if (
            singular_value is not None
            and np.isfinite(singular_value)
            and singular_value > 0.0
        ):
            value = float(singular_value)
            self.minimum_singular_value = (
                value
                if self.minimum_singular_value is None
                else min(self.minimum_singular_value, value)
            )

    def snapshot(self) -> NeighborCacheIntervalStatistics:
        return NeighborCacheIntervalStatistics(
            request_digest=self.request_digest,
            reference_frame_index=self.reference_frame_index,
            last_frame_index=self.last_frame_index,
            evaluations=self.evaluations,
            reuse_evaluations=self.reuse_evaluations,
            candidate_pairs=self.candidate_pairs,
            minimum_safety_margin=self.minimum_safety_margin,
            minimum_singular_value=self.minimum_singular_value,
            terminal_rebuild_reason=self.terminal_rebuild_reason,
        )


@dataclass(slots=True)
class _MutableStatistics:
    evaluations: int = 0
    rebuilds: int = 0
    reuse_evaluations: int = 0
    candidate_pair_evaluations: int = 0
    accepted_pairs: int = 0
    current_candidate_pairs: int = 0
    rebuild_reasons: Counter[str] = field(default_factory=Counter)
    intervals: list[_MutableInterval] = field(default_factory=list)

    def snapshot(self) -> NeighborCacheStatistics:
        return NeighborCacheStatistics(
            evaluations=self.evaluations,
            rebuilds=self.rebuilds,
            reuse_evaluations=self.reuse_evaluations,
            candidate_pair_evaluations=self.candidate_pair_evaluations,
            accepted_pairs=self.accepted_pairs,
            current_candidate_pairs=self.current_candidate_pairs,
            rebuild_reasons=tuple(sorted(self.rebuild_reasons.items())),
            rebuild_intervals=tuple(interval.snapshot() for interval in self.intervals),
        )


class NeighborSearchSession:
    """Persistent request-keyed neighbor-search session.

    The session is bound to one :class:`AtomisticFrameCollection`.  It owns one
    immutable :class:`VerletPairCache` per exact normalized request digest.
    Sessions are intentionally not thread-safe; use one session per serial
    trajectory loop or one independent session per worker.
    """

    def __init__(
        self,
        collection: AtomisticFrameCollection,
        options: VerletCacheOptions | None = None,
    ) -> None:
        if not isinstance(collection, AtomisticFrameCollection):
            raise TypeError("collection must be an AtomisticFrameCollection.")
        self.collection = collection
        self.options = VerletCacheOptions() if options is None else options
        if not isinstance(self.options, VerletCacheOptions):
            raise TypeError("options must be a VerletCacheOptions instance.")
        self._caches: dict[str, VerletPairCache] = {}
        self._statistics: dict[str, _MutableStatistics] = {}

    @property
    def n_caches(self) -> int:
        return len(self._caches)

    @property
    def request_digests(self) -> tuple[str, ...]:
        return tuple(sorted(self._caches))

    def clear(self) -> None:
        """Discard all candidates and statistics owned by this session."""
        self._caches.clear()
        self._statistics.clear()

    def statistics(self, request_digest: str | None = None) -> NeighborCacheStatistics:
        """Return an immutable per-request or aggregate statistics snapshot."""
        if request_digest is not None:
            digest = str(request_digest)
            record = self._statistics.get(digest)
            if record is None:
                return NeighborCacheStatistics(0, 0, 0, 0, 0, 0, ())
            return record.snapshot()

        aggregate = _MutableStatistics()
        for digest in sorted(self._statistics):
            record = self._statistics[digest]
            aggregate.evaluations += record.evaluations
            aggregate.rebuilds += record.rebuilds
            aggregate.reuse_evaluations += record.reuse_evaluations
            aggregate.candidate_pair_evaluations += record.candidate_pair_evaluations
            aggregate.accepted_pairs += record.accepted_pairs
            aggregate.current_candidate_pairs += record.current_candidate_pairs
            aggregate.rebuild_reasons.update(record.rebuild_reasons)
            aggregate.intervals.extend(record.intervals)
        return aggregate.snapshot()

    def cache_for_request(self, request_digest: str) -> VerletPairCache:
        """Return the current immutable cache for an existing request digest."""
        try:
            return self._caches[str(request_digest)]
        except KeyError as exc:
            raise KeyError("No cache exists for the requested digest.") from exc

    def build_neighbor_list(
        self,
        *,
        frame_index: int,
        center_indices: ArrayLike,
        candidate_neighbor_indices: ArrayLike,
        cutoff: float | PairCutoff,
        pair_counting: PairCounting = PairCounting.DIRECTED,
    ) -> NeighborListResult:
        """Evaluate one request using a valid cache or an exact S1 rebuild."""
        frame = _validated_single_frame_index(self.collection, frame_index)
        centers = _validated_indices(
            center_indices,
            n_atoms=self.collection.n_atoms,
            name="center_indices",
        )
        candidates = _validated_indices(
            candidate_neighbor_indices,
            n_atoms=self.collection.n_atoms,
            name="candidate_neighbor_indices",
        )
        mode = PairCounting(pair_counting)
        _validate_selection_relation(centers, candidates, mode)
        physical_cutoff = validate_cutoff(
            cutoff,
            collection=self.collection,
            frame_indices=[frame],
        )
        # Classical Verlet buffering: build candidates at cutoff + skin and
        # filter them at the physical cutoff on every evaluation (Verlet, 1967,
        # DOI 10.1103/PhysRev.159.98).
        list_cutoff = physical_cutoff + self.options.skin
        digest = _request_digest(
            self.collection,
            centers=centers,
            candidates=candidates,
            pair_counting=mode,
            physical_cutoff=physical_cutoff,
            options=self.options,
        )
        record = self._statistics.setdefault(digest, _MutableStatistics())
        cache = self._caches.get(digest)
        rebuild_reason: str | None = None
        safety_margin: float | None = None
        singular_value: float | None = None
        if cache is None:
            rebuild_reason = "initial_build"
        elif self.options.deformation_aware:
            rebuild_reason, safety_margin, singular_value = _deformation_aware_validity(
                self.collection,
                frame_index=frame,
                cache=cache,
                options=self.options,
            )
        elif not np.array_equal(
            np.asarray(self.collection.cells[frame], dtype=float),
            cache.reference_cell,
        ):
            rebuild_reason = "cell_changed"
        else:
            displacement = _maximum_reference_displacement(
                self.collection,
                frame_index=frame,
                cache=cache,
            )
            # The two endpoints can close by at most twice the largest
            # reference-relative displacement.  This is the standard automatic
            # Verlet-list update logic discussed by Chialvo and Debenedetti
            # (1990), DOI 10.1016/0010-4655(90)90007-N.
            safety_margin = self.options.skin - 2.0 * displacement
            singular_value = 1.0
            if safety_margin <= self.options.safety_tolerance:
                rebuild_reason = "displacement_limit"

        if rebuild_reason is not None:
            if record.intervals and rebuild_reason != "initial_build":
                previous_interval = record.intervals[-1]
                previous_interval.update_metrics(
                    safety_margin=safety_margin,
                    singular_value=singular_value,
                )
                previous_interval.terminal_rebuild_reason = rebuild_reason
            cache = _rebuild_cache(
                self.collection,
                frame_index=frame,
                centers=centers,
                candidates=candidates,
                physical_cutoff=physical_cutoff,
                list_cutoff=list_cutoff,
                pair_counting=mode,
                request_digest=digest,
                options=self.options,
            )
            self._caches[digest] = cache
            record.rebuilds += 1
            record.rebuild_reasons[rebuild_reason] += 1
            record.current_candidate_pairs = cache.n_candidate_pairs
            record.intervals.append(
                _MutableInterval(
                    request_digest=digest,
                    reference_frame_index=frame,
                    last_frame_index=frame,
                    candidate_pairs=cache.n_candidate_pairs,
                    minimum_safety_margin=self.options.skin,
                    minimum_singular_value=1.0,
                )
            )
        else:
            record.reuse_evaluations += 1
            interval = record.intervals[-1]
            interval.reuse_evaluations += 1
            interval.update_metrics(
                safety_margin=safety_margin,
                singular_value=singular_value,
            )

        result = _evaluate_cached_pairs(
            self.collection,
            frame_index=frame,
            cache=cache,
        )
        record.evaluations += 1
        record.candidate_pair_evaluations += cache.n_candidate_pairs
        record.accepted_pairs += result.n_pairs
        interval = record.intervals[-1]
        interval.evaluations += 1
        interval.last_frame_index = frame
        return result


def _request_digest(
    collection: AtomisticFrameCollection,
    *,
    centers: IntArray,
    candidates: IntArray,
    pair_counting: PairCounting,
    physical_cutoff: float,
    options: VerletCacheOptions,
) -> str:
    payload = {
        "schema": VERLET_REQUEST_SCHEMA,
        "digest_algorithm": VERLET_DIGEST_ALGORITHM,
        "n_atoms": collection.n_atoms,
        "atomic_numbers": np.asarray(
            collection.atomic_numbers, dtype=np.int32
        ).tolist(),
        "pbc": np.asarray(collection.pbc, dtype=bool).tolist(),
        "center_indices": centers.tolist(),
        "candidate_neighbor_indices": candidates.tolist(),
        "pair_counting": pair_counting.value,
        "physical_cutoff": float(physical_cutoff).hex(),
        "skin": float(options.skin).hex(),
        "safety_tolerance": float(options.safety_tolerance).hex(),
        "deformation_aware": options.deformation_aware,
        "max_cell_condition_number": float(options.max_cell_condition_number).hex(),
        "cell_list_options": asdict(options.cell_list_options),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rebuild_cache(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    centers: IntArray,
    candidates: IntArray,
    physical_cutoff: float,
    list_cutoff: float,
    pair_counting: PairCounting,
    request_digest: str,
    options: VerletCacheOptions,
) -> VerletPairCache:
    if options.deformation_aware:
        _validate_deformation_cell(
            collection.cells[frame_index],
            max_condition_number=options.max_cell_condition_number,
            label=f"Frame {frame_index} cell",
        )
    candidate_result = build_cell_list_neighbor_list(
        collection,
        frame_index=frame_index,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=list_cutoff,
        pair_counting=pair_counting,
        options=options.cell_list_options,
    )
    selected = np.unique(np.concatenate((centers, candidates))).astype(
        np.int64, copy=False
    )
    reference_positions = np.asarray(
        collection.get_wrapped_positions(frame_index), dtype=float
    )[selected]
    reference_fractional = np.asarray(
        collection.fractional_positions[frame_index], dtype=float
    )[selected]
    cell, _ = _validated_cell_and_pbc(collection.cells[frame_index], collection.pbc)
    active_pairs = _active_species_pairs(
        collection,
        centers=centers,
        candidates=candidates,
    )
    active_cutoffs = np.full(active_pairs.shape[0], physical_cutoff, dtype=float)
    return VerletPairCache(
        request_digest=request_digest,
        reference_frame_index=frame_index,
        selected_atom_indices=selected,
        reference_wrapped_positions=reference_positions,
        reference_fractional_positions=reference_fractional,
        reference_cell=cell,
        active_pair_atomic_numbers=active_pairs,
        active_pair_cutoffs=active_cutoffs,
        center_indices=candidate_result.center_indices,
        candidate_neighbor_indices=candidate_result.neighbor_indices,
        candidate_offsets=candidate_result.offsets,
        physical_cutoff=physical_cutoff,
        list_cutoff=list_cutoff,
        pair_counting=pair_counting,
        skin=options.skin,
    )


def _active_species_pairs(
    collection: AtomisticFrameCollection,
    *,
    centers: IntArray,
    candidates: IntArray,
) -> IntArray:
    """Return sorted canonical species pairs that can occur in one request."""
    atomic_numbers = np.asarray(collection.atomic_numbers, dtype=np.int64)
    center_numbers = atomic_numbers[centers]
    candidate_numbers = atomic_numbers[candidates]
    pairs: set[tuple[int, int]] = set()

    if np.array_equal(centers, candidates):
        species, counts = np.unique(center_numbers, return_counts=True)
        for index, species_a in enumerate(species):
            for species_b in species[index:]:
                if species_a == species_b and counts[index] < 2:
                    continue
                pairs.add((int(species_a), int(species_b)))
    else:
        for species_a in np.unique(center_numbers):
            for species_b in np.unique(candidate_numbers):
                a = int(species_a)
                b = int(species_b)
                pairs.add((a, b) if a <= b else (b, a))

    return np.asarray(sorted(pairs), dtype=np.int64).reshape(-1, 2)


def _validate_deformation_cell(
    cell: ArrayLike,
    *,
    max_condition_number: float,
    label: str,
) -> tuple[FloatArray, float]:
    """Validate a cell for stable deformation-map and SVD evaluation."""
    matrix, _ = _validated_cell_and_pbc(cell, np.ones(3, dtype=bool))
    try:
        singular_values = np.linalg.svd(matrix, compute_uv=False)
    except np.linalg.LinAlgError as exc:
        raise InvalidCellGeometryError(f"{label} SVD did not converge.") from exc
    if singular_values.shape != (3,) or np.any(~np.isfinite(singular_values)):
        raise InvalidCellGeometryError(f"{label} has non-finite singular values.")
    smallest = float(singular_values[-1])
    largest = float(singular_values[0])
    if smallest <= 0.0:
        raise InvalidCellGeometryError(f"{label} is singular.")
    condition_number = largest / smallest
    if not np.isfinite(condition_number) or condition_number > max_condition_number:
        raise InvalidCellGeometryError(
            f"{label} is numerically ill-conditioned: 2-norm condition number "
            f"{condition_number:.8g} exceeds the configured limit "
            f"{max_condition_number:.8g}."
        )
    return matrix, float(condition_number)


def _species_displacement_maxima(
    atomic_numbers: IntArray,
    displacement_norms: FloatArray,
) -> dict[int, float]:
    """Return one maximum nonaffine displacement norm per selected species."""
    maxima: dict[int, float] = {}
    for species in np.unique(atomic_numbers):
        mask = atomic_numbers == species
        maxima[int(species)] = float(np.max(displacement_norms[mask]))
    return maxima


def _deformation_aware_validity(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    cache: VerletPairCache,
    options: VerletCacheOptions,
) -> tuple[str | None, float | None, float | None]:
    """Return rebuild reason, minimum raw safety margin, and sigma_min."""
    current_cell, _ = _validate_deformation_cell(
        collection.cells[frame_index],
        max_condition_number=options.max_cell_condition_number,
        label=f"Frame {frame_index} cell",
    )
    reference_cell, _ = _validate_deformation_cell(
        cache.reference_cell,
        max_condition_number=options.max_cell_condition_number,
        label="Reference cell",
    )

    if not collection.coordinates_are_time_unwrapped:
        if not np.array_equal(current_cell, reference_cell):
            return "fractional_unwrapping_unavailable", None, None
        displacement = _maximum_reference_displacement(
            collection,
            frame_index=frame_index,
            cache=cache,
        )
        margin = options.skin - 2.0 * displacement
        reason = "displacement_limit" if margin <= options.safety_tolerance else None
        return reason, float(margin), 1.0

    fractional = np.asarray(collection.fractional_positions[frame_index], dtype=float)
    if fractional.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(fractional)):
        raise InvalidCellGeometryError(
            f"Frame {frame_index} fractional positions must be finite with shape "
            "(n_atoms, 3)."
        )

    try:
        deformation = np.linalg.solve(reference_cell, current_cell)
        singular_values = np.linalg.svd(deformation, compute_uv=False)
    except np.linalg.LinAlgError as exc:
        raise InvalidCellGeometryError(
            f"Could not evaluate the frame-{frame_index} deformation map."
        ) from exc
    if singular_values.shape != (3,) or np.any(~np.isfinite(singular_values)):
        return "nonfinite_deformation_margin", None, None
    sigma_min = float(singular_values[-1])
    if sigma_min <= 0.0 or not np.isfinite(sigma_min):
        return "nonfinite_deformation_margin", None, None

    current_fractional = fractional[cache.selected_atom_indices]
    delta_fractional = current_fractional - cache.reference_fractional_positions
    nonaffine_vectors = delta_fractional @ current_cell
    nonaffine_norms = np.linalg.norm(nonaffine_vectors, axis=1)
    if np.any(~np.isfinite(nonaffine_norms)):
        return "nonfinite_deformation_margin", None, sigma_min

    selected_numbers = np.asarray(
        collection.atomic_numbers[cache.selected_atom_indices], dtype=np.int64
    )
    if cache.active_pair_atomic_numbers.shape[0] == 0:
        return None, None, sigma_min
    displacement_maxima = _species_displacement_maxima(
        selected_numbers,
        np.asarray(nonaffine_norms, dtype=float),
    )
    # mdstats S3 theorem: affine contraction is bounded with sigma_min,
    # then species-resolved nonaffine endpoint budgets are subtracted.  This
    # complete criterion is a package-specific derivation; Cui et al. (2009)
    # and Dobson et al. (2016) are related variable-cell prior art, not sources
    # for this exact formula.
    affine_margins = (
        sigma_min * (cache.active_pair_cutoffs + cache.skin) - cache.active_pair_cutoffs
    )
    endpoint_bounds = np.asarray(
        [
            displacement_maxima[int(species_a)] + displacement_maxima[int(species_b)]
            for species_a, species_b in cache.active_pair_atomic_numbers
        ],
        dtype=float,
    )
    margins = affine_margins - endpoint_bounds
    if np.any(~np.isfinite(affine_margins)) or np.any(~np.isfinite(margins)):
        return "nonfinite_deformation_margin", None, sigma_min
    minimum_margin = float(np.min(margins))
    if minimum_margin > options.safety_tolerance:
        return None, minimum_margin, sigma_min
    if np.any(affine_margins <= options.safety_tolerance):
        return "cell_deformation_limit", minimum_margin, sigma_min
    return "nonaffine_displacement_limit", minimum_margin, sigma_min


def _maximum_reference_displacement(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    cache: VerletPairCache,
) -> float:
    positions = np.asarray(collection.get_wrapped_positions(frame_index), dtype=float)
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise InvalidCellGeometryError(
            f"Frame {frame_index} positions must be finite with shape (n_atoms, 3)."
        )
    current = positions[cache.selected_atom_indices]
    raw = current - cache.reference_wrapped_positions
    _, distances, _ = minimum_image_geometry(
        raw,
        cell=cache.reference_cell,
        pbc=collection.pbc,
    )
    if distances.size == 0:
        return 0.0
    return float(np.max(distances))


def _evaluate_cached_pairs(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    cache: VerletPairCache,
) -> NeighborListResult:
    positions = np.asarray(collection.get_wrapped_positions(frame_index), dtype=float)
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise InvalidCellGeometryError(
            f"Frame {frame_index} positions must be finite with shape (n_atoms, 3)."
        )
    cell, pbc = _validated_cell_and_pbc(collection.cells[frame_index], collection.pbc)
    row_counts = np.zeros(cache.center_indices.size, dtype=np.int64)
    neighbor_chunks: list[IntArray] = []
    vector_chunks: list[FloatArray] = []
    distance_chunks: list[FloatArray] = []
    shift_chunks: list[IntArray] = []
    zero_tolerance = max(
        1.0e-12,
        np.finfo(float).eps * max(1.0, cache.physical_cutoff) * 64.0,
    )

    for row, center_atom in enumerate(cache.center_indices):
        start = int(cache.candidate_offsets[row])
        stop = int(cache.candidate_offsets[row + 1])
        row_candidates = cache.candidate_neighbor_indices[start:stop]
        if row_candidates.size == 0:
            continue
        raw = positions[row_candidates] - positions[int(center_atom)]
        vectors, distances, shifts = minimum_image_geometry(raw, cell=cell, pbc=pbc)
        mask = distances < cache.physical_cutoff
        coincident = mask & (distances <= zero_tolerance)
        if np.any(coincident):
            bad_neighbor = int(row_candidates[np.flatnonzero(coincident)[0]])
            raise CoincidentAtomsError(
                f"Distinct selected atoms {int(center_atom)} and {bad_neighbor} "
                f"are coincident in frame {frame_index}."
            )
        accepted_neighbors = row_candidates[mask]
        row_counts[row] = accepted_neighbors.size
        if accepted_neighbors.size:
            neighbor_chunks.append(np.asarray(accepted_neighbors, dtype=np.int64))
            vector_chunks.append(np.asarray(vectors[mask], dtype=float))
            distance_chunks.append(np.asarray(distances[mask], dtype=float))
            shift_chunks.append(np.asarray(shifts[mask], dtype=np.int64))

    offsets = np.empty(cache.center_indices.size + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(row_counts, out=offsets[1:])
    neighbors = (
        np.concatenate(neighbor_chunks)
        if neighbor_chunks
        else np.empty(0, dtype=np.int64)
    )
    vectors = (
        np.concatenate(vector_chunks, axis=0)
        if vector_chunks
        else np.empty((0, 3), dtype=float)
    )
    distances = (
        np.concatenate(distance_chunks) if distance_chunks else np.empty(0, dtype=float)
    )
    shifts = (
        np.concatenate(shift_chunks, axis=0)
        if shift_chunks
        else np.empty((0, 3), dtype=np.int64)
    )
    return NeighborListResult(
        frame_index=frame_index,
        center_indices=cache.center_indices,
        neighbor_indices=neighbors,
        offsets=offsets,
        vectors=vectors,
        distances=distances,
        image_shifts=shifts,
        cutoff=cache.physical_cutoff,
        pair_counting=cache.pair_counting,
        backend=NeighborSearchBackend.VERLET_CACHE,
    )
