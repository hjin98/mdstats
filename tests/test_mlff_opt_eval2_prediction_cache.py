from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_execution
from mdstats.training_data.model_features import AtomicModelPrediction, MaceCalculatorProvider, ModelCheckpointIdentity
from mdstats.training_data.production_model_sweep import (
    AtomicModelPredictionManifest,
    _write_prediction,
)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _frame(*, energy: float = -2.0, force: float = 0.0) -> Atoms:
    atoms = Atoms(
        numbers=[3, 8],
        positions=[[0.0, 0.0, 0.0], [1.8, 0.0, 0.0]],
        cell=np.eye(3) * 6.0,
        pbc=True,
    )
    atoms.info["REF_energy"] = energy
    atoms.arrays["REF_forces"] = np.full((2, 3), force, dtype=float)
    atoms.info["REF_stress"] = np.zeros(6)
    return atoms


def _target_artifact(path: Path, frame_uid: str) -> mdstats.MaceExtxyzArtifact:
    return mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        configuration_count=1,
        frame_uids=(frame_uid,),
        atomic_numbers=(3, 8),
        policy_digest=_h("target-policy"),
        sidecar_relative_path="target.manifest.json",
        sidecar_sha256=_h("target-sidecar-file"),
        sidecar_digest=_h("target-sidecar-record"),
    )


def _run_and_checkpoint(
    target_artifact: mdstats.MaceExtxyzArtifact,
    candidate: Path,
    *,
    replay_digest: str | None = None,
):
    run = mdstats.TrainingCampaignRunPlan(
        run_id="opt-eval2-run",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=_h("job"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=(
            mdstats.TrainingMode.MULTIHEAD_REPLAY
            if replay_digest is not None
            else mdstats.TrainingMode.NAIVE_FINE_TUNING
        ),
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=_h("metric-policy"),
        target_monitor_artifact_digest=target_artifact.content_digest,
        replay_monitor_artifact_digest=replay_digest,
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


def _install_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: _Provider()),
    )


def test_metric_policy_change_reuses_predictions_after_checkpoint_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    frame_uid = _h("target-frame")
    artifact = _target_artifact(target, frame_uid)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_and_checkpoint(artifact, candidate)
    cache = tmp_path / "prediction-cache"
    _install_provider(monkeypatch)
    calls = []

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        calls.append((Path(model_path).name, head))
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.2 * len(atoms),
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.1),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    policy1 = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), combined_force_weight=1.0
    )
    first = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy1,
        prediction_cache_directory=cache,
    )
    assert len(calls) == 1
    assert first.target_candidate_prediction_digest is not None

    # The expensive checkpoint bytes can disappear after predictions are durable.
    candidate.unlink()
    policy2 = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), combined_force_weight=3.0
    )
    second = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=None,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy2,
        prediction_cache_directory=cache,
    )
    assert len(calls) == 1
    assert second.target_candidate_prediction_digest == first.target_candidate_prediction_digest
    assert second.target_candidate_metrics.force_component_rmse_ev_per_angstrom == pytest.approx(0.1)
    assert second.target_candidate_metrics.combined_loss > first.target_candidate_metrics.combined_loss
    assert mdstats.checkpoint_prediction_cache_complete(
        cache,
        checkpoint_sha256=checkpoint.sha256,
        target_geometry_identities=artifact.frame_uids,
        policy=policy2,
    )


def test_corrupt_prediction_artifact_recomputes_when_checkpoint_is_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target, _h("target-frame-corrupt"))
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_and_checkpoint(artifact, candidate)
    cache = tmp_path / "prediction-cache"
    _install_provider(monkeypatch)
    count = {"value": 0}

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        count["value"] += 1
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]),
                forces_ev_per_angstrom=np.zeros((len(atoms), 3)),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    policy = mdstats.CheckpointEvaluationPolicy(condition_keys=())
    mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
    )
    assert count["value"] == 1
    key = campaign_execution._evaluation_prediction_key(
        model_sha256=checkpoint.sha256,
        head=policy.target_head_name,
        geometry_identities=artifact.frame_uids,
        policy=policy,
    )
    from mdstats.training_data.evaluation_predictions import load_evaluation_prediction_artifact

    loaded = load_evaluation_prediction_artifact(cache, key)
    assert loaded is not None
    prediction_artifact, _ = loaded
    data_path = cache / prediction_artifact.relative_path
    data_path.write_bytes(data_path.read_bytes() + b"corrupt")
    mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
    )
    assert count["value"] == 2


