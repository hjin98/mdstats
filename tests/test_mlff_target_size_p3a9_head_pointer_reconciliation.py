"""P3A9 acceptance suite: stale-head successor reconciliation repair,
deterministic scientific replay, fork/orphan rejection, CAS lock, and process-level concurrency closure."""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
import tests.test_mlff_target_size_execution_p3e as p3e
from mdstats.training_data.eval2 import Eval2NumericalEvaluationError, Eval2TargetMetricRecord
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    CURRENT_HEAD_FILENAME,
    SCREEN_WINDOW_FILENAME,
    TargetSizeBoundarySnapshot,
    TargetSizeCandidateMaterialization,
    TargetSizeCandidateOutcome,
    TargetSizeCandidateTrajectory,
    TargetSizeCellCompletionRecord,
    TargetSizeCompleteBoundaryBatch,
    TargetSizeContinuationRequest,
    TargetSizeExecutionHead,
    TargetSizeExecutionResolver,
    TargetSizeRestartAuthority,
    TargetSizeScreenWindow,
    apply_complete_boundary_batch,
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    commit_target_size_boundary_batch,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initial_target_size_continuation_request,
    initialize_target_size_screen,
    load_current_execution_head,
    materialize_target_size_candidate,
    persist_complete_boundary_batch,
    promote_target_size_boundary_snapshot,
    reconcile_target_size_screen_root,
    record_candidate_boundary_outcome,
    resolve_target_size_candidate_for_resume,
    run_target_size_direct_boundary_inference,
    run_target_size_eval2_reduction,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    translate_target_size_eval2_failure,
    translate_target_size_train2_failure,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_execution.persistence import (
    publish_immutable_json_create_or_verify,
    publish_mutable_json_atomic,
)
from mdstats.training_data.target_size_experiment import (
    NumericalFailureKind,
    ReducerStatus,
    TargetSizeBoundaryMetric,
    TargetSizeNumericalFailure,
)
from mdstats.training_data.train2_runtime import Train2NumericalFailureRecord, Train2RuntimePlan


def _env(tmp_path: Path, *, root_name: str = "screen"):
    return p3e._env(tmp_path, root_name=root_name)


def _publish_head_file(root_path: Path, head: TargetSizeExecutionHead) -> Path:
    head_path = root_path / "heads" / f"{head.content_digest}.json"
    publish_immutable_json_create_or_verify(
        head_path, head.to_dict(), deserializer=TargetSizeExecutionHead.from_dict
    )
    return head_path


def _execute_boundary(env, tmp_path: Path, state, boundary: int):
    definition = env["aggregate"].definition
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    b_epoch, eval_size, keys = requirements
    assert b_epoch == boundary
    completion_records = []
    for size, seed in keys:
        (
            trajectory,
            role,
            snapshot,
            completion_record,
            materialization,
            eval_artifact,
            pred_evidence,
            metric_record,
        ) = p3e._execute_candidate_boundary(env, tmp_path, size, seed, boundary)
        completion_records.append(completion_record)
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion_record,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
            planned_rung=p3e._rung_provenance(env, trajectory, boundary)[0],
            predecessor_continuation=p3e._rung_provenance(env, trajectory, boundary)[1],
            restart_authority=env["authority"],
        )
    batch = build_complete_boundary_batch(definition, state, completion_records)
    return batch


# ---------------------------------------------------------------------------
# Section 4.1: Focused crash / replay acceptance
# ---------------------------------------------------------------------------

# 1. complete boundary batch durable, immutable head absent -> existing unique-batch recovery succeeds
def test_p3a9_req1_complete_batch_durable_head_absent_recovery(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req1")
    state = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state, 1)
    persist_complete_boundary_batch(env["root"], batch0)

    # current_head.json does not exist, heads/ is empty
    assert not (env["root"] / CURRENT_HEAD_FILENAME).is_file()
    assert not (env["root"] / "heads").is_dir() or len(list((env["root"] / "heads").glob("*.json"))) == 0

    reconciled = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert reconciled is not None
    assert reconciled.batch_digest == batch0.content_digest
    assert (env["root"] / CURRENT_HEAD_FILENAME).is_file()
    assert (env["root"] / "heads" / f"{reconciled.content_digest}.json").is_file()


