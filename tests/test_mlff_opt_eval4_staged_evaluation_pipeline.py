from __future__ import annotations

from dataclasses import replace
import hashlib
import threading
import time
from pathlib import Path
from types import SimpleNamespace

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


def test_staged_eval_has_one_outer_owner_and_binds_joint_model_job_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    lock = threading.Lock()
    active = 0
    peak = 0
    observed_jobs: list[int] = []

    class Prepared:
        def __init__(self):
            self.execution_plan = mdstats.InferenceExecutionPlan(
                batch_policy="auto", selected_batch_size=8,
                maximum_batch_size=32,
            )

    def infer(prepared):
        nonlocal active, peak
        observed_jobs.append(prepared.execution_plan.selected_concurrent_model_jobs)
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return True

    tasks = tuple(
        campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=str(index),
            label=f"eval-{index}",
            start_detail="joint",
            prepare=Prepared,
            requires_inference=lambda prepared: True,
            infer=infer,
            finalize=lambda prepared, result: result,
            done_detail=lambda result, wall: "done",
        )
        for index in range(2)
    )
    cfg = _pipeline_cfg()
    cfg["execution"]["parallel_evaluation_jobs"] = 2

    results = campaign_cli._run_staged_evaluation_tasks(
        tasks, cfg=cfg, phase="evaluation", device="cpu", progress=_Progress()
    )

    assert results == {"0": True, "1": True}
    assert peak == 1
    assert observed_jobs == [2, 2]


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


def test_dynamics_reduction_overlaps_next_single_slot_simulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"].update({
        "parallel_dynamics_jobs": 1,
        "maximum_parallel_dynamics_jobs": 1,
        "parallel_dynamics_prepare_jobs": 1,
        "parallel_dynamics_finalize_jobs": 1,
        "dynamics_pipeline_buffer_jobs": 2,
        "dynamics_estimated_ram_mib_per_job": 1.0,
        "parallel_dynamics_stabilization_seconds": 0.0,
        "parallel_dynamics_cpu_stabilization_seconds": 0.0,
        "parallel_dynamics_stability_samples": 2,
        "parallel_dynamics_monitor_interval_seconds": 0.005,
    })
    lock = threading.Lock()
    spans: dict[str, list[float]] = {}
    active_simulations = 0
    peak_simulations = 0

    def mark(name: str, delay: float, *, simulation: bool = False) -> str:
        nonlocal active_simulations, peak_simulations
        with lock:
            spans[name] = [time.monotonic(), 0.0]
            if simulation:
                active_simulations += 1
                peak_simulations = max(peak_simulations, active_simulations)
        time.sleep(delay)
        with lock:
            spans[name][1] = time.monotonic()
            if simulation:
                active_simulations -= 1
        return name

    def task(index: int) -> campaign_cli._StagedEvaluationTask:
        return campaign_cli._StagedEvaluationTask(
            display_index=index + 1, key=f"case-{index}", label=f"case-{index}",
            start_detail="DYN pipeline test", prepare=lambda: True,
            requires_inference=lambda prepared: True,
            infer=lambda prepared: mark(f"simulate{index}", 0.08, simulation=True),
            finalize=lambda prepared, result: mark(f"reduce{index}", 0.12),
            done_detail=lambda result, wall: result,
        )

    result = campaign_cli._run_staged_evaluation_tasks(
        [task(0), task(1)], cfg=cfg, phase="dynamics", device="cpu", progress=_Progress()
    )
    assert set(result) == {"case-0", "case-1"}
    assert peak_simulations == 1
    assert spans["simulate1"][0] < spans["reduce0"][1]
    assert spans["simulate1"][1] > spans["reduce0"][0]


