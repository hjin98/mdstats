from __future__ import annotations

import hashlib

import mdstats
from mdstats.training_data import campaign_cli
from tests.test_mlff_data9b1_campaign_checkpoint_control import (
    _bundle,
    _metric_policy,
    _qualification,
)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _campaign() -> mdstats.TrainingCampaignPlan:
    metric = _metric_policy()
    replay = _bundle(
        mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        size=512,
        seed=1,
        metric_policy=metric,
    )
    naive = _bundle(
        mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        size=512,
        seed=1,
        metric_policy=metric,
    )
    return mdstats.build_training_campaign_plan(
        _qualification(replay),
        (naive, replay),
        campaign_id="partial-evidence",
        policy=mdstats.TrainingCampaignPolicy(
            required_training_modes=(
                mdstats.TrainingMode.NAIVE_FINE_TUNING,
                mdstats.TrainingMode.MULTIHEAD_REPLAY,
            ),
            required_selection_sizes=(512,),
            required_seeds=(1,),
        ),
    )


def _variant_runs(campaign: mdstats.TrainingCampaignPlan, mode: mdstats.TrainingMode):
    return tuple(run for run in campaign.runs if run.training_mode is mode)


def test_complete_variant_is_available_before_other_methods_finish() -> None:
    campaign = _campaign()
    replay = _variant_runs(campaign, mdstats.TrainingMode.MULTIHEAD_REPLAY)
    availability = campaign_cli._variant_availability(
        campaign, (run.content_digest for run in replay)
    )
    assert len(availability) == 1
    selected = availability[0]
    assert selected.evidence_level is mdstats.VerificationEvidenceLevel.COMPLETE_VARIANT
    assert selected.completed_fold_indices == (0, 1, 2)
    assert selected.final_completed is True
    assert selected.missing_runs == ()
    assert "other configured campaign variants remain unfinished" in " ".join(
        campaign_cli._partial_evidence_warnings(selected)
    )


def test_two_completed_folds_enable_weaker_cross_validation() -> None:
    campaign = _campaign()
    replay = _variant_runs(campaign, mdstats.TrainingMode.MULTIHEAD_REPLAY)
    completed = tuple(
        run.content_digest for run in replay if run.fold_index in {0, 2}
    )
    selected = campaign_cli._variant_availability(campaign, completed)[0]
    assert selected.evidence_level is mdstats.VerificationEvidenceLevel.PARTIAL_CROSS_VALIDATION
    assert selected.completed_fold_indices == (0, 2)
    assert selected.final_completed is False
    warning = " ".join(campaign_cli._partial_evidence_warnings(selected))
    assert "2/3 cross-validation folds" in warning
    assert "final-development model is incomplete" in warning


def test_one_completed_fold_falls_back_to_single_model_evidence() -> None:
    campaign = _campaign()
    replay = _variant_runs(campaign, mdstats.TrainingMode.MULTIHEAD_REPLAY)
    completed = tuple(
        run.content_digest for run in replay if run.fold_index == 1
    )
    selected = campaign_cli._variant_availability(campaign, completed)[0]
    assert selected.evidence_level is mdstats.VerificationEvidenceLevel.SINGLE_MODEL
    assert selected.completed_fold_indices == (1,)
    warning = " ".join(campaign_cli._partial_evidence_warnings(selected))
    assert "no cross-fold estimate" in warning


def test_partial_scope_filters_method_seed_and_selection_size() -> None:
    campaign = _campaign()
    completed = tuple(run.content_digest for run in campaign.runs)
    availability = campaign_cli._variant_availability(
        campaign,
        completed,
        training_mode="multihead_replay",
        seed=1,
        selection_size=512,
    )
    assert len(availability) == 1
    assert availability[0].training_mode is mdstats.TrainingMode.MULTIHEAD_REPLAY


def _member(run_digest: str, run_id: str, fold: int | None) -> mdstats.VerificationModelRecord:
    return mdstats.VerificationModelRecord(
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        run_plan_digest=run_digest,
        run_id=run_id,
        kind=(
            mdstats.MaceJobKind.FINAL_DEVELOPMENT
            if fold is None
            else mdstats.MaceJobKind.CROSS_VALIDATION_FOLD
        ),
        fold_index=fold,
        checkpoint_selection_record_digest=_h(f"selection-{run_id}"),
        source_checkpoint_path=f"/{run_id}.pt",
        source_checkpoint_sha256=_h(f"checkpoint-{run_id}"),
        target_head_name="target_head",
        exported_model_path=f"/{run_id}.model",
        exported_model_sha256=_h(f"model-{run_id}"),
        byte_size=100,
    )


