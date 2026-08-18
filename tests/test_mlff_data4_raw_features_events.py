from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from ase.data import atomic_numbers

import mdstats
from tests.test_mlff_data2_source_catalog import _write


def _frame_data(
    atomic_number_sequence: tuple[int, ...],
    positions: np.ndarray,
    *,
    cell: np.ndarray,
    forces: np.ndarray | None = None,
    stresses: np.ndarray | None = None,
    temperatures: tuple[float, float] = (700.0, 705.0),
) -> mdstats.FrameData:
    n_frames, n_atoms, _ = positions.shape
    assert n_frames == 2 and n_atoms == len(atomic_number_sequence)
    return mdstats.FrameData(
        source_frame_indices=np.arange(n_frames, dtype=np.int64),
        frame_ids=np.arange(n_frames, dtype=np.int64),
        steps=np.arange(n_frames, dtype=np.int64),
        times_ps=np.arange(n_frames, dtype=np.float64) * 0.001,
        atomic_numbers=np.asarray(atomic_number_sequence, dtype=np.int32),
        pbc=np.array([True, True, True]),
        cells_angstrom=np.repeat(cell[None, :, :], n_frames, axis=0),
        fractional_positions=positions,
        energies_ev=np.array([-10.0, -9.8]),
        forces_ev_per_angstrom=(
            np.zeros((n_frames, n_atoms, 3), dtype=np.float64)
            if forces is None
            else forces
        ),
        stresses_ev_per_angstrom3=(
            np.repeat((-0.1 * np.eye(3))[None, :, :], n_frames, axis=0)
            if stresses is None
            else stresses
        ),
        temperatures_kelvin=np.asarray(temperatures, dtype=np.float64),
        scf_iteration_limit_reached=(False, False),
    )


def _ring_points(center: np.ndarray, radius: float, count: int, cell_length: float) -> np.ndarray:
    angles = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
    cartesian = np.column_stack(
        (
            center[0] + radius * np.cos(angles),
            center[1] + radius * np.sin(angles),
            np.full(count, center[2]),
        )
    )
    return cartesian / cell_length


def _site_fixture() -> tuple[tuple[str, ...], mdstats.FrameData, mdstats.LtaPartitionProfilePolicy]:
    length = 30.0
    cell = length * np.eye(3)
    ring4 = _ring_points(np.array([6.0, 6.0, 6.0]), 1.0, 4, length)
    ring6 = _ring_points(np.array([15.0, 6.0, 6.0]), 1.2, 6, length)
    ring8 = _ring_points(np.array([24.0, 6.0, 6.0]), 1.4, 8, length)
    framework = np.vstack((ring4, ring6, ring8))
    frame0_mobile = np.array(
        [
            [6.0, 6.0, 5.7],
            [15.0, 6.0, 6.0],
            [24.0, 6.0, 6.0],
        ]
    ) / length
    frame1_mobile = np.array(
        [
            [6.0, 6.0, 6.3],
            [24.0, 6.0, 6.0],
            [24.0, 6.0, 10.0],
        ]
    ) / length
    positions = np.stack(
        (np.vstack((framework, frame0_mobile)), np.vstack((framework, frame1_mobile)))
    )
    elements = tuple(["O"] * 18 + ["Li", "Na", "K"])
    numbers = tuple(atomic_numbers[symbol] for symbol in elements)
    forces = np.zeros((2, len(elements), 3), dtype=np.float64)
    forces[0, 18] = [3.0, 0.0, 0.0]
    policy = mdstats.LtaPartitionProfilePolicy(
        ring_definitions=(
            mdstats.LtaRingDefinition("r4", 4, tuple(range(0, 4))),
            mdstats.LtaRingDefinition("r6", 6, tuple(range(4, 10))),
            mdstats.LtaRingDefinition("r8", 8, tuple(range(10, 18))),
        )
    )
    return elements, _frame_data(numbers, positions, cell=cell, forces=forces), policy


def _framework_fixture(*, recovery: bool) -> tuple[tuple[str, ...], mdstats.FrameData]:
    length = 15.0
    cell = length * np.eye(3)
    center = np.array([7.5, 7.5, 7.5])
    tetra = np.asarray(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ],
        dtype=float,
    )
    tetra = center + 1.6 * tetra / np.sqrt(3.0)
    good = np.vstack((center, tetra, np.array([2.0, 2.0, 2.0]))) / length
    bad = np.array(good, copy=True)
    bad[1] = np.array([12.0, 12.0, 12.0]) / length
    positions = np.stack((bad, good) if recovery else (good, bad))
    elements = ("Si", "O", "O", "O", "O", "Li")
    numbers = tuple(atomic_numbers[symbol] for symbol in elements)
    return elements, _frame_data(numbers, positions, cell=cell)


