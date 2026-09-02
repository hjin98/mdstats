"""Assembled real-owner storage acceptance across the P1-P7 lifecycle.

Nothing here mocks an inventory, currentness, liveness, or retention owner. The
campaign, CampaignStore, the P1-P5 lifecycle, the accepted final-production
publication resolver, the P7 binding/plan/reference/component/record owners, the
campaign-store fences, the P5 run-activity owner, and the storage
planner/executor/archive/dedup engines all execute as production code. Only MACE
training, the numerical model forward, and the conversion/execution of a toy
checkpoint sit below the already accepted P5/P7 seams.

This is functional integration. It is not, and does not claim to be, real
external-DFT scientific qualification or long production GPU/HPC qualification,
both of which remain deferred.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import tests._mlff_post_selection_fixture as p5
import tests._mlff_qualification_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignCliError, CampaignStore
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
    read_manifest,
    verify_cold_archive,
)
from mdstats.training_data.storage.control_plane import (
    open_storage_control_plane_readonly,
)
from mdstats.training_data.storage.executor import synchronization_for
from mdstats.training_data.storage.inventory import (
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
)
from mdstats.training_data.storage.plan import (
    StoragePlanStaleError,
    build_storage_plan,
    revalidate_plan,
)
from mdstats.training_data.storage.policy import (
    ACTION_ARCHIVE,
    ACTION_CLEANUP,
    ACTION_REPORT,
    resolve_storage_policy,
)


# ---------------------------------------------------------------------------
# Real-owner helpers
# ---------------------------------------------------------------------------


def _args(**kwargs):
    base = {"tier": None, "apply": False, "dry_run": False, "top": 200, "deep": False}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _open(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    boundary = cli._campaign_ownership_boundary(cfg, paths, store)
    return cfg, paths, store, boundary


def _context(config: Path):
    cfg, paths, store, boundary = _open(config)
    return storage_commands.StorageCommandContext(cfg, paths, store, boundary), store


def _snapshot(config: Path, *, certify: bool = True):
    cfg, paths, store, boundary = _open(config)
    try:
        return (
            build_storage_inventory(
                cfg,
                paths,
                store,
                protected_inputs=boundary.protected_inputs,
                control_plane=open_storage_control_plane_readonly(paths),
                certify=certify,
            ),
            paths,
        )
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


def _advance_generation(config: Path) -> None:
    """Make the current selected lineage historical through the real owner."""

    p5.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0


# ---------------------------------------------------------------------------
# Cross-owner dependency closure after the attempt reference is released
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

    for tier in ("safe", "cache"):
        context, store = _context(config)
        try:
            policy = resolve_storage_policy({}, action=ACTION_CLEANUP, tier=tier)
            plan, _ = storage_commands.build_cleanup_plan(context, policy)
            planned = {str(item.path) for item in plan.actions}
            assert not (planned & {str(item) for item in checkpoints})
        finally:
            store.close()

    for decision in archive_candidates(snapshot):
        if not decision.eligible:
            continue
        assert not any(
            str(item) == str(decision.path)
            or str(item).startswith(str(decision.path) + os.sep)
            for item in checkpoints
        )


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

    reference_root = paths.workspace / "qualification-references"
    assert reference_root.is_dir()
    protected, why = snapshot.path_protection(reference_root)
    assert protected, why

    assert p4d._run(config, "storage", "cleanup", "--tier", "cache", "--apply") == 0
    assert reference_root.is_dir()
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
        ["storage", "report", "--deep"],
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

    assert _published_checkpoints(config, harness)


def test_advancing_the_lineage_releases_the_old_current_dependency(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)
    old_checkpoints = _published_checkpoints(config, harness)

    snapshot, _paths = _snapshot(config)
    assert all(snapshot.path_protection(item)[0] for item in old_checkpoints)

    _advance_generation(config)

    advanced, _paths = _snapshot(config)
    assert advanced.current_generation == 2
    historical = [item for item in archive_candidates(advanced) if item.eligible]
    assert historical, "the superseded generation produced no cold-replaceable bulk"
    assert all("g1" in str(item.path) for item in historical)


# ---------------------------------------------------------------------------
# Owner races and stale plans
# ---------------------------------------------------------------------------


def test_p5_object_before_pointer_publication_wins_against_storage(tmp_path: Path):
    """A paused real publication is never observed half-open by storage.

    The publication is held between its immutable object write and the
    CampaignStore pointer commit. A real public storage operation runs
    concurrently and reaches the owner barrier while that window is open; it
    must not proceed until the window closes, and when it does the object is
    still there and the pointer resolves.

    The barrier itself is production code: the spy below only observes when the
    storage executor is about to enter it.
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

    def observed_barrier(paths, synchronization):
        storage_at_barrier.set()
        return original_barrier(paths, synchronization)

    def paused_pointer(*args, **kwargs):
        if not window_open.is_set():
            window_open.set()
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
        assert resolve_current_final_production_publication(context) is not None
    finally:
        store.close()


def test_a_stale_running_historical_p5_run_is_never_mutated(tmp_path: Path):
    """A run that began under g1 keeps writing after g2 becomes current.

    Generation supersession is not a liveness proof. The real P5 execution path
    holds its run-activity lease for the whole write lifetime, so a storage
    operation that wants to archive or deduplicate that run tree has to wait for
    the owner, not for a pathname to look old.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        post_selection_run_activity_lease,
    )

    harness = p5.PostSelectionHarness()
    config, _workspace = p5.build_selected_campaign(tmp_path)
    assert p5.run_cross_validate(config, harness) == 0
    assert p5.run_train_production(config, harness) == 0
    _advance_generation(config)

    _cfg, paths, store, _boundary = _open(config)
    try:
        runs = sorted(
            item
            for item in (paths.internal / "post-selection" / "g1" / "runs").iterdir()
            if item.is_dir()
        )
    finally:
        store.close()
    assert runs
    run_root = runs[0]
    contents = [item for item in sorted(run_root.rglob("*")) if item.is_file()]
    assert contents
    sample = contents[0]
    before = sample.read_bytes()

    finished = threading.Event()
    storage_done = threading.Event()
    outcome: list[str] = []

    def storage_worker() -> None:
        try:
            assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
            outcome.append("finished-after-owner" if finished.is_set() else "raced")
        finally:
            storage_done.set()

    worker = threading.Thread(target=storage_worker, daemon=True)
    # The real owner-local lease, held exactly as P5 execution holds it.
    with post_selection_run_activity_lease(run_root):
        worker.start()
        time.sleep(1.0)
        assert sample.read_bytes() == before
        finished.set()
    storage_done.wait(180.0)
    worker.join(180.0)
    assert outcome == ["finished-after-owner"], outcome


def test_owner_advancement_between_plan_and_apply_refuses_the_plan(
    qualified_campaign,
):
    config, _workspace, _harness = qualified_campaign
    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_CLEANUP, tier="cache")
        plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
        scratch = Path(context.paths.internal) / "post-selection" / "g99" / "objects"
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "object.json").write_text("{}\n", encoding="utf-8")
        advanced = context.snapshot(policy, certify=True)
        with pytest.raises(StoragePlanStaleError, match="owner|closure"):
            revalidate_plan(plan, advanced, policy)
    finally:
        store.close()


def test_a_same_generation_publication_change_stales_a_plan(tmp_path: Path):
    """Owner advancement with unchanged paths and bytes still invalidates."""

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_CLEANUP, tier="safe")
        plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
        publication = [
            view for view in snapshot.views if view.artifact_id.startswith("p5:publication")
        ]
        assert publication and publication[0].state_identity

        # Republish the qualification pointer: no path and no byte on the P5 side
        # changes, but P7's current record identity does.
        from mdstats.training_data.qualification.store import (
            POINTER_QUALIFICATION_RECORD,
            _pointer_key,
        )

        cfg, paths = cli._load_config(config)
        from mdstats.training_data.campaign_post_selection import (
            load_current_selected_training_context,
        )

        selected = load_current_selected_training_context(cfg, paths, store)
        key = _pointer_key(selected.binding, POINTER_QUALIFICATION_RECORD)
        with store.exclusive_transaction() as db:
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, "b" * 64)
            )
        advanced = context.snapshot(policy, certify=True)
        with pytest.raises(StoragePlanStaleError):
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
# Invocation-local authorization and observational commands, end to end
# ---------------------------------------------------------------------------


def test_a_persisted_apply_or_action_cannot_authorize_or_redirect(qualified_campaign):
    config, _workspace, _harness = qualified_campaign
    text = Path(config).read_text(encoding="utf-8")
    try:
        Path(config).write_text(
            text + '\n[storage]\napply = true\naction = "cleanup"\n', encoding="utf-8"
        )
        with pytest.raises(CampaignCliError, match="authority-bearing"):
            p4d._run(config, "storage", "report")
    finally:
        Path(config).write_text(text, encoding="utf-8")
    assert p4d._run(config, "storage", "report") == 0


def _tree_signature(root: Path) -> dict[str, tuple[int, int, int]]:
    signature: dict[str, tuple[int, int, int]] = {}
    for path in sorted(root.rglob("*")):
        try:
            stats = path.lstat()
        except OSError:
            continue
        signature[str(path.relative_to(root))] = (
            int(stats.st_mode),
            int(stats.st_size),
            int(stats.st_mtime_ns),
        )
    return signature


def test_every_non_apply_command_leaves_a_real_campaign_unchanged(qualified_campaign):
    config, workspace, _harness = qualified_campaign
    before = _tree_signature(Path(workspace))
    for argv in (
        ["storage", "report"],
        ["storage", "report", "--deep"],
        ["storage", "cleanup", "--tier", "safe", "--dry-run"],
        ["storage", "cleanup", "--tier", "cache", "--dry-run"],
        ["storage", "deduplicate", "--dry-run"],
        ["storage", "archive", "list"],
        ["storage", "archive", "create", "--dry-run"],
    ):
        assert p4d._run(config, *argv) == 0
    after = _tree_signature(Path(workspace))
    assert after == before, sorted(set(after) ^ set(before))


# ---------------------------------------------------------------------------
# Frame cache: conservative retention through the real owner
# ---------------------------------------------------------------------------


def test_the_frame_cache_is_retained_by_every_tier(tmp_path: Path):
    """No P1 liveness seam exists, so the cache tier truthfully evicts nothing."""

    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths, store, boundary = _open(config)
    try:
        manifest = paths.internal / "frame-cache" / "frame-cache.json"
        before = manifest.read_bytes()
        snapshot = build_storage_inventory(
            cfg,
            paths,
            store,
            protected_inputs=boundary.protected_inputs,
            control_plane=open_storage_control_plane_readonly(paths),
            certify=True,
        )
        view = snapshot.view("p1:frame_cache")
        assert view is not None
        assert view.cache_reconstructible is True
        assert view.cache_evictable is False
        decisions = {item.artifact_id: item for item in cache_candidates(snapshot)}
        assert decisions["p1:frame_cache"].eligible is False
    finally:
        store.close()

    assert p4d._run(config, "storage", "cleanup", "--tier", "cache", "--apply") == 0
    assert manifest.read_bytes() == before


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
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Archive lifecycle against a real historical generation
# ---------------------------------------------------------------------------


def _historical_campaign(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)
    _advance_generation(config)
    return config, workspace, harness


def test_historical_archive_round_trip_through_a_fresh_process(tmp_path: Path):
    config, _workspace, _harness = _historical_campaign(tmp_path)

    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    view = snapshot.view(eligible[0].artifact_id)
    members, refusals = snapshot.authorized_members(view)
    assert refusals == ()
    sample = members[0]
    original = sample.read_bytes()

    assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
    assert not sample.exists(), "eligible historical hot bytes were not reclaimed"

    # Fresh process: catalog discovery and verification with nothing cached.
    plane = open_storage_control_plane_readonly(paths)
    entries = list_archives(plane)
    assert entries
    identity = entries[0]["archive_identity"]
    manifest = verify_cold_archive(
        plane, identity, resolve_storage_policy({}, action=ACTION_REPORT)
    )
    assert manifest["represented_artifact_ids"]
    assert manifest["source_plan_actions"]

    assert p4d._run(config, "storage", "archive", "restore", identity, "--apply") == 0
    assert sample.read_bytes() == original

    reopened = CampaignStore(paths.state_db)
    try:
        assert load_target_size_campaign_revision(reopened).state.generation == 2
    finally:
        reopened.close()


def test_a_root_that_is_an_ancestor_of_an_eligible_artifact_is_rejected(
    tmp_path: Path,
):
    config, _workspace, _harness = _historical_campaign(tmp_path)
    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    parent = Path(eligible[0].path).parent.relative_to(paths.workspace)
    sibling = paths.internal / "post-selection" / "g1" / "objects"
    before = _tree_signature(sibling) if sibling.is_dir() else {}

    with pytest.raises(CampaignCliError, match="ancestor|narrow|widen"):
        p4d._run(
            config, "storage", "archive", "create", "--root", str(parent), "--apply"
        )
    if sibling.is_dir():
        assert _tree_signature(sibling) == before


def test_an_archive_candidate_that_becomes_protected_is_not_reclaimed(
    tmp_path: Path,
):
    """Bytes unchanged, semantics changed: the hot member stays."""

    from mdstats.training_data.storage.archive import (
        archive_create_engine,
        build_archive_plan_actions,
    )

    config, _workspace, _harness = _historical_campaign(tmp_path)
    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_ARCHIVE, apply=True)
        context.consequential_plane(policy)
        snapshot = context.snapshot(policy, certify=True)
        selected = [item for item in archive_candidates(snapshot) if item.eligible]
        assert selected
        bundle = build_archive_plan_actions(
            workspace=Path(context.paths.workspace),
            snapshot=snapshot,
            selected=selected,
            boundary=context.boundary,
            policy=policy,
            reclaim_hot=True,
        )
        plan = build_storage_plan(snapshot, policy, bundle.actions)

        # The owner advances: a newly published P5 generation root appears.
        scratch = Path(context.paths.internal) / "post-selection" / "g42" / "objects"
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "object.json").write_text("{}\n", encoding="utf-8")

        result = context.executor(policy).run(
            plan,
            trigger="test:stale-archive",
            synchronization=synchronization_for(plan, snapshot),
            engine=archive_create_engine(
                workspace=Path(context.paths.workspace),
                control_plane=context.control_plane,
                policy=policy,
                boundary=context.boundary,
                bundle=bundle,
                reclaim_hot=True,
            ),
        )
        assert result.status == "refused"
        for action in plan.actions:
            assert Path(action.path).is_file()
    finally:
        store.close()


def test_archive_refuses_hot_removal_of_a_current_publication_dependency(
    qualified_campaign,
):
    config, _workspace, harness = qualified_campaign
    checkpoints = _published_checkpoints(config, harness)
    snapshot, _paths = _snapshot(config)
    for decision in archive_candidates(snapshot):
        for checkpoint in checkpoints:
            if str(checkpoint).startswith(str(decision.path)):
                assert not decision.eligible, decision.reason


def test_current_public_resolver_hot_paths_are_never_archive_removable(
    qualified_campaign,
):
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
    names = {str(item) for item in hot_required}
    assert any("post-selection" in item and "objects" in item for item in names)
    assert any("qualification" in item for item in names)
    assert any(item.endswith("campaign.sqlite3") for item in names)


def test_an_unexpected_descendant_of_a_real_historical_run_is_retained(
    tmp_path: Path,
):
    config, _workspace, _harness = _historical_campaign(tmp_path)
    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    run_root = Path(eligible[0].path)
    stranger = run_root / "checkpoints" / "someone-elses.bin"
    stranger.write_bytes(b"not mine")

    reduced, _paths = _snapshot(config)
    view = reduced.view(eligible[0].artifact_id)
    assert view.archive_eligible is False
    assert "did not write" in view.detail

    # Other historical runs are still archivable; this one is not, and the
    # stranger's bytes are never collected, reclaimed, or represented.
    assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
    assert stranger.read_bytes() == b"not mine"
    plane = open_storage_control_plane_readonly(paths)
    for entry in list_archives(plane):
        manifest = read_manifest(plane, entry["archive_identity"])
        assert eligible[0].artifact_id not in manifest["represented_artifact_ids"]
        assert all(
            not str(item["path"]).startswith(run_root.name)
            for item in manifest["members"]
        )


# ---------------------------------------------------------------------------
# Dedup against a real historical generation
# ---------------------------------------------------------------------------


def _publish_historical_run(paths, generation: int, name: str, members: dict) -> Path:
    """One historical P5 run published in the real owner's own order.

    The outputs land first, the terminal record becomes durable next, and only
    then does the owner freeze its create-once completion anchor - which is the
    order real execution uses and the only order the anchor accepts.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        record_post_selection_run_members,
    )

    root = paths.internal / "post-selection" / f"g{generation}" / "runs" / name
    (root / "checkpoints").mkdir(parents=True, exist_ok=True)
    for relative, payload in members.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        os.chmod(destination, 0o644)
    (root / "run-evidence.json").write_text("{}\n", encoding="utf-8")
    record_post_selection_run_members(root)
    return root


