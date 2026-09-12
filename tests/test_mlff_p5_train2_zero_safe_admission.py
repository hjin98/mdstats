"""Real-owner acceptance for zero-safe TRAIN2 admission and phase ownership.

The P5 admission/supervision owner is
``campaign_post_selection_runtime._execute_post_selection_pending_runs``, driven
here through the real ``cross-validate`` command. Only MACE numerics are
substituted, through the shared fixture's two seams below the owner boundary,
plus bounded deterministic resource facts where the claim *is* resource
semantics.

The governed propositions are:

1. an unsafe or infeasible initial resource state cannot force-launch TRAIN2,
   and an idle queue with pending work fails explicitly instead of spinning;
2. one TRAIN scheduler slot owns TRAIN2 only, so EVAL2 cannot overlap an
   independently admitted TRAIN2 child;
3. authenticated TRAIN2 work survives an interruption before EVAL2;
4. scheduler failure reporting counts queued/active/completed/failed work from
   actual ownership rather than a derived formula;
5. temporary architecture classification releases its accelerator residency.

TRAIN2 memory-pressure backoff, per-job demotion, and the soft/hard boundary
separation are governed by ``test_mlff_p5_train2_memory_backoff``.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import tests._mlff_post_selection_fixture as fx

from mdstats.training_data import campaign_post_selection_runtime as runtime
from mdstats.training_data.campaign_post_selection_runtime import (
    resolve_current_cv_acceptance,
)
from mdstats.training_data.training_parallel import TrainingAdmissionBlockedError


def _selected_campaign(tmp_path: Path, *, execution: str = "") -> Path:
    """One frozen, CV-feasible campaign, optionally with execution overrides."""

    config_text = fx.fixture_config_text()
    if execution:
        config_text = f"{config_text}\n[execution]\n{execution}\n"
    config, _workspace = fx.build_selected_campaign(
        tmp_path, config_text=config_text
    )
    return config


def _no_cv_acceptance(config: Path) -> None:
    cfg, paths, store = fx.load_context(config)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            build_post_selection_contexts,
        )

        contexts = build_post_selection_contexts(
            cfg, paths, store, trainer=None, inference_evaluator=None
        )
        for context in contexts:
            assert resolve_current_cv_acceptance(context) is None
    finally:
        store.close()


class _TimedHarness(fx.PostSelectionHarness):
    """Records when TRAIN2 actually executed; the base records EVAL2."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.train_windows: list[tuple[float, float]] = []

    def train(self, request):
        started = time.monotonic()
        try:
            return super().train(request)
        finally:
            self.train_windows.append((started, time.monotonic()))


# --- 1. Zero safe admission is representable end to end --------------------


def test_zero_feasible_training_slots_fail_explicitly_and_launch_nothing(
    tmp_path: Path,
) -> None:
    """Pending work plus an infeasible envelope is a typed failure, not a spin.

    The hard per-process reservation is host RAM here, so the case is exact and
    hardware-independent. The VRAM form of the same arithmetic is closed
    separately by
    ``test_the_target_host_vram_baseline_launches_nothing_through_the_real_owner``.
    Both establish that a zero-safe plan *propagates* through the real
    submission loop instead of being floored back to one job.
    """

    config = _selected_campaign(
        tmp_path,
        execution="estimated_training_ram_mib_per_job = 100000000.0",
    )
    harness = _TimedHarness()
    started = time.monotonic()
    with pytest.raises(TrainingAdmissionBlockedError) as failure:
        fx.run_cross_validate(config, harness)
    assert time.monotonic() - started < 120.0, "an idle zero-slot queue must not spin"
    assert "no job is currently resource-admissible" in str(failure.value)
    assert "host RAM budget" in str(failure.value)
    assert harness.runs == [], "no TRAIN2 job may launch from a zero-safe plan"
    _no_cv_acceptance(config)


