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


def test_dedup_frees_physical_bytes_when_the_last_alias_disappears(tmp_path: Path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        record_post_selection_run_members,
    )

    config, _workspace, _harness = _historical_campaign(tmp_path)
    snapshot, paths = _snapshot(config)
    eligible = [item for item in archive_candidates(snapshot) if item.eligible]
    assert eligible
    run_root = Path(eligible[0].path)

    payload = b"duplicate" * 4096
    first = run_root / "checkpoints" / "dup-a.bin"
    second = run_root / "checkpoints" / "dup-b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    record_post_selection_run_members(run_root)

    assert p4d._run(config, "storage", "deduplicate", "--apply") == 0
    assert first.stat().st_ino == second.stat().st_ino
    assert first.stat().st_nlink == 2
    assert not (open_storage_control_plane_readonly(paths).root / "content-store").exists()

    first.unlink()
    assert second.stat().st_nlink == 1
    second.unlink()
    record_post_selection_run_members(run_root)
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

        real_remove = executor_mod.remove_durably
        removed: list[Path] = []

        def failing_remove(path: Path) -> bool:
            if len(removed) >= 2:
                raise RuntimeError("injected interruption after a strict subset")
            removed.append(path)
            return real_remove(path)

        executor_mod.remove_durably = failing_remove
        storage_commands.remove_durably = failing_remove
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