def test_dynamics_authenticated_receipt_path_bypasses_simulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"].update({
        "parallel_dynamics_jobs": 1,
        "maximum_parallel_dynamics_jobs": 1,
        "parallel_dynamics_prepare_jobs": 1,
        "parallel_dynamics_finalize_jobs": 1,
        "parallel_dynamics_stabilization_seconds": 0.0,
        "parallel_dynamics_cpu_stabilization_seconds": 0.0,
    })
    simulated = []
    receipt_metric = object()
    task = campaign_cli._StagedEvaluationTask(
        display_index=1, key="accepted", label="accepted", start_detail="restart",
        prepare=lambda: receipt_metric,
        requires_inference=lambda prepared: False,
        infer=lambda prepared: simulated.append(True),
        cached_result=lambda prepared: prepared,
        finalize=lambda prepared, result: result,
        done_detail=lambda result, wall: "reused",
    )
    result = campaign_cli._run_staged_evaluation_tasks(
        [task], cfg=cfg, phase="dynamics", device="cpu", progress=_Progress()
    )
    assert result["accepted"] is receipt_metric
    assert not simulated

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


def test_dynamics_sibling_failure_cancels_active_external_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import signal
    import subprocess
    import mdstats.training_data.dyn_verify as dyn_verify
    from mdstats.training_data.inference_parallel import inference_cancellation_requested

    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    active = threading.Event()
    terminated = threading.Event()
    signals = []

    class Process:
        pid = 9876

        def wait(self, timeout=None):
            active.set()
            if terminated.is_set():
                return -signal.SIGTERM
            raise subprocess.TimeoutExpired(["fake"], timeout)

    monkeypatch.setattr(dyn_verify.subprocess, "Popen", lambda *args, **kwargs: Process())

    def killpg(pid, sig):
        signals.append((pid, sig))
        terminated.set()

    monkeypatch.setattr(dyn_verify.os, "killpg", killpg)

    def external(_prepared):
        return dyn_verify._run_file_backed_process(
            ("fake",),
            cwd=tmp_path,
            environment={},
            stdout_path=tmp_path / "external.stdout.log",
            stderr_path=tmp_path / "external.stderr.log",
            timeout_seconds=10.0,
            cancellation_requested=inference_cancellation_requested,
        )

    def fail_sibling(_prepared):
        assert active.wait(timeout=2.0)
        raise RuntimeError("sibling failed")

    tasks = (
        campaign_cli._StagedEvaluationTask(
            display_index=1, key="external", label="external", start_detail="external",
            prepare=lambda: True, requires_inference=lambda prepared: True,
            infer=external, finalize=lambda prepared, result: result,
            done_detail=lambda result, wall: "done",
        ),
        campaign_cli._StagedEvaluationTask(
            display_index=2, key="failure", label="failure", start_detail="failure",
            prepare=lambda: True, requires_inference=lambda prepared: True,
            infer=fail_sibling, finalize=lambda prepared, result: result,
            done_detail=lambda result, wall: "done",
        ),
    )
    cfg = {
        "performance": {"cpu_fraction": 0.90, "ram_fraction": 0.80},
        "execution": {
            "parallel_dynamics_jobs": 2,
            "maximum_parallel_dynamics_jobs": 2,
            "parallel_dynamics_prepare_jobs": 2,
            "parallel_dynamics_finalize_jobs": 1,
            "dynamics_pipeline_buffer_jobs": 2,
            "dynamics_estimated_ram_mib_per_job": 1.0,
            "parallel_dynamics_cpu_stabilization_seconds": 0.0,
            "parallel_dynamics_stability_samples": 2,
            "parallel_dynamics_monitor_interval_seconds": 0.01,
        },
    }

    with pytest.raises(campaign_cli.CampaignCliError, match="sibling failed"):
        campaign_cli._run_staged_evaluation_tasks(
            tasks, cfg=cfg, phase="dynamics", device="cpu", progress=_Progress()
        )
    assert signals == [(9876, signal.SIGTERM)]


