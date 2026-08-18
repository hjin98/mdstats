from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data2_source_catalog_spec.md"
SPEC_PDF = ROOT / "docs" / "specs" / "training_data" / "mlff_data2_source_catalog_spec.pdf"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
STAGE = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md"


def test_data2_spec_declares_runtime_boundary_and_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "MLFF-DATA2",
        "TrainingDataSourceCatalog",
        "VaspEnergyLabelPolicy",
        "TheoryIdentity",
        "EnergyReferenceIdentity",
        "DerivativeConvention",
        "NumericalQualityProfile",
        "SoftwareProvenance",
        "LabelDomainCatalog",
        "AtomicReferenceIdentifiabilityCatalog",
        "AtomicReferenceIdentifiabilityReport",
        "No energy values enter the structural rank audit",
        "one target label domain per initial MACE bundle",
    ):
        assert token in text


def test_data2_status_and_public_exports() -> None:
    assert "MLFF-DATA2 is implemented in `0.20.30a0`" in ARCH.read_text(encoding="utf-8")
    assert "## MLFF-DATA2 - implemented in 0.20.30a0" in STAGE.read_text(encoding="utf-8")
    assert callable(mdstats.build_training_data_source_catalog)
    assert callable(mdstats.analyze_atomic_reference_identifiability)
    assert SPEC_PDF.stat().st_size > 5_000
