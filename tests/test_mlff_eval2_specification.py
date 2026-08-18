from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
EXAMPLE = ROOT / "campaign.toml.example"


def test_eval2_release_and_manual_contract_are_current():
    text = MANUAL.read_text(encoding="utf-8")
    assert mdstats.__version__ == "0.20.185a0"
    assert "EVAL2 is implemented in `mdstats 0.20.171a0`" in text
    assert "Implementation status (`0.20.171a0`): complete for static target/replay checkpoint evaluation" in text
    assert "development-only complement" in text
    assert "configured cap is identity-bearing" in text


def test_generated_and_example_configs_freeze_eval2_rescue_cap():
    source = inspect.getsource(campaign_cli)
    example = EXAMPLE.read_text(encoding="utf-8")
    assert 'eval2_candidate_rescue_cap = 5' in source
    assert 'eval2_candidate_rescue_cap = 5' in example


def test_train2_evaluate_dispatches_to_eval2_and_verify_dispatches_to_deploy_verify1():
    evaluate_source = inspect.getsource(campaign_cli.command_evaluate)
    verify_source = inspect.getsource(campaign_cli.command_verify)
    assert "_command_evaluate_train2" in evaluate_source
    assert "_command_verify_train2_deploy" in verify_source
    stage_b = inspect.getsource(campaign_cli._eval2_stage_b_evidence)
    assert "foundation_checkpoint.canonical_content_digest" in stage_b
    assert "replay_diagnostic_force_rmse_mev_per_a" in stage_b
    stage_b0 = inspect.getsource(campaign_cli._eval2_stage_b0_evidence)
    assert "foundation_checkpoint.canonical_content_digest" in stage_b0
    assert "include_replay=False" in stage_b0
