from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

import mdstats


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


def _write_long_vasprun(
    root: Path,
    run_id: str,
    *,
    n_frames: int = 48,
    position_offset: float = 0.0,
    force_event_frame: int | None = None,
) -> Path:
    directory = root / run_id
    directory.mkdir(parents=True)
    elements = ("Li", "O")
    gamma = "10 10"
    calculations: list[str] = []
    for index in range(n_frames):
        shift = position_offset + 0.001 * index
        positions = [(0.1 + shift, 0.1, 0.1), (0.5, 0.5, 0.5)]
        force = 3.0 if force_event_frame == index else 0.1 + 0.001 * index
        forces = [(force, 0.0, 0.0), (-force, 0.0, 0.0)]
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
    text = f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i><i name="subversion" type="string">test</i></generator>
  <incar>
    <i name="IBRION" type="int">0</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i>
    <v name="LANGEVIN_GAMMA">{gamma}</v><i name="GGA" type="string">PE</i>
    <i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i><i name="ISPIN" type="int">1</i>
    <i name="LDAU" type="logical">F</i><i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
    <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
  </incar>
  <kpoints><generation param="Gamma"><v name="divisions">1 1 1</v></generation>
    <varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters>
    <separator name="electronic"><i name="EDIFF">1e-5</i><i name="NELM" type="int">100</i>
      <i name="NELMIN" type="int">2</i><i name="ALGO" type="string">Normal</i>
      <i name="GGA" type="string">PE</i><i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i>
      <i name="ISPIN" type="int">1</i><i name="LDAU" type="logical">F</i><i name="ENCUT">520</i>
      <i name="LASPH" type="logical">T</i><i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
    </separator>
    <separator name="ionic"><i name="IBRION" type="int">0</i><i name="NSW" type="int">{n_frames}</i><i name="POTIM">1</i>
      <i name="TEBEG">700</i><i name="TEEND">700</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i>
      <i name="ISIF" type="int">2</i><i name="ISYM" type="int">0</i><v name="LANGEVIN_GAMMA">{gamma}</v>
    </separator>
  </parameters>
  {_atominfo(elements)}
  <structure name="initialpos"><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
    <varray name="positions"><v>0.1 0.1 0.1</v><v>0.5 0.5 0.5</v></varray></structure>
  {''.join(calculations)}