def _site_catalogs(tmp_path: Path):
    site_elements, site_data, site_policy = _site_fixture()
    _write(tmp_path, "site", site_elements)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="data4-site", system_profile="lta")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    data = {"site": site_data}
    frames = mdstats.build_training_frame_catalog(
        sources,
        data,
        temperature_targets_by_run={"site": mdstats.TemperatureTargetEvidence(700.0, 700.0, "test")},
    )
    return sources, frames, data, site_policy


def _framework_catalogs(tmp_path: Path):
    loss_elements, loss_data = _framework_fixture(recovery=False)
    recovery_elements, recovery_data = _framework_fixture(recovery=True)
    _write(tmp_path, "loss", loss_elements)
    _write(tmp_path, "recovery", recovery_elements)
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="data4-framework", system_profile="lta")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    data = {"loss": loss_data, "recovery": recovery_data}
    frames = mdstats.build_training_frame_catalog(
        sources,
        data,
        temperature_targets_by_run={
            name: mdstats.TemperatureTargetEvidence(700.0, 700.0, "test") for name in data
        },
    )
    return sources, frames, data


def test_supplied_ase_version_and_real_data3_vasp_path(tmp_path: Path) -> None:
    import ase

    assert ase.__version__ == "3.29.0"
    _write(tmp_path, "run", ("Li", "O"))
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="ase-real")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    frames = mdstats.build_vasp_training_frame_catalog(sources, base_directory=tmp_path)
    assert len(frames.frames) == 2
    assert all(item.energy_present and item.forces_present for item in frames.frames)


def test_minimum_image_triclinic_displacement() -> None:
    cell = np.array([[10.0, 0.0, 0.0], [2.0, 9.0, 0.0], [0.0, 1.0, 8.0]])
    result = mdstats.minimum_image_displacements(
        np.array([[0.95, 0.95, 0.95]]),
        np.array([[0.05, 0.05, 0.05]]),
        cell=cell,
        pbc=np.array([True, True, True]),
    )
    assert result.shape == (1, 1, 3)
    assert result[0, 0] == pytest.approx([1.2, 1.0, 0.8])


def test_raw_features_pressure_species_and_pairs(tmp_path: Path) -> None:
    sources, frames, data, _ = _site_catalogs(tmp_path)
    raw = mdstats.build_raw_feature_catalog(
        sources,
        frames,
        data,
        policy=mdstats.RawFeaturePolicy.lta_default(),
    )
    site_frame = next(item for item in frames.frames if item.run_id == "site" and item.source_frame_index == 0)
    record = raw.for_frame(site_frame.frame_uid)
    assert record.pressure_ev_per_angstrom3 == pytest.approx(0.1)
    assert record.stress_von_mises_ev_per_angstrom3 == pytest.approx(0.0)
    li = next(item for item in record.species_force_statistics if item.symbol == "Li")
    assert li.norm_max_ev_per_angstrom == pytest.approx(3.0)
    assert record.force_component_rms_ev_per_angstrom == pytest.approx(
        np.sqrt(9.0 / (21 * 3))
    )
    k_o = next(item for item in record.pair_geometry_statistics if item.rule_id == "k-o")
    assert k_o.coordination_mean == pytest.approx(8.0)
    assert k_o.minimum_pair_distance_angstrom == pytest.approx(1.4, rel=1e-8)
    assert mdstats.RawFeatureCatalog.from_dict(raw.to_dict()) == raw


