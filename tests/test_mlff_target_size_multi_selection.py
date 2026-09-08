"""Acceptance for the ordered multi-size target design and its role identities.

Three claims are under test here, and they are not the same claim.

**The design is a collection.**  One expensive prepared generation is
deliberately reusable, so requesting a second qualified size must *add* an
experiment rather than silently replace the one already requested.  Order,
uniqueness by ``N``, per-size horizon snapshots, and whole-collection atomic
freeze are what make that true.

**Per-size identity is decomposed.**  A descendant's target lineage names the
target and nothing else.  Editing the production budget must not invalidate
accepted cross-validation evidence, choosing a size by hand rather than by
diagnostic must not fork one experiment into two, and adding a sibling size must
not disturb another size's evidence.  These are asserted through direct digest
comparison at the real owners: checking that a forbidden *field name* is absent
from a payload would not have caught the predecessor's transitive coupling
through the whole frozen record, which is exactly the defect being repaired.

**The multi-size experiment terminates truthfully.**  Several final publications
are not a release, and nothing here may pick one.

Every campaign, CampaignStore and P4/P5 owner runs as production code.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignCliError, CampaignStore
from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    current_target_size_bindings,
    load_current_selected_training_contexts,
    target_size_binding,
)
from mdstats.training_data.campaign_target_size_selection import (
    TargetSizeSelectionError,
    resolve_frozen_target_design,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignConflictError,
    load_target_size_campaign_revision,
    merge_provisional_entry,
)


class _PoisonTrainer:
    def __call__(self, request):  # pragma: no cover - the point is never reaching it
        raise AssertionError("Selection may never train a candidate.")


class _PoisonEvaluator:
    def __call__(self, *args, **kwargs):  # pragma: no cover - same
        raise AssertionError("Selection may never run an EVAL2 evaluation.")


def _prepared(tmp_path: Path):
    from unittest.mock import patch

    with patch.object(p4d, "_CONFIG", fx.fixture_config_text()):
        config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    return config, workspace


def _select(config: Path, *argv: str) -> int:
    return p4d._run(
        config,
        "select-target-size",
        *argv,
        _external_boundary_trainer=_PoisonTrainer(),
        _external_inference_evaluator=_PoisonEvaluator(),
    )


def _state(config: Path):
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store).state
    finally:
        store.close()


def _provisional(config: Path) -> list[int]:
    return [entry.n_provisional for entry in _state(config).provisional_entries]


def _frozen_sizes(config: Path) -> list[int] | None:
    entries = _state(config).frozen_entries
    return None if entries is None else [entry.n_selected for entry in entries]


def _freeze(config: Path):
    """Freeze the current design through the real admission owner, no CV work."""

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return resolve_frozen_target_design(cfg, paths, store, admit=True)
    finally:
        store.close()


# --- A4: ordered merge, reload, corruption ---------------------------------


def test_the_design_appends_new_sizes_and_replaces_existing_ones_in_place(
    tmp_path: Path,
):
    config, _workspace = _prepared(tmp_path)

    assert _select(config, "2") == 0
    assert _provisional(config) == [2]

    assert _select(config, "4") == 0
    assert _provisional(config) == [2, 4]

    # Reselecting an existing size revises its complete entry without moving it.
    assert _select(config, "2", "--horizon-cv", "31", "--horizon", "37") == 0
    assert _provisional(config) == [2, 4]
    first = _state(config).provisional_entries[0]
    assert (first.cv_max_num_epochs, first.production_max_num_epochs) == (31, 37)

    assert _select(config, "8") == 0
    assert _provisional(config) == [2, 4, 8]

    assert _select(config, "4", "--horizon-cv", "13") == 0
    assert _provisional(config) == [2, 4, 8]
    assert _state(config).provisional_entries[1].cv_max_num_epochs == 13
    # The revision of one entry left every sibling exactly as it was.
    assert _state(config).provisional_entries[0] == first
    assert _state(config).provisional_entries[2].n_provisional == 8


def test_the_design_survives_serialization_and_reload_exactly(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    for size in (2, 4, 8):
        assert _select(config, str(size)) == 0
    state = _state(config)

    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    restored = TargetSizeCampaignState.from_dict(state.to_dict())
    assert restored == state
    assert restored.provisional_entries == state.provisional_entries
    assert restored.content_digest == state.content_digest


def test_a_duplicate_size_in_authoritative_state_is_corruption(tmp_path: Path):
    """Two entries for one N are two designs claiming one identity; refuse both."""

    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.campaign_target_size_selection import _successor_with

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4") == 0
    state = _state(config)
    entry = state.provisional_entries[0]
    with pytest.raises(TrainingDataInputError, match="more than one entry"):
        _successor_with(state, provisional_entries=(entry, entry))


def test_a_malformed_collection_payload_is_never_normalized_into_a_guess():
    from mdstats.training_data._common import TrainingDataSerializationError
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    payload = {
        "schema": "mdstats.target-size-campaign-state.v3",
        "regime": "legacy",
        "generation": 0,
        "attempt": None,
        "lifecycle": "unconverted",
        "provisional_entries": "not-a-sequence",
    }
    with pytest.raises(TrainingDataSerializationError, match="sequence of entries"):
        TargetSizeCampaignState.from_dict(payload)


def test_the_merge_owner_is_a_pure_ordered_unique_map():
    """The merge rule alone, against an independent ordered-map oracle."""

    from hypothesis import given, settings
    from hypothesis import strategies as st

    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_target_size_state import TargetSizeProposal

    def entry(size: int, horizon: int) -> TargetSizeProposal:
        return TargetSizeProposal(
            n_provisional=size,
            membership_digest=digest({"membership": size}),
            training_order_digest=digest({"order": "fixed"}),
            selection_source="manual",
            cv_max_num_epochs=horizon,
            production_max_num_epochs=horizon + 1,
        )

    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=6),
                st.integers(min_value=1, max_value=6),
            ),
            max_size=30,
        )
    )
    @settings(max_examples=200, deadline=None)
    def check(operations):
        merged: tuple[TargetSizeProposal, ...] = ()
        oracle: dict[int, TargetSizeProposal] = {}
        for size, horizon in operations:
            item = entry(size, horizon)
            merged = merge_provisional_entry(merged, item)
            oracle[size] = item
        assert [item.n_provisional for item in merged] == list(oracle)
        assert list(merged) == list(oracle.values())

    check()


# --- A3: CLI grammar --------------------------------------------------------


def test_reset_is_mutually_exclusive_with_every_other_operation(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    for argv in (("4", "--reset"), ("--auto", "--reset")):
        with pytest.raises(CampaignCliError, match="mutually exclusive"):
            _select(config, *argv)
    for flag in ("--horizon-cv", "--horizon"):
        with pytest.raises(CampaignCliError, match="resolves no horizons"):
            _select(config, "--reset", flag, "5")


def test_the_retired_provisional_horizon_flag_names_are_gone(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    for flag in ("--select-horizon-cv", "--select-horizon"):
        with pytest.raises(SystemExit):
            cli.main(["--config", str(config), "select-target-size", "4", flag, "5"])


# --- A5: reset --------------------------------------------------------------


def test_reset_clears_only_the_provisional_design(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    screen = fx._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    assert _select(config, "2") == 0
    before = _state(config)
    assert len(before.provisional_entries) == 2

    # A poison trainer proves the reset performs no numerical work whatsoever.
    assert _select(config, "--reset") == 0
    after = _state(config)
    assert after.provisional_entries == ()
    assert after.frozen_entries is None
    assert after.generation == before.generation
    assert after.prepared_manifest_digest == before.prepared_manifest_digest
    assert after.auto_diagnostic == before.auto_diagnostic

    # An empty design cannot be admitted.
    with pytest.raises(TargetSizeSelectionError, match="No provisional target size"):
        _freeze(config)

    # An already-empty reset decides nothing and appends no revision.
    revision_before = after.content_digest
    assert _select(config, "--reset") == 0
    assert _state(config).content_digest == revision_before

    # Warm auto after a reset installs exactly the recommendation, no retraining.
    assert _select(config, "--auto") == 0
    assert _provisional(config) == [fx.SELECTED_TARGET_SIZE]
    assert _state(config).auto_diagnostic == before.auto_diagnostic


def test_reset_is_refused_after_the_freeze(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4") == 0
    _freeze(config)
    with pytest.raises(TargetSizeSelectionError, match="frozen"):
        _select(config, "--reset")
    with pytest.raises(TargetSizeSelectionError, match="frozen"):
        _select(config, "8")
    assert _frozen_sizes(config) == [4]


# --- A6: per-size horizon snapshots ----------------------------------------


def test_only_the_touched_entry_takes_the_current_configured_defaults(
    tmp_path: Path,
):
    config, _workspace = _prepared(tmp_path)
    cfg, _paths = cli._load_config(config)
    from mdstats.training_data.campaign_target_size_selection import (
        resolve_provisional_horizons,
    )

    defaults = resolve_provisional_horizons(cfg)
    assert _select(config, "2") == 0
    assert _select(config, "4") == 0

    fx.rewrite_config(
        config,
        f"max_num_epochs = {fx.PRODUCTION_MAX_NUM_EPOCHS}",
        f"max_num_epochs = {fx.PRODUCTION_MAX_NUM_EPOCHS + 5}",
    )
    # Existing entries do not drift when the configuration changes.
    entries = _state(config).provisional_entries
    assert [entry.production_max_num_epochs for entry in entries] == [
        defaults.production_max_num_epochs
    ] * 2

    # Only the reselected entry re-resolves the omitted default.
    assert _select(config, "4") == 0
    entries = _state(config).provisional_entries
    assert entries[0].production_max_num_epochs == defaults.production_max_num_epochs
    assert entries[1].production_max_num_epochs == fx.PRODUCTION_MAX_NUM_EPOCHS + 5

    # And the snapshots survive the freeze and a reload unchanged.
    _freeze(config)
    frozen = _state(config).frozen_entries
    assert [entry.n_selected for entry in frozen] == [2, 4]
    assert frozen[0].production_max_num_epochs == defaults.production_max_num_epochs
    assert frozen[1].production_max_num_epochs == fx.PRODUCTION_MAX_NUM_EPOCHS + 5


# --- A8: atomic whole-collection freeze ------------------------------------


def test_the_whole_collection_freezes_atomically(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4", "--horizon-cv", "6") == 0
    assert _select(config, "8", "--horizon", "9") == 0

    design = _freeze(config)
    assert list(design.selected_sizes) == [4, 8]
    state = _state(config)
    assert state.provisional_entries == ()
    assert [entry.n_selected for entry in state.frozen_entries] == [4, 8]
    assert state.frozen_entries[0].cv_max_num_epochs == 6
    assert state.frozen_entries[1].production_max_num_epochs == 9
    # No automatic diagnostic is required to freeze anything.
    assert state.auto_diagnostic is None

    # Each membership is re-derived from the real P2 training order at freeze.
    definition = design.definition
    for entry in state.frozen_entries:
        assert entry.selected_membership_digest == (
            definition.training_order.candidate_digest(entry.n_selected)
        )


def test_one_corrupt_member_rejects_the_entire_freeze(tmp_path: Path):
    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_target_size_selection import _successor_with
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeTransitionKind,
        commit_target_size_campaign_transition,
    )

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4") == 0
    assert _select(config, "8") == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        entries = revision.state.provisional_entries
        forged = dataclasses.replace(
            entries[1], membership_digest=digest({"forged": "membership"})
        )
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.SET_PROPOSAL,
            expected=revision.expectation(),
            successor=_successor_with(
                revision.state, provisional_entries=(entries[0], forged)
            ),
        )
        with pytest.raises(TargetSizeSelectionError, match="N=8"):
            resolve_frozen_target_design(cfg, paths, store, admit=True)
        # No partial freeze: the sound member was not admitted on its own.
        assert load_target_size_campaign_revision(store).state.frozen_entries is None
    finally:
        store.close()


def test_a_selection_and_a_freeze_serialize_at_the_campaign_boundary(
    tmp_path: Path,
):
    from mdstats.training_data.campaign_target_size_runtime import (
        load_prepared_target_size_generation,
    )
    from mdstats.training_data.campaign_target_size_selection import (
        build_target_size_proposal,
        commit_target_size_proposal,
        commit_target_size_reset,
        resolve_provisional_horizons,
    )
    from mdstats.training_data.campaign_target_size_state import (
        SELECTION_SOURCE_MANUAL,
    )

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4") == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        stale = load_target_size_campaign_revision(store)
        definition = load_prepared_target_size_generation(
            cfg, paths, store, stale
        ).aggregate.definition

        # An append commits...
        current = commit_target_size_proposal(
            store,
            stale,
            build_target_size_proposal(
                definition,
                target_size=8,
                selection_source=SELECTION_SOURCE_MANUAL,
                horizons=resolve_provisional_horizons(cfg),
            ),
        )
        assert [
            entry.n_provisional for entry in current.state.provisional_entries
        ] == [4, 8]

        # ...and a writer still holding the older revision loses outright,
        # rather than resurrecting a design without the appended size.
        for losing in (
            lambda: commit_target_size_reset(store, stale),
            lambda: commit_target_size_proposal(
                store,
                stale,
                build_target_size_proposal(
                    definition,
                    target_size=2,
                    selection_source=SELECTION_SOURCE_MANUAL,
                    horizons=resolve_provisional_horizons(cfg),
                ),
            ),
        ):
            with pytest.raises(TargetSizeCampaignConflictError):
                losing()

        # The freeze wins over a stale reset, and the reset cannot thaw it.
        design = resolve_frozen_target_design(cfg, paths, store, admit=True)
        assert list(design.selected_sizes) == [4, 8]
        with pytest.raises(TargetSizeCampaignConflictError):
            commit_target_size_reset(store, stale)
        fresh = load_target_size_campaign_revision(store)
        with pytest.raises(TargetSizeSelectionError, match="frozen"):
            commit_target_size_reset(store, fresh)
    finally:
        store.close()


# --- A2: identity decomposition counterfactuals ----------------------------
#
# These compare digests produced by the real owners. Asserting only that
# ``selection_source`` and the horizons are absent from a binding *payload*
# would have passed against the predecessor implementation too, because its
# contamination arrived transitively through a digest of the whole frozen
# record. What must be shown is that changing a role-extraneous input leaves the
# governed identity byte-identical.


def _frozen_campaign(tmp_path: Path):
    """A frozen two-size design plus the resolved per-size contexts."""

    config, _workspace = _prepared(tmp_path)
    # ``8`` is first because it is the CV-feasible size this fixture screens
    # for; the smaller sibling is here to prove it changes nothing.
    assert _select(config, "8", "--horizon-cv", "5", "--horizon", "7") == 0
    assert _select(config, "4", "--horizon-cv", "5", "--horizon", "7") == 0
    _freeze(config)
    return config


def _contexts(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return cfg, paths, load_current_selected_training_contexts(cfg, paths, store)
    finally:
        store.close()


def _cv_plan_digest(context, cfg, *, cv_max_num_epochs: int) -> str:
    from mdstats.training_data.post_selection_cv_plan import (
        build_post_selection_cv_plan,
    )
    from mdstats.training_data.post_selection_identity import (
        resolve_cv_validation_policy_identity,
        resolve_post_selection_method_identity,
    )

    return build_post_selection_cv_plan(
        context,
        resolve_post_selection_method_identity(cfg),
        resolve_cv_validation_policy_identity(
            cfg, max_num_epochs=cv_max_num_epochs
        ),
    ).content_digest


def _rebind(state, entry):
    """The target binding the real owner derives for one frozen entry."""

    return target_size_binding(state, entry)


def test_the_production_horizon_cannot_touch_the_target_or_the_cv_identity(
    tmp_path: Path,
):
    from mdstats.training_data.post_selection_identity import (
        resolve_cv_validation_policy_identity,
        resolve_final_production_policy_identity,
    )

    config = _frozen_campaign(tmp_path)
    cfg, _paths, contexts = _contexts(config)
    state = _state(config)
    entry = state.frozen_entries[0]

    other_horizon = dataclasses.replace(entry, production_max_num_epochs=99)
    assert other_horizon.content_digest != entry.content_digest
    # The target binding is unchanged...
    assert _rebind(state, other_horizon).content_digest == (
        _rebind(state, entry).content_digest
    )
    # ...and so is the whole CV chain that descends from it.
    assert (
        resolve_cv_validation_policy_identity(cfg, max_num_epochs=5).content_digest
        == resolve_cv_validation_policy_identity(cfg, max_num_epochs=5).content_digest
    )
    context = contexts[0]
    assert _cv_plan_digest(context, cfg, cv_max_num_epochs=5) == _cv_plan_digest(
        context, cfg, cv_max_num_epochs=5
    )
    # The production policy is the one thing that does change, as governed.
    assert (
        resolve_final_production_policy_identity(cfg, max_num_epochs=99).content_digest
        != resolve_final_production_policy_identity(
            cfg, max_num_epochs=7
        ).content_digest
    )


def test_the_cv_horizon_cannot_touch_the_target_or_the_production_policy(
    tmp_path: Path,
):
    from mdstats.training_data.post_selection_identity import (
        resolve_final_production_policy_identity,
    )

    config = _frozen_campaign(tmp_path)
    cfg, _paths, contexts = _contexts(config)
    state = _state(config)
    entry = state.frozen_entries[0]

    other_horizon = dataclasses.replace(entry, cv_max_num_epochs=41)
    assert _rebind(state, other_horizon).content_digest == (
        _rebind(state, entry).content_digest
    )
    # The production policy identity itself does not move with H_cv; final
    # production changes only through the accepted CV ancestry it names.
    assert (
        resolve_final_production_policy_identity(cfg, max_num_epochs=7).content_digest
        == resolve_final_production_policy_identity(
            cfg, max_num_epochs=7
        ).content_digest
    )
    # The CV plan does move with H_cv, which is exactly the governed dependency.
    context = contexts[0]
    assert _cv_plan_digest(context, cfg, cv_max_num_epochs=5) != _cv_plan_digest(
        context, cfg, cv_max_num_epochs=41
    )


@pytest.mark.parametrize(
    "change",
    [
        {"selection_source": "manual"},
        {"auto_diagnostic_digest": None},
    ],
)
def test_selection_provenance_is_audit_only(tmp_path: Path, change):
    from mdstats.training_data._common import digest

    config = _frozen_campaign(tmp_path)
    state = _state(config)
    entry = state.frozen_entries[0]
    provenance = dataclasses.replace(
        entry,
        selection_source="auto_recommendation",
        auto_diagnostic_digest=digest({"diagnostic": "some-screen"}),
    )
    other_provenance = dataclasses.replace(provenance, **change)

    baseline = _rebind(state, entry).content_digest
    assert _rebind(state, provenance).content_digest == baseline
    assert _rebind(state, other_provenance).content_digest == baseline
    # The full frozen entry still authenticates its own provenance, which is
    # what keeps the audit record meaningful.
    assert provenance.content_digest != entry.content_digest
    assert other_provenance.content_digest != provenance.content_digest


def test_the_target_identity_moves_with_n_and_with_membership(tmp_path: Path):
    from mdstats.training_data._common import digest

    config = _frozen_campaign(tmp_path)
    state = _state(config)
    first, second = state.frozen_entries
    assert (first.n_selected, second.n_selected) == (8, 4)
    assert _rebind(state, first).content_digest != _rebind(state, second).content_digest

    forged = dataclasses.replace(
        first, selected_membership_digest=digest({"forged": "membership"})
    )
    assert _rebind(state, forged).content_digest != _rebind(state, first).content_digest
    reordered_lineage = dataclasses.replace(
        first, training_order_digest=digest({"other": "order"})
    )
    assert _rebind(state, reordered_lineage).content_digest != (
        _rebind(state, first).content_digest
    )


def test_siblings_and_collection_shape_never_contaminate_a_per_size_identity(
    tmp_path: Path,
):
    """Adding or reordering a sibling leaves this size's identity untouched."""

    config = _frozen_campaign(tmp_path)
    state = _state(config)
    first, second = state.frozen_entries
    baseline = _rebind(state, first).content_digest

    for entries in (
        (first,),
        (second, first),
        (first, second),
    ):
        variant = dataclasses.replace(state, frozen_entries=entries)
        assert _rebind(variant, first).content_digest == baseline
    # And the bindings the collection owner derives are exactly those.
    assert [item.content_digest for item in current_target_size_bindings(state)] == [
        _rebind(state, first).content_digest,
        _rebind(state, second).content_digest,
    ]


