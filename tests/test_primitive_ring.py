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
    PrimitiveRingCatalog,
    PrimitiveRingComplexityError,
    PrimitiveRingFamily,
    PrimitiveRingInputError,
    PrimitiveRingOptions,
    PrimitiveRingSearchMethod,
    PrimitiveRingSearchStatus,
    build_atomic_connectivity_state,
    build_framework_topology,
    enumerate_primitive_rings,
    expand_primitive_ring_atomic_walk,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


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


def linker_topology(
    atomic_numbers: list[int],
    edges: tuple[AtomicEdgeKey, ...],
    *,
    rules: tuple[FrameworkPathRule, ...],
    roles: dict[str, str],
) -> FrameworkTopology:
    collection = make_collection(atomic_numbers)
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(uniform_edges=edges),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        roles,
        path_rules=rules,
        name="decorated graph",
    )
    return build_framework_topology(state, mapping)


def size_counts(catalog: PrimitiveRingCatalog) -> dict[int, int]:
    return {item.ring_size: item.ring_count for item in catalog.ring_size_counts}


def default_options(**kwargs: object) -> PrimitiveRingOptions:
    return PrimitiveRingOptions(max_ring_size=8, **kwargs)


def removed_edge_options(**kwargs: object) -> PrimitiveRingOptions:
    return PrimitiveRingOptions(
        method=PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST,
        max_ring_size=8,
        **kwargs,
    )


def test_default_method_family_and_round_trip() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    catalog = enumerate_primitive_rings(topology, options=default_options())
    assert catalog.search_method is PrimitiveRingSearchMethod.SHORTEST_PATH_PAIRS
    assert catalog.ring_family is PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT
    assert size_counts(catalog) == {3: 1}
    assert catalog.rings[0].winding == (0, 0, 0)
    assert catalog.rings[0].edge_steps == catalog.rings[0].steps
    assert PrimitiveRingCatalog.from_dict(catalog.to_dict()) == catalog
    assert json.loads(json.dumps(catalog.to_dict())) == catalog.to_dict()


def test_square_and_shortcut_rejection() -> None:
    square = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    assert size_counts(
        enumerate_primitive_rings(square, options=default_options())
    ) == {4: 1}

    diagonal = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
            AtomicEdgeKey(0, 2),
        ),
    )
    catalog = enumerate_primitive_rings(diagonal, options=default_options())
    assert size_counts(catalog) == {3: 2}
    assert catalog.diagnostics.rejected_nonprimitive > 0


def test_optional_shortcut_witnesses_explain_rejection() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
            AtomicEdgeKey(0, 2),
        ),
    )
    catalog = enumerate_primitive_rings(
        topology,
        options=default_options(generate_shortcut_witnesses=True),
    )
    assert catalog.diagnostics.rejected_nonprimitive == 2
    assert len(catalog.diagnostics.shortcut_witnesses) == 2
    witness = catalog.diagnostics.shortcut_witnesses[0]
    assert witness.shortcut_length == 1
    assert witness.first_cycle_arc_length == 2
    assert witness.second_cycle_arc_length == 2


def test_parallel_linker_paths_form_two_member_ring() -> None:
    topology = linker_topology(
        [14, 14, 8, 8],
        (
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(0, 3),
            AtomicEdgeKey(1, 3),
        ),
        rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        roles={"Si": "vertex", "O": "linker"},
    )
    catalog = enumerate_primitive_rings(topology, options=default_options())
    assert size_counts(catalog) == {2: 1}
    assert all(ids == (0,) for ids in catalog.edge_to_ring_ids)


def test_odd_and_even_tied_shortest_path_generators() -> None:
    triangle = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    triangle_catalog = enumerate_primitive_rings(triangle, options=default_options())
    assert triangle_catalog.diagnostics.odd_anchors_considered > 0

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
    theta_catalog = enumerate_primitive_rings(theta, options=default_options())
    assert size_counts(theta_catalog) == {4: 3}
    assert theta_catalog.diagnostics.even_anchors_considered > 0
    assert theta_catalog.diagnostics.shortest_paths_enumerated >= 3


