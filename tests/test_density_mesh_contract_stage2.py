"""Stage 2 face-contract tests for density mesh preparation."""

from __future__ import annotations

import json

import numpy as np
import pytest

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    DensityMeshFaceContract,
    DensityRenderOptions,
    evaluate_density_mesh_face_contract,
    DensitySourceProvenance,
    PeriodicBlockScalarField3D,
    PeriodicWeightedSamples3D,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_reference,
    prepare_sparse_density_mesh,
)
from mdstats.plotting.atomic_density import PeriodicScalarField3D, density_mesh_arrays
from mdstats.plotting.graph_errors import GraphComplexityError, GraphStyleError


def _sparse_field() -> PeriodicBlockScalarField3D:
    positions = np.asarray([[0.43, 0.48, 0.54]], dtype=np.float64)
    samples = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.ones(1, dtype=np.float64),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy",
            atom_indices=(0,),
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        samples,
        grid_shape=(24, 24, 24),
        display_cell=np.eye(3, dtype=np.float64) * 6.0,
        gaussian_bandwidth=0.35,
        field_key="stage2-density",
        label="stage2 density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=(8, 8, 8),
        max_stored_block_values=5_000_000,
        max_planning_bytes=500_000_000,
    )


def _dense_field(field: PeriodicBlockScalarField3D) -> PeriodicScalarField3D:
    return PeriodicScalarField3D(
        field_key=field.field_key,
        label=field.label,
        values=field.to_dense_values(max_nodes=1_000_000),
        display_cell=field.display_cell,
        total_measure=field.total_measure,
        selected_atom_indices=(0,),
        gaussian_bandwidth=field.gaussian_bandwidth,
        source_provenance=field.source_provenance,
        metadata=field.metadata,
    )


def test_face_contract_round_trip_and_mode_invariants() -> None:
    contract = DensityMeshFaceContract.scene_controller(
        raw_extraction_face_limit=500_000,
        visual_target_faces=25_000,
        metadata={"shell_key": "atomic:Na:0.5"},
    )
    restored = DensityMeshFaceContract.from_json_dict(
        json.loads(json.dumps(contract.to_json_dict()))
    )
    assert restored == contract
    assert restored.mode == "scene_controller"
    assert restored.standalone_final_face_limit is None
    with pytest.raises(GraphStyleError, match="requires standalone_final_face_limit=None"):
        DensityMeshFaceContract(
            raw_extraction_face_limit=500_000,
            visual_target_faces=25_000,
            standalone_final_face_limit=250_000,
            mode="scene_controller",
        )


def test_render_options_migrate_legacy_max_mesh_faces() -> None:
    legacy = DensityRenderOptions(max_mesh_faces=1234)
    assert legacy.standalone_final_mesh_faces == 1234
    assert legacy.max_mesh_faces == 1234
    payload = legacy.to_json_dict()
    assert payload["standalone_final_mesh_faces"] == 1234
    assert payload["max_mesh_faces"] == 1234
    restored = DensityRenderOptions.from_json_dict(payload)
    assert restored == legacy

    old_payload = dict(payload)
    old_payload.pop("standalone_final_mesh_faces")
    migrated = DensityRenderOptions.from_json_dict(old_payload)
    assert migrated.standalone_final_mesh_faces == 1234



def test_reported_582375_face_shell_becomes_scene_refit_debt() -> None:
    report = evaluate_density_mesh_face_contract(
        582_375,
        DensityMeshFaceContract.scene_controller(
            raw_extraction_face_limit=1_000_000,
            visual_target_faces=250_000,
        ),
    )
    assert report.visual_target_met is False
    assert report.visual_target_overage_faces == 332_375
    assert report.requires_scene_refit is True
    assert report.standalone_final_limit_met is None
    restored = type(report).from_json_dict(
        json.loads(json.dumps(report.to_json_dict()))
    )
    assert restored == report


