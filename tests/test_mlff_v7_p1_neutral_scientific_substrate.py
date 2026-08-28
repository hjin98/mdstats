from __future__ import annotations

import inspect
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import _campaign_cli_core, campaign_cli
from mdstats.training_data._common import digest
from mdstats.training_data.identity import label_payload_digest
from mdstats.training_data.v7_neutral_substrate import (
    V7FrameIdentity,
    V7FrameIdentityCatalog,
    V7NeutralPartitionPolicy,
    V7NeutralRoleBudget,
    V7NeutralStatisticalBase,
    V7SourceAuthority,
    build_v7_frame_identity,
    build_v7_frame_identity_catalog,
    build_v7_neutral_statistical_base,
    build_v7_source_authority_from_data2_catalog,
    canonical_training_label_payload_digest,
    v7_source_record_from_data2,
)
from mdstats.training_data.v7_neutral_substrate import identity as v7_identity
from mdstats.training_data.v7_neutral_substrate import partition as v7_partition
from mdstats.training_data.v7_neutral_substrate import sources as v7_sources


def _atominfo(elements: tuple[str, ...]) -> str:
    unique = list(dict.fromkeys(elements))
    type_index = {symbol: index + 1 for index, symbol in enumerate(unique)}
    atoms = "".join(
        f"<rc><c>{symbol}</c><c>{type_index[symbol]}</c></rc>" for symbol in elements
    )
    types = "".join(
        f"<rc><c>{elements.count(symbol)}</c><c>{symbol}</c><c>1.0</c><c>1</c>"
        f"<c>PAW_PBE {symbol} test</c></rc>"
        for symbol in unique
    )
    return (
        f'<atominfo><atoms>{len(elements)}</atoms><types>{len(unique)}</types>'
        f'<array name="atoms"><set>{atoms}</set></array>'
        f'<array name="atomtypes"><set>{types}</set></array></atominfo>'
    )


def _vectors(values: list[tuple[float, float, float]]) -> str:
    return "".join(f"<v>{x:.12g} {y:.12g} {z:.12g}</v>" for x, y, z in values)