def test_true_label_replay_reuses_foundation_pseudolabel_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target, _h("target-frame-replay"))
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    foundation_sha = hashlib.sha256(foundation.read_bytes()).hexdigest()
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")

    pseudo = tmp_path / "replay-pseudo.extxyz"
    pseudo_frame = _frame(energy=-1.5, force=0.25)
    write(pseudo, [pseudo_frame], format="extxyz")
    true = tmp_path / "replay-true.extxyz"
    true_frame = _frame(energy=-2.0, force=0.0)
    write(true, [true_frame], format="extxyz")
    pseudo_artifact = mdstats.inspect_replay_extxyz(
        pseudo,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation_checkpoint_digest=foundation_sha,
    )
    true_artifact = mdstats.inspect_replay_extxyz(
        true, label_mode=mdstats.ReplayLabelMode.TRUE_DFT
    )
    assert pseudo_artifact.geometry_identities == true_artifact.geometry_identities
    run, checkpoint = _run_and_checkpoint(
        artifact, candidate, replay_digest=pseudo_artifact.content_digest
    )
    _install_provider(monkeypatch)
    calls = []

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        calls.append((Path(model_path).name, head))
        if Path(model_path).resolve() == foundation.resolve():
            raise AssertionError("foundation inference should be replaced by pseudolabel reuse")
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]),
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.1),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    result = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        replay_monitor_path=true,
        replay_monitor_artifact=true_artifact,
        training_replay_monitor_artifact=pseudo_artifact,
        training_replay_monitor_path=pseudo,
        replay_baseline_model_path=foundation,
        policy=mdstats.CheckpointEvaluationPolicy(
            replay_baseline_head_name=None, condition_keys=()
        ),
        prediction_cache_directory=tmp_path / "prediction-cache",
    )
    assert len(calls) == 2  # target candidate + replay candidate only
    assert result.replay_foundation_prediction_digest is not None
    assert result.replay_foundation_metrics.force_component_rmse_ev_per_angstrom == pytest.approx(0.25)
    assert any(
        note == "replay_foundation_prediction_source:foundation_pseudolabel_replay"
        for note in result.metric_record.evaluation_notes
    )


def test_target_foundation_reuses_data6_prediction_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    frame_uid = _h("target-frame-data6")
    artifact = _target_artifact(target, frame_uid)
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    foundation_sha = hashlib.sha256(foundation.read_bytes()).hexdigest()
    run, checkpoint = _run_and_checkpoint(artifact, candidate)
    _install_provider(monkeypatch)

    policy = mdstats.CheckpointEvaluationPolicy(
        replay_baseline_head_name=None,
        condition_keys=(),
        evaluate_foundation_on_target=True,
    )
    sweep_root = tmp_path / "data6-sweep"
    checkpoint_identity = ModelCheckpointIdentity(
        model_family="MACE-MPA-0",
        checkpoint_locator=str(foundation),
        checkpoint_sha256=foundation_sha,
        calculator_class="mace.calculators.MACECalculator",
        model_version="MPA-0",
        supported_atomic_numbers=(3, 8),
        device=policy.device,
        default_dtype=policy.default_dtype,
        metadata=(("acceleration_policy_digest", policy.acceleration_policy.policy_digest),),
    )
    data6_prediction = AtomicModelPrediction(
        energy_ev=-1.6,
        forces_ev_per_angstrom=np.full((2, 3), 0.2),
        stress_ev_per_angstrom3=np.zeros((3, 3)),
    )
    record = _write_prediction(
        sweep_root,
        frame_uid=frame_uid,
        frame_record_digest=_h("frame-record"),
        checkpoint_identity=checkpoint_identity,
        prediction=data6_prediction,
    )
    manifest = AtomicModelPredictionManifest(
        dataset_id="dataset",
        frame_catalog_digest=_h("frame-catalog"),
        data5_bundle_digest=_h("data5"),
        checkpoint_identity=checkpoint_identity,
        records=(record,),
        excluded_frame_uids=(),
    )
    calls = []

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        calls.append(Path(model_path).name)
        if Path(model_path).resolve() == foundation.resolve():
            raise AssertionError("foundation inference should be replaced by DATA6 prediction reuse")
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]),
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.1),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    result = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        replay_baseline_model_path=foundation,
        policy=policy,
        prediction_cache_directory=tmp_path / "prediction-cache",
        foundation_prediction_manifest=manifest,
        foundation_prediction_root=sweep_root,
    )
    assert calls == [candidate.name]
    assert result.target_foundation_prediction_digest is not None
    assert result.target_foundation_metrics.force_component_rmse_ev_per_angstrom == pytest.approx(0.2)
    assert any(
        note == "target_foundation_prediction_source:data6_foundation_prediction_manifest"
        for note in result.metric_record.evaluation_notes
    )


