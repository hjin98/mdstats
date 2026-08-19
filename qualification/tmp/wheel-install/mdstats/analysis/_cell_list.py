"""Exact single-frame triclinic cell-list candidate generation.

This private module implements stage S1 of the neighbor-search acceleration
plan.  It uses a possibly Minkowski-reduced internal lattice basis, fractional
linked cells, and a metric-aware bin-offset stencil to generate a conservative
candidate set.  Every candidate pair is then evaluated with the authoritative
minimum-image routine in the original cell, so the scientific result and image
shift convention remain identical to the dense oracle.

Algorithmic provenance
----------------------
The linked-cell foundation follows Quentrec and Brot (1973),
DOI 10.1016/0021-9991(73)90046-6.  General-periodic-box pair-list and
metric-search context is provided by Heinz and Huenenberger (2004),
DOI 10.1002/jcc.20071; Cui, Sun, and Qu (2009),
DOI 10.1007/s11434-009-0197-0; and Rogers (2016),
DOI 10.1016/j.jmgm.2016.07.004.

The optional search-basis reduction calls ASE (Larsen et al., 2017,
DOI 10.1088/1361-648X/aa680e).  ASE's low-dimensional Minkowski-reduction
implementation follows Nguyen and Stehle (2009),
DOI 10.1145/1597036.1597050.

The perpendicular-height bin policy, exact active-set minimization over each
fractional bin-offset box, deterministic candidate normalization, and final
original-basis image recovery are mdstats-specific adaptations; the references
above are not claimed as sources for those details.

No trajectory cache or Verlet reuse is implemented here.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from dataclasses import dataclass
from itertools import product

import numpy as np
from ase.geometry import minkowski_reduce
from numpy.typing import ArrayLike

from ..collection import AtomisticFrameCollection
from ._neighbors import (
    BoolArray,
    CellListComplexityError,
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


@dataclass(frozen=True, slots=True)
class CellListPlan:
    """Immutable geometric plan for one frame and one list radius."""

    search_cell: FloatArray
    basis_transform: IntArray
    inverse_basis_transform: IntArray
    pbc: BoolArray
    bin_counts: IntArray
    bin_origins: FloatArray
    bin_widths: FloatArray
    stencil_offsets: IntArray
    reduction_applied: bool

    def __post_init__(self) -> None:
        search_cell = np.asarray(self.search_cell, dtype=float).copy()
        transform = np.asarray(self.basis_transform, dtype=np.int64).copy()
        inverse = np.asarray(self.inverse_basis_transform, dtype=np.int64).copy()
        pbc = np.asarray(self.pbc, dtype=bool).copy()
        counts = np.asarray(self.bin_counts, dtype=np.int64).copy()
        origins = np.asarray(self.bin_origins, dtype=float).copy()
        widths = np.asarray(self.bin_widths, dtype=float).copy()
        stencil = np.asarray(self.stencil_offsets, dtype=np.int64).copy()
        if search_cell.shape != (3, 3):
            raise ValueError("search_cell must have shape (3, 3).")
        if transform.shape != (3, 3) or inverse.shape != (3, 3):
            raise ValueError("Basis transforms must have shape (3, 3).")
        if pbc.shape != (3,) or counts.shape != (3,):
            raise ValueError("pbc and bin_counts must have shape (3,).")
        if origins.shape != (3,) or widths.shape != (3,):
            raise ValueError("bin_origins and bin_widths must have shape (3,).")
        if stencil.ndim != 2 or stencil.shape[1:] != (3,):
            raise ValueError("stencil_offsets must have shape (n_offsets, 3).")
        if np.any(counts <= 0) or np.any(widths <= 0.0):
            raise ValueError("Cell-list bin counts and widths must be positive.")
        for array in (
            search_cell,
            transform,
            inverse,
            pbc,
            counts,
            origins,
            widths,
            stencil,
        ):
            array.setflags(write=False)
        object.__setattr__(self, "search_cell", search_cell)
        object.__setattr__(self, "basis_transform", transform)
        object.__setattr__(self, "inverse_basis_transform", inverse)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "bin_counts", counts)
        object.__setattr__(self, "bin_origins", origins)
        object.__setattr__(self, "bin_widths", widths)
        object.__setattr__(self, "stencil_offsets", stencil)

    @property
    def stencil_size(self) -> int:
        return int(self.stencil_offsets.shape[0])


@dataclass(frozen=True, slots=True)
class CellListDiagnostics:
    """Deterministic diagnostics for S1 verification and benchmarking."""

    reduction_applied: bool
    bin_counts: tuple[int, int, int]
    stencil_size: int
    occupied_candidate_bins: int
    bin_visits: int
    unique_candidate_pairs: int
    exact_pair_evaluations: int
    accepted_pairs: int



@lru_cache(maxsize=256)
def _cached_periodic_cell_list_plan(
    cell_bytes: bytes,
    pbc_tuple: tuple[bool, bool, bool],
    cutoff: float,
    options: CellListOptions,
) -> CellListPlan:
    """Cache cell-only plan/stencil work for fully periodic fixed cells."""

    cell = np.frombuffer(cell_bytes, dtype=np.float64).reshape(3, 3).copy()
    pbc = np.asarray(pbc_tuple, dtype=np.bool_)
    transform, inverse_transform, search_cell, reduction_applied = _prepare_search_basis(
        cell, pbc, options
    )
    # For a fully periodic box, bin origins/counts and the metric stencil depend
    # only on cell geometry, cutoff, and policy; particle coordinates are not
    # consulted by ``prepare_cell_list_plan`` on periodic axes.
    return prepare_cell_list_plan(
        np.zeros((1, 3), dtype=np.float64),
        search_cell=search_cell,
        basis_transform=transform,
        inverse_basis_transform=inverse_transform,
        pbc=pbc,
        cutoff=float(cutoff),
        options=options,
        reduction_applied=reduction_applied,
    )


def build_cell_list_neighbor_list(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: float | PairCutoff,
    pair_counting: PairCounting = PairCounting.DIRECTED,
    options: CellListOptions | None = None,
) -> NeighborListResult:
    """Build one exact CSR neighbor list with the S1 cell-list backend."""
    result, _ = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=frame_index,
        center_indices=center_indices,
        candidate_neighbor_indices=candidate_neighbor_indices,
        cutoff=cutoff,
        pair_counting=pair_counting,
        options=options,
    )
    return result


def build_cell_list_neighbor_list_with_diagnostics(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: float | PairCutoff,
    pair_counting: PairCounting = PairCounting.DIRECTED,
    options: CellListOptions | None = None,
) -> tuple[NeighborListResult, CellListDiagnostics]:
    """Build a cell-list result and return transparent search diagnostics."""
    frame = _validated_single_frame_index(collection, frame_index)
    centers = _validated_indices(
        center_indices, n_atoms=collection.n_atoms, name="center_indices"
    )
    candidates = _validated_indices(
        candidate_neighbor_indices,
        n_atoms=collection.n_atoms,
        name="candidate_neighbor_indices",
    )
    mode = PairCounting(pair_counting)
    _validate_selection_relation(centers, candidates, mode)
    policy = CellListOptions() if options is None else options
    radius = validate_cutoff(cutoff, collection=collection, frame_indices=[frame])

    positions = np.asarray(collection.get_wrapped_positions(frame), dtype=float)
    original_fractional = np.asarray(
        collection.get_wrapped_fractional_positions(frame), dtype=float
    )
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise InvalidCellGeometryError(
            f"Frame {frame} positions must be finite with shape (n_atoms, 3)."
        )
    if original_fractional.shape != (collection.n_atoms, 3) or np.any(
        ~np.isfinite(original_fractional)
    ):
        raise InvalidCellGeometryError(
            f"Frame {frame} fractional positions must be finite with shape "
            "(n_atoms, 3)."
        )
    cell, pbc = _validated_cell_and_pbc(collection.cells[frame], collection.pbc)

    if bool(np.all(pbc)):
        plan = _cached_periodic_cell_list_plan(
            np.ascontiguousarray(cell, dtype=np.float64).tobytes(),
            tuple(bool(value) for value in pbc),
            float(radius),
            policy,
        )
        inverse_transform = plan.inverse_basis_transform
    else:
        transform, inverse_transform, search_cell, reduction_applied = (
            _prepare_search_basis(cell, pbc, policy)
        )
    search_fractional = original_fractional @ inverse_transform
    search_fractional = np.asarray(search_fractional, dtype=float)
    for axis, periodic in enumerate(pbc):
        if periodic:
            search_fractional[:, axis] -= np.floor(search_fractional[:, axis])

    if not bool(np.all(pbc)):
        selected = np.unique(np.concatenate((centers, candidates)))
        plan = prepare_cell_list_plan(
            search_fractional[selected],
            search_cell=search_cell,
            basis_transform=transform,
            inverse_basis_transform=inverse_transform,
            pbc=pbc,
            cutoff=radius,
            options=policy,
            reduction_applied=reduction_applied,
        )
    all_bin_indices = assign_fractional_bins(search_fractional, plan)

    candidate_bin_coordinates = all_bin_indices[candidates]
    candidate_bin_flat = np.ravel_multi_index(
        (
            candidate_bin_coordinates[:, 0],
            candidate_bin_coordinates[:, 1],
            candidate_bin_coordinates[:, 2],
        ),
        tuple(int(value) for value in plan.bin_counts),
        order="C",
    ).astype(np.int64, copy=False)
    candidate_sort = np.argsort(candidate_bin_flat, kind="stable")
    sorted_candidate_bin_flat = candidate_bin_flat[candidate_sort]
    sorted_candidate_slots = candidate_sort.astype(np.int64, copy=False)

    neighbor_chunks: list[IntArray] = []
    vector_chunks: list[FloatArray] = []
    distance_chunks: list[FloatArray] = []
    shift_chunks: list[IntArray] = []
    row_counts = np.zeros(centers.size, dtype=np.int64)
    zero_tolerance = max(1.0e-12, np.finfo(float).eps * max(1.0, radius) * 64.0)
    bin_visits = 0
    unique_candidate_pairs = 0
    exact_pair_evaluations = 0

    # Candidate-bin queries are expanded in bounded center batches.  All work
    # inside one batch—periodic wrapping, occupied-bin lookup, ragged range
    # expansion, pair deduplication, and exact MIC evaluation—is performed by
    # NumPy kernels.  Python only orchestrates coarse batches.
    maximum_query_entries = max(1, min(policy.max_stencil_candidates, 1_000_000))
    center_batch_size = max(1, maximum_query_entries // max(1, plan.stencil_size))
    shape_tuple = tuple(int(value) for value in plan.bin_counts)
    shape_array = np.asarray(plan.bin_counts, dtype=np.int64)
    stencil = np.asarray(plan.stencil_offsets, dtype=np.int64)
    for center_start in range(0, centers.size, center_batch_size):
        center_stop = min(centers.size, center_start + center_batch_size)
        batch_rows = np.arange(center_start, center_stop, dtype=np.int64)
        batch_bins = all_bin_indices[centers[batch_rows]]
        targets = batch_bins[:, None, :] + stencil[None, :, :]
        valid = np.ones(targets.shape[:2], dtype=bool)
        for axis in range(3):
            if plan.pbc[axis]:
                targets[:, :, axis] %= shape_array[axis]
            else:
                valid &= (targets[:, :, axis] >= 0) & (
                    targets[:, :, axis] < shape_array[axis]
                )
        query_rows = np.broadcast_to(
            batch_rows[:, None], valid.shape
        )[valid]
        query_targets = targets[valid]
        bin_visits += int(query_targets.shape[0])
        if query_targets.size == 0:
            continue
        query_flat = np.ravel_multi_index(
            (
                query_targets[:, 0],
                query_targets[:, 1],
                query_targets[:, 2],
            ),
            shape_tuple,
            order="C",
        ).astype(np.int64, copy=False)
        lower = np.searchsorted(sorted_candidate_bin_flat, query_flat, side="left")
        upper = np.searchsorted(sorted_candidate_bin_flat, query_flat, side="right")
        lengths = upper - lower
        occupied = lengths > 0
        if not np.any(occupied):
            continue
        occupied_rows = query_rows[occupied]
        occupied_lower = lower[occupied]
        occupied_lengths = lengths[occupied]
        total_expanded = int(np.sum(occupied_lengths, dtype=np.int64))
        segment_ends = np.cumsum(occupied_lengths, dtype=np.int64)
        segment_starts = segment_ends - occupied_lengths
        expanded_segments = np.repeat(
            np.arange(occupied_lengths.size, dtype=np.int64), occupied_lengths
        )
        within_segment = np.arange(total_expanded, dtype=np.int64) - np.repeat(
            segment_starts, occupied_lengths
        )
        candidate_positions = occupied_lower[expanded_segments] + within_segment
        pair_rows = occupied_rows[expanded_segments]
        pair_slots = sorted_candidate_slots[candidate_positions]
        pair_codes = pair_rows * candidates.size + pair_slots
        pair_codes = np.unique(pair_codes)
        pair_rows = pair_codes // candidates.size
        pair_slots = pair_codes % candidates.size
        row_candidates = candidates[pair_slots]
        center_atoms = centers[pair_rows]
        keep = row_candidates != center_atoms
        if mode is PairCounting.UNORDERED_IDENTICAL:
            keep &= center_atoms < row_candidates
        pair_rows = pair_rows[keep]
        row_candidates = row_candidates[keep]
        center_atoms = center_atoms[keep]
        if row_candidates.size == 0:
            continue

        unique_candidate_pairs += int(row_candidates.size)
        raw = positions[row_candidates] - positions[center_atoms]
        row_vectors, row_distances, row_shifts = minimum_image_geometry(
            raw, cell=cell, pbc=pbc
        )
        exact_pair_evaluations += int(row_candidates.size)
        accepted = row_distances < radius
        coincident = accepted & (row_distances <= zero_tolerance)
        if np.any(coincident):
            bad = int(np.flatnonzero(coincident)[0])
            raise CoincidentAtomsError(
                f"Distinct selected atoms {int(center_atoms[bad])} and "
                f"{int(row_candidates[bad])} are coincident in frame {frame}."
            )
        if not np.any(accepted):
            continue
        accepted_rows = pair_rows[accepted]
        row_counts += np.bincount(
            accepted_rows, minlength=centers.size
        ).astype(np.int64, copy=False)
        neighbor_chunks.append(np.asarray(row_candidates[accepted], dtype=np.int64))
        vector_chunks.append(np.asarray(row_vectors[accepted], dtype=float))
        distance_chunks.append(np.asarray(row_distances[accepted], dtype=float))
        shift_chunks.append(np.asarray(row_shifts[accepted], dtype=np.int64))

    offsets = np.empty(centers.size + 1, dtype=np.int64)
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
    image_shifts = (
        np.concatenate(shift_chunks, axis=0)
        if shift_chunks
        else np.empty((0, 3), dtype=np.int64)
    )
    result = NeighborListResult(
        frame_index=frame,
        center_indices=centers,
        neighbor_indices=neighbors,
        offsets=offsets,
        vectors=vectors,
        distances=distances,
        image_shifts=image_shifts,
        cutoff=radius,
        pair_counting=mode,
        backend=NeighborSearchBackend.CELL_LIST,
    )
    diagnostics = CellListDiagnostics(
        reduction_applied=plan.reduction_applied,
        bin_counts=tuple(int(value) for value in plan.bin_counts),
        stencil_size=plan.stencil_size,
        occupied_candidate_bins=int(np.unique(candidate_bin_flat).size),
        bin_visits=bin_visits,
        unique_candidate_pairs=unique_candidate_pairs,
        exact_pair_evaluations=exact_pair_evaluations,
        accepted_pairs=result.n_pairs,
    )
    return result, diagnostics


def prepare_cell_list_plan(
    selected_search_fractional: ArrayLike,
    *,
    search_cell: ArrayLike,
    basis_transform: ArrayLike,
    inverse_basis_transform: ArrayLike,
    pbc: ArrayLike,
    cutoff: float,
    options: CellListOptions,
    reduction_applied: bool,
) -> CellListPlan:
    """Prepare bin geometry and the exact metric-aware offset stencil."""
    fractional = np.asarray(selected_search_fractional, dtype=float)
    if fractional.ndim != 2 or fractional.shape[1] != 3 or fractional.shape[0] == 0:
        raise ValueError("selected_search_fractional must have shape (n, 3), n > 0.")
    if np.any(~np.isfinite(fractional)):
        raise ValueError("selected_search_fractional must be finite.")
    cell, periodic = _validated_cell_and_pbc(search_cell, pbc)
    transform = _validated_integer_unimodular_matrix(
        basis_transform, name="basis_transform"
    )
    inverse = _validated_integer_unimodular_matrix(
        inverse_basis_transform, name="inverse_basis_transform"
    )
    if not np.array_equal(transform @ inverse, np.eye(3, dtype=np.int64)):
        raise InvalidCellGeometryError(
            "Basis transforms are not exact integer inverses."
        )

    inverse_cell = np.linalg.inv(cell)
    reciprocal_norms = np.linalg.norm(inverse_cell, axis=0)
    if np.any(~np.isfinite(reciprocal_norms)) or np.any(reciprocal_norms <= 0.0):
        raise InvalidCellGeometryError("Could not compute positive cell-plane heights.")
    heights = 1.0 / reciprocal_norms

    counts = np.ones(3, dtype=np.int64)
    origins = np.zeros(3, dtype=float)
    widths = np.ones(3, dtype=float)
    for axis in range(3):
        if periodic[axis]:
            counts[axis] = max(1, int(np.floor(heights[axis] / cutoff)))
            origins[axis] = 0.0
            widths[axis] = 1.0 / counts[axis]
            continue
        low = float(np.min(fractional[:, axis]))
        high = float(np.max(fractional[:, axis]))
        span = high - low
        origins[axis] = low
        if span <= options.coordinate_tolerance:
            counts[axis] = 1
            widths[axis] = max(cutoff / heights[axis], 1.0e-12)
        else:
            counts[axis] = max(1, int(np.floor(span * heights[axis] / cutoff)))
            widths[axis] = span / counts[axis]

    stencil = _build_metric_stencil(
        cell=cell,
        pbc=periodic,
        bin_counts=counts,
        bin_widths=widths,
        cutoff=cutoff,
        options=options,
    )
    return CellListPlan(
        search_cell=cell,
        basis_transform=transform,
        inverse_basis_transform=inverse,
        pbc=periodic,
        bin_counts=counts,
        bin_origins=origins,
        bin_widths=widths,
        stencil_offsets=stencil,
        reduction_applied=reduction_applied,
    )


def assign_fractional_bins(
    search_fractional: ArrayLike, plan: CellListPlan
) -> IntArray:
    """Assign search-basis fractional coordinates to deterministic bins."""
    fractional = np.asarray(search_fractional, dtype=float)
    if fractional.ndim != 2 or fractional.shape[1] != 3:
        raise ValueError("search_fractional must have shape (n_atoms, 3).")
    bins = np.empty_like(fractional, dtype=np.int64)
    for axis in range(3):
        coordinate = fractional[:, axis]
        if plan.pbc[axis]:
            coordinate = coordinate - np.floor(coordinate)
        scaled = (coordinate - plan.bin_origins[axis]) / plan.bin_widths[axis]
        axis_bins = np.floor(scaled).astype(np.int64)
        if plan.pbc[axis]:
            axis_bins %= plan.bin_counts[axis]
        else:
            axis_bins = np.clip(axis_bins, 0, plan.bin_counts[axis] - 1)
        bins[:, axis] = axis_bins
    return bins


def _prepare_search_basis(
    cell: FloatArray,
    pbc: BoolArray,
    options: CellListOptions,
) -> tuple[IntArray, IntArray, FloatArray, bool]:
    identity = np.eye(3, dtype=np.int64)
    if not options.use_lattice_reduction or np.count_nonzero(pbc) < 2:
        return identity, identity, np.asarray(cell, dtype=float).copy(), False

    # Direct software dependency: ASE's ``minkowski_reduce`` is described by
    # Larsen et al. (2017), DOI 10.1088/1361-648X/aa680e, and its
    # low-dimensional reduction lineage is Nguyen and Stehle (2009),
    # DOI 10.1145/1597036.1597050.
    try:
        reduced_cell, operation = minkowski_reduce(cell, pbc=pbc)
    except Exception as exc:  # pragma: no cover - defensive ASE boundary
        raise InvalidCellGeometryError("Minkowski lattice reduction failed.") from exc
    transform = _validated_integer_unimodular_matrix(
        operation, name="Minkowski reduction transform"
    )
    reduced = np.asarray(reduced_cell, dtype=float)
    if not np.allclose(
        reduced,
        transform @ cell,
        rtol=options.reduction_rtol,
        atol=options.reduction_atol,
    ):
        raise InvalidCellGeometryError(
            "Reduced cell is inconsistent with its integer basis transform."
        )
    _validate_periodic_subspace_transform(transform, pbc)
    inverse_float = np.linalg.inv(transform)
    inverse = np.rint(inverse_float).astype(np.int64)
    if not np.allclose(inverse_float, inverse, rtol=0.0, atol=1.0e-12):
        raise InvalidCellGeometryError(
            "Reduced-cell transform does not have an integer inverse."
        )
    if not np.array_equal(transform @ inverse, identity):
        raise InvalidCellGeometryError(
            "Reduced-cell transform and inverse are not exactly unimodular."
        )
    applied = not np.array_equal(transform, identity)
    return transform, inverse, reduced, applied


def _validate_periodic_subspace_transform(transform: IntArray, pbc: BoolArray) -> None:
    periodic_axes = np.flatnonzero(pbc)
    nonperiodic_axes = np.flatnonzero(~pbc)
    if nonperiodic_axes.size:
        if np.any(transform[np.ix_(periodic_axes, nonperiodic_axes)] != 0):
            raise InvalidCellGeometryError(
                "Lattice reduction mixed nonperiodic vectors into periodic vectors."
            )
        for axis in nonperiodic_axes:
            expected = np.zeros(3, dtype=np.int64)
            expected[axis] = 1
            if not np.array_equal(transform[axis], expected):
                raise InvalidCellGeometryError(
                    "Lattice reduction changed a nonperiodic basis vector."
                )


def _validated_integer_unimodular_matrix(matrix: ArrayLike, *, name: str) -> IntArray:
    raw = np.asarray(matrix)
    if raw.shape != (3, 3) or np.any(~np.isfinite(raw)):
        raise InvalidCellGeometryError(f"{name} must be a finite 3x3 matrix.")
    rounded = np.rint(raw).astype(np.int64)
    if not np.allclose(raw, rounded, rtol=0.0, atol=1.0e-12):
        raise InvalidCellGeometryError(f"{name} must contain integers.")
    determinant = int(round(float(np.linalg.det(rounded))))
    if abs(determinant) != 1:
        raise InvalidCellGeometryError(f"{name} must be unimodular.")
    return rounded


def _build_metric_stencil(
    *,
    cell: FloatArray,
    pbc: BoolArray,
    bin_counts: IntArray,
    bin_widths: FloatArray,
    cutoff: float,
    options: CellListOptions,
) -> IntArray:
    """Build the conservative exact metric stencil for one search plan.

    Metric-tensor neighbor searching for general parallelepiped cells has
    published precedent in Cui, Sun, and Qu (2009), and related periodic-region
    search formulations appear in Heinz and Huenenberger (2004) and Rogers
    (2016).  The finite offset bounds and 3-D active-set box minimizer used here
    are the mdstats construction, not a transcription of those algorithms.
    """
    inverse_cell = np.linalg.inv(cell)
    heights = 1.0 / np.linalg.norm(inverse_cell, axis=0)
    axis_ranges: list[range] = []
    total_offsets = 1
    for axis in range(3):
        fractional_reach = cutoff / heights[axis]
        max_abs = int(np.ceil(fractional_reach / bin_widths[axis] + 1.0 + 1.0e-12))
        if not pbc[axis]:
            max_abs = min(max_abs, int(bin_counts[axis] - 1))
        axis_range = range(-max_abs, max_abs + 1)
        axis_ranges.append(axis_range)
        total_offsets *= len(axis_range)
    if total_offsets > options.max_stencil_candidates:
        raise CellListComplexityError(
            "Metric-stencil candidate count exceeds max_stencil_candidates: "
            f"{total_offsets} > {options.max_stencil_candidates}."
        )

    metric = cell @ cell.T
    cutoff_squared = cutoff * cutoff
    tolerance = options.metric_tolerance * max(1.0, cutoff_squared)
    axis_values = [np.asarray(tuple(values), dtype=np.int64) for values in axis_ranges]
    mesh = np.meshgrid(*axis_values, indexing="ij")
    all_offsets = np.column_stack([values.ravel() for values in mesh]).astype(
        np.int64, copy=False
    )
    retained_parts: list[np.ndarray] = []
    # Bound active-set temporaries independently of the number of stencil
    # candidates.  Each batch evaluates all 27 active-set patterns in compiled
    # array kernels.
    batch_size = 100_000
    for start in range(0, all_offsets.shape[0], batch_size):
        current = all_offsets[start : start + batch_size]
        lower = (current.astype(np.float64) - 1.0) * bin_widths[None, :]
        upper = (current.astype(np.float64) + 1.0) * bin_widths[None, :]
        minimum_squared = _minimum_metric_norm_squared_in_boxes(
            metric,
            lower,
            upper,
            tolerance=options.coordinate_tolerance,
        )
        keep = minimum_squared <= cutoff_squared + tolerance
        if np.any(keep):
            retained_parts.append(current[keep])
    if not retained_parts:
        raise CellListComplexityError("Metric-aware stencil is unexpectedly empty.")
    retained = np.concatenate(retained_parts, axis=0)
    if retained.shape[0] > options.max_stencil_offsets:
        raise CellListComplexityError(
            "Retained metric-stencil size exceeds max_stencil_offsets: "
            f"{retained.shape[0]} > {options.max_stencil_offsets}."
        )
    order = np.lexsort((retained[:, 2], retained[:, 1], retained[:, 0]))
    return np.ascontiguousarray(retained[order], dtype=np.int64)


def _minimum_metric_norm_squared_in_boxes(
    metric: FloatArray,
    lower: FloatArray,
    upper: FloatArray,
    *,
    tolerance: float,
) -> FloatArray:
    """Exactly minimize a 3-D quadratic over many axis-aligned boxes."""

    lower_array = np.asarray(lower, dtype=np.float64)
    upper_array = np.asarray(upper, dtype=np.float64)
    if (
        lower_array.shape != upper_array.shape
        or lower_array.ndim != 2
        or lower_array.shape[1:] != (3,)
    ):
        raise ValueError("lower and upper must have shape (n_boxes, 3).")
    count = lower_array.shape[0]
    best = np.full(count, np.inf, dtype=np.float64)
    for states in product((-1, 0, 1), repeat=3):
        fixed = np.flatnonzero(states).astype(np.int64, copy=False)
        free = np.flatnonzero(np.asarray(states) == 0).astype(np.int64, copy=False)
        points = np.zeros((count, 3), dtype=np.float64)
        if fixed.size:
            state_values = np.asarray(states, dtype=np.int8)[fixed]
            points[:, fixed] = np.where(
                state_values[None, :] < 0,
                lower_array[:, fixed],
                upper_array[:, fixed],
            )
        if free.size:
            free_metric = metric[np.ix_(free, free)]
            if fixed.size:
                rhs = -points[:, fixed] @ metric[np.ix_(free, fixed)].T
            else:
                rhs = np.zeros((count, free.size), dtype=np.float64)
            try:
                points[:, free] = np.linalg.solve(
                    free_metric, rhs.T
                ).T
            except np.linalg.LinAlgError as exc:  # pragma: no cover
                raise InvalidCellGeometryError(
                    "Cell metric became singular during stencil construction."
                ) from exc
            feasible = np.all(
                (points[:, free] >= lower_array[:, free] - tolerance)
                & (points[:, free] <= upper_array[:, free] + tolerance),
                axis=1,
            )
            points[:, free] = np.clip(
                points[:, free], lower_array[:, free], upper_array[:, free]
            )
        else:
            feasible = np.ones(count, dtype=bool)
        values = np.einsum("ni,ij,nj->n", points, metric, points, optimize=True)
        best[feasible] = np.minimum(best[feasible], values[feasible])
    if np.any(~np.isfinite(best)):  # pragma: no cover
        raise InvalidCellGeometryError(
            "Could not minimize the cell metric over one or more bin boxes."
        )
    return np.maximum(best, 0.0)


def _minimum_metric_norm_squared_in_box(
    metric: FloatArray,
    lower: FloatArray,
    upper: FloatArray,
    *,
    tolerance: float,
) -> float:
    """Exactly minimize ``x.T @ metric @ x`` over a three-dimensional box.

    The convex optimum has each coordinate either free or active at one of its
    two bounds.  Enumerating the 3^3 active-set patterns is therefore exact up
    to the linear-solve tolerance.
    """
    best = float("inf")
    for states in product((-1, 0, 1), repeat=3):
        fixed = np.asarray(
            [index for index, state in enumerate(states) if state], dtype=int
        )
        free = np.asarray(
            [index for index, state in enumerate(states) if not state], dtype=int
        )
        point = np.zeros(3, dtype=float)
        if fixed.size:
            for axis in fixed:
                point[axis] = lower[axis] if states[int(axis)] < 0 else upper[axis]
        if free.size:
            free_metric = metric[np.ix_(free, free)]
            if fixed.size:
                rhs = -metric[np.ix_(free, fixed)] @ point[fixed]
            else:
                rhs = np.zeros(free.size, dtype=float)
            try:
                point[free] = np.linalg.solve(free_metric, rhs)
            except np.linalg.LinAlgError as exc:  # pragma: no cover - SPD guard
                raise InvalidCellGeometryError(
                    "Cell metric became singular during stencil construction."
                ) from exc
            if np.any(point[free] < lower[free] - tolerance) or np.any(
                point[free] > upper[free] + tolerance
            ):
                continue
            point[free] = np.clip(point[free], lower[free], upper[free])
        value = float(point @ metric @ point)
        if value < best:
            best = value
    if not np.isfinite(best):  # pragma: no cover - active-set completeness guard
        raise InvalidCellGeometryError(
            "Could not minimize the cell metric over a bin box."
        )
    return max(0.0, best)
