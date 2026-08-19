"""Shared minimum-image neighbor geometry for structural observables.

The private kernel returns a compact CSR-style neighbor list.  RDF consumes the
flat distances, coordination consumes row lengths, and bond-angle analysis
consumes row-grouped displacement vectors.  Search acceleration can change in
the future without changing this result contract.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import itertools

import numpy as np
from ase.geometry import find_mic, is_minkowski_reduced, minkowski_reduce
from ase.geometry.geometry import complete_cell, wrap_positions
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from .cutoffs import PairCutoff

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class NeighborError(RuntimeError):
    """Base class for shared neighbor-search failures."""


class InvalidNeighborSelectionError(NeighborError):
    """Raised for malformed, duplicate, or ambiguous atom selections."""


class InvalidNeighborCutoffError(NeighborError):
    """Raised when a cutoff is nonpositive or nonfinite."""


class UnsafeNeighborCutoffError(NeighborError):
    """Raised when a cutoff exceeds the unique minimum-image radius."""


class InvalidCellGeometryError(NeighborError):
    """Raised when cell or PBC data are malformed."""


class CoincidentAtomsError(NeighborError):
    """Raised when distinct selected atoms occupy the same position."""


class CellListComplexityError(NeighborError):
    """Raised when an exact cell-list stencil exceeds configured hard limits."""


class PairCounting(str, Enum):
    """Pair-retention convention used by the CSR neighbor result."""

    DIRECTED = "directed"
    UNORDERED_IDENTICAL = "unordered_identical"


class NeighborSearchBackend(str, Enum):
    """Neighbor-search implementation selected by the shared facade."""

    DENSE = "dense"
    CELL_LIST = "cell_list"
    VERLET_CACHE = "verlet_cache"


@dataclass(frozen=True, slots=True)
class CellListOptions:
    """Configuration for exact single-frame cell-list candidate generation."""

    use_lattice_reduction: bool = True
    max_stencil_candidates: int = 1_000_000
    max_stencil_offsets: int = 250_000
    metric_tolerance: float = 1.0e-12
    coordinate_tolerance: float = 1.0e-12
    reduction_rtol: float = 1.0e-12
    reduction_atol: float = 1.0e-12

    def __post_init__(self) -> None:
        if not isinstance(self.use_lattice_reduction, (bool, np.bool_)):
            raise TypeError("use_lattice_reduction must be boolean.")
        object.__setattr__(
            self, "use_lattice_reduction", bool(self.use_lattice_reduction)
        )
        for name in ("max_stencil_candidates", "max_stencil_offsets"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise TypeError(f"{name} must be an integer.")
            value = int(value)
            if value <= 0:
                raise ValueError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        for name in (
            "metric_tolerance",
            "coordinate_tolerance",
            "reduction_rtol",
            "reduction_atol",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class NeighborListResult:
    """CSR-style neighbors for one frame and one center/candidate pair."""

    frame_index: int
    center_indices: IntArray
    neighbor_indices: IntArray
    offsets: IntArray
    vectors: FloatArray
    distances: FloatArray
    image_shifts: IntArray
    cutoff: float
    pair_counting: PairCounting
    backend: NeighborSearchBackend = NeighborSearchBackend.DENSE

    def __post_init__(self) -> None:
        centers = np.asarray(self.center_indices, dtype=np.int64).copy()
        neighbors = np.asarray(self.neighbor_indices, dtype=np.int64).copy()
        offsets = np.asarray(self.offsets, dtype=np.int64).copy()
        vectors = np.asarray(self.vectors, dtype=float).copy()
        distances = np.asarray(self.distances, dtype=float).copy()
        image_shifts = np.asarray(self.image_shifts, dtype=np.int64).copy()
        if centers.ndim != 1 or neighbors.ndim != 1 or offsets.ndim != 1:
            raise ValueError(
                "Neighbor index and offset arrays must be one-dimensional."
            )
        if offsets.shape != (centers.size + 1,):
            raise ValueError("offsets must have shape (n_centers + 1,).")
        if offsets.size == 0 or offsets[0] != 0 or offsets[-1] != neighbors.size:
            raise ValueError("offsets must start at zero and end at n_pairs.")
        if np.any(np.diff(offsets) < 0):
            raise ValueError("offsets must be nondecreasing.")
        if vectors.shape != (neighbors.size, 3):
            raise ValueError("vectors must have shape (n_pairs, 3).")
        if distances.shape != (neighbors.size,):
            raise ValueError("distances must have shape (n_pairs,).")
        if image_shifts.shape != (neighbors.size, 3):
            raise ValueError("image_shifts must have shape (n_pairs, 3).")
        if np.any(~np.isfinite(vectors)) or np.any(~np.isfinite(distances)):
            raise ValueError("Neighbor vectors and distances must be finite.")
        if not np.allclose(
            np.linalg.norm(vectors, axis=1), distances, rtol=1e-12, atol=1e-12
        ):
            raise ValueError("distances are inconsistent with vectors.")
        if np.any(distances >= float(self.cutoff)):
            raise ValueError("Every returned distance must satisfy distance < cutoff.")
        if isinstance(self.frame_index, bool) or not isinstance(
            self.frame_index, (int, np.integer)
        ):
            raise TypeError("frame_index must be an integer.")
        frame_index = int(self.frame_index)
        if frame_index < 0:
            raise ValueError("frame_index must be nonnegative in a neighbor result.")
        cutoff = float(self.cutoff)
        if not np.isfinite(cutoff) or cutoff <= 0.0:
            raise ValueError("cutoff must be positive and finite.")
        pair_counting = PairCounting(self.pair_counting)
        backend = NeighborSearchBackend(self.backend)
        for array in (
            centers,
            neighbors,
            offsets,
            vectors,
            distances,
            image_shifts,
        ):
            array.setflags(write=False)
        object.__setattr__(self, "frame_index", frame_index)
        object.__setattr__(self, "center_indices", centers)
        object.__setattr__(self, "neighbor_indices", neighbors)
        object.__setattr__(self, "offsets", offsets)
        object.__setattr__(self, "vectors", vectors)
        object.__setattr__(self, "distances", distances)
        object.__setattr__(self, "image_shifts", image_shifts)
        object.__setattr__(self, "cutoff", cutoff)
        object.__setattr__(self, "pair_counting", pair_counting)
        object.__setattr__(self, "backend", backend)

    @property
    def n_centers(self) -> int:
        return int(self.center_indices.size)

    @property
    def n_pairs(self) -> int:
        return int(self.neighbor_indices.size)

    @property
    def coordination_counts(self) -> IntArray:
        """Number of retained neighbors for every center row."""
        return np.diff(self.offsets).astype(np.int64, copy=False)

    def row_slice(self, local_center: int) -> slice:
        """Return the flat-array slice for one local center slot."""
        if local_center < 0 or local_center >= self.n_centers:
            raise IndexError("local_center is outside the neighbor list.")
        return slice(
            int(self.offsets[local_center]), int(self.offsets[local_center + 1])
        )


@lru_cache(maxsize=256)
def _cached_general_mic_geometry(
    cell_bytes: bytes,
    pbc_tuple: tuple[bool, bool, bool],
) -> tuple[FloatArray, FloatArray, IntArray, IntArray, FloatArray]:
    """Cache cell-only work for exact general minimum-image geometry.

    ASE's :func:`find_mic` performs Minkowski reduction and constructs the
    Voronoi-relevant lattice vectors on every call.  Structural campaigns call
    the kernel tens of thousands of times with an identical fixed cell, so the
    repeated reduction dominates runtime.  The cache key uses the exact cell
    bytes: no geometry is rounded or approximated.

    The integer unimodular transform returned by :func:`minkowski_reduce` is
    retained as part of the cache.  GFX3D-HARDEN3 uses it to propagate exact
    lattice-image labels through the reduced basis instead of reconstructing
    those labels afterward with a floating inverse/rounding step.
    """

    cell = np.frombuffer(cell_bytes, dtype=np.float64).reshape(3, 3).copy()
    pbc = np.asarray(pbc_tuple, dtype=np.bool_)
    complete = np.asarray(complete_cell(cell), dtype=np.float64)
    reduced_raw, operation_raw = minkowski_reduce(complete, pbc=pbc)
    reduced = np.asarray(reduced_raw, dtype=np.float64)
    operation = np.asarray(operation_raw, dtype=np.int64)
    ranges = [np.arange(-int(periodic), int(periodic) + 1) for periodic in pbc]
    hkls = np.asarray(
        [(0, 0, 0), *itertools.product(*ranges)], dtype=np.int64
    )
    voronoi_vectors = hkls @ reduced
    reduced_inverse = np.linalg.inv(reduced)
    for array in (reduced, voronoi_vectors, operation, hkls, reduced_inverse):
        array.setflags(write=False)
    return reduced, voronoi_vectors, operation, hkls, reduced_inverse


def _general_mic_search(
    vectors: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
) -> tuple[
    FloatArray,
    FloatArray,
    IntArray,
    FloatArray,
    IntArray,
    IntArray,
]:
    """Run the cached ASE-equivalent general-cell MIC search.

    This helper performs only the geometric part of the search and returns the
    selected reduced-cell H/K/L row as auxiliary data.  Callers that need only
    vectors and distances therefore do not pay for, or fail because of,
    integer lattice-image bookkeeping.
    """

    contiguous_cell = np.ascontiguousarray(cell, dtype=np.float64)
    reduced, voronoi_vectors, operation, hkls, _reduced_inverse = (
        _cached_general_mic_geometry(
            contiguous_cell.tobytes(), tuple(bool(value) for value in pbc)
        )
    )
    # Keep the established ASE-equivalent wrapped Cartesian positions so the
    # returned MIC vectors remain governed by the same search as ASE find_mic.
    positions = wrap_positions(vectors, reduced, pbc=pbc, eps=0)
    candidates = positions[None, :, :] + voronoi_vectors[:, None, :]
    squared = np.einsum("kni,kni->kn", candidates, candidates)
    indices = np.argmin(squared, axis=0)
    rows = np.arange(vectors.shape[0])
    minimum = candidates[indices, rows, :]
    distances = np.sqrt(squared[indices, rows])
    return minimum, distances, indices, reduced, operation, hkls


def _cached_general_find_mic_vectors(
    vectors: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
) -> tuple[FloatArray, FloatArray]:
    """Return exact general-cell MIC vectors and norms without image labels.

    DATA6 local-structure features and several analysis paths consume only MIC
    geometry.  They must not be coupled to the stricter integer-image
    reconstruction contract required by periodic graph consumers.
    """

    minimum, distances, _indices, _reduced, _operation, _hkls = (
        _general_mic_search(vectors, cell=cell, pbc=pbc)
    )
    return minimum, distances


def _cached_general_find_mic(
    vectors: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
) -> tuple[FloatArray, FloatArray, IntArray]:
    """Return exact general-cell MIC vectors, norms, and integer image shifts.

    The geometric search is intentionally identical to ASE's general MIC
    construction.  Image labels are tracked algebraically in the reduced
    lattice and transformed back with the exact unimodular operation matrix.
    This removes the numerically fragile ``(mic - raw) @ inv(cell)`` recovery
    that could reject an otherwise valid MIC in long GFX3D trajectories.
    """

    minimum, distances, indices, reduced, operation, hkls = _general_mic_search(
        vectors, cell=cell, pbc=pbc
    )

    # ``wrap_positions(..., eps=0)`` computes reduced fractional coordinates
    # with ``np.linalg.solve(reduced.T, vectors.T).T`` before applying modulo.
    # Recompute those coordinates through the same solve rather than through a
    # precomputed inverse.  Values lying within a few ulps of an integer
    # lattice plane can land on opposite sides of ``floor`` when an explicit
    # inverse is multiplied back, producing a spurious whole-cell shift even
    # for a perfectly valid, well-conditioned lattice.
    reduced_fractional = np.linalg.solve(
        np.asarray(reduced, dtype=np.float64).T,
        np.asarray(vectors, dtype=np.float64).T,
    ).T
    wrap_coefficients = np.zeros_like(reduced_fractional, dtype=np.int64)
    for axis, periodic in enumerate(np.asarray(pbc, dtype=bool)):
        if periodic:
            wrap_coefficients[:, axis] = -np.floor(
                reduced_fractional[:, axis]
            ).astype(np.int64)
    reduced_shifts = wrap_coefficients + hkls[indices]
    # Validate in the reduced basis, where the MIC search itself is carried
    # out.  Reconstructing through a nearly singular original basis may lose
    # digits through cancellation even when the integer lattice label is exact.
    stable_reconstruction = (
        np.asarray(vectors, dtype=np.float64) + reduced_shifts @ reduced
    )
    stable_scale = max(1.0, float(np.max(np.abs(reduced))))
    if not np.allclose(
        stable_reconstruction,
        minimum,
        rtol=2.0e-12,
        atol=8.0e-12 * stable_scale,
    ):
        raise InvalidCellGeometryError(
            "Reduced-basis minimum-image lattice bookkeeping became inconsistent."
        )
    image_shifts = np.asarray(reduced_shifts @ operation, dtype=np.int64)
    image_shifts[:, ~np.asarray(pbc, dtype=bool)] = 0
    return minimum, distances, image_shifts


def minimum_image_geometry(
    displacements: ArrayLike,
    *,
    cell: ArrayLike,
    pbc: ArrayLike,
) -> tuple[FloatArray, FloatArray, IntArray]:
    """Return minimum-image vectors, norms, and lattice image shifts.

    The returned integer shift ``m`` obeys the row-vector convention

    ``mic_vector = raw_displacement + m @ cell``.

    Existing structural analyses normally need only vectors and distances; the
    image shifts are retained for periodic graph construction.
    """
    raw = np.asarray(displacements, dtype=float)
    if raw.shape[-1:] != (3,):
        raise ValueError("displacements must end with a Cartesian dimension of 3.")
    cell_array, pbc_array = _validated_cell_and_pbc(cell, pbc)
    original_shape = raw.shape
    flat = raw.reshape(-1, 3)
    if np.any(~np.isfinite(flat)):
        raise ValueError("displacements contain non-finite values.")
    if flat.size == 0:
        return (
            np.empty(original_shape, dtype=float),
            np.empty(original_shape[:-1]),
            np.empty(original_shape, dtype=np.int64),
        )
    if np.any(pbc_array):
        # The exact general MIC is used here so fixed-cell campaigns can reuse
        # Minkowski reduction and Voronoi-vector construction.  This preserves
        # arbitrary triclinic-cell correctness while removing a large repeated
        # cell-only cost from every frame.
        vectors, distances, shifts = _cached_general_find_mic(
            flat, cell=cell_array, pbc=pbc_array
        )
        vectors = np.asarray(vectors, dtype=float)
        distances = np.asarray(distances, dtype=float)
        shifts = np.asarray(shifts, dtype=np.int64)
        # Image labels were obtained algebraically through the exact integer
        # unimodular reduced-cell transform in ``_cached_general_find_mic``.
        # Do not revalidate by multiplying those labels through the original
        # cell: for a nearly singular basis that mathematically equivalent
        # Cartesian reconstruction can lose many ulps through cancellation.
    else:
        vectors = flat.copy()
        distances = np.linalg.norm(vectors, axis=1)
        shifts = np.zeros_like(flat, dtype=np.int64)
    return (
        vectors.reshape(original_shape),
        distances.reshape(original_shape[:-1]),
        shifts.reshape(original_shape),
    )


def minimum_image_vectors(
    displacements: ArrayLike,
    *,
    cell: ArrayLike,
    pbc: ArrayLike,
) -> tuple[FloatArray, FloatArray]:
    """Return exact general-cell minimum-image vectors and their norms.

    This vectors-only path deliberately skips lattice-image reconstruction.
    Analyses such as DATA6 local-structure selection do not consume integer
    image shifts, and deriving them requires two additional matrix products,
    rounding, allocation, and a full reconstruction check for every pair.
    """

    raw = np.asarray(displacements, dtype=float)
    if raw.shape[-1:] != (3,):
        raise ValueError("displacements must end with a Cartesian dimension of 3.")
    cell_array, pbc_array = _validated_cell_and_pbc(cell, pbc)
    original_shape = raw.shape
    flat = raw.reshape(-1, 3)
    if np.any(~np.isfinite(flat)):
        raise ValueError("displacements contain non-finite values.")
    if flat.size == 0:
        return (
            np.empty(original_shape, dtype=float),
            np.empty(original_shape[:-1], dtype=float),
        )
    if np.any(pbc_array):
        vectors, distances = _cached_general_find_mic_vectors(
            flat, cell=cell_array, pbc=pbc_array
        )
    else:
        vectors = flat.copy()
        distances = np.linalg.norm(vectors, axis=1)
    return (
        np.asarray(vectors, dtype=float).reshape(original_shape),
        np.asarray(distances, dtype=float).reshape(original_shape[:-1]),
    )


def compute_safe_cutoff(
    collection: AtomisticFrameCollection,
    *,
    frame_indices: ArrayLike,
) -> float:
    """Return the exact unique minimum-image radius over selected frames.

    For each frame, the supported radius is one half of the shortest nonzero
    translation in the periodic lattice,

    ``0.5 * min(||n @ cell|| for nonzero periodic integer n)``.

    The shortest translation is obtained from an ASE Minkowski-reduced basis,
    whose first periodic vector is a shortest lattice vector.  A fully
    nonperiodic collection has no periodic-image ambiguity and returns
    ``numpy.inf``.
    """
    frames = _validated_frame_indices(collection, frame_indices)
    pbc = np.asarray(collection.pbc, dtype=bool)
    if pbc.shape != (3,):
        raise InvalidCellGeometryError("collection.pbc must have shape (3,).")
    if not np.any(pbc):
        return float(np.inf)

    safe = np.inf
    exact_cell_cache: dict[bytes, float] = {}
    for frame in frames:
        cell, _ = _validated_cell_and_pbc(collection.cells[int(frame)], pbc)
        cell_key = np.ascontiguousarray(cell, dtype=np.float64).tobytes()
        shortest = exact_cell_cache.get(cell_key)
        if shortest is None:
            shortest = _shortest_periodic_translation_length(cell, pbc)
            exact_cell_cache[cell_key] = shortest
        frame_safe = 0.5 * shortest
        if not np.isfinite(frame_safe) or frame_safe <= 0.0:
            raise InvalidCellGeometryError(
                "Could not determine a positive shortest periodic translation "
                f"in frame {frame}."
            )
        safe = min(safe, frame_safe)
    return float(safe)


def validate_cutoff(
    cutoff: float | PairCutoff,
    *,
    collection: AtomisticFrameCollection,
    frame_indices: ArrayLike,
) -> float:
    """Validate a cutoff and return its numeric radius in angstrom."""
    radius = float(cutoff.radius if isinstance(cutoff, PairCutoff) else cutoff)
    if not np.isfinite(radius) or radius <= 0.0:
        raise InvalidNeighborCutoffError("cutoff must be positive and finite.")
    safe = compute_safe_cutoff(collection, frame_indices=frame_indices)
    tolerance = max(1.0e-10, 1.0e-10 * radius)
    if np.isfinite(safe) and radius > safe + tolerance:
        raise UnsafeNeighborCutoffError(
            f"cutoff={radius:.8g} A exceeds the exact safe unique minimum-image "
            f"radius {safe:.8g} A, defined as half the shortest nonzero "
            "periodic lattice translation."
        )
    return radius


def _build_dense_neighbor_list(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: float | PairCutoff,
    pair_counting: PairCounting = PairCounting.DIRECTED,
    block_size: int = 256,
) -> NeighborListResult:
    """Build one deterministic CSR neighbor list using blocked dense geometry."""
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
    if isinstance(block_size, bool) or not isinstance(block_size, (int, np.integer)):
        raise TypeError("block_size must be an integer.")
    block_size = int(block_size)
    if block_size <= 0:
        raise ValueError("block_size must be positive.")
    radius = validate_cutoff(cutoff, collection=collection, frame_indices=[frame])

    positions = np.asarray(collection.get_wrapped_positions(frame), dtype=float)
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise InvalidCellGeometryError(
            f"Frame {frame} positions must be finite with shape (n_atoms, 3)."
        )
    cell, pbc = _validated_cell_and_pbc(collection.cells[frame], collection.pbc)
    candidate_positions = positions[candidates]

    neighbor_chunks: list[IntArray] = []
    vector_chunks: list[FloatArray] = []
    distance_chunks: list[FloatArray] = []
    shift_chunks: list[IntArray] = []
    row_counts = np.zeros(centers.size, dtype=np.int64)
    zero_tolerance = max(1.0e-12, np.finfo(float).eps * max(1.0, radius) * 64.0)

    for start in range(0, centers.size, block_size):
        stop = min(start + block_size, centers.size)
        block_centers = centers[start:stop]
        displacement = (
            candidate_positions[None, :, :] - positions[block_centers][:, None, :]
        )
        vectors, distances, image_shifts = minimum_image_geometry(
            displacement, cell=cell, pbc=pbc
        )

        for local_offset, center_atom in enumerate(block_centers):
            row_vectors = vectors[local_offset]
            row_distances = distances[local_offset]
            row_shifts = image_shifts[local_offset]
            mask = row_distances < radius
            mask &= candidates != center_atom
            if mode is PairCounting.UNORDERED_IDENTICAL:
                mask &= center_atom < candidates

            coincident = mask & (row_distances <= zero_tolerance)
            if np.any(coincident):
                bad_neighbor = int(candidates[np.flatnonzero(coincident)[0]])
                raise CoincidentAtomsError(
                    f"Distinct selected atoms {int(center_atom)} and {bad_neighbor} "
                    f"are coincident in frame {frame}."
                )

            accepted_indices = candidates[mask]
            accepted_vectors = row_vectors[mask]
            accepted_distances = row_distances[mask]
            accepted_shifts = row_shifts[mask]
            row_counts[start + local_offset] = accepted_indices.size
            if accepted_indices.size:
                neighbor_chunks.append(np.asarray(accepted_indices, dtype=np.int64))
                vector_chunks.append(np.asarray(accepted_vectors, dtype=float))
                distance_chunks.append(np.asarray(accepted_distances, dtype=float))
                shift_chunks.append(np.asarray(accepted_shifts, dtype=np.int64))

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
    return NeighborListResult(
        frame_index=frame,
        center_indices=centers,
        neighbor_indices=neighbors,
        offsets=offsets,
        vectors=vectors,
        distances=distances,
        image_shifts=image_shifts,
        cutoff=radius,
        pair_counting=mode,
        backend=NeighborSearchBackend.DENSE,
    )


def build_neighbor_list(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: float | PairCutoff,
    pair_counting: PairCounting = PairCounting.DIRECTED,
    backend: NeighborSearchBackend = NeighborSearchBackend.DENSE,
    block_size: int = 256,
    cell_list_options: CellListOptions | None = None,
) -> NeighborListResult:
    """Build one deterministic CSR neighbor list with an explicit backend.

    Stages S0-S1 provide stateless dense and cell-list backends.  Stages
    S2-S3 fixed- and variable-cell reuse are available through
    ``NeighborSearchSession``; this
    stateless facade still performs no cross-frame caching.
    """
    selected_backend = NeighborSearchBackend(backend)
    if selected_backend is NeighborSearchBackend.DENSE:
        return _build_dense_neighbor_list(
            collection,
            frame_index=frame_index,
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            block_size=block_size,
        )
    if selected_backend is NeighborSearchBackend.CELL_LIST:
        from ._cell_list import build_cell_list_neighbor_list

        return build_cell_list_neighbor_list(
            collection,
            frame_index=frame_index,
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            options=cell_list_options,
        )
    if selected_backend is NeighborSearchBackend.VERLET_CACHE:
        raise ValueError(
            "VERLET_CACHE is result provenance for NeighborSearchSession and "
            "cannot be selected through the stateless build_neighbor_list facade."
        )
    raise AssertionError(f"Unhandled neighbor backend: {selected_backend!r}.")


def iter_neighbor_lists(
    collection: AtomisticFrameCollection,
    *,
    frame_indices: ArrayLike,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: float | PairCutoff,
    pair_counting: PairCounting = PairCounting.DIRECTED,
    backend: NeighborSearchBackend = NeighborSearchBackend.DENSE,
    block_size: int = 256,
    cell_list_options: CellListOptions | None = None,
) -> Iterator[NeighborListResult]:
    """Yield one CSR neighbor list per selected frame."""
    frames = _validated_frame_indices(collection, frame_indices)
    validate_cutoff(cutoff, collection=collection, frame_indices=frames)
    for frame in frames:
        yield build_neighbor_list(
            collection,
            frame_index=int(frame),
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            backend=backend,
            block_size=block_size,
            cell_list_options=cell_list_options,
        )


def _validated_indices(array: ArrayLike, *, n_atoms: int, name: str) -> IntArray:
    raw = np.asarray(array)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise InvalidNeighborSelectionError(
            f"{name} must be a one-dimensional integer array."
        )
    indices = raw.astype(np.int64, copy=True)
    if indices.size == 0:
        raise InvalidNeighborSelectionError(f"{name} is empty.")
    if np.any(indices < 0) or np.any(indices >= n_atoms):
        raise InvalidNeighborSelectionError(
            f"{name} contains out-of-range atom indices."
        )
    if np.unique(indices).size != indices.size:
        raise InvalidNeighborSelectionError(f"{name} contains duplicate indices.")
    return indices


def _validate_selection_relation(
    centers: IntArray, candidates: IntArray, mode: PairCounting
) -> None:
    identical = np.array_equal(centers, candidates)
    overlap = np.intersect1d(centers, candidates, assume_unique=False)
    if overlap.size and not identical:
        raise InvalidNeighborSelectionError(
            "Center and candidate selections must be disjoint or exactly identical."
        )
    if mode is PairCounting.UNORDERED_IDENTICAL and not identical:
        raise InvalidNeighborSelectionError(
            "UNORDERED_IDENTICAL requires exactly identical center and candidate selections."
        )


def _validated_single_frame_index(
    collection: AtomisticFrameCollection, frame_index: int
) -> int:
    if isinstance(frame_index, bool) or not isinstance(frame_index, (int, np.integer)):
        raise TypeError("frame_index must be an integer.")
    frame = int(frame_index)
    if frame < 0:
        frame += collection.n_frames
    if frame < 0 or frame >= collection.n_frames:
        raise IndexError("frame_index is outside the collection.")
    return frame


def _validated_frame_indices(
    collection: AtomisticFrameCollection, frame_indices: ArrayLike
) -> IntArray:
    raw = np.asarray(frame_indices)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise TypeError("frame_indices must be a one-dimensional integer array.")
    frames = raw.astype(np.int64, copy=True)
    if frames.size == 0:
        raise ValueError("frame_indices is empty.")
    frames[frames < 0] += collection.n_frames
    if np.any(frames < 0) or np.any(frames >= collection.n_frames):
        raise IndexError("frame_indices contains an out-of-range frame.")
    if np.unique(frames).size != frames.size:
        raise ValueError("frame_indices contains duplicates.")
    return frames


def _validated_cell_and_pbc(
    cell: ArrayLike, pbc: ArrayLike
) -> tuple[FloatArray, BoolArray]:
    matrix = np.asarray(cell, dtype=float)
    periodic = np.asarray(pbc, dtype=bool)
    if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
        raise InvalidCellGeometryError("cell must be a finite 3x3 matrix.")
    if periodic.shape != (3,):
        raise InvalidCellGeometryError("pbc must have shape (3,).")
    if abs(float(np.linalg.det(matrix))) <= 1.0e-14:
        raise InvalidCellGeometryError("cell must be nonsingular.")
    return matrix, periodic


def _shortest_periodic_translation_length(
    cell: FloatArray, pbc: BoolArray
) -> float:
    """Return the exact shortest nonzero periodic lattice translation."""
    contiguous = np.ascontiguousarray(np.asarray(cell, dtype=np.float64))
    periodic = tuple(bool(value) for value in np.asarray(pbc, dtype=bool))
    return _cached_shortest_periodic_translation_length(contiguous.tobytes(), periodic)


@lru_cache(maxsize=512)
def _cached_shortest_periodic_translation_length(
    cell_bytes: bytes, pbc_tuple: tuple[bool, bool, bool]
) -> float:
    """Cached exact shortest periodic translation for an immutable cell key.

    ASE's low-dimensional Minkowski reduction returns a basis with the
    shortest possible vector lengths ordered by norm.  Only periodic rows are
    included for partially periodic cells.  The integer transform is checked
    so this routine cannot silently accept a basis that changes the periodic
    translation lattice.
    """
    cell = np.frombuffer(cell_bytes, dtype=np.float64).reshape(3, 3).copy()
    pbc = np.asarray(pbc_tuple, dtype=np.bool_)
    periodic_axes = np.flatnonzero(pbc)
    dimension = int(periodic_axes.size)
    if dimension == 0:
        return float(np.inf)
    if dimension == 1:
        length = float(np.linalg.norm(cell[periodic_axes[0]]))
        if not np.isfinite(length) or length <= 1.0e-14:
            raise InvalidCellGeometryError(
                "The periodic cell vector must have positive finite length."
            )
        return length

    # ASE's implementation follows Nguyen and Stehle (2009),
    # DOI 10.1145/1597036.1597050.  ASE documents that the reduced basis has
    # shortest possible vector lengths ordered by norm.
    try:
        reduced_cell, operation = minkowski_reduce(cell, pbc=pbc)
    except Exception as exc:  # pragma: no cover - defensive ASE boundary
        raise InvalidCellGeometryError(
            "Minkowski reduction failed while determining the shortest "
            "periodic lattice translation."
        ) from exc

    reduced = np.asarray(reduced_cell, dtype=float)
    operation_array = np.asarray(operation)
    if reduced.shape != (3, 3) or np.any(~np.isfinite(reduced)):
        raise InvalidCellGeometryError(
            "Minkowski reduction returned an invalid reduced cell."
        )
    if operation_array.shape != (3, 3) or np.any(~np.isfinite(operation_array)):
        raise InvalidCellGeometryError(
            "Minkowski reduction returned an invalid basis transform."
        )
    operation_integer = np.rint(operation_array).astype(np.int64)
    if not np.allclose(operation_array, operation_integer, rtol=0.0, atol=1.0e-12):
        raise InvalidCellGeometryError(
            "Minkowski reduction transform is not integer-valued."
        )
    determinant = int(round(float(np.linalg.det(operation_integer))))
    if abs(determinant) != 1:
        raise InvalidCellGeometryError(
            "Minkowski reduction transform is not unimodular."
        )
    tolerance = 2.0e-10 * max(1.0, float(np.max(np.abs(cell))))
    if not np.allclose(
        reduced, operation_integer @ cell, rtol=1.0e-12, atol=tolerance
    ):
        raise InvalidCellGeometryError(
            "Minkowski-reduced cell is inconsistent with its integer transform."
        )
    if np.any(operation_integer[np.ix_(periodic_axes, np.flatnonzero(~pbc))]):
        raise InvalidCellGeometryError(
            "Minkowski reduction mixed nonperiodic vectors into the periodic "
            "translation lattice."
        )
    periodic_transform = operation_integer[np.ix_(periodic_axes, periodic_axes)]
    periodic_determinant = int(round(float(np.linalg.det(periodic_transform))))
    if abs(periodic_determinant) != 1:
        raise InvalidCellGeometryError(
            "Minkowski reduction did not preserve the periodic sublattice."
        )
    try:
        reduced_ok = bool(is_minkowski_reduced(reduced, pbc=pbc))
    except Exception as exc:  # pragma: no cover - defensive ASE boundary
        raise InvalidCellGeometryError(
            "Could not certify the Minkowski-reduced periodic basis."
        ) from exc
    if not reduced_ok:
        raise InvalidCellGeometryError(
            "ASE returned a basis that is not Minkowski reduced."
        )

    periodic_norms = np.linalg.norm(reduced[periodic_axes], axis=1)
    shortest = float(np.min(periodic_norms))
    if not np.isfinite(shortest) or shortest <= 1.0e-14:
        raise InvalidCellGeometryError(
            "The shortest periodic lattice translation is not positive and finite."
        )
    return shortest


def _periodic_cell_heights(cell: FloatArray, pbc: BoolArray) -> FloatArray:
    """Return perpendicular periodic cell heights for diagnostics only.

    These heights are useful for cell-list binning, but they are not the exact
    unique minimum-image radius for a skewed lattice.
    """
    axes = np.flatnonzero(pbc)
    if axes.size == 1:
        return np.asarray([np.linalg.norm(cell[axes[0]])], dtype=float)
    if axes.size == 2:
        a = cell[axes[0]]
        b = cell[axes[1]]
        area = float(np.linalg.norm(np.cross(a, b)))
        if area <= 1.0e-14:
            raise InvalidCellGeometryError(
                "Periodic cell vectors are linearly dependent."
            )
        return np.asarray([area / np.linalg.norm(b), area / np.linalg.norm(a)])

    volume = abs(float(np.linalg.det(cell)))
    heights = []
    for axis in range(3):
        other = [index for index in range(3) if index != axis]
        face_area = float(np.linalg.norm(np.cross(cell[other[0]], cell[other[1]])))
        if face_area <= 1.0e-14:
            raise InvalidCellGeometryError("Cell face area is zero.")
        heights.append(volume / face_area)
    return np.asarray(heights, dtype=float)