# 2. immutable successor head durable, current_head.json still on predecessor -> unique successor replays and pointer advances
def test_p3a9_req2_immutable_successor_head_durable_stale_pointer(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req2")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    # Commit boundary 1 cleanly
    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest

    # Run boundary 2, build batch1, publish immutable batch1 and immutable head1, but DO NOT update current_head.json
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1)

    # Verify stale pointer condition: current_head is still head0
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest
    assert (env["root"] / "heads" / f"{head1.content_digest}.json").is_file()

    # Reconcile: must discover unique successor head1, replay deterministically, and advance current_head.json to head1
    reconciled = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert reconciled is not None
    assert reconciled.content_digest == head1.content_digest
    assert load_current_execution_head(env["root"]).content_digest == head1.content_digest


# 3. stale pointer followed by multiple valid linear successors -> complete chain replays and pointer advances to unique tip
def test_p3a9_req3_stale_pointer_multiple_valid_linear_successors(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req3")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    # Commit boundary 1 cleanly
    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Step 2: publish batch1 and head1
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1)

    # Step 3: publish batch2 and head2
    batch2 = _execute_boundary(env, tmp_path, post_state1, 10)
    persist_complete_boundary_batch(env["root"], batch2)
    post_state2 = apply_complete_boundary_batch(definition, post_state1, batch2)
    head2 = TargetSizeExecutionHead(
        parent_head_digest=head1.content_digest,
        batch_digest=batch2.content_digest,
        pre_state_digest=post_state1.content_digest,
        post_state_digest=post_state2.content_digest,
        pre_state=post_state1,
        post_state=post_state2,
    )
    _publish_head_file(env["root"], head2)

    # current_head.json is still at head0
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest

    # Reconcile advances through head1 to head2
    reconciled = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert reconciled is not None
    assert reconciled.content_digest == head2.content_digest
    assert load_current_execution_head(env["root"]).content_digest == head2.content_digest


# 4. current_head.json missing with one valid chain -> pointer is rebuilt only after full replay
def test_p3a9_req4_current_head_missing_with_valid_chain(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req4")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    head1 = commit_target_size_boundary_batch(env["root"], definition, head0.post_state, batch1)

    # Remove current_head.json
    (env["root"] / CURRENT_HEAD_FILENAME).unlink()
    assert not (env["root"] / CURRENT_HEAD_FILENAME).is_file()

    reconciled = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert reconciled is not None
    assert reconciled.content_digest == head1.content_digest
    assert (env["root"] / CURRENT_HEAD_FILENAME).is_file()
    assert load_current_execution_head(env["root"]).content_digest == head1.content_digest


# 5. stale pointer with one corrupted successor -> reject and do not advance pointer
def test_p3a9_req5_stale_pointer_with_corrupted_successor_rejects(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req5")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Create successor batch and head, but tamper with head1's post_state_digest
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    tampered_post_state = replace(post_state1, active_candidate_sizes=())
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=tampered_post_state.content_digest,
        pre_state=head0.post_state,
        post_state=tampered_post_state,
    )
    _publish_head_file(env["root"], head1)

    with pytest.raises(mdstats.TrainingDataInputError):
        reconcile_target_size_screen_root(env["root"], env["authority"])

    # Verify pointer was NOT advanced
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest


# 6. stale pointer with two children from the same parent -> reject as fork
def test_p3a9_req6_stale_pointer_with_two_children_rejects_as_fork(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req6")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Create two different child heads claiming parent head0
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1_a = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1_a)

    head1_b = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch0.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=head0.post_state.content_digest,
        pre_state=head0.post_state,
        post_state=head0.post_state,
    )
    _publish_head_file(env["root"], head1_b)

    with pytest.raises(mdstats.TrainingDataInputError, match="Fork detected"):
        reconcile_target_size_screen_root(env["root"], env["authority"])


