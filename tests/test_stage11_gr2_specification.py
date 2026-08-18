from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "plotting_grid_adaptation_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
STATUS = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_status_history.md"
README = ROOT / "README.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "stage11_dependency_graph.json"


def test_gr2_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-GR2",
        "DensityVisualGridAdaptation",
        "DensityGridGeometry",
        "DensityLogicalGridPlan",
        "selected_visual_grid_replay",
        "explicit_shape",
        "target_lattice_interval",
        "GraphComplexityError",
        "not a scientific convergence certificate",
        "Stage 11E-GR3",
    ):
        assert token in text


def test_gr2_public_api_exports() -> None:
    assert callable(mdstats.prepare_density_visual_grid_adaptation)
    assert "DensityVisualGridAdaptation" in mdstats.__all__
    assert "DENSITY_VISUAL_GRID_ADAPTATION_SCHEMA" in mdstats.__all__
    assert "DENSITY_VISUAL_POLICY_ID" in mdstats.__all__


def test_architecture_marks_gr2_implemented_and_advances_to_gr3() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    graph = GRAPH.read_text(encoding="utf-8")
    assert "Architecture revision 57" in manual
    assert "implemented in `0.20.25a0`" in manual
    assert "plotting_grid_adaptation_spec.md" in manual
    assert "## 0.20.25a0 - Stage 11E-GR2" in status
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in readme
    assert '"architecture_revision": 57' in graph
