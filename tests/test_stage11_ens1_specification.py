from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/io/vasp_ensemble_certificate_spec.md"
MANUAL = ROOT / "docs/arch_manuals/stage11_site_kinetics_architecture.md"


def test_ens1_specification_is_permanent_and_source_authoritative():
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-ENS1",
        "SimulationControlCertificate",
        "SimulationControlComponent",
        "SimulationControlDecision",
        "SYSTEM",
        "comment",
        "MDALGO = 2",
        "SMASS = -3",
        "fixed-cell NVE",
        "not_applicable",
        "Missing companion evidence is never converted into affirmative absence",
        "force-provider",
        "continuation",
    ):
        assert token in text


def test_stage11_manual_marks_ens1_complete_and_current_progression():
    text = MANUAL.read_text(encoding="utf-8")
    section = text.split("## Stage 11E-ENS1", 1)[1].split("## Stage 11E-STAT0", 1)[0]
    assert "complete in `0.20.18a0`" in section
    assert "vasp_ensemble_certificate_spec.md" in section
    assert "Stages 11E-ENS1 through 11E-STAT2 are now implemented" in text
    assert "11E-SAMP0" in text
