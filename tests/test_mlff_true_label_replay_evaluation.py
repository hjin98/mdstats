from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
import time

import numpy as np
import pytest
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read, write

import mdstats
from mdstats.training_data import campaign_cli, campaign_execution
from mdstats.training_data.model_features import MaceCalculatorProvider


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _source_frame(index: int) -> Atoms:
    atoms = Atoms(
        "LiO",
        positions=[[0.0, 0.0, 0.0], [1.5 + 0.05 * index, 0.0, 0.0]],
        cell=np.eye(3) * (6.0 + 0.1 * index),
        pbc=True,
    )
    atoms.calc = SinglePointCalculator(
        atoms,
        energy=-2.0 - index,
        forces=np.full((2, 3), 0.01 * (index + 1)),
        stress=np.full(6, 0.001 * (index + 1)),
    )
    return atoms


def _pseudo_split(source: list[Atoms], indices: tuple[int, ...], path: Path) -> None:
    frames = []
    for source_index in indices:
        atoms = source[source_index].copy()
        atoms.calc = None
        atoms.info["REF_energy"] = 100.0 + source_index
        atoms.arrays["REF_forces"] = np.full((2, 3), 9.0)
        atoms.info["REF_stress"] = np.full(6, 8.0)
        atoms.info["replay_source_index"] = source_index
        atoms.info["replay_pseudolabel_model_sha256"] = _h("foundation")
        frames.append(atoms)
    write(path, frames, format="extxyz")


def test_true_label_directory_materializes_original_source_labels_and_reuses_cache(
    tmp_path: Path,
) -> None:
    root = tmp_path / "replay"
    root.mkdir()
    source = [_source_frame(i) for i in range(4)]
    write(root / "mp_replay_selected.extxyz", source, format="extxyz")
    _pseudo_split(source, (0, 2, 3), root / "replay_train.extxyz")
    _pseudo_split(source, (1,), root / "replay_monitor.extxyz")

    output = tmp_path / "cache"
    resolution = mdstats.resolve_true_label_replay_directory(
        root,
        replay_train_path=root / "replay_train.extxyz",
        replay_monitor_path=root / "replay_monitor.extxyz",
        output_directory=output,
        require_train=True,
    )
    assert resolution.materialized
    assert resolution.train_artifact is not None
    assert resolution.monitor_artifact.label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    true_monitor = read(resolution.monitor_path, index=0, format="extxyz")
    assert true_monitor.info["REF_energy"] == pytest.approx(-3.0)
    np.testing.assert_allclose(true_monitor.arrays["REF_forces"], 0.02)
    np.testing.assert_allclose(true_monitor.info["REF_stress"], 0.002)
    assert "replay_pseudolabel_model_sha256" not in true_monitor.info

    monitor_path = Path(resolution.monitor_path)
    first_mtime = monitor_path.stat().st_mtime_ns
    time.sleep(0.001)
    restored = mdstats.resolve_true_label_replay_directory(
        root,
        replay_train_path=root / "replay_train.extxyz",
        replay_monitor_path=root / "replay_monitor.extxyz",
        output_directory=output,
        require_train=True,
    )
    assert Path(restored.monitor_path).stat().st_mtime_ns == first_mtime
    assert restored.monitor_artifact == resolution.monitor_artifact


