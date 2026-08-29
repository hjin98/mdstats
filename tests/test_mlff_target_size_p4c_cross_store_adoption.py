"""P4-C acceptance: cross-store adoption of authenticated P3 execution heads,
the section 6.2 recovery matrix, the frozen P3 -> CampaignStore -> STOR lock
ordering, and the storage retention fence that protects the reconciliation
frontier.

Every case runs against a real ``CampaignStore`` SQLite file and the real P3
resolver/reconciler from ``target_size_execution``.  The storage race runs
through the real ``CampaignOwnershipBoundary`` destructive authorization that
production cleanup consumes, not a test-local flag.
"""

from __future__ import annotations

import ast
import json
import multiprocessing
import time
from pathlib import Path

import pytest

import tests.test_mlff_target_size_execution_p3e as p3e
from tests.test_mlff_target_size_p3a9_head_pointer_reconciliation import (
    _env,
    _execute_boundary,
    _publish_head_file,
)

from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import digest
from mdstats.training_data.storage_accounting import CampaignOwnershipBoundary
from mdstats.training_data.campaign_target_size_adoption import (
    TargetSizeAdoptionCorruptionError,
    TargetSizeScientificIdentityError,
    adopt_reconciled_execution_head,
    load_adopted_execution_head,
    reconcile_and_adopt_target_size_head,
)
from mdstats.training_data.campaign_target_size_retention import (
    build_target_size_retention_fence,
    retention_fence_for_revision,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignConflictError,
    TargetSizeCampaignState,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    load_target_size_campaign_revision,
)
from mdstats.training_data.campaign_target_size_cutover import (
    begin_target_size_cutover,
    bind_current_target_size_authorities,
    complete_target_size_cutover,
)
from mdstats.training_data.campaign_target_size_view import (
    build_target_size_result_view,
    write_target_size_result_view,
)
from mdstats.training_data.target_size_execution import (
    CURRENT_HEAD_FILENAME,
    TargetSizeExecutionHead,
    apply_complete_boundary_batch,
    commit_target_size_boundary_batch,
    load_current_execution_head,
    persist_complete_boundary_batch,
    reconcile_target_size_screen_root,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


def _campaign(tmp_path: Path, env) -> tuple[CampaignStore, object]:
    """A real campaign store already cut over and bound to this screen."""

    store = CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    aggregate = env["aggregate"]
    transitioning = begin_target_size_cutover(store)
    bound = bind_current_target_size_authorities(
        store,
        transitioning,
        frame_authority_digest=aggregate.frame_authority_digest,
        neutral_statistical_base_digest=aggregate.neutral_statistical_base_digest,
        split_exclusion_digest=digest({"fixture": "split-exclusion"}),
        policy_digest=aggregate.policy.content_digest,
        experiment_definition_digest=aggregate.definition.content_digest,
        aggregate_digest=aggregate.content_digest,
    )
    current = complete_target_size_cutover(store, bound)
    screen_active = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
        expected=current.expectation(),
        successor=TargetSizeCampaignState(
            regime=TargetSizeRegime.CURRENT,
            generation=current.state.generation,
            lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
            attempt="attempt-1",
            frame_authority_digest=current.state.frame_authority_digest,
            neutral_statistical_base_digest=(
                current.state.neutral_statistical_base_digest
            ),
            split_exclusion_digest=current.state.split_exclusion_digest,
            policy_digest=current.state.policy_digest,
            experiment_definition_digest=current.state.experiment_definition_digest,
            aggregate_digest=current.state.aggregate_digest,
            execution_context_digest=env["context"].content_digest,
            common_preparation_digest=env["common"].content_digest,
            screen_window_digest=env["window"].content_digest,
            execution_root=env["root"].name,
        ),
    ).revision
    return store, screen_active


# --- Recovery matrix: crash before P3 immutable publication -----------------


