"""Current campaign CLI behavior after the destructive target-size cutover.

The retired pre-V7 lifecycle - `materialize`, `preflight`, `train`,
`extend-seed`, `evaluate`, `verify` and their DATA8/MLCV/adaptive machinery -
was removed by P6, together with the tests whose only contract was that
topology. What remains here is the neutral, still-current CLI behavior:
configuration authoring, the campaign store, manifest approval, wrapper shims,
stage/config binding, and the public command surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mdstats.training_data import campaign_cli


def test_parser_exposes_the_current_lifecycle_surface() -> None:
    parser = campaign_cli.build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert tuple(choices) == (
        "init", "doctor", "prepare", "select-target-size",
        "cross-validate", "train-production", "storage", "qualification",
        "status", "advance", "guide",
    )
    assert parser.parse_args(["select-target-size"]).func is campaign_cli.command_select_target_size
    assert parser.parse_args(["cross-validate"]).func is campaign_cli.command_cross_validate
    assert parser.parse_args(["train-production"]).func is campaign_cli.command_train_production
    # Post-production qualification is a separate downstream family with a
    # frozen semantic split; bare `qualification` is observational.
    qualification = choices["qualification"]
    qualification_choices = qualification._subparsers._group_actions[0].choices
    assert tuple(qualification_choices) == ("status", "run", "activate-locked")
    assert parser.parse_args(["qualification"]).func is campaign_cli.command_qualification_status
    assert (
        parser.parse_args(["qualification", "run"]).func is campaign_cli.command_qualification_run
    )
    assert (
        parser.parse_args(["qualification", "activate-locked"]).func
        is campaign_cli.command_qualification_activate_locked
    )
    assert parser.parse_args(["qualification", "run", "--case-workers", "4"]).case_workers == 4
    assert parser.parse_args(["qualification", "activate-locked", "--confirm"]).confirm is True
    with pytest.raises(SystemExit):
        parser.parse_args(["qualification", "activate"])
    storage = choices["storage"]
    storage_choices = storage._subparsers._group_actions[0].choices
    assert tuple(storage_choices) == ("report", "cleanup")
    assert parser.parse_args(["storage"]).func is campaign_cli.command_storage
    assert parser.parse_args(["storage", "report", "--top", "7"]).top == 7
    assert parser.parse_args(["storage", "cleanup", "--tier", "cache"]).func is campaign_cli.command_cleanup
    with pytest.raises(SystemExit):
        parser.parse_args(["storage", "deduplicate", "--apply"])
    with pytest.raises(SystemExit):
        parser.parse_args(["storage", "archive", "verify"])


def test_retired_lifecycle_commands_are_absent_from_the_parser() -> None:
    parser = campaign_cli.build_parser()
    choices = parser._subparsers._group_actions[0].choices
    retired = {"materialize", "preflight", "train", "extend-seed", "evaluate", "verify"}
    assert not (set(choices) & retired)
    for name in retired:
        assert not hasattr(campaign_cli, f"command_{name.replace('-', '_')}")


def test_top_level_cleanup_is_rejected_and_normalizer_is_absent() -> None:
    assert not hasattr(campaign_cli, "_normalize_legacy_storage_argv")
    with pytest.raises(SystemExit):
        campaign_cli.main(["cleanup", "--tier", "safe"])


def test_init_creates_one_config_and_one_state_database(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    result = campaign_cli.main([
        "--config", str(config), "init", "--workspace", "work",
        "--training-root", "training", "--foundation-model", "foundation.model",
        "--replay-train", "replay-train.xyz", "--replay-monitor", "replay-monitor.xyz",
    ])
    assert result == 0
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert '[training.naive_fine_tuning]' in text
    assert '[training.multihead_replay]' in text
    assert 'enabled = false' in text
    assert 'seeds = [1, 2]' in text
    assert 'mode = "external_pseudolabel"' in text
    assert "allow_small_corpus = false" in text
    assert "online_monitor_seed = 161803" in text
    assert "online_target_monitor_configurations = 256" in text
    assert "online_replay_monitor_configurations = 512" in text
    assert 'inference_batch_policy = "auto"' in text
    assert "maximum_inference_batch_size = 32" in text
    assert "[cleanup]" in text
    assert "storage cleanup --tier safe|cache." in text
    evaluation = text[text.index("[evaluation]"):text.index("[export]")]
    assert "\nbatch_size = 8\n" not in evaluation
    assert "[preflight]" not in text
    assert "[verification]" not in text
    assert "target_size_power_min = 7" in text
    assert "target_size_power_max = 14" in text
    assert "evaluation_size_powers = [8, 9, 10]" in text
    state = tmp_path / "work" / ".mdstats" / "campaign.sqlite3"
    assert state.is_file()
    assert not state.with_name(state.name + "-wal").exists()

def test_campaign_store_roundtrip_and_stage_state(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite3")
    store.put_record("example", {"schema": "example.v1", "value": 4})
    assert store.get_payload("example")["value"] == 4
    store.set_stage("prepare", campaign_cli.StageState.WAITING, "review manifest")
    assert store.stage("prepare") == (campaign_cli.StageState.WAITING, "review manifest")
    assert store.record_keys() == ("example",)

def test_manifest_discovery_requires_digest_approval(tmp_path: Path) -> None:
    training = tmp_path / "training"
    training.mkdir()
    (training / "LTA_Na.300K.init.xml").write_text("<modeling/>", encoding="utf-8")
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root=str(training), foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    with pytest.raises(campaign_cli.CampaignCliError, match="Review reference groups"):
        campaign_cli._ensure_manifest(cfg, paths, approve=False)
    assert paths.manifest.is_file()
    with pytest.raises(campaign_cli.CampaignCliError, match="not approved"):
        campaign_cli._ensure_manifest(cfg, paths, approve=False)
    approved = campaign_cli._ensure_manifest(cfg, paths, approve=True)
    assert len(approved.runs) == 1
    assert approved.runs[0].run_id == "LTA_Na.300K.init"

def test_local_wrapper_shims_have_qualified_names(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    wrappers = campaign_cli._ensure_local_wrappers(paths)
    assert set(wrappers) == {"mdstats-mace-train", "mdstats-mace-eval", "mdstats-mace-select-head"}
    assert all(path.is_file() and path.stat().st_mode & 0o111 for path in wrappers.values())

def test_status_prints_next_safe_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    assert campaign_cli.main(["--config", str(config), "status"]) == 0
    output = capsys.readouterr().out
    assert "Next command:" in output
    assert "doctor" in output

def test_prepare_refuses_to_skip_doctor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    result = campaign_cli.main(["--config", str(config), "prepare"])
    assert result == 2
    assert "Stage `doctor` is not complete" in capsys.readouterr().err

def test_stage_completion_is_bound_to_current_configuration(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    campaign_cli._mark_stage(store, paths, "doctor", campaign_cli.StageState.COMPLETE, "passed")
    assert campaign_cli._effective_stage(store, paths, "doctor")[0] is campaign_cli.StageState.COMPLETE
    config.write_text(config.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    state, message = campaign_cli._effective_stage(store, paths, "doctor")
    assert state is campaign_cli.StageState.WAITING
    assert "campaign.toml changed" in message

def test_shipped_campaign_example_matches_two_seed_default() -> None:
    text = (Path(__file__).resolve().parents[1] / "campaign.toml.example").read_text(encoding="utf-8")
    multi = text[text.index("[training.multihead_replay]") : text.index("[runtime]")]
    assert "enabled = true" in multi
    assert "seeds = [1, 2]" in multi
    assert "[post_selection.cv]" in multi
    naive = text[text.index("[training.naive_fine_tuning]") : text.index("[training.multihead_replay]")]
    assert "enabled = false" in naive
    assert "seeds = [1, 2]" in naive