def test_octagon_with_parallel_detours_is_primitive_but_not_edge_shortest() -> None:
    # Each octagon edge has a two-edge detour, so removed-edge shortest closure
    # finds only the eight triangles. The 8-cycle remains primitive because no
    # detour is shorter than the adjacent one-edge arc.
    edges: list[AtomicEdgeKey] = []
    for index in range(8):
        other = (index + 1) % 8
        edges.extend(
            (
                AtomicEdgeKey(min(index, other), max(index, other)),
                AtomicEdgeKey(index, 8 + index),
                AtomicEdgeKey(min(other, 8 + index), max(other, 8 + index)),
            )
        )
    topology = direct_topology(16, tuple(edges))
    default = enumerate_primitive_rings(topology, options=default_options())
    subset = enumerate_primitive_rings(topology, options=removed_edge_options())
    assert size_counts(default) == {3: 8, 8: 1}
    assert size_counts(subset) == {3: 8}
    assert subset.ring_family is PrimitiveRingFamily.EDGE_SHORTEST_SUBSET


def test_tree_is_empty_and_complete() -> None:
    topology = direct_topology(
        4,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(2, 3)),
    )
    catalog = enumerate_primitive_rings(topology, options=default_options())
    assert catalog.rings == ()
    assert catalog.complete_for_ring_sizes_up_to == 8
    assert not catalog.diagnostics.truncated


def test_boundary_crossing_zero_winding_ring() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1, (1, 0, 0)),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3, (-1, 0, 0)),
            AtomicEdgeKey(0, 3),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=default_options())
    assert size_counts(catalog) == {4: 1}
    assert catalog.rings[0].winding == (0, 0, 0)


def test_noncontractible_quotient_loop_is_not_local_ring() -> None:
    topology = direct_topology(
        3,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(0, 2, (1, 0, 0)),
        ),
    )
    assert not enumerate_primitive_rings(topology, options=default_options()).rings


def test_removed_edge_method_preserves_lifted_instance_semantics() -> None:
    topology = direct_topology(
        6,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(2, 4),
            AtomicEdgeKey(0, 4, (-1, 0, 0)),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(3, 5),
            AtomicEdgeKey(1, 5, (1, 0, 0)),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=removed_edge_options())
    repeated_edge_ring = [
        ring
        for ring in catalog.rings
        if sum(step.edge_index == 0 for step in ring.steps) == 2
    ]
    assert len(repeated_edge_ring) == 1
    assert repeated_edge_ring[0].size == 8
    assert catalog.diagnostics.removed_edge_searches


def test_asymmetric_decorated_paths_remain_distinct_and_expand() -> None:
    topology = linker_topology(
        [14, 13, 8, 16, 16, 8],
        (
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(0, 4),
            AtomicEdgeKey(4, 5),
            AtomicEdgeKey(1, 5),
        ),
        rules=(
            FrameworkPathRule.from_symbols(
                "Si-O-S-Al", ("O", "S"), endpoint_symbols=("Si", "Al")
            ),
            FrameworkPathRule.from_symbols(
                "Si-S-O-Al", ("S", "O"), endpoint_symbols=("Si", "Al")
            ),
        ),
        roles={"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"},
    )
    catalog = enumerate_primitive_rings(topology, options=default_options())
    assert size_counts(catalog) == {2: 1}
    assert {token.edge_key.rule_id for token in catalog.rings[0].key.edge_tokens} == {
        "Si-O-S-Al",
        "Si-S-O-Al",
    }
    walk = expand_primitive_ring_atomic_walk(topology, catalog.rings[0], close=True)
    assert walk[0] == walk[-1]
    assert {atom.atom_index for atom in walk if atom.atom_index >= 2} == {2, 3, 4, 5}


def test_determinism_and_digest_tampering() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    first = enumerate_primitive_rings(topology, options=default_options())
    second = enumerate_primitive_rings(topology, options=default_options())
    assert first == second
    assert first.digest == second.digest
    payload = first.to_dict()
    payload["complete_for_ring_sizes_up_to"] -= 1
    with pytest.raises(ValueError):
        PrimitiveRingCatalog.from_dict(payload)


