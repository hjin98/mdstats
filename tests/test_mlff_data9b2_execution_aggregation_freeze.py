from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli, campaign_execution
from mdstats.training_data._common import digest


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _metric_policy() -> mdstats.CheckpointMetricPolicy:
    return mdstats.CheckpointMetricPolicy(
        primary_metric="target_force_component_rmse",
        focus_atomic_numbers=(3, 11, 19),
        maximum_energy_mae_ev_per_atom=0.01,
        maximum_focus_force_rmse_ev_per_angstrom=0.2,
        maximum_stress_rmse_ev_per_angstrom3=0.1,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.3,
        maximum_replay_degradation_fraction=0.5,
    )


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


def _job(tmp_path: Path) -> tuple[mdstats.MaceJobArtifact, mdstats.TrainingCampaignRunPlan, Path]:
    compatibility, probe = _probe()
    config = tmp_path / "job" / "mace_config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("name: fake\n", encoding="utf-8")
    protocol = mdstats.TrainingProtocolIdentity(
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        foundation_checkpoint=mdstats.FoundationCheckpointIdentity(
            reference="/foundation.model", sha256=_h("foundation")
        ),
        compatibility_probe_digest=probe.content_digest,
        data7_bundle_digest=_h("data7"),
        target_train_artifact_digest=_h("train"),
        target_valid_artifact_digest=_h("valid"),
        replay_plan_digest=None,
        training_objective_policy_digest=_h("objective"),
        configuration_weight_policy_digest=_h("weights"),
        checkpoint_metric_policy_digest=_metric_policy().policy_digest,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cpu", default_dtype="float32", seed=1, max_num_epochs=2
        ),
        selection_size=4,
        real_pt_data_ratio_threshold=0.0,
    )
    dry = mdstats.MaceLoaderDryRun(
        compatibility_probe_digest=probe.content_digest,
        exposure_backend=mdstats.MaceExposureBackend.NATIVE_MACE_FIXED,
        target_head_name="target_head",
        replay_head_name=None,
        head_order=("target_head",),
        validation_head_order=("target_head",),
        native_checkpoint_head="target_head",
        target_train_count_exported=4,
        target_train_count_effective=4,
        replay_train_count_exported=0,
        replay_train_count_effective=0,
        real_pt_data_ratio_threshold=0.0,
        implicit_target_duplication_factor=1,
        target_validation_count=2,
        replay_validation_count=0,
        dry_run_command=("mdstats-mace-train", "--config", "mace_config.yaml", "--dry_run"),
    )
    job = mdstats.MaceJobArtifact(
        job_id="fake-final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        relative_directory="job",
        config_relative_path="job/mace_config.yaml",
        config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        command_relative_path="job/run.sh",
        command_sha256=_h("command"),
        target_train_artifact_digest=protocol.target_train_artifact_digest,
        target_valid_artifact_digest=protocol.target_valid_artifact_digest,
        fold_evaluation_artifact_digest=None,
        replay_plan_digest=None,
        protocol=protocol,
        loader_dry_run=dry,
    )
    run = mdstats.TrainingCampaignRunPlan(
        run_id="fake-final",
        data8_bundle_digest=_h("data8"),
        mace_job_artifact_digest=job.content_digest,
        job_id=job.job_id,
        kind=job.kind,
        fold_index=None,
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        selection_size=4,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=protocol.content_digest,
        checkpoint_metric_policy_digest=_metric_policy().policy_digest,
        target_monitor_artifact_digest=_h("target-monitor"),
        replay_monitor_artifact_digest=None,
        relative_output_directory="job",
    )
    return job, run, config


