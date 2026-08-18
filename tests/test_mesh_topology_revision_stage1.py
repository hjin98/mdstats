"""Stage 1 regression locks for the mesh-budget/topology revision.

These tests intentionally preserve and reproduce the four reported 0.19.73a0
failure modes. Later stages will change the expected outcome while retaining the
same deterministic fixtures.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    BrowserMeshBudget,
    BrowserMeshBudgetFailure,
    BrowserMeshTraceUsage,
    BrowserMeshUsage,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkMapping,
    FrameworkPathRule,
    TopologyConsistency,
    build_topology_catalog,
    compute_atomic_connectivity,
    require_browser_mesh_budget,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey
from mdstats.plotting.density_sparse_mesh import _require_sparse_mesh_face_limit
from mdstats.plotting.graph_errors import GraphComplexityError

_DATA = Path(__file__).parent / "data" / "mesh_topology_revision_stage1_cases.json"
_CASES = json.loads(_DATA.read_text())


def _seven_topology_catalog():
    """Return a real seven-class projected framework catalog in seven frames."""

    # Four T atoms provide six distinct endpoint pairs. Six O linkers encode one
    # projected edge per pair; the final frame is the empty projected topology.
    atomic_numbers = np.asarray([14, 14, 13, 13, 8, 8, 8, 8, 8, 8], dtype=np.int32)
    n_frames = 7
    n_atoms = int(atomic_numbers.size)
    collection = AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=np.repeat((np.eye(3) * 20.0)[None, ...], n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("mesh-topology-stage1",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )
    endpoint_pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    frame_edges: dict[int, tuple[AtomicEdgeKey, ...]] = {}
    for frame_index, (left, right) in enumerate(endpoint_pairs):
        linker = 4 + frame_index
        frame_edges[frame_index] = (
            AtomicEdgeKey(left, linker),
            AtomicEdgeKey(linker, right),
        )
    frame_edges[6] = ()
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(frame_edges=frame_edges),
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="T-O-T-stage1-seven-class",
    )
    return build_topology_catalog(collection, connectivity, mapping)


@pytest.mark.parametrize(
    "face_count",
    tuple(_CASES["browser_scene_face_overshoots"]),
)
def test_reported_browser_face_overshoots_reproduce_exact_failure(face_count: int) -> None:
    """Lock the 301,838 and 314,640 post-replication failures."""

    budget = BrowserMeshBudget(
        max_final_density_faces=int(_CASES["browser_face_budget"]),
        max_final_density_vertices=1_000_000,
        max_plotly_traces=64,
    )
    usage = BrowserMeshUsage(
        density_traces=(
            BrowserMeshTraceUsage(
                trace_key=f"reported-scene-{face_count}",
                face_count=face_count,
                vertex_count=150_000,
            ),
        ),
        non_density_trace_count=4,
    )
    with pytest.raises(
        BrowserMeshBudgetFailure,
        match=rf"final_density_faces={face_count}>{_CASES['browser_face_budget']}",
    ) as error:
        require_browser_mesh_budget(usage, budget=budget)
    assert error.value.report.violations == (
        f"final_density_faces={face_count}>{_CASES['browser_face_budget']}",
    )


def test_reported_sparse_shell_reproduces_fixed_per_shell_failure() -> None:
    """Lock the 582,375 versus 250,000 terminal shell failure cheaply."""

    face_count = int(_CASES["sparse_shell_face_count"])
    face_limit = int(_CASES["sparse_shell_face_limit"])
    with pytest.raises(
        GraphComplexityError,
        match=(
            rf"Sparse density mesh contains {face_count} faces after optional "
            rf"simplification, exceeding max_mesh_faces={face_limit}"
        ),
    ):
        _require_sparse_mesh_face_limit(
            face_count,
            face_limit,
            after_simplification=True,
        )


def test_seven_category_catalog_fixture_is_exact_and_deterministic() -> None:
    """Lock a real seven-class partitioned topology fixture for later stages."""

    first = _seven_topology_catalog()
    second = _seven_topology_catalog()
    assert first.consistency is TopologyConsistency.PARTITIONED
    assert first.n_topologies == int(_CASES["partitioned_topology_count"])
    np.testing.assert_array_equal(first.frame_topology_ids, np.arange(7))
    assert first.digest == second.digest
    assert first.to_dict() == second.to_dict()


def test_example_no_longer_contains_uniform_only_rejection() -> None:
    example_path = (
        Path(__file__).parents[1] / "examples" / "plot_lta_mixed_alkali_density.py"
    )
    source = example_path.read_text()
    assert "require_uniform_topology_catalog" not in source
    assert "TopologyCatalog.from_dict" in source
    assert "HystereticDistanceConnectivity" in source