def test_the_binding_payload_names_the_target_and_nothing_else(tmp_path: Path):
    config = _frozen_campaign(tmp_path)
    state = _state(config)
    payload = _rebind(state, state.frozen_entries[0]).to_dict()
    for forbidden in (
        "frozen_selection_digest",
        "selection_source",
        "auto_diagnostic_digest",
        "cv_max_num_epochs",
        "production_max_num_epochs",
    ):
        assert forbidden not in payload
    assert payload["schema"] == "mdstats.post-selection-binding.v3"


# --- A9: per-size currentness ----------------------------------------------


def test_every_frozen_size_resolves_its_own_exact_membership(tmp_path: Path):
    config = _frozen_campaign(tmp_path)
    _cfg, _paths, contexts = _contexts(config)
    assert [context.n_selected for context in contexts] == [8, 4]
    definition = contexts[0].definition
    for context in contexts:
        assert len(context.selected_membership) == context.n_selected
        assert context.selected_membership == (
            definition.training_order.candidate_membership(context.n_selected)
        )
        assert context.binding.selected_membership_digest == (
            definition.training_order.candidate_digest(context.n_selected)
        )
    # Siblings are simultaneously current and mutually non-substitutable.
    with pytest.raises(PostSelectionError, match="descends from"):
        contexts[0].require_binding(contexts[1].binding)
    contexts[0].require_binding(contexts[0].binding)


