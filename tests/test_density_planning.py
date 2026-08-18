"""LD0-R3 bounded density-scene planning tests."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats import (
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    AtomisticFrameCollection,
    AtomicDensityOptions,
    AtomicDensitySelection,
    DensityKernelOptions,
    DensityStorageOptions,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    build_framework_topology,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
)
from mdstats.plotting import (
    DensityPhaseAFieldPlan,
    DensityPhaseBFieldPlan,
    DensityPlanningLimits,
    GraphComplexityError,
    occupied_cic_node_indices,
    plan_density_scene,
    validate_density_phase_a,
)


def phase_a(**changes: int) -> DensityPhaseAFieldPlan:
    values = dict(
        field_key="field",
        source_kind="atomic_occupancy",
        construction_order=0,
        sample_count_upper=1,
        sample_bytes_upper=32,
        logical_node_count_upper=64,
        cic_insertions_upper=8,
        stencil_value_count_upper=0,
        nonzero_node_count_upper=64,
        stored_value_count_upper=64,
        stored_block_count_upper=0,
        kernel_pair_count_upper=0,
        component_value_count_upper=125,
        mesh_cell_count_upper=64,
        mesh_face_count_upper=960,
        render_point_count_upper=0,
        retained_bytes_upper=512,
        transient_bytes_upper=16_480,
    )
    values.update(changes)
    return DensityPhaseAFieldPlan(**values)


def phase_b(**changes: object) -> DensityPhaseBFieldPlan:
    values: dict[str, object] = dict(
        field_key="field",
        source_kind="atomic_occupancy",
        construction_order=0,
        sample_count=1,
        sample_bytes=32,
        grid_shape=(4, 4, 4),
        logical_node_count=64,
        occupied_cic_node_indices=np.asarray([0], dtype=np.int64),
        nonzero_node_count_upper=64,
        stored_value_count=64,
        stored_block_count=0,
        stencil_value_count=0,
        kernel_pair_count=0,
        component_value_count=125,
        mesh_cell_count=64,
        mesh_face_count_upper=960,
        render_point_count_upper=0,
        planning_bytes=8,
        retained_bytes=512,
        transient_bytes_upper=16_480,
    )
    values.update(changes)
    return DensityPhaseBFieldPlan(**values)


def permissive_limits(**changes: int) -> DensityPlanningLimits:
    base = DensityPlanningLimits(
        max_density_fields=8,
        max_density_voxels=10_000,
        max_density_samples=10_000,
        max_density_sample_bytes=10_000_000,
        max_density_planning_bytes=10_000_000,
        max_density_stencil_values=10_000,
        max_density_nonzero_nodes=10_000,
        max_density_stored_block_values=10_000,
        max_density_blocks=10_000,
        max_density_kernel_pairs=10_000,
        max_density_component_values=10_000,
        max_density_mesh_cells=10_000,
        max_density_mesh_faces=100_000,
        max_density_render_points=10_000,
        max_density_total_peak_bytes=1_000_000_000,
    )
    return replace(base, **changes)


def test_occupied_cic_nodes_follow_logical_node_convention() -> None:
    on_node = occupied_cic_node_indices(
        np.asarray([[0.25, 0.50, 0.75]]),
        (4, 4, 4),
        max_planning_bytes=10_000,
    )
    assert on_node.tolist() == [np.ravel_multi_index((1, 2, 3), (4, 4, 4))]
    off_node = occupied_cic_node_indices(
        np.asarray([[0.30, 0.55, 0.80]]),
        (4, 4, 4),
        max_planning_bytes=10_000,
    )
    assert off_node.size == 8
    assert np.all(off_node[1:] > off_node[:-1])
    assert not off_node.flags.writeable


def test_scene_plan_is_deterministic_and_immutable() -> None:
    plan1 = plan_density_scene(
        phase_a_fields=(phase_a(),),
        phase_b_fields=(phase_b(),),
        limits=permissive_limits(),
    )
    plan2 = plan_density_scene(
        phase_a_fields=(phase_a(),),
        phase_b_fields=(phase_b(),),
        limits=permissive_limits(),
    )
    assert plan1.approval_id == plan2.approval_id
    assert plan1.phase_c_approved
    assert plan1.estimated_peak_bytes >= plan1.retained_bytes
    assert plan1.to_json_dict()["approval_id"] == plan1.approval_id
    restored = type(plan1).from_json_dict(plan1.to_json_dict(include_indices=True))
    assert restored.approval_id == plan1.approval_id
    np.testing.assert_array_equal(
        restored.phase_b_fields[0].occupied_cic_node_indices,
        plan1.phase_b_fields[0].occupied_cic_node_indices,
    )
    assert not plan1.phase_b_fields[0].occupied_cic_node_indices.flags.writeable


@pytest.mark.parametrize(
    ("field_changes", "limit_changes", "limit_name"),
    [
        ({"sample_count_upper": 2}, {"max_density_samples": 1}, "max_density_samples"),
        ({"sample_bytes_upper": 64}, {"max_density_sample_bytes": 32}, "max_density_sample_bytes"),
        ({"stencil_value_count_upper": 2}, {"max_density_stencil_values": 1}, "max_density_stencil_values"),
        ({"nonzero_node_count_upper": 64}, {"max_density_nonzero_nodes": 63}, "max_density_nonzero_nodes"),
        ({"stored_value_count_upper": 64}, {"max_density_stored_block_values": 63}, "max_density_stored_block_values"),
        ({"stored_block_count_upper": 2}, {"max_density_blocks": 1}, "max_density_blocks"),
        ({"kernel_pair_count_upper": 2}, {"max_density_kernel_pairs": 1}, "max_density_kernel_pairs"),
        ({"component_value_count_upper": 125}, {"max_density_component_values": 124}, "max_density_component_values"),
        ({"mesh_cell_count_upper": 64}, {"max_density_mesh_cells": 63}, "max_density_mesh_cells"),
        ({"mesh_face_count_upper": 960}, {"max_density_mesh_faces": 959}, "max_density_mesh_faces"),
        ({"render_point_count_upper": 2}, {"max_density_render_points": 1}, "max_density_render_points"),
    ],
)
def test_every_phase_a_hard_limit_fails_before_allocation(
    field_changes: dict[str, int],
    limit_changes: dict[str, int],
    limit_name: str,
) -> None:
    with pytest.raises(GraphComplexityError, match=limit_name):
        validate_density_phase_a(
            (phase_a(**field_changes),),
            permissive_limits(**limit_changes),
        )


def test_field_count_limit_is_phase_a_failure() -> None:
    second = replace(phase_a(), field_key="field-2", construction_order=1)
    with pytest.raises(GraphComplexityError, match="max_density_fields"):
        validate_density_phase_a(
            (phase_a(), second),
            permissive_limits(max_density_fields=1),
        )


@pytest.mark.parametrize(
    ("limit_changes", "limit_name"),
    [
        ({"max_density_planning_bytes": 7}, "max_density_planning_bytes"),
        ({"max_density_voxels": 63}, "max_density_voxels"),
        ({"max_density_total_peak_bytes": 16_479}, "max_density_total_peak_bytes"),
    ],
)
def test_phase_c_limits_are_enforced(
    limit_changes: dict[str, int], limit_name: str
) -> None:
    upper = phase_a()
    exact = phase_b()
    if limit_name == "max_density_total_peak_bytes":
        # A tiny primary memory budget also tightens all derived low-level
        # guardrails.  Keep this fixture below those earlier limits so the test
        # reaches the intended Phase-C peak check.
        upper = phase_a(
            logical_node_count_upper=48,
            nonzero_node_count_upper=48,
            stored_value_count_upper=48,
            component_value_count_upper=96,
            mesh_cell_count_upper=48,
            mesh_face_count_upper=144,
            retained_bytes_upper=384,
        )
        exact = phase_b(
            grid_shape=(3, 4, 4),
            logical_node_count=48,
            nonzero_node_count_upper=48,
            stored_value_count=48,
            component_value_count=96,
            mesh_cell_count=48,
            mesh_face_count_upper=144,
            retained_bytes=384,
        )
    with pytest.raises(GraphComplexityError, match=limit_name):
        plan_density_scene(
            phase_a_fields=(upper,),
            phase_b_fields=(exact,),
            limits=permissive_limits(**limit_changes),
        )


def make_collection() -> AtomisticFrameCollection:
    one = np.asarray(
        [
            [0.10, 0.10, 0.10],
            [0.20, 0.10, 0.10],
            [0.30, 0.10, 0.10],
            [0.70, 0.50, 0.50],
        ]
    )
    frac = np.repeat(one[None, :, :], 3, axis=0)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(3, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11], dtype=np.int32),
        masses=np.ones(4),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(3, dtype=np.int64),
        times=np.arange(3, dtype=float),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], 3, axis=0),
        origins=np.zeros((3, 3)),
        fractional_positions=frac,
        velocities=np.zeros((3, 4, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-planning",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def topology_for(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.1, ("Al", "O"): 2.1}
        )
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="bridge"),
        ),
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, mapping)




def test_phase_c_enforces_scene_wide_stencil_limit() -> None:
    upper_1 = phase_a(stencil_value_count_upper=64)
    upper_2 = replace(
        upper_1,
        field_key="field-2",
        construction_order=1,
    )
    exact_1 = phase_b(stencil_value_count=64)
    exact_2 = replace(
        exact_1,
        field_key="field-2",
        construction_order=1,
    )
    with pytest.raises(GraphComplexityError, match="max_density_stencil_values"):
        plan_density_scene(
            phase_a_fields=(upper_1, upper_2),
            phase_b_fields=(exact_1, exact_2),
            limits=permissive_limits(max_density_stencil_values=100),
        )


def test_canonical_scene_plan_records_dense_stencil_and_operator() -> None:
    collection = make_collection()
    scene = prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(8, 8, 8),
            gaussian_bandwidth=0.25,
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
            ),
            storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
        ),
    )
    plan = scene.planning_record
    assert plan is not None
    field_plan = plan.phase_b_fields[0]
    assert field_plan.stencil_value_count == 8**3
    assert field_plan.metadata["operator"] == DISCRETE_PERIODIZED_OPERATOR
    assert plan.metadata["operator"] == DISCRETE_PERIODIZED_OPERATOR
    assert plan.metadata["operators"] == (DISCRETE_PERIODIZED_OPERATOR,)
    assert plan.metadata["total_stencil_values"] == 8**3

def test_scene_carries_approved_plan_and_realization_summary() -> None:
    collection = make_collection()
    scene = prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(8, 8, 8), gaussian_bandwidth=0.25
        ),
    )
    plan = scene.planning_record
    assert plan is not None and plan.phase_c_approved
    assert [v.field_key for v in plan.phase_b_fields] == ["atomic-density-0"]
    assert plan.phase_b_fields[0].grid_shape == (8, 8, 8)
    assert scene.metadata["density_planning_approval_id"] == plan.approval_id
    realized = scene.metadata["density_realization_summary"]
    assert realized["realized_retained_bytes"] <= plan.retained_bytes
    assert realized["estimated_peak_bytes"] == plan.estimated_peak_bytes


def test_phase_b_failure_occurs_before_dense_field_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = make_collection()
    import mdstats.plotting.atomic_density as atomic_density_module

    called = False
    original = atomic_density_module.PeriodicScalarField3D

    def forbidden(*args: object, **kwargs: object):
        nonlocal called
        called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(atomic_density_module, "PeriodicScalarField3D", forbidden)
    with pytest.raises(GraphComplexityError, match="max_density_planning_bytes"):
        prepare_framework_dynamics_scene(
            collection,
            topology_for(collection),
            atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
            atomic_density_options=AtomicDensityOptions(
                grid_shape=(8, 8, 8), gaussian_bandwidth=0.25
            ),
            resources=FrameworkDynamicsResources(max_density_planning_bytes=1),
        )
    assert not called


def test_global_approval_precedes_first_field_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = make_collection()
    import mdstats.plotting.atomic_density as atomic_density_module
    import mdstats.plotting.framework_dynamics as dynamics_module

    approved = False
    original_plan = dynamics_module.plan_density_scene
    original_field = atomic_density_module.PeriodicScalarField3D

    def wrapped_plan(*args: object, **kwargs: object):
        nonlocal approved
        result = original_plan(*args, **kwargs)
        approved = True
        return result

    def wrapped_field(*args: object, **kwargs: object):
        assert approved
        return original_field(*args, **kwargs)

    monkeypatch.setattr(dynamics_module, "plan_density_scene", wrapped_plan)
    monkeypatch.setattr(atomic_density_module, "PeriodicScalarField3D", wrapped_field)
    prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(8, 8, 8), gaussian_bandwidth=0.25
        ),
    )
    assert approved


def test_phase_c_uses_hybrid_direct_pairs_not_nominal_contributions() -> None:
    upper = phase_a(
        stencil_value_count_upper=1,
        kernel_pair_count_upper=10,
        nonzero_node_count_upper=1,
        stored_value_count_upper=1,
        component_value_count_upper=0,
        mesh_cell_count_upper=0,
        mesh_face_count_upper=0,
        retained_bytes_upper=64,
        transient_bytes_upper=256,
        metadata={"backend": "local_sparse"},
    )
    exact = phase_b(
        stencil_value_count=1,
        kernel_pair_count=10,
        nonzero_node_count_upper=1,
        stored_value_count=1,
        component_value_count=0,
        mesh_cell_count=0,
        mesh_face_count_upper=0,
        retained_bytes=64,
        transient_bytes_upper=256,
        metadata={
            "backend": "local_sparse",
            "phase_b_execution_planner": "ld8_s3_hybrid_exact_v1",
            "kernel_pair_semantics": "actual_direct_tile_pairs",
            "exact_contribution_count": 10_000,
            "direct_pair_count": 10,
            "fft_padded_node_count": 4096,
            "hybrid_estimated_wall_seconds": 0.001,
        },
    )
    plan = plan_density_scene(
        phase_a_fields=(upper,),
        phase_b_fields=(exact,),
        limits=permissive_limits(
            max_density_fields=1,
            max_density_kernel_pairs=100,
            max_density_stencil_values=100,
            max_density_nonzero_nodes=100,
            max_density_stored_block_values=100,
            max_density_component_values=100,
            max_density_mesh_cells=100,
            max_density_mesh_faces=100,
            max_density_total_peak_bytes=1_000_000,
        ),
    )
    assert plan.metadata["total_direct_kernel_pairs"] == 10
    assert plan.metadata["total_exact_contributions"] == 10_000
    assert plan.metadata["total_fft_padded_nodes"] == 4096
    assert plan.metadata["hybrid_field_count"] == 1


def test_phase_c_records_hybrid_fft_wall_time_without_rejecting() -> None:
    upper = phase_a(
        stencil_value_count_upper=1,
        kernel_pair_count_upper=0,
        nonzero_node_count_upper=1,
        stored_value_count_upper=1,
        component_value_count_upper=0,
        mesh_cell_count_upper=0,
        mesh_face_count_upper=0,
        retained_bytes_upper=64,
        transient_bytes_upper=256,
        metadata={"backend": "local_sparse"},
    )
    exact = phase_b(
        stencil_value_count=1,
        kernel_pair_count=0,
        nonzero_node_count_upper=1,
        stored_value_count=1,
        component_value_count=0,
        mesh_cell_count=0,
        mesh_face_count_upper=0,
        retained_bytes=64,
        transient_bytes_upper=256,
        metadata={
            "backend": "local_sparse",
            "phase_b_execution_planner": "ld8_s3_hybrid_exact_v1",
            "kernel_pair_semantics": "actual_direct_tile_pairs",
            "exact_contribution_count": 10_000,
            "direct_pair_count": 0,
            "fft_padded_node_count": 1_000_000,
            "hybrid_estimated_wall_seconds": 10.0,
        },
    )
    plan = plan_density_scene(
        phase_a_fields=(upper,),
        phase_b_fields=(exact,),
        limits=permissive_limits(
            max_density_fields=1,
            max_density_kernel_pairs=100,
            max_density_stencil_values=100,
            max_density_nonzero_nodes=100,
            max_density_stored_block_values=100,
            max_density_component_values=100,
            max_density_mesh_cells=100,
            max_density_mesh_faces=100,
            max_density_total_peak_bytes=1_000_000,
            max_density_wall_time_seconds=1.0,
        ),
    )
    assert plan.phase_c_approved is True
    assert plan.metadata["estimated_preparation_wall_seconds"] > 1.0
    assert plan.metadata["wall_time_admission_enforced"] is False
    assert plan.metadata["wall_time_budget_exceeded"] is True


def test_par_dens3_scene_approval_is_worker_storage_and_executor_neutral() -> None:
    scientific_metadata = {
        "operator": "discrete_periodized_v1",
        "gaussian_bandwidth": 0.5,
        "consumer_registration_signature": "same-registration",
        "selected_atom_indices": [3],
    }
    dense = phase_b(metadata={**scientific_metadata, "backend": "dense"})
    sparse = phase_b(
        stored_value_count=32,
        stored_block_count=1,
        metadata={
            **scientific_metadata,
            "backend": "local_sparse",
            "phase_b_execution_planner": "ld8_s3_hybrid_exact_v1",
            "hybrid_estimated_wall_seconds": 9.0,
            "direct_pair_count": 123,
            "exact_contribution_count": 456,
            "hybrid_plan_identity": "a" * 64,
            "hybrid_predicted_peak_bytes": 123456,
            "fft_workers": 4,
            "block_shape": [8, 8, 8],
        },
    )
    limits_one = replace(permissive_limits(), max_density_threads=1)
    limits_four = replace(permissive_limits(), max_density_threads=4)
    plan_one = plan_density_scene(
        phase_a_fields=(phase_a(stored_block_count_upper=1),), phase_b_fields=(dense,), limits=limits_one,
        metadata={"registration_mode": "material", "frame_count": 10},
    )
    plan_four = plan_density_scene(
        phase_a_fields=(phase_a(stored_block_count_upper=1),), phase_b_fields=(sparse,), limits=limits_four,
        metadata={"registration_mode": "material", "frame_count": 10},
    )
    assert plan_one.approval_id == plan_four.approval_id
    assert plan_one.execution_plan_id != plan_four.execution_plan_id
    assert plan_one.to_json_dict()["approval_identity_semantics"] == (
        "worker_storage_executor_neutral_scientific_plan_v2"
    )


def test_legacy_v1_scene_plan_preserves_resource_sensitive_digest_semantics() -> None:
    current = plan_density_scene(
        phase_a_fields=(phase_a(),),
        phase_b_fields=(phase_b(metadata={"operator": "discrete_periodized_v1"}),),
        limits=replace(permissive_limits(), max_density_threads=1),
    )
    legacy = replace(current, schema_version="mdstats.density-scene-plan.v1")
    assert legacy.approval_id == legacy.execution_plan_id
    payload = legacy.to_json_dict(include_indices=True)
    assert "execution_plan_id" not in payload
    restored = type(legacy).from_json_dict(payload)
    assert restored.schema_version == "mdstats.density-scene-plan.v1"
    assert restored.approval_id == legacy.approval_id


def test_legacy_v2_scene_plan_preserves_par_dens2_scientific_digest_semantics() -> None:
    scientific_metadata = {
        "operator": "discrete_periodized_v1",
        "gaussian_bandwidth": 0.5,
        "consumer_registration_signature": "same-registration",
    }
    base = plan_density_scene(
        phase_a_fields=(phase_a(stored_block_count_upper=1),),
        phase_b_fields=(
            phase_b(
                stored_value_count=32,
                stored_block_count=1,
                metadata={
                    **scientific_metadata,
                    "backend": "local_sparse",
                    "hybrid_plan_identity": "a" * 64,
                    "hybrid_predicted_peak_bytes": 1000,
                    "fft_workers": 1,
                },
            ),
        ),
        limits=replace(permissive_limits(), max_density_threads=1),
    )
    legacy = replace(base, schema_version="mdstats.density-scene-plan.v2")
    changed_execution = replace(
        base,
        schema_version="mdstats.density-scene-plan.v2",
        phase_b_fields=(
            phase_b(
                stored_value_count=32,
                stored_block_count=1,
                metadata={
                    **scientific_metadata,
                    "backend": "local_sparse",
                    "hybrid_plan_identity": "b" * 64,
                    "hybrid_predicted_peak_bytes": 2000,
                    "fft_workers": 4,
                },
            ),
        ),
    )
    # v2 remains frozen at the PAR-DENS2 projection; fields that were not
    # excluded there remain digest-significant for historical compatibility.
    assert legacy.approval_id != changed_execution.approval_id
    payload = legacy.to_json_dict(include_indices=True)
    assert payload["approval_identity_semantics"] == (
        "worker_backend_neutral_scientific_plan_v1"
    )
    restored = type(legacy).from_json_dict(payload)
    assert restored.schema_version == "mdstats.density-scene-plan.v2"
    assert restored.approval_id == legacy.approval_id
