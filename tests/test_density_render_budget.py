"""LD9-V0 hard browser-budget contract tests."""

from __future__ import annotations

import pytest

from mdstats.plotting.density_render_budget import (
    BrowserMeshBudget,
    BrowserMeshBudgetFailure,
    BrowserMeshTraceUsage,
    BrowserMeshUsage,
    browser_usage_from_counts,
    evaluate_browser_mesh_budget,
    require_browser_mesh_budget,
)
from mdstats.plotting.graph_errors import GraphStyleError


def test_post_replication_counts_are_hard_scene_totals() -> None:
    usage = BrowserMeshUsage(
        density_traces=(
            BrowserMeshTraceUsage(
                trace_key="Na-50", face_count=20_000, vertex_count=12_000
            ),
            BrowserMeshTraceUsage(
                trace_key="O-95",
                face_count=70_000,
                vertex_count=40_000,
                display_replication=3,
            ),
        ),
        non_density_trace_count=10,
        final_html_bytes=10_000_000,
    )
    assert usage.final_density_face_count == 230_000
    assert usage.final_density_vertex_count == 132_000
    assert usage.plotly_trace_count == 14
    report = evaluate_browser_mesh_budget(usage)
    assert report.passed


def test_hard_budget_raises_before_serialization() -> None:
    usage = browser_usage_from_counts(
        face_counts=(250_000, 100_000),
        vertex_counts=(120_000, 90_000),
        trace_keys=("inner", "outer"),
        non_density_trace_count=63,
        final_html_bytes=50 * 1024**2,
    )
    report = evaluate_browser_mesh_budget(usage)
    assert not report.passed
    assert any(value.startswith("final_density_faces=") for value in report.violations)
    assert any(value.startswith("final_density_vertices=") for value in report.violations)
    assert any(value.startswith("plotly_traces=") for value in report.violations)
    assert any(value.startswith("final_html_bytes=") for value in report.violations)
    with pytest.raises(BrowserMeshBudgetFailure) as error:
        require_browser_mesh_budget(usage)
    assert error.value.report == report
    assert error.value.to_json_dict()["report"]["passed"] is False


def test_interactive_profile_rejects_advisory_or_pre_replication_budget() -> None:
    usage = browser_usage_from_counts(face_counts=(1,), vertex_counts=(3,))
    with pytest.raises(GraphStyleError):
        evaluate_browser_mesh_budget(usage, budget=BrowserMeshBudget(hard_limit=False))
    with pytest.raises(GraphStyleError):
        evaluate_browser_mesh_budget(
            usage,
            budget=BrowserMeshBudget(apply_after_display_replication=False),
        )


def test_raw_reference_profile_allows_explicit_advisory_budget() -> None:
    usage = browser_usage_from_counts(face_counts=(500_000,), vertex_counts=(300_000,))
    report = evaluate_browser_mesh_budget(
        usage,
        budget=BrowserMeshBudget(hard_limit=False),
        profile="raw_reference",
    )
    assert not report.passed
    assert require_browser_mesh_budget(
        usage,
        budget=BrowserMeshBudget(hard_limit=False),
        profile="raw_reference",
    ) == report


def test_browser_budget_records_round_trip_canonical_json() -> None:
    usage = BrowserMeshUsage(
        density_traces=(
            BrowserMeshTraceUsage(
                trace_key="Na-50",
                face_count=1234,
                vertex_count=678,
                display_replication=2,
                retained_array_bytes=4096,
                metadata={"shell": 0.5},
            ),
        ),
        non_density_trace_count=4,
        final_html_bytes=123_456,
        metadata={"scene": "test"},
    )
    report = evaluate_browser_mesh_budget(usage)
    restored = type(report).from_json_dict(report.to_json_dict())
    assert restored == report
    assert restored.to_json_dict() == report.to_json_dict()
