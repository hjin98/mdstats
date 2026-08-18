from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import digest


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _probe() -> tuple[mdstats.MaceCompatibilityPolicy, mdstats.MaceSourceProbe]:
    policy = mdstats.MaceCompatibilityPolicy()
    probe = mdstats.MaceSourceProbe(
        policy_digest=policy.policy_digest,
        run_train_sha256=_h("run_train"),
        train_sha256=_h("train"),
        multihead_sha256=_h("multihead"),
        pt_head_sorted_first=True,
        target_validation_head_is_last=True,
        native_checkpoint_uses_last_validation_head=True,
        implicit_target_duplication_present=True,
        dry_run_supported=True,
        save_all_checkpoints_supported=True,
        fixed_file_adapter_supported=True,
    )
    return policy, probe


def _replay_artifact(name: str, geom: str) -> mdstats.ReplayFileArtifact:
    return mdstats.ReplayFileArtifact(
        path=f"/{name}.xyz",
        sha256=_h(name),
        configuration_count=1,
        atomic_numbers=(3, 8),
        geometry_identities=(_h(geom),),
        label_identities=(_h(f"label-{name}"),),
        energy_key="REF_energy",
        forces_key="REF_forces",
        stress_key="REF_stress",
        stress_present_count=1,
    )


def _replay_plan() -> mdstats.ReplayPreparationPlan:
    return mdstats.ReplayPreparationPlan(
        mode=mdstats.ReplayMode.PRESELECTED,
        train_artifact=_replay_artifact("replay-train", "geom-train"),
        monitor_artifact=_replay_artifact("replay-monitor", "geom-monitor"),
        head_weight=1.0,
        target_weight=5.0,
    )


def _job(
    *,
    probe: mdstats.MaceSourceProbe,
    replay: mdstats.ReplayPreparationPlan,
    mode: mdstats.TrainingMode,
    size: int,
    seed: int,
    fold: int | None,
    metric_policy: mdstats.CheckpointMetricPolicy,
) -> mdstats.MaceJobArtifact:
    kind = (
        mdstats.MaceJobKind.FINAL_DEVELOPMENT
        if fold is None
        else mdstats.MaceJobKind.CROSS_VALIDATION_FOLD
    )
    suffix = "final" if fold is None else f"fold-{fold}"
    replay_digest = None if mode is mdstats.TrainingMode.NAIVE_FINE_TUNING else replay.content_digest
    protocol = mdstats.TrainingProtocolIdentity(
        training_mode=mode,
        foundation_checkpoint=mdstats.FoundationCheckpointIdentity(
            reference="/foundation.model",
            sha256=_h("foundation"),
        ),
        compatibility_probe_digest=probe.content_digest,
        data7_bundle_digest=_h(f"data7-{mode.value}-{size}-{seed}-{suffix}"),
        target_train_artifact_digest=_h(f"train-{mode.value}-{size}-{seed}-{suffix}"),
        target_valid_artifact_digest=_h(f"valid-{mode.value}-{size}-{seed}-{suffix}"),
        replay_plan_digest=replay_digest,
        training_objective_policy_digest=_h("objective"),
        configuration_weight_policy_digest=_h("configuration-weight"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cpu",
            default_dtype="float32",
            seed=seed,
            max_num_epochs=3,
        ),
        selection_size=size,
        real_pt_data_ratio_threshold=0.0,
    )
    has_replay = mode is mdstats.TrainingMode.MULTIHEAD_REPLAY
    dry_run = mdstats.MaceLoaderDryRun(
        compatibility_probe_digest=probe.content_digest,
        exposure_backend=mdstats.MaceExposureBackend.NATIVE_MACE_FIXED,
        target_head_name="target_head",
        replay_head_name="pt_head" if has_replay else None,
        head_order=("pt_head", "target_head") if has_replay else ("target_head",),
        validation_head_order=("pt_head", "target_head") if has_replay else ("target_head",),
        native_checkpoint_head="target_head",
        target_train_count_exported=size,
        target_train_count_effective=size,
        replay_train_count_exported=1 if has_replay else 0,
        replay_train_count_effective=1 if has_replay else 0,
        real_pt_data_ratio_threshold=0.0,
        implicit_target_duplication_factor=1,
        target_validation_count=2,
        replay_validation_count=1 if has_replay else 0,
        dry_run_command=("mdstats-mace-train", "--config", "mace_config.yaml", "--dry_run"),
    )
    return mdstats.MaceJobArtifact(
        job_id=f"{mode.value}-{size}-{seed}-{suffix}",
        kind=kind,
        fold_index=fold,
        relative_directory=f"jobs/{mode.value}/{size}/{seed}/{suffix}",
        config_relative_path=f"jobs/{mode.value}/{size}/{seed}/{suffix}/mace_config.yaml",
        config_sha256=_h(f"config-{mode.value}-{size}-{seed}-{suffix}"),
        command_relative_path=f"jobs/{mode.value}/{size}/{seed}/{suffix}/run_mace.sh",
        command_sha256=_h(f"command-{mode.value}-{size}-{seed}-{suffix}"),
        target_train_artifact_digest=protocol.target_train_artifact_digest,
        target_valid_artifact_digest=protocol.target_valid_artifact_digest,
        fold_evaluation_artifact_digest=None if fold is None else _h(f"eval-{mode.value}-{size}-{seed}-{fold}"),
        replay_plan_digest=replay_digest,
        protocol=protocol,
        loader_dry_run=dry_run,
    )