# 7. unrelated authenticated orphan head -> reject
def test_p3a9_req7_unrelated_authenticated_orphan_head_rejects(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req7")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Add an orphan head whose parent is "0"*64
    orphan_head = TargetSizeExecutionHead(
        parent_head_digest="0" * 64,
        batch_digest=batch0.content_digest,
        pre_state_digest=state0.content_digest,
        post_state_digest=head0.post_state.content_digest,
        pre_state=state0,
        post_state=head0.post_state,
    )
    _publish_head_file(env["root"], orphan_head)

    with pytest.raises(mdstats.TrainingDataInputError, match="Orphan head detected"):
        reconcile_target_size_screen_root(env["root"], env["authority"])


# 8. tampered parent/batch/pre-state/post-state relation -> reject through owning validator/reducer path
def test_p3a9_req8_tampered_relations_reject_through_owning_validator(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req8")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Successor with pre_state not matching head0's post_state
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch0.content_digest,
        pre_state_digest=state0.content_digest,  # refers to initial state rather than head0.post_state
        post_state_digest=head0.post_state.content_digest,
        pre_state=state0,
        post_state=head0.post_state,
    )
    _publish_head_file(env["root"], head1)

    with pytest.raises(mdstats.TrainingDataInputError, match="reducer-state discontinuity"):
        reconcile_target_size_screen_root(env["root"], env["authority"])


# 9. exact duplicate reconciliation/retry -> idempotent identical result
def test_p3a9_req9_duplicate_reconciliation_retry_idempotent(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_req9")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1)

    # First reconciliation advances pointer
    rec1 = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert rec1.content_digest == head1.content_digest

    # Duplicate reconciliation is idempotent
    rec2 = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert rec2.content_digest == head1.content_digest


# 10. fresh-process restart after repaired crash state yields same reducer state, active matrix/terminal state, and scientific outcome identity as uninterrupted execution
def test_p3a9_req10_fresh_process_restart_after_repaired_crash_state(tmp_path: Path) -> None:
    env_clean = _env(tmp_path / "clean", root_name="screen")
    env_crash = _env(tmp_path / "crash", root_name="screen")

    definition = env_clean["aggregate"].definition
    state0 = env_clean["aggregate"].reducer_state

    # 1. Uninterrupted run through boundary 1 and 2
    batch0_clean = _execute_boundary(env_clean, tmp_path / "clean", state0, 1)
    head0_clean = commit_target_size_boundary_batch(env_clean["root"], definition, state0, batch0_clean)
    batch1_clean = _execute_boundary(env_clean, tmp_path / "clean", head0_clean.post_state, 3)
    head1_clean = commit_target_size_boundary_batch(env_clean["root"], definition, head0_clean.post_state, batch1_clean)

    # 2. Crash run: commit boundary 1, build & persist boundary 2 batch and head, crash before updating current_head.json
    batch0_crash = _execute_boundary(env_crash, tmp_path / "crash", state0, 1)
    head0_crash = commit_target_size_boundary_batch(env_crash["root"], definition, state0, batch0_crash)
    batch1_crash = _execute_boundary(env_crash, tmp_path / "crash", head0_crash.post_state, 3)
    persist_complete_boundary_batch(env_crash["root"], batch1_crash)
    post_state1_crash = apply_complete_boundary_batch(definition, head0_crash.post_state, batch1_crash)
    head1_crash = TargetSizeExecutionHead(
        parent_head_digest=head0_crash.content_digest,
        batch_digest=batch1_crash.content_digest,
        pre_state_digest=head0_crash.post_state.content_digest,
        post_state_digest=post_state1_crash.content_digest,
        pre_state=head0_crash.post_state,
        post_state=post_state1_crash,
    )
    _publish_head_file(env_crash["root"], head1_crash)

    # Reconcile crashed screen
    reconciled_crash = reconcile_target_size_screen_root(env_crash["root"], env_crash["authority"])
    assert reconciled_crash is not None
    assert reconciled_crash.content_digest == head1_clean.content_digest
    assert reconciled_crash.post_state.content_digest == head1_clean.post_state.content_digest
    assert reconciled_crash.post_state.active_candidate_sizes == head1_clean.post_state.active_candidate_sizes
    assert reconciled_crash.post_state.status == head1_clean.post_state.status


# ---------------------------------------------------------------------------
# Section 4.2: Real-owner process-level concurrency acceptance
# ---------------------------------------------------------------------------

def _worker_commit(barrier, queue, root_path, definition, state, batch):
    try:
        barrier.wait(timeout=10)
        head = commit_target_size_boundary_batch(root_path, definition, state, batch)
        queue.put(("commit", head.content_digest, None))
    except Exception as e:
        queue.put(("commit", None, f"{type(e).__name__}: {e}"))


def _worker_reconcile(barrier, queue, root_path, authority, label="reconcile"):
    try:
        barrier.wait(timeout=10)
        head = reconcile_target_size_screen_root(root_path, authority)
        digest_val = head.content_digest if head is not None else None
        queue.put((label, digest_val, None))
    except Exception as e:
        queue.put((label, None, f"{type(e).__name__}: {e}"))


# Race A: Legitimate commit/retry versus reconciliation on the same stale-pointer successor
def test_p3a9_concurrency_race_a_commit_vs_reconcile(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_race_a")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    # Commit boundary 1 cleanly
    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest

    # Run boundary 2, build batch1, publish immutable batch1 and immutable head1, leave current_head.json pointing at head0
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1)
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest

    ctx = multiprocessing.get_context("fork")
    barrier = ctx.Barrier(2)
    queue = ctx.Queue()

    p_commit = ctx.Process(
        target=_worker_commit,
        args=(barrier, queue, env["root"], definition, head0.post_state, batch1),
    )
    p_reconcile = ctx.Process(
        target=_worker_reconcile,
        args=(barrier, queue, env["root"], env["authority"], "reconcile"),
    )

    try:
        p_commit.start()
        p_reconcile.start()

        p_commit.join(timeout=30)
        p_reconcile.join(timeout=30)

        assert not p_commit.is_alive(), "Worker commit timed out (possible deadlock)"
        assert not p_reconcile.is_alive(), "Worker reconcile timed out (possible deadlock)"
    finally:
        if p_commit.is_alive():
            p_commit.terminate()
            p_commit.join()
        if p_reconcile.is_alive():
            p_reconcile.terminate()
            p_reconcile.join()

    results = {}
    while not queue.empty():
        label, digest_val, err = queue.get_nowait()
        assert err is None, f"Worker {label} failed: {err}"
        results[label] = digest_val

    assert "commit" in results
    assert "reconcile" in results
    assert results["commit"] == head1.content_digest
    assert results["reconcile"] == head1.content_digest

    # Current head pointer resolves to head1
    curr = load_current_execution_head(env["root"])
    assert curr is not None
    assert curr.content_digest == head1.content_digest

    # Immutable head graph contains exactly head0 and head1
    heads_on_disk = {p.stem for p in (env["root"] / "heads").glob("*.json")}
    assert heads_on_disk == {head0.content_digest, head1.content_digest}

    # Third process reconciliation returns same head1
    fresh_rec = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert fresh_rec is not None
    assert fresh_rec.content_digest == head1.content_digest


# Race B: Concurrent reconcilers on the same stale-pointer root
def test_p3a9_concurrency_race_b_concurrent_reconcilers(tmp_path: Path) -> None:
    env = _env(tmp_path, root_name="screen_race_b")
    state0 = env["aggregate"].reducer_state
    definition = env["aggregate"].definition

    # Commit boundary 1 cleanly
    batch0 = _execute_boundary(env, tmp_path, state0, 1)
    head0 = commit_target_size_boundary_batch(env["root"], definition, state0, batch0)

    # Publish batch1 and head1, leave current_head.json at head0
    batch1 = _execute_boundary(env, tmp_path, head0.post_state, 3)
    persist_complete_boundary_batch(env["root"], batch1)
    post_state1 = apply_complete_boundary_batch(definition, head0.post_state, batch1)
    head1 = TargetSizeExecutionHead(
        parent_head_digest=head0.content_digest,
        batch_digest=batch1.content_digest,
        pre_state_digest=head0.post_state.content_digest,
        post_state_digest=post_state1.content_digest,
        pre_state=head0.post_state,
        post_state=post_state1,
    )
    _publish_head_file(env["root"], head1)
    assert load_current_execution_head(env["root"]).content_digest == head0.content_digest

    ctx = multiprocessing.get_context("fork")
    barrier = ctx.Barrier(2)
    queue = ctx.Queue()

    p_rec1 = ctx.Process(
        target=_worker_reconcile,
        args=(barrier, queue, env["root"], env["authority"], "rec1"),
    )
    p_rec2 = ctx.Process(
        target=_worker_reconcile,
        args=(barrier, queue, env["root"], env["authority"], "rec2"),
    )

    try:
        p_rec1.start()
        p_rec2.start()

        p_rec1.join(timeout=30)
        p_rec2.join(timeout=30)

        assert not p_rec1.is_alive(), "Worker rec1 timed out (possible deadlock)"
        assert not p_rec2.is_alive(), "Worker rec2 timed out (possible deadlock)"
    finally:
        if p_rec1.is_alive():
            p_rec1.terminate()
            p_rec1.join()
        if p_rec2.is_alive():
            p_rec2.terminate()
            p_rec2.join()

    results = {}
    while not queue.empty():
        label, digest_val, err = queue.get_nowait()
        assert err is None, f"Worker {label} failed: {err}"
        results[label] = digest_val

    assert "rec1" in results
    assert "rec2" in results
    assert results["rec1"] == head1.content_digest
    assert results["rec2"] == head1.content_digest

    # Current head pointer resolves to head1
    curr = load_current_execution_head(env["root"])
    assert curr is not None
    assert curr.content_digest == head1.content_digest

    # Immutable head graph contains exactly head0 and head1
    heads_on_disk = {p.stem for p in (env["root"] / "heads").glob("*.json")}
    assert heads_on_disk == {head0.content_digest, head1.content_digest}

    # Third process reconciliation returns same head1
    fresh_rec = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert fresh_rec is not None
    assert fresh_rec.content_digest == head1.content_digest
