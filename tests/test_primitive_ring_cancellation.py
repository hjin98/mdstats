from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    ExplicitConnectivity,
    FiniteRingCancellationStatus,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    PrimitiveRingCancellationInputError,
    PrimitiveRingOptions,
    RingPlacement,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_primitive_ring_index,
    enumerate_primitive_rings,
    ring_placement_support,
    ring_placements_covering_edge,
    solve_finite_ring_cancellation,
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


def weak_primitive_fixture():
    # Outer 6-cycle plus center 6 connected to alternating vertices 0,2,4.
    # The three center routes tie (do not shorten) the corresponding two-edge
    # outer arcs, so the outer 6-ring is primitive/no-strict-shortcut but equals
    # the GF(2) sum of the three 4-rings.
    topology = direct_topology(
        7,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(3, 4),
            AtomicEdgeKey(4, 5),
            AtomicEdgeKey(0, 5),
            AtomicEdgeKey(0, 6),
            AtomicEdgeKey(2, 6),
            AtomicEdgeKey(4, 6),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    rings4 = tuple(ring for ring in catalog.rings if ring.size == 4)
    rings6 = tuple(ring for ring in catalog.rings if ring.size == 6)
    assert len(rings4) == 3
    assert len(rings6) == 1
    return catalog, index, rings4, rings6[0]


def test_exact_three_component_decomposition_of_weak_primitive_ring() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    target = rp(index, ring6.key, ZERO)
    candidates = tuple(rp(index, ring.key, ZERO) for ring in reversed(rings4))

    result = solve_finite_ring_cancellation(index, target, candidates)

    assert result.status is FiniteRingCancellationStatus.DECOMPOSITION_FOUND
    assert result.witness is not None
    assert result.witness.target_placement == target
    assert result.witness.component_placements == tuple(sorted(candidates))
    assert result.candidate_placements == tuple(sorted(candidates))


def test_common_translation_preserves_exact_decomposition() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    shift = (3, -2, 1)
    target = rp(index, ring6.key, shift)
    candidates = tuple(rp(index, ring.key, shift) for ring in rings4)

    result = solve_finite_ring_cancellation(index, target, candidates)

    assert result.status is FiniteRingCancellationStatus.DECOMPOSITION_FOUND
    assert result.witness is not None
    target_support = ring_placement_support(index, target)
    zero_support = ring_placement_support(index, rp(index, ring6.key, ZERO))
    assert tuple(
        (edge.edge_key, tuple(a - b for a, b in zip(edge.anchor_shift, base.anchor_shift, strict=True)))
        for edge, base in zip(target_support.edge_instances, zero_support.edge_instances, strict=True)
    ) == tuple((edge.edge_key, shift) for edge in target_support.edge_instances)


def test_missing_or_wrong_image_component_is_not_in_supplied_span() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    target = rp(index, ring6.key, ZERO)
    correct = tuple(rp(index, ring.key, ZERO) for ring in rings4)

    missing = solve_finite_ring_cancellation(index, target, correct[:2])
    assert missing.status is FiniteRingCancellationStatus.NOT_IN_SUPPLIED_SPAN
    assert missing.witness is None

    wrong_image = correct[:2] + (rp(index, rings4[2].key, (1, 0, 0)),)
    wrong = solve_finite_ring_cancellation(index, target, wrong_image)
    assert wrong.status is FiniteRingCancellationStatus.NOT_IN_SUPPLIED_SPAN
    assert wrong.witness is None


def test_candidate_order_and_redundant_remote_candidate_do_not_change_witness() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    target = rp(index, ring6.key, ZERO)
    correct = tuple(rp(index, ring.key, ZERO) for ring in rings4)
    remote = rp(index, rings4[0].key, (5, 0, 0))

    first = solve_finite_ring_cancellation(index, target, (*correct, remote))
    second = solve_finite_ring_cancellation(index, target, (remote, *reversed(correct)))

    assert first == second
    assert first.witness is not None
    assert remote not in first.witness.component_placements


def test_duplicate_equal_and_larger_candidates_are_rejected() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    target6 = rp(index, ring6.key, ZERO)
    candidate4 = rp(index, rings4[0].key, ZERO)

    with pytest.raises(PrimitiveRingCancellationInputError, match="duplicate"):
        solve_finite_ring_cancellation(index, target6, (candidate4, candidate4))

    with pytest.raises(PrimitiveRingCancellationInputError, match="strictly smaller"):
        solve_finite_ring_cancellation(
            index,
            target6,
            (rp(index, ring6.key, (1, 0, 0)),),
        )

    target4 = candidate4
    with pytest.raises(PrimitiveRingCancellationInputError, match="strictly smaller"):
        solve_finite_ring_cancellation(index, target4, (target6,))


def test_empty_candidate_set_is_exact_negative_only() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    result = solve_finite_ring_cancellation(
        index,
        rp(index, ring6.key, ZERO),
        (),
    )
    assert result.status is FiniteRingCancellationStatus.NOT_IN_SUPPLIED_SPAN
    assert result.witness is None
    assert result.candidate_placements == ()


def test_parallel_edges_remain_distinct_in_support() -> None:
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

    support = ring_placement_support(index, rp(index, ring.key, ZERO))
    assert ring.size == 2
    assert len(support.edge_instances) == 2
    assert support.edge_instances[0].edge_key != support.edge_instances[1].edge_key


def test_na_lta_support_ground_gate() -> None:
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
    translation = (2, -1, 3)

    for ring in catalog.rings:
        zero = rp(index, ring.key, ZERO)
        moved = rp(index, ring.key, translation)
        support0 = ring_placement_support(index, zero)
        support1 = ring_placement_support(index, moved)
        assert len(support0.edge_instances) == ring.size
        assert len(support1.edge_instances) == ring.size
        assert len(set(support0.edge_instances)) == ring.size
        assert len(set(support1.edge_instances)) == ring.size

        shifted_expected = {
            (edge.edge_key, tuple(a + b for a, b in zip(edge.anchor_shift, translation, strict=True)))
            for edge in support0.edge_instances
        }
        shifted_actual = {
            (edge.edge_key, edge.anchor_shift) for edge in support1.edge_instances
        }
        assert shifted_actual == shifted_expected

        for edge in support0.edge_instances:
            hits = ring_placements_covering_edge(index, edge)
            assert any(hit.placement == zero for hit in hits)
