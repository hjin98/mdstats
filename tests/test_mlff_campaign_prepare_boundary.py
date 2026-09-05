"""`prepare` owns publication verification, input change, and its own CAS.

These are the four consequences of one ownership boundary, so they are tested
as one boundary:

.. code-block:: text

    capture the currentness token
     -> decide reuse or rebuild from exact prepare-owned input identities
     -> build and publish immutable prepared content
     -> create-or-VERIFY every identity that already exists
     -> short CAS adoption against the captured token
     -> publish the derived view the resulting state actually has

Everything below drives the real CLI entry point, the real publishers, the real
frame-cache owner, and the real ``CampaignStore``; only MACE's numerical work is
substituted, strictly below those owners.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import tests._mlff_post_selection_fixture as p5
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_prepared_generation as prepared_module
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_prepared_generation import (
    PreparedGenerationError,
    prepared_generation_root,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_cutover import (
    TargetSizeStalePreparationError,
)
from mdstats.training_data.campaign_target_size_runtime import (
    load_prepared_target_size_generation,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _ingesting_config() -> str:
    """The P4 fixture campaign with a profile the catalog owner can rebuild.

    ``prepare`` must be able to reach its own catalog reconstruction path, so
    this fixture declares the one material profile the campaign CLI resolves.
    """

    return p4d._CONFIG.replace('profile = "generic"', 'profile = "lta"')


def _campaign(tmp_path: Path):
    with patch.object(p4d, "_CONFIG", _ingesting_config()):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    return config, cfg, paths


def _prepared(tmp_path: Path):
    config, cfg, paths = _campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    return config, cfg, paths


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def _history(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_history(store)
    finally:
        store.close()


def _mutate_one_source(cfg, paths) -> Path:
    """Change source bytes in a way that stays a valid, ingestible run."""

    training_root = Path(cli._path_cfg(cfg, paths, "training_root"))
    victim = sorted(training_root.rglob("vasprun.xml"))[0]
    victim.write_text(
        victim.read_text(encoding="utf-8").replace(
            '<i name="SIGMA">0.05</i>', '<i name="SIGMA">0.06</i>', 1
        ),
        encoding="utf-8",
    )
    return victim


# ---------------------------------------------------------------------------
# IR1 -- an existing content identity is verified, never assumed
# ---------------------------------------------------------------------------


def test_a_preseeded_prepared_component_is_verified_before_adoption(
    tmp_path: Path,
):
    """A pathname states what bytes should be there; it does not prove it."""

    config, _cfg, paths = _prepared(tmp_path)
    before = _revision(paths)
    objects = prepared_generation_root(paths) / "objects"
    victim = sorted(objects.iterdir())[0]
    original = victim.read_bytes()
    victim.write_bytes(b'{"schema": "not-what-this-digest-names"}\n')

    with pytest.raises(PreparedGenerationError):
        p4d._run(config, "prepare")

    after = _revision(paths)
    assert after.state_revision == before.state_revision
    assert after.state.generation == before.state.generation
    # The conflicting object is not silently repaired: another generation may
    # depend on whatever is actually on disk.
    assert victim.read_bytes() != original


def test_a_preseeded_prepared_manifest_is_verified_before_adoption(tmp_path: Path):
    config, _cfg, paths = _prepared(tmp_path)
    before = _revision(paths)
    manifest_path = (
        prepared_generation_root(paths)
        / "generations"
        / f"{before.state.prepared_manifest_digest}.json"
    )
    assert manifest_path.is_file()
    manifest_path.write_text('{"schema": "wrong"}\n', encoding="utf-8")

    with pytest.raises(PreparedGenerationError):
        p4d._run(config, "prepare")

    after = _revision(paths)
    assert after.state_revision == before.state_revision


def test_a_corrupt_frame_member_under_an_intact_entry_manifest_fails_closed(
    tmp_path: Path,
):
    """The entry manifest can be perfectly intact while a member has rotted."""

    config, _cfg, paths = _prepared(tmp_path)
    before = _revision(paths)
    manifest = read_prepared_generation_manifest(
        paths, before.state.prepared_manifest_digest
    )
    cache_root = paths.internal / "frame-cache"
    entry_manifest = cache_root / str(manifest.frame_records[0]["relative_path"])
    entry_bytes = entry_manifest.read_bytes()
    entry = json.loads(entry_bytes.decode("utf-8"))
    member = entry_manifest.parent / str(entry["members"][0]["relative_path"])
    member.write_bytes(member.read_bytes() + b"\x00")

    with pytest.raises(Exception) as excinfo:
        p4d._run(config, "prepare")
    assert "frame-cache" in str(excinfo.value).lower().replace("_", "-")

    # The entry manifest is untouched, and no generation was advanced onto the
    # unauthenticated entry.
    assert entry_manifest.read_bytes() == entry_bytes
    assert _revision(paths).state_revision == before.state_revision


# ---------------------------------------------------------------------------
# IR2 -- `prepare` owns changed-source detection, and is idempotent otherwise
# ---------------------------------------------------------------------------


def test_ordinary_prepare_routes_a_changed_source_to_a_fresh_generation(
    tmp_path: Path,
):
    """No operator escape flag: the change is detected by the prepare owner."""

    config, cfg, paths = _prepared(tmp_path)
    first = _revision(paths)
    first_manifest = read_prepared_generation_manifest(
        paths, first.state.prepared_manifest_digest
    )
    _mutate_one_source(cfg, paths)

    # Before the next explicit `prepare`, the adopted generation still means
    # exactly what it meant when it was adopted.
    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, _revision(paths)
        )
    finally:
        store.close()
    assert authorities.identity == dict(first_manifest.scientific_identity)

    assert p4d._run(config, "prepare") == 0

    second = _revision(paths)
    assert second.state.generation == first.state.generation + 1
    assert (
        second.state.prepared_manifest_digest
        != first.state.prepared_manifest_digest
    )
    # The superseded generation's published bytes are untouched; nothing was
    # edited in place to produce the successor.
    assert read_prepared_generation_manifest(
        paths, first.state.prepared_manifest_digest
    ).scientific_identity == first_manifest.scientific_identity


def test_an_unchanged_repeated_prepare_is_a_no_op(tmp_path: Path):
    config, _cfg, paths = _prepared(tmp_path)
    before = _revision(paths)
    transitions = len(_history(paths))
    assert p4d._run(config, "prepare") == 0
    after = _revision(paths)
    assert after.state_revision == before.state_revision
    assert len(_history(paths)) == transitions


def test_an_unchanged_terminal_prepare_succeeds_and_preserves_terminal_state(
    tmp_path: Path,
):
    """A scientifically valid no-op must not fail inside a derived file writer."""

    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    before = _revision(paths)
    assert before.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
    view_path = paths.results / "target-size-state.json"
    before_view = json.loads(view_path.read_text(encoding="utf-8"))

    assert p4d._run(config, "prepare") == 0

    after = _revision(paths)
    assert after.state_revision == before.state_revision
    assert after.state.generation == before.state.generation
    assert after.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
    assert after.state.terminal.to_dict() == before.state.terminal.to_dict()
    after_view = json.loads(view_path.read_text(encoding="utf-8"))
    assert after_view["terminal"] == before_view["terminal"]
    assert after_view["canonical_generation"] == before_view["canonical_generation"]


# ---------------------------------------------------------------------------
# IR3 -- adoption is fenced to the revision the build started from
# ---------------------------------------------------------------------------


class _PublicationBarrier:
    """Hold a real publication open so two prepares genuinely overlap."""

    def __init__(self, *, hold: bool):
        self.real = prepared_module.publish_prepared_generation
        self.published = threading.Event()
        self.release = threading.Event()
        self.hold = hold
        self.calls = 0
        self._owner: int | None = None
        self._lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        result = self.real(*args, **kwargs)
        with self._lock:
            self.calls += 1
            mine = self._owner is None
            if mine:
                self._owner = threading.get_ident()
        if self.hold and mine:
            self.published.set()
            assert self.release.wait(timeout=300)
        return result


def test_identical_concurrent_prepares_converge_on_one_generation(tmp_path: Path):
    """Same inputs, two real publishers: one generation, no second transition."""

    config, _cfg, paths = _prepared(tmp_path)
    before = _revision(paths)
    barrier = _PublicationBarrier(hold=False)
    gate = threading.Barrier(2, timeout=300)
    results: list[object] = []

    def attempt() -> None:
        gate.wait()
        results.append(p4d._run(config, "prepare"))

    with patch.object(prepared_module, "publish_prepared_generation", barrier):
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=300)

    assert results == [0, 0]
    assert barrier.calls == 2, "both attempts must reach the real publisher"
    after = _revision(paths)
    assert after.state_revision == before.state_revision
    assert after.state.generation == before.state.generation


def test_a_stale_concurrent_prepare_cannot_supersede_the_winner(tmp_path: Path):
    """Last finisher does not win; the token the build began from decides."""

    config, cfg, paths = _campaign(tmp_path)
    barrier = _PublicationBarrier(hold=True)
    failures: list[BaseException] = []

    def loser() -> None:
        try:
            p4d._run(config, "prepare")
        except BaseException as exc:  # noqa: BLE001 - re-raised by the assertion
            failures.append(exc)

    with patch.object(prepared_module, "publish_prepared_generation", barrier):
        thread = threading.Thread(target=loser)
        thread.start()
        assert barrier.published.wait(timeout=300), "the loser never published"

        # The winner runs its *entire* prepare -- including the expensive
        # catalog reconstruction -- while the loser sits inside publication.
        # That is only possible because no campaign-wide writer lock is held
        # across construction.
        _mutate_one_source(cfg, paths)
        assert p4d._run(config, "prepare") == 0
        winner = _revision(paths)

        barrier.release.set()
        thread.join(timeout=300)

    assert failures and isinstance(failures[0], TargetSizeStalePreparationError)
    current = _revision(paths)
    assert current.state_revision == winner.state_revision
    assert current.state.generation == winner.state.generation

    # The loser's residue is unreachable content, and the winner's generation
    # is still fully loadable through the real consumption owner.
    store = CampaignStore(paths.state_db)
    try:
        authorities = load_prepared_target_size_generation(cfg, paths, store, current)
    finally:
        store.close()
    assert authorities.frame_data_by_run
