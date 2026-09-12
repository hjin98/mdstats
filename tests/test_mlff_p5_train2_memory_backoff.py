"""Real-owner acceptance for TRAIN2 memory-pressure backoff.

The governed owner is the pair
``training_parallel.AdaptiveTrainingConcurrency`` (the admission/backoff
decision) and
``campaign_post_selection_runtime._execute_post_selection_pending_runs`` (owned
TRAIN2 lifetime, per-job demotion, teardown, requeue and accounting). Both are
driven here through the real cross-validation caller; only MACE numerics and the
device telemetry probe are substituted, and the telemetry substitution is
bounded and deterministic because the claim *is* resource-control semantics.

The governed propositions are:

1. a sustained soft-envelope violation at owned concurrency ``N > 1`` demotes
   exactly one owned job - the most recently admitted one - instead of
   cancelling the wave;
2. the surviving job continues, the demoted task returns to the pending
   queue, and every planned fold still completes exactly once;
3. the demoted worker's own completion, not a future cancellation request, is
   the barrier before the slot is reused;
4. a disproven concurrency level is not re-entered in the same execution;
5. one owned job over the soft envelope holds rather than terminating;
6. a genuine authoritative failure is still raised rather than swallowed;
7. foreign occupancy constrains owned concurrency without mdstats claiming
   ownership of foreign processes.
"""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fx

from mdstats.training_data.campaign_post_selection_runtime import (
    resolve_current_cv_acceptance,
)

_GIB = 1024 ** 3


def _selected_campaign(
    tmp_path: Path, *, execution: str = "", fold_count: int | None = None
) -> Path:
    config_text = fx.fixture_config_text()
    if fold_count is not None:
        config_text = config_text.replace(
            "fold_count = 2", f"fold_count = {int(fold_count)}"
        )
    if execution:
        config_text = f"{config_text}\n[execution]\n{execution}\n"
    config, _workspace = fx.build_selected_campaign(tmp_path, config_text=config_text)
    return config


#: Small enough that promotion and two consecutive control observations happen
#: inside a short test, and identical in structure to the operator defaults.
_FAST_CONTROL = "\n".join(
    (
        "parallel_training_monitor_interval_seconds = 0.05",
        "parallel_training_epoch_stabilization_seconds = 0.0",
        "parallel_training_epoch_stability_samples = 2",
        "training_progress_interval_seconds = 0.05",
        # Host RAM is not the claim here and its live budget varies with
        # whatever else the machine is doing; pin the per-job reservation so the
        # planned ceiling is decided by the VRAM semantics under test.
        "estimated_training_ram_mib_per_job = 512.0",
    )
)


def _install_telemetry(monkeypatch, probe) -> None:
    """Bind the bounded deterministic device probe to the owning module."""

    from mdstats.training_data import training_parallel

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", probe)


def _cuda_cv_context(config: Path, harness):
    """Build the real post-selection context, bound to a CUDA device policy."""

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
    )

    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    context = build_post_selection_contexts(
        cfg,
        paths,
        store,
        trainer=harness,
        inference_evaluator=harness.evaluate,
        admit=True,
    )[0]
    return (
        replace(
            context,
            method_policies=replace(context.method_policies, device="cuda:0"),
        ),
        store,
    )


def _sample(used_gib: float, utilization: float, total_gib: float = 24.0):
    from mdstats.training_data.training_parallel import GpuTelemetrySample

    return GpuTelemetrySample(
        sampled_monotonic=time.monotonic(),
        device_index=0,
        utilization_percent=utilization,
        used_bytes=int(used_gib * _GIB),
        total_bytes=int(total_gib * _GIB),
    )