def test_supervised_execution_retries_and_inventories(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "if [ ! -f first_failed ]; then touch first_failed; echo fail >&2; exit 3; fi\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-1.pt\"\n"
        "echo success\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    policy = mdstats.TrainingExecutionPolicy(max_attempts=2, checkpoint_glob="*epoch*.pt")
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=policy,
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
    )
    assert record.state is mdstats.TrainingRunState.SUCCEEDED
    assert len(record.attempts) == 2
    assert record.attempts[0].state is mdstats.TrainingRunState.FAILED
    assert "--restart_latest" not in record.attempts[1].command
    assert Path(record.attempts[0].working_directory) == (tmp_path / "job").resolve()
    assert "--model_dir" in record.attempts[0].command
    assert str((output / "models").resolve()) in record.attempts[0].command
    assert "--checkpoints_dir" in record.attempts[0].command
    assert str(checkpoints.resolve()) in record.attempts[0].command
    assert record.checkpoint_catalog.checkpoints[0].epoch == 1
    assert mdstats.TrainingRunExecutionRecord.from_dict(record.to_dict()) == record
    assert (output / "training_execution.json").is_file()

def test_supervised_execution_restarts_only_when_checkpoint_exists(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "if [ ! -f first_failed ]; then "
        "touch first_failed; printf partial > \"$CHECKPOINT_DIR/model_epoch-0.pt\"; exit 3; fi\n"
        "case \" $* \" in *\" --restart_latest \"*) ;; *) exit 9 ;; esac\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-1.pt\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=mdstats.TrainingExecutionPolicy(max_attempts=2, checkpoint_glob="*epoch*.pt"),
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
    )
    assert record.state is mdstats.TrainingRunState.SUCCEEDED
    assert "--restart_latest" in record.attempts[1].command




def test_interruption_preserves_checkpoint_and_does_not_consume_retry_budget(tmp_path: Path) -> None:
    import threading
    import time

    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "case \" $* \" in *\" --restart_latest \"*) "
        "printf final > \"$CHECKPOINT_DIR/model_epoch-1.pt\"; exit 0 ;; esac\n"
        "printf partial > \"$CHECKPOINT_DIR/model_epoch-0.pt\"\n"
        "while true; do sleep 1; done\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    stop = threading.Event()
    threading.Timer(0.2, stop.set).start()
    policy = mdstats.TrainingExecutionPolicy(
        max_attempts=1, checkpoint_glob="*epoch*.pt", terminate_grace_seconds=1.0
    )
    interrupted = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=policy,
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        progress_interval_seconds=0.05,
        stop_requested=stop.is_set,
    )
    assert interrupted.state is mdstats.TrainingRunState.INTERRUPTED
    assert len(interrupted.attempts) == 1
    assert (checkpoints / "model_epoch-0.pt").is_file()
    assert not (output / "active_process.json").exists()

    resumed = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=policy,
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        prior_record=interrupted,
    )
    assert resumed.state is mdstats.TrainingRunState.SUCCEEDED
    assert len(resumed.attempts) == 2
    assert "--restart_latest" in resumed.attempts[-1].command


def test_training_execution_policy_reads_legacy_v1_payload() -> None:
    policy = mdstats.TrainingExecutionPolicy()
    payload = policy.to_dict()
    payload["schema"] = "mdstats.training-execution-policy.v1"
    payload.pop("runtime_layout_version")
    body = {key: value for key, value in payload.items() if key != "policy_digest"}
    payload["policy_digest"] = digest(body)
    restored = mdstats.TrainingExecutionPolicy.from_dict(payload)
    assert restored.runtime_layout_version == "legacy-run-cwd.v1"


def _manual_run(*, mode: mdstats.TrainingMode, family: str, seed: int, fold: int | None, value: int) -> mdstats.TrainingCampaignRunPlan:
    return mdstats.TrainingCampaignRunPlan(
        run_id=f"{mode.value}-{seed}-{fold}",
        data8_bundle_digest=_h(f"data8-{value}"),
        mace_job_artifact_digest=_h(f"job-{value}"),
        job_id=f"job-{value}",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT if fold is None else mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=fold,
        training_mode=mode,
        selection_size=512,
        seed=seed,
        protocol_family_digest=_h(family),
        protocol_variant_digest=_h(f"{family}-{seed}"),
        protocol_digest=_h(f"protocol-{value}"),
        checkpoint_metric_policy_digest=_metric_policy().policy_digest,
        target_monitor_artifact_digest=_h(f"target-{value}"),
        replay_monitor_artifact_digest=None if mode is mdstats.TrainingMode.NAIVE_FINE_TUNING else _h("replay-monitor"),
        relative_output_directory=f"runs/{value}",
    )


