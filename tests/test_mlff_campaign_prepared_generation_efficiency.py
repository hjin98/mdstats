"""What the repaired stage boundary actually costs, measured on real commands.

The point of publishing an immutable prepared generation was never elegance: it
was that currentness used to cost O(dataset). Every downstream command restored
DATA4 and rebuilt the P1/P2/P3-common graph from live inputs just to prove that
nothing had changed. The counters here bind that claim to the real commands, and
the footprint measurements bind the other half of it - that making the substrate
durable must not be paid for by copying the dataset once per generation.

Wall time is reported rather than asserted. A timing threshold on a shared
machine is a flaky test, not evidence; the structural counts are what actually
establish the claim, and they are exact.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_prepared_generation import (
    prepared_generation_root,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)


class _Counters:
    """Count the upstream owners a command reaches, through the real owners."""

    def __init__(self, monkeypatch) -> None:
        self.data4_restores = 0
        self.source_frame_reads = 0
        self.substrate_builds = 0

        import mdstats.io as io_module
        from mdstats.training_data import campaign_target_size_runtime as runtime
        from mdstats.training_data import data4_sharded_store

        real_restore = data4_sharded_store.read_data4_sharded_record
        real_read = io_module.read_vasp_frames
        real_build = runtime.build_prepared_target_size_substrate

        def restore(*args, **kwargs):
            self.data4_restores += 1
            return real_restore(*args, **kwargs)

        def read(*args, **kwargs):
            self.source_frame_reads += 1
            return real_read(*args, **kwargs)

        def build(*args, **kwargs):
            self.substrate_builds += 1
            return real_build(*args, **kwargs)

        monkeypatch.setattr(
            data4_sharded_store, "read_data4_sharded_record", restore
        )
        monkeypatch.setattr(io_module, "read_vasp_frames", read)
        monkeypatch.setattr(
            runtime, "build_prepared_target_size_substrate", build
        )

    def summary(self) -> str:
        return (
            f"data4_restores={self.data4_restores}; "
            f"source_frame_reads={self.source_frame_reads}; "
            f"substrate_builds={self.substrate_builds}"
        )


def _footprint(root: Path) -> tuple[int, int]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return sum(path.stat().st_size for path in files), len(files)


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def test_downstream_commands_pay_no_upstream_reconstruction(
    tmp_path: Path, monkeypatch, capsys
):
    """`select` and `status` reach no preparation owner at all."""

    config, _workspace = p4d._fixture_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)

    cold = _Counters(monkeypatch)
    started = time.monotonic()
    assert p4d._run(config, "prepare") == 0
    prepare_seconds = time.monotonic() - started
    assert cold.substrate_builds >= 1, "prepare is the construction boundary"

    warm = _Counters(monkeypatch)
    started = time.monotonic()
    assert p4d._run(config, "prepare") == 0
    repeat_seconds = time.monotonic() - started

    harness = p4d._BoundedNumericalHarness()
    select = _Counters(monkeypatch)
    started = time.monotonic()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    select_seconds = time.monotonic() - started

    status = _Counters(monkeypatch)
    started = time.monotonic()
    assert cli.main(["--config", str(config), "status"]) == 0
    status_seconds = time.monotonic() - started

    resume = _Counters(monkeypatch)
    started = time.monotonic()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    resume_seconds = time.monotonic() - started

    # The structural claim: consumption reconstructs nothing.
    assert select.data4_restores == 0
    assert select.source_frame_reads == 0
    assert select.substrate_builds == 0
    assert resume.data4_restores == 0
    assert resume.source_frame_reads == 0
    assert resume.substrate_builds == 0
    assert status.data4_restores == 0
    assert status.source_frame_reads == 0
    assert status.substrate_builds == 0

    with capsys.disabled():
        print(
            "\n[prepared-generation I/O]"
            f"\n  cold prepare      {prepare_seconds:7.2f}s  {cold.summary()}"
            f"\n  repeated prepare  {repeat_seconds:7.2f}s  {warm.summary()}"
            f"\n  select (first)    {select_seconds:7.2f}s  {select.summary()}"
            f"\n  select (resume)   {resume_seconds:7.2f}s  {resume.summary()}"
            f"\n  status            {status_seconds:7.2f}s  {status.summary()}"
        )


def test_generations_share_content_instead_of_copying_the_dataset(
    tmp_path: Path, capsys
):
    """A second generation republishes only what actually changed."""

    config, _workspace = p4d._fixture_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    assert p4d._run(config, "prepare") == 0

    prepared_root = prepared_generation_root(paths)
    cache_root = paths.internal / "frame-cache"
    fresh_bytes, fresh_files = _footprint(prepared_root)
    cache_bytes, cache_files = _footprint(cache_root)
    first = _revision(paths)
    first_manifest = read_prepared_generation_manifest(
        paths, first.state.prepared_manifest_digest
    )

    # Repeating an unchanged preparation must add nothing at all.
    assert p4d._run(config, "prepare") == 0
    repeat_bytes, repeat_files = _footprint(prepared_root)
    assert (repeat_bytes, repeat_files) == (fresh_bytes, fresh_files)
    assert _revision(paths).state.generation == first.state.generation

    # Change a preparation-scientific policy: a fresh generation is required,
    # and it must reuse every component the change does not touch.
    text = config.read_text(encoding="utf-8")
    assert "development_minimum_independent_units = 4" in text
    config.write_text(
        text.replace(
            "development_minimum_independent_units = 4",
            "development_minimum_independent_units = 3",
        ),
        encoding="utf-8",
    )
    # Editing the campaign file invalidates the doctor stage, exactly as it
    # does for an operator; rerunning it is part of changing the policy.
    store = CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    finally:
        store.close()
    assert p4d._run(config, "prepare") == 0

    second = _revision(paths)
    assert second.state.generation == first.state.generation + 1
    second_manifest = read_prepared_generation_manifest(
        paths, second.state.prepared_manifest_digest
    )
    shared = {
        name
        for name, value in second_manifest.component_digests.items()
        if first_manifest.component_digests[name] == value
    }
    changed = set(second_manifest.component_digests) - shared
    assert "frame_catalog" in shared and "source_catalog" in shared
    assert changed, "a changed preparation policy must change something"

    # The normalized payload is bound by content, so it is shared outright.
    assert second_manifest.frame_records == first_manifest.frame_records
    assert _footprint(cache_root) == (cache_bytes, cache_files)

    second_bytes, second_files = _footprint(prepared_root)
    incremental_bytes = second_bytes - fresh_bytes
    with capsys.disabled():
        print(
            "\n[prepared-generation footprint]"
            f"\n  fresh generation      {fresh_bytes:>10,} B in {fresh_files} file(s)"
            f"\n  unchanged repeat      {repeat_bytes - fresh_bytes:>10,} B added"
            f"\n  changed policy        {incremental_bytes:>10,} B added"
            f"\n  components reused     {sorted(shared)}"
            f"\n  components republished{sorted(changed)}"
            f"\n  normalized cache      {cache_bytes:>10,} B in {cache_files} file(s), unchanged"
        )
    # The second generation costs metadata, never another copy of the dataset.
    assert incremental_bytes < fresh_bytes


def test_warm_prepared_load_keeps_normalized_arrays_memory_mapped(
    tmp_path: Path, capsys
):
    """Generation safety must not cost the mmap sharing it replaced."""

    import numpy as np

    from mdstats.training_data.campaign_target_size_runtime import (
        load_prepared_target_size_generation,
    )

    config, _workspace = p4d._fixture_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    assert p4d._run(config, "prepare") == 0
    revision = _revision(paths)

    store = CampaignStore(paths.state_db)
    started = time.monotonic()
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, revision
        )
    finally:
        store.close()
    load_seconds = time.monotonic() - started

    def _is_mapped(array) -> bool:
        # The reader hands back a view over the mapping rather than the mapping
        # object itself, so the page-cache sharing lives on the base.
        seen = array
        while seen is not None:
            if isinstance(seen, np.memmap):
                return True
            seen = getattr(seen, "base", None)
        return False

    mapped = 0
    total = 0
    for data in authorities.frame_data_by_run.values():
        for name in ("fractional_positions", "cells_angstrom", "atomic_numbers"):
            total += 1
            if _is_mapped(getattr(data, name)):
                mapped += 1
    assert total, "the prepared generation exposed no normalized arrays"
    assert mapped == total, (
        "normalized arrays were materialized into private RAM instead of being "
        "shared read-only through the page cache"
    )
    with capsys.disabled():
        print(
            f"\n[warm prepared load] {load_seconds:.3f}s; "
            f"{mapped}/{total} normalized arrays memory-mapped"
        )
