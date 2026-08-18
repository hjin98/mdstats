from __future__ import annotations

import json
from pathlib import Path

from mdstats.training_data import campaign_cli


def _append_rows(path: Path, *, epoch: int, count: int) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for index in range(count):
            handle.write(json.dumps({"mode": "opt", "epoch": epoch, "index": index}) + "\n")


def test_restart_progress_is_checkpoint_and_attempt_aware(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    results = tmp_path / "results"
    checkpoints = tmp_path / "checkpoints"
    for directory in (logs, results, checkpoints):
        directory.mkdir()
    result = results / "model_train.txt"
    _append_rows(result, epoch=0, count=3)
    _append_rows(result, epoch=1, count=3)
    (checkpoints / "model_epoch-1.pt").write_bytes(b"checkpoint")

    probe = campaign_cli._MaceTrainingProgressProbe(
        log_dir=logs,
        result_dir=results,
        checkpoint_dir=checkpoints,
        expected_updates=90,
        device="cpu",
        max_epochs=30,
    )
    initial = probe.snapshot()
    assert initial.updates == 6
    assert initial.latest_epoch == 1
    assert initial.phase == "epoch 2/30 (inactive)"

    # MACE 0.3.16 historically appended a lower epoch after restart. Those
    # rows are duplicate work relative to the durable checkpoint and must not
    # move the display backward or inflate the percentage.
    _append_rows(result, epoch=0, count=2)
    repeated = probe.snapshot()
    assert repeated.updates == 6
    assert repeated.latest_epoch == 1
    assert "duplicate updates excluded" in repeated.phase

    _append_rows(result, epoch=2, count=4)
    resumed = probe.snapshot()
    assert resumed.updates == 10
    assert resumed.latest_epoch == 2
    assert resumed.phase == "epoch 3/30"


def test_explicit_method_seed_and_fold_matrix_defaults_and_final_only() -> None:
    cfg = {
        "selection": {"sizes": [512]},
        "training": {
            "naive_fine_tuning": {
                "enabled": True,
                "seeds": [7],
                "cross_validation_folds": 0,
                "fold_partition_seed": 123,
            },
            "multihead_replay": {
                "enabled": True,
                "seeds": [11, 13],
                "cross_validation_folds": 4,
                "fold_partition_seed": 456,
            },
        },
    }
    variants = campaign_cli._variant_specs(cfg)
    assert [(v.mode, v.seed, v.cross_validation_folds, v.fold_partition_seed) for v in variants] == [
        ("naive_fine_tuning", 7, 0, 123),
        ("multihead_replay", 11, 4, 456),
        ("multihead_replay", 13, 4, 456),
    ]


def test_initial_toml_exposes_every_campaign_random_seed(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    result = campaign_cli.main(
        [
            "--config", str(config), "init",
            "--workspace", "work",
            "--training-root", "training",
            "--foundation-model", "foundation.model",
            "--replay-train", "replay-train.xyz",
            "--replay-monitor", "replay-monitor.xyz",
        ]
    )
    assert result == 0
    text = config.read_text(encoding="utf-8")
    assert "[training.naive_fine_tuning]" in text
    assert "[training.multihead_replay]" in text
    assert "seeds = [1, 2]" in text
    assert "enabled = false" in text
    assert "cross_validation_folds = 3" in text
    assert "fold_partition_seed = 104729" in text
    assert "feature_projection_seed = 271828" in text
    assert "seed = 42" in text
    assert "velocity_seed = 314159" in text


def test_generated_default_training_matrix_is_multihead_two_seed_three_fold(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
        ),
        encoding="utf-8",
    )
    cfg, _ = campaign_cli._load_config(config)
    variants = campaign_cli._variant_specs(cfg)
    assert [(v.mode, v.seed, v.cross_validation_folds, v.fold_partition_seed) for v in variants] == [
        ("multihead_replay", 1, 3, 104729),
        ("multihead_replay", 2, 3, 104729),
    ]