def _vasprun(
    elements: tuple[str, ...],
    *,
    n_frames: int = 2,
    gga: str = "PE",
    ediff: float = 1.0e-5,
    ismear: int = 0,
    ldau: bool = False,
    hybrid: bool = False,
    unresolved_gga: bool = False,
    position_offset: float = 0.0,
    force_event_frame: int | None = None,
    tebeg: int = 700,
) -> str:
    calculations: list[str] = []
    for index in range(n_frames):
        shift = position_offset + 0.001 * index
        positions = [(0.1 + shift, 0.1, 0.1), (0.5, 0.5, 0.5)][: len(elements)]
        while len(positions) < len(elements):
            positions.append((0.2 * len(positions), 0.2, 0.2))
        force = 3.0 if force_event_frame == index else 0.1 + 0.001 * index
        forces = [(force, 0.0, 0.0) if i == 0 else (-force if i == 1 else 0.0, 0.0, 0.0)
                  for i in range(len(elements))]
        energy = -10.0 + 0.01 * index
        calculations.append(
            f'''<calculation>
    <scstep><energy><i name="e_fr_energy">{energy}</i><i name="e_0_energy">{energy + 0.1}</i></energy></scstep>
    <structure><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
      <varray name="positions">{_vectors(positions)}</varray></structure>
    <varray name="forces">{_vectors(forces)}</varray>
    <varray name="stress"><v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v></varray>
    <energy><i name="e_fr_energy">{energy}</i><i name="e_0_energy">{energy + 0.1}</i><i name="e_wo_entrp">{energy + 0.05}</i>
      <i name="kinetic">0.5</i><i name="nosepot">0</i><i name="nosekinetic">0</i>
      <i name="lattice kinetic">0</i><i name="total">{energy + 0.5}</i></energy>
  </calculation>'''
        )
    gamma = " ".join("10" for _ in sorted(set(elements)))
    gga_tag = "" if unresolved_gga else f'<i name="GGA" type="string">{gga}</i>'
    ldau_flag = "T" if ldau else "F"
    ldau_extra = (
        '<i name="LDAUTYPE" type="int">2</i><v name="LDAUL">-1 2</v>'
        '<v name="LDAUU">0 4</v><v name="LDAUJ">0 0</v>'
        if ldau
        else ""
    )
    hybrid_tag = '<i name="LHFCALC" type="logical">T</i><i name="AEXX">0.25</i>' if hybrid else ""
    return f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i><i name="subversion" type="string">test</i></generator>
  <incar>
    <i name="IBRION" type="int">0</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i>
    <v name="LANGEVIN_GAMMA">{gamma}</v>{gga_tag}
    <i name="ISMEAR" type="int">{ismear}</i><i name="SIGMA">0.05</i><i name="ISPIN" type="int">1</i>
    <i name="LDAU" type="logical">{ldau_flag}</i>{ldau_extra}{hybrid_tag}
    <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
    <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
  </incar>
  <kpoints><generation param="Gamma"><v name="divisions">1 1 1</v></generation>
    <varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters>
    <separator name="electronic"><i name="EDIFF">{ediff}</i><i name="NELM" type="int">100</i>
      <i name="NELMIN" type="int">2</i><i name="ALGO" type="string">Normal</i>
      {gga_tag}<i name="ISMEAR" type="int">{ismear}</i><i name="SIGMA">0.05</i>
      <i name="ISPIN" type="int">1</i><i name="LDAU" type="logical">{ldau_flag}</i>
      <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
      <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
    </separator>
    <separator name="ionic"><i name="IBRION" type="int">0</i><i name="NSW" type="int">{n_frames}</i><i name="POTIM">1</i>
      <i name="TEBEG">{tebeg}</i><i name="TEEND">{tebeg}</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i>
      <i name="ISIF" type="int">2</i><i name="ISYM" type="int">0</i><v name="LANGEVIN_GAMMA">{gamma}</v>
    </separator>
  </parameters>
  {_atominfo(elements)}
  <structure name="initialpos"><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
    <varray name="positions">{_vectors([(0.1, 0.1, 0.1)] * len(elements))}</varray></structure>
  {''.join(calculations)}
