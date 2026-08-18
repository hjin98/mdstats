from __future__ import annotations

from pathlib import Path
import inspect

import mdstats
from mdstats.training_data import campaign_cli


ROOT = Path(__file__).resolve().parents[1]


def test_opt_eval4_release_identity_preserves_mlff_compatibility() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()


def test_opt_eval4_architecture_and_spec_record_pipeline_contract() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (
        ROOT
        / "docs/specs/training_data/mlff_opt_eval4_staged_evaluation_pipeline_spec.md"
    ).read_text()
    assert "OPT-EVAL4 - staged evaluation pipeline" in manual
    assert "implemented in mdstats 0.20.101a0" in manual
    assert "OPT-EVAL1 through OPT-CTRL1 is complete" in manual
    assert "CPU monitor/cache preparation" in manual
    assert "accelerator-admitted checkpoint materialization" in manual
    assert "Status: implemented in mdstats 0.20.101a0." in spec
    assert "cache-only" in spec.lower()
    assert "backpressure" in spec.lower()


def test_opt_eval4_generated_config_exposes_bounded_cpu_pipeline_controls() -> None:
    template = campaign_cli._config_template(
        workspace="/tmp/workspace",
        training_root="/tmp/training",
        foundation_model="/tmp/foundation.model",
        replay_train="/tmp/replay-train.extxyz",
        replay_monitor="/tmp/replay-monitor.extxyz",
    )
    for line in (
        "parallel_evaluation_prepare_jobs = 0",
        "parallel_evaluation_finalize_jobs = 0",
        "evaluation_pipeline_buffer_jobs = 0",
    ):
        assert line in template


def test_campaign_evaluate_uses_staged_runner() -> None:
    source = inspect.getsource(campaign_cli.command_evaluate)
    assert "_run_staged_evaluation_tasks(" in source
    assert "prepare_mace_checkpoint_evaluation" in source
    assert "run_prepared_mace_checkpoint_inference" in source
    assert "finalize_prepared_mace_checkpoint_evaluation" in source