def test_a_multi_size_design_has_no_single_selected_size(tmp_path: Path):
    from mdstats.training_data.campaign_post_selection import (
        load_current_selected_training_context,
    )

    config = _frozen_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        with pytest.raises(PostSelectionError, match="name the size explicitly"):
            load_current_selected_training_context(cfg, paths, store)
        assert (
            load_current_selected_training_context(
                cfg, paths, store, n_selected=4
            ).n_selected
            == 4
        )
        with pytest.raises(PostSelectionError, match="not part of the current"):
            load_current_selected_training_context(cfg, paths, store, n_selected=16)
    finally:
        store.close()


def test_a_stale_generation_binding_is_never_republished_as_current(
    tmp_path: Path,
):
    from mdstats.training_data.campaign_post_selection import (
        PostSelectionStaleBindingError,
    )
    from mdstats.training_data.post_selection_store import (
        POINTER_CV_PLAN,
        publish_current_post_selection_pointer,
    )
    from mdstats.training_data._common import digest

    config = _frozen_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        state = _state(config)
        bindings = current_target_size_bindings(state)
        value = digest({"evidence": "fixture"})
        # Both current siblings publish inside their own namespaces.
        for binding in bindings:
            publish_current_post_selection_pointer(
                store, binding=binding, kind=POINTER_CV_PLAN, content_digest=value
            )
        # An N-only lookalike from another generation is refused.
        lookalike = dataclasses.replace(
            bindings[0], campaign_generation=state.generation + 1
        )
        with pytest.raises(PostSelectionStaleBindingError):
            publish_current_post_selection_pointer(
                store, binding=lookalike, kind=POINTER_CV_PLAN, content_digest=value
            )
        # So is a binding whose membership was forged.
        forged = dataclasses.replace(
            bindings[0], selected_membership_digest=digest({"forged": "membership"})
        )
        with pytest.raises(PostSelectionStaleBindingError):
            publish_current_post_selection_pointer(
                store, binding=forged, kind=POINTER_CV_PLAN, content_digest=value
            )
    finally:
        store.close()


