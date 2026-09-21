"""Assembled acceptance: one collection-wide production TRAIN wave.

Everything here is driven through the real public ``train-production`` command
(and the real ``cross-validate`` that must precede it).  Only MACE numerics and
the device telemetry probe are substituted, strictly below the P5 owner
boundary, and the telemetry substitution is bounded and deterministic because
the claim is scheduler resource-policy semantics, not production resource
adequacy.  No GPU qualification is claimed: the campaign stays scientifically
CPU-configured and the synthetic device facts exist only to exercise the
existing adaptive admission branch.

The governed propositions are:

1. every final-production position that still requires TRAIN2 after
   collection-wide recovery normalization enters **one** adaptive scheduler
   wave, whatever selected size owns it;
2. that wave is TRAIN-only and ends at authenticated sealed TRAIN2 roots;
3. already-sealed and terminal-but-unsealed roots are normalized *before* the
   wave is sized, seal with zero trainer launch, and never enter task_count;
4. EVAL2, per-seed assessment and publication stay serial, frozen-size and
   required-seed ordered, and fail fast;
5. every new admission - first, later, requeued, and the finalization phase -
   is linearized against target-size generation transitions;
6. public cross-validation keeps its per-size outer-serial waves.
"""

from __future__ import annotations

import dataclasses
import json
import math
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_post_selection_runtime as runtime
from mdstats.training_data import training_parallel
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    PostSelectionStaleBindingError,
)
from mdstats.training_data.post_selection_execution import PostSelectionCancelledError
from mdstats.training_data.post_selection_publication import (
    resolve_current_final_production_publication,
)
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.training_parallel import GpuTelemetrySample

_GIB = 1024 ** 3

#: Two CV-feasible qualified sizes from the fixture ladder, with deliberately
#: different frozen production horizons.
FIRST_SIZE = 8
SECOND_SIZE = 16
FIRST_HORIZON = 2
SECOND_HORIZON = 3

#: Operator-shaped control values, small enough that promotion and consecutive
#: control observations happen inside a short test.
_FAST_CONTROL = """

[execution]
parallel_training_jobs = 0
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 4
parallel_training_epoch_stabilization_seconds = 0.0
parallel_training_epoch_stability_samples = 2
parallel_training_monitor_interval_seconds = 0.05
parallel_training_epoch_activity_timeout_seconds = 30.0
training_progress_interval_seconds = 0.05
estimated_training_ram_mib_per_job = 512.0
terminate_grace_seconds = 0.2
"""


class _PoisonTrainer:
    def __call__(self, request):  # pragma: no cover - never reached
        raise AssertionError("Selection may never train a candidate.")


def _two_size_campaign(
    tmp_path: Path, *, production_seeds: str = "[5]", control: str = _FAST_CONTROL
) -> Path:
    """One frozen two-size design, cross-validated, ready for production."""

    from unittest.mock import patch

    config_text = fx.fixture_config_text().replace(
        "[post_selection.production]\nseeds = [5]",
        f"[post_selection.production]\nseeds = {production_seeds}",
    )
    assert f"seeds = {production_seeds}" in config_text
    config_text += control
    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    for size, horizon in ((FIRST_SIZE, FIRST_HORIZON), (SECOND_SIZE, SECOND_HORIZON)):
        assert (
            p4d._run(
                config,
                "select-target-size",
                str(size),
                "--horizon",
                str(horizon),
                _external_boundary_trainer=_PoisonTrainer(),
                _external_inference_evaluator=_PoisonTrainer(),
            )
            == 0
        )
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    return config


def _resources() -> SystemResourceSnapshot:
    return SystemResourceSnapshot(
        cpu_threads_available=32,
        cpu_fraction=0.9,
        cpu_threads_budget=28,
        ram_available_bytes=120 * _GIB,
        ram_fraction=0.8,
        ram_budget_bytes=96 * _GIB,
        gpu_memory_fraction=0.9,
        gpu=GpuResourceSnapshot(
            available=True,
            device_count=1,
            selected_device=0,
            device_name="bounded-test-gpu",
            free_bytes=int(23.6 * _GIB),
            total_bytes=24 * _GIB,
            budget_bytes=int(24 * 0.9 * _GIB),
            reason="bounded-test",
        ),
    )


def _safe_sample(used_gib: float = 0.4, utilization: float = 5.0) -> GpuTelemetrySample:
    return GpuTelemetrySample(
        sampled_monotonic=time.monotonic(),
        device_index=0,
        utilization_percent=utilization,
        used_bytes=int(used_gib * _GIB),
        total_bytes=24 * _GIB,
    )


def _bind_bounded_device(
    monkeypatch: pytest.MonkeyPatch,
    *,
    telemetry=lambda _device: _safe_sample(),
    device_by_size: dict[int, str] | None = None,
) -> None:
    """Bind deterministic device facts below the production owner.

    The command still enumerates, plans, recovers, schedules and publishes on
    its own; only the device policy each context carries and the telemetry
    probe are supplied, so the existing CUDA admission branch is exercised
    without a GPU and without touching any scientific identity.
    """

    monkeypatch.setattr(cli, "_performance_resources", lambda _cfg: _resources())
    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", telemetry)
    original = runtime.build_post_selection_contexts

    def bounded(*args, **kwargs):
        contexts = original(*args, **kwargs)
        bound = []
        for context in contexts:
            device = (device_by_size or {}).get(
                int(context.selected.n_selected), "cuda:0"
            )
            bound.append(
                replace(
                    context,
                    method_policies=replace(context.method_policies, device=device),
                )
            )
        return tuple(bound)

    monkeypatch.setattr(runtime, "build_post_selection_contexts", bounded)


