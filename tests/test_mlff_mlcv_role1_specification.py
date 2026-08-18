from __future__ import annotations

from pathlib import Path

import mdstats


def test_mlcv_role1_architecture_is_marked_implemented() -> None:
    text = (Path(__file__).parents[1] / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(encoding="utf-8")
    section = text[text.index("# Post-0.20.129 conventional-CV") :]
    assert "MLCV-ROLE1 implemented in" in section
    assert "0.20.131a0" in section
    assert "mdstats.mlcv-role-catalog.v1" in section
    assert "outer-CV or locked-test evidence" in section
    assert "3 x (3 + 1) = 12" in section


def test_mlcv_role1_public_contract_is_exported() -> None:
    assert mdstats.MLCV_ROLE_CATALOG_SCHEMA == "mdstats.mlcv-role-catalog.v1"
    assert mdstats.MLCV_ROLE_AUTHORITY_VERSION == "mdstats.mlcv-role-authority.2026-08.v1"
    assert mdstats.MLFF_DATA8_PARSER_VERSION == "0.20.132a0"
    assert "MlcvRoleCatalog" in mdstats.__all__