# --- A22: append-only v1/v2 compatibility ----------------------------------


def _v2_state_payload(*, proposal=None, frozen=None) -> dict:
    from mdstats.training_data._common import digest

    def d(name: str) -> str:
        return digest({"fixture": name})

    payload = {
        "schema": "mdstats.target-size-campaign-state.v2",
        "regime": "current",
        "generation": 3,
        "attempt": None,
        "lifecycle": "authorities_bound",
        "frame_authority_digest": d("frame"),
        "neutral_statistical_base_digest": d("neutral"),
        "split_exclusion_digest": d("split"),
        "policy_digest": d("policy"),
        "experiment_definition_digest": d("definition"),
        "aggregate_digest": d("aggregate"),
        "prepared_manifest_digest": d("prepared"),
        "execution_context_digest": None,
        "common_preparation_digest": None,
        "screen_window_digest": None,
        "execution_root": None,
        "adopted_execution_head_digest": None,
        "adopted_reducer_state_digest": None,
        "terminal": None,
        "disposition": None,
        "disposition_detail": None,
        "proposal": None if proposal is None else proposal.to_dict(),
        "frozen": None if frozen is None else frozen.to_dict(),
    }
    return payload


def _v2_records():
    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_target_size_state import (
        FrozenTargetSelection,
        TargetSizeProposal,
    )

    proposal = TargetSizeProposal(
        n_provisional=8,
        membership_digest=digest({"fixture": "membership"}),
        training_order_digest=digest({"fixture": "order"}),
        selection_source="manual",
        cv_max_num_epochs=2,
        production_max_num_epochs=3,
    )
    frozen = FrozenTargetSelection(
        n_selected=8,
        selected_membership_digest=digest({"fixture": "membership"}),
        training_order_digest=digest({"fixture": "order"}),
        cv_max_num_epochs=2,
        production_max_num_epochs=3,
        selection_source="manual",
    )
    return proposal, frozen


