from __future__ import annotations

import hashlib

import mdstats


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _policy() -> mdstats.CheckpointMetricPolicy:
    return mdstats.CheckpointMetricPolicy(
        focus_atomic_numbers=(3, 19),
        maximum_energy_mae_ev_per_atom=0.005,
        maximum_focus_force_rmse_ev_per_angstrom=0.10,
        maximum_stress_rmse_ev_per_angstrom3=0.02,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.15,
        maximum_replay_degradation_fraction=0.20,
    )


def _run() -> mdstats.TrainingCampaignRunPlan:
    return mdstats.TrainingCampaignRunPlan(
        run_id="multihead-replay-test",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=_h("job"),
        job_id="fold-00",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=_policy().policy_digest,
        target_monitor_artifact_digest=_h("target"),
        replay_monitor_artifact_digest=_h("replay"),
        relative_output_directory="runs/test",
    )


def _checkpoint(
    run: mdstats.TrainingCampaignRunPlan, epoch: int, name: str
) -> mdstats.CheckpointFileRecord:
    return mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id=f"{run.run_id}:epoch-{epoch}",
        relative_path=f"checkpoints/{name}.pt",
        epoch=epoch,
        sha256=_h(name),
        size_bytes=100,
    )


def _metric(
    run: mdstats.TrainingCampaignRunPlan,
    checkpoint: mdstats.CheckpointFileRecord,
    *,
    force: float,
    replay: float,
    label_mode: mdstats.ReplayLabelMode | None,
    baseline: float = 0.000002013,
) -> mdstats.CheckpointMetricRecord:
    degradation = max(0.0, replay - baseline) / baseline
    if label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
        degradation = None
    return mdstats.CheckpointMetricRecord(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=checkpoint.sha256,
        target_monitor_artifact_digest=run.target_monitor_artifact_digest,
        energy_mae_ev_per_atom=0.0003,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("K", force), ("Li", force * 0.9)),
        stress_rmse_ev_per_angstrom3=0.0004,
        worst_condition_force_rmse_ev_per_angstrom=force,
        target_combined_loss=force,
        replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
        replay_baseline_metric=baseline,
        replay_candidate_metric=replay,
        replay_degradation_fraction=degradation,
        replay_label_mode=label_mode,
    )


def test_foundation_pseudolabel_replay_is_diagnostic_not_accuracy_gate() -> None:
    run = _run()
    checkpoint = _checkpoint(run, 29, "epoch29")
    legacy_metric = _metric(
        run,
        checkpoint,
        force=0.025017,
        replay=0.043439,
        label_mode=None,
    )
    evaluation = mdstats.CheckpointEvaluationRecord(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=checkpoint.sha256,
        evaluation_policy_digest=_h("evaluation-policy"),
        target_monitor_artifact_digest=run.target_monitor_artifact_digest,
        target_monitor_sha256=_h("target-bytes"),
        replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
        replay_monitor_sha256=_h("replay-bytes"),
        candidate_model_path="checkpoint.pt",
        candidate_model_sha256=checkpoint.sha256,
        replay_baseline_model_path="foundation.model",
        replay_baseline_model_sha256=_h("foundation"),
        target_configuration_count=10,
        replay_configuration_count=10,
        condition_force_rmse_ev_per_angstrom=(("condition", 0.025017),),
        metric_record=legacy_metric,
    )

    rebound = mdstats.bind_checkpoint_evaluation_replay_provenance(
        evaluation, mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    )
    metric = rebound.metric_record
    assert metric.replay_label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert metric.replay_degradation_fraction is None
    assert metric.replay_candidate_metric == 0.043439
    decision = mdstats.assess_checkpoint_admissibility(run, checkpoint, metric, _policy())
    assert decision.outcome is mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE
    assert decision.rejection_reasons == ()


def test_true_dft_replay_still_enforces_true_label_retention_gate() -> None:
    run = _run()
    checkpoint = _checkpoint(run, 29, "epoch29-true")
    metric = _metric(
        run,
        checkpoint,
        force=0.025,
        replay=0.043,
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    decision = mdstats.assess_checkpoint_admissibility(run, checkpoint, metric, _policy())
    assert decision.outcome is mdstats.CheckpointAdmissibilityOutcome.REJECTED
    assert decision.rejection_reasons == ("replay_retention_threshold_exceeded",)


def test_pseudolabel_foundation_self_mismatch_is_a_provenance_failure() -> None:
    run = _run()
    checkpoint = _checkpoint(run, 1, "bad-foundation")
    metric = _metric(
        run,
        checkpoint,
        force=0.025,
        replay=0.03,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        baseline=0.002,
    )
    decision = mdstats.assess_checkpoint_admissibility(run, checkpoint, metric, _policy())
    assert decision.rejection_reasons == ("pseudolabel_foundation_self_mismatch",)


def test_checkpoint_ranking_uses_dft_target_metric_not_pseudolabel_disagreement() -> None:
    run = _run()
    c0 = _checkpoint(run, 0, "epoch0")
    c1 = _checkpoint(run, 29, "epoch29")
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory="/tmp",
        checkpoints=(c0, c1),
        pattern="*.pt",
    )
    selection = mdstats.select_checkpoint(
        run,
        catalog,
        (
            _metric(
                run,
                c0,
                force=0.035,
                replay=0.005,
                label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
            ),
            _metric(
                run,
                c1,
                force=0.025,
                replay=0.050,
                label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
            ),
        ),
        _policy(),
    )
    assert selection.selected_checkpoint_sha256 == c1.sha256
    assert selection.selected_checkpoint_epoch == 29