def test_dedup_frees_physical_bytes_when_the_last_alias_disappears(tmp_path: Path):
    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)

    payload = b"duplicate" * 4096
    run_root = _publish_historical_run(
        paths,
        1,
        "dedup-run",
        {"checkpoints/dup-a.bin": payload, "checkpoints/dup-b.bin": payload},
    )
    first = run_root / "checkpoints" / "dup-a.bin"
    second = run_root / "checkpoints" / "dup-b.bin"

    assert p4d._run(config, "storage", "deduplicate", "--apply") == 0
    assert first.stat().st_ino == second.stat().st_ino
    assert first.stat().st_nlink == 2
    assert not (open_storage_control_plane_readonly(paths).root / "content-store").exists()

    first.unlink()
    assert second.stat().st_nlink == 1
    second.unlink()
    assert not first.exists() and not second.exists()


# ---------------------------------------------------------------------------
# Interruption, truthfulness, and fresh-process reauthentication
# ---------------------------------------------------------------------------


def test_interrupted_multi_action_cleanup_is_truthful_and_re_plans(tmp_path: Path):
    """A crash after a strict subset of real removals is truthful and resumable.

    The removals are the P7 attempt-local scratch a genuinely released attempt
    left behind - nothing here is a synthetic orphan planted for the test.
    """

    from mdstats.training_data.storage import executor as executor_mod

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    cfg, paths, store, boundary = _open(config)
    try:
        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        policy = resolve_storage_policy(
            {}, action=ACTION_CLEANUP, tier="safe", apply=True
        )
        context.consequential_plane(policy)
        plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
        targets = [
            Path(action.path) for action in plan.actions if action.action == "remove"
        ]
        assert len(targets) >= 3, targets

        # The failpoint has to sit on whichever removal owner the actions
        # actually reach: generic storage removal, and the P7 released-attempt
        # boundary that owns descriptor-relative reclamation.
        from mdstats.training_data.qualification import store as qstore

        real_remove = executor_mod.remove_durably
        real_released = qstore.remove_released_attempt_member
        removed: list[Path] = []

        def _interrupt_after_two() -> None:
            if len(removed) >= 2:
                raise RuntimeError("injected interruption after a strict subset")

        def failing_remove(path: Path) -> bool:
            _interrupt_after_two()
            removed.append(path)
            return real_remove(path)

        def failing_released(paths_arg, attempt_root, member_name, **kwargs):
            _interrupt_after_two()
            removed.append(Path(attempt_root) / member_name)
            return real_released(paths_arg, attempt_root, member_name, **kwargs)

        executor_mod.remove_durably = failing_remove
        storage_commands.remove_durably = failing_remove
        qstore.remove_released_attempt_member = failing_released
        try:
            with pytest.raises(RuntimeError, match="injected interruption"):
                context.executor(policy).run(
                    plan,
                    trigger="test:interrupt",
                    synchronization=synchronization_for(plan, snapshot),
                    engine=storage_commands._cleanup_engine(context, policy),
                )
        finally:
            executor_mod.remove_durably = real_remove
            storage_commands.remove_durably = real_remove
            qstore.remove_released_attempt_member = real_released

        surviving = [item for item in targets if item.exists()]
        assert len(surviving) == len(targets) - 2

        audit = context.control_plane.read_audit()
        assert audit and all(item.get("status") != "complete" for item in audit)
        assert any(item.get("status") == "partial" for item in audit)

        retry_plan, retry_snapshot = storage_commands.build_cleanup_plan(context, policy)
        retry_targets = [
            action for action in retry_plan.actions if action.action == "remove"
        ]
        assert len(retry_targets) == len(surviving)
        result = context.executor(policy).run(
            retry_plan,
            trigger="test:retry",
            synchronization=synchronization_for(retry_plan, retry_snapshot),
            engine=storage_commands._cleanup_engine(context, policy),
        )
        assert result.status == "complete"
        assert not [item for item in targets if item.exists()]
    finally:
        store.close()

    # The interruption cost only released scratch: the publication still resolves.
    assert _published_checkpoints(config, harness)


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
        assert _published_checkpoints(config, harness)


def test_p3_publication_window_evidence_survives_storage_cleanup(tmp_path: Path):
    """Storage cannot race P3's publish-before-adopt window."""

    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths, store, boundary = _open(config)
    try:
        revision = load_target_size_campaign_revision(store)
        root = Path(paths.workspace) / revision.state.execution_root
        published = root / "materializations" / ("c" * 64 + ".json")
        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_text("{}\n", encoding="utf-8")

        authorized, detail = boundary.destructive_authorization(published)
        assert not authorized
        assert "publish" in detail or "reachab" in detail or "recently" in detail
    finally:
        store.close()

    for tier in ("safe", "cache"):
        assert p4d._run(config, "storage", "cleanup", "--tier", tier, "--apply") == 0
        assert published.is_file()


def test_the_storage_audit_records_every_applied_operation(tmp_path: Path):
    config, _workspace, _harness = _historical_campaign(tmp_path)
    assert p4d._run(config, "storage", "deduplicate", "--apply") == 0
    assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0

    _cfg, paths, store, _boundary = _open(config)
    try:
        plane = open_storage_control_plane_readonly(paths)
        actions = {item["action"] for item in plane.read_audit()}
        assert {"deduplicate", "archive", "cleanup"} <= actions
        assert all(
            item.get("grants_scientific_authority") is False
            for item in plane.read_audit()
        )
    finally:
        store.close()


def test_restore_never_changes_pre_existing_container_metadata(tmp_path: Path):
    """Restoring into a live campaign touches no directory it did not create.

    A restore installs members under directories the campaign already owns.
    Those directories carry their own permissions and timestamps, which belong
    to the owner that made them; silently normalizing them to whatever the
    archive happened to record would be an unrequested mutation of live campaign
    state. The only directory whose timestamp may legitimately move is one that
    actually gains an entry, and that is computed here from the manifest rather
    than assumed.
    """

    config, _workspace, _harness = _historical_campaign(tmp_path)

    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    run_root = Path(eligible[0].path)
    os.chmod(run_root, 0o750)

    assert p4d._run(config, "storage", "archive", "create", "--apply") == 0
    plane = open_storage_control_plane_readonly(paths)
    identity = list_archives(plane)[0]["archive_identity"]
    manifest = read_manifest(plane, identity)

    workspace = Path(paths.workspace)
    # The family the restore installs into. The storage control plane and the
    # campaign state directory are excluded on purpose: an authorized restore
    # legitimately appends its own journal, catalog, and audit records there.
    family = Path(paths.internal) / "post-selection"
    pre_existing = {
        path: (path.stat().st_mode, path.stat().st_mtime_ns)
        for path in [family, *sorted(family.rglob("*"))]
        if path.is_dir() and not path.is_symlink()
    }
    assert run_root in pre_existing, "the archived run root did not survive as a container"

    # Every directory that will legitimately gain an entry: the closest existing
    # ancestor of each member path that the restore has to create.
    gains_an_entry: set[Path] = set()
    for member in manifest["members"]:
        probe = (workspace / str(member["path"])).parent
        while probe not in pre_existing and probe != family and probe != workspace:
            probe = probe.parent
        gains_an_entry.add(probe)
    assert gains_an_entry

    assert p4d._run(config, "storage", "archive", "restore", identity, "--apply") == 0

    for path, (mode, mtime) in pre_existing.items():
        if not path.is_dir():
            continue
        stats = path.stat()
        # Permissions are never normalized to whatever the archive recorded.
        assert stats.st_mode == mode, path
        if path not in gains_an_entry:
            assert stats.st_mtime_ns == mtime, path
    assert run_root.stat().st_mode & 0o777 == 0o750