class _SchedulerSpy:
    """Count the concurrency owners the invocation actually constructs."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.plans: list[dict] = []
        self.controllers: list[object] = []
        real_plan = training_parallel.build_training_concurrency_plan
        real_controller = training_parallel.AdaptiveTrainingConcurrency

        def plan(**kwargs):
            built = real_plan(**kwargs)
            self.plans.append({**kwargs, "plan": built})
            return built

        def controller(plan_value, policy):
            built = real_controller(plan_value, policy)
            self.controllers.append(built)
            return built

        monkeypatch.setattr(training_parallel, "build_training_concurrency_plan", plan)
        monkeypatch.setattr(training_parallel, "AdaptiveTrainingConcurrency", controller)


class _ConcurrentProductionHarness(fx.PostSelectionHarness):
    """A child that stays alive until the wave reaches its expected width.

    It plays the part a real MACE child plays for the scheduler: it reports
    optimizer activity through the existing progress observer, honours the
    per-job cooperative stop handle, and only then runs the fixture's real
    TRAIN2 runtime to produce an authenticated summary.
    """

    def __init__(self, *, expected_width: int = 2, deadline: float = 120.0, **kwargs):
        super().__init__(**kwargs)
        self.expected_width = int(expected_width)
        self.deadline = float(deadline)
        self.lock = threading.Lock()
        self.runtime_lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        #: (identity, entered, exited) monotonic windows of every attempt.
        self.windows: list[tuple[str, float, float]] = []
        self.width_reached = threading.Event()

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        entered = time.monotonic()
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active >= self.expected_width:
                self.width_reached.set()
        try:
            if request.progress_observer is not None:
                request.progress_observer({"true_epoch": True, "phase": "training"})
            if not self.width_reached.wait(self.deadline):
                raise AssertionError(
                    f"the production wave never reached {self.expected_width} "
                    f"concurrent trainers (max {self.max_active})"
                )
            # The fixture's TRAIN2 runtime remains the real continuation,
            # checkpoint and evidence owner; only its toy model section is
            # serialized, because this suite exercises scheduler wiring rather
            # than a concurrent process-global torch fixture.
            with self.runtime_lock:
                return super().train(request)
        finally:
            with self.lock:
                self.active -= 1
            self.windows.append((identity, entered, time.monotonic()))


def _contexts(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return cfg, paths, runtime.build_post_selection_contexts(cfg, paths, store)
    finally:
        store.close()


def _production_run_roots(config: Path) -> list[Path]:
    """Every current production run root, through the real plan owners."""

    runs = _runs_root(config)
    _cfg, _paths, contexts = _contexts(config)
    roots: list[Path] = []
    for context in contexts:
        plan = runtime.resolve_current_final_production_plan(context)
        assert plan is not None
        for seed in plan.required_final_seeds:
            run_plan = runtime.build_final_production_run_plan(plan, optimizer_seed=seed)
            roots.append(runs / run_plan.run_identity)
    return roots


def _scheduler_lines(printed: str, status: str) -> list[str]:
    return [
        line
        for line in printed.splitlines()
        if line.startswith(f"[TRAIN scheduler] status={status}")
    ]


def _runs_root(config: Path) -> Path:
    from mdstats.training_data.post_selection_store import post_selection_root

    _cfg, _paths, contexts = _contexts(config)
    _cfg2, paths = cli._load_config(config)
    return post_selection_root(
        paths, contexts[0].selected.binding.campaign_generation
    ) / "runs"


# --- A1 / A3 / A12 / A15 / A17 / A18 ---------------------------------------


def test_two_sizes_one_seed_each_enter_one_global_train_wave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A1/A3/A12/A15/A17/A18 through the real ``train-production`` command."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    harness = _ConcurrentProductionHarness(expected_width=2)

    capsys.readouterr()
    assert fx.run_train_production(config, harness) == 0
    printed = capsys.readouterr().out

    # A1: one wave, one controller, truthful two-job plan, two live trainers.
    assert len(spy.controllers) == 1, "more than one TRAIN controller was built"
    assert len(spy.plans) == 1, [item["task_count"] for item in spy.plans]
    assert spy.plans[0]["task_count"] == 2
    assert harness.max_active == 2
    assert len(harness.runs) == 2

    # A12: the public scheduler line describes the global wave from the start.
    planned = _scheduler_lines(printed, "planned")
    assert planned and "progress=0/2" in planned[0], planned
    assert "unit=training-run" in planned[0]

    # A3/A15: each position carried its own exact horizon and membership, and
    # the four scientific identities are distinct per size.
    by_epochs = {
        int(request.plan.budget_policy.planned_epochs): request
        for request in harness.requests
    }
    assert sorted(by_epochs) == [FIRST_HORIZON, SECOND_HORIZON]
    memberships = {
        int(request.materialization.target_train_artifact.configuration_count)
        for request in harness.requests
    }
    assert memberships == {FIRST_SIZE, SECOND_SIZE}
    assert len({str(request.run_plan.run_identity) for request in harness.requests}) == 2
    assert (
        len(
            {
                str(request.run_plan.training_trajectory_identity)
                for request in harness.requests
            }
        )
        == 2
    )

    # A17: every per-job dimension the one controller assumes is shared was
    # equal for the actual TRAIN_REQUIRED positions; the differing scientific
    # inputs (N, horizon, seed) are not scheduler inputs.
    _cfg, _paths, contexts = _contexts(config)
    assert spy.plans[0]["device"] == "cuda:0"
    assert spy.plans[0]["loader_workers_per_job"] == 0

    # A18: no EVAL2 provider ran while a scheduler-owned TRAIN2 child was live.
    last_train_end = max(end for _identity, _start, end in harness.windows)
    assert harness.evaluations, "EVAL2 must have executed"
    assert min(harness.evaluations) >= last_train_end

    # EVAL2/finalization stays serial and frozen-size ordered.
    eval_lines = [
        line for line in printed.splitlines() if line.startswith("[EVAL2 serial]")
    ]
    ordered_sizes = [
        int(line.split("N_selected=")[1].split(";")[0])
        for line in eval_lines
        if "N_selected=" in line
    ]
    assert ordered_sizes == [FIRST_SIZE, SECOND_SIZE]

    # Both sizes finalized through their own publication owner.
    for context, expected_epochs in zip(contexts, (FIRST_HORIZON, SECOND_HORIZON)):
        plan = runtime.resolve_current_final_production_plan(context)
        assert plan is not None and plan.planned_epochs == expected_epochs
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
        assert decision.binding.content_digest == context.selected.binding.content_digest


def test_global_scheduler_owns_train_only_and_stops_at_sealed_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A18 structural/behavioural: the wave returns sealed roots, not evidence."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    harness = _ConcurrentProductionHarness(expected_width=2)

    stop_flags: list[bool] = []
    real_run = runtime.execute_post_selection_run

    def observed(context, **kwargs):
        stop_flags.append(bool(kwargs.get("stop_after_training")))
        return real_run(context, **kwargs)

    monkeypatch.setattr(runtime, "execute_post_selection_run", observed)
    monkeypatch.setattr(
        runtime, "_execute_pending_post_selection_run",
        lambda task, **kwargs: observed(
            task.context,
            run_plan=task.run_plan,
            budget_policy=task.budget_policy,
            training_frame_uids=task.training_frame_uids,
            monitor_frame_uids=task.monitor_frame_uids,
            outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
            progress_context=task.progress_context,
            **kwargs,
        ),
    )
    assert fx.run_train_production(config, harness) == 0
    # Two TRAIN-only entries (the wave) then two evaluating entries (per-size
    # finalization), never the other way round.
    assert stop_flags == [True, True, False, False]


# --- A2: four positions from two sizes and two seeds ------------------------


def test_two_sizes_two_seeds_drain_one_bounded_global_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    harness = _ConcurrentProductionHarness(expected_width=2)

    capsys.readouterr()
    assert fx.run_train_production(config, harness) == 0
    printed = capsys.readouterr().out

    assert len(spy.controllers) == 1
    assert [item["task_count"] for item in spy.plans] == [4]
    planned = _scheduler_lines(printed, "planned")
    assert planned and "progress=0/4" in planned[0], planned
    assert len(harness.runs) == 4
    assert len(set(harness.runs)) == 4, "a run identity was scheduled twice"
    assert 2 <= harness.max_active <= 4

    # Bounded concurrency drained the queue without schedule-order-dependent
    # reduction: both sizes publish their own two-seed product.
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
        assert len(decision.seed_evidence) == 2


# --- A7: recovery normalization, mixed restart, canonical EVAL order --------


class _InterruptAfterTerminalEpoch(fx.PostSelectionHarness):
    """Seal the first position, then leave the second terminal-but-unsealed."""

    def train(self, request):
        self.requests.append(request)
        identity = str(request.run_plan.run_identity)
        self.runs.append(identity)
        if len(self.runs) == 1:
            return fx.train_like_mace(request)
        return fx.train_like_mace(
            request,
            stop_after_epoch=int(request.plan.execution_epoch_limit) - 1,
            fail_after_persist=True,
        )


def _interrupted_two_size_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, list[str]]:
    """One sealed root, one terminal-but-unsealed root, two untouched positions."""

    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    _bind_bounded_device(monkeypatch)
    harness = _InterruptAfterTerminalEpoch()
    with pytest.raises(AssertionError, match="bounded interruption"):
        fx.run_train_production(config, harness)
    assert len(harness.runs) == 2
    return config, list(harness.runs)


def test_terminal_but_unsealed_roots_seal_before_the_wave_is_sized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A7: only genuinely TRAIN_REQUIRED positions reach the scheduler."""

    config, interrupted_runs = _interrupted_two_size_production(tmp_path, monkeypatch)
    runs = _runs_root(config)
    sealed_first, terminal_unsealed = (runs / name for name in interrupted_runs)
    assert runtime.read_post_selection_run_completion(sealed_first)[0] is not None
    assert runtime.read_post_selection_run_completion(terminal_unsealed)[0] is None
    before = sorted(path.name for path in terminal_unsealed.rglob("*"))
    capsys.readouterr()

    spy = _SchedulerSpy(monkeypatch)
    harness = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, harness) == 0
    printed = capsys.readouterr().out

    # The terminal-but-unsealed root sealed through its own owner, with zero
    # trainer launch, and neither reused root entered the wave.
    assert runtime.read_post_selection_run_completion(terminal_unsealed)[0] is not None
    assert len(harness.runs) == 2
    assert set(harness.runs).isdisjoint(interrupted_runs)
    assert [item["task_count"] for item in spy.plans] == [2]
    assert len(spy.controllers) == 1
    assert "train_required=2; sealed=2" in printed
    recovered = [
        line
        for line in printed.splitlines()
        if line.startswith("[TRAIN] status=reused; terminal TRAIN2 sealed by recovery")
    ]
    assert len(recovered) == 1, printed
    appended = set(path.name for path in terminal_unsealed.rglob("*")) - set(before)
    assert {"run-topology.json", "run-completion.json"} <= appended

    # Finalization visits frozen sizes in order and required seeds in plan
    # order, regardless of which root was sealed when.
    order = [
        (
            int(line.split("N_selected=")[1].split(";")[0]),
            int(line.split("seed=")[1].split(";")[0]),
        )
        for line in printed.splitlines()
        if line.startswith("[EVAL2 serial] status=running") and "N_selected=" in line
    ]
    assert order == [
        (FIRST_SIZE, 5),
        (FIRST_SIZE, 6),
        (SECOND_SIZE, 5),
        (SECOND_SIZE, 6),
    ]

    # A fully sealed collection builds no adaptive scheduler at all.
    capsys.readouterr()
    rerun = fx.PostSelectionHarness()
    spy_again = _SchedulerSpy(monkeypatch)
    assert fx.run_train_production(config, rerun) == 0
    reprinted = capsys.readouterr().out
    assert rerun.runs == []
    assert spy_again.plans == [] and spy_again.controllers == []
    assert "[TRAIN scheduler] status=" not in reprinted
    assert "train_required=0; sealed=4" in reprinted


# --- R1: every classification is owned by the run-activity lease ------------


