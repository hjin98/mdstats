"""LD4 transactional automatic density-backend selection tests."""

from __future__ import annotations

from dataclasses import replace
import json

import numpy as np
import pytest

from mdstats import (
    AUTO_BACKEND,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    AtomisticFrameCollection,
    AtomicDensityOptions,
    AtomicDensitySelection,
    DensityBackendCandidateEstimate,
    DensityBackendCandidateSet,
    DensityBackendSelection,
    DensityKernelOptions,
    DensityPhaseAFieldPlan,
    DensityPhaseBFieldPlan,
    DensityPlanningLimits,
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
    preferred_auto_backend,
    prepare_framework_dynamics_scene,
    select_density_scene_backends,
)
from mdstats.plotting.atomic_density import prepare_atomic_density_fields
from mdstats.plotting.graph_errors import GraphComplexityError


def _collection(fractional: np.ndarray) -> AtomisticFrameCollection:
    frac = np.asarray(fractional, dtype=np.float64)
    n_frames, n_atoms, _ = frac.shape
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11][:n_atoms], dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-ld4",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _localized_collection() -> AtomisticFrameCollection:
    frac = np.asarray(
        [
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.70, 0.50, 0.50]],
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.71, 0.50, 0.50]],
        ],
        dtype=np.float64,
    )
    return _collection(frac)


def _broad_collection() -> AtomisticFrameCollection:
    coords = np.array(
        np.meshgrid(
            np.arange(8, dtype=np.float64) / 8.0,
            np.arange(8, dtype=np.float64) / 8.0,
            np.arange(8, dtype=np.float64) / 8.0,
            indexing="ij",
        )
    ).reshape(3, -1).T
    frac = np.empty((coords.shape[0], 4, 3), dtype=np.float64)
    frac[:, :3, :] = np.asarray(
        [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10]]
    )
    frac[:, 3, :] = coords
    return _collection(frac)


def _auto_options(shape: tuple[int, int, int]) -> AtomicDensityOptions:
    return AtomicDensityOptions(
        grid_shape=shape,
        gaussian_bandwidth=0.0,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend=AUTO_BACKEND,
            local_block_shape=(4, 4, 4),
        ),
    )


def _prepare(collection: AtomisticFrameCollection, shape: tuple[int, int, int], budget: int):
    n_frames = collection.n_frames
    return prepare_atomic_density_fields(
        collection,
        frame_indices=tuple(range(n_frames)),
        frame_weights=np.full(n_frames, 1.0 / n_frames),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((n_frames, 3)),
        selections=(AtomicDensitySelection(atom_indices=(3,)),),
        options=_auto_options(shape),
        max_fields=4,
        max_total_voxels=budget,
        max_samples=10_000,
    )[0]


def _estimate(
    backend: str,
    *,
    active_fraction: float,
    peak: int,
    work: int,
    feasible: bool = True,
) -> DensityBackendCandidateEstimate:
    logical = 1000
    return DensityBackendCandidateEstimate(
        backend=backend,
        feasible=feasible,
        logical_node_count=logical,
        active_node_count=int(round(active_fraction * logical)),
        stored_value_count=logical if backend == DENSE_BACKEND else 200,
        stored_block_count=0 if backend == DENSE_BACKEND else 4,
        kernel_pair_count=0 if backend == DENSE_BACKEND else 300,
        planning_bytes=100,
        retained_bytes=200,
        estimated_peak_bytes=peak,
        estimated_work=work,
        infeasible_reason=None if feasible else "infeasible",
    )


def test_policy_anchors_and_tie_breaks() -> None:
    dense = _estimate(DENSE_BACKEND, active_fraction=1.0, peak=1000, work=1000)
    broad_sparse = _estimate(
        LOCAL_SPARSE_BACKEND, active_fraction=0.60, peak=200, work=100
    )
    assert preferred_auto_backend(
        dense, broad_sparse, sparse_activation_fraction=0.20
    ) == (DENSE_BACKEND, "broad_active_fraction")

    localized = _estimate(
        LOCAL_SPARSE_BACKEND, active_fraction=0.10, peak=600, work=900
    )
    assert preferred_auto_backend(
        dense, localized, sparse_activation_fraction=0.20
    ) == (LOCAL_SPARSE_BACKEND, "localized_and_memory_efficient")

    intermediate = _estimate(
        LOCAL_SPARSE_BACKEND, active_fraction=0.30, peak=800, work=1200
    )
    assert preferred_auto_backend(
        dense, intermediate, sparse_activation_fraction=0.20
    ) == (LOCAL_SPARSE_BACKEND, "lower_estimated_peak_bytes")

    tied = _estimate(
        LOCAL_SPARSE_BACKEND, active_fraction=0.30, peak=1000, work=1000
    )
    assert preferred_auto_backend(
        dense, tied, sparse_activation_fraction=0.20
    ) == (DENSE_BACKEND, "dense_tie_break")


