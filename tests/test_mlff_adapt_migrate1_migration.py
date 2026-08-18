from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _candidate():
    return mdstats.FullEvaluationCandidateRecord(
        finalist_rank=1,
        finalist_batch_index=1,
        run_plan_digest=_sha("run"),
        run_id="run-1",
        checkpoint_sha256=_sha("checkpoint"),
        checkpoint_epoch=4,
        evaluation_record_digest=_sha("eval"),
        target_force_rmse_ev_per_angstrom=0.024,
        replay_force_rmse_ev_per_angstrom=0.026,
        full_score_ev_per_angstrom=0.025,
        admissible=True,
        rejection_reasons=(),
        replay_foundation_force_rmse_ev_per_angstrom=0.020,
        replay_absolute_degradation_ev_per_angstrom=0.006,
        replay_fractional_degradation=0.30,
    )


def _adaptive_records(tmp_path: Path):
    candidate = _candidate()
    evaluation = mdstats.AdaptiveFullEvaluationRecord(
        campaign_plan_digest=_sha("campaign"),
        policy_digest=_sha("eval-policy"),
        finalist_queue_digest=_sha("queue"),
        full_target_artifact_digest=_sha("target-domain"),
        full_replay_artifact_digest=_sha("replay-domain"),
        evaluated_candidates=(candidate,),
        completed_batch_count=1,
        outcome="admissible_candidates_available",
    )
    attempt = mdstats.AdaptiveVerificationCandidateRecord(
        adaptive_full_evaluation_digest=evaluation.content_digest,
        verification_policy_digest=_sha("verify-policy"),
        full_evaluation_candidate_digest=candidate.content_digest,
        finalist_rank=1,
        finalist_batch_index=1,
        run_plan_digest=candidate.run_plan_digest,
        run_id=candidate.run_id,
        checkpoint_sha256=candidate.checkpoint_sha256,
        checkpoint_epoch=candidate.checkpoint_epoch,
        full_score_ev_per_angstrom=candidate.full_score_ev_per_angstrom,
        target_force_rmse_ev_per_angstrom=candidate.target_force_rmse_ev_per_angstrom,
        replay_force_rmse_ev_per_angstrom=candidate.replay_force_rmse_ev_per_angstrom,
        candidate_model_sha256=_sha("model"),
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        verification_case_digests=(_sha("case"),),
        passed=True,
        rejection_reasons=(),
    )
    verification = mdstats.AdaptiveVerificationRecord(
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=evaluation.content_digest,
        verification_policy_digest=_sha("verify-policy"),
        attempts=(attempt,),
        outcome="verified_candidate_selected",
        selected_attempt_digest=attempt.content_digest,
    )
    model_path = tmp_path / "selected.model"
    model_path.write_bytes(b"verified")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    deployment = mdstats.AdaptiveDeploymentModelRecord(
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=evaluation.content_digest,
        adaptive_verification_digest=verification.content_digest,
        selected_full_evaluation_candidate_digest=candidate.content_digest,
        selected_verification_attempt_digest=attempt.content_digest,
        run_plan_digest=candidate.run_plan_digest,
        run_id=candidate.run_id,
        checkpoint_sha256=candidate.checkpoint_sha256,
        checkpoint_epoch=candidate.checkpoint_epoch,
        target_head_name="target_head",
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        exported_model_path=str(model_path),
        exported_model_sha256=model_sha,
        byte_size=model_path.stat().st_size,
    )
    freeze = mdstats.AdaptiveProtocolFreezeRecord(
        production_qualification_digest=_sha("qualification"),
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=evaluation.content_digest,
        adaptive_verification_digest=verification.content_digest,
        adaptive_deployment_model_digest=deployment.content_digest,
        selected_full_evaluation_candidate_digest=candidate.content_digest,
        full_target_artifact_digest=evaluation.full_target_artifact_digest,
        full_replay_artifact_digest=evaluation.full_replay_artifact_digest,
        exported_model_sha256=model_sha,
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        frozen_at_utc="2026-08-09T23:00:00+00:00",
    )
    return evaluation, verification, deployment, freeze


def test_authority_adapter_roundtrip_for_adaptive_freeze(tmp_path: Path):
    _, _, _, freeze = _adaptive_records(tmp_path)
    authority = mdstats.protocol_freeze_authority_from_adaptive(freeze)
    assert authority.authority_kind == "adaptive_deployment"
    assert authority.source_record_digest == freeze.content_digest
    assert authority.protected_model_sha256 == (freeze.exported_model_sha256,)
    assert authority.model_inference_dtype == "float32"
    assert authority.scientific_analysis_dtype == "float64"
    assert mdstats.ProtocolFreezeAuthorityRecord.from_dict(authority.to_dict()) == authority
    assert mdstats.protocol_freeze_authority_from_payload(freeze.to_dict()) == authority


