from __future__ import annotations

from pathlib import Path

import numpy as np

import mdstats


BASE_CELL = np.asarray(
    [
        [14.89726500, 0.0, 8.60093996],
        [4.96575500, 14.04527614, 8.60093996],
        [0.0, 0.0, 17.20187991],
    ],
    dtype=float,
)


def _axes(cell: np.ndarray) -> np.ndarray:
    a, b, c = cell
    conventional = np.asarray((b + c - a, a + c - b, a + b - c))
    return conventional / np.linalg.norm(conventional, axis=1)[:, None]


def _stretch(kind: str, value: float) -> np.ndarray:
    if kind == "hydro":
        return (1.0 + value) ** (1.0 / 3.0) * np.eye(3)
    axes = _axes(BASE_CELL)
    if kind == "ortho":
        aligned = np.diag((1.0 + value, 1.0 - value, 1.0 / (1.0 - value**2)))
    else:
        simple = np.eye(3)
        simple[0, 1] = value
        vals, vecs = np.linalg.eigh(simple.T @ simple)
        aligned = vecs @ np.diag(np.sqrt(vals)) @ vecs.T
    return axes.T @ aligned @ axes


def _basis(cell: np.ndarray) -> str:
    return "".join("<v>" + " ".join(f"{value:.12f}" for value in row) + "</v>" for row in cell)


def _write_xml(path: Path, cell: np.ndarray, *, temperature: float = 700.0, truncated: bool = False) -> None:
    content = f'''<modeling>
  <incar>
    <i name="IBRION" type="int">0</i>
    <i name="MDALGO" type="int">3</i>
    <i name="SMASS">-3</i>
    <i name="ISIF" type="int">2</i>
    <i name="POTIM">1.0</i>
    <i name="NSW" type="int">2</i>
    <i name="TEBEG">{temperature}</i>
    <i name="TEEND">{temperature}</i>
    <v name="LANGEVIN_GAMMA">5 5 5 5 5 5</v>
  </incar>
  <atominfo><array name="atoms"><set>
    <rc><c>Li</c></rc><rc><c>Na</c></rc><rc><c>K</c></rc>
    <rc><c>Al</c></rc><rc><c>Si</c></rc><rc><c>O</c></rc>
  </set></array></atominfo>
  <structure name="initialpos"><crystal><varray name="basis">{_basis(cell)}</varray></crystal></structure>
  <calculation><structure><crystal><varray name="basis">{_basis(cell)}</varray></crystal></structure></calculation>
  <calculation><structure><crystal><varray name="basis">{_basis(cell)}</varray></crystal></structure></calculation>
</modeling>'''
    if truncated:
        content = content.removesuffix("</modeling>")
    path.write_text(content, encoding="utf-8")


def test_lta_manifest_inference_verifies_all_six_profile_strains_and_percent_names(tmp_path: Path) -> None:
    _write_xml(tmp_path / "LTA_LiNaK.700K.init.xml", BASE_CELL)
    cases = (
        ("hydro+5.0", "hydro", +0.05),
        ("hydro-5", "hydro", -0.05),
        ("ortho+2", "ortho", +0.02),
        ("ortho-2", "ortho", -0.02),
        ("shear+2", "shear", +0.02),
        ("shear-2", "shear", -0.02),
    )
    for title, kind, value in cases:
        cell = BASE_CELL @ _stretch(kind, value).T
        _write_xml(tmp_path / f"LTA_LiNaK_strained.{title}.init.xml", cell)

    manifest = mdstats.discover_vasp_manifest(
        tmp_path, dataset_id="lta", system_profile="lta", pattern="**/*.xml"
    )
    result = mdstats.infer_training_manifest_metadata(manifest, base_directory=tmp_path)

    assert result.resolved_xml_metadata_runs == 7
    assert result.fixed_cell_runs == 7
    assert result.strain_candidate_runs == 6
    assert result.verified_strain_runs == 6
    assert result.rejected_strain_runs == 0
    assert result.warnings == ()

    reference = next(run for run in result.manifest.runs if run.run_id == "LTA_LiNaK.700K.init")
    assert reference.reference_group == "LTA_LiNaK_strain_family"
    assert dict(reference.assertions)["intended_strain_class"] == "unstrained"
    assert dict(reference.assertions)["ensemble"] == "nvt"
    assert dict(reference.assertions)["target_temperature_kelvin"] == 700.0

    plus_hydro = next(run for run in result.manifest.runs if "hydro__5.0" in run.run_id)
    assertions = dict(plus_hydro.assertions)
    inference = dict(plus_hydro.inference)
    assert assertions["intended_volume_change"] == 0.05
    assert plus_hydro.reference_run_id == reference.run_id
    assert inference["strain_candidate"]["value_interpretation"] == "percent_by_magnitude"
    assert inference["strain_verification"]["status"] == "passed"