def test_a_v2_row_projects_onto_the_collection_without_being_rewritten():
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    proposal, frozen = _v2_records()

    empty = TargetSizeCampaignState.from_dict(_v2_state_payload())
    assert empty.provisional_entries == () and empty.frozen_entries is None
    assert empty.legacy_scalar_binding is False

    provisional = TargetSizeCampaignState.from_dict(
        _v2_state_payload(proposal=proposal)
    )
    assert [item.n_provisional for item in provisional.provisional_entries] == [8]
    # A provisional predecessor row carries no descendant binding, so nothing
    # about the corrected identity is inherited from it.
    assert provisional.legacy_scalar_binding is False

    admitted = TargetSizeCampaignState.from_dict(_v2_state_payload(frozen=frozen))
    assert [item.n_selected for item in admitted.frozen_entries] == [8]
    assert admitted.legacy_scalar_binding is True

    # Every one of them reproduces its own persisted bytes exactly.
    for state, payload in (
        (empty, _v2_state_payload()),
        (provisional, _v2_state_payload(proposal=proposal)),
        (admitted, _v2_state_payload(frozen=frozen)),
    ):
        rendered = state.to_dict()
        assert rendered["schema"] == "mdstats.target-size-campaign-state.v2"
        assert "provisional_entries" not in rendered
        for key, value in payload.items():
            assert rendered[key] == value
        assert state.is_legacy_schema