def test_an_unexpected_descendant_of_a_released_attempt_is_retained(tmp_path: Path):
    """P7 attempt-local bulk is reclaimable only where P7 recorded it."""

    from mdstats.training_data.qualification.store import (
        ATTEMPT_MEMBER_MANIFEST_FILENAME,
    )

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)

    snapshot, paths = _snapshot(config)
    scratch = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.path.is_dir()
    ]
    assert scratch, "the released attempt exposed no attempt-local scratch tree"
    assert all(view.safe_reclaimable for view in scratch)
    attempt_root = scratch[0].path.parent
    assert (attempt_root / ATTEMPT_MEMBER_MANIFEST_FILENAME).is_file()

    stranger = scratch[0].path / "someone-elses.bin"
    stranger.write_bytes(b"not mine")
    reduced, _paths = _snapshot(config)
    view = reduced.view(scratch[0].artifact_id)
    assert view.safe_reclaimable is False
    assert "did not write" in view.detail

    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert stranger.read_bytes() == b"not mine"

    stranger.unlink()
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert not scratch[0].path.exists()


# ---------------------------------------------------------------------------
# IR15-2 - dedup fences the canonical source owner, not only the destination
# ---------------------------------------------------------------------------


def _dedup_plan_canonical(config) -> tuple[Path, Path]:
    """The canonical source and one replacement the real planner chose."""

    from mdstats.training_data.storage.dedup import build_dedup_plan

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db, create=False)
    try:
        with cli.observational_campaign_state():
            boundary = cli._campaign_ownership_boundary(cfg, paths, store)
            snapshot = build_storage_inventory(
                cfg,
                paths,
                store,
                protected_inputs=boundary.protected_inputs,
                control_plane=open_storage_control_plane_readonly(paths),
                certify=True,
            )
            actions, groups, _excluded = build_dedup_plan(
                snapshot, resolve_storage_policy({}, action="deduplicate")
            )
    finally:
        store.close()
    assert actions, "the planner found no cross-run duplicate"
    return Path(str(actions[0].binding["canonical"])), Path(actions[0].path)


def test_dedup_waits_for_the_canonical_source_run_not_only_the_destination(
    tmp_path: Path,
):
    """A dedup group can span two historical runs, and only one is written to.

    The canonical source is never modified, yet its inode becomes the bytes
    behind a second name. P5 lets a run that began under an older selected
    binding keep executing, so historical status is not a no-writer proof: the
    canonical's own run-activity lease has to be held too, or dedup can alias a
    file some live writer is still producing.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        post_selection_run_activity_lease,
    )

    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    payload = b"cross-run-duplicate" * 512
    run_a = _publish_historical_run(paths, 1, "dedup-a", {"checkpoints/dup.bin": payload})
    run_b = _publish_historical_run(paths, 1, "dedup-b", {"checkpoints/dup.bin": payload})

    del run_a, run_b
    canonical, replacement = _dedup_plan_canonical(config)
    assert canonical.parent.parent != replacement.parent.parent, (
        "the planner did not produce a cross-run dedup group"
    )
    canonical_run = canonical.parent.parent

    finished = threading.Event()
    done = threading.Event()
    outcome: list[str] = []

    def worker() -> None:
        try:
            assert p4d._run(config, "storage", "deduplicate", "--apply") == 0
            outcome.append("after-owner" if finished.is_set() else "raced")
        finally:
            done.set()

    thread = threading.Thread(target=worker, daemon=True)
    # Hold *only* the canonical source's lease. Before the repair, storage held
    # the destination's lease and proceeded regardless.
    with post_selection_run_activity_lease(canonical_run):
        thread.start()
        time.sleep(1.0)
        assert replacement.stat().st_ino != canonical.stat().st_ino, (
            "dedup relinked while the canonical source owner was still active"
        )
        finished.set()
    done.wait(180.0)
    thread.join(180.0)
    assert outcome == ["after-owner"], outcome
    assert replacement.stat().st_ino == canonical.stat().st_ino


def test_dedup_acquires_every_source_and_destination_seam_without_deadlock(
    tmp_path: Path,
):
    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    payload = b"many-alias" * 512
    for name in ("dedup-x", "dedup-y", "dedup-z"):
        _publish_historical_run(paths, 1, name, {"checkpoints/dup.bin": payload})

    from mdstats.training_data.storage.dedup import build_dedup_plan
    from mdstats.training_data.storage.executor import synchronization_for
    from mdstats.training_data.storage.plan import build_storage_plan

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db, create=False)
    try:
        with cli.observational_campaign_state():
            boundary = cli._campaign_ownership_boundary(cfg, paths, store)
            snapshot = build_storage_inventory(
                cfg,
                paths,
                store,
                protected_inputs=boundary.protected_inputs,
                control_plane=open_storage_control_plane_readonly(paths),
                certify=True,
            )
            policy = resolve_storage_policy({}, action="deduplicate")
            actions, _groups, _excluded = build_dedup_plan(snapshot, policy)
            plan = build_storage_plan(snapshot, policy, actions)
            synchronization = synchronization_for(plan, snapshot)
    finally:
        store.close()

    fenced = {Path(item).name for item in synchronization.run_roots}
    assert {"dedup-x", "dedup-y", "dedup-z"} <= fenced, sorted(fenced)
    # One deterministic order, so two operations can never build a cycle.
    assert list(synchronization.run_roots) == sorted(synchronization.run_roots)

    assert p4d._run(config, "storage", "deduplicate", "--apply") == 0
    inodes = {
        (paths.internal / "post-selection" / "g1" / "runs" / name / "checkpoints" / "dup.bin")
        .stat()
        .st_ino
        for name in ("dedup-x", "dedup-y", "dedup-z")
    }
    assert len(inodes) == 1


def test_canonical_bindings_feed_synchronization_not_only_mutation() -> None:
    """Structural: the canonical source is declared to the synchronization builder."""

    import ast

    dedup_source = (
        Path(cli.__file__).parent.joinpath("storage", "dedup.py").read_text(encoding="utf-8")
    )
    assert "synchronization_paths=(canonical,)" in dedup_source
    assert "synchronization_artifact_ids=(" in dedup_source

    executor_source = (
        Path(cli.__file__).parent.joinpath("storage", "executor.py").read_text(encoding="utf-8")
    )
    tree = ast.parse(executor_source)
    builder = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "synchronization_for"
    )
    dumped = ast.dump(builder)
    assert "synchronization_paths" in dumped
    assert "synchronization_artifact_ids" in dumped


# ---------------------------------------------------------------------------
# IR15-4 / IR16-4 - partial reclaim survives losing the terminal evidence
# ---------------------------------------------------------------------------


def test_partial_reclaim_resumes_after_the_terminal_evidence_goes_cold(
    tmp_path: Path,
):
    """The completion anchor, not the terminal record, is what certifies a run.

    An interrupted hot reclamation can already have removed the fold/run
    evidence while other represented members are still hot. If certification
    needed that file, the next process could never finish the reclamation it
    started.
    """

    from mdstats.training_data.storage.archive import BOUNDARY_DURING_RECLAMATION

    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    run_root = _publish_historical_run(
        paths,
        1,
        "reclaim-run",
        {
            "checkpoints/first.bin": b"first" * 512,
            # Sorts after `run-evidence.json`, so the interruption below lands
            # with the terminal record already cold and a member still hot.
            "zz-late.bin": b"late" * 512,
        },
    )
    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
    )

    evidence = run_root / "run-evidence.json"
    anchor = run_root / RUN_COMPLETION_ANCHOR_FILENAME
    topology = run_root / RUN_TOPOLOGY_MANIFEST_FILENAME
    late = run_root / "zz-late.bin"
    relative_root = str(run_root.relative_to(paths.workspace))

    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_ARCHIVE, apply=True)
        context.consequential_plane(policy)
        payload = storage_commands.storage_archive(
            context,
            _args(
                archive_command="create",
                root=[relative_root],
                apply=True,
                keep_hot=True,
            ),
        )
        identity = payload["archive"]["archive_identity"]
    finally:
        store.close()

    def failpoint(name: str) -> None:
        if name != BOUNDARY_DURING_RECLAMATION:
            return
        if not evidence.exists() and late.exists():
            raise RuntimeError("injected interruption after the terminal record went cold")

    context, store = _context(config)
    try:
        with pytest.raises(RuntimeError, match="injected interruption"):
            storage_commands.storage_archive(
                context,
                _args(
                    archive_command="reclaim",
                    archive_identity=identity,
                    apply=True,
                    failpoint=failpoint,
                ),
            )
    finally:
        store.close()
    assert not evidence.exists(), "the fixture never reached the intended interruption"
    assert anchor.is_file(), "the completion anchor was reclaimed with the members"
    assert topology.is_file(), "the topology manifest was reclaimed with the members"
    assert late.is_file()

    # Fresh process: the owner still certifies the run from its retained anchor.
    snapshot, _paths = _snapshot(config)
    view = snapshot.view(f"p5:run:g1:{run_root.name}")
    assert view is not None and view.archive_eligible is True

    assert p4d._run(config, "storage", "archive", "reclaim", identity, "--apply") == 0
    assert not late.exists()
    assert anchor.is_file() and topology.is_file()

    # Explicit restore brings the historical evidence back without promoting it.
    assert p4d._run(config, "storage", "archive", "restore", identity, "--apply") == 0
    assert evidence.is_file()
    reopened = CampaignStore(paths.state_db)
    try:
        assert load_target_size_campaign_revision(reopened).state.generation == 2
    finally:
        reopened.close()


# ---------------------------------------------------------------------------
# IR15-5 - maintenance serializes against a real CampaignStore writer
# ---------------------------------------------------------------------------


def test_state_maintenance_serializes_against_a_concurrent_campaign_writer(
    tmp_path: Path,
):
    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    writer = CampaignStore(paths.state_db)
    try:
        for _index in range(400):
            writer.event("info", "fixture", "x" * 256)

        holding = threading.Event()
        release = threading.Event()
        failures: list[BaseException] = []

        def hold_the_write_lock() -> None:
            store = CampaignStore(paths.state_db)
            try:
                with store.exclusive_transaction() as db:
                    db.execute(
                        "INSERT INTO events(timestamp_utc,level,stage,message) "
                        "VALUES ('t','info','fixture','held')"
                    )
                    holding.set()
                    release.wait(20.0)
            except BaseException as exc:  # pragma: no cover - surfaced below
                failures.append(exc)
            finally:
                store.close()

        thread = threading.Thread(target=hold_the_write_lock, daemon=True)
        thread.start()
        assert holding.wait(30.0)

        maintainer = threading.Thread(
            target=lambda: p4d._run(
                config, "storage", "cleanup", "--tier", "safe", "--apply"
            ),
            daemon=True,
        )
        maintainer.start()
        time.sleep(1.0)
        release.set()
        thread.join(30.0)
        maintainer.join(120.0)
        assert not failures, failures
    finally:
        writer.close()

    # The database is intact and its scientific authority is unchanged.
    reopened = CampaignStore(paths.state_db)
    try:
        assert load_target_size_campaign_revision(reopened) is not None
        with reopened._connect() as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        reopened.close()


# ---------------------------------------------------------------------------
# IR16-5 - supported storage writers cannot interleave with reauthentication
# ---------------------------------------------------------------------------


def test_a_second_storage_operation_cannot_interleave_with_reauthentication(
    tmp_path: Path,
):
    """The lease is what makes protected reauthentication meaningful."""

    from mdstats.training_data.storage import archive as archive_mod

    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    _publish_historical_run(paths, 1, "race-run", {"checkpoints/one.bin": b"one" * 512})

    context, store = _context(config)
    try:
        policy = resolve_storage_policy({}, action=ACTION_ARCHIVE, apply=True)
        context.consequential_plane(policy)
        payload = storage_commands.storage_archive(
            context,
            _args(archive_command="create", root=None, apply=True, keep_hot=True),
        )
        identity = payload["archive"]["archive_identity"]
    finally:
        store.close()

    inside = threading.Event()
    release = threading.Event()
    order: list[str] = []
    original = archive_mod.reauthenticate_representation
    failures: list[BaseException] = []

    def paused(control_plane, policy_, bound):
        manifest = original(control_plane, policy_, bound)
        inside.set()
        release.wait(60.0)
        order.append("reauthenticated")
        return manifest

    def first_operation() -> None:
        try:
            assert (
                p4d._run(config, "storage", "archive", "reclaim", identity, "--apply")
                == 0
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    def second_operation() -> None:
        try:
            assert (
                p4d._run(
                    config, "storage", "archive", "create", "--apply", "--keep-hot"
                )
                == 0
            )
            order.append("second")
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    archive_mod.reauthenticate_representation = paused
    first = threading.Thread(target=first_operation, daemon=True)
    second = threading.Thread(target=second_operation, daemon=True)
    try:
        first.start()
        assert inside.wait(60.0), "the reclaim never reached protected reauthentication"
        second.start()
        time.sleep(1.5)
        assert order == [], "a second storage operation interleaved with the lease"
        release.set()
        first.join(120.0)
        second.join(120.0)
    finally:
        archive_mod.reauthenticate_representation = original
    assert not failures, failures
    assert order and order[0] == "reauthenticated", order


# ---------------------------------------------------------------------------
# IR16-2 - observation through the real public dispatch
# ---------------------------------------------------------------------------


def test_the_public_report_opens_every_nested_store_read_only(tmp_path: Path):
    config, _workspace = p5.build_selected_campaign(tmp_path)
    opened: list[bool] = []
    original = cli.CampaignStore.__init__

    def recording(self, path, *, create: bool = True):
        original(self, path, create=create)
        opened.append(bool(self.read_only))

    cli.CampaignStore.__init__ = recording
    try:
        assert p4d._run(config, "storage", "report") == 0
    finally:
        cli.CampaignStore.__init__ = original
    assert opened, "the report opened no campaign store at all"
    assert all(opened), "an observational report opened a writable campaign store"


# ---------------------------------------------------------------------------
# IR17-3 / IR18-2 - the VACUUM benefit predicate survives a cross-process writer
# ---------------------------------------------------------------------------


_COMPETING_WRITER = """
import sys, time
sys.path.insert(0, {repository!r})
from mdstats.training_data._campaign_cli_core import CampaignStore

