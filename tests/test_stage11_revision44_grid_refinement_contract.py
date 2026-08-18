from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
GRID_SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "scientific_grid_refinement_spec.md"
CONSISTENCY = ROOT / "docs" / "specs" / "documentation" / "stage11_revision44_grid_refinement_consistency_spec.md"
INDEX = ROOT / "docs" / "specs" / "analysis" / "density" / "index.md"
STATUS = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_status_history.md"


def test_revision44_partial_refactor_contract() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture revision 48" in text.lower()
    assert "Revision 44 planning update" in STATUS.read_text(encoding="utf-8")
    assert "**partial refactor**" in text
    for stage in range(6):
        assert f"11E-GR{stage}" in text
    assert "ScientificGridRefinementPolicy" in text
    assert "DensityFieldResolutionCertificate" in text
    assert "BasinGridConvergenceCertificate" in text
    assert "CorridorGridConvergenceCertificate" in text
    assert r"\Sigma_h=\text{constant}" in text
    assert "unresolved_due_to_resolution_budget" in text
    assert "plotting's adaptive bandwidth selection" in text
    assert "Grid convergence concerns discretization" in text
    assert "SAMP1/SAMP2" in text


def test_revision44_grid_spec_and_index() -> None:
    spec = GRID_SPEC.read_text(encoding="utf-8")
    assert len(spec) > 7_000
    assert "The selected architecture is a **partial refactor**" in spec
    assert "field numerics: converged" in spec
    assert "transition corridors: unresolved" in spec
    assert "budget-limited unconverged ladder" in spec
    consistency = CONSISTENCY.read_text(encoding="utf-8")
    assert "GR0/GR1" in consistency
    index = INDEX.read_text(encoding="utf-8")
    assert "scientific_grid_refinement_spec.md" in index
