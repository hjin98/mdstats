"""Focused tests for periodic atomic connectivity and state cataloging."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    ConnectivityScope,
    DistanceConnectivity,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    HystereticDistanceConnectivity,
    PairCutoffRegistry,
    ReferenceDistanceConnectivity,
    compute_atomic_connectivity,
)
from mdstats.analysis.atomic_connectivity import (
    AtomicConnectivityResult,
    AtomicEdgeKey,
    ConnectivityConsistency,
    ConnectivityFrameSelectionError,
    ConnectivityScopeError,
    build_atomic_connectivity_state,
)


def make_collection(
    positions: np.ndarray,
    *,
    atomic_numbers: np.ndarray,
    semantics: FrameSemantics = FrameSemantics.ENSEMBLE,
    cell: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    positions = np.asarray(positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape
    if cell is None:
        cells = np.repeat((np.eye(3) * 10.0)[None, ...], n_frames, axis=0)
    else:
        matrix = np.asarray(cell, dtype=float)
        cells = (
            np.repeat(matrix[None, ...], n_frames, axis=0)
            if matrix.ndim == 2
            else matrix
        )
    fractional = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells))
    times = (
        np.arange(n_frames, dtype=float)
        if semantics is FrameSemantics.TRAJECTORY
        else None
    )
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool) if pbc is None else np.asarray(pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=(
            np.zeros((n_frames, n_atoms, 3))
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source=(
                "native" if semantics is FrameSemantics.TRAJECTORY else "unavailable"
            ),
            coordinate_normalization=(
                "minimum_image_inferred"
                if semantics is FrameSemantics.TRAJECTORY
                else "independent_frame_wrapping"
            ),
            stress_source=None,
            units_source="synthetic",
        ),
    )


def si_o_registry(radius: float) -> PairCutoffRegistry:
    return PairCutoffRegistry.from_mapping({("Si", "O"): radius})


def test_scope_inclusion_union_and_exclusions_win() -> None:
    collection = make_collection(
        np.zeros((4, 3)), atomic_numbers=np.array([14, 8, 11, 6])
    )
    scope = ConnectivityScope.from_selection(
        included_species=("Si", "O"),
        included_atom_indices=(2, 3),
        excluded_species=("Na",),
        excluded_atom_indices=(1,),
    )
    definition = ExplicitConnectivity(scope=scope, uniform_edges=())
    result = compute_atomic_connectivity(collection, definition)
    np.testing.assert_array_equal(result.resolved_scope.atom_indices, [0, 3])


def test_scope_rejects_absent_explicit_species() -> None:
    collection = make_collection(np.zeros((2, 3)), atomic_numbers=np.array([14, 8]))
    definition = ExplicitConnectivity(
        scope=ConnectivityScope.from_selection(included_species=("K",)),
        uniform_edges=(),
    )
    with pytest.raises(ConnectivityScopeError):
        compute_atomic_connectivity(collection, definition)


def test_distance_connectivity_builds_uniform_state() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [5.0, 0.0, 0.0]],
            [[0.1, 0.0, 0.0], [1.1, 0.0, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    collection = make_collection(positions, atomic_numbers=np.array([14, 8, 11]))
    definition = DistanceConnectivity(
        cutoffs=si_o_registry(1.5),
        scope=ConnectivityScope.from_selection(included_species=("Si", "O")),
    )
    result = compute_atomic_connectivity(collection, definition)
    assert result.consistency is ConnectivityConsistency.UNIFORM
    assert result.n_states == 1
    assert result.states[0].edge_keys == (AtomicEdgeKey(0, 1, (0, 0, 0)),)
    np.testing.assert_array_equal(result.states[0].degree, [1, 1])


def test_periodic_boundary_edge_records_image_shift() -> None:
    collection = make_collection(
        np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        atomic_numbers=np.array([14, 8]),
    )
    state = build_atomic_connectivity_state(
        collection,
        DistanceConnectivity(si_o_registry(1.5)),
        frame_index=0,
    )
    # Canonical gauge normalization moves the periodic translation onto atom representatives,
    # so a single tree edge has zero normalized shift.
    assert state.edge_keys == (AtomicEdgeKey(0, 1, (0, 0, 0)),)


def test_periodic_gauge_is_invariant_to_atom_image_representatives() -> None:
    collection = make_collection(np.zeros((3, 3)), atomic_numbers=np.array([14, 8, 14]))
    first = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 1, (1, 0, 0)),
                AtomicEdgeKey(1, 2, (0, 0, 0)),
            )
        ),
        frame_index=0,
    )
    second = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 1, (0, 0, 0)),
                AtomicEdgeKey(1, 2, (0, 0, 0)),
            )
        ),
        frame_index=0,
    )
    assert first.digest == second.digest
    np.testing.assert_array_equal(first.edge_image_shifts, second.edge_image_shifts)


def test_hysteresis_prevents_cutoff_flicker_and_builds_segments() -> None:
    distances = [1.0, 1.5, 1.7, 1.3, 1.1]
    positions = np.array(
        [[[0.0, 0.0, 0.0], [distance, 0.0, 0.0]] for distance in distances]
    )
    collection = make_collection(
        positions,
        atomic_numbers=np.array([14, 8]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    definition = HystereticDistanceConnectivity(
        formation_cutoffs=si_o_registry(1.2),
        breaking_cutoffs=si_o_registry(1.6),
    )
    result = compute_atomic_connectivity(collection, definition)
    assert result.consistency is ConnectivityConsistency.PARTITIONED
    assert result.n_states == 2
    assert result.segments is not None
    assert [
        segment.result_position_stop - segment.result_position_start
        for segment in result.segments
    ] == [2, 2, 1]
    assert len(result.transitions) == 2
    assert result.transitions[0].removed_edges
    assert result.transitions[1].added_edges


def test_hysteresis_rejects_ensemble_and_sparse_frames() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.1, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]],
        ]
    )
    definition = HystereticDistanceConnectivity(
        formation_cutoffs=si_o_registry(1.2),
        breaking_cutoffs=si_o_registry(1.6),
    )
    ensemble = make_collection(positions, atomic_numbers=np.array([14, 8]))
    with pytest.raises(Exception, match="time-ordered trajectory"):
        compute_atomic_connectivity(ensemble, definition)
    trajectory = make_collection(
        positions,
        atomic_numbers=np.array([14, 8]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    with pytest.raises(ConnectivityFrameSelectionError):
        compute_atomic_connectivity(trajectory, definition, frame_indices=[0, 2])


def test_reference_connectivity_is_order_independent_for_ensemble() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.7, 0.0, 0.0]],
        ]
    )
    collection = make_collection(positions, atomic_numbers=np.array([14, 8]))
    definition = ReferenceDistanceConnectivity(
        discovery_cutoffs=si_o_registry(1.2),
        formation_cutoffs=si_o_registry(1.1),
        retention_cutoffs=si_o_registry(1.6),
        reference_frame=0,
    )
    ordered = compute_atomic_connectivity(
        collection, definition, frame_indices=[0, 1, 2]
    )
    permuted = compute_atomic_connectivity(
        collection, definition, frame_indices=[2, 0, 1]
    )
    assert {state.digest for state in ordered.states} == {
        state.digest for state in permuted.states
    }
    assert ordered.state_for_frame(0).n_edges == 1
    assert ordered.state_for_frame(1).n_edges == 1
    assert ordered.state_for_frame(2).n_edges == 0
    assert ordered.segments is None
    assert ordered.transitions == ()


def test_per_frame_mode_does_not_reconcile_equal_states() -> None:
    collection = make_collection(
        np.array(
            [
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            ]
        ),
        atomic_numbers=np.array([14, 8]),
    )
    result = compute_atomic_connectivity(
        collection, DistanceConnectivity(si_o_registry(1.2)), state_mode="per_frame"
    )
    assert result.consistency is ConnectivityConsistency.PER_FRAME
    assert result.n_states == 2
    np.testing.assert_array_equal(result.frame_state_ids, [0, 1])


def test_result_serialization_round_trip() -> None:
    collection = make_collection(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        atomic_numbers=np.array([14, 8]),
    )
    result = compute_atomic_connectivity(
        collection, DistanceConnectivity(si_o_registry(1.2))
    )
    restored = AtomicConnectivityResult.from_dict(result.to_dict())
    assert restored.states[0].digest == result.states[0].digest
    np.testing.assert_array_equal(restored.frame_state_ids, result.frame_state_ids)
    assert restored.definition.kind == result.definition.kind


def test_non_tree_shift_preserves_periodic_cycle_information() -> None:
    collection = make_collection(np.zeros((3, 3)), atomic_numbers=np.array([14, 8, 14]))
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 1, (0, 0, 0)),
                AtomicEdgeKey(1, 2, (0, 0, 0)),
                AtomicEdgeKey(0, 2, (1, 0, 0)),
            )
        ),
        frame_index=0,
    )
    assert any(edge.image_shift != (0, 0, 0) for edge in state.edge_keys)


def test_distance_connectivity_verlet_cache_matches_uncached_result() -> None:
    from mdstats import VerletCacheOptions

    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [5.0, 0.0, 0.0]],
            [[0.05, 0.0, 0.0], [1.15, 0.0, 0.0], [5.0, 0.0, 0.0]],
            [[0.10, 0.0, 0.0], [1.10, 0.0, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    collection = make_collection(
        positions,
        atomic_numbers=np.array([14, 8, 11]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    definition = DistanceConnectivity(cutoffs=si_o_registry(1.5))
    uncached = compute_atomic_connectivity(collection, definition)
    cached = compute_atomic_connectivity(
        collection,
        definition,
        verlet_cache_options=VerletCacheOptions(skin=0.6),
    )
    assert cached.frame_state_ids.tolist() == uncached.frame_state_ids.tolist()
    assert [state.digest for state in cached.states] == [
        state.digest for state in uncached.states
    ]
    stats = cached.metadata["neighbor_cache"]
    assert stats["evaluations"] == 3
    assert stats["rebuilds"] == 1
    assert stats["reuse_evaluations"] == 2


def test_hysteretic_cache_uses_one_outer_distance_pass_per_frame() -> None:
    from mdstats import VerletCacheOptions

    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.30, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.05, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.35, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.65, 0.0, 0.0]],
        ]
    )
    collection = make_collection(
        positions,
        atomic_numbers=np.array([14, 8]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    definition = HystereticDistanceConnectivity(
        formation_cutoffs=si_o_registry(1.10),
        breaking_cutoffs=si_o_registry(1.50),
    )
    uncached = compute_atomic_connectivity(collection, definition)
    cached = compute_atomic_connectivity(
        collection,
        definition,
        verlet_cache_options=VerletCacheOptions(skin=0.5),
    )
    assert cached.frame_state_ids.tolist() == uncached.frame_state_ids.tolist()
    assert [state.digest for state in cached.states] == [
        state.digest for state in uncached.states
    ]
    stats = cached.metadata["neighbor_cache"]
    assert stats["evaluations"] == collection.n_frames
    assert stats["candidate_pair_evaluations"] >= stats["accepted_pairs"]


def test_reference_connectivity_cache_matches_uncached_result() -> None:
    from mdstats import VerletCacheOptions

    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [3.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.3, 0.0, 0.0], [2.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.7, 0.0, 0.0], [1.0, 0.0, 0.0]],
        ]
    )
    collection = make_collection(
        positions,
        atomic_numbers=np.array([14, 8, 8]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    definition = ReferenceDistanceConnectivity(
        discovery_cutoffs=si_o_registry(1.20),
        formation_cutoffs=si_o_registry(1.10),
        retention_cutoffs=si_o_registry(1.60),
        reference_frame=0,
    )
    uncached = compute_atomic_connectivity(collection, definition)
    cached = compute_atomic_connectivity(
        collection,
        definition,
        verlet_cache_options=VerletCacheOptions(skin=0.6),
    )
    assert cached.frame_state_ids.tolist() == uncached.frame_state_ids.tolist()
    assert [state.digest for state in cached.states] == [
        state.digest for state in uncached.states
    ]
    assert cached.metadata["neighbor_cache"]["evaluations"] == collection.n_frames + 1