def test_legacy_v2_evaluation_record_migrates_without_prediction_digests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """0.20.97a0 evaluation rows remain readable after the v3 schema upgrade."""

    from mdstats.training_data._common import digest

    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target, _h("target-frame-v2"))
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    run, checkpoint = _run_and_checkpoint(artifact, candidate)
    _install_provider(monkeypatch)

    monkeypatch.setattr(
        campaign_execution,
        "_predict_model_on_atoms",
        lambda model_path, atoms_list, *, head, policy, provider=None: tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]),
                forces_ev_per_angstrom=np.zeros((len(atoms), 3)),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        ),
    )
    current = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=mdstats.CheckpointEvaluationPolicy(condition_keys=()),
        prediction_cache_directory=tmp_path / "prediction-cache",
    )
    payload = current.to_dict()
    payload["schema"] = "mdstats.checkpoint-evaluation-record.v2"
    for name in (
        "target_candidate_prediction_digest",
        "target_foundation_prediction_digest",
        "replay_candidate_prediction_digest",
        "replay_foundation_prediction_digest",
    ):
        payload.pop(name, None)
    payload.pop("content_digest", None)
    payload["content_digest"] = digest(payload)

    restored = mdstats.CheckpointEvaluationRecord.from_dict(payload)
    assert restored.target_candidate_prediction_digest is None
    assert restored.target_foundation_prediction_digest is None
    assert restored.metric_record == current.metric_record
    assert restored.target_candidate_metrics == current.target_candidate_metrics