def test_lta_site_state_and_full_resolution_events(tmp_path: Path) -> None:
    sources, frames, data, site_policy = _site_catalogs(tmp_path)
    raw = mdstats.build_raw_feature_catalog(
        sources,
        frames,
        data,
        policy=mdstats.RawFeaturePolicy.lta_default(),
    )
    lta_policy = mdstats.LtaPartitionProfilePolicy(
        ring_definitions=site_policy.ring_definitions,
        require_oxygen_framework_coordination=1,
    )
    lta = mdstats.build_lta_partition_feature_catalog(frames, data, policy=lta_policy)
    site_frames = sorted(
        (item for item in frames.frames if item.run_id == "site"),
        key=lambda item: item.source_frame_index,
    )
    first_states = {item.symbol: item for item in lta.states_for_frame(site_frames[0].frame_uid)}
    second_states = {item.symbol: item for item in lta.states_for_frame(site_frames[1].frame_uid)}
    assert first_states["Li"].site_class is mdstats.LtaSiteClass.RING_4_ON_CENTER
    assert first_states["Na"].site_class is mdstats.LtaSiteClass.RING_6_ON_CENTER
    assert first_states["K"].site_class is mdstats.LtaSiteClass.RING_8_ON_CENTER
    assert second_states["Li"].ring_crossing
    assert second_states["Na"].site_changed
    assert second_states["K"].coordination_changed

    events = mdstats.detect_full_resolution_events(
        frames,
        raw,
        lta_features=lta,
        policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
    )
    types = {item.event_type for item in events.events}
    assert mdstats.FrameEventType.RING_CROSSING in types
    assert mdstats.FrameEventType.SITE_CHANGE in types
    assert mdstats.FrameEventType.COORDINATION_CHANGE in types
    assert mdstats.FrameEventType.FORCE_THRESHOLD in types
    crossing = next(item for item in events.events if item.event_type is mdstats.FrameEventType.RING_CROSSING)
    assert len(crossing.protected_frame_uids) == 2
    assert second_states["Li"].atom_index in crossing.affected_atom_indices
    assert mdstats.LtaPartitionFeatureCatalog.from_dict(lta.to_dict()) == lta
    assert mdstats.FullResolutionEventCatalog.from_dict(events.to_dict()) == events



def test_framework_integrity_loss_and_recovery_events(tmp_path: Path) -> None:
    sources, frames, data = _framework_catalogs(tmp_path)
    raw = mdstats.build_raw_feature_catalog(sources, frames, data)
    lta = mdstats.build_lta_partition_feature_catalog(
        frames,
        data,
        policy=mdstats.LtaPartitionProfilePolicy(
            require_oxygen_framework_coordination=1,
        ),
    )
    events = mdstats.detect_full_resolution_events(frames, raw, lta_features=lta)
    types = {item.event_type for item in events.events}
    assert mdstats.FrameEventType.FRAMEWORK_INTEGRITY_LOSS in types
    assert mdstats.FrameEventType.FRAMEWORK_INTEGRITY_RECOVERY in types

def test_data4_bundle_cache_and_tamper_rejection(tmp_path: Path) -> None:
    sources, frames, data, site_policy = _site_catalogs(tmp_path / "sources")
    bundle = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        data,
        raw_feature_policy=mdstats.RawFeaturePolicy.lta_default(),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
            ring_definitions=site_policy.ring_definitions,
            require_oxygen_framework_coordination=1,
        ),
        event_policy=mdstats.EventDetectionPolicy(force_norm_max_threshold_ev_per_angstrom=2.0),
        partition_role_budget=mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=2),
    )
    assert mdstats.Data4FeatureBundle.from_dict(bundle.to_dict()) == bundle
    cache = tmp_path / "cache"
    manifest = mdstats.write_data4_feature_cache(bundle, cache)
    loaded, loaded_manifest = mdstats.read_data4_feature_cache(cache)
    assert loaded == bundle
    assert loaded_manifest == manifest

    raw_path = cache / "raw_features.json"
    payload = raw_path.read_text(encoding="utf-8")
    raw_path.write_text(payload.replace('"dataset_id":"data4-site"', '"dataset_id":"changed"'), encoding="utf-8")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="hash mismatch"):
        mdstats.read_data4_feature_cache(cache)


def test_vasp_data4_integrated_smoke(tmp_path: Path) -> None:
    _write(tmp_path, "run", ("Li", "O"))
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="vasp-data4")
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    frames, bundle = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=tmp_path,
        raw_feature_policy=mdstats.RawFeaturePolicy(
            pair_rules=(mdstats.PairFeatureRule("li-o", 3, 8, 3.0),)
        ),
    )
    assert len(frames.frames) == 2
    assert len(bundle.raw_features.records) == 2
    assert bundle.lta_partition_features is None
    assert bundle.events.protected_frame_uids == ()


def test_role_budget_round_trip_and_validation() -> None:
    policy = mdstats.PartitionRoleBudgetPolicy(
        development_minimum_independent_units=5,
        cross_validation_folds=4,
        required_condition_axes=("composition", "temperature_condition"),
    )
    assert mdstats.PartitionRoleBudgetPolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(mdstats.TrainingDataInputError, match="at least two"):
        mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=1)


def test_data4_record_tamper_rejection(tmp_path: Path) -> None:
    sources, frames, data, _ = _site_catalogs(tmp_path)
    raw = mdstats.build_raw_feature_catalog(sources, frames, data)
    damaged = deepcopy(raw.to_dict())
    damaged["dataset_id"] = "tampered"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.RawFeatureCatalog.from_dict(damaged)