def test_legacy_cached_evaluation_migrates_without_reinference() -> None:
    from mdstats.training_data._common import digest

    run = _run()
    checkpoint = _checkpoint(run, 29, "legacy-epoch29")
    metric = _metric(
        run,
        checkpoint,
        force=0.025017,
        replay=0.043439,
        label_mode=None,
    )
    metric_payload = metric.to_dict()
    metric_payload["schema"] = "mdstats.checkpoint-metric-record.v1"
    metric_payload.pop("replay_label_mode", None)
    metric_payload.pop("content_digest", None)
    metric_payload["content_digest"] = digest(metric_payload)

    payload = {
        "schema": "mdstats.checkpoint-evaluation-record.v1",
        "run_plan_digest": run.content_digest,
        "checkpoint_sha256": checkpoint.sha256,
        "evaluation_policy_digest": _h("evaluation-policy"),
        "target_monitor_artifact_digest": run.target_monitor_artifact_digest,
        "target_monitor_sha256": _h("target-bytes"),
        "replay_monitor_artifact_digest": run.replay_monitor_artifact_digest,
        "replay_monitor_sha256": _h("replay-bytes"),
        "candidate_model_path": "checkpoint.pt",
        "candidate_model_sha256": checkpoint.sha256,
        "replay_baseline_model_path": "foundation.model",
        "replay_baseline_model_sha256": _h("foundation"),
        "target_configuration_count": 10,
        "replay_configuration_count": 10,
        "condition_force_rmse_ev_per_angstrom": {"condition": 0.025017},
        "metric_record": metric_payload,
    }
    payload["content_digest"] = digest(payload)

    restored = mdstats.CheckpointEvaluationRecord.from_dict(payload)
    assert restored.metric_record.replay_label_mode is None
    rebound = mdstats.bind_checkpoint_evaluation_replay_provenance(
        restored, mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    )
    assert rebound.metric_record.replay_degradation_fraction is None
    assert rebound.metric_record.replay_candidate_metric == 0.043439


def test_true_label_override_cached_record_rebinds_training_lineage_without_reinference() -> None:
    """0.20.95 records may carry TRUE_DFT digest in both outer and metric fields.

    Restart reconciliation must keep the outer evaluation artifact identity while
    rebinding admissibility to the frozen training replay lineage.
    """

    from dataclasses import replace

    run = _run()
    checkpoint = _checkpoint(run, 7, "true-label-override")
    true_label_digest = _h("true-dft-replay-monitor")
    metric = replace(
        _metric(
            run,
            checkpoint,
            force=0.025,
            replay=0.0000021,
            label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
            baseline=0.0000020,
        ),
        replay_monitor_artifact_digest=true_label_digest,
        evaluation_notes=("replay_labels:evaluation_true_dft_override",),
    )
    stale_02095 = mdstats.CheckpointEvaluationRecord(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=checkpoint.sha256,
        evaluation_policy_digest=_h("evaluation-policy"),
        target_monitor_artifact_digest=run.target_monitor_artifact_digest,
        target_monitor_sha256=_h("target-bytes"),
        replay_monitor_artifact_digest=true_label_digest,
        replay_monitor_sha256=_h("true-replay-bytes"),
        candidate_model_path="checkpoint.pt",
        candidate_model_sha256=checkpoint.sha256,
        replay_baseline_model_path="foundation.model",
        replay_baseline_model_sha256=_h("foundation"),
        target_configuration_count=10,
        replay_configuration_count=10,
        condition_force_rmse_ev_per_angstrom=(("condition", 0.025),),
        metric_record=metric,
    )

    # Exercise durable restart serialization rather than only an in-memory replace.
    restored = mdstats.CheckpointEvaluationRecord.from_dict(stale_02095.to_dict())
    rebound = mdstats.bind_checkpoint_evaluation_replay_provenance(
        restored,
        mdstats.ReplayLabelMode.TRUE_DFT,
        training_replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
    )

    assert rebound.replay_monitor_artifact_digest == true_label_digest
    assert rebound.metric_record.replay_monitor_artifact_digest == run.replay_monitor_artifact_digest
    decision = mdstats.assess_checkpoint_admissibility(
        run, checkpoint, rebound.metric_record, _policy()
    )
    assert decision.outcome is mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE
