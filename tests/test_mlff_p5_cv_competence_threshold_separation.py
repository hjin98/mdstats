"""Foundation-CV competence versus fresh-production checkpoint quality.

Foundation adaptation shares one method between CV and production, but each run
is judged under its role's target-force ceiling: CV checkpoint competence and
the default held-out ceiling are 0.045 eV/angstrom, production checkpoint
quality is 0.030 eV/angstrom, and scratch keeps its pre-separation 0.030.  The
shared replay/finite/physical constraints stay in the method identity.
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdstats.training_data._common import TrainingDataSerializationError
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.campaign_post_selection_runtime import (
    PostSelectionContext,
)
from mdstats.training_data.post_selection_identity import (
    POST_SELECTION_METHOD_IDENTITY_SCHEMA,
    CvValidationPolicyIdentity,
    FinalProductionPolicyIdentity,
    PostSelectionMethodIdentity,
    post_selection_checkpoint_admissibility,
    resolve_cv_validation_policy_identity,
    resolve_final_production_policy_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from tests.test_mlff_target_size_p5_r10_guards import (
    _foundation_inspection,
    _policy_config,
)

FOUNDATION_MODES = ("naive_fine_tuning", "multihead_replay")


def _above(value: float) -> float:
    return math.nextafter(value, math.inf)


def _config(mode: str, *, foundation: Path | None, **tables) -> dict:
    replay = mode == "multihead_replay"
    config = _policy_config(
        mode, foundation=foundation if mode != "scratch" else None, replay=replay
    )
    if replay:
        config["foundation"] = {"family": "mace_mpa_0", "head": "default"}
    for name, value in tables.items():
        config[name] = value
    return config


@pytest.fixture()
def foundation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "foundation.model"
    path.write_bytes(b"bounded-foundation")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda item: _foundation_inspection(Path(item)),
    )
    return path


def _resolved(config: dict):
    policies = resolve_post_selection_method_policies(config)
    method = resolve_post_selection_method_identity(config, policies=policies)
    cv = resolve_cv_validation_policy_identity(
        config, training_mode=policies.training_mode
    )
    production = resolve_final_production_policy_identity(config)
    return policies, method, cv, production


# --- role ceilings resolve per mode ----------------------------------------


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_foundation_roles_resolve_45_45_30(foundation: Path, mode: str):
    _policies, _method, cv, production = _resolved(_config(mode, foundation=foundation))
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.045
    assert cv.acceptance_metric == "target_force_rmse_ev_per_angstrom"
    assert cv.acceptance_maximum == 0.045
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030


def test_scratch_roles_keep_pre_separation_ceilings():
    config = _config("scratch", foundation=None)
    _policies, _method, cv, production = _resolved(config)
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030
    assert cv.acceptance_maximum == 0.030
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030
    # Scratch CV still follows the [acceptance] ceiling it always read.
    raised = _config(
        "scratch",
        foundation=None,
        acceptance={"maximum_target_force_rmse_ev_per_angstrom": 0.02},
    )
    assert (
        resolve_cv_validation_policy_identity(raised).checkpoint_maximum_target_force_rmse_ev_per_angstrom
        == 0.02
    )


def test_mode_is_resolved_from_configuration_when_not_supplied(foundation: Path):
    config = _config("naive_fine_tuning", foundation=foundation)
    assert resolve_cv_validation_policy_identity(config) == (
        resolve_cv_validation_policy_identity(config, training_mode="naive_fine_tuning")
    )


def test_explicit_outer_ceiling_is_not_rewritten(foundation: Path):
    config = _config(
        "naive_fine_tuning",
        foundation=foundation,
        post_selection={"cv": {"acceptance_maximum": 0.030}},
    )
    cv = resolve_cv_validation_policy_identity(config)
    assert cv.acceptance_maximum == 0.030
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.045


def test_alternate_outer_metric_cannot_donate_its_threshold(foundation: Path):
    config = _config(
        "naive_fine_tuning",
        foundation=foundation,
        post_selection={
            "cv": {
                "acceptance_metric": "energy_mae_ev_per_atom",
                "acceptance_maximum": 0.9,
            }
        },
    )
    policies, _method, cv, _production = _resolved(config)
    assert cv.acceptance_maximum == 0.9
    effective = post_selection_checkpoint_admissibility(policies, cv)
    assert effective.maximum_target_force_rmse_ev_per_angstrom == 0.045


# --- identity ownership and invalidation -----------------------------------


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_role_only_ceiling_edits_do_not_move_shared_method(foundation: Path, mode: str):
    base = _config(mode, foundation=foundation)
    _p, method, cv, production = _resolved(base)

    production_edit = _config(
        mode,
        foundation=foundation,
        acceptance={"maximum_target_force_rmse_ev_per_angstrom": 0.025},
    )
    _p2, method2, cv2, production2 = _resolved(production_edit)
    assert method2.content_digest == method.content_digest
    assert cv2.content_digest == cv.content_digest
    assert production2.content_digest != production.content_digest

    cv_edit = _config(
        mode, foundation=foundation, post_selection={"cv": {"acceptance_maximum": 0.04}}
    )
    _p3, method3, cv3, production3 = _resolved(cv_edit)
    assert method3.content_digest == method.content_digest
    assert production3.content_digest == production.content_digest
    assert cv3.content_digest != cv.content_digest

    # A CV-only checkpoint-ceiling change is a CV-policy change alone.
    moved = dataclasses.replace(
        cv, checkpoint_maximum_target_force_rmse_ev_per_angstrom=0.05
    )
    assert moved.content_digest != cv.content_digest


def test_shared_replay_constraint_moves_method_and_both_roles(foundation: Path):
    base = _config("multihead_replay", foundation=foundation)
    policies, method, cv, production = _resolved(base)
    edited = _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={"allowed_replay_degradation_mev_per_a": 20.0},
    )
    policies2, method2, cv2, production2 = _resolved(edited)
    assert method2.content_digest != method.content_digest
    for role, role2 in ((cv, cv2), (production, production2)):
        before = post_selection_checkpoint_admissibility(policies, role)
        after = post_selection_checkpoint_admissibility(policies2, role2)
        assert before.policy_digest != after.policy_digest


def test_method_identity_cutover_excludes_role_ceiling(foundation: Path):
    _policies, method, _cv, _production = _resolved(
        _config("naive_fine_tuning", foundation=foundation)
    )
    payload = method.to_dict()
    assert payload["schema"] == POST_SELECTION_METHOD_IDENTITY_SCHEMA
    assert POST_SELECTION_METHOD_IDENTITY_SCHEMA.endswith(".v3")
    assert "checkpoint_admissibility_policy_digest" not in payload
    assert "maximum_target_force_rmse_ev_per_angstrom" not in json.dumps(payload)
    assert PostSelectionMethodIdentity.from_dict(payload) == method

    # A pre-cutover payload, which bound the target-bearing admissibility digest
    # as shared method, cannot authorize current work.
    historical = dict(payload)
    historical["schema"] = "mdstats.post-selection-method-identity.v2"
    historical["checkpoint_admissibility_policy_digest"] = historical.pop(
        "shared_checkpoint_constraints_digest"
    )
    historical.pop("content_digest")
    with pytest.raises(TrainingDataSerializationError):
        PostSelectionMethodIdentity.from_dict(historical)
    for cls, old_schema, record in (
        (CvValidationPolicyIdentity, "mdstats.post-selection-cv-policy-identity.v2", _cv_record()),
        (
            FinalProductionPolicyIdentity,
            "mdstats.post-selection-final-production-policy-identity.v1",
            _production_record(),
        ),
    ):
        stale = {**record.to_dict(), "schema": old_schema}
        stale.pop("content_digest")
        stale.pop("checkpoint_maximum_target_force_rmse_ev_per_angstrom")
        with pytest.raises(TrainingDataSerializationError):
            cls.from_dict(stale)


def _cv_record() -> CvValidationPolicyIdentity:
    return resolve_cv_validation_policy_identity({}, training_mode="naive_fine_tuning")


def _production_record() -> FinalProductionPolicyIdentity:
    return resolve_final_production_policy_identity({})


def test_role_policies_round_trip_their_ceiling():
    for record in (_cv_record(), _production_record()):
        assert type(record).from_dict(record.to_dict()) == record


# --- effective admissibility predicates ------------------------------------


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_effective_predicates_and_boundaries(foundation: Path, mode: str):
    policies, _method, cv, production = _resolved(_config(mode, foundation=foundation))
    cv_policy = post_selection_checkpoint_admissibility(policies, cv)
    production_policy = post_selection_checkpoint_admissibility(policies, production)
    replay = (
        {"replay_degradation_ev_per_angstrom": 0.0, "replay_label_mode": "true_dft"}
        if policies.replay_enabled
        else {"replay_degradation_ev_per_angstrom": None}
    )

    def admissible(policy, value):
        return policy.candidate_admissible(
            target_force_rmse_ev_per_angstrom=value, **replay
        )

    assert admissible(cv_policy, 0.042)
    assert admissible(cv_policy, 0.045)
    assert not admissible(cv_policy, _above(0.045))
    assert not admissible(production_policy, 0.042)
    assert admissible(production_policy, 0.030)
    assert not admissible(production_policy, _above(0.030))
    assert cv_policy.policy_digest != production_policy.policy_digest

    # Every shared gate is identical for both roles.
    shared = {
        key: value
        for key, value in cv_policy.to_dict().items()
        if key not in {"maximum_target_force_rmse_ev_per_angstrom", "policy_digest"}
    }
    assert shared == {
        key: value
        for key, value in production_policy.to_dict().items()
        if key not in {"maximum_target_force_rmse_ev_per_angstrom", "policy_digest"}
    }
    if policies.replay_enabled:
        for policy in (cv_policy, production_policy):
            reasons = policy.failure_reasons(
                target_force_rmse_ev_per_angstrom=0.01,
                replay_degradation_ev_per_angstrom=_above(0.030),
                replay_label_mode="foundation_pseudolabel",
            )
            assert set(reasons) == {
                "replay_true_dft_evidence_missing",
                "replay_retention_ceiling_exceeded",
            }


def test_scratch_cv_does_not_begin_passing_at_42_mev():
    config = _config("scratch", foundation=None)
    policies, _method, cv, production = _resolved(config)
    for role in (cv, production):
        effective = post_selection_checkpoint_admissibility(policies, role)
        assert not effective.candidate_admissible(
            target_force_rmse_ev_per_angstrom=0.042,
            replay_degradation_ev_per_angstrom=None,
        )


def test_run_admissibility_authenticates_the_run_role_policy(foundation: Path):
    policies, method, cv, production = _resolved(
        _config("naive_fine_tuning", foundation=foundation)
    )
    context = PostSelectionContext(
        cfg={},
        paths=None,
        store=None,
        selected=None,
        method=method,
        method_policies=policies,
        cv_policy=cv,
        production_policy=production,
        trainer=None,
        inference_evaluator=None,
    )
    cv_run = SimpleNamespace(
        run_role="post_selection_cv",
        run_identity="aa" * 32,
        method_identity_digest=method.content_digest,
        cv_policy_identity_digest=cv.content_digest,
    )
    production_run = SimpleNamespace(
        run_role="final_production",
        run_identity="bb" * 32,
        method_identity_digest=method.content_digest,
        final_production_policy_digest=production.content_digest,
    )
    assert (
        context.checkpoint_admissibility(cv_run).maximum_target_force_rmse_ev_per_angstrom
        == 0.045
    )
    assert (
        context.checkpoint_admissibility(
            production_run
        ).maximum_target_force_rmse_ev_per_angstrom
        == 0.030
    )
    stale_cv = dataclasses.replace(
        cv, checkpoint_maximum_target_force_rmse_ev_per_angstrom=0.030
    )
    for run in (
        SimpleNamespace(**{**vars(cv_run), "cv_policy_identity_digest": stale_cv.content_digest}),
        SimpleNamespace(**{**vars(cv_run), "method_identity_digest": "cc" * 32}),
        # A production run can never borrow the CV role's policy.
        SimpleNamespace(
            **{**vars(production_run), "final_production_policy_digest": cv.content_digest}
        ),
        SimpleNamespace(**{**vars(cv_run), "run_role": "target_size_screen"}),
    ):
        with pytest.raises(PostSelectionError):
            context.checkpoint_admissibility(run)


# --- assembled cross-validate -> train-production --------------------------


def _foundation_campaign(tmp_path: Path, *, mode: str) -> Path:
    from tests._mlff_post_selection_fixture import (
        build_selected_campaign,
        fixture_config_text,
    )
    from tests.test_mlff_target_size_p5_r10_guards import _write_tiny_mace_foundation

    text = fixture_config_text().replace("acceptance_maximum = 0.5\n", "")
    if mode == "naive_fine_tuning":
        model = tmp_path / "foundation.model"
        _write_tiny_mace_foundation(model)
        text = text.replace(
            'training_root = "{training_root}"',
            f'training_root = "{{training_root}}"\nfoundation_model = "{model}"\n'
            'foundation_head = "default"',
        )
    config, _workspace = build_selected_campaign(tmp_path / "campaign", config_text=text)
    return config


@pytest.mark.slow
def test_assembled_foundation_cv_passes_42_mev_and_production_refuses_it(
    tmp_path: Path, capsys
):
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
        resolve_current_cv_plan,
    )
    from mdstats.training_data.post_selection_cv_plan import build_cv_fold_run_plan
    from tests._mlff_post_selection_fixture import (
        PostSelectionHarness,
        load_context,
        run_cross_validate,
        run_train_production,
    )

    config = _foundation_campaign(tmp_path, mode="naive_fine_tuning")
    harness = PostSelectionHarness(force_offset=0.042)
    assert run_cross_validate(config, harness) == 0
    assert "CV checkpoint target-force ceiling=0.045 eV/angstrom" in capsys.readouterr().out

    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        assert context.method.training_mode == "naive_fine_tuning"
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None and acceptance.accepted
        persisted_cv = context.evidence_store.get(
            plan.cv_policy_identity_digest, CvValidationPolicyIdentity.from_dict
        )
        assert persisted_cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.045
        for seed_record in acceptance.seed_acceptances:
            for fold in seed_record.fold_acceptances:
                assert fold.acceptance_maximum == 0.045
                assert 0.030 < fold.outer_metric_value <= 0.045
        # Fixed budget: every fold trained its whole frozen CV horizon.
        assert len(harness.runs) == plan.fold_count * len(plan.required_cv_seeds)

        # Evidence judged under this CV policy cannot be reached under another
        # CV ceiling: the run positions move and the old run is refused.
        run_plan = build_cv_fold_run_plan(
            plan,
            fold_index=0,
            optimizer_seed=plan.required_cv_seeds[0],
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        other = dataclasses.replace(
            context,
            cv_policy=dataclasses.replace(
                context.cv_policy,
                checkpoint_maximum_target_force_rmse_ev_per_angstrom=0.030,
            ),
        )
        with pytest.raises(PostSelectionError):
            other.checkpoint_admissibility(run_plan)
    finally:
        store.close()

    # The same 42 meV/angstrom behavior is not production quality.
    with pytest.raises(
        PostSelectionError, match=r"target-force ceiling 0\.03 eV/angstrom"
    ):
        run_train_production(config, PostSelectionHarness(force_offset=0.042))


@pytest.mark.slow
def test_assembled_scratch_cv_still_rejects_42_mev(tmp_path: Path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
    )
    from tests._mlff_post_selection_fixture import (
        PostSelectionHarness,
        load_context,
        run_cross_validate,
    )

    config = _foundation_campaign(tmp_path, mode="scratch")
    from mdstats.training_data.post_selection_cv_acceptance import (
        PostSelectionCvRejectedError,
    )

    with pytest.raises(PostSelectionCvRejectedError):
        run_cross_validate(config, PostSelectionHarness(force_offset=0.042))
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        assert context.method.training_mode == "scratch"
        acceptance = resolve_current_cv_acceptance(context)
        assert acceptance is not None and not acceptance.accepted
        folds = [
            fold
            for seed_record in acceptance.seed_acceptances
            for fold in seed_record.fold_acceptances
        ]
        assert folds and all(not fold.accepted for fold in folds)
        assert all(
            "target_threshold_exceeded" in fold.checkpoint_rejection_reasons
            for fold in folds
        )
    finally:
        store.close()


# --- property: composition is exactly "shared constraints + role ceiling" ----

from hypothesis import given, settings
from hypothesis import strategies as st

_ceilings = st.floats(min_value=1.0e-4, max_value=1.0, allow_nan=False)


@settings(max_examples=60, deadline=None)
@given(cv_ceiling=_ceilings, production_ceiling=_ceilings)
def test_property_role_ceiling_is_the_only_role_difference(
    cv_ceiling: float, production_ceiling: float
):
    config = _config("scratch", foundation=None)
    policies = resolve_post_selection_method_policies(config)
    shared_digest = policies.shared_checkpoint_constraints_digest
    cv = dataclasses.replace(
        resolve_cv_validation_policy_identity(config),
        checkpoint_maximum_target_force_rmse_ev_per_angstrom=cv_ceiling,
    )
    production = dataclasses.replace(
        resolve_final_production_policy_identity(config),
        checkpoint_maximum_target_force_rmse_ev_per_angstrom=production_ceiling,
    )
    effective = [
        post_selection_checkpoint_admissibility(policies, role) for role in (cv, production)
    ]
    for policy, ceiling in zip(effective, (cv_ceiling, production_ceiling)):
        assert policy.candidate_admissible(
            target_force_rmse_ev_per_angstrom=ceiling,
            replay_degradation_ev_per_angstrom=None,
        )
        assert not policy.candidate_admissible(
            target_force_rmse_ev_per_angstrom=_above(ceiling),
            replay_degradation_ev_per_angstrom=None,
        )
    strip = lambda payload: {
        key: value
        for key, value in payload.items()
        if key not in {"maximum_target_force_rmse_ev_per_angstrom", "policy_digest"}
    }
    assert strip(effective[0].to_dict()) == strip(effective[1].to_dict())
    assert policies.shared_checkpoint_constraints_digest == shared_digest
    assert (effective[0].policy_digest == effective[1].policy_digest) == (
        cv_ceiling == production_ceiling
    )
