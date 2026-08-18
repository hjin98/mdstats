from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "io" / "ensemble_admissibility_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"


def test_stat2_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-STAT2",
        "PmfAdmissibilityCertificate",
        "EvidenceAdmissibilityOverlay",
        "microcanonical",
        "canonical",
        "Gibbs",
        "ReweightingProvenance",
        "EnsembleApproximationProvenance",
        "pmf_force_mask",
        "not_evaluated_for_subselected_source_segment",
    ):
        assert token in text


def test_architecture_retains_stat2_implementation_in_revision52() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Architecture revision 57" in text
    assert "implemented in `0.20.21a0`" in text
    assert "Stage 11E-SAMP0" in text
    assert "implemented in `0.20.22a0`" in text


def test_stat2_public_api_exports() -> None:
    assert callable(mdstats.assess_pmf_admissibility)
    assert callable(mdstats.assess_vasp_pmf_admissibility)
    assert callable(mdstats.prepare_evidence_admissibility_overlay)
    assert "PmfAdmissibilityCertificate" in mdstats.__all__