def _publish_plans_without_recovery(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive the real command through Phase A/B and stop before recovery.

    Afterwards every per-binding FinalProductionPlan pointer is current and no
    production run root exists yet, which is exactly the state in which a
    locator-time observation of an absent root is tempting and wrong.
    """

    real = runtime._train_final_production_collection

    def stop(*_args, **_kwargs):
        raise PostSelectionError("bounded stop before recovery normalization")

    monkeypatch.setattr(runtime, "_train_final_production_collection", stop)
    with pytest.raises(PostSelectionError, match="bounded stop"):
        fx.run_train_production(config, fx.PostSelectionHarness())
    monkeypatch.setattr(runtime, "_train_final_production_collection", real)


def test_recovery_classifies_positions_only_under_the_run_activity_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """R1: a competing owner that wins the lease owns the classification.

    The position's root is absent when this invocation resolves its locator -
    the one observation the normalization pass may legitimately make outside
    the lease.  A second owner then acquires the *existing* run-activity lease
    for that exact root and drives the position to an authenticated sealed
    TRAIN2 root through the real run owner.  Normalization blocks at the
    ownership boundary and, once it holds the lease, must classify from the
    authoritative post-transition state: the position is reusable, not
    ``TRAIN_REQUIRED``.

    No new lease, liveness registry, PID/mtime inference or collection lock is
    involved; the only exclusion used is the one the run owner already holds.
    """

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    _publish_plans_without_recovery(config, monkeypatch)

    roots = _production_run_roots(config)
    assert len(roots) == 2
    contested = roots[0]
    assert not contested.exists(), "the contested root must start out absent"

    at_boundary = threading.Event()
    lease_held = threading.Event()
    failures: list[BaseException] = []
    winner = fx.PostSelectionHarness()
    main = threading.current_thread()
    real_lease = runtime.post_selection_run_activity_lease

    def win_the_position() -> None:
        """Take the lease first, then create and seal the root under it.

        The root is deliberately still absent when the lease is taken: that is
        the only construction in which a pre-lease pathname observation and the
        authoritative lease-owned state disagree.
        """

        cfg, paths = cli._load_config(config)
        store = CampaignStore(paths.state_db)
        try:
            contexts = runtime.build_post_selection_contexts(
                cfg,
                paths,
                store,
                trainer=winner.train,
                inference_evaluator=winner.evaluate,
                admit=True,
            )
            task = runtime._plan_final_production(contexts[0], first_key=0).tasks[0]
            root = runtime.resolve_post_selection_training_root(
                task.context, task.run_plan
            )
            assert root.path == contested and not root.path.exists()
            with real_lease(root.path):
                lease_held.set()
                # Bounded: if normalization never asks for this lease it has
                # already classified the position without ownership, which the
                # assertions below then report.
                at_boundary.wait(45.0)
                root.path.mkdir(parents=True, exist_ok=True)
                runtime._execute_post_selection_run_locked(
                    task.context,
                    run_plan=task.run_plan,
                    budget_policy=task.budget_policy,
                    training_frame_uids=task.training_frame_uids,
                    monitor_frame_uids=task.monitor_frame_uids,
                    outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
                    root=root,
                    progress_context=task.progress_context,
                    stop_after_training=True,
                )
        except BaseException as exc:  # surfaced by the main thread
            failures.append(exc)
        finally:
            lease_held.set()
            store.close()

    def observed_lease(run_root):
        # Only this invocation's own normalization pass is observed; the
        # competing owner and the scheduler's workers run on other threads.
        if threading.current_thread() is main and Path(run_root) == contested:
            at_boundary.set()
        return real_lease(run_root)

    monkeypatch.setattr(runtime, "post_selection_run_activity_lease", observed_lease)

    thread = threading.Thread(target=win_the_position, name="competing-p5-owner")
    thread.start()
    try:
        assert lease_held.wait(180.0), "the competing owner never took the lease"
        assert not failures, failures
        assert not contested.exists(), "the contested root must still be absent"

        capsys.readouterr()
        spy = _SchedulerSpy(monkeypatch)
        harness = _ConcurrentProductionHarness(expected_width=1)
        assert fx.run_train_production(config, harness) == 0
        printed = capsys.readouterr().out
    finally:
        thread.join(300.0)
    assert not thread.is_alive()
    assert not failures, failures

    # The classification boundary was actually reached, and the winning owner
    # is the only one that ever trained the contested position.
    assert at_boundary.is_set(), (
        "recovery normalization never asked for the run-activity lease of a root "
        "it observed as absent; it classified the position before owning it"
    )
    assert winner.runs == [contested.name], winner.runs
    assert runtime.read_post_selection_run_completion(contested)[0] is not None

    # The contested position was classified reusable from the post-transition
    # state: no trainer request, no task-count inflation, no duplicate run.
    assert contested.name not in harness.runs
    assert len(harness.runs) == 1 and len(set(harness.runs)) == 1
    assert [item["task_count"] for item in spy.plans] == [1]
    assert len(spy.controllers) == 1
    assert "train_required=1; sealed=1" in printed
    planned = _scheduler_lines(printed, "planned")
    assert planned and "progress=0/1" in planned[0], planned

    # Both sizes still finalize through their own publication owner.
    for context in _contexts(config)[2]:
        assert resolve_current_final_production_publication(context) is not None


# --- A6 / A13: integrity normalization and plan-pointer semantics -----------


def _final_plan_digests(config: Path) -> list[str | None]:
    from mdstats.training_data.post_selection_store import (
        POINTER_FINAL_PLAN,
        read_current_post_selection_pointer,
    )

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        contexts = runtime.build_post_selection_contexts(cfg, paths, store)
        return [
            read_current_post_selection_pointer(
                store, binding=context.selected.binding, kind=POINTER_FINAL_PLAN
            )
            for context in contexts
        ]
    finally:
        store.close()


def test_corrupt_continuation_fails_before_any_sibling_trainer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A6(1)/A13 post-Phase-B: a corrupt root stops the wave, rolls nothing back."""

    from mdstats.training_data.train2_runtime import TRAIN2_RUNTIME_SUMMARY_FILENAME

    config, interrupted_runs = _interrupted_two_size_production(tmp_path, monkeypatch)
    runs = _runs_root(config)
    sealed_first, terminal_unsealed = (runs / name for name in interrupted_runs)
    # Corrupt the *later* position so an earlier valid recovery seal exists
    # before the failure.
    summary = terminal_unsealed / "checkpoints" / TRAIN2_RUNTIME_SUMMARY_FILENAME
    summary.write_text('{"schema": "foreign", "completed_epochs": 99}', encoding="utf-8")
    before_pointers = _final_plan_digests(config)
    assert all(before_pointers)
    capsys.readouterr()

    spy = _SchedulerSpy(monkeypatch)
    harness = fx.PostSelectionHarness()
    with pytest.raises(Exception) as failure:
        fx.run_train_production(config, harness)
    printed = capsys.readouterr().out

    assert "TRAIN2" in str(failure.value) or "authenticate" in str(failure.value)
    assert harness.runs == [], "a sibling trainer launched behind a corrupt root"
    assert harness.evaluations == [], "EVAL2 began after a recovery failure"
    assert spy.plans == [] and spy.controllers == []
    assert "[TRAIN scheduler] status=" not in printed
    # Independently valid per-binding plan pointers stay current, and the
    # earlier root that recovery legitimately sealed stays sealed.
    assert _final_plan_digests(config) == before_pointers
    assert runtime.read_post_selection_run_completion(sealed_first)[0] is not None
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        assert resolve_current_final_production_publication(context) is None


def test_corrupt_sealed_root_fails_before_any_sibling_trainer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A6(2): a sealed root that no longer authenticates stops the collection."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    assert fx.run_train_production(config, _ConcurrentProductionHarness()) == 0
    roots = _production_run_roots(config)
    assert len(roots) == 2
    record = roots[-1] / "materialization" / "materialization.json"
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["content_digest"] = "0" * 64
    record.write_text(json.dumps(payload), encoding="utf-8")

    spy = _SchedulerSpy(monkeypatch)
    harness = fx.PostSelectionHarness()
    with pytest.raises(Exception):
        fx.run_train_production(config, harness)
    assert harness.runs == []
    assert spy.plans == [] and spy.controllers == []


def test_phase_a_second_line_cv_authorization_precedes_every_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A13 Phase-A: the per-size fence stands even without the collection barrier."""

    from unittest.mock import patch

    config_text = fx.fixture_config_text() + _FAST_CONTROL
    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    for size, horizon in ((FIRST_SIZE, FIRST_HORIZON), (SECOND_SIZE, SECOND_HORIZON)):
        assert (
            p4d._run(
                config,
                "select-target-size",
                str(size),
                "--horizon",
                str(horizon),
                _external_boundary_trainer=_PoisonTrainer(),
                _external_inference_evaluator=_PoisonTrainer(),
            )
            == 0
        )
    # Cross-validate only the first size, through the real CV owner.
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        cv = fx.PostSelectionHarness()
        contexts = runtime.build_post_selection_contexts(
            cfg, paths, store, trainer=cv.train, inference_evaluator=cv.evaluate,
            admit=True,
        )
        _plan, acceptance = runtime.execute_post_selection_cross_validation(contexts[0])
        assert acceptance.accepted
    finally:
        store.close()

    # Disable only the *collection* barrier, so the per-size authorization
    # fence is the single thing that can refuse this invocation.
    monkeypatch.setattr(runtime, "_cv_admission_blockers", lambda contexts: ())
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="requires a current accepted"):
        fx.run_train_production(config, harness)
    assert harness.runs == []
    assert spy.plans == []
    # Phase A failed before any plan pointer became current, including the
    # authorized first size's.
    assert _final_plan_digests(config) == [None, None]


def test_phase_b_pointer_race_stops_before_train2_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A13 Phase-B: a losing pointer commit is not a collection rollback."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    from mdstats.training_data.post_selection_store import POINTER_FINAL_PLAN

    real_publish = runtime.publish_current_post_selection_pointer
    commits: list[str] = []

    def racing_publish(store, *, binding, kind, content_digest, position=None):
        if kind == POINTER_FINAL_PLAN:
            commits.append(str(binding.content_digest))
            if len(commits) == 2:
                raise PostSelectionStaleBindingError(
                    "A newer frozen target-size design became current while this "
                    "post-selection work was running."
                )
        return real_publish(
            store,
            binding=binding,
            kind=kind,
            content_digest=content_digest,
            position=position,
        )

    monkeypatch.setattr(
        runtime, "publish_current_post_selection_pointer", racing_publish
    )
    harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionStaleBindingError):
        fx.run_train_production(config, harness)
    assert harness.runs == [], "TRAIN2 started behind a stale pointer commit"
    assert spy.plans == []
    first, second = _final_plan_digests(config)
    assert first is not None, "a validly committed sibling pointer was rolled back"
    assert second is None


# --- A14: fail-fast per-size finalization after a successful global wave ----


def test_finalization_fails_fast_in_frozen_size_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    _bind_bounded_device(monkeypatch)
    # Every checkpoint measures far outside the production admissibility
    # ceiling, so the first size fails with typed no-admissible outcomes.
    harness = _ConcurrentProductionHarness(expected_width=2, force_offset=1.0)
    capsys.readouterr()
    with pytest.raises(PostSelectionError, match="No checkpoint passed"):
        fx.run_train_production(config, harness)
    printed = capsys.readouterr().out
    assert len(harness.runs) == 4, "the whole collection must still have trained"

    # All required seeds of the first size were evaluated and assessed before
    # that size failed; the later size began no fresh EVAL2 at all.
    order = [
        (
            int(line.split("N_selected=")[1].split(";")[0]),
            int(line.split("seed=")[1].split(";")[0]),
        )
        for line in printed.splitlines()
        if line.startswith("[EVAL2 serial] status=running") and "N_selected=" in line
    ]
    assert order == [(FIRST_SIZE, 5), (FIRST_SIZE, 6)]
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        assert resolve_current_final_production_publication(context) is None
    first_plan = runtime.resolve_current_final_production_plan(contexts[0])
    assert first_plan is not None
    for seed in first_plan.required_final_seeds:
        run_plan = runtime.build_final_production_run_plan(
            first_plan, optimizer_seed=seed
        )
        assessment = runtime.resolve_current_final_seed_assessment(contexts[0], run_plan)
        assert assessment is not None and not assessment.selected

    # The later size's authenticated sealed TRAIN2 roots stay reusable: a rerun
    # retrains nothing.
    rerun = fx.PostSelectionHarness(force_offset=1.0)
    with pytest.raises(PostSelectionError, match="No checkpoint passed"):
        fx.run_train_production(config, rerun)
    assert rerun.runs == []


# --- A8: whole-wave failure, cancellation, reaping, restart -----------------


class _FailAfterWaveWidth(fx.PostSelectionHarness):
    """The second admitted position fails once both are owned by the wave."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lock = threading.Lock()
        self.runtime_lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.order: list[str] = []
        self.stopped: list[str] = []
        self.width = threading.Event()

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        with self.lock:
            self.runs.append(identity)
            self.order.append(identity)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            ordinal = len(self.order)
            if self.active >= 2:
                self.width.set()
        try:
            if request.progress_observer is not None:
                request.progress_observer({"true_epoch": True, "phase": "training"})
            assert self.width.wait(120.0), "the wave never admitted two positions"
            if ordinal == 2:
                raise RuntimeError("bounded TRAIN2 child failure")
            stop = request.cancellation_event
            assert stop is not None
            while not stop.is_set():
                time.sleep(0.01)
            self.stopped.append(identity)
            raise PostSelectionCancelledError(
                "Post-selection MACE training was cancelled."
            )
        finally:
            with self.lock:
                self.active -= 1


def test_wave_failure_cancels_every_owned_task_and_starts_no_eval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    harness = _FailAfterWaveWidth()
    capsys.readouterr()
    with pytest.raises(RuntimeError, match="bounded TRAIN2 child failure"):
        fx.run_train_production(config, harness)
    printed = capsys.readouterr().out

    assert harness.max_active == 2
    assert harness.stopped == [harness.order[0]], (
        "the surviving cross-size sibling was not signalled and reaped"
    )
    assert harness.evaluations == [], "EVAL2 began after a failed TRAIN wave"
    failed = _scheduler_lines(printed, "failed")
    # The failure report is emitted while the owned sibling is still being
    # reaped, so truthful accounting here is "one failed, nothing queued";
    # the reaping itself is proved by ``harness.stopped`` above and by the
    # command returning only after every worker has returned.
    assert failed and "failed_jobs=1" in failed[-1], failed
    assert "queued_jobs=0" in failed[-1], failed
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        assert resolve_current_final_production_publication(context) is None

    # The next healthy invocation schedules only outstanding work.
    resumed = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, resumed) == 0
    assert len(resumed.runs) == 2
    for context in _contexts(config)[2]:
        assert resolve_current_final_production_publication(context) is not None


