"""Plot-D4 framework vertex-occupancy and edge-length density tests."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    AUTO_BACKEND,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    DensityKernelOptions,
    DensityStorageOptions,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDensity3DRenderOptions,
    FrameworkDensityOptions,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    build_framework_topology,
    compute_atomic_connectivity,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
)
from mdstats.plotting import GraphAdapterError, GraphComplexityError
from mdstats.plotting.density_sparse_mesh import prepare_sparse_density_mesh
from mdstats.plotting.framework_density import prepare_framework_density_fields


def make_collection(
    fractional: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    frac = np.asarray(fractional, dtype=float)
    n_frames, n_atoms, _ = frac.shape
    if cells is None:
        cells = np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0)
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11][:n_atoms], dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool) if pbc is None else np.asarray(pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        times=np.arange(n_frames, dtype=float)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        cells=np.asarray(cells, dtype=float),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, n_atoms, 3))
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic-framework-density",
            source_files=("synthetic",),
            velocity_source="synthetic"
            if semantics is FrameSemantics.TRAJECTORY
            else "unavailable",
            coordinate_normalization="time_unwrapped_fractional"
            if semantics is FrameSemantics.TRAJECTORY
            else "independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),
        ),
    )


def topology_for(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.0, ("Al", "O"): 2.0})
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, mapping())


def bent_fractional(n_frames: int = 3) -> np.ndarray:
    one = np.asarray(
        [
            [0.10, 0.10, 0.10],
            [0.20, 0.20, 0.10],
            [0.30, 0.10, 0.10],
            [0.70, 0.50, 0.50],
        ]
    )
    return np.repeat(one[None, :, :], n_frames, axis=0)


def scene(
    collection: AtomisticFrameCollection,
    *,
    options: FrameworkDensityOptions | None = None,
    dynamics: FrameworkDynamicsOptions | None = None,
    resources: FrameworkDynamicsResources | None = None,
):
    resolved = options or FrameworkDensityOptions(
        grid_shape=(16, 16, 16),
        gaussian_bandwidth=0.25,
        edge_sample_spacing=0.15,
    )
    # This module tests the dense scientific oracle unless sparse storage is
    # explicitly requested. Default automatic selection is tested separately.
    if resolved.storage_options.grid_backend == AUTO_BACKEND:
        resolved = replace(
            resolved,
            storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
        )
    return prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        framework_density_options=resolved,
        options=dynamics,
        resources=(
            resources
            if resources is not None
            else FrameworkDynamicsResources(max_density_voxels=2_000_000)
        ),
    )


def sparse_framework_options(
    *, edge_source: str = "projected", block_shape: tuple[int, int, int] = (8, 8, 8)
) -> FrameworkDensityOptions:
    return FrameworkDensityOptions(
        grid_shape=(24, 24, 24),
        gaussian_bandwidth=0.40,
        edge_source=edge_source,
        edge_sample_spacing=0.15,
        edge_sample_spacing_mode="explicit",
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=block_shape
        ),
    )


def test_vertex_density_integrates_to_framework_vertex_count() -> None:
    prepared = scene(make_collection(bent_fractional()))
    fields = prepared.framework_density_fields
    assert fields is not None and fields.vertex_density is not None
    assert fields.vertex_density.total_measure == 2.0
    assert fields.vertex_density.integral == pytest.approx(2.0, abs=2.0e-12)
    assert fields.vertex_density.metadata["physical_units"] == "angstrom^-3"


def test_projected_edge_density_integrates_to_mean_total_length() -> None:
    prepared = scene(make_collection(bent_fractional()))
    fields = prepared.framework_density_fields
    assert fields is not None and fields.edge_length_density is not None
    edge = fields.edge_length_density
    assert edge.total_measure == pytest.approx(2.0, abs=1.0e-12)
    assert edge.integral == pytest.approx(2.0, abs=2.0e-12)
    assert edge.metadata["physical_units"] == "angstrom^-2"


def test_canonical_framework_channels_preserve_both_measures() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.35,
            edge_sample_spacing=0.15,
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
            ),
        ),
    )
    fields = prepared.framework_density_fields
    assert fields is not None
    assert fields.vertex_density is not None
    assert fields.edge_length_density is not None
    assert fields.vertex_density.integral == pytest.approx(2.0, abs=5.0e-13)
    assert fields.edge_length_density.integral == pytest.approx(2.0, abs=5.0e-13)
    for field in fields.fields:
        assert field.smoothing_operator == DISCRETE_PERIODIZED_OPERATOR
        assert field.metadata["canonical_convolution_method"] == "fft"
        assert field.metadata["stencil_offset_count"] > 1
        assert (
            field.metadata["density_planning"]["phase_b"]["stencil_value_count"]
            == field.values.size
        )


def test_atomic_path_edge_source_preserves_bent_path_arc_length() -> None:
    collection = make_collection(bent_fractional())
    projected = scene(collection).framework_density_fields
    atomic = scene(
        collection,
        options=FrameworkDensityOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.20,
            edge_source="atomic_paths",
            edge_sample_spacing=0.12,
        ),
    ).framework_density_fields
    assert projected is not None and atomic is not None
    assert (
        projected.edge_length_density is not None
        and atomic.edge_length_density is not None
    )
    assert projected.edge_length_density.total_measure == pytest.approx(2.0)
    assert atomic.edge_length_density.total_measure == pytest.approx(2.0 * np.sqrt(2.0))
    assert atomic.edge_length_density.metadata["edge_source"] == "atomic_paths"


def test_integer_framework_wrapping_is_invariant() -> None:
    left = bent_fractional()
    right = np.array(left, copy=True)
    right[:, :3, :] += np.asarray([2.0, -1.0, 3.0])
    a = scene(make_collection(left)).framework_density_fields
    b = scene(make_collection(right)).framework_density_fields
    assert a is not None and b is not None
    np.testing.assert_allclose(
        a.vertex_density.values, b.vertex_density.values, atol=2.0e-12, rtol=0.0
    )
    np.testing.assert_allclose(
        a.edge_length_density.values,
        b.edge_length_density.values,
        atol=2.0e-12,
        rtol=0.0,
    )


def test_independent_ensemble_framework_density_is_supported() -> None:
    frac = bent_fractional(3)
    frac[:, 1, 1] = [0.18, 0.20, 0.22]
    prepared = scene(make_collection(frac, semantics=FrameSemantics.ENSEMBLE))
    assert prepared.trajectory_paths is None
    assert prepared.framework_density_fields.vertex_density.integral == pytest.approx(
        2.0
    )


def test_framework_registration_removes_rigid_density_drift() -> None:
    static = bent_fractional(3)
    shifted = np.array(static, copy=True)
    shifted[:, :, 0] += np.asarray([0.0, 0.12, 0.24])[:, None]
    dynamics = FrameworkDynamicsOptions(
        registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED
    )
    reference = scene(
        make_collection(static), dynamics=dynamics
    ).framework_density_fields
    registered = scene(
        make_collection(shifted), dynamics=dynamics
    ).framework_density_fields
    np.testing.assert_allclose(
        reference.vertex_density.values,
        registered.vertex_density.values,
        atol=2.0e-12,
        rtol=0.0,
    )
    np.testing.assert_allclose(
        reference.edge_length_density.values,
        registered.edge_length_density.values,
        atol=2.0e-12,
        rtol=0.0,
    )


def test_variable_cell_laboratory_framework_density_is_rejected() -> None:
    frac = bent_fractional(2)
    cells = np.asarray([np.eye(3) * 10.0, np.eye(3) * 14.0])
    collection = make_collection(frac, cells=cells)
    material = scene(collection).framework_density_fields.edge_length_density
    assert material.total_measure == pytest.approx(2.0)
    with pytest.raises(GraphAdapterError, match="laboratory-frame density"):
        scene(
            collection,
            dynamics=FrameworkDynamicsOptions(
                registration_mode=SpatialRegistrationMode.LABORATORY
            ),
        )


def test_channels_can_be_requested_independently() -> None:
    vertex_only = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(8, 8, 8), include_edge_density=False
        ),
    ).framework_density_fields
    edge_only = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(8, 8, 8), include_vertex_density=False
        ),
    ).framework_density_fields
    assert (
        vertex_only.vertex_density is not None
        and vertex_only.edge_length_density is None
    )
    assert (
        edge_only.vertex_density is None and edge_only.edge_length_density is not None
    )


def test_framework_density_resource_preflight() -> None:
    with pytest.raises(GraphComplexityError, match="remaining max_density_fields"):
        scene(
            make_collection(bent_fractional()),
            resources=FrameworkDynamicsResources(max_density_fields=1),
        )
    with pytest.raises(GraphComplexityError, match="quadrature samples"):
        scene(
            make_collection(bent_fractional()),
            options=FrameworkDensityOptions(
                grid_shape=(8, 8, 8), edge_sample_spacing=0.01
            ),
            resources=FrameworkDynamicsResources(max_density_samples=10),
        )


def test_first_backend_rejects_mixed_periodicity() -> None:
    collection = make_collection(bent_fractional(), pbc=np.asarray([True, True, False]))
    with pytest.raises(GraphAdapterError, match="requires periodicity"):
        scene(collection)


def test_framework_density_renders_as_separate_channels(tmp_path) -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(10, 10, 10),
            gaussian_bandwidth=0.30,
            edge_sample_spacing=0.20,
            store_sample_positions=True,
        ),
    )
    result = plot_framework_dynamics_3d(
        prepared,
        framework_density_options=FrameworkDensity3DRenderOptions(show_samples=True),
    )
    assert set(result.framework_density_trace_indices) == {
        "framework-vertex-density",
        "framework-edge-length-density",
    }
    assert result.render_metadata["framework_density_field_count"] == 2
    target = tmp_path / "framework-density.html"
    result.write_html(target)
    assert target.stat().st_size > 10_000


def test_framework_density_mesh_channels_have_nonempty_geometry() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(14, 14, 14),
            gaussian_bandwidth=0.30,
            edge_sample_spacing=0.20,
        ),
    )
    result = plot_framework_dynamics_3d(
        prepared,
        framework_density_options=FrameworkDensity3DRenderOptions(
            mass_fractions=(0.55, 0.88), render_mode="mesh"
        ),
    )
    for field_key, trace_ids in result.framework_density_trace_indices.items():
        assert len(trace_ids) == 2, field_key
        for trace_id in trace_ids:
            trace = result.figure.data[trace_id]
            assert trace.type == "mesh3d"
            assert len(trace.x) > 0
            assert len(trace.i) > 0
            assert trace.opacity > 0.0


def test_framework_default_grid_uses_constant_interval() -> None:
    collection = make_collection(
        bent_fractional(), cells=np.repeat((np.eye(3) * 10.0)[None, :, :], 3, axis=0)
    )
    prepared = scene(
        collection,
        options=FrameworkDensityOptions(
            grid_interval=0.25,
            gaussian_bandwidth=0.35,
            edge_sample_spacing=0.20,
        ),
    )
    fields = prepared.framework_density_fields
    assert fields is not None
    assert fields.vertex_density is not None
    assert fields.edge_length_density is not None
    assert fields.vertex_density.grid_shape == (40, 40, 40)
    assert fields.edge_length_density.grid_shape == (40, 40, 40)
    assert (
        fields.vertex_density.metadata["grid_definition"] == "target_lattice_interval"
    )
    assert fields.vertex_density.metadata["grid_interval_target"] == pytest.approx(0.25)


def test_framework_explicit_grid_shape_overrides_interval() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(11, 13, 15),
            grid_interval=0.01,
            gaussian_bandwidth=0.35,
            edge_sample_spacing=0.20,
        ),
    )
    fields = prepared.framework_density_fields
    assert fields is not None and fields.vertex_density is not None
    assert fields.vertex_density.grid_shape == (11, 13, 15)
    assert fields.vertex_density.metadata["grid_definition"] == "explicit_shape"


def test_framework_default_bandwidth_tracks_grid_interval_ratio() -> None:
    collection = make_collection(
        bent_fractional(),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], 3, axis=0),
    )
    prepared = scene(
        collection,
        options=FrameworkDensityOptions(
            grid_interval=0.25,
            adaptive_smearing=False,
            edge_sample_spacing=0.20,
        ),
    )
    fields = prepared.framework_density_fields
    assert fields is not None and fields.vertex_density is not None
    field = fields.vertex_density
    assert field.gaussian_bandwidth == pytest.approx(0.50)
    assert field.metadata["gaussian_to_grid_ratio_target"] == pytest.approx(2.0)
    assert field.metadata[
        "gaussian_to_longest_grid_interval_realized"
    ] == pytest.approx(2.0)
    assert field.metadata["smearing_definition"] == "grid_ratio"


def test_sparse_framework_channels_match_dense_canonical_fields() -> None:
    collection = make_collection(bent_fractional())
    dense_options = FrameworkDensityOptions(
        grid_shape=(24, 24, 24),
        gaussian_bandwidth=0.40,
        edge_sample_spacing=0.15,
        edge_sample_spacing_mode="explicit",
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(grid_backend="dense"),
    )
    dense = scene(collection, options=dense_options).framework_density_fields
    sparse = scene(
        collection, options=sparse_framework_options()
    ).framework_density_fields
    assert dense is not None and sparse is not None
    for dense_field, sparse_field in zip(dense.fields, sparse.fields, strict=True):
        assert sparse_field.storage_backend == "local_sparse"
        np.testing.assert_allclose(
            sparse_field.to_dense_values(max_nodes=24**3),
            dense_field.values,
            rtol=5.0e-13,
            atol=5.0e-13 * max(1.0, float(np.max(dense_field.values))),
        )
        assert sparse_field.integral == pytest.approx(
            dense_field.integral, rel=0.0, abs=5.0e-13
        )
        for fraction in (0.50, 0.80, 0.95):
            assert sparse_field.threshold_for_mass_fraction(fraction) == pytest.approx(
                dense_field.threshold_for_mass_fraction(fraction),
                rel=0.0,
                abs=5.0e-12 * max(1.0, float(np.max(dense_field.values))),
            )


def test_sparse_framework_provenance_and_units_are_dimensionally_distinct() -> None:
    prepared = scene(
        make_collection(bent_fractional()), options=sparse_framework_options()
    )
    fields = prepared.framework_density_fields
    assert fields is not None
    vertex = fields.vertex_density
    edge = fields.edge_length_density
    assert vertex is not None and edge is not None
    assert vertex.physical_units == "angstrom^-3"
    assert edge.physical_units == "angstrom^-2"
    assert vertex.source_provenance.vertex_keys
    assert not vertex.source_provenance.edge_keys
    assert edge.source_provenance.edge_keys
    assert edge.source_provenance.metadata["resolution_reference_source"] == (
        "framework_vertices"
    )
    assert edge.metadata["quadrature_weight_sum"] == pytest.approx(
        edge.total_measure, rel=0.0, abs=5.0e-13
    )


def test_framework_edge_orientation_reversal_leaves_sparse_field_unchanged() -> None:
    vertices = np.asarray([[[0.15, 0.20, 0.30], [0.85, 0.20, 0.30]]])
    segments = np.asarray([[[[0.85, 0.20, 0.30], [1.15, 0.20, 0.30]]]])
    weights = np.asarray([1.0])
    options = FrameworkDensityOptions(
        grid_shape=(32, 32, 32),
        gaussian_bandwidth=0.30,
        include_vertex_density=False,
        edge_sample_spacing=0.05,
        edge_sample_spacing_mode="explicit",
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="local_sparse", local_block_shape=(8, 8, 8)
        ),
    )
    kwargs = dict(
        vertex_fractional_by_frame=vertices,
        vertex_atom_indices=(0, 1),
        edge_atom_indices=(0, 1),
        frame_weights=weights,
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        options=options,
        max_fields=2,
        max_total_voxels=10_000_000,
        max_samples=100_000,
    )
    forward = prepare_framework_density_fields(
        edge_segments_fractional_by_frame=segments, **kwargs
    ).edge_length_density
    reverse = prepare_framework_density_fields(
        edge_segments_fractional_by_frame=segments[:, :, ::-1, :], **kwargs
    ).edge_length_density
    assert forward is not None and reverse is not None
    np.testing.assert_array_equal(
        forward.to_dense_values(max_nodes=32**3),
        reverse.to_dense_values(max_nodes=32**3),
    )
    assert forward.total_measure == reverse.total_measure


def test_auto_edge_quadrature_tracks_grid_and_kernel_resolution() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(64, 64, 64),
            gaussian_bandwidth=0.10,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="auto",
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
            ),
            storage_options=DensityStorageOptions(
                grid_backend="local_sparse", local_block_shape=(8, 8, 8)
            ),
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=1_000_000,
            max_density_stored_block_values=2_000_000,
            max_density_nonzero_nodes=1_000_000,
            max_density_kernel_pairs=10_000_000,
            max_density_total_peak_bytes=512_000_000,
        ),
    )
    edge = prepared.framework_density_fields.edge_length_density
    assert edge is not None
    assert edge.metadata["edge_sample_spacing_mode"] == "auto"
    assert edge.metadata["edge_sample_spacing_realized"] == pytest.approx(0.0125)
    assert edge.metadata["edge_sample_spacing_underresolved"] is False


def test_sparse_atomic_path_edge_channel_is_supported() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=sparse_framework_options(edge_source="atomic_paths"),
    )
    fields = prepared.framework_density_fields
    assert fields is not None and fields.edge_length_density is not None
    edge = fields.edge_length_density
    assert edge.storage_backend == "local_sparse"
    assert edge.metadata["edge_source"] == "atomic_paths"
    assert edge.source_provenance.edge_keys
    assert edge.integral == pytest.approx(edge.total_measure, abs=5.0e-13)


def test_sparse_framework_meshes_have_periodic_seam_consistency() -> None:
    prepared = scene(
        make_collection(bent_fractional()), options=sparse_framework_options()
    )
    fields = prepared.framework_density_fields
    assert fields is not None
    for field in fields.fields:
        surface = prepare_sparse_density_mesh(
            field,
            0.80,
            max_faces=200_000,
            max_candidate_cells=200_000,
            max_raw_faces=500_000,
            max_raw_vertices=1_500_000,
            max_workspace_bytes=512_000_000,
            max_dense_fallback_nodes=1_000_000,
            allow_cloud_fallback=False,
        )
        assert surface.render_kind == "mesh"
        assert surface.mesh is not None
        topology = surface.mesh.topology
        assert topology.interior_edge_incidence_failures == 0
        assert topology.unpaired_boundary_edge_count == 0
        assert topology.maximum_boundary_seam_mismatch <= 1.0e-10 * 10.0


def test_sparse_framework_channels_render_without_renderer_special_cases() -> None:
    prepared = scene(
        make_collection(bent_fractional()), options=sparse_framework_options()
    )
    mesh_result = plot_framework_dynamics_3d(
        prepared,
        framework_density_options=FrameworkDensity3DRenderOptions(
            mass_fractions=(0.65, 0.85), render_mode="mesh"
        ),
    )
    assert set(mesh_result.framework_density_trace_indices) == {
        "framework-vertex-density",
        "framework-edge-length-density",
    }
    for trace_ids in mesh_result.framework_density_trace_indices.values():
        assert len(trace_ids) == 2
        assert all(
            mesh_result.figure.data[index].type == "mesh3d" for index in trace_ids
        )

    cloud_result = plot_framework_dynamics_3d(
        prepared,
        framework_density_options=FrameworkDensity3DRenderOptions(
            mass_fractions=(0.60, 0.80),
            render_mode="voxel_cloud",
            cloud_max_points=2000,
        ),
    )
    for trace_ids in cloud_result.framework_density_trace_indices.values():
        assert len(trace_ids) == 1
        assert cloud_result.figure.data[trace_ids[0]].type == "scatter3d"


def test_auto_edge_quadrature_meets_ld3_convergence_gate() -> None:
    collection = make_collection(bent_fractional())
    base = dict(
        grid_shape=(32, 32, 32),
        gaussian_bandwidth=0.30,
        include_vertex_density=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(grid_backend="dense"),
    )
    automatic = scene(
        collection,
        options=FrameworkDensityOptions(
            **base,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="auto",
            edge_quadrature_refinement_levels=2,
        ),
    ).framework_density_fields.edge_length_density
    assert automatic is not None
    realized = float(automatic.metadata["edge_sample_spacing_realized"])
    finer = scene(
        collection,
        options=FrameworkDensityOptions(
            **base,
            edge_sample_spacing=0.5 * realized,
            edge_sample_spacing_mode="explicit",
        ),
    ).framework_density_fields.edge_length_density
    assert finer is not None
    l1 = float(np.sum(np.abs(automatic.values - finer.values))) / float(
        np.sum(np.abs(finer.values))
    )
    linf = float(np.max(np.abs(automatic.values - finer.values))) / float(
        np.max(finer.values)
    )
    hdr = max(
        abs(
            automatic.threshold_for_mass_fraction(q)
            - finer.threshold_for_mass_fraction(q)
        )
        / max(1.0e-30, finer.threshold_for_mass_fraction(q))
        for q in (0.50, 0.80, 0.95)
    )
    assert l1 <= 2.0e-3
    assert linf <= 1.0e-2
    assert hdr <= 1.0e-3


def test_edge_quadrature_refinement_levels_zero_uses_base_policy() -> None:
    prepared = scene(
        make_collection(bent_fractional()),
        options=FrameworkDensityOptions(
            grid_shape=(64, 64, 64),
            gaussian_bandwidth=0.10,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="auto",
            edge_quadrature_refinement_levels=0,
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
            ),
        ),
    )
    edge = prepared.framework_density_fields.edge_length_density
    assert edge is not None
    assert edge.metadata["edge_sampling_policy_spacing"] == pytest.approx(0.05)
    assert edge.metadata["edge_sample_spacing_realized"] == pytest.approx(0.05)
    assert edge.metadata["edge_quadrature_refinement_levels"] == 0


def test_explicit_edge_quadrature_warns_but_preserves_underresolved_spacing() -> None:
    with pytest.warns(RuntimeWarning, match="edge_sample_spacing is coarser"):
        prepared = scene(
            make_collection(bent_fractional()),
            options=FrameworkDensityOptions(
                grid_shape=(64, 64, 64),
                gaussian_bandwidth=0.10,
                edge_sample_spacing=0.20,
                edge_sample_spacing_mode="explicit",
                kernel_options=DensityKernelOptions(
                    smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
                ),
            ),
        )
    edge = prepared.framework_density_fields.edge_length_density
    assert edge is not None
    assert edge.metadata["edge_sample_spacing_realized"] == pytest.approx(0.20)
    assert edge.metadata["edge_sample_spacing_underresolved"] is True


def test_auto_edge_quadrature_converges_for_skew_periodic_atomic_paths() -> None:
    cell = np.asarray(
        [[10.0, 0.0, 0.0], [5.0, 8.660254037844386, 0.0], [2.0, 1.0, 9.0]]
    )
    vertices = np.asarray([[[0.10, 0.10, 0.10], [0.30, 0.20, 0.10]]])
    segments = np.asarray(
        [
            [
                [[0.95, 0.15, 0.12], [1.22, 0.31, 0.18]],
                [[0.30, 0.20, 0.10], [0.60, 0.45, 0.20]],
            ]
        ]
    )
    common = dict(
        vertex_fractional_by_frame=vertices,
        vertex_atom_indices=(0, 1),
        edge_segments_fractional_by_frame=segments,
        edge_atom_indices=(0, 1),
        frame_weights=np.asarray([1.0]),
        display_cell=cell,
        registration_mode="material",
        max_fields=1,
        max_total_voxels=1_000_000,
        max_samples=1_000_000,
    )
    options = dict(
        grid_shape=(32, 32, 32),
        gaussian_bandwidth=0.30,
        include_vertex_density=False,
        edge_source="atomic_paths",
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(grid_backend="dense"),
    )
    automatic = prepare_framework_density_fields(
        **common,
        options=FrameworkDensityOptions(
            **options,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="auto",
            edge_quadrature_refinement_levels=2,
        ),
    ).edge_length_density
    assert automatic is not None
    realized = float(automatic.metadata["edge_sample_spacing_realized"])
    finer = prepare_framework_density_fields(
        **common,
        options=FrameworkDensityOptions(
            **options,
            edge_sample_spacing=0.5 * realized,
            edge_sample_spacing_mode="explicit",
        ),
    ).edge_length_density
    assert finer is not None
    l1 = float(np.sum(np.abs(automatic.values - finer.values))) / float(
        np.sum(np.abs(finer.values))
    )
    linf = float(np.max(np.abs(automatic.values - finer.values))) / float(
        np.max(finer.values)
    )
    hdr = max(
        abs(
            automatic.threshold_for_mass_fraction(q)
            - finer.threshold_for_mass_fraction(q)
        )
        / max(1.0e-30, finer.threshold_for_mass_fraction(q))
        for q in (0.50, 0.80, 0.95)
    )
    assert l1 <= 2.0e-3
    assert linf <= 1.0e-2
    assert hdr <= 1.0e-3


def test_sparse_framework_realization_matches_approved_phase_b_counts() -> None:
    prepared = scene(
        make_collection(bent_fractional()), options=sparse_framework_options()
    )
    fields = prepared.framework_density_fields
    assert fields is not None
    for field in fields.fields:
        summary = field.storage_summary()
        phase_b = field.metadata["density_planning"]["phase_b"]
        assert summary.nonzero_node_count == phase_b["nonzero_node_count_upper"]
        assert summary.stored_block_count == phase_b["stored_block_count"]
        assert summary.stored_value_count == phase_b["stored_value_count"]
        assert summary.realized_bytes == phase_b["retained_bytes"]


def test_sparse_framework_storage_limit_fails_before_realization() -> None:
    with pytest.raises(GraphComplexityError, match="max_density_stored_block_values"):
        scene(
            make_collection(bent_fractional()),
            options=sparse_framework_options(),
            resources=FrameworkDynamicsResources(max_density_stored_block_values=1),
        )
