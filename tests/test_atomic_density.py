"""Plot-D3 periodic atomic-density field and rendering tests."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    AUTO_BACKEND,
    DENSE_BACKEND,
    LOCAL_SPARSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    DensityKernelOptions,
    DensityStorageOptions,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    build_framework_topology,
    compute_atomic_connectivity,
    density_grid_intervals,
    resolve_density_grid_shape,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
)
from mdstats.plotting import GraphAdapterError, GraphComplexityError


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
    if pbc is None:
        pbc = np.ones(3, dtype=bool)
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11][:n_atoms], dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.asarray(pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64) if semantics is FrameSemantics.TRAJECTORY else None,
        times=np.arange(n_frames, dtype=float) if semantics is FrameSemantics.TRAJECTORY else None,
        cells=np.asarray(cells, dtype=float),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, n_atoms, 3)) if semantics is FrameSemantics.TRAJECTORY else None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic-density",
            source_files=("synthetic",),
            velocity_source="synthetic" if semantics is FrameSemantics.TRAJECTORY else "unavailable",
            coordinate_normalization="time_unwrapped_fractional" if semantics is FrameSemantics.TRAJECTORY else "independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def base_fractional(n_frames: int = 4) -> np.ndarray:
    one = np.asarray(
        [
            [0.10, 0.10, 0.10],
            [0.20, 0.10, 0.10],
            [0.30, 0.10, 0.10],
            [0.70, 0.50, 0.50],
        ]
    )
    return np.repeat(one[None, :, :], n_frames, axis=0)


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
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.1, ("Al", "O"): 2.1})
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, mapping())


def density_scene(
    collection: AtomisticFrameCollection,
    selection: AtomicDensitySelection,
    *,
    density_options: AtomicDensityOptions | None = None,
    scene_options: FrameworkDynamicsOptions | None = None,
    resources: FrameworkDynamicsResources | None = None,
):
    resolved = density_options or AtomicDensityOptions(
        grid_shape=(16, 16, 16), gaussian_bandwidth=0.25
    )
    # This module tests the dense scientific oracle. Default automatic backend
    # behavior is covered by test_density_backend_selection.py.
    if resolved.storage_options.grid_backend == AUTO_BACKEND:
        resolved = replace(
            resolved,
            storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
        )
    return prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        atomic_density_selections=(selection,),
        atomic_density_options=resolved,
        options=scene_options,
        resources=(
            resources
            if resources is not None
            else FrameworkDynamicsResources(max_density_voxels=2_000_000)
        ),
    )


def test_single_atom_density_integrates_to_one() -> None:
    scene = density_scene(
        make_collection(base_fractional()),
        AtomicDensitySelection(atom_indices=(3,)),
    )
    field = scene.atomic_density_fields[0]
    assert field.total_measure == 1.0
    assert field.integral == pytest.approx(1.0, abs=2.0e-12)
    assert field.selected_atom_indices == (3,)
    assert field.metadata["physical_units"] == "angstrom^-3"


def test_species_density_integrates_to_selected_atom_count() -> None:
    collection = make_collection(base_fractional())
    scene = density_scene(collection, AtomicDensitySelection(species=("Si", "Al"), label="T density"))
    field = scene.atomic_density_fields[0]
    assert field.total_measure == 2.0
    assert field.integral == pytest.approx(2.0, abs=2.0e-12)
    assert field.label == "T density"


def test_integer_wrapping_is_density_invariant() -> None:
    left = base_fractional()
    right = np.array(left, copy=True)
    right[:, 3, :] += np.asarray([2.0, -1.0, 3.0])
    field_left = density_scene(make_collection(left), AtomicDensitySelection(atom_indices=(3,))).atomic_density_fields[0]
    field_right = density_scene(make_collection(right), AtomicDensitySelection(atom_indices=(3,))).atomic_density_fields[0]
    np.testing.assert_allclose(field_left.values, field_right.values, rtol=0.0, atol=2.0e-13)


def test_gaussian_smoothing_preserves_mass_and_reduces_peak() -> None:
    collection = make_collection(base_fractional(1))
    raw = density_scene(
        collection,
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(grid_shape=(16, 16, 16), gaussian_bandwidth=0.0),
    ).atomic_density_fields[0]
    smooth = density_scene(
        collection,
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(grid_shape=(16, 16, 16), gaussian_bandwidth=0.5),
    ).atomic_density_fields[0]
    assert raw.integral == pytest.approx(1.0)
    assert smooth.integral == pytest.approx(1.0)
    assert float(np.max(smooth.values)) < float(np.max(raw.values))
    assert np.count_nonzero(smooth.values) > np.count_nonzero(raw.values)




def test_canonical_discrete_operator_integrates_and_records_diagnostics() -> None:
    field = density_scene(
        make_collection(base_fractional()),
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.5,
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR,
                kernel_tail_tolerance=1.0e-8,
            ),
        ),
    ).atomic_density_fields[0]
    assert field.integral == pytest.approx(1.0, abs=5.0e-13)
    assert field.smoothing_operator == DISCRETE_PERIODIZED_OPERATOR
    assert field.metadata["canonical_convolution_method"] == "fft"
    assert field.metadata["stencil_offset_count"] > 1
    assert field.metadata["periodic_image_contribution_count"] >= field.metadata[
        "stencil_offset_count"
    ]
    planning = field.metadata["density_planning"]
    assert planning["phase_b"]["stencil_value_count"] == field.values.size


def test_canonical_operator_is_integer_translation_invariant() -> None:
    left = base_fractional()
    right = np.array(left, copy=True)
    right[:, 3, :] += np.asarray([1.0, -2.0, 3.0])
    options = AtomicDensityOptions(
        grid_shape=(16, 16, 16),
        gaussian_bandwidth=0.5,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    a = density_scene(
        make_collection(left),
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=options,
    ).atomic_density_fields[0]
    b = density_scene(
        make_collection(right),
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=options,
    ).atomic_density_fields[0]
    np.testing.assert_allclose(a.values, b.values, rtol=0.0, atol=5.0e-13)

def test_independent_ensemble_density_is_supported() -> None:
    frac = base_fractional(3)
    frac[:, 3, 0] = [0.68, 0.70, 0.72]
    collection = make_collection(frac, semantics=FrameSemantics.ENSEMBLE)
    scene = density_scene(collection, AtomicDensitySelection(species=("Na",)))
    assert scene.trajectory_paths is None
    assert len(scene.atomic_density_fields) == 1
    assert scene.atomic_density_fields[0].integral == pytest.approx(1.0)


def test_framework_registration_removes_rigid_density_drift() -> None:
    static = base_fractional(4)
    drifting = np.array(static, copy=True)
    drifting[:, :, 0] += np.asarray([0.0, 0.12, 0.24, 0.36])[:, None]
    reference = density_scene(
        make_collection(static),
        AtomicDensitySelection(atom_indices=(3,)),
        scene_options=FrameworkDynamicsOptions(registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED),
    ).atomic_density_fields[0]
    registered = density_scene(
        make_collection(drifting),
        AtomicDensitySelection(atom_indices=(3,)),
        scene_options=FrameworkDynamicsOptions(registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED),
    ).atomic_density_fields[0]
    np.testing.assert_allclose(reference.values, registered.values, atol=2.0e-12, rtol=0.0)


def test_variable_cell_laboratory_density_is_rejected() -> None:
    frac = base_fractional(2)
    cells = np.asarray([np.eye(3) * 10.0, np.eye(3) * 14.0])
    collection = make_collection(frac, cells=cells)
    material = density_scene(collection, AtomicDensitySelection(atom_indices=(3,))).atomic_density_fields[0]
    assert material.integral == pytest.approx(1.0)
    with pytest.raises(GraphAdapterError, match="laboratory-frame density"):
        density_scene(
            collection,
            AtomicDensitySelection(atom_indices=(3,)),
            scene_options=FrameworkDynamicsOptions(
                registration_mode=SpatialRegistrationMode.LABORATORY
            ),
        )


def test_highest_density_thresholds_are_monotone() -> None:
    field = density_scene(make_collection(base_fractional()), AtomicDensitySelection(atom_indices=(3,))).atomic_density_fields[0]
    thresholds = [field.threshold_for_mass_fraction(q) for q in (0.50, 0.80, 0.95)]
    assert thresholds[0] >= thresholds[1] >= thresholds[2] >= 0.0


def test_density_resource_preflight() -> None:
    collection = make_collection(base_fractional())
    with pytest.raises(GraphComplexityError, match="max_density_fields"):
        prepare_framework_dynamics_scene(
            collection,
            topology_for(collection),
            atomic_density_selections=(
                AtomicDensitySelection(atom_indices=(0,)),
                AtomicDensitySelection(atom_indices=(3,)),
            ),
            atomic_density_options=AtomicDensityOptions(grid_shape=(8, 8, 8)),
            resources=FrameworkDynamicsResources(max_density_fields=1),
        )
    with pytest.raises(GraphComplexityError, match="max_density_voxels"):
        density_scene(
            collection,
            AtomicDensitySelection(atom_indices=(3,)),
            density_options=AtomicDensityOptions(grid_shape=(16, 16, 16)),
            resources=FrameworkDynamicsResources(max_density_voxels=1000),
        )


def test_first_backend_rejects_mixed_periodicity() -> None:
    collection = make_collection(base_fractional(), pbc=np.asarray([True, True, False]))
    with pytest.raises(GraphAdapterError, match="requires periodicity"):
        density_scene(collection, AtomicDensitySelection(atom_indices=(3,)))


def test_isosurface_and_sample_cloud_render_and_serialize(tmp_path) -> None:
    collection = make_collection(base_fractional())
    scene = density_scene(
        collection,
        AtomicDensitySelection(species=("Na",), label="Na cloud"),
        density_options=AtomicDensityOptions(
            grid_shape=(12, 12, 12),
            gaussian_bandwidth=0.35,
            store_sample_positions=True,
        ),
    )
    result = plot_framework_dynamics_3d(
        scene,
        density_options=AtomicDensity3DRenderOptions(show_samples=True),
    )
    density_ids = result.density_trace_indices["atomic-density-0"]
    assert len(density_ids) == len(AtomicDensity3DRenderOptions().mass_fractions) + 1
    assert density_ids == tuple(range(density_ids[0], density_ids[0] + len(density_ids)))
    assert result.render_metadata["atomic_density_field_count"] == 1
    target = tmp_path / "atomic-density.html"
    result.write_html(target)
    assert target.stat().st_size > 10_000


def test_density_render_resource_limit() -> None:
    scene = density_scene(
        make_collection(base_fractional()),
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.25,
            adaptive_smearing=False,
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=2_000_000,
            max_density_render_points=10,
        ),
    )
    with pytest.raises(GraphComplexityError, match="max_density_render_points"):
        plot_framework_dynamics_3d(
            scene,
            density_options=AtomicDensity3DRenderOptions(mass_fractions=(0.85, 0.95)),
        )


def test_density_mesh_renderer_emits_explicit_triangles() -> None:
    collection = make_collection(base_fractional())
    scene = density_scene(
        collection,
        AtomicDensitySelection(species=("Na",), label="Na cloud"),
        density_options=AtomicDensityOptions(
            grid_shape=(12, 12, 12), gaussian_bandwidth=0.35
        ),
    )
    result = plot_framework_dynamics_3d(
        scene,
        density_options=AtomicDensity3DRenderOptions(
            mass_fractions=(0.55, 0.88), render_mode="mesh"
        ),
    )
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert len(trace_ids) == 2
    for trace_id in trace_ids:
        trace = result.figure.data[trace_id]
        assert trace.type == "mesh3d"
        assert len(trace.x) > 0
        assert len(trace.i) > 0
        assert np.all(np.isfinite(np.asarray(trace.x, dtype=float)))
    assert not any(trace.type == "isosurface" for trace in result.figure.data)


def test_density_voxel_cloud_fallback_emits_visible_points() -> None:
    collection = make_collection(base_fractional())
    scene = density_scene(
        collection,
        AtomicDensitySelection(species=("Na",), label="Na cloud"),
        density_options=AtomicDensityOptions(
            grid_shape=(12, 12, 12), gaussian_bandwidth=0.35
        ),
    )
    result = plot_framework_dynamics_3d(
        scene,
        density_options=AtomicDensity3DRenderOptions(
            mass_fractions=(0.55, 0.88),
            render_mode="voxel_cloud",
            cloud_max_points=500,
        ),
    )
    trace_ids = result.density_trace_indices["atomic-density-0"]
    assert len(trace_ids) == 1
    trace = result.figure.data[trace_ids[0]]
    assert trace.type == "scatter3d"
    assert len(trace.x) > 0
    assert trace.marker.opacity > 0.0


def test_default_density_shell_preserves_metric_in_lta_primitive_cell() -> None:
    from mdstats.plotting.atomic_density import (
        PeriodicScalarField3D,
        _deposit_cic,
        _periodic_gaussian,
        density_mesh_arrays,
    )

    cell = np.asarray(
        [
            [17.3630, 0.0, 0.0],
            [8.6815, 15.0368, 0.0],
            [8.6815, 5.0123, 14.1768],
        ],
        dtype=float,
    )
    options = AtomicDensityOptions()
    shape = resolve_density_grid_shape(
        cell, grid_shape=options.grid_shape, grid_interval=options.grid_interval
    )
    center_fractional = np.asarray([[0.37, 0.41, 0.43]], dtype=float)
    bandwidth = options.gaussian_to_grid_ratio * max(
        density_grid_intervals(cell, shape)
    )
    mass = _deposit_cic(center_fractional, np.asarray([1.0]), shape)
    mass = _periodic_gaussian(mass, cell, bandwidth)
    voxel_volume = abs(float(np.linalg.det(cell))) / float(np.prod(shape))
    field = PeriodicScalarField3D(
        field_key="isotropic-probe",
        label="isotropic probe",
        values=mass / voxel_volume,
        display_cell=cell,
        total_measure=1.0,
        selected_atom_indices=(0,),
        gaussian_bandwidth=bandwidth,
    )
    vertices, _faces, _threshold = density_mesh_arrays(
        field, 0.50, max_faces=250_000
    )
    fractional = vertices @ np.linalg.inv(cell)
    displacement_fractional = fractional - center_fractional[0]
    displacement_fractional -= np.rint(displacement_fractional)
    radii = np.linalg.norm(displacement_fractional @ cell, axis=1)
    assert float(np.max(radii) / np.min(radii)) < 1.10


def test_underresolved_density_grid_warns() -> None:
    collection = make_collection(base_fractional())
    with pytest.warns(RuntimeWarning, match="under-resolved"):
        density_scene(
            collection,
            AtomicDensitySelection(atom_indices=(3,)),
            density_options=AtomicDensityOptions(
                grid_shape=(16, 16, 16), gaussian_bandwidth=0.10
            ),
        )


def test_default_grid_shape_is_derived_from_constant_interval() -> None:
    cell = np.asarray(
        [
            [17.3630, 0.0, 0.0],
            [8.6815, 15.0368, 0.0],
            [8.6815, 5.0123, 14.1768],
        ],
        dtype=float,
    )
    options = AtomicDensityOptions()
    assert options.grid_shape is None
    assert options.grid_interval == pytest.approx(0.20)
    assert options.gaussian_bandwidth is None
    assert options.gaussian_to_grid_ratio == pytest.approx(2.0)
    assert options.adaptive_smearing is True
    assert options.max_smearing_to_sample_sd_ratio == pytest.approx(0.50)
    shape = resolve_density_grid_shape(
        cell, grid_shape=options.grid_shape, grid_interval=options.grid_interval
    )
    assert shape == (87, 87, 87)
    intervals = density_grid_intervals(cell, shape)
    assert max(intervals) <= 0.20 + 1.0e-12
    assert min(intervals) > 0.19


def test_automatic_grid_uses_each_cell_vector_length() -> None:
    cell = np.asarray(
        [
            [10.0, 0.0, 0.0],
            [2.0, 12.0, 0.0],
            [1.0, 3.0, 8.0],
        ],
        dtype=float,
    )
    shape = resolve_density_grid_shape(
        cell, grid_shape=None, grid_interval=0.5
    )
    expected = tuple(int(np.ceil(length / 0.5 - 1.0e-12)) for length in np.linalg.norm(cell, axis=1))
    assert shape == expected
    assert max(density_grid_intervals(cell, shape)) <= 0.5 + 1.0e-12


def test_explicit_grid_shape_overrides_interval() -> None:
    cell = np.eye(3) * 10.0
    shape = resolve_density_grid_shape(
        cell, grid_shape=(17, 19, 23), grid_interval=0.01
    )
    assert shape == (17, 19, 23)


def test_automatic_grid_metadata_is_recorded() -> None:
    collection = make_collection(base_fractional())
    field = density_scene(
        collection,
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(
            grid_interval=0.25, adaptive_smearing=False
        ),
    ).atomic_density_fields[0]
    assert field.metadata["grid_definition"] == "target_lattice_interval"
    assert field.metadata["grid_shape"] == (40, 40, 40)
    assert field.metadata["grid_interval_target"] == pytest.approx(0.25)
    assert field.metadata["grid_intervals_realized"] == pytest.approx((0.25, 0.25, 0.25))


def test_explicit_grid_metadata_is_recorded() -> None:
    collection = make_collection(base_fractional())
    field = density_scene(
        collection,
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(grid_shape=(12, 14, 16), grid_interval=0.01),
    ).atomic_density_fields[0]
    assert field.metadata["grid_definition"] == "explicit_shape"
    assert field.metadata["grid_shape"] == (12, 14, 16)


def test_default_gaussian_bandwidth_is_twice_longest_realized_interval() -> None:
    collection = make_collection(base_fractional())
    field = density_scene(
        collection,
        AtomicDensitySelection(atom_indices=(3,)),
        density_options=AtomicDensityOptions(adaptive_smearing=False),
    ).atomic_density_fields[0]
    longest = max(field.metadata["grid_intervals_realized"])
    assert field.gaussian_bandwidth == pytest.approx(2.0 * longest)
    assert field.metadata["gaussian_to_grid_ratio_target"] == pytest.approx(2.0)
    assert field.metadata["gaussian_to_longest_grid_interval_realized"] == pytest.approx(2.0)
    assert field.metadata["smearing_definition"] == "grid_ratio"


def test_periodic_position_sd_uses_minimum_image_metric() -> None:
    from mdstats.plotting.atomic_density import periodic_item_standard_deviations

    cell = np.eye(3) * 10.0
    samples = np.asarray(
        [
            [[0.99, 0.50, 0.50]],
            [[0.01, 0.50, 0.50]],
        ],
        dtype=float,
    )
    values = periodic_item_standard_deviations(
        samples,
        weights=np.asarray([0.5, 0.5]),
        cell=cell,
        pbc=np.ones(3, dtype=bool),
    )
    # Minimum-image displacements are +/-0.1 A along x.  The isotropic
    # per-component SD is sqrt((0.1^2) / 3).
    assert values[0] == pytest.approx(0.1 / np.sqrt(3.0), rel=1.0e-10)


def test_adaptive_smearing_refines_grid_to_sample_spread() -> None:
    from mdstats.plotting.atomic_density import prepare_atomic_density_fields

    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.45, 0.50, 0.50], [0.55, 0.50, 0.50]], dtype=float
    )
    cells = np.repeat((np.eye(3) * 2.0)[None, :, :], 2, axis=0)
    collection = make_collection(frac, cells=cells)
    with pytest.warns(RuntimeWarning, match="Adaptive density refinement"):
        field = prepare_atomic_density_fields(
            collection,
            frame_indices=(0, 1),
            frame_weights=np.asarray([0.5, 0.5]),
            display_cell=cells[0],
            registration_mode="material",
            framework_drift=np.zeros((2, 3)),
            selections=(AtomicDensitySelection(atom_indices=(3,)),),
            options=AtomicDensityOptions(),
            max_fields=1,
            max_total_voxels=4_000_000,
            max_samples=100,
        )[0]
    assert field.metadata["adaptive_smearing_triggered"] is True
    assert field.metadata["adaptive_smearing_budget_limited"] is False
    assert min(field.grid_shape) > 100
    reference_sd = field.metadata["sample_sd_reference"]
    assert reference_sd is not None
    assert field.gaussian_bandwidth <= 0.5 * reference_sd + 1.0e-12
    assert field.metadata["gaussian_to_longest_grid_interval_realized"] == pytest.approx(2.0)


def test_adaptive_smearing_uses_sparse_backend_without_dense_voxel_backoff() -> None:
    from mdstats.plotting.atomic_density import prepare_atomic_density_fields

    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.49, 0.50, 0.50], [0.51, 0.50, 0.50]], dtype=float
    )
    collection = make_collection(frac)
    with pytest.warns(RuntimeWarning, match="Adaptive density refinement"):
        field = prepare_atomic_density_fields(
            collection,
            frame_indices=(0, 1),
            frame_weights=np.asarray([0.5, 0.5]),
            display_cell=np.eye(3) * 10.0,
            registration_mode="material",
            framework_drift=np.zeros((2, 3)),
            selections=(AtomicDensitySelection(atom_indices=(3,)),),
            options=AtomicDensityOptions(),
            max_fields=1,
            max_total_voxels=1_000_000,
            max_samples=100,
        )[0]
    assert field.metadata["adaptive_smearing_triggered"] is True
    assert field.metadata["adaptive_smearing_budget_limited"] is False
    assert field.storage_backend == LOCAL_SPARSE_BACKEND
    assert np.prod(field.grid_shape) > 1_000_000
    reference_sd = field.metadata["sample_sd_reference"]
    assert reference_sd is not None
    assert field.gaussian_bandwidth <= 0.5 * reference_sd + 1.0e-12


def test_density_voxel_cloud_uses_logical_node_coordinates() -> None:
    from mdstats.plotting.atomic_density import (
        PeriodicScalarField3D,
        density_voxel_cloud_arrays,
    )

    values = np.zeros((4, 4, 4), dtype=float)
    values[1, 2, 3] = 1.0
    field = PeriodicScalarField3D(
        field_key="node-coordinate-test",
        label="node coordinate test",
        values=values,
        display_cell=np.eye(3) * 4.0,
        total_measure=1.0,
        selected_atom_indices=(0,),
        gaussian_bandwidth=0.0,
    )
    points, intensities, threshold = density_voxel_cloud_arrays(
        field, 0.5, max_points=10
    )
    np.testing.assert_allclose(points, [[1.0, 2.0, 3.0]], atol=1.0e-14)
    np.testing.assert_allclose(intensities, [1.0])
    assert threshold == pytest.approx(1.0)