def _bundle(
    *,
    mode: mdstats.TrainingMode,
    size: int,
    seed: int,
    metric_policy: mdstats.CheckpointMetricPolicy,
) -> mdstats.Data8PreparationBundle:
    compatibility, probe = _probe()
    replay = _replay_plan() if mode is mdstats.TrainingMode.MULTIHEAD_REPLAY else mdstats.ReplayPreparationPlan(mode=mdstats.ReplayMode.NONE)
    jobs = tuple(
        _job(
            probe=probe,
            replay=replay,
            mode=mode,
            size=size,
            seed=seed,
            fold=fold,
            metric_policy=metric_policy,
        )
        for fold in (None, 0, 1, 2)
    )
    return mdstats.Data8PreparationBundle(
        dataset_id="lta-production",
        source_catalog_digest=_h("source-catalog"),
        frame_catalog_digest=_h("frame-catalog"),
        data5_bundle_digest=_h("data5"),
        compatibility_policy=compatibility,
        compatibility_probe=probe,
        replay_plan=replay,
        jobs=jobs,
        target_artifacts=(),
        fold_evaluation_artifacts=(),
        sealed_outer_evaluations=(),
        output_directory="/data8",
    )


def _qualification(anchor: mdstats.Data8PreparationBundle, *, passed: bool = True) -> mdstats.ProductionCorpusQualificationRecord:
    return mdstats.ProductionCorpusQualificationRecord(
        production_plan_digest=_h("production-plan"),
        dataset_id="lta-production",
        expected_source_count=27,
        source_count=27,
        total_frame_count=37632,
        normalization_manifest_digest=_h("normalization"),
        reference_manifest_digest=_h("reference"),
        run_evidence_digest=_h("run-evidence"),
        source_catalog_digest=anchor.source_catalog_digest,
        frame_catalog_digest=anchor.frame_catalog_digest,
        data4_bundle_digest=_h("data4"),
        data5_bundle_digest=anchor.data5_bundle_digest,
        data6_bundle_digest=_h("data6"),
        data7_bundle_digests=tuple(_h(f"data7-{i}") for i in range(4)),
        data8_bundle_digest=anchor.content_digest,
        eligible_frame_count=37632,
        degraded_frame_count=0,
        rejected_frame_count=0,
        unresolved_strain_frame_count=0,
        duplicate_geometry_group_count=0,
        duplicate_labeled_group_count=0,
        composition_formulas=("Al24Li12Na12O96Si24",),
        target_temperatures_kelvin=(300.0, 700.0, 800.0),
        ensembles=("NVT",),
        strain_class_counts=(("unstrained", 1),),
        feasibility_outcomes=(("fully_supported", 1),),
        independence_grade_counts=(("trajectory_block", 1),),
        event_type_counts=(),
        partition_unit_count=12,
        condition_count=27,
        cross_validation_fold_count=3,
        leakage_audit_passed=True,
        profile_extension_coverage_materialized=True,
        foundation_features_materialized=True,
        foundation_residual_e0_materialized=True,
        data8_artifacts_materialized=True,
        replay_corpus_bound=True,
        target_corpus_qualified=True,
        full_data9a_passed=passed,
        status=mdstats.ProductionGateStatus.PASSED if passed else mdstats.ProductionGateStatus.CONDITIONALLY_READY,
        blockers=() if passed else ("production_replay_corpus_not_bound",),
        warnings=(),
    )


def _metric_policy() -> mdstats.CheckpointMetricPolicy:
    return mdstats.CheckpointMetricPolicy(
        primary_metric="target_force_component_rmse",
        focus_atomic_numbers=(3, 11, 19),
        maximum_energy_mae_ev_per_atom=0.005,
        maximum_focus_force_rmse_ev_per_angstrom=0.10,
        maximum_stress_rmse_ev_per_angstrom3=0.02,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.15,
        maximum_replay_degradation_fraction=0.20,
    )