def _qualification(anchor: str) -> mdstats.ProductionCorpusQualificationRecord:
    return mdstats.ProductionCorpusQualificationRecord(
        production_plan_digest=_h("production-plan"),
        dataset_id="lta-production",
        expected_source_count=27,
        source_count=27,
        total_frame_count=37632,
        normalization_manifest_digest=_h("normalization"),
        reference_manifest_digest=_h("reference"),
        run_evidence_digest=_h("run-evidence"),
        source_catalog_digest=_h("source-catalog"),
        frame_catalog_digest=_h("frame-catalog"),
        data4_bundle_digest=_h("data4"),
        data5_bundle_digest=_h("data5"),
        data6_bundle_digest=_h("data6"),
        data7_bundle_digests=tuple(_h(f"data7-{i}") for i in range(4)),
        data8_bundle_digest=anchor,
        eligible_frame_count=37632,
        degraded_frame_count=0,
        rejected_frame_count=0,
        unresolved_strain_frame_count=0,
        duplicate_geometry_group_count=0,
        duplicate_labeled_group_count=0,
        composition_formulas=("AlNaO4Si",),
        target_temperatures_kelvin=(300.0, 700.0, 800.0),
        ensembles=("NVT",),
        strain_class_counts=(("unstrained", 21), ("strained", 6)),
        feasibility_outcomes=(("fully_supported", 1),),
        independence_grade_counts=(("trajectory_block", 1),),
        event_type_counts=(),
        partition_unit_count=12,
        condition_count=27,
        cross_validation_fold_count=2,
        leakage_audit_passed=True,
        profile_extension_coverage_materialized=True,
        foundation_features_materialized=True,
        foundation_residual_e0_materialized=True,
        data8_artifacts_materialized=True,
        replay_corpus_bound=True,
        target_corpus_qualified=True,
        full_data9a_passed=True,
        status=mdstats.ProductionGateStatus.PASSED,
        blockers=(),
        warnings=(),
    )


def _decision_and_metric(run: mdstats.TrainingCampaignRunPlan, metric_value: float, epoch: int = 1):
    sha = _h(f"checkpoint-{run.run_id}")
    metric = mdstats.CheckpointMetricRecord(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=sha,
        target_monitor_artifact_digest=run.target_monitor_artifact_digest,
        energy_mae_ev_per_atom=0.002,
        force_component_rmse_ev_per_angstrom=metric_value,
        focus_force_rmse_ev_per_angstrom=(("Li", metric_value),),
        stress_rmse_ev_per_angstrom3=0.01,
        worst_condition_force_rmse_ev_per_angstrom=metric_value + 0.01,
        target_combined_loss=metric_value,
        replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
        replay_baseline_metric=None if run.replay_monitor_artifact_digest is None else 0.05,
        replay_candidate_metric=None if run.replay_monitor_artifact_digest is None else 0.055,
        replay_degradation_fraction=None if run.replay_monitor_artifact_digest is None else 0.1,
    )
    decision = mdstats.CheckpointAdmissibilityDecision(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=sha,
        checkpoint_metric_record_digest=metric.content_digest,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        outcome=mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE,
        primary_metric_name="target_force_component_rmse",
        primary_metric_value=metric_value,
    )
    selection = mdstats.CheckpointSelectionRecord(
        run_plan_digest=run.content_digest,
        checkpoint_catalog_digest=_h(f"catalog-{run.run_id}"),
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        decisions=(decision,),
        selected_checkpoint_sha256=sha,
        selected_checkpoint_epoch=epoch,
        selected_primary_metric_value=metric_value,
    )
    return selection, metric


