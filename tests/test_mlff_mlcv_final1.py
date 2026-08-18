from types import SimpleNamespace

import pytest

import mdstats


def _run(seed, kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT, fold=None):
    return SimpleNamespace(
        content_digest=(f"{seed:x}" * 64)[:64],
        run_id=f"multihead-seed{seed}-{'final' if fold is None else f'fold{fold:02d}'}",
        kind=kind,
        fold_index=fold,
        seed=seed,
        protocol_variant_digest=(f"{seed+4:x}" * 64)[:64],
        protocol_family_digest="a" * 64,
    )


def _candidate(seed, score, target=None, replay=None):
    target = score if target is None else target
    # Choose absolute replay so its signed degradation reproduces the requested score geometry.
    foundation = 0.075
    degradation = 2.0*score - target
    replay = foundation + degradation if replay is None else replay
    degradation = replay - foundation
    return SimpleNamespace(
        checkpoint_sha256=(f"{seed+8:x}" * 64)[:64], checkpoint_epoch=5 + seed,
        target_force_rmse_ev_per_angstrom=target, replay_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=foundation,
        replay_degradation_force_rmse_ev_per_angstrom=degradation,
        replay_degradation_budget_ev_per_angstrom=0.030,
        replay_absolute_ceiling_ev_per_angstrom=foundation+0.030,
        replay_baseline_model_sha256="6"*64, full_score_ev_per_angstrom=score,
    )


def _selection(run, score=0.025, outcome="representative_selected"):
    rep = None if outcome == "no_representative" else _candidate(run.seed, score)
    return SimpleNamespace(
        run_plan_digest=run.content_digest,
        run_id=run.run_id,
        kind=run.kind,
        fold_index=run.fold_index,
        seed=run.seed,
        selection_policy_digest="b" * 64,
        target_full_artifact_digest="c" * 64,
        target_full_sha256="d" * 64,
        replay_full_artifact_digest="e" * 64,
        replay_full_sha256="f" * 64,
        outcome=outcome,
        representative_candidate=rep,
        content_digest=(f"{run.seed+1:x}" * 64)[:64],
        serialization_schema="mdstats.mlcv-run-selection-record.v2",
    )


def _cv(run, outcome="cv_robust"):
    return SimpleNamespace(
        seed=run.seed,
        protocol_variant_digest=run.protocol_variant_digest,
        outcome=outcome,
        content_digest=(f"{run.seed+11:x}" * 64)[:64],
    )


def _campaign(runs):
    return SimpleNamespace(content_digest="9" * 64, runs=tuple(runs))


def _campaign_cv(campaign, outcome="cv_robust", seed_aggregates=()):
    return SimpleNamespace(
        campaign_plan_digest=campaign.content_digest,
        outcome=outcome,
        content_digest="8" * 64,
        seed_aggregates=tuple(seed_aggregates),
    )


def test_final1_only_final_runs_compete_and_lowest_full_score_wins():
    runs = [_run(1), _run(2), _run(3)]
    campaign = _campaign(runs)
    selections = [_selection(runs[0], 0.027), _selection(runs[1], 0.023), _selection(runs[2], 0.025)]
    cvs = [_cv(run) for run in runs]
    result = mdstats.build_mlcv_final_selection(campaign, _campaign_cv(campaign), cvs, selections)
    assert result.outcome == "production_candidate_selected"
    assert result.production_best_seed == 2
    assert [v.seed for v in result.qualified_candidates] == [2, 3, 1]
    assert len(result.qualified_committee_candidate_digests) == 3
    assert result.production_model_published is False
    restored = mdstats.MlcvFinalSelectionRecord.from_dict(result.to_dict())
    assert restored.content_digest == result.content_digest


def test_final1_failed_final_seed_is_omitted_from_committee_not_padded():
    runs = [_run(1), _run(2), _run(3)]
    campaign = _campaign(runs)
    selections = [_selection(runs[0], 0.027), _selection(runs[1], outcome="no_representative"), _selection(runs[2], 0.025)]
    result = mdstats.build_mlcv_final_selection(
        campaign, _campaign_cv(campaign), [_cv(run) for run in runs], selections
    )
    assert result.outcome == "production_candidate_selected"
    assert result.production_best_seed == 3
    assert [v.seed for v in result.qualified_candidates] == [3, 1]
    failed = next(v for v in result.candidates if v.seed == 2)
    assert failed.rejection_reasons == ("no_final_representative",)


