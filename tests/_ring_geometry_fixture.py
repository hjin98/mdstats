from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from ase.data import atomic_masses, atomic_numbers

from mdstats.analysis import build_reference_ring_geometry_catalog
from mdstats.analysis.atomic_connectivity import (
    AtomicEdgeKey,
    ConnectivityScope,
    ExplicitConnectivity,
    compute_atomic_connectivity,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics

from tests._lta_tiling_fixture import DATA, lta_reference_geometry


def _read_poscar(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lines = path.read_text().splitlines()
    scale = float(lines[1].split()[0])
    cell = np.asarray(
        [[float(value) for value in lines[index].split()[:3]] for index in range(2, 5)],
        dtype=np.float64,
    ) * scale
    symbols = lines[5].split()
    counts = [int(value) for value in lines[6].split()]
    position = 7
    if lines[position].strip().lower().startswith("s"):
        position += 1
    mode = lines[position].strip().lower()
    position += 1
    n_atoms = sum(counts)
    coordinates = np.asarray(
        [
            [float(value) for value in lines[position + index].split()[:3]]
            for index in range(n_atoms)
        ],
        dtype=np.float64,
    )
    if mode.startswith("c"):
        coordinates = coordinates @ np.linalg.inv(cell)
    numbers = np.concatenate(
        [
            np.full(count, atomic_numbers[symbol], dtype=np.int32)
            for symbol, count in zip(symbols, counts, strict=True)
        ]
    )
    return cell, coordinates, numbers


def make_lta_collection(
    *,
    fractional_positions: np.ndarray | None = None,
    cell: np.ndarray | None = None,
    origin: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    source_cell, source_fractional, numbers = _read_poscar(DATA / "Na_LTA_relaxed.POSCAR")
    active_cell = source_cell if cell is None else np.asarray(cell, dtype=np.float64)
    active_fractional = (
        source_fractional
        if fractional_positions is None
        else np.asarray(fractional_positions, dtype=np.float64)
    )
    active_origin = np.zeros(3, dtype=np.float64) if origin is None else np.asarray(origin, dtype=np.float64)
    masses = np.asarray([atomic_masses[int(number)] for number in numbers], dtype=np.float64)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=masses,
        pbc=np.asarray([True, True, True]),
        steps=None,
        times=None,
        cells=active_cell[None, :, :],
        origins=active_origin[None, :],
        fractional_positions=active_fractional[None, :, :],
        metadata={},
        provenance=FrameCollectionProvenance(
            source_format="ase-structure",
            source_files=("Na_LTA_relaxed.POSCAR",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="VASP POSCAR",
        ),
    )


def make_framework_connectivity(collection: AtomisticFrameCollection):
    topology, _reference, _geometry = lta_reference_geometry()
    edges: set[AtomicEdgeKey] = set()
    framework_atoms: set[int] = set()
    for path in topology.edges:
        framework_atoms.update(int(value) for value in path.atomic_path_indices)
        for atom_i, atom_j, shift in zip(
            path.atomic_path_indices[:-1],
            path.atomic_path_indices[1:],
            path.atomic_edge_image_shifts,
            strict=True,
        ):
            edges.add(AtomicEdgeKey(int(atom_i), int(atom_j), tuple(int(value) for value in shift)))
    scope = ConnectivityScope.from_selection(
        included_atom_indices=tuple(sorted(framework_atoms))
    )
    return compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(scope=scope, uniform_edges=tuple(sorted(edges))),
    )


@lru_cache(maxsize=1)
def lta_reference_ring_geometry_fixture():
    topology, reference, geometry = lta_reference_geometry()
    collection = make_lta_collection()
    connectivity = make_framework_connectivity(collection)
    catalog = build_reference_ring_geometry_catalog(
        geometry,
        reference.complex,
        reference.ring_index,
        topology,
        collection,
        connectivity,
    )
    return topology, reference, geometry, collection, connectivity, catalog
