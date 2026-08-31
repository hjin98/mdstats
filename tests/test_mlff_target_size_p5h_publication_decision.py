"""P5-H acceptance: the predecessor-owned final-publication decision.

Deciding which completed production seeds constitute the released product is a
predecessor act. It has to be taken from pre-qualification evidence alone,
before any downstream physical or release observation exists, or "the
committee" silently becomes "the members that survived qualification" - which
is member selection on release evidence.

These tests drive the real P1-P5 lifecycle. Only MACE training and the
numerical forward are substituted, through the already accepted P5 seams.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    fixture_config_text,
    load_context,
    run_cross_validate,
    run_train_production,
)

from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_final_production_completion,
    resolve_current_final_production_publication,
)
from mdstats.training_data.post_selection_publication import (
    COMMITTEE_ALL_QUALIFIED,
    COMMITTEE_SINGLE_BEST,
    FINAL_PUBLICATION_DECISION_POLICY_IDENTITY,
    FinalProductionPublicationDecision,
    decide_final_production_publication,
)


def _campaign(tmp_path: Path, *, seeds: str, committee: str | None = None, harness=None):
    text = fixture_config_text().replace("seeds = [5]", f"seeds = {seeds}")
    if committee is not None:
        text += f'committee_policy = "{committee}"\n'
    config, workspace = build_selected_campaign(tmp_path, config_text=text)
    active = PostSelectionHarness() if harness is None else harness
    assert run_cross_validate(config, active) == 0
    assert run_train_production(config, active) == 0
    return config, workspace, active


def _context(config: Path):
    cfg, paths, store = load_context(config)
    return build_post_selection_context(cfg, paths, store), store


def _decision(config: Path) -> FinalProductionPublicationDecision:
    context, store = _context(config)
    try:
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
        return decision
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Both committee policies
# ---------------------------------------------------------------------------


def test_p5h_all_qualified_publishes_every_admissible_required_seed(tmp_path: Path):
    config, _workspace, _harness = _campaign(tmp_path, seeds="[5, 6]")
    decision = _decision(config)
    assert decision.committee_policy == COMMITTEE_ALL_QUALIFIED
    assert decision.published_member_ids == ("seed-5", "seed-6")
    assert [item.optimizer_seed for item in decision.seed_evidence] == [5, 6]
    assert all(item.admissible for item in decision.seed_evidence)
    assert decision.decision_policy_identity == FINAL_PUBLICATION_DECISION_POLICY_IDENTITY
    # The decision binds the whole upstream lineage it descends from.
    assert decision.target_head_name
    assert decision.m3_membership_digest
    assert decision.cv_authorization_digest


def test_p5h_single_best_selects_the_canonical_best_seed(tmp_path: Path):
    """Deliberately different M3 target metrics decide the published member."""

    harness = PostSelectionHarness()
    text = fixture_config_text().replace("seeds = [5]", "seeds = [5, 6]")
    text += f'committee_policy = "{COMMITTEE_SINGLE_BEST}"\n'
    config, _workspace = build_selected_campaign(tmp_path, config_text=text)
    assert run_cross_validate(config, harness) == 0

    # Resolve the two required run identities, then give seed 6 the materially
    # better M3 target error before production trains.
    context, store = _context(config)
    try:
        from mdstats.training_data.post_selection_production import (
            build_final_production_plan,
            build_final_production_run_plan,
        )
        from mdstats.training_data.campaign_post_selection_runtime import (
            resolve_current_cv_acceptance,
            resolve_current_cv_plan,
        )

        plan = build_final_production_plan(
            context.selected,
            context.method,
            context.production_policy,
            cv_plan=resolve_current_cv_plan(context),
            cv_acceptance=resolve_current_cv_acceptance(context),
        )
        identities = {
            seed: build_final_production_run_plan(plan, optimizer_seed=seed).run_identity
            for seed in plan.required_final_seeds
        }
    finally:
        store.close()
    harness.run_force_offsets = {identities[5]: 0.020, identities[6]: 0.002}
    assert run_train_production(config, harness) == 0

    decision = _decision(config)
    assert decision.committee_policy == COMMITTEE_SINGLE_BEST
    assert decision.published_member_ids == ("seed-6",)
    # Both seeds' evidence is retained; only one is published.
    assert [item.optimizer_seed for item in decision.seed_evidence] == [5, 6]


def test_p5h_single_best_tie_is_deterministic_across_reopen(tmp_path: Path):
    """Identical M3 evidence still yields one deterministic answer."""

    config, _workspace, _harness = _campaign(
        tmp_path, seeds="[5, 6]", committee=COMMITTEE_SINGLE_BEST
    )
    first = _decision(config)
    assert len(first.published_member_ids) == 1
    for _ in range(3):
        again = _decision(config)
        assert again.content_digest == first.content_digest
        assert again.published_member_ids == first.published_member_ids
    # Re-deciding from the live completion reproduces the published decision,
    # so the answer does not depend on when the decision is taken.
    context, store = _context(config)
    try:
        completion = resolve_current_final_production_completion(context)
        recomputed = decide_final_production_publication(context, completion)
        assert recomputed.content_digest == first.content_digest
    finally:
        store.close()


# ---------------------------------------------------------------------------
# No downstream influence, no post-hoc shrinking
# ---------------------------------------------------------------------------


def test_p5h_publication_is_immutable_and_has_no_membership_api(tmp_path: Path):
    config, _workspace, _harness = _campaign(tmp_path, seeds="[5, 6]")
    decision = _decision(config)
    for name in dir(decision):
        assert not name.startswith(("add_", "remove_", "set_", "replace_", "shrink")), name
    with pytest.raises(Exception):
        decision.published_member_ids = ("seed-5",)  # type: ignore[misc]
    # A later downstream failure cannot shrink the published set: re-resolving
    # the current publication yields the same members regardless.
    assert _decision(config).published_member_ids == decision.published_member_ids


def test_p5h_decision_source_contains_no_downstream_evidence():
    """The decision inputs are structurally pre-qualification evidence only."""

    import ast

    from mdstats.training_data import post_selection_publication

    path = Path(post_selection_publication.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(str(node.module or ""))
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    for forbidden in ("qualification", "locked", "physical", "deployment", "dynamics"):
        assert not any(forbidden in name for name in imported), forbidden

    # No downstream identifier is referenced anywhere in the decision code, as
    # opposed to in its prose.
    referenced = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    for forbidden in (
        "qualification",
        "locked",
        "physical",
        "deployment",
        "dynamics",
        "relaxation",
        "calibration",
    ):
        offenders = sorted(name for name in referenced if forbidden in name.lower())
        assert not offenders, (forbidden, offenders)


# ---------------------------------------------------------------------------
# Fail-closed lineage
# ---------------------------------------------------------------------------


def test_p5h_corrupt_representative_evidence_fails_closed(tmp_path: Path):
    config, _workspace, _harness = _campaign(tmp_path, seeds="[5]")
    context, store = _context(config)
    try:
        completion = resolve_current_final_production_completion(context)
        evidence = completion.runs[0]
        path = context.evidence_store.object_path(evidence.representative_record_digest)
        assert path.is_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["admissible"] = not payload["admissible"]
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(Exception):
            decide_final_production_publication(context, completion)
    finally:
        store.close()


def test_p5h_missing_representative_evidence_is_recovered_or_fails_closed(tmp_path: Path):
    """A run root without durable records is re-evaluated, never synthesized."""

    config, _workspace, _harness = _campaign(tmp_path, seeds="[5]")
    context, store = _context(config)
    try:
        completion = resolve_current_final_production_completion(context)
        evidence = completion.runs[0]
        representative_path = context.evidence_store.object_path(
            evidence.representative_record_digest
        )
        metric_path = context.evidence_store.object_path(
            evidence.monitor_metric_record_digest
        )
        representative_path.unlink()
        metric_path.unlink()
    finally:
        store.close()

    # Recovery goes through the real EVAL2/provider owner and must reproduce the
    # exact digests the run evidence already bound.
    harness = PostSelectionHarness()
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(
            cfg, paths, store, inference_evaluator=harness.evaluate
        )
        completion = resolve_current_final_production_completion(context)
        recovered = decide_final_production_publication(context, completion)
        assert recovered.published_member_ids == ("seed-5",)
        assert representative_path.is_file() and metric_path.is_file()
    finally:
        store.close()


def test_p5h_stale_lineage_publication_is_historical_not_current(tmp_path: Path):
    """A decision that no longer binds current lineage is never current."""

    from tests._mlff_post_selection_fixture import rewrite_config

    config, _workspace, _harness = _campaign(
        tmp_path, seeds="[5, 6]", committee=COMMITTEE_SINGLE_BEST
    )
    before = _decision(config)
    assert before.committee_policy == COMMITTEE_SINGLE_BEST
    assert len(before.published_member_ids) == 1

    # Changing the committee policy changes which members the current product
    # is; the previously decided publication must not answer for it.
    rewrite_config(
        config,
        f'committee_policy = "{COMMITTEE_SINGLE_BEST}"',
        f'committee_policy = "{COMMITTEE_ALL_QUALIFIED}"',
    )
    context, store = _context(config)
    try:
        # The current-resolution chain refuses to answer at all: either the
        # final-plan owner rejects the moved policy first, or the publication
        # resolver rejects the retired lineage it binds. Both are correct; what
        # must never happen is exposing the old committee as the current one.
        with pytest.raises(PostSelectionError, match="stale|retired lineage"):
            resolve_current_final_production_publication(context)
    finally:
        store.close()

    # Republishing through the owner makes the new committee current, and the
    # old decision survives on disk as immutable historical evidence.
    harness = PostSelectionHarness()
    assert run_train_production(config, harness) == 0
    after = _decision(config)
    assert after.committee_policy == COMMITTEE_ALL_QUALIFIED
    assert after.published_member_ids == ("seed-5", "seed-6")
    context, store = _context(config)
    try:
        assert context.evidence_store.has(before.content_digest)
    finally:
        store.close()
