from __future__ import annotations

import json
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


def _progress_request(*, timeout: float = 10.0, initial_summary=None):
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
        optimizer_policy=SimpleNamespace(batch_size=1),
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