def _campaign_and_evidence():
    runs = []
    counter = 0
    for mode, family, base in (
        (mdstats.TrainingMode.NAIVE_FINE_TUNING, "naive-family", 0.08),
        (mdstats.TrainingMode.MULTIHEAD_REPLAY, "replay-family", 0.06),
    ):
        for seed in (1, 2):
            for fold in (0, 1, None):
                counter += 1
                runs.append(_manual_run(mode=mode, family=family, seed=seed, fold=fold, value=counter))
    bundles = tuple(sorted({v.data8_bundle_digest for v in runs}))
    qualification = _qualification(bundles[0])
    campaign = mdstats.TrainingCampaignPlan(
        campaign_id="data9b2",
        dataset_id="lta-production",
        production_qualification_digest=qualification.content_digest,
        production_plan_digest=qualification.production_plan_digest,
        qualified_anchor_data8_bundle_digest=bundles[0],
        policy=mdstats.TrainingCampaignPolicy(
            required_seeds=(1, 2),
            required_training_modes=(mdstats.TrainingMode.NAIVE_FINE_TUNING, mdstats.TrainingMode.MULTIHEAD_REPLAY),
            required_selection_sizes=(512,),
        ),
        expected_cross_validation_fold_count=2,
        runs=tuple(runs),
        data8_bundle_digests=bundles,
    )
    selections = {}
    metrics = {}
    for run in campaign.runs:
        base = 0.08 if run.training_mode is mdstats.TrainingMode.NAIVE_FINE_TUNING else 0.06
        value = base + 0.002 * run.seed + (0.001 * (run.fold_index or 0))
        selection, metric = _decision_and_metric(run, value)
        selections[run.content_digest] = selection
        metrics[run.content_digest] = metric
    return qualification, campaign, selections, metrics


def test_aggregation_comparison_committee_freeze_and_activation() -> None:
    qualification, campaign, selections, metrics = _campaign_and_evidence()
    variants = []
    for variant in sorted({v.protocol_variant_digest for v in campaign.runs}):
        variants.append(
            mdstats.aggregate_protocol_variant(
                campaign, selections, metrics, protocol_variant_digest=variant
            )
        )
    families = []
    for family in sorted({v.protocol_family_digest for v in variants}):
        families.append(mdstats.aggregate_protocol_family([v for v in variants if v.protocol_family_digest == family]))
    comparison = mdstats.compare_protocol_families(families)
    assert comparison.selected_training_mode is mdstats.TrainingMode.MULTIHEAD_REPLAY
    selected_family = next(v for v in families if v.content_digest == comparison.selected_family_aggregate_digest)

    members = []
    final_selections = []
    for run in campaign.runs:
        if run.protocol_family_digest == comparison.selected_protocol_family_digest and run.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT:
            selection = selections[run.content_digest]
            final_selections.append(selection)
            members.append(
                mdstats.CommitteeMemberRecord(
                    protocol_family_digest=run.protocol_family_digest,
                    seed=run.seed,
                    final_run_plan_digest=run.content_digest,
                    checkpoint_selection_record_digest=selection.content_digest,
                    source_checkpoint_path=f"/checkpoints/{run.seed}.pt",
                    source_checkpoint_sha256=selection.selected_checkpoint_sha256,
                    target_head_name="target_head",
                    exported_model_path=f"/models/{run.seed}.model",
                    exported_model_sha256=_h(f"model-{run.seed}"),
                    byte_size=100 + run.seed,
                )
            )
    export_policy = mdstats.CommitteeExportPolicy(minimum_members=2)
    committee = mdstats.build_committee_identity(campaign, comparison, members, policy=export_policy)
    freeze = mdstats.freeze_training_protocol(
        qualification, campaign, comparison, selected_family, committee, final_selections
    )
    sealed = mdstats.SealedEvaluationArtifact(
        role="outer_locked_test",
        label_domain_id="vasp-pbe",
        frame_uids=(_h("locked-frame"),),
        frame_catalog_digest=qualification.frame_catalog_digest,
        data5_bundle_digest=qualification.data5_bundle_digest,
    )
    activation = mdstats.activate_sealed_evaluation(freeze, committee, (sealed,))
    assert activation.outcome is mdstats.EvaluationActivationOutcome.ACTIVATED
    assert mdstats.ProtocolFreezeRecord.from_dict(freeze.to_dict()) == freeze
    assert mdstats.CommitteeIdentity.from_dict(committee.to_dict()) == committee
    assert mdstats.EvaluationActivationDecision.from_dict(activation.to_dict()) == activation