def test_dynamics_keyboard_interrupt_cancels_active_external_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import signal
    import subprocess
    import mdstats.training_data.dyn_verify as dyn_verify
    from mdstats.training_data.inference_parallel import inference_cancellation_requested

    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    active = threading.Event()
    terminated = threading.Event()
    signals = []

    class Process:
        pid = 9877

        def wait(self, timeout=None):
            active.set()
            if terminated.is_set():
                return -signal.SIGTERM
            raise subprocess.TimeoutExpired(["fake"], timeout)

    monkeypatch.setattr(dyn_verify.subprocess, "Popen", lambda *args, **kwargs: Process())

    def killpg(pid, sig):
        signals.append((pid, sig))
        terminated.set()

    monkeypatch.setattr(dyn_verify.os, "killpg", killpg)
    real_wait = campaign_cli._core.wait
    def interrupt_wait(futures, **kwargs):
        if active.wait(timeout=0.05):
            raise KeyboardInterrupt
        return real_wait(futures, **kwargs)

    monkeypatch.setattr(campaign_cli._core, "wait", interrupt_wait)
    task = campaign_cli._StagedEvaluationTask(
        display_index=1, key="interrupt", label="interrupt", start_detail="interrupt",
        prepare=lambda: True, requires_inference=lambda prepared: True,
        infer=lambda prepared: dyn_verify._run_file_backed_process(
            ("fake",), cwd=tmp_path, environment={},
            stdout_path=tmp_path / "interrupt.stdout.log",
            stderr_path=tmp_path / "interrupt.stderr.log", timeout_seconds=10.0,
            cancellation_requested=inference_cancellation_requested,
        ),
        finalize=lambda prepared, result: result,
        done_detail=lambda result, wall: "done",
    )
    cfg = _pipeline_cfg()
    cfg["execution"]["parallel_dynamics_jobs"] = 1
    cfg["execution"]["maximum_parallel_dynamics_jobs"] = 1
    cfg["execution"]["dynamics_estimated_ram_mib_per_job"] = 1.0

    with pytest.raises(KeyboardInterrupt):
        campaign_cli._run_staged_evaluation_tasks(
            [task], cfg=cfg, phase="dynamics", device="cpu", progress=_Progress()
        )
    assert signals == [(9877, signal.SIGTERM)]


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


def test_target_only_evaluation_authorization_is_independent_of_target_override(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run = mdstats.TrainingCampaignRunPlan(
        run_id="opt-eval4-target-size-run",
        data8_bundle_digest=_h("data8-target-size"),
        mace_job_artifact_digest=_h("job-target-size"),
        job_id="job-target-size",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("family-target-size"),
        protocol_variant_digest=_h("variant-target-size"),
        protocol_digest=_h("protocol-target-size"),
        checkpoint_metric_policy_digest=_h("metric-policy-target-size"),
        target_monitor_artifact_digest=artifact.content_digest,
        replay_monitor_artifact_digest=_h("training-replay-target-size"),
        relative_output_directory="run-target-size",
    )
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        size_bytes=candidate.stat().st_size,
    )
    prepared = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=mdstats.CheckpointEvaluationPolicy(condition_keys=()),
        allow_target_only_evaluation=True,
    )
    assert prepared.target_only_evaluation_authorized
    assert prepared.replay_monitor_artifact is None
    assert prepared.baseline_model_path is None

    with pytest.raises(
        mdstats.TrainingDataInputError,
        match="Target-only evaluation cannot also carry replay monitor inputs",
    ):
        mdstats.prepare_mace_checkpoint_evaluation(
            run,
            checkpoint,
            candidate_model_path=candidate,
            calculator_model_path=candidate,
            target_monitor_path=target,
            target_monitor_artifact=artifact,
            policy=mdstats.CheckpointEvaluationPolicy(condition_keys=()),
            replay_monitor_path=target,
            allow_target_only_evaluation=True,
        )