def test_p4c_recovery_crash_before_publication_leaves_campaign_unchanged(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_pre_publication")
    store, revision = _campaign(tmp_path, env)
    try:
        after, head = reconcile_and_adopt_target_size_head(
            store, revision, root=env["root"], authority=env["authority"]
        )
        assert head is None
        assert after == revision
        assert after.state.adopted_execution_head_digest is None
    finally:
        store.close()


# --- Recovery matrix: complete batch durable, head absent -------------------


def test_p4c_recovery_complete_batch_without_head_is_reconciled_then_adopted(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_batch_no_head")
    store, revision = _campaign(tmp_path, env)
    try:
        batch = _execute_boundary(env, tmp_path, env["aggregate"].reducer_state, 1)
        persist_complete_boundary_batch(env["root"], batch)
        assert not (env["root"] / CURRENT_HEAD_FILENAME).is_file()

        after, head = reconcile_and_adopt_target_size_head(
            store, revision, root=env["root"], authority=env["authority"]
        )
        assert head is not None
        assert head.batch_digest == batch.content_digest
        assert after.state.adopted_execution_head_digest == head.content_digest
        assert after.state.adopted_reducer_state_digest == (
            head.post_state.content_digest
        )
        assert after.sequence == revision.sequence + 1
    finally:
        store.close()


# --- Recovery matrix: durable successor head with a stale P3 pointer --------


def test_p4c_recovery_stale_pointer_successor_is_reconciled_then_adopted(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_stale_pointer")
    store, revision = _campaign(tmp_path, env)
    try:
        definition = env["aggregate"].definition
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], definition, state0, batch0
        )
        adopted0 = adopt_reconciled_execution_head(store, revision, head0)

        # P3 publishes a durable successor but its local pointer stays stale.
        batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
        persist_complete_boundary_batch(env["root"], batch1)
        post1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
        head1 = TargetSizeExecutionHead(
            parent_head_digest=head0.content_digest,
            batch_digest=batch1.content_digest,
            pre_state_digest=head0.post_state.content_digest,
            post_state_digest=post1.content_digest,
            pre_state=head0.post_state,
            post_state=post1,
        )
        _publish_head_file(env["root"], head1)
        assert (
            load_current_execution_head(env["root"]).content_digest
            == head0.content_digest
        )

        # SQLite is behind P3: reconcile repairs the pointer, then the campaign
        # CAS-adopts the exact successor under the same canonical generation.
        after, head = reconcile_and_adopt_target_size_head(
            store, adopted0, root=env["root"], authority=env["authority"]
        )
        assert head.content_digest == head1.content_digest
        assert after.state.adopted_execution_head_digest == head1.content_digest
        assert after.state.generation == adopted0.state.generation
        assert after.state.attempt == adopted0.state.attempt
    finally:
        store.close()


# --- Recovery matrix: P3 ahead of SQLite adopts without rerunning work ------


def test_p4c_recovery_sqlite_behind_p3_adopts_without_rerunning_science(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_sqlite_behind")
    store, revision = _campaign(tmp_path, env)
    try:
        definition = env["aggregate"].definition
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], definition, state0, batch0
        )
        completions = sorted((env["root"] / "completions").rglob("*.json"))
        assert completions
        fingerprint = {path: path.stat().st_mtime_ns for path in completions}

        after, head = reconcile_and_adopt_target_size_head(
            store, revision, root=env["root"], authority=env["authority"]
        )
        assert head.content_digest == head0.content_digest
        assert after.state.adopted_execution_head_digest == head0.content_digest
        # No completed cell was rewritten by the adoption.
        assert {path: path.stat().st_mtime_ns for path in completions} == fingerprint

        # Re-adopting the identity already held is a no-op, not a new revision.
        assert adopt_reconciled_execution_head(store, after, head0) == after
    finally:
        store.close()


# --- Recovery matrix: SQLite references missing/corrupt P3 head -------------


