from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np
import pytest

from mdstats.training_data._common import TrainingDataInputError, TrainingDataSerializationError
from mdstats.training_data.replay import (
    DEFAULT_REPLAY_SPLIT_RATIO,
    DEFAULT_REPLAY_SPLIT_SEED,
    REPLAY_GEOMETRY_IDENTITY_SCHEMA,
    REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM,
    REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA,
    REPLAY_SOURCE_ARTIFACT_SCHEMA,
    ReplayLabelMode,
    ReplaySingleSourceConfig,
    ReplaySourceArtifact,
    ReplaySplitManifest,
    build_replay_split_manifest,
    canonical_replay_geometry_identity,
    inspect_replay_source_extxyz,
    normalize_replay_split_ratio,
    single_source_replay_config_from_campaign,
)


class _Cell:
    def __init__(self, array):
        self.array = np.asarray(array, dtype=np.float64)


class _Atoms:
    def __init__(self, numbers, positions, cell, pbc=(True, True, True)):
        self.numbers = np.asarray(numbers, dtype=np.int64)
        self.positions = np.asarray(positions, dtype=np.float64)
        self.cell = _Cell(cell)
        self.pbc = np.asarray(pbc, dtype=bool)


def _hex_digest(index: int) -> str:
    return hashlib.sha256(f"geometry-{index}".encode()).hexdigest()


def _source(count: int = 12_000) -> ReplaySourceArtifact:
    ids = tuple(_hex_digest(i) for i in range(count))
    return ReplaySourceArtifact(
        path="/replay/replay_fps_12000.extxyz",
        sha256=hashlib.sha256(b"source").hexdigest(),
        configuration_count=count,
        atomic_numbers=(1, 8, 11, 13, 14),
        geometry_identities=ids,
        source_label_identities=(None,) * count,
        source_energy_present_count=0,
        source_forces_present_count=0,
        source_stress_present_count=0,
    )


def test_geometry_identity_contract_is_versioned_quantized_and_atom_order_preserving():
    atoms = _Atoms([8, 1], [[0.123456781, 0, 0], [1, 2, 3]], np.eye(3) * 10)
    same_bin = _Atoms([8, 1], [[0.123456783, 0, 0], [1, 2, 3]], np.eye(3) * 10)
    next_bin = _Atoms([8, 1], [[0.123456792, 0, 0], [1, 2, 3]], np.eye(3) * 10)
    reordered = _Atoms([1, 8], [[1, 2, 3], [0.123456781, 0, 0]], np.eye(3) * 10)
    assert REPLAY_GEOMETRY_IDENTITY_SCHEMA.endswith(".v1")
    assert REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM == 1.0e-8
    assert canonical_replay_geometry_identity(atoms) == canonical_replay_geometry_identity(same_bin)
    assert canonical_replay_geometry_identity(atoms) != canonical_replay_geometry_identity(next_bin)
    assert canonical_replay_geometry_identity(atoms) != canonical_replay_geometry_identity(reordered)


def test_default_12000_split_is_exactly_10000_2000_disjoint_and_complete():
    source = _source()
    manifest = build_replay_split_manifest(source)
    assert manifest.split_ratio == DEFAULT_REPLAY_SPLIT_RATIO == (5, 1)
    assert manifest.split_seed == DEFAULT_REPLAY_SPLIT_SEED == 42
    assert manifest.train_count == 10_000
    assert manifest.monitor_count == 2_000
    assert not (set(manifest.train_geometry_identities) & set(manifest.monitor_geometry_identities))
    assert set(manifest.train_geometry_identities) | set(manifest.monitor_geometry_identities) == set(source.geometry_identities)


def test_split_membership_is_independent_of_source_or_eligible_input_order():
    source = _source(97)
    forward = build_replay_split_manifest(source, split_ratio="10:2", split_seed=123)
    reverse_source = ReplaySourceArtifact(
        path=source.path,
        sha256=source.sha256,
        configuration_count=source.configuration_count,
        atomic_numbers=source.atomic_numbers,
        geometry_identities=tuple(reversed(source.geometry_identities)),
        source_label_identities=tuple(reversed(source.source_label_identities)),
        source_energy_present_count=0,
        source_forces_present_count=0,
        source_stress_present_count=0,
    )
    reverse = build_replay_split_manifest(
        reverse_source,
        eligible_geometry_identities=tuple(reversed(source.geometry_identities)),
        split_ratio=(5, 1),
        split_seed=123,
    )
    assert forward.split_ratio == reverse.split_ratio == (5, 1)
    assert set(forward.train_geometry_identities) == set(reverse.train_geometry_identities)
    assert set(forward.monitor_geometry_identities) == set(reverse.monitor_geometry_identities)
    assert forward.eligible_geometry_set_digest == reverse.eligible_geometry_set_digest
    assert forward == reverse
    assert forward.content_digest == reverse.content_digest