def test_target_only_evaluation_does_not_authorize_target_monitor_override(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_checkpoint(artifact, candidate)
    run = replace(
        run, target_monitor_artifact_digest=_h("different-target-monitor")
    )
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        size_bytes=candidate.stat().st_size,
    )
    with pytest.raises(
        mdstats.TrainingDataInputError,
        match="Target monitor artifact lineage does not match campaign run",
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


def test_target_size_eval2_full_checkpoint_authorizes_frozen_target_only_monitor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target-size.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run = mdstats.TrainingCampaignRunPlan(
        run_id="target-size-eval2-run",
        data8_bundle_digest=_h("target-size-data8"),
        mace_job_artifact_digest=_h("target-size-job"),
        job_id="target-size-job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("target-size-family"),
        protocol_variant_digest=_h("target-size-variant"),
        protocol_digest=_h("target-size-protocol"),
        checkpoint_metric_policy_digest=_h("target-size-metric-policy"),
        target_monitor_artifact_digest=artifact.content_digest,
        replay_monitor_artifact_digest=_h("target-size-training-replay"),
        relative_output_directory="target-size-run",
    )
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        size_bytes=candidate.stat().st_size,
    )
    role = mdstats.Eval2TargetRole(
        label_domain_id="label-domain-target-size",
        role_kind="size_development_complement",
        target_data_role_freeze_digest=_h("target-size-role-freeze"),
        target_size_study_digest=_h("target-size-study"),
        evaluation_frame_uids=artifact.frame_uids,
        correlation_block_ids=(_h("target-size-block"),),
        excluded_training_frame_uids=(_h("target-size-training-frame"),),
    )
    point = mdstats.Eval2TrajectoryPoint(
        epoch=0,
        checkpoint_sha256=checkpoint.sha256,
        lightweight_target_score_ev_per_angstrom=0.01,
        normalized_schedule_progress=0.1,
        instantaneous_learning_rate=1.0e-3,
        phase="adaptation",
        runtime_summary_digest=_h("target-size-runtime"),
        stable_candidate_identity="target-size-epoch-1",
    )
    job = SimpleNamespace(
        relative_directory="job",
        config_relative_path="job/config.yaml",
        protocol=SimpleNamespace(
            checkpoint_admissibility_policy=mdstats.CheckpointAdmissibilityPolicy()
        ),
    )
    execution = SimpleNamespace(checkpoint_catalog=SimpleNamespace())
    bundle = SimpleNamespace(
        replay_plan=SimpleNamespace(
            monitor_artifact=SimpleNamespace(
                content_digest=run.replay_monitor_artifact_digest
            )
        )
    )

    class Store:
        def __init__(self):
            self.records = {}

        def get_record_optional(self, key, _record_type):
            return self.records.get(key)

        def delete_record(self, key):
            self.records.pop(key, None)

        def put_record(self, key, value):
            self.records[key] = value

    store = Store()
    paths = SimpleNamespace(internal=tmp_path / "internal", runs=tmp_path / "runs")
    campaign_core = campaign_cli._core
    monkeypatch.setattr(
        campaign_core,
        "_eval2_evaluation_policy",
        lambda *_args, **_kwargs: mdstats.CheckpointEvaluationPolicy(condition_keys=()),
    )
    monkeypatch.setattr(
        campaign_core,
        "_evaluation_inference_execution_plan",
        lambda *_args, **_kwargs: mdstats.InferenceExecutionPlan(
            batch_policy="fixed", selected_batch_size=1, maximum_batch_size=1
        ),
    )
    monkeypatch.setattr(
        campaign_core,
        "_checkpoint_source_for_evaluation",
        lambda *_args, **_kwargs: (candidate, None),
    )
    monkeypatch.setattr(
        mdstats, "materialize_mace_checkpoint_model", lambda *_args, **_kwargs: candidate
    )
    observed = {}

    def infer(prepared, *, calculator_model_path=None, **_kwargs):
        observed["target_only_authorized"] = prepared.target_only_evaluation_authorized
        observed["target_monitor_override"] = (
            prepared.target_monitor_artifact.content_digest
            != prepared.run_plan.target_monitor_artifact_digest
        )
        return mdstats.CheckpointEvaluationPredictionBundle(
            target_candidate_predictions=(
                AtomicModelPrediction(
                    energy_ev=-1.9,
                    forces_ev_per_angstrom=np.full((2, 3), 0.01),
                    stress_ev_per_angstrom3=np.zeros((3, 3)),
                ),
            ),
            target_candidate_artifact=None,
            target_foundation_predictions=None,
            target_foundation_artifact=None,
            replay_candidate_predictions=None,
            replay_candidate_artifact=None,
            replay_foundation_predictions=None,
            replay_foundation_artifact=None,
        )

    monkeypatch.setattr(mdstats, "run_prepared_mace_checkpoint_inference", infer)
    result = campaign_core._eval2_full_checkpoint(
        cfg={},
        paths=paths,
        store=store,
        run=run,
        job=job,
        bundle=bundle,
        root=tmp_path,
        execution=execution,
        checkpoint=checkpoint,
        point=point,
        target_role=role,
        target_artifact=artifact,
        target_path=target,
        true_replay_resolution=None,
        baseline_model=None,
        model_dtype="float32",
        local_wrappers={"mdstats-mace-train": tmp_path / "unused-wrapper"},
        shortlist_reasons=("target_size_v5_epoch_1_exact_endpoint",),
        full_evaluation_rank=1,
        include_replay=False,
    )
    assert observed == {
        "target_only_authorized": True,
        "target_monitor_override": False,
    }
    assert result.target_metrics.configuration_count == 1
    assert result.replay_candidate_force_rmse_ev_per_angstrom is None
    eval_key = (
        f"eval2_evaluation:target-only:{run.run_id}:"
        f"{role.content_digest}:{checkpoint.sha256}"
    )
    evaluation = store.records[eval_key]
    assert evaluation.replay_monitor_artifact_digest is None
    assert evaluation.replay_configuration_count == 0
    assert evaluation.replay_baseline_model_path is None
    assert (
        "evaluation_scope:authorized_target_only"
        in evaluation.metric_record.evaluation_notes
    )