def test_final1_campaign_cv_failure_blocks_all_production_and_committee():
    runs = [_run(1), _run(2), _run(3)]
    campaign = _campaign(runs)
    cvs = [_cv(runs[0]), _cv(runs[1], "cv_failed"), _cv(runs[2])]
    result = mdstats.build_mlcv_final_selection(
        campaign, _campaign_cv(campaign, "cv_failed"), cvs,
        [_selection(run, 0.020 + run.seed * 0.001) for run in runs],
    )
    assert result.outcome == "cv_failed"
    assert result.production_best_seed is None
    assert result.qualified_committee_candidate_digests == ()


def test_final1_zero_fold_cv_not_performed_can_proceed_without_fabricating_cv():
    runs = [_run(1), _run(2)]
    campaign = _campaign(runs)
    cvs = [_cv(run, "cv_not_performed") for run in runs]
    result = mdstats.build_mlcv_final_selection(
        campaign, _campaign_cv(campaign, "cv_not_performed"), cvs,
        [_selection(runs[0], 0.024), _selection(runs[1], 0.025)],
    )
    assert result.outcome == "production_candidate_selected"
    assert result.production_best_seed == 1
    assert {v.seed_cv_outcome for v in result.candidates} == {"cv_not_performed"}


def test_final1_rejects_fold_selection_and_incomparable_final_validation_domains():
    final = _run(1)
    campaign = _campaign([final])
    cv = [_cv(final)]
    fold = _run(1, mdstats.MaceJobKind.CROSS_VALIDATION_FOLD, 0)
    fold_sel = _selection(fold, 0.02)
    with pytest.raises(mdstats.TrainingDataInputError, match="fold selection"):
        mdstats.build_mlcv_final_selection(campaign, _campaign_cv(campaign), cv, [fold_sel])

    runs = [_run(1), _run(2)]
    campaign = _campaign(runs)
    a, b = _selection(runs[0]), _selection(runs[1])
    b.target_full_artifact_digest = "7" * 64
    with pytest.raises(mdstats.TrainingDataInputError, match="identical D_full"):
        mdstats.build_mlcv_final_selection(campaign, _campaign_cv(campaign), [_cv(v) for v in runs], [a, b])



def test_final1_requires_exact_seed_cv_records_embedded_in_campaign_aggregate():
    runs = [_run(1), _run(2)]
    campaign = _campaign(runs)
    embedded = [_cv(run) for run in runs]
    substituted = list(embedded)
    substituted[1] = SimpleNamespace(
        seed=embedded[1].seed,
        protocol_variant_digest=embedded[1].protocol_variant_digest,
        outcome=embedded[1].outcome,
        content_digest="0" * 64,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="authenticated evidence"):
        mdstats.build_mlcv_final_selection(
            campaign, _campaign_cv(campaign, seed_aggregates=embedded), substituted,
            [_selection(run) for run in runs],
        )

def test_final1_committee_record_cannot_claim_production_publication():
    member = mdstats.MlcvFinalCommitteeMemberRecord(
        final_candidate_digest="1"*64, seed=1, final_run_plan_digest="2"*64,
        run_selection_record_digest="3"*64, checkpoint_sha256="4"*64,
        checkpoint_epoch=8, full_score_ev_per_angstrom=0.025,
        replay_absolute_full_rmse_ev_per_angstrom=0.080,
        replay_foundation_full_rmse_ev_per_angstrom=0.075,
        replay_degradation_full_rmse_ev_per_angstrom=0.005,
        replay_degradation_budget_ev_per_angstrom=0.030,
        target_head_name="target_head", exported_model_path="/tmp/seed1.model",
        exported_model_sha256="5"*64, byte_size=100,
    )
    committee = mdstats.MlcvFinalCommitteeRecord(
        campaign_plan_digest="6"*64, final_selection_record_digest="7"*64,
        members=(member,), production_best_member_digest=member.content_digest,
    )
    assert committee.production_model_published is False
    with pytest.raises(mdstats.TrainingDataInputError, match="verified production"):
        mdstats.MlcvFinalCommitteeRecord(
            campaign_plan_digest="6"*64, final_selection_record_digest="7"*64,
            members=(member,), production_best_member_digest=member.content_digest,
            production_model_published=True,
        )