def test_checkpoint_evaluation_uses_true_labels_without_changing_training_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.extxyz"
    replay_pseudo = tmp_path / "replay-pseudo.extxyz"
    replay_true = tmp_path / "replay-true.extxyz"
    target_atoms = _source_frame(0)
    target_atoms.calc = None
    target_atoms.info["REF_energy"] = -2.0
    target_atoms.arrays["REF_forces"] = np.zeros((2, 3))
    target_atoms.info["REF_stress"] = np.zeros(6)
    write(target, [target_atoms], format="extxyz")
    pseudo_atoms = target_atoms.copy()
    pseudo_atoms.info["REF_energy"] = 10.0
    write(replay_pseudo, [pseudo_atoms], format="extxyz")
    true_atoms = target_atoms.copy()
    true_atoms.info["REF_energy"] = -2.0
    write(replay_true, [true_atoms], format="extxyz")

    foundation = tmp_path / "foundation.model"
    candidate = tmp_path / "candidate.pt"
    foundation.write_bytes(b"foundation")
    candidate.write_bytes(b"candidate")
    foundation_sha = hashlib.sha256(foundation.read_bytes()).hexdigest()
    candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    training_replay = mdstats.inspect_replay_extxyz(
        replay_pseudo,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation_checkpoint_digest=foundation_sha,
    )
    true_replay = mdstats.inspect_replay_extxyz(
        replay_true, label_mode=mdstats.ReplayLabelMode.TRUE_DFT
    )
    target_artifact = mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=target.name,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        configuration_count=1,
        frame_uids=(_h("target-frame"),),
        atomic_numbers=(3, 8),
        policy_digest=_h("target-policy"),
        sidecar_relative_path="target.manifest.json",
        sidecar_sha256=_h("target-sidecar-file"),
        sidecar_digest=_h("target-sidecar-record"),
    )
    run = mdstats.TrainingCampaignRunPlan(
        run_id="true-label-refresh",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=_h("job"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=_h("metric-policy"),
        target_monitor_artifact_digest=target_artifact.content_digest,
        replay_monitor_artifact_digest=training_replay.content_digest,
        relative_output_directory="run",
    )
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate",
        epoch=1,
        relative_path=candidate.name,
        sha256=candidate_sha,
        size_bytes=candidate.stat().st_size,
    )

    class Provider:
        def set_head(self, head):
            self.head = head

    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: Provider()),
    )

    # Use call order to make the foundation/candidate prediction errors distinct.
    calls = []

    def ordered_predictions(model_path, atoms_list, *, head, policy, provider=None):
        from mdstats.training_data.model_features import AtomicModelPrediction

        calls.append((Path(model_path).name, head))
        # New OPT-EVAL2 order: target candidate, target foundation, replay
        # candidate, replay foundation.  References have zero forces/stress.
        values = [0.10, 0.20, 0.33, 0.30]
        error = values[len(calls) - 1]
        result = []
        for atoms in atoms_list:
            result.append(
                AtomicModelPrediction(
                    energy_ev=float(atoms.info["REF_energy"]) + error * len(atoms),
                    forces_ev_per_angstrom=np.full((len(atoms), 3), error),
                    stress_ev_per_angstrom3=np.full((3, 3), error),
                )
            )
        return tuple(result)

    monkeypatch.setattr(campaign_execution, "_predict_model_on_atoms", ordered_predictions)
    evaluation = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=candidate,
        target_monitor_path=target,
        target_monitor_artifact=target_artifact,
        replay_monitor_path=replay_true,
        replay_monitor_artifact=true_replay,
        training_replay_monitor_artifact=training_replay,
        replay_baseline_model_path=foundation,
        policy=mdstats.CheckpointEvaluationPolicy(
            replay_baseline_head_name=None,
            condition_keys=(),
            evaluate_foundation_on_target=True,
        ),
    )
    assert evaluation.replay_monitor_artifact_digest == true_replay.content_digest
    assert evaluation.metric_record.replay_monitor_artifact_digest == training_replay.content_digest
    assert evaluation.metric_record.replay_label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert evaluation.metric_record.replay_degradation_fraction == pytest.approx(0.10)
    assert evaluation.target_candidate_metrics.force_component_rmse_ev_per_angstrom == 0.10
    assert evaluation.target_foundation_metrics.force_component_rmse_ev_per_angstrom == 0.20
    assert evaluation.replay_foundation_metrics.force_component_rmse_ev_per_angstrom == 0.30
    assert evaluation.replay_candidate_metrics.force_component_rmse_ev_per_angstrom == 0.33
    assert evaluation.has_complete_model_comparison
    assert mdstats.CheckpointEvaluationRecord.from_dict(evaluation.to_dict()) == evaluation