def test_localized_atomic_auto_selects_sparse_and_matches_forced_sparse() -> None:
    collection = _localized_collection()
    auto = _prepare(collection, (64, 64, 64), 400_000)
    assert auto.storage_backend == LOCAL_SPARSE_BACKEND
    assert auto.grid_shape == (64, 64, 64)
    selection = auto.metadata["backend_selection"]
    assert selection["reason"] == "localized_and_memory_efficient"
    assert selection["local_sparse"]["active_fraction"] <= 0.20

    forced_options = replace(
        _auto_options((64, 64, 64)),
        storage_options=DensityStorageOptions(
            grid_backend=LOCAL_SPARSE_BACKEND, local_block_shape=(4, 4, 4)
        ),
    )
    forced = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(3,)),),
        options=forced_options,
        max_fields=4,
        max_total_voxels=1,
        max_samples=10_000,
    )[0]
    np.testing.assert_array_equal(
        auto.to_dense_values(max_nodes=1_000_000),
        forced.to_dense_values(max_nodes=1_000_000),
    )


def test_broad_atomic_auto_selects_dense() -> None:
    field = _prepare(_broad_collection(), (8, 8, 8), 10_000)
    assert field.storage_backend == DENSE_BACKEND
    selection = field.metadata["backend_selection"]
    assert selection["reason"] == "broad_active_fraction"
    assert selection["local_sparse"]["active_fraction"] == pytest.approx(1.0)


def test_auto_never_reduces_resolution_to_fit_dense_budget() -> None:
    field = _prepare(_localized_collection(), (64, 64, 64), 64)
    assert field.grid_shape == (64, 64, 64)
    assert field.storage_backend == LOCAL_SPARSE_BACKEND
    selection = field.metadata["backend_selection"]
    assert selection["dense"]["feasible"] is False
    assert "dense" in selection["reason"]




def test_default_options_select_sparse_without_dense_resolution_backoff() -> None:
    collection = _localized_collection()
    field = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(3,)),),
        options=AtomicDensityOptions(
            grid_shape=(64, 64, 64),
            gaussian_bandwidth=0.0,
            adaptive_smearing=False,
        ),
        max_fields=4,
        max_total_voxels=64,
        max_samples=10_000,
    )[0]

    assert field.grid_shape == (64, 64, 64)
    assert field.storage_backend == LOCAL_SPARSE_BACKEND
    selection = field.metadata["backend_selection"]
    assert selection["requested_backend"] == AUTO_BACKEND
    assert selection["dense"]["feasible"] is False
    assert selection["selected_backend"] == LOCAL_SPARSE_BACKEND
    assert field.metadata["adaptive_smearing_budget_limited"] is False




def test_default_adaptive_resolution_is_not_broadened_by_dense_voxel_limit() -> None:
    collection = _localized_collection()
    options = AtomicDensityOptions(
        grid_interval=0.20,
        adaptive_smearing=True,
        max_smearing_to_sample_sd_ratio=0.50,
        spread_sampling_strategy="all",
    )
    with pytest.warns(RuntimeWarning, match="Adaptive density refinement"):
        field = prepare_atomic_density_fields(
            collection,
            frame_indices=(0, 1),
            frame_weights=np.asarray([0.5, 0.5]),
            display_cell=np.eye(3) * 10.0,
            registration_mode="material",
            framework_drift=np.zeros((2, 3)),
            selections=(AtomicDensitySelection(atom_indices=(3,)),),
            options=options,
            max_fields=4,
            max_total_voxels=64,
            max_samples=10_000,
        )[0]

    assert field.storage_backend == LOCAL_SPARSE_BACKEND
    assert field.metadata["adaptive_smearing_triggered"] is True
    assert field.metadata["adaptive_smearing_budget_limited"] is False
    assert (
        field.gaussian_bandwidth / field.metadata["sample_sd_reference"]
        <= 0.50 + 1.0e-12
    )
    assert np.prod(field.grid_shape, dtype=object) > 64
    selection = field.metadata["backend_selection"]
    assert selection["dense"]["feasible"] is False
    assert selection["selected_backend"] == LOCAL_SPARSE_BACKEND


def test_selection_record_round_trips_through_canonical_json() -> None:
    field = _prepare(_localized_collection(), (64, 64, 64), 400_000)
    restored = DensityBackendSelection.from_json_dict(
        field.metadata["backend_selection"]
    )
    payload = json.loads(json.dumps(restored.to_json_dict(), sort_keys=True))
    round_tripped = DensityBackendSelection.from_json_dict(payload)
    assert round_tripped.to_json_dict() == restored.to_json_dict()
    assert round_tripped.field_key == field.field_key


