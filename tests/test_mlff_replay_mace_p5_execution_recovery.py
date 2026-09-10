"""Bounded owner-level evidence for the consolidated P5 recovery workplan."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fixture
import tests.test_mlff_downstream_integration_closure as downstream
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_post_selection_runtime as runtime
from mdstats.training_data.post_selection_execution import PostSelectionExecutionError
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.training_parallel import GpuTelemetrySample

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
            device_name="bounded-test-gpu",
            free_bytes=int(23.6 * _GIB),
            total_bytes=24 * _GIB,
            budget_bytes=int(24 * 0.9 * _GIB),
            reason="bounded-test",
        ),
    )


class _PromotionTrainer(fixture.PostSelectionHarness):
    """Substitute only the expensive trainer while retaining P5 supervision."""

    def __init__(self, *, fail_first_after_promotion: bool = False) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._runtime_lock = threading.Lock()
        self.fail_first_after_promotion = fail_first_after_promotion
        self.first_entered = threading.Event()
        self.second_entered = threading.Event()
        self.cancel_seen = threading.Event()

    def train(self, request):
        from mdstats.training_data.post_selection_execution import (
            _PostSelectionTrainingProgress,
        )
        from mdstats.training_data.train2_runtime import load_train2_runtime_summary

        with self._lock:
            self.requests.append(request)
            ordinal = len(self.requests)

        config = json.loads(
            (
                request.materialization_directory
                / request.materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        metric_path = (
            Path(request.materialization_directory).parent
            / "results"
            / f"{config['name']}_run-{int(config['seed'])}_train.txt"
        )
        metric_path.parent.mkdir(parents=True, exist_ok=True)
        progress = _PostSelectionTrainingProgress(
            request,
            metric_path=metric_path,
            initial_summary=None,
            summary_loader=load_train2_runtime_summary,
        )
        metric_path.write_text(
            json.dumps({"mode": "opt", "epoch": 0, "loss": 0.25}) + "\n",
            encoding="utf-8",
        )
        observation = progress.refresh(request.checkpoint_directory)
        assert observation["phase"] == "training"
        assert observation["true_epoch"] is True
        assert request.progress_observer is not None
        request.progress_observer(
            {**observation, "status": "running", "alive": True}
        )

        if ordinal == 1:
            self.first_entered.set()
            assert self.second_entered.wait(8.0), (
                "the real P5 scheduler did not admit the safe second training run"
            )
            if self.fail_first_after_promotion:
                raise RuntimeError("bounded active-run failure")
        else:
            self.second_entered.set()
            if self.fail_first_after_promotion:
                cancellation_event = request.cancellation_event
                assert cancellation_event is not None
                while not cancellation_event.is_set():
                    time.sleep(0.01)
                self.cancel_seen.set()
                raise RuntimeError("bounded sibling cancellation")

        # The fixture's TRAIN2 runtime is still the real continuation,
        # checkpoint, evidence, and EVAL2 owner. Serialize only its toy model
        # section because this test is exercising scheduler wiring, not a
        # concurrent process-global torch fixture.
        with self._runtime_lock:
            return fixture.train_like_mace(request)


@pytest.mark.slow
def test_real_p5_per_size_scheduler_promotes_safe_live_training_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live child heartbeat reaches the real P5 scheduler and admits run two."""

    config_text = fixture.fixture_config_text() + """

[execution]
parallel_training_jobs = 0
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 2
parallel_training_epoch_stabilization_seconds = 0.0
parallel_training_epoch_activity_timeout_seconds = 10.0
parallel_training_epoch_stability_samples = 2
parallel_training_monitor_interval_seconds = 0.05
training_progress_interval_seconds = 0.05
"""
    config, _workspace = fixture.build_selected_campaign(
        tmp_path / "campaign", config_text=config_text
    )
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    harness = _PromotionTrainer()

    def safe_telemetry(_device: str) -> GpuTelemetrySample:
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=5.0,
            used_bytes=int(0.4 * _GIB),
            total_bytes=24 * _GIB,
        )

    monkeypatch.setattr(cli, "_performance_resources", lambda _cfg: _resources())
    from mdstats.training_data import training_parallel

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", safe_telemetry)
    try:
        contexts = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )
        assert len(contexts) == 1
        # The campaign remains scientifically CPU-configured; this bounded
        # owner test supplies safe synthetic GPU telemetry solely to exercise
        # the existing adaptive admission branch without claiming GPU
        # qualification or changing the method identity.
        context = replace(
            contexts[0],
            method_policies=replace(
                contexts[0].method_policies,
                device="cuda:0",
            ),
        )
        _plan, acceptance = runtime.execute_post_selection_cross_validation(context)
        assert acceptance.accepted
        assert harness.first_entered.is_set()
        assert harness.second_entered.is_set()
        assert len(harness.requests) == 2
    finally:
        store.close()


