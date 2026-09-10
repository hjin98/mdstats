from __future__ import annotations

import json
import pytest
import time
from pathlib import Path
from types import SimpleNamespace

from mdstats.training_data.post_selection_execution import (
    _PostSelectionTrainingProgress,
)
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.training_parallel import (
    AdaptiveTrainingConcurrency,
    GpuTelemetrySample,
    TrainingConcurrencyPolicy,
    build_training_concurrency_plan,
)

_GIB = 1024 ** 3


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
            device_name="RTX 3090",
            free_bytes=int(23.6 * _GIB),
            total_bytes=24 * _GIB,
            budget_bytes=int(24 * 0.9 * _GIB),
            reason="available",
        ),
    )


def _sample(seconds: float, used_gib: float, utilization: float = 25.0) -> GpuTelemetrySample:
    return GpuTelemetrySample(
        sampled_monotonic=seconds,
        device_index=0,
        utilization_percent=utilization,
        used_bytes=int(used_gib * _GIB),
        total_bytes=24 * _GIB,
    )


def _plan(policy: TrainingConcurrencyPolicy | None = None):
    resolved = policy or TrainingConcurrencyPolicy(epoch_stabilization_seconds=0.0)
    return build_training_concurrency_plan(
        task_count=16,
        device="cuda:0",
        loader_workers_per_job=4,
        resources=_resources(),
        policy=resolved,
        gpu_sample=_sample(0.0, 0.4, 1.0),
    )


def test_rtx3090_auto_plan_starts_one_and_caps_at_three() -> None:
    policy = TrainingConcurrencyPolicy(epoch_stabilization_seconds=0.0)
    plan = _plan(policy)
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 3
    assert plan.gpu_utilization_budget_percent == 90.0
    assert plan.cpu_threads_per_job >= 1


def test_stable_initialization_does_not_authorize_second_job() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    decision = None
    for second in range(1, 9):
        decision = controller.observe(
            _sample(float(second), 1.2, 5.0),
            active_jobs=1,
            epoch_active_jobs=0,
            now=float(second),
        )
    assert decision is not None
    assert not decision.changed
    assert controller.target_jobs == 1
    assert "true epoch" in decision.reason


def test_one_true_epoch_job_promotes_to_two_when_both_projections_are_safe() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        maximum_auto_jobs=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    decision = None
    for second, used, util in (
        (1.0, 6.08, 24.0),
        (2.0, 6.10, 25.0),
        (3.0, 6.09, 24.0),
        (4.0, 6.10, 25.0),
    ):
        decision = controller.observe(
            _sample(second, used, util),
            active_jobs=1,
            epoch_active_jobs=1,
            now=second,
        )
    assert decision is not None
    assert decision.changed
    assert controller.target_jobs == 2
    assert decision.predicted_utilization_percent_at_target is not None
    assert decision.predicted_utilization_percent_at_target < 90.0
    assert decision.predicted_bytes_at_target is not None
    assert decision.predicted_bytes_at_target < controller.plan.gpu_memory_budget_bytes


def test_two_jobs_do_not_promote_when_projected_gpu_utilization_exceeds_90_percent() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        maximum_auto_jobs=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    controller.target_jobs = 2
    decision = None
    for second, used, util in (
        (1.0, 11.75, 69.0),
        (2.0, 11.78, 70.0),
        (3.0, 11.76, 69.0),
        (4.0, 11.77, 70.0),
    ):
        decision = controller.observe(
            _sample(second, used, util),
            active_jobs=2,
            epoch_active_jobs=2,
            now=second,
        )
    assert decision is not None
    assert not decision.changed
    assert controller.target_jobs == 2
    assert decision.predicted_utilization_percent_at_target is not None
    assert decision.predicted_utilization_percent_at_target >= 90.0
    assert "GPU utilization" in decision.reason