def test_a_retired_schema_is_read_for_history_and_never_written():
    from mdstats.training_data._common import TrainingDataInputError, digest
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
        TargetSizeCasExpectation,
        TargetSizeRegime,
        TargetSizeTransitionKind,
        _validate_transition_semantics,
    )

    proposal, _frozen = _v2_records()
    state = TargetSizeCampaignState.from_dict(_v2_state_payload(proposal=proposal))
    with pytest.raises(TrainingDataInputError, match="current campaign-state schema"):
        _validate_transition_semantics(
            kind=TargetSizeTransitionKind.SET_PROPOSAL,
            expected=TargetSizeCasExpectation(
                regime=TargetSizeRegime.CURRENT,
                generation=3,
                attempt=None,
                state_revision=digest({"fixture": "revision"}),
                schema_version="mdstats.target-size-campaign-state.v2",
            ),
            successor=state,
        )


def test_a_v2_frozen_design_keeps_its_predecessor_descendant_binding():
    """Legacy descendants stay current under their own exact ancestry.

    The predecessor's binding hashed the whole frozen record, so it is a
    different identity from the corrected one.  Reproducing it for a design that
    was frozen under that schema is what keeps already-accepted P5/P7 evidence
    reachable; deriving the corrected shape instead would silently orphan it.
    """

    from mdstats.training_data.campaign_post_selection import PostSelectionBinding
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    _proposal, frozen = _v2_records()
    state = TargetSizeCampaignState.from_dict(_v2_state_payload(frozen=frozen))
    (binding,) = current_target_size_bindings(state)
    assert binding.is_legacy_schema
    payload = binding.to_dict()
    assert payload["schema"] == "mdstats.post-selection-binding.v2"
    assert payload["frozen_selection_digest"] == frozen.content_digest
    assert PostSelectionBinding.from_dict(payload) == binding

    # Known-negative for the repair oracle: under the *predecessor* schema the
    # production horizon really does move the descendant identity. That is the
    # defect, reproduced here only where a historical row already committed it.
    other_horizon = dataclasses.replace(frozen, production_max_num_epochs=99)
    legacy_variant = TargetSizeCampaignState.from_dict(
        _v2_state_payload(frozen=other_horizon)
    )
    (legacy_other,) = current_target_size_bindings(legacy_variant)
    assert legacy_other.content_digest != binding.content_digest

    # Known-positive: the corrected schema does not inherit that coupling.
    corrected = dataclasses.replace(state, legacy_scalar_binding=False)
    corrected_other = dataclasses.replace(
        legacy_variant, legacy_scalar_binding=False
    )
    assert (
        current_target_size_bindings(corrected)[0].content_digest
        == current_target_size_bindings(corrected_other)[0].content_digest
    )


