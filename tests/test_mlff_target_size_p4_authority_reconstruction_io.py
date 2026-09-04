"""P4 post-DATA4 authority reconstruction: structural I/O and parallelism.

The defect these tests close was not a wrong scientific result: current
authority construction rebuilt the canonical frame authority straight from
``vasprun.xml`` and only afterwards restored the normalized frame cache, so a
warm-cache ``prepare`` re-read every source frame it already had, serially and
silently.  These tests bind the repaired structure -- one authentication owner,
one normalized-frame acquisition, bounded parallelism -- to the real owners
rather than to a fake orchestration path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_runtime import (
    build_current_target_size_authorities,
)
from mdstats.training_data.neutral_substrate import frame_authority as frame_authority_module
from mdstats.training_data.neutral_substrate import (
    authenticate_vasp_source_authority,
    build_canonical_frame_authority,
    build_source_authority_from_data2_catalog,
    build_vasp_canonical_frame_authority,
)


def _prepared(tmp_path: Path):
    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    cfg, paths = cli._load_config(config)
    return cfg, paths, workspace


def _count_source_frame_reads(monkeypatch) -> list[str]:
    """Wrap the real VASP frame reader, not a stand-in for it."""

    import mdstats.io as io_module

    calls: list[str] = []
    real = io_module.read_vasp_frames

    def counting(path, *args, **kwargs):
        calls.append(str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(io_module, "read_vasp_frames", counting)
    return calls


def test_p4_warm_cache_authority_reconstruction_reads_no_source_frames(
    tmp_path: Path, monkeypatch
):
    """A warm normalized frame cache means zero full VASP frame reads."""

    cfg, paths, _workspace = _prepared(tmp_path)
    assert (paths.internal / "frame-cache").is_dir()

    calls = _count_source_frame_reads(monkeypatch)
    store = CampaignStore(paths.state_db)
    try:
        authorities = build_current_target_size_authorities(cfg, paths, store)
    finally:
        store.close()
    assert calls == []
    # Fresh authentication still ran against the real files.
    assert authorities.frame_authority.content_digest
    assert authorities.common.content_digest


def test_p4_cache_rebuild_reads_each_source_at_most_once(
    tmp_path: Path, monkeypatch
):
    """A missing cache rebuilds with one source read per run, then reuses it."""

    cfg, paths, _workspace = _prepared(tmp_path)
    cache_root = paths.internal / "frame-cache"
    for path in sorted(cache_root.rglob("*")):
        if path.is_file():
            path.unlink()

    calls = _count_source_frame_reads(monkeypatch)
    store = CampaignStore(paths.state_db)
    try:
        authorities = build_current_target_size_authorities(cfg, paths, store)
    finally:
        store.close()
    run_count = len(authorities.source_catalog.sources)
    assert len(calls) == run_count
    assert len(set(calls)) == run_count


def test_p4_canonical_and_common_share_one_frame_data_mapping(tmp_path: Path):
    """Both consumers receive the same normalized mapping, not two loads."""

    cfg, paths, _workspace = _prepared(tmp_path)
    store = CampaignStore(paths.state_db)
    try:
        authorities = build_current_target_size_authorities(cfg, paths, store)
    finally:
        store.close()
    observed: list[int] = []
    for run_id, data in authorities.frame_data_by_run.items():
        observed.append(id(data))
        record, frame_data, _index = next(
            value
            for value in authorities.frame_array_index.values()
            if value[0].run_id == run_id
        )
        assert frame_data is data
    assert len(observed) == len(set(observed))


def test_p4_no_second_frame_cache_or_currentness_authority(tmp_path: Path):
    """The repair introduced no parallel cache, registry, or freshness store."""

    cfg, paths, workspace = _prepared(tmp_path)
    internal = paths.internal
    caches = sorted(
        path.name
        for path in internal.iterdir()
        if path.is_dir() and "cache" in path.name
    )
    assert caches == ["frame-cache"]

    source = (
        Path(mdstats.__file__).resolve().parent
        / "training_data"
        / "campaign_target_size_runtime.py"
    ).read_text(encoding="utf-8")
    # The orchestration composes existing owners; it owns no cache or
    # authentication checklist of its own.
    for forbidden in (
        "trust_cache",
        "fast_mode",
        "skip_validation",
        "write_frame_data_cache",
        "certify_vasp_simulation_controls",
        "read_vasp_frames",
    ):
        assert forbidden not in source


@pytest.mark.parametrize("workers", [1, 2])
def test_p4_canonical_frame_construction_is_worker_count_invariant(
    tmp_path: Path, workers: int
):
    """Worker count changes throughput only, never a scientific product."""

    import tests.test_mlff_target_size_execution_p3a as p3a

    # A genuinely multi-run corpus, so ``workers>1`` really executes the
    # isolated process map rather than being clamped back to serial.
    manifest = p3a._order_divergent_manifest(tmp_path)
    sources = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    assert len(sources.sources) > 1
    source_authority = build_source_authority_from_data2_catalog(
        sources, manifest=manifest
    )
    authenticated = authenticate_vasp_source_authority(
        source_authority, base_directory=tmp_path
    )
    frame_data = frame_authority_module.read_authenticated_vasp_frame_data(
        authenticated
    )
    progress: list[str] = []
    authority = build_canonical_frame_authority(
        source_authority,
        frame_data,
        temperature_targets_by_run=(
            frame_authority_module.authenticated_vasp_temperature_targets(
                authenticated
            )
        ),
        parallel_workers=workers,
        progress_callback=progress.append,
    )
    reference = build_vasp_canonical_frame_authority(
        source_authority, base_directory=tmp_path
    )
    assert authority.content_digest == reference.content_digest
    assert [f.frame_uid for f in authority.frames] == [
        f.frame_uid for f in reference.frames
    ]
    assert authority.eligibility.to_dict() == reference.eligibility.to_dict()
    assert [r.to_dict() for r in authority.strain_records] == [
        r.to_dict() for r in reference.strain_records
    ]
    assert authority.duplicates.to_dict() == reference.duplicates.to_dict()
    # The expensive phase reports progress rather than going silent, and the
    # reported worker count is the one that actually ran.
    assert progress and all("canonical frames" in line for line in progress)
    assert all(f"workers={workers}" in line for line in progress)
    assert len(progress) == len(source_authority.sources)


def test_p4_authentication_is_independent_of_frame_payload(tmp_path: Path, monkeypatch):
    """Fresh P1 authentication reads no frame payload at all."""

    manifest, sources, _frames, _data4 = p4d._data4_bundle(tmp_path)
    source_authority = build_source_authority_from_data2_catalog(
        sources, manifest=manifest
    )
    calls = _count_source_frame_reads(monkeypatch)
    authenticated = authenticate_vasp_source_authority(
        source_authority, base_directory=tmp_path
    )
    assert calls == []
    assert set(authenticated) == {s.run_id for s in source_authority.sources}
    for record in authenticated.values():
        assert record.energy_channel is not None
        assert record.temperature_target.evidence


@pytest.mark.parametrize(
    "field, value",
    [
        ("source_identity_signature", "identity"),
        ("source_control_digest", "control"),
        ("ensemble_certificate_digest", "certificate"),
        ("ensemble", "ensemble"),
        ("selected_energy_channel", "channel"),
        ("selected_energy_units", "units"),
        ("selected_energy_semantic_role", "role"),
    ],
)
def test_p4_authentication_rejects_each_perturbed_source_fact(
    tmp_path: Path, field: str, value: str
):
    """One owner proves every P1 fact; a valid cache can never mask any of them."""

    from dataclasses import replace

    from mdstats.training_data._common import TrainingDataInputError

    manifest, sources, _frames, _data4 = p4d._data4_bundle(tmp_path)
    source_authority = build_source_authority_from_data2_catalog(
        sources, manifest=manifest
    )
    # A well-formed authority is accepted...
    assert authenticate_vasp_source_authority(
        source_authority, base_directory=tmp_path
    )

    original = source_authority.sources[0]
    if field == "ensemble":
        replacement = "nve" if original.ensemble != "nve" else "nvt"
    elif field in {"source_identity_signature", "source_control_digest",
                   "ensemble_certificate_digest"}:
        replacement = "0" * 64
    else:
        replacement = f"perturbed-{value}"
    perturbed = replace(
        source_authority,
        sources=(replace(original, **{field: replacement}),)
        + tuple(source_authority.sources[1:]),
    )
    with pytest.raises(TrainingDataInputError):
        authenticate_vasp_source_authority(perturbed, base_directory=tmp_path)
