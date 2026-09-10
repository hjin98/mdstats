"""Bounded owner-level evidence for the consolidated P5 recovery workplan."""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest

import tests._mlff_post_selection_fixture as fixture
import tests.test_mlff_downstream_integration_closure as downstream
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_post_selection_runtime as runtime
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


def _write_real_p5_process_wrapper(
    path: Path,
    event_directory: Path,
    *,
    failure_claim: Path | None = None,
    real_mace_model: bool = False,
    pre_train_sleep: float = 0.8,
) -> None:
    """Write a tiny child around the production P5 subprocess boundary.

    The parent still performs all P5 authentication and scheduling.  This
    child only replaces the expensive MACE loop below ``MacePostSelectionTrainer``:
    it emits one real optimizer metric, then runs the existing TRAIN2 fixture
    owner (optionally with a real MACE model) so the parent observes the same
    stream and receives the same durable summary shape as production.
    """

    repo_root = Path(__file__).resolve().parents[1]
    claim_expression = "None" if failure_claim is None else repr(str(failure_claim))
    path.write_text(
        f"""#!{sys.executable}
import argparse
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, {str(repo_root)!r})

from mdstats.training_data.post_selection_execution import PostSelectionMaterialization
from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
    Train2RuntimePlan,
)
from tests._mlff_post_selection_fixture import train_like_mace

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--model_dir', required=True)
parser.add_argument('--checkpoints_dir', required=True)
parser.add_argument('--log_dir', required=True)
parser.add_argument('--results_dir', required=True)
args = parser.parse_args()

event_directory = Path({str(event_directory)!r})
event_directory.mkdir(parents=True, exist_ok=True)

def event(kind, **payload):
    record = {{'kind': kind, 'pid': os.getpid(), **payload}}
    (event_directory / (kind + '-' + str(os.getpid()) + '.json')).write_text(
        json.dumps(record, sort_keys=True), encoding='utf-8'
    )

internal = json.loads(
    (Path.cwd() / 'post_selection_mace_config.yaml').read_text(encoding='utf-8')
)
event('started', seed=int(internal['seed']), checkpoints=str(args.checkpoints_dir))
metric_path = Path(args.results_dir) / (
    str(internal['name']) + '_run-' + str(int(internal['seed'])) + '_train.txt'
)
metric_path.parent.mkdir(parents=True, exist_ok=True)
with metric_path.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps({{'mode': 'opt', 'epoch': 0, 'loss': 0.25}}) + '\\n')
    handle.flush()

claim = {claim_expression}
if claim is not None:
    try:
        descriptor = os.open(str(claim), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        owner = False
    else:
        os.close(descriptor)
        owner = True
    if owner:
        time.sleep({float(pre_train_sleep)!r})
        raise SystemExit(37)
    try:
        while True:
            time.sleep(0.05)
    except KeyboardInterrupt:
        event('cancelled')
        raise

time.sleep({float(pre_train_sleep)!r})
plan = Train2RuntimePlan.from_dict(
    json.loads(os.environ[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE])
)
materialization = PostSelectionMaterialization.from_dict(
    json.loads((Path.cwd() / 'materialization.json').read_text(encoding='utf-8'))
)
# Deliberately omit optimizer_policy: the authenticated MACE execution
# authority passed by the parent is the child-side authority.  The optional
# real model path only needs the immutable materialization configuration.
request = SimpleNamespace(
    plan=plan,
    run_plan=SimpleNamespace(optimizer_seed=int(internal['seed'])),
    materialization=materialization,
    materialization_directory=Path.cwd(),
    checkpoint_directory=Path(args.checkpoints_dir),
    start_epoch=0,
)
summary = train_like_mace(request, real_mace_model={bool(real_mace_model)!r})
if summary is None:
    raise RuntimeError('TRAIN2 runtime produced no canonical summary')
event(
    'completed',
    seed=int(internal['seed']),
    checkpoints=str(args.checkpoints_dir),
    model_architecture_digest=getattr(summary, 'model_architecture_digest', None),
)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _real_p5_execution_config(*, seeds: str = "[11]") -> str:
    return fixture.fixture_config_text().replace(
        "seeds = [11]", f"seeds = {seeds}"
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
terminate_grace_seconds = 0.2
"""


def _patch_bounded_training_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


@pytest.mark.slow
def test_real_p5_process_scheduler_promotes_from_mace_metrics_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The production scheduler observes a real trainer subprocess and promotes run two."""

    config, _workspace = fixture.build_selected_campaign(
        tmp_path / "campaign",
        config_text=_real_p5_execution_config(),
    )
    events = tmp_path / "events"
    wrapper = tmp_path / "mdstats-mace-train"
    _write_real_p5_process_wrapper(wrapper, events)
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    evaluator = fixture.PostSelectionHarness()
    _patch_bounded_training_resources(monkeypatch)
    from mdstats.training_data.post_selection_execution import MacePostSelectionTrainer

    trainer = MacePostSelectionTrainer(
        wrapper_path=wrapper,
        poll_interval_seconds=0.05,
        visible_progress_interval_seconds=0.05,
        terminate_grace_seconds=0.2,
    )
    try:
        contexts = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=trainer,
            inference_evaluator=evaluator.evaluate,
            admit=True,
        )
        context = replace(
            contexts[0],
            method_policies=replace(contexts[0].method_policies, device="cuda:0"),
        )
        _plan, acceptance = runtime.execute_post_selection_cross_validation(context)
        assert acceptance.accepted
    finally:
        store.close()

    started = sorted(events.glob("started-*.json"))
    completed = sorted(events.glob("completed-*.json"))
    assert len(started) == 2
    assert len(completed) == 2
    assert all(
        json.loads(path.read_text(encoding="utf-8"))["kind"] == "completed"
        for path in completed
    )


@pytest.mark.slow
def test_real_p5_process_failure_stops_admission_and_reaps_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real child failure cancels its active sibling before queued work launches."""

    config, _workspace = fixture.build_selected_campaign(
        tmp_path / "campaign",
        config_text=_real_p5_execution_config(seeds="[11, 12]"),
    )
    events = tmp_path / "events"
    wrapper = tmp_path / "mdstats-mace-train"
    claim = tmp_path / "failure-claim"
    _write_real_p5_process_wrapper(
        wrapper,
        events,
        failure_claim=claim,
        pre_train_sleep=5.0,
    )
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    evaluator = fixture.PostSelectionHarness()
    _patch_bounded_training_resources(monkeypatch)
    from mdstats.training_data.post_selection_execution import (
        MacePostSelectionTrainer,
        PostSelectionExecutionError,
    )

    trainer = MacePostSelectionTrainer(
        wrapper_path=wrapper,
        poll_interval_seconds=0.05,
        visible_progress_interval_seconds=0.05,
        terminate_grace_seconds=0.2,
    )
    try:
        contexts = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=trainer,
            inference_evaluator=evaluator.evaluate,
            admit=True,
        )
        context = replace(
            contexts[0],
            method_policies=replace(contexts[0].method_policies, device="cuda:0"),
        )
        with pytest.raises(PostSelectionExecutionError, match=r"exit 37"):
            runtime.execute_post_selection_cross_validation(context)
    finally:
        store.close()

    started = sorted(events.glob("started-*.json"))
    cancelled = sorted(events.glob("cancelled-*.json"))
    completed = sorted(events.glob("completed-*.json"))
    # Four exact CV slots were queued. Only the first two may have crossed the
    # real trainer boundary before the first active process failed.
    assert len(started) == 2
    assert cancelled
    assert not completed
    post_selection_root = Path(paths.state_db).parent / "post-selection"
    assert not list(post_selection_root.rglob(runtime.FOLD_ACCEPTANCE_FILENAME))
    assert not list(post_selection_root.rglob(runtime.RUN_EVIDENCE_FILENAME))