# --- R5: a sealed cross-size sibling survives a later wave failure ----------


#: Two owned slots exactly, so the wave's admission order is deterministic:
#: one position runs alone and seals, two more are then owned simultaneously,
#: and the fourth can only be admitted if a slot is released.
_TWO_SLOT_CONTROL = _FAST_CONTROL.replace(
    "maximum_parallel_training_jobs = 4", "maximum_parallel_training_jobs = 2"
)


class _SealOneThenFailAnother(fx.PostSelectionHarness):
    """Seal the first position, then fail a later one while a sibling is live."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lock = threading.Lock()
        self.order: list[str] = []
        self.stopped: list[str] = []
        self.admitted_after_failure: list[str] = []
        self.active = 0
        self.max_active = 0
        self.failed_at: float | None = None
        self.sealed_before_failure = 0
        #: Roots already sealed when the wave began (the CV roots), so only
        #: seals produced by this production wave are counted.
        self.baseline: set[str] | None = None

    @staticmethod
    def _sealed_roots(request) -> list[str]:
        runs_root = request.materialization_directory.parent.parent
        return sorted(
            root.name
            for root in runs_root.iterdir()
            if root.is_dir() and (root / "run-completion.json").is_file()
        )

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        with self.lock:
            self.order.append(identity)
            ordinal = len(self.order)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.failed_at is not None:
                self.admitted_after_failure.append(identity)
        try:
            if self.baseline is None:
                self.baseline = set(self._sealed_roots(request))
            if ordinal == 1:
                # The real run owner trains this position to its authenticated
                # terminal TRAIN2 root and publishes the existing completion
                # seal when this returns.
                return super().train(request)
            if request.progress_observer is not None:
                request.progress_observer({"true_epoch": True, "phase": "training"})
            deadline = time.monotonic() + 180.0
            if ordinal == 2:
                # Fail only once a sibling seal is durable *and* another owned
                # position is genuinely active beside this one.
                while True:
                    assert time.monotonic() < deadline, "the wave never settled"
                    sealed = set(self._sealed_roots(request)) - (self.baseline or set())
                    with self.lock:
                        beside = self.active >= 2
                    if sealed and beside:
                        with self.lock:
                            self.sealed_before_failure = len(sealed)
                            self.failed_at = time.monotonic()
                        raise RuntimeError("bounded TRAIN2 child failure")
                    time.sleep(0.01)
            stop = request.cancellation_event
            assert stop is not None
            while not stop.is_set():
                assert time.monotonic() < deadline, "the sibling was never signalled"
                time.sleep(0.01)
            with self.lock:
                self.stopped.append(identity)
            raise PostSelectionCancelledError(
                "Post-selection MACE training was cancelled."
            )
        finally:
            with self.lock:
                self.active -= 1


def test_a_sealed_sibling_survives_a_later_wave_failure_and_is_not_retrained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """R5/A8: completed TRAIN2 evidence is durable across a failed wave.

    One cross-size production position reaches an authenticated sealed TRAIN2
    root through the existing completion/topology owner.  Only then does a
    second, still-active position fail while a third is owned and a fourth is
    queued.  The failure must stop admission, cancel and reap the owned
    sibling, and begin no EVAL2 - and the retry must reuse the sealed sibling
    with zero trainer relaunch, scheduling only the outstanding
    ``TRAIN_REQUIRED`` positions.
    """

    config = _two_size_campaign(
        tmp_path, production_seeds="[5, 6]", control=_TWO_SLOT_CONTROL
    )
    _bind_bounded_device(monkeypatch)
    harness = _SealOneThenFailAnother()
    capsys.readouterr()
    with pytest.raises(RuntimeError, match="bounded TRAIN2 child failure"):
        fx.run_train_production(config, harness)
    printed = capsys.readouterr().out

    # One sibling was already sealed when the failure happened, one sibling was
    # active and was signalled and reaped, and nothing further was admitted.
    assert harness.sealed_before_failure == 1
    assert harness.max_active == 2
    assert len(harness.order) == 3, harness.order
    assert harness.stopped == [harness.order[2]], harness.stopped
    assert harness.admitted_after_failure == []
    assert harness.evaluations == [], "EVAL2 began after a failed TRAIN wave"
    failed = _scheduler_lines(printed, "failed")
    assert failed and "failed_jobs=1" in failed[-1], failed

    sealed_roots = [
        root
        for root in _production_run_roots(config)
        if runtime.read_post_selection_run_completion(root)[0] is not None
    ]
    assert [root.name for root in sealed_roots] == [harness.order[0]]
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        assert resolve_current_final_production_publication(context) is None

    # The retry authenticates and reuses the sealed sibling; only genuinely
    # outstanding positions re-enter the scheduler's task count.
    capsys.readouterr()
    spy = _SchedulerSpy(monkeypatch)
    retry = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, retry) == 0
    reprinted = capsys.readouterr().out

    assert harness.order[0] not in retry.runs, "a sealed sibling was retrained"
    assert len(retry.runs) == 3 and len(set(retry.runs)) == 3
    assert [item["task_count"] for item in spy.plans] == [3]
    assert len(spy.controllers) == 1
    assert "train_required=3; sealed=1" in reprinted
    planned = _scheduler_lines(reprinted, "planned")
    assert planned and "progress=0/3" in planned[0], planned

    # Frozen-order finalization then completes for the whole collection.
    order = [
        int(line.split("N_selected=")[1].split(";")[0])
        for line in reprinted.splitlines()
        if line.startswith("[EVAL2 serial] status=running") and "N_selected=" in line
    ]
    assert order == [FIRST_SIZE, FIRST_SIZE, SECOND_SIZE, SECOND_SIZE]
    for context in _contexts(config)[2]:
        decision = resolve_current_final_production_publication(context)
        assert decision is not None and len(decision.seed_evidence) == 2


# --- A9: cross-size memory demotion keeps scientific identity ---------------


class _OccupancyProductionHarness(fx.PostSelectionHarness):
    """Aggregate occupancy rises with owned concurrency, as a real wave does."""

    OCCUPANCY_GIB = {0: 0.4, 1: 10.0, 2: 22.2}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lock = threading.Lock()
        self.runtime_lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.order: list[str] = []
        self.stopped: list[str] = []
        self.attempts: dict[str, int] = {}
        self.start_epochs: dict[tuple[str, int], int] = {}
        self._peaked = threading.Event()

    def occupancy_gib(self) -> float:
        with self.lock:
            active = self.active
        return self.OCCUPANCY_GIB[min(active, 2)]

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        with self.lock:
            attempt = self.attempts.get(identity, 0) + 1
            self.attempts[identity] = attempt
            if attempt == 1:
                self.order.append(identity)
            self.start_epochs[(identity, attempt)] = int(request.start_epoch)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active >= 2:
                self._peaked.set()
        try:
            if request.progress_observer is not None:
                request.progress_observer({"true_epoch": True, "phase": "training"})
            deadline = time.monotonic() + 180.0
            while True:
                if time.monotonic() > deadline:
                    raise AssertionError("the demotion fixture never settled")
                stop = request.cancellation_event
                if stop is not None and stop.is_set():
                    with self.lock:
                        self.stopped.append(identity)
                    raise PostSelectionCancelledError(
                        "Post-selection MACE training was cancelled."
                    )
                with self.lock:
                    settled = self._peaked.is_set() and self.active <= 1
                if settled:
                    break
                time.sleep(0.005)
            with self.runtime_lock:
                return super().train(request)
        finally:
            with self.lock:
                self.active -= 1


def test_cross_size_memory_demotion_preserves_identity_and_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A9: the most recently admitted cross-size task is the deterministic victim."""

    config = _two_size_campaign(tmp_path)
    harness = _OccupancyProductionHarness()
    _bind_bounded_device(
        monkeypatch,
        telemetry=lambda _device: _safe_sample(used_gib=harness.occupancy_gib()),
    )
    capsys.readouterr()
    assert fx.run_train_production(config, harness) == 0
    printed = capsys.readouterr().out

    assert harness.max_active == 2
    assert len(harness.order) == 2
    victim = harness.order[-1]
    assert harness.stopped == [victim], harness.stopped
    assert "backoff 2->1; slot=" in printed
    # The demoted position kept its exact scientific identity and returned to
    # the queue rather than being counted as failed or duplicated.
    assert harness.attempts[victim] == 2
    assert harness.attempts[harness.order[0]] == 1
    assert len(set(harness.order)) == 2
    failed_lines = [
        line for line in printed.splitlines() if "[TRAIN scheduler] status=" in line
    ]
    assert all("failed_jobs=0" in line for line in failed_lines), failed_lines
    for context in _contexts(config)[2]:
        assert resolve_current_final_production_publication(context) is not None


# --- A10: one resource domain is proved, not assumed ------------------------


def test_incompatible_execution_profile_fails_before_any_trainer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch, device_by_size={SECOND_SIZE: "cuda:1"})
    spy = _SchedulerSpy(monkeypatch)
    harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="cannot share one TRAIN scheduler"):
        fx.run_train_production(config, harness)
    assert harness.runs == []
    assert spy.plans == [] and spy.controllers == []


