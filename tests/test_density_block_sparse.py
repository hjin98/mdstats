"""LD1-B production atomic block-sparse density tests."""

from __future__ import annotations

import json

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    DISCRETE_PERIODIZED_OPERATOR,
    DensityKernelOptions,
    DensitySourceProvenance,
    DensityRenderOptions,
    DensityStorageOptions,
    DistanceConnectivity,
    FrameCollectionProvenance,
    ExpandedCellDisplay,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDensityOptions,
    FrameworkMapping,
    FrameworkPathRule,
    GAUSSIAN_SIGMA_BROADENING,
    PeriodicBlockScalarField3D,
    PeriodicPackedBlockScalarField3D,
    PairCutoffRegistry,
    PeriodicWeightedSamples3D,
    build_framework_topology,
    compute_atomic_connectivity,
    pack_sparse_reference_blocks,
    plan_block_packing,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
    prepare_sparse_canonical_density_reference,
)
from mdstats.plotting.atomic_density import prepare_atomic_density_fields
from mdstats.plotting.graph_errors import (
    GraphComplexityError,
    GraphUnsupportedFeatureError,
)


def weighted_samples(
    positions: np.ndarray, weights: np.ndarray | None = None
) -> PeriodicWeightedSamples3D:
    positions = np.asarray(positions, dtype=np.float64)
    if weights is None:
        weights = np.ones(positions.shape[0], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(2,)
        ),
        total_measure=float(np.sum(weights, dtype=np.float64)),
        measure_kind="occupancy",
        measure_units="count",
    )


def reference_field(
    *,
    shape: tuple[int, int, int] = (10, 9, 7),
    sigma: float = 0.36,
):
    cell = np.asarray(
        [[5.0, 0.0, 0.0], [1.2, 4.5, 0.0], [0.7, 0.4, 3.8]],
        dtype=np.float64,
    )
    batch = weighted_samples(
        np.asarray([[0.113, 0.287, 0.619], [0.913, 0.887, 0.019]]),
        np.asarray([0.35, 0.65]),
    )
    return prepare_sparse_canonical_density_reference(
        batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="atomic-density-0",
        label="Na density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )


def make_collection() -> AtomisticFrameCollection:
    fractional = np.asarray(
        [
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.70, 0.50, 0.50]],
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.71, 0.50, 0.50]],
        ],
        dtype=np.float64,
    )
    n_frames, n_atoms, _ = fractional.shape
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11], dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-block-sparse",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_block_packing_matches_flat_reference_and_partial_masks() -> None:
    reference = reference_field()
    field = pack_sparse_reference_blocks(
        reference,
        block_shape=(4, 4, 4),
        selected_atom_indices=(2,),
        max_stored_block_values=1_000_000,
    )
    assert isinstance(field, PeriodicBlockScalarField3D)
    assert field.block_valid_masks is not None
    np.testing.assert_array_equal(
        field.to_dense_values(max_nodes=10_000_000),
        reference.to_dense_values(max_nodes=10_000_000),
    )
    assert field.integral == pytest.approx(reference.integral, abs=5.0e-13)
    for q in (0.5, 0.8, 0.95):
        assert field.hdr_details(q).to_json_dict() == reference.hdr_details(q).to_json_dict()


def test_public_iteration_and_periodic_gather_match_reference() -> None:
    reference = reference_field(shape=(11, 10, 9), sigma=0.31)
    field = pack_sparse_reference_blocks(reference, block_shape=(3, 4, 5))
    batches = list(field.iter_stored_nodes(batch_size=17))
    coordinates = np.concatenate([batch[0] for batch in batches], axis=0)
    values = np.concatenate([batch[1] for batch in batches], axis=0)
    flat = np.ravel_multi_index(
        (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]),
        field.grid_shape,
        order="C",
    )
    np.testing.assert_array_equal(flat, reference.active_flat_indices)
    np.testing.assert_array_equal(values, reference.active_values)

    queries = np.asarray(
        [[0, 0, 0], [10, 9, 8], [-1, -1, -1], [11, 10, 9], [22, -10, 18]],
        dtype=np.int64,
    )
    np.testing.assert_array_equal(
        field.gather_node_values(queries), reference.gather_node_values(queries)
    )


def test_block_field_json_round_trip_is_exact() -> None:
    field = pack_sparse_reference_blocks(reference_field(), block_shape=(4, 4, 4))
    payload = field.to_json_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    restored = PeriodicBlockScalarField3D.from_json_dict(json.loads(encoded))
    assert restored.metadata == field.metadata
    np.testing.assert_array_equal(restored.active_block_indices, field.active_block_indices)
    np.testing.assert_array_equal(restored.block_values, field.block_values)
    np.testing.assert_array_equal(restored.block_valid_masks, field.block_valid_masks)
    np.testing.assert_array_equal(
        restored.to_dense_values(max_nodes=10_000_000),
        field.to_dense_values(max_nodes=10_000_000),
    )


