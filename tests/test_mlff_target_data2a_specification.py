from __future__ import annotations

from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_target_data2a_public_contract_and_manual_status() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "TARGET-DATA2A is implemented in `mdstats 0.20.163a0`" in text
    assert "`TargetDataRoleFreeze`" in text
    assert "repeating DATA4-DATA9A" in text
    assert mdstats.TARGET_DATA_ROLE_FREEZE_VERSION == "mdstats.target-data2a.role-freeze.2026-08.v1"
    assert callable(mdstats.build_target_data_role_freeze)