def test_p4c_recovery_missing_referenced_head_is_hard_corruption(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_missing_head")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)
        resolver = env["authority"].resolver
        assert load_adopted_execution_head(resolver, adopted).content_digest == (
            head0.content_digest
        )

        resolver.head_path(head0.content_digest).unlink()
        with pytest.raises(TargetSizeAdoptionCorruptionError) as excinfo:
            load_adopted_execution_head(resolver, adopted)
        assert "cannot be rebuilt from campaign state" in str(excinfo.value)
    finally:
        store.close()


def test_p4c_recovery_corrupt_referenced_head_is_hard_corruption(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_corrupt_head")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)
        resolver = env["authority"].resolver
        path = resolver.head_path(head0.content_digest)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["batch_digest"] = digest({"fixture": "tampered-batch"})
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(TargetSizeAdoptionCorruptionError):
            load_adopted_execution_head(resolver, adopted)
    finally:
        store.close()


# --- current_head.json is never campaign authority --------------------------


def test_p4c_current_head_pointer_is_not_campaign_authority(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_pointer_authority")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)
        resolver = env["authority"].resolver

        # Deleting the rebuildable local pointer cannot invalidate the campaign
        # adoption, because the campaign bound the immutable head digest.
        (env["root"] / CURRENT_HEAD_FILENAME).unlink()
        assert load_adopted_execution_head(resolver, adopted).content_digest == (
            head0.content_digest
        )

        # Forging the pointer cannot change what the campaign adopted either.
        (env["root"] / CURRENT_HEAD_FILENAME).write_text(
            json.dumps({"content_digest": digest({"fixture": "forged"})}),
            encoding="utf-8",
        )
        reloaded = load_target_size_campaign_revision(store)
        assert reloaded.state.adopted_execution_head_digest == head0.content_digest
    finally:
        store.close()


def test_p4c_head_from_a_different_experiment_identity_is_rejected(tmp_path: Path):
    """Equality of a head digest never substitutes for scientific identity: a
    head whose reducer states bind a different P2 experiment cannot be adopted."""

    env = _env(tmp_path, root_name="screen_identity")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )

        # A fresh generation bound to a different P2 experiment definition.
        foreign = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
            expected=revision.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=revision.state.generation + 1,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                frame_authority_digest=revision.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    revision.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=revision.state.split_exclusion_digest,
                policy_digest=revision.state.policy_digest,
                experiment_definition_digest=digest({"fixture": "other-experiment"}),
                aggregate_digest=revision.state.aggregate_digest,
                execution_context_digest=env["context"].content_digest,
                common_preparation_digest=env["common"].content_digest,
                screen_window_digest=env["window"].content_digest,
                execution_root=env["root"].name,
            ),
        ).revision

        with pytest.raises(TargetSizeScientificIdentityError) as excinfo:
            adopt_reconciled_execution_head(store, foreign, head0)
        assert "different P2 experiment definition" in str(excinfo.value)
        assert load_target_size_campaign_revision(store) == foreign
    finally:
        store.close()


def test_p4c_head_from_a_different_execution_context_is_rejected(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_context_identity")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        foreign = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
            expected=revision.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=revision.state.generation + 1,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                frame_authority_digest=revision.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    revision.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=revision.state.split_exclusion_digest,
                policy_digest=revision.state.policy_digest,
                experiment_definition_digest=(
                    revision.state.experiment_definition_digest
                ),
                aggregate_digest=revision.state.aggregate_digest,
                execution_context_digest=digest({"fixture": "other-context"}),
                common_preparation_digest=env["common"].content_digest,
                screen_window_digest=env["window"].content_digest,
                execution_root=env["root"].name,
            ),
        ).revision

        with pytest.raises(TargetSizeScientificIdentityError) as excinfo:
            adopt_reconciled_execution_head(store, foreign, head0)
        assert "different P3 execution context" in str(excinfo.value)
    finally:
        store.close()


# --- Recovery matrix: derived view missing after a committed transition -----


