from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "common_grid_planning_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
README = ROOT / "README.md"


def test_gr1_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-GR1",
        "DensityLogicalGridPlan",
        "DensityNestedGridLadder",
        "DensityFieldReuseKey",
        "DensityBackendCandidatePlan",
        "DensityBackendSelectionPlan",
        "unresolved_due_to_resolution_budget",
        "physical-resolution-first/backend-second",
        "target_interval=0",
        "Stage 11E-GR2",
    ):
        assert token in text


def test_gr1_public_api_exports() -> None:
    assert callable(mdstats.plan_finest_feasible_density_grid)
    assert callable(mdstats.plan_deterministic_density_grid_ladder)
    assert callable(mdstats.select_density_backend_after_grid)
    assert "DensityLogicalGridPlan" in mdstats.__all__
    assert "DensityFieldReuseKey" in mdstats.__all__


def test_architecture_marks_gr1_implemented_and_advances_to_gr2() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Architecture revision 57" in text
    assert "implemented in `0.20.24a0`" in text
    assert "common_grid_planning_spec.md" in text
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in README.read_text(
        encoding="utf-8"
    )
