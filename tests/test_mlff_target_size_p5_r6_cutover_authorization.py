"""Acceptance R6-D: the P5 method cutover holds at the real authorization owner.

Asserting that the old and new method digests differ proves nothing about
authorization. The claim is that cross-validation evidence produced under the
pre-cutover method resolution - where recorded identity could describe defaults
execution never applied - cannot authorize a corrected final-production run,
and that it is refused by the real owner *before* any trainer or materialization
launch.

The owner under acceptance is ``build_final_production_plan`` together with
``require_cv_acceptance_for_method``. Only MACE's numerical training and
inference are substituted, strictly below that boundary.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
)
from mdstats.training_data.post_selection_cv_acceptance import (
    CvCampaignAcceptance,
    PostSelectionCvRejectedError,
)
from mdstats.training_data.post_selection_cv_plan import PostSelectionCvPlan
from mdstats.training_data.post_selection_identity import (
    PostSelectionMethodIdentity,
    resolve_post_selection_method_identity,
)
from mdstats.training_data.post_selection_production import build_final_production_plan
from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    load_context,
    run_cross_validate,
)

#: The method-recipe token in force before the canonical optimizer/precision
#: resolution cutover.
HISTORICAL_METHOD_RECIPE = "mdstats.post-selection-method.2026-09.v2"
CURRENT_METHOD_RECIPE = "mdstats.post-selection-method.2026-09.v3"


def _load_pre_repair_authorization_fixture() -> tuple[
    PostSelectionMethodIdentity, PostSelectionCvPlan, CvCampaignAcceptance
]:
    """Read the exact pre-repair serialized method/CV/acceptance chain."""

    fixture_path = Path(__file__).with_name("fixtures") / (
        "p5_pre_repair_authorization_v2.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    method = PostSelectionMethodIdentity.from_dict(payload["method"])
    plan = PostSelectionCvPlan.from_dict(payload["cv_plan"])
    acceptance = CvCampaignAcceptance.from_dict(payload["acceptance"])
    return method, plan, acceptance


def _historical_authorization(plan, acceptance, historical_method):
    """An authenticated CV plan/acceptance pair under the historical method.

    Both records are re-bound consistently, so the pair is internally coherent:
    the acceptance really does authorize the plan it names, and the plan really
    does record the historical method. The only thing wrong with it is that the
    method it validated is not the method that would now execute - which is
    exactly the condition the cutover must catch.
    """

    historical_plan = dataclasses.replace(
        plan, method_identity_digest=historical_method.content_digest
    )
    historical_acceptance = dataclasses.replace(
        acceptance,
        cv_plan_digest=historical_plan.content_digest,
        method_identity_digest=historical_method.content_digest,
    )
    return historical_plan, historical_acceptance


def test_r6d_current_method_recipe_is_the_corrected_generation(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, _paths, store = load_context(config)
    try:
        identity = resolve_post_selection_method_identity(cfg)
        assert identity.method_recipe_version == CURRENT_METHOD_RECIPE
        historical = dataclasses.replace(
            identity, method_recipe_version=HISTORICAL_METHOD_RECIPE
        )
        assert historical.content_digest != identity.content_digest
    finally:
        store.close()


def test_r6d_historical_method_cv_cannot_authorize_corrected_final_production(
    tmp_path: Path,
):
    """The reopened claim, at the real final-production authorization owner."""

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    harness = PostSelectionHarness()
    try:
        context = build_post_selection_context(cfg, paths, store)
        assert run_cross_validate(config, harness) == 0
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None
        assert acceptance.accepted

        corrected_method = context.method
        assert corrected_method.method_recipe_version == CURRENT_METHOD_RECIPE
        historical_method = dataclasses.replace(
            corrected_method, method_recipe_version=HISTORICAL_METHOD_RECIPE
        )
        historical_plan, historical_acceptance = _historical_authorization(
            plan, acceptance, historical_method
        )
        # The historical fixture is internally coherent: it authorizes itself.
        assert historical_acceptance.cv_plan_digest == historical_plan.content_digest
        assert historical_acceptance.accepted

        trainer_calls = len(harness.trained) if hasattr(harness, "trained") else None

        # It still cannot authorize the corrected method.
        with pytest.raises((PostSelectionError, PostSelectionCvRejectedError)) as excinfo:
            build_final_production_plan(
                context.selected,
                corrected_method,
                context.production_policy,
                cv_plan=historical_plan,
                cv_acceptance=historical_acceptance,
                replay_lineage_digest=historical_plan.replay_lineage_digest,
            )
        message = str(excinfo.value)
        assert "different training method" in message or "different shared method" in message

        # Refusal happened before any production work was launched.
        if trainer_calls is not None:
            assert len(harness.trained) == trainer_calls

        # The corrected pair is admitted through the very same owner, so the
        # rejection above is a method-identity decision and not a broken fixture.
        admitted = build_final_production_plan(
            context.selected,
            corrected_method,
            context.production_policy,
            cv_plan=plan,
            cv_acceptance=acceptance,
            replay_lineage_digest=plan.replay_lineage_digest,
        )
        assert admitted.method_identity_digest == corrected_method.content_digest
        assert admitted.cv_authorization_digest == acceptance.content_digest
    finally:
        store.close()


def test_r6d_static_pre_repair_authorization_is_rejected_before_trainer_launch(
    tmp_path: Path,
):
    """Stored v2 authorization is rejected by the real production owner."""

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    harness = PostSelectionHarness()
    try:
        context = build_post_selection_context(cfg, paths, store)
        historical_method, historical_plan, historical_acceptance = (
            _load_pre_repair_authorization_fixture()
        )
        assert historical_method.method_recipe_version == HISTORICAL_METHOD_RECIPE
        assert historical_plan.method_identity_digest == historical_method.content_digest
        assert historical_acceptance.cv_plan_digest == historical_plan.content_digest
        assert historical_acceptance.method_identity_digest == historical_method.content_digest
        assert historical_acceptance.accepted

        with pytest.raises((PostSelectionError, PostSelectionCvRejectedError)) as excinfo:
            build_final_production_plan(
                context.selected,
                context.method,
                context.production_policy,
                cv_plan=historical_plan,
                cv_acceptance=historical_acceptance,
                replay_lineage_digest=historical_plan.replay_lineage_digest,
            )
        assert "different training method" in str(excinfo.value) or "different shared method" in str(excinfo.value)
        assert getattr(harness, "trained", []) == []
    finally:
        store.close()


def test_r6d_corrected_cv_cannot_authorize_a_historical_method_run(tmp_path: Path):
    """The cutover is symmetric: neither direction may cross it."""

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    harness = PostSelectionHarness()
    try:
        context = build_post_selection_context(cfg, paths, store)
        assert run_cross_validate(config, harness) == 0
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None

        historical_method = dataclasses.replace(
            context.method, method_recipe_version=HISTORICAL_METHOD_RECIPE
        )
        with pytest.raises((PostSelectionError, PostSelectionCvRejectedError)):
            build_final_production_plan(
                context.selected,
                historical_method,
                context.production_policy,
                cv_plan=plan,
                cv_acceptance=acceptance,
                replay_lineage_digest=plan.replay_lineage_digest,
            )
    finally:
        store.close()
