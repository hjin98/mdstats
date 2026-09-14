"""Bounded owner-level evidence for the consolidated P5 recovery workplan."""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fixture
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
        # Representative CUDA-OOM text on the child's stderr. The parent must
        # reach the same outcome without classifying it: production owns no OOM
        # stderr parser.
        print(
            'torch.OutOfMemoryError: CUDA out of memory. Tried to allocate '
            '646.00 MiB. GPU 0 has a total capacity of 24.00 GiB',
            file=sys.stderr,
            flush=True,
        )
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
    assert not evaluator.evaluations, "no EVAL2 may follow a failed TRAIN wave"
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


def test_r4_retirement_destination_collision_is_preserved(tmp_path: Path) -> None:
    """An existing scratch destination is an integrity conflict, not a target."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    checkpoint_directory = run_root / "checkpoints"
    checkpoint_directory.mkdir()
    checkpoint_marker = checkpoint_directory / "authenticated-state"
    checkpoint_marker.write_bytes(b"canonical")
    retirement = runtime._post_selection_retirement_path(run_root, "checkpoints")
    retirement.mkdir()
    retirement_marker = retirement / "unknown-state"
    retirement_marker.write_bytes(b"foreign")

    with pytest.raises(
        runtime.PostSelectionExecutionError,
        match=(
            "retirement scratch exists while its canonical namespace is still present"
        ),
    ):
        runtime._detach_post_selection_namespace(
            run_root,
            checkpoint_directory,
            canonical_name="checkpoints",
        )

    assert checkpoint_marker.read_bytes() == b"canonical"
    assert retirement_marker.read_bytes() == b"foreign"
