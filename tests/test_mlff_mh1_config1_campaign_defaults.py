from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from mdstats.training_data import campaign_cli


def _template(**kwargs: object) -> str:
    params = dict(
        workspace="mlff-campaign",
        training_root="/target",
        foundation_model="/models/foundation.model",
        replay_train="/replay/train.extxyz",
        replay_monitor="/replay/monitor.extxyz",
        default_device="cuda",
        precision_profile="single",
    )
    params.update(kwargs)
    return campaign_cli._config_template(**params)


def test_config1_new_template_defaults_to_mh1_omat_pbe_e3nn() -> None:
    cfg = tomllib.loads(_template())
    assert cfg["campaign"]["id"] == "lta-mh1-omat-pbe-finetune"
    assert cfg["foundation"] == {
        "family": "mace_mh_1",
        "head": "omat_pbe",
        "label": "MACE-MH-1",
    }
    # Compatibility/display only; the canonical source is [foundation].
    assert cfg["model"]["foundation_name"] == "MACE-MH-1"
    assert cfg["acceleration"]["backend"] == "e3nn"
    assert cfg["acceleration"]["only_cueq"] is False
    assert cfg["acceleration"]["require_available"] is True
    assert "replay_baseline_head" not in cfg["evaluation"]
    assert "verification" not in cfg


def test_config1_explicit_mpa0_e3nn_retains_historical_template_semantics() -> None:
    cfg = tomllib.loads(
        _template(
            foundation_family="mace_mpa_0",
            foundation_head="default",
            foundation_label="MPA-0-medium",
            acceleration_backend="e3nn",
        )
    )
    assert cfg["campaign"]["id"] == "lta-mpa0-finetune"
    assert cfg["foundation"] == {
        "family": "mace_mpa_0",
        "head": "default",
        "label": "MPA-0-medium",
    }
    assert cfg["model"]["foundation_name"] == "MPA-0-medium"
    assert cfg["acceleration"]["backend"] == "e3nn"


def test_config1_legacy_mpa0_toml_normalizes_in_memory_without_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "campaign.toml"
    legacy = _template(
        foundation_family="mace_mpa_0",
        foundation_head="default",
        foundation_label="MPA-0-medium",
        acceleration_backend="e3nn",
    )
    # Simulate the exact pre-CONFIG1 shape: no canonical [foundation] section.
    start = legacy.index("[foundation]\n")
    end = legacy.index("[paths]\n")
    legacy = legacy[:start] + legacy[end:]
    path.write_text(legacy, encoding="utf-8")
    before = path.read_bytes()

    cfg, _ = campaign_cli._load_config(path)
    assert cfg["foundation"] == {
        "family": "mace_mpa_0",
        "head": "default",
        "label": "MPA-0-medium",
        "legacy_normalized": True,
    }
    assert path.read_bytes() == before


def test_config1_unknown_head_blind_legacy_foundation_is_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "campaign.toml"
    legacy = _template(
        foundation_family="mace_mpa_0",
        foundation_head="default",
        acceleration_backend="e3nn",
    )
    start = legacy.index("[foundation]\n")
    end = legacy.index("[paths]\n")
    legacy = legacy[:start] + legacy[end:]
    legacy = legacy.replace('foundation_name = "MPA-0-medium"', 'foundation_name = "my-custom-mace"')
    path.write_text(legacy, encoding="utf-8")

    cfg, _ = campaign_cli._load_config(path)
    assert "foundation" not in cfg
    with pytest.raises(campaign_cli.CampaignCliError, match="could not be normalized safely"):
        campaign_cli._foundation_config(cfg)


def test_config1_present_foundation_requires_explicit_nonempty_family_and_head(tmp_path: Path) -> None:
    path = tmp_path / "campaign.toml"
    text = _template().replace('head = "omat_pbe"', 'head = ""', 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(campaign_cli.CampaignCliError, match=r"\[foundation\]\.head"):
        campaign_cli._load_config(path)




def test_config1_foundation_contract_digest_changes_with_family_head_or_backend() -> None:
    base = tomllib.loads(_template())
    base_digest = campaign_cli._foundation_configuration_contract(base)["content_digest"]

    head = tomllib.loads(_template(foundation_head="omol"))
    backend = tomllib.loads(_template(acceleration_backend="cueq"))
    family = tomllib.loads(
        _template(foundation_family="mace_mpa_0", foundation_head="default", acceleration_backend="cueq")
    )
    assert campaign_cli._foundation_configuration_contract(head)["content_digest"] != base_digest
    assert campaign_cli._foundation_configuration_contract(backend)["content_digest"] != base_digest
    assert campaign_cli._foundation_configuration_contract(family)["content_digest"] != base_digest

def test_config1_conflicting_legacy_source_head_alias_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "campaign.toml"
    text = _template()
    text = text.replace(
        "[evaluation]\n",
        "[evaluation]\nreplay_baseline_head = \"omol\"\n",
        1,
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(campaign_cli.CampaignCliError, match="conflicts with canonical"):
        campaign_cli._load_config(path)


def test_config1_invalid_canonical_family_fails_during_load(tmp_path: Path) -> None:
    path = tmp_path / "campaign.toml"
    text = _template().replace('family = "mace_mh_1"', 'family = "not_a_mace_family"', 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(campaign_cli.CampaignCliError, match=r"Invalid \[foundation\]\.family"):
        campaign_cli._load_config(path)


def test_config1_shipped_example_is_the_new_generalized_default() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = tomllib.loads((root / "campaign.toml.example").read_text(encoding="utf-8"))
    assert cfg["campaign"]["id"] == "lta-mh1-omat-pbe-finetune"
    assert cfg["foundation"]["family"] == "mace_mh_1"
    assert cfg["foundation"]["head"] == "omat_pbe"
    assert cfg["paths"]["foundation_model"] == "/path/to/mace-mh-1.model"
    assert cfg["acceleration"]["backend"] == "e3nn"

def test_config1_init_defaults_are_explicit_not_environment_autodetected(tmp_path: Path) -> None:
    target = tmp_path / "campaign.toml"
    parser = campaign_cli.build_parser()
    args = parser.parse_args(["--config", str(target), "init"])
    assert args.foundation_family == "mace_mh_1"
    assert args.backend == "e3nn"
    rc = args.func(args)
    assert rc == 0
    cfg = tomllib.loads(target.read_text(encoding="utf-8"))
    assert cfg["foundation"]["family"] == "mace_mh_1"
    assert cfg["foundation"]["head"] == "omat_pbe"
    assert cfg["paths"]["foundation_model"] == "/path/to/mace-mh-1.model"
    assert cfg["acceleration"]["backend"] == "e3nn"


def test_config1_init_allows_explicit_mpa0_e3nn(tmp_path: Path) -> None:
    target = tmp_path / "campaign.toml"
    parser = campaign_cli.build_parser()
    args = parser.parse_args(
        [
            "--config", str(target), "init",
            "--foundation-family", "mace_mpa_0",
            "--backend", "e3nn",
        ]
    )
    rc = args.func(args)
    assert rc == 0
    cfg = tomllib.loads(target.read_text(encoding="utf-8"))
    assert cfg["foundation"]["family"] == "mace_mpa_0"
    assert cfg["foundation"]["head"] == "default"
    assert cfg["paths"]["foundation_model"] == "/path/to/mace-mpa-0-medium.model"
    assert cfg["acceleration"]["backend"] == "e3nn"