def test_the_target_host_vram_baseline_launches_nothing_through_the_real_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The supplied 24 GiB / 20.2 GiB / 90% / 6 GiB case, end to end.

    The resource probe is a bounded deterministic fixture because the claim is
    scheduler admission semantics, not telemetry plumbing. Everything above it -
    the planner, the controller, the submission loop, and the CV caller - is the
    real owner, and the 90% default is the configured one.
    """

    from dataclasses import replace

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import training_parallel
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import GpuTelemetrySample

    gib = 1024 ** 3
    config = _selected_campaign(tmp_path)
    monkeypatch.setattr(
        training_parallel,
        "query_gpu_telemetry",
        lambda device: GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=12.0,
            used_bytes=int(20.2 * gib),
            total_bytes=24 * gib,
        ),
    )

    harness = _TimedHarness()
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )[0]
        context = replace(
            context,
            method_policies=replace(context.method_policies, device="cuda:0"),
        )
        with pytest.raises(TrainingAdmissionBlockedError) as failure:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    message = str(failure.value)
    assert "baseline 20.2 GiB" in message
    assert "6.0 GiB job reservation" in message
    assert "21.6 GiB training VRAM envelope" in message
    assert harness.runs == [], "no TRAIN2 job may launch from a zero-safe plan"
    _no_cv_acceptance(config)


def test_a_positive_configured_job_cap_does_not_bypass_admission(
    tmp_path: Path,
) -> None:
    """``parallel_training_jobs`` is a ceiling, never launch permission."""

    config = _selected_campaign(
        tmp_path,
        execution=(
            "parallel_training_jobs = 4\n"
            "estimated_training_ram_mib_per_job = 100000000.0"
        ),
    )
    harness = _TimedHarness()
    with pytest.raises(TrainingAdmissionBlockedError):
        fx.run_cross_validate(config, harness)
    assert harness.runs == []


def test_a_feasible_campaign_still_completes_cross_validation(
    tmp_path: Path,
) -> None:
    """The repair must not disturb ordinary admissible operation."""

    config = _selected_campaign(tmp_path)
    harness = _TimedHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert harness.runs, "an admissible campaign must actually train"
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


# --- 2. One TRAIN slot owns TRAIN2 only ------------------------------------


def test_eval2_never_overlaps_a_sibling_train2_child(tmp_path: Path) -> None:
    """The TRAIN scheduler future ends at authenticated TRAIN2 ownership."""

    config = _selected_campaign(tmp_path)
    harness = _TimedHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert len(harness.train_windows) >= 2, "the fixture must drive several folds"
    assert harness.evaluations, "EVAL2 must have executed"

    last_train_end = max(end for _start, end in harness.train_windows)
    first_evaluation = min(harness.evaluations)
    assert first_evaluation >= last_train_end, (
        "an EVAL2 provider ran while a TRAIN2 child was still owned by the "
        "training scheduler"
    )


# --- 3. Authenticated TRAIN2 survives an interruption before EVAL2 ---------


class _Eval2Interrupt(_TimedHarness):
    """Fails at the first EVAL2 consumer, after TRAIN2 is already durable."""

    def evaluate(self, provider, atoms_list):
        raise RuntimeError("simulated interruption before EVAL2 completed")


def test_completed_train2_state_is_reused_after_interruption_before_eval2(
    tmp_path: Path,
) -> None:
    config = _selected_campaign(tmp_path)
    interrupted = _Eval2Interrupt()
    with pytest.raises(RuntimeError, match="simulated interruption"):
        fx.run_cross_validate(config, interrupted)
    assert interrupted.runs, "TRAIN2 must have executed before the interruption"
    _no_cv_acceptance(config)

    resumed = _TimedHarness()
    assert fx.run_cross_validate(config, resumed) == 0
    assert resumed.runs == [], (
        "authenticated TRAIN2 continuations were retrained instead of reused"
    )


# --- 4. Truthful scheduler failure accounting ------------------------------


class _FirstTrainFails(fx.PostSelectionHarness):
    def train(self, request):
        self.runs.append(request.run_plan.run_identity)
        raise RuntimeError("simulated TRAIN2 child failure")


def test_scheduler_failure_reporting_counts_work_truthfully(
    tmp_path: Path, capsys
) -> None:
    """A submitted slot that failed is never reported as still queued."""

    config = _selected_campaign(tmp_path)
    with pytest.raises(RuntimeError, match="simulated TRAIN2 child failure"):
        fx.run_cross_validate(config, _FirstTrainFails())
    printed = capsys.readouterr().out
    failure_lines = [
        line
        for line in printed.splitlines()
        if "[TRAIN scheduler] status=failed" in line
    ]
    assert failure_lines, printed
    line = failure_lines[-1]
    assert "failed_jobs=1" in line, line
    assert "active_jobs=0" in line, line
    assert "completed_jobs=0" in line, line
    # The historical defect: the failed slot was counted back into pending.
    assert "pending_jobs=" not in line, line
    _no_cv_acceptance(config)


# --- 5. Temporary architecture classification releases accelerator memory --


def _cuda_or_skip():
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():  # pragma: no cover - host dependent
        pytest.skip("CUDA residency is the claim under test")
    return torch


def _architecture_context():
    return SimpleNamespace(
        method_policies=SimpleNamespace(foundation_model=None)
    )


def _resident_model_factory(torch):
    class _Resident:
        """A bounded stand-in that owns real device memory, like a MACE model.

        The self-reference is deliberate. ``torch.nn.Module`` graphs - and the
        third-party CuEq conversion products built from them - routinely form
        reference cycles, so dropping the last name is *not* sufficient to
        reclaim device memory. That is precisely why the lifetime boundary has
        to collect rather than rely on function-scope reclamation.
        """

        def __init__(self) -> None:
            self.block = torch.zeros(16 * 1024 * 1024, device="cuda")
            self.cycle = self

    return _Resident


def _without_automatic_collection():
    """Hold automatic generational collection still for a residency claim."""

    import contextlib
    import gc

    @contextlib.contextmanager
    def scope():
        enabled = gc.isenabled()
        gc.disable()
        try:
            yield
        finally:
            if enabled:
                gc.enable()
            gc.collect()

    return scope()


def test_repeated_architecture_classification_releases_its_residency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Classification is not training: it may not retain model-scale VRAM.

    The real owner under acceptance is the helper's lifetime boundary. MACE's
    own conversion path is an execution dependency below it and is bounded
    here, but the residency observation is a real CUDA allocator observation.
    """

    torch = _cuda_or_skip()
    from mdstats.training_data import model_features as mf

    resident = _resident_model_factory(torch)
    monkeypatch.setattr(
        mf,
        "build_mace_model_from_configuration",
        lambda payload, *, foundation_model_path=None: resident(),
    )
    monkeypatch.setattr(
        mf, "realize_mace_training_model", lambda model, payload: (resident(), "cueq")
    )
    monkeypatch.setattr(
        mf, "mace_model_execution_architecture_digest", lambda model: "d" * 64
    )

    context = _architecture_context()
    with _without_automatic_collection():
        # Warm the allocator so the baseline is not measuring first-touch growth.
        runtime._post_selection_current_training_architecture(
            context, current_config={}
        )
        baseline = int(torch.cuda.memory_allocated())
        digests = set()
        for _attempt in range(4):
            digest, realization = (
                runtime._post_selection_current_training_architecture(
                    context, current_config={}
                )
            )
            digests.add((digest, realization))
        residency = int(torch.cuda.memory_allocated())
    assert digests == {("d" * 64, "cueq")}, "the digest semantics must be unchanged"
    assert residency <= baseline, (
        "repeated architecture classification accumulated device residency: "
        f"{residency} bytes allocated against a {baseline} byte baseline"
    )