def test_an_incompatible_profile_on_a_sealed_position_does_not_block_the_wave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A10: a position that never shares the TRAIN domain cannot veto it."""

    config, interrupted = _interrupted_two_size_production(tmp_path, monkeypatch)
    # The first size's positions are sealed/normalized; give that size a
    # scheduler-incompatible device anyway.
    _bind_bounded_device(monkeypatch, device_by_size={FIRST_SIZE: "cuda:1"})
    spy = _SchedulerSpy(monkeypatch)
    harness = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, harness) == 0
    assert [item["task_count"] for item in spy.plans] == [2]
    assert set(harness.runs).isdisjoint(interrupted)


# --- A17 / R2: one common resource-policy owner, not production qualification


_MIB = 1024 ** 2


def test_distinct_production_sizes_and_horizons_make_one_resource_demand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A17 structural check: what ``N`` and ``H_prod`` enter the shared wave.

    Two positions that both remain ``TRAIN_REQUIRED`` after recovery
    normalization differ in every scientific input the single-controller
    contract is suspected of depending on: selected size (and therefore exact
    training membership and materialized dataset), and frozen production
    horizon.  This test checks the common policy/plan interface and the actual
    runtime inputs; it does not qualify empirical production RAM/VRAM
    adequacy.

    * **device/VRAM geometry** - device, backend, learned precision, model and
      runtime realization, replay lineage and the batch/validation-batch
      geometry that determines device residency are equal, so no
      dataset-wide or horizon-wide device-resident state exists beside the
      common batch/model geometry.  The operative live bound is the aggregate
      VRAM/utilization envelope, which is observed from telemetry and is
      likewise not a function of ``N``.
    * **CPU/threading** - loader-worker count and the plan's derived native
      thread geometry come from one configuration and one task count.
    * **host RAM** - the materialized training transport grows with ``N``.  Its
      serialized size is retained below only as descriptive transport evidence;
      it is not treated as a resident-memory bound or a production
      qualification.
    * **horizon** - ``H_prod`` reaches the runtime only as the epoch budget and
      execution epoch limit, i.e. as work *duration*, leaving every resident
      quantity untouched.
    """

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    scheduled: list = []
    real_wave = runtime._train_post_selection_pending_runs

    def observed(pending, **kwargs):
        scheduled.extend(pending)
        return real_wave(pending, **kwargs)

    monkeypatch.setattr(runtime, "_train_post_selection_pending_runs", observed)
    harness = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, harness) == 0

    # The two positions that actually shared the TRAIN resource domain.
    assert len(scheduled) == 2
    small, large = sorted(
        scheduled, key=lambda task: int(task.context.selected.n_selected)
    )
    assert int(small.context.selected.n_selected) == FIRST_SIZE
    assert int(large.context.selected.n_selected) == SECOND_SIZE
    assert int(small.run_plan.planned_epochs) == FIRST_HORIZON
    assert int(large.run_plan.planned_epochs) == SECOND_HORIZON
    assert len(small.training_frame_uids) < len(large.training_frame_uids)

    # (a) Every dimension the one controller assumes is shared, proved equal
    # over exactly those two positions - and the proof covers the dimensions
    # A17 names, not an arbitrary subset.
    small_profile = dict(runtime._post_selection_scheduler_profile(small))
    large_profile = dict(runtime._post_selection_scheduler_profile(large))
    assert small_profile == large_profile
    assert set(small_profile) == {
        "device",
        "optimizer device",
        "learned-model precision",
        "training method/model realization",
        "batch size",
        "loader workers per job",
        "training acceleration",
        "replay lineage",
        "concurrency policy and per-job RAM/VRAM estimates",
        "CPU/RAM/GPU allocation",
        "progress interval",
        "trainer/process-supervision owner",
    }

    # (b) The exact optimizer realization each position trained under: the
    # device-resident geometry is a function of configuration only, never of
    # membership size or horizon.
    def optimizer(task):
        return runtime._optimizer_policy_for(
            task.context,
            seed=task.run_plan.optimizer_seed,
            planned_epochs=task.run_plan.planned_epochs,
        )

    light, heavy = optimizer(small), optimizer(large)
    for field in ("device", "default_dtype", "batch_size", "valid_batch_size"):
        assert getattr(light, field) == getattr(heavy, field), field
    assert int(getattr(light, "num_workers", 0)) == int(getattr(heavy, "num_workers", 0))

    # (c) What the TRAIN2 runtime really received.  Removing the epoch budget,
    # the per-epoch structure count and the execution epoch limit leaves two
    # byte-identical runtime plans, so ``N`` and ``H_prod`` reach the runtime
    # only as work duration and epoch size.
    by_size = {
        int(request.materialization.target_train_artifact.configuration_count): request
        for request in harness.requests
    }
    assert sorted(by_size) == [FIRST_SIZE, SECOND_SIZE]
    light_request, heavy_request = by_size[FIRST_SIZE], by_size[SECOND_SIZE]
    assert int(light_request.plan.execution_epoch_limit) == FIRST_HORIZON
    assert int(heavy_request.plan.execution_epoch_limit) == SECOND_HORIZON
    assert int(light_request.plan.structures_per_epoch) < int(
        heavy_request.plan.structures_per_epoch
    )
    # ``optimizer_policy_digest`` is horizon-derived (the LR schedule spans the
    # frozen epoch budget) and is a scientific identity, not a resource fact:
    # every resource-relevant field of that same policy was proved equal in (b).
    assert light_request.plan.optimizer_policy_digest != (
        heavy_request.plan.optimizer_policy_digest
    )
    duration_only = {
        "budget_policy",
        "structures_per_epoch",
        "execution_epoch_limit",
        "optimizer_policy_digest",
    }
    assert {
        key: value
        for key, value in light_request.plan.to_dict().items()
        if key not in duration_only | {"content_digest"}
    } == {
        key: value
        for key, value in heavy_request.plan.to_dict().items()
        if key not in duration_only | {"content_digest"}
    }
    # The epoch budgets differ only in the frozen horizon itself.
    light_budget = light_request.plan.budget_policy.to_dict()
    heavy_budget = heavy_request.plan.budget_policy.to_dict()
    assert light_budget["planned_epochs"] != heavy_budget["planned_epochs"]
    horizon_derived = {"planned_epochs", "content_digest", "policy_digest"}
    assert {
        k: v for k, v in light_budget.items() if k not in horizon_derived
    } == {k: v for k, v in heavy_budget.items() if k not in horizon_derived}

    # (d) The one per-job quantity that genuinely scales with ``N`` is the
    # host-resident dataset the trainer constructs from the materialized
    # training set.  The serialized transport below is *descriptive transport
    # evidence only*: a serialized byte count is not a bound on the resident
    # memory of the real MACE process, and this test does not treat it as one.
    # The measured real-child rows are intentionally not applied to this fast
    # fixture's policy.  They remain bounded observations for the separate
    # counterfactual predicate test and for actual-run qualification.
    def transport_bytes(request) -> int:
        transport = request.materialization_directory / "target_train.extxyz"
        assert transport.is_file()
        return transport.stat().st_size

    assert transport_bytes(light_request) < transport_bytes(heavy_request)
    plan = spy.plans[0]["plan"]

    # (e) The planner's demand model saw the shared profile and the task count
    # and nothing else; ``N``, membership, seed and horizon are not among its
    # inputs at all.
    inputs = {key: value for key, value in spy.plans[0].items() if key != "plan"}
    assert set(inputs) == {
        "task_count",
        "device",
        "loader_workers_per_job",
        "resources",
        "policy",
        "gpu_sample",
    }
    assert inputs["task_count"] == 2
    for task in (small, large):
        assert inputs["policy"] == runtime._post_selection_training_concurrency_policy(
            task.context
        )
        assert inputs["device"] == str(task.context.method_policies.device)
        assert inputs["loader_workers_per_job"] == int(
            getattr(optimizer(task), "num_workers", 0)
        )
    # The per-job RAM/VRAM reservations are the configured size-independent
    # values, not anything derived from a task.
    assert plan.estimated_ram_bytes_per_job == int(
        inputs["policy"].estimated_ram_mib_per_job * _MIB
    )
    assert plan.estimated_gpu_bytes_per_job == int(
        inputs["policy"].estimated_gpu_memory_mib_per_job * _MIB
    )
    # The VRAM admission envelope is observed aggregate telemetry times the
    # configured fraction: a live device bound, independent of ``N``.
    assert plan.gpu_memory_observation == "telemetry"
    assert plan.baseline_gpu_used_bytes == int(inputs["gpu_sample"].used_bytes)
    assert plan.gpu_memory_budget_bytes == int(
        int(inputs["gpu_sample"].total_bytes) * inputs["policy"].gpu_memory_fraction
    )

    # (f) Rebuilding from the larger task's *resolved wave policy* reproduces
    # the captured plan.  This is a structural common-policy relation only;
    # it is not a claim that the configured estimate is empirically adequate
    # for production-scale workloads.
    homogeneous = training_parallel.build_training_concurrency_plan(
        task_count=2,
        device=str(large.context.method_policies.device),
        loader_workers_per_job=int(getattr(heavy, "num_workers", 0)),
        resources=inputs["resources"],
        policy=runtime._post_selection_training_concurrency_policy(large.context),
        gpu_sample=inputs["gpu_sample"],
    )
    assert homogeneous == plan


# --- A17 / R2A+R2B+R2C: bounded observations and a negative counterfactual --


@dataclasses.dataclass(frozen=True)
class _MeasuredTrainingDemand:
    """One externally measured peak resource demand of a real TRAIN2 child.

    These are bounded observations, not a universal production-adequacy
    qualification and not values derived from serialized transport size. Each
    row is the peak resident host memory and peak device memory of one real
    ``mdstats-mace-train`` child - the exact P5/MACE child boundary
    ``post_selection_execution`` spawns - driven over a materially
    representative TRAIN_REQUIRED production membership of the live LTA
    campaign, sampled externally from ``/proc/<pid>/status`` and confirmed by
    the kernel ``VmHWM`` high-water mark so no excursion between samples can be
    missed.  The full provenance is recorded in section 13 of
    ``workplans/active/MLFF_PRODUCTION_GLOBAL_TRAIN_SCHEDULER_REPAIR_WORKPLAN.md``.

    The measurement host's device is not the production target device, so these
    rows are bounded development observations for the D4 admission discussion,
    not a physical GPU qualification or universal production bound; final
    target-hardware qualification stays deferred.
    """

    label: str
    #: Target-head training configurations (the frozen ``N`` of the position).
    configurations: int
    #: Replay (``pt_head``) training configurations resident beside them.
    replay_configurations: int
    #: Atoms per configuration - uniform over the whole prepared frame pool.
    atoms_per_configuration: int
    #: Largest neighbour-list edge count over the membership at ``r_max=5.0``.
    max_edges_per_configuration: int
    #: Peak resident host memory of the owned child process tree.
    peak_host_rss_bytes: int
    #: Peak device memory the child held, as the aggregate telemetry the
    #: scheduler itself observes reports it (CUDA context + allocator reserve).
    peak_device_bytes: int