def test_split_manifest_binds_qualification_authority_without_label_namespace():
    source = _source(12)
    qualification = hashlib.sha256(b"qualified-set-v1").hexdigest()
    eligible = source.geometry_identities[:10]
    manifest = build_replay_split_manifest(source, eligible_geometry_identities=eligible, qualification_authority_digest=qualification)
    assert manifest.qualification_authority_digest == qualification
    assert manifest.configuration_count == 10
    assert manifest.train_count == 8
    assert manifest.monitor_count == 2
    assert set(manifest.train_geometry_identities + manifest.monitor_geometry_identities) == set(eligible)


def test_replay_source_and_split_round_trip_fail_closed():
    source = _source(12)
    assert ReplaySourceArtifact.from_dict(source.to_dict()) == source
    relocated = ReplaySourceArtifact(
        path="/different/location/replay.extxyz",
        sha256=source.sha256,
        configuration_count=source.configuration_count,
        atomic_numbers=source.atomic_numbers,
        geometry_identities=source.geometry_identities,
        source_label_identities=source.source_label_identities,
        source_energy_present_count=source.source_energy_present_count,
        source_forces_present_count=source.source_forces_present_count,
        source_stress_present_count=source.source_stress_present_count,
    )
    assert relocated.content_digest == source.content_digest
    manifest = build_replay_split_manifest(source)
    assert ReplaySplitManifest.from_dict(manifest.to_dict()) == manifest
    damaged = copy.deepcopy(manifest.to_dict())
    damaged["monitor_geometry_identities"][0] = damaged["train_geometry_identities"][0]
    with pytest.raises((TrainingDataInputError, TrainingDataSerializationError)):
        ReplaySplitManifest.from_dict(damaged)


def test_new_config_normalizes_ratio_and_rejects_mixed_authority(tmp_path: Path):
    cfg = {"paths": {"replay_set": "replay_fps_12000.extxyz"}, "replay": {"label_mode": "foundation_pseudolabel", "split_ratio": "10:2"}}
    resolved = single_source_replay_config_from_campaign(cfg, base_directory=tmp_path)
    assert resolved is not None
    assert resolved.serialization_schema == REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA
    assert resolved.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert resolved.split_ratio == (5, 1)
    assert resolved.split_seed == 42
    assert resolved.replay_set_path == str((tmp_path / "replay_fps_12000.extxyz").resolve())
    assert ReplaySingleSourceConfig.from_dict(resolved.to_dict()) == resolved
    mixed = copy.deepcopy(cfg)
    mixed["paths"]["replay_train"] = "old_train.extxyz"
    with pytest.raises(TrainingDataInputError, match="cannot be combined"):
        single_source_replay_config_from_campaign(mixed, base_directory=tmp_path)


def test_legacy_config_remains_outside_new_single_source_authority():
    legacy = {"paths": {"replay_train": "replay_train.extxyz", "replay_monitor": "replay_monitor.extxyz", "replay_true_labels": "true_labels"}, "replay": {"mode": "external_pseudolabel"}}
    assert single_source_replay_config_from_campaign(legacy) is None


def test_ratio_validation_and_normalization():
    assert normalize_replay_split_ratio("5/1") == (5, 1)
    assert normalize_replay_split_ratio((15, 3)) == (5, 1)
    with pytest.raises(TrainingDataInputError):
        normalize_replay_split_ratio("5:0")
    with pytest.raises(TrainingDataInputError):
        normalize_replay_split_ratio("5:1:1")


def test_streaming_source_inspection_preserves_true_labels_and_rejects_duplicates(tmp_path: Path):
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.io import write
    from ase.calculators.singlepoint import SinglePointCalculator

    frames = []
    for index in range(3):
        atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.75 + 0.1 * index]], cell=[5, 5, 5], pbc=True)
        atoms.calc = SinglePointCalculator(atoms, energy=-1.0 - index, forces=np.full((2, 3), 0.01 * index), stress=np.arange(6, dtype=np.float64) * 0.001)
        frames.append(atoms)
    path = tmp_path / "replay.extxyz"
    write(path, frames, format="extxyz")
    artifact = inspect_replay_source_extxyz(path)
    assert artifact.configuration_count == 3
    assert artifact.source_energy_present_count == 3
    assert artifact.source_forces_present_count == 3
    assert artifact.source_stress_present_count == 3
    assert artifact.complete_true_label_count == 3
    duplicate_path = tmp_path / "duplicate.extxyz"
    write(duplicate_path, [frames[0], frames[0].copy()], format="extxyz")
    with pytest.raises(TrainingDataInputError, match="duplicate canonical geometry"):
        inspect_replay_source_extxyz(duplicate_path)
