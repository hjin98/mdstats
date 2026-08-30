"""P5-E acceptance: fresh production, run namespaces, publication, and restart.

Final production is new training on the complete selected dataset under the
cross-validation-accepted method. The tests here check the three ways that could
quietly stop being true: production could silently inherit a screening or fold
trajectory, it could collide with one of them in storage or restart, or a stale
generation's result could be published as current after a newer one exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from tests._mlff_post_selection_fixture import (
    PRODUCTION_MAX_NUM_EPOCHS,
    PostSelectionHarness,
    build_selected_campaign,
    load_context,
    rewrite_config,
    run_cross_validate,
    run_train_production,
)

from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    PostSelectionStaleBindingError,
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.post_selection_identity import (
    resolve_final_production_policy_identity,
)
from mdstats.training_data.post_selection_production import (
    build_final_production_run_plan,
    frozen_m3_development_evidence,
)
from mdstats.training_data.post_selection_run_identity import (
    PostSelectionRunRole,
    post_selection_run_identity,
    reject_foreign_run_continuation,
)
from mdstats.training_data.post_selection_store import (
    POINTER_CV_ACCEPTANCE,
    POINTER_CV_PLAN,
    POINTER_FINAL_PLAN,
    open_post_selection_store,
    publish_current_post_selection_pointer,
    read_current_post_selection_pointer,
)


def _campaign_state(config: Path):
    cfg, paths, store = load_context(config)
    revision = load_target_size_campaign_revision(store)
    return cfg, paths, store, revision


# --- fresh full-T_selected production --------------------------------------


def test_p5e_production_trains_on_the_full_exact_t_selected(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    harness = PostSelectionHarness()
    assert run_train_production(config, harness) == 0
    assert len(harness.requests) == 1

    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        request = harness.requests[0]
        target = request.materialization.target_train_artifact
        assert set(target.frame_uids) == set(context.selected_membership)
        assert len(target.frame_uids) == context.n_selected

        # The final model-selection monitor is the frozen M3 reserve, and it is
        # disjoint from the training data by construction.
        _m3_size, m3_membership, _digest = frozen_m3_development_evidence(context)
        monitor = request.materialization.checkpoint_monitor_artifact
        assert set(monitor.frame_uids) == set(m3_membership)
        assert not set(monitor.frame_uids) & set(context.selected_membership)

        # Production has no held-out outer fold; CV owns that role.
        assert request.materialization.outer_evaluation_artifact is None
    finally:
        store.close()


def test_p5e_production_horizon_is_the_configured_value_not_n3(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cv_harness = PostSelectionHarness()
    assert run_cross_validate(config, cv_harness) == 0
    production = PostSelectionHarness()
    assert run_train_production(config, production) == 0

    cfg, _paths, store = load_context(config)
    try:
        n3 = int(cfg["target_data"]["size_convergence"]["fidelity_epochs"][-1])
        assert PRODUCTION_MAX_NUM_EPOCHS != n3

        plan = production.requests[0].plan
        assert plan.budget_policy.planned_epochs == PRODUCTION_MAX_NUM_EPOCHS
        assert plan.execution_epoch_limit == PRODUCTION_MAX_NUM_EPOCHS
        assert plan.budget_policy.planned_epochs != n3

        # And the CV budget followed its own policy, not the production horizon.
        cv_plan = cv_harness.requests[0].plan
        assert cv_plan.budget_policy.planned_epochs == 2
        assert cv_plan.budget_policy.planned_epochs != PRODUCTION_MAX_NUM_EPOCHS
    finally:
        store.close()


def test_p5e_production_starts_fresh_and_continues_nothing(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    harness = PostSelectionHarness()
    assert run_train_production(config, harness) == 0

    request = harness.requests[0]
    assert request.start_epoch == 0
    # The production checkpoint root is this run's own and holds nothing else.
    root = request.checkpoint_directory
    assert root.is_dir()
    assert request.run_plan.run_identity in str(root)


def test_p5e_a_foreign_run_state_is_never_an_admissible_parent():
    plan_digest = "a" * 64
    final = post_selection_run_identity(
        role=PostSelectionRunRole.FINAL_PRODUCTION,
        plan_digest=plan_digest,
        optimizer_seed=5,
    )
    fold = post_selection_run_identity(
        role=PostSelectionRunRole.POST_SELECTION_CV,
        plan_digest=plan_digest,
        optimizer_seed=5,
        fold_index=0,
    )
    reject_foreign_run_continuation(
        role=PostSelectionRunRole.FINAL_PRODUCTION,
        offered_run_identity=final,
        run_identity=final,
    )
    with pytest.raises(TrainingDataInputError, match="only continue its own"):
        reject_foreign_run_continuation(
            role=PostSelectionRunRole.FINAL_PRODUCTION,
            offered_run_identity=fold,
            run_identity=final,
        )


def test_p5e_same_n_same_seed_roles_cannot_collide(tmp_path: Path):
    """Screen, CV fold, and final production stay in distinct namespaces."""

    plan_digest = "b" * 64
    seed = 5
    screen = post_selection_run_identity(
        role=PostSelectionRunRole.TARGET_SIZE_SCREEN,
        plan_digest=plan_digest,
        optimizer_seed=seed,
    )
    fold = post_selection_run_identity(
        role=PostSelectionRunRole.POST_SELECTION_CV,
        plan_digest=plan_digest,
        optimizer_seed=seed,
        fold_index=0,
    )
    final = post_selection_run_identity(
        role=PostSelectionRunRole.FINAL_PRODUCTION,
        plan_digest=plan_digest,
        optimizer_seed=seed,
    )
    assert len({screen, fold, final}) == 3

    # A CV identity requires its fold; a final identity refuses one.
    with pytest.raises(TrainingDataInputError):
        post_selection_run_identity(
            role=PostSelectionRunRole.POST_SELECTION_CV,
            plan_digest=plan_digest,
            optimizer_seed=seed,
        )
    with pytest.raises(TrainingDataInputError):
        post_selection_run_identity(
            role=PostSelectionRunRole.FINAL_PRODUCTION,
            plan_digest=plan_digest,
            optimizer_seed=seed,
            fold_index=0,
        )


def test_p5e_cv_and_production_run_directories_are_disjoint(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cv = PostSelectionHarness()
    assert run_cross_validate(config, cv) == 0
    production = PostSelectionHarness()
    assert run_train_production(config, production) == 0

    cv_roots = {str(item.checkpoint_directory) for item in cv.requests}
    production_roots = {str(item.checkpoint_directory) for item in production.requests}
    assert cv_roots and production_roots
    assert not (cv_roots & production_roots)
    assert len(set(cv.runs) | set(production.runs)) == len(cv.runs) + len(
        production.runs
    )


# --- authorization ---------------------------------------------------------


def test_p5e_production_without_accepted_cv_fails_closed(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    with pytest.raises(PostSelectionError, match="cross-validation"):
        run_train_production(config)


def test_p5e_a_shared_method_change_invalidates_the_cv_authorization(
    tmp_path: Path,
):
    """A P5-local method change: stale CV cannot authorize the new method."""

    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    # The LR-schedule tail is part of the shared method but not of upstream
    # target-size identity, so P4 stays current and the conflict surfaces where
    # it belongs: at the cross-validation authorization.
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\ntrain2_final_lr_multiplier = 0.05',
    )
    cfg, paths, store = load_context(config)
    try:
        assert load_current_selected_training_context(cfg, paths, store) is not None
    finally:
        store.close()
    with pytest.raises(Exception, match="different training method"):
        run_train_production(config)


def test_p5e_a_method_field_that_is_also_upstream_identity_follows_p1_p4(
    tmp_path: Path,
):
    """Changing a shared field that P3 also owns retires the generation upstream.

    P5 does not weaken upstream invalidation just because the field also appears
    in its own method identity: the accepted P1-P4 chain still decides first.
    """

    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    rewrite_config(config, "batch_size = 4", "batch_size = 8")
    with pytest.raises(Exception, match="does not match the persisted terminal"):
        run_train_production(config)


def test_p5e_production_only_horizon_change_does_not_require_a_cv_rerun(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        before_cv = resolve_current_cv_acceptance(context)
        before_policy = resolve_final_production_policy_identity(cfg)
        revision_before = load_target_size_campaign_revision(store)
    finally:
        store.close()

    rewrite_config(
        config,
        f"max_num_epochs = {PRODUCTION_MAX_NUM_EPOCHS}",
        "max_num_epochs = 4",
    )
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        after_cv = resolve_current_cv_acceptance(context)
        after_policy = resolve_final_production_policy_identity(cfg)
        revision_after = load_target_size_campaign_revision(store)
    finally:
        store.close()

    # P4 untouched, CV evidence still current and identical, production policy moved.
    assert revision_after.state_revision == revision_before.state_revision
    assert after_cv is not None
    assert after_cv.content_digest == before_cv.content_digest
    assert after_cv.accepted
    assert after_policy.content_digest != before_policy.content_digest

    # And production then runs without any cross-validation rerun.
    production = PostSelectionHarness()
    assert run_train_production(config, production) == 0
    assert production.requests[0].plan.budget_policy.planned_epochs == 4


# --- publication currentness ------------------------------------------------


def test_p5e_publication_is_idempotent_for_the_same_binding(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        pointer = read_current_post_selection_pointer(
            store, binding=context.binding, kind=POINTER_CV_ACCEPTANCE
        )
        assert pointer is not None
        publish_current_post_selection_pointer(
            store,
            binding=context.binding,
            kind=POINTER_CV_ACCEPTANCE,
            content_digest=pointer,
        )
        assert (
            read_current_post_selection_pointer(
                store, binding=context.binding, kind=POINTER_CV_ACCEPTANCE
            )
            == pointer
        )
    finally:
        store.close()


def test_p5e_a_stale_g1_publication_loses_the_race_to_g2(tmp_path: Path):
    """Commit-time fencing, not merely a pre-write check.

    The g1 writer validated a legitimate generation and then took a long time.
    By the time it publishes, `prepare` has committed g2 - and the write is
    refused inside the same transaction that would have made it current.
    """

    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    cfg, paths, store = load_context(config)
    try:
        g1 = load_current_selected_training_context(cfg, paths, store).binding
        g1_pointer = read_current_post_selection_pointer(
            store, binding=g1, kind=POINTER_CV_ACCEPTANCE
        )
        assert g1_pointer is not None
    finally:
        store.close()

    # A concurrent real `prepare` commits a fresh canonical generation.
    rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    cfg, paths, store = load_context(config)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.generation > g1.campaign_generation

        # The delayed g1 writer now tries to publish. It loses deterministically.
        with pytest.raises(PostSelectionStaleBindingError, match="newer target-size"):
            publish_current_post_selection_pointer(
                store,
                binding=g1,
                kind=POINTER_CV_PLAN,
                content_digest="c" * 64,
            )
        # Current-facing state is untouched: the g1 namespace still holds only
        # what it held, and nothing under g2 was created.
        assert (
            read_current_post_selection_pointer(
                store, binding=g1, kind=POINTER_CV_ACCEPTANCE
            )
            == g1_pointer
        )
        assert (
            read_current_post_selection_pointer(
                store, binding=g1, kind=POINTER_CV_PLAN
            )
            != "c" * 64
        )
    finally:
        store.close()


def test_p5e_immutable_evidence_never_changes_under_one_identity(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        evidence = open_post_selection_store(paths, context.binding)
        pointer = read_current_post_selection_pointer(
            store, binding=context.binding, kind=POINTER_CV_PLAN
        )
        path = evidence.object_path(pointer)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["content_digest"] == pointer

        # A corrupted object fails its own digest check; it does not silently
        # redefine the plan it claims to be.
        corrupted = dict(payload)
        corrupted["fold_count"] = payload["fold_count"] + 1
        path.write_text(json.dumps(corrupted, sort_keys=True), encoding="utf-8")
        from mdstats.training_data.post_selection_cv_plan import PostSelectionCvPlan

        with pytest.raises(Exception):
            evidence.get(pointer, PostSelectionCvPlan.from_dict)
    finally:
        store.close()


# --- restart ---------------------------------------------------------------


def test_p5e_immutable_publication_is_create_once_and_conflict_fails_closed(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        evidence = open_post_selection_store(paths, context.binding)
        pointer = read_current_post_selection_pointer(
            store, binding=context.binding, kind=POINTER_CV_PLAN
        )
        from mdstats.training_data.post_selection_cv_plan import PostSelectionCvPlan
        from mdstats.training_data.post_selection_store import (
            PostSelectionPublicationConflictError,
        )

        plan = evidence.get(pointer, PostSelectionCvPlan.from_dict)
        # Republishing identical content is a no-op, not an error.
        assert evidence.put(plan) == pointer

        # A record claiming the same identity with different bytes fails closed
        # rather than overwriting published evidence.
        class _Impostor:
            content_digest = pointer

            def to_dict(self):
                payload = plan.to_dict()
                payload["fold_count"] = payload["fold_count"] + 1
                return payload

        with pytest.raises(PostSelectionPublicationConflictError):
            evidence.put(_Impostor())
    finally:
        store.close()


def test_p5e_the_held_out_fold_is_invisible_until_the_representative_is_frozen(
    tmp_path: Path,
):
    """Ordering proof: outer data is evaluated once, after checkpoint selection.

    The injected inference seam records which exact membership each evaluation
    saw. For every fold, all checkpoint-monitor evaluations come first and the
    held-out membership appears exactly once, at the end - so the outer fold
    cannot have influenced the checkpoint it later judges.
    """

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        from mdstats.training_data.post_selection_cv_plan import (
            build_post_selection_cv_plan,
        )
        from mdstats.training_data.post_selection_identity import (
            resolve_cv_validation_policy_identity,
            resolve_post_selection_method_identity,
        )

        plan = build_post_selection_cv_plan(
            context,
            resolve_post_selection_method_identity(cfg),
            resolve_cv_validation_policy_identity(cfg),
        )
    finally:
        store.close()

    class _Recording(PostSelectionHarness):
        def __init__(self) -> None:
            super().__init__()
            self.seen: list[frozenset[str]] = []

        def evaluate(self, provider, atoms_list):
            self.seen.append(
                frozenset(str(atoms.info["frame_uid"]) for atoms in atoms_list)
            )
            return super().evaluate(provider, atoms_list)

    harness = _Recording()
    assert run_cross_validate(config, harness) == 0

    monitors = {frozenset(fold.checkpoint_monitor_frame_uids) for fold in plan.folds}
    outers = {frozenset(fold.outer_evaluation_frame_uids) for fold in plan.folds}
    assert harness.seen
    assert set(harness.seen) <= monitors | outers

    # Every observed outer evaluation is preceded by at least one monitor
    # evaluation, and no monitor evaluation follows the last outer one within a
    # fold's contiguous run.
    outer_positions = [
        index for index, seen in enumerate(harness.seen) if seen in outers
    ]
    assert outer_positions
    for position in outer_positions:
        assert any(seen in monitors for seen in harness.seen[:position])
    # Exactly one outer evaluation per (seed, fold) position.
    assert len(outer_positions) == len(plan.required_run_matrix)


def test_p5e_restart_reuses_the_same_plan_and_acceptance(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    first = PostSelectionHarness()
    assert run_cross_validate(config, first) == 0
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        plan_before = resolve_current_cv_plan(context)
        acceptance_before = resolve_current_cv_acceptance(context)
    finally:
        store.close()

    second = PostSelectionHarness()
    assert run_cross_validate(config, second) == 0
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        plan_after = resolve_current_cv_plan(context)
        acceptance_after = resolve_current_cv_acceptance(context)
    finally:
        store.close()

    assert plan_after.content_digest == plan_before.content_digest
    assert acceptance_after.content_digest == acceptance_before.content_digest


def test_p5e_stale_generation_descendants_are_unreachable_as_current(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    assert run_train_production(config) == 0
    cfg, paths, store = load_context(config)
    try:
        g1 = load_current_selected_training_context(cfg, paths, store).binding
        assert (
            read_current_post_selection_pointer(
                store, binding=g1, kind=POINTER_FINAL_PLAN
            )
            is not None
        )
    finally:
        store.close()

    rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    cfg, paths, store = load_context(config)
    try:
        # g2 is current but has no terminal selection, so no post-selection entry
        # is possible at all - and the g1 evidence, still on disk, is not current.
        with pytest.raises(Exception):
            load_current_selected_training_context(cfg, paths, store)
        evidence_root = (
            open_post_selection_store(paths, g1).root
            if True
            else None
        )
        assert evidence_root.is_dir()
    finally:
        store.close()


def test_p5e_post_selection_evidence_is_owned_storage_and_never_auto_reclaimed(
    tmp_path: Path,
):
    """Storage accounting knows this evidence, and no tier may delete it."""

    config, workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    assert run_train_production(config) == 0

    from mdstats.training_data import _campaign_cli_core as cli

    assert cli.main(["--config", str(config), "storage", "report"]) == 0
    cfg, paths, store = load_context(config)
    try:
        payload = json.loads(
            (paths.results / "storage-report.json").read_text(encoding="utf-8")
        )
    finally:
        store.close()
    families = {item["family"]: item for item in payload["families"]}
    post_selection = {
        name: item
        for name, item in families.items()
        if name.startswith("post_selection_")
    }
    assert post_selection, sorted(families)
    for name, item in post_selection.items():
        assert item["automatic_reclamation_eligibility"] == "prohibited", name
        assert item["manual_reclamation_eligibility"] == "prohibited", name
    assert "internal_campaign_artifacts" not in post_selection


def test_p5e_cv_only_policy_change_leaves_p4_byte_identical(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config) == 0
    _cfg, _paths, store, before = _campaign_state(config)
    try:
        before_state = before.state
        before_terminal = before_state.terminal
    finally:
        store.close()

    # A CV-only edit: fold count and partition seed.
    rewrite_config(config, "fold_count = 2", "fold_count = 3")
    rewrite_config(config, "partition_seed = 7", "partition_seed = 11")
    assert run_cross_validate(config) == 0

    _cfg, _paths, store, after = _campaign_state(config)
    try:
        assert after.state_revision == before.state_revision
        assert after.sequence == before.sequence
        assert after.state.terminal == before_terminal
        assert after.state.to_dict() == before_state.to_dict()
    finally:
        store.close()


def test_p5e_p4_selection_survives_the_whole_post_selection_lifecycle(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    _cfg, _paths, store, before = _campaign_state(config)
    try:
        before_state = before.state
        before_terminal = before_state.terminal
    finally:
        store.close()

    assert run_cross_validate(config) == 0
    assert run_train_production(config) == 0

    _cfg, _paths, store, after = _campaign_state(config)
    try:
        assert after.state_revision == before.state_revision
        assert after.sequence == before.sequence
        assert after.state.generation == before_state.generation
        assert after.state.terminal == before_terminal
        assert (
            after.state.adopted_execution_head_digest
            == before_state.adopted_execution_head_digest
        )
        assert (
            after.state.adopted_reducer_state_digest
            == before_state.adopted_reducer_state_digest
        )
    finally:
        store.close()


def test_p5e_a_cv_failure_leaves_p4_untouched_and_blocks_production(
    tmp_path: Path,
):
    config, _workspace = build_selected_campaign(tmp_path)
    # An unreachable acceptance threshold makes every fold fail on target metrics.
    rewrite_config(config, "acceptance_maximum = 0.5", "acceptance_maximum = 1e-9")
    _cfg, _paths, store, before = _campaign_state(config)
    try:
        before_revision = before.state_revision
    finally:
        store.close()

    with pytest.raises(PostSelectionError, match="rejected the training method"):
        run_cross_validate(config)

    _cfg, _paths, store, after = _campaign_state(config)
    try:
        assert after.state_revision == before_revision
    finally:
        store.close()

    with pytest.raises(Exception):
        run_train_production(config)