</modeling>'''
    path = directory / "vasprun.xml"
    path.write_text(text, encoding="utf-8")
    return path


def _manifest(
    root: Path,
    runs: tuple[str, ...],
    *,
    replicas: bool = False,
    structural_realizations: bool = False,
) -> mdstats.TrainingDataManifest:
    return mdstats.TrainingDataManifest(
        dataset_id="data5",
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=run,
                vasprun=f"{run}/vasprun.xml",
                reference_group="bulk",
                replica_id=f"replica-{index}" if replicas else None,
                assertions=(
                    (("regime", "production"), ("structural_realization_id", f"ordering-{index}"))
                    if structural_realizations
                    else (("regime", "production"),)
                ),
            )
            for index, run in enumerate(runs)
        ),
    )


def _policy(*, calibration: int = 1, purge: int = 0) -> mdstats.PartitionPolicy:
    return mdstats.PartitionPolicy(
        role_budget=mdstats.PartitionRoleBudgetPolicy(
            development_minimum_independent_units=4,
            outer_monitor_minimum_independent_units=1,
            calibration_minimum_independent_units=calibration,
            locked_interpolation_test_minimum_independent_units=1,
            cross_validation_folds=3,
            checkpoint_monitor_minimum_units_per_fold=1,
            purge_units_between_roles=purge,
            allow_calibration_deferral=True,
        ),
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=4,
            explicit_block_length_frames=4,
        ),
        minimum_units_per_condition_for_full_outer_roles=7,
    )


def _build(
    tmp_path: Path,
    *,
    runs: tuple[str, ...] = ("run",),
    replicas: bool = False,
    event_frame: int | None = 8,
    policy: mdstats.PartitionPolicy | None = None,
):
    for index, run in enumerate(runs):
        _write_long_vasprun(tmp_path, run, position_offset=0.2 * index, force_event_frame=event_frame)
    manifest = _manifest(tmp_path, runs, replicas=replicas)
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=(policy or _policy()).role_budget,
    )
    bundle = mdstats.build_data5_partition_bundle(
        sources,
        frames,
        data4,
        partition_policy=policy or _policy(),
    )
    return sources, frames, data4, bundle


def test_supplied_ase_and_real_vasp_to_data5(tmp_path: Path) -> None:
    import ase

    assert ase.__version__ == "3.29.0"
    _, _, _, bundle = _build(tmp_path)
    assert bundle.leakage_audit.passed
    assert bundle.feasibility_reports[0].is_usable
    assert len(bundle.outer_partitions[0].units_for(mdstats.OuterRole.LOCKED_INTERPOLATION_TEST)) >= 1
    assert len(bundle.cross_validation_plans[0].folds) == 3


def test_event_window_is_one_partition_unit(tmp_path: Path) -> None:
    _, _, data4, bundle = _build(tmp_path, event_frame=8)
    event = next(item for item in data4.events.events if item.event_type is mdstats.FrameEventType.FORCE_THRESHOLD)
    unit_ids = {
        unit.unit_id
        for unit in bundle.unit_catalog.units
        if set(unit.frame_uids) & set(event.protected_frame_uids)
    }
    assert len(unit_ids) == 1
    unit = bundle.unit_catalog.unit(next(iter(unit_ids)))
    assert unit.contains_protected_event_frames
    assert event.event_id in unit.event_ids


def test_outer_roles_folds_and_blinding_are_disjoint(tmp_path: Path) -> None:
    _, _, _, bundle = _build(tmp_path)
    outer = bundle.outer_partitions[0]
    all_outer = [unit_id for role in mdstats.OuterRole for unit_id in outer.units_for(role)]
    assert len(all_outer) == len(set(all_outer)) == len(bundle.unit_catalog.units)
    development = set(outer.units_for(mdstats.OuterRole.DEVELOPMENT))
    held_out = set()
    for fold in bundle.cross_validation_plans[0].folds:
        groups = [
            set(fold.training_unit_ids),
            set(fold.checkpoint_monitor_unit_ids),
            set(fold.evaluation_unit_ids),
            set(fold.purged_unit_ids),
        ]
        assert set().union(*groups) == development
        assert all(not groups[i] & groups[j] for i in range(4) for j in range(i + 1, 4))
        held_out |= set(fold.evaluation_unit_ids)
    assert held_out == development
    locked = bundle.blinding_boundaries.for_role(mdstats.OuterRole.LOCKED_INTERPOLATION_TEST)
    assert locked.access_for(mdstats.EvidenceOperation.RAW_GEOMETRY_ACCESS) is mdstats.EvidenceAccess.SEALED_UNTIL_PROTOCOL_FREEZE
    assert locked.access_for(mdstats.EvidenceOperation.LABEL_DERIVED_SELECTION) is mdstats.EvidenceAccess.FORBIDDEN


def test_replica_and_temporal_independence_grades(tmp_path: Path) -> None:
    _, _, _, temporal = _build(tmp_path / "temporal", runs=("run",), replicas=False)
    assert temporal.independence_reports[0].weakest_grade in {
        mdstats.IndependenceGrade.PURGED_TEMPORAL_BLOCK,
        mdstats.IndependenceGrade.SLOW_STATE_NOT_DECORRELATED,
    }
    _, _, _, replicated = _build(tmp_path / "replicas", runs=("a", "b"), replicas=True)
    assert all(
        unit.independence_grade is mdstats.IndependenceGrade.INDEPENDENT_REPLICA
        for unit in replicated.unit_catalog.units
    )


def test_calibration_can_be_deferred(tmp_path: Path) -> None:
    policy = mdstats.PartitionPolicy(
        role_budget=mdstats.PartitionRoleBudgetPolicy(
            development_minimum_independent_units=4,
            outer_monitor_minimum_independent_units=1,
            calibration_minimum_independent_units=5,
            locked_interpolation_test_minimum_independent_units=1,
            cross_validation_folds=3,
            checkpoint_monitor_minimum_units_per_fold=1,
            purge_units_between_roles=0,
            allow_calibration_deferral=True,
        ),
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=6,
            explicit_block_length_frames=6,
        ),
        require_condition_coverage_in_outer_roles=False,
    )
    _, _, _, bundle = _build(tmp_path, policy=policy)
    report = bundle.feasibility_reports[0]
    assert report.calibration_deferred
    assert report.outcome is mdstats.PartitionFeasibilityOutcome.CALIBRATION_DEFERRED
    assert not bundle.outer_partitions[0].units_for(mdstats.OuterRole.UNCERTAINTY_CALIBRATION)


def test_serialization_and_tamper_rejection(tmp_path: Path) -> None:
    _, _, _, bundle = _build(tmp_path)
    payload = bundle.to_dict()
    assert mdstats.Data5PartitionBundle.from_dict(payload) == bundle
    tampered = deepcopy(payload)
    tampered["unit_catalog"]["units"][0]["source_frame_stop"] += 1
    with pytest.raises((mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)):
        mdstats.Data5PartitionBundle.from_dict(tampered)



def test_independent_structural_realization_grade(tmp_path: Path) -> None:
    for index, run in enumerate(("a", "b")):
        _write_long_vasprun(tmp_path, run, position_offset=0.2 * index, force_event_frame=None)
    manifest = _manifest(tmp_path, ("a", "b"), structural_realizations=True)
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    policy = _policy()
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        partition_role_budget=policy.role_budget,
    )
    bundle = mdstats.build_data5_partition_bundle(
        sources,
        frames,
        data4,
        partition_policy=policy,
    )
    assert all(
        unit.independence_grade is mdstats.IndependenceGrade.INDEPENDENT_STRUCTURAL_REALIZATION
        for unit in bundle.unit_catalog.units
    )
    assert {unit.structural_realization_id for unit in bundle.unit_catalog.units} == {"ordering-0", "ordering-1"}


def test_leakage_audit_detects_missing_outer_purge(tmp_path: Path) -> None:
    policy = _policy(purge=1)
    _write_long_vasprun(tmp_path, "run", n_frames=80, force_event_frame=None)
    manifest = _manifest(tmp_path, ("run",))
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        partition_role_budget=policy.role_budget,
    )
    units = mdstats.build_partition_unit_catalog(sources, frames, data4, policy=policy)
    feasibility = mdstats.assess_partition_feasibility(units, policy=policy)
    outer = mdstats.build_outer_partitions(units, feasibility, policy=policy)[0]
    payload = outer.to_dict()
    changed = False
    for assignment in payload["assignments"]:
        if assignment["role"] == mdstats.OuterRole.PURGED.value:
            assignment["role"] = mdstats.OuterRole.DEVELOPMENT.value
            assignment.pop("content_digest", None)
            changed = True
            break
    assert changed
    payload.pop("content_digest", None)
    broken = mdstats.OuterPartition.from_dict(payload)
    report = mdstats.audit_partition_leakage(
        units,
        (broken,),
        (),
        frames,
        data4,
        partition_policy=policy,
    )
    assert not report.passed
    assert any(item.code == "missing_outer_purge_neighbor" for item in report.findings)


def test_copied_trajectory_leakage_fails_closed(tmp_path: Path) -> None:
    path_a = _write_long_vasprun(tmp_path, "a", force_event_frame=None)
    directory_b = tmp_path / "b"
    directory_b.mkdir()
    (directory_b / "vasprun.xml").write_bytes(path_a.read_bytes())
    manifest = _manifest(tmp_path, ("a", "b"), replicas=True)
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    policy = _policy()
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        partition_role_budget=policy.role_budget,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="leakage"):
        mdstats.build_data5_partition_bundle(
            sources,
            frames,
            data4,
            partition_policy=policy,
        )


def test_temporal_neighbor_index_matches_legacy_scan(tmp_path: Path) -> None:
    from mdstats.training_data.partition import (
        _build_temporal_neighbor_index,
        _neighbor_unit_ids,
    )

    # Reuse a production-shaped DATA5 catalog from the standard fixture helper.
    _sources, _frames, _data4, data5 = _build(tmp_path)
    units = data5.unit_catalog.units
    selected = {units[index].unit_id for index in range(0, len(units), 3)}

    def legacy(radius: int) -> set[str]:
        by_run: dict[str, list[object]] = {}
        for unit in units:
            by_run.setdefault(unit.run_id, []).append(unit)
        result: set[str] = set()
        for run_units in by_run.values():
            ordered = sorted(run_units, key=lambda item: item.source_frame_start)
            for position, unit in enumerate(ordered):
                if unit.unit_id not in selected:
                    continue
                first = max(0, position - radius)
                last = min(len(ordered), position + radius + 1)
                result.update(item.unit_id for item in ordered[first:last])
        return result - selected

    temporal_index = _build_temporal_neighbor_index(units)
    for radius in (0, 1, 2, 4):
        assert _neighbor_unit_ids(
            units,
            selected,
            radius,
            temporal_index=temporal_index,
        ) == legacy(radius)
