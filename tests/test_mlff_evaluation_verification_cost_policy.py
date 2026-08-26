from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import mdstats
from mdstats.training_data import campaign_cli


_DIGEST = "a" * 64


def _catalog(tmp_path: Path, epochs: range) -> mdstats.CandidateCheckpointCatalog:
    records = []
    for epoch in epochs:
        path = tmp_path / f"model_epoch-{epoch}.pt"
        path.write_bytes(f"checkpoint-{epoch}".encode())
        records.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=_DIGEST,
                candidate_id=f"run:epoch:{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=campaign_cli._sha256(path),
                size_bytes=path.stat().st_size,
            )
        )
    return mdstats.CandidateCheckpointCatalog(
        run_plan_digest=_DIGEST,
        root_directory=str(tmp_path),
        checkpoints=tuple(records),
        pattern="*epoch*.pt",
    )


def test_checkpoint_shortlist_uses_validation_history_and_latest(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, range(6))
    results = tmp_path / "results"
    results.mkdir()
    rows = []
    target_rmse = [0.8, 0.6, 0.4, 0.2, 0.3, 0.35]
    target_loss = [0.9, 0.7, 0.5, 0.45, 0.25, 0.4]
    replay_rmse = [0.2, 0.19, 0.18, 0.17, 0.16, 0.15]
    for epoch in range(6):
        rows.append({"mode": "eval", "epoch": epoch, "head": "target_head", "rmse_f": target_rmse[epoch], "loss": target_loss[epoch]})
        rows.append({"mode": "eval", "epoch": epoch, "head": "pt_head", "rmse_f": replay_rmse[epoch], "loss": replay_rmse[epoch]})
    (results / "run-1_train.txt").write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    run = SimpleNamespace(replay_monitor_artifact_digest="b" * 64)
    shortlist = campaign_cli._checkpoint_shortlist(
        run,
        catalog,
        results,
        maximum_candidates=4,
    )

    assert len(shortlist.catalog.checkpoints) == 4
    assert 3 in shortlist.selected_epochs  # best target force RMSE
    assert 4 in shortlist.selected_epochs  # best target loss
    assert 5 in shortlist.selected_epochs  # latest and best replay
    assert shortlist.original_count == 6
    assert shortlist.used_training_history is True
    assert shortlist.to_dict()["original_catalog_digest"] == catalog.content_digest


def test_checkpoint_shortlist_zero_keeps_all(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, range(3))
    shortlist = campaign_cli._checkpoint_shortlist(
        SimpleNamespace(replay_monitor_artifact_digest=None),
        catalog,
        tmp_path / "missing-results",
        maximum_candidates=0,
    )
    assert shortlist.catalog.content_digest == catalog.content_digest
    assert shortlist.selected_epochs == (0, 1, 2)


def test_verification_full_members_prefers_final_for_interim() -> None:
    fold = SimpleNamespace(run_id="fold", exported_model_path="fold.model", kind=SimpleNamespace(value="cross_validation_fold"))
    final = SimpleNamespace(run_id="final", exported_model_path="final.model", kind=SimpleNamespace(value="final_development"))
    result = campaign_cli._verification_full_members(
        (fold, final),
        SimpleNamespace(),
        full_verification=False,
    )
    assert result == (final,)
    assert campaign_cli._verification_full_members(
        (fold, final), SimpleNamespace(), full_verification=True
    ) == (fold, final)


def test_generated_config_exposes_adaptive_evaluation_and_verification() -> None:
    text = campaign_cli._config_template(
        workspace="workspace",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
    )
    assert 'checkpoint_strategy = "train2_target_first"' in text
    assert "finalist_count = 5" in text
    assert "fallback_to_next_full_evaluation_candidate = true" in text
    assert "screening_steps = 200" in text
    assert "sample_interval_steps = 10" in text
    assert "prune_screened_out_checkpoints_after_evaluate = true" in text
    assert "parallel_inference_calibration_window_seconds = 120.0" in text
    assert "inference_minimum_calibration_seconds = 20.0" in text
    assert "inference_calibration_stability_relative_tolerance = 0.10" in text
    assert "inference_gpu_minimum_activity_fraction = 0.01" in text
    assert "inference_gpu_calibration_peak_trim_fraction = 0.05" in text
    assert "inference_gpu_calibration_band_fraction = 0.10" in text
    assert "parallel_inference_cpu_calibration_window_seconds = 20.0" in text