def test_packing_limit_fails_before_block_value_allocation(monkeypatch) -> None:
    reference = reference_field(shape=(12, 11, 10), sigma=0.4)
    called = False

    def forbidden_zeros(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("block-value allocation occurred")

    monkeypatch.setattr("mdstats.plotting.density_block_sparse.np.zeros", forbidden_zeros)
    with pytest.raises(GraphComplexityError, match="max_stored_block_values"):
        pack_sparse_reference_blocks(
            reference,
            block_shape=(4, 4, 4),
            max_stored_block_values=1,
        )
    assert called is False


def test_atomic_local_sparse_species_selection_and_dense_budget_independence() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(64, 64, 64),
        gaussian_bandwidth=0.0,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    fields = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(species=("Si", "Al"), label="T density"),),
        options=options,
        max_fields=2,
        max_total_voxels=64,
        max_samples=100,
        max_stored_block_values=100_000,
    )
    field = fields[0]
    assert isinstance(field, PeriodicPackedBlockScalarField3D)
    assert field.selected_atom_indices == (0, 2)
    assert field.source_provenance.atom_indices == (0, 2)
    assert field.total_measure == 2.0
    assert field.integral == pytest.approx(2.0, abs=5.0e-13)
    assert field.metadata["sparse_resolution_independent_of_dense_voxel_budget"] is True
    assert int(np.prod(field.grid_shape)) > 64


def test_localized_storage_gate_exceeds_tenfold_reduction() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(128, 128, 128),
        gaussian_bandwidth=0.0,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    field = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,)),),
        options=options,
        max_fields=1,
        max_total_voxels=64,
        max_samples=100,
        max_stored_block_values=100_000,
    )[0]
    summary = field.storage_summary()
    fraction = summary.stored_value_count / summary.logical_node_count
    assert fraction <= 0.10
    assert summary.logical_node_count / summary.stored_value_count >= 10.0


def test_local_sparse_defaults_to_supported_discrete_operator() -> None:
    options = AtomicDensityOptions(
        storage_options=DensityStorageOptions(grid_backend="local_sparse")
    )
    assert options.kernel_options.smoothing_operator == DISCRETE_PERIODIZED_OPERATOR


def test_plan_block_packing_is_deterministic() -> None:
    reference = reference_field(shape=(13, 11, 9), sigma=0.28)
    first = plan_block_packing(
        reference.active_flat_indices,
        logical_grid_shape=reference.grid_shape,
        block_shape=(5, 4, 3),
    )
    second = plan_block_packing(
        reference.active_flat_indices.copy(),
        logical_grid_shape=reference.grid_shape,
        block_shape=(5, 4, 3),
    )
    assert first.to_json_dict() == second.to_json_dict()



def framework_topology(collection: AtomisticFrameCollection):
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols(
                "T-O-T", ("O",), edge_kind="oxygen_bridge"
            ),
        ),
    )
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.1, ("Al", "O"): 2.1}
        )
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, mapping)


def test_scene_planner_records_sparse_counts_and_renderer_supports_ld2_b_mesh() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(64, 64, 64),
        gaussian_bandwidth=0.0,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=options,
    )
    field = scene.atomic_density_fields[0]
    assert isinstance(field, PeriodicPackedBlockScalarField3D)
    assert field.metadata["production_backend"] is True
    assert scene.planning_record is not None
    phase_b = scene.planning_record.phase_b_fields[0]
    assert phase_b.metadata["backend"] == "local_sparse"
    assert phase_b.stored_block_count == field.storage_summary().stored_block_count
    assert phase_b.stored_value_count >= field.storage_summary().stored_value_count
    realized_phase_b = field.metadata["density_planning"]["phase_b"]
    assert realized_phase_b["stored_value_count"] == field.storage_summary().stored_value_count
    if "planned_fixed_block_stored_value_count" in realized_phase_b:
        assert realized_phase_b["planned_fixed_block_stored_value_count"] == phase_b.stored_value_count
    else:
        assert realized_phase_b["realized_target_node_count"] == field.storage_summary().stored_value_count
        assert realized_phase_b["realized_target_block_count"] == field.storage_summary().stored_block_count
        assert realized_phase_b["hybrid_phase_b_matches_realization"] is True
    assert scene.planning_record.metadata["backend"] == "local_sparse"
    result = plot_framework_dynamics_3d(scene)
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert trace_ids
    assert all(result.figure.data[index].type == "mesh3d" for index in trace_ids)
    assert result.render_metadata["density_meshes"]["atomic-density-0"]


def test_scene_renderer_supports_sparse_voxel_cloud_and_trace_provenance() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(64, 64, 64),
        gaussian_bandwidth=0.20,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=options,
    )
    result = plot_framework_dynamics_3d(
        scene,
        density_options=AtomicDensity3DRenderOptions(
            render_options=DensityRenderOptions(
                render_mode="voxel_cloud",
                mass_fractions=(0.50, 0.95),
                cloud_max_points=173,
            )
        ),
    )
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert len(trace_ids) == 1
    provenance = result.density_trace_provenance[trace_ids[0]]
    assert provenance.field_key == "atomic-density-0"
    assert provenance.storage_backend == "local_sparse"
    assert provenance.image_shift == (0, 0, 0)
    assert provenance.selected_point_count <= 173
    assert result.render_metadata["density_node_clouds"]["atomic-density-0"][
        "resources"
    ]["selected_point_count"] == provenance.selected_point_count


