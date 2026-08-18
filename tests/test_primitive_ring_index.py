from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    ExplicitConnectivity,
    FrameworkAtomRole,
    FrameworkEdgeKey,
    FrameworkEdgePath,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    LiftedEdgeInstanceRef,
    LiftedVertexRef,
    PrimitiveRingIndexInputError,
    PrimitiveRingInputError,
    PrimitiveRingOptions,
    RingEdgePlacement,
    RingPlacement,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_primitive_ring_index,
    enumerate_primitive_rings,
    ring_placements_covering_edge,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


ZERO = (0, 0, 0)


def rp(index, key, shift):
    return RingPlacement(index.topology_graph_digest, key, shift)


def make_collection(
    atomic_numbers: list[int],
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> AtomisticFrameCollection:
    n_atoms = len(atomic_numbers)
    cell = np.eye(3) * 10.0
    positions = np.arange(n_atoms * 3, dtype=float).reshape(n_atoms, 3) * 0.1
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.asarray(pbc, dtype=bool),
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


def direct_topology(
    n_vertices: int,
    edges: tuple[AtomicEdgeKey, ...],
) -> FrameworkTopology:
    collection = make_collection([14] * n_vertices)
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(uniform_edges=edges),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": FrameworkAtomRole.VERTEX},
        path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        name="direct graph",
    )
    return build_framework_topology(state, mapping)


def options(max_ring_size: int = 8) -> PrimitiveRingOptions:
    return PrimitiveRingOptions(max_ring_size=max_ring_size)


def test_stable_key_lookup_and_unknown_key_rejection() -> None:
    triangle = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    square = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    triangle_catalog = enumerate_primitive_rings(triangle, options=options())
    square_catalog = enumerate_primitive_rings(square, options=options())
    index = build_primitive_ring_index(triangle_catalog)

    ring = triangle_catalog.rings[0]
    assert index.ring_id_for_key(ring.key) == ring.ring_id
    assert index.ring_for_key(ring.key) is ring
    with pytest.raises(PrimitiveRingIndexInputError, match="absent"):
        index.ring_id_for_key(square_catalog.rings[0].key)


def test_canonical_edge_anchor_handles_forward_and_reverse_steps() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1, (1, 0, 0)),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3, (-1, 0, 0)),
            AtomicEdgeKey(0, 3),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    ring = catalog.rings[0]
    saw_forward = False
    saw_reverse = False

    for step_index, step in enumerate(ring.steps):
        source = ring.vertex_walk[step_index]
        edge_key = catalog.edge_searches[step.edge_index].edge_key
        instance = index.canonical_edge_instance(ring.key, step_index)
        if step.orientation == 1:
            saw_forward = True
            expected = source.image_shift
        else:
            saw_reverse = True
            expected = tuple(
                a - b
                for a, b in zip(source.image_shift, edge_key.image_shift, strict=True)
            )
        assert instance.edge_key == edge_key
        assert instance.anchor_shift == expected

    assert saw_forward
    assert saw_reverse


def test_common_translation_is_recovered_for_boundary_crossing_ring() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1, (1, 0, 0)),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3, (-1, 0, 0)),
            AtomicEdgeKey(0, 3),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    ring = catalog.rings[0]
    translation = (2, -3, 1)

    for step_index, step in enumerate(ring.steps):
        canonical = index.canonical_edge_instance(ring.key, step_index)
        target = LiftedEdgeInstanceRef(
            index.topology_graph_digest,
            canonical.edge_key,
            tuple(
                a + b
                for a, b in zip(canonical.anchor_shift, translation, strict=True)
            ),
        )
        expected = RingEdgePlacement(
            placement=rp(index, ring.key, translation),
            step_index=step_index,
            orientation=step.orientation,
        )
        assert expected in ring_placements_covering_edge(index, target)