def test_nve_diagnostics_are_sampled_without_skipping_integration(tmp_path: Path) -> None:
    import numpy as np
    from ase import Atoms
    from ase.calculators.calculator import Calculator, all_changes
    from ase.io import write

    class ZeroCalculator(Calculator):
        implemented_properties = ["energy", "forces"]

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            self.results["energy"] = 0.0
            self.results["forces"] = np.zeros((len(atoms), 3), dtype=float)

    structure = tmp_path / "structure.xyz"
    write(structure, Atoms("Li3", positions=[[0, 0, 0], [2, 0, 0], [0, 2, 0]], cell=[20, 20, 20], pbc=True))
    acceleration = SimpleNamespace(backend=SimpleNamespace(value="e3nn"))
    import threading
    from mdstats.training_data.inference_parallel import inference_start_signal

    inference_started = threading.Event()
    with inference_start_signal(inference_started.set):
        result = campaign_cli._nve_verify(
            tmp_path / "unused.model",
            structure,
            device="cpu",
            dtype="float32",
            acceleration_policy=acceleration,
            temperature=10.0,
            timestep_fs=0.1,
            steps=20,
            velocity_seed=7,
            sample_interval_steps=5,
            calculator=ZeroCalculator(),
        )
    assert inference_started.is_set()
    assert result["steps"] == 20
    assert result["sample_interval_steps"] == 5
    assert result["sample_count"] == 5
    assert result["finite"] is True


def test_inadmissible_bounded_shortlist_returns_diagnostic_instead_of_selection(tmp_path: Path) -> None:
    from tests.test_mlff_data9b1_campaign_checkpoint_control import (
        _manual_run,
        _metric_policy,
        _metrics,
    )

    policy = _metric_policy()
    run = _manual_run(policy)
    catalog = _catalog(tmp_path, range(2))
    # Rebind the generic catalog fixture to the real run lineage.
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory=catalog.root_directory,
        checkpoints=tuple(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run.content_digest,
                candidate_id=value.candidate_id,
                epoch=value.epoch,
                relative_path=value.relative_path,
                sha256=value.sha256,
                size_bytes=value.size_bytes,
            )
            for value in catalog.checkpoints
        ),
        pattern=catalog.pattern,
    )
    metrics = tuple(
        _metrics(run, checkpoint, force=0.20, replay=0.50)
        for checkpoint in catalog.checkpoints
    )
    shortlist = campaign_cli._CheckpointShortlist(
        catalog=catalog,
        original_catalog_digest="b" * 64,
        original_count=30,
        selected_epochs=tuple(value.epoch for value in catalog.checkpoints),
        reasons_by_epoch=tuple((value.epoch, ("test",)) for value in catalog.checkpoints),
        history_files=(),
        used_training_history=True,
    )
    selection, failure = campaign_cli._checkpoint_selection_or_failure(
        run, shortlist, catalog, metrics, policy
    )
    assert selection is None
    assert failure is not None
    assert failure["bounded_shortlist"] is True
    assert failure["evaluated_checkpoint_count"] == 2
    assert failure["available_checkpoint_count"] == 30
    assert failure["reason_counts"]["replay_retention_threshold_exceeded"] == 2
    assert "2/30 shortlisted checkpoints" in campaign_cli._format_checkpoint_selection_failure(failure)


def test_core_selection_error_reports_rejection_reasons(tmp_path: Path) -> None:
    from tests.test_mlff_data9b1_campaign_checkpoint_control import (
        _manual_run,
        _metric_policy,
        _metrics,
    )

    policy = _metric_policy()
    run = _manual_run(policy)
    for epoch in range(2):
        (tmp_path / f"model_epoch-{epoch}.pt").write_bytes(str(epoch).encode())
    catalog = mdstats.inventory_mace_checkpoints(run, tmp_path)
    metrics = tuple(
        _metrics(run, checkpoint, force=0.20, replay=0.50)
        for checkpoint in catalog.checkpoints
    )
    import pytest
    with pytest.raises(mdstats.TrainingDataInputError) as error:
        mdstats.select_checkpoint(run, catalog, metrics, policy)
    message = str(error.value)
    assert "focus_force_rmse_threshold_exceeded=2" in message
    assert "replay_retention_threshold_exceeded=2" in message
