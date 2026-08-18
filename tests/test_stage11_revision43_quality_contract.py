from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "trajectory_temperature_quality_spec.md"
STATUS = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_status_history.md"


def test_revision43_temperature_and_quality_contract() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture revision 48" in text
    assert "Revision 43 planning update" in STATUS.read_text(encoding="utf-8")
    assert r"T_t=\frac{2K_{\mathrm{ion}}(t)}{f_{\mathrm{ion}}k_{\mathrm B}}" in text
    assert "IonicTemperatureDefinition" in text
    assert "IonicTemperatureStatistics" in text
    assert "NumericalMDQualityControls" in text
    assert "strictly_qualified" in text
    assert "degraded_quality" in text
    assert "unqualified" in text
    assert "TrajectoryDegradedQualityWarning" in text
    assert "TrajectoryIntegrityError" in text
    assert "only `unqualified` blocks scientific execution" in text
    assert "quality verdict controls execution rejection only" in text


def test_revision43_spec_exists_and_is_nonempty() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert len(text) > 2_000
    assert "User `SYSTEM` text has no scientific authority" in text
    assert "Analysis proceeds" in text
