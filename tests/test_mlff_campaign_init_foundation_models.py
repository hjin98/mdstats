from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from mdstats.training_data import campaign_cli
from mdstats.training_data.foundation import (
    MaceFoundationInspection,
    MaceFoundationSpec,
)


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


def _inspection(
    *,
    heads: tuple[str, ...],
    interaction: str,
    agnostic: bool,
    edge_irreps: str | None,
) -> MaceFoundationInspection:
    return MaceFoundationInspection(
        reference="/bounded/test.model",
        sha256="1" * 64,
        model_class="ScaleShiftMACE",
        model_module="mace.modules.models",
        available_heads=heads,
        atomic_numbers=(1, 8),
        r_max_angstrom=5.0,
        num_interactions=2,
        model_dtype="float32",
        atomic_energies_shape=(len(heads), 2),
        interaction_signatures=({"class": interaction},),
        product_signatures=({"class": "EquivariantProductBasisBlock"},),
        readout_signatures=({"class": "LinearReadoutBlock"},),
        edge_irreps=edge_irreps,
        use_agnostic_product=agnostic,
        use_last_readout_only=False,
        state_shape_digest="2" * 64,
    )


def test_both_supported_foundation_families_resolve_their_current_head_semantics() -> None:
    mpa = MaceFoundationSpec(
        family="mace_mpa_0",
        requested_head="default",
        requested_atomic_numbers=(1, 8),
    ).resolve(
        _inspection(
            heads=("default",),
            interaction="DensityBasedResidualInteractionBlock",
            agnostic=False,
            edge_irreps=None,
        )
    )
    assert mpa.model_family == "mace_mpa_0"
    assert mpa.foundation_head == "default"
    assert mpa.available_heads == ("default",)

    mh1 = MaceFoundationSpec(
        family="mace_mh_1",
        requested_head="omat_pbe",
        requested_atomic_numbers=(1, 8),
    ).resolve(
        _inspection(
            heads=("omat_pbe", "pbe", "scan"),
            interaction="RealAgnosticNonLinearResidualInteractionBlock",
            agnostic=True,
            edge_irreps="1x0e + 1x1o",
        )
    )
    assert mh1.model_family == "mace_mh_1"
    assert mh1.foundation_head == "omat_pbe"
    assert mh1.available_heads == ("omat_pbe", "pbe", "scan")
