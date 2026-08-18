"""TS4 tests for exact atomic/framework cross-layer statistics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    CombinedStatisticsOptions,
    CrossLayerBoundaryKind,
    CrossLayerCatalogRegime,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkMapping,
    FrameworkPathRule,
    TopologyCatalogOptions,
    TopologyStatistics,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    build_topology_catalog,
    compute_atomic_connectivity,
    compute_topology_statistics,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def make_collection(
    n_frames: int, semantics: FrameSemantics
) -> AtomisticFrameCollection:
    atomic_numbers = np.asarray([14, 8, 13, 11], dtype=np.int32)
    cell = np.eye(3) * 12.0
    fractional = np.zeros((n_frames, atomic_numbers.size, 3), dtype=float)
    fractional[:, :, 0] = [0.1, 0.2, 0.3, 0.5]
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(500, 500 + n_frames, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.ones(atomic_numbers.size),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64) * 10
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        times=np.arange(n_frames, dtype=float) * 0.1
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        cells=np.repeat(cell[None, ...], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros_like(fractional)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
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


def mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "Na": "spectator"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="T-O-T with Na spectator",
    )


def make_catalogs(
    sequence: str = "XYYX",
    *,
    semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
    per_frame: bool = False,
):
    collection = make_collection(len(sequence), semantics)
    bridge = (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2))
    na_contact = AtomicEdgeKey(1, 3)
    frame_edges = {}
    for frame, label in enumerate(sequence):
        if label == "X":
            edges = bridge
        elif label == "Y":
            edges = (*bridge, na_contact)
        elif label == "Z":
            edges = (na_contact,)
        else:  # pragma: no cover - fixture guard
            raise ValueError(label)
        frame_edges[frame] = edges
    atomic = compute_atomic_connectivity(
        collection, ExplicitConnectivity(frame_edges=frame_edges)
    )
    framework = build_topology_catalog(
        collection,
        atomic,
        mapping(),
        catalog_options=TopologyCatalogOptions(
            mode="per_frame" if per_frame else "catalog"
        ),
    )
    return atomic, framework


def test_atomic_variable_framework_uniform_contingency_and_summary() -> None:
    atomic, framework = make_catalogs("XYYX")
    result = compute_topology_statistics(
        atomic,
        framework,
        steps=[0, 10, 20, 30],
        times=[0.0, 0.1, 0.2, 0.3],
        time_unit="ps",
    )
    assert (
        result.summary.regime
        is CrossLayerCatalogRegime.ATOMIC_VARIABLE_FRAMEWORK_UNIFORM
    )
    assert result.summary.interpretation == (
        "atomic connectivity varies while framework topology remains uniform"
    )
    assert result.atomic.n_states == 2
    assert result.framework.n_topologies == 1
    np.testing.assert_array_equal(result.contingency.frame_count_matrix, [[2], [2]])
    np.testing.assert_allclose(result.contingency.probability_matrix, [[0.5], [0.5]])
    np.testing.assert_array_equal(
        result.contingency.atomic_states_per_framework_class, [2]
    )
    np.testing.assert_array_equal(
        result.contingency.framework_classes_per_atomic_state, [1, 1]
    )
    assert result.contingency.atomic_to_framework_compression_ratio == 2.0
    assert result.contingency.atomic_state(0).is_deterministic
    assert result.contingency.framework_class(0).n_atomic_states == 2


def test_exact_boundary_classification_distinguishes_atomic_only_and_coupled() -> None:
    atomic, framework = make_catalogs("XYZY")
    result = compute_topology_statistics(atomic, framework)
    boundaries = result.boundary_statistics
    assert boundaries is not None
    assert boundaries.n_frame_boundaries == 3
    assert boundaries.n_atomic_only_boundaries == 1
    assert boundaries.n_coupled_boundaries == 2
    assert boundaries.n_framework_only_boundaries == 0
    assert boundaries.n_stable_boundaries == 0
    assert [event.kind for event in boundaries.events] == [
        CrossLayerBoundaryKind.ATOMIC_ONLY,
        CrossLayerBoundaryKind.COUPLED,
        CrossLayerBoundaryKind.COUPLED,
    ]
    assert result.summary.n_atomic_changed_boundaries == 3
    assert result.summary.n_framework_changed_boundaries == 2
    assert result.summary.n_framework_preserving_atomic_boundaries == 1
    assert result.summary.n_framework_changing_atomic_boundaries == 2
    assert result.summary.regime is CrossLayerCatalogRegime.FRAMEWORK_VARIABLE


def test_stable_boundaries_are_counted_but_not_materialized_as_events() -> None:
    atomic, framework = make_catalogs("XXYY")
    result = compute_topology_statistics(atomic, framework)
    boundaries = result.boundary_statistics
    assert boundaries is not None
    assert boundaries.n_stable_boundaries == 2
    assert boundaries.n_atomic_only_boundaries == 1
    assert len(boundaries.events) == 1
    assert boundaries.events[0].result_position_after == 2


def test_ensemble_has_contingency_but_no_boundary_statistics() -> None:
    atomic, framework = make_catalogs("XYZY", semantics=FrameSemantics.ENSEMBLE)
    result = compute_topology_statistics(atomic, framework)
    assert result.boundary_statistics is None
    assert result.summary.n_atomic_changed_boundaries is None
    assert result.metadata["boundary_statistics_status"] == "ensemble_non_temporal"
    assert result.atomic.axis.x_label == "Sample index"


def test_per_frame_framework_mode_disables_cross_layer_boundary_interpretation() -> (
    None
):
    atomic, framework = make_catalogs("XYYX", per_frame=True)
    result = compute_topology_statistics(atomic, framework)
    assert result.alignment_mode == "exact_per_frame"
    assert result.boundary_statistics is None
    assert result.metadata["boundary_statistics_status"] == (
        "unreconciled_per_frame_identity"
    )
    assert result.framework.n_topologies == 4


def test_option_can_disable_boundary_statistics() -> None:
    atomic, framework = make_catalogs("XYZY")
    result = compute_topology_statistics(
        atomic,
        framework,
        options=CombinedStatisticsOptions(include_boundary_statistics=False),
    )
    assert result.boundary_statistics is None
    assert result.metadata["boundary_statistics_status"] == "disabled_by_option"


def test_catalog_alignment_requires_exact_frames_ids_and_state_assignments() -> None:
    atomic, framework = make_catalogs("XYYX")

    shifted_collection = make_collection(4, FrameSemantics.TRAJECTORY)
    shifted_collection = AtomisticFrameCollection(
        frame_semantics=shifted_collection.frame_semantics,
        frame_ids=shifted_collection.frame_ids + 1,
        atomic_numbers=shifted_collection.atomic_numbers,
        masses=shifted_collection.masses,
        pbc=shifted_collection.pbc,
        steps=shifted_collection.steps,
        times=shifted_collection.times,
        cells=shifted_collection.cells,
        origins=shifted_collection.origins,
        fractional_positions=shifted_collection.fractional_positions,
        velocities=shifted_collection.velocities,
        provenance=shifted_collection.provenance,
    )
    bridge = (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2))
    na_contact = AtomicEdgeKey(1, 3)
    shifted_atomic = compute_atomic_connectivity(
        shifted_collection,
        ExplicitConnectivity(
            frame_edges={
                0: bridge,
                1: (*bridge, na_contact),
                2: (*bridge, na_contact),
                3: bridge,
            }
        ),
    )
    shifted_framework = build_topology_catalog(
        shifted_collection, shifted_atomic, mapping()
    )
    with pytest.raises(TopologyStatisticsInputError):
        compute_topology_statistics(atomic, shifted_framework)

    _, differently_ordered_framework = make_catalogs("XXYY")
    with pytest.raises(TopologyStatisticsInputError):
        compute_topology_statistics(atomic, differently_ordered_framework)


def test_combined_result_round_trip_and_digest_tampering() -> None:
    atomic, framework = make_catalogs("XYZY")
    result = compute_topology_statistics(atomic, framework)
    restored = TopologyStatistics.from_dict(result.to_dict())
    assert restored.to_dict() == result.to_dict()
    assert restored.digest == result.digest
    payload = result.to_dict()
    payload["metadata"]["tampered"] = True
    with pytest.raises(TopologyStatisticsConsistencyError):
        TopologyStatistics.from_dict(payload)


def test_contingency_arrays_are_read_only() -> None:
    atomic, framework = make_catalogs("XYYX")
    result = compute_topology_statistics(atomic, framework)
    assert not result.contingency.frame_count_matrix.flags.writeable
    assert not result.contingency.probability_matrix.flags.writeable
    with pytest.raises(ValueError):
        result.contingency.frame_count_matrix[0, 0] = 7


def test_wrong_input_types_are_rejected() -> None:
    atomic, framework = make_catalogs("XYYX")
    with pytest.raises(TypeError):
        compute_topology_statistics(object(), framework)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        compute_topology_statistics(atomic, object())  # type: ignore[arg-type]