def test_architecture_classification_cleans_up_on_the_exception_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    torch = _cuda_or_skip()
    from mdstats.training_data import model_features as mf

    resident = _resident_model_factory(torch)
    monkeypatch.setattr(
        mf,
        "build_mace_model_from_configuration",
        lambda payload, *, foundation_model_path=None: resident(),
    )
    monkeypatch.setattr(
        mf, "realize_mace_training_model", lambda model, payload: (resident(), "cueq")
    )

    def _fail(model):
        raise ValueError("digest could not be computed")

    monkeypatch.setattr(mf, "mace_model_execution_architecture_digest", _fail)

    context = _architecture_context()
    with _without_automatic_collection():
        with pytest.raises(ValueError, match="digest could not be computed"):
            runtime._post_selection_current_training_architecture(
                context, current_config={}
            )
        baseline = int(torch.cuda.memory_allocated())
        for _attempt in range(3):
            with pytest.raises(ValueError):
                runtime._post_selection_current_training_architecture(
                    context, current_config={}
                )
        residency = int(torch.cuda.memory_allocated())
    assert residency <= baseline, (
        "the conversion/digest exception path leaked device residency: "
        f"{residency} bytes allocated against a {baseline} byte baseline"
    )


# --- 6. A live child that must be stopped mid-flight -----------------------


