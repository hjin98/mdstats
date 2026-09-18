from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


ROOT = Path(__file__).resolve().parents[1]


def test_train2a_manual_and_generated_config_contract() -> None:
    manual = (ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(
        encoding="utf-8"
    )
    assert "assessment-independent `EvaluationMeasurementIdentity`" in manual
    assert "strict D2 lexicographic minimum" in manual
    assert "replay-warning diagnostic policy" in manual
    assert "checkpoint SHA-256" in manual

    cfg = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
    )
    assert 'policy_generation = "train2"' in cfg
    assert 'checkpoint_strategy = "train2_target_first"' in cfg
    assert "target_stop_fraction =" not in cfg
    assert "replay_stop_multiplier =" not in cfg
    assert "target_score_weight =" not in cfg
    assert "replay_score_weight =" not in cfg


def test_train2a_public_policy_defaults_have_zero_replay_selection_authority() -> None:
    selection = mdstats.CheckpointSelectionPolicy()
    admissibility = mdstats.CheckpointAdmissibilityPolicy()
    assert selection.exact_tie_break == "stable_candidate_identity"
    assert all("replay" not in metric.lower() for metric in (
        selection.primary_target_metric,
        *selection.secondary_target_metrics,
    ))
    assert admissibility.replay_label_requirement == "true_dft"
    assert admissibility.replay_degradation_budget_ev_per_angstrom == 0.030
