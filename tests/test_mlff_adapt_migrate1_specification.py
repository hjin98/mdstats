from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_adaptive_migration_spec.md"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
QUAL = ROOT / "release" / "mlff_adapt_migrate1_lifecycle_qualification.json"


def test_adapt_migrate1_release_identity_and_specification() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in `mdstats 0.20.128a0`." in text
    assert "ProtocolFreezeAuthorityRecord" in text
    assert "AdaptiveMigrationRecord" in text
    assert "0.20.127 adaptive alias reconciliation" in text
    assert "storage report` remains read-only" in text
    assert "does **not** delete or reinterpret historical EVAL-MF" in text


def test_architecture_closes_all_seven_adaptive_gates() -> None:
    text = ARCH.read_text(encoding="utf-8")
    section = text[text.index("## ADAPT-MIGRATE1") : text.index("## Completion rule for the adaptive-training revision")]
    assert "**Status:** implemented in `mdstats 0.20.128a0`." in section
    assert "### ADAPT-MIGRATE1 implementation record (`0.20.128a0`)" in section
    assert "ProtocolFreezeAuthorityRecord" in section
    assert "AdaptiveMigrationRecord" in section
    assert "all seven adaptive gates are implemented" in text


def test_migration_source_exposes_fail_closed_authority_and_evaluator_boundaries() -> None:
    source = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    assert "def _enforce_evaluation_migration_boundary" in source
    assert "def _reconcile_adaptive_migration" in source
    assert "def _reuse_frozen_adaptive_evaluation" in source
    assert "def _read_storage_migration_summary" in source
    assert "ProtocolFreezeAuthorityRecord" in (ROOT / "mdstats" / "training_data" / "adaptive_migration.py").read_text(encoding="utf-8")
    assert "mode=ro" in source


def test_generated_config_keeps_final_adaptive_defaults() -> None:
    source = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    for expected in (
        "max_num_epochs = 30",
        "online_target_monitor_configurations = 256",
        "online_replay_monitor_configurations = 512",
        "target_stop_fraction = 0.80",
        "replay_stop_multiplier = 1.20",
        "maximum_target_force_rmse_ev_per_angstrom = 0.030",
        "target_score_weight = 1.0",
        "replay_score_weight = 1.0",
        "finalist_count = 5",
        "finalist_rescue_batch_size = 5",
        'checkpoint_strategy = "mlcv_nested_cv"',
    ):
        assert expected in source


def test_migrate1_release_qualification_is_frozen() -> None:
    import json
    payload = json.loads(QUAL.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-adapt-migrate1-qualification.v1"
    assert payload["package_version"] == "0.20.128a0"
    assert payload["status"] == "qualified"
    assert payload["required_outcome_coverage"]["top_five_and_next_five_rescue"] is True
    assert payload["migration_contract"]["storage_deletion_authority_broadened"] is False
