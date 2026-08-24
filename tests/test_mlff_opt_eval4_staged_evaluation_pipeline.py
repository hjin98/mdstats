from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_cli, campaign_execution
from mdstats.training_data.inference_parallel import CpuTelemetrySample
from mdstats.training_data.model_features import AtomicModelPrediction, MaceCalculatorProvider
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _frame() -> Atoms:
    atoms = Atoms(
        numbers=[3, 8],
        positions=[[0.0, 0.0, 0.0], [1.8, 0.0, 0.0]],
        cell=np.eye(3) * 6.0,
        pbc=True,
    )
    atoms.info["REF_energy"] = -2.0
    atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=float)
    atoms.info["REF_stress"] = np.zeros(6)
    return atoms


def _target_artifact(path: Path) -> mdstats.MaceExtxyzArtifact:
    return mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        configuration_count=1,
        frame_uids=(_h("opt-eval4-frame"),),
        atomic_numbers=(3, 8),
        policy_digest=_h("target-policy"),
        sidecar_relative_path="target.manifest.json",
        sidecar_sha256=_h("target-sidecar-file"),
        sidecar_digest=_h("target-sidecar-record"),
    )


def _run_checkpoint(artifact: mdstats.MaceExtxyzArtifact, candidate: Path):
    run = mdstats.TrainingCampaignRunPlan(
        run_id="opt-eval4-run",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=_h("job"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=_h("metric-policy"),
        target_monitor_artifact_digest=artifact.content_digest,
        replay_monitor_artifact_digest=None,
        relative_output_directory="run",
    )
    sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=sha,
        size_bytes=candidate.stat().st_size,
    )
    return run, checkpoint


class _Provider:
    def set_head(self, head):
        self.head = head


def test_staged_scientific_api_cache_only_restart_needs_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_checkpoint(artifact, candidate)
    cache = tmp_path / "predictions"
    policy = mdstats.CheckpointEvaluationPolicy(condition_keys=())

    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: _Provider()),
    )
    calls = {"predict": 0}

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        calls["predict"] += 1
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.1,
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.05),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)

    prepared = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
    )
    assert prepared.requires_model_inference
    bundle = mdstats.run_prepared_mace_checkpoint_inference(
        prepared, calculator_model_path=candidate
    )
    first = mdstats.finalize_prepared_mace_checkpoint_evaluation(prepared, bundle)
    assert calls["predict"] == 1
    assert "evaluation_pipeline:prepared-inference-finalize-v1" in first.metric_record.evaluation_notes

    candidate.unlink()
    prepared_cached = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
    )
    assert not prepared_cached.requires_model_inference
    cached_bundle = mdstats.run_prepared_mace_checkpoint_inference(prepared_cached)
    second = mdstats.finalize_prepared_mace_checkpoint_evaluation(
        prepared_cached, cached_bundle
    )
    assert calls["predict"] == 1
    assert second.metric_record.force_component_rmse_ev_per_angstrom == pytest.approx(
        first.metric_record.force_component_rmse_ev_per_angstrom
    )


def _resources() -> SystemResourceSnapshot:
    gib = 1024**3
    return SystemResourceSnapshot(
        cpu_threads_available=8,
        cpu_fraction=0.90,
        cpu_threads_budget=7,
        ram_available_bytes=48 * gib,
        ram_fraction=0.80,
        ram_budget_bytes=int(48 * gib * 0.80),
        gpu_memory_fraction=0.90,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "test"),
    )


class _Probe:
    def __init__(self, **kwargs):
        pass

    def sample(self, **kwargs):
        return CpuTelemetrySample(time.monotonic(), 0.0)

    def reset(self):
        pass


class _Progress:
    def item_start(self, *args, **kwargs):
        pass

    def item_done(self, *args, **kwargs):
        pass


def _pipeline_cfg() -> dict:
    return {
        "performance": {"cpu_fraction": 0.90, "ram_fraction": 0.80},
        "execution": {
            "parallel_evaluation_jobs": 1,
            "parallel_evaluation_prepare_jobs": 1,
            "parallel_evaluation_finalize_jobs": 1,
            "evaluation_pipeline_buffer_jobs": 2,
            "evaluation_estimated_ram_mib_per_job": 1.0,
            "parallel_evaluation_stabilization_seconds": 0.0,
            "parallel_evaluation_cpu_stabilization_seconds": 0.0,
            "parallel_evaluation_stability_samples": 2,
            "parallel_evaluation_monitor_interval_seconds": 0.005,
        },
    }


