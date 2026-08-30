"""P5-G assembled integration: the complete current post-selection lifecycle.

One flow, through the real CLI entrypoints, the real campaign store, and the
real P1/P2/P3/P4/P5 owners:

`prepare` -> `select-target-size` -> `cross-validate` -> `train-production`
-> fresh-process reload -> re-resolved currentness.

Only MACE's numerical work is substituted, strictly below the accepted owner
boundary. Everything the assertions look at - authority, lineage, fold roles,
acceptance, freshness, namespaces, publication - is production behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests._mlff_post_selection_fixture import (
    PRODUCTION_MAX_NUM_EPOCHS,
    PostSelectionHarness,
    build_selected_campaign,
    load_context,
    run_cross_validate,
    run_train_production,
)

from mdstats.training_data.campaign_post_selection import (
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
)
from mdstats.training_data.post_selection_execution import (
    PostSelectionFittedPreparation,
    PostSelectionMaterialization,
)
from mdstats.training_data.post_selection_production import (
    frozen_m3_development_evidence,
)
from mdstats.training_data.post_selection_run_identity import PostSelectionRunRole
from mdstats.training_data.post_selection_store import (
    open_post_selection_store,
    post_selection_root,
)


def test_p5g_assembled_post_selection_lifecycle(tmp_path: Path, capsys):
    config, workspace = build_selected_campaign(tmp_path)

    _cfg, _paths, store = load_context(config)
    try:
        before = load_target_size_campaign_revision(store)
        before_terminal = before.state.terminal
        n_selected = before_terminal.selected_target_size
        selected_digest = before_terminal.selected_membership_digest
    finally:
        store.close()

    # 1. Cross-validate the frozen method on exactly the selected data.
    cv = PostSelectionHarness()
    assert run_cross_validate(config, cv) == 0
    output = capsys.readouterr().out
    assert "Cross-validated the exact selected dataset" in output

    # 2. Produce freshly on the full selected data under the accepted method.
    production = PostSelectionHarness()
    assert run_train_production(config, production) == 0
    output = capsys.readouterr().out
    assert "fresh production run" in output

    # 3. A fresh process re-resolves currentness from CampaignStore and exposes
    #    exactly the matching immutable descendants.
    cfg, paths, store = load_context(config)
    try:
        selected = load_current_selected_training_context(cfg, paths, store)
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        assert plan is not None and acceptance is not None and final_plan is not None

        # --- the selection is exactly what P4 froze, before and after --------
        assert selected.n_selected == n_selected
        assert selected.selected_membership_digest == selected_digest
        assert plan.binding.content_digest == selected.binding.content_digest

        # --- the CV universe is exactly T_selected, completely covered -------
        universe = set(selected.selected_membership)
        held_out: list[str] = []
        for fold in plan.folds:
            assert set(fold.all_frame_uids) == universe
            held_out.extend(fold.outer_evaluation_component_ids)
        assert len(set(held_out)) == len(held_out)

        # --- every required (seed, fold) passed the target-only predicate ----
        assert acceptance.accepted
        assert acceptance.rejection_reasons == ()
        assert len(acceptance.seed_acceptances) == len(plan.required_cv_seeds)
        for seed_record in acceptance.seed_acceptances:
            assert seed_record.accepted
            assert [item.fold_index for item in seed_record.fold_acceptances] == list(
                range(plan.fold_count)
            )
            for fold_record in seed_record.fold_acceptances:
                assert fold_record.accepted
                assert fold_record.outer_metric_value <= fold_record.acceptance_maximum
        assert acceptance.dispersion_policy == "diagnostic_only"

        # --- production descends from that exact acceptance and method -------
        assert final_plan.cv_authorization_digest == acceptance.content_digest
        assert final_plan.method_identity_digest == context.method.content_digest
        assert final_plan.cv_plan_digest == plan.content_digest
        assert final_plan.n_selected == n_selected
        assert final_plan.target_membership_digest == selected_digest
        assert final_plan.planned_epochs == PRODUCTION_MAX_NUM_EPOCHS

        # --- M3 is inherited lineage on the plan, not a production knob ------
        m3_size, m3_membership, m3_digest = frozen_m3_development_evidence(selected)
        assert final_plan.m3_evaluation_size == m3_size
        assert final_plan.m3_membership_digest == m3_digest
        assert "m3_membership_digest" not in context.production_policy.to_dict()
        assert not set(m3_membership) & universe

        # --- fold-local fitting saw only its own training frames -------------
        evidence = open_post_selection_store(paths, selected.binding)
        preparations = []
        for path in sorted((evidence.root / "objects").rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") == "mdstats.post-selection-fitted-preparation.v1":
                preparations.append(PostSelectionFittedPreparation.from_dict(payload))
        assert preparations
        by_membership = {item.membership_digest: item for item in preparations}
        assert len(by_membership) > 1  # folds fit different products
        for fold in plan.folds:
            training = set(fold.training_frame_uids)
            matching = [
                item for item in preparations if set(item.membership) == training
            ]
            assert matching, fold.fold_index
            for item in matching:
                assert not set(item.membership) & set(
                    fold.outer_evaluation_frame_uids
                )
                assert not set(item.membership) & set(
                    fold.checkpoint_monitor_frame_uids
                )

        # --- final production fitted from the full T_selected ---------------
        final_fits = [
            item for item in preparations if set(item.membership) == universe
        ]
        assert final_fits

        # --- run namespaces stay disjoint across roles -----------------------
        materializations = []
        for path in sorted((evidence.root / "objects").rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") == "mdstats.post-selection-materialization.v1":
                materializations.append(
                    PostSelectionMaterialization.from_dict(payload)
                )
        identities = [item.run_identity for item in materializations]
        assert len(set(identities)) == len(identities)
        assert set(cv.runs) | set(production.runs) == set(identities)
        assert not set(cv.runs) & set(production.runs)

        # --- P4 is byte-for-byte untouched by all of the above ---------------
        after = load_target_size_campaign_revision(store)
        assert after.state_revision == before.state_revision
        assert after.sequence == before.sequence
        assert after.state.terminal == before_terminal
        history = load_target_size_campaign_history(store)
        assert len(history) == before.sequence + 1
    finally:
        store.close()

    # 4. The post-selection evidence lives under the campaign-owned root for
    #    this exact generation, beside - never inside - the target-size root.
    root = post_selection_root(paths, before.state.generation)
    assert root.is_dir()
    assert (root / "objects").is_dir()
    assert (root / "runs").is_dir()


def test_p5g_production_run_plans_carry_the_final_production_role(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    production = PostSelectionHarness()
    assert run_train_production(config, production) == 0
    for request in production.requests:
        assert (
            PostSelectionRunRole(request.run_plan.run_role)
            is PostSelectionRunRole.FINAL_PRODUCTION
        )
        assert request.run_plan.planned_epochs == PRODUCTION_MAX_NUM_EPOCHS


def test_p5g_cv_run_plans_carry_the_cross_validation_role(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cv = PostSelectionHarness()
    assert run_cross_validate(config, cv) == 0
    seen = set()
    for request in cv.requests:
        assert (
            PostSelectionRunRole(request.run_plan.run_role)
            is PostSelectionRunRole.POST_SELECTION_CV
        )
        seen.add((request.run_plan.optimizer_seed, request.run_plan.fold_index))
    assert seen == {(11, 0), (11, 1)}