def test_historical_protocol_freeze_remains_readable_through_authority_adapter():
    freeze = mdstats.ProtocolFreezeRecord(
        production_qualification_digest=_sha("qualification"),
        campaign_plan_digest=_sha("campaign"),
        source_catalog_digest=_sha("source"),
        frame_catalog_digest=_sha("frames"),
        data5_bundle_digest=_sha("data5"),
        protocol_comparison_record_digest=_sha("comparison"),
        selected_protocol_family_digest=_sha("family"),
        selected_family_aggregate_digest=_sha("aggregate"),
        committee_identity_digest=_sha("committee"),
        committee_member_model_sha256=(_sha("model-a"), _sha("model-b")),
        final_checkpoint_selection_record_digests=(_sha("sel-a"), _sha("sel-b")),
        frozen_at_utc="2026-08-01T00:00:00+00:00",
    )
    authority = mdstats.protocol_freeze_authority_from_payload(freeze.to_dict())
    assert authority.authority_kind == "historical_committee"
    assert authority.source_record_digest == freeze.content_digest
    assert authority.model_inference_dtype is None
    assert authority.protected_model_sha256 == freeze.committee_member_model_sha256


def test_reconcile_upgrades_020127_adaptive_alias_without_deleting_history(tmp_path: Path):
    paths = SimpleNamespace(
        state_db=tmp_path / ".mdstats" / "campaign.sqlite3",
        results=tmp_path / "results",
    )
    paths.results.mkdir(parents=True)
    store = campaign_cli.CampaignStore(paths.state_db)
    evaluation, verification, deployment, freeze = _adaptive_records(tmp_path)
    store.put_records({
        "adaptive_full_evaluation": evaluation,
        "adaptive_verification": verification,
        "adaptive_deployment_model": deployment,
        "adaptive_protocol_freeze": freeze,
        # Exact 0.20.127a0 compatibility alias.
        "protocol_freeze": freeze,
        "committee": {"schema": "historical.test", "content_digest": _sha("old")},
        "multifidelity_policy:old-run": {"schema": "historical.mf"},
    })
    migration = campaign_cli._reconcile_adaptive_migration(paths, store)
    assert migration.migrated_legacy_protocol_freeze_alias_schema == mdstats.ADAPTIVE_PROTOCOL_FREEZE_SCHEMA
    assert migration.historical_evidence_keys == ("committee", "multifidelity_policy:old-run")
    assert store.get_payload("adaptive_protocol_freeze")["schema"] == mdstats.ADAPTIVE_PROTOCOL_FREEZE_SCHEMA
    assert store.get_payload("protocol_freeze")["schema"] == mdstats.PROTOCOL_FREEZE_AUTHORITY_SCHEMA
    assert store.has_record("committee")
    assert store.has_record("multifidelity_policy:old-run")
    assert (paths.results / "adaptive-migration.json").is_file()
    # Exact restart/reconciliation is idempotent.
    assert campaign_cli._reconcile_adaptive_migration(paths, store) == migration


def test_reconcile_refuses_dual_historical_and_adaptive_authority(tmp_path: Path):
    paths = SimpleNamespace(
        state_db=tmp_path / ".mdstats" / "campaign.sqlite3",
        results=tmp_path / "results",
    )
    paths.results.mkdir(parents=True)
    store = campaign_cli.CampaignStore(paths.state_db)
    evaluation, verification, deployment, freeze = _adaptive_records(tmp_path)
    store.put_records({
        "adaptive_full_evaluation": evaluation,
        "adaptive_verification": verification,
        "adaptive_deployment_model": deployment,
        "adaptive_protocol_freeze": freeze,
        "protocol_freeze": {
            "schema": mdstats.PROTOCOL_FREEZE_RECORD_SCHEMA,
            "content_digest": _sha("legacy-freeze"),
        },
    })
    with pytest.raises(campaign_cli.CampaignCliError, match="historical committee protocol freeze"):
        campaign_cli._reconcile_adaptive_migration(paths, store)


def test_storage_authority_requires_valid_schema_not_key_presence(tmp_path: Path):
    store = campaign_cli.CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    store.put_record("protocol_freeze", {"schema": "bogus.freeze.v1"})
    with pytest.raises(campaign_cli.CampaignCliError, match="unsupported schema"):
        campaign_cli._has_authoritative_protocol_freeze(store)


def test_evaluation_migration_boundary_separates_adaptive_and_historical_campaigns():
    adaptive = SimpleNamespace(
        runs=(SimpleNamespace(protocol=SimpleNamespace(adaptive_stop_policy=object())),)
    )
    historical = SimpleNamespace(
        runs=(SimpleNamespace(protocol=SimpleNamespace(adaptive_stop_policy=None)),)
    )
    campaign_cli._enforce_evaluation_migration_boundary(adaptive, "adaptive_topk")
    campaign_cli._enforce_evaluation_migration_boundary(historical, "multi_fidelity")
    with pytest.raises(campaign_cli.CampaignCliError, match="must use checkpoint_strategy='adaptive_topk'"):
        campaign_cli._enforce_evaluation_migration_boundary(adaptive, "multi_fidelity")
    with pytest.raises(campaign_cli.CampaignCliError, match="predates adaptive/MLCV protocol identity"):
        campaign_cli._enforce_evaluation_migration_boundary(historical, "adaptive_topk")


