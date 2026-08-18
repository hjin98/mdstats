from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUAL = ROOT / "release" / "par_dens0_na_lta_qualification.json"


def test_par_dens0_real_na_lta_qualification_is_release_bound() -> None:
    payload = json.loads(QUAL.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.par-dens0-na-lta-qualification.v1"
    assert payload["package_version"] == "0.20.120a0"
    assert payload["input"]["frames"] == 10001
    assert payload["input"]["na_atoms"] == 24
    results = payload["results_angstrom"]
    assert results["production_512_reference"] == pytest.approx(
        results["basin_aware_all_reference"], rel=0.01
    )
    assert results["two_basin_na_global"] > 2.0 * results["two_basin_na_full_within_basin"]
    assert results["two_basin_na_production_within_basin"] == pytest.approx(0.08, abs=0.01)
    convergence = payload["production_convergence"]
    assert convergence["effective_anchor_samples"] == 512
    assert convergence["relative_anchor_change"] < convergence["converged_at_relative_tolerance"]
    assert convergence["relative_confidence_half_width"] > convergence["relative_anchor_change"]
