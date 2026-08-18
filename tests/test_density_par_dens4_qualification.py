from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAR0 = ROOT / "release" / "par_dens0_na_lta_qualification.json"
PAR4 = ROOT / "release" / "par_dens4_na_lta_qualification.json"


def test_par_dens4_na_lta_qualification_is_bound_and_preserves_identity() -> None:
    par0 = json.loads(PAR0.read_text(encoding="utf-8"))
    par4 = json.loads(PAR4.read_text(encoding="utf-8"))
    assert par4["package_version"] == "0.20.143a0"
    assert par4["input"]["sha256"] == par0["input"]["sha256"]
    assert par4["input"]["full_frames"] == par0["input"]["frames"] == 10001
    q = par4["bounded_preprocessing_qualification"]
    assert q["hysteretic_worker_counts"] == [1, 4]
    assert q["frame_state_ids_equal"] is True
    assert q["state_digests_equal"] is True
    assert q["transitions_equal"] is True
    reuse = q["geometry_reuse"]
    assert reuse["cache_hits_after_warm_full"] == 202
    assert reuse["warm_and_cold_full_connectivity_equal"] is True
    assert reuse["warm_vs_cold_full_speedup"] > 1.0
    assert q["framework_scene_schema"] == "mdstats.framework-dynamics-scene.v15"
    assert par4["interpretation"]["par_dens5_next"] is True