@pytest.mark.slow
def test_real_p5_scheduler_failure_stops_admission_and_cancels_active_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed active run cannot admit queued work or leave its sibling live."""

    config_text = fixture.fixture_config_text().replace(
        "seeds = [11]", "seeds = [11, 12]"
    ) + """

[execution]
parallel_training_jobs = 0
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 2
parallel_training_epoch_stabilization_seconds = 0.0
parallel_training_epoch_activity_timeout_seconds = 10.0
parallel_training_epoch_stability_samples = 2
parallel_training_monitor_interval_seconds = 0.05
training_progress_interval_seconds = 0.05
"""
    config, _workspace = fixture.build_selected_campaign(
        tmp_path / "campaign", config_text=config_text
    )
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    harness = _PromotionTrainer(fail_first_after_promotion=True)

    def safe_telemetry(_device: str) -> GpuTelemetrySample:
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=5.0,
            used_bytes=int(0.4 * _GIB),
            total_bytes=24 * _GIB,
        )

    monkeypatch.setattr(cli, "_performance_resources", lambda _cfg: _resources())
    from mdstats.training_data import training_parallel

    monkeypatch.setattr(training_parallel, "query_gpu_telemetry", safe_telemetry)
    try:
        contexts = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )
        context = replace(
            contexts[0],
            method_policies=replace(
                contexts[0].method_policies,
                device="cuda:0",
            ),
        )
        with pytest.raises(RuntimeError, match="bounded active-run failure"):
            runtime.execute_post_selection_cross_validation(context)
        assert harness.first_entered.is_set()
        assert harness.second_entered.is_set()
        assert harness.cancel_seen.is_set()
        # Four CV slots exist with two seeds and two folds; only the two
        # already-active slots may have reached the trainer before failure.
        assert len(harness.requests) == 2
    finally:
        store.close()


def _pre_fix_foundation_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Leave a real completed TRAIN2 run with only the pre-fix config spelling."""

    campaign_root = tmp_path / "campaign-root"
    campaign_root.mkdir()
    store_dir = tmp_path / "foundation-store"
    store_dir.mkdir()
    foundation = store_dir / "foundation.model"
    import mdstats.training_data.post_selection_execution as execution

    original_config_builder = runtime._post_selection_mace_config
    original_execution_config_builder = execution._post_selection_mace_config

    def pre_fix_config(**kwargs):
        config = original_config_builder(**kwargs)
        config.pop("compute_avg_num_neighbors", None)
        return config

    monkeypatch.setattr(runtime, "_post_selection_mace_config", pre_fix_config)
    monkeypatch.setattr(execution, "_post_selection_mace_config", pre_fix_config)
    config = downstream._foundation_backed_campaign(
        campaign_root,
        foundation=foundation,
        spelling="../foundation-store/foundation.model",
    )
    pauser = downstream._PauseAfterFullHorizon()
    with pytest.raises(AssertionError, match="bounded interruption"):
        p4d._run(
            config,
            "cross-validate",
            _external_post_selection_trainer=pauser,
            _external_inference_evaluator=fixture.PostSelectionHarness().evaluate,
        )
    assert pauser.requests
    monkeypatch.setattr(runtime, "_post_selection_mace_config", original_config_builder)
    monkeypatch.setattr(
        execution,
        "_post_selection_mace_config",
        original_execution_config_builder,
    )
    return (
        config,
        Path(pauser.requests[0].checkpoint_directory).parent,
        pauser.requests[0].run_plan.run_identity,
    )