def test_available_model_verification_set_roundtrip() -> None:
    run0, run1, final = _h("run0"), _h("run1"), _h("final")
    record = mdstats.AvailableModelVerificationSet(
        campaign_plan_digest=_h("campaign"),
        available_execution_digest=_h("executions"),
        selected_protocol_family_digest=_h("family"),
        selected_protocol_variant_digest=_h("variant"),
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        evidence_level=mdstats.VerificationEvidenceLevel.COMPLETE_VARIANT,
        expected_cross_validation_folds=2,
        completed_cross_validation_folds=(0, 1),
        final_development_completed=True,
        completed_run_plan_digests=(run0, run1, final),
        missing_run_plan_digests=(),
        evidence_run_plan_digests=(run0, run1),
        primary_metric_name="target_force_component_rmse",
        primary_metric_values=(0.08, 0.09),
        mean_primary_metric=0.085,
        worst_primary_metric=0.09,
        members=(
            _member(run0, "fold-00", 0),
            _member(run1, "fold-01", 1),
            _member(final, "final", None),
        ),
        warnings=("interim",),
        created_at_utc="2026-08-06T19:00:00Z",
    )
    assert mdstats.AvailableModelVerificationSet.from_dict(record.to_dict()) == record


def test_single_configured_family_can_be_selected_without_fake_comparison() -> None:
    family = mdstats.ProtocolFamilyAggregate(
        campaign_plan_digest=_h("campaign"),
        protocol_family_digest=_h("family"),
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        primary_metric_name="target_force_component_rmse",
        variant_aggregate_digests=(_h("variant"),),
        seeds=(17,),
        seed_mean_fold_metrics=(0.08,),
        mean_cross_validated_metric=0.08,
        between_seed_standard_deviation=0.0,
        worst_seed_metric=0.08,
    )
    comparison = mdstats.compare_protocol_families((family,))
    assert comparison.selected_protocol_family_digest == family.protocol_family_digest
    assert comparison.comparison_notes == (
        "single_configured_family_no_cross_protocol_comparison",
    )


def test_parser_and_template_expose_interim_controls() -> None:
    parser = campaign_cli.build_parser()
    evaluate = parser.parse_args(
        ["evaluate", "--training-mode", "multihead_replay", "--seed", "1"]
    )
    assert evaluate.training_mode == "multihead_replay"
    assert evaluate.seed == 1
    verify = parser.parse_args(["verify", "--require-frozen"])
    assert verify.require_frozen is True
    template = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay.xyz",
        replay_monitor="monitor.xyz",
    )
    assert "allow_partial_campaign = true" in template
    assert "allow_interim_completed_models = true" in template


def test_final_only_variant_aggregates_from_final_metric_without_fake_fold(tmp_path) -> None:
    from tests.test_mlff_data9b1_campaign_checkpoint_control import _manual_run, _metrics

    metric_policy = _metric_policy()
    run = _manual_run(metric_policy)
    policy = mdstats.TrainingCampaignPolicy(
        required_seeds=(1,),
        required_training_modes=(mdstats.TrainingMode.MULTIHEAD_REPLAY,),
        required_selection_sizes=(512,),
        required_variants=((mdstats.TrainingMode.MULTIHEAD_REPLAY, 512, 1, 0),),
        require_cross_validation=True,
    )
    campaign = mdstats.TrainingCampaignPlan(
        campaign_id="final-only",
        dataset_id="dataset",
        production_qualification_digest=_h("qualification"),
        production_plan_digest=_h("plan"),
        qualified_anchor_data8_bundle_digest=run.data8_bundle_digest,
        policy=policy,
        expected_cross_validation_fold_count=0,
        runs=(run,),
        data8_bundle_digests=(run.data8_bundle_digest,),
    )
    checkpoint_path = tmp_path / "model_epoch-0.pt"
    checkpoint_path.write_bytes(b"checkpoint")
    catalog = mdstats.inventory_mace_checkpoints(run, tmp_path)
    checkpoint = catalog.checkpoints[0]
    metric = _metrics(run, checkpoint, force=0.05, replay=0.01)
    selection = mdstats.select_checkpoint(
        run, catalog, (metric,), metric_policy
    )
    aggregate = mdstats.aggregate_protocol_variant(
        campaign,
        {run.content_digest: selection},
        {run.content_digest: metric},
        protocol_variant_digest=run.protocol_variant_digest,
    )
    assert aggregate.fold_run_plan_digests == ()
    assert aggregate.fold_primary_metric_values == ()
    assert aggregate.mean_fold_primary_metric == selection.selected_primary_metric_value
