from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    HystereticDistanceConnectivity,
    compute_atomic_connectivity,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def _load_example_module():
    path = Path(__file__).parents[1] / "examples" / "plot_lta_mixed_alkali_density.py"
    spec = importlib.util.spec_from_file_location("mdstats_lta_example_01979", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _two_frame_tetrahedral_collection() -> AtomisticFrameCollection:
    cell = np.eye(3, dtype=float) * 20.0
    cartesian = np.asarray(
        [
            [
                [10.0, 10.0, 10.0],
                [11.60, 10.0, 10.0],
                [8.35, 10.0, 10.0],
                [10.0, 11.70, 10.0],
                [10.0, 10.0, 8.25],
            ],
            [
                [10.0, 10.0, 10.0],
                [12.20, 10.0, 10.0],
                [8.35, 10.0, 10.0],
                [10.0, 11.70, 10.0],
                [10.0, 10.0, 8.25],
            ],
        ],
        dtype=float,
    )
    fractional = cartesian / 20.0
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(2, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 8, 8, 8], dtype=np.int32),
        masses=np.ones(5, dtype=float),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(2, dtype=np.int64),
        times=np.arange(2, dtype=float),
        cells=np.repeat(cell[None, :, :], 2, axis=0),
        origins=np.zeros((2, 3), dtype=float),
        fractional_positions=fractional,
        velocities=np.zeros((2, 5, 3), dtype=float),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("lta-hysteresis",),
            velocity_source="native",
            coordinate_normalization="fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_lta_example_uses_framework_only_hysteresis() -> None:
    module = _load_example_module()
    trajectory = _two_frame_tetrahedral_collection()
    definition, audit = module.framework_connectivity_definition(trajectory)

    assert isinstance(definition, HystereticDistanceConnectivity)
    assert definition.formation_cutoffs.contains("Si", "O")
    assert definition.breaking_cutoffs.contains("Si", "O")
    assert not definition.formation_cutoffs.contains("Na", "O")
    assert audit["Si"]["formation_cutoff_angstrom"] < audit["Si"]["breaking_cutoff_angstrom"]


def test_hysteresis_retains_transiently_stretched_framework_bond() -> None:
    module = _load_example_module()
    trajectory = _two_frame_tetrahedral_collection()
    definition, _audit = module.framework_connectivity_definition(trajectory)
    connectivity = compute_atomic_connectivity(trajectory, definition)

    stretched_edge = AtomicEdgeKey(0, 1)
    np.testing.assert_array_equal(
        connectivity.edge_presence(stretched_edge),
        np.asarray([True, True]),
    )
    assert connectivity.n_states == 1


def test_atomic_mean_graph_definition_extends_framework_hysteresis_only_when_needed() -> None:
    module = _load_example_module()
    trajectory = _two_frame_tetrahedral_collection()
    framework, _audit = module.framework_connectivity_definition(trajectory)
    full = module.atomic_connectivity_definition(trajectory, framework)
    assert full.to_dict() == framework.to_dict()