#: MACE 0.3.16 / torch 2.13.0+cu126, mace-mpa-0-medium foundation, multihead
#: finetuning with the campaign's own true-label replay views, float32,
#: batch_size=2, valid_batch_size=2, num_workers=0, enable_cueq=true,
#: amsgrad, ema=true - i.e. the exact pinned realization the live campaign's
#: own ``mace_run_config.yaml`` carries.  One true epoch each.
_MEASURED_PRODUCTION_DEMAND: tuple[_MeasuredTrainingDemand, ...] = (
    _MeasuredTrainingDemand(
        label="N=512 production membership",
        configurations=512,
        replay_configurations=10000,
        atoms_per_configuration=168,
        max_edges_per_configuration=4956,
        peak_host_rss_bytes=7003 * _MIB,
        peak_device_bytes=6152 * _MIB,
    ),
    _MeasuredTrainingDemand(
        label="N=8192 production membership",
        configurations=8192,
        replay_configurations=10000,
        atoms_per_configuration=168,
        max_edges_per_configuration=4956,
        peak_host_rss_bytes=9912 * _MIB,
        peak_device_bytes=5154 * _MIB,
    ),
)

_MEASURED_LIGHT, _MEASURED_HEAVY = _MEASURED_PRODUCTION_DEMAND


def _shipped_execution_default(key: str) -> float:
    """One ``[execution]`` default as the shipped configuration owner writes it."""

    template = cli._config_template(
        workspace="/tmp/a17",
        training_root="/tmp/a17/dataset",
        foundation_model="/tmp/a17/foundation.model",
        foundation_family="mace_mpa_0",
    )
    values = [
        line.split("=", 1)[1].strip()
        for line in template.splitlines()
        if line.startswith(f"{key} =")
    ]
    assert len(values) == 1, f"{key} must have exactly one shipped default"
    return float(values[0])


def _production_default_policy() -> training_parallel.TrainingConcurrencyPolicy:
    """The shipped-default policy used only by the negative counterfactual.

    Three owners publish it - the ``TrainingConcurrencyPolicy`` dataclass
    defaults, the generated campaign template, and the runtime resolver's
    fallbacks - and the counterfactual is only meaningful if they agree.  This
    helper is not an oracle for the real wave, whose fixture explicitly uses
    ``_FAST_CONTROL``.
    """

    policy = training_parallel.TrainingConcurrencyPolicy()
    assert float(policy.estimated_ram_mib_per_job) == _shipped_execution_default(
        "estimated_training_ram_mib_per_job"
    )
    assert float(
        policy.estimated_gpu_memory_mib_per_job
    ) == _shipped_execution_default("estimated_training_vram_mib_per_job")
    return policy


@dataclasses.dataclass(frozen=True)
class _A17Verdict:
    closed: bool
    reasons: tuple[str, ...]
    controller_estimate_bytes: int
    predicted_device_bytes: int


def _a17_next_admission_verdict(
    *,
    plan,
    policy,
    controller_estimate_bytes: int,
    heavier: _MeasuredTrainingDemand,
    resources,
) -> _A17Verdict:
    """Judge a counterfactual admission against an independent heavier bound.

    ``controller_estimate_bytes`` is read back from the *real* controller (it is
    the ``memory_estimate`` that ``AdaptiveTrainingConcurrency.observe``
    computes as ``max(stable observed per job, configured per-job estimate)``);
    nothing here re-implements that relation.  What this function adds is the
    question the controller cannot ask for itself: would that estimate bound
    the independently measured demand of the task that is about to be admitted?
    This helper is evidence about predicate discrimination only, not about the
    actual fast-control production wave or universal production adequacy.
    """

    reasons: list[str] = []
    if int(heavier.peak_device_bytes) > int(controller_estimate_bytes):
        reasons.append(
            f"{heavier.label} needs {heavier.peak_device_bytes / _GIB:.2f} GiB of "
            f"device memory but the controller reserves only "
            f"{controller_estimate_bytes / _GIB:.2f} GiB per job"
        )
    if int(heavier.peak_host_rss_bytes) > int(plan.estimated_ram_bytes_per_job):
        reasons.append(
            f"{heavier.label} needs {heavier.peak_host_rss_bytes / _GIB:.2f} GiB of "
            f"resident host memory but the common per-job RAM estimate is "
            f"{plan.estimated_ram_bytes_per_job / _GIB:.2f} GiB"
        )
    candidate_jobs = 2
    predicted = int(plan.baseline_gpu_used_bytes or 0) + math.ceil(
        candidate_jobs
        * int(controller_estimate_bytes)
        * float(policy.observed_memory_growth_margin)
    )
    if predicted >= int(plan.gpu_memory_budget_bytes):
        reasons.append(
            f"projected aggregate VRAM {predicted / _GIB:.2f} GiB at "
            f"{candidate_jobs} jobs reaches the "
            f"{plan.gpu_memory_budget_bytes / _GIB:.2f} GiB envelope"
        )
    if candidate_jobs * int(heavier.peak_host_rss_bytes) > int(
        resources.ram_budget_bytes
    ):
        reasons.append("two measured host-RAM peaks exceed the host RAM budget")
    return _A17Verdict(
        closed=not reasons,
        reasons=tuple(reasons),
        controller_estimate_bytes=int(controller_estimate_bytes),
        predicted_device_bytes=int(predicted),
    )


def _calibrate_observed_device_then_estimate(
    plan,
    policy,
    *,
    observed_device_bytes: int,
    utilization_percent: float = 40.0,
) -> tuple[object, object]:
    """Run the real controller through one bounded calibration window.

    The caller supplies a bounded control observation so this helper exercises
    the existing promotion relation.  It is not a resource-qualification
    harness and does not establish a task's empirical RAM/VRAM demand.
    """

    controller = training_parallel.AdaptiveTrainingConcurrency(plan, policy)
    baseline = int(plan.baseline_gpu_used_bytes or 0)
    aggregate = baseline + int(observed_device_bytes)
    start = 1_000.0
    decision = None
    step = float(policy.monitor_interval_seconds)
    for index in range(40):
        now = start + index * step
        decision = controller.observe(
            GpuTelemetrySample(
                sampled_monotonic=now,
                device_index=0,
                utilization_percent=utilization_percent,
                used_bytes=aggregate,
                total_bytes=24 * _GIB,
            ),
            active_jobs=1,
            epoch_active_jobs=1,
            now=now,
        )
        if decision.target_jobs > 1:
            break
    return controller, decision


def test_lighter_first_admission_bounds_the_heavier_next_production_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A17 structural check: lighter first, heavier next, one resolved policy.

    The development gate is that the real production wave has one resolved
    resource policy/plan and that its existing controller can promote from a
    common observation relation without learning selected-size or task
    identity.  This deliberately does not judge empirical production RAM/VRAM
    adequacy: the fixture's ``_FAST_CONTROL`` policy is the policy under test,
    and the long measured resource observations remain bounded evidence for
    actual-run qualification.

    Two independent structural facts are joined here, and neither substitutes
    for the other:

    * the **ordering and sharing** facts come from the real wave below - which
      position is admitted first, that the next admission is the heavier one,
      and that both are planned by one ``TrainingConcurrencyPlan`` built from
      one policy;
    * the **promotion** fact comes from the captured wave plan/policy and the
      existing ``AdaptiveTrainingConcurrency`` relation.

    The independently measured resource rows are intentionally not used as a
    positive judgment about this fast fixture's wave.
    """

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    admitted: list[int] = []
    real_wave = runtime._train_post_selection_pending_runs

    def observed(pending, **kwargs):
        admitted.extend(int(task.context.selected.n_selected) for task in pending)
        return real_wave(pending, **kwargs)

    monkeypatch.setattr(runtime, "_train_post_selection_pending_runs", observed)
    harness = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, harness) == 0

    # (1) The lighter position is the first admission and the heavier position
    # is the next one: deterministic queueing follows the frozen size order, so
    # the risky ordering is the one production actually takes.
    assert admitted == [FIRST_SIZE, SECOND_SIZE]
    assert len(spy.plans) == 1 and len(spy.controllers) == 1
    wave_plan = spy.plans[0]["plan"]
    wave_policy = spy.plans[0]["policy"]
    assert int(wave_plan.task_count) == 2

    # (2) The wave consumed the campaign's resolved policy, including the
    # deliberately small fast-test RAM reservation.  This prevents a default
    # policy/plan constructed outside the wave from becoming its oracle.
    wave_contexts = _contexts(config)[2]
    assert all(
        runtime._post_selection_training_concurrency_policy(context) == wave_policy
        for context in wave_contexts
    )
    assert float(wave_policy.estimated_ram_mib_per_job) == 512.0
    assert wave_plan.estimated_ram_bytes_per_job == 512 * _MIB
    assert wave_plan.gpu_memory_observation == "telemetry"
    assert set(spy.plans[0]) == {
        "task_count",
        "device",
        "loader_workers_per_job",
        "resources",
        "policy",
        "gpu_sample",
        "plan",
    }

    # (3) Drive the existing controller with a bounded control observation and
    # read back the exact estimate it promotes on.  The observation is only a
    # control input; it is not a measured bound for either production task.
    observed_device_bytes = int(wave_plan.estimated_gpu_bytes_per_job) + _GIB
    controller, decision = _calibrate_observed_device_then_estimate(
        wave_plan,
        wave_policy,
        observed_device_bytes=observed_device_bytes,
    )
    assert decision is not None
    assert int(decision.target_jobs) == 2, decision.reason
    estimate = int(decision.observed_bytes_per_job)
    # This is the promotion relation itself, not a re-derivation of it: the
    # controller's own estimate equals max(stable observed per job, configured).
    stable_per_job = observed_device_bytes
    assert estimate == max(
        stable_per_job, int(wave_plan.estimated_gpu_bytes_per_job)
    )

    # (4) The wave really did consume one common estimate regime.  No selected
    # size, seed, membership, or horizon appears in the controller inputs.
    assert int(wave_plan.estimated_ram_bytes_per_job) == int(
        wave_policy.estimated_ram_mib_per_job * _MIB
    )


def test_a17_is_not_closable_when_a_heavier_task_exceeds_the_common_estimate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A17/R2C negative: predicate discrimination is the bound, not the plan.

    Nothing about the policy, the plan or the telemetry changes here.  Only the
    heavier task's independently established demand does, and that alone must
    make the acceptance report A17 open.  This is what proves the positive case
    above is discriminating rather than tautological - equality of
    ``TrainingConcurrencyPolicy``, equality of ``TrainingConcurrencyPlan`` and a
    common synthetic telemetry trace are all held fixed across the two cases.

    No production OOM is manufactured: the counterfactual stops at the
    compatibility/evidence boundary.  This does not qualify the real wave,
    whose fixture deliberately uses ``_FAST_CONTROL`` rather than the shipped
    defaults.
    """

    policy = _production_default_policy()
    plan = training_parallel.build_training_concurrency_plan(
        task_count=2,
        device="cuda:0",
        loader_workers_per_job=0,
        resources=_resources(),
        policy=policy,
        gpu_sample=_safe_sample(),
    )
    controller, decision = _calibrate_observed_device_then_estimate(
        plan,
        policy,
        observed_device_bytes=int(_MEASURED_LIGHT.peak_device_bytes),
    )
    estimate = int(decision.observed_bytes_per_job)

    admissible = _a17_next_admission_verdict(
        plan=plan,
        policy=policy,
        controller_estimate_bytes=estimate,
        heavier=_MEASURED_HEAVY,
        resources=_resources(),
    )
    assert admissible.closed

    # One counterfactual heavier task per resource axis; the common estimate is
    # untouched, so each failure is attributable to the bound alone.
    heavier_on_device = dataclasses.replace(
        _MEASURED_HEAVY,
        label="counterfactual device-heavier membership",
        peak_device_bytes=estimate + 1 * _GIB,
    )
    device_verdict = _a17_next_admission_verdict(
        plan=plan,
        policy=policy,
        controller_estimate_bytes=estimate,
        heavier=heavier_on_device,
        resources=_resources(),
    )
    assert not device_verdict.closed
    assert any("device memory" in reason for reason in device_verdict.reasons)
    assert device_verdict.controller_estimate_bytes == admissible.controller_estimate_bytes

    heavier_on_host = dataclasses.replace(
        _MEASURED_HEAVY,
        label="counterfactual host-heavier membership",
        peak_host_rss_bytes=int(plan.estimated_ram_bytes_per_job) + 1 * _GIB,
    )
    host_verdict = _a17_next_admission_verdict(
        plan=plan,
        policy=policy,
        controller_estimate_bytes=estimate,
        heavier=heavier_on_host,
        resources=_resources(),
    )
    assert not host_verdict.closed
    assert any("resident host memory" in reason for reason in host_verdict.reasons)

    # The plan and policy are provably identical across all three judgements,
    # so neither could have been the discriminator.
    for other in (heavier_on_device, heavier_on_host):
        assert other.configurations == _MEASURED_HEAVY.configurations
        assert other.atoms_per_configuration == _MEASURED_HEAVY.atoms_per_configuration
    assert plan == training_parallel.build_training_concurrency_plan(
        task_count=2,
        device="cuda:0",
        loader_workers_per_job=0,
        resources=_resources(),
        policy=policy,
        gpu_sample=_safe_sample(),
    )