class _OccupancyHarness(fx.PostSelectionHarness):
    """A child whose accelerator occupancy and stop response are observable.

    It plays the part the real MACE child plays for the scheduler: it reports
    optimizer activity through the existing progress observer, it honours the
    per-job cooperative stop handle the scheduler hands it, and it stays alive
    until the scheduler has had the chance to judge live telemetry.
    """

    #: Aggregate GiB by owned active-job count. The one-job value is optimistic
    #: enough for the controller to project a safe next job; the value at the
    #: peak proves that projection wrong, which is the observed defect (INV-9).
    OCCUPANCY_GIB = {0: 0.4, 1: 10.0, 2: 22.2}

    def __init__(
        self,
        *,
        partial_stop_victim: bool = False,
        sticky_pressure: bool = False,
        occupancy_gib_by_active: dict[int, float] | None = None,
        peak_jobs: int = 2,
        failing_victim: bool = False,
        teardown_delay_seconds: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        #: The demotion victim raises an unrelated authoritative failure at the
        #: stop boundary instead of the owner's cancellation outcome.
        self._failing_victim = bool(failing_victim)
        #: How long the child takes to reap and finalize after observing its
        #: stop, i.e. deliberately not instantaneous teardown.
        self._teardown_delay_seconds = float(teardown_delay_seconds)
        #: Occupancy that does not fall back when concurrency does, i.e. the
        #: demoted worker's memory was not reclaimed.
        self._sticky_pressure = bool(sticky_pressure)
        self._occupancy = dict(occupancy_gib_by_active or self.OCCUPANCY_GIB)
        #: The owned concurrency this fixture drives the controller up to.
        self.peak_jobs = int(peak_jobs)
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        #: Admission order of run identities, first attempt first.
        self.order: list[str] = []
        #: Identities that observed their own cooperative stop signal.
        self.stopped: list[str] = []
        #: (identity, attempt) -> (entered, exited) monotonic window.
        self.windows: dict[tuple[str, int], tuple[float, float]] = {}
        self.attempts: dict[str, int] = {}
        self.start_epochs: dict[tuple[str, int], int] = {}
        self._peaked = threading.Event()
        self._partial_stop_victim = bool(partial_stop_victim)
        #: A child never finishes before the fixture has driven the scheduler to
        #: its peak concurrency; expiry is a fixture failure, never a silent
        #: completion that would turn into a cryptic downstream assertion.
        self.deadline_seconds = 180.0

    def occupancy_gib(self) -> float:
        with self.lock:
            active = self.active
            peaked = self._peaked.is_set()
        if active <= 0:
            return self._occupancy[0]
        if self._sticky_pressure and peaked:
            return self._occupancy[self.peak_jobs]
        return self._occupancy[min(active, self.peak_jobs)]

    def train(self, request):
        identity = str(request.run_plan.run_identity)
        entered = time.monotonic()
        with self.lock:
            attempt = self.attempts.get(identity, 0) + 1
            self.attempts[identity] = attempt
            if attempt == 1:
                self.order.append(identity)
            victim = (
                self._partial_stop_victim
                and attempt == 1
                and len(self.order) == self.peak_jobs
            )
            self.start_epochs[(identity, attempt)] = int(request.start_epoch)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active >= self.peak_jobs:
                self._peaked.set()
        try:
            if request.progress_observer is not None:
                request.progress_observer({"true_epoch": True, "phase": "training"})
            partial = None
            if victim:
                # Real partial work: one authenticated epoch is persisted
                # before the demotion, so the restart must come back through
                # the existing checkpoint/continuation authority.
                partial = fx.train_like_mace(request, stop_after_epoch=0)
                assert partial is not None
            stop = request.cancellation_event
            limit = entered + self.deadline_seconds
            while True:
                if time.monotonic() >= limit:
                    raise AssertionError(
                        "the scheduler never reached concurrency "
                        f"{self.peak_jobs} (max {self.max_active}) within "
                        f"{self.deadline_seconds:.0f}s"
                    )
                if stop is not None and stop.is_set():
                    from mdstats.training_data.post_selection_execution import (
                        PostSelectionCancelledError,
                    )

                    with self.lock:
                        self.stopped.append(identity)
                    if self._teardown_delay_seconds > 0.0:
                        # Real teardown is not instantaneous: the production
                        # child is signalled, reaped, and finalized before the
                        # owner returns its cancellation outcome.
                        time.sleep(self._teardown_delay_seconds)
                    if self._failing_victim:
                        # An unrelated backend fault that races the stop
                        # request. The owner did not produce a cancellation
                        # outcome, so nothing about it is retractable work.
                        raise RuntimeError(
                            "mace backend crashed: libcudart.so relocation error"
                        )
                    raise PostSelectionCancelledError(
                        "Post-selection MACE training was cancelled."
                    )
                with self.lock:
                    settled = (
                        self._peaked.is_set()
                        and self.active <= self.peak_jobs - 1
                        # When the victim fails on its own authority there is no
                        # resumed wave to settle into: every remaining child
                        # stays live until the terminal path stops and reaps it.
                        and not self._failing_victim
                    )
                if settled and not victim:
                    break
                time.sleep(0.005)
            return super().train(request)
        finally:
            with self.lock:
                self.active -= 1
            self.windows[(identity, attempt)] = (entered, time.monotonic())


# --- 1. The observed 24 GiB / 21.6 GiB / 22.2 GiB challenge ----------------


def test_sustained_two_job_pressure_demotes_one_job_and_completes_every_fold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The reproduced defect case adapts through ``2 -> 1`` instead of failing.

    Total 24.0 GiB, configured envelope 21.6 GiB, GPU utilization far below the
    admission ceiling, no CUDA OOM, and aggregate occupancy persistently at
    22.2 GiB once two owned jobs are running.
    """

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    harness = _OccupancyHarness(partial_stop_victim=True)
    _install_telemetry(
        monkeypatch, lambda device: _sample(harness.occupancy_gib(), 40.0)
    )

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out

    # 1. Concurrency 2 was genuinely reached and then retracted.
    assert harness.max_active == 2, printed
    assert "backoff 2->1" in printed, printed
    assert "effective_ceiling=1" in printed, printed

    # 2. Exactly one deterministic victim: the most recently admitted job.
    assert harness.stopped == [harness.order[1]], (
        "backoff must demote the most recently admitted active owned job only"
    )
    assert harness.order[0] not in harness.stopped, (
        "an unaffected active job was cancelled by ordinary backoff"
    )

    # 3. The demoted task was requeued and restarted; nothing else was.
    victim = harness.order[1]
    survivor = harness.order[0]
    assert harness.attempts[victim] == 2
    assert harness.attempts[survivor] == 1

    # 4. Teardown barrier: the restarted attempt begins after the demoted
    #    worker's own completion, not merely after a cancellation request.
    first_start, first_end = harness.windows[(victim, 1)]
    second_start, _second_end = harness.windows[(victim, 2)]
    assert second_start >= first_end, (
        "the slot was reused before its demoted worker finished"
    )
    assert "worker teardown observed" in printed, printed

    # 5. The restart resumed through the existing checkpoint authority rather
    #    than a new retry convention, and published no partial fold.
    assert harness.start_epochs[(victim, 1)] == 0
    assert harness.start_epochs[(victim, 2)] >= 1, (
        "the demoted run did not resume from its authenticated TRAIN2 summary"
    )

    # 6. Accounting: a demotion is not a scientific failure, and every planned
    #    fold completed exactly once.
    scheduler_lines = [
        line for line in printed.splitlines() if "[TRAIN scheduler] status=" in line
    ]
    assert scheduler_lines
    assert all("failed_jobs=0" in line for line in scheduler_lines), scheduler_lines
    final = [
        line for line in scheduler_lines if "status=training-completed" in line
    ]
    assert final, scheduler_lines
    assert "completed_jobs=2" in final[-1], final[-1]
    assert "queued_jobs=0" in final[-1], final[-1]
    assert acceptance.accepted
    assert sorted(harness.attempts) == sorted({survivor, victim})

    # 7. No re-promotion after the level was disproven.
    assert harness.max_active == 2, "concurrency must never have exceeded two"
    assert harness.stopped == [victim], "no second demotion was warranted"

    cfg, paths, store = fx.load_context(config)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            build_post_selection_contexts,
        )

        contexts = build_post_selection_contexts(
            cfg, paths, store, trainer=None, inference_evaluator=None
        )
        assert resolve_current_cv_acceptance(contexts[0]).accepted
    finally:
        store.close()


# --- 2. One owned job over the soft envelope holds ------------------------


def test_sustained_soft_pressure_at_one_job_holds_instead_of_terminating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Q3/INV-1: the minimum owned concurrency has no lower state to reach.

    This is the semantics the prior hard-live-VRAM-guard doctrine got wrong:
    crossing the soft envelope is not by itself proof that the workload is
    infeasible, so a feasible single job must run to completion.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    live = {"active": 0}
    lock = threading.Lock()

    class _SoloHarness(fx.PostSelectionHarness):
        def train(self, request):
            with lock:
                live["active"] += 1
            try:
                if request.progress_observer is not None:
                    request.progress_observer(
                        {"true_epoch": True, "phase": "training"}
                    )
                # Long enough for several control observations to be judged.
                time.sleep(0.4)
                assert not request.cancellation_event.is_set(), (
                    "a soft-envelope crossing at one owned job stopped the job"
                )
                return super().train(request)
            finally:
                with lock:
                    live["active"] -= 1

    harness = _SoloHarness()
    _install_telemetry(
        monkeypatch,
        lambda device: _sample(22.5 if live["active"] else 0.4, 40.0),
    )
    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert acceptance.accepted
    assert len(harness.runs) == 2, "every planned fold must still be trained"
    assert "minimum owned TRAIN2 concurrency" in printed, printed
    assert "backoff" not in printed, printed


# --- 3. Backoff does not swallow an authoritative hard failure ------------


def test_an_authoritative_child_failure_is_not_swallowed_by_backoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F6: a genuine CUDA OOM under soft pressure still ends the invocation."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    live = {"active": 0}
    attempts: list[str] = []

    class _OomHarness(fx.PostSelectionHarness):
        def train(self, request):
            attempts.append(str(request.run_plan.run_identity))
            live["active"] += 1
            try:
                if request.progress_observer is not None:
                    request.progress_observer(
                        {"true_epoch": True, "phase": "training"}
                    )
                time.sleep(0.2)
                raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")
            finally:
                live["active"] -= 1

    harness = _OomHarness()
    _install_telemetry(
        monkeypatch,
        lambda device: _sample(22.5 if live["active"] else 0.4, 40.0),
    )
    context, store = _cuda_cv_context(config, harness)
    try:
        with pytest.raises(RuntimeError, match="CUDA out of memory"):
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    assert len(attempts) == 1, (
        "an authoritative hard failure must not be retried by the backoff path"
    )


# --- 4. Foreign occupancy constrains but is never owned -------------------


def test_foreign_occupancy_lowers_owned_concurrency_without_claiming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Q10/F7: aggregate telemetry includes foreign use; ownership does not.

    The foreign resident here is never an mdstats child, so the only owned
    response available is to reduce or hold owned concurrency. The structural
    half of the claim - that no owned code terminates a process it did not
    start - is closed by
    ``test_the_scheduler_owns_no_foreign_process_termination_path``.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    live = {"active": 0}

    class _ForeignPressureHarness(fx.PostSelectionHarness):
        def train(self, request):
            live["active"] += 1
            try:
                if request.progress_observer is not None:
                    request.progress_observer(
                        {"true_epoch": True, "phase": "training"}
                    )
                time.sleep(0.3)
                return super().train(request)
            finally:
                live["active"] -= 1

    harness = _ForeignPressureHarness()
    # 14.0 GiB of foreign residency that mdstats never admitted and can never
    # reclaim: one owned job fits, a second never will.
    _install_telemetry(
        monkeypatch,
        lambda device: _sample(14.0 + (8.6 if live["active"] else 0.0), 30.0),
    )
    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert acceptance.accepted
    assert len(harness.runs) == 2
    assert "target_jobs=1" in printed, printed


def test_the_scheduler_owns_no_foreign_process_termination_path() -> None:
    """Structural: owned TRAIN2 code kills only processes it started itself."""

    import inspect

    from mdstats.training_data import campaign_post_selection_runtime as runtime
    from mdstats.training_data import post_selection_execution as execution
    from mdstats.training_data import training_parallel

    for module in (runtime, training_parallel):
        source = inspect.getsource(module)
        for forbidden in ("os.kill", "psutil", "killpg", "pkill", "--kill"):
            assert forbidden not in source, (
                f"{module.__name__} reaches outside owned child ownership: {forbidden}"
            )

    # The one termination owner takes a process handle the caller started.
    signature = inspect.signature(execution._terminate_post_selection_process)
    assert list(signature.parameters)[0] == "process"


# --- 5. Pressure that survives the demotion is re-evaluated, not retried ---


def test_unreclaimed_pressure_after_demotion_admits_no_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Q11: a demotion that does not free memory must not trigger a blind retry.

    Occupancy here stays above the soft envelope after the demoted worker has
    gone, which is what residual foreign or parent baseline occupancy looks
    like. The controller must re-evaluate at the lower owned concurrency: hold,
    admit nothing, and neither terminally fail nor loop replacements.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    harness = _OccupancyHarness(sticky_pressure=True)
    _install_telemetry(
        monkeypatch, lambda device: _sample(harness.occupancy_gib(), 40.0)
    )

    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert acceptance.accepted
    assert harness.max_active == 2, "concurrency must never have been raised again"
    assert "backoff 2->1" in printed, printed
    assert printed.count("backoff") == printed.count("backoff 2->1"), (
        "a second backoff has no lower owned concurrency to reach"
    )

    victim = harness.order[1]
    survivor = harness.order[0]
    assert harness.attempts[victim] == 2
    _survivor_start, survivor_end = harness.windows[(survivor, 1)]
    replacement_start, _replacement_end = harness.windows[(victim, 2)]
    assert replacement_start >= survivor_end, (
        "a replacement was admitted while aggregate pressure was still unreclaimed"
    )


# --- 6. Victim determinism at concurrency three ---------------------------


def test_backoff_from_three_demotes_the_third_admitted_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Q6/INV-5: given admission order A, B, C, a ``3 -> 2`` backoff demotes C.

    This also closes F4 at a level above one: the effective ceiling settles at
    two, so the run cannot climb back to the concurrency live telemetry just
    disproved even though occupancy is comfortably safe at two.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(
        tmp_path,
        execution=_FAST_CONTROL,
        fold_count=3,
    )
    harness = _OccupancyHarness(
        peak_jobs=3,
        occupancy_gib_by_active={0: 0.4, 1: 7.0, 2: 13.6, 3: 22.2},
    )
    _install_telemetry(
        monkeypatch, lambda device: _sample(harness.occupancy_gib(), 40.0)
    )

    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert "ceiling=3" in printed, "the fixture must plan a three-job ceiling"
    assert harness.max_active == 3, printed
    assert "backoff 3->2" in printed, printed
    assert "backoff 3->1" not in printed, printed
    assert "effective_ceiling=2" in printed, printed
    assert harness.stopped == [harness.order[2]], (
        "the third admitted job is the deterministic victim"
    )
    assert harness.attempts[harness.order[0]] == 1
    assert harness.attempts[harness.order[1]] == 1
    assert harness.attempts[harness.order[2]] == 2
    assert "effective_ceiling=3" not in printed.split("backoff 3->2", 1)[1], (
        "a disproven concurrency level was re-entered"
    )
    assert acceptance.accepted
    assert len(harness.attempts) == 3


# --- 7. Teardown that cannot be confirmed is a causal terminal failure -----


def test_a_worker_that_never_quiesces_is_a_causal_terminal_memory_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-3(3)/Q11: an owning-layer teardown defect is surfaced, not looped.

    Bounded deterministic failure injection: the demoted child ignores its
    cooperative stop while the real scheduler, controller, telemetry loop and
    run path stay live. Because owned accelerator lifetime cannot then be
    confirmed released, no safe owned execution state can be re-established and
    the existing terminal safety error is raised with its causal reason - rather
    than the scheduler blocking forever or retrying a replacement.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import TrainingMemorySafetyError

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)

    live = {"active": 0}
    lock = threading.Lock()

    class _DeafHarness(fx.PostSelectionHarness):
        """A child that never honours its stop handle."""

        def train(self, request):
            with lock:
                live["active"] += 1
            try:
                if request.progress_observer is not None:
                    request.progress_observer(
                        {"true_epoch": True, "phase": "training"}
                    )
                time.sleep(4.0)
                raise AssertionError("the scheduler should have stopped waiting")
            finally:
                with lock:
                    live["active"] -= 1

    def probe(device):
        with lock:
            active = live["active"]
        used = {0: 0.4, 1: 10.0}.get(active, 22.2)
        return _sample(used, 40.0)

    harness = _DeafHarness()
    # The execution owner's own child termination/reaping bound, the same
    # contract ``MacePostSelectionTrainer`` derives from its termination grace.
    # A child that is still running after it has elapsed has violated the
    # termination path the scheduler authorized.
    harness.cancellation_teardown_seconds = 0.5
    _install_telemetry(monkeypatch, probe)
    context, store = _cuda_cv_context(config, harness)
    try:
        with pytest.raises(TrainingMemorySafetyError) as stop:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    message = str(stop.value)
    assert "did not quiesce" in message, message
    assert "accelerator lifetime cannot be confirmed released" in message, message
    assert "execution owner" in message, (
        "the teardown deadline must name the termination authority it came from"
    )


# --- 8. Demotion never reclassifies an independent child failure ----------


def test_a_victim_that_fails_at_the_demotion_boundary_stays_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """B1: the scheduler's intent to stop a job is not evidence about why it raised.

    Two owned jobs, persistent soft pressure, the most recently admitted job
    selected for demotion - but that job then raises an unrelated backend
    failure instead of the execution owner's cancellation outcome. Only the
    explicit cancellation outcome is retractable resource work, so this failure
    must keep its own authority.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(tmp_path, execution=_FAST_CONTROL)
    harness = _OccupancyHarness(failing_victim=True)
    _install_telemetry(
        monkeypatch, lambda device: _sample(harness.occupancy_gib(), 40.0)
    )

    context, store = _cuda_cv_context(config, harness)
    try:
        with pytest.raises(RuntimeError, match="mace backend crashed"):
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert "backoff 2->1" in printed, printed

    # 1. The failure propagated causally and was not requeued or retried.
    victim = harness.order[1]
    assert harness.attempts[victim] == 1, (
        "an authoritative child failure at the demotion boundary was requeued"
    )
    assert harness.stopped[0] == victim

    # 2. The terminal path, not the adaptation loop, owns the outcome: the
    #    surviving owned job - which would otherwise still be running - was
    #    signalled and reaped by the whole-wave cleanup.
    survivor = harness.order[0]
    assert harness.attempts[survivor] == 1
    assert survivor in harness.stopped, (
        "the terminal cleanup path did not stop and reap the remaining owned job"
    )
    assert (survivor, 1) in harness.windows
    assert "status=failed" in printed, printed
    assert "failed_jobs=1" in printed, printed

    # 3. No acceptance was published from a failed wave.
    cfg, paths, acceptance_store = fx.load_context(config)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            build_post_selection_contexts,
        )

        contexts = build_post_selection_contexts(
            cfg, paths, acceptance_store, trainer=None, inference_evaluator=None
        )
        assert resolve_current_cv_acceptance(contexts[0]) is None
    finally:
        acceptance_store.close()


