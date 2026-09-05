"""Storage composes with the prepared generation, across every affected operation.

Once the prepared substrate became a durable restart dependency, "cleanup does
not break the campaign" stopped being a statement about cleanup alone. Storage
Revision 38 also deduplicates, archives, verifies, restores, and performs
campaign-state maintenance, and each of those transforms bytes a later command
must still be able to consume. A prepared generation that survives cleanup but
not dedup is not protected; it is lucky.

So every operation here runs through the real storage owners, and after each one
a real downstream consumer is re-run: the prepared generation must still load
and authenticate, and it must do so without reaching a single preparation owner.
That last part is the whole point - a storage operation that silently pushed the
next command back into DATA4 restore or live source parsing would look perfectly
successful while having destroyed the boundary this work exists to establish.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_prepared_generation import (
    prepared_generation_protected_paths,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_runtime import (
    load_prepared_target_size_generation,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)


class _NoReconstruction:
    """Fail loudly if a preparation owner is reached during consumption."""

    def __init__(self, monkeypatch) -> None:
        import mdstats.io as io_module
        from mdstats.training_data import campaign_target_size_runtime as runtime
        from mdstats.training_data import data4_sharded_store

        self.reached: list[str] = []

        def guard(name):
            def _guard(*args, **kwargs):
                self.reached.append(name)
                raise AssertionError(
                    f"consumption after a storage operation reached {name}"
                )

            return _guard

        monkeypatch.setattr(
            data4_sharded_store,
            "read_data4_sharded_record",
            guard("read_data4_sharded_record"),
        )
        monkeypatch.setattr(io_module, "read_vasp_frames", guard("read_vasp_frames"))
        monkeypatch.setattr(
            runtime,
            "build_prepared_target_size_substrate",
            guard("build_prepared_target_size_substrate"),
        )


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def _consume(cfg, paths) -> None:
    """Run a real downstream consumer of the current prepared generation."""

    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, revision
        )
    finally:
        store.close()
    assert authorities.frame_data_by_run
    assert authorities.common.content_digest == (
        revision.state.common_preparation_digest
    )
    # Touch the normalized payload so a detached or emptied member is a failure
    # here rather than a surprise in the next real command.
    for data in authorities.frame_data_by_run.values():
        assert data.n_frames > 0
        assert data.fractional_positions.shape[0] == data.n_frames


def _selected_campaign(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
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
    cfg, paths = cli._load_config(config)
    return config, cfg, paths


def _storage(config: Path, *argv: str) -> int:
    return cli.main(["--config", str(config), "storage", *argv])


def test_every_affected_storage_operation_leaves_the_generation_consumable(
    tmp_path: Path, monkeypatch, capsys
):
    config, cfg, paths = _selected_campaign(tmp_path)
    manifest = read_prepared_generation_manifest(
        paths, _revision(paths).state.prepared_manifest_digest
    )
    protected = prepared_generation_protected_paths(
        paths, [_revision(paths).state.prepared_manifest_digest]
    )
    assert protected

    def _protected_snapshot() -> dict[str, bytes]:
        return {
            str(path): path.read_bytes()
            for path in sorted(protected)
            if path.is_file()
        }

    before = _protected_snapshot()
    assert before, "the generation protects no files, so this proves nothing"

    operations: list[tuple[str, tuple[str, ...]]] = [
        ("report", ("report",)),
        ("report --deep", ("report", "--deep")),
        ("cleanup safe (dry run)", ("cleanup", "--tier", "safe", "--dry-run")),
        ("cleanup safe (apply)", ("cleanup", "--tier", "safe", "--apply")),
        ("cleanup cache (dry run)", ("cleanup", "--tier", "cache", "--dry-run")),
        ("cleanup cache (apply)", ("cleanup", "--tier", "cache", "--apply")),
        ("deduplicate (dry run)", ("deduplicate", "--dry-run")),
        ("deduplicate (apply)", ("deduplicate", "--apply")),
        ("archive create (dry run)", ("archive", "create", "--dry-run")),
        (
            "archive create (apply, keep hot)",
            ("archive", "create", "--apply", "--keep-hot"),
        ),
        ("archive list", ("archive", "list")),
    ]

    executed: list[str] = []
    for label, argv in operations:
        assert _storage(config, *argv) == 0, label
        executed.append(label)
        # The bytes the current generation requires are still exactly there.
        assert _protected_snapshot() == before, (
            f"{label} changed content the current prepared generation requires"
        )
        # ...and the next command still consumes them without reconstructing.
        guard = _NoReconstruction(monkeypatch)
        _consume(cfg, paths)
        assert guard.reached == []
        monkeypatch.undo()

    with capsys.disabled():
        print(
            "\n[storage composition] operations exercised against one prepared "
            f"generation:\n  " + "\n  ".join(executed)
        )


def test_archive_verify_and_restore_keep_the_generation_authoritative(
    tmp_path: Path, monkeypatch
):
    """Verify and restore are representation operations, never authority ones."""

    config, cfg, paths = _selected_campaign(tmp_path)
    assert _storage(config, "archive", "create", "--apply", "--keep-hot") == 0

    from types import SimpleNamespace

    from mdstats.training_data.storage import commands as storage_commands

    store = CampaignStore(paths.state_db, create=False)
    try:
        boundary = cli._campaign_ownership_boundary(cfg, paths, store)
        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        with cli.observational_campaign_state():
            catalog = storage_commands.storage_archive(
                context, SimpleNamespace(archive_command="list")
            )
    finally:
        store.close()

    identities = [
        str(item["archive_identity"]) for item in catalog.get("archives", ())
    ]
    if not identities:
        pytest.skip(
            "no owner in this bounded campaign declared cold-replaceable bulk, so "
            "there is no cataloged archive to verify or restore"
        )

    before = _revision(paths)
    for identity in identities:
        assert _storage(config, "archive", "verify", identity) == 0
        assert _storage(config, "archive", "restore", identity, "--dry-run") == 0

    after = _revision(paths)
    # Neither operation may touch scientific currentness.
    assert after.state_revision == before.state_revision
    assert after.state.prepared_manifest_digest == (
        before.state.prepared_manifest_digest
    )
    guard = _NoReconstruction(monkeypatch)
    _consume(cfg, paths)
    assert guard.reached == []


def test_retiring_a_historical_generation_keeps_the_members_it_shares(
    tmp_path: Path, monkeypatch, capsys
):
    """Reachability, not pathname age, decides what a retirement may release.

    Two generations that differ in one preparation policy still share the whole
    normalized payload and several immutable components. Retiring the older one
    must not take the shared content with it, because the newer one is the thing
    the campaign is actually running on.
    """

    config, cfg, paths = _selected_campaign(tmp_path)
    first = _revision(paths)
    first_manifest = read_prepared_generation_manifest(
        paths, first.state.prepared_manifest_digest
    )

    text = config.read_text(encoding="utf-8")
    assert "development_minimum_independent_units = 4" in text
    config.write_text(
        text.replace(
            "development_minimum_independent_units = 4",
            "development_minimum_independent_units = 3",
        ),
        encoding="utf-8",
    )
    store = CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    finally:
        store.close()
    assert p4d._run(config, "prepare") == 0
    # The consumer must read the configuration now in force; the previous one
    # names a preparation policy this generation was deliberately not built
    # under, and the loader is right to refuse it.
    cfg, paths = cli._load_config(config)

    second = _revision(paths)
    assert second.state.generation == first.state.generation + 1
    second_manifest = read_prepared_generation_manifest(
        paths, second.state.prepared_manifest_digest
    )

    shared = prepared_generation_protected_paths(
        paths, [first.state.prepared_manifest_digest]
    ) & prepared_generation_protected_paths(
        paths, [second.state.prepared_manifest_digest]
    )
    assert shared, "the two generations share nothing, so nothing is being proven"
    # The normalized payload is shared outright.
    assert second_manifest.frame_records == first_manifest.frame_records

    shared_before = {
        str(path): path.read_bytes() for path in sorted(shared) if path.is_file()
    }
    for argv in (
        ("cleanup", "--tier", "safe", "--apply"),
        ("cleanup", "--tier", "cache", "--apply"),
        ("deduplicate", "--apply"),
        ("archive", "create", "--apply", "--keep-hot"),
    ):
        assert _storage(config, *argv) == 0
        assert {
            str(path): path.read_bytes() for path in sorted(shared) if path.is_file()
        } == shared_before, f"{argv} released content the current generation shares"

    guard = _NoReconstruction(monkeypatch)
    _consume(cfg, paths)
    assert guard.reached == []
    with capsys.disabled():
        print(
            f"\n[shared-member retention] {len(shared)} object(s) reachable from "
            "both generations survived every applied storage operation"
        )
