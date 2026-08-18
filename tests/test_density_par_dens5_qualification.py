from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUAL = ROOT / "release" / "par_dens5_na_lta_qualification.json"


def test_par_dens5_na_lta_qualification_is_bound_and_fail_safe() -> None:
    data = json.loads(QUAL.read_text(encoding="utf-8"))
    assert data["schema"] == "mdstats.par-dens5-na-lta-qualification.v1"
    assert data["package_version"] == "0.20.144a0"
    assert data["input"]["sha256"] == "81c86cc40f5a11031f80817213eb558c02348494d1c6cad9b4775a5bc3c9f9cd"
    run = data["bounded_gpu_fallback_qualification"]
    assert run["selected_frames"] == 101
    assert run["max_absolute_density_difference_by_field"] == {"Na": 0.0, "Si": 0.0, "O": 0.0}
    assert all(run["content_identity_equal_by_field"].values())
    assert run["hdr_thresholds_equal"] is True
    assert run["gpu_reports"]["off"]["reason_counts"] == {"gpu_disabled": 327}
    assert run["gpu_reports"]["auto"]["reason_counts"] == {"cuda_unavailable": 327}
    policy = data["gpu_policy"]
    assert policy["usable_vram_fraction"] == 0.8
    assert policy["scientific_precision"] == "fp64_only"
    assert policy["automatic_cpu_fallback"] is True
    assert data["acceptance"]["gpu_speedup_claimed"] is False
    assert data["interpretation"]["par_dens6_next"] is True
