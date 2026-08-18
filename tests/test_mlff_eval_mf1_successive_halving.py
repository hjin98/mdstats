from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_execution
from mdstats.training_data.model_features import AtomicModelPrediction, MaceCalculatorProvider


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_monitor_ladders_are_nested_balanced_and_equal_fraction() -> None:
    policy = mdstats.MultiFidelityEvaluationPolicy()
    target_ids = tuple(_h(f"target-{i}") for i in range(100))
    replay_ids = tuple(_h(f"replay-{i}") for i in range(50))
    target = mdstats.build_monitor_ladder(
        domain="target",
        monitor_artifact_digest=_h("target-artifact"),
        geometry_identities=target_ids,
        policy=policy,
        stratum_labels=tuple(f"c{i % 5}" for i in range(100)),
        source_labels=tuple(f"run{i % 10}" for i in range(100)),
        temporal_indices=tuple(i // 10 for i in range(100)),
    )
    replay = mdstats.build_monitor_ladder(
        domain="replay",
        monitor_artifact_digest=_h("replay-artifact"),
        geometry_identities=replay_ids,
        policy=policy,
        stratum_labels=tuple(f"c{i % 5}" for i in range(50)),
        source_labels=tuple(f"run{i % 5}" for i in range(50)),
        temporal_indices=tuple(i // 5 for i in range(50)),
    )
    assert tuple(len(v) for v in target.round_indices) == (10, 33, 100)
    assert tuple(len(v) for v in replay.round_indices) == (5, 17, 50)
    assert target.round_indices[0] == target.round_indices[1][:10]
    assert target.round_indices[1] == target.round_indices[2][:33]
    assert replay.round_indices[0] == replay.round_indices[1][:5]
    assert replay.round_indices[1] == replay.round_indices[2][:17]
    assert target.round_delta_indices[1] == target.round_indices[1][10:]
    assert replay.round_delta_indices[2] == replay.round_indices[2][17:]


def _frame(index: int) -> Atoms:
    atoms = Atoms(
        numbers=[3, 8],
        positions=[[0.01 * index, 0.0, 0.0], [1.8 + 0.01 * index, 0.0, 0.0]],
        cell=np.eye(3) * 6.0,
        pbc=True,
    )
    atoms.info["REF_energy"] = -2.0 + 0.01 * index
    atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=float)
    atoms.info["REF_stress"] = np.zeros(6)
    return atoms


def _artifact(path: Path, count: int) -> mdstats.MaceExtxyzArtifact:
    return mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        configuration_count=count,
        frame_uids=tuple(_h(f"frame-{i}") for i in range(count)),
        atomic_numbers=(3, 8),
        policy_digest=_h("target-policy"),
        sidecar_relative_path="target.manifest.json",
        sidecar_sha256=_h("target-sidecar-file"),
        sidecar_digest=_h("target-sidecar-record"),
    )


def _run_checkpoint(artifact: mdstats.MaceExtxyzArtifact, candidate: Path):
    metric_policy = mdstats.CheckpointMetricPolicy()
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mf1-run",
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
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
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


