"""Assembled acceptance: one collection-wide production TRAIN wave.

Everything here is driven through the real public ``train-production`` command
(and the real ``cross-validate`` that must precede it).  Only MACE numerics and
the device telemetry probe are substituted, strictly below the P5 owner
boundary, and the telemetry substitution is bounded and deterministic because
the claim *is* resource-admission semantics.  No GPU qualification is claimed:
the campaign stays scientifically CPU-configured and the synthetic device facts
exist only to exercise the existing adaptive admission branch.

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

import json
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


def test_serial_and_concurrent_widths_produce_identical_governed_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A4: width changes queueing only.

    The first invocation runs the whole collection strictly serially; the
    second re-plans, re-authenticates and re-finalizes the same collection
    with a wider effective width.  Every governed identity available to the
    deterministic double - final plans, run/trajectory identities, assessment
    positions, seed assessments and per-size publications - must be identical,
    and the wider invocation must not retrain a single root.
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
                }
            )
        collected.append(
            {
                "binding": context.selected.binding.content_digest,
                "final_plan": plan.content_digest,
                "publication": decision.content_digest,
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