def _set_persisted_architecture(run_root: Path, architecture_digest: str) -> None:
    """Update the existing authenticated TRAIN2 copies as a test counterfactual."""

    import torch

    from mdstats.training_data.train2_runtime import Train2RuntimeSummary

    checkpoint_directory = run_root / "checkpoints"
    summary_paths = [
        checkpoint_directory / "train2_runtime.json",
        *sorted(checkpoint_directory.glob("train2_runtime_epoch-*.json")),
    ]
    for summary_path in summary_paths:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        payload["model_architecture_digest"] = architecture_digest
        payload.pop("content_digest", None)
        summary = Train2RuntimeSummary.from_dict(payload)
        summary_path.write_text(
            json.dumps(summary.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    companion_path = checkpoint_directory / "train2_runtime.pt"
    companion = torch.load(companion_path, map_location="cpu", weights_only=False)
    companion["model_architecture_digest"] = architecture_digest
    torch.save(companion, companion_path)


@pytest.mark.slow
def test_pre_fix_completed_representation_reuses_equal_persisted_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the authenticated realized architecture permits pre-fix reuse."""

    config, run_root, old_run_identity = _pre_fix_foundation_workspace(
        tmp_path, monkeypatch
    )
    materialization = run_root / "materialization"
    config_path = materialization / "post_selection_mace_config.yaml"
    config_before = config_path.read_bytes()
    persisted = json.loads(
        (run_root / "checkpoints" / "train2_runtime.json").read_text(
            encoding="utf-8"
        )
    )
    assert "model_architecture_digest" not in persisted
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        context = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=fixture.PostSelectionHarness().train,
            inference_evaluator=fixture.PostSelectionHarness().evaluate,
        )[0]
        old_config = json.loads(config_path.read_text(encoding="utf-8"))
        current_config = dict(old_config)
        current_config["compute_avg_num_neighbors"] = False
        current_architecture, _realization = (
            runtime._post_selection_current_training_architecture(
                context,
                current_config=current_config,
            )
        )
    finally:
        store.close()
    _set_persisted_architecture(run_root, current_architecture)

    resumed = fixture.PostSelectionHarness()
    assert fixture.run_cross_validate(config, resumed) == 0
    # The completed TRAIN2 horizon is reused directly; the retry reaches EVAL2
    # without launching another trainer for this run. The other required fold
    # is still independently executed.
    assert resumed.requests
    assert all(
        request.run_plan.run_identity != old_run_identity
        for request in resumed.requests
    )
    assert config_path.read_bytes() == config_before
    assert "compute_avg_num_neighbors" not in json.loads(
        config_path.read_text(encoding="utf-8")
    )


@pytest.mark.slow
def test_pre_fix_different_persisted_architecture_is_preserved_and_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-fix representation cannot admit a different realized model."""

    config, run_root, _old_run_identity = _pre_fix_foundation_workspace(
        tmp_path, monkeypatch
    )
    materialization = run_root / "materialization"
    config_before = materialization.joinpath(
        "post_selection_mace_config.yaml"
    ).read_bytes()
    _set_persisted_architecture(run_root, "f" * 64)
    checkpoint_before = downstream._file_tree_bytes(run_root / "checkpoints")

    resumed = fixture.PostSelectionHarness()
    with pytest.raises(PostSelectionExecutionError, match="architecture differs"):
        fixture.run_cross_validate(config, resumed)
    assert resumed.requests == []
    assert materialization.joinpath("post_selection_mace_config.yaml").read_bytes() == (
        config_before
    )
    assert downstream._file_tree_bytes(run_root / "checkpoints") == checkpoint_before