def test_nested_rounds_infer_only_new_delta_and_compose_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    frames = [_frame(i) for i in range(10)]
    write(target, frames, format="extxyz")
    artifact = _artifact(target, 10)
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
    call_sizes: list[int] = []

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        call_sizes.append(len(atoms_list))
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.1,
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.05),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)

    round1 = (0, 5, 2)
    p1 = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
        target_configuration_indices=round1,
    )
    b1 = mdstats.run_prepared_mace_checkpoint_inference(p1, calculator_model_path=candidate)
    r1 = mdstats.finalize_prepared_mace_checkpoint_evaluation(p1, b1)
    assert r1.target_configuration_count == 3

    delta2 = (8, 1)
    p2 = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
        target_configuration_indices=delta2,
    )
    b2 = mdstats.run_prepared_mace_checkpoint_inference(p2, calculator_model_path=candidate)
    mdstats.finalize_prepared_mace_checkpoint_evaluation(p2, b2)

    cumulative = round1 + delta2
    pc = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
        target_configuration_indices=cumulative,
    )
    assert not pc.requires_model_inference
    bc = mdstats.run_prepared_mace_checkpoint_inference(pc)
    rc = mdstats.finalize_prepared_mace_checkpoint_evaluation(pc, bc)
    assert rc.target_configuration_count == 5
    assert call_sizes == [3, 2]

    direct_cache = tmp_path / "direct-predictions"
    pd = mdstats.prepare_mace_checkpoint_evaluation(
        run, checkpoint, candidate_model_path=candidate, calculator_model_path=candidate,
        target_monitor_path=target, target_monitor_artifact=artifact, policy=policy,
        prediction_cache_directory=direct_cache, target_configuration_indices=cumulative,
    )
    bd = mdstats.run_prepared_mace_checkpoint_inference(pd, calculator_model_path=candidate)
    rd = mdstats.finalize_prepared_mace_checkpoint_evaluation(pd, bd)
    assert rd.metric_record.force_component_rmse_ev_per_angstrom == pytest.approx(
        rc.metric_record.force_component_rmse_ev_per_angstrom, rel=0.0, abs=1.0e-15
    )
    assert rd.metric_record.energy_mae_ev_per_atom == pytest.approx(
        rc.metric_record.energy_mae_ev_per_atom, rel=0.0, abs=1.0e-15
    )
    assert call_sizes == [3, 2, 5]


