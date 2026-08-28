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
from mdstats.training_data.neutral_substrate import (
    CanonicalFrameAuthority,
    CanonicalFrameIdentity,
    CanonicalFrameRecord,
    LeakageSeverity,
    NeutralFeasibilityOutcome,
    NeutralFeasibilityReport,
    NeutralFeatureEvidence,
    NeutralIndependenceReport,
    NeutralLeakageFinding,
    NeutralLeakageReport,
    NeutralOuterPartition,
    NeutralPartitionConditionKey,
    NeutralPartitionPolicy,
    NeutralPartitionUnit,
    NeutralRoleAssignment,
    NeutralRoleBudget,
    NeutralStatisticalBase,
    NeutralUnitCatalog,
    SourceAuthority,
    SourceRecord,
    build_advisory_compatibility_report,
    build_canonical_frame_authority,
    build_canonical_frame_identity,
    build_independence_report,
    build_neutral_feature_evidence_from_data4_bundle,
    build_neutral_outer_partition,
    build_neutral_statistical_base,
    build_neutral_unit_catalog,
    build_provenance_diagnostics,
    build_source_authority,
    build_source_authority_from_data2_catalog,
    build_vasp_canonical_frame_authority,
    canonical_training_label_payload_digest,
    source_record_from_data2,
)
from mdstats.training_data.neutral_substrate import features as ns_features
from mdstats.training_data.neutral_substrate import frame_authority as ns_frames
from mdstats.training_data.neutral_substrate import identity as ns_identity
from mdstats.training_data.neutral_substrate import partition as ns_partition
from mdstats.training_data.neutral_substrate import sources as ns_sources


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
    nelm: int = 100,
    scf_steps_per_frame: int = 1,
    ismear: int = 0,
    isif: int = 2,
    gamma_l: float | None = None,
    pmass: float | None = None,
    ldau: bool = False,
    hybrid: bool = False,
    unresolved_gga: bool = False,
    position_offset: float = 0.0,
    force_event_frame: int | None = None,
    catastrophic_force: bool = False,
    tebeg: int = 700,
) -> str:
    calculations: list[str] = []
    for index in range(n_frames):
        shift = position_offset + 0.001 * index
        positions = [(0.1 + shift, 0.1, 0.1), (0.5, 0.5, 0.5)][: len(elements)]
        while len(positions) < len(elements):
            positions.append((0.2 * len(positions), 0.2, 0.2))
        if catastrophic_force:
            force = 500.0
        elif force_event_frame == index:
            force = 3.0
        else:
            force = 0.1 + 0.001 * index
        forces = [(force, 0.0, 0.0) if i == 0 else (-force if i == 1 else 0.0, 0.0, 0.0)
                  for i in range(len(elements))]
        energy = -10.0 + 0.01 * index
        scsteps = "".join(
            f'<scstep><energy><i name="e_fr_energy">{energy}</i><i name="e_0_energy">{energy + 0.1}</i></energy></scstep>'
            for _ in range(scf_steps_per_frame)
        )
        calculations.append(
            f'''<calculation>
    {scsteps}
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
    gamma_l_tag = f'<i name="LANGEVIN_GAMMA_L">{gamma_l}</i>' if gamma_l is not None else ""
    pmass_tag = f'<i name="PMASS">{pmass or 100.0}</i>' if (isif == 3 or pmass is not None) else ""
    return f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i><i name="subversion" type="string">test</i></generator>
  <incar>
    <i name="IBRION" type="int">0</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">{isif}</i>
    <v name="LANGEVIN_GAMMA">{gamma}</v>{gamma_l_tag}{pmass_tag}{gga_tag}
    <i name="ISMEAR" type="int">{ismear}</i><i name="SIGMA">0.05</i><i name="ISPIN" type="int">1</i>
    <i name="LDAU" type="logical">{ldau_flag}</i>{ldau_extra}{hybrid_tag}
    <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
    <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
  </incar>
  <kpoints><generation param="Gamma"><v name="divisions">1 1 1</v></generation>
    <varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters>
    <separator name="electronic"><i name="EDIFF">{ediff}</i><i name="NELM" type="int">{nelm}</i>
      <i name="NELMIN" type="int">2</i><i name="ALGO" type="string">Normal</i>
      {gga_tag}<i name="ISMEAR" type="int">{ismear}</i><i name="SIGMA">0.05</i>
      <i name="ISPIN" type="int">1</i><i name="LDAU" type="logical">{ldau_flag}</i>
      <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
      <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
    </separator>
    <separator name="ionic"><i name="IBRION" type="int">0</i><i name="NSW" type="int">{n_frames}</i><i name="POTIM">1</i>
      <i name="TEBEG">{tebeg}</i><i name="TEEND">{tebeg}</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i>
      <i name="ISIF" type="int">{isif}</i><i name="ISYM" type="int">0</i><v name="LANGEVIN_GAMMA">{gamma}</v>
      {gamma_l_tag}{pmass_tag}
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
    return digest({"fixture": "neutral-p1"})


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


def _neutral_policy() -> NeutralPartitionPolicy:
    return NeutralPartitionPolicy(
        role_budget=NeutralRoleBudget(
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


def _data4_bundle(tmp_path: Path, *, n_frames: int = 48, tebeg: int = 700, sub_dir: str = "run"):
    _write(
        tmp_path,
        sub_dir,
        ("Li", "O"),
        n_frames=n_frames,
        force_event_frame=8,
        tebeg=tebeg,
    )
    manifest = mdstats.TrainingDataManifest(
        dataset_id="neutral-p1",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id=sub_dir,
                vasprun=f"{sub_dir}/vasprun.xml",
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


def _build_full_neutral_chain(
    manifest: mdstats.TrainingDataManifest,
    tmp_path: Path,
    *,
    advisory_policy: mdstats.LabelCompatibilityPolicy | None = None,
    partition_policy: NeutralPartitionPolicy | None = None,
):
    source_cat = mdstats.build_training_data_source_catalog(
        manifest,
        base_directory=tmp_path,
        label_compatibility_policy=advisory_policy,
    )
    frames_cat, data4 = mdstats.build_vasp_data4_feature_bundle(
        source_cat,
        base_directory=tmp_path,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=_data4_role_budget(),
    )
    source_auth = build_source_authority_from_data2_catalog(
        source_cat, advisory_compatibility_policy=advisory_policy
    )
    frame_auth = build_vasp_canonical_frame_authority(
        source_auth,
        base_directory=tmp_path,
    )
    feature_ev = build_neutral_feature_evidence_from_data4_bundle(
        source_auth, frame_auth, data4
    )
    stat_base = build_neutral_statistical_base(
        source_auth, frame_auth, feature_ev, policy=partition_policy
    )
    return source_auth, frame_auth, feature_ev, stat_base


# =========================================================================
# Pass P1-B: Source Authority Tests
# =========================================================================


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
    authority = build_source_authority_from_data2_catalog(catalog)
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
    rebuilt = SourceAuthority.from_dict(json.loads(json.dumps(authority.to_dict())))
    assert rebuilt.content_digest == authority.content_digest
    assert rebuilt.advisory_compatibility == authority.advisory_compatibility
    assert authority.to_dict()["schema"] == "mdstats.source-authority.v1"


def test_p1b_grouping_policy_does_not_change_usable_membership_or_source_identity(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "li", ("Li", "O"), ediff=1.0e-5)
    _write(tmp_path, "na", ("Na", "O"), ediff=1.0e-6)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="grouping")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    default = build_source_authority_from_data2_catalog(catalog)
    split = build_source_authority_from_data2_catalog(
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
    record = source_record_from_data2(broken)
    assert record.target_usable is False
    assert "missing_required_energy_labels" in record.mechanical_rejection_codes
    empty_units = replace(
        source,
        selected_energy=replace(source.selected_energy, units=""),
    )
    unit_record = source_record_from_data2(empty_units)
    assert unit_record.target_usable is False
    assert "unconvertible_energy_channel" in unit_record.mechanical_rejection_codes


def test_p1b_source_facts_preservation(tmp_path: Path) -> None:
    """P1-B: SourceAuthority preserves composition, ensemble, quality facts, and timestep."""
    _write(tmp_path, "run_facts", ("Li", "O"), n_frames=4, tebeg=650)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="facts")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    authority = build_source_authority_from_data2_catalog(catalog)
    source = authority.source("run_facts")

    assert isinstance(source.composition, mdstats.SourceComposition)
    assert source.composition.atom_count == 2
    assert source.composition.reduced_formula == "LiO"
    assert source.composition.as_dict() == {"Li": 1, "O": 1}
    assert source.ensemble.lower() == "nvt"
    assert source.quality_assessment_status == catalog.source("run_facts").quality_assessment_status
    assert source.quality_outcome is None

    payload = json.loads(json.dumps(authority.to_dict()))
    rebuilt = SourceAuthority.from_dict(payload)
    assert rebuilt.content_digest == authority.content_digest
    r_source = rebuilt.source("run_facts")
    assert r_source.composition.atom_count == 2
    assert r_source.composition.as_dict() == {"Li": 1, "O": 1}
    assert r_source.ensemble.lower() == "nvt"
    assert r_source.quality_assessment_status == source.quality_assessment_status


def test_p1b_strict_deserialization_rejection(tmp_path: Path) -> None:
    """P1-B: Deserialization rejects missing required fields without synthesizing defaults."""
    _write(tmp_path, "run_strict", ("Li", "O"), n_frames=2)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="strict")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    authority = build_source_authority_from_data2_catalog(catalog)
    source = authority.source("run_strict")
    payload = source.to_dict()

    # Reject missing composition
    bad = dict(payload)
    del bad["composition"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'composition'"):
        SourceRecord.from_dict(bad)

    # Reject missing ensemble
    bad = dict(payload)
    del bad["ensemble"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'ensemble'"):
        SourceRecord.from_dict(bad)

    # Reject missing quality_assessment_status
    bad = dict(payload)
    del bad["quality_assessment_status"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'quality_assessment_status'"):
        SourceRecord.from_dict(bad)

    # Reject missing source_control_digest
    bad = dict(payload)
    del bad["source_control_digest"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'source_control_digest'"):
        SourceRecord.from_dict(bad)

    # Reject missing ensemble_certificate_digest
    bad = dict(payload)
    del bad["ensemble_certificate_digest"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'ensemble_certificate_digest'"):
        SourceRecord.from_dict(bad)

    # Reject invalid schema
    bad = dict(payload)
    bad["schema"] = "invalid.schema"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="Unsupported source-record schema"):
        SourceRecord.from_dict(bad)

    # Authority missing dataset_id
    auth_payload = authority.to_dict()
    bad_auth = dict(auth_payload)
    del bad_auth["dataset_id"]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="missing required field: 'dataset_id'"):
        SourceAuthority.from_dict(bad_auth)


# =========================================================================
# Pass P1-C: Canonical Label and Frame Authority Tests
# =========================================================================


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


def test_p1c_canonical_labels_reject_non_finite_numerics() -> None:
    # NaN in energy
    with pytest.raises(mdstats.TrainingDataInputError, match="energy_ev must be finite"):
        canonical_training_label_payload_digest(
            selected_energy_channel="e_fr_energy",
            energy_semantic_role="free_energy",
            energy_units="eV",
            energy_normalization="extensive",
            entropy_convention="electronic_entropy_included",
            energy_ev=float("nan"),
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=_digest(),
        )

    # Inf in energy
    with pytest.raises(mdstats.TrainingDataInputError, match="energy_ev must be finite"):
        canonical_training_label_payload_digest(
            selected_energy_channel="e_fr_energy",
            energy_semantic_role="free_energy",
            energy_units="eV",
            energy_normalization="extensive",
            entropy_convention="electronic_entropy_included",
            energy_ev=float("inf"),
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=_digest(),
        )

    # NaN in forces
    with pytest.raises(mdstats.TrainingDataInputError, match="forces must contain only finite values"):
        canonical_training_label_payload_digest(
            selected_energy_channel="e_fr_energy",
            energy_semantic_role="free_energy",
            energy_units="eV",
            energy_normalization="extensive",
            entropy_convention="electronic_entropy_included",
            energy_ev=-10.0,
            forces_ev_per_angstrom=np.asarray([[np.nan, 0.0, 0.0], [0.0, 0.0, 0.0]]),
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=_digest(),
        )

    # Inf in stress
    with pytest.raises(mdstats.TrainingDataInputError, match="stress must contain only finite values"):
        canonical_training_label_payload_digest(
            selected_energy_channel="e_fr_energy",
            energy_semantic_role="free_energy",
            energy_units="eV",
            energy_normalization="extensive",
            entropy_convention="electronic_entropy_included",
            energy_ev=-10.0,
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=np.full((3, 3), np.inf),
            derivative_convention_digest=_digest(),
        )


def test_p1c_canonical_frame_authority_from_real_arrays(tmp_path: Path) -> None:
    """Test canonical frame authority constructed from real VASP/FrameData arrays."""
    _write(tmp_path, "run_real", ("Li", "O"), n_frames=8, tebeg=600)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="canonical-real",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_real",
                vasprun="run_real/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)

    assert frame_auth.source_authority_digest == source_auth.content_digest
    assert len(frame_auth.frames) == 8
    assert frame_auth.to_dict()["schema"] == "mdstats.canonical-frame-authority.v1"
    assert "label_domain_id" not in json.dumps(frame_auth.to_dict())

    # Verify that canonical label digests were computed from actual array values
    first_frame = frame_auth.frames[0]
    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    path = tmp_path / "run_real/vasprun.xml"
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")
    expected_digest = canonical_training_label_payload_digest(
        selected_energy_channel="e_fr_energy",
        energy_semantic_role=source_auth.source("run_real").selected_energy_semantic_role,
        energy_units=source_auth.source("run_real").selected_energy_units,
        energy_normalization="extensive",
        entropy_convention="electronic_entropy_included",
        energy_ev=channel.as_array()[0],
        forces_ev_per_angstrom=collection.forces[0],
        stress_ev_per_angstrom3=collection.stresses[0],
        derivative_convention_digest=source_auth.source("run_real").electronic_structure.derivative_convention.content_digest,
    )
    assert first_frame.canonical_label_payload_digest == expected_digest

    rebuilt = CanonicalFrameAuthority.from_dict(json.loads(json.dumps(frame_auth.to_dict())))
    assert rebuilt.content_digest == frame_auth.content_digest
    assert rebuilt == frame_auth


def test_p1c_composition_and_atom_count_mismatch_rejected(tmp_path: Path) -> None:
    """P1-C: FrameData with atom count or composition mismatch against SourceAuthority is rejected."""
    _write(tmp_path, "run_mismatch", ("Li", "O"), n_frames=4)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="mismatch",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_mismatch",
                vasprun="run_mismatch/vasprun.xml",
                reference_group="bulk",
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)

    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    path = tmp_path / "run_mismatch/vasprun.xml"
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")

    # Mismatched atom count
    bad_count_frame_data = {
        "run_mismatch": mdstats.FrameData(
            frame_ids=np.arange(collection.n_frames, dtype=np.int64),
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            steps=np.arange(collection.n_frames, dtype=np.int64),
            times_ps=np.zeros(collection.n_frames, dtype=np.float64),
            atomic_numbers=np.asarray([3, 8, 8], dtype=np.int32),  # 3 atoms vs source count 2
            pbc=np.asarray([True, True, True]),
            cells_angstrom=collection.cells,
            fractional_positions=np.zeros((collection.n_frames, 3, 3), dtype=np.float64),
            energies_ev=channel.as_array(),
            forces_ev_per_angstrom=np.zeros((collection.n_frames, 3, 3), dtype=np.float64),
            stresses_ev_per_angstrom3=collection.stresses,
            temperatures_kelvin=np.full(collection.n_frames, 300.0),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    with pytest.raises(mdstats.TrainingDataInputError, match="Atom count mismatch"):
        build_canonical_frame_authority(source_auth, bad_count_frame_data)

    # Mismatched composition (same count 2, but Na + O instead of Li + O)
    bad_comp_frame_data = {
        "run_mismatch": mdstats.FrameData(
            frame_ids=np.arange(collection.n_frames, dtype=np.int64),
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            steps=np.arange(collection.n_frames, dtype=np.int64),
            times_ps=np.zeros(collection.n_frames, dtype=np.float64),
            atomic_numbers=np.asarray([11, 8], dtype=np.int32),  # Na, O instead of Li, O
            pbc=np.asarray([True, True, True]),
            cells_angstrom=collection.cells,
            fractional_positions=np.zeros((collection.n_frames, 2, 3), dtype=np.float64),
            energies_ev=channel.as_array(),
            forces_ev_per_angstrom=np.zeros((collection.n_frames, 2, 3), dtype=np.float64),
            stresses_ev_per_angstrom3=collection.stresses,
            temperatures_kelvin=np.full(collection.n_frames, 300.0),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    with pytest.raises(mdstats.TrainingDataInputError, match="Composition mismatch"):
        build_canonical_frame_authority(source_auth, bad_comp_frame_data)


def test_p1c_ensemble_and_quality_propagation(tmp_path: Path) -> None:
    """P1-C: Real source ensemble and source quality status reach temperature/strain and eligibility."""
    _write(tmp_path, "run_prop", ("Li", "O"), n_frames=4, tebeg=700)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="prop",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_prop",
                vasprun="run_prop/vasprun.xml",
                reference_group="bulk",
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)

    from mdstats.io import read_vasp_frames, read_vasp_run_controls
    path = tmp_path / "run_prop/vasprun.xml"
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")

    frame_data = {
        "run_prop": mdstats.FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=channel.as_array(),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }

    # 1. Test ensemble propagation
    source_auth_npt = replace(
        source_auth,
        sources=(replace(source_auth.sources[0], ensemble="npt"),),
    )
    frame_auth_npt = build_canonical_frame_authority(source_auth_npt, frame_data)
    assert frame_auth_npt.temperature_conditions.for_run("run_prop").ensemble == "npt"
    assert frame_auth_npt.strain_records[0].context_class == mdstats.StrainContextClass.VARIABLE_CELL_FLUCTUATION

    # 2. Test quality status propagation
    source_auth_failed = replace(
        source_auth,
        sources=(replace(source_auth.sources[0], quality_assessment_status="failed", quality_outcome="unqualified"),),
    )
    frame_auth_failed = build_canonical_frame_authority(source_auth_failed, frame_data)
    for dec in frame_auth_failed.eligibility.decisions:
        assert dec.state == mdstats.FrameEligibilityState.INELIGIBLE
        assert "source_trajectory_unqualified" in dec.reason_codes


def test_p1c_parallel_worker_equivalence(tmp_path: Path) -> None:
    """P1-C: Canonical frame authority construction is bit-for-bit identical across worker counts."""
    _write(tmp_path, "run_p1", ("Li", "O"), n_frames=4)
    _write(tmp_path, "run_p2", ("Na", "O"), n_frames=4)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="par-equiv")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)

    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    frame_data = {}
    for s in source_auth.sources:
        path = tmp_path / s.source_locator
        collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
        bundle = read_vasp_run_controls(path)
        channel = bundle.energy_catalog.channel(s.selected_energy_channel)
        frame_data[s.run_id] = mdstats.FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=channel.as_array(),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )

    auth_seq = build_canonical_frame_authority(source_auth, frame_data, parallel_workers=1)
    auth_par = build_canonical_frame_authority(source_auth, frame_data, parallel_workers=2)

    assert auth_seq.content_digest == auth_par.content_digest
    assert auth_seq == auth_par


def test_p1c_required_label_ordering_and_authority_precedence(tmp_path: Path) -> None:
    """P1-C: Required-label validity precedes label authority while preserving physical frame existence."""
    _write(tmp_path, "run_prec", ("Li", "O"), n_frames=2)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="precedence")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)

    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    path = tmp_path / "run_prec/vasprun.xml"
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")

    # Frame 0: valid energy (-10.0), Frame 1: missing energy (None)
    # Set identical fractional positions so geometry fingerprints match exactly
    positions = np.zeros((2, 2, 3), dtype=np.float64)
    positions[0] = [[0.1, 0.1, 0.1], [0.5, 0.5, 0.5]]
    positions[1] = [[0.1, 0.1, 0.1], [0.5, 0.5, 0.5]]

    energies_partial = np.asarray([-10.0, np.nan], dtype=np.float64)  # NaN for frame 1
    # FrameData with stresses=None (to test optional vs required stress)
    frame_data = {
        "run_prec": mdstats.FrameData(
            frame_ids=np.arange(2, dtype=np.int64),
            source_frame_indices=np.arange(2, dtype=np.int64),
            steps=np.arange(2, dtype=np.int64),
            times_ps=np.zeros(2, dtype=np.float64),
            atomic_numbers=np.asarray([3, 8], dtype=np.int32),
            pbc=np.asarray([True, True, True]),
            cells_angstrom=collection.cells[:2],
            fractional_positions=positions,
            energies_ev=energies_partial,
            forces_ev_per_angstrom=collection.forces[:2],
            stresses_ev_per_angstrom3=None,
            temperatures_kelvin=np.full(2, 300.0),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached[:2],
        )
    }

    # 1. Under default policy (energy required, stress optional):
    frame_auth = build_canonical_frame_authority(source_auth, frame_data)

    f0 = frame_auth.frames[0]
    f1 = frame_auth.frames[1]

    # Frame 0 has valid energy -> has authoritative label
    assert f0.has_authoritative_label is True
    assert f0.canonical_label_payload_digest is not None
    assert f0.labeled_configuration_fingerprint is not None

    # Frame 1 has non-finite/missing energy -> NO authoritative label
    assert f1.has_authoritative_label is False
    assert f1.canonical_label_payload_digest is None
    assert f1.labeled_configuration_fingerprint is None

    # But Frame 1 still exists as a physical frame with occurrence and geometry identity
    assert f1.frame_uid is not None
    assert f1.geometry_fingerprint == f0.geometry_fingerprint
    assert frame_auth.eligibility.for_frame(f1.frame_uid).state == mdstats.FrameEligibilityState.INELIGIBLE

    # Geometry duplicates group both frames together, but labeled duplicates group 0 frames
    assert len(frame_auth.duplicates.geometry_groups) == 1
    assert len(frame_auth.duplicates.geometry_groups[0].frame_uids) == 2
    assert len(frame_auth.duplicates.labeled_groups) == 0

    # 2. Stress requirement test:
    # When stress is REQUIRED and stress is absent, Frame 0 loses label authority:
    req_stress_policy = mdstats.FrameEligibilityPolicy(
        stress_requirement=mdstats.StressRequirement.REQUIRED
    )
    frame_auth_req_stress = build_canonical_frame_authority(
        source_auth, frame_data, eligibility_policy=req_stress_policy
    )
    assert frame_auth_req_stress.frames[0].has_authoritative_label is False
    assert frame_auth_req_stress.frames[0].canonical_label_payload_digest is None

    # 3. Serialization durability of frame authority with un-labeled frames:
    payload = json.loads(json.dumps(frame_auth.to_dict()))
    rebuilt = CanonicalFrameAuthority.from_dict(payload)
    assert rebuilt.content_digest == frame_auth.content_digest
    assert rebuilt.frames[1].has_authoritative_label is False
    assert rebuilt.frames[1].canonical_label_payload_digest is None


# =========================================================================
# Pass P1-D: Neutral Feature Evidence and Statistical Base Tests
# =========================================================================


def test_p1d_neutral_feature_evidence_assembly_and_round_trip(tmp_path: Path) -> None:
    _manifest, sources, _frames, data4 = _data4_bundle(tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)
    feature_ev = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4)

    assert feature_ev.source_authority_digest == source_auth.content_digest
    assert feature_ev.frame_authority_digest == frame_auth.content_digest
    assert feature_ev.raw_features.source_catalog_digest == source_auth.content_digest
    assert feature_ev.raw_features.frame_catalog_digest == frame_auth.content_digest
    assert feature_ev.events.frame_catalog_digest == frame_auth.content_digest

    payload = json.loads(json.dumps(feature_ev.to_dict()))
    rebuilt = NeutralFeatureEvidence.from_dict(payload)
    assert rebuilt.content_digest == feature_ev.content_digest
    assert feature_ev.to_dict()["schema"] == "mdstats.neutral-feature-evidence.v1"


def test_p1d_lta_typed_profile_rebinding(tmp_path: Path) -> None:
    """Test typed rebinding of LtaPartitionFeatureCatalog to canonical frame authority."""
    _manifest, sources, legacy_frames, data4 = _data4_bundle(tmp_path, n_frames=16)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)

    policy = mdstats.LtaPartitionProfilePolicy()
    lta_records = tuple(
        mdstats.LtaFramePartitionRecord(
            frame_uid=f.frame_uid,
            frame_record_digest=f.content_digest,  # legacy DATA3 digest
            policy_digest=policy.policy_digest,
            profile_status=mdstats.LtaProfileStatus.RESOLVED,
            framework_integrity=True,
            site_classes_present=("ring_8_on_center",),
            ring_sizes_present=(8,),
            coordination_change=False,
            site_change=False,
            ring_crossing=False,
            mobile_state_count=0,
        )
        for f in legacy_frames.frames
    )
    legacy_lta = mdstats.LtaPartitionFeatureCatalog(
        dataset_id=legacy_frames.dataset_id,
        frame_catalog_digest=legacy_frames.content_digest,
        policy=policy,
        frame_records=lta_records,
        mobile_states=(),
    )
    wrapped_legacy = mdstats.wrap_lta_partition_features(legacy_lta)

    # Put wrapped_legacy into data4 with matching event linkage
    events_with_lta = replace(
        data4.events, profile_feature_catalog_digests=(wrapped_legacy.content_digest,)
    )
    data4_with_lta = replace(
        data4, profile_partition_features=(wrapped_legacy,), events=events_with_lta
    )

    # Rebind through NeutralFeatureEvidence
    feature_ev = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4_with_lta)
    assert len(feature_ev.profile_partition_features) == 1
    rebound_wrapper = feature_ev.profile_partition_features[0]

    assert rebound_wrapper.frame_catalog_digest == frame_auth.content_digest
    typed_rebound = rebound_wrapper.as_lta_partition()
    assert typed_rebound.frame_catalog_digest == frame_auth.content_digest
    assert rebound_wrapper.scientific_payload_digest == typed_rebound.content_digest

    # Verify each frame record has canonical frame record digest
    for r in typed_rebound.frame_records:
        assert r.frame_record_digest == frame_auth.frame(r.frame_uid).content_digest

    # Verify profile_partition_state_changed executes on rebound payload
    uids = [f.frame_uid for f in frame_auth.frames]
    changed = mdstats.profile_partition_state_changed(feature_ev.profile_partition_features, uids)
    assert changed is False

    # Round trip and restart durability
    rebuilt = NeutralFeatureEvidence.from_dict(json.loads(json.dumps(feature_ev.to_dict())))
    assert rebuilt.content_digest == feature_ev.content_digest
    rebuilt_typed = rebuilt.profile_partition_features[0].as_lta_partition()
    assert rebuilt_typed.frame_catalog_digest == frame_auth.content_digest
    assert mdstats.profile_partition_state_changed(rebuilt.profile_partition_features, uids) is False


def test_p1d_generic_profile_dispatch_and_unsupported_rejection(tmp_path: Path) -> None:
    """P1-D: Generic provider dispatch rejects unsupported opaque providers explicitly."""
    _manifest, sources, legacy_frames, data4 = _data4_bundle(tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)

    unsupported_profile = mdstats.ProfileFeatureCatalog(
        extension_id="unregistered_custom",
        stage=mdstats.ProfileFeatureStage.PARTITION,
        provider_identity=mdstats.MaterialProfileProviderIdentity(
            provider_id="mdstats.profile.custom.partition",
            provider_version="1.0",
            configuration_digest=_digest(),
        ),
        frame_catalog_digest=legacy_frames.content_digest,
        payload_schema="mdstats.custom.v1",
        payload={"dummy": 123, "content_digest": _digest()},
    )
    events_unsupported = replace(
        data4.events, profile_feature_catalog_digests=(unsupported_profile.content_digest,)
    )
    profile = mdstats.build_single_phase_material_profile(
        profile_id="unregistered-custom-profile",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        extensions=("unregistered_custom",),
    )
    contracts = mdstats.build_material_profile_contracts(profile)
    data4_unsupported = replace(
        data4,
        material_profile_contracts=contracts,
        profile_partition_features=(unsupported_profile,),
        events=events_unsupported,
    )

    with pytest.raises(
        mdstats.TrainingDataInputError,
        match="Unsupported partition-stage material-profile provider: 'unregistered_custom'",
    ):
        build_neutral_feature_evidence_from_data4_bundle(
            source_auth, frame_auth, data4_unsupported
        )


def test_p1d_neutral_statistical_base_assembled_chain_and_round_trip(tmp_path: Path) -> None:
    _manifest, sources, _frames, data4 = _data4_bundle(tmp_path)
    policy = _neutral_policy()
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)
    feature_ev = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4)
    base = build_neutral_statistical_base(source_auth, frame_auth, feature_ev, policy=policy)

    payload = json.loads(json.dumps(base.to_dict()))
    rebuilt = NeutralStatisticalBase.from_dict(payload)
    assert rebuilt.content_digest == base.content_digest
    assert "label_domain_id" not in json.dumps(base.to_dict())
    assert "cross_validation" not in json.dumps(base.to_dict())
    assert "fold" not in json.dumps(base.to_dict())

    # Lineage verification
    assert base.unit_catalog.source_authority_digest == source_auth.content_digest
    assert base.unit_catalog.frame_authority_digest == frame_auth.content_digest
    assert base.unit_catalog.feature_evidence_digest == feature_ev.content_digest

    # Disjointness of protected roles
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

    assert base.leakage.passed is True
    assert base.leakage.error_count == 0

    for unit in base.unit_catalog.units:
        assert unit.correlation_group_id == unit.unit_id
        assert not hasattr(unit.condition, "label_domain_id")


def test_p1d_neutral_base_rejects_legacy_and_mismatched_authorities(tmp_path: Path) -> None:
    _manifest, sources, legacy_frames, data4 = _data4_bundle(tmp_path)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)
    feature_ev = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4)

    # Reject passing legacy DATA2/DATA3/DATA4 objects
    with pytest.raises(mdstats.TrainingDataInputError, match="SourceAuthority"):
        build_neutral_statistical_base(sources, frame_auth, feature_ev)

    with pytest.raises(mdstats.TrainingDataInputError, match="CanonicalFrameAuthority"):
        build_neutral_statistical_base(source_auth, legacy_frames, feature_ev)

    with pytest.raises(mdstats.TrainingDataInputError, match="NeutralFeatureEvidence"):
        build_neutral_statistical_base(source_auth, frame_auth, data4)

    # Reject mismatched lineage
    tampered_source = replace(source_auth, manifest_digest=_digest())
    with pytest.raises(mdstats.TrainingDataInputError, match="Frame authority does not match"):
        build_neutral_unit_catalog(tampered_source, frame_auth, feature_ev)


# =========================================================================
# Pass P1-E: Package Acceptance Tests
# =========================================================================


def test_p1e_real_owner_integration(tmp_path: Path) -> None:
    """P1-E1: Required real-owner integration through the actual P1 owner chain."""
    _write(tmp_path, "run_e1", ("Li", "O"), n_frames=32, tebeg=650)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="p1-e1",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_e1",
                vasprun="run_e1/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    auth, frame, feat, base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )

    assert isinstance(auth, SourceAuthority)
    assert isinstance(frame, CanonicalFrameAuthority)
    assert isinstance(feat, NeutralFeatureEvidence)
    assert isinstance(base, NeutralStatisticalBase)

    assert frame.source_authority_digest == auth.content_digest
    assert feat.source_authority_digest == auth.content_digest
    assert feat.frame_authority_digest == frame.content_digest
    assert base.unit_catalog.source_authority_digest == auth.content_digest
    assert base.unit_catalog.frame_authority_digest == frame.content_digest
    assert base.unit_catalog.feature_evidence_digest == feat.content_digest


def test_p1e_compatibility_policy_invariance_proof(tmp_path: Path) -> None:
    """P1-E2: Changing advisory compatibility grouping policy leaves all scientific identities identical."""
    _write(tmp_path, "li", ("Li", "O"), n_frames=32, tebeg=600, ediff=1.0e-5)
    _write(tmp_path, "na", ("Na", "O"), n_frames=32, tebeg=700, ediff=1.0e-6)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="invariance-proof",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="li",
                vasprun="li/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
            mdstats.TrainingDataRunSpec(
                run_id="na",
                vasprun="na/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    policy = _neutral_policy()

    # Build chain under default policy
    auth1, frame1, feat1, base1 = _build_full_neutral_chain(
        manifest, tmp_path, advisory_policy=None, partition_policy=policy
    )

    # Build chain under split policy (which creates different advisory groups)
    split_policy = mdstats.LabelCompatibilityPolicy(
        numerical_differences_are_quality_flags=False,
        software_differences_are_quality_flags=False,
    )
    auth2, frame2, feat2, base2 = _build_full_neutral_chain(
        manifest, tmp_path, advisory_policy=split_policy, partition_policy=policy
    )

    # Advisory reports must differ
    assert auth1.advisory_compatibility.policy_digest != auth2.advisory_compatibility.policy_digest
    assert auth1.advisory_compatibility.source_group_ids != auth2.advisory_compatibility.source_group_ids

    # Every scientific identity across the assembled chain MUST BE IDENTICAL:
    assert auth1.content_digest == auth2.content_digest
    assert auth1.target_usable_run_ids == auth2.target_usable_run_ids
    assert [s.content_digest for s in auth1.sources] == [s.content_digest for s in auth2.sources]

    assert frame1.content_digest == frame2.content_digest
    assert [f.content_digest for f in frame1.frames] == [f.content_digest for f in frame2.frames]
    assert [f.canonical_label_payload_digest for f in frame1.frames] == [
        f.canonical_label_payload_digest for f in frame2.frames
    ]
    assert frame1.duplicates.content_digest == frame2.duplicates.content_digest

    assert feat1.content_digest == feat2.content_digest

    assert base1.unit_catalog.content_digest == base2.unit_catalog.content_digest
    assert [u.content_digest for u in base1.unit_catalog.units] == [
        u.content_digest for u in base2.unit_catalog.units
    ]
    assert base1.outer_partition.content_digest == base2.outer_partition.content_digest
    assert base1.content_digest == base2.content_digest


def test_p1e_assembled_numerical_change_sensitivity_proof(tmp_path: Path) -> None:
    """P1-E3: Assembled numerical-change sensitivity proof through the real builder."""
    _manifest, sources, _frames, data4 = _data4_bundle(tmp_path, n_frames=48)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth1 = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)
    feature_ev1 = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth1, data4)
    stat_base1 = build_neutral_statistical_base(source_auth, frame_auth1, feature_ev1, policy=_neutral_policy())

    from mdstats.io import read_vasp_frames, read_vasp_run_controls
    path = tmp_path / "run/vasprun.xml"
    bundle = read_vasp_run_controls(path)
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    channel = bundle.energy_catalog.channel("e_fr_energy")

    # 1. Mutate energy on frame 0
    energies_mod = channel.as_array().copy()
    energies_mod[0] = -99.9  # change frame 0 energy
    frame_data_e = {
        "run": mdstats.FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=energies_mod,
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    frame_auth_e = build_canonical_frame_authority(source_auth, frame_data_e)
    feature_ev_e = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth_e, data4)
    stat_base_e = build_neutral_statistical_base(source_auth, frame_auth_e, feature_ev_e, policy=_neutral_policy())

    assert frame_auth1.frames[0].canonical_label_payload_digest != frame_auth_e.frames[0].canonical_label_payload_digest
    assert frame_auth1.frames[0].labeled_configuration_fingerprint != frame_auth_e.frames[0].labeled_configuration_fingerprint
    assert frame_auth1.frames[1].canonical_label_payload_digest == frame_auth_e.frames[1].canonical_label_payload_digest
    assert frame_auth1.content_digest != frame_auth_e.content_digest
    assert feature_ev1.content_digest != feature_ev_e.content_digest
    assert stat_base1.content_digest != stat_base_e.content_digest

    # 2. Mutate forces on frame 0
    forces_mod = collection.forces.copy()
    forces_mod[0, 0, 0] += 2.5
    frame_data_f = {
        "run": mdstats.FrameData(
            frame_ids=np.arange(collection.n_frames, dtype=np.int64),
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            steps=np.arange(collection.n_frames, dtype=np.int64),
            times_ps=collection.times,
            atomic_numbers=np.asarray([3, 8], dtype=np.int32),
            pbc=np.asarray([True, True, True]),
            cells_angstrom=collection.cells,
            fractional_positions=collection.fractional_positions,
            energies_ev=channel.as_array(),
            forces_ev_per_angstrom=forces_mod,
            stresses_ev_per_angstrom3=collection.stresses,
            temperatures_kelvin=collection.temperatures,
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    frame_auth_f = build_canonical_frame_authority(source_auth, frame_data_f)
    feature_ev_f = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth_f, data4)
    stat_base_f = build_neutral_statistical_base(source_auth, frame_auth_f, feature_ev_f, policy=_neutral_policy())

    assert frame_auth1.frames[0].canonical_label_payload_digest != frame_auth_f.frames[0].canonical_label_payload_digest
    assert frame_auth1.frames[0].labeled_configuration_fingerprint != frame_auth_f.frames[0].labeled_configuration_fingerprint
    assert frame_auth1.frames[1].canonical_label_payload_digest == frame_auth_f.frames[1].canonical_label_payload_digest
    assert frame_auth1.content_digest != frame_auth_f.content_digest
    assert feature_ev1.content_digest != feature_ev_f.content_digest
    assert stat_base1.content_digest != stat_base_f.content_digest

    # 3. Non-finite value: frame loses label authority while retaining geometry/physical identity
    energies_nan = channel.as_array().copy()
    energies_nan[0] = np.nan
    frame_data_nan = {
        "run": mdstats.FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=energies_nan,
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    frame_auth_nan = build_canonical_frame_authority(source_auth, frame_data_nan)
    assert frame_auth_nan.frames[0].has_authoritative_label is False
    assert frame_auth_nan.frames[0].canonical_label_payload_digest is None
    assert frame_auth_nan.frames[0].labeled_configuration_fingerprint is None
    assert frame_auth_nan.frames[0].geometry_fingerprint == frame_auth1.frames[0].geometry_fingerprint
    assert frame_auth_nan.frames[0].frame_uid == frame_auth1.frames[0].frame_uid
    assert frame_auth_nan.eligibility.for_frame(frame_auth_nan.frames[0].frame_uid).state == mdstats.FrameEligibilityState.INELIGIBLE


def test_p1e_unresolved_provenance_assembled_proof(tmp_path: Path) -> None:
    """P1-E4: Unresolved provenance traverses the full current-generation owner chain without label_domain_id."""
    _write(tmp_path, "unresolved_run", ("Li", "O"), n_frames=32, unresolved_gga=True, tebeg=700)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="unresolved-assembled",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="unresolved_run",
                vasprun="unresolved_run/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(
        manifest,
        base_directory=tmp_path,
        source_policy=mdstats.SourceAuditPolicy(fail_on_unresolved_label_domain=False),
    )
    source_auth = build_source_authority_from_data2_catalog(sources)
    assert "unresolved_run" in source_auth.provenance_diagnostics.unresolved_or_partial_source_ids

    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)
    assert len(frame_auth.frames) == 32
    assert "label_domain_id" not in json.dumps(frame_auth.to_dict())

    path = tmp_path / "unresolved_run/vasprun.xml"
    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")
    frame_data = {
        "unresolved_run": mdstats.FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=channel.as_array(),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    raw = mdstats.build_raw_feature_catalog(source_auth, frame_auth, frame_data)
    events = mdstats.detect_full_resolution_events(
        frame_auth,
        raw,
        policy=mdstats.EventDetectionPolicy(pre_frames=1, post_frames=1),
    )
    feature_ev = NeutralFeatureEvidence(
        dataset_id=frame_auth.dataset_id,
        source_authority_digest=source_auth.content_digest,
        frame_authority_digest=frame_auth.content_digest,
        raw_features=raw,
        events=events,
    )
    stat_base = build_neutral_statistical_base(source_auth, frame_auth, feature_ev, policy=_neutral_policy())

    assert stat_base.leakage.passed is True
    assert stat_base.leakage.error_count == 0


def test_p1e_source_fact_preservation_proof(tmp_path: Path) -> None:
    """P1-E4: Source-fact preservation proof: real NPT inference, real unqualified status, control binding, and composition mismatch."""
    # 1. Real VASP NPT ensemble inference end-to-end
    _write(tmp_path, "run_npt", ("Li", "O"), n_frames=8, isif=3, gamma_l=10.0, tebeg=750)
    manifest_npt = mdstats.TrainingDataManifest(
        dataset_id="npt-proof",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_npt",
                vasprun="run_npt/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    catalog_npt = mdstats.build_training_data_source_catalog(manifest_npt, base_directory=tmp_path)
    source_auth_npt = build_source_authority_from_data2_catalog(catalog_npt)
    assert source_auth_npt.source("run_npt").ensemble.upper() == "NPT"

    frame_auth_npt = build_vasp_canonical_frame_authority(source_auth_npt, base_directory=tmp_path)
    assert frame_auth_npt.temperature_conditions.for_run("run_npt").ensemble.upper() == "NPT"
    assert frame_auth_npt.strain_records[0].context_class == mdstats.StrainContextClass.VARIABLE_CELL_FLUCTUATION

    # 2. Real unconverged VASP XML quality assessment end-to-end
    _write(tmp_path, "run_unconv", ("Li", "O"), n_frames=8, catastrophic_force=True, tebeg=700)
    manifest_u = mdstats.TrainingDataManifest(
        dataset_id="unconv-proof",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run_unconv",
                vasprun="run_unconv/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    catalog_u = mdstats.build_training_data_source_catalog(
        manifest_u,
        base_directory=tmp_path,
        source_policy=mdstats.SourceAuditPolicy(
            trajectory_assessment_mode=mdstats.SourceTrajectoryAssessmentMode.FULL_REQUIRED,
            fail_on_unresolved_label_domain=False,
        ),
    )
    source_u = catalog_u.source("run_unconv")
    assert source_u.quality_outcome == "unqualified"
    source_auth_u = build_source_authority_from_data2_catalog(catalog_u)
    assert source_auth_u.source("run_unconv").quality_outcome == "unqualified"

    frame_auth_u = build_vasp_canonical_frame_authority(source_auth_u, base_directory=tmp_path)
    for dec in frame_auth_u.eligibility.decisions:
        assert dec.state == mdstats.FrameEligibilityState.INELIGIBLE
        assert "source_trajectory_unqualified" in dec.reason_codes

    # 3. Source control-binding mismatch rejection in direct rebuild
    mismatched_source = replace(source_auth_npt.sources[0], source_control_digest=_digest())
    mismatched_auth = replace(source_auth_npt, sources=(mismatched_source,))
    with pytest.raises(mdstats.TrainingDataInputError, match="Source control interpretation mismatch"):
        build_vasp_canonical_frame_authority(mismatched_auth, base_directory=tmp_path)

    # 4. Composition mismatch rejection
    from mdstats.io import read_vasp_frames, read_vasp_run_controls
    path = tmp_path / "run_npt/vasprun.xml"
    collection = read_vasp_frames(path, strict=True, assess_quality=False, assess_stationarity=False, assess_admissibility=False)
    bundle = read_vasp_run_controls(path)
    channel = bundle.energy_catalog.channel("e_fr_energy")

    bad_frame_data = {
        "run_npt": mdstats.FrameData(
            frame_ids=np.arange(collection.n_frames, dtype=np.int64),
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            steps=np.arange(collection.n_frames, dtype=np.int64),
            times_ps=np.zeros(collection.n_frames, dtype=np.float64),
            atomic_numbers=np.asarray([3, 8, 8], dtype=np.int32),  # 3 atoms vs source count 2
            pbc=np.asarray([True, True, True]),
            cells_angstrom=collection.cells,
            fractional_positions=np.zeros((collection.n_frames, 3, 3), dtype=np.float64),
            energies_ev=channel.as_array(),
            forces_ev_per_angstrom=np.zeros((collection.n_frames, 3, 3), dtype=np.float64),
            stresses_ev_per_angstrom3=collection.stresses,
            temperatures_kelvin=np.full(collection.n_frames, 300.0),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
    }
    with pytest.raises(mdstats.TrainingDataInputError, match="Atom count mismatch"):
        build_canonical_frame_authority(source_auth_npt, bad_frame_data)


def test_p1e_material_profile_genericity_lta_and_restart_proof(tmp_path: Path) -> None:
    """P1-E6: Material-profile genericity, LTA typed provider rebinding, and durable restart proof."""
    # 1. AST check: neutral features.py does NOT contain if extension_id == 'lta'
    features_src = inspect.getsource(ns_features)
    assert 'extension_id == "lta"' not in features_src
    assert "extension_id == 'lta'" not in features_src

    # 2. LTA provider execution through generic dispatch
    _manifest, sources, legacy_frames, data4 = _data4_bundle(tmp_path, n_frames=48)
    source_auth = build_source_authority_from_data2_catalog(sources)
    frame_auth = build_vasp_canonical_frame_authority(source_auth, base_directory=tmp_path)

    policy = mdstats.LtaPartitionProfilePolicy()
    lta_records = tuple(
        mdstats.LtaFramePartitionRecord(
            frame_uid=f.frame_uid,
            frame_record_digest=f.content_digest,
            policy_digest=policy.policy_digest,
            profile_status=mdstats.LtaProfileStatus.RESOLVED,
            framework_integrity=True,
            site_classes_present=("ring_8_on_center",),
            ring_sizes_present=(8,),
            coordination_change=False,
            site_change=False,
            ring_crossing=False,
            mobile_state_count=0,
        )
        for f in legacy_frames.frames
    )
    legacy_lta = mdstats.LtaPartitionFeatureCatalog(
        dataset_id=legacy_frames.dataset_id,
        frame_catalog_digest=legacy_frames.content_digest,
        policy=policy,
        frame_records=lta_records,
        mobile_states=(),
    )
    wrapped_legacy = mdstats.wrap_lta_partition_features(legacy_lta)
    events_with_lta = replace(
        data4.events, profile_feature_catalog_digests=(wrapped_legacy.content_digest,)
    )
    data4_with_lta = replace(
        data4, profile_partition_features=(wrapped_legacy,), events=events_with_lta
    )

    feature_ev = build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4_with_lta)
    rebound_wrapper = feature_ev.profile_partition_features[0]

    # Verify typed lineage
    assert rebound_wrapper.frame_catalog_digest == frame_auth.content_digest
    typed_rebound = rebound_wrapper.as_lta_partition()
    assert typed_rebound.frame_catalog_digest == frame_auth.content_digest
    for r in typed_rebound.frame_records:
        assert r.frame_record_digest == frame_auth.frame(r.frame_uid).content_digest

    # 3. Serialization and restart durability
    payload = json.loads(json.dumps(feature_ev.to_dict()))
    restarted = NeutralFeatureEvidence.from_dict(payload)
    assert restarted.content_digest == feature_ev.content_digest
    restarted_typed = restarted.profile_partition_features[0].as_lta_partition()
    assert restarted_typed.frame_catalog_digest == frame_auth.content_digest

    uids = [f.frame_uid for f in frame_auth.frames]
    assert mdstats.profile_partition_state_changed(restarted.profile_partition_features, uids) is False

    # 4. Rebuilding NeutralStatisticalBase from restarted evidence
    stat_base = build_neutral_statistical_base(source_auth, frame_auth, restarted, policy=_neutral_policy())
    assert stat_base.leakage.passed is True

    # 5. Unsupported opaque provider is rejected
    unsupported = mdstats.ProfileFeatureCatalog(
        extension_id="unsupported_polymer",
        stage=mdstats.ProfileFeatureStage.PARTITION,
        provider_identity=mdstats.MaterialProfileProviderIdentity(
            provider_id="mdstats.profile.polymer.partition",
            provider_version="1.0",
            configuration_digest=_digest(),
        ),
        frame_catalog_digest=legacy_frames.content_digest,
        payload_schema="mdstats.polymer.v1",
        payload={"dummy": 1, "content_digest": _digest()},
    )
    profile = mdstats.build_single_phase_material_profile(
        profile_id="unsupported-polymer-profile",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        extensions=("unsupported_polymer",),
    )
    contracts = mdstats.build_material_profile_contracts(profile)
    data4_bad = replace(
        data4,
        material_profile_contracts=contracts,
        profile_partition_features=(unsupported,),
        events=replace(data4.events, profile_feature_catalog_digests=(unsupported.content_digest,)),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="Unsupported partition-stage material-profile provider"):
        build_neutral_feature_evidence_from_data4_bundle(source_auth, frame_auth, data4_bad)


def test_p1e_invalid_adapter_absence_proof() -> None:
    """P1-E7: Structurally prove absence of build_canonical_frame_authority_from_data3_catalog."""
    import mdstats.training_data.neutral_substrate as ns

    assert not hasattr(ns, "build_canonical_frame_authority_from_data3_catalog")
    assert not hasattr(ns_frames, "build_canonical_frame_authority_from_data3_catalog")


def test_p1e_naming_and_absence_proof() -> None:
    """P1-E8: Structurally verify that new code and schemas contain no v7_/V7 architecture prefix."""
    import mdstats.training_data.neutral_substrate as ns

    for symbol in dir(ns):
        if symbol.startswith("_"):
            continue
        assert not symbol.startswith("v7_"), f"Symbol {symbol} starts with v7_"
        assert not symbol.startswith("V7"), f"Symbol {symbol} starts with V7"
        assert not symbol.startswith("build_v7_"), f"Symbol {symbol} starts with build_v7_"

    for mod in (ns, ns_sources, ns_identity, ns_frames, ns_features, ns_partition):
        src = inspect.getsource(mod)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            assert "mdstats.v7-" not in line, f"Found mdstats.v7- schema in {mod.__name__}: {line}"
            assert "build_v7_" not in line, f"Found build_v7_ in {mod.__name__}: {line}"
            assert "V7Source" not in line, f"Found V7Source in {mod.__name__}: {line}"
            assert "V7Neutral" not in line, f"Found V7Neutral in {mod.__name__}: {line}"
            assert "V7Frame" not in line, f"Found V7Frame in {mod.__name__}: {line}"


def test_p1e_runtime_isolation_proof(tmp_path: Path) -> None:
    """P1-E8: Verify that current prepare/select-target-size runtime remains isolated from neutral substrate."""
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

    assert "neutral_substrate" not in training_init
    assert "neutral_substrate" not in campaign
    assert "neutral_substrate" not in core
    assert "neutral_substrate" not in public


