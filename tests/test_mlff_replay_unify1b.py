from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from mdstats.training_data._common import TrainingDataInputError, TrainingDataSerializationError
from mdstats.training_data.replay import (
    REPLAY_TRUE_LABEL_CACHE_SCHEMA,
    REPLAY_TRUE_LABEL_VIEW_SCHEMA,
    ReplaySourceArtifact,
    ReplaySplitRole,
    ReplayTrueLabelCache,
    ReplayTrueLabelViewArtifact,
    build_replay_split_manifest,
    build_replay_true_label_cache,
    canonical_replay_geometry_identity,
    inspect_replay_source_extxyz,
    materialize_replay_true_label_views,
)


def _write_true_label_source(path: Path, count: int = 12, *, missing_index: int | None = None) -> None:
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    frames = []
    for index in range(count):
        atoms = Atoms(
            "H2",
            positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.7 + 0.01 * index]],
            cell=[5.0, 5.0, 5.0],
            pbc=True,
        )
        if index != missing_index:
            atoms.calc = SinglePointCalculator(
                atoms,
                energy=-10.0 - index,
                forces=np.full((2, 3), 0.01 * (index + 1), dtype=np.float64),
                stress=np.arange(6, dtype=np.float64) * 0.001 * (index + 1),
            )
        frames.append(atoms)
    write(path, frames, format="extxyz")


def test_true_label_cache_is_order_independent_and_round_trips(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 7)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    assert cache.serialization_schema == REPLAY_TRUE_LABEL_CACHE_SCHEMA
    assert cache.configuration_count == 7
    assert cache.complete_true_label_count == 7
    assert cache.missing_true_label_count == 0
    assert ReplayTrueLabelCache.from_dict(cache.to_dict()) == cache

    reversed_source = ReplaySourceArtifact(
        path="/relocated/reordered.extxyz",
        sha256=source.sha256,
        configuration_count=source.configuration_count,
        atomic_numbers=source.atomic_numbers,
        geometry_identities=tuple(reversed(source.geometry_identities)),
        source_label_identities=tuple(reversed(source.source_label_identities)),
        source_energy_present_count=source.source_energy_present_count,
        source_forces_present_count=source.source_forces_present_count,
        source_stress_present_count=source.source_stress_present_count,
    )
    reordered_cache = build_replay_true_label_cache(reversed_source)
    assert reordered_cache.content_digest == cache.content_digest
    assert reordered_cache.label_mapping_digest == cache.label_mapping_digest

    damaged = copy.deepcopy(cache.to_dict())
    damaged["source_label_identities"][0] = "0" * 64
    with pytest.raises(TrainingDataSerializationError):
        ReplayTrueLabelCache.from_dict(damaged)


def test_true_label_cache_can_inventory_missing_truth_but_requested_view_fails_closed(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 6, missing_index=2)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    assert cache.complete_true_label_count == 5
    assert cache.missing_true_label_count == 1
    split = build_replay_split_manifest(source, split_ratio=(1, 1), split_seed=11)
    missing_identity = source.geometry_identities[2]
    role = (
        ReplaySplitRole.TRAIN
        if missing_identity in split.train_geometry_identities
        else ReplaySplitRole.MONITOR
    )
    with pytest.raises(TrainingDataInputError, match="lacks a complete finite source energy/forces"):
        materialize_replay_true_label_views(source, cache, split, tmp_path / "views", roles=(role,))