def test_default_resource_limits_are_transactional() -> None:
    topology = direct_topology(
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
    state_limited = enumerate_primitive_rings(
        topology,
        options=default_options(max_lifted_states_per_source=1),
    )
    assert not state_limited.rings
    assert state_limited.diagnostics.truncated
    assert any(search.truncated for search in state_limited.diagnostics.source_searches)

    path_limited = enumerate_primitive_rings(
        topology,
        options=default_options(max_shortest_paths_per_target=1),
    )
    assert path_limited.diagnostics.truncated
    assert not path_limited.search_completed_without_resource_truncation

    candidate_limited = enumerate_primitive_rings(
        topology,
        options=default_options(max_total_candidates=1),
    )
    assert candidate_limited.diagnostics.truncated


def test_strict_resource_limit_raises() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    with pytest.raises(PrimitiveRingComplexityError):
        enumerate_primitive_rings(
            topology,
            options=default_options(max_lifted_states_per_source=1, strict=True),
        )


def test_removed_edge_resource_statuses_remain_available() -> None:
    topology = direct_topology(
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
    catalog = enumerate_primitive_rings(
        topology,
        options=removed_edge_options(max_shortest_paths_per_target=1),
    )
    assert any(
        search.status is PrimitiveRingSearchStatus.PATH_LIMIT_EXCEEDED
        for search in catalog.edge_searches
    )


def test_min_ring_size_filters_candidates() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    catalog = enumerate_primitive_rings(
        topology,
        options=PrimitiveRingOptions(min_ring_size=4, max_ring_size=8),
    )
    assert catalog.rings == ()
    assert catalog.search_completed_without_resource_truncation


def test_nonzero_self_image_edge_is_not_automatic_one_member_ring() -> None:
    base = direct_topology(1, ())
    edge = FrameworkEdgePath(
        key=FrameworkEdgeKey(
            vertex_i=0,
            vertex_j=0,
            image_shift=(1, 0, 0),
            internal_linker_indices=(),
            internal_linker_image_offsets=(),
            rule_id="direct",
        ),
        atomic_path_indices=(0, 0),
        atomic_edge_image_shifts=((1, 0, 0),),
        internal_linker_atomic_numbers=(),
        raw_image_shift=(1, 0, 0),
        edge_kind="direct",
    )
    topology = replace(
        base,
        edges=(edge,),
        degree=np.asarray([2], dtype=np.int32),
        component_labels=np.asarray([0], dtype=np.int32),
        n_components=1,
        projection_report=replace(
            base.projection_report,
            candidate_path_count=1,
            accepted_edge_count=1,
            self_image_edge_count=1,
        ),
        graph_digest="",
        digest="",
    )
    assert not enumerate_primitive_rings(topology, options=default_options()).rings


def test_na_lta_corrected_default_and_removed_edge_subset() -> None:
    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    topology = FrameworkTopology.from_dict(payload)
    default = enumerate_primitive_rings(topology, options=default_options())
    subset = enumerate_primitive_rings(topology, options=removed_edge_options())
    assert topology.n_vertices == 48
    assert topology.n_edges == 96
    assert size_counts(default) == {4: 36, 6: 40, 8: 6}
    assert size_counts(subset) == {4: 36, 6: 16}
    assert default.search_completed_without_resource_truncation
    assert default.diagnostics.index_depth == 4
    assert len(default.rings) == 82
    assert len(subset.rings) == 52
    framework_atoms = set(int(x) for x in topology.vertex_atom_indices)
    linker_atoms = set(int(x) for x in topology.resolved_roles.linker_atom_indices)
    spectator_atoms = set(
        int(x) for x in topology.resolved_roles.spectator_atom_indices
    )
    for ring in default.rings:
        assert {vertex.atom_index for vertex in ring.vertex_walk} <= framework_atoms
        expanded = expand_primitive_ring_atomic_walk(topology, ring)
        assert {atom.atom_index for atom in expanded} <= framework_atoms | linker_atoms
        assert not ({atom.atom_index for atom in expanded} & spectator_atoms)


def test_v1_catalog_migrates_as_removed_edge_subset() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    current = enumerate_primitive_rings(topology, options=removed_edge_options())
    payload = current.to_dict()
    payload.pop("search_method")
    payload.pop("ring_family")
    payload.pop("diagnostics")
    payload["canonical_schema_version"] = "mdstats.primitive-ring.v1"
    payload["options"] = {
        "min_ring_size": 2,
        "max_ring_size": 8,
        "max_lifted_states_per_edge": 250_000,
        "max_shortest_paths_per_edge": 100_000,
        "max_total_candidates": 1_000_000,
        "allow_one_member_rings": False,
        "strict_resource_limits": False,
    }
    payload["digest"] = "legacy-digest-is-not-reused"

    catalog = PrimitiveRingCatalog.from_dict(payload)
    assert catalog.search_method is PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST
    assert catalog.ring_family is PrimitiveRingFamily.EDGE_SHORTEST_SUBSET
    assert catalog.canonical_schema_version == "mdstats.primitive-ring.v2"
    assert size_counts(catalog) == {3: 1}
    assert "Migrated from v1" in catalog.diagnostics.messages[0]


def test_one_member_ring_options_are_explicitly_reserved() -> None:
    with pytest.raises(PrimitiveRingInputError, match="not implemented"):
        PrimitiveRingOptions(min_ring_size=1, allow_one_member_rings=True)
