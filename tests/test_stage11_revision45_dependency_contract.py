from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
SPEC = ROOT / "docs" / "specs" / "documentation" / "stage11_revision45_dependency_force_transition_consistency_spec.md"


def normalized_text() -> str:
    return re.sub(r"\s+", " ", MANUAL.read_text(encoding="utf-8"))


def test_revision45_dependency_and_force_contract() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    flat = normalized_text()
    assert "architecture revision 48" in text
    assert "Revision-47 authoritative typed dependency graph" in text
    assert "Revision 45 planning correction" in (ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_status_history.md").read_text(encoding="utf-8")
    assert "LocalMechanicalForceRefinement" in text
    assert "ThermodynamicMeanForceCertificate" in text
    assert "EvidenceCrossfitPartition" in text
    assert "thermodynamic_validation" in text
    assert "PreliminaryCorridorSupport" in text
    assert "FinalTransitionEventCertificate" in text
    assert "Stage 11E-THERMO3A" in text
    assert "Stage 11E-THERMO3B" in text
    assert "Stage 11E-THERMO4A" in text
    assert "Stage 11E-THERMO4B" in text
    assert "Stage 11F0" in text and "RateBoundModel" in text
    assert "Stage 11G0" in text and "Stage 11G1" in text
    assert "Stage 11H" in text and "Stage 11I" in text
    assert "`validated_transition_saddle` is a THERMO3B outcome" in flat
    assert "next mandatory implementation boundary" not in flat.lower()
    assert "revision-42 dependency map" not in flat.lower()


def test_revision45_normative_manual_excludes_release_chronology_labels() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Implementation status in `" not in text
    assert "implements this boundary:" not in text
    assert "Baseline compatibility requirements" in text
    assert SPEC.stat().st_size > 1_000