def test_eval2_target_only_scope_is_not_a_generic_replay_bypass(tmp_path: Path) -> None:
    job = SimpleNamespace(
        protocol=SimpleNamespace(
            checkpoint_admissibility_policy=mdstats.CheckpointAdmissibilityPolicy()
        )
    )
    with pytest.raises(
        campaign_cli._core.CampaignCliError,
        match="reserved for the TARGET-SIZE-V5 development-complement role",
    ):
        campaign_cli._core._eval2_full_checkpoint(
            cfg={},
            paths=SimpleNamespace(),
            store=SimpleNamespace(),
            run=SimpleNamespace(),
            job=job,
            bundle=SimpleNamespace(),
            root=tmp_path,
            execution=SimpleNamespace(),
            checkpoint=SimpleNamespace(),
            point=SimpleNamespace(),
            target_role=SimpleNamespace(role_kind="cv_checkpoint_monitor"),
            target_artifact=SimpleNamespace(),
            target_path=tmp_path / "unused.extxyz",
            true_replay_resolution=None,
            baseline_model=None,
            model_dtype="float32",
            local_wrappers={},
            include_replay=False,
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
            return np.zeros(400 * 1024, dtype=np.uint8)

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
    # Prepared bytes plus the explicit inference-worker reservation nearly fill
    # the cap, so the producer is held until the first inference reservation is
    # released. CPU finalization may then overlap the next preparation.
    assert spans["prepare1"][0] >= spans["infer0"][1]


def test_staged_runner_fails_when_one_prepared_payload_exceeds_byte_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"]["evaluation_pipeline_buffer_mib"] = 1.5
    task = campaign_cli._StagedEvaluationTask(
        display_index=1, key="oversized", label="oversized", start_detail="bytes",
        prepare=lambda: np.zeros(2 * 1024**2, dtype=np.uint8),
        requires_inference=lambda prepared: True, infer=lambda prepared: 1,
        finalize=lambda prepared, inferred: inferred,
        done_detail=lambda result, wall: "done",
    )
    with pytest.raises(campaign_cli.CampaignCliError, match="cannot admit one required payload"):
        campaign_cli._run_staged_evaluation_tasks(
            [task], cfg=cfg, device="cpu", progress=_Progress()
        )


def test_explicit_pipeline_subbudget_cannot_exceed_global_ram_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    resources = SystemResourceSnapshot(
        cpu_threads_available=resources.cpu_threads_available,
        cpu_fraction=resources.cpu_fraction,
        cpu_threads_budget=resources.cpu_threads_budget,
        ram_available_bytes=1024**2,
        ram_fraction=0.80,
        ram_budget_bytes=1024**2,
        gpu_memory_fraction=resources.gpu_memory_fraction,
        gpu=resources.gpu,
    )
    monkeypatch.setattr(
        campaign_cli._core, "detect_system_resources", lambda **kwargs: resources
    )
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"]["evaluation_estimated_ram_mib_per_job"] = 0.25
    cfg["execution"]["evaluation_pipeline_buffer_mib"] = 2.0
    task = campaign_cli._StagedEvaluationTask(
        display_index=1,
        key="global-cap",
        label="global-cap",
        start_detail="global-cap",
        prepare=lambda: 1,
        requires_inference=lambda prepared: True,
        infer=lambda prepared: prepared,
        finalize=lambda prepared, inferred: inferred,
        done_detail=lambda result, wall: "done",
    )

    with pytest.raises(campaign_cli.CampaignCliError, match="exceeding the active global RAM budget"):
        campaign_cli._run_staged_evaluation_tasks(
            [task], cfg=cfg, device="cpu", progress=_Progress()
        )


def test_finalize_working_memory_is_reserved_before_worker_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign_cli._core, "detect_system_resources", lambda **kwargs: _resources())
    monkeypatch.setattr(campaign_cli._core, "CpuTelemetryProbe", _Probe)
    monkeypatch.setattr(campaign_cli._core, "query_gpu_telemetry", lambda device: None)
    cfg = _pipeline_cfg()
    cfg["execution"]["evaluation_pipeline_buffer_mib"] = 1.5
    cfg["execution"]["evaluation_finalize_working_memory_mib"] = 1.0
    spans: dict[str, list[float]] = {}
    lock = threading.Lock()

    def record(name: str, delay: float):
        with lock:
            spans[name] = [time.monotonic(), 0.0]
        time.sleep(delay)
        with lock:
            spans[name][1] = time.monotonic()

    def task(index: int):
        def prepare():
            record(f"prepare{index}", 0.01)
            return np.zeros(400 * 1024, dtype=np.uint8)

        def infer(prepared):
            record(f"infer{index}", 0.01)
            return index

        def finalize(prepared, inferred):
            record(f"finalize{index}", 0.05)
            return inferred

        return campaign_cli._StagedEvaluationTask(
            display_index=index + 1,
            key=f"finalize-reservation-{index}",
            label=f"finalize-reservation-{index}",
            start_detail="finalize-reservation",
            prepare=prepare,
            requires_inference=lambda prepared: True,
            infer=infer,
            finalize=finalize,
            done_detail=lambda result, wall: "done",
        )

    result = campaign_cli._run_staged_evaluation_tasks(
        [task(0), task(1)], cfg=cfg, device="cpu", progress=_Progress()
    )
    assert result == {
        "finalize-reservation-0": 0,
        "finalize-reservation-1": 1,
    }
    assert spans["prepare1"][0] >= spans["finalize0"][1]


def test_ase_atoms_retained_bytes_include_array_storage() -> None:
    from ase import Atoms

    atoms = Atoms("H100", positions=np.zeros((100, 3)))
    atoms.arrays["large"] = np.zeros((100, 64), dtype=np.float64)
    retained = campaign_cli._core._evaluation_payload_bytes(atoms)
    assert retained >= atoms.arrays["large"].nbytes + atoms.positions.nbytes
    assert retained > atoms.__sizeof__()
