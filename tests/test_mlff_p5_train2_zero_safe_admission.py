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


# --- 6. A sustained memory hazard stops owned TRAIN2 before CUDA OOM -------


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


def test_a_sustained_memory_hazard_stops_owned_training_before_cuda_oom(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Occupancy above the envelope during initialization stops the run.

    This drives the real P5 admission/supervision owner with a CUDA device and a
    bounded deterministic telemetry fixture: admission sees a clean baseline, and
    the child is then observed above the configured envelope while it is still
    initializing - exactly the target-host situation that previously survived as
    "waiting for true epoch compute" until CUDA ran out of memory.
    """

    from dataclasses import replace

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        execute_post_selection_cross_validation,
    )
    from mdstats.training_data.training_parallel import (
        GpuTelemetrySample,
        TrainingMemorySafetyError,
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
        # Admission observes a clean device; the device goes over the envelope
        # only once the child is actually running, which is the ordering the
        # target-host failure had.
        used = 22.5 if live["training"] else 0.4
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=4.0,
            used_bytes=int(used * gib),
            total_bytes=24 * gib,
        )

    # The scheduler resolves this from ``training_parallel`` at call time, so the
    # bounded resource fixture is installed on the owning module.
    from mdstats.training_data import training_parallel

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
        with pytest.raises(TrainingMemorySafetyError) as stop:
            execute_post_selection_cross_validation(context)
    finally:
        store.close()

    assert "before CUDA out of memory" in str(stop.value)
    assert "training envelope" in str(stop.value)
    assert len(harness.runs) == 1, "admission must not have launched a second job"
    _no_cv_acceptance(config)


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
