from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import mdstats
import pytest
from mdstats.training_data import _campaign_cli_core as campaign_cli_core
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
EXAMPLE = ROOT / "campaign.toml.example"


def test_deploy_verify1_public_api_and_target_size_boundary_are_current():
    text = MANUAL.read_text(encoding="utf-8")
    assert mdstats.__version__ == "0.20.242a0"
    assert "selected target size is protocol-global" in text
    assert "downstream model/protocol acceptance cannot alter the immutable size choice" in text
    assert mdstats.DeployVerifyRunRecord is not None
    assert mdstats.run_lammps_mliap_run0 is not None


def test_generated_and_example_configs_freeze_deployment_parity_policy():
    source = inspect.getsource(campaign_cli_core)
    example = EXAMPLE.read_text(encoding="utf-8")
    for token in (
        'deployment_probe_configurations = 16',
        'deployment_float32_rtol = 1.0e-5',
        'deployment_float64_rtol = 1.0e-9',
        'deployment_lammps_executable = "lmp"',
        'deployment_lammps_arguments = ["-k", "on", "g", "1"',
    ):
        assert token in source
        assert token in example


def test_train2_verify_dispatches_only_post_selection_final_development_candidates():
    verify_source = inspect.getsource(campaign_cli.command_verify)
    assert "_command_verify_train2_deploy" in verify_source
    candidate_source = inspect.getsource(campaign_cli._deploy_verify_candidate_runs)
    assert "MaceJobKind.FINAL_DEVELOPMENT" in candidate_source
    assert "selected_target_size" in candidate_source
    assert "stage_b_finalist_sizes" not in candidate_source
    assert "target_size_stage_c" not in candidate_source


def test_deploy_policy_is_model_dtype_bound():
    cfg = {"verification": {"deployment_probe_configurations": 7}}
    policy = campaign_cli._deploy_verify_policy(cfg, model_dtype="float64")
    assert policy.model_dtype == "float64"
    assert policy.maximum_probe_configurations == 7
    assert policy.tolerances == (1e-9, 1e-10)


def test_candidate_resolution_blocks_preselection_and_excludes_cv_runs():
    final = mdstats.MaceJobKind.FINAL_DEVELOPMENT
    cv = mdstats.MaceJobKind.CROSS_VALIDATION_FOLD
    runs = (
        SimpleNamespace(kind=final, seed=1, selection_size=512, run_id="f512s1"),
        SimpleNamespace(kind=final, seed=1, selection_size=1024, run_id="f1024s1"),
        SimpleNamespace(kind=final, seed=2, selection_size=1024, run_id="f1024s2"),
        SimpleNamespace(kind=cv, seed=1, selection_size=1024, run_id="cv1024"),
    )
    campaign = SimpleNamespace(runs=runs)
    screening = SimpleNamespace(outcome="awaiting_epoch_30", selected_target_size=None)
    with pytest.raises(campaign_cli.CampaignCliError, match="blocked until target-size selection"):
        campaign_cli._deploy_verify_candidate_runs(campaign, screening)

    selected = SimpleNamespace(outcome=mdstats.OUTCOME_SELECTED, selected_target_size=1024)
    stage, candidates = campaign_cli._deploy_verify_candidate_runs(campaign, selected)
    assert stage == "production"
    assert [r.run_id for r in candidates] == ["f1024s1", "f1024s2"]
