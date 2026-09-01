"""P5-C acceptance: the complete, leakage-safe, selected-only CV plan.

Two properties are load-bearing here. The CV universe is *exactly* ``T_selected``
- an unselected sibling never enters it, and no eligible selected component
silently drops out. And leakage safety is inherited whole from the canonical P1
split-exclusion relation authority rather than rediscovered, so a pair of frames
connected only by a protected-event or lineage relation is as indivisible as a
pair inside one correlation unit.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests._mlff_post_selection_fixture import (
    build_selected_campaign,
    load_context,
)

from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    load_current_selected_training_context,
)
from mdstats.training_data.neutral_substrate.split_exclusion import (
    NeutralSplitExclusionEvidence,
    NeutralSplitExclusionGroup,
    RELATION_KIND_PROTECTED_EVENT,
    split_exclusion_component_digest,
)
from mdstats.training_data.post_selection_cv_plan import (
    PostSelectionCvFold,
    PostSelectionCvInfeasibleError,
    PostSelectionCvPlan,
    build_post_selection_cv_plan,
    build_selected_relation_projection,
    validate_post_selection_cv_plan,
)
from mdstats.training_data.post_selection_identity import (
    resolve_cv_validation_policy_identity,
    resolve_post_selection_method_identity,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


def _plan_environment(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    context = load_current_selected_training_context(cfg, paths, store)
    method = resolve_post_selection_method_identity(cfg)
    policy = resolve_cv_validation_policy_identity(cfg)
    return config, cfg, paths, store, context, method, policy


def test_p5c_cv_universe_is_exactly_t_selected(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        projection = build_selected_relation_projection(context)
        plan = build_post_selection_cv_plan(
            context, method, policy, projection=projection
        )
        selected = set(context.selected_membership)
        for fold in plan.folds:
            assert set(fold.all_frame_uids) == selected
            groups = (
                set(fold.training_frame_uids),
                set(fold.checkpoint_monitor_frame_uids),
                set(fold.outer_evaluation_frame_uids),
                set(fold.purged_frame_uids),
            )
            for index, left in enumerate(groups):
                for right in groups[index + 1 :]:
                    assert not (left & right)
            # No split-exclusion component is ever divided across roles: a
            # component is the indivisible unit of assignment.
            for component in projection.components:
                members = set(component)
                containing = [role for role in groups if members & role]
                assert len(containing) == 1
                assert members <= containing[0]
    finally:
        store.close()


def test_p5c_every_eligible_component_is_held_out_exactly_once(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        projection = build_selected_relation_projection(context)
        plan = build_post_selection_cv_plan(
            context, method, policy, projection=projection
        )
        held_out = list(plan.held_out_component_ids)
        assert sorted(held_out) == sorted(projection.component_identities)
        assert len(set(held_out)) == len(held_out)
    finally:
        store.close()


def test_p5c_an_unselected_protected_sibling_cannot_enter_the_universe(
    tmp_path: Path,
):
    """Adversarial: a selected frame is related to an unselected one.

    The relation is honoured - it simply has no in-universe endpoint to bind, so
    the CV population stays exactly the selected data instead of growing to keep
    the relation whole.
    """

    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        authorities = context.authorities
        order = authorities.aggregate.definition.training_order.frame_uids
        selected = set(context.selected_membership)
        unselected = next(uid for uid in order if uid not in selected)
        inside = context.selected_membership[0]

        evidence = NeutralSplitExclusionEvidence(
            dataset_id=authorities.split_exclusion.dataset_id,
            frame_authority_digest=authorities.split_exclusion.frame_authority_digest,
            unit_catalog_digest=authorities.split_exclusion.unit_catalog_digest,
            groups=authorities.split_exclusion.groups
            + (
                NeutralSplitExclusionGroup(
                    relation_kind=RELATION_KIND_PROTECTED_EVENT,
                    relation_key="p5c-adversarial-cross-boundary",
                    frame_uids=(inside, unselected),
                ),
            ),
        )
        object.__setattr__(context.authorities, "split_exclusion", evidence)
        object.__setattr__(
            context.binding, "split_exclusion_digest", evidence.content_digest
        )
        projection = build_selected_relation_projection(context)
        members = {uid for component in projection.components for uid in component}
        assert members == selected
        assert unselected not in members
    finally:
        store.close()


def test_p5c_a_relation_only_pair_stays_in_one_component(tmp_path: Path):
    """Two selected frames linked *only* by an added protected relation merge."""

    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        authorities = context.authorities
        baseline = build_selected_relation_projection(context)
        assert len(baseline.components) >= 2
        left = baseline.components[0][0]
        right = baseline.components[1][0]

        evidence = NeutralSplitExclusionEvidence(
            dataset_id=authorities.split_exclusion.dataset_id,
            frame_authority_digest=authorities.split_exclusion.frame_authority_digest,
            unit_catalog_digest=authorities.split_exclusion.unit_catalog_digest,
            groups=authorities.split_exclusion.groups
            + (
                NeutralSplitExclusionGroup(
                    relation_kind=RELATION_KIND_PROTECTED_EVENT,
                    relation_key="p5c-relation-only-link",
                    frame_uids=(left, right),
                ),
            ),
        )
        object.__setattr__(context.authorities, "split_exclusion", evidence)
        object.__setattr__(
            context.binding, "split_exclusion_digest", evidence.content_digest
        )
        merged = build_selected_relation_projection(context)
        assert len(merged.components) == len(baseline.components) - 1
        component = next(item for item in merged.components if left in item)
        assert right in component
        assert merged.component_of(left) == merged.component_of(right)
        assert merged.component_of(left) == split_exclusion_component_digest(component)
    finally:
        store.close()


def test_p5c_plan_construction_is_byte_deterministic(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        first = build_post_selection_cv_plan(context, method, policy)
        second = build_post_selection_cv_plan(context, method, policy)
        assert first.content_digest == second.content_digest
        assert first.to_dict() == second.to_dict()
        assert (
            PostSelectionCvPlan.from_dict(first.to_dict()).content_digest
            == first.content_digest
        )
    finally:
        store.close()


def test_p5c_infeasible_fold_count_rejects_before_any_training(tmp_path: Path):
    _config, cfg, _paths, store, context, method, _policy = _plan_environment(tmp_path)
    try:
        impossible = resolve_cv_validation_policy_identity(
            {
                "post_selection": {
                    "cv": {"fold_count": 64, "seeds": [11], "max_num_epochs": 2}
                }
            }
        )
        with pytest.raises(PostSelectionCvInfeasibleError, match="cannot support K"):
            build_post_selection_cv_plan(context, method, impossible)
    finally:
        store.close()


def test_p5c_an_omitted_selected_frame_rejects(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        plan = build_post_selection_cv_plan(context, method, policy)
        fold = next(
            item for item in plan.folds if len(item.outer_evaluation_frame_uids) > 1
        )
        trimmed = PostSelectionCvFold(
            fold_index=fold.fold_index,
            training_frame_uids=fold.training_frame_uids,
            checkpoint_monitor_frame_uids=fold.checkpoint_monitor_frame_uids,
            outer_evaluation_frame_uids=fold.outer_evaluation_frame_uids[:-1],
            purged_frame_uids=fold.purged_frame_uids,
            training_component_ids=fold.training_component_ids,
            checkpoint_monitor_component_ids=fold.checkpoint_monitor_component_ids,
            outer_evaluation_component_ids=fold.outer_evaluation_component_ids,
            purged_component_ids=fold.purged_component_ids,
        )
        others = tuple(item for item in plan.folds if item.fold_index != fold.fold_index)
        damaged = PostSelectionCvPlan(
            binding=plan.binding,
            method_identity_digest=plan.method_identity_digest,
            cv_policy_identity_digest=plan.cv_policy_identity_digest,
            relation_authority_digest=plan.relation_authority_digest,
            projection_digest=plan.projection_digest,
            fold_count=plan.fold_count,
            folds=(trimmed,) + others,
            required_cv_seeds=plan.required_cv_seeds,
        )
        with pytest.raises(PostSelectionError, match="silently omitted"):
            validate_post_selection_cv_plan(damaged, context)
    finally:
        store.close()


def test_p5c_duplicate_outer_holdout_rejects(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        plan = build_post_selection_cv_plan(context, method, policy)
        first, second = plan.folds[0], plan.folds[1]
        # Fold 1 claims fold 0's outer components as well: one component would be
        # held out twice while another is never evaluated.
        duplicated = PostSelectionCvFold(
            fold_index=second.fold_index,
            training_frame_uids=second.training_frame_uids,
            checkpoint_monitor_frame_uids=second.checkpoint_monitor_frame_uids,
            outer_evaluation_frame_uids=second.outer_evaluation_frame_uids,
            purged_frame_uids=second.purged_frame_uids,
            training_component_ids=second.training_component_ids,
            checkpoint_monitor_component_ids=second.checkpoint_monitor_component_ids,
            outer_evaluation_component_ids=first.outer_evaluation_component_ids,
            purged_component_ids=second.purged_component_ids,
        )
        with pytest.raises(PostSelectionError, match="exactly one outer fold"):
            PostSelectionCvPlan(
                binding=plan.binding,
                method_identity_digest=plan.method_identity_digest,
                cv_policy_identity_digest=plan.cv_policy_identity_digest,
                relation_authority_digest=plan.relation_authority_digest,
                projection_digest=plan.projection_digest,
                fold_count=plan.fold_count,
                folds=(first, duplicated),
                required_cv_seeds=plan.required_cv_seeds,
            )
    finally:
        store.close()


def test_p5c_a_changed_relation_authority_rejects_a_stale_plan(tmp_path: Path):
    _config, _cfg, _paths, store, context, method, policy = _plan_environment(tmp_path)
    try:
        plan = build_post_selection_cv_plan(context, method, policy)
        validate_post_selection_cv_plan(plan, context)

        authorities = context.authorities
        rebuilt = NeutralSplitExclusionEvidence(
            dataset_id=authorities.split_exclusion.dataset_id,
            frame_authority_digest=authorities.split_exclusion.frame_authority_digest,
            unit_catalog_digest=authorities.split_exclusion.unit_catalog_digest,
            groups=authorities.split_exclusion.groups
            + (
                NeutralSplitExclusionGroup(
                    relation_kind=RELATION_KIND_PROTECTED_EVENT,
                    relation_key="p5c-authority-change",
                    frame_uids=tuple(context.selected_membership[:2]),
                ),
            ),
        )
        object.__setattr__(context.authorities, "split_exclusion", rebuilt)
        object.__setattr__(
            context.binding, "split_exclusion_digest", rebuilt.content_digest
        )
        with pytest.raises(PostSelectionError, match="retired P1 split-exclusion"):
            validate_post_selection_cv_plan(plan, context)
    finally:
        store.close()


def test_p5c_no_local_relation_taxonomy_is_defined_by_post_selection():
    """Structural: P5 consumes P1 relation semantics and defines none."""

    offenders: list[tuple[str, str]] = []
    for path in sorted(_TRAINING_DATA.glob("*post_selection*.py")):
        source = path.read_text(encoding="utf-8")
        for marker in (
            "RELATION_KIND_",
            "NeutralSplitExclusionGroup(",
            "label_domain_id",
            "cross_validation_plans",
            "cv_not_performed",
        ):
            if marker in source:
                offenders.append((path.name, marker))
    assert not offenders, offenders

    # The one P1 entry point post-selection uses is the canonical closure owner.
    tree = ast.parse(
        (_TRAINING_DATA / "post_selection_cv_plan.py").read_text(encoding="utf-8")
    )
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "neutral_substrate.split_exclusion"
        for alias in node.names
    }
    assert imported == {
        "project_split_exclusion_constraint_components",
        "split_exclusion_component_digest",
    }, imported
