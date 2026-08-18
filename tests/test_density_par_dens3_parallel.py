from __future__ import annotations

import warnings

import numpy as np

from mdstats import (
    AtomisticFrameCollection,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    DensityKernelOptions,
    DensityStorageOptions,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDensityOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    build_framework_topology,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
)
from mdstats.plotting.density_sparse_mesh import prepare_sparse_density_mesh


def _collection(n_frames: int = 6) -> AtomisticFrameCollection:
    base = np.asarray(
        [[0.10, 0.10, 0.10], [0.20, 0.20, 0.10], [0.30, 0.10, 0.10], [0.70, 0.50, 0.50]],
        dtype=float,
    )
    frac = np.repeat(base[None, :, :], n_frames, axis=0)
    # Small deterministic motion keeps adaptive diagnostics finite without
    # changing topology.
    frac[:, 0, 2] += np.linspace(-0.003, 0.003, n_frames)
    frac[:, 1, 1] += np.linspace(0.002, -0.002, n_frames)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11], dtype=np.int32),
        masses=np.ones(4),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, 4, 3)),
        provenance=FrameCollectionProvenance(
            source_format="par-dens3-synthetic",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _topology(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.0, ("Al", "O"): 2.0})
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),),
    )
    return build_framework_topology(state, mapping)


def _scene(*, workers: int, sparse: bool):
    collection = _collection()
    storage = DensityStorageOptions(
        grid_backend="local_sparse" if sparse else DENSE_BACKEND,
        local_block_shape=(4, 4, 4),
    )
    options = FrameworkDensityOptions(
        grid_shape=(24, 24, 24),
        gaussian_bandwidth=0.40,
        adaptive_smearing=False,
        edge_sample_spacing=0.15,
        edge_sample_spacing_mode="explicit",
        kernel_options=DensityKernelOptions(smoothing_operator=DISCRETE_PERIODIZED_OPERATOR),
        storage_options=storage,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return prepare_framework_dynamics_scene(
            collection,
            _topology(collection),
            framework_density_options=options,
            resources=FrameworkDynamicsResources(
                max_threads=workers,
                max_memory_bytes="2GiB",
                max_density_voxels=500_000,
            ),
        )


def test_par_dens3_dense_fields_execute_concurrently_without_changing_science() -> None:
    serial = _scene(workers=1, sparse=False)
    parallel = _scene(workers=4, sparse=False)
    assert serial.planning_record is not None and parallel.planning_record is not None
    assert serial.planning_record.approval_id == parallel.planning_record.approval_id
    assert serial.planning_record.schema_version == "mdstats.density-scene-plan.v3"
    assert parallel.metadata["density_scheduler_policy"] == "par_dens3_parallel_field_realization_v1"
    assert serial.metadata["density_scheduler_summary"]["maximum_concurrent_tasks"] == 1
    assert parallel.metadata["density_scheduler_summary"]["maximum_concurrent_tasks"] >= 2
    assert serial.framework_density_fields is not None
    assert parallel.framework_density_fields is not None
    for left, right in zip(serial.framework_density_fields.fields, parallel.framework_density_fields.fields, strict=True):
        np.testing.assert_array_equal(left.values, right.values)
        assert left.integral == right.integral
        for fraction in (0.50, 0.80, 0.95):
            assert left.threshold_for_mass_fraction(fraction) == right.threshold_for_mass_fraction(fraction)


def test_par_dens3_sparse_worker_counts_preserve_field_support_hdr_and_mesh() -> None:
    serial = _scene(workers=1, sparse=True)
    parallel = _scene(workers=4, sparse=True)
    assert serial.planning_record is not None and parallel.planning_record is not None
    assert serial.planning_record.approval_id == parallel.planning_record.approval_id
    # The execution plan is allowed to differ because FFT worker/cost evidence is
    # intentionally separate from the scientific authority.
    assert serial.planning_record.execution_plan_id != parallel.planning_record.execution_plan_id
    assert serial.framework_density_fields is not None
    assert parallel.framework_density_fields is not None
    for left, right in zip(serial.framework_density_fields.fields, parallel.framework_density_fields.fields, strict=True):
        assert left.content_identity == right.content_identity
        np.testing.assert_array_equal(left.active_block_indices, right.active_block_indices)
        np.testing.assert_array_equal(left.occupancy_bitsets, right.occupancy_bitsets)
        np.testing.assert_array_equal(left.packed_values, right.packed_values)
        assert left.integral == right.integral
        for fraction in (0.50, 0.80, 0.95):
            assert left.threshold_for_mass_fraction(fraction) == right.threshold_for_mass_fraction(fraction)
        surface_left = prepare_sparse_density_mesh(
            left, 0.80, max_faces=200_000, max_candidate_cells=200_000,
            max_raw_faces=500_000, max_raw_vertices=1_500_000,
            max_workspace_bytes=512_000_000, max_dense_fallback_nodes=1_000_000,
            allow_cloud_fallback=False,
        )
        surface_right = prepare_sparse_density_mesh(
            right, 0.80, max_faces=200_000, max_candidate_cells=200_000,
            max_raw_faces=500_000, max_raw_vertices=1_500_000,
            max_workspace_bytes=512_000_000, max_dense_fallback_nodes=1_000_000,
            allow_cloud_fallback=False,
        )
        assert surface_left.mesh is not None and surface_right.mesh is not None
        np.testing.assert_array_equal(surface_left.mesh.vertices_fractional, surface_right.mesh.vertices_fractional)
        np.testing.assert_array_equal(surface_left.mesh.faces, surface_right.mesh.faces)
        assert surface_left.mesh.scientific_hdr_threshold == surface_right.mesh.scientific_hdr_threshold
        assert surface_left.mesh.topology.to_json_dict() == surface_right.mesh.topology.to_json_dict()