def test_parallel_edges_remain_distinct_for_two_member_ring() -> None:
    collection = make_collection([14, 14, 8, 8])
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 2),
                AtomicEdgeKey(1, 2),
                AtomicEdgeKey(0, 3),
                AtomicEdgeKey(1, 3),
            )
        ),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="parallel linker graph",
    )
    topology = build_framework_topology(state, mapping)
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    ring = catalog.rings[0]

    assert ring.size == 2
    assert ring.steps[0].edge_index != ring.steps[1].edge_index
    first = index.canonical_edge_instance(ring.key, 0)
    second = index.canonical_edge_instance(ring.key, 1)
    first_hits = ring_placements_covering_edge(index, first)
    second_hits = ring_placements_covering_edge(index, second)
    assert {hit.step_index for hit in first_hits if hit.placement.ring_key == ring.key} == {0}
    assert {hit.step_index for hit in second_hits if hit.placement.ring_key == ring.key} == {1}


def test_shared_edge_returns_all_represented_ring_occurrences() -> None:
    theta = direct_topology(
        5,
        (
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(0, 3),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(0, 4),
            AtomicEdgeKey(1, 4),
        ),
    )
    catalog = enumerate_primitive_rings(theta, options=options())
    index = build_primitive_ring_index(catalog)
    assert len(catalog.rings) == 3

    edge_index = next(
        i for i, ring_ids in enumerate(catalog.edge_to_ring_ids) if len(ring_ids) == 2
    )
    seed_ring = catalog.rings[catalog.edge_to_ring_ids[edge_index][0]]
    seed_step = next(i for i, step in enumerate(seed_ring.steps) if step.edge_index == edge_index)
    edge_instance = index.canonical_edge_instance(seed_ring.key, seed_step)
    hits = ring_placements_covering_edge(index, edge_instance)

    assert len(hits) == 2
    assert {hit.placement.ring_key for hit in hits} == {
        catalog.rings[ring_id].key for ring_id in catalog.edge_to_ring_ids[edge_index]
    }


def test_invalid_edge_and_step_indices_are_rejected() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    ring = catalog.rings[0]

    with pytest.raises(PrimitiveRingIndexInputError, match="outside ring size"):
        index.canonical_edge_instance(ring.key, ring.size)
    with pytest.raises(PrimitiveRingIndexInputError, match="source catalog"):
        ring_placements_covering_edge(
            index,
            LiftedEdgeInstanceRef(index.topology_graph_digest, FrameworkEdgeKey(100, 101, ZERO, (), (), "missing"), ZERO),
        )


def test_catalog_rejects_discontinuous_stored_vertex_walk() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    ring = catalog.rings[0]
    vertices = list(ring.vertex_walk)
    vertices[1] = LiftedVertexRef(vertices[1].atom_index, (1, 0, 0))
    bad_ring = replace(ring, vertex_walk=tuple(vertices), digest="")

    with pytest.raises(PrimitiveRingInputError, match="discontinuous"):
        # Sanity: the index itself is never reached because the hardened source
        # catalog constructor must reject the inconsistent stored walk first.
        build_primitive_ring_index(replace(catalog, rings=(bad_ring,), digest=""))


def test_na_lta_exact_occurrence_gate() -> None:
    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    topology = FrameworkTopology.from_dict(payload)
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)

    assert {item.ring_size: item.ring_count for item in catalog.ring_size_counts} == {
        4: 36,
        6: 40,
        8: 6,
    }
    assert len(catalog.rings) == 82
    assert index.occurrence_count == 432

    for ring in catalog.rings:
        assert index.ring_for_key(ring.key) is ring
        for step_index, step in enumerate(ring.steps):
            edge_instance = index.canonical_edge_instance(ring.key, step_index)
            expected = RingEdgePlacement(
                placement=rp(index, ring.key, ZERO),
                step_index=step_index,
                orientation=step.orientation,
            )
            assert expected in ring_placements_covering_edge(index, edge_instance)

    translation = (3, -2, 1)
    sampled = [
        (ring, step_index)
        for ring in catalog.rings
        for step_index in range(ring.size)
    ][::17]
    for ring, step_index in sampled:
        step = ring.steps[step_index]
        canonical = index.canonical_edge_instance(ring.key, step_index)
        translated = LiftedEdgeInstanceRef(
            index.topology_graph_digest,
            canonical.edge_key,
            tuple(
                a + b
                for a, b in zip(canonical.anchor_shift, translation, strict=True)
            ),
        )
        expected = RingEdgePlacement(
            placement=rp(index, ring.key, translation),
            step_index=step_index,
            orientation=step.orientation,
        )
        assert expected in ring_placements_covering_edge(index, translated)