def test_staged_runner_overlaps_prepare_and_finalize_with_single_inference_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)

    lock = threading.Lock()
    spans: dict[str, list[float]] = {}
    callback_threads: list[int] = []
    caller_thread = threading.get_ident()

    def span(name: str, delay: float):
        with lock:
            spans[name] = [time.monotonic(), 0.0]
        time.sleep(delay)
        with lock:
            spans[name][1] = time.monotonic()

    def make_task(index: int) -> campaign_cli._StagedEvaluationTask:
        def prepare():
            span(f"prepare{index}", 0.08)
            return index

        def infer(prepared):
            span(f"infer{index}", 0.18)
            return prepared

        def finalize(prepared, inferred):
            span(f"finalize{index}", 0.10)
            return inferred

        return campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=f"task-{index}",
            label=f"task-{index}",
            start_detail="pipeline-test",
            prepare=prepare,
            requires_inference=lambda prepared: True,
            infer=infer,
            finalize=finalize,
            done_detail=lambda result, wall: str(result),
            on_success=lambda result: callback_threads.append(threading.get_ident()),
        )

    results = campaign_cli._run_staged_evaluation_tasks(
        [make_task(0), make_task(1)],
        cfg=_pipeline_cfg(),
        device="cpu",
        progress=_Progress(),
    )
    assert results == {"task-0": 0, "task-1": 1}
    # With one inference slot, the second CPU prepare is launched as soon as the
    # first prepared item enters inference and therefore overlaps infer0.
    assert spans["prepare1"][0] < spans["infer0"][1]
    assert spans["prepare1"][1] > spans["infer0"][0]
    # CPU finalization of task0 overlaps the admitted inference of task1.
    assert spans["finalize0"][0] < spans["infer1"][1]
    assert spans["finalize0"][1] > spans["infer1"][0]
    assert callback_threads and set(callback_threads) == {caller_thread}


def test_cache_only_staged_task_bypasses_inference_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    execution_threads: list[str] = []

    task = campaign_cli._StagedEvaluationTask(
        display_index=1,
        key="cached",
        label="cached",
        start_detail="cached",
        prepare=lambda: "prepared",
        requires_inference=lambda prepared: False,
        infer=lambda prepared: execution_threads.append(threading.current_thread().name) or "predictions",
        finalize=lambda prepared, predictions: (prepared, predictions),
        done_detail=lambda result, wall: "done",
    )
    result = campaign_cli._run_staged_evaluation_tasks(
        [task], cfg=_pipeline_cfg(), device="cpu", progress=_Progress()
    )
    assert result["cached"] == ("prepared", "predictions")
    assert execution_threads
    assert all(name.startswith("mdstats-eval-finalize") for name in execution_threads)

@pytest.mark.parametrize(
    "key",
    ["parallel_evaluation_prepare_jobs", "parallel_evaluation_finalize_jobs"],
)
def test_staged_runner_rejects_negative_cpu_stage_worker_counts(
    key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"][key] = -1
    task = campaign_cli._StagedEvaluationTask(
        display_index=1,
        key="bad-config",
        label="bad-config",
        start_detail="bad-config",
        prepare=lambda: "prepared",
        requires_inference=lambda prepared: False,
        infer=lambda prepared: "predictions",
        finalize=lambda prepared, predictions: "done",
        done_detail=lambda result, wall: "done",
    )
    with pytest.raises(campaign_cli.CampaignCliError, match="zero \\(auto\\) or positive"):
        campaign_cli._run_staged_evaluation_tasks(
            [task], cfg=cfg, device="cpu", progress=_Progress()
        )


def test_staged_runner_stage_failure_stops_new_work_without_deadlock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"]["evaluation_pipeline_buffer_jobs"] = 1
    executed: list[str] = []

    def make_task(index: int) -> campaign_cli._StagedEvaluationTask:
        def prepare():
            executed.append(f"prepare{index}")
            if index == 0:
                raise RuntimeError("prepare exploded")
            return index

        return campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=f"failure-{index}",
            label=f"failure-{index}",
            start_detail="failure-test",
            prepare=prepare,
            requires_inference=lambda prepared: True,
            infer=lambda prepared: executed.append(f"infer{index}") or prepared,
            finalize=lambda prepared, inferred: inferred,
            done_detail=lambda result, wall: "done",
        )

    with pytest.raises(
        campaign_cli.CampaignCliError,
        match="stage=CPU preparation",
    ):
        campaign_cli._run_staged_evaluation_tasks(
            [make_task(0), make_task(1)],
            cfg=cfg,
            device="cpu",
            progress=_Progress(),
        )
    assert executed == ["prepare0"]


