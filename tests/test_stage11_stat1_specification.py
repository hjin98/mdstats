from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "io" / "production_regime_catalog_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"


def test_stat1_specification_exists_and_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-STAT1",
        "ProductionWindowPolicy",
        "QualityDiagnosticBlockPartition",
        "ProductionRegimeCatalog",
        "source-observable",
        "selection_conditioned",
        "1 meV",
        "26 meV",
    ):
        assert token in text


def test_architecture_marks_stat1_implemented() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "11E-STAT1" in text
    assert "implemented in `0.20.20a0`" in text
    assert "Stage 11E-STAT2" in text


def test_stat1_public_api_exports() -> None:
    assert callable(mdstats.assess_production_regimes)
    assert callable(mdstats.assess_vasp_production_regimes)
    assert "ProductionWindowPolicy" in mdstats.__all__
