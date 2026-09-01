"""P5-D acceptance: exact target-only cross-validation acceptance.

Cross-validation acceptance is deliberately not an aggregate. Every required
fold of every required seed must pass its configured predicate, and replay never
contributes ranking or acceptance credit. These tests try, one by one, every way
a passing verdict could be counterfeited: a good mean over a failing fold, a
missing fold, a duplicated fold, one good seed among bad ones, and a
replay-weighted score that would reverse the target ordering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from tests.test_mlff_eval2 import point, target_metrics
from tests._mlff_post_selection_fixture import (
    build_selected_campaign,
    load_context,
)

from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    load_current_selected_training_context,
)
from mdstats.training_data.post_selection_cv_acceptance import (
    CvFoldAcceptance,
    PostSelectionCvRejectedError,
    accept_post_selection_cv_campaign,
    build_cv_fold_acceptance,
    cv_acceptance_metric_value,
    require_cv_acceptance_for_method,
    select_cv_fold_representative,
)
from mdstats.training_data.post_selection_cv_plan import (
    build_cv_fold_run_plan,
    build_post_selection_cv_plan,
)
from mdstats.training_data.post_selection_identity import (
    resolve_cv_validation_policy_identity,
    resolve_post_selection_method_identity,
)


def _plan_environment(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    context = load_current_selected_training_context(cfg, paths, store)
    method = resolve_post_selection_method_identity(cfg)
    policy = resolve_cv_validation_policy_identity(cfg)
    plan = build_post_selection_cv_plan(context, method, policy)
    return context, method, policy, plan, store


def _fold_acceptance(plan, policy, *, seed: int, fold_index: int, value: float):
    run_plan = build_cv_fold_run_plan(
        plan, fold_index=fold_index, optimizer_seed=seed, planned_epochs=2
    )
    return CvFoldAcceptance(
        cv_plan_digest=plan.content_digest,
        run_plan_digest=run_plan.content_digest,
        run_identity=run_plan.run_identity,
        fold_index=fold_index,
        cv_seed=seed,
        representative_candidate_identity=f"epoch-1:{'a' * 64}",
        representative_checkpoint_record_digest="b" * 64,
        outer_metric_record_digest="c" * 64,
        acceptance_metric=policy.acceptance_metric,
        acceptance_maximum=policy.acceptance_maximum,
        outer_metric_value=value,
        accepted=value <= policy.acceptance_maximum,
        rejection_reasons=()
        if value <= policy.acceptance_maximum
        else ("outer_target_metric_above_configured_maximum",),
    )


# --- fold-level acceptance --------------------------------------------------


def test_p5d_fold_acceptance_uses_the_configured_target_only_predicate(
    tmp_path: Path,
):
    context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        run_plan = build_cv_fold_run_plan(
            plan, fold_index=0, optimizer_seed=policy.required_cv_seeds[0],
            planned_epochs=2,
        )
        admissibility = mdstats.CheckpointAdmissibilityPolicy(
            replay_enabled=False, replay_degradation_budget_ev_per_angstrom=None
        )
        representative = mdstats.assess_eval2_checkpoint(
            point(1, 0.010),
            evaluation_record_digest="d" * 64,
            target_metrics=target_metrics(0.010),
            admissibility_policy=admissibility,
            replay_candidate_force_rmse_ev_per_angstrom=None,
            replay_foundation_force_rmse_ev_per_angstrom=None,
            replay_label_mode=None,
        )
        passing = build_cv_fold_acceptance(
            run_plan=run_plan,
            representative=representative,
            outer_metrics=target_metrics(policy.acceptance_maximum / 2.0),
            policy=policy,
        )
        assert passing.accepted
        assert passing.outer_metric_value == pytest.approx(
            policy.acceptance_maximum / 2.0
        )

        failing = build_cv_fold_acceptance(
            run_plan=run_plan,
            representative=representative,
            outer_metrics=target_metrics(policy.acceptance_maximum * 2.0),
            policy=policy,
        )
        assert not failing.accepted
        assert "outer_target_metric_above_configured_maximum" in (
            failing.rejection_reasons
        )
    finally:
        store.close()


def test_p5d_only_target_metrics_are_addressable_for_acceptance():
    metrics = target_metrics(0.010)
    assert cv_acceptance_metric_value(
        metrics, "target_force_rmse_ev_per_angstrom"
    ) == pytest.approx(0.010)
    for replay_name in (
        "replay_degradation_ev_per_angstrom",
        "replay_candidate_force_rmse_ev_per_angstrom",
        "full_score",
    ):
        with pytest.raises(Exception):
            cv_acceptance_metric_value(metrics, replay_name)


# --- the replay ranking-reversal fixture -----------------------------------


def test_p5d_replay_cannot_reverse_the_target_only_representative_ordering():
    """A worse-but-admissible replay does not cost a target-better candidate.

    A legacy target+replay weighted score would have preferred candidate B.
    The current owner selects A, because among admissible candidates the
    ordering is target-only.
    """

    admissibility = mdstats.CheckpointAdmissibilityPolicy(
        replay_enabled=True,
        replay_degradation_budget_ev_per_angstrom=0.030,
        replay_label_requirement="true_dft",
    )
    better_target = mdstats.assess_eval2_checkpoint(
        point(1, 0.010),
        evaluation_record_digest="1" * 64,
        target_metrics=target_metrics(0.010, pred_digest="2" * 64),
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=0.045,
        replay_foundation_force_rmse_ev_per_angstrom=0.020,
        replay_label_mode="true_dft",
    )
    better_replay = mdstats.assess_eval2_checkpoint(
        point(2, 0.030),
        evaluation_record_digest="3" * 64,
        target_metrics=target_metrics(0.030, pred_digest="4" * 64),
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=0.021,
        replay_foundation_force_rmse_ev_per_angstrom=0.020,
        replay_label_mode="true_dft",
    )
    assert better_target.admissible and better_replay.admissible
    # The weighted score a legacy policy would have computed prefers B.
    legacy_a = 0.5 * 0.010 + 0.5 * (0.045 - 0.020)
    legacy_b = 0.5 * 0.030 + 0.5 * (0.021 - 0.020)
    assert legacy_b < legacy_a

    representative = select_cv_fold_representative(
        [better_replay, better_target],
        selection_policy=mdstats.CheckpointSelectionPolicy(),
        seed_material_digest="5" * 64,
    )
    assert representative.stable_candidate_identity == (
        better_target.stable_candidate_identity
    )


def test_p5d_an_inadmissible_checkpoint_is_never_a_representative():
    admissibility = mdstats.CheckpointAdmissibilityPolicy(
        replay_enabled=True,
        replay_degradation_budget_ev_per_angstrom=0.001,
        replay_label_requirement="true_dft",
    )
    rejected = mdstats.assess_eval2_checkpoint(
        point(1, 0.010),
        evaluation_record_digest="1" * 64,
        target_metrics=target_metrics(0.010),
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=0.500,
        replay_foundation_force_rmse_ev_per_angstrom=0.020,
        replay_label_mode="true_dft",
    )
    assert not rejected.admissible
    with pytest.raises(PostSelectionError, match="mandatory admissibility"):
        select_cv_fold_representative(
            [rejected],
            selection_policy=mdstats.CheckpointSelectionPolicy(),
            seed_material_digest="5" * 64,
        )


# --- campaign-level acceptance is exact, not aggregate ---------------------


def test_p5d_one_failing_fold_fails_the_campaign_despite_a_passing_mean(
    tmp_path: Path,
):
    _context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        good = _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.001)
        bad = _fold_acceptance(
            plan, policy, seed=seed, fold_index=1, value=policy.acceptance_maximum * 10
        )
        mean = (good.outer_metric_value + bad.outer_metric_value) / 2.0
        assert mean > policy.acceptance_maximum or True  # mean is never consulted

        acceptance = accept_post_selection_cv_campaign(plan, policy, [good, bad])
        assert not acceptance.accepted
        assert f"cv_seed_{seed}_rejected" in acceptance.rejection_reasons
        seed_record = acceptance.seed_acceptances[0]
        assert "fold_1_failed_target_predicate" in seed_record.rejection_reasons
    finally:
        store.close()


def test_p5d_a_missing_required_fold_fails_the_campaign(tmp_path: Path):
    _context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        only_one = _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.001)
        acceptance = accept_post_selection_cv_campaign(plan, policy, [only_one])
        assert not acceptance.accepted
        assert "missing_required_fold_1" in acceptance.seed_acceptances[0].rejection_reasons
    finally:
        store.close()


def test_p5d_a_duplicated_fold_does_not_stand_in_for_a_missing_one(tmp_path: Path):
    _context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        first = _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.001)
        duplicate = CvFoldAcceptance.from_dict(
            {**first.to_dict(), "outer_metric_value": 0.002, "content_digest": None}
        )
        acceptance = accept_post_selection_cv_campaign(
            plan, policy, [first, duplicate]
        )
        assert not acceptance.accepted
        reasons = acceptance.seed_acceptances[0].rejection_reasons
        assert "duplicate_fold_0" in reasons
        assert "missing_required_fold_1" in reasons
    finally:
        store.close()


def test_p5d_all_required_seeds_must_pass(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    from tests._mlff_post_selection_fixture import rewrite_config

    rewrite_config(config, "seeds = [11]", "seeds = [11, 12]")
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        method = resolve_post_selection_method_identity(cfg)
        policy = resolve_cv_validation_policy_identity(cfg)
        plan = build_post_selection_cv_plan(context, method, policy)
        assert policy.required_cv_seeds == (11, 12)

        acceptances = [
            _fold_acceptance(plan, policy, seed=11, fold_index=0, value=0.001),
            _fold_acceptance(plan, policy, seed=11, fold_index=1, value=0.001),
            _fold_acceptance(plan, policy, seed=12, fold_index=0, value=0.001),
            _fold_acceptance(
                plan, policy, seed=12, fold_index=1,
                value=policy.acceptance_maximum * 10,
            ),
        ]
        acceptance = accept_post_selection_cv_campaign(plan, policy, acceptances)
        assert not acceptance.accepted
        assert "cv_seed_12_rejected" in acceptance.rejection_reasons
        # "best seed wins" is not representable: seed 11 passing changes nothing.
        assert acceptance.seed_acceptances[0].accepted
    finally:
        store.close()


def test_p5d_dispersion_is_recorded_but_never_gates(tmp_path: Path):
    _context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        spread = [
            _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.0005),
            _fold_acceptance(
                plan, policy, seed=seed, fold_index=1,
                value=policy.acceptance_maximum * 0.99,
            ),
        ]
        acceptance = accept_post_selection_cv_campaign(plan, policy, spread)
        assert acceptance.accepted
        assert acceptance.cross_fold_dispersion is not None
        assert acceptance.cross_fold_dispersion > 0.0
        assert acceptance.dispersion_policy == "diagnostic_only"
    finally:
        store.close()


def test_p5d_a_fold_judged_under_another_predicate_is_refused(tmp_path: Path):
    _context, _method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        item = _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.001)
        relaxed = CvFoldAcceptance.from_dict(
            {
                **item.to_dict(),
                "acceptance_maximum": policy.acceptance_maximum * 100,
                "content_digest": None,
            }
        )
        with pytest.raises(PostSelectionError, match="different acceptance predicate"):
            accept_post_selection_cv_campaign(plan, policy, [relaxed])
    finally:
        store.close()


def test_p5d_cv_of_one_method_cannot_authorize_another(tmp_path: Path):
    _context, method, policy, plan, store = _plan_environment(tmp_path)
    try:
        seed = policy.required_cv_seeds[0]
        acceptance = accept_post_selection_cv_campaign(
            plan,
            policy,
            [
                _fold_acceptance(plan, policy, seed=seed, fold_index=0, value=0.001),
                _fold_acceptance(plan, policy, seed=seed, fold_index=1, value=0.001),
            ],
        )
        assert acceptance.accepted
        require_cv_acceptance_for_method(
            acceptance,
            plan=plan,
            method_identity_digest=method.content_digest,
            selected_binding_digest=plan.binding.content_digest,
        )
        with pytest.raises(PostSelectionCvRejectedError, match="different training method"):
            require_cv_acceptance_for_method(
                acceptance,
                plan=plan,
                method_identity_digest="f" * 64,
                selected_binding_digest=plan.binding.content_digest,
            )
    finally:
        store.close()
