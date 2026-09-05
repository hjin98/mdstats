"""Partial-boundary restart: active is not the same claim as unexecuted.

A production ``select-target-size`` restart entered boundary 1, retrained an
``(N, optimizer_seed)`` cell that had already been published by the interrupted
run, and only discovered the collision at publication:

.. code-block:: text

    TrainingDataInputError: Conflicting immutable progress record already
    exists for this logical cell.

The immutable progress guard was right.  The scheduler was wrong.  A boundary
that was interrupted before its complete matrix existed correctly leaves the P2
reducer at its pre-boundary state, so P2 still reports the whole boundary as
active - and the runtime read "active according to P2" as "not yet executed",
which those are not while a boundary is incomplete.

The repair is entirely on the scheduling side: durable per-cell progress is
authenticated through the one completion-record replay owner, recovered cells
are reused in exact P2 order, and only genuinely missing cells reach TRAIN2 and
EVAL2.  Nothing about immutable publication is relaxed - the conflict remains a
hard error, it simply stops being reachable by ordinary restart.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.target_size_execution import (
    TargetSizeCandidateOutcome,
    TargetSizeExecutionResolver,
    collect_boundary_cell_completion_records,
    derive_active_boundary_requirements,
    record_candidate_boundary_outcome,
    recover_authenticated_boundary_progress,
)

import tests.test_mlff_target_size_execution_p3e as p3e
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)


# ---------------------------------------------------------------------------
# Focused recovery evidence at the P3 owner
# ---------------------------------------------------------------------------


def _publish_cell(env, tmp_path: Path, size: int, seed: int, boundary: int):
    """Execute and publish one real cell through the accepted P3 owners."""

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
    planned_rung, predecessor = p3e._rung_provenance(env, trajectory, boundary)
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
        planned_rung=planned_rung,
        predecessor_continuation=predecessor,
        restart_authority=env["authority"],
    )
    return completion_record


def _first_boundary(env):
    requirements = derive_active_boundary_requirements(
        env["aggregate"].definition, env["aggregate"].reducer_state
    )
    assert requirements is not None
    boundary, _evaluation_size, keys = requirements
    return boundary, keys


def _root_inventory(root: Path) -> dict[str, int]:
    return {
        str(path.relative_to(root)): path.stat().st_size
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_valid_current_boundary_progress_is_recovered_and_creates_nothing(
    tmp_path: Path,
):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    size, seed = keys[0]
    published = _publish_cell(env, tmp_path, size, seed, boundary)

    before = _root_inventory(env["root"])
    recovered = recover_authenticated_boundary_progress(
        env["root"],
        env["window"],
        env["authority"],
        boundary_epoch=boundary,
        active_keys=keys,
    )
    after = _root_inventory(env["root"])

    assert list(recovered) == [(size, seed)]
    assert recovered[(size, seed)].content_digest == published.content_digest
    assert recovered[(size, seed)].outcome.content_digest == (
        published.outcome.content_digest
    )
    # Recovery is authentication, not execution: replaying the complete parent
    # graph must not mint a single new artifact byte.
    assert after == before


def test_absent_progress_for_an_active_key_is_work_not_corruption(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    recovered = recover_authenticated_boundary_progress(
        env["root"],
        env["window"],
        env["authority"],
        boundary_epoch=boundary,
        active_keys=keys,
    )
    assert set(recovered) == {keys[0]}
    missing = [key for key in keys if key not in recovered]
    assert missing == list(keys[1:])


def test_recovery_preserves_exact_p2_matrix_order(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    # Publish out of P2 order on purpose.
    for size, seed in reversed(keys):
        _publish_cell(env, tmp_path, size, seed, boundary)

    recovered = recover_authenticated_boundary_progress(
        env["root"],
        env["window"],
        env["authority"],
        boundary_epoch=boundary,
        active_keys=keys,
    )
    assert tuple(recovered) == tuple(keys)


def test_progress_outside_the_active_matrix_fails_closed(tmp_path: Path):
    """A durable cell P2 is not asking for is contradictory evidence."""

    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    # Both an inactive target size and a foreign optimizer seed present as the
    # same thing to the scheduler: a cell outside the exact active key set.
    with pytest.raises(TrainingDataInputError) as excinfo:
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys[1:],
        )
    assert "outside the" in str(excinfo.value)


def test_progress_from_a_foreign_screen_window_fails_closed(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    published = _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    resolver = TargetSizeExecutionResolver(env["root"])
    foreign_window_digest = "f" * 64
    foreign = TargetSizeCandidateOutcome(
        window_digest=foreign_window_digest,
        boundary_epoch=boundary,
        trajectory_digest=published.trajectory_digest,
        completion_record_digest=published.content_digest,
        outcome=published.outcome,
    )
    # Written at its own deterministic key, so only the screen identity is wrong.
    foreign_path = resolver.progress_path(
        foreign_window_digest,
        boundary,
        published.target_size,
        published.optimizer_seed,
    )
    foreign_path.write_text(
        json.dumps(foreign.to_dict(), sort_keys=True), encoding="utf-8"
    )

    with pytest.raises(TrainingDataInputError) as excinfo:
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys,
        )
    assert "different screen window" in str(excinfo.value)


def test_progress_filename_that_is_not_its_cell_key_fails_closed(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    progress_dir = env["root"] / "progress" / str(boundary)
    original = next(iter(progress_dir.glob("*.json")))
    (progress_dir / f"{'a' * 64}.json").write_bytes(original.read_bytes())

    with pytest.raises(TrainingDataInputError) as excinfo:
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys,
        )
    assert "deterministic cell key" in str(excinfo.value)


def test_progress_pointing_at_another_cells_completion_fails_closed(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    first = _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)
    second = _publish_cell(env, tmp_path, keys[1][0], keys[1][1], boundary)

    resolver = TargetSizeExecutionResolver(env["root"])
    path = resolver.progress_path(
        env["window"].content_digest,
        boundary,
        first.target_size,
        first.optimizer_seed,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["completion_record_digest"] = second.content_digest
    # Self-consistent on its face: only the reference is foreign.
    payload.pop("content_digest", None)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(TrainingDataInputError) as excinfo:
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys,
        )
    assert "different cells" in str(excinfo.value)


def test_progress_with_a_rewritten_outcome_fails_closed(tmp_path: Path):
    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    first = _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    resolver = TargetSizeExecutionResolver(env["root"])
    path = resolver.progress_path(
        env["window"].content_digest,
        boundary,
        first.target_size,
        first.optimizer_seed,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["outcome"]["target_force_rmse_mev_per_a"] = float(
        payload["outcome"]["target_force_rmse_mev_per_a"]
    ) + 1.0
    payload["outcome"].pop("content_digest", None)
    payload.pop("content_digest", None)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(TrainingDataInputError):
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys,
        )


@pytest.mark.parametrize(
    "subdirectory",
    [
        "trajectories",
        "materializations",
        "planned_rungs",
        "snapshots",
        "roles",
        "evaluation_artifacts",
        "predictions",
        "metrics",
    ],
)
def test_deep_parent_tamper_fails_before_the_cell_counts_as_complete(
    tmp_path: Path, subdirectory: str
):
    """The top-level pair stays self-consistent; the parent graph does not.

    One representative object per parent class is enough to prove the shared
    replay owner is live on the recovery path; the per-field negatives already
    live with that owner's own restart tests.
    """

    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    _publish_cell(env, tmp_path, keys[0][0], keys[0][1], boundary)

    parents = sorted((env["root"] / subdirectory).glob("*.json"))
    assert parents, f"no durable {subdirectory} parent was published"
    parents[0].unlink()

    with pytest.raises(TrainingDataInputError):
        recover_authenticated_boundary_progress(
            env["root"],
            env["window"],
            env["authority"],
            boundary_epoch=boundary,
            active_keys=keys,
        )


def test_recovery_does_not_weaken_immutable_publication(tmp_path: Path):
    """The anti-regression boundary: the guard the bug ran into stays hard."""

    from dataclasses import replace

    env = p3e._env(tmp_path)
    boundary, keys = _first_boundary(env)
    size, seed = keys[0]
    published = _publish_cell(env, tmp_path, size, seed, boundary)

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
    planned_rung, predecessor = p3e._rung_provenance(env, trajectory, boundary)

    # 1. Exact retry of the same evidence remains idempotent.
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
        planned_rung=planned_rung,
        predecessor_continuation=predecessor,
        restart_authority=env["authority"],
    )
    assert (
        len(
            collect_boundary_cell_completion_records(
                env["root"], env["window"], boundary_epoch=boundary
            )
        )
        == 1
    )

    # 2. A genuinely different result for the same logical cell is still a hard
    #    conflict, not a "latest wins" merge.
    forged_outcome = replace(
        published.outcome,
        target_force_rmse_mev_per_a=(
            published.outcome.target_force_rmse_mev_per_a + 5.0
        ),
    )
    forged = replace(
        completion_record,
        outcome=forged_outcome,
        outcome_digest=forged_outcome.content_digest,
    )
    with pytest.raises(TrainingDataInputError):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            forged,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
            planned_rung=planned_rung,
            predecessor_continuation=predecessor,
            restart_authority=env["authority"],
        )
    # The rejected result left nothing behind.
    assert (
        collect_boundary_cell_completion_records(
            env["root"], env["window"], boundary_epoch=boundary
        )[0].content_digest
        == published.content_digest
    )


# ---------------------------------------------------------------------------
# The reported defect, at the real production owner
# ---------------------------------------------------------------------------


class _RestartHarness(p4d._BoundedNumericalHarness):
    """The ordinary bounded harness plus interruption and re-execution proof.

    ``forbidden`` holds the ``(N, seed, boundary)`` rungs whose scientific work
    is already durable.  A trainer call for one of those is the defect itself,
    so it fails the test here rather than three owners later at the immutable
    progress slot.
    """

    def __init__(self, *, stop_after=None, stop_at_epoch_limit=None, forbidden=()):
        super().__init__()
        self.trained: list[tuple[int, int, int]] = []
        self.start_epochs: dict[tuple[int, int, int], int] = {}
        self.stop_after = stop_after
        self.stop_at_epoch_limit = stop_at_epoch_limit
        self.forbidden = set(forbidden)

    def train(self, request):
        rung = (
            int(request.trajectory.target_size),
            int(request.trajectory.optimizer_seed),
            int(request.plan.execution_epoch_limit),
        )
        assert rung not in self.forbidden, (
            f"already published cell {rung} was scheduled for re-execution"
        )
        assert rung not in self.trained, f"cell {rung} executed twice in one run"
        relevant = (
            self.trained
            if self.stop_at_epoch_limit is None
            else [r for r in self.trained if r[2] == self.stop_at_epoch_limit]
        )
        if self.stop_after is not None and (
            self.stop_at_epoch_limit is None
            or rung[2] == self.stop_at_epoch_limit
        ):
            if len(relevant) >= self.stop_after:
                raise OSError("simulated operational interruption")
        self.trained.append(rung)
        self.start_epochs[rung] = int(request.start_epoch)
        return super().train(request)

    def rungs_at(self, epoch_limit: int) -> list[tuple[int, int]]:
        return [(size, seed) for size, seed, limit in self.trained if limit == epoch_limit]


def _screen_root(paths, revision) -> Path:
    from mdstats.training_data.campaign_target_size_runtime import (
        current_target_size_execution_root,
    )

    return current_target_size_execution_root(paths, revision.state.generation)


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def _prepared(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    _cfg, paths = cli_load(config)
    return config, paths


def cli_load(config: Path):
    from mdstats.training_data import _campaign_cli_core as cli

    return cli._load_config(config)


def _select(config: Path, harness: _RestartHarness) -> int:
    return p4d._run(
        config,
        "select-target-size",
        _external_boundary_trainer=harness.train,
        _external_inference_evaluator=harness.evaluate,
    )


def test_partial_first_boundary_restart_reuses_published_cells(tmp_path: Path):
    """The reported failure, reproduced and closed at the production owner."""

    config, paths = _prepared(tmp_path)
    first_keys = _active_keys(config, boundary_epoch=1)

    interrupted = _RestartHarness(stop_after=2)
    with pytest.raises(OSError):
        _select(config, interrupted)
    published = interrupted.rungs_at(1)
    assert len(published) == 2

    # Partial progress is durable, and it advanced nothing.
    revision = _revision(paths)
    root = _screen_root(paths, revision)
    assert revision.state.adopted_execution_head_digest is None
    assert revision.state.adopted_reducer_state_digest is None
    assert revision.state.terminal is None
    assert not sorted((root / "heads").glob("*.json"))
    assert not (root / "batches").is_dir() or not sorted(
        (root / "batches").glob("*.json")
    )
    assert len(sorted((root / "progress" / "1").glob("*.json"))) == 2

    # A fresh invocation must recover those cells rather than recompute them.
    resumed = _RestartHarness(
        forbidden={(size, seed, 1) for size, seed in published}
    )
    assert _select(config, resumed) == 0

    executed_first = resumed.rungs_at(1)
    assert set(executed_first).isdisjoint(set(published))
    assert len(executed_first) == len(set(executed_first))
    assert set(executed_first) | set(published) == set(
        first_keys
    )

    # Exactly one boundary-1 batch and one boundary-1 reducer transition exist.
    batches = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "batches").glob("*.json"))
    ]
    first_boundary_batches = [b for b in batches if b["boundary_epoch"] == 1]
    assert len(first_boundary_batches) == 1
    # ...assembled in exact P2 size-major/seed-minor order, whatever mix of
    # recovered and newly executed cells produced it.
    resolver = TargetSizeExecutionResolver(root)
    ordered = [
        json.loads(
            resolver.completion_path(1, digest).read_text(encoding="utf-8")
        )
        for digest in first_boundary_batches[0]["completion_record_digests"]
    ]
    assert [
        (record["target_size"], record["optimizer_seed"]) for record in ordered
    ] == list(first_keys)
    # No recovered cell produced a second completion or progress record.
    assert len(sorted((root / "progress" / "1").glob("*.json"))) == len(
        first_keys
    )
    assert len(sorted((root / "completions" / "1").glob("*.json"))) == len(
        first_keys
    )

    final = _revision(paths)
    assert final.state.adopted_execution_head_digest is not None


def _active_keys(config: Path, *, boundary_epoch: int):
    """The exact active matrix P2 requires, read from P2 rather than the test.

    The screen context is built by the same production owner the runtime uses,
    because the P2 reducer only accepts boundary evidence once the execution
    context is bound.
    """

    from mdstats.training_data.campaign_target_size_runtime import (
        build_screen_context,
    )
    from mdstats.training_data.target_size_execution import (
        load_current_execution_head,
    )

    cfg, paths = cli_load(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        screen = build_screen_context(
            cfg,
            paths,
            store,
            revision,
            trainer=_unusable_trainer,
        )
    finally:
        store.close()
    head = load_current_execution_head(screen.root)
    state = screen.aggregate.reducer_state if head is None else head.post_state
    requirements = derive_active_boundary_requirements(
        screen.aggregate.definition, state
    )
    assert requirements is not None
    assert requirements[0] == boundary_epoch
    return requirements[2]


def _unusable_trainer(request):  # pragma: no cover - never invoked
    raise AssertionError("the key reader must not execute scientific work")


def test_restarted_screen_matches_an_uninterrupted_screen(tmp_path: Path):
    """Interruption changes what runs, never what the screen concludes."""

    interrupted_config, interrupted_paths = _prepared(tmp_path / "interrupted")
    first = _RestartHarness(stop_after=2)
    with pytest.raises(OSError):
        _select(interrupted_config, first)
    resumed = _RestartHarness(
        forbidden={(size, seed, 1) for size, seed in first.rungs_at(1)}
    )
    assert _select(interrupted_config, resumed) == 0

    clean_config, clean_paths = _prepared(tmp_path / "clean")
    assert _select(clean_config, _RestartHarness()) == 0

    restarted_state = _revision(interrupted_paths).state
    clean_state = _revision(clean_paths).state
    assert restarted_state.terminal is not None
    assert (
        restarted_state.adopted_reducer_state_digest
        == clean_state.adopted_reducer_state_digest
    )


def test_partial_later_boundary_restart_uses_existing_continuation(tmp_path: Path):
    """Current-boundary recovery and `n1 -> n2` continuation stay distinct."""

    config, paths = _prepared(tmp_path)

    interrupted = _RestartHarness(stop_after=1, stop_at_epoch_limit=3)
    with pytest.raises(OSError):
        _select(config, interrupted)
    completed_first = interrupted.rungs_at(1)
    completed_second = interrupted.rungs_at(3)
    assert completed_first, "the first boundary never committed"
    assert len(completed_second) == 1

    revision = _revision(paths)
    root = _screen_root(paths, revision)
    assert revision.state.adopted_execution_head_digest is not None
    assert len(sorted((root / "progress" / "3").glob("*.json"))) == 1
    survivors = set(_active_keys(config, boundary_epoch=3))

    resumed = _RestartHarness(
        forbidden=(
            {(size, seed, 1) for size, seed in completed_first}
            | {(size, seed, 3) for size, seed in completed_second}
        )
    )
    assert _select(config, resumed) == 0

    # No committed boundary and no recovered current-boundary cell was re-run.
    assert resumed.rungs_at(1) == []
    executed_second = resumed.rungs_at(3)
    assert set(executed_second).isdisjoint(set(completed_second))
    # Eliminated candidates receive no work: everything executed at boundary 2
    # is a survivor P2 asked for.
    assert set(executed_second) | set(completed_second) == survivors
    # The missing survivors resumed from the authenticated predecessor rung
    # rather than starting over.
    assert all(
        resumed.start_epochs[(size, seed, 3)] == 1 for size, seed in executed_second
    )

    assert _revision(paths).state.terminal is not None


@pytest.mark.parametrize("corruption", ["tampered_parent", "foreign_window"])
def test_contradictory_durable_progress_stops_the_screen(
    tmp_path: Path, corruption: str
):
    """Unexplained current-root evidence fails closed before new work starts."""

    config, paths = _prepared(tmp_path)
    interrupted = _RestartHarness(stop_after=2)
    with pytest.raises(OSError):
        _select(config, interrupted)
    revision = _revision(paths)
    root = _screen_root(paths, revision)

    if corruption == "tampered_parent":
        trajectory = sorted((root / "trajectories").glob("*.json"))[0]
        payload = json.loads(trajectory.read_text(encoding="utf-8"))
        payload["target_size"] = int(payload["target_size"]) + 1
        trajectory.write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
    else:
        progress = sorted((root / "progress" / "1").glob("*.json"))[0]
        payload = json.loads(progress.read_text(encoding="utf-8"))
        resolver = TargetSizeExecutionResolver(root)
        foreign_window = "e" * 64
        payload["window_digest"] = foreign_window
        payload.pop("content_digest", None)
        resolver.progress_path(
            foreign_window,
            1,
            int(payload["outcome"]["target_size"]),
            int(payload["outcome"]["optimizer_seed"]),
        ).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    blocked = _RestartHarness()
    with pytest.raises(mdstats.TrainingDataInputError):
        _select(config, blocked)
    assert blocked.trained == [], "new scientific work started on a corrupt root"