# --- A15: duplicate global identity fails closed ---------------------------


def test_a_duplicate_global_run_identity_fails_before_any_trainer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    real_builder = runtime.build_final_production_run_plan
    built: list[object] = []

    def colliding(plan, *, optimizer_seed):
        run_plan = real_builder(plan, optimizer_seed=optimizer_seed)
        built.append(run_plan)
        # The second size's position resolves to the first size's run.
        return built[0]

    monkeypatch.setattr(runtime, "build_final_production_run_plan", colliding)
    harness = fx.PostSelectionHarness()
    with pytest.raises(Exception, match="same run identity"):
        fx.run_train_production(config, harness)
    assert harness.runs == []
    assert spy.plans == []
    assert _final_plan_digests(config) == [None, None]


# --- A16: public cross-validation is unchanged ------------------------------


class _CvOrderHarness(fx.PostSelectionHarness):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lock = threading.Lock()
        self.windows: list[tuple[int, float, float]] = []

    def train(self, request):
        started = time.monotonic()
        count = int(request.materialization.target_train_artifact.configuration_count)
        try:
            with self.lock:
                return super().train(request)
        finally:
            self.windows.append((count, started, time.monotonic()))


def test_cross_validation_keeps_its_outer_serial_selected_size_wave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A16: CV still runs one per-size wave at a time, with no global queue."""

    from unittest.mock import patch

    config_text = fx.fixture_config_text() + _FAST_CONTROL
    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    for size, horizon in ((FIRST_SIZE, FIRST_HORIZON), (SECOND_SIZE, SECOND_HORIZON)):
        assert (
            p4d._run(
                config,
                "select-target-size",
                str(size),
                "--horizon",
                str(horizon),
                _external_boundary_trainer=_PoisonTrainer(),
                _external_inference_evaluator=_PoisonTrainer(),
            )
            == 0
        )
    _bind_bounded_device(monkeypatch)
    spy = _SchedulerSpy(monkeypatch)
    harness = _CvOrderHarness()
    assert fx.run_cross_validate(config, harness) == 0

    # One wave per selected size, each sized by that size's own fold/seed
    # matrix - never one collection-global CV queue.
    assert [item["task_count"] for item in spy.plans] == [2, 2]
    assert len(spy.controllers) == 2
    # Four folds ran as two waves of two. Each fold trains on its own size's
    # partition of ``T_N``, so the two waves are distinguishable by their fold
    # training counts, and the earlier wave must finish before the later one
    # starts.
    ordered = sorted(harness.windows, key=lambda window: window[1])
    assert len(ordered) == 4
    first, second = ordered[:2], ordered[2:]
    assert max(end for _n, _s, end in first) <= min(
        start for _n, start, _e in second
    ), "cross-validation interleaved selected sizes"
    assert {count for count, _s, _e in first} != {count for count, _s, _e in second}
    assert sum(count for count, _s, _e in ordered) == FIRST_SIZE + SECOND_SIZE
    for context in _contexts(config)[2]:
        acceptance = runtime.resolve_current_cv_acceptance(context)
        assert acceptance is not None and acceptance.accepted


# --- A19: generation rollover is linearized against every admission ---------


def _commit_generation_rollover(config: Path) -> None:
    """Retire the frozen design through the real `prepare` transition owner."""

    fx.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0


def _campaign_generation(config: Path) -> int:
    from mdstats.training_data.campaign_target_size_state import (
        load_target_size_campaign_revision,
    )

    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return int(load_target_size_campaign_revision(store).state.generation)
    finally:
        store.close()


class _AdmissionRace:
    """Pause at the real serialized admission boundary and act there.

    The fence itself stays the production owner: this seam only decides *when*
    a competing campaign transition commits relative to one exact admission,
    which is the ordering a wall-clock test cannot pin down.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        at_call: int,
        when: str,
        action,
    ) -> None:
        from contextlib import contextmanager

        self.calls = 0
        self.acted = False
        real = runtime.post_selection_collection_admission

        @contextmanager
        def fenced(store, *, signature):
            self.calls += 1
            mine = self.calls == int(at_call)
            if mine and when == "before":
                action()
                self.acted = True
            with real(store, signature=signature):
                yield
            if mine and when == "after":
                action()
                self.acted = True

        monkeypatch.setattr(runtime, "post_selection_collection_admission", fenced)


class _StopAwareHarness(fx.PostSelectionHarness):
    """Stay alive under scheduler ownership until cancelled."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lock = threading.Lock()
        self.stopped: list[str] = []
        self.entered = threading.Event()

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        with self.lock:
            self.runs.append(identity)
        if request.progress_observer is not None:
            request.progress_observer({"true_epoch": True, "phase": "training"})
        self.entered.set()
        stop = request.cancellation_event
        assert stop is not None
        deadline = time.monotonic() + 120.0
        while not stop.is_set():
            if time.monotonic() > deadline:
                raise AssertionError("the stale wave never cancelled its owned child")
            time.sleep(0.01)
        with self.lock:
            self.stopped.append(identity)
        raise PostSelectionCancelledError("Post-selection MACE training was cancelled.")


def test_rollover_winning_the_admission_boundary_admits_no_further_train2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A19(1): the queued old-generation task is never submitted."""

    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    _bind_bounded_device(monkeypatch)
    race = _AdmissionRace(
        monkeypatch,
        at_call=2,
        when="before",
        action=lambda: _commit_generation_rollover(config),
    )
    harness = _StopAwareHarness()
    with pytest.raises(PostSelectionStaleBindingError, match="no longer current"):
        fx.run_train_production(config, harness)
    assert race.acted
    assert len(harness.runs) == 1, harness.runs
    assert harness.stopped == harness.runs, "the owned worker was not cancelled/reaped"
    assert harness.evaluations == [], "EVAL2 began for a retired design"


def test_admission_winning_the_boundary_settles_and_then_stops_admitting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A19(2): work admitted before rollover settles; nothing else is admitted."""

    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    _bind_bounded_device(monkeypatch)
    race = _AdmissionRace(
        monkeypatch,
        at_call=2,
        when="after",
        action=lambda: _commit_generation_rollover(config),
    )
    harness = _ConcurrentProductionHarness(expected_width=2)
    runs = _runs_root(config)
    with pytest.raises(PostSelectionStaleBindingError):
        fx.run_train_production(config, harness)
    assert race.acted
    # Exactly the two tasks admitted before the rollover ran, and they reached
    # their authenticated sealed TRAIN2 roots as ordinary owned work.
    assert len(harness.runs) == 2, harness.runs
    assert harness.evaluations == []
    for identity in harness.runs:
        assert runtime.read_post_selection_run_completion(runs / identity)[0] is not None


def test_rollover_before_the_finalization_admission_starts_no_eval2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A19(3): the EVAL/finalization phase has its own linearization point."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    assert fx.run_train_production(config, _ConcurrentProductionHarness()) == 0

    race = _AdmissionRace(
        monkeypatch,
        at_call=1,
        when="before",
        action=lambda: _commit_generation_rollover(config),
    )
    harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionStaleBindingError):
        fx.run_train_production(config, harness)
    assert race.acted and race.calls == 1
    assert harness.runs == []
    assert harness.evaluations == [], "EVAL2 began after the design was retired"


def test_finalization_admitted_first_still_cannot_publish_stale_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A19(4): commit-time per-binding fences remain authoritative."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    assert fx.run_train_production(config, _ConcurrentProductionHarness()) == 0

    race = _AdmissionRace(
        monkeypatch,
        at_call=1,
        when="after",
        action=lambda: _commit_generation_rollover(config),
    )
    harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionStaleBindingError) as failure:
        fx.run_train_production(config, harness)
    assert race.acted and race.calls == 1
    assert harness.runs == []
    # The finalization phase was admitted (the serialized fence passed) and
    # ran; what refuses the result is the existing commit-time per-binding
    # publication fence, whose message is distinct from the admission fence's.
    assert "became current while this post-selection work was running" in str(
        failure.value
    ), str(failure.value)


def test_a_same_generation_revision_does_not_cancel_the_wave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A19: only a changed `(generation, ordered bindings)` retires the queue."""

    config = _two_size_campaign(tmp_path)
    _bind_bounded_device(monkeypatch)
    before = _campaign_generation(config)

    def unchanged_prepare() -> None:
        assert p4d._run(config, "prepare") == 0

    race = _AdmissionRace(
        monkeypatch, at_call=1, when="before", action=unchanged_prepare
    )
    harness = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config, harness) == 0
    assert race.acted
    assert _campaign_generation(config) == before
    for context in _contexts(config)[2]:
        assert resolve_current_final_production_publication(context) is not None


