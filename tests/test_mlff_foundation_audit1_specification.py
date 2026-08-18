from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_foundation_audit1_public_contract_and_manual_status() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "FOUNDATION-AUDIT1 is implemented in `mdstats 0.20.164a0`" in text
    assert "`FoundationTargetAudit`" in text
    assert "does **not** perform a second foundation-model inference sweep" in text
    assert "`deferred_protocol`" in text
    assert mdstats.FOUNDATION_AUDIT_VERSION == "mdstats.foundation-audit1.target-baseline.2026-08.v1"
    assert callable(mdstats.build_foundation_target_audit)
    assert callable(mdstats.validate_foundation_target_audit_authority)