def test_sparse_scene_target_miss_is_reported_not_rejected() -> None:
    field = _sparse_field()
    target = 4
    surface = prepare_sparse_density_mesh(
        field,
        0.8,
        face_contract=DensityMeshFaceContract.scene_controller(
            raw_extraction_face_limit=500_000,
            visual_target_faces=target,
        ),
        max_raw_vertices=1_500_000,
        max_workspace_bytes=500_000_000,
    )
    assert surface.mesh is not None
    assert surface.mesh.faces.shape[0] > target
    assert surface.mesh.metadata["visual_target_met"] is False
    assert surface.mesh.metadata["visual_target_overage_faces"] == (
        surface.mesh.faces.shape[0] - target
    )
    contract_payload = surface.mesh.metadata["mesh_face_contract"]
    assert contract_payload["mode"] == "scene_controller"
    assert contract_payload["standalone_final_face_limit"] is None


def test_sparse_standalone_final_limit_remains_hard() -> None:
    field = _sparse_field()
    with pytest.raises(GraphComplexityError, match=r"max_mesh_faces=4"):
        prepare_sparse_density_mesh(
            field,
            0.8,
            face_contract=DensityMeshFaceContract.standalone(
                final_face_limit=4,
                raw_extraction_face_limit=500_000,
            ),
            max_raw_vertices=1_500_000,
            max_workspace_bytes=500_000_000,
        )


def test_dense_scene_target_miss_is_not_a_terminal_limit() -> None:
    field = _dense_field(_sparse_field())
    vertices, faces, _level = density_mesh_arrays(
        field,
        0.8,
        face_contract=DensityMeshFaceContract.scene_controller(
            raw_extraction_face_limit=500_000,
            visual_target_faces=4,
        ),
    )
    assert vertices.shape[0] > 0
    assert faces.shape[0] > 4


def test_dense_standalone_final_limit_remains_hard() -> None:
    field = _dense_field(_sparse_field())
    with pytest.raises(
        GraphComplexityError,
        match=r"standalone_final_face_limit=4",
    ):
        density_mesh_arrays(
            field,
            0.8,
            face_contract=DensityMeshFaceContract.standalone(
                final_face_limit=4,
                raw_extraction_face_limit=500_000,
            ),
        )


def test_runtime_raw_limit_remains_authoritative() -> None:
    requested = DensityMeshFaceContract.scene_controller(
        raw_extraction_face_limit=900_000,
        visual_target_faces=20_000,
    )
    resolved = requested.resolve_raw_limit(300_000)
    assert resolved.raw_extraction_face_limit == 300_000
    assert resolved.visual_target_faces == 20_000
    assert resolved.standalone_final_face_limit is None


def test_framework_renderer_uses_scene_controller_contract() -> None:
    import importlib.util
    from pathlib import Path

    pytest.importorskip("plotly")
    from mdstats import (
        AtomicDensityOptions,
        AtomicDensitySelection,
        DensityKernelOptions,
        DensityStorageOptions,
        DISCRETE_PERIODIZED_OPERATOR,
        plot_framework_dynamics_3d,
        prepare_framework_dynamics_scene,
    )

    helper_path = Path(__file__).parent / "test_density_block_sparse.py"
    spec = importlib.util.spec_from_file_location("stage2_sparse_helper", helper_path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    collection = helper.make_collection()
    scene = prepare_framework_dynamics_scene(
        collection,
        helper.framework_topology(collection),
        atomic_density_selections=(AtomicDensitySelection(atom_indices=(3,)),),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(64, 64, 64),
            gaussian_bandwidth=0.0,
            adaptive_smearing=False,
            kernel_options=DensityKernelOptions(
                smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
            ),
            storage_options=DensityStorageOptions(
                grid_backend="local_sparse",
                local_block_shape=(8, 8, 8),
            ),
        ),
    )
    result = plot_framework_dynamics_3d(scene)
    plan = result.render_metadata["density_scene_budget_plan"]
    assert plan["requests"][0]["max_canonical_faces"] == (
        scene.resources.max_density_mesh_faces
    )
    records = result.render_metadata["density_meshes"]["atomic-density-0"]
    assert records
    for record in records:
        contract = record["mesh_face_contract"]
        report = record["mesh_face_report"]
        assert contract["mode"] == "scene_controller"
        assert contract["standalone_final_face_limit"] is None
        assert report["contract"] == contract