def _framework_topology(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.0, ("Al", "O"): 2.0}
        )
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
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
    return build_framework_topology(state, mapping)


def test_scene_auto_selects_all_localized_channels_before_realization() -> None:
    collection = _localized_collection()
    storage = DensityStorageOptions(
        grid_backend=AUTO_BACKEND,
        local_block_shape=(4, 4, 4),
    )
    kernel = DensityKernelOptions(
        smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        _framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(32, 32, 32),
            gaussian_bandwidth=0.20,
            adaptive_smearing=False,
            kernel_options=kernel,
            storage_options=storage,
        ),
        framework_density_options=FrameworkDensityOptions(
            grid_shape=(32, 32, 32),
            gaussian_bandwidth=0.20,
            adaptive_smearing=False,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="explicit",
            kernel_options=kernel,
            storage_options=storage,
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=200_000,
            max_density_total_peak_bytes=500_000_000,
        ),
    )
    fields = [*scene.atomic_density_fields]
    assert scene.framework_density_fields is not None
    fields.extend(scene.framework_density_fields.fields)
    assert len(fields) == 3
    assert all(field.storage_backend == LOCAL_SPARSE_BACKEND for field in fields)
    assert scene.planning_record is not None
    selected = tuple(
        str(plan.metadata["backend"])
        for plan in scene.planning_record.phase_b_fields
    )
    assert selected == (LOCAL_SPARSE_BACKEND,) * 3
    for field in fields:
        decision = field.metadata["backend_selection"]
        assert decision["selected_backend"] == LOCAL_SPARSE_BACKEND
        assert decision["requested_backend"] == AUTO_BACKEND
        assert decision["local_sparse"]["active_fraction"] < 0.50

    forced_storage = DensityStorageOptions(
        grid_backend=LOCAL_SPARSE_BACKEND,
        local_block_shape=(4, 4, 4),
    )
    forced_scene = prepare_framework_dynamics_scene(
        collection,
        _framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(32, 32, 32),
            gaussian_bandwidth=0.20,
            adaptive_smearing=False,
            kernel_options=kernel,
            storage_options=forced_storage,
        ),
        framework_density_options=FrameworkDensityOptions(
            grid_shape=(32, 32, 32),
            gaussian_bandwidth=0.20,
            adaptive_smearing=False,
            edge_sample_spacing=0.20,
            edge_sample_spacing_mode="explicit",
            kernel_options=kernel,
            storage_options=forced_storage,
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=1,
            max_density_total_peak_bytes=500_000_000,
        ),
    )
    forced_fields = [*forced_scene.atomic_density_fields]
    assert forced_scene.framework_density_fields is not None
    forced_fields.extend(forced_scene.framework_density_fields.fields)
    for automatic, forced in zip(fields, forced_fields, strict=True):
        np.testing.assert_array_equal(
            automatic.to_dense_values(max_nodes=100_000),
            forced.to_dense_values(max_nodes=100_000),
        )
        assert automatic.integral == forced.integral
        for fraction in (0.5, 0.8, 0.95):
            assert automatic.threshold_for_mass_fraction(fraction) == (
                forced.threshold_for_mass_fraction(fraction)
            )


def _phase_a(field_key: str, order: int) -> DensityPhaseAFieldPlan:
    return DensityPhaseAFieldPlan(
        field_key=field_key,
        source_kind="atomic_occupancy",
        construction_order=order,
        sample_count_upper=1,
        sample_bytes_upper=32,
        logical_node_count_upper=64,
        cic_insertions_upper=8,
        stencil_value_count_upper=64,
        nonzero_node_count_upper=64,
        stored_value_count_upper=64,
        stored_block_count_upper=8,
        kernel_pair_count_upper=1000,
        component_value_count_upper=125,
        mesh_cell_count_upper=64,
        mesh_face_count_upper=960,
        render_point_count_upper=64,
        retained_bytes_upper=1_000_000,
        transient_bytes_upper=1_000_000,
        metadata={"backend": AUTO_BACKEND},
    )


def _phase_b(field_key: str, order: int, backend: str) -> DensityPhaseBFieldPlan:
    dense = backend == DENSE_BACKEND
    return DensityPhaseBFieldPlan(
        field_key=field_key,
        source_kind="atomic_occupancy",
        construction_order=order,
        sample_count=1,
        sample_bytes=32,
        grid_shape=(4, 4, 4),
        logical_node_count=64,
        occupied_cic_node_indices=np.asarray([0], dtype=np.int64),
        nonzero_node_count_upper=8 if not dense else 64,
        stored_value_count=64 if dense else 8,
        stored_block_count=0 if dense else 1,
        stencil_value_count=1,
        kernel_pair_count=0 if dense else 8,
        component_value_count=125 if dense else 0,
        mesh_cell_count=64 if dense else 0,
        mesh_face_count_upper=960 if dense else 0,
        render_point_count_upper=0,
        planning_bytes=8,
        retained_bytes=512 if dense else 80,
        transient_bytes_upper=20_000 if dense else 2_000,
        metadata={"backend": backend, "operator": DISCRETE_PERIODIZED_OPERATOR},
    )


