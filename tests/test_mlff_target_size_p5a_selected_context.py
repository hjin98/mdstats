"""P5-A acceptance: the current selected-training entry and its lineage binding.

Every test drives the real P4 exposure boundary, the real CampaignStore, and the
real P1/P2/P3 owners. The question under test is always the same one: can
anything other than the *current* authenticated P4 SELECTED terminal result
become the basis of post-selection work?
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from tests._mlff_post_selection_fixture import (
    build_selected_campaign,
    load_context,
)

from mdstats.training_data.campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionBinding,
    PostSelectionError,
    PostSelectionStaleBindingError,
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_revision,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


def test_p5a_adapter_projects_the_exact_authenticated_selection(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.lifecycle is TargetSizeLifecycle.DIAGNOSTIC_COMPLETE

        context = load_current_selected_training_context(cfg, paths, store)
        assert isinstance(context, CurrentSelectedTrainingContext)
        (frozen,) = revision.state.frozen_entries
        n_selected = frozen.n_selected
        assert context.n_selected == n_selected

        # T_selected is the exact ordered pi_train prefix, not a resampling.
        definition = context.authorities.aggregate.definition
        expected = definition.training_order.candidate_membership(n_selected)
        assert context.selected_membership == expected
        assert context.selected_membership_digest == frozen.selected_membership_digest
        assert context.binding.campaign_generation == revision.state.generation
        # The target binding names the target and nothing else. The full frozen
        # entry's digest is deliberately *not* its parent: that digest covers
        # both role horizons and the selection provenance, so using it would
        # make every descendant depend transitively on inputs the binding is
        # defined to exclude.
        payload = context.binding.to_dict()
        for forbidden in (
            "frozen_selection_digest",
            "selection_source",
            "auto_diagnostic_digest",
            "cv_max_num_epochs",
            "production_max_num_epochs",
        ):
            assert forbidden not in payload
        assert payload["n_selected"] == n_selected
        assert payload["selected_membership_digest"] == (
            frozen.selected_membership_digest
        )
    finally:
        store.close()


def test_p5a_group_metadata_cannot_enlarge_the_selected_membership(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        authorities = context.authorities
        # Every selected frame belongs to at least one P1 relation group in this
        # fixture's population; none of that pulls an extra frame into
        # T_selected, whose size is decided upstream and only upstream.
        related = {
            uid
            for group in authorities.split_exclusion.groups
            for uid in group.frame_uids
        }
        assert related - set(context.selected_membership)
        assert len(context.selected_membership) == context.n_selected
    finally:
        store.close()


def test_p5a_post_selection_requires_an_admitted_freeze(tmp_path: Path):
    """A provisional proposal is not an entry point; only an admitted freeze is.

    This replaces the retired rule that a terminal automatic *scientific
    failure* blocked post-selection work. Diagnostic outcomes no longer gate the
    downstream campaign at all; what gates it is whether the operator's design
    has been admitted and frozen.
    """

    from mdstats.training_data.campaign_target_size_selection import (
        TargetSizeSelectionError,
        build_target_size_proposal,
        commit_target_size_proposal,
        resolve_provisional_horizons,
    )
    from mdstats.training_data.campaign_target_size_state import (
        SELECTION_SOURCE_MANUAL,
    )
    from mdstats.training_data.campaign_target_size_runtime import (
        load_prepared_target_size_generation,
    )

    config, _workspace = build_selected_campaign(tmp_path)

    # A fresh generation: prepared substrate, no proposal, no freeze.
    from tests._mlff_post_selection_fixture import rewrite_config

    rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    cfg, paths, store = load_context(config)
    try:
        revision = load_target_size_campaign_revision(store)
        assert (
            revision.state.frozen_entries is None
            and revision.state.provisional_entries == ()
        )
        with pytest.raises(TargetSizeSelectionError, match="No frozen target-size"):
            load_current_selected_training_context(cfg, paths, store)

        # Even a complete, valid provisional proposal is not an entry point.
        definition = load_prepared_target_size_generation(
            cfg, paths, store, revision
        ).aggregate.definition
        proposal = build_target_size_proposal(
            definition,
            target_size=int(definition.qualified_candidate_sizes[0]),
            selection_source=SELECTION_SOURCE_MANUAL,
            horizons=resolve_provisional_horizons(cfg),
        )
        commit_target_size_proposal(store, revision, proposal)
        with pytest.raises(TargetSizeSelectionError, match="No frozen target-size"):
            load_current_selected_training_context(cfg, paths, store)

        # Admission is the boundary, and it is the only thing that changes this.
        context = load_current_selected_training_context(
            cfg, paths, store, admit=True
        )
        assert context.n_selected == int(definition.qualified_candidate_sizes[0])
    finally:
        store.close()


def test_p5a_retained_g1_binding_is_stale_after_a_real_g2_prepare(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        g1 = load_current_selected_training_context(cfg, paths, store).binding
    finally:
        store.close()

    # A real scientific-identity change, then a real `prepare`, advances the
    # canonical generation exactly as production does.
    from tests._mlff_post_selection_fixture import rewrite_config

    rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0

    cfg, paths, store = load_context(config)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.generation > g1.campaign_generation
        # g2 has no terminal result yet, so post-selection entry fails closed and
        # the retained g1 binding cannot make it current.
        with pytest.raises(Exception):
            load_current_selected_training_context(cfg, paths, store)
    finally:
        store.close()


def test_p5a_binding_comparison_rejects_a_foreign_generation(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = load_current_selected_training_context(cfg, paths, store)
        foreign = PostSelectionBinding.from_dict(
            {
                **context.binding.to_dict(),
                "campaign_generation": context.binding.campaign_generation + 1,
                "content_digest": None,
            }
        )
        context.require_binding(context.binding)
        with pytest.raises(PostSelectionStaleBindingError):
            context.require_binding(foreign)
    finally:
        store.close()


def test_p5a_missing_derived_result_view_does_not_redirect_or_block(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        view = paths.results / "target-size-state.json"
        if view.is_file():
            view.unlink()
        context = load_current_selected_training_context(cfg, paths, store)
        assert context.n_selected > 0
        assert not view.is_file()
    finally:
        store.close()


def test_p5a_no_post_selection_module_reads_the_result_view_as_authority():
    """Structural: no P5 module parses the derived result JSON at all."""

    offenders: list[tuple[str, str]] = []
    for path in sorted(_TRAINING_DATA.glob("*post_selection*.py")):
        source = path.read_text(encoding="utf-8")
        for marker in ("target-size-state.json", "build_target_size_result_view"):
            if marker in source:
                offenders.append((path.name, marker))
    assert not offenders, offenders


def test_p5a_only_one_current_selected_training_adapter_exists():
    """Structural: exactly one owner reaches the P4 exposure boundary."""

    callers: list[str] = []
    for path in sorted(_TRAINING_DATA.glob("*post_selection*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(
                alias.name == "resolve_frozen_target_design"
                for alias in node.names
            ):
                callers.append(path.name)
    assert callers == ["campaign_post_selection.py"], callers