class _SlowTrain(fx.PostSelectionHarness):
    """A child that stays alive long enough for telemetry to be judged."""

    def __init__(self, *, live, seconds: float = 2.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.live = live
        self.seconds = float(seconds)

    def train(self, request):
        self.runs.append(request.run_plan.run_identity)
        self.requests.append(request)
        self.live["training"] = True
        time.sleep(self.seconds)
        raise AssertionError("the scheduler should have stopped this child")


# --- 7. Runtime memory-observability loss fails closed ---------------------


def test_runtime_memory_observability_loss_stops_owned_training(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live accelerator work may not continue without a memory observation.

    Admission sees a trustworthy clean device, and the observation is then lost
    while the child holds the accelerator. The real P5 supervision owner must
    stop the wave through the existing typed resource path rather than treat an
    unobservable device as implicitly safe.
    """

    from dataclasses import replace

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import training_parallel
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import (
        GpuTelemetrySample,
        TrainingResourceObservabilityError,
    )

    gib = 1024 ** 3
    config = _selected_campaign(
        tmp_path,
        execution="\n".join(
            (
                "parallel_training_monitor_interval_seconds = 0.05",
                "parallel_training_epoch_stabilization_seconds = 0.0",
                "training_progress_interval_seconds = 0.05",
            )
        ),
    )

    live = {"training": False}

    def telemetry(device: str):
        if live["training"]:
            return None
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=4.0,
            used_bytes=int(0.4 * gib),
            total_bytes=24 * gib,
        )

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", telemetry)

    harness = _SlowTrain(live=live, seconds=2.0)
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )[0]
        context = replace(
            context,
            method_policies=replace(context.method_policies, device="cuda:0"),
        )
        with pytest.raises(TrainingResourceObservabilityError) as stop:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    assert "unobservable" in str(stop.value)
    assert len(harness.runs) == 1, "admission must not have launched a second job"
    _no_cv_acceptance(config)


# --- 8. A failed TRAIN wave terminates before EVAL2 ------------------------


class _SecondTrainFails(_TimedHarness):
    """The first slot reaches an authenticated TRAIN2 summary; the next fails."""

    def train(self, request):
        if self.runs:
            self.runs.append(request.run_plan.run_identity)
            raise RuntimeError("simulated later TRAIN2 child failure")
        return super().train(request)


def test_a_failed_train_wave_starts_no_eval2_and_preserves_trained_state(
    tmp_path: Path,
) -> None:
    """A generic TRAIN2 failure ends the invocation before any EVAL2 begins.

    The historical behavior evaluated every already-trained sibling and only
    then re-raised, so a device whose TRAIN2 state was unknown received fresh
    accelerator work. Progress is still preserved: the authenticated TRAIN2
    summary of the completed slot is the restart boundary, and a later healthy
    invocation reuses it instead of retraining.
    """

    config = _selected_campaign(tmp_path)
    failing = _SecondTrainFails()
    with pytest.raises(RuntimeError, match="simulated later TRAIN2 child failure"):
        fx.run_cross_validate(config, failing)
    assert len(failing.train_windows) == 1, "one slot must have completed TRAIN2"
    assert failing.evaluations == [], (
        "EVAL2 ran for a previously trained sibling after the TRAIN wave failed"
    )
    _no_cv_acceptance(config)

    resumed = _TimedHarness()
    assert fx.run_cross_validate(config, resumed) == 0
    assert len(resumed.runs) == 1, (
        "the completed slot's authenticated TRAIN2 continuation was not reused; "
        f"the rerun retrained {resumed.runs}"
    )
    assert resumed.evaluations, "the healthy rerun must reach EVAL2"
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


class _TrainAlwaysFails(_TimedHarness):
    def train(self, request):
        self.runs.append(request.run_plan.run_identity)
        raise RuntimeError("simulated production TRAIN2 child failure")


def test_final_production_shares_the_failure_before_eval2_owner(
    tmp_path: Path,
) -> None:
    """Final production uses the same corrected TRAIN admission/failure owner."""

    config = _selected_campaign(tmp_path)
    assert fx.run_cross_validate(config, _TimedHarness()) == 0

    failing = _TrainAlwaysFails()
    with pytest.raises(RuntimeError, match="simulated production TRAIN2 child failure"):
        fx.run_train_production(config, failing)
    assert failing.runs, "the production TRAIN wave must have been entered"
    assert failing.evaluations == [], (
        "final production began EVAL2 after its TRAIN wave failed"
    )


# --- 9. No operator-facing memory-hazard debounce knob exists --------------


def test_no_operator_facing_memory_hazard_grace_key_exists() -> None:
    """The transient-observation bound is controller-local, not configuration.

    Operator tuning was never an accepted requirement, so neither the
    production configuration path nor the checked-in operator example may carry
    a latent, undocumented debounce key.
    """

    from mdstats.training_data.training_parallel import TrainingConcurrencyPolicy

    key = "parallel_training_memory_hazard_grace_seconds"
    runtime_source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert key not in runtime_source
    example = Path(runtime.__file__).resolve().parents[2] / "campaign.toml.example"
    assert example.is_file()
    assert key not in example.read_text(encoding="utf-8")
    assert not hasattr(
        TrainingConcurrencyPolicy(), "memory_hazard_grace_seconds"
    )


# --- 10. Blocker B1: CPU serial replacement across monitor observations -----


class _MultiSlotCpuHarness(_TimedHarness):
    """A CPU harness that sleeps during train to ensure crossing monitor observations."""

    def __init__(self, *, slot_duration: float = 0.12, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slot_duration = float(slot_duration)
        self.active_jobs = 0
        self.max_active_jobs = 0
        import threading
        self._lock = threading.Lock()

    def train(self, request):
        with self._lock:
            self.active_jobs += 1
            if self.active_jobs > self.max_active_jobs:
                self.max_active_jobs = self.active_jobs
        try:
            time.sleep(self.slot_duration)
            return super().train(request)
        finally:
            with self._lock:
                self.active_jobs -= 1


def test_cpu_serial_multi_slot_crosses_monitor_observations_without_hang(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CPU serial replacement continues normally across monitor observations (B1).

    AdaptiveTrainingConcurrency.observe() returns memory_safe=None on CPU plans.
    The P5 scheduler must derive admission_blocked from memory_safe only on
    accelerator-memory-controlled plans, preserving CPU maximum_jobs=1 and
    ordinary serial replacement submission across all pending slots.
    """

    from mdstats.training_data.training_parallel import AdaptiveTrainingConcurrency

    config = _selected_campaign(
        tmp_path,
        execution="\n".join(
            (
                "parallel_training_monitor_interval_seconds = 0.04",
                "training_progress_interval_seconds = 0.04",
            )
        ),
    )

    observations = 0
    orig_observe = AdaptiveTrainingConcurrency.observe

    def observe_spy(self, *args, **kwargs):
        nonlocal observations
        observations += 1
        return orig_observe(self, *args, **kwargs)

    monkeypatch.setattr(AdaptiveTrainingConcurrency, "observe", observe_spy)

    harness = _MultiSlotCpuHarness(slot_duration=0.10)
    assert fx.run_cross_validate(config, harness) == 0

    assert observations >= 2, f"expected multiple observations during run, got {observations}"
    assert harness.max_active_jobs == 1, (
        f"CPU training must remain serial, observed {harness.max_active_jobs} concurrent jobs"
    )
    assert len(harness.runs) == 2, (
        f"expected all pending CV slots (2) to be admitted, got {len(harness.runs)}"
    )
    assert harness.evaluations, "successful wave must reach ordinary serial EVAL2"

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

    # Shared final-production caller
    prod_harness = _MultiSlotCpuHarness(slot_duration=0.08)
    assert fx.run_train_production(config, prod_harness) == 0
    assert prod_harness.max_active_jobs == 1
    assert prod_harness.runs, "production TRAIN slots must be admitted"
    assert prod_harness.evaluations, "production must complete through EVAL2"


# --- 11. Blocker B2: Idle transient CUDA admission wait on poll cadence -----


def test_idle_transient_cuda_admission_blocking_waits_rather_than_spins_unsafe_to_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idle pending queue: unsafe -> safe waits on poll interval, then admits (B2)."""

    from dataclasses import replace
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import training_parallel
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import GpuTelemetrySample

    gib = 1024 ** 3
    config = _selected_campaign(
        tmp_path,
        execution="\n".join(
            (
                "parallel_training_monitor_interval_seconds = 0.05",
                "parallel_training_epoch_stabilization_seconds = 0.0",
                "training_progress_interval_seconds = 0.05",
            )
        ),
    )

    import threading

    job1_ready = threading.Event()
    observation_1_done = threading.Event()

    class _SyncHarness(_TimedHarness):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.completed_jobs = 0

        def train(self, request):
            res = super().train(request)
            if self.completed_jobs == 0:
                job1_ready.set()
                observation_1_done.wait(timeout=5.0)
            self.completed_jobs += 1
            return res

    harness = _SyncHarness()
    preflight_calls = 0
    sleep_calls: list[float] = []
    orig_sleep = time.sleep

    def telemetry_spy(device: str):
        nonlocal preflight_calls
        if preflight_calls < 2 or not job1_ready.is_set():
            if preflight_calls < 2:
                preflight_calls += 1
            return GpuTelemetrySample(
                sampled_monotonic=time.monotonic(),
                device_index=0,
                utilization_percent=5.0,
                used_bytes=int(0.4 * gib),
                total_bytes=24 * gib,
            )
        if not observation_1_done.is_set():
            observation_1_done.set()
            return GpuTelemetrySample(
                sampled_monotonic=time.monotonic(),
                device_index=0,
                utilization_percent=5.0,
                used_bytes=int(22.5 * gib),
                total_bytes=24 * gib,
            )
        # Observation 2+ (idle queue / subsequent execution): safe clears block
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=5.0,
            used_bytes=int(0.4 * gib),
            total_bytes=24 * gib,
        )

    def sleep_spy(duration: float):
        sleep_calls.append(duration)
        orig_sleep(min(duration, 0.005))

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", telemetry_spy)
    monkeypatch.setattr(time, "sleep", sleep_spy)

    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = build_post_selection_contexts(
            cfg, paths, store, trainer=harness.train, inference_evaluator=harness.evaluate, admit=True
        )[0]
        context = replace(context, method_policies=replace(context.method_policies, device="cuda:0"))
        plan, acceptance = execute_post_selection_cross_validation(context)
        assert acceptance.accepted
    finally:
        store.close()

    assert sleep_calls, "scheduler must wait on poll interval while idle and admission blocked"
    assert len(harness.runs) == 2, "both slots must eventually complete after recovery"


def test_idle_transient_cuda_admission_blocking_unsafe_to_unsafe_fails_explicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idle pending queue: unsafe -> unsafe waits, then typed zero-admission failure (B2)."""

    from dataclasses import replace
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import training_parallel
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import (
        GpuTelemetrySample,
        TrainingAdmissionBlockedError,
    )

    gib = 1024 ** 3
    config = _selected_campaign(
        tmp_path,
        execution="\n".join(
            (
                "parallel_training_monitor_interval_seconds = 0.04",
                "parallel_training_epoch_stabilization_seconds = 0.0",
                "training_progress_interval_seconds = 0.04",
            )
        ),
    )

    import threading

    job1_ready = threading.Event()
    observation_1_done = threading.Event()

    class _SyncHarness(_TimedHarness):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.completed_jobs = 0

        def train(self, request):
            res = super().train(request)
            if self.completed_jobs == 0:
                job1_ready.set()
                observation_1_done.wait(timeout=5.0)
            self.completed_jobs += 1
            return res

    harness = _SyncHarness()
    preflight_calls = 0
    sleep_calls: list[float] = []
    orig_sleep = time.sleep

    def telemetry_spy(device: str):
        nonlocal preflight_calls
        if preflight_calls < 2 or not job1_ready.is_set():
            if preflight_calls < 2:
                preflight_calls += 1
            return GpuTelemetrySample(
                sampled_monotonic=time.monotonic(),
                device_index=0,
                utilization_percent=5.0,
                used_bytes=int(0.4 * gib),
                total_bytes=24 * gib,
            )
        if not observation_1_done.is_set():
            observation_1_done.set()
        # Observation 1 (while Job 1 active) and Observation 2 (queue idle): both unsafe
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=5.0,
            used_bytes=int(22.5 * gib),
            total_bytes=24 * gib,
        )

    def sleep_spy(duration: float):
        sleep_calls.append(duration)
        orig_sleep(min(duration, 0.005))

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", telemetry_spy)
    monkeypatch.setattr(time, "sleep", sleep_spy)

    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = build_post_selection_contexts(
            cfg, paths, store, trainer=harness.train, inference_evaluator=harness.evaluate, admit=True
        )[0]
        context = replace(context, method_policies=replace(context.method_policies, device="cuda:0"))
        with pytest.raises(TrainingAdmissionBlockedError) as exc_info:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    assert sleep_calls, "scheduler must wait on poll interval before confirmed zero-safe admission"
    assert "no job is currently resource-admissible" in str(exc_info.value)
    assert len(harness.runs) == 1, "second job must never launch from persistent unsafe state"
    _no_cv_acceptance(config)


def test_idle_transient_cuda_admission_blocking_missing_to_missing_fails_explicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idle pending queue: missing -> missing waits, then typed zero/observability failure (B2)."""

    from dataclasses import replace
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import training_parallel
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import (
        GpuTelemetrySample,
        TrainingAdmissionBlockedError,
    )

    gib = 1024 ** 3
    config = _selected_campaign(
        tmp_path,
        execution="\n".join(
            (
                "parallel_training_monitor_interval_seconds = 0.04",
                "parallel_training_epoch_stabilization_seconds = 0.0",
                "training_progress_interval_seconds = 0.04",
            )
        ),
    )

    import threading

    job1_ready = threading.Event()
    observation_1_done = threading.Event()

    class _SyncHarness(_TimedHarness):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.completed_jobs = 0

        def train(self, request):
            res = super().train(request)
            if self.completed_jobs == 0:
                job1_ready.set()
                observation_1_done.wait(timeout=5.0)
            self.completed_jobs += 1
            return res

    harness = _SyncHarness()
    preflight_calls = 0
    sleep_calls: list[float] = []
    orig_sleep = time.sleep

    def telemetry_spy(device: str):
        nonlocal preflight_calls
        if preflight_calls < 2 or not job1_ready.is_set():
            if preflight_calls < 2:
                preflight_calls += 1
            return GpuTelemetrySample(
                sampled_monotonic=time.monotonic(),
                device_index=0,
                utilization_percent=5.0,
                used_bytes=int(0.4 * gib),
                total_bytes=24 * gib,
            )
        if not observation_1_done.is_set():
            observation_1_done.set()
        # Observation 1 (while Job 1 active) and Observation 2 (queue idle): both missing
        return None

    def sleep_spy(duration: float):
        sleep_calls.append(duration)
        orig_sleep(min(duration, 0.005))

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", telemetry_spy)
    monkeypatch.setattr(time, "sleep", sleep_spy)

    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = build_post_selection_contexts(
            cfg, paths, store, trainer=harness.train, inference_evaluator=harness.evaluate, admit=True
        )[0]
        context = replace(context, method_policies=replace(context.method_policies, device="cuda:0"))
        with pytest.raises(TrainingAdmissionBlockedError) as exc_info:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    assert sleep_calls, "scheduler must wait on poll interval before confirmed zero-safe admission"
    assert "no job is currently resource-admissible" in str(exc_info.value)
    assert len(harness.runs) == 1, "second job must never launch when memory observability is lost"
    _no_cv_acceptance(config)


# --- 12. Blocker B3: Same completion batch classifies all done futures ------


class _MixedDoneBatchHarness(_TimedHarness):
    """Two concurrently admitted jobs: fold 0 succeeds and fold 1 fails."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        import threading
        self.barrier = threading.Barrier(2)

    def train(self, request):
        fold = int(getattr(request.run_plan, "fold_index", len(self.runs)))
        self.runs.append(request.run_plan.run_identity)
        self.barrier.wait(timeout=5.0)
        if fold == 1:
            raise RuntimeError("simulated TRAIN2 child failure for fold 1")
        return super().train(request)


def test_one_completion_batch_truthfully_classifies_already_done_sibling(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Classify the complete done batch before surfacing the first failure (B3).

    When a completion batch contains both a successful and a failing future,
    pop every done future from active, count completed and failed truthfully,
    and raise after classification so the failure report distinguishes active=0,
    completed=1, failed=1, queued excluding both submitted slots, no EVAL2 runs,
    and the completed slot's authenticated summary is reused on restart.
    """

    import concurrent.futures
    from concurrent.futures import FIRST_COMPLETED
    from mdstats.training_data import training_parallel

    config = _selected_campaign(tmp_path)

    orig_build_plan = training_parallel.build_training_concurrency_plan

    def plan_with_two_initial_jobs(*args, **kwargs):
        p = orig_build_plan(*args, **kwargs)
        from dataclasses import replace
        return replace(p, initial_jobs=2, maximum_jobs=2)

    monkeypatch.setattr(
        training_parallel, "build_training_concurrency_plan", plan_with_two_initial_jobs
    )

    orig_wait = concurrent.futures.wait

    def wait_both_done(futures, timeout=None, return_when=FIRST_COMPLETED):
        for f in futures:
            try:
                f.exception(timeout=5.0)
            except Exception:
                pass
        return orig_wait(futures, timeout=timeout, return_when=return_when)

    monkeypatch.setattr(concurrent.futures, "wait", wait_both_done)

    harness = _MixedDoneBatchHarness()
    with pytest.raises(RuntimeError, match="simulated TRAIN2 child failure for fold 1"):
        fx.run_cross_validate(config, harness)

    printed = capsys.readouterr().out
    failure_lines = [
        line
        for line in printed.splitlines()
        if "[TRAIN scheduler] status=failed" in line
    ]
    assert failure_lines, printed
    line = failure_lines[-1]

    # Verify truthful reporting from the classified batch
    assert "completed_jobs=1" in line, line
    assert "failed_jobs=1" in line, line
    assert "active_jobs=0" in line, line
    assert "queued_jobs=0" in line, line
    assert harness.evaluations == [], "no EVAL2 may run after TRAIN wave failure"
    _no_cv_acceptance(config)

    # Restart: the completed fold 0 must be reused from its authenticated summary
    resumed = _TimedHarness()
    assert fx.run_cross_validate(config, resumed) == 0
    assert len(resumed.runs) == 1, (
        "the completed slot must be reused on restart rather than retrained; "
        f"got retrained runs: {resumed.runs}"
    )
    assert resumed.evaluations, "the healthy restart must complete through EVAL2"