def test_parallel_foundation_source_import_is_single_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parallel checkpoint workers import one shared foundation prediction set once."""

    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time

    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    artifact = _target_artifact(target, _h("target-frame-single-flight"))
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    candidate_a = tmp_path / "candidate-a.pt"
    candidate_b = tmp_path / "candidate-b.pt"
    candidate_a.write_bytes(b"candidate-a")
    candidate_b.write_bytes(b"candidate-b")
    run_a, checkpoint_a = _run_and_checkpoint(artifact, candidate_a)
    run_b, checkpoint_b = _run_and_checkpoint(artifact, candidate_b)
    _install_provider(monkeypatch)

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        if Path(model_path).resolve() == foundation.resolve():
            raise AssertionError("foundation inference should not run when DATA6 reuse is available")
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]),
                forces_ev_per_angstrom=np.zeros((len(atoms), 3)),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    source_calls = {"value": 0}
    call_lock = threading.Lock()

    def data6_source(*args, **kwargs):
        with call_lock:
            source_calls["value"] += 1
        # Widen the race so a missing single-flight lock would reliably execute twice.
        time.sleep(0.05)
        return (
            (
                AtomicModelPrediction(
                    energy_ev=-2.0,
                    forces_ev_per_angstrom=np.zeros((2, 3)),
                    stress_ev_per_angstrom3=np.zeros((3, 3)),
                ),
            ),
            _h("data6-source"),
        )

    monkeypatch.setattr(campaign_execution, "_data6_foundation_predictions", data6_source)
    cache = tmp_path / "prediction-cache"
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), evaluate_foundation_on_target=True
    )

    def evaluate(candidate, run, checkpoint):
        return mdstats.evaluate_mace_checkpoint(
            run,
            checkpoint,
            candidate_model_path=candidate,
            calculator_model_path=candidate,
            target_monitor_path=target,
            target_monitor_artifact=artifact,
            policy=policy,
            replay_baseline_model_path=foundation,
            prediction_cache_directory=cache,
            foundation_prediction_manifest=object(),
            foundation_prediction_root=tmp_path,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(evaluate, candidate_a, run_a, checkpoint_a)
        second = pool.submit(evaluate, candidate_b, run_b, checkpoint_b)
        first_result = first.result()
        second_result = second.result()

    assert source_calls["value"] == 1
    assert first_result.target_foundation_prediction_digest is not None
    assert (
        first_result.target_foundation_prediction_digest
        == second_result.target_foundation_prediction_digest
    )


def test_true_label_replay_correction_reuses_candidate_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing true replay labels does not require candidate MACE inference again."""

    target = tmp_path / "target.extxyz"
    write(target, [_frame()], format="extxyz")
    target_artifact = _target_artifact(target, _h("target-frame-label-correction"))
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    foundation_sha = hashlib.sha256(foundation.read_bytes()).hexdigest()
    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")

    pseudo = tmp_path / "replay-pseudo.extxyz"
    write(pseudo, [_frame(energy=-1.8, force=0.2)], format="extxyz")
    pseudo_artifact = mdstats.inspect_replay_extxyz(
        pseudo,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation_checkpoint_digest=foundation_sha,
    )
    true_v1 = tmp_path / "replay-true-v1.extxyz"
    true_v2 = tmp_path / "replay-true-v2.extxyz"
    write(true_v1, [_frame(energy=-2.0, force=0.0)], format="extxyz")
    write(true_v2, [_frame(energy=-2.2, force=-0.1)], format="extxyz")
    true_artifact_v1 = mdstats.inspect_replay_extxyz(
        true_v1, label_mode=mdstats.ReplayLabelMode.TRUE_DFT
    )
    true_artifact_v2 = mdstats.inspect_replay_extxyz(
        true_v2, label_mode=mdstats.ReplayLabelMode.TRUE_DFT
    )
    assert true_artifact_v1.geometry_identities == pseudo_artifact.geometry_identities
    assert true_artifact_v2.geometry_identities == pseudo_artifact.geometry_identities
    assert true_artifact_v1.label_payload_digest != true_artifact_v2.label_payload_digest

    run, checkpoint = _run_and_checkpoint(
        target_artifact, candidate, replay_digest=pseudo_artifact.content_digest
    )
    _install_provider(monkeypatch)
    calls = {"candidate": 0, "foundation": 0}

    def predict(model_path, atoms_list, *, head, policy, provider=None):
        if Path(model_path).resolve() == foundation.resolve():
            calls["foundation"] += 1
        else:
            calls["candidate"] += 1
        return tuple(
            AtomicModelPrediction(
                energy_ev=-1.9,
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.05),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", predict)
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), replay_baseline_head_name=None
    )
    cache = tmp_path / "prediction-cache"

    first = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=target_artifact,
        policy=policy,
        replay_monitor_path=true_v1,
        replay_monitor_artifact=true_artifact_v1,
        training_replay_monitor_artifact=pseudo_artifact,
        training_replay_monitor_path=pseudo,
        replay_baseline_model_path=foundation,
        prediction_cache_directory=cache,
    )
    # Candidate target + replay are the only actual model evaluations; replay
    # foundation comes from the frozen pseudolabel artifact.
    assert calls == {"candidate": 2, "foundation": 0}

    candidate.unlink()
    second = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=None,
        target_monitor_path=target,
        target_monitor_artifact=target_artifact,
        policy=policy,
        replay_monitor_path=true_v2,
        replay_monitor_artifact=true_artifact_v2,
        training_replay_monitor_artifact=pseudo_artifact,
        training_replay_monitor_path=pseudo,
        replay_baseline_model_path=foundation,
        prediction_cache_directory=cache,
    )
    assert calls == {"candidate": 2, "foundation": 0}
    assert second.replay_candidate_prediction_digest == first.replay_candidate_prediction_digest
    assert second.metric_record.replay_candidate_metric != first.metric_record.replay_candidate_metric
    assert "target_candidate_prediction_cache:hit" in second.metric_record.evaluation_notes
    assert "replay_candidate_prediction_cache:hit" in second.metric_record.evaluation_notes