def test_global_resource_override_is_deterministic() -> None:
    limits = DensityPlanningLimits(
        max_density_fields=2,
        max_density_voxels=64,
        max_density_samples=100,
        max_density_sample_bytes=1_000_000,
        max_density_planning_bytes=1_000_000,
        max_density_stencil_values=1_000,
        max_density_nonzero_nodes=1_000,
        max_density_stored_block_values=1_000,
        max_density_blocks=100,
        max_density_kernel_pairs=10_000,
        max_density_component_values=1_000,
        max_density_mesh_cells=1_000,
        max_density_mesh_faces=10_000,
        max_density_render_points=1_000,
        # The authoritative runtime-memory envelope must be large enough to
        # admit two fields; the explicit per-scene limits below still test the
        # deterministic global backend override rather than host scarcity.
        max_density_total_peak_bytes=1_000_000_000,
    )
    candidates = []
    for order in range(2):
        dense_plan = _phase_b(f"f{order}", order, DENSE_BACKEND)
        sparse_plan = _phase_b(f"f{order}", order, LOCAL_SPARSE_BACKEND)
        dense_est = _estimate(
            DENSE_BACKEND, active_fraction=1.0, peak=20_000, work=100
        )
        sparse_est = _estimate(
            LOCAL_SPARSE_BACKEND, active_fraction=0.60, peak=2_000, work=10
        )
        candidates.append(
            DensityBackendCandidateSet(
                field_key=f"f{order}",
                requested_backend=AUTO_BACKEND,
                dense_plan=dense_plan,
                sparse_plan=sparse_plan,
                dense_estimate=dense_est,
                sparse_estimate=sparse_est,
                preferred_backend=DENSE_BACKEND,
                preferred_reason="broad_active_fraction",
                sparse_activation_fraction=0.20,
            )
        )
    plan = select_density_scene_backends(
        phase_a_fields=(_phase_a("f0", 0), _phase_a("f1", 1)),
        candidates=tuple(candidates),
        limits=limits,
    )
    selected = tuple(str(v.metadata["backend"]) for v in plan.phase_b_fields)
    assert selected == (DENSE_BACKEND, LOCAL_SPARSE_BACKEND)
    second = plan.phase_b_fields[1].metadata["backend_selection"]
    assert second["globally_overridden"] is True
    assert second["reason"].startswith("global_resource_override")


def test_no_feasible_backend_reports_both_reasons() -> None:
    dense = _estimate(
        DENSE_BACKEND,
        active_fraction=1.0,
        peak=1,
        work=1,
        feasible=False,
    )
    sparse = _estimate(
        LOCAL_SPARSE_BACKEND,
        active_fraction=0.0,
        peak=1,
        work=1,
        feasible=False,
    )
    with pytest.raises(GraphComplexityError, match="Neither dense nor local_sparse"):
        preferred_auto_backend(dense, sparse, sparse_activation_fraction=0.20)


def test_forced_local_sparse_phase_b_uses_exact_hybrid_execution_plan() -> None:
    collection = _localized_collection()
    storage = DensityStorageOptions(
        grid_backend=LOCAL_SPARSE_BACKEND,
        local_block_shape=(4, 4, 4),
    )
    kernel = DensityKernelOptions(
        smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        _framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(32, 32, 32),
            gaussian_bandwidth=0.20,
            adaptive_smearing=False,
            kernel_options=kernel,
            storage_options=storage,
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=200_000,
            max_density_total_peak_bytes=500_000_000,
        ),
    )
    assert scene.planning_record is not None
    plan = scene.planning_record.phase_b_fields[0]
    assert plan.metadata["phase_b_execution_planner"] == "ld8_s3_hybrid_exact_v1"
    assert plan.metadata["kernel_pair_semantics"] == "actual_direct_tile_pairs"
    assert plan.kernel_pair_count == plan.metadata["direct_pair_count"]
    assert plan.kernel_pair_count <= plan.metadata["exact_contribution_count"]
    assert (
        plan.metadata["hybrid_direct_tile_count"]
        + plan.metadata["hybrid_fft_tile_count"]
        == plan.metadata["hybrid_compute_tile_count"]
    )
    assert scene.planning_record.metadata["total_direct_kernel_pairs"] == plan.kernel_pair_count
    assert (
        scene.planning_record.metadata["total_exact_contributions"]
        == plan.metadata["exact_contribution_count"]
    )