def test_two_jobs_promote_to_three_only_when_memory_and_utilization_are_both_safe() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        maximum_auto_jobs=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    controller.target_jobs = 2
    decision = None
    for second, used, util in (
        (1.0, 11.75, 49.0),
        (2.0, 11.78, 50.0),
        (3.0, 11.76, 49.0),
        (4.0, 11.77, 50.0),
    ):
        decision = controller.observe(
            _sample(second, used, util),
            active_jobs=2,
            epoch_active_jobs=2,
            now=second,
        )
    assert decision is not None
    assert decision.changed
    assert controller.target_jobs == 3
    assert decision.predicted_utilization_percent_at_target is not None
    assert decision.predicted_utilization_percent_at_target < 90.0
    assert decision.predicted_bytes_at_target is not None
    assert decision.predicted_bytes_at_target < controller.plan.gpu_memory_budget_bytes


def test_stable_post_add_saturation_throttles_future_replacements() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        maximum_auto_jobs=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    controller.target_jobs = 3
    decision = None
    for second, used, util in (
        (1.0, 17.2, 94.0),
        (2.0, 17.3, 95.0),
        (3.0, 17.2, 94.0),
        (4.0, 17.3, 95.0),
    ):
        decision = controller.observe(
            _sample(second, used, util),
            active_jobs=3,
            epoch_active_jobs=3,
            now=second,
        )
    assert decision is not None
    assert decision.changed
    assert decision.target_jobs == 2
    assert "future replacements throttled" in decision.reason


def test_cpu_auto_mode_remains_serial() -> None:
    policy = TrainingConcurrencyPolicy()
    plan = build_training_concurrency_plan(
        task_count=8,
        device="cpu",
        loader_workers_per_job=4,
        resources=_resources(),
        policy=policy,
        gpu_sample=None,
    )
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 1


def _progress_request(
    *, timeout: float = 10.0, initial_summary=None, batch_size: int = 1
):
    request = SimpleNamespace(
        plan=SimpleNamespace(
            budget_policy=SimpleNamespace(planned_epochs=2),
            replay_monitor_enabled=False,
            structures_per_epoch=1,
        ),
        materialization=SimpleNamespace(
            target_train_artifact=SimpleNamespace(configuration_count=1)
        ),
        replay_train_artifact=None,
        optimizer_policy=SimpleNamespace(batch_size=batch_size),
        optimizer_activity_timeout_seconds=timeout,
    )
    return request, initial_summary


def test_p5_progress_readiness_uses_fresh_optimizer_activity_not_epoch_count(
    tmp_path: Path,
) -> None:
    """The real progress observer exposes the scheduler's current-work facts."""

    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    metric_path = tmp_path / "results" / "train.txt"
    metric_path.parent.mkdir()
    request, initial_summary = _progress_request(
        timeout=10.0,
        initial_summary=SimpleNamespace(
            completed_updates=1,
            completed_epochs=1,
            planned_updates=2,
            phase="validation",
        ),
    )
    progress = _PostSelectionTrainingProgress(
        request,
        metric_path=metric_path,
        initial_summary=initial_summary,
        summary_loader=lambda _directory: initial_summary,
    )

    # A resumed completed epoch is not current optimizer activity.
    assert progress.refresh(checkpoint_directory)["true_epoch"] is False

    metric_path.write_text(
        json.dumps({"mode": "opt", "epoch": 1, "loss": 0.25}) + "\n",
        encoding="utf-8",
    )
    ready = progress.refresh(checkpoint_directory)
    assert ready["phase"] == "training"
    assert ready["true_epoch"] is True

    # One ordinary poll without a new optimizer record remains ready inside
    # the configured activity window.
    assert progress.refresh(checkpoint_directory)["true_epoch"] is True

    with metric_path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"mode": "eval", "epoch": 1, "loss": 0.20}) + "\n"
        )
    validating = progress.refresh(checkpoint_directory)
    assert validating["phase"] == "validation"
    assert validating["true_epoch"] is False

    with metric_path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"mode": "opt", "epoch": 2, "loss": 0.15}) + "\n"
        )
    assert progress.refresh(checkpoint_directory)["true_epoch"] is True

    progress.last_optimizer_update_monotonic -= 11.0
    assert progress.refresh(checkpoint_directory)["true_epoch"] is False