def test_campaign_multifidelity_screening_all_epochs_then_full_finalists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from mdstats.training_data import campaign_cli

    root = tmp_path / "data8"
    job_root = root / "job"
    job_root.mkdir(parents=True)
    target = job_root / "target.extxyz"
    write(target, [_frame(i) for i in range(10)], format="extxyz")
    artifact = _artifact(target, 10)
    # No sidecar is required for correctness; the planner falls back to the
    # immutable extxyz order/metadata when it is absent.
    metric_policy = mdstats.CheckpointMetricPolicy()
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mf1-campaign-run",
        data8_bundle_digest=_h("data8-campaign"),
        mace_job_artifact_digest=_h("job-campaign"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family-campaign"),
        protocol_variant_digest=_h("variant-campaign"),
        protocol_digest=_h("protocol-campaign"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        target_monitor_artifact_digest=artifact.content_digest,
        replay_monitor_artifact_digest=None,
        relative_output_directory="run",
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    checkpoints = []
    for epoch in range(9):
        path = checkpoint_root / f"epoch-{epoch}.pt"
        path.write_bytes(f"checkpoint-{epoch}".encode())
        checkpoints.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run.content_digest,
                candidate_id=f"candidate-{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size_bytes=path.stat().st_size,
            )
        )
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory=str(checkpoint_root),
        checkpoints=tuple(checkpoints),
        pattern="*.pt",
    )
    bundle = SimpleNamespace(
        target_artifacts=(artifact,),
        replay_plan=SimpleNamespace(monitor_artifact=None),
    )
    config_path = root / "job" / "config.yaml"
    config_path.write_text("model: test\n", encoding="utf-8")
    job = SimpleNamespace(relative_directory="job", config_relative_path="job/config.yaml")
    execution = SimpleNamespace(checkpoint_catalog=catalog)

    cfg = {
        "campaign": {"workspace": str(tmp_path / "workspace")},
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
            "parallel_evaluation_monitor_interval_seconds": 0.001,
        },
        "evaluation": {
            "multi_fidelity_round_fractions": [0.10, 0.33, 1.0],
            "multi_fidelity_survival_fraction": 1.0 / 3.0,
            "multi_fidelity_minimum_finalists": 3,
        },
    }
    cfg_file = tmp_path / "campaign.toml"
    cfg_file.write_text("", encoding="utf-8")
    paths = campaign_cli.CampaignPaths.from_config(cfg_file, cfg)
    paths.ensure()
    store = campaign_cli.CampaignStore(paths.state_db)

    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: _Provider()),
    )
    # No checkpoint reconstruction is needed for the synthetic provider.
    monkeypatch.setattr(mdstats, "materialize_mace_checkpoint_model", lambda checkpoint, source, **kwargs: Path(source))
    inferred_configuration_count = {epoch: 0 for epoch in range(9)}

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        epoch = int(Path(model_path).stem.split("-")[-1])
        inferred_configuration_count[epoch] += len(atoms_list)
        # Epoch 4 is the true optimum; surrounding epochs remain close enough to
        # exercise deterministic ranking rather than trivial epoch ordering.
        force_error = 0.01 + 0.002 * abs(epoch - 4)
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + force_error,
                forces_ev_per_angstrom=np.full((len(atoms), 3), force_error),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)

    shortlist = campaign_cli._multi_fidelity_screen_run(
        cfg=cfg,
        paths=paths,
        store=store,
        run=run,
        original_catalog=catalog,
        bundle=bundle,
        job=job,
        root=root,
        execution=execution,
        evaluation_policy=mdstats.CheckpointEvaluationPolicy(condition_keys=(), device="cpu"),
        metric_policy=metric_policy,
        true_replay_resolution=None,
        baseline_model=None,
        prediction_cache_directory=paths.internal / "evaluation-predictions",
        graph_cache_directory=paths.internal / "evaluation-graphs",
        foundation_prediction_manifest=None,
        foundation_prediction_root=None,
        local_wrappers={"mdstats-mace-train": tmp_path / "unused-wrapper"},
    )
    assert shortlist.original_count == 9
    assert len(shortlist.catalog.checkpoints) == 3
    assert 4 in shortlist.selected_epochs
    policy = campaign_cli._multi_fidelity_policy(cfg)
    # Every checkpoint entered the first round.
    for checkpoint in checkpoints:
        assert store.has_record(
            f"multifidelity_round:{run.run_id}:{policy.policy_digest}:0:{checkpoint.sha256}"
        )
    # Only the three finalists receive the authoritative full evaluation record.
    finalist_shas = {checkpoint.sha256 for checkpoint in shortlist.catalog.checkpoints}
    for checkpoint in checkpoints:
        assert store.has_record(f"evaluation:{run.run_id}:{checkpoint.sha256}") == (
            checkpoint.sha256 in finalist_shas
        )
    # The screening record is auditable: every candidate has an explicit rank,
    # retained/screened-out outcome, and deterministic reason code.
    survivor_payload = store.get_payload(
        f"multifidelity_survivors:{run.run_id}:{policy.policy_digest}:0"
    )
    ranking = survivor_payload["ranking"]
    assert len(ranking) == 9
    assert [entry["rank"] for entry in ranking] == list(range(1, 10))
    assert {entry["outcome"] for entry in ranking} == {"retained", "screened_out"}
    assert all(str(entry["reason_code"]).startswith("multifidelity_round1_") for entry in ranking)
    # Delta-only inference reduces work below exhaustive 9 * 10 configurations.
    assert sum(inferred_configuration_count.values()) < 90
    first_pass_work = dict(inferred_configuration_count)
    restarted = campaign_cli._multi_fidelity_screen_run(
        cfg=cfg,
        paths=paths,
        store=store,
        run=run,
        original_catalog=catalog,
        bundle=bundle,
        job=job,
        root=root,
        execution=execution,
        evaluation_policy=mdstats.CheckpointEvaluationPolicy(condition_keys=(), device="cpu"),
        metric_policy=metric_policy,
        true_replay_resolution=None,
        baseline_model=None,
        prediction_cache_directory=paths.internal / "evaluation-predictions",
        graph_cache_directory=paths.internal / "evaluation-graphs",
        foundation_prediction_manifest=None,
        foundation_prediction_root=None,
        local_wrappers={"mdstats-mace-train": tmp_path / "unused-wrapper"},
    )
    assert restarted.selected_epochs == shortlist.selected_epochs
    assert inferred_configuration_count == first_pass_work
    store.close()