def test_geometry_mismatch_rejects_operational_strain_assertions_and_reference_group(tmp_path: Path) -> None:
    _write_xml(tmp_path / "LTA_LiNaK.700K.init.xml", BASE_CELL)
    wrong_cell = BASE_CELL @ _stretch("shear", 0.02).T
    _write_xml(tmp_path / "LTA_LiNaK_strained.hydro+5.init.xml", wrong_cell)

    manifest = mdstats.discover_vasp_manifest(
        tmp_path, dataset_id="mismatch", system_profile="lta", pattern="**/*.xml"
    )
    result = mdstats.infer_training_manifest_metadata(manifest, base_directory=tmp_path)

    assert result.verified_strain_runs == 0
    assert result.rejected_strain_runs == 1
    assert result.warnings
    reference = next(run for run in result.manifest.runs if "strained" not in run.run_id)
    strained = next(run for run in result.manifest.runs if "strained" in run.run_id)
    assert reference.reference_group is None
    assert strained.reference_group is None
    assert strained.reference_run_id is None
    assert "intended_strain_class" not in dict(strained.assertions)
    assert dict(strained.inference)["strain_verification"]["status"] == "rejected"


def test_truncated_xml_still_yields_review_metadata_without_bypassing_later_source_gate(tmp_path: Path) -> None:
    _write_xml(tmp_path / "LTA_K.700K.init.xml", BASE_CELL, truncated=True)
    manifest = mdstats.discover_vasp_manifest(
        tmp_path, dataset_id="partial", system_profile="lta", pattern="**/*.xml"
    )
    result = mdstats.infer_training_manifest_metadata(manifest, base_directory=tmp_path)
    run = result.manifest.runs[0]
    assertions = dict(run.assertions)
    inference = dict(run.inference)["xml_metadata"]
    assert assertions["ensemble"] == "nvt"
    assert assertions["target_temperature_kelvin"] == 700.0
    assert assertions["fixed_cell"] is True
    assert inference["xml_parse_complete"] is False
    assert "partial vasprun.xml" in inference["xml_parse_warning"]


def test_manifest_run_v1_payload_remains_loadable() -> None:
    legacy = {
        "schema": "mdstats.training-data-run-spec.v1",
        "run_id": "legacy",
        "vasprun": "vasprun.xml",
        "companion_files": {},
        "reference_group": None,
        "replica_id": None,
        "reference_run_id": None,
        "assertions": {},
    }
    run = mdstats.TrainingDataRunSpec.from_dict(legacy)
    assert run.run_id == "legacy"
    assert run.inference == ()


def test_strained_filename_temperature_is_ignored_for_reference_identity_but_used_for_ranking(tmp_path: Path) -> None:
    _write_xml(tmp_path / "LTA_LiNaK.300K.init.xml", BASE_CELL, temperature=300.0)
    _write_xml(tmp_path / "LTA_LiNaK.700K.init.xml", BASE_CELL, temperature=700.0)
    strained_cell = BASE_CELL @ _stretch("hydro", 0.05).T
    _write_xml(
        tmp_path / "LTA_LiNaK_strained.hydro+5.600K.init.xml",
        strained_cell,
        temperature=600.0,
    )

    manifest = mdstats.discover_vasp_manifest(
        tmp_path, dataset_id="temperature-name", system_profile="lta", pattern="**/*.xml"
    )
    result = mdstats.infer_training_manifest_metadata(manifest, base_directory=tmp_path)

    strained = next(run for run in result.manifest.runs if "strained" in run.run_id)
    assert result.verified_strain_runs == 1
    assert strained.reference_run_id == "LTA_LiNaK.700K.init"



def test_refresh_removes_stale_automatic_reference_relationship_after_geometry_changes(tmp_path: Path) -> None:
    reference_path = tmp_path / "LTA_LiNaK.700K.init.xml"
    strained_path = tmp_path / "LTA_LiNaK_strained.hydro+5.init.xml"
    _write_xml(reference_path, BASE_CELL)
    _write_xml(strained_path, BASE_CELL @ _stretch("hydro", 0.05).T)
    manifest = mdstats.discover_vasp_manifest(
        tmp_path, dataset_id="refresh", system_profile="lta", pattern="**/*.xml"
    )
    first = mdstats.infer_training_manifest_metadata(manifest, base_directory=tmp_path)
    assert first.verified_strain_runs == 1
    assert any(run.reference_group for run in first.manifest.runs)

    # Relabel the actual cell as hydro while replacing it by shear. Refresh must
    # remove the previously promoted baseline relationship before rejecting it.
    _write_xml(strained_path, BASE_CELL @ _stretch("shear", 0.02).T)
    second = mdstats.infer_training_manifest_metadata(first.manifest, base_directory=tmp_path)
    assert second.verified_strain_runs == 0
    assert second.rejected_strain_runs == 1
    for run in second.manifest.runs:
        assert run.reference_group is None
        assert run.reference_run_id is None
        assert "intended_strain_class" not in dict(run.assertions)