def test_p5_progress_keeps_unknown_horizon_for_empty_full_batch_projection(
    tmp_path: Path,
) -> None:
    """A tiny fold does not publish a zero denominator before TRAIN2 reports its loader."""

    request = _progress_request(batch_size=4)[0]
    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    metric_path = tmp_path / "results" / "train.txt"
    metric_path.parent.mkdir()
    progress = _PostSelectionTrainingProgress(
        request,
        metric_path=metric_path,
        initial_summary=None,
        summary_loader=lambda _directory: None,
    )
    metric_path.write_text(_opt_line(), encoding="utf-8")

    observation = progress.refresh(checkpoint_directory)
    assert observation["planned_updates"] is None
    assert observation["completed_updates"] == 1
    request.progress_observer = None
    request.progress_callback = None
    request.progress_context = None
    request.telemetry_ref = None
    progress.emit(
        request,
        checkpoint_directory=checkpoint_directory,
        visible_interval_seconds=10.0,
        status="running",
        force=True,
    )


def _new_metrics_progress(tmp_path: Path, *, initial_summary=None):
    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    metric_path = tmp_path / "results" / "train.txt"
    metric_path.parent.mkdir()
    request, _ = _progress_request(initial_summary=initial_summary)
    return (
        _PostSelectionTrainingProgress(
            request,
            metric_path=metric_path,
            initial_summary=initial_summary,
            summary_loader=lambda _directory: initial_summary,
        ),
        checkpoint_directory,
        metric_path,
    )


def _opt_line() -> str:
    return json.dumps({"mode": "opt", "epoch": 0, "loss": 0.25}) + "\n"


def test_p5_metrics_equal_optimizer_lines_are_two_append_only_events(
    tmp_path: Path,
) -> None:
    progress, checkpoint_directory, metric_path = _new_metrics_progress(tmp_path)

    metric_path.write_text(_opt_line() * 2, encoding="utf-8")
    observation = progress.refresh(checkpoint_directory)

    assert observation["optimizer_updates_since_launch"] == 2
    assert progress.metric_offset == metric_path.stat().st_size


def test_p5_metrics_equal_optimizer_lines_in_separate_reads_advance_activity(
    tmp_path: Path,
) -> None:
    progress, checkpoint_directory, metric_path = _new_metrics_progress(tmp_path)

    metric_path.write_text(_opt_line(), encoding="utf-8")
    assert progress.refresh(checkpoint_directory)["optimizer_updates_since_launch"] == 1
    first_activity = progress.last_optimizer_update_monotonic
    time.sleep(0.001)

    with metric_path.open("a", encoding="utf-8") as stream:
        stream.write(_opt_line())
    observation = progress.refresh(checkpoint_directory)

    assert observation["optimizer_updates_since_launch"] == 2
    assert progress.last_optimizer_update_monotonic is not None
    assert first_activity is not None
    assert progress.last_optimizer_update_monotonic > first_activity


def test_p5_metrics_refresh_without_new_bytes_does_not_count_or_refresh(
    tmp_path: Path,
) -> None:
    progress, checkpoint_directory, metric_path = _new_metrics_progress(tmp_path)

    metric_path.write_text(_opt_line(), encoding="utf-8")
    assert progress.refresh(checkpoint_directory)["optimizer_updates_since_launch"] == 1
    activity = progress.last_optimizer_update_monotonic

    observation = progress.refresh(checkpoint_directory)

    assert observation["optimizer_updates_since_launch"] == 1
    assert progress.last_optimizer_update_monotonic == activity


def test_p5_metrics_partial_optimizer_line_counts_once_after_newline(
    tmp_path: Path,
) -> None:
    progress, checkpoint_directory, metric_path = _new_metrics_progress(tmp_path)
    line = _opt_line()

    metric_path.write_text(line[:-1], encoding="utf-8")
    assert progress.refresh(checkpoint_directory)["optimizer_updates_since_launch"] == 0
    assert progress.metric_remainder == line[:-1]

    with metric_path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    observation = progress.refresh(checkpoint_directory)

    assert observation["optimizer_updates_since_launch"] == 1
    assert progress.metric_remainder == ""