# --- 9. Teardown duration is not optimizer-liveness freshness --------------


def test_backoff_survives_a_zero_optimizer_activity_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """B2: optimizer-progress freshness never bounds child teardown.

    ``parallel_training_epoch_activity_timeout_seconds = 0`` is a legal
    liveness-tuning value that makes every child's optimizer activity look
    stale immediately. Teardown here is deliberately not instantaneous, so if
    that number were still the demotion deadline the barrier would fail. The
    demotion must instead complete through the execution owner's own
    termination contract and requeue normally.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        execute_post_selection_cross_validation,
    )

    config = _selected_campaign(
        tmp_path,
        execution=_FAST_CONTROL
        + "\nparallel_training_epoch_activity_timeout_seconds = 0.0",
    )
    harness = _OccupancyHarness(
        partial_stop_victim=True, teardown_delay_seconds=0.3
    )
    _install_telemetry(
        monkeypatch, lambda device: _sample(harness.occupancy_gib(), 40.0)
    )

    context, store = _cuda_cv_context(config, harness)
    try:
        _plan, acceptance = execute_post_selection_cross_validation(context)
    finally:
        store.close()

    printed = capsys.readouterr().out
    assert "backoff 2->1" in printed, printed
    assert "did not quiesce" not in printed, printed
    victim = harness.order[1]
    assert harness.stopped == [victim]
    assert harness.attempts[victim] == 2, (
        "a non-instantaneous cooperative teardown was rejected"
    )
    assert acceptance.accepted
    assert len(harness.attempts) == 2


def test_the_demotion_barrier_reads_only_the_execution_owner_contract() -> None:
    """Structural: no liveness/control cadence can be the teardown deadline.

    Runtime evidence cannot show the absence of a coupling, so the one
    admissible deadline source is asserted directly on the owning source.
    """

    import inspect

    from mdstats.training_data import campaign_post_selection_runtime as runtime
    from mdstats.training_data.post_selection_execution import (
        MacePostSelectionTrainer,
    )

    source = inspect.getsource(runtime.__dict__["_execute_post_selection_pending_runs"])
    barrier = source.split("def demote_most_recently_admitted", 1)[1].split(
        "def complete_eval2_for_trained_slots", 1
    )[0]
    for forbidden in (
        "epoch_activity_timeout_seconds",
        "monitor_interval_seconds",
        "poll_interval",
    ):
        assert forbidden not in barrier, (
            f"the demotion teardown barrier reuses {forbidden} as a deadline"
        )
    assert "teardown_bound" in barrier

    # The bound is declared by the execution owner and cannot expire before its
    # own escalating terminate/reap sequence.
    trainer = MacePostSelectionTrainer(
        wrapper_path=Path("unused"),
        poll_interval_seconds=1.0,
        terminate_grace_seconds=30.0,
    )
    assert trainer.cancellation_teardown_seconds >= 2.0 * 30.0
