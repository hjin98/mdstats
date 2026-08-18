from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "fixed_kernel_grid_refinement_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
STATUS = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_status_history.md"
README = ROOT / "README.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "stage11_dependency_graph.json"


def test_gr3_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-GR3",
        "ScientificGridRefinementPolicy",
        "GridConvergenceStoppingPolicy",
        "stage11_grid_stopping_v1",
        "stage11_feature_correspondence_v1",
        "DensityFieldResolutionCertificate",
        "BasinGridConvergenceCertificate",
        "CorridorGridConvergenceCertificate",
        "unresolved_due_to_resolution_budget",
        "unresolved_due_to_refinement_limit",
        "two consecutive",
        "Stage 11E-GR4",
    ):
        assert token in text


def test_gr3_public_api_exports() -> None:
    assert callable(mdstats.plan_scientific_grid_refinement)
    assert callable(mdstats.certify_density_field_resolution)
    assert callable(mdstats.certify_basin_grid_convergence)
    assert callable(mdstats.certify_corridor_grid_convergence)
    assert callable(mdstats.prepare_scientific_grid_refinement_bundle)
    assert "ScientificGridRefinementPolicy" in mdstats.__all__
    assert "ScientificGridRefinementBundle" in mdstats.__all__
    assert mdstats.GridConvergenceStoppingPolicy().policy_version == "stage11_grid_stopping_v1"


def test_architecture_marks_gr3_implemented_and_advances_to_gr4() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    graph = GRAPH.read_text(encoding="utf-8")
    assert "Architecture revision 57" in manual
    assert "implemented in `0.20.26a0`" in manual
    assert "fixed_kernel_grid_refinement_spec.md" in manual
    assert "## 0.20.26a0 - Stage 11E-GR3" in status
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in readme
    assert '"architecture_revision": 57' in graph
