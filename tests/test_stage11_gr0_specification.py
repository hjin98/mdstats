from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "analysis" / "density" / "common_grid_diagnostics_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
README = ROOT / "README.md"


def test_gr0_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-GR0",
        "DensityGridGeometry",
        "PeriodicMeanDiagnostic",
        "PeriodicSpreadDiagnostics",
        "ReciprocalResolutionDiagnostic",
        "PeriodicGaussianStencilMoments",
        "ArtificialBroadeningDiagnostic",
        "DensityNumericalResourceError",
        "oblique periodic cell",
        "Stage 11E-GR1",
    ):
        assert token in text


def test_gr0_public_api_exports() -> None:
    assert callable(mdstats.prepare_density_grid_geometry)
    assert "DensityGridGeometry" in mdstats.__all__
    assert "DensityNumericalResourceError" in mdstats.__all__


def test_architecture_marks_gr0_implemented_and_advances_to_gr1() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Architecture revision 57" in text
    assert "implemented in `0.20.23a0`" in text
    assert "Stage 11E-GR1" in text
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in README.read_text(
        encoding="utf-8"
    )
