from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from mdstats.training_data import campaign_cli


def _init(tmp_path: Path, *extra: str):
    config = tmp_path / "campaign.toml"
    workspace = tmp_path / "workspace"
    rc = campaign_cli.main(
        [
            "--config",
            str(config),
            "init",
            *extra,
            "--workspace",
            str(workspace),
        ]
    )
    assert rc == 0
    with config.open("rb") as handle:
        return tomllib.load(handle)


@pytest.mark.parametrize(
    "model,family,head,label,path_suffix",
    [
        ("mh-1", "mace_mh_1", "omat_pbe", "MACE-MH-1", "mace-mh-1.model"),
        ("mpa-0", "mace_mpa_0", "default", "MPA-0-medium", "mace-mpa-0-medium.model"),
    ],
)
def test_init_positional_model_selects_existing_foundation_authority(
    tmp_path: Path,
    model: str,
    family: str,
    head: str,
    label: str,
    path_suffix: str,
) -> None:
    cfg = _init(tmp_path, model)
    assert cfg["foundation"] == {
        "family": family,
        "head": head,
        "label": label,
    }
    assert cfg["model"]["foundation_name"] == label
    assert cfg["paths"]["foundation_model"].endswith(path_suffix)


def test_init_without_model_preserves_mh1_default(tmp_path: Path) -> None:
    cfg = _init(tmp_path)
    assert cfg["foundation"]["family"] == "mace_mh_1"
    assert cfg["foundation"]["head"] == "omat_pbe"
    assert cfg["model"]["foundation_name"] == "MACE-MH-1"
    assert cfg["paths"]["foundation_model"].endswith("mace-mh-1.model")


def test_init_positional_and_legacy_family_must_not_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "campaign.toml"
    rc = campaign_cli.main(
        [
            "--config",
            str(config),
            "init",
            "mh-1",
            "--foundation-family",
            "mace_mpa_0",
        ]
    )
    assert rc == 2
    assert not config.exists()
    assert "conflicts with --foundation-family" in capsys.readouterr().err

def test_init_positional_and_matching_legacy_family_succeeds(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    workspace = tmp_path / "workspace"
    rc = campaign_cli.main(
        [
            "--config",
            str(config),
            "init",
            "mh-1",
            "--foundation-family",
            "mace_mh_1",
            "--workspace",
            str(workspace),
        ]
    )
    assert rc == 0
    with config.open("rb") as handle:
        cfg = tomllib.load(handle)
    assert cfg["foundation"]["family"] == "mace_mh_1"
    assert cfg["foundation"]["head"] == "omat_pbe"


def test_init_config_named_init_resolves_correctly_without_ambiguity(tmp_path: Path) -> None:
    config = tmp_path / "init"
    workspace = tmp_path / "workspace"
    rc = campaign_cli.main(
        [
            "--config",
            str(config),
            "init",
            "mh-1",
            "--workspace",
            str(workspace),
        ]
    )
    assert rc == 0
    assert config.is_file()
    with config.open("rb") as handle:
        cfg = tomllib.load(handle)
    assert cfg["foundation"]["family"] == "mace_mh_1"
    assert cfg["foundation"]["head"] == "omat_pbe"


def test_init_options_before_positional_model_succeeds(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    workspace = tmp_path / "workspace"
    rc = campaign_cli.main(
        [
            "--config",
            str(config),
            "init",
            "--workspace",
            str(workspace),
            "mpa-0",
        ]
    )
    assert rc == 0
    with config.open("rb") as handle:
        cfg = tomllib.load(handle)
    assert cfg["foundation"]["family"] == "mace_mpa_0"
    assert cfg["foundation"]["head"] == "default"


def test_init_unsupported_model_fails_at_parser(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "campaign.toml"
    with pytest.raises(SystemExit) as excinfo:
        campaign_cli.main(
            [
                "--config",
                str(config),
                "init",
                "unsupported-model",
            ]
        )
    assert excinfo.value.code == 2
    assert not config.exists()
    err = capsys.readouterr().err
    assert "invalid choice" in err or "unsupported-model" in err
