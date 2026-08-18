from __future__ import annotations

import json
from pathlib import Path

import pytest

from mdstats.graphics3d.cli import main
from mdstats.graphics3d.config import (
    LTA_MIXED_ALKALI_PRESET,
    compile_graphics3d_config,
    load_graphics3d_toml,
    parse_layer_shorthand,
)
from mdstats.graphics3d.errors import Graphics3DValidationError


def test_layer_shorthand_compiles_to_typed_selection() -> None:
    layer = parse_layer_shorthand("density:Na@Na occupancy")
    assert layer.layer_type == "density"
    assert layer.name == "Na occupancy"
    assert layer.selection.species == ("Na",)

    pair = parse_layer_shorthand("connectivity:Na-O")
    assert pair.selection.pairs == (("O", "Na"),)


def test_layer_shorthand_rejects_mixed_pair_and_species() -> None:
    with pytest.raises(Graphics3DValidationError, match="cannot mix"):
        parse_layer_shorthand("connectivity:Na-O,Na")


def test_toml_layers_replace_preset_and_cli_layers_replace_toml(tmp_path: Path) -> None:
    config = tmp_path / "scene.toml"
    config.write_text(
        """
[scene]
preset = "lta-mixed-alkali-density"
title = "configured"

[[layer]]
type = "trajectory"
name = "Na paths"
selection = { species = ["Na"] }
""",
        encoding="utf-8",
    )
    payload = load_graphics3d_toml(config)
    compiled = compile_graphics3d_config(
        payload,
        present_species=("Si", "Al", "O", "Na"),
    )
    assert [layer.name for layer in compiled.request.layers] == ["Na paths"]
    overridden = compile_graphics3d_config(
        payload,
        present_species=("Si", "Al", "O", "Na"),
        cli_layers=("framework", "density:Na"),
    )
    assert [layer.layer_type for layer in overridden.request.layers] == ["framework", "density"]


def test_lta_preset_expands_only_present_density_species() -> None:
    compiled = compile_graphics3d_config(
        {},
        preset=LTA_MIXED_ALKALI_PRESET,
        present_species=("Si", "Al", "O", "Na"),
    )
    assert [layer.layer_type for layer in compiled.request.layers[:3]] == [
        "framework", "connectivity", "trajectory"
    ]
    densities = [layer for layer in compiled.request.layers if layer.layer_type == "density"]
    assert [layer.selection.species for layer in densities] == [
        ("Si",), ("Al",), ("O",), ("Na",)
    ]


def test_toml_unknown_keys_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[scene]\nunknown = 1\n", encoding="utf-8")
    with pytest.raises(Graphics3DValidationError, match=r"Unknown keys in GFX3D \[scene\]"):
        load_graphics3d_toml(path)
    path.write_text("mystery = 1\n", encoding="utf-8")
    with pytest.raises(Graphics3DValidationError, match="Unknown GFX3D TOML"):
        load_graphics3d_toml(path)


def _write_small_lammps_dump(path: Path) -> None:
    path.write_text(
        """ITEM: TIMESTEP
0
ITEM: TIME
0.0
ITEM: UNITS
metal
ITEM: NUMBER OF ATOMS
4
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Si 0.10 0.10 0.10 0 0 0
2 Al 0.20 0.10 0.10 0 0 0
3 O  0.15 0.10 0.10 0 0 0
4 Na 0.60 0.60 0.60 0 0 0
ITEM: TIMESTEP
1
ITEM: TIME
0.001
ITEM: UNITS
metal
ITEM: NUMBER OF ATOMS
4
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Si 0.10 0.10 0.10 0 0 0
2 Al 0.20 0.10 0.10 0 0 0
3 O  0.15 0.10 0.10 0 0 0
4 Na 0.61 0.60 0.60 0 0 0
""",
        encoding="utf-8",
    )


def test_manifest_only_is_source_aware_without_scientific_preparation(tmp_path: Path) -> None:
    dump = tmp_path / "dump.test.lammpstrj"
    manifest = tmp_path / "scene.json"
    _write_small_lammps_dump(dump)
    code = main(
        [
            str(dump),
            "--preset", LTA_MIXED_ALKALI_PRESET,
            "--manifest-only",
            "--manifest", str(manifest),
            "--quiet",
        ]
    )
    assert code == 0
    payload = json.loads(manifest.read_text())
    assert payload["schema_version"] == "mdstats.graphics3d.scene-manifest.v1"
    assert payload["resolved_input_format"] == "lammps-dump"
    assert payload["atom_species_mapping"]["present_species"] == ["Si", "Al", "O", "Na"]
    assert [layer["layer_type"] for layer in payload["ordered_layer_requests"][:3]] == [
        "framework", "connectivity", "trajectory"
    ]
    assert payload["expanded_presets"] == [LTA_MIXED_ALKALI_PRESET]


def test_manifest_only_refuses_overwrite_without_force(tmp_path: Path) -> None:
    dump = tmp_path / "dump.test.lammpstrj"
    manifest = tmp_path / "scene.json"
    _write_small_lammps_dump(dump)
    manifest.write_text("{}\n")
    code = main(
        [str(dump), "--layer", "framework", "--manifest-only", "--manifest", str(manifest), "--quiet"]
    )
    assert code == 2
    assert manifest.read_text() == "{}\n"
    code = main(
        [str(dump), "--layer", "framework", "--manifest-only", "--manifest", str(manifest), "--force", "--quiet"]
    )
    assert code == 0
