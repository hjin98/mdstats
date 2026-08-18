from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAR0 = ROOT / "release" / "par_dens0_na_lta_qualification.json"
PAR3 = ROOT / "release" / "par_dens3_na_lta_qualification.json"


def test_par_dens3_na_lta_qualification_is_bound_to_reference_and_invariant() -> None:
    par0 = json.loads(PAR0.read_text(encoding="utf-8"))
    par3 = json.loads(PAR3.read_text(encoding="utf-8"))
    assert par3["package_version"] == "0.20.142a0"
    assert par3["input"]["sha256"] == par0["input"]["sha256"]
    assert par3["input"]["full_frames"] == par0["input"]["frames"] == 10001
    q = par3["bounded_parallel_qualification"]
    assert q["worker_counts"] == [1, 4]
    assert q["maximum_concurrent_tasks"][0] == 1
    assert q["maximum_concurrent_tasks"][1] >= 3
    assert q["scientific_approval_id_equal"] is True
    assert q["execution_plan_id_equal"] is False
    assert q["scene_plan_schema"] == "mdstats.density-scene-plan.v3"
    assert all(value == 0.0 for value in q["max_absolute_density_difference_by_field"].values())
    assert all(q["content_identity_equal_by_field"].values())
    assert par3["acceptance"]["periodic_support_equal"] is True
    assert par3["acceptance"]["meshes_equal"] is True
