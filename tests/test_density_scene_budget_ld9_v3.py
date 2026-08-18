"""LD9-V3 scene-wide allocation and hard export budget tests."""

from __future__ import annotations

import pytest

from mdstats import (
    BrowserMeshBudget,
    BrowserMeshBudgetFailure,
    BrowserMeshTraceUsage,
    BrowserMeshUsage,
    DensitySceneAllocationOptions,
    DensitySceneShellRequest,
    allocate_density_scene_budget,
    require_browser_mesh_budget,
)


def _requests() -> tuple[DensitySceneShellRequest, ...]:
    return tuple(
        DensitySceneShellRequest(
            shell_key=f"field-{index}:{fraction}",
            field_key=f"field-{index // 3}",
            label=f"field {index // 3}",
            mass_fraction=fraction,
            selected_node_count=(index + 1) * 10_000,
            display_replication=(2 if index == 5 else 1),
            visual_importance=(1.0, 0.72, 0.48)[index % 3],
            max_canonical_faces=100_000,
        )
        for index, fraction in enumerate((0.5, 0.8, 0.95, 0.5, 0.8, 0.95))
    )


def test_scene_allocation_never_exceeds_post_replication_budget() -> None:
    budget = BrowserMeshBudget(max_final_density_faces=100_000)
    plan = allocate_density_scene_budget(
        _requests(),
        budget=budget,
        options=DensitySceneAllocationOptions(min_canonical_faces_per_shell=2_000),
    )
    assert plan.allocated_serialized_faces <= 100_000
    assert plan.unallocated_serialized_faces >= 0
    assert sum(item.target_serialized_faces for item in plan.allocations) == plan.allocated_serialized_faces
    replicated = plan.allocation_for("field-5:0.95")
    assert replicated.target_serialized_faces == 2 * replicated.target_canonical_faces


def test_scene_allocation_is_deterministic() -> None:
    first = allocate_density_scene_budget(_requests())
    second = allocate_density_scene_budget(tuple(reversed(_requests())))
    first_map = {item.shell_key: item.target_canonical_faces for item in first.allocations}
    second_map = {item.shell_key: item.target_canonical_faces for item in second.allocations}
    assert first_map == second_map


def test_minimum_reserve_failure_is_structured() -> None:
    with pytest.raises(Exception, match="minimum face reserve"):
        allocate_density_scene_budget(
            _requests(),
            budget=BrowserMeshBudget(max_final_density_faces=10_000),
            options=DensitySceneAllocationOptions(min_canonical_faces_per_shell=4_000),
        )


def test_plotly_trace_budget_counts_replication() -> None:
    usage = BrowserMeshUsage(
        density_traces=(
            BrowserMeshTraceUsage(
                trace_key="shell",
                face_count=1_000,
                vertex_count=600,
                display_replication=4,
            ),
        ),
        non_density_trace_count=61,
    )
    with pytest.raises(BrowserMeshBudgetFailure, match="plotly_traces=65>64"):
        require_browser_mesh_budget(usage)