def test_migration_record_roundtrip_and_fp64_analysis_invariant(tmp_path: Path):
    evaluation, verification, deployment, freeze = _adaptive_records(tmp_path)
    authority = mdstats.protocol_freeze_authority_from_adaptive(freeze)
    record = mdstats.AdaptiveMigrationRecord(
        campaign_plan_digest=freeze.campaign_plan_digest,
        adaptive_full_evaluation_digest=evaluation.content_digest,
        adaptive_verification_digest=verification.content_digest,
        adaptive_deployment_model_digest=deployment.content_digest,
        adaptive_protocol_freeze_digest=freeze.content_digest,
        protocol_freeze_authority_digest=authority.content_digest,
        model_inference_dtype="float64",
        scientific_analysis_dtype="float64",
        historical_evidence_keys=("committee",),
        migrated_at_utc=freeze.frozen_at_utc,
    )
    assert mdstats.AdaptiveMigrationRecord.from_dict(record.to_dict()) == record
    with pytest.raises(Exception, match="float64"):
        mdstats.AdaptiveMigrationRecord(
            campaign_plan_digest=freeze.campaign_plan_digest,
            adaptive_full_evaluation_digest=evaluation.content_digest,
            adaptive_verification_digest=verification.content_digest,
            adaptive_deployment_model_digest=deployment.content_digest,
            adaptive_protocol_freeze_digest=freeze.content_digest,
            protocol_freeze_authority_digest=authority.content_digest,
            model_inference_dtype="float32",
            scientific_analysis_dtype="float32",
            historical_evidence_keys=(),
            migrated_at_utc=freeze.frozen_at_utc,
        )


def test_frozen_adaptive_evaluation_is_reused_not_recomputed(tmp_path: Path):
    config = tmp_path / "campaign.toml"
    config.write_text("[campaign]\nid='test'\n", encoding="utf-8")
    paths = SimpleNamespace(
        state_db=tmp_path / ".mdstats" / "campaign.sqlite3",
        results=tmp_path / "results",
        config=config,
    )
    paths.results.mkdir(parents=True)
    store = campaign_cli.CampaignStore(paths.state_db)
    evaluation, verification, deployment, freeze = _adaptive_records(tmp_path)
    store.put_records({
        "adaptive_full_evaluation": evaluation,
        "adaptive_verification": verification,
        "adaptive_deployment_model": deployment,
        "adaptive_protocol_freeze": freeze,
        "protocol_freeze": mdstats.protocol_freeze_authority_from_adaptive(freeze),
    })
    assert campaign_cli._reuse_frozen_adaptive_evaluation(paths, store) is True
    migration = store.get_record("adaptive_migration", mdstats.AdaptiveMigrationRecord)
    assert migration.adaptive_full_evaluation_digest == evaluation.content_digest
    state, message = store.stage("evaluate")
    assert state is campaign_cli.StageState.COMPLETE
    assert "immutable" in message


def test_storage_report_reads_migration_authority_without_mutating_state_db(tmp_path: Path):
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="../training",
            foundation_model="../foundation.model",
            replay_train="../replay-train.xyz",
            replay_monitor="../replay-monitor.xyz",
            replay_true_labels="../true-labels",
        ),
        encoding="utf-8",
    )
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    historical = mdstats.ProtocolFreezeRecord(
        production_qualification_digest=_sha("qualification"),
        campaign_plan_digest=_sha("campaign"),
        source_catalog_digest=_sha("source"),
        frame_catalog_digest=_sha("frames"),
        data5_bundle_digest=_sha("data5"),
        protocol_comparison_record_digest=_sha("comparison"),
        selected_protocol_family_digest=_sha("family"),
        selected_family_aggregate_digest=_sha("aggregate"),
        committee_identity_digest=_sha("committee"),
        committee_member_model_sha256=(_sha("model-a"),),
        final_checkpoint_selection_record_digests=(_sha("sel-a"),),
        frozen_at_utc="2026-08-01T00:00:00+00:00",
    )
    store.put_record("protocol_freeze", historical)
    store.put_record("multifidelity_round:legacy", {"schema": "historical.mf"})
    before = hashlib.sha256(paths.state_db.read_bytes()).hexdigest()
    rc = campaign_cli.command_storage(SimpleNamespace(config=str(config), top=5))
    after = hashlib.sha256(paths.state_db.read_bytes()).hexdigest()
    assert rc == 0
    assert before == after
    payload = __import__("json").loads((paths.results / "storage-report.json").read_text())
    assert payload["protocol_freeze_authority"]["authority_kind"] == "historical_committee"
    assert payload["historical_algorithm_evidence_keys"] == ["multifidelity_round:legacy"]