def test_new_config_requests_true_label_directory_but_legacy_config_remains_valid() -> None:
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.extxyz",
        replay_monitor="replay_monitor.extxyz",
        replay_true_labels="true-label-root",
    )
    assert 'replay_true_labels = "true-label-root"' in text
    assert 'mode = "external_pseudolabel"' in text
    assert 'checkpoint_strategy = "train2_target_first"' in text


def test_true_label_refresh_uses_retained_selected_checkpoint_after_pruning(
    tmp_path: Path,
) -> None:
    run_digest = _h("run-plan")
    root = tmp_path / "checkpoints"
    root.mkdir()
    records = []
    for epoch in (1, 2, 3):
        path = root / f"epoch-{epoch}.pt"
        path.write_bytes(f"checkpoint-{epoch}".encode())
        records.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run_digest,
                candidate_id=f"epoch-{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size_bytes=path.stat().st_size,
            )
        )
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run_digest,
        root_directory=str(root),
        checkpoints=tuple(records),
        pattern="*.pt",
    )
    shortlist_catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run_digest,
        root_directory=str(root),
        checkpoints=(records[0], records[1]),
        pattern="*.pt",
    )
    shortlist = campaign_cli._CheckpointShortlist(
        catalog=shortlist_catalog,
        original_catalog_digest=catalog.content_digest,
        original_count=3,
        selected_epochs=(1, 2),
        reasons_by_epoch=((1, ("best",)), (2, ("latest",))),
        history_files=(),
        used_training_history=True,
    )
    # Simulate cleanup: epoch 1 was screened/evaluated and deleted, epoch 2 is
    # still available, and the previous selected epoch 3 is retained.
    (root / records[0].relative_path).unlink()
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite")
    store.put_record(
        "selection:run-a",
        {"selected_checkpoint_sha256": records[2].sha256},
    )
    store.put_record(
        "checkpoint_retention:run-a",
        {"removed_checkpoints": [records[0].to_dict()]},
    )
    refreshed, unavailable = campaign_cli._available_checkpoint_refresh_shortlist(
        SimpleNamespace(run_id="run-a"), shortlist, catalog, store
    )
    assert unavailable == 1
    assert [item.epoch for item in refreshed.catalog.checkpoints] == [2, 3]
    assert "retained_checkpoint_available_for_true_label_refresh" in dict(
        refreshed.reasons_by_epoch
    )[3]


def test_evaluation_policy_writes_runtime_independent_v8_identity() -> None:
    legacy_compatible = mdstats.CheckpointEvaluationPolicy(
        evaluate_foundation_on_target=False
    )
    payload = legacy_compatible.to_dict()
    assert payload["schema"] == "mdstats.checkpoint-evaluation-policy.v8"
    assert "batch_size" not in payload
    assert "cache_monitor_datasets" not in payload
    assert "cache_replay_baseline" not in payload
    assert "evaluate_foundation_on_target" not in payload
    assert mdstats.CheckpointEvaluationPolicy.from_dict(payload) == legacy_compatible

    full_comparison = mdstats.CheckpointEvaluationPolicy(
        evaluate_foundation_on_target=True
    )
    payload = full_comparison.to_dict()
    assert payload["schema"] == "mdstats.checkpoint-evaluation-policy.v8"
    assert payload["evaluate_foundation_on_target"] is True
    assert mdstats.CheckpointEvaluationPolicy.from_dict(payload) == full_comparison


def test_model_dataset_metrics_allow_missing_stress() -> None:
    record = mdstats.ModelDatasetMetricRecord(
        configuration_count=2,
        energy_mae_ev_per_atom=0.1,
        force_component_rmse_ev_per_angstrom=0.2,
        stress_rmse_ev_per_angstrom3=None,
        worst_condition_force_rmse_ev_per_angstrom=0.3,
        combined_loss=0.4,
    )
    assert record.stress_rmse_ev_per_angstrom3 is None
    assert mdstats.ModelDatasetMetricRecord.from_dict(record.to_dict()) == record
