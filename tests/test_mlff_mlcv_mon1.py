from __future__ import annotations

import csv
import json
from pathlib import Path

import mdstats


def test_mlcv_monitor_policy_roundtrip_and_defaults() -> None:
    policy = mdstats.MlcvMonitorPolicy()
    assert policy.target_light_configurations == 256
    assert policy.replay_light_configurations == 512
    assert policy.training_diagnostic_configurations == 256
    assert mdstats.MlcvMonitorPolicy.from_dict(policy.to_dict()) == policy


def test_mlcv_diagnostic_history_is_reporting_only_and_reproducible(tmp_path: Path) -> None:
    log = tmp_path / "run_train.txt"
    rows = [
        {"mode": "opt", "epoch": 0, "loss": 1.2},
        {"mode": "opt", "epoch": 0, "loss": 0.8},
        {"mode": "eval", "epoch": 0, "head": "target_train_diagnostic", "rmse_f": 0.021},
        {"mode": "eval", "epoch": 0, "head": "pt_head", "rmse_f": 0.034},
        {"mode": "eval", "epoch": 0, "head": "target_head", "rmse_f": 0.027},
        {"mode": "opt", "epoch": 1, "loss": 0.6},
        {"mode": "eval", "epoch": 1, "head": "target_train_diagnostic", "rmse_f": 0.018},
        {"mode": "eval", "epoch": 1, "head": "pt_head", "rmse_f": 0.035},
        {"mode": "eval", "epoch": 1, "head": "target_head", "rmse_f": 0.023},
    ]
    log.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    out = tmp_path / "diagnostics"
    first = mdstats.write_mlcv_diagnostic_history(
        log,
        out,
        stop_epoch=1,
        stop_reason="target_success",
    )
    assert first["reporting_inference_count"] == 0
    assert first["thresholds"]["target_success_stop"] == 0.024
    assert first["thresholds"]["replay_exhaustion_stop"] == 0.036
    assert [item["checkpoint_target_force_rmse"] for item in first["metrics"]] == [0.027, 0.023]
    assert [item["checkpoint_replay_force_rmse"] for item in first["metrics"]] == [0.034, 0.035]
    assert first["metrics"][0]["train_objective_loss"] == 1.0
    assert [item["train_target_diagnostic_force_rmse"] for item in first["metrics"]] == [0.021, 0.018]
    assert (out / "training_history.json").is_file()
    assert (out / "training_history.csv").is_file()
    assert (out / "validation_history.png").is_file()
    assert (out / "validation_history.png").stat().st_size > 0
    with (out / "training_history.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert [int(row["epoch"]) for row in csv_rows] == [0, 1]

    second = mdstats.write_mlcv_diagnostic_history(
        log,
        out,
        stop_epoch=1,
        stop_reason="target_success",
    )
    assert second["content_digest"] == first["content_digest"]


def test_historical_online_monitor_policy_v1_reads_with_diagnostic_default() -> None:
    old = {
        "schema": "mdstats.online-monitor-policy.v1",
        "target_configurations": 256,
        "replay_configurations": 512,
        "seed": 161803,
        "target_strategy": "balanced_condition_run_time_systematic",
        "replay_strategy": "chemistry_size_systematic",
    }
    policy = mdstats.OnlineMonitorPolicy.from_dict(old)
    assert policy.training_diagnostic_configurations == 256


def test_execution_reporting_writes_run_diagnostics_without_inference(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from mdstats.training_data.campaign_execution import _write_mlcv_run_diagnostics_if_available

    job_root = tmp_path / "job"
    run_root = tmp_path / "run"
    result_dir = run_root / "results"
    job_root.mkdir()
    result_dir.mkdir(parents=True)
    (job_root / "target_training_diagnostic.xyz").write_text("placeholder\n", encoding="utf-8")
    metrics = [
        {"mode": "opt", "epoch": 0, "loss": 0.9},
        {"mode": "eval", "epoch": 0, "head": "pt_head", "rmse_f": 0.033},
        {"mode": "eval", "epoch": 0, "head": "target_head", "rmse_f": 0.026},
    ]
    (result_dir / "example_train.txt").write_text(
        "\n".join(json.dumps(item) for item in metrics) + "\n", encoding="utf-8"
    )
    job = SimpleNamespace(protocol=SimpleNamespace(adaptive_stop_policy=None))
    _write_mlcv_run_diagnostics_if_available(
        job_root=job_root, run_root=run_root, result_dir=result_dir, job=job
    )
    diagnostics = run_root / "diagnostics"
    assert (diagnostics / "persisted_mace_metrics.jsonl").is_file()
    payload = json.loads((diagnostics / "training_history.json").read_text())
    assert payload["reporting_inference_count"] == 0
    assert payload["metrics"][0]["checkpoint_target_force_rmse"] == 0.026
    assert payload["metrics"][0]["checkpoint_replay_force_rmse"] == 0.033
    assert (diagnostics / "training_history.csv").is_file()
    assert (diagnostics / "validation_history.png").is_file()


def test_training_diagnostic_loader_is_prepended_and_target_head_encoded(tmp_path: Path, monkeypatch) -> None:
    import pytest
    pytest.importorskip("mace")
    import numpy as np
    from ase import Atoms
    from ase.io import write
    from types import SimpleNamespace
    from mdstats.training_data.mlcv_monitors import (
        MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME,
        MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE,
        prepare_training_diagnostic_validation_loader,
    )

    path = tmp_path / "target_training_diagnostic.xyz"
    atoms = Atoms("H2", positions=[[0.0, 0.0, 0.0], [0.75, 0.0, 0.0]], cell=[6.0, 6.0, 6.0], pbc=True)
    atoms.info["REF_energy"] = -1.0
    atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=float)
    write(path, [atoms], format="extxyz")
    monkeypatch.setenv(MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE, str(path))

    model = SimpleNamespace(heads=["pt_head", "target_head"], atomic_numbers=[1], r_max=3.0)
    reference = SimpleNamespace(batch_size=4, pin_memory=False, num_workers=0)
    original = {"pt_head": reference, "target_head": reference}
    observed = prepare_training_diagnostic_validation_loader(model, original)
    assert list(observed) == [MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME, "pt_head", "target_head"]
    assert observed[MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME].batch_size == 4
    batch = next(iter(observed[MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME]))
    # target_head is index 1 in model.heads, proving that the diagnostic loader
    # evaluates the target head while its dictionary key remains diagnostic-only.
    assert set(int(v) for v in batch.head.reshape(-1).tolist()) == {1}