def test_lazy_monitor_only_materialization_preserves_source_truth_and_split_membership(tmp_path: Path):
    pytest.importorskip("ase")
    from ase.io import iread

    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 12)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source, split_ratio=(5, 1), split_seed=42)
    output_dir = tmp_path / "views"

    results = materialize_replay_true_label_views(
        source,
        cache,
        split,
        output_dir,
        roles=(ReplaySplitRole.MONITOR,),
        buffer_size=2,
    )
    assert set(results) == {ReplaySplitRole.MONITOR}
    view = results[ReplaySplitRole.MONITOR]
    assert view.serialization_schema == REPLAY_TRUE_LABEL_VIEW_SCHEMA
    assert view.configuration_count == split.monitor_count == 2
    assert ReplayTrueLabelViewArtifact.from_dict(view.to_dict()) == view
    assert not (output_dir / "replay_train.true-label.extxyz").exists()
    assert (output_dir / "replay_monitor.true-label.extxyz.replay.json").is_file()

    seen = set()
    cache_mapping = cache.label_mapping
    for atoms in iread(view.path, index=":", format="extxyz"):
        identity = canonical_replay_geometry_identity(atoms)
        seen.add(identity)
        assert atoms.info["replay_split_role"] == "monitor"
        assert atoms.info["replay_label_mode"] == "true_dft"
        assert atoms.info["replay_label_namespace"] == "source_true"
        assert atoms.info["replay_true_label_identity"] == cache_mapping[identity]
        assert atoms.info["replay_true_label_cache_digest"] == cache.content_digest
        assert atoms.info["replay_split_manifest_digest"] == split.content_digest
        assert "replay_pseudolabel_model_sha256" not in atoms.info
        assert np.asarray(atoms.arrays["REF_forces"]).shape == (2, 3)
        assert np.isfinite(float(atoms.info["REF_energy"]))
    assert seen == set(split.monitor_geometry_identities)


def test_train_and_monitor_missing_views_are_materialized_in_one_source_pass(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 18)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source, split_ratio=(5, 1), split_seed=42)

    import ase.io

    original_iread = ase.io.iread
    calls = []

    def counted_iread(*args, **kwargs):
        calls.append(args[0] if args else kwargs.get("filename"))
        return original_iread(*args, **kwargs)

    monkeypatch.setattr(ase.io, "iread", counted_iread)
    results = materialize_replay_true_label_views(source, cache, split, tmp_path / "views")
    assert set(results) == {ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR}
    assert len(calls) == 1
    assert results[ReplaySplitRole.TRAIN].configuration_count == 15
    assert results[ReplaySplitRole.MONITOR].configuration_count == 3


def test_authenticated_cache_hit_does_not_reopen_source_and_deleted_view_reconstructs(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 12)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source)
    output_dir = tmp_path / "views"

    first = materialize_replay_true_label_views(
        source, cache, split, output_dir, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]

    import ase.io

    def forbidden_iread(*args, **kwargs):
        raise AssertionError("cache hit must not parse source")

    monkeypatch.setattr(ase.io, "iread", forbidden_iread)
    second = materialize_replay_true_label_views(
        source, cache, split, output_dir, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]
    assert second == first

    monkeypatch.undo()
    Path(first.path).unlink()
    rebuilt = materialize_replay_true_label_views(
        source, cache, split, output_dir, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]
    assert rebuilt.logical_digest == first.logical_digest
    assert Path(rebuilt.path).is_file()


def test_materialization_rejects_source_or_split_authority_mismatch(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 8)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source)

    foreign_path = tmp_path / "foreign.extxyz"
    _write_true_label_source(foreign_path, 9)
    foreign = inspect_replay_source_extxyz(foreign_path)
    foreign_cache = build_replay_true_label_cache(foreign)
    with pytest.raises(TrainingDataInputError, match="geometry authorities differ"):
        materialize_replay_true_label_views(source, foreign_cache, split, tmp_path / "bad")


def test_materialization_rejects_same_geometry_cache_with_changed_label_authority(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_true_label_source(source_path, 8)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source)
    changed_labels = list(source.source_label_identities)
    changed_labels[0] = "f" * 64
    masquerading_source = ReplaySourceArtifact(
        path=source.path,
        sha256=source.sha256,
        configuration_count=source.configuration_count,
        atomic_numbers=source.atomic_numbers,
        geometry_identities=source.geometry_identities,
        source_label_identities=tuple(changed_labels),
        source_energy_present_count=source.source_energy_present_count,
        source_forces_present_count=source.source_forces_present_count,
        source_stress_present_count=source.source_stress_present_count,
    )
    with pytest.raises(TrainingDataInputError, match="label authorities differ"):
        materialize_replay_true_label_views(
            masquerading_source,
            cache,
            split,
            tmp_path / "masquerade",
            roles=(ReplaySplitRole.MONITOR,),
        )
