"""Deterministic neighbor-search cases and an independent scalar oracle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._neighbors import (
    CoincidentAtomsError,
    NeighborListResult,
    NeighborSearchBackend,
    PairCounting,
    minimum_image_geometry,
    validate_cutoff,
)

GeometryKind = Literal["orthogonal", "triclinic", "mixed_pbc", "boundary"]
SelectionKind = Literal["directed_disjoint", "unordered_identical"]


@dataclass(frozen=True, slots=True)
class RandomNeighborCase:
    """One reproducible single-frame neighbor-search input."""

    name: str
    seed: int
    collection: AtomisticFrameCollection
    center_indices: np.ndarray
    candidate_indices: np.ndarray
    cutoff: float
    pair_counting: PairCounting


def make_collection_from_fractional(
    fractional_positions: np.ndarray,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
    atomic_numbers: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    """Build a one-frame ensemble from wrapped fractional coordinates."""
    fractional = np.asarray(fractional_positions, dtype=float)
    if fractional.ndim != 2 or fractional.shape[1] != 3:
        raise ValueError("fractional_positions must have shape (n_atoms, 3).")
    n_atoms = fractional.shape[0]
    numbers = (
        np.ones(n_atoms, dtype=np.int32)
        if atomic_numbers is None
        else np.asarray(atomic_numbers, dtype=np.int32)
    )
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.array([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.ones(n_atoms, dtype=float),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=np.asarray(cell, dtype=float)[None, :, :],
        origins=np.zeros((1, 3), dtype=float),
        fractional_positions=fractional[None, :, :],
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic-neighbor-case",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def generate_random_neighbor_case(
    *,
    seed: int,
    geometry: GeometryKind,
    selection: SelectionKind,
    n_atoms: int = 24,
) -> RandomNeighborCase:
    """Generate a stable random case covering one geometry/selection regime."""
    if n_atoms < 6:
        raise ValueError("n_atoms must be at least 6.")
    rng = np.random.default_rng(seed)
    cell, pbc = _geometry(geometry)
    fractional = rng.random((n_atoms, 3))

    # Every case contains one known close pair; boundary cases exercise a
    # periodic image explicitly.  Remaining atoms stay random and reproducible.
    if geometry == "boundary":
        fractional[0] = [0.98, 0.22, 0.31]
        fractional[1] = [0.02, 0.22, 0.31]
    else:
        fractional[0] = [0.20, 0.30, 0.40]
        fractional[1] = [0.25, 0.30, 0.40]

    numbers = rng.choice(np.array([8, 13, 14], dtype=np.int32), size=n_atoms)
    collection = make_collection_from_fractional(
        fractional,
        cell=cell,
        pbc=pbc,
        atomic_numbers=numbers,
    )
    if selection == "unordered_identical":
        indices = np.arange(n_atoms, dtype=np.int64)
        centers = indices
        candidates = indices.copy()
        counting = PairCounting.UNORDERED_IDENTICAL
    else:
        permutation = rng.permutation(n_atoms).astype(np.int64)
        split = n_atoms // 2
        centers = permutation[:split]
        candidates = permutation[split:]
        counting = PairCounting.DIRECTED
    return RandomNeighborCase(
        name=f"{geometry}-{selection}-seed-{seed}",
        seed=seed,
        collection=collection,
        center_indices=centers,
        candidate_indices=candidates,
        cutoff=2.4,
        pair_counting=counting,
    )


def build_scalar_reference_neighbor_list(
    case: RandomNeighborCase,
) -> NeighborListResult:
    """Enumerate pairs one by one as an independent dense-oracle check."""
    collection = case.collection
    frame = 0
    radius = validate_cutoff(
        case.cutoff,
        collection=collection,
        frame_indices=[frame],
    )
    positions = np.asarray(collection.get_wrapped_positions(frame), dtype=float)
    cell = np.asarray(collection.cells[frame], dtype=float)
    pbc = np.asarray(collection.pbc, dtype=bool)
    centers = np.asarray(case.center_indices, dtype=np.int64)
    candidates = np.asarray(case.candidate_indices, dtype=np.int64)
    zero_tolerance = max(1.0e-12, np.finfo(float).eps * max(1.0, radius) * 64.0)

    row_counts = np.zeros(centers.size, dtype=np.int64)
    neighbors: list[int] = []
    vectors: list[np.ndarray] = []
    distances: list[float] = []
    shifts: list[np.ndarray] = []
    for row, center in enumerate(centers):
        for candidate in candidates:
            if center == candidate:
                continue
            if (
                case.pair_counting is PairCounting.UNORDERED_IDENTICAL
                and center >= candidate
            ):
                continue
            raw = positions[candidate] - positions[center]
            vector, distance, image_shift = minimum_image_geometry(
                raw[None, :],
                cell=cell,
                pbc=pbc,
            )
            scalar_distance = float(distance[0])
            if scalar_distance >= radius:
                continue
            if scalar_distance <= zero_tolerance:
                raise CoincidentAtomsError(
                    f"Distinct selected atoms {int(center)} and {int(candidate)} "
                    "are coincident in scalar reference construction."
                )
            row_counts[row] += 1
            neighbors.append(int(candidate))
            vectors.append(np.asarray(vector[0], dtype=float))
            distances.append(scalar_distance)
            shifts.append(np.asarray(image_shift[0], dtype=np.int64))

    offsets = np.empty(centers.size + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(row_counts, out=offsets[1:])
    return NeighborListResult(
        frame_index=frame,
        center_indices=centers,
        neighbor_indices=np.asarray(neighbors, dtype=np.int64),
        offsets=offsets,
        vectors=(
            np.asarray(vectors, dtype=float).reshape(-1, 3)
            if vectors
            else np.empty((0, 3), dtype=float)
        ),
        distances=np.asarray(distances, dtype=float),
        image_shifts=(
            np.asarray(shifts, dtype=np.int64).reshape(-1, 3)
            if shifts
            else np.empty((0, 3), dtype=np.int64)
        ),
        cutoff=radius,
        pair_counting=case.pair_counting,
        backend=NeighborSearchBackend.DENSE,
    )


def _geometry(geometry: GeometryKind) -> tuple[np.ndarray, np.ndarray]:
    if geometry == "orthogonal":
        return np.diag([12.0, 11.0, 10.0]), np.array([True, True, True])
    if geometry == "triclinic":
        return (
            np.array(
                [
                    [11.0, 0.0, 0.0],
                    [3.2, 10.0, 0.0],
                    [1.4, 2.1, 9.2],
                ]
            ),
            np.array([True, True, True]),
        )
    if geometry == "mixed_pbc":
        return (
            np.array(
                [
                    [12.0, 0.0, 0.0],
                    [2.5, 9.5, 0.0],
                    [1.2, 1.8, 11.0],
                ]
            ),
            np.array([True, False, True]),
        )
    if geometry == "boundary":
        return np.diag([10.0, 11.0, 12.0]), np.array([True, True, True])
    raise ValueError(f"Unknown geometry kind: {geometry!r}.")
