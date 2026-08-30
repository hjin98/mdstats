"""P5-B acceptance: the acyclic method -> policy -> plan -> evidence hierarchy.

These tests exist to make one property observable: a policy identity is
computable *before* the work it authorizes, and therefore cannot contain that
work's results. The invalidation consequences the parent DAG requires follow
from that property, so they are asserted here too - a production horizon edit
must not disturb cross-validation, and a CV edit must not disturb production.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests._mlff_post_selection_fixture import (
    PRODUCTION_MAX_NUM_EPOCHS,
    build_selected_campaign,
    fixture_config_text,
    load_context,
)

from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    load_current_selected_training_context,
)
from mdstats.training_data.post_selection_cv_plan import (
    build_post_selection_cv_plan,
    build_selected_relation_projection,
)
from mdstats.training_data.post_selection_identity import (
    CV_AGGREGATION_ALL_REQUIRED,
    CV_DISPERSION_DIAGNOSTIC_ONLY,
    DEFAULT_CV_MAX_NUM_EPOCHS,
    cv_training_budget_policy,
    final_production_training_budget_policy,
    resolve_cv_validation_policy_identity,
    resolve_final_production_policy_identity,
    resolve_post_selection_method_identity,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


def _cfg_from(text: str) -> dict:
    import tomllib

    return tomllib.loads(text)


def _base_cfg(**replacements: str) -> dict:
    text = fixture_config_text().format(workspace="/tmp/w", training_root="/tmp/t")
    for old, new in replacements.items():
        marker = old.replace("__", " ")
        assert marker in text, marker
        text = text.replace(marker, new)
    return _cfg_from(text)


# --- the three identities are pure functions of configuration --------------


def test_p5b_policy_identities_resolve_before_any_numerical_work(tmp_path: Path):
    """No DATA7/DATA8/TRAIN2/EVAL2 artifact exists yet, and none is needed."""

    config, workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        method = resolve_post_selection_method_identity(cfg)
        cv_policy = resolve_cv_validation_policy_identity(cfg)
        production = resolve_final_production_policy_identity(cfg)
    finally:
        store.close()
    for identity in (method, cv_policy, production):
        assert identity.content_digest

    # The post-selection evidence root is only created by execution; resolving
    # the policies did not touch it.
    from mdstats.training_data.post_selection_store import post_selection_root

    assert not post_selection_root(paths, 1).exists()


def test_p5b_policy_serialization_contains_no_descendant_evidence():
    """Structural: no realized product is addressable inside a policy digest."""

    cfg = _base_cfg()
    method = resolve_post_selection_method_identity(cfg).to_dict()
    cv_policy = resolve_cv_validation_policy_identity(cfg).to_dict()
    production = resolve_final_production_policy_identity(cfg).to_dict()

    forbidden_everywhere = (
        "fold_membership",
        "training_frame_uids",
        "outer_evaluation_frame_uids",
        "checkpoint_monitor_frame_uids",
        "selected_membership_digest",
        "projection_digest",
        "relation_authority_digest",
        "fitted_weights_digest",
        "fitted_atomic_reference_digest",
        "runtime_summary_digest",
        "representative_candidate_identity",
        "cv_authorization_digest",
    )
    for payload in (method, cv_policy, production):
        for key in forbidden_everywhere:
            assert key not in payload, (key, payload["schema"])

    # Role-specific exclusions from the corrected hierarchy.
    for key in ("fold_count", "partition_seed", "cv_max_num_epochs",
                "production_max_num_epochs", "m3_membership_digest"):
        assert key not in method, key
    for key in ("m3_membership_digest", "m3_evaluation_size", "production_max_num_epochs"):
        assert key not in cv_policy, key
    for key in ("m3_membership_digest", "m3_evaluation_size", "cv_max_num_epochs",
                "fold_count", "partition_seed"):
        assert key not in production, key


def test_p5b_no_reverse_authority_from_evidence_to_policy():
    """Structural: the identity module imports no evidence/plan owner."""

    tree = ast.parse(
        (_TRAINING_DATA / "post_selection_identity.py").read_text(encoding="utf-8")
    )
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    descendants = {
        ".post_selection_cv_plan",
        ".post_selection_cv_acceptance",
        ".post_selection_production",
        ".post_selection_execution",
        ".post_selection_store",
        ".campaign_post_selection_runtime",
    }
    assert not (imported & descendants), sorted(imported & descendants)


# --- the parent invalidation DAG -------------------------------------------


def test_p5b_production_horizon_change_moves_only_the_production_policy():
    before = _base_cfg()
    after = _base_cfg(
        **{f"max_num_epochs__=__{PRODUCTION_MAX_NUM_EPOCHS}": "max_num_epochs = 17"}
    )
    assert (
        resolve_final_production_policy_identity(before).content_digest
        != resolve_final_production_policy_identity(after).content_digest
    )
    assert (
        resolve_post_selection_method_identity(before).content_digest
        == resolve_post_selection_method_identity(after).content_digest
    )
    assert (
        resolve_cv_validation_policy_identity(before).content_digest
        == resolve_cv_validation_policy_identity(after).content_digest
    )


def test_p5b_cv_policy_change_moves_only_the_cv_policy():
    before = _base_cfg()
    after = _base_cfg(**{"fold_count__=__2": "fold_count = 3"})
    assert (
        resolve_cv_validation_policy_identity(before).content_digest
        != resolve_cv_validation_policy_identity(after).content_digest
    )
    assert (
        resolve_final_production_policy_identity(before).content_digest
        == resolve_final_production_policy_identity(after).content_digest
    )
    assert (
        resolve_post_selection_method_identity(before).content_digest
        == resolve_post_selection_method_identity(after).content_digest
    )


def test_p5b_shared_method_change_moves_both_roles():
    before = _base_cfg()
    after = _base_cfg(**{"batch_size__=__4": "batch_size = 8"})
    assert (
        resolve_post_selection_method_identity(before).content_digest
        != resolve_post_selection_method_identity(after).content_digest
    )
    # The role-specific policies are unchanged - they never described the method.
    assert (
        resolve_cv_validation_policy_identity(before).content_digest
        == resolve_cv_validation_policy_identity(after).content_digest
    )
    assert (
        resolve_final_production_policy_identity(before).content_digest
        == resolve_final_production_policy_identity(after).content_digest
    )


def test_p5b_cv_budget_is_independent_of_the_production_horizon_and_of_n3():
    cfg = _base_cfg()
    method = resolve_post_selection_method_identity(cfg)
    cv_policy = resolve_cv_validation_policy_identity(cfg)
    production = resolve_final_production_policy_identity(cfg)

    cv_budget = cv_training_budget_policy(method, cv_policy)
    final_budget = final_production_training_budget_policy(method, production)
    assert cv_budget.planned_epochs == cv_policy.cv_max_num_epochs == 2
    assert final_budget.planned_epochs == PRODUCTION_MAX_NUM_EPOCHS
    # n3 for this fixture is the last configured fidelity epoch.
    n3 = int(cfg["target_data"]["size_convergence"]["fidelity_epochs"][-1])
    assert final_budget.planned_epochs != n3
    assert cv_budget.planned_epochs != n3

    # Raising only the production horizon leaves the CV budget where it was.
    raised = _base_cfg(
        **{f"max_num_epochs__=__{PRODUCTION_MAX_NUM_EPOCHS}": "max_num_epochs = 41"}
    )
    assert (
        cv_training_budget_policy(
            resolve_post_selection_method_identity(raised),
            resolve_cv_validation_policy_identity(raised),
        ).planned_epochs
        == 2
    )


def test_p5b_cv_budget_default_is_its_own_established_value():
    text = fixture_config_text().format(workspace="/tmp/w", training_root="/tmp/t")
    text = text.replace("max_num_epochs = 2\n", "")
    cfg = _cfg_from(text)
    policy = resolve_cv_validation_policy_identity(cfg)
    assert policy.cv_max_num_epochs == DEFAULT_CV_MAX_NUM_EPOCHS
    assert policy.cv_max_num_epochs != PRODUCTION_MAX_NUM_EPOCHS


# --- frozen acceptance semantics -------------------------------------------


def test_p5b_cv_policy_rejects_fewer_than_two_folds():
    for folds in (0, 1):
        cfg = _base_cfg(**{"fold_count__=__2": f"fold_count = {folds}"})
        with pytest.raises(PostSelectionError, match="at least two folds"):
            resolve_cv_validation_policy_identity(cfg)


def test_p5b_cv_policy_pins_the_frozen_aggregation_and_dispersion_rules():
    policy = resolve_cv_validation_policy_identity(_base_cfg())
    assert policy.aggregation_rule == CV_AGGREGATION_ALL_REQUIRED
    assert policy.dispersion_policy == CV_DISPERSION_DIAGNOSTIC_ONLY


def test_p5b_a_second_production_horizon_authority_is_refused():
    text = fixture_config_text().format(workspace="/tmp/w", training_root="/tmp/t")
    text = text.replace(
        "[post_selection.production]", "[post_selection.production]\nmax_num_epochs = 9"
    )
    with pytest.raises(PostSelectionError, match="second"):
        resolve_final_production_policy_identity(_cfg_from(text))


def test_p5b_cv_policy_refuses_a_target_size_derived_budget_field():
    text = fixture_config_text().format(workspace="/tmp/w", training_root="/tmp/t")
    text = text.replace("[post_selection.cv]", "[post_selection.cv]\nn3 = 10")
    with pytest.raises(PostSelectionError, match="independent of both target-size"):
        resolve_cv_validation_policy_identity(_cfg_from(text))


# --- plans depend on policies; policies never depend on plans ---------------


def test_p5b_cv_plan_moves_with_the_projection_while_the_policy_stands_still(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        method = resolve_post_selection_method_identity(cfg)
        policy = resolve_cv_validation_policy_identity(cfg)
        projection = build_selected_relation_projection(context)
        plan = build_post_selection_cv_plan(
            context, method, policy, projection=projection
        )

        # Same method, same resolved CV configuration, different authenticated
        # selected-only relation projection: the plan changes, the policy does
        # not, and the stale plan no longer validates.
        from mdstats.training_data.post_selection_cv_plan import (
            SelectedRelationProjection,
            validate_post_selection_cv_plan,
        )

        merged = SelectedRelationProjection(
            relation_authority_digest=projection.relation_authority_digest,
            frame_authority_digest=projection.frame_authority_digest,
            neutral_unit_catalog_digest=projection.neutral_unit_catalog_digest,
            selected_membership_digest=projection.selected_membership_digest,
            components=(
                tuple(sorted(projection.components[0] + projection.components[1])),
            )
            + projection.components[2:],
        )
        assert merged.content_digest != projection.content_digest
        assert (
            resolve_cv_validation_policy_identity(cfg).content_digest
            == policy.content_digest
        )
        with pytest.raises(PostSelectionError):
            validate_post_selection_cv_plan(plan, context, projection=merged)
    finally:
        store.close()