def test_sparse_voxel_cloud_match_graph_replication_uses_primary_shifts() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(48, 48, 48),
        gaussian_bandwidth=0.18,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=options,
    )
    result = plot_framework_dynamics_3d(
        scene,
        periodic=ExpandedCellDisplay(image_ranges=((0, 1), (0, 0), (0, 0))),
        density_options=AtomicDensity3DRenderOptions(
            render_options=DensityRenderOptions(
                render_mode="voxel_cloud",
                mass_fractions=(0.50, 0.95),
                display_replication="match_graph",
                cloud_max_points=97,
            )
        ),
    )
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert len(trace_ids) == 2
    shifts = tuple(result.density_trace_provenance[index].image_shift for index in trace_ids)
    assert shifts == ((0, 0, 0), (1, 0, 0))
    first = result.figure.data[trace_ids[0]]
    second = result.figure.data[trace_ids[1]]
    np.testing.assert_allclose(
        np.asarray(second.x, dtype=float) - np.asarray(first.x, dtype=float),
        scene.display_cell[0, 0],
        rtol=0.0,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        np.asarray(second.y, dtype=float) - np.asarray(first.y, dtype=float),
        scene.display_cell[0, 1],
        rtol=0.0,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        np.asarray(second.z, dtype=float) - np.asarray(first.z, dtype=float),
        scene.display_cell[0, 2],
        rtol=0.0,
        atol=1.0e-12,
    )


def test_framework_local_sparse_is_available_after_ld3() -> None:
    options = FrameworkDensityOptions(
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(grid_backend="local_sparse"),
    )
    assert options.storage_options.grid_backend == "local_sparse"


def test_localized_lta_primitive_storage_gate_with_nonzero_canonical_kernel() -> None:
    """The normative LTA benchmark retains fine resolution with <10% slots."""

    from dataclasses import replace

    collection = make_collection()
    cell = np.asarray(
        [
            [17.3630, 0.0, 0.0],
            [8.6815, 15.0368, 0.0],
            [8.6815, 5.0123, 14.1768],
        ],
        dtype=np.float64,
    )
    collection = replace(
        collection,
        cells=np.repeat(cell[None, :, :], collection.n_frames, axis=0),
    )
    options = AtomicDensityOptions(
        grid_shape=(128, 128, 128),
        gaussian_bandwidth=0.25,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    field = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=cell,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,)),),
        options=options,
        max_fields=1,
        max_total_voxels=64,
        max_samples=100,
        max_stored_block_values=2_000_000,
    )[0]
    summary = field.storage_summary()
    dense_slots = int(np.prod(field.grid_shape, dtype=np.int64))
    assert summary.stored_value_count / dense_slots <= 0.10
    assert dense_slots / summary.stored_value_count >= 10.0
    assert field.gaussian_bandwidth == pytest.approx(0.25)
    assert field.integral == pytest.approx(1.0, abs=5.0e-13)


def test_sparse_mesh_match_graph_replication_uses_primary_shifts() -> None:
    collection = make_collection()
    options = AtomicDensityOptions(
        grid_shape=(32, 32, 32),
        gaussian_bandwidth=0.24,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=options,
    )
    result = plot_framework_dynamics_3d(
        scene,
        periodic=ExpandedCellDisplay(image_ranges=((0, 1), (0, 0), (0, 0))),
        density_options=AtomicDensity3DRenderOptions(
            render_options=DensityRenderOptions(
                render_mode="mesh",
                mass_fractions=(0.80, 0.90),
                display_replication="match_graph",
                max_mesh_faces=100_000,
            )
        ),
    )
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert len(trace_ids) == 4
    shifts = tuple(result.density_trace_provenance[index].image_shift for index in trace_ids)
    assert shifts == ((0, 0, 0), (1, 0, 0), (0, 0, 0), (1, 0, 0))
    first = result.figure.data[trace_ids[0]]
    second = result.figure.data[trace_ids[1]]
    np.testing.assert_allclose(
        np.asarray(second.x, dtype=float) - np.asarray(first.x, dtype=float),
        scene.display_cell[0, 0],
        rtol=0.0,
        atol=1.0e-6,
    )
    np.testing.assert_allclose(
        np.asarray(second.y, dtype=float) - np.asarray(first.y, dtype=float),
        scene.display_cell[0, 1],
        rtol=0.0,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        np.asarray(second.z, dtype=float) - np.asarray(first.z, dtype=float),
        scene.display_cell[0, 2],
        rtol=0.0,
        atol=1.0e-12,
    )
