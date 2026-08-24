from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from mdstats.training_data.replay import (
    ReplaySplitRole,
    build_replay_split_manifest,
    build_replay_true_label_cache,
    inspect_replay_source_extxyz,
    materialize_replay_true_label_views,
)
from mdstats.training_data.replay_index import (
    EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA,
    REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA,
    ExtxyzSourceIndex,
    ReplaySourceIndex,
    build_extxyz_source_index,
    build_replay_source_index,
    iter_indexed_extxyz_frames,
    iter_indexed_replay_frames,
    replay_source_indices_for_identities,
)


def _write_source(path: Path, count: int = 24) -> None:
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    frames = []
    for i in range(count):
        atoms = Atoms(
            "H2",
            positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.70 + 0.003 * i]],
            cell=[5.0, 5.0, 5.0],
            pbc=True,
        )
        atoms.calc = SinglePointCalculator(
            atoms,
            energy=-5.0 - i,
            forces=np.full((2, 3), 0.001 * (i + 1), dtype=np.float64),
            stress=np.arange(6, dtype=np.float64) * 1.0e-4 * (i + 1),
        )
        frames.append(atoms)
    write(path, frames, format="extxyz")


def test_source_index_round_trip_cache_hit_and_corruption_rebuild(tmp_path: Path) -> None:
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 24)
    source = inspect_replay_source_extxyz(source_path)
    cache = tmp_path / "index"
    first = build_replay_source_index(source, cache)
    assert first.configuration_count == source.configuration_count
    assert first.source_sha256 == source.sha256
    assert ReplaySourceIndex.from_dict(first.to_dict()) == first

    receipt = cache / "replay-source-index.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA
    payload["index"]["frame_offsets"][3] += 1
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    rebuilt = build_replay_source_index(source, cache)
    assert rebuilt.content_digest == first.content_digest
    assert rebuilt.frame_offsets == first.frame_offsets


def test_source_index_invalidates_when_source_bytes_change(tmp_path: Path) -> None:
    source_path = tmp_path / "replay.extxyz"
    cache = tmp_path / "index"
    _write_source(source_path, 12)
    first_source = inspect_replay_source_extxyz(source_path)
    first = build_replay_source_index(first_source, cache)
    _write_source(source_path, 13)
    second_source = inspect_replay_source_extxyz(source_path)
    second = build_replay_source_index(second_source, cache)
    assert second.source_sha256 != first.source_sha256
    assert second.configuration_count == 13
    assert second.content_digest != first.content_digest


def test_indexed_frame_reader_is_chunk_size_invariant_and_exact(tmp_path: Path) -> None:
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 24)
    source = inspect_replay_source_extxyz(source_path)
    index = build_replay_source_index(source, tmp_path / "index")
    requested = (0, 1, 5, 9, 10, 11, 23)
    first = list(iter_indexed_replay_frames(source, index, source_indices=requested, chunk_size=1))
    second = list(iter_indexed_replay_frames(source, index, source_indices=requested, chunk_size=8))
    assert [i for i, _ in first] == list(requested) == [i for i, _ in second]
    from mdstats.training_data.replay import canonical_replay_geometry_identity
    assert [canonical_replay_geometry_identity(a) for _, a in first] == [source.geometry_identities[i] for i in requested]
    assert [canonical_replay_geometry_identity(a) for _, a in second] == [source.geometry_identities[i] for i in requested]


def test_generic_extxyz_index_sparse_access_matches_full_ase_read(tmp_path: Path) -> None:
    source_path = tmp_path / "target.extxyz"
    _write_source(source_path, 24)
    source = inspect_replay_source_extxyz(source_path)
    index = build_extxyz_source_index(
        source_path, source_sha256=source.sha256,
        source_artifact_digest=source.content_digest,
        cache_directory=tmp_path / "generic-index",
    )
    assert ExtxyzSourceIndex.from_dict(index.to_dict()) == index
    receipt = json.loads(
        (tmp_path / "generic-index" / "extxyz-source-index.json").read_text(encoding="utf-8")
    )
    assert receipt["schema"] == EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA
    requested = (0, 3, 4, 17, 23)
    sparse = list(iter_indexed_extxyz_frames(index, source_indices=requested, chunk_size=2))
    from ase.io import read
    full = read(source_path, index=":", format="extxyz")
    assert [position for position, _ in sparse] == list(requested)
    for (position, observed), expected_position in zip(sparse, requested, strict=True):
        assert position == expected_position
        assert observed == full[expected_position]


def test_generic_extxyz_index_concurrent_creation_is_atomic(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    source_path = tmp_path / "target.extxyz"
    _write_source(source_path, 18)
    source = inspect_replay_source_extxyz(source_path)
    cache = tmp_path / "generic-index"

    def build():
        return build_extxyz_source_index(
            source_path, source_sha256=source.sha256,
            source_artifact_digest=source.content_digest, cache_directory=cache,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = tuple(pool.map(lambda _: build(), range(24)))
    assert len({value.content_digest for value in values}) == 1
    assert not tuple(cache.glob("*.tmp"))
    payload = json.loads((cache / "extxyz-source-index.json").read_text(encoding="utf-8"))
    assert ExtxyzSourceIndex.from_dict(payload["index"]).content_digest == values[0].content_digest


def test_monitor_only_materialization_with_index_reads_only_monitor_source_indices(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 30)
    source = inspect_replay_source_extxyz(source_path)
    index = build_replay_source_index(source, tmp_path / "index")
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source, split_ratio=(5, 1), split_seed=42)
    expected = replay_source_indices_for_identities(source, split.monitor_geometry_identities)

    import mdstats.training_data.replay as replay_module
    original = replay_module.iter_indexed_replay_frames
    calls = []

    def counted(source_arg, index_arg, **kwargs):
        calls.append(tuple(kwargs.get("source_indices") or ()))
        yield from original(source_arg, index_arg, **kwargs)

    monkeypatch.setattr(replay_module, "iter_indexed_replay_frames", counted)
    import ase.io
    monkeypatch.setattr(ase.io, "iread", lambda *a, **k: (_ for _ in ()).throw(AssertionError("indexed path must not scan with iread")))
    result = materialize_replay_true_label_views(
        source,
        cache,
        split,
        tmp_path / "views",
        roles=(ReplaySplitRole.MONITOR,),
        source_index=index,
        buffer_size=2,
    )[ReplaySplitRole.MONITOR]
    assert result.configuration_count == split.monitor_count
    assert calls == [expected]
    assert len(expected) == split.monitor_count


def test_indexed_and_streaming_true_label_views_have_identical_authority(tmp_path: Path) -> None:
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 36)
    source = inspect_replay_source_extxyz(source_path)
    index = build_replay_source_index(source, tmp_path / "index")
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source, split_ratio=(5, 1), split_seed=17)
    old = materialize_replay_true_label_views(source, cache, split, tmp_path / "stream")
    new = materialize_replay_true_label_views(source, cache, split, tmp_path / "indexed", source_index=index)
    for role in (ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR):
        assert new[role].logical_digest == old[role].logical_digest
        assert new[role].geometry_set_digest == old[role].geometry_set_digest
        assert new[role].true_label_set_digest == old[role].true_label_set_digest
        assert Path(new[role].path).read_bytes() == Path(old[role].path).read_bytes()
