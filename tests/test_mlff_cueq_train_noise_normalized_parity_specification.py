from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import acceleration, campaign_cli

ROOT=Path(__file__).resolve().parents[1]

def test_rev86_parity_material_is_historical_and_no_longer_current_authority():
    assert campaign_cli._training_acceleration_parity_policy().tolerance("float32") == (1.0e-5, 1.0e-6)
    policy=campaign_cli._training_acceleration_noise_normalized_policy()
    assert policy.repeat_count == 10 and policy.warmup_count == 1
    assert policy.force_distribution_quantile == 99.0
    assert policy.force_distribution_ratio_ceiling == 1.25
    assert policy.force_max_self_factor == 1.5
    assert policy.force_max_absolute_ceiling == 1.0e-4
    assert acceleration.TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_POLICY_SCHEMA.endswith(".v1")
    assert acceleration.TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_RECORD_SCHEMA.endswith(".v1")
    manual=(ROOT/"docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note=(ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV86.md").read_text()
    spec=(ROOT/"docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md").read_text()
    assert "CUEQ_TRAIN2_NOISE_NORMALIZED_PARITY" not in manual
    assert "0.20.219a0" in note
    assert "ratio(m)" in spec and "1.25" in spec
    graph=json.loads((ROOT/"docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes={n["id"]:n for n in graph["nodes"]}
    assert "CUEQ_TRAIN2_NOISE_NORMALIZED_PARITY" not in nodes
    index=(ROOT/"docs/specs/training_data/README.md").read_text()
    assert "Backend qualification reports, hotfix notes, parity diagnostics, and obsolete migration policies are not current semantic owners." in index
