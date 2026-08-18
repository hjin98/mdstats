from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stat0_specification_owns_required_contracts() -> None:
    text = (ROOT / "docs/specs/io/trajectory_quality_spec.md").read_text(encoding="utf-8")
    for token in (
        "**Stage:** 11E-STAT0",
        "strictly_qualified",
        "degraded_quality",
        "unqualified",
        "IonicTemperatureDefinition",
        "IonicTemperatureStatistics",
        "DiagnosticRequirement",
        "hard_integrity_required",
        "verdict_critical",
        "method_specific",
        "optional",
        "RealizedEnsembleConsistency",
        "TrajectoryIntegrityError",
        "TrajectoryDegradedQualityWarning",
        "501 ionic degrees of freedom",
        "-0.205 eV/ps",
    ):
        assert token in text


def test_stat0_architecture_and_readme_progression() -> None:
    manual = (ROOT / "docs/arch_manuals/stage11_site_kinetics_architecture.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "architecture revision 57" in manual
    assert "11E-STAT0 ionic-temperature/integrity/quality evaluation" in manual
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in readme
    assert "Stage 11E-STAT0 is the next implementation stage" not in readme
