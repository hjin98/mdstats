"""Focused LD8-P0 and LD9-V0 benchmark/calibration contract tests."""

from __future__ import annotations

import numpy as np

from benchmarks.density_ld8_p0_benchmark import _block_profile, _executor_spike
from benchmarks.density_ld9_v0_calibration import calibrate
from mdstats.plotting.density_render_budget import BrowserMeshBudget


class _SyntheticStencil:
    grid_shape = (9, 9, 9)
    active_flat_indices = np.asarray(
        [0, 1, 9, 10, 81, 82, 90, 91], dtype=np.int64
    )
    active_weights = np.full(8, 1.0 / 8.0, dtype=np.float64)


def test_block_profile_accounts_for_packed_and_fixed_storage() -> None:
    flat = np.asarray([0, 1, 7, 8, 9, 63], dtype=np.int64)
    profile = _block_profile(flat, (4, 4, 4), 2)
    assert profile["occupied_node_count"] == flat.size
    assert profile["occupied_block_count"] >= 2
    assert 0.0 < profile["occupied_fraction_within_stored_blocks"] <= 1.0
    assert profile["estimated_packed_positive_bytes"] < (
        profile["estimated_fixed_block_bytes"] + flat.size * 8
    )


def test_executor_spike_preserves_dense_linear_convolution() -> None:
    result = _executor_spike(
        _SyntheticStencil(), tile_edge=4, fill_fraction=0.25, seed=17
    )
    assert result["relative_l1_difference"] < 1.0e-12
    assert result["max_absolute_difference"] < 1.0e-12
    assert result["direct_seconds"] > 0.0
    assert result["fft_seconds"] > 0.0


def test_ld9_calibration_reports_post_replication_budget_failure() -> None:
    summary = {
        "package_version": "0.19.53a0",
        "mesh_trace_count": 12,
        "mesh_face_count": 3_184_902,
        "mesh_vertex_count": 1_599_000,
        "trajectory_atom_count": 168,
        "html_bytes": 186_335_598,
    }
    browser = {"status": "failed", "metrics": {"trace_count": 184}}
    result = calibrate(
        summary,
        browser_validation=browser,
        budget=BrowserMeshBudget(),
    )
    report = result["budget_report"]
    assert not report["passed"]
    assert result["required_reduction"]["faces"] > 10.0
    assert result["required_reduction"]["vertices"] > 7.0
    assert result["required_reduction"]["html_bytes"] > 4.0
    assert any(value.startswith("final_density_faces=") for value in report["violations"])