def test_corrupt_partial_prediction_shard_recomputes_only_that_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    write(target, [_frame(i) for i in range(6)], format="extxyz")
    artifact = _artifact(target, 6)
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
    calls: list[int] = []

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        calls.append(len(atoms_list))
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.1,
                forces_ev_per_angstrom=np.full((len(atoms), 3), 0.05),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)
    indices = (0, 3, 5)
    first = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
        target_configuration_indices=indices,
    )
    first_bundle = mdstats.run_prepared_mace_checkpoint_inference(
        first, calculator_model_path=candidate
    )
    mdstats.finalize_prepared_mace_checkpoint_evaluation(first, first_bundle)
    assert calls == [3]
    npz_files = list(cache.rglob("*.npz"))
    assert len(npz_files) == 1
    npz_files[0].write_bytes(b"corrupt")

    recovered = mdstats.prepare_mace_checkpoint_evaluation(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=artifact,
        policy=policy,
        prediction_cache_directory=cache,
        target_configuration_indices=indices,
    )
    assert recovered.requires_model_inference
    recovered_bundle = mdstats.run_prepared_mace_checkpoint_inference(
        recovered, calculator_model_path=candidate
    )
    mdstats.finalize_prepared_mace_checkpoint_evaluation(recovered, recovered_bundle)
    assert calls == [3, 3]



def test_monitor_order_metadata_uses_available_source_and_temporal_metadata(
    tmp_path: Path,
) -> None:
    from mdstats.training_data import campaign_cli

    monitor = tmp_path / "metadata.extxyz"
    atoms_list = []
    for index in range(4):
        atoms = _frame(index)
        atoms.info["config_type"] = "target"
        atoms.info["run_id"] = "run-a" if index < 2 else "run-b"
        atoms.info["source_frame_index"] = 10 + index
        atoms.info["temperature_kelvin"] = 300 if index % 2 == 0 else 700
        atoms_list.append(atoms)
    write(monitor, atoms_list, format="extxyz")
    geometry = tuple(_h(f"metadata-{index}") for index in range(4))
    strata, sources, temporal = campaign_cli._monitor_order_metadata(
        monitor,
        geometry,
        condition_keys=("temperature_kelvin",),
    )
    assert sources == ("run-a", "run-a", "run-b", "run-b")
    assert temporal == (10, 11, 12, 13)
    assert strata[0].endswith("|300")
    assert strata[1].endswith("|700")

def _replay_artifact(path: Path, count: int) -> mdstats.ReplayFileArtifact:
    return mdstats.ReplayFileArtifact(
        path=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        configuration_count=count,
        atomic_numbers=(3, 8),
        geometry_identities=tuple(_h(f"replay-geometry-{i}") for i in range(count)),
        label_identities=tuple(_h(f"replay-label-{i}") for i in range(count)),
        energy_key="REF_energy",
        forces_key="REF_forces",
        stress_key="REF_stress",
        stress_present_count=count,
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )


def test_multifidelity_replay_finalist_gets_full_target_and_full_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from mdstats.training_data import campaign_cli

    root = tmp_path / "data8"
    job_root = root / "job"
    job_root.mkdir(parents=True)
    target = job_root / "target.extxyz"
    replay = root / "replay.extxyz"
    write(target, [_frame(i) for i in range(6)], format="extxyz")
    write(replay, [_frame(i + 20) for i in range(6)], format="extxyz")
    target_artifact = _artifact(target, 6)
    replay_artifact = _replay_artifact(replay, 6)
    metric_policy = mdstats.CheckpointMetricPolicy()
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mf1-replay-run",
        data8_bundle_digest=_h("data8-replay"),
        mace_job_artifact_digest=_h("job-replay"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family-replay"),
        protocol_variant_digest=_h("variant-replay"),
        protocol_digest=_h("protocol-replay"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        target_monitor_artifact_digest=target_artifact.content_digest,
        replay_monitor_artifact_digest=replay_artifact.content_digest,
        relative_output_directory="run",
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    checkpoints = []
    for epoch in range(3):
        path = checkpoint_root / f"epoch-{epoch}.pt"
        path.write_bytes(f"checkpoint-{epoch}".encode())
        checkpoints.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run.content_digest,
                candidate_id=f"candidate-{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size_bytes=path.stat().st_size,
            )
        )
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory=str(checkpoint_root),
        checkpoints=tuple(checkpoints),
        pattern="*.pt",
    )
    baseline = tmp_path / "foundation.model"
    baseline.write_bytes(b"foundation")
    bundle = SimpleNamespace(
        target_artifacts=(target_artifact,),
        replay_plan=SimpleNamespace(monitor_artifact=replay_artifact),
        output_directory=str(root),
    )
    (root / "job" / "config.yaml").write_text("model: test\n", encoding="utf-8")
    job = SimpleNamespace(relative_directory="job", config_relative_path="job/config.yaml")
    execution = SimpleNamespace(checkpoint_catalog=catalog)
    cfg = {
        "campaign": {"workspace": str(tmp_path / "workspace")},
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
            "parallel_evaluation_monitor_interval_seconds": 0.001,
        },
        "evaluation": {
            "multi_fidelity_round_fractions": [0.5, 1.0],
            "multi_fidelity_survival_fraction": 1.0 / 3.0,
            "multi_fidelity_minimum_finalists": 1,
        },
    }
    cfg_file = tmp_path / "campaign.toml"
    cfg_file.write_text("", encoding="utf-8")
    paths = campaign_cli.CampaignPaths.from_config(cfg_file, cfg)
    paths.ensure()
    store = campaign_cli.CampaignStore(paths.state_db)
    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: _Provider()),
    )
    monkeypatch.setattr(
        mdstats,
        "materialize_mace_checkpoint_model",
        lambda checkpoint, source, **kwargs: Path(source),
    )

    def predict(model_path, atoms_list, *, head, policy, provider=None, **kwargs):
        path = Path(model_path)
        if path.name == baseline.name:
            error = 0.01
        else:
            epoch = int(path.stem.split("-")[-1])
            error = (0.015, 0.012, 0.020)[epoch]
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + error,
                forces_ev_per_angstrom=np.full((len(atoms), 3), error),
                stress_ev_per_angstrom3=np.zeros((3, 3)),
            )
            for atoms in atoms_list
        )

    monkeypatch.setattr(campaign_execution, "_predict_model_on_monitor", predict)
    shortlist = campaign_cli._multi_fidelity_screen_run(
        cfg=cfg,
        paths=paths,
        store=store,
        run=run,
        original_catalog=catalog,
        bundle=bundle,
        job=job,
        root=root,
        execution=execution,
        evaluation_policy=mdstats.CheckpointEvaluationPolicy(
            condition_keys=(), device="cpu", replay_baseline_head_name=None
        ),
        metric_policy=metric_policy,
        true_replay_resolution=None,
        baseline_model=baseline,
        prediction_cache_directory=paths.internal / "evaluation-predictions",
        graph_cache_directory=paths.internal / "evaluation-graphs",
        foundation_prediction_manifest=None,
        foundation_prediction_root=None,
        local_wrappers={"mdstats-mace-train": tmp_path / "unused-wrapper"},
    )
    assert len(shortlist.catalog.checkpoints) == 1
    finalist = shortlist.catalog.checkpoints[0]
    final_record = store.get_record(
        f"evaluation:{run.run_id}:{finalist.sha256}",
        mdstats.CheckpointEvaluationRecord,
    )
    assert final_record.target_configuration_count == 6
    assert final_record.replay_configuration_count == 6
    policy = campaign_cli._multi_fidelity_policy(cfg)
    round0 = store.get_payload(
        f"multifidelity_round:{run.run_id}:{policy.policy_digest}:0:{checkpoints[0].sha256}"
    )
    assert round0["target_configuration_count"] == 3
    assert round0["replay_configuration_count"] == 3
    assert round0["evidence_class"] == "screening_partial"
    store.close()