@pytest.mark.slow
def test_real_p5_train2_persists_live_mace_architecture_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real P5 child model and durable TRAIN2 companion share one descriptor."""

    config, _workspace = fixture.build_selected_campaign(
        tmp_path / "campaign",
        config_text=_real_p5_execution_config(),
    )
    events = tmp_path / "events"
    wrapper = tmp_path / "mdstats-mace-train"
    _write_real_p5_process_wrapper(wrapper, events, real_mace_model=True)
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    evaluator = fixture.PostSelectionHarness()
    _patch_bounded_training_resources(monkeypatch)
    import torch

    from mdstats.training_data.model_features import (
        build_mace_model_from_configuration,
        mace_model_execution_architecture_digest,
    )
    from mdstats.training_data.post_selection_execution import MacePostSelectionTrainer
    from mdstats.training_data.train2_runtime import load_train2_runtime_summary

    trainer = MacePostSelectionTrainer(
        wrapper_path=wrapper,
        poll_interval_seconds=0.05,
        visible_progress_interval_seconds=0.05,
        terminate_grace_seconds=0.2,
    )
    try:
        contexts = runtime.build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=trainer,
            inference_evaluator=evaluator.evaluate,
            admit=True,
        )
        context = replace(
            contexts[0],
            method_policies=replace(contexts[0].method_policies, device="cuda:0"),
        )
        _plan, acceptance = runtime.execute_post_selection_cross_validation(context)
        assert acceptance.accepted
    finally:
        store.close()

    completed = sorted(events.glob("completed-*.json"))
    assert len(completed) == 2
    for event_path in completed:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        checkpoint_directory = Path(event["checkpoints"])
        summary = load_train2_runtime_summary(checkpoint_directory)
        assert summary.model_architecture_digest
        companion = torch.load(
            checkpoint_directory / "train2_runtime.pt",
            map_location="cpu",
            weights_only=False,
        )
        assert companion["model_architecture_digest"] == summary.model_architecture_digest
        materialization_directory = checkpoint_directory.parent / "materialization"
        payload = json.loads(
            (materialization_directory / "post_selection_mace_config.yaml").read_text(
                encoding="utf-8"
            )
        )
        model = build_mace_model_from_configuration(payload)
        assert (
            mace_model_execution_architecture_digest(model)
            == summary.model_architecture_digest
        )


def _pre_fix_foundation_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    pauser_factory: Callable[[], Any] = downstream._PauseAfterFullHorizon,
    request_index: int = 0,
):
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
    pauser = pauser_factory()
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
    request = pauser.requests[request_index]
    return config, Path(request.checkpoint_directory).parent, request.run_plan.run_identity


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
def test_pre_fix_different_persisted_architecture_is_recomputed_for_one_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authenticated stale run is replaced without touching its sibling."""

    class _CompleteFirstThenPauseFullSecond:
        """Leave one completed sibling and one authenticated stale candidate."""

        def __init__(self) -> None:
            self.requests: list[object] = []

        def __call__(self, request):
            self.requests.append(request)
            if len(self.requests) == 1:
                return fixture.train_like_mace(request)
            return fixture.train_like_mace(
                request,
                stop_after_epoch=request.plan.execution_epoch_limit - 1,
                fail_after_persist=True,
            )

    config, run_root, old_run_identity = _pre_fix_foundation_workspace(
        tmp_path,
        monkeypatch,
        pauser_factory=_CompleteFirstThenPauseFullSecond,
        request_index=1,
    )
    sibling_roots = [
        item
        for item in run_root.parent.iterdir()
        if item.is_dir() and not item.name.startswith(".") and item != run_root
    ]
    assert len(sibling_roots) == 1
    sibling_root = sibling_roots[0]
    materialization = run_root / "materialization"
    config_before = materialization.joinpath(
        "post_selection_mace_config.yaml"
    ).read_bytes()
    _set_persisted_architecture(run_root, "f" * 64)
    checkpoint_before = downstream._file_tree_bytes(run_root / "checkpoints")

    # The first sibling was trained by the bounded fixture, whose toy model
    # deliberately has no architecture descriptor. Give that already
    # authenticated sibling the current descriptor so this test isolates the
    # stale-architecture replacement branch below.
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
        current_config = json.loads(
            materialization.joinpath("post_selection_mace_config.yaml").read_text(
                encoding="utf-8"
            )
        )
        current_config["compute_avg_num_neighbors"] = False
        current_architecture, _realization = (
            runtime._post_selection_current_training_architecture(
                context,
                current_config=current_config,
            )
        )
    finally:
        store.close()
    _set_persisted_architecture(sibling_root, current_architecture)
    sibling_before = {
        "materialization": downstream._file_tree_bytes(
            sibling_root / "materialization"
        ),
        "checkpoints": downstream._file_tree_bytes(sibling_root / "checkpoints"),
    }

    resumed = fixture.PostSelectionHarness()
    assert fixture.run_cross_validate(config, resumed) == 0
    assert [request.run_plan.run_identity for request in resumed.requests] == [
        old_run_identity
    ]
    assert resumed.requests[0].start_epoch == 0
    assert materialization.joinpath("post_selection_mace_config.yaml").read_bytes() != (
        config_before
    )
    current_config = json.loads(
        materialization.joinpath("post_selection_mace_config.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert current_config["compute_avg_num_neighbors"] is False
    assert "model_architecture_digest" not in json.loads(
        (run_root / "checkpoints" / "train2_runtime.json").read_text(
            encoding="utf-8"
        )
    )
    assert downstream._file_tree_bytes(run_root / "checkpoints") != checkpoint_before
    assert {
        "materialization": downstream._file_tree_bytes(
            sibling_root / "materialization"
        ),
        "checkpoints": downstream._file_tree_bytes(sibling_root / "checkpoints"),
    } == sibling_before
