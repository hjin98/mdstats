from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rev87_warning_domain_is_retained_under_current_release() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV87.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_campaign_warning_domain_spec.md").read_text()
    # Revision 87 is historical evidence; the current normative warning-domain
    # owner is the dedicated specification, not the proposed D3 candidate
    # manual's historical aggregate text.
    assert "WARN-DOMAIN1" in note
    assert 'status: "proposed D3 renewal candidate pending independent review"' in manual
    assert "Gate: `WARN-DOMAIN1`" in spec
    assert "0.20.220a0" in note
    assert "WARNING:root:" in spec
    assert "worker thread" in spec