def test_p4c_recovery_missing_derived_view_is_rebuilt_without_rolling_back(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_view")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)
        resolver = env["authority"].resolver

        view_path = tmp_path / "results" / "target-size.json"
        first = write_target_size_result_view(view_path, adopted, resolver=resolver)
        assert first["authoritative"] is False
        view_path.unlink()

        reloaded = load_target_size_campaign_revision(store)
        assert reloaded == adopted
        rebuilt = write_target_size_result_view(view_path, reloaded, resolver=resolver)
        assert rebuilt == first
        assert rebuilt["adopted_execution_head_digest"] == head0.content_digest
    finally:
        store.close()


# --- Stale/generation races return typed conflicts, P3 history untouched ----


def test_p4c_stale_generation_writer_cannot_mutate_or_touch_p3_history(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_stale_writer")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)

        p3_before = {
            path: path.read_bytes()
            for path in sorted(env["root"].rglob("*.json"))
        }
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
            expected=adopted.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=adopted.state.generation + 1,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
                frame_authority_digest=adopted.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    adopted.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=adopted.state.split_exclusion_digest,
                policy_digest=adopted.state.policy_digest,
                experiment_definition_digest=(
                    adopted.state.experiment_definition_digest
                ),
                aggregate_digest=adopted.state.aggregate_digest,
            ),
        )

        # The pre-adoption revision belongs to the replaced generation, so its
        # writer can no longer mutate anything.
        with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
            adopt_reconciled_execution_head(
                store,
                revision,
                head0,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
            )
        assert excinfo.value.conflict_kind == "stale_generation"
        assert {
            path: path.read_bytes() for path in sorted(env["root"].rglob("*.json"))
        } == p3_before
    finally:
        store.close()


def test_p4c_two_same_generation_adopters_admit_one_successor(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_race_adopt")
    store_a = CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    store_a.close()
    store, revision = _campaign(tmp_path, env)
    writer_b = CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    try:
        definition = env["aggregate"].definition
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], definition, state0, batch0
        )
        seen_by_b = load_target_size_campaign_revision(writer_b)
        assert seen_by_b == revision

        adopt_reconciled_execution_head(store, revision, head0)
        with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
            adopt_reconciled_execution_head(
                writer_b,
                seen_by_b,
                head0,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
            )
        assert excinfo.value.conflict_kind == "stale_revision"
    finally:
        store.close()
        writer_b.close()


# --- Frozen cross-subsystem lock/transaction ordering -----------------------


def test_p4c_no_campaign_transaction_is_open_during_p3_reconciliation(
    tmp_path: Path, monkeypatch
):
    env = _env(tmp_path, root_name="screen_lock_order")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        persist_complete_boundary_batch(env["root"], batch0)

        import mdstats.training_data.target_size_execution.coordinator as coordinator

        observed: list[bool] = []
        real = coordinator.reconcile_target_size_screen_root

        def watching(root, authority):
            observed.append(store._connect().in_transaction)
            return real(root, authority)

        monkeypatch.setattr(
            coordinator, "reconcile_target_size_screen_root", watching
        )
        after, head = reconcile_and_adopt_target_size_head(
            store, revision, root=env["root"], authority=env["authority"]
        )
        assert head is not None
        assert observed == [False]
        assert after.state.adopted_execution_head_digest == head.content_digest
    finally:
        store.close()


