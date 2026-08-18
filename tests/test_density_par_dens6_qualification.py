from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "release/par_dens6_na_lta_qualification.json"


def test_par_dens6_na_lta_qualification_authorizes_cpu_path() -> None:
    data = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    assert data["schema"] == "mdstats.par-dens6-na-lta-qualification.v3"
    assert data["package_version"] == "0.20.145a0"
    assert data["input"]["frames"] == 10001
    assert data["input"]["atoms_per_frame"] == 168
    assert data["basin_aware_spread_evidence"]["same_trajectory_sha256"] is True
    assert [item["selected_frames"] for item in data["three_scale_atomic_density_benchmark"]] == [101, 1001, 10001]

    comparison = data["long_trajectory_scientific_comparison"]
    assert comparison["max_absolute_pointwise_difference"] == {"Na": 0.0, "Si": 0.0, "O": 0.0}
    assert all(comparison["content_identity_equal"].values())
    assert all(comparison["integrals_equal"].values())
    assert all(comparison["hdr_50_80_95_equal"].values())
    assert all(comparison["executor_partition_equal"].values())

    speed = data["long_trajectory_speedup_classification"]
    assert speed["material"] is True
    assert data["long_trajectory_speedup_vs_single_worker_median"] > 1.0
    assert speed["gain_fraction"] >= speed["material_gain_floor"]

    acceptance = data["acceptance"]
    assert acceptance["cpu_budget_obeyed"] is True
    assert acceptance["memory_budget_obeyed"] is True
    assert acceptance["pointwise_reference_equal"] is True
    assert acceptance["content_identity_equal"] is True
    assert acceptance["executor_partition_equal"] is True
    assert acceptance["deterministic_repeat_equal"] is True
    assert acceptance["material_long_trajectory_speedup_observed"] is True
    assert acceptance["production_cpu_path_authorized"] is True


def test_par_dens6_autotune_does_not_change_scientific_operator() -> None:
    data = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    operator = data["scientific_operator"]
    assert operator["grid_shape"] == [64, 64, 64]
    assert operator["gaussian_bandwidth_angstrom"] == 0.5
    assert operator["smoothing_operator"] == "discrete_periodized_v1"
    assert operator["resolution_changed_by_autotune"] is False
    assert operator["operator_identity_changed_by_autotune"] is False
