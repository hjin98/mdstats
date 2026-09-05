"""The prepared generation is built once by `prepare` and consumed thereafter.

The defect these tests close was an ownership error, not a slow helper: the
campaign persisted only the *identities* of the P1/P2/P3-common substrate, so
`select-target-size` and every current-terminal exposure rebuilt the whole
scientific graph from live inputs -- restoring DATA4 and re-authenticating VASP
sources -- merely to prove nothing had changed.  Currentness therefore cost
O(dataset), and a downstream command silently depended on live source bytes it
does not own.

Everything here drives the real campaign CLI, the real ``CampaignStore``, and
the real P1/P2/P3 owners; only MACE's numerical work is substituted, below the
owner boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_prepared_generation import (
    PREPARED_COMPONENT_NAMES,
    PreparedGenerationConfigurationError,
    PreparedGenerationError,
    PreparedGenerationMissingError,
    prepared_generation_protected_paths,
    prepared_generation_root,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_runtime import (
    load_prepared_target_size_generation,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)


def _prepared(tmp_path: Path):
    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    cfg, paths = cli._load_config(config)
    return config, cfg, paths


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


# --- publication -----------------------------------------------------------


def test_prepare_publishes_every_component_and_binds_it_to_the_generation(
    tmp_path: Path,
):
    _config, _cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    digest = revision.state.prepared_manifest_digest
    assert digest is not None, "prepare must bind an immutable prepared substrate"

    manifest = read_prepared_generation_manifest(paths, digest)
    assert set(manifest.component_digests) == set(PREPARED_COMPONENT_NAMES)
    root = prepared_generation_root(paths)
    for name, component_digest in manifest.component_digests.items():
        path = root / "objects" / f"{component_digest}.json"
        assert path.is_file(), f"prepared component {name} was not published"
    assert manifest.frame_records, "the prepared generation binds no frame members"
    # The manifest authenticates the identity the campaign store binds.
    assert manifest.scientific_identity["aggregate_digest"] == (
        revision.state.aggregate_digest
    )


def test_downstream_load_never_reconstructs_the_substrate(tmp_path: Path, monkeypatch):
    """Loading the current generation touches no prepare-only owner.

    The claim is semantic, so the assertions are bound to the real prepare-only
    owners: if any of them runs during a downstream load, the load is
    reconstructing science it was supposed to consume.
    """

    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)

    called: list[str] = []

    def _forbid(name, module, attribute):
        real = getattr(module, attribute)

        def _guard(*args, **kwargs):
            called.append(name)
            return real(*args, **kwargs)

        monkeypatch.setattr(module, attribute, _guard)

    import mdstats.io as io_module
    from mdstats.training_data import data4_sharded_store
    from mdstats.training_data import neutral_substrate

    _forbid("read_vasp_frames", io_module, "read_vasp_frames")
    _forbid(
        "read_data4_sharded_record",
        data4_sharded_store,
        "read_data4_sharded_record",
    )
    for attribute in (
        "authenticate_vasp_source_authority",
        "build_canonical_frame_authority",
        "build_neutral_statistical_base",
    ):
        _forbid(attribute, neutral_substrate, attribute)

    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, revision
        )
    finally:
        store.close()

    assert called == []
    assert authorities.identity["aggregate_digest"] == revision.state.aggregate_digest
    assert authorities.common.content_digest == (
        revision.state.common_preparation_digest
    )
    assert authorities.frame_data_by_run


def test_select_and_terminal_exposure_consume_the_published_generation(
    tmp_path: Path, monkeypatch
):
    """The whole `prepare -> select` boundary performs no upstream replay."""

    config, _cfg, paths = _prepared(tmp_path)

    restores: list[str] = []
    from mdstats.training_data import data4_sharded_store

    real = data4_sharded_store.read_data4_sharded_record

    def _counting(*args, **kwargs):
        restores.append("data4")
        return real(*args, **kwargs)

    monkeypatch.setattr(data4_sharded_store, "read_data4_sharded_record", _counting)

    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    assert restores == []


# --- immutability and generation safety ------------------------------------


def test_source_mutation_does_not_reinterpret_an_adopted_generation(
    tmp_path: Path,
):
    config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    before = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )

    training_root = Path(cli._path_cfg(cfg, paths, "training_root"))
    victims = sorted(training_root.rglob("vasprun.xml"))
    assert victims, "the fixture must own at least one source file"
    victims[0].write_text(
        victims[0].read_text(encoding="utf-8") + "\n<!-- edited -->\n",
        encoding="utf-8",
    )

    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, _revision(paths)
        )
    finally:
        store.close()
    # The adopted generation still means exactly what it meant when adopted.
    assert authorities.identity == dict(before.scientific_identity)


def test_a_second_prepare_never_overwrites_current_frame_members(tmp_path: Path):
    """A future generation may only add; the current one must stay loadable."""

    config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    manifest = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )
    cache_root = paths.internal / "frame-cache"
    members = {
        str(record["relative_path"]): (
            cache_root / str(record["relative_path"])
        ).read_bytes()
        for record in manifest.frame_records
    }
    assert members

    # Republish the normalized content for every run through the real writer,
    # exactly as a future generation's preparation would.
    import mdstats

    store = CampaignStore(paths.state_db)
    try:
        sources = store.get_record(
            "source_catalog", mdstats.TrainingDataSourceCatalog
        )
    finally:
        store.close()
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(
        sources, base_directory=Path(cli._path_cfg(cfg, paths, "training_root"))
    )
    mdstats.write_frame_data_cache(sources, frame_data, cache_root)

    for relative, payload in members.items():
        path = cache_root / relative
        assert path.is_file(), f"a current frame member was deleted: {relative}"
        assert path.read_bytes() == payload

    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, _revision(paths)
        )
    finally:
        store.close()
    assert authorities.frame_data_by_run


def test_unchanged_repeated_prepare_reuses_published_content(tmp_path: Path):
    """Content addressing, not per-generation copies, is what bounds growth."""

    config, _cfg, paths = _prepared(tmp_path)
    objects = prepared_generation_root(paths) / "objects"
    first = {path.name for path in objects.iterdir()}
    assert first

    assert p4d._run(config, "prepare") == 0
    assert {path.name for path in objects.iterdir()} == first


# --- fail-closed behaviour -------------------------------------------------


def test_a_missing_prepared_component_fails_closed(tmp_path: Path):
    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    manifest = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )
    victim = (
        prepared_generation_root(paths)
        / "objects"
        / f"{manifest.component_digests['aggregate']}.json"
    )
    victim.unlink()

    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PreparedGenerationMissingError):
            load_prepared_target_size_generation(cfg, paths, store, revision)
    finally:
        store.close()


def test_a_corrupt_prepared_component_fails_closed(tmp_path: Path):
    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    manifest = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )
    victim = (
        prepared_generation_root(paths)
        / "objects"
        / f"{manifest.component_digests['frame_authority']}.json"
    )
    victim.write_text(victim.read_text(encoding="utf-8") + " ", encoding="utf-8")

    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PreparedGenerationError):
            load_prepared_target_size_generation(cfg, paths, store, revision)
    finally:
        store.close()


def test_a_missing_frame_member_fails_closed_without_rebuilding_it(tmp_path: Path):
    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    manifest = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )
    entry = paths.internal / "frame-cache" / str(
        manifest.frame_records[0]["relative_path"]
    )
    entry.unlink()

    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PreparedGenerationError):
            load_prepared_target_size_generation(cfg, paths, store, revision)
    finally:
        store.close()


def test_a_generation_without_prepared_state_requires_an_explicit_prepare(
    tmp_path: Path,
):
    """Old-format generations are not retrofitted by a downstream command."""

    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    old_format = revision.__class__(
        **{
            **{
                field: getattr(revision, field)
                for field in revision.__dataclass_fields__
                if field != "state"
            },
            "state": revision.state.__class__(
                **{
                    **{
                        name: getattr(revision.state, name)
                        for name in revision.state.__dataclass_fields__
                    },
                    "prepared_manifest_digest": None,
                }
            ),
        }
    )
    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PreparedGenerationMissingError) as excinfo:
            load_prepared_target_size_generation(cfg, paths, store, old_format)
    finally:
        store.close()
    assert "prepare" in str(excinfo.value)


def test_changed_preparation_configuration_is_refused_not_mixed_in(tmp_path: Path):
    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    changed = json.loads(json.dumps(cfg))
    changed["partition"]["development_minimum_independent_units"] = 6

    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PreparedGenerationConfigurationError) as excinfo:
            load_prepared_target_size_generation(changed, paths, store, revision)
    finally:
        store.close()
    assert "Run `prepare`" in str(excinfo.value)


def test_post_selection_only_configuration_does_not_touch_the_generation(
    tmp_path: Path,
):
    """Only the preparation-owning configuration domain can invalidate here."""

    _config, cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    neutral = json.loads(json.dumps(cfg))
    neutral.setdefault("cv", {})["folds"] = 7
    neutral.setdefault("production", {})["horizon_epochs"] = 512

    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(
            neutral, paths, store, revision
        )
    finally:
        store.close()
    assert authorities.identity["aggregate_digest"] == revision.state.aggregate_digest


# --- storage reachability --------------------------------------------------


def test_owner_reachability_protects_every_member_the_generation_needs(
    tmp_path: Path,
):
    """Retention follows what an owner still requires, not a pathname."""

    _config, _cfg, paths = _prepared(tmp_path)
    revision = _revision(paths)
    protected = prepared_generation_protected_paths(
        paths, [revision.state.prepared_manifest_digest]
    )
    manifest = read_prepared_generation_manifest(
        paths, revision.state.prepared_manifest_digest
    )
    root = prepared_generation_root(paths)
    for component_digest in manifest.component_digests.values():
        assert root / "objects" / f"{component_digest}.json" in protected
    cache_root = paths.internal / "frame-cache"
    for record in manifest.frame_records:
        assert cache_root / str(record["relative_path"]) in protected

    # An unrelated digest reaches nothing, so retention never over-protects.
    assert prepared_generation_protected_paths(paths, [None]) == set()