def test_campaign_plan_requires_passed_gate_and_complete_matrix() -> None:
    metric_policy = _metric_policy()
    replay = _bundle(mode=mdstats.TrainingMode.MULTIHEAD_REPLAY, size=512, seed=1, metric_policy=metric_policy)
    naive = _bundle(mode=mdstats.TrainingMode.NAIVE_FINE_TUNING, size=512, seed=1, metric_policy=metric_policy)
    policy = mdstats.TrainingCampaignPolicy(
        required_training_modes=(mdstats.TrainingMode.NAIVE_FINE_TUNING, mdstats.TrainingMode.MULTIHEAD_REPLAY),
        required_selection_sizes=(512,),
        required_seeds=(1,),
    )
    plan = mdstats.build_training_campaign_plan(
        _qualification(replay),
        (replay, naive),
        campaign_id="lta-data9b1",
        policy=policy,
    )
    assert len(plan.runs) == 8
    assert len({v.protocol_family_digest for v in plan.runs}) == 2
    assert mdstats.TrainingCampaignPlan.from_dict(plan.to_dict()) == plan

    # Records written before method-specific seed/fold configuration used the
    # v2 policy payload.  Loading that policy into the current v3 object changes
    # the newly computed plan digest, but the exact serialized legacy payload
    # must remain acceptable after its own digest and every nested digest pass.
    legacy_payload = deepcopy(plan.to_dict())
    legacy_policy = dict(legacy_payload["policy"])
    legacy_policy["schema"] = "mdstats.training-campaign-policy.v2"
    legacy_policy.pop("required_variants", None)
    legacy_policy.pop("policy_digest", None)
    legacy_policy["policy_digest"] = digest(legacy_policy)
    legacy_payload["policy"] = legacy_policy
    legacy_payload.pop("content_digest", None)
    legacy_payload["content_digest"] = digest(legacy_payload)

    migrated = mdstats.TrainingCampaignPlan.from_dict(legacy_payload)
    assert migrated.runs == plan.runs
    assert migrated.policy.required_variants == ()
    assert migrated.content_digest != legacy_payload["content_digest"]

    tampered = deepcopy(legacy_payload)
    tampered["campaign_id"] = "tampered-campaign"
    with pytest.raises(
        mdstats.TrainingDataSerializationError,
        match="Training-campaign plan digest mismatch",
    ):
        mdstats.TrainingCampaignPlan.from_dict(tampered)

    with pytest.raises(mdstats.TrainingDataInputError, match="passed full DATA9A"):
        mdstats.build_training_campaign_plan(
            _qualification(replay, passed=False),
            (replay, naive),
            campaign_id="blocked",
            policy=policy,
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="matrix"):
        mdstats.build_training_campaign_plan(
            _qualification(replay),
            (replay,),
            campaign_id="missing-naive",
            policy=policy,
        )


def test_campaign_plan_rejects_missing_fold_and_raw_wrapper() -> None:
    metric_policy = _metric_policy()
    replay = _bundle(mode=mdstats.TrainingMode.MULTIHEAD_REPLAY, size=512, seed=1, metric_policy=metric_policy)
    truncated = mdstats.Data8PreparationBundle(
        dataset_id=replay.dataset_id,
        source_catalog_digest=replay.source_catalog_digest,
        frame_catalog_digest=replay.frame_catalog_digest,
        data5_bundle_digest=replay.data5_bundle_digest,
        compatibility_policy=replay.compatibility_policy,
        compatibility_probe=replay.compatibility_probe,
        replay_plan=replay.replay_plan,
        jobs=tuple(v for v in replay.jobs if v.fold_index != 2),
        target_artifacts=(),
        fold_evaluation_artifacts=(),
        sealed_outer_evaluations=(),
        output_directory=replay.output_directory,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="fold coverage"):
        mdstats.build_training_campaign_plan(
            _qualification(truncated),
            (truncated,),
            campaign_id="truncated",
            policy=mdstats.TrainingCampaignPolicy(required_selection_sizes=(512,)),
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="precision-aware"):
        mdstats.TrainingCampaignPolicy(
            required_selection_sizes=(512,),
            required_execution_wrapper="mace_run_train",
        )


def _manual_run(metric_policy: mdstats.CheckpointMetricPolicy) -> mdstats.TrainingCampaignRunPlan:
    return mdstats.TrainingCampaignRunPlan(
        run_id="replay-512-seed1-final",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=_h("job"),
        job_id="job-final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        target_monitor_artifact_digest=_h("target-monitor"),
        replay_monitor_artifact_digest=_h("replay-monitor"),
        relative_output_directory="jobs/final",
    )