def test_p5_metrics_eval_records_validate_phase_without_optimizer_count(
    tmp_path: Path,
) -> None:
    progress, checkpoint_directory, metric_path = _new_metrics_progress(tmp_path)

    metric_path.write_text(
        json.dumps({"mode": "eval", "epoch": 0, "loss": 0.20}) + "\n",
        encoding="utf-8",
    )
    observation = progress.refresh(checkpoint_directory)

    assert observation["phase"] == "validation"
    assert observation["optimizer_updates_since_launch"] == 0
    assert observation["true_epoch"] is False


def test_p5_metrics_restart_ignores_historical_bytes_and_counts_later_append(
    tmp_path: Path,
) -> None:
    initial_summary = SimpleNamespace(
        completed_updates=2,
        completed_epochs=1,
        planned_updates=4,
        phase="validation",
    )
    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    metric_path = tmp_path / "results" / "train.txt"
    metric_path.parent.mkdir()
    metric_path.write_text(_opt_line() * 2, encoding="utf-8")
    request, _ = _progress_request(initial_summary=initial_summary)
    progress = _PostSelectionTrainingProgress(
        request,
        metric_path=metric_path,
        initial_summary=initial_summary,
        summary_loader=lambda _directory: initial_summary,
    )

    historical = progress.refresh(checkpoint_directory)
    assert historical["optimizer_updates_since_launch"] == 0
    assert historical["completed_updates"] == 2

    with metric_path.open("a", encoding="utf-8") as stream:
        stream.write(_opt_line())
    later = progress.refresh(checkpoint_directory)

    assert later["optimizer_updates_since_launch"] == 1
    assert later["completed_updates"] == 3


def test_fluctuating_epoch_utilization_is_averaged_not_waited_out() -> None:
    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=30.0,
        monitor_interval_seconds=10.0,
        stability_samples=4,
        maximum_auto_jobs=4,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    decision = None
    # Large, realistic kernel/data-loader fluctuations. The mean remains low
    # enough that a second job is safe; variation itself must not block forever.
    for second, used, util in (
        (0.0, 6.0, 10.0),
        (10.0, 6.2, 55.0),
        (20.0, 6.1, 15.0),
        (30.0, 6.2, 50.0),
    ):
        decision = controller.observe(
            _sample(second, used, util),
            active_jobs=1,
            epoch_active_jobs=1,
            now=second,
        )
    assert decision is not None
    assert decision.changed
    assert controller.target_jobs == 2
    assert "averages" in decision.reason


# --- Zero-safe TRAIN2 admission -------------------------------------------
#
# The target-host counterexample: a 24 GiB device whose aggregate occupancy is
# already 20.2 GiB cannot hold even the first configured 6 GiB training job
# under the 90% envelope. The former planner manufactured `initial=1, ceiling=1`
# from that state and the submission loop floored the target to one, so a
# zero-safe resource state could never reach execution.


def _contended_resources(
    *,
    ram_budget_bytes: int | None = 96 * _GIB,
    gpu: GpuResourceSnapshot | None = None,
) -> SystemResourceSnapshot:
    base = _resources()
    return SystemResourceSnapshot(
        cpu_threads_available=base.cpu_threads_available,
        cpu_fraction=base.cpu_fraction,
        cpu_threads_budget=base.cpu_threads_budget,
        ram_available_bytes=base.ram_available_bytes,
        ram_fraction=base.ram_fraction,
        ram_budget_bytes=ram_budget_bytes,
        gpu_memory_fraction=base.gpu_memory_fraction,
        gpu=base.gpu if gpu is None else gpu,
    )


def test_target_host_baseline_resolves_to_zero_admissible_jobs() -> None:
    """20.2 GiB baseline + 6 GiB job vs a 21.6 GiB envelope is zero jobs."""

    policy = TrainingConcurrencyPolicy(epoch_stabilization_seconds=0.0)
    plan = build_training_concurrency_plan(
        task_count=5,
        device="cuda:0",
        loader_workers_per_job=4,
        resources=_contended_resources(),
        policy=policy,
        gpu_sample=_sample(0.0, 20.2, 12.0),
    )
    assert plan.maximum_jobs == 0
    assert plan.initial_jobs == 0
    assert plan.zero_safe_admission
    # The 90% default is untouched: the envelope is what the policy says.
    assert plan.gpu_memory_budget_bytes == int(24 * _GIB * 0.90)
    assert "zero currently admissible training jobs" in plan.reason
    assert "21.6 GiB training VRAM envelope" in plan.reason
    assert "zero safe admission" in plan.summary()


def test_positive_configured_job_cap_cannot_override_zero_safe_admission() -> None:
    """``parallel_training_jobs`` is a maximum cap, never an admission bypass."""

    policy = TrainingConcurrencyPolicy(
        requested_jobs=4, epoch_stabilization_seconds=0.0
    )
    plan = build_training_concurrency_plan(
        task_count=5,
        device="cuda:0",
        loader_workers_per_job=4,
        resources=_contended_resources(),
        policy=policy,
        gpu_sample=_sample(0.0, 20.2, 12.0),
    )
    assert plan.maximum_jobs == 0
    assert plan.initial_jobs == 0


def test_insufficient_host_ram_resolves_to_zero_safe_training_jobs() -> None:
    """A host-RAM budget too small for one process is zero jobs, not one."""

    policy = TrainingConcurrencyPolicy(
        estimated_ram_mib_per_job=8192.0, epoch_stabilization_seconds=0.0
    )
    plan = build_training_concurrency_plan(
        task_count=4,
        device="cuda:0",
        loader_workers_per_job=2,
        resources=_contended_resources(ram_budget_bytes=4 * _GIB),
        policy=policy,
        gpu_sample=_sample(0.0, 0.4, 1.0),
    )
    assert plan.maximum_jobs == 0
    assert plan.zero_safe_admission
    assert "host RAM budget" in plan.reason


def test_safe_low_baseline_still_starts_exactly_one_job() -> None:
    """Zero-safe representability must not disturb ordinary startup."""

    plan = _plan()
    assert plan.initial_jobs == 1
    assert not plan.zero_safe_admission
    assert plan.gpu_memory_observation == "telemetry"
    assert plan.utilization_telemetry_available


def test_missing_utilization_telemetry_selects_conservative_serial_work() -> None:
    """Known memory capacity with no telemetry runs one job and never promotes."""

    policy = TrainingConcurrencyPolicy(epoch_stabilization_seconds=0.0)
    plan = build_training_concurrency_plan(
        task_count=8,
        device="cuda:0",
        loader_workers_per_job=4,
        resources=_contended_resources(),
        policy=policy,
        gpu_sample=None,
    )
    assert plan.gpu_memory_observation == "snapshot"
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 1
    assert not plan.utilization_telemetry_available

    controller = AdaptiveTrainingConcurrency(plan, policy)
    decision = controller.observe(
        _sample(1.0, 6.0, 30.0), active_jobs=1, epoch_active_jobs=1, now=1.0
    )
    assert controller.target_jobs == 1
    assert not decision.changed
    assert decision.memory_safe is True
    assert "parallel promotion is not authorized" in decision.reason


def test_unobservable_device_memory_blocks_automatic_admission() -> None:
    """Device availability and memory observability are separate facts."""

    from mdstats.training_data.training_parallel import (
        TrainingResourceObservabilityError,
    )

    blind = GpuResourceSnapshot(
        available=True,
        device_count=1,
        selected_device=0,
        device_name="RTX 3090",
        free_bytes=None,
        total_bytes=None,
        budget_bytes=None,
        reason="CUDA present; memory probe failed",
    )
    with pytest.raises(TrainingResourceObservabilityError):
        build_training_concurrency_plan(
            task_count=3,
            device="cuda:0",
            loader_workers_per_job=2,
            resources=_contended_resources(gpu=blind),
            policy=TrainingConcurrencyPolicy(epoch_stabilization_seconds=0.0),
            gpu_sample=None,
        )


