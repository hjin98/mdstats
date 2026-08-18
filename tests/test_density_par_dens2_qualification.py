from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAR0 = ROOT / "release" / "par_dens0_na_lta_qualification.json"
PAR2 = ROOT / "release" / "par_dens2_na_lta_qualification.json"


def test_par_dens2_na_lta_worker_invariance_qualification_is_bound_to_par0_source() -> None:
    par0 = json.loads(PAR0.read_text(encoding="utf-8"))
    par2 = json.loads(PAR2.read_text(encoding="utf-8"))
    assert par2["package_version"] == "0.20.141a0"
    assert par2["input"]["sha256"] == par0["input"]["sha256"]
    assert par2["input"]["full_frames"] == par0["input"]["frames"] == 10001
    smoke = par2["bounded_scheduler_smoke"]
    assert smoke["worker_counts"] == [1, 4]
    assert smoke["max_absolute_density_difference"] == 0.0
    assert smoke["integrated_grid_sum"][0] == smoke["integrated_grid_sum"][1]
    assert smoke["scientific_approval_id_equal"] is True
    assert smoke["scheduler_policy"] == "par_dens2_global_resource_scheduler_v1"
    assert par2["interpretation"]["par_dens3_concurrency_enabled"] is False