store = CampaignStore({database!r})
try:
    with store.writer_exclusion():
        open({ready!r}, "w").close()
        # Consume the free pages the maintenance decision was based on, while
        # holding the exclusion that maintenance is waiting for.
        for index in range({rows}):
            store.event("info", "competitor", "y" * 512)
        time.sleep({hold})
finally:
    store.close()
"""


def _maintenance_policy(events: int = 1_000_000) -> dict:
    return {
        "storage": {
            "sqlite_compaction_maximum_events": events,
            "sqlite_compaction_minimum_reclaimable_bytes": 4096,
            "sqlite_compaction_minimum_reclaimable_fraction": 0.001,
        }
    }


def test_a_second_process_can_invalidate_the_vacuum_benefit_while_it_waits(
    tmp_path: Path,
):
    """The rewrite is authorized by free space that must still be free.

    Measuring the freelist and then queuing for the database is the race this
    exclusion exists to close: another *process* - the normal case, a second CLI
    invocation - can commit in between and consume exactly the space the
    decision was based on. A thread-only mutex cannot see that writer at all.
    """

    import subprocess
    import sys

    from mdstats.training_data.storage.executor import (
        StorageExecutionResult,
        synchronization_for,
    )
    from mdstats.training_data.storage.maintenance import (
        campaign_state_maintenance_engine,
        plan_campaign_state_maintenance,
        vacuum_is_worthwhile,
    )

    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        for _index in range(4000):
            store.event("info", "fixture", "z" * 512)
        store.prune_events(maximum_events=10)
        worthwhile, _bytes, _fraction, detail = vacuum_is_worthwhile(
            store,
            resolve_storage_policy(_maintenance_policy(), action=ACTION_CLEANUP),
        )
        assert worthwhile, detail

        # A retention bound nothing exceeds, so the only maintenance authority
        # in this plan is the rewrite itself: a prune running first would
        # legitimately free more pages and make the rewrite worthwhile again,
        # which is correct behavior but not the race under test.
        merged = {**cfg, **_maintenance_policy()}
        boundary = cli._campaign_ownership_boundary(merged, paths, store)
        context = storage_commands.StorageCommandContext(
            merged, paths, store, boundary
        )
        policy = resolve_storage_policy(merged, action=ACTION_CLEANUP, apply=True)
        context.consequential_plane(policy)
        decision = plan_campaign_state_maintenance(store, paths, policy)
        assert decision.vacuum_action is not None, decision.reason
        assert decision.prune_action is None, decision.reason
        plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
        before = paths.state_db.stat().st_size

        def _start_competitor(rows: int, hold: float):
            ready = tmp_path / f"competitor-ready-{rows}-{hold}"
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _COMPETING_WRITER.format(
                        repository=str(Path(cli.__file__).resolve().parents[2]),
                        database=str(paths.state_db),
                        ready=str(ready),
                        rows=rows,
                        hold=hold,
                    ),
                ]
            )
            deadline = time.time() + 60.0
            while not ready.exists() and time.time() < deadline:
                time.sleep(0.05)
            assert ready.exists(), "the competing writer never started"
            return child

        # (a) The real maintenance engine, with the competitor holding the
        #     exclusion: the benefit predicate is observed *after* the wait, so
        #     it sees the state the competitor left rather than the one that
        #     authorized the plan.
        child = _start_competitor(rows=6000, hold=2.0)
        try:
            outcome = StorageExecutionResult(
                operation_identity="t" * 32,
                plan_identity=plan.plan_identity,
                policy_identity=policy.policy_identity,
                action=policy.action,
                status="refused",
            )
            engine = campaign_state_maintenance_engine(store, policy)
            engine(decision.vacuum_action, snapshot, outcome)
        finally:
            assert child.wait(120) == 0
        assert not outcome.completed, "the rewrite ran on a stale benefit observation"
        assert outcome.refused
        assert "every competing writer was excluded" in outcome.refused[0]["refusal"]
        assert paths.state_db.stat().st_size >= before

        # (b) The same race through the real public executor changes nothing
        #     either: the campaign-state owner advanced, so the plan itself is
        #     stale and no rewrite happens.
        child = _start_competitor(rows=2000, hold=1.0)
        try:
            result = context.executor(policy).run(
                plan,
                trigger="test:cross-process-vacuum",
                synchronization=synchronization_for(plan, snapshot),
                engine=storage_commands._cleanup_engine(context, policy),
            )
        finally:
            assert child.wait(120) == 0
        assert not any(
            item["action"] == "vacuum_campaign_state" for item in result.completed
        )
        assert paths.state_db.stat().st_size >= before
    finally:
        store.close()

    # The exclusion is released on every terminal path, so a fresh process can
    # take the ordinary writer path immediately.
    fresh = CampaignStore(paths.state_db)
    try:
        fresh.event("info", "after", "the writer path is available again")
    finally:
        fresh.close()


def test_the_writer_exclusion_is_released_after_an_injected_rewrite_failure(
    tmp_path: Path,
):
    config, _workspace = p5.build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        for _index in range(4000):
            store.event("info", "fixture", "z" * 512)
        store.prune_events(maximum_events=10)

        original = CampaignStore.vacuum

        def failing_vacuum(self) -> None:
            raise OSError("injected rewrite failure")

        CampaignStore.vacuum = failing_vacuum
        try:
            assert (
                p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
            )
        finally:
            CampaignStore.vacuum = original
        # Not deadlocked and not permanently excluded.
        store.event("info", "after", "still writable")
    finally:
        store.close()


def test_no_supported_campaign_writer_bypasses_the_owner_exclusion() -> None:
    """Structural: every mutation funnels through one process-safe primitive."""

    import ast

    source = Path(cli.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    store = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "CampaignStore"
    )
    writing = {
        "set_meta",
        "put_record",
        "put_records",
        "delete_records",
        "delete_record",
        "set_stage",
        "event",
        "prune_events",
        "vacuum",
        "exclusive_transaction",
    }
    for node in store.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in writing:
            continue
        dumped = ast.dump(node)
        assert (
            "writer_exclusion" in dumped or "exclusive_transaction" in dumped
        ), node.name


# ---------------------------------------------------------------------------
# IR18-4 - dedup staging liveness comes from the storage-operation lease
# ---------------------------------------------------------------------------


def test_live_dedup_staging_is_never_reclaimed_by_a_concurrent_cleanup(
    tmp_path: Path,
):
    from mdstats.training_data.storage.lease import (
        StorageLeaseUnavailableError,
        storage_operation_lease,
    )

    config, _workspace, _harness = _historical_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    plane = open_storage_control_plane_readonly(paths)
    context, store = _context(config)
    try:
        plane = context.consequential_plane(
            resolve_storage_policy({}, action=ACTION_CLEANUP, apply=True)
        )
    finally:
        store.close()
    live = plane.staging_root_for("a" * 32) / "dedup"
    live.mkdir(parents=True)
    (live / "0-held.bin").write_bytes(b"staged")

    with storage_operation_lease(plane):
        # Another operation cannot even begin while this lease is held, so it
        # can never decide that live staging is abandoned.
        with pytest.raises((StorageLeaseUnavailableError, CampaignCliError)):
            cfg, paths2 = cli._load_config(config)
            fresh = CampaignStore(paths2.state_db)
            try:
                boundary = cli._campaign_ownership_boundary(cfg, paths2, fresh)
                other = storage_commands.StorageCommandContext(
                    {**cfg, "storage": {"operation_lease_timeout_seconds": 1}},
                    paths2,
                    fresh,
                    boundary,
                )
                storage_commands.storage_cleanup(other, _args(tier="safe", apply=True))
            finally:
                fresh.close()
    assert (live / "0-held.bin").is_file()

    # With no live operation, the same staging is ordinary storage-owned residue.
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert not live.exists()


# ---------------------------------------------------------------------------
# R19-B - the P7 released-attempt proof
# ---------------------------------------------------------------------------


def _released_attempt_root(config: Path) -> Path:
    snapshot, _paths = _snapshot(config)
    scratch = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    ]
    assert scratch, "the released attempt exposed no attempt-local scratch"
    root = scratch[0].path
    while root.parent.name != "attempts":
        root = root.parent
    return root


def _released_attempt_campaign(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0
    _release_attempt(config, harness)
    return config, workspace, harness


@pytest.mark.parametrize(
    "intrusion",
    [
        "top_level_file",
        "top_level_empty_directory",
        "nested_file",
        "nested_empty_directory",
        "nested_symlink",
        "file_to_directory",
    ],
)
def test_a_foreign_node_in_a_released_attempt_is_retained(tmp_path: Path, intrusion):
    """Containment beneath a released attempt is not authorship."""

    import shutil as _shutil

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    before = _snapshot(config)[0]
    reclaimable_before = {
        view.artifact_id
        for view in before.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    }
    assert reclaimable_before, "the fixture produced no reclaimable released scratch"
    victim_owner = sorted(
        view.path
        for view in before.views
        if view.artifact_id in reclaimable_before and view.path.is_dir()
    )

    if intrusion == "top_level_file":
        planted = attempt / "someone-elses.bin"
        planted.write_bytes(b"not mine")
    elif intrusion == "top_level_empty_directory":
        planted = attempt / "someone-elses-dir"
        planted.mkdir()
    elif intrusion == "file_to_directory":
        assert victim_owner
        existing = next(
            item for item in sorted(victim_owner[0].rglob("*")) if item.is_file()
        )
        existing.unlink()
        existing.mkdir()
        planted = existing
    else:
        assert victim_owner
        inside = victim_owner[0]
        if intrusion == "nested_file":
            planted = inside / "foreign.bin"
            planted.write_bytes(b"not mine")
        elif intrusion == "nested_empty_directory":
            planted = inside / "foreign-dir"
            planted.mkdir()
        else:
            planted = inside / "foreign-link"
            planted.symlink_to(attempt / "attempt-state.json")

    after = _snapshot(config)[0]
    if intrusion in ("top_level_file", "top_level_empty_directory"):
        exposed = [
            view
            for view in after.views
            if view.artifact_id.endswith(f":{planted.name}") and view.safe_reclaimable
        ]
        assert exposed == [], "a foreign top-level node became reclaimable"
    else:
        assert not any(
            view.safe_reclaimable
            for view in after.views
            if view.artifact_id.startswith("p7:attempt_scratch:")
            and view.path == victim_owner[0]
        ), "a contaminated attempt member stayed reclaimable"

    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert planted.exists() or planted.is_symlink()
    del _shutil


@pytest.mark.parametrize(
    "field",
    [
        "attempt_root",
        "attempt_identity",
        "binding_digest",
        "publication_digest",
        "state_digest",
        "released_state",
        "content_digest",
        "schema",
        "node_count",
    ],
)
def test_a_tampered_released_attempt_proof_fails_closed(tmp_path: Path, field: str):
    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload[field] = (
        "0" * 64
        if field.endswith("digest") or field.endswith("identity")
        else ("someone-else" if field != "node_count" else 99)
    )
    proof.write_text(json.dumps(payload), encoding="utf-8")

    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    ), f"a proof with a tampered {field} still authorized reclamation"
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert proof.is_file()


def test_a_symlinked_attempt_state_or_proof_grants_no_authority(tmp_path: Path):
    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    for name in ("attempt-members.json", "attempt-state.json"):
        target = attempt / name
        saved = target.read_bytes()
        planted = attempt.parent / f"planted-{name}"
        planted.write_bytes(saved)
        target.unlink()
        target.symlink_to(planted)
        snapshot, _paths = _snapshot(config)
        assert not any(
            view.safe_reclaimable
            for view in snapshot.views
            if view.artifact_id.startswith("p7:attempt_scratch:")
        ), f"a symlinked {name} still authorized reclamation"
        target.unlink()
        target.write_bytes(saved)
        planted.unlink()


def test_a_v2_development_manifest_authorizes_nothing(tmp_path: Path):
    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"
    proof.write_text(
        json.dumps(
            {
                "schema": "mdstats.qualification-attempt-members.v2",
                "attempt_root": attempt.name,
                "members": ["components", "deployment"],
                "member_count": 2,
            }
        ),
        encoding="utf-8",
    )
    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    )
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert (attempt / "components").exists() or (attempt / "deployment").exists()


def test_an_unreadable_attempt_state_blocks_consequential_planning(tmp_path: Path):
    """An active attempt's references can pin exact P5 checkpoints.

    Silently dropping a state nobody can read would erase a cross-owner
    retention edge, so the whole plan becomes unavailable until it is repaired.
    """

    from mdstats.training_data.storage.inventory import OwnerGraphError

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    checkpoints = _published_checkpoints(config, harness)
    assert checkpoints
    attempt = _released_attempt_root(config)
    state = attempt / "attempt-state.json"
    saved = state.read_bytes()
    state.write_bytes(b"{ this is not json")

    snapshot, _paths = _snapshot(config)
    assert snapshot.integrity_failures
    assert any("attempt state" in item for item in snapshot.integrity_failures)
    with pytest.raises(OwnerGraphError):
        snapshot.require_planable()
    for argv in (
        ["storage", "cleanup", "--tier", "safe", "--apply"],
        ["storage", "deduplicate", "--apply"],
        ["storage", "archive", "create", "--apply"],
    ):
        # Either refusal is truthful and both fail closed: the owner-graph gate,
        # or the workspace-wide retention ambiguity standing behind it.
        with pytest.raises(
            CampaignCliError, match="owner graph|cannot be authenticated"
        ):
            p4d._run(config, *argv)
    for checkpoint in checkpoints:
        assert checkpoint.is_file()
    # Reporting stays available and names the exact problem.
    assert p4d._run(config, "storage", "report") == 0

    state.write_bytes(saved)
    repaired, _paths = _snapshot(config)
    assert repaired.integrity_failures == ()
    repaired.require_planable()


def test_an_aborted_attempt_that_reopens_loses_its_release_authority(tmp_path: Path):
    """The proof binds the released state, so a legal reopen invalidates it."""

    from mdstats.training_data.qualification.store import (
        acquire_attempt_reference,
        read_attempt_state,
    )

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    before = _snapshot(config)[0]
    assert any(
        view.safe_reclaimable
        for view in before.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    )

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        # A terminal attempt is monotonic, so model the supported reopen through
        # the real owner on a second, aborted attempt identity.
        binding = session.context.selected.binding
        identity = "b" * 64
        acquire_attempt_reference(
            paths,
            binding,
            attempt_identity=identity,
            publication_digest=session.binding.publication_digest,
            binding_digest=session.binding.content_digest,
            referenced_paths=(),
        )
        from mdstats.training_data.qualification.store import release_attempt_reference

        release_attempt_reference(
            paths, binding, attempt_identity=identity, terminal=False
        )
        released = _snapshot(config)[0]
        reopened_root = None
        for view in released.views:
            if view.artifact_id.endswith(identity) and view.path.name == identity:
                reopened_root = view.path
        assert reopened_root is not None

        # Reopening publishes a new active state; the release proof now binds a
        # state that is no longer current.
        acquire_attempt_reference(
            paths,
            binding,
            attempt_identity=identity,
            publication_digest=session.binding.publication_digest,
            binding_digest=session.binding.content_digest,
            referenced_paths=(),
        )
        assert read_attempt_state(paths, binding, identity).is_active
    finally:
        store.close()

    after = _snapshot(config)[0]
    assert not any(
        view.safe_reclaimable
        for view in after.views
        if view.artifact_id.startswith(f"p7:attempt_scratch:1:{identity}")
    ), "a reopened attempt's scratch stayed reclaimable"


# ---------------------------------------------------------------------------
# R19-D - bounded P7 reporting
# ---------------------------------------------------------------------------


def test_normal_report_does_not_scale_with_released_attempt_bulk(tmp_path: Path):
    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"

    def _report_cost() -> tuple[int, bool]:
        visits = {"n": 0}
        touched: list[str] = []
        real_lstat = os.lstat
        real_scandir = os.scandir
        real_open = os.open

        def counting_lstat(path, *args, **kwargs):
            visits["n"] += 1
            return real_lstat(path, *args, **kwargs)

        def counting_scandir(*args, **kwargs):
            visits["n"] += 1
            return real_scandir(*args, **kwargs)

        def recording_open(path, *args, **kwargs):
            touched.append(str(path))
            return real_open(path, *args, **kwargs)

        os.lstat = counting_lstat
        os.scandir = counting_scandir
        os.open = recording_open
        try:
            assert p4d._run(config, "storage", "report") == 0
        finally:
            os.lstat = real_lstat
            os.scandir = real_scandir
            os.open = real_open
        return visits["n"], str(proof) in touched

    baseline, read_proof = _report_cost()
    assert not read_proof, "the bounded report parsed the full released-attempt proof"

    grown = attempt / "components"
    grown.mkdir(exist_ok=True)
    for index in range(500):
        (grown / f"bulk-{index}.bin").write_bytes(b"x" * 32)
    after, read_proof_again = _report_cost()
    assert not read_proof_again
    assert after < baseline + 60, (baseline, after)

    # Consequential planning does pay for the exact proof, and refuses the run
    # that now contains 500 nodes nobody recorded.
    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    )


def test_bounded_and_exact_p7_reporting_share_one_owner_truth(tmp_path: Path):
    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    bounded, _paths = _snapshot(config, certify=False)
    exact, _paths = _snapshot(config, certify=True)
    bounded_scratch = [
        view for view in bounded.views if view.artifact_id.startswith("p7:attempt_scratch:")
    ]
    exact_scratch = [
        view for view in exact.views if view.artifact_id.startswith("p7:attempt_scratch:")
    ]
    assert bounded_scratch and exact_scratch
    # Bounded reporting says "released, needs exact certification"; it never
    # claims per-member deletion authority.
    assert all(view.container_only for view in bounded_scratch)
    assert all(not view.safe_reclaimable for view in bounded_scratch)
    assert any("needs exact certification" in view.detail for view in bounded_scratch)
    assert any(view.safe_reclaimable for view in exact_scratch)


# ---------------------------------------------------------------------------
# R19-C - constructor writes are part of the cross-process writer census
# ---------------------------------------------------------------------------


_CONSTRUCTING_CHILD = """
import sys, time
sys.path.insert(0, {repository!r})
open({started!r}, "w").close()
from mdstats.training_data._campaign_cli_core import CampaignStore