def test_p4c_no_target_size_transaction_body_nests_reconciliation_or_cleanup():
    """Structural proof of section 6.3: nothing slow or destructive runs inside
    a campaign write transaction."""

    forbidden = {
        "reconcile_target_size_screen_root",
        "reconcile_and_adopt_target_size_head",
        "commit_target_size_boundary_batch",
        "record_candidate_boundary_outcome",
        "_cleanup_remove",
        "deduplicate_immutable_files",
        "create_cold_archive",
        "restore_cold_archive",
        "rmtree",
        "unlink",
    }
    for name in (
        "campaign_target_size_state.py",
        "campaign_target_size_cutover.py",
        "campaign_target_size_adoption.py",
        "campaign_target_size_retention.py",
    ):
        tree = ast.parse((_TRAINING_DATA / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            uses_transaction = any(
                "exclusive_transaction" in ast.dump(item.context_expr)
                for item in node.items
            )
            if not uses_transaction:
                continue
            called = {
                inner.func.attr if isinstance(inner.func, ast.Attribute) else
                (inner.func.id if isinstance(inner.func, ast.Name) else "")
                for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
            }
            assert not (called & forbidden), (name, sorted(called & forbidden))


# --- Retention fence: the reconciliation frontier survives real cleanup -----


def _fence_for(store, tmp_path: Path):
    return build_target_size_retention_fence(
        store, tmp_path, publication_window_seconds=0.0
    )


def _boundary_for(store, tmp_path: Path) -> CampaignOwnershipBoundary:
    return CampaignOwnershipBoundary(
        tmp_path, retention_fence=_fence_for(store, tmp_path)
    )


def test_p4c_fence_protects_unadopted_head_and_batch_before_adoption(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_fence_unadopted")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        # Deliberately do NOT adopt: this is exactly the publication ->
        # reconciliation -> adoption window.
        assert (
            load_target_size_campaign_revision(store).state
            .adopted_execution_head_digest
            is None
        )
        boundary = _boundary_for(store, tmp_path)
        resolver = env["authority"].resolver
        for path in (
            resolver.head_path(head0.content_digest),
            resolver.batch_path(batch0.content_digest),
            env["root"],
            env["root"] / CURRENT_HEAD_FILENAME,
        ):
            authorized, detail = boundary.destructive_authorization(path)
            assert not authorized, path
            assert "target-size" in detail
    finally:
        store.close()


def test_p4c_fence_protects_the_full_completion_and_snapshot_ancestry(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_fence_ancestry")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        persist_complete_boundary_batch(env["root"], batch0)
        boundary = _boundary_for(store, tmp_path)

        checked = 0
        for subdirectory in (
            "completions",
            "trajectories",
            "materializations",
            "snapshots",
            "roles",
            "predictions",
            "metrics",
            "evaluation_artifacts",
            "continuations",
            "planned_rungs",
            "progress",
        ):
            directory = env["root"] / subdirectory
            if not directory.is_dir():
                continue
            for path in directory.rglob("*.json"):
                authorized, detail = boundary.destructive_authorization(path)
                assert not authorized, path
                checked += 1
        assert checked > 0
    finally:
        store.close()


def test_p4c_fence_releases_provably_unreachable_owned_residue(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_fence_residue")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        orphan = env["root"] / "trajectories" / f"{digest({'orphan': True})}.json"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_text(json.dumps({"schema": "orphan"}), encoding="utf-8")
        old = time.time() - 86_400
        import os as _os

        _os.utime(orphan, (old, old))

        boundary = _boundary_for(store, tmp_path)
        authorized, detail = boundary.destructive_authorization(orphan)
        assert authorized, detail
    finally:
        store.close()


def test_p4c_fence_retains_recent_evidence_that_could_still_be_referenced(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_fence_recent")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        just_published = env["root"] / "snapshots" / f"{digest({'fresh': True})}.json"
        just_published.parent.mkdir(parents=True, exist_ok=True)
        just_published.write_text(json.dumps({"schema": "fresh"}), encoding="utf-8")

        boundary = CampaignOwnershipBoundary(
            tmp_path,
            retention_fence=build_target_size_retention_fence(
                store, tmp_path, publication_window_seconds=3600.0
            ),
        )
        authorized, detail = boundary.destructive_authorization(just_published)
        assert not authorized
        assert "race publication and adoption" in detail
    finally:
        store.close()


def test_p4c_fence_never_grants_authority_outside_the_workspace(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_fence_external")
    store, revision = _campaign(tmp_path, env)
    external = tmp_path.parent / "external-input"
    external.mkdir(parents=True, exist_ok=True)
    try:
        boundary = _boundary_for(store, tmp_path)
        authorized, detail = boundary.destructive_authorization(external)
        assert not authorized
        assert "outside the campaign workspace" in detail

        escape = env["root"] / "escape"
        escape.symlink_to(external, target_is_directory=True)
        authorized, detail = boundary.destructive_authorization(escape / "child")
        assert not authorized
    finally:
        store.close()


def _cleanup_race_child(workspace_text: str, targets: list[str], queue) -> None:
    """A separate process running real STOR destructive authorization."""

    store = CampaignStore(Path(workspace_text) / ".mdstats" / "campaign.sqlite3")
    try:
        boundary = CampaignOwnershipBoundary(
            Path(workspace_text),
            retention_fence=build_target_size_retention_fence(
                store, Path(workspace_text), publication_window_seconds=0.0
            ),
        )
        deleted: list[str] = []
        for target in targets:
            path = Path(target)
            authorized, _ = boundary.destructive_authorization(path)
            if authorized and path.is_file():
                path.unlink()
                deleted.append(target)
        queue.put(deleted)
    finally:
        store.close()


def test_p4c_cleanup_racing_publication_and_adoption_deletes_nothing_adoptable(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_cleanup_race")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        definition = env["aggregate"].definition
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], definition, state0, batch0
        )
        adopted = adopt_reconciled_execution_head(store, revision, head0)

        # A successor is published while SQLite still references head0. This is
        # the exact window a cleanup pass must not delete into.
        batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
        persist_complete_boundary_batch(env["root"], batch1)
        post1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
        head1 = TargetSizeExecutionHead(
            parent_head_digest=head0.content_digest,
            batch_digest=batch1.content_digest,
            pre_state_digest=head0.post_state.content_digest,
            post_state_digest=post1.content_digest,
            pre_state=head0.post_state,
            post_state=post1,
        )
        _publish_head_file(env["root"], head1)

        targets = [str(path) for path in sorted(env["root"].rglob("*.json"))]
        old = time.time() - 86_400
        import os as _os

        for target in targets:
            _os.utime(target, (old, old))
        assert targets

        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        child = context.Process(
            target=_cleanup_race_child, args=(str(tmp_path), targets, queue)
        )
        child.start()
        child.join(timeout=300)
        assert child.exitcode == 0
        deleted = queue.get(timeout=30)
        assert deleted == [], deleted

        # The unadopted successor is still adoptable after the cleanup attempt.
        after, head = reconcile_and_adopt_target_size_head(
            store, adopted, root=env["root"], authority=env["authority"]
        )
        assert head.content_digest == head1.content_digest
        assert after.state.adopted_execution_head_digest == head1.content_digest
    finally:
        store.close()


def test_p4c_production_cleanup_owner_consumes_the_retention_fence(tmp_path: Path):
    """The fence is honoured by the real production cleanup path, not only by a
    directly constructed boundary."""

    from mdstats.training_data._campaign_cli_core import (
        CampaignPaths,
        _CampaignCleanupReport,
        _campaign_ownership_boundary,
        _cleanup_remove,
    )

    env = _env(tmp_path, root_name="screen_production_cleanup")
    store, revision = _campaign(tmp_path, env)
    try:
        state0 = env["aggregate"].reducer_state
        batch0 = _execute_boundary(env, tmp_path, state0, 1)
        head0 = commit_target_size_boundary_batch(
            env["root"], env["aggregate"].definition, state0, batch0
        )
        resolver = env["authority"].resolver
        head_path = resolver.head_path(head0.content_digest)
        batch_path = resolver.batch_path(batch0.content_digest)

        config = tmp_path / "campaign.toml"
        config.write_text("", encoding="utf-8")
        cfg = {"campaign": {"workspace": str(tmp_path)}, "cleanup": {"stale_age_hours": 0.25}}
        paths = CampaignPaths.from_config(config, cfg)
        boundary = _campaign_ownership_boundary(cfg, paths, store)
        report = _CampaignCleanupReport(
            phase="p4c-retention-fence", dry_run=False, ownership_boundary=boundary
        )

        import os as _os

        old = time.time() - 86_400
        for path in (head_path, batch_path):
            _os.utime(path, (old, old))
            _cleanup_remove(report, path, reason="test destructive attempt")

        assert report.actions == []
        assert len(report.skipped) == 2
        assert all("target-size" in item for item in report.skipped)
        assert head_path.is_file()
        assert batch_path.is_file()
    finally:
        store.close()


def test_p4c_fence_is_inert_when_no_current_generation_owns_a_root(tmp_path: Path):
    store = CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    try:
        fence = build_target_size_retention_fence(store, tmp_path)
        assert not fence.is_active
        assert fence.protects(tmp_path / "anything") == (False, "")
        boundary = CampaignOwnershipBoundary(tmp_path, retention_fence=fence)
        authorized, _ = boundary.destructive_authorization(tmp_path / "scratch.json")
        assert authorized
    finally:
        store.close()


def test_p4c_transitioning_campaign_protects_its_whole_execution_root(
    tmp_path: Path,
):
    env = _env(tmp_path, root_name="screen_transitioning")
    store = CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    try:
        transitioning = begin_target_size_cutover(store)
        moved = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.BIND_AUTHORITIES,
            expected=transitioning.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.TRANSITIONING,
                generation=transitioning.state.generation,
                lifecycle=TargetSizeLifecycle.AWAITING_AUTHORITIES,
                execution_root=env["root"].name,
            ),
        ).revision
        fence = retention_fence_for_revision(moved, tmp_path)
        assert fence.protect_everything
        protected, detail = fence.protects(env["root"] / "anything.json")
        assert protected
        assert "destructive target-size cutover" in detail
    finally:
        store.close()


def test_p4c_real_runtime_first_publication_retention_race(
    tmp_path: Path, monkeypatch
):
    """P4-C2 mandatory acceptance: drive the real select-target-size runtime,
    intercept real initialize_target_size_screen with a synchronization wrapper,
    observe the actual root argument passed by production runtime, prove SQLite
    is still in AUTHORITIES_BOUND with no execution_root, and prove an independent
    process running real STOR cleanup is denied deletion of the runtime-created root
    and freshly published P3 files. Then resume and complete the screen.
    """
    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
    import mdstats.training_data.target_size_execution as p3

    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0

    real_init = p3.initialize_target_size_screen
    race_checked = False

    def synchronized_init(root, aggregate, context, common):
        nonlocal race_checked
        window = real_init(root, aggregate, context, common)
        observed_root = Path(root)

        # 1. Assert CampaignStore is still AUTHORITIES_BOUND, no attempt, no execution_root:
        store_check = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
        try:
            persisted = load_target_size_campaign_revision(store_check)
            assert persisted.state.lifecycle is TargetSizeLifecycle.AUTHORITIES_BOUND
            assert persisted.state.execution_root is None
            assert persisted.state.adopted_execution_head_digest is None
        finally:
            store_check.close()

        # 2. Derive targets from the actual runtime observed root and published files:
        published_files = sorted(observed_root.rglob("*.json"))
        assert published_files, "P3 screen initialization produced no files"
        targets = [str(observed_root)] + [str(p) for p in published_files]

        # 3. Independent child process runs real STOR destructive cleanup authorization:
        mp_context = multiprocessing.get_context("spawn")
        queue = mp_context.Queue()
        child = mp_context.Process(
            target=_cleanup_race_child, args=(str(workspace), targets, queue)
        )
        child.start()
        child.join(timeout=300)
        assert child.exitcode == 0
        deleted = queue.get(timeout=30)
        assert deleted == [], f"STOR deleted protected first-publication files: {deleted}"

        # 4. Verify all published files and root directory remain intact:
        for p in published_files:
            assert p.is_file(), f"File was deleted: {p}"
        assert observed_root.is_dir()

        race_checked = True
        return window

    monkeypatch.setattr(p3, "initialize_target_size_screen", synchronized_init)
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
    assert race_checked, "Real runtime first-publication race was not executed"

    # Verify campaign reached terminal state successfully after the race:
    store_final = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        final_revision = load_target_size_campaign_revision(store_final)
        assert final_revision.state.lifecycle in (
            TargetSizeLifecycle.TERMINAL_SELECTED,
            TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
        )
    finally:
        store_final.close()


def test_p4c_canonical_root_owner_uniqueness():
    """P4-C2 structural requirement: runtime and retention must both import and use
    the single canonical root owner from campaign_target_size_paths, with no local
    duplicated path formulas or constants."""
    from mdstats.training_data.campaign_target_size_paths import (
        target_size_execution_root,
        target_size_execution_root_locator,
        TARGET_SIZE_EXECUTION_ROOT_NAME,
    )

    pkg_dir = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"
    runtime_text = (pkg_dir / "campaign_target_size_runtime.py").read_text(encoding="utf-8")
    retention_text = (pkg_dir / "campaign_target_size_retention.py").read_text(encoding="utf-8")

    # Both must import from campaign_target_size_paths:
    assert "from .campaign_target_size_paths import" in runtime_text
    assert "target_size_execution_root" in runtime_text
    assert "from .campaign_target_size_paths import target_size_execution_root" in retention_text

    # Retention must not hardcode TARGET_SIZE_EXECUTION_ROOT_NAME:
    assert 'TARGET_SIZE_EXECUTION_ROOT_NAME = "target-size"' not in retention_text


