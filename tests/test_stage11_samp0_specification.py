from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "io" / "sampling_crossfit_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
README = ROOT / "README.md"


def test_samp0_specification_names_normative_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Stage 11E-SAMP0",
        "EvidenceCrossfitPartition",
        "CompleteSystemBlock",
        "SamplingAdequacyPolicy",
        "FeatureCorrespondencePolicy",
        "stage11_feature_correspondence_v1",
        "discovery",
        "model_selection",
        "basin_validation",
        "corridor_validation",
        "thermodynamic_estimation",
        "thermodynamic_validation",
        "final_refit",
        "complete-system effective",
    ):
        assert token in text


def test_architecture_marks_samp0_implemented_and_advances_to_gr0() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Architecture revision 57" in text
    assert "implemented in `0.20.22a0`" in text
    assert "The following runtime stage is Stage" in text
    assert "11E-GR0" in text
    assert "Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage" in README.read_text(
        encoding="utf-8"
    )


def test_samp0_public_api_exports() -> None:
    assert callable(mdstats.build_evidence_crossfit_partition)
    assert "EvidenceCrossfitPartition" in mdstats.__all__
    assert "SamplingAdequacyPolicy" in mdstats.__all__
    assert "FeatureCorrespondencePolicy" in mdstats.__all__
