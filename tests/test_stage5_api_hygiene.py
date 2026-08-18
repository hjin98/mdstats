from __future__ import annotations

import mdstats
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    CycleParameterization,
    ExplicitConnectivity,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    LiftedEdgeInstanceRef,
    PrimitiveRingCancellationInputError,
    PrimitiveRingIndexInputError,
    PrimitiveRingOptions,
    RingPlacement,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_primitive_ring_index,
    enumerate_primitive_rings,
    ring_placement_support,
    ring_placements_covering_edge,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics
import numpy as np

ZERO = (0, 0, 0)


def _collection(n: int) -> AtomisticFrameCollection:
    cell = np.eye(3) * 10.0
    positions = np.arange(n * 3, dtype=float).reshape(n, 3) * 0.1
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=np.asarray([14] * n, dtype=np.int32),
        masses=np.ones(n),
        pbc=np.asarray((True, True, True), dtype=bool),
        steps=None,
        times=None,
        cells=cell[None, ...],
        origins=np.zeros((1, 3)),
        fractional_positions=(positions @ np.linalg.inv(cell))[None, ...],
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _index(n: int, edges: tuple[AtomicEdgeKey, ...]):
    state = build_atomic_connectivity_state(
        _collection(n), ExplicitConnectivity(uniform_edges=edges), frame_index=0
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": FrameworkAtomRole.VERTEX},
        path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        name="direct",
    )
    topology = build_framework_topology(state, mapping)
    catalog = enumerate_primitive_rings(
        topology, options=PrimitiveRingOptions(max_ring_size=8)
    )
    return build_primitive_ring_index(catalog)


def test_cycle_parameterization_matches_declared_vertex_and_step_rules() -> None:
    forward = CycleParameterization(start_vertex_index=2, orientation=1)
    reverse = CycleParameterization(start_vertex_index=2, orientation=-1)
    assert forward.vertex_permutation(5) == (2, 3, 4, 0, 1)
    assert forward.step_permutation(5) == (2, 3, 4, 0, 1)
    assert reverse.vertex_permutation(5) == (2, 1, 0, 4, 3)
    assert reverse.step_permutation(5) == (1, 0, 4, 3, 2)


def test_source_bound_ring_and_edge_records_reject_cross_topology_use() -> None:
    triangle = _index(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    square = _index(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    ring = triangle.catalog.rings[0]
    placement = RingPlacement(triangle.topology_graph_digest, ring.key, ZERO)
    edge = triangle.canonical_edge_instance(ring.key, 0)

    with pytest.raises(PrimitiveRingIndexInputError, match="different topology"):
        square.translated_edge_instances(placement)
    with pytest.raises(PrimitiveRingIndexInputError, match="different topology"):
        ring_placements_covering_edge(square, edge)
    with pytest.raises(PrimitiveRingCancellationInputError, match="different topology"):
        ring_placement_support(square, placement)


def test_canonical_support_accessor_preserves_order_and_translation() -> None:
    index = _index(
        4,
        (
            AtomicEdgeKey(0, 1, (1, 0, 0)),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3, (-1, 0, 0)),
            AtomicEdgeKey(0, 3),
        ),
    )
    ring = index.catalog.rings[0]
    canonical = index.canonical_edge_instances(ring.key)
    shift = (3, -2, 1)
    moved = index.translated_edge_instances(
        RingPlacement(index.topology_graph_digest, ring.key, shift)
    )
    assert len(canonical) == ring.size
    assert tuple(edge.edge_key for edge in canonical) == tuple(edge.edge_key for edge in moved)
    assert tuple(
        tuple(a + b for a, b in zip(edge.anchor_shift, shift, strict=True))
        for edge in canonical
    ) == tuple(edge.anchor_shift for edge in moved)


def test_stage5_advanced_infrastructure_is_not_reexported_at_package_root() -> None:
    for name in (
        "PrimitiveRingIndex",
        "RingPlacement",
        "ValidatedPeriodicAutomorphism",
        "LiftedEdgeInstanceRef",
    ):
        assert not hasattr(mdstats, name)