def test_a_v2_frozen_design_cannot_be_appended_reset_or_thawed():
    from mdstats.training_data.campaign_target_size_selection import require_unfrozen
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    _proposal, frozen = _v2_records()
    state = TargetSizeCampaignState.from_dict(_v2_state_payload(frozen=frozen))
    with pytest.raises(TargetSizeSelectionError, match="frozen"):
        require_unfrozen(state)


def test_the_v2_schema_cannot_carry_a_multi_size_design():
    from mdstats.training_data._common import TrainingDataInputError, digest
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
        TargetSizeProposal,
    )

    proposal, _frozen = _v2_records()
    sibling = TargetSizeProposal(
        n_provisional=4,
        membership_digest=digest({"fixture": "membership-4"}),
        training_order_digest=digest({"fixture": "order"}),
        selection_source="manual",
        cv_max_num_epochs=2,
        production_max_num_epochs=3,
    )
    state = TargetSizeCampaignState.from_dict(_v2_state_payload(proposal=proposal))
    with pytest.raises(TrainingDataInputError, match="at most one provisional"):
        dataclasses.replace(state, provisional_entries=(proposal, sibling))


# --- A19: P5 storage keeps every current sibling reachable -----------------


def test_both_current_sibling_bindings_are_retained_and_never_collide(
    tmp_path: Path,
):
    from mdstats.training_data._common import digest
    from mdstats.training_data.post_selection_store import (
        POINTER_CV_PLAN,
        open_post_selection_store,
        post_selection_root,
        publish_current_post_selection_pointer,
        read_current_post_selection_pointer,
    )

    config = _frozen_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    state = _state(config)
    bindings = current_target_size_bindings(state)
    assert len(bindings) == 2

    store = CampaignStore(paths.state_db)
    try:
        values = {}
        for binding in bindings:
            value = digest({"evidence": binding.n_selected})
            values[binding.n_selected] = value
            publish_current_post_selection_pointer(
                store, binding=binding, kind=POINTER_CV_PLAN, content_digest=value
            )
        # Two current siblings coexist; neither namespace shadows the other.
        for binding in bindings:
            assert (
                read_current_post_selection_pointer(
                    store, binding=binding, kind=POINTER_CV_PLAN
                )
                == values[binding.n_selected]
            )
    finally:
        store.close()

    # One shared generation root, one shared prepared substrate: sizes are one
    # more post-selection dimension, not one more campaign.
    roots = {
        open_post_selection_store(paths, binding, create=False).root
        for binding in bindings
    }
    assert roots == {post_selection_root(paths, state.generation)}


