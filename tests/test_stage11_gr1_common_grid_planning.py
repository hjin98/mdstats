"""Stage 11E-GR1 scientific planner, ladder, reuse, and backend tests."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis.density import (
    DensityBackendCandidatePlan,
    DensityBackendSelectionPlan,
    DensityFieldReuseKey,
    DensityGridPlanStatus,
    DensityLogicalGridPlan,
    DensityNestedGridLadder,
    DensityNumericalInputError,
    DensityNumericalResourceError,
    DensityNumericalSerializationError,
    ScientificDensityResourcePolicy,
    density_logical_grid_signature,
    plan_deterministic_density_grid_ladder,
    plan_finest_feasible_density_grid,
    prepare_density_grid_geometry,
    require_identical_density_field_reuse,
    select_density_backend_after_grid,
)
from mdstats.plotting.atomic_density import _finest_budgeted_grid_shape
from mdstats.plotting.graph_errors import GraphComplexityError

ROOT = Path(__file__).resolve().parents[1]
PLANNING_MODULE = ROOT / "mdstats" / "analysis" / "density" / "planning.py"


def skew_cell() -> np.ndarray:
    return np.asarray(
        [[9.2, 0.0, 0.0], [3.4, 8.1, 0.0], [2.3, 1.7, 7.6]],
        dtype=np.float64,
    )


def policy(max_voxels: int) -> ScientificDensityResourcePolicy:
    return ScientificDensityResourcePolicy(
        max_fields=8,
        max_total_voxels=max_voxels,
        max_samples=100_000,
        max_nonzero_nodes=max_voxels,
        max_stored_block_values=max_voxels,
        max_blocks=max_voxels,
        max_kernel_pairs=10_000_000,
        max_planning_bytes=64 * 1024**2,
        max_workspace_bytes=64 * 1024**2,
        max_cic_contributions=10_000_000,
        max_memory_bytes=128 * 1024**2,
        max_threads=2,
        max_wall_time_seconds=60.0,
        metadata={"test_policy": True},
    )


def test_target_grid_plan_retains_requested_and_realized_intervals() -> None:
    plan = plan_finest_feasible_density_grid(
        skew_cell(),
        target_interval=0.45,
        coarsest_interval=0.90,
        resource_policy=policy(1_000_000),
        metadata={"case": "target"},
    )
    assert plan.status is DensityGridPlanStatus.TARGET_REACHED
    assert plan.target_reached
    assert not plan.budget_limited
    assert plan.selected_geometry.grid_shape == plan.target_geometry.grid_shape
    assert plan.target_geometry.requested_grid_interval == 0.45
    assert max(plan.target_geometry.realized_intervals) <= 0.45
    assert plan.scientific_resource_signature == policy(1_000_000).signature
    restored = DensityLogicalGridPlan.from_json_dict(plan.to_json_dict())
    assert restored.to_json_dict() == plan.to_json_dict()


def test_budget_limited_plan_matches_plotting_oracle_adapter() -> None:
    cell = skew_cell()
    target = prepare_density_grid_geometry(cell, grid_interval=0.18)
    coarse = prepare_density_grid_geometry(cell, grid_interval=0.72)
    limit = max(coarse.logical_voxel_count, target.logical_voxel_count // 5)
    plan = plan_finest_feasible_density_grid(
        cell,
        target_interval=0.18,
        coarsest_interval=0.72,
        max_logical_voxels=limit,
    )
    plotting_shape, plotting_limited = _finest_budgeted_grid_shape(
        cell,
        target_interval=0.18,
        nominal_interval=0.72,
        max_voxels=limit,
    )
    assert plan.status is DensityGridPlanStatus.BUDGET_LIMITED
    assert plan.reason_codes == ("unresolved_due_to_resolution_budget",)
    assert plan.selected_geometry.grid_shape == plotting_shape
    assert plotting_limited
    assert plan.selected_geometry.logical_voxel_count <= limit
    assert plan.target_geometry.logical_voxel_count > limit
    assert plan.selected_geometry.requested_grid_interval is not None


def test_zero_target_interval_selects_the_finest_budgeted_grid() -> None:
    cell = skew_cell()
    limit = 30_000
    plan = plan_finest_feasible_density_grid(
        cell,
        target_interval=0.0,
        coarsest_interval=0.72,
        max_logical_voxels=limit,
        metadata={"case": "unbounded_target"},
    )
    plotting_shape, plotting_limited = _finest_budgeted_grid_shape(
        cell,
        target_interval=0.0,
        nominal_interval=0.72,
        max_voxels=limit,
    )
    assert plan.status is DensityGridPlanStatus.BUDGET_LIMITED
    assert plan.selected_geometry.grid_shape == plotting_shape
    assert plan.selected_geometry.logical_voxel_count <= limit
    assert plan.target_geometry.logical_voxel_count > limit
    assert plan.target_geometry.metadata["requested_target_interval"] == 0.0
    assert plotting_limited


def test_finest_plan_fails_when_even_coarsest_grid_is_infeasible() -> None:
    cell = skew_cell()
    coarse = prepare_density_grid_geometry(cell, grid_interval=0.8)
    with pytest.raises(DensityNumericalResourceError, match="coarsest density grid"):
        plan_finest_feasible_density_grid(
            cell,
            target_interval=0.2,
            coarsest_interval=0.8,
            max_logical_voxels=coarse.logical_voxel_count - 1,
        )
    with pytest.raises(GraphComplexityError, match="coarsest density grid"):
        _finest_budgeted_grid_shape(
            cell,
            target_interval=0.2,
            nominal_interval=0.8,
            max_voxels=coarse.logical_voxel_count - 1,
        )


def test_nested_ladder_is_exactly_factor_two_and_deterministic() -> None:
    kwargs = dict(
        coarsest_interval=1.2,
        finest_interval=0.20,
        refinement_factor=2,
        max_levels=8,
        max_logical_voxels=10_000_000,
    )
    first = plan_deterministic_density_grid_ladder(skew_cell(), **kwargs)
    second = plan_deterministic_density_grid_ladder(skew_cell(), **kwargs)
    assert first.status is DensityGridPlanStatus.TARGET_REACHED
    assert first.signature == second.signature
    assert first.to_json_dict() == second.to_json_dict()
    for coarse, fine in zip(first.levels[:-1], first.levels[1:], strict=True):
        assert fine.grid_shape == tuple(2 * item for item in coarse.grid_shape)
        assert fine.logical_voxel_count == 8 * coarse.logical_voxel_count
    assert max(first.finest_feasible_geometry.realized_intervals) <= 0.20
    restored = DensityNestedGridLadder.from_json_dict(first.to_json_dict())
    assert restored.to_json_dict() == first.to_json_dict()


def test_nested_ladder_budget_limit_is_signed_and_not_promoted() -> None:
    base = plan_deterministic_density_grid_ladder(
        skew_cell(),
        coarsest_interval=1.2,
        finest_interval=0.2,
        max_levels=8,
        max_logical_voxels=10_000_000,
    )
    assert len(base.levels) >= 3
    limit = base.levels[-2].logical_voxel_count
    limited = plan_deterministic_density_grid_ladder(
        skew_cell(),
        coarsest_interval=1.2,
        finest_interval=0.2,
        max_levels=8,
        max_logical_voxels=limit,
    )
    assert limited.status is DensityGridPlanStatus.BUDGET_LIMITED
    assert limited.budget_limited
    assert not limited.target_reached
    assert limited.reason_codes == ("unresolved_due_to_resolution_budget",)
    assert limited.finest_feasible_geometry.logical_voxel_count <= limit
    assert limited.requested_finest_geometry.logical_voxel_count > limit


def test_nested_ladder_depth_limit_is_distinct_from_budget_limit() -> None:
    limited = plan_deterministic_density_grid_ladder(
        skew_cell(),
        coarsest_interval=1.2,
        finest_interval=0.05,
        max_levels=2,
        max_logical_voxels=100_000_000,
    )
    assert limited.status is DensityGridPlanStatus.LEVEL_LIMITED
    assert not limited.budget_limited
    assert limited.reason_codes == ("unresolved_due_to_ladder_depth",)


def test_field_reuse_key_is_backend_independent_and_fails_closed() -> None:
    geometry = prepare_density_grid_geometry(skew_cell(), grid_interval=0.5)
    common = dict(
        field_kind="species_number_density",
        source_signature="source-a",
        sample_selection_signature="frames-0-99:Na",
        weight_signature="uniform-frame-weights",
        fixed_kernel_signature="gaussian-covariance-a",
        logical_grid_signature=density_logical_grid_signature(geometry),
        normalization_signature="unit-integral-number-density",
    )
    dense = DensityFieldReuseKey(**common, metadata={"backend": "dense"})
    sparse = DensityFieldReuseKey(
        **common, metadata={"backend": "local_sparse", "cache_hit": True}
    )
    assert dense.signature == sparse.signature
    assert dense.cache_key == sparse.cache_key
    require_identical_density_field_reuse(dense, sparse)
    changed = DensityFieldReuseKey(
        **{**common, "weight_signature": "biased-frame-weights"}
    )
    with pytest.raises(DensityNumericalInputError, match="weight_signature"):
        require_identical_density_field_reuse(dense, changed)
    restored = DensityFieldReuseKey.from_json_dict(dense.to_json_dict())
    assert restored.signature == dense.signature


def test_backend_selection_occurs_after_grid_and_kernel_freeze() -> None:
    plan = plan_finest_feasible_density_grid(
        skew_cell(),
        target_interval=0.4,
        coarsest_interval=0.8,
        max_logical_voxels=1_000_000,
    )
    grid_sig = plan.logical_grid_signature
    dense = DensityBackendCandidatePlan(
        backend="dense",
        logical_grid_signature=grid_sig,
        fixed_kernel_signature="kernel-a",
        feasible=True,
        estimated_storage_values=plan.selected_geometry.logical_voxel_count,
        estimated_workspace_bytes=8_000_000,
        estimated_work=15.0,
    )
    sparse = DensityBackendCandidatePlan(
        backend="local_sparse",
        logical_grid_signature=grid_sig,
        fixed_kernel_signature="kernel-a",
        feasible=True,
        estimated_storage_values=10_000,
        estimated_workspace_bytes=2_000_000,
        estimated_work=4.0,
    )
    selected = select_density_backend_after_grid(
        plan,
        fixed_kernel_signature="kernel-a",
        candidates=(dense, sparse),
    )
    assert selected.selected_backend == "local_sparse"
    assert selected.logical_grid_signature == plan.logical_grid_signature
    assert selected.logical_grid_plan_signature == plan.signature
    restored = DensityBackendSelectionPlan.from_json_dict(selected.to_json_dict())
    assert restored.to_json_dict() == selected.to_json_dict()


def test_backend_candidate_cannot_change_grid_or_kernel() -> None:
    plan = plan_finest_feasible_density_grid(
        skew_cell(),
        target_interval=0.4,
        coarsest_interval=0.8,
        max_logical_voxels=1_000_000,
    )
    wrong_grid = DensityBackendCandidatePlan(
        backend="dense",
        logical_grid_signature="different-grid",
        fixed_kernel_signature="kernel-a",
        feasible=True,
        estimated_storage_values=1,
        estimated_workspace_bytes=1,
        estimated_work=1.0,
    )
    with pytest.raises(DensityNumericalInputError, match="preserve the frozen logical grid"):
        select_density_backend_after_grid(
            plan,
            fixed_kernel_signature="kernel-a",
            candidates=(wrong_grid,),
        )
    wrong_kernel = DensityBackendCandidatePlan(
        backend="dense",
        logical_grid_signature=plan.logical_grid_signature,
        fixed_kernel_signature="kernel-b",
        feasible=True,
        estimated_storage_values=1,
        estimated_workspace_bytes=1,
        estimated_work=1.0,
    )
    with pytest.raises(DensityNumericalInputError, match="preserve the fixed kernel"):
        select_density_backend_after_grid(
            plan,
            fixed_kernel_signature="kernel-a",
            candidates=(wrong_kernel,),
        )


def test_forced_infeasible_backend_fails_without_grid_replanning() -> None:
    plan = plan_finest_feasible_density_grid(
        skew_cell(),
        target_interval=0.4,
        coarsest_interval=0.8,
        max_logical_voxels=1_000_000,
    )
    dense = DensityBackendCandidatePlan(
        backend="dense",
        logical_grid_signature=plan.logical_grid_signature,
        fixed_kernel_signature="kernel-a",
        feasible=False,
        estimated_storage_values=plan.selected_geometry.logical_voxel_count,
        estimated_workspace_bytes=100_000_000,
        estimated_work=10.0,
        reason_codes=("workspace_limit",),
    )
    sparse = DensityBackendCandidatePlan(
        backend="local_sparse",
        logical_grid_signature=plan.logical_grid_signature,
        fixed_kernel_signature="kernel-a",
        feasible=True,
        estimated_storage_values=1_000,
        estimated_workspace_bytes=1_000_000,
        estimated_work=3.0,
    )
    with pytest.raises(DensityNumericalResourceError, match="unavailable or infeasible"):
        select_density_backend_after_grid(
            plan,
            fixed_kernel_signature="kernel-a",
            candidates=(dense, sparse),
            requested_backend="dense",
        )
    assert plan.target_reached


def test_serialized_signature_tampering_is_rejected() -> None:
    plan = plan_finest_feasible_density_grid(
        skew_cell(),
        target_interval=0.4,
        coarsest_interval=0.8,
        max_logical_voxels=1_000_000,
    )
    payload = plan.to_json_dict()
    payload["metadata"] = {"tampered": True}
    with pytest.raises(DensityNumericalSerializationError, match="signature mismatch"):
        DensityLogicalGridPlan.from_json_dict(payload)


def test_planner_imports_no_rendering_or_graph_policy() -> None:
    tree = ast.parse(PLANNING_MODULE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    lowered = "\n".join(imported).lower()
    for forbidden in (
        "plotly",
        "graph_errors",
        "mesh",
        "browser",
        "scene_budget",
        "render_budget",
    ):
        assert forbidden not in lowered
    with pytest.raises(TypeError, match="ScientificDensityResourcePolicy"):
        plan_finest_feasible_density_grid(
            skew_cell(),
            target_interval=0.4,
            coarsest_interval=0.8,
            resource_policy=object(),  # type: ignore[arg-type]
        )