# --- A4: execution width is not a scientific input --------------------------


def _prepared_ancestry(config: Path) -> list[dict]:
    """The frozen design and accepted CV ancestry a campaign enters production with."""

    _cfg, _paths, contexts = _contexts(config)
    ancestry = []
    for context in contexts:
        acceptance = runtime.resolve_current_cv_acceptance(context)
        plan = runtime.resolve_current_cv_plan(context)
        assert acceptance is not None and acceptance.accepted and plan is not None
        ancestry.append(
            {
                "n_selected": int(context.selected.n_selected),
                "binding": context.selected.binding.content_digest,
                "method": context.method.content_digest,
                "cv_plan": plan.content_digest,
                "cv_acceptance": acceptance.content_digest,
            }
        )
    return ancestry


def test_fresh_serial_and_fresh_concurrent_production_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A4: two isolated, identically prepared campaigns, two execution widths.

    Campaign A executes fresh production at effective width exactly 1.
    Campaign B executes *fresh* production through the same real collection
    scheduler at a width that genuinely admits overlapping TRAIN2 jobs - the
    bounded child in B blocks until the wave really owns two simultaneous
    trainers, so the concurrency is executed rather than merely configured.

    Neither arm reuses the other's evidence: both train every position from
    nothing.  After canonical ordering (frozen selected-size order, then
    ``required_final_seeds`` order) every governed scientific identity and
    every piece of deterministic evidence must agree, while the width itself
    appears nowhere in them.
    """

    import shutil

    # Both campaigns are built, independently and from nothing, at the *same*
    # absolute workspace path, one after the other.  Run-local materialization
    # records legitimately carry their own absolute output directory, so this
    # keeps the comparison an exact identity comparison rather than one that
    # has to normalize workspace location away.
    arena = tmp_path / "arena"
    arena.mkdir()
    _bind_bounded_device(monkeypatch)

    config_a = _two_size_campaign(arena, production_seeds="[5, 6]")
    ancestry = _prepared_ancestry(config_a)
    fx.rewrite_config(
        config_a,
        "maximum_parallel_training_jobs = 4",
        "maximum_parallel_training_jobs = 1",
    )
    serial_spy = _SchedulerSpy(monkeypatch)
    serial = fx.PostSelectionHarness()
    assert fx.run_train_production(config_a, serial) == 0
    assert [item["plan"].maximum_jobs for item in serial_spy.plans] == [1]
    assert len(serial.runs) == 4, "the serial arm must execute fresh production"
    serial_identities = _governed_identities(config_a)

    shutil.move(str(arena), str(tmp_path / "serial-arm"))
    arena.mkdir()
    config_b = _two_size_campaign(arena, production_seeds="[5, 6]")
    assert config_b == config_a
    # Identically prepared: same frozen bindings, memberships, horizons and
    # accepted CV ancestry, established independently in each campaign.
    assert _prepared_ancestry(config_b) == ancestry

    wide_spy = _SchedulerSpy(monkeypatch)
    wide = _ConcurrentProductionHarness(expected_width=2)
    assert fx.run_train_production(config_b, wide) == 0
    assert len(wide.runs) == 4, "the concurrent arm must execute fresh production"
    assert len(wide_spy.plans) == 1 and len(wide_spy.controllers) == 1
    assert wide_spy.plans[0]["plan"].maximum_jobs > 1
    assert wide.max_active >= 2

    # The concurrent arm really overlapped two fresh TRAIN2 jobs in the one
    # collection wave, rather than draining a queue one position at a time.
    overlaps = [
        (left[0], right[0])
        for index, left in enumerate(wide.windows)
        for right in wide.windows[index + 1 :]
        if left[1] < right[2] and right[1] < left[2]
    ]
    assert overlaps, wide.windows

    # Width, queue order and timing are execution-only: every governed
    # identity and every deterministic evidence item agrees after canonical
    # ordering (frozen size order, then required-seed order), and the differing
    # width appears in none of them.
    assert _governed_identities(config_b) == serial_identities


def test_reusing_sealed_roots_across_a_width_change_retrains_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Completed evidence survives an execution-only width change.

    This is a reuse/restart property, not the serial/concurrent equivalence
    proof: the second invocation legitimately launches no trainer at all.
    """

    config = _two_size_campaign(tmp_path, production_seeds="[5, 6]")
    fx.rewrite_config(
        config, "maximum_parallel_training_jobs = 4", "maximum_parallel_training_jobs = 1"
    )
    _bind_bounded_device(monkeypatch)
    serial_spy = _SchedulerSpy(monkeypatch)
    serial = fx.PostSelectionHarness()
    assert fx.run_train_production(config, serial) == 0
    assert [item["plan"].maximum_jobs for item in serial_spy.plans] == [1]
    assert len(serial.runs) == 4
    serial_identities = _governed_identities(config)

    fx.rewrite_config(
        config, "maximum_parallel_training_jobs = 1", "maximum_parallel_training_jobs = 4"
    )
    wide_spy = _SchedulerSpy(monkeypatch)
    wide = fx.PostSelectionHarness()
    assert fx.run_train_production(config, wide) == 0
    assert wide.runs == [], "a wider width retrained an authenticated root"
    assert wide_spy.plans == [], "sealed positions were scheduled again"
    assert _governed_identities(config) == serial_identities


def _governed_identities(config: Path) -> list[dict]:
    """Every scheduler-independent identity a finished collection publishes."""

    _cfg, _paths, contexts = _contexts(config)
    collected: list[dict] = []
    for context in contexts:
        plan = runtime.resolve_current_final_production_plan(context)
        assert plan is not None
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
        seeds = []
        for seed in plan.required_final_seeds:
            run_plan = runtime.build_final_production_run_plan(plan, optimizer_seed=seed)
            assessment = runtime.resolve_current_final_seed_assessment(context, run_plan)
            assert assessment is not None
            seeds.append(
                {
                    "run_identity": run_plan.run_identity,
                    "trajectory": run_plan.training_trajectory_identity,
                    "assessment": assessment.content_digest,
                    "root": assessment.training_root_identity,
                    # The complete deterministic evidence the bounded trainer
                    # seam produced: selected checkpoint, measurements, policy
                    # ancestry and the training materialization it bound.
                    "evidence": assessment.to_dict(),
                }
            )
        collected.append(
            {
                "binding": context.selected.binding.content_digest,
                "final_plan": plan.content_digest,
                "publication": decision.content_digest,
                "decision": decision.to_dict(),
                "seeds": seeds,
            }
        )
    return collected


# --- Structural acceptance --------------------------------------------------


def test_structural_ownership_of_the_production_train_wave() -> None:
    """The retired per-size production scheduler owner is gone, not wrapped."""

    import ast
    import inspect

    source = Path(runtime.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    # No per-size production execution owner survives beside the collection one.
    assert "execute_final_production" not in functions
    assert not hasattr(runtime, "execute_final_production")

    # Exactly one construction site for the adaptive TRAIN controller and its
    # plan, and both live in the one shared scheduler.
    for name in ("AdaptiveTrainingConcurrency", "build_training_concurrency_plan"):
        sites = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
        ]
        assert len(sites) == 1, (name, len(sites))
    scheduler = inspect.getsource(runtime._train_post_selection_pending_runs)
    assert "AdaptiveTrainingConcurrency(" in scheduler
    assert "build_training_concurrency_plan(" in scheduler

    # The shared wave is TRAIN-only: it never evaluates, assesses or publishes.
    for forbidden in (
        "evaluate_post_selection_run_candidates",
        "publish_post_selection_run_measurements",
        "publish_current_post_selection_pointer",
        "PostSelectionRunEvidence",
    ):
        assert forbidden not in scheduler, forbidden
    assert "stop_after_training=True" in scheduler

    # The ownership transition happens inside the serialized admission fence:
    # a read followed by a later submit would reopen the TOCTOU window.
    submit_available = next(
        node
        for node in ast.walk(functions["_train_post_selection_pending_runs"])
        if isinstance(node, ast.FunctionDef) and node.name == "submit_available"
    )
    fenced = [
        node
        for node in ast.walk(submit_available)
        if isinstance(node, ast.With)
        and any(
            isinstance(item.context_expr, ast.IfExp) for item in node.items
        )
    ]
    assert len(fenced) == 1, "the admission fence is not a single with-block"
    fenced_calls = {
        child.func.attr
        for child in ast.walk(fenced[0])
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
    }
    assert {"popleft", "submit"} <= fenced_calls, fenced_calls
    assert not [
        node
        for node in ast.walk(submit_available)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit"
        and node not in list(ast.walk(fenced[0]))
    ]

    # The command adds no executor, pool or second scheduler of its own.
    command = functions["execute_current_train_production"]
    called = {
        child.func.attr if isinstance(child.func, ast.Attribute) else child.func.id
        for child in ast.walk(command)
        if isinstance(child, ast.Call) and isinstance(child.func, (ast.Name, ast.Attribute))
    }
    assert not (
        called
        & {"ThreadPoolExecutor", "ProcessPoolExecutor", "Pool", "Thread", "Process", "submit"}
    )
    # Public cross-validation keeps its own per-size composition.
    cv = inspect.getsource(runtime.execute_post_selection_cross_validation)
    assert "_run_post_selection_positions(" in cv
    assert "_train_final_production_collection" not in cv

    # The wave key is execution-only: no scientific digest consumes it.
    for name in ("_plan_final_production", "_train_final_production_collection"):
        body = inspect.getsource(getattr(runtime, name))
        assert ".key" not in body.replace("first_key + slot", "")