store = CampaignStore({database!r})
try:
    open({finished!r}, "w").close()
finally:
    store.close()
"""


def test_a_second_process_cannot_bootstrap_schema_while_the_gate_is_held(
    tmp_path: Path,
):
    """Writable construction writes; therefore it joins the writer census.

    A constructor that bootstrapped its schema outside the exclusion would let a
    second process mutate the database while maintenance believed every
    supported writer was excluded - which is exactly the guarantee the VACUUM
    benefit predicate rests on.
    """

    import subprocess
    import sys

    config, _workspace = p5.build_selected_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    started = tmp_path / "child-started"
    finished = tmp_path / "child-finished"
    try:
        with store.writer_exclusion():
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _CONSTRUCTING_CHILD.format(
                        repository=str(Path(cli.__file__).resolve().parents[2]),
                        database=str(paths.state_db),
                        started=str(started),
                        finished=str(finished),
                    ),
                ]
            )
            deadline = time.time() + 60.0
            while not started.exists() and time.time() < deadline:
                time.sleep(0.05)
            assert started.exists(), "the child never started"
            time.sleep(1.5)
            assert not finished.exists(), (
                "a second process completed a writable construction while the "
                "writer exclusion was held"
            )
        assert child.wait(120) == 0
        assert finished.exists()
    finally:
        store.close()

    fresh = CampaignStore(paths.state_db)
    try:
        fresh.event("info", "after", "the writer path is available again")
    finally:
        fresh.close()


# ---------------------------------------------------------------------------
# R21-A / R21-B / IR20-2 - strict, root-bound, identity-authenticated P7 state
# ---------------------------------------------------------------------------


def _assert_p7_ambiguity_blocks_everything(config: Path, checkpoints) -> None:
    """No planning, no released scratch, no destructive authorization anywhere."""

    from mdstats.training_data.qualification.store import (
        build_qualification_retention_fence,
    )
    from mdstats.training_data.storage.inventory import OwnerGraphError

    snapshot, paths = _snapshot(config)
    assert snapshot.integrity_failures, "an unresolved attempt raised no integrity failure"
    with pytest.raises(OwnerGraphError):
        snapshot.require_planable()

    # R21-B: the local classifier must agree with the global graph. A test that
    # only proved require_planable() was red could stay green while a parallel
    # reader kept classifying the attempt as released.
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    ), "released scratch authority survived an unresolved attempt state"

    # R21-D: the physical boundary refuses independently of the planner, and it
    # refuses for artifacts far outside the P7 tree.
    fence = build_qualification_retention_fence(paths)
    assert fence.ambiguous_attempt_state is True
    assert fence.ambiguity_reasons
    cfg, _paths = cli._load_config(config)
    store = CampaignStore(paths.state_db, create=False)
    try:
        with cli.observational_campaign_state():
            boundary = cli._campaign_ownership_boundary(cfg, paths, store)
    finally:
        store.close()
    for checkpoint in checkpoints:
        authorized, why = boundary.destructive_authorization(checkpoint)
        assert not authorized, checkpoint
        assert "cannot be authenticated" in why
    unrelated = paths.internal / "records"
    unrelated.mkdir(parents=True, exist_ok=True)
    authorized, why = boundary.destructive_authorization(unrelated / "anything.bin")
    assert not authorized and "cannot be authenticated" in why

    assert p4d._run(config, "storage", "report") == 0
    for checkpoint in checkpoints:
        assert checkpoint.is_file()


def _assert_p7_repair_restores_planning(config: Path) -> None:
    from mdstats.training_data.qualification.store import (
        build_qualification_retention_fence,
    )

    snapshot, paths = _snapshot(config)
    assert snapshot.integrity_failures == ()
    snapshot.require_planable()
    assert build_qualification_retention_fence(paths).ambiguous_attempt_state is False


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_state",
        "wrong_root_state",
        "missing_digest",
        "state_symlink",
        "attempt_root_symlink",
        "generation_root_symlink",
        "attempts_container_symlink",
        "state_fifo",
        "canonical_identity_mismatch",
        "missing_required_field",
        "null_referenced_paths",
        "noncanonical_generation",
        "family_root_symlink",
        "family_root_wrong_kind",
        "family_root_unreadable",
        "scratch_fifo",
    ],
)
def test_unauthenticated_p7_attempt_state_blocks_everything(
    tmp_path: Path, corruption: str
):
    """Unknown P7 liveness is a workspace-wide reduction, not a local one.

    An active attempt's `referenced_paths` routinely name P5 publication
    checkpoints outside the P7 tree. If the state cannot be authenticated those
    paths are unrecoverable, so nothing campaign-managed may be authorized until
    it is repaired - and the storage planner is not the only thing that has to
    say so.
    """

    import shutil as _shutil

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    checkpoints = _published_checkpoints(config, harness)
    assert checkpoints
    attempt = _released_attempt_root(config)
    attempts_root = attempt.parent
    generation_root = attempts_root.parent
    state = attempt / "attempt-state.json"
    saved = state.read_bytes()
    restore: list = []

    if corruption == "missing_state":
        state.unlink()
        restore.append(lambda: state.write_bytes(saved))
    elif corruption == "wrong_root_state":
        # A digest-valid state, published for a different attempt, copied over
        # this one. Self-consistency is not identity.
        from mdstats.training_data.qualification.store import (
            QualificationAttemptState,
            _expected_attempt_identity,
        )

        # A record that is valid in every independent way: its self digest
        # recomputes, and its attempt identity really is the canonical identity
        # derived from the binding it names. The *only* thing wrong is that it
        # was published for a different attempt than the root it sits in, so
        # nothing but the state/root relation can refuse it.
        payload = json.loads(saved.decode("utf-8"))
        foreign_binding = "b" * 64
        foreign_identity = _expected_attempt_identity(foreign_binding)
        assert foreign_identity != payload["attempt_identity"]
        payload["binding_digest"] = foreign_binding
        payload["attempt_identity"] = foreign_identity
        payload.pop("content_digest", None)
        payload["content_digest"] = QualificationAttemptState.from_dict(
            dict(payload)
        ).content_digest
        other = attempts_root / foreign_identity
        other.mkdir()
        (other / "attempt-state.json").write_text(json.dumps(payload), encoding="utf-8")
        state.write_text(json.dumps(payload), encoding="utf-8")
        restore.append(lambda: state.write_bytes(saved))
        restore.append(lambda: _shutil.rmtree(other))
    elif corruption == "missing_digest":
        payload = json.loads(saved.decode("utf-8"))
        payload.pop("content_digest", None)
        payload["referenced_paths"] = []
        payload["state"] = "terminal"
        state.write_text(json.dumps(payload), encoding="utf-8")
        restore.append(lambda: state.write_bytes(saved))
    elif corruption == "canonical_identity_mismatch":
        # Directory name, recorded identity, and self digest all agree - but the
        # binding they name derives a different canonical attempt identity.
        payload = json.loads(saved.decode("utf-8"))
        payload["binding_digest"] = "d" * 64
        payload.pop("content_digest", None)
        state.write_text(json.dumps(payload), encoding="utf-8")
        from mdstats.training_data.qualification.store import QualificationAttemptState

        rebuilt = QualificationAttemptState.from_dict(
            json.loads(state.read_text(encoding="utf-8"))
        )
        payload["content_digest"] = rebuilt.content_digest
        state.write_text(json.dumps(payload), encoding="utf-8")
        restore.append(lambda: state.write_bytes(saved))
    elif corruption == "state_fifo":
        state.unlink()
        os.mkfifo(state)
        restore.append(lambda: (state.unlink(), state.write_bytes(saved)))
    elif corruption == "state_symlink":
        planted = attempts_root / "planted-state.json"
        planted.write_bytes(saved)
        state.unlink()
        state.symlink_to(planted)
        restore.append(lambda: (state.unlink(), state.write_bytes(saved), planted.unlink()))
    elif corruption == "attempt_root_symlink":
        moved = attempts_root.parent / f"moved-{attempt.name}"
        attempt.rename(moved)
        attempt.symlink_to(moved)
        restore.append(lambda: (attempt.unlink(), moved.rename(attempt)))
    elif corruption == "generation_root_symlink":
        moved = generation_root.parent / f"moved-{generation_root.name}"
        generation_root.rename(moved)
        generation_root.symlink_to(moved)
        restore.append(lambda: (generation_root.unlink(), moved.rename(generation_root)))
    elif corruption == "missing_required_field":
        # IR23-1: syntactically valid JSON, digest field present, one required
        # field gone. `from_dict` raises KeyError; the owner boundary must turn
        # that into unresolved authority rather than let it escape.
        payload = json.loads(saved.decode("utf-8"))
        payload.pop("binding_digest", None)
        state.write_text(json.dumps(payload), encoding="utf-8")
        restore.append(lambda: state.write_bytes(saved))
    elif corruption == "null_referenced_paths":
        # IR23-1: a parseable object with an invalid container type.
        payload = json.loads(saved.decode("utf-8"))
        payload["referenced_paths"] = None
        state.write_text(json.dumps(payload), encoding="utf-8")
        restore.append(lambda: state.write_bytes(saved))
    elif corruption == "noncanonical_generation":
        # R24: the reserved generation namespace has exactly one spelling. A
        # second, noncanonical one is an integrity problem, not another place
        # for the owner to go looking for state.
        planted = generation_root.parent / "g01"
        planted.mkdir()
        restore.append(lambda: planted.rmdir())
    elif corruption == "family_root_symlink":
        family = generation_root.parent
        moved = family.parent / "moved-qualification"
        family.rename(moved)
        family.symlink_to(moved)
        restore.append(lambda: (family.unlink(), moved.rename(family)))
    elif corruption == "family_root_wrong_kind":
        family = generation_root.parent
        moved = family.parent / "moved-qualification"
        family.rename(moved)
        family.write_bytes(b"not a directory")
        restore.append(lambda: (family.unlink(), moved.rename(family)))
    elif corruption == "family_root_unreadable":
        family = generation_root.parent
        mode = family.stat().st_mode
        os.chmod(family, 0o000)
        restore.append(lambda: os.chmod(family, mode))
    elif corruption == "scratch_fifo":
        # R22-2.2: a special node inside the released *scratch*, distinct from
        # the attempt-state special-node case. It cannot be certified, so the
        # containing member keeps its bytes - and because the top-level node set
        # no longer matches the proof, the whole released authority is withdrawn.
        member = next(
            item for item in sorted(attempt.iterdir()) if item.is_dir()
        )
        planted = member / "someone-elses.fifo"
        os.mkfifo(planted)
        restore.append(lambda: planted.unlink())
    else:  # attempts_container_symlink
        moved = generation_root / "moved-attempts"
        attempts_root.rename(moved)
        attempts_root.symlink_to(moved)
        restore.append(lambda: (attempts_root.unlink(), moved.rename(attempts_root)))

    if corruption == "scratch_fifo":
        # A special node below a released attempt reduces that attempt's
        # authority; it is not unknown cross-owner liveness, so ordinary
        # planning stays available while the contaminated member is retained.
        snapshot, _paths = _snapshot(config)
        assert not any(
            view.safe_reclaimable
            for view in snapshot.views
            if view.artifact_id.startswith("p7:attempt_scratch:")
        ), "a released attempt containing a FIFO still authorized reclamation"
        assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
        assert planted.is_fifo()
        for checkpoint in checkpoints:
            assert checkpoint.is_file()
    else:
        _assert_p7_ambiguity_blocks_everything(config, checkpoints)
        if corruption == "wrong_root_state":
            # R22-2.1: the state is self-digest-valid, so the only thing left to
            # refuse it is the relation between the record and the root it was
            # found under.
            snapshot, _paths = _snapshot(config)
            assert any(
                "different attempt identity than the directory it was read from"
                in item
                for item in snapshot.integrity_failures
            ), snapshot.integrity_failures
    for undo in restore:
        undo()
    _assert_p7_repair_restores_planning(config)


def test_the_strict_state_authority_is_the_only_storage_facing_reader() -> None:
    """Structural: no permissive parse confers storage authority beside it."""

    import ast

    store_source = (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(store_source)
    for name in (
        "iter_attempt_state_census",
        "read_attempt_state_at",
        "build_qualification_retention_fence",
    ):
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        dumped = ast.dump(node)
        assert "from_dict" not in dumped, name
        assert (
            "authenticate_attempt_state" in dumped
            or "iter_attempt_state_authorities" in dumped
            or "iter_attempt_state_census" in dumped
            or "observe_qualification_namespace" in dumped
        ), name

    owners = (Path(cli.__file__).parent / "storage" / "owners.py").read_text(
        encoding="utf-8"
    )
    assert "QualificationAttemptState" not in owners, (
        "a storage owner view still parses attempt state for itself"
    )
    assert "read_attempt_state_at" not in owners


def test_the_p7_owner_view_never_rediscovers_the_attempt_hierarchy() -> None:
    """IR25-1: the forbidden mechanism itself, not a proxy for it.

    The storage-facing P7 view must take its generation/attempt facts from the
    one descriptor-bound namespace result. A followable rediscovery of
    `qualification/gN/attempts/<attempt>` here would observe the target of an
    ancestor substituted after the strict census, which is exactly the window
    the descriptor descent closed. This asserts on the mechanisms that would
    reopen it, so removing the consolidation fails the test.
    """

    import ast

    from mdstats.training_data.qualification import store as qualification_store

    owners_path = Path(cli.__file__).parent / "storage" / "owners.py"
    source = owners_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item
        for item in ast.walk(tree)
        if isinstance(item, ast.FunctionDef) and item.name == "qualification_views"
    )
    body = "".join(source.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])

    assert "observe_qualification_namespace" in body, (
        "the P7 view no longer consumes the strict namespace authority"
    )
    for forbidden in (
        "_generation_roots",
        ".iterdir()",
        ".glob(",
        "certified_attempt_nodes",
        "validate_bound_attempt_proof",
        "read_attempt_member_proof",
    ):
        assert forbidden not in body, (
            f"the P7 owner view rediscovers the attempt hierarchy via {forbidden}"
        )
    # The path-taking storage certification helper is retired outright rather
    # than kept for source compatibility: both its proof read and its descendant
    # observation were pathname-based, so leaving it would leave the bypass.
    assert not hasattr(qualification_store, "certified_attempt_nodes"), (
        "a path-taking released-attempt certification helper is still reachable"
    )
    # `is_dir()` survives only for durable non-attempt evidence, never to reach
    # attempt state or scratch.
    for line in body.splitlines():
        if ".is_dir()" in line:
            assert "reveal_root" in line or "reference_root" in line, line

    # Exact certification is descriptor-relative, and it recomputes the expected
    # locator from the authenticated generation rather than looking the ancestry
    # up again by name.
    store_source = (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")
    store_tree = ast.parse(store_source)
    certify = next(
        item
        for item in ast.walk(store_tree)
        if isinstance(item, ast.FunctionDef)
        and item.name == "_certify_attempt_from_descriptor"
    )
    certify_body = "".join(
        store_source.splitlines(keepends=True)[certify.lineno - 1 : certify.end_lineno]
    )
    assert "dir_fd=attempt_fd" in certify_body
    assert "_observe_attempt_nodes_from_descriptor" in certify_body
    # The docstring may *discuss* the rejected name lookup; the code may not
    # perform one, so the check is on executable nodes only.
    certify_code = ast.dump(
        ast.Module(
            body=[
                item
                for item in certify.body
                if not (
                    isinstance(item, ast.Expr)
                    and isinstance(item.value, ast.Constant)
                    and isinstance(item.value.value, str)
                )
            ],
            type_ignores=[],
        )
    )
    assert "parent" not in certify_code, (
        "exact certification still derives the generation from a name lookup"
    )

    # And every consequential P7 removal goes through the owner's own
    # descriptor-relative boundary rather than a generic absolute-path delete.
    commands = (Path(cli.__file__).parent / "storage" / "commands.py").read_text(
        encoding="utf-8"
    )
    assert "remove_released_attempt_member" in commands
    engine = next(
        item
        for item in ast.walk(ast.parse(commands))
        if isinstance(item, ast.FunctionDef) and item.name == "_cleanup_engine"
    )
    engine_body = "".join(
        commands.splitlines(keepends=True)[engine.lineno - 1 : engine.end_lineno]
    )
    released = engine_body.index("P7_RELEASED_ATTEMPT_AUTHORIZER")
    generic = engine_body.index("remove_durably(action.path)")
    assert released < generic, (
        "a released P7 action can reach the generic path removal first"
    )


# ---------------------------------------------------------------------------
# IR20-3 - repeated terminal release validates the retained proof
# ---------------------------------------------------------------------------


def _repeat_terminal_release(config: Path, harness):
    from mdstats.training_data.qualification.store import release_attempt_reference

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        return release_attempt_reference(
            paths,
            session.context.selected.binding,
            attempt_identity=session.binding.attempt_identity,
        )
    finally:
        store.close()


def test_a_valid_repeated_terminal_release_reuses_the_bound_proof(tmp_path: Path):
    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"
    state = attempt / "attempt-state.json"
    before = (proof.read_bytes(), state.read_bytes())
    scratch = sorted(str(item) for item in attempt.rglob("*"))

    result = _repeat_terminal_release(config, harness)
    assert result is not None and result.state == "terminal"
    assert (proof.read_bytes(), state.read_bytes()) == before
    assert sorted(str(item) for item in attempt.rglob("*")) == scratch


@pytest.mark.parametrize(
    "damage", ["missing", "v2_only", "self_digest", "binding_digest", "publication_digest"]
)
def test_a_repeated_terminal_release_fails_closed_on_a_broken_proof(
    tmp_path: Path, damage: str
):
    """The owner must surface a lost proof, not report an ordinary success."""

    from mdstats.training_data.qualification.store import QualificationLineageError

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"
    payload = json.loads(proof.read_text(encoding="utf-8"))
    scratch_before = sorted(
        str(item) for item in attempt.rglob("*") if item != proof
    )

    if damage == "missing":
        proof.unlink()
    elif damage == "v2_only":
        proof.write_text(
            json.dumps(
                {
                    "schema": "mdstats.qualification-attempt-members.v2",
                    "attempt_root": attempt.name,
                    "members": [],
                    "member_count": 0,
                }
            ),
            encoding="utf-8",
        )
    elif damage == "self_digest":
        payload["content_digest"] = "0" * 64
        proof.write_text(json.dumps(payload), encoding="utf-8")
    else:
        # Contradict the state while keeping the record self-consistent, so only
        # the cross-field binding check can catch it.
        from mdstats.training_data._common import digest as _digest

        payload[damage] = "e" * 64
        body = {k: v for k, v in payload.items() if k != "content_digest"}
        payload["content_digest"] = _digest(body)
        proof.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QualificationLineageError, match="released-attempt proof"):
        _repeat_terminal_release(config, harness)
    assert (
        sorted(str(item) for item in attempt.rglob("*") if item != proof)
        == scratch_before
    )


# ---------------------------------------------------------------------------
# IR20-4 - concurrent aborted reopen versus real storage cleanup, both orders
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("owner_first", [True, False])
def test_an_aborted_reopen_and_storage_cleanup_never_interleave(
    tmp_path: Path, owner_first: bool
):
    """Both orderings, through the production attempt-state lock.

    Attempt identity is canonically derived from the qualification binding, so
    there is exactly one attempt per binding: the aborted-reopen lifecycle has to
    be exercised on that attempt, not on an invented second one. Whichever side
    takes the seam first, the other waits - storage never removes scratch an
    attempt is in the middle of reopening, and a reopen never lands mid-removal.
    """

    from mdstats.training_data.qualification.store import (
        ATTEMPT_ABORTED,
        acquire_attempt_reference,
        read_attempt_state_at,
        release_attempt_reference,
    )

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _run_to_waiting(config, harness) == 0

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        binding = session.context.selected.binding
        identity = session.binding.attempt_identity
        publication = session.binding.publication_digest
        binding_digest = session.binding.content_digest
        aborted = release_attempt_reference(
            paths, binding, attempt_identity=identity, terminal=False
        )
        assert aborted is not None and aborted.state == ATTEMPT_ABORTED
        attempt_root = paths.internal / "qualification" / "g1" / "attempts" / identity
    finally:
        store.close()
    assert attempt_root.is_dir()

    order: list[str] = []
    failures: list[BaseException] = []
    first_inside = threading.Event()
    release = threading.Event()

    # IR22-2.3: instrument the *production* seam rather than a stand-in. Both
    # the P7 owner and the storage owner barrier reach the attempt lock through
    # this one primitive, so the wrapper delegates to it and only signals after
    # the real lock has been acquired. The designated first contender then holds
    # it while the second one runs, which is what makes each ordering actually
    # happen rather than merely being asked for.
    from mdstats.training_data import target_size_execution as _tse

    acquisitions: list[tuple[str, str]] = []
    acquisition_lock = threading.Lock()
    real_publication_lock = _tse.artifact_publication_lock

    @contextmanager
    def _instrumented_lock(target, *args, **kwargs):
        watched = Path(target).name == "attempt-state.json"
        who = threading.current_thread().name
        with real_publication_lock(target, *args, **kwargs):
            if watched:
                with acquisition_lock:
                    acquisitions.append((who, "enter"))
                if who == "first":
                    first_inside.set()
                    release.wait(120.0)
            try:
                yield
            finally:
                if watched:
                    with acquisition_lock:
                        acquisitions.append((who, "exit"))

    def reopen() -> None:
        try:
            _c, p, s, sess = fx.load_session(config, harness)
            try:
                acquire_attempt_reference(
                    p,
                    sess.context.selected.binding,
                    attempt_identity=identity,
                    publication_digest=publication,
                    binding_digest=binding_digest,
                    referenced_paths=(),
                )
            finally:
                s.close()
            order.append("reopen")
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    def cleanup() -> None:
        try:
            assert (
                p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
            )
            order.append("cleanup")
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    winner, loser = (reopen, cleanup) if owner_first else (cleanup, reopen)
    winner_name = "reopen" if owner_first else "cleanup"
    loser_name = "cleanup" if owner_first else "reopen"

    _tse.artifact_publication_lock = _instrumented_lock
    try:
        first = threading.Thread(target=winner, name="first", daemon=True)
        first.start()
        assert first_inside.wait(180.0), f"{winner_name} never reached the attempt seam"
        second = threading.Thread(target=loser, name="second", daemon=True)
        second.start()
        time.sleep(2.0)

        # The real seam is held by the first contender. The second one may be
        # anywhere in its own prologue, but it has not acquired the attempt lock
        # and it has certainly not completed.
        with acquisition_lock:
            observed = list(acquisitions)
        assert observed == [("first", "enter")], observed
        assert order == [], f"{loser_name} completed while the attempt seam was held"

        release.set()
        first.join(300.0)
        second.join(300.0)
    finally:
        _tse.artifact_publication_lock = real_publication_lock
        release.set()
    assert not failures, failures
    assert not first.is_alive() and not second.is_alive()

    # Both orderings really happened: the designated winner acquired and left
    # the production seam before the loser ever entered it, and finished first.
    assert acquisitions[0] == ("first", "enter"), acquisitions
    entries = [index for index, item in enumerate(acquisitions) if item[1] == "enter"]
    depth = 0
    for _who, event in acquisitions:
        depth += 1 if event == "enter" else -1
        assert depth in (0, 1), acquisitions
    assert len(entries) >= 1
    if any(who == "second" for who, _event in acquisitions):
        second_enter = next(
            index for index, item in enumerate(acquisitions) if item[0] == "second"
        )
        assert acquisitions.index(("first", "exit")) < second_enter, acquisitions
    assert order and order[0] == winner_name, order

    # The reopened attempt is active again, and its scratch is not classified as
    # released regardless of which side won the race.
    state = read_attempt_state_at(attempt_root)
    assert state is not None and state.is_active
    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith(f"p7:attempt_scratch:1:{identity}")
    )


# ---------------------------------------------------------------------------
# R24 - the authenticated root identity survives to the mutation seam
# ---------------------------------------------------------------------------


def _released_scratch_view(config: Path, *, member_name: str | None = None):
    """The exact reclaimable released-scratch view and its snapshot."""

    snapshot, paths = _snapshot(config)
    views = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
        and view.safe_reclaimable
        and view.path.is_dir()
        and (member_name is None or view.path.name == member_name)
    ]
    assert views, "the fixture produced no reclaimable released scratch directory"
    return snapshot, paths, views[0]


def test_the_released_scratch_view_carries_its_authenticated_root_identity(
    tmp_path: Path,
):
    """R24-3: the accepted authority is root-bound, not name-bound."""

    from mdstats.training_data.storage.owners import P7_RELEASED_ATTEMPT_AUTHORIZER

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    _snap, _paths, view = _released_scratch_view(config)
    assert view.exact_authorizer == P7_RELEASED_ATTEMPT_AUTHORIZER
    assert view.root_identity is not None
    observed = view.path.parent.stat()
    assert int(view.root_identity["device"]) == int(observed.st_dev)
    assert int(view.root_identity["inode"]) == int(observed.st_ino)


@pytest.mark.parametrize("swap", ["symlink", "same_shaped_directory"])
def test_a_root_swap_after_certification_transfers_no_authority(
    tmp_path: Path, swap: str
):
    """R24-3: certification happens on a directory, not on a name.

    Between the under-lock certification and the final common mutation, the
    attempt root is replaced. `shutil.rmtree` avoiding symlink attacks says
    nothing about the top-level name it was handed, so the replacement must be
    refused by identity - including when it is a same-shaped plain directory
    that no symlink check could distinguish.
    """

    import shutil as _shutil

    from mdstats.training_data.storage.executor import remove_certified_subtree

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    snapshot, _paths, view = _released_scratch_view(config)
    members, refusals = snapshot.authorized_members(view)
    assert members and not refusals, (members, refusals)

    attempt = view.path.parent
    parked = attempt.parent / "parked"
    if swap == "symlink":
        attempt.rename(parked)
        attempt.symlink_to(parked)
        replacement = parked
    else:
        # A byte-for-byte twin: same names, same kinds, same self-valid state,
        # different inode. Only the recorded identity separates them.
        _shutil.copytree(attempt, parked, symlinks=True)
        attempt.rename(attempt.parent / "original")
        parked.rename(attempt)
        replacement = attempt

    after, _paths2 = _snapshot(config)
    swapped = after.view(view.artifact_id)
    if swapped is not None:
        # The owner re-derives its own view honestly; what must not happen is
        # the *old* accepted authority being spent on the new object.
        pass
    members_after, refusals_after = snapshot.authorized_members(view)
    assert members_after == (), members_after
    assert refusals_after, "a replaced root produced no refusal"
    assert any(
        "different filesystem object" in why or "unresolved" in why
        for _path, why in refusals_after
    ), refusals_after

    # And the last seam refuses independently, with the originally authorized
    # member list still in hand.
    removed, why = remove_certified_subtree(
        view.path,
        members=members,
        refusals=(),
        root_identity=view.root_identity,
    )
    assert removed is False
    assert "no longer the filesystem object" in why or "re-observed" in why, why
    assert (replacement / view.path.name).exists() or view.path.exists()


def test_a_released_attempt_copied_under_another_generation_grants_nothing(
    tmp_path: Path,
):
    """R24-2: the released root is generation-scoped, not a basename."""

    import shutil as _shutil

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    generation_root = attempt.parent.parent
    family = generation_root.parent
    # A complete, ordinary-looking foreign generation: the evidence store the
    # attempt views depend on exists too, so the copied attempt is refused by
    # its root binding rather than by an incidental hole in the owner graph.
    _shutil.copytree(generation_root / "objects", family / "g99" / "objects")
    other = family / "g99" / "attempts"
    other.mkdir(parents=True)
    copied = other / attempt.name
    _shutil.copytree(attempt, copied, symlinks=True)

    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:99:")
    ), "a whole attempt copied into another generation carried its authority along"
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert copied.is_dir()
    assert sorted(item.name for item in copied.iterdir())


def test_a_basename_only_proof_grants_no_authority(tmp_path: Path):
    """R24-2: the incomplete development form is diagnostic, never authority."""

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    attempt = _released_attempt_root(config)
    proof = attempt / "attempt-members.json"
    payload = json.loads(proof.read_text(encoding="utf-8"))
    recorded = str(payload["attempt_root"])
    assert "/" in recorded, "the production proof is not generation-scoped"
    from mdstats.training_data._common import digest as _digest

    payload["attempt_root"] = recorded.rsplit("/", 1)[-1]
    body = {k: v for k, v in payload.items() if k != "content_digest"}
    payload["content_digest"] = _digest(body)
    proof.write_text(json.dumps(payload), encoding="utf-8")

    # The record still authenticates against its own identity; only the root
    # locator is the incomplete development form.
    from mdstats.training_data.qualification.store import (
        validate_attempt_member_proof_bytes,
    )

    parsed, why = validate_attempt_member_proof_bytes(proof.read_bytes())
    assert parsed is None, "the fixture is refused by something other than the root"
    assert "bare attempt name" in why, why

    snapshot, _paths = _snapshot(config)
    assert not any(
        view.safe_reclaimable
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:")
    ), "a basename-only proof still authorized reclamation"
    assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    assert proof.is_file()


@pytest.mark.parametrize(
    "component", ["generation_root", "attempts_container", "attempt"]
)
@pytest.mark.parametrize("replacement", ["removed", "substituted"])
def test_an_ancestor_replaced_between_enumeration_and_open_fails_closed(
    tmp_path: Path, component: str, replacement: str
):
    """R22/R24-1: enumerate-then-replace is unresolved, never ordinary absence.

    The race is injected at the real directory-open seam, for each
    authority-bearing component of the descent, in both shapes: the entry
    vanishing between enumeration and open, and a same-named symlink to a
    foreign tree taking its place.
    """

    from mdstats.training_data.qualification import store as qstore

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    checkpoints = _published_checkpoints(config, harness)
    attempt = _released_attempt_root(config)
    attempts_root = attempt.parent
    generation_root = attempts_root.parent
    _snapshot_before, paths = _snapshot(config)
    target = {
        "generation_root": generation_root,
        "attempts_container": attempts_root,
        "attempt": attempt,
    }[component]
    parked = target.parent / f"parked-{target.name}"

    real_open = qstore._open_directory_nofollow
    swapped: list[str] = []

    def racing_open(name: str, *, dir_fd=None):
        if name == target.name and not swapped:
            # The entry was enumerated a moment ago; by the time the owner tries
            # to open it authoritatively it is gone, or it is something else.
            swapped.append(name)
            target.rename(parked)
            if replacement == "substituted":
                target.symlink_to(parked)
        return real_open(name, dir_fd=dir_fd)

    qstore._open_directory_nofollow = racing_open
    try:
        authorities = qstore.iter_attempt_state_authorities(paths)
    finally:
        qstore._open_directory_nofollow = real_open
    assert swapped, "the race never fired"

    unresolved = [item for item in authorities if not item.resolved]
    assert not any(item.resolved for item in authorities), (
        "the raced descent still produced released-attempt authority"
    )
    if component == "attempts_container" and replacement == "removed":
        # This one child is reached by literal name rather than by enumeration,
        # so its genuine absence at the authoritative lookup is ordinary "no
        # attempts for this generation" - the contract's one absence case. What
        # must not happen is authority being produced anyway.
        assert authorities == () or unresolved, authorities
    else:
        assert unresolved, (
            f"a {component} lost mid-observation was reported as simply absent"
        )
        assert any(
            "namespace changed" in item.reason or "could not be opened" in item.reason
            for item in unresolved
        ), [item.reason for item in unresolved]

    if replacement == "substituted":
        target.unlink()
    parked.rename(target)
    _assert_p7_repair_restores_planning(config)
    for checkpoint in checkpoints:
        assert checkpoint.is_file()


def test_a_nested_mount_under_released_scratch_is_never_traversed(tmp_path: Path):
    """R24-1/IR25-3.3: a descriptor-safe descent does not make a mount ours.

    The mount directory is created *before* the attempt is released, so the
    released proof records it as an ordinary certified directory. Exact
    authorization therefore has no unexpected-node contradiction to fall over
    on: the only thing that can stop the traversal is the mount boundary itself.
    """

    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert _qualify_nonlocked(config, harness) == 0

    # Plant the directory while the attempt is still active, then release: the
    # proof P7 publishes records it as one of its own certified nodes.
    active, paths = _snapshot(config, certify=False)
    attempt = next(
        view.path
        for view in active.views
        if view.artifact_id.startswith("p7:attempt:")
    )
    member = next(item for item in sorted(attempt.iterdir()) if item.is_dir())
    nested = member / "mounted"
    nested.mkdir()
    (nested / "foreign.bin").write_bytes(b"someone else's bytes")
    _release_attempt(config, harness)

    snapshot, _paths, view = _released_scratch_view(config, member_name=member.name)
    recorded = {item.path for item in view.certified_nodes}
    assert "mounted" in recorded, sorted(recorded)
    assert "mounted/foreign.bin" in recorded, sorted(recorded)

    set_mount_resolver(
        MountIdentityResolver(mount_points=frozenset({str(nested)}), available=True)
    )
    try:
        fresh, _paths2 = _snapshot(config)
        target = fresh.view(view.artifact_id)
        assert target is not None
        # The mount is the *only* thing that changed, and it is enough: the
        # descriptor descent classifies the mounted directory as unowned, so the
        # exact certification contradicts and the container stops being
        # reclaimable at all.
        assert not target.safe_reclaimable, target.detail
        assert "mount" in target.detail, target.detail
        members, refusals = fresh.authorized_members(target)
        assert all("mounted" not in str(item) for item in members), members
        # And the real cleanup retains rather than emptying the mounted tree.
        assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    finally:
        set_mount_resolver(None)
    assert (nested / "foreign.bin").read_bytes() == b"someone else's bytes"

def test_a_stale_handle_at_the_open_seam_is_unresolved_not_absent(tmp_path: Path):
    """R24-1: `ESTALE` at the real open seam is ambiguity, never absence."""

    import errno

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    checkpoints = _published_checkpoints(config, harness)
    attempt = _released_attempt_root(config)

    real_os_open = os.open

    def stale_open(name, *args, **kwargs):
        if isinstance(name, str) and name == attempt.name:
            raise OSError(errno.ESTALE, "Stale file handle", name)
        return real_os_open(name, *args, **kwargs)

    os.open = stale_open
    try:
        _assert_p7_ambiguity_blocks_everything(config, checkpoints)
        assert p4d._run(config, "storage", "report") == 0
    finally:
        os.open = real_os_open
    _assert_p7_repair_restores_planning(config)


def test_the_released_root_locator_survives_a_workspace_relocation(tmp_path: Path):
    """R24-2: the durable locator is workspace-portable, not an absolute path."""

    import shutil as _shutil

    config, workspace, _harness = _released_attempt_campaign(tmp_path)
    before, _paths = _snapshot(config)
    reclaimable_before = {
        view.artifact_id
        for view in before.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    }
    assert reclaimable_before

    moved = tmp_path / "relocated-workspace"
    _shutil.copytree(workspace, moved, symlinks=True)
    relocated_config = tmp_path / "relocated.toml"
    relocated_config.write_text(
        config.read_text(encoding="utf-8").replace(str(workspace), str(moved)),
        encoding="utf-8",
    )

    after, _paths2 = _snapshot(relocated_config)
    reclaimable_after = {
        view.artifact_id
        for view in after.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    }
    assert reclaimable_after == reclaimable_before, (
        "relocating the workspace changed released-attempt authority"
    )


@pytest.mark.parametrize("swap", ["symlink", "same_shaped_directory"])
def test_an_apply_time_root_swap_transfers_no_authority(tmp_path: Path, swap: str):
    """R26-A: the race fires below the owner, just before the destructive call.

    The real cleanup runs. For each released action the P7 owner re-acquires the
    strict namespace, checks the attempt-root identity, and only then reaches
    the fd-relative mutation - which is where the public attempt pathname is
    replaced.

    Two things must hold afterwards. The action that was already inside its
    mutation completes against the descriptor it holds, which is the object the
    certification was performed on. Every action after it re-acquires by name,
    finds something that is not that object, and refuses. Authority is never
    transferred to the replacement - which is the guarantee R26 freezes, rather
    than an inode compare-and-delete the kernel does not offer.

    Both a proof-certified directory and a proof-certified top-level regular
    file are exercised: the released plan contains both.
    """

    import shutil as _shutil

    from mdstats.training_data.qualification import store as qstore

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    snapshot, _paths = _snapshot(config)
    released = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    ]
    assert any(view.path.is_dir() for view in released), released
    assert any(view.path.is_file() for view in released), released
    attempt = released[0].path.parent
    parked = attempt.parent / "parked"
    fired: list[str] = []

    def perform_swap() -> None:
        if fired:
            return
        fired.append(swap)
        if swap == "symlink":
            attempt.rename(parked)
            attempt.symlink_to(parked)
        else:
            # A byte-for-byte twin with a different root inode: no symlink check
            # could tell it from the certified original.
            _shutil.copytree(attempt, parked, symlinks=True)
            attempt.rename(attempt.parent / "original")
            parked.rename(attempt)

    # Below the semantic owner and above the syscall: the strict reacquisition
    # and the attempt-root identity check have already run, the descriptor is
    # open, and these are the two destructive transitions that remain.
    outcomes: list[tuple[str, bool, str]] = []
    real_member = qstore.remove_released_attempt_member
    real_unlink = qstore._unlink_certified_file
    real_remove_directory = qstore._remove_certified_directory

    def observed_member(paths_arg, attempt_root, member_name, **kwargs):
        result = real_member(paths_arg, attempt_root, member_name, **kwargs)
        outcomes.append((member_name, result[0], result[1]))
        return result

    def raced_unlink(parent_fd, name):
        perform_swap()
        return real_unlink(parent_fd, name)

    def raced_remove_directory(*args, **kwargs):
        perform_swap()
        return real_remove_directory(*args, **kwargs)

    qstore.remove_released_attempt_member = observed_member
    qstore._unlink_certified_file = raced_unlink
    qstore._remove_certified_directory = raced_remove_directory
    try:
        assert p4d._run(config, "storage", "cleanup", "--tier", "safe", "--apply") == 0
    finally:
        qstore.remove_released_attempt_member = real_member
        qstore._unlink_certified_file = real_unlink
        qstore._remove_certified_directory = real_remove_directory

    assert fired, "the race never fired"
    assert outcomes, "no released action reached the P7 mutation boundary"
    assert outcomes[0][1] is True, outcomes
    later = outcomes[1:]
    assert later, "the plan had only one released action, so nothing raced the swap"
    for name, removed, why in later:
        assert removed is False, (name, why)
        assert (
            "different filesystem object" in why or "namespace is unresolved" in why
        ), (name, why)

    # Nothing the replacement holds was touched under the original's authority.
    if swap == "same_shaped_directory":
        surviving = sorted(item.name for item in attempt.iterdir())
        for name, _removed, _why in outcomes:
            assert name in surviving, (name, surviving)
    else:
        # The symlink points back at the original directory, so the only member
        # missing from it is the one whose own mutation legitimately completed.
        surviving = sorted(item.name for item in parked.iterdir())
        for name, _removed, _why in later:
            assert name in surviving, (name, surviving)


def test_a_released_action_refuses_when_the_root_identity_changed(tmp_path: Path):
    """R26-A: a root replaced *before* the fd-relative mutation is refused.

    The complement of the race above. Here the substitution happens before the
    owner re-acquires the namespace, so the identity it observes does not match
    the one the certification was performed against, and the action refuses
    instead of acting on the replacement.
    """

    import shutil as _shutil

    from mdstats.training_data.qualification.store import (
        remove_released_attempt_member,
    )

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    snapshot, paths, view = _released_scratch_view(config)
    attempt = view.path.parent
    parked = attempt.parent / "parked"
    _shutil.copytree(attempt, parked, symlinks=True)
    attempt.rename(attempt.parent / "original")
    parked.rename(attempt)

    removed, why = remove_released_attempt_member(
        paths,
        attempt,
        view.path.name,
        expected_root_identity=view.root_identity,
        certified_nodes=[
            {"path": view.path.name, "kind": "directory"},
            *(
                {"path": f"{view.path.name}/{item.path}", "kind": item.kind}
                for item in view.certified_nodes
            ),
        ],
    )
    assert removed is False
    assert "different filesystem object" in why, why
    assert list((attempt / view.path.name).rglob("*")), "the replacement was emptied"


def test_released_mutation_refuses_without_the_directory_descriptor_primitives(
    tmp_path: Path, monkeypatch
):
    """R26-A: an unsupported platform retains rather than falling back.

    If the no-follow/dir-fd boundary is unavailable there is no way to carry the
    authenticated attempt root through to the destructive syscall, and the
    accepted answer is to refuse - never to reach for absolute-path traversal.
    """

    from mdstats.training_data.qualification import store as qstore

    config, _workspace, _harness = _released_attempt_campaign(tmp_path)
    _snapshot_before, paths, view = _released_scratch_view(config)
    monkeypatch.setattr(qstore, "dir_fd_mutation_supported", lambda: False)

    removed, why = qstore.remove_released_attempt_member(
        paths,
        view.path.parent,
        view.path.name,
        expected_root_identity=view.root_identity,
        certified_nodes=[{"path": view.path.name, "kind": "directory"}],
    )
    assert removed is False
    assert "retained rather than removed by pathname" in why, why
    assert list(view.path.rglob("*")), "scratch was removed on an unsupported platform"


def test_a_stale_handle_at_the_open_seam_is_unresolved_not_absent(tmp_path: Path):
    """R24-1: `ESTALE` at the real open seam is ambiguity, never absence."""

    import errno

    config, _workspace, harness = _released_attempt_campaign(tmp_path)
    checkpoints = _published_checkpoints(config, harness)
    attempt = _released_attempt_root(config)

    real_os_open = os.open

    def stale_open(name, *args, **kwargs):
        if isinstance(name, str) and name == attempt.name:
            raise OSError(errno.ESTALE, "Stale file handle", name)
        return real_os_open(name, *args, **kwargs)

    os.open = stale_open
    try:
        _assert_p7_ambiguity_blocks_everything(config, checkpoints)
        assert p4d._run(config, "storage", "report") == 0
    finally:
        os.open = real_os_open
    _assert_p7_repair_restores_planning(config)


def test_the_released_root_locator_survives_a_workspace_relocation(tmp_path: Path):
    """R24-2: the durable locator is workspace-portable, not an absolute path."""

    import shutil as _shutil

    config, workspace, _harness = _released_attempt_campaign(tmp_path)
    before, _paths = _snapshot(config)
    reclaimable_before = {
        view.artifact_id
        for view in before.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    }
    assert reclaimable_before

    moved = tmp_path / "relocated-workspace"
    _shutil.copytree(workspace, moved, symlinks=True)
    relocated_config = tmp_path / "relocated.toml"
    relocated_config.write_text(
        config.read_text(encoding="utf-8").replace(str(workspace), str(moved)),
        encoding="utf-8",
    )

    after, _paths2 = _snapshot(relocated_config)
    reclaimable_after = {
        view.artifact_id
        for view in after.views
        if view.artifact_id.startswith("p7:attempt_scratch:") and view.safe_reclaimable
    }
    assert reclaimable_after == reclaimable_before, (
        "relocating the workspace changed released-attempt authority"
    )