def test_learning_curve_requires_unique_sizes() -> None:
    _, campaign, selections, metrics = _campaign_and_evidence()
    variants = [
        mdstats.aggregate_protocol_variant(campaign, selections, metrics, protocol_variant_digest=v)
        for v in sorted({r.protocol_variant_digest for r in campaign.runs})
    ]
    replay = mdstats.aggregate_protocol_family(
        [v for v in variants if v.training_mode is mdstats.TrainingMode.MULTIHEAD_REPLAY]
    )
    curve = mdstats.build_learning_curve((replay,), training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY)
    assert curve.selection_sizes == (512,)
    assert mdstats.LearningCurveRecord.from_dict(curve.to_dict()) == curve
    with pytest.raises(mdstats.TrainingDataInputError, match="duplicate selection"):
        mdstats.build_learning_curve((replay, replay), training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY)


def test_supervised_execution_timeout_persists_fail_closed_record(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "trap 'exit 0' TERM\n"
        "sleep 30 &\n"
        "wait\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=mdstats.TrainingExecutionPolicy(
            max_attempts=1,
            timeout_seconds=0.2,
            terminate_grace_seconds=0.2,
        ),
        wrapper_path=wrapper,
    )
    assert record.state is mdstats.TrainingRunState.TIMED_OUT
    assert record.attempts[0].failure_reason == "timeout"
    persisted = mdstats.TrainingRunExecutionRecord.from_dict(
        __import__("json").loads((output / "training_execution.json").read_text(encoding="utf-8"))
    )
    assert persisted == record


def test_checkpoint_evaluation_rejects_unbound_target_monitor(tmp_path: Path) -> None:
    _, run, _ = _job(tmp_path)
    model = tmp_path / "candidate.model"
    model.write_bytes(b"candidate")
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id="candidate:epoch-0",
        epoch=0,
        relative_path=model.name,
        sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
        size_bytes=model.stat().st_size,
    )
    target = tmp_path / "target.extxyz"
    target.write_text("unparsed-by-design\n", encoding="utf-8")
    artifact = mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=target.name,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        configuration_count=1,
        frame_uids=(_h("target-frame"),),
        atomic_numbers=(1,),
        policy_digest=_h("policy"),
        sidecar_relative_path="target.extxyz.manifest.json",
        sidecar_sha256=_h("sidecar-file"),
        sidecar_digest=_h("sidecar-record"),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="lineage"):
        mdstats.evaluate_mace_checkpoint(
            run,
            checkpoint,
            candidate_model_path=model,
            target_monitor_path=target,
            target_monitor_artifact=artifact,
        )


def test_supervised_execution_emits_periodic_heartbeat(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "sleep 0.18\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-1.pt\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    heartbeats: list[tuple[int, float]] = []
    checkpoints = tmp_path / "checkpoints"
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=tmp_path / "execution",
        checkpoint_directory=checkpoints,
        policy=mdstats.TrainingExecutionPolicy(max_attempts=1, checkpoint_glob="*epoch*.pt"),
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        progress_callback=lambda attempt, elapsed, stdout, stderr: heartbeats.append((attempt, elapsed)),
        progress_interval_seconds=0.05,
    )
    assert record.state is mdstats.TrainingRunState.SUCCEEDED
    assert heartbeats
    assert all(attempt == 1 and elapsed > 0.0 for attempt, elapsed in heartbeats)


def test_cancellation_polling_does_not_flood_visible_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "sleep 0.13\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-1.pt\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setattr(campaign_execution, "_CANCELLATION_POLL_SECONDS", 0.01)
    heartbeats: list[float] = []
    checkpoints = tmp_path / "checkpoints"
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=tmp_path / "execution",
        checkpoint_directory=checkpoints,
        policy=mdstats.TrainingExecutionPolicy(max_attempts=1, checkpoint_glob="*epoch*.pt"),
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        progress_callback=lambda _attempt, elapsed, _stdout, _stderr: heartbeats.append(elapsed),
        progress_interval_seconds=0.05,
        stop_requested=lambda: False,
    )
    assert record.state is mdstats.TrainingRunState.SUCCEEDED
    assert 1 <= len(heartbeats) <= 3
    assert all(
        later - earlier >= 0.04
        for earlier, later in zip(heartbeats, heartbeats[1:])
    )