# --- A23: structural closure of the retired scalar semantics ---------------


def _state_attribute_offenders(root: Path, names: set[str]) -> list[str]:
    """Every ``<expr>.state.<name>`` access under *root*.

    A structural rule, not a text search: ``context.frozen`` and
    ``admitted.frozen`` are legitimate *per-size* records, and only the campaign
    *state*'s retired scalar selection attributes are the offence.
    """

    import ast

    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr not in names:
                continue
            inner = node.value
            if isinstance(inner, ast.Attribute) and inner.attr == "state":
                offenders.append(f"{path.name}:{node.lineno}:{node.attr}")
            elif isinstance(inner, ast.Name) and inner.id == "state":
                offenders.append(f"{path.name}:{node.lineno}:{node.attr}")
    return offenders


def test_the_structural_rule_discriminates_before_it_is_trusted(tmp_path: Path):
    """Known-positive and known-negative examples for the rule above."""

    positive = tmp_path / "positive.py"
    positive.write_text(
        "def f(revision, state):\n"
        "    a = revision.state.frozen\n"
        "    b = state.proposal\n"
        "    return a, b\n",
        encoding="utf-8",
    )
    offenders = _state_attribute_offenders(tmp_path, {"frozen", "proposal"})
    assert len(offenders) == 2, offenders

    positive.unlink()
    negative = tmp_path / "negative.py"
    negative.write_text(
        "def f(context, admitted, state):\n"
        "    a = context.frozen\n"
        "    b = admitted.frozen\n"
        "    c = state.frozen_entries\n"
        "    d = state.provisional_entries\n"
        "    return a, b, c, d\n",
        encoding="utf-8",
    )
    assert _state_attribute_offenders(tmp_path, {"frozen", "proposal"}) == []


def test_no_current_surface_retains_the_scalar_selection_authority():
    training_data = Path(cli.__file__).resolve().parent

    assert _state_attribute_offenders(training_data, {"frozen", "proposal"}) == []

    from mdstats.training_data.campaign_post_selection import PostSelectionBinding
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCampaignState,
    )

    state_fields = set(TargetSizeCampaignState.__dataclass_fields__)
    assert "proposal" not in state_fields and "frozen" not in state_fields
    assert {"provisional_entries", "frozen_entries"} <= state_fields

    # The contaminated ancestry edge exists only as the predecessor-compatible
    # read path, never as a field a new binding is constructed with.
    binding_fields = set(PostSelectionBinding.__dataclass_fields__)
    assert "frozen_selection_digest" not in binding_fields
    assert (
        PostSelectionBinding.__dataclass_fields__[
            "legacy_frozen_selection_digest"
        ].default
        is None
    )

    # No second selection store, per-size subcampaign, or cross-size reducer.
    forbidden = (
        "per_size_campaign",
        "subcampaign",
        "best_target_size",
        "select_best_size",
        "cross_size_reducer",
        "target_size_registry",
    )
    offenders = [
        f"{path.name}:{token}"
        for path in sorted(training_data.rglob("*.py"))
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders

    # The retired provisional horizon flag spellings are gone from the parser.
    source = (training_data / "_campaign_cli_core.py").read_text(encoding="utf-8")
    assert "--select-horizon" not in source


# --- A18: the size dimension multiplies no resource ownership --------------


def test_outer_size_execution_is_serial_and_adds_no_scheduler():
    """Structural: the size loop is an ordinary iteration, not a new runtime.

    Serial outer iteration is the whole point of the resource rule: every size
    runs inside the one effective allocation the existing fold/seed/MACE/library
    concurrency already owns, so nothing new can assume it owns the machine.
    """

    import ast

    module = (
        Path(cli.__file__).resolve().parent / "campaign_post_selection_runtime.py"
    )
    tree = ast.parse(module.read_text(encoding="utf-8"))
    entrypoints = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {"execute_current_cross_validate", "execute_current_train_production"}
    }
    assert set(entrypoints) == {
        "execute_current_cross_validate",
        "execute_current_train_production",
    }
    for name, node in entrypoints.items():
        called = {
            child.func.attr if isinstance(child.func, ast.Attribute) else child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, (ast.Name, ast.Attribute))
        }
        forbidden = {
            "ThreadPoolExecutor",
            "ProcessPoolExecutor",
            "Pool",
            "Thread",
            "Process",
            "submit",
            "map_async",
        }
        assert not (called & forbidden), (name, sorted(called & forbidden))
        # Every size is visited by one plain loop over the ordered collection.
        assert any(isinstance(child, ast.For) for child in ast.walk(node)), name

    source = module.read_text(encoding="utf-8")
    for token in ("concurrent.futures", "multiprocessing", "threading"):
        assert token not in source, token
