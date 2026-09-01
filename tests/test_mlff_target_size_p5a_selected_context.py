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
        assert revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED

        context = load_current_selected_training_context(cfg, paths, store)
        assert isinstance(context, CurrentSelectedTrainingContext)
        n_selected = revision.state.terminal.selected_target_size
        assert context.n_selected == n_selected

        # T_selected is the exact ordered pi_train prefix, not a resampling.
        definition = context.authorities.aggregate.definition
        expected = definition.training_order.candidate_membership(n_selected)
        assert context.selected_membership == expected
        assert (
            context.selected_membership_digest
            == revision.state.terminal.selected_membership_digest
        )
        assert context.binding.campaign_generation == revision.state.generation
        assert context.binding.campaign_state_revision == revision.state_revision
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


def test_p5a_scientific_failure_terminal_cannot_enter_post_selection(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        # Rewrite only the persisted lifecycle: the loader must refuse before any
        # post-selection state exists, rather than trusting the stored label.
        from mdstats.training_data import campaign_target_size_terminal as terminal

        original = terminal.load_validated_target_size_terminal_result

        def _failed(cfg_, paths_, store_, *, expected_revision=None):
            validated = original(cfg_, paths_, store_, expected_revision=expected_revision)
            state = validated.revision.state
            object.__setattr__(
                state, "lifecycle", TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE
            )
            return validated

        terminal.load_validated_target_size_terminal_result = _failed
        try:
            with pytest.raises(PostSelectionError, match="SELECTED"):
                load_current_selected_training_context(cfg, paths, store)
        finally:
            terminal.load_validated_target_size_terminal_result = original
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
                alias.name == "expose_current_target_size_terminal_result"
                for alias in node.names
            ):
                callers.append(path.name)
    assert callers == ["campaign_post_selection.py"], callers
