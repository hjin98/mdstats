"""Assembled real-owner storage acceptance across the P1-P7 lifecycle.

Nothing in this module mocks an inventory, currentness, or retention owner.
The campaign, CampaignStore, P1-P5 lifecycle, the accepted final-production
publication resolver, the P7 binding/plan/reference/component/record owners,
the campaign-store fences, the storage planner/executor/archive/dedup owners,
and the real CLI parser and dispatch all execute as production code.  Only MACE
training, the numerical model forward, and the conversion/execution of a toy
checkpoint sit below the already accepted P5/P7 seams.

This is functional integration.  It is not, and does not claim to be, real
external-DFT scientific qualification or long production GPU/HPC qualification,
both of which remain deferred.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import tests._mlff_post_selection_fixture as p5
import tests._mlff_qualification_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.qualification.publication import (
    checkpoint_path_for_member,
    resolve_authenticated_final_publication,
)
from mdstats.training_data.qualification.store import (
    ATTEMPT_TERMINAL,
    read_attempt_state,
    release_attempt_reference,
)
from mdstats.training_data.storage import commands as storage_commands
from mdstats.training_data.storage.archive import (
    list_archives,
    restore_cold_archive,
    verify_cold_archive,
)
from mdstats.training_data.storage.control_plane import open_storage_control_plane
from mdstats.training_data.storage.inventory import (
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
)
from mdstats.training_data.storage.plan import StoragePlanStaleError, revalidate_plan
from mdstats.training_data.storage.policy import (
    ACTION_ARCHIVE,
    ACTION_CLEANUP,
    ACTION_REPORT,
    resolve_storage_policy,
)


# ---------------------------------------------------------------------------
# Real-owner helpers
# ---------------------------------------------------------------------------


def _open(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    boundary = cli._campaign_ownership_boundary(cfg, paths, store)
    return cfg, paths, store, boundary


def _context(config: Path):
    cfg, paths, store, boundary = _open(config)
    return storage_commands.StorageCommandContext(cfg, paths, store, boundary), store


def _snapshot(config: Path):
    cfg, paths, store, boundary = _open(config)
    try:
        return build_storage_inventory(
            cfg,
            paths,
            store,
            protected_inputs=boundary.protected_inputs,
            control_plane=open_storage_control_plane(paths),
        ), paths
    finally:
        store.close()


def _published_checkpoints(config: Path, harness) -> tuple[Path, ...]:
    """The exact frozen representative checkpoints of the current publication."""

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        publication = resolve_authenticated_final_publication(session.context)
        return tuple(
            checkpoint_path_for_member(session.context, member)
            for member in publication.members
        )
    finally:
        store.close()


def _run_to_waiting(config: Path, harness) -> int:
    return fx.run_qualification_command(config, "run", harness=harness)


def _supply_reference(config: Path, harness) -> None:
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()


def _qualify_nonlocked(config: Path, harness) -> int:
    assert _run_to_waiting(config, harness) == 0
    _supply_reference(config, harness)
    return fx.run_qualification_command(config, "run", harness=harness)


def _release_attempt(config: Path, harness) -> None:
    """Drive the attempt reference to terminal through the real P7 owner."""

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        release_attempt_reference(
            paths,
            session.context.selected.binding,
            attempt_identity=session.binding.attempt_identity,
        )
        state = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        assert state is not None and state.state == ATTEMPT_TERMINAL
        assert state.referenced_paths == ()
    finally:
        store.close()


@pytest.fixture(scope="module")
def qualified_campaign(tmp_path_factory):
    """One real campaign driven through P1-P5 and a terminal P7 attempt."""

    tmp_path = tmp_path_factory.mktemp("storage-qualified")
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)
    return config, workspace, harness


@pytest.fixture(scope="module")
def waiting_campaign(tmp_path_factory):
    """A real campaign truthfully stopped at ``waiting_for_reference``."""

    tmp_path = tmp_path_factory.mktemp("storage-waiting")
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _run_to_waiting(config, harness) == 0
    _release_attempt(config, harness)
    return config, workspace, harness


# ---------------------------------------------------------------------------
# R10-1 - post-attempt cross-owner dependency closure
# ---------------------------------------------------------------------------


def test_post_terminal_p7_publication_still_pins_the_exact_p5_checkpoint(
    qualified_campaign,
):
    """The attempt lease is gone; the publication dependency is not."""

    config, _workspace, harness = qualified_campaign
    checkpoints = _published_checkpoints(config, harness)
    assert checkpoints

    snapshot, _paths = _snapshot(config)
    for checkpoint in checkpoints:
        protected, why = snapshot.path_protection(checkpoint)
        assert protected, f"{checkpoint} lost its cross-owner protection"
        assert "publication" in why or "checkpoint" in why or "required by" in why

    # Every consequential action agrees, and none of them plans to touch it.
    for policy in (
        resolve_storage_policy({}, action=ACTION_CLEANUP, tier="safe"),
        resolve_storage_policy({}, action=ACTION_CLEANUP, tier="cache"),
    ):
        context, store = _context(config)
        try:
            plan, _ = storage_commands.build_cleanup_plan(context, policy)
            planned = {str(item.path) for item in plan.actions}
            assert not (planned & {str(item) for item in checkpoints})
        finally:
            store.close()
    for decision in archive_candidates(snapshot):
        assert not any(
            str(decision.path) == str(item) or str(item).startswith(str(decision.path) + os.sep)
            for item in checkpoints
        ) or not decision.eligible

    # The ownership boundary agrees independently of the closure.
    _cfg, _paths, store, boundary = _open(config)
    try:
        for checkpoint in checkpoints:
            authorized, _detail = boundary.destructive_authorization(checkpoint)
            # The P7 attempt reference is released, so the boundary alone would
            # allow it; the cross-owner closure is what still protects it.
            assert authorized
    finally:
        store.close()


def test_waiting_for_reference_pins_the_publication_and_resume_lineage(
    waiting_campaign,
):
    config, _workspace, harness = waiting_campaign
    checkpoints = _published_checkpoints(config, harness)
    snapshot, paths = _snapshot(config)
    for checkpoint in checkpoints:
        protected, _why = snapshot.path_protection(checkpoint)
        assert protected

    waiting = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("p7:waiting_for_reference")
    ]
    assert waiting, "the P7 owner reported no waiting_for_reference lineage"

    # The exact reference request lineage and every durable P7 record are
    # retained through storage planning; only released attempt-local bulk is
    # ever a candidate, and the attempt record itself is never one.
    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_CLEANUP, tier="cache")
        plan, _ = storage_commands.build_cleanup_plan(context, policy)
        qualification = paths.internal / "qualification"
        for action in plan.actions:
            candidate = Path(action.path)
            if qualification not in candidate.parents:
                continue
            assert "attempts" in candidate.parts, candidate
            assert candidate.name != "attempt-state.json", candidate
        reference_root = paths.workspace / "qualification-references"
        assert reference_root.is_dir()
        protected, why = context.snapshot().path_protection(reference_root)
        assert protected, why
    finally:
        store.close()

    # Applying the cache tier leaves the waiting lineage resumable.
    assert p4d._run(config, "storage", "cleanup", "--tier", "cache", "--apply") == 0
    assert (paths.workspace / "qualification-references").is_dir()
    assert _published_checkpoints(config, harness)


def test_p4_current_terminal_reload_survives_every_allowed_storage_operation(
    tmp_path: Path,
):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    _cfg, paths, store, _boundary = _open(config)
    try:
        before = load_target_size_campaign_revision(store)
    finally:
        store.close()

    for argv in (
        ["storage", "report"],
        ["storage", "cleanup", "--tier", "safe", "--apply"],
        ["storage", "cleanup", "--tier", "cache", "--apply"],
        ["storage", "deduplicate", "--apply"],
        ["storage", "archive", "create", "--apply"],
    ):
        assert p4d._run(config, *argv) == 0

    reopened = CampaignStore(paths.state_db)
    try:
        after = load_target_size_campaign_revision(reopened)
        assert after == before
        assert after.state.terminal == before.state.terminal
    finally:
        reopened.close()

    # And the P7 publication still re-authenticates its exact P5 member bytes.
    assert _published_checkpoints(config, harness)


def test_advancing_the_lineage_releases_the_old_current_dependency(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)
    old_checkpoints = _published_checkpoints(config, harness)

    snapshot, _paths = _snapshot(config)
    assert all(snapshot.path_protection(item)[0] for item in old_checkpoints)

    # A genuinely newer substrate generation becomes current.
    p5.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    advanced, paths = _snapshot(config)
    assert advanced.current_generation == 2
    historical = [item for item in archive_candidates(advanced) if item.eligible]
    assert historical, "the superseded generation produced no cold-replaceable bulk"
    assert any("g1" in str(item.path) for item in historical)


# ---------------------------------------------------------------------------
# R10-2 - the real P5 object-before-pointer race
# ---------------------------------------------------------------------------


def test_p5_object_before_pointer_publication_wins_against_storage(tmp_path: Path):
    """A paused real publication is never observed half-open by storage.

    The publication is held between its immutable object write and the
    CampaignStore pointer commit.  A real public storage operation runs
    concurrently and reaches the owner barrier while that window is open; it
    must not proceed until the window closes, and when it does the object is
    still there and the pointer resolves.

    The barrier itself is production code: the spy below only observes when the
    storage executor is about to enter it, so the test can wait for that moment
    instead of guessing a sleep long enough for a loaded machine.
    """

    from mdstats.training_data import post_selection_store as pointer_mod
    from mdstats.training_data.storage import executor as executor_mod

    harness = p5.PostSelectionHarness()
    config, _workspace = p5.build_selected_campaign(tmp_path)
    assert p5.run_cross_validate(config, harness) == 0

    window_open = threading.Event()
    storage_at_barrier = threading.Event()
    order: list[str] = []
    original_pointer = pointer_mod.publish_current_post_selection_pointer
    original_barrier = executor_mod.owner_mutation_barrier

    def observed_barrier(paths, generations):
        storage_at_barrier.set()
        return original_barrier(paths, generations)

    def paused_pointer(*args, **kwargs):
        if not window_open.is_set():
            window_open.set()
            # The publisher holds the owner barrier across this wait, so the
            # storage executor must block on it rather than proceed.
            storage_at_barrier.wait(60.0)
            time.sleep(0.5)
        original_pointer(*args, **kwargs)
        order.append("publication")

    storage_error: list[BaseException] = []

    def storage_worker() -> None:
        window_open.wait(120.0)
        try:
            assert p4d._run(config, "storage", "cleanup", "--tier", "cache", "--apply") == 0
            order.append("storage")
        except BaseException as exc:  # pragma: no cover - surfaced below
            storage_error.append(exc)

    worker = threading.Thread(target=storage_worker, daemon=True)
    pointer_mod.publish_current_post_selection_pointer = paused_pointer
    executor_mod.owner_mutation_barrier = observed_barrier
    try:
        worker.start()
        assert p5.run_train_production(config, harness) == 0
    finally:
        pointer_mod.publish_current_post_selection_pointer = original_pointer
        executor_mod.owner_mutation_barrier = original_barrier
        worker.join(180.0)
    assert not storage_error, storage_error
    assert storage_at_barrier.is_set(), "the storage executor never reached the barrier"
    assert order and order[0] == "publication", order

    # The immutable object survived and the current pointer resolves.
    _cfg, _paths, store, _boundary = _open(config)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            build_post_selection_context,
        )
        from mdstats.training_data.post_selection_publication import (
            resolve_current_final_production_publication,
        )

        cfg, paths = cli._load_config(config)
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
    finally:
        store.close()


def test_owner_advancement_between_plan_and_apply_refuses_the_plan(
    qualified_campaign,
):
    config, _workspace, _harness = qualified_campaign
    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_CLEANUP, tier="cache")
        plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
        # A new owner artifact appears: the closure and owner identity move.
        scratch = Path(context.paths.internal) / "post-selection" / "g99" / "objects"
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "object.json").write_text("{}\n", encoding="utf-8")
        advanced = context.snapshot()
        with pytest.raises(StoragePlanStaleError, match="owner|closure"):
            revalidate_plan(plan, advanced, policy)
    finally:
        store.close()


def test_storage_policy_change_between_plan_and_apply_refuses(qualified_campaign):
    config, _workspace, _harness = qualified_campaign
    context, store = _context(config)
    try:
        planned = resolve_storage_policy({}, action=ACTION_CLEANUP, tier="safe")
        plan, snapshot = storage_commands.build_cleanup_plan(context, planned)
        changed = resolve_storage_policy(
            {"storage": {"safety_reserve_bytes": 12345}},
            action=ACTION_CLEANUP,
            tier="safe",
            apply=True,
        )
        with pytest.raises(StoragePlanStaleError, match="policy changed"):
            revalidate_plan(plan, snapshot, changed)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Cache eviction with an exact owner rebuild
# ---------------------------------------------------------------------------


def test_positive_cache_eviction_rebuilds_the_identical_owner_result(tmp_path: Path):
    """The one owner-certified cache seam: evict, rebuild, prove identity."""

    import mdstats

    harness = p5.PostSelectionHarness()
    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths, store, boundary = _open(config)
    try:
        manifest_path = paths.internal / "frame-cache" / "frame-cache.json"
        before = json.loads(manifest_path.read_text(encoding="utf-8"))

        snapshot = build_storage_inventory(
            cfg,
            paths,
            store,
            protected_inputs=boundary.protected_inputs,
            control_plane=open_storage_control_plane(paths),
        )
        frame_cache = snapshot.view("p1:frame_cache")
        assert frame_cache is not None and frame_cache.cache_reconstructible, (
            frame_cache.detail if frame_cache else "no frame-cache owner view"
        )
        assert any(
            item.artifact_id == "p1:frame_cache" and item.eligible
            for item in cache_candidates(snapshot)
        )
    finally:
        store.close()

    assert p4d._run(config, "storage", "cleanup", "--tier", "cache", "--apply") == 0
    assert not (paths.internal / "frame-cache").exists()

    # The real owner rebuilds it exactly from the authenticated DATA2 catalog.
    cfg, paths, store, _boundary = _open(config)
    try:
        catalog = store.get_record("source_catalog", mdstats.TrainingDataSourceCatalog)
        rebuilt = cli._load_or_rebuild_frame_data(cfg, paths, catalog)
        assert rebuilt
    finally:
        store.close()
    after = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert after["source_catalog_digest"] == before["source_catalog_digest"]
    assert {item["run_id"]: item["sha256"] for item in after["records"]} == {
        item["run_id"]: item["sha256"] for item in before["records"]
    }


def test_safe_tier_never_evicts_the_frame_or_receipt_cache(qualified_campaign):
    config, _workspace, _harness = qualified_campaign
    context, store = _context(config)
    try:
        plan, _snapshot = storage_commands.build_cleanup_plan(
            context, resolve_storage_policy({}, action=ACTION_CLEANUP, tier="safe")
        )
        for action in plan.actions:
            assert "frame-cache" not in str(action.path)
            assert "hash-receipts" not in str(action.path)
            assert action.action == "remove"
    finally:
        store.close()


# ---------------------------------------------------------------------------
# S5 - archive an eligible historical artifact, restore it, reauthenticate cold
# ---------------------------------------------------------------------------


def test_historical_archive_round_trip_through_a_fresh_process(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    # A genuinely newer generation makes the previous one historical.
    p5.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    sample = next(
        path
        for root in (item.path for item in eligible)
        for path in sorted(Path(root).rglob("*"))
        if path.is_file()
    )
    original = sample.read_bytes()

    assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
    assert not sample.exists(), "eligible historical hot bytes were not reclaimed"

    # Fresh process: catalog discovery and verification with nothing cached.
    control_plane = open_storage_control_plane(paths)
    entries = list_archives(control_plane)
    assert entries
    identity = entries[0]["archive_identity"]
    verify_cold_archive(
        control_plane, identity, resolve_storage_policy({}, action=ACTION_REPORT)
    )

    # Explicit restore is what regains the historical capability.
    assert p4d._run(config, "storage", "archive", "restore", identity, "--apply") == 0
    assert sample.read_bytes() == original

    # Restoring bytes never promoted the historical generation to current.
    reopened = CampaignStore(paths.state_db)
    try:
        assert load_target_size_campaign_revision(reopened).state.generation == 2
    finally:
        reopened.close()


def test_archive_refuses_hot_removal_of_a_current_publication_dependency(
    qualified_campaign,
):
    config, _workspace, harness = qualified_campaign
    checkpoints = _published_checkpoints(config, harness)
    snapshot, _paths = _snapshot(config)
    for decision in archive_candidates(snapshot):
        for checkpoint in checkpoints:
            overlapping = str(checkpoint).startswith(str(decision.path))
            if overlapping:
                assert not decision.eligible, decision.reason


# ---------------------------------------------------------------------------
# Interruption after a strict subset of multi-action work
# ---------------------------------------------------------------------------


def test_interrupted_multi_action_cleanup_is_truthful_and_re_plans(tmp_path: Path):
    """A crash after a subset of individually safe removals is recoverable."""

    from mdstats.training_data.storage import executor as executor_mod

    harness = p5.PostSelectionHarness()
    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths, store, boundary = _open(config)
    try:
        records = paths.internal / "records"
        records.mkdir(parents=True, exist_ok=True)
        old = time.time() - 30 * 86_400
        orphans = []
        for name in ("orphan-a", "orphan-b", "orphan-c"):
            child = records / name
            child.mkdir(exist_ok=True)
            (child / "payload.bin").write_bytes(b"orphan" * 64)
            os.utime(child / "payload.bin", (old, old))
            os.utime(child, (old, old))
            orphans.append(child)

        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        policy = resolve_storage_policy(
            {}, action=ACTION_CLEANUP, tier="safe", apply=True
        )
        plan, _snapshot = storage_commands.build_cleanup_plan(context, policy)
        assert len(plan.actions) >= 3

        real_remove = executor_mod._remove_durably
        removed: list[Path] = []

        def failing_remove(path: Path) -> bool:
            if len(removed) >= 2:
                raise RuntimeError("injected interruption after a strict subset")
            removed.append(path)
            return real_remove(path)

        executor_mod._remove_durably = failing_remove
        try:
            with pytest.raises(RuntimeError, match="injected interruption"):
                context.executor(policy).apply(plan, trigger="test:interrupt")
        finally:
            executor_mod._remove_durably = real_remove

        surviving = [item for item in orphans if item.exists()]
        assert len(surviving) == len(orphans) - 2

        # No terminal `complete` audit was published for the interrupted run.
        audit = context.control_plane.read_audit()
        assert all(item.get("status") != "complete" for item in audit)

        # A retry re-inventories and re-plans rather than reusing the old set.
        retry_plan, _ = storage_commands.build_cleanup_plan(context, policy)
        assert len(retry_plan.actions) == len(surviving)
        result = context.executor(policy).apply(retry_plan, trigger="test:retry")
        assert result.status == "complete"
        assert not [item for item in orphans if item.exists()]
    finally:
        store.close()


def test_fresh_process_reauthentication_after_every_completed_operation(
    tmp_path: Path,
):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    for argv in (
        ["storage", "report"],
        ["storage", "report", "--deep"],
        ["storage", "cleanup", "--tier", "safe", "--apply"],
        ["storage", "cleanup", "--tier", "cache", "--apply"],
        ["storage", "deduplicate", "--apply"],
    ):
        assert p4d._run(config, *argv) == 0
        # Each operation is followed by a fresh-process reauthentication of the
        # exact published product through the real P5/P7 owners.
        assert _published_checkpoints(config, harness)


# ---------------------------------------------------------------------------
# P3 publication window and current-resolver hot paths
# ---------------------------------------------------------------------------


def test_p3_publication_window_evidence_survives_storage_cleanup(tmp_path: Path):
    """Storage cannot race P3's publish-before-adopt window.

    The accepted P3 filesystem evidence-graph fence is composed into the same
    ownership boundary the storage executor consults, so freshly published
    execution evidence is denied to storage even though the campaign store has
    not adopted it yet.
    """

    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths, store, boundary = _open(config)
    try:
        revision = load_target_size_campaign_revision(store)
        root = Path(paths.workspace) / revision.state.execution_root
        # A brand-new content-addressed artifact: published, not yet referenced.
        published = root / "materializations" / ("c" * 64 + ".json")
        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_text("{}\n", encoding="utf-8")

        authorized, detail = boundary.destructive_authorization(published)
        assert not authorized
        assert "publish" in detail or "reachab" in detail or "recently" in detail

        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        for tier in ("safe", "cache"):
            payload = storage_commands.storage_cleanup(
                context, SimpleNamespace(tier=tier, apply=True, dry_run=False)
            )
            assert payload["execution"]["status"] in {"complete", "partial"}
            assert published.is_file()
    finally:
        store.close()


def test_current_public_resolver_hot_paths_are_never_archive_removable(
    qualified_campaign,
):
    """Nothing a current resolver dereferences directly can be archived away."""

    config, _workspace, _harness = qualified_campaign
    snapshot, _paths = _snapshot(config)
    hot_required = set(snapshot.hot_required_paths())
    assert hot_required
    for decision in archive_candidates(snapshot):
        if not decision.eligible:
            continue
        for required in hot_required:
            assert not (
                decision.path == required
                or str(required).startswith(str(decision.path) + os.sep)
                or str(decision.path).startswith(str(required) + os.sep)
            ), (decision.path, required)
    # The P5/P7 immutable object stores and the campaign state are all in it.
    names = {str(item) for item in hot_required}
    assert any("post-selection" in item and "objects" in item for item in names)
    assert any("qualification" in item for item in names)
    assert any(item.endswith("campaign.sqlite3") for item in names)