def test_supervised_execution_resumes_checkpoint_after_unrecorded_interruption(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "case \" $* \" in *\" --restart_latest \"*) ;; *) exit 9 ;; esac\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-2.pt\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    # Simulate a child that wrote a checkpoint before the parent was killed and
    # therefore never committed a TrainingRunExecutionRecord.
    (checkpoints / "model_epoch-1.pt").write_text("partial", encoding="utf-8")
    record = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=mdstats.TrainingExecutionPolicy(max_attempts=2, checkpoint_glob="*epoch*.pt"),
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        prior_record=None,
    )
    assert record.state is mdstats.TrainingRunState.SUCCEEDED
    assert "--restart_latest" in record.attempts[0].command



def test_post_evaluate_cleanup_keeps_selected_checkpoint_and_full_metric_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    from types import SimpleNamespace
    import torch

    job, run, job_config = _job(tmp_path)
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay.xyz",
            replay_monitor="monitor.xyz",
        ),
        encoding="utf-8",
    )
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    run_root = paths.runs / run.run_id
    checkpoint_root = run_root / "checkpoints"
    checkpoint_root.mkdir(parents=True)
    models = run_root / "models"
    models.mkdir(parents=True)
    template = torch.nn.Linear(2, 1)
    torch.save(template, models / "fake.model")
    for epoch, delta in ((1, 0.1), (2, 0.2)):
        candidate = torch.nn.Linear(2, 1)
        with torch.no_grad():
            candidate.weight.add_(delta)
        torch.save(
            {
                "model": candidate.state_dict(),
                "optimizer": {
                    "state": {
                        0: {
                            "exp_avg": torch.ones(10000),
                            "exp_avg_sq": torch.ones(10000),
                        }
                    }
                },
                "lr_scheduler": {"last_epoch": epoch},
            },
            checkpoint_root / f"model_epoch-{epoch}.pt",
        )
    catalog = mdstats.inventory_mace_checkpoints(
        run, checkpoint_root, pattern="*epoch*.pt"
    )
    stdout = run_root / "attempt-01.stdout.log"
    stderr = run_root / "attempt-01.stderr.log"
    stdout.write_text("complete\n", encoding="utf-8")
    stderr.write_bytes(b"")
    policy = mdstats.TrainingExecutionPolicy(checkpoint_glob="*epoch*.pt")
    attempt = mdstats.TrainingRunAttemptRecord(
        run_plan_digest=run.content_digest,
        attempt_index=1,
        execution_policy_digest=policy.policy_digest,
        command=("mdstats-mace-train", "--config", "mace_config.yaml"),
        command_digest=digest(
            {
                "schema": "mdstats.training-command.v1",
                "argv": ["mdstats-mace-train", "--config", "mace_config.yaml"],
            }
        ),
        working_directory=str((tmp_path / "job").resolve()),
        config_sha256=job.config_sha256,
        environment_digest=_h("environment"),
        started_at_utc="2026-08-06T00:00:00Z",
        finished_at_utc="2026-08-06T01:00:00Z",
        elapsed_seconds=3600.0,
        state=mdstats.TrainingRunState.SUCCEEDED,
        return_code=0,
        stdout_relative_path=stdout.name,
        stdout_sha256=hashlib.sha256(stdout.read_bytes()).hexdigest(),
        stderr_relative_path=stderr.name,
        stderr_sha256=hashlib.sha256(stderr.read_bytes()).hexdigest(),
    )
    execution = mdstats.TrainingRunExecutionRecord(
        run_plan_digest=run.content_digest,
        mace_job_artifact_digest=job.content_digest,
        execution_policy_digest=policy.policy_digest,
        attempts=(attempt,),
        state=mdstats.TrainingRunState.SUCCEEDED,
        successful_attempt_index=1,
        checkpoint_catalog=catalog,
    )
    store.put_record(f"execution:{run.run_id}", execution)
    metrics = []
    for index, checkpoint in enumerate(catalog.checkpoints, start=1):
        metric = mdstats.CheckpointMetricRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=checkpoint.sha256,
            target_monitor_artifact_digest=run.target_monitor_artifact_digest,
            energy_mae_ev_per_atom=0.001,
            force_component_rmse_ev_per_angstrom=0.1 / index,
            focus_force_rmse_ev_per_angstrom=(("mobile", 0.1 / index),),
            stress_rmse_ev_per_angstrom3=0.01,
            worst_condition_force_rmse_ev_per_angstrom=0.1,
            target_combined_loss=0.1 / index,
        )
        metrics.append(metric)
        store.put_record(
            f"evaluation:{run.run_id}:{checkpoint.sha256}",
            {"schema": "cached-evaluation.v1", "checkpoint": checkpoint.sha256},
        )
    selection = mdstats.select_checkpoint(run, catalog, metrics, _metric_policy())
    store.put_record(f"selection:{run.run_id}", selection)

    monkeypatch.setattr(campaign_cli, "_current_data8_entries", lambda _store: ())
    monkeypatch.setattr(
        campaign_cli,
        "_job_lookup",
        lambda _entries: {job.content_digest: (None, job, tmp_path)},
    )

    report = campaign_cli._compact_evaluated_checkpoints(
        cfg,
        paths,
        store,
        SimpleNamespace(runs=(run,)),
    )
    assert report.reclaimed_bytes > 0
    retained = store.get_record(
        f"execution:{run.run_id}", mdstats.TrainingRunExecutionRecord
    )
    # STOR2 preserves the original scientific checkpoint catalog identity.
    assert len(retained.checkpoint_catalog.checkpoints) == 2
    assert retained.checkpoint_catalog.content_digest == catalog.content_digest
    assert len(list(checkpoint_root.glob("*.pt"))) == 1
    selected_record = next(
        item for item in catalog.checkpoints
        if item.sha256 == selection.selected_checkpoint_sha256
    )
    assert (checkpoint_root / selected_record.relative_path).is_file()
    nonselected = next(
        item for item in catalog.checkpoints
        if item.sha256 != selection.selected_checkpoint_sha256
    )
    capsule = store.get_record(
        f"checkpoint_capsule:{run.run_id}:{nonselected.sha256}",
        mdstats.EvaluationStateCapsuleRecord,
    )
    assert Path(capsule.capsule_path).is_file()
    assert capsule.capsule_size_bytes < capsule.source_checkpoint_size_bytes
    original = campaign_cli._evaluation_checkpoint_catalog(
        store, run.run_id, retained
    )
    assert len(original.checkpoints) == 2
    retention = store.get_payload(f"checkpoint_retention:{run.run_id}")
    assert retention["schema"] == "mdstats.mlff-checkpoint-retention.v2"
    assert retention["selected_checkpoint_restart_capable"] is True
    ok, detail = campaign_cli._completed_checkpoint_storage_matches(
        paths, store, run.run_id, catalog
    )
    assert ok, detail

    # STOR2 is restart/idempotency safe: a second pass trusts the committed capsule,
    # leaves the selected raw checkpoint untouched, and performs no further compaction.
    second = campaign_cli._compact_evaluated_checkpoints(
        cfg, paths, store, SimpleNamespace(runs=(run,))
    )
    assert second.reclaimed_bytes == 0
    assert len(list(checkpoint_root.glob("*.pt"))) == 1
    assert Path(capsule.capsule_path).is_file()