def test_target_only_outer_cv_authorization_omits_run_replay_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AGG1 may evaluate the sealed outer target without re-evaluating replay.

    Multi-head run plans retain training replay lineage, but conventional CV
    assigns replay authority to SELECT1.  The outer fold is target-only by
    design and therefore needs one explicit authorization to suppress the
    generic evaluator's normal replay requirement.
    """
    target = tmp_path / "outer.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")

    run = mdstats.TrainingCampaignRunPlan(
        run_id="opt-eval4-outer-run",
        data8_bundle_digest=_h("data8-outer"),
        mace_job_artifact_digest=_h("job-outer"),
        job_id="job-outer",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("family-outer"),
        protocol_variant_digest=_h("variant-outer"),
        protocol_digest=_h("protocol-outer"),
        checkpoint_metric_policy_digest=_h("metric-policy-outer"),
        target_monitor_artifact_digest=_h("inner-target-monitor"),
        replay_monitor_artifact_digest=_h("training-replay-lineage"),
        relative_output_directory="run-outer",
    )
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        size_bytes=candidate.stat().st_size,
    )
    policy = mdstats.CheckpointEvaluationPolicy(condition_keys=())

    with pytest.raises(
        mdstats.TrainingDataInputError,
        match="Replay evaluation requires an evaluation monitor and foundation baseline model",
    ):
        mdstats.prepare_mace_checkpoint_evaluation(
            run,
            checkpoint,
            candidate_model_path=candidate,
            calculator_model_path=candidate,
            target_monitor_path=target,
            target_monitor_artifact=artifact,
            policy=policy,
            allow_target_monitor_override=True,
        )

    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: _Provider()),
    )

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.1,
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.05),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)
    prepared = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        allow_target_monitor_override=True,
        allow_target_only_evaluation=True,
    )
    assert prepared.replay_monitor_artifact is None
    assert prepared.target_only_evaluation_authorized
    bundle = mdstats.run_prepared_mace_checkpoint_inference(
        prepared, calculator_model_path=candidate
    )
    record = mdstats.finalize_prepared_mace_checkpoint_evaluation(prepared, bundle)
    assert record.replay_monitor_artifact_digest is None
    assert record.replay_configuration_count == 0
    assert "evaluation_scope:authorized_target_only" in record.metric_record.evaluation_notes


def test_target_only_evaluation_requires_explicit_target_override(tmp_path: Path) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_checkpoint(artifact, candidate)
    with pytest.raises(
        mdstats.TrainingDataInputError,
        match="reserved for an explicit target-monitor override",
    ):
        mdstats.prepare_mace_checkpoint_evaluation(
            run,
            checkpoint,
            candidate_model_path=candidate,
            calculator_model_path=candidate,
            target_monitor_path=target,
            target_monitor_artifact=artifact,
            policy=mdstats.CheckpointEvaluationPolicy(condition_keys=()),
            allow_target_only_evaluation=True,
        )


def test_staged_runner_one_thread_budget_serializes_all_cpu_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gib = 1024**3
    one_thread = SystemResourceSnapshot(
        cpu_threads_available=2,
        cpu_fraction=0.50,
        cpu_threads_budget=1,
        ram_available_bytes=8 * gib,
        ram_fraction=0.80,
        ram_budget_bytes=int(8 * gib * 0.80),
        gpu_memory_fraction=0.90,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "test"),
    )
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: one_thread)
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)

    lock = threading.Lock()
    active = 0
    peak = 0

    def stage(value):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.01)
        with lock:
            active -= 1
        return value

    tasks = [
        campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=f"one-{index}",
            label=f"one-{index}",
            start_detail="one-thread",
            prepare=lambda index=index: stage(index),
            requires_inference=lambda prepared: True,
            infer=lambda prepared: stage(prepared),
            finalize=lambda prepared, inferred: stage(inferred),
            done_detail=lambda result, wall: "done",
        )
        for index in range(2)
    ]
    result = campaign_cli._run_staged_evaluation_tasks(
        tasks, cfg=_pipeline_cfg(), device="cpu", progress=_Progress()
    )
    assert result == {"one-0": 0, "one-1": 1}
    assert peak == 1


def test_staged_runner_applies_byte_budget_to_all_retained_stage_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"]["evaluation_pipeline_buffer_mib"] = 1.5

    spans: dict[str, list[float]] = {}
    lock = threading.Lock()

    def record(name: str, delay: float) -> None:
        with lock:
            spans[name] = [time.monotonic(), 0.0]
        time.sleep(delay)
        with lock:
            spans[name][1] = time.monotonic()

    def make_task(index: int) -> campaign_cli._StagedEvaluationTask:
        def prepare():
            record(f"prepare{index}", 0.02)
            return np.zeros(2 * 1024**2, dtype=np.uint8)

        def infer(prepared):
            record(f"infer{index}", 0.06)
            return index

        def finalize(prepared, inferred):
            record(f"finalize{index}", 0.04)
            return inferred

        return campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=f"bytes-{index}",
            label=f"bytes-{index}",
            start_detail="byte-budget",
            prepare=prepare,
            requires_inference=lambda prepared: True,
            infer=infer,
            finalize=finalize,
            done_detail=lambda result, wall: "done",
        )

    result = campaign_cli._run_staged_evaluation_tasks(
        [make_task(0), make_task(1)],
        cfg=cfg,
        device="cpu",
        progress=_Progress(),
    )
    assert result == {"bytes-0": 0, "bytes-1": 1}
    # The first 2 MiB prepared payload alone exceeds the 1.5 MiB cap.  It is
    # allowed to drain (deadlock avoidance), but no second preparation may be
    # admitted while that payload is retained by inference or finalization.
    assert spans["prepare1"][0] >= spans["finalize0"][1]