def test_checkpoint_inventory_is_content_addressed_and_contained(tmp_path: Path) -> None:
    run = _manual_run(_metric_policy())
    (tmp_path / "model_epoch-0.pt").write_bytes(b"checkpoint-zero")
    (tmp_path / "model_epoch-1.pt").write_bytes(b"checkpoint-one")
    catalog = mdstats.inventory_mace_checkpoints(run, tmp_path)
    assert [v.epoch for v in catalog.checkpoints] == [0, 1]
    assert all(len(v.sha256) == 64 for v in catalog.checkpoints)
    assert mdstats.CandidateCheckpointCatalog.from_dict(catalog.to_dict()) == catalog

    duplicate = tmp_path / "copy_epoch-2.pt"
    duplicate.write_bytes(b"checkpoint-one")
    with pytest.raises(mdstats.TrainingDataInputError, match="duplicate file content"):
        mdstats.inventory_mace_checkpoints(run, tmp_path)


def _metrics(run: mdstats.TrainingCampaignRunPlan, checkpoint: mdstats.CheckpointFileRecord, *, force: float, replay: float, energy: float = 0.002) -> mdstats.CheckpointMetricRecord:
    return mdstats.CheckpointMetricRecord(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=checkpoint.sha256,
        target_monitor_artifact_digest=run.target_monitor_artifact_digest,
        energy_mae_ev_per_atom=energy,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("Li", force + 0.01), ("Na", force + 0.02), ("K", force + 0.03)),
        stress_rmse_ev_per_angstrom3=0.01,
        worst_condition_force_rmse_ev_per_angstrom=force + 0.04,
        target_combined_loss=force * 10.0,
        replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
        replay_baseline_metric=0.05,
        replay_candidate_metric=0.05 * (1.0 + replay),
        replay_degradation_fraction=replay,
    )


def test_checkpoint_constraints_and_deterministic_selection(tmp_path: Path) -> None:
    policy = _metric_policy()
    run = _manual_run(policy)
    for epoch, content in enumerate((b"a", b"b", b"c")):
        (tmp_path / f"model_epoch-{epoch}.pt").write_bytes(content)
    catalog = mdstats.inventory_mace_checkpoints(run, tmp_path)
    cp0, cp1, cp2 = catalog.checkpoints
    records = (
        _metrics(run, cp0, force=0.070, replay=0.10),
        _metrics(run, cp1, force=0.060, replay=0.25),  # rejected by replay
        _metrics(run, cp2, force=0.065, replay=0.12),
    )
    selection = mdstats.select_checkpoint(run, catalog, records, policy)
    assert selection.selected_checkpoint_sha256 == cp2.sha256
    rejected = next(v for v in selection.decisions if v.checkpoint_sha256 == cp1.sha256)
    assert rejected.outcome is mdstats.CheckpointAdmissibilityOutcome.REJECTED
    assert "replay_retention_threshold_exceeded" in rejected.rejection_reasons
    assert mdstats.CheckpointSelectionRecord.from_dict(selection.to_dict()) == selection

    tampered = deepcopy(selection.to_dict())
    tampered["selected_checkpoint_epoch"] = 99
    with pytest.raises((mdstats.TrainingDataSerializationError, mdstats.TrainingDataInputError)):
        mdstats.CheckpointSelectionRecord.from_dict(tampered)


def test_checkpoint_selection_requires_complete_metrics_and_one_admissible(tmp_path: Path) -> None:
    policy = _metric_policy()
    run = _manual_run(policy)
    (tmp_path / "model_epoch-0.pt").write_bytes(b"a")
    (tmp_path / "model_epoch-1.pt").write_bytes(b"b")
    catalog = mdstats.inventory_mace_checkpoints(run, tmp_path)
    cp0, cp1 = catalog.checkpoints
    with pytest.raises(mdstats.TrainingDataInputError, match="coverage"):
        mdstats.select_checkpoint(run, catalog, (_metrics(run, cp0, force=0.06, replay=0.1),), policy)
    rejected = (
        _metrics(run, cp0, force=0.20, replay=0.1),
        _metrics(run, cp1, force=0.06, replay=0.5),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="No candidate checkpoint"):
        mdstats.select_checkpoint(run, catalog, rejected, policy)


def test_metric_record_requires_complete_replay_evidence() -> None:
    run = _manual_run(_metric_policy())
    with pytest.raises(mdstats.TrainingDataInputError, match="complete"):
        mdstats.CheckpointMetricRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=_h("checkpoint"),
            target_monitor_artifact_digest=run.target_monitor_artifact_digest,
            energy_mae_ev_per_atom=0.001,
            force_component_rmse_ev_per_angstrom=0.05,
            replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
        )
