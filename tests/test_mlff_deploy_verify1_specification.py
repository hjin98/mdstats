from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
EXAMPLE = ROOT / "campaign.toml.example"


def test_deploy_verify1_release_manual_and_public_api_are_current():
    text = MANUAL.read_text(encoding="utf-8")
    assert mdstats.__version__ == "0.20.180a0"
    assert "DEPLOY-VERIFY1 is implemented in `mdstats 0.20.172a0`" in text
    assert "Implementation status (`0.20.172a0`): complete" in text
    assert "correlation-block round-robin" in text
    assert mdstats.DeployVerifyRunRecord is not None
    assert mdstats.run_lammps_mliap_run0 is not None


def test_generated_and_example_configs_freeze_deployment_parity_policy():
    source = inspect.getsource(campaign_cli)
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


def test_train2_verify_dispatches_only_final_development_candidates():
    verify_source = inspect.getsource(campaign_cli.command_verify)
    assert "_command_verify_train2_deploy" in verify_source
    candidate_source = inspect.getsource(campaign_cli._deploy_verify_candidate_runs)
    assert "MaceJobKind.FINAL_DEVELOPMENT" in candidate_source
    assert "stage_b_finalist_sizes" in candidate_source
    assert "selected_target_size" in candidate_source


def test_deploy_policy_is_model_dtype_bound():
    cfg = {"verification": {"deployment_probe_configurations": 7}}
    policy = campaign_cli._deploy_verify_policy(cfg, model_dtype="float64")
    assert policy.model_dtype == "float64"
    assert policy.maximum_probe_configurations == 7
    assert policy.tolerances == (1e-9, 1e-10)


def test_candidate_resolution_excludes_cv_runs_and_uses_screening_then_production_seeds():
    final = mdstats.MaceJobKind.FINAL_DEVELOPMENT
    cv = mdstats.MaceJobKind.CROSS_VALIDATION_FOLD
    runs = (
        SimpleNamespace(kind=final, seed=1, selection_size=512, run_id="f512s1"),
        SimpleNamespace(kind=final, seed=1, selection_size=1024, run_id="f1024s1"),
        SimpleNamespace(kind=final, seed=2, selection_size=1024, run_id="f1024s2"),
        SimpleNamespace(kind=cv, seed=1, selection_size=512, run_id="cv512"),
    )
    campaign = SimpleNamespace(runs=runs)
    screening = SimpleNamespace(
        outcome="awaiting_stage_c_full_training",
        stage_b_finalist_sizes=(512, 1024),
        policy=SimpleNamespace(screening_optimizer_seed=1),
    )
    stage, candidates = campaign_cli._deploy_verify_candidate_runs(campaign, screening)
    assert stage == "target_size_stage_c"
    assert [r.run_id for r in candidates] == ["f512s1", "f1024s1"]

    selected = SimpleNamespace(outcome="selected", selected_target_size=1024)
    stage, candidates = campaign_cli._deploy_verify_candidate_runs(campaign, selected)
    assert stage == "production"
    assert [r.run_id for r in candidates] == ["f1024s1", "f1024s2"]