def test_completed_training_run_is_checksum_verified_and_not_recalculated(tmp_path: Path) -> None:
    job, run, _ = _job(tmp_path)
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        "#!/bin/sh\n"
        "mkdir -p \"$CHECKPOINT_DIR\"\n"
        "printf model > \"$CHECKPOINT_DIR/model_epoch-1.pt\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    output = tmp_path / "execution"
    checkpoints = tmp_path / "checkpoints"
    policy = mdstats.TrainingExecutionPolicy(
        max_attempts=2, checkpoint_glob="*epoch*.pt"
    )
    first = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=policy,
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
    )
    assert first.state is mdstats.TrainingRunState.SUCCEEDED

    # A completed checksummed record must be returned before the wrapper is
    # launched again.  Replacing the executable with a failure makes any
    # accidental recalculation immediately visible.
    wrapper.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    wrapper.chmod(0o755)
    second = mdstats.execute_training_run(
        run,
        job,
        data8_root=tmp_path,
        execution_root=output,
        checkpoint_directory=checkpoints,
        policy=policy,
        environment={"CHECKPOINT_DIR": str(checkpoints)},
        wrapper_path=wrapper,
        prior_record=first,
    )
    assert second == first
    assert len(second.attempts) == 1


def test_committee_seed_coverage_follows_selected_method_matrix() -> None:
    runs = []
    counter = 1000
    variant_specs = (
        (mdstats.TrainingMode.NAIVE_FINE_TUNING, "naive-family-asymmetric", (1, 2), 0.08),
        (mdstats.TrainingMode.MULTIHEAD_REPLAY, "replay-family-asymmetric", (17,), 0.05),
    )
    for mode, family, seeds, _ in variant_specs:
        for seed in seeds:
            for fold in (0, 1, None):
                counter += 1
                runs.append(_manual_run(mode=mode, family=family, seed=seed, fold=fold, value=counter))
    bundles = tuple(sorted({run.data8_bundle_digest for run in runs}))
    qualification = _qualification(bundles[0])
    campaign = mdstats.TrainingCampaignPlan(
        campaign_id="data9b2-asymmetric-seeds",
        dataset_id="lta-production",
        production_qualification_digest=qualification.content_digest,
        production_plan_digest=qualification.production_plan_digest,
        qualified_anchor_data8_bundle_digest=bundles[0],
        policy=mdstats.TrainingCampaignPolicy(
            required_seeds=(1, 2, 17),
            required_training_modes=(
                mdstats.TrainingMode.NAIVE_FINE_TUNING,
                mdstats.TrainingMode.MULTIHEAD_REPLAY,
            ),
            required_selection_sizes=(512,),
            required_variants=(
                (mdstats.TrainingMode.NAIVE_FINE_TUNING, 512, 1, 2),
                (mdstats.TrainingMode.NAIVE_FINE_TUNING, 512, 2, 2),
                (mdstats.TrainingMode.MULTIHEAD_REPLAY, 512, 17, 2),
            ),
        ),
        expected_cross_validation_fold_count=2,
        runs=tuple(runs),
        data8_bundle_digests=bundles,
    )
    selections = {}
    metrics = {}
    for run in campaign.runs:
        base = 0.08 if run.training_mode is mdstats.TrainingMode.NAIVE_FINE_TUNING else 0.05
        selection, metric = _decision_and_metric(
            run, base + 0.001 * (run.fold_index or 0)
        )
        selections[run.content_digest] = selection
        metrics[run.content_digest] = metric
    variants = [
        mdstats.aggregate_protocol_variant(
            campaign, selections, metrics, protocol_variant_digest=digest_value
        )
        for digest_value in sorted({run.protocol_variant_digest for run in campaign.runs})
    ]
    families = [
        mdstats.aggregate_protocol_family(
            [variant for variant in variants if variant.protocol_family_digest == family]
        )
        for family in sorted({variant.protocol_family_digest for variant in variants})
    ]
    comparison = mdstats.compare_protocol_families(families)
    assert comparison.selected_training_mode is mdstats.TrainingMode.MULTIHEAD_REPLAY
    selected_runs = [
        run for run in campaign.runs
        if run.protocol_family_digest == comparison.selected_protocol_family_digest
        and run.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT
    ]
    assert [run.seed for run in selected_runs] == [17]
    members = []
    for run in selected_runs:
        selection = selections[run.content_digest]
        members.append(
            mdstats.CommitteeMemberRecord(
                protocol_family_digest=run.protocol_family_digest,
                seed=run.seed,
                final_run_plan_digest=run.content_digest,
                checkpoint_selection_record_digest=selection.content_digest,
                source_checkpoint_path=f"/checkpoints/{run.seed}.pt",
                source_checkpoint_sha256=selection.selected_checkpoint_sha256,
                target_head_name="target_head",
                exported_model_path=f"/models/{run.seed}.model",
                exported_model_sha256=_h(f"asymmetric-model-{run.seed}"),
                byte_size=100 + run.seed,
            )
        )
    committee = mdstats.build_committee_identity(
        campaign,
        comparison,
        members,
        policy=mdstats.CommitteeExportPolicy(minimum_members=1),
    )
    assert tuple(member.seed for member in committee.members) == (17,)