</modeling>'''


def _write(root: Path, name: str, elements: tuple[str, ...], **kwargs) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    path = directory / "vasprun.xml"
    path.write_text(_vasprun(elements, **kwargs), encoding="utf-8")
    return path


def _digest() -> str:
    return digest({"fixture": "v7-p1"})


def _identity_kwargs(**overrides):
    payload = {
        "run_id": "run-a",
        "source_locator": "run-a/vasprun.xml",
        "source_identity_signature": _digest(),
        "source_frame_index": 0,
        "atomic_numbers": np.asarray([3, 8], dtype=np.int64),
        "pbc": np.asarray([True, True, True]),
        "cell": np.eye(3) * 10.0,
        "fractional_positions": np.asarray([[0.1, 0.1, 0.1], [0.5, 0.5, 0.5]]),
        "selected_energy_channel": "e_fr_energy",
        "energy_semantic_role": "free_energy",
        "energy_units": "eV",
        "energy_normalization": "extensive",
        "entropy_convention": "electronic_entropy_included",
        "energy_ev": -10.0,
        "forces_ev_per_angstrom": np.asarray([[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]]),
        "stress_ev_per_angstrom3": -100.0 * np.eye(3),
        "derivative_convention_digest": _digest(),
        "electronic_structure_fingerprint_digest": digest({"xc": "pbe"}),
    }
    payload.update(overrides)
    return payload


def _neutral_policy() -> V7NeutralPartitionPolicy:
    return V7NeutralPartitionPolicy(
        role_budget=V7NeutralRoleBudget(
            development_minimum_independent_units=4,
            outer_monitor_minimum_independent_units=1,
            calibration_minimum_independent_units=1,
            locked_interpolation_test_minimum_independent_units=1,
            purge_units_between_roles=0,
            allow_calibration_deferral=True,
        ),
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=4,
            explicit_block_length_frames=4,
        ),
        minimum_units_per_condition_for_full_outer_roles=7,
    )


def _data4_role_budget() -> mdstats.PartitionRoleBudgetPolicy:
    return mdstats.PartitionRoleBudgetPolicy(
        development_minimum_independent_units=4,
        outer_monitor_minimum_independent_units=1,
        calibration_minimum_independent_units=1,
        locked_interpolation_test_minimum_independent_units=1,
        cross_validation_folds=3,
        checkpoint_monitor_minimum_units_per_fold=1,
        purge_units_between_roles=0,
        allow_calibration_deferral=True,
    )


def _data4_bundle(tmp_path: Path, *, n_frames: int = 48, tebeg: int = 700):
    _write(
        tmp_path,
        "run",
        ("Li", "O"),
        n_frames=n_frames,
        force_event_frame=8,
        tebeg=tebeg,
    )
    manifest = mdstats.TrainingDataManifest(
        dataset_id="v7-p1",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run",
                vasprun="run/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=_data4_role_budget(),
    )
    return manifest, sources, frames, data4


def test_p1b_mixed_provenance_is_usable_and_unresolved_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "dft", ("Li", "O"))
    _write(tmp_path, "dftu", ("Li", "O"), ldau=True)
    _write(tmp_path, "hybrid", ("Li", "O"), hybrid=True)
    _write(tmp_path, "smear", ("Li", "O"), ismear=1)
    _write(tmp_path, "quality", ("Li", "O"), ediff=1.0e-6)
    _write(tmp_path, "unresolved", ("Li", "O"), unresolved_gga=True)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="mixed")
    catalog = mdstats.build_training_data_source_catalog(
        manifest,
        base_directory=tmp_path,
        source_policy=mdstats.SourceAuditPolicy(fail_on_unresolved_label_domain=False),
    )
    assert catalog.source("unresolved").label_domain_id is None
    authority = build_v7_source_authority_from_data2_catalog(catalog)
    assert set(authority.target_usable_run_ids) == {
        "dft",
        "dftu",
        "hybrid",
        "smear",
        "quality",
        "unresolved",
    }
    fingerprints = {item.electronic_structure.content_digest for item in authority.sources}
    assert len(fingerprints) >= 5
    assert "unresolved" in authority.provenance_diagnostics.unresolved_or_partial_source_ids
    assert "dft_u" in authority.provenance_diagnostics.varying_dimensions
    assert "hybrid" in authority.provenance_diagnostics.varying_dimensions
    rebuilt = V7SourceAuthority.from_dict(json.loads(json.dumps(authority.to_dict())))
    assert rebuilt.content_digest == authority.content_digest
    assert rebuilt.advisory_compatibility == authority.advisory_compatibility


def test_p1b_grouping_policy_does_not_change_usable_membership_or_source_identity(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "li", ("Li", "O"), ediff=1.0e-5)
    _write(tmp_path, "na", ("Na", "O"), ediff=1.0e-6)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="grouping")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    default = build_v7_source_authority_from_data2_catalog(catalog)
    split = build_v7_source_authority_from_data2_catalog(
        catalog,
        advisory_compatibility_policy=mdstats.LabelCompatibilityPolicy(
            numerical_differences_are_quality_flags=False,
        ),
    )
    assert default.target_usable_run_ids == split.target_usable_run_ids
    assert [item.content_digest for item in default.sources] == [
        item.content_digest for item in split.sources
    ]
    assert default.content_digest == split.content_digest
    assert default.advisory_compatibility.policy_digest != split.advisory_compatibility.policy_digest
    assert "label_domain_id" not in json.dumps(default.to_dict())


def test_p1b_missing_energy_is_mechanically_unusable(tmp_path: Path) -> None:
    _write(tmp_path, "run", ("Li", "O"))
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="energy")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source = catalog.source("run")
    broken = replace(
        source,
        selected_energy=replace(source.selected_energy, present_count=0),
    )
    record = v7_source_record_from_data2(broken)
    assert record.target_usable is False
    assert "missing_required_energy_labels" in record.mechanical_rejection_codes
    empty_units = replace(
        source,
        selected_energy=replace(source.selected_energy, units=""),
    )
    unit_record = v7_source_record_from_data2(empty_units)
    assert unit_record.target_usable is False
    assert "unconvertible_energy_channel" in unit_record.mechanical_rejection_codes


def test_p1c_canonical_labels_ignore_provenance_and_grouping() -> None:
    left = canonical_training_label_payload_digest(
        selected_energy_channel="e_fr_energy",
        energy_semantic_role="free_energy",
        energy_units="eV",
        energy_normalization="extensive",
        entropy_convention="electronic_entropy_included",
        energy_ev=-10.0,
        forces_ev_per_angstrom=np.asarray([[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]]),
        stress_ev_per_angstrom3=-100.0 * np.eye(3),
        derivative_convention_digest=_digest(),
    )
    right = canonical_training_label_payload_digest(
        selected_energy_channel="e_fr_energy",
        energy_semantic_role="free_energy",
        energy_units="eV",
        energy_normalization="extensive",
        entropy_convention="electronic_entropy_included",
        energy_ev=-10.0,
        forces_ev_per_angstrom=np.asarray([[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]]),
        stress_ev_per_angstrom3=-100.0 * np.eye(3),
        derivative_convention_digest=_digest(),
    )
    assert left == right
    changed = canonical_training_label_payload_digest(
        selected_energy_channel="e_fr_energy",
        energy_semantic_role="free_energy",
        energy_units="eV",
        energy_normalization="extensive",
        entropy_convention="electronic_entropy_included",
        energy_ev=-9.5,
        forces_ev_per_angstrom=np.asarray([[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]]),
        stress_ev_per_angstrom3=-100.0 * np.eye(3),
        derivative_convention_digest=_digest(),
    )
    assert changed != left
    with pytest.raises(mdstats.TrainingDataInputError, match="energy_units"):
        canonical_training_label_payload_digest(
            selected_energy_channel="e_fr_energy",
            energy_semantic_role="free_energy",
            energy_units="",
            energy_normalization="extensive",
            entropy_convention="electronic_entropy_included",
            energy_ev=-10.0,
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=_digest(),
        )
    assert "label_domain_id" not in inspect.signature(
        canonical_training_label_payload_digest
    ).parameters
    assert "label_domain_id" in inspect.signature(label_payload_digest).parameters
    with pytest.raises(mdstats.TrainingDataInputError, match="label_domain_id"):
        label_payload_digest(
            label_domain_id="",
            selected_energy_channel="e_fr_energy",
            energy_ev=-10.0,
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=_digest(),
        )


def test_p1c_frame_identity_and_duplicates_round_trip() -> None:
    first = build_v7_frame_identity(**_identity_kwargs())
    same_labels_other_provenance = build_v7_frame_identity(
        **_identity_kwargs(electronic_structure_fingerprint_digest=digest({"xc": "pbe+u"}))
    )
    assert first.canonical_label_payload_digest == (
        same_labels_other_provenance.canonical_label_payload_digest
    )
    assert first.labeled_configuration_fingerprint == (
        same_labels_other_provenance.labeled_configuration_fingerprint
    )
    assert first.electronic_structure_fingerprint_digest != (
        same_labels_other_provenance.electronic_structure_fingerprint_digest
    )
    other_run = build_v7_frame_identity(
        **_identity_kwargs(run_id="run-b", source_locator="run-b/vasprun.xml", source_frame_index=0)
    )
    assert first.geometry_fingerprint == other_run.geometry_fingerprint
    catalog = build_v7_frame_identity_catalog(
        (first, other_run),
        source_frame_counts={"run-a": 2, "run-b": 2},
    )
    assert catalog.duplicates.geometry_groups
    rebuilt = V7FrameIdentityCatalog.from_dict(json.loads(json.dumps(catalog.to_dict())))
    assert rebuilt == catalog
    assert first.to_dict()["schema"] == "mdstats.v7-frame-identity.v1"
    assert "label_domain_id" not in json.dumps(first.to_dict())
    assert V7FrameIdentity.from_dict(first.to_dict()) == first


def test_p1d_neutral_base_has_no_domain_or_cv_and_round_trips(tmp_path: Path) -> None:
    _manifest, sources, frames, data4 = _data4_bundle(tmp_path)
    policy = _neutral_policy()
    base = build_v7_neutral_statistical_base(sources, frames, data4, policy=policy)
    payload = json.loads(json.dumps(base.to_dict()))
    rebuilt = V7NeutralStatisticalBase.from_dict(payload)
    assert rebuilt.content_digest == base.content_digest
    assert "label_domain_id" not in json.dumps(base.to_dict())
    assert "cross_validation" not in json.dumps(base.to_dict())
    assert "fold" not in json.dumps(base.to_dict())
    protected = {
        mdstats.OuterRole.DEVELOPMENT,
        mdstats.OuterRole.OUTER_MONITOR,
        mdstats.OuterRole.UNCERTAINTY_CALIBRATION,
        mdstats.OuterRole.LOCKED_INTERPOLATION_TEST,
    }
    occupied: dict[mdstats.OuterRole, set[str]] = {role: set() for role in protected}
    for assignment in base.outer_partition.assignments:
        if assignment.role in protected:
            occupied[assignment.role].add(assignment.unit_id)
    for left in protected:
        for right in protected:
            if left is right:
                continue
            assert occupied[left].isdisjoint(occupied[right])
    for unit in base.unit_catalog.units:
        assert unit.correlation_group_id == unit.unit_id
        assert not hasattr(unit.condition, "label_domain_id")
    relabeled = build_v7_neutral_statistical_base(
        sources,
        frames,
        data4,
        policy=policy,
        user_labels_by_frame_uid={
            item.frame_uid: {"user_condition": "shifted"} for item in frames.frames
        },
    )
    assert {unit.unit_id for unit in relabeled.unit_catalog.units} != {
        unit.unit_id for unit in base.unit_catalog.units
    }


def test_p1d_grouping_policy_does_not_change_neutral_units(tmp_path: Path) -> None:
    manifest, sources, frames, data4 = _data4_bundle(tmp_path)
    policy = _neutral_policy()
    first = build_v7_neutral_statistical_base(sources, frames, data4, policy=policy)
    split_sources = mdstats.build_training_data_source_catalog(
        manifest,
        base_directory=tmp_path,
        label_compatibility_policy=mdstats.LabelCompatibilityPolicy(
            numerical_differences_are_quality_flags=False,
            software_differences_are_quality_flags=False,
        ),
    )
    split_frames, split_data4 = mdstats.build_vasp_data4_feature_bundle(
        split_sources,
        base_directory=tmp_path,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=_data4_role_budget(),
    )
    second = build_v7_neutral_statistical_base(
        split_sources, split_frames, split_data4, policy=policy
    )
    assert {unit.unit_id for unit in first.unit_catalog.units} == {
        unit.unit_id for unit in second.unit_catalog.units
    }
    assert {
        (item.unit_id, item.role.value) for item in first.outer_partition.assignments
    } == {
        (item.unit_id, item.role.value) for item in second.outer_partition.assignments
    }


def test_p1e_v7_is_unreachable_from_public_runtime_and_old_data2_still_assigns_domains(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "li", ("Li", "O"), ediff=1.0e-5)
    _write(tmp_path, "na", ("Na", "O"), ediff=1.0e-6)
    _write(tmp_path, "k_lda", ("K", "O"), gga="91")
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="legacy")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    assert catalog.source("li").label_domain_id == catalog.source("na").label_domain_id
    assert catalog.source("k_lda").label_domain_id != catalog.source("li").label_domain_id
    public = json.dumps(list(getattr(mdstats, "__all__", ())))
    training_init = Path(mdstats.training_data.__file__).read_text(encoding="utf-8")
    campaign = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    core = Path(_campaign_cli_core.__file__).read_text(encoding="utf-8")
    assert "v7_neutral_substrate" not in training_init
    assert "v7_neutral_substrate" not in campaign
    assert "v7_neutral_substrate" not in core
    assert "v7_neutral_substrate" not in public
    identity_src = inspect.getsource(v7_identity)
    partition_src = inspect.getsource(v7_partition)
    sources_src = inspect.getsource(v7_sources)
    assert "label_domain_id" not in identity_src
    assert "label_domain_id" not in partition_src
    assert "label_domain_id" not in sources_src
    assert "cross_validation" not in partition_src.lower()
    assert "cross_validation_folds" not in inspect.getsource(V7NeutralRoleBudget)