def test_memory_hazard_is_detected_before_true_epoch_readiness() -> None:
    """An over-envelope child in initialization is a hazard, not "waiting"."""

    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0, memory_hazard_grace_seconds=60.0
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)

    early = controller.observe(
        _sample(5.0, 22.0, 3.0), active_jobs=1, epoch_active_jobs=0, now=5.0
    )
    assert early.memory_safe is False
    assert not early.memory_hazard
    assert "true epoch" not in early.reason
    assert "training envelope" in early.reason

    sustained = controller.observe(
        _sample(70.0, 22.0, 3.0), active_jobs=1, epoch_active_jobs=0, now=70.0
    )
    assert sustained.memory_hazard
    assert sustained.memory_safe is False
    assert "21.6 GiB training envelope" in sustained.reason


def test_a_transient_vram_spike_does_not_stop_training() -> None:
    """The bounded debounce must not convert a fluctuation into a stop."""

    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0, memory_hazard_grace_seconds=60.0
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    assert not controller.observe(
        _sample(5.0, 22.0, 80.0), active_jobs=1, epoch_active_jobs=1, now=5.0
    ).memory_hazard
    recovered = controller.observe(
        _sample(15.0, 6.0, 80.0), active_jobs=1, epoch_active_jobs=1, now=15.0
    )
    assert not recovered.memory_hazard
    assert recovered.memory_safe is True
    assert not controller.observe(
        _sample(200.0, 22.0, 80.0), active_jobs=1, epoch_active_jobs=1, now=200.0
    ).memory_hazard, "the unsafe window restarts after a safe observation"


def test_an_idle_baseline_above_the_envelope_is_not_a_hazard_stop() -> None:
    """With nothing admitted there is no owned execution to stop."""

    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0, memory_hazard_grace_seconds=0.0
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    decision = controller.observe(
        _sample(5.0, 23.0, 0.0), active_jobs=0, epoch_active_jobs=0, now=5.0
    )
    assert not decision.memory_hazard


def test_active_work_consuming_capacity_holds_instead_of_collapsing_to_zero() -> None:
    """A saturated envelope while work is live is a wait, not zero admission.

    ``minimum_parallel_training_jobs=1`` means "once one job is feasible, do not
    voluntarily target less than one". Zero safe admission is a statement about
    what can be *launched*, never a reason to abandon live work.
    """

    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        memory_hazard_grace_seconds=600.0,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    decision = None
    for second, used in ((1.0, 19.0), (2.0, 19.1), (3.0, 19.0), (4.0, 19.1)):
        decision = controller.observe(
            _sample(second, used, 40.0),
            active_jobs=1,
            epoch_active_jobs=1,
            now=second,
        )
    assert decision is not None
    assert not decision.changed
    assert controller.target_jobs == 1, "live work must never be targeted away"
    assert decision.memory_safe is True
    assert "not admitted" in decision.reason


def test_over_envelope_occupancy_with_several_jobs_still_throttles() -> None:
    """Memory safety must not short-circuit the accepted saturation throttle.

    Two already-running jobs are not killed for being over the envelope: the
    calibrated throttle lowers the replacement target so concurrency falls when
    an active run finishes. Only a single owned job, which throttling cannot
    relieve, escalates to a stop.
    """

    policy = TrainingConcurrencyPolicy(
        epoch_stabilization_seconds=0.0,
        stability_samples=4,
        memory_hazard_grace_seconds=0.0,
    )
    controller = AdaptiveTrainingConcurrency(_plan(policy), policy)
    controller.target_jobs = 2
    decisions = [
        controller.observe(
            _sample(float(second), 22.0, 85.0),
            active_jobs=2,
            epoch_active_jobs=2,
            now=float(second),
        )
        for second in range(1, 6)
    ]
    assert not any(item.memory_hazard for item in decisions), (
        "running work must not be killed"
    )
    assert all(item.memory_safe is False for item in decisions)
    throttled = [item for item in decisions if "throttled" in item.reason]
    assert len(throttled) == 1, [item.reason for item in decisions]
    assert throttled[0].changed
    assert throttled[0].target_jobs == 1
    assert controller.target_jobs == 1
