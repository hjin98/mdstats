from __future__ import annotations

import io
from pathlib import Path

import numpy as np

import mdstats
from mdstats.training_data._array_pickle import (
    dump_with_array_references,
    load_with_array_references,
    estimate_array_reference_spill_bytes,
)
from mdstats.training_data import sources
from tests.test_mlff_data2_source_catalog import _write


def test_isolated_worker_transport_keeps_memmaps_as_small_file_references(tmp_path: Path) -> None:
    source = tmp_path / "large.npy"
    np.save(source, np.arange(1_000_000, dtype=np.float64), allow_pickle=False)
    mapped = np.load(source, mmap_mode="r", allow_pickle=False)
    payload = {"values": mapped, "window": mapped[100:200]}
    handle = io.BytesIO()
    dump_with_array_references(
        payload,
        handle,
        array_directory=tmp_path / "array-refs",
    )
    assert handle.tell() < 2_048
    handle.seek(0)
    restored = load_with_array_references(handle)
    assert isinstance(restored["values"], np.memmap)
    assert isinstance(restored["window"], np.memmap)
    np.testing.assert_array_equal(restored["values"], mapped)
    np.testing.assert_array_equal(restored["window"], mapped[100:200])
    assert not restored["values"].flags.writeable


def test_isolated_worker_transport_spills_large_in_memory_arrays(tmp_path: Path) -> None:
    values = np.arange(300_000, dtype=np.float64)
    handle = io.BytesIO()
    dump_with_array_references(
        {"values": values},
        handle,
        array_directory=tmp_path / "array-refs",
        externalize_bytes=1_024,
    )
    assert handle.tell() < 2_048
    assert len(tuple((tmp_path / "array-refs").glob("*.npy"))) == 1
    handle.seek(0)
    restored = load_with_array_references(handle)["values"]
    assert isinstance(restored, np.memmap)
    np.testing.assert_array_equal(restored, values)


def test_vasp_training_source_uses_one_control_parse(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path, "run", ("Li", "O"))
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="single-parse")
    import mdstats.io.vasp_controls as controls

    calls = 0
    original = controls._parse_vasp_xml

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(controls, "_parse_vasp_xml", counted)
    loaded = sources.load_vasp_training_source(
        manifest.runs[0], base_directory=tmp_path, strict=True
    )
    assert len(loaded.frame_data.fractional_positions) == 2
    assert calls == 1


def test_array_reference_spill_estimator_counts_only_large_in_memory_arrays(tmp_path: Path) -> None:
    source = tmp_path / "mapped.npy"
    np.save(source, np.arange(300_000, dtype=np.float64), allow_pickle=False)
    mapped = np.load(source, mmap_mode="r", allow_pickle=False)
    resident = np.arange(300_000, dtype=np.float64)
    small = np.arange(8, dtype=np.float64)
    estimate = estimate_array_reference_spill_bytes(
        {"mapped": mapped, "resident": resident, "resident_alias": resident, "small": small},
        externalize_bytes=1_024,
    )
    assert resident.nbytes <= estimate <= resident.nbytes + 8192
