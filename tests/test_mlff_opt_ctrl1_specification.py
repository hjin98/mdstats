from __future__ import annotations

from pathlib import Path
import inspect

import mdstats
from mdstats.training_data import campaign_cli, training_parallel

ROOT = Path(__file__).resolve().parents[1]


def test_opt_ctrl1_release_identity_preserves_scientific_compatibility() -> None:
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert campaign_cli.VERIFICATION_RUNTIME_COMPATIBILITY_VERSION == "0.20.85a0"
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()


def test_opt_ctrl1_architecture_and_spec_close_roadmap() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (
        ROOT
        / "docs/specs/training_data/mlff_opt_ctrl1_control_plane_telemetry_spec.md"
    ).read_text()
    assert "OPT-CTRL1 - control-plane and telemetry cleanup - implemented in 0.20.103a0" in manual
    assert "OPT-EVAL1 through OPT-CTRL1 is complete" in manual
    assert "Status: implemented in mdstats 0.20.103a0." in spec
    for token in (
        "get_record_optional",
        "hash-receipts.sqlite3",
        "libnvidia-ml",
        "parallel_inference_post_calibration_monitor_interval_seconds",
        "iread()",
    ):
        assert token in spec


def test_generated_config_records_post_calibration_poll_control() -> None:
    template = campaign_cli._config_template(
        workspace="/tmp/workspace",
        training_root="/tmp/training",
        foundation_model="/tmp/foundation.model",
        replay_train="/tmp/replay-train.extxyz",
        replay_monitor="/tmp/replay-monitor.extxyz",
    )
    assert "parallel_inference_post_calibration_monitor_interval_seconds = 30.0" in template


def test_gpu_telemetry_implementation_prefers_nvml() -> None:
    source = inspect.getsource(training_parallel.query_gpu_telemetry)
    assert "_query_gpu_telemetry_nvml" in source
    assert "_query_gpu_telemetry_nvidia_smi" in source
