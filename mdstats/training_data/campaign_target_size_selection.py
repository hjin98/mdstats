"""The operator-owned target-size design: provisional collection, then freeze.

The automatic screen used to be the only thing allowed to decide how much target
data downstream training would use.  It no longer is.  Its short-horizon
force-RMSE comparison is evidence about one configured screening protocol, not
proof that a size is asymptotically right, and the product must not let that
proxy masquerade as the experimental-design decision.

So the decision lives here instead, in two clearly separated phases:

.. code-block:: text

    select-target-size <N> | --auto   ->  merge one complete per-size entry
                                          (N, T_N identity, H_cv, H_prod) into
                                          the ordered provisional design

    select-target-size --reset        ->  clear the provisional design

    cross-validate                    ->  freeze: the *complete* ordered design
                                          becomes immutable downstream ancestry

The design is a collection, not a single choice, because one expensive prepared
generation is deliberately reusable: an operator comparing behaviour across
qualified sizes must be able to request several longer-horizon experiments from
it without the newest command erasing the previous request.  A new ``N`` is
appended; an ``N`` already in the design has its complete entry replaced in
place, keeping its position.  Empty is the canonical unselected state.

Between selection and freeze the operator may change their mind freely; after
the freeze, nothing here can change the design at all.  Each entry is complete
when it is set: both role horizons are resolved to explicit values at that
moment, so a later ``campaign.toml`` edit cannot silently rewrite a decision
that already exists, and reselecting one size never disturbs its siblings.

``T_provisional`` and ``T_selected`` are never stored as lists.  Both are
``pi_train[:N]``, and their identity is re-derived through the real P2 training
order on every set and again at freeze - for every member of the design.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import TrainingDataError
from .campaign_target_size_state import (
    SELECTION_SOURCE_AUTO_RECOMMENDATION,
    SELECTION_SOURCE_MANUAL,
    FrozenTargetSelection,
    TargetSizeCampaignRevision,
    TargetSizeCampaignState,
    TargetSizeProposal,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    merge_provisional_entry,
)


class TargetSizeSelectionError(TrainingDataError):
    """The requested provisional selection or freeze cannot be authenticated."""


@dataclass(frozen=True, slots=True)
class ResolvedHorizons:
    """One invocation's complete effective role-specific training horizons."""

    cv_max_num_epochs: int
    production_max_num_epochs: int


def resolve_provisional_horizons(
    cfg: Mapping[str, Any],
    *,
    cv_max_num_epochs: int | None = None,
    production_max_num_epochs: int | None = None,
) -> ResolvedHorizons:
    """Resolve both horizons for one proposal-setting invocation.

    The configured owners stay canonical: ``[post_selection.cv].max_num_epochs``
    for cross-validation and ``[training].max_num_epochs`` for final production.
    A CLI flag is an explicit override *for this invocation only* - it never
    edits ``campaign.toml`` and never becomes a sticky default for the next
    proposal.  Resolution happens here, once, and the resolved values are what
    the proposal persists.
    """

    from .post_selection_identity import (
        resolve_cv_validation_policy_identity,
        resolve_final_production_policy_identity,
    )

    resolved_cv = (
        int(cv_max_num_epochs)
        if cv_max_num_epochs is not None
        else int(resolve_cv_validation_policy_identity(cfg).cv_max_num_epochs)
    )
    resolved_production = (
        int(production_max_num_epochs)
        if production_max_num_epochs is not None
        else int(
            resolve_final_production_policy_identity(cfg).production_max_num_epochs
        )
    )
    for value, label in (
        (resolved_cv, "--horizon-cv"),
        (resolved_production, "--horizon"),
    ):
        if value <= 0:
            raise TargetSizeSelectionError(
                f"{label} must be a positive number of epochs; got {value}."
            )
    return ResolvedHorizons(
        cv_max_num_epochs=resolved_cv,
        production_max_num_epochs=resolved_production,
    )


def authenticate_candidate_membership(definition: Any, target_size: int) -> str:
    """Return the exact ``pi_train[:N]`` identity for one qualified candidate.

    Membership is asked of the accepted P2 training-order owner, so a manual
    choice is authenticated by exactly the machinery that authenticates an
    automatic one.  There is no second membership constructor.
    """

    size = int(target_size)
    qualified = tuple(definition.qualified_candidate_sizes)
    if size not in qualified:
        raise TargetSizeSelectionError(
            f"Target size {size} is not a configured qualified candidate. "
            f"Qualified candidate sizes are {list(qualified)}."
        )
    return definition.training_order.candidate_digest(size)


def require_unfrozen(state: TargetSizeCampaignState) -> None:
    if state.frozen_entries is not None:
        sizes = ", ".join(
            f"N={entry.n_selected} (CV horizon {entry.cv_max_num_epochs}, "
            f"production horizon {entry.production_max_num_epochs})"
            for entry in state.frozen_entries
        )
        raise TargetSizeSelectionError(
            "The downstream target design is frozen: `cross-validate` already "
            f"admitted {sizes}. Frozen ancestry is never edited in place; start "
            "another experiment with a fresh `prepare` generation instead."
        )


def _successor_with(
    state: TargetSizeCampaignState,
    *,
    provisional_entries: tuple[TargetSizeProposal, ...] = (),
    frozen_entries: tuple[FrozenTargetSelection, ...] | None = None,
) -> TargetSizeCampaignState:
    """Rewrite only the selection axis of an otherwise identical state."""

    return TargetSizeCampaignState(
        regime=state.regime,
        generation=state.generation,
        lifecycle=state.lifecycle,
        attempt=state.attempt,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        policy_digest=state.policy_digest,
        experiment_definition_digest=state.experiment_definition_digest,
        aggregate_digest=state.aggregate_digest,
        prepared_manifest_digest=state.prepared_manifest_digest,
        execution_context_digest=state.execution_context_digest,
        common_preparation_digest=state.common_preparation_digest,
        screen_window_digest=state.screen_window_digest,
        execution_root=state.execution_root,
        adopted_execution_head_digest=state.adopted_execution_head_digest,
        adopted_reducer_state_digest=state.adopted_reducer_state_digest,
        auto_diagnostic=state.auto_diagnostic,
        provisional_entries=provisional_entries,
        frozen_entries=frozen_entries,
        disposition=state.disposition,
        disposition_detail=state.disposition_detail,
    )


def build_target_size_proposal(
    definition: Any,
    *,
    target_size: int,
    selection_source: str,
    horizons: ResolvedHorizons,
    auto_diagnostic_digest: str | None = None,
) -> TargetSizeProposal:
    """Compose one complete provisional proposal against authenticated P2 state."""

    if selection_source not in (
        SELECTION_SOURCE_MANUAL,
        SELECTION_SOURCE_AUTO_RECOMMENDATION,
    ):
        raise TargetSizeSelectionError(
            f"Unsupported target-size selection source {selection_source!r}."
        )
    return TargetSizeProposal(
        n_provisional=int(target_size),
        membership_digest=authenticate_candidate_membership(definition, target_size),
        training_order_digest=definition.training_order.content_digest,
        selection_source=selection_source,
        cv_max_num_epochs=horizons.cv_max_num_epochs,
        production_max_num_epochs=horizons.production_max_num_epochs,
        auto_diagnostic_digest=auto_diagnostic_digest,
    )


def commit_target_size_proposal(
    store: Any,
    revision: TargetSizeCampaignRevision,
    proposal: TargetSizeProposal,
) -> TargetSizeCampaignRevision:
    """Merge one per-size proposal into the provisional design, atomically.

    A size that is not in the design is appended; a size that is already in it
    has its complete entry replaced without moving its list position.  Both
    manual selection and an adopted automatic recommendation come through here,
    so neither can acquire collection authority the other lacks.
    """

    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeSelectionError(
            "Only the current target-size runtime can hold a provisional design."
        )
    require_unfrozen(state)
    merged = merge_provisional_entry(state.provisional_entries, proposal)
    if merged == state.provisional_entries:
        # The operator asked for the design they already have. Recording an
        # identical collection would add a revision that decides nothing.
        return revision
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.SET_PROPOSAL,
        expected=revision.expectation(),
        successor=_successor_with(state, provisional_entries=merged),
    ).revision


def commit_target_size_reset(
    store: Any, revision: TargetSizeCampaignRevision
) -> TargetSizeCampaignRevision:
    """Clear every provisional entry in one transition, pre-freeze only.

    Reset owns exactly one axis.  The prepared generation, the adopted P3 head
    and any valid automatic-diagnostic evidence are untouched, because none of
    them is the operator's provisional choice; discarding expensive diagnostic
    work to express "I have not chosen yet" would be a different, worse command.
    """

    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeSelectionError(
            "Only the current target-size runtime can hold a provisional design."
        )
    require_unfrozen(state)
    if not state.provisional_entries:
        # Already the canonical unselected state. A revision that decides
        # nothing is not worth appending to an authenticated chain.
        return revision
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.RESET_PROPOSAL,
        expected=revision.expectation(),
        successor=_successor_with(state, provisional_entries=()),
    ).revision


@dataclass(frozen=True, slots=True)
class AdmittedTargetSelection:
    """One frozen per-size entry plus the authenticated substrate that proves it."""

    revision: TargetSizeCampaignRevision
    authorities: Any
    frozen: FrozenTargetSelection

    @property
    def definition(self) -> Any:
        return self.authorities.aggregate.definition


@dataclass(frozen=True, slots=True)
class AdmittedTargetDesign:
    """The complete frozen ordered design, authenticated as one collection."""

    revision: TargetSizeCampaignRevision
    authorities: Any
    per_size: tuple[AdmittedTargetSelection, ...]

    @property
    def definition(self) -> Any:
        return self.authorities.aggregate.definition

    @property
    def selected_sizes(self) -> tuple[int, ...]:
        return tuple(item.frozen.n_selected for item in self.per_size)


def resolve_frozen_target_design(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
) -> AdmittedTargetDesign:
    """Resolve the frozen downstream design, admitting the whole collection when asked.

    ``admit`` is the freeze authority and belongs to ``cross-validate`` alone.
    Every other post-selection reader passes ``admit=False`` and therefore
    *requires* a freeze that already happened: describing or continuing
    downstream work must never be able to commit the experiment.

    Admission is the first and only freeze point, and it is whole-collection.
    It re-establishes current campaign state, reloads and authenticates the one
    shared prepared generation, revalidates *every* proposed ``N`` against the
    current qualified candidate set, re-derives each exact ``pi_train[:N]``
    identity from the P2 training order, and publishes the complete ordered
    frozen design - every membership and both effective role horizons per size -
    in one CAS transition before any numerical downstream work begins.  One
    unauthenticatable member rejects the entire admission: a requested
    multi-size experiment is never quietly reduced to the subset that happened
    to still validate.

    No automatic-screen execution head or reducer is required.  A campaign that
    never ran the diagnostic freezes exactly the same way as one that did.
    """

    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_runtime import load_prepared_target_size_generation

    revision = require_current_target_size_runtime(store)
    state = revision.state
    authorities = load_prepared_target_size_generation(cfg, paths, store, revision)
    definition = authorities.aggregate.definition

    if state.frozen_entries is not None:
        # Freeze is idempotent for repeated/resumed post-selection invocations,
        # but never trusted from campaign state alone: every frozen membership
        # is re-derived from the current P2 training order before it is reused.
        for entry in state.frozen_entries:
            _authenticate_frozen(entry, definition)
        return _design(revision, authorities, state.frozen_entries)

    if not admit:
        raise TargetSizeSelectionError(
            "No frozen target-size design exists for this campaign generation. "
            "`cross-validate` is the admission boundary that freezes the current "
            "provisional design; run it before any other post-selection work."
        )
    if not state.provisional_entries:
        raise TargetSizeSelectionError(
            "No provisional target size has been chosen for this generation. Run "
            "`select-target-size <N>` to choose one explicitly, or "
            "`select-target-size --auto` to run the optional automatic diagnostic "
            "and adopt its recommendation. Selecting further sizes appends them; "
            "`cross-validate` then freezes the complete design at once."
        )
    frozen_entries = tuple(
        _admit_entry(proposal, definition) for proposal in state.provisional_entries
    )
    revision = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.FREEZE_SELECTION,
        expected=revision.expectation(),
        successor=_successor_with(state, frozen_entries=frozen_entries),
    ).revision
    # Per-size contexts are derived only from the committed frozen state, never
    # from the proposals that produced it.
    return _design(revision, authorities, revision.state.frozen_entries)


def _design(
    revision: TargetSizeCampaignRevision,
    authorities: Any,
    frozen_entries: Any,
) -> AdmittedTargetDesign:
    return AdmittedTargetDesign(
        revision=revision,
        authorities=authorities,
        per_size=tuple(
            AdmittedTargetSelection(revision, authorities, entry)
            for entry in frozen_entries
        ),
    )


def _admit_entry(
    proposal: TargetSizeProposal, definition: Any
) -> FrozenTargetSelection:
    membership_digest = authenticate_candidate_membership(
        definition, proposal.n_provisional
    )
    if (
        membership_digest != proposal.membership_digest
        or definition.training_order.content_digest != proposal.training_order_digest
    ):
        raise TargetSizeSelectionError(
            f"The provisional entry for N={proposal.n_provisional} names a target "
            "membership the current P2 training order does not reproduce. No part "
            "of the design is admitted; run `select-target-size` again against the "
            "current prepared generation."
        )
    return FrozenTargetSelection(
        n_selected=proposal.n_provisional,
        selected_membership_digest=membership_digest,
        training_order_digest=proposal.training_order_digest,
        cv_max_num_epochs=proposal.cv_max_num_epochs,
        production_max_num_epochs=proposal.production_max_num_epochs,
        selection_source=proposal.selection_source,
        auto_diagnostic_digest=proposal.auto_diagnostic_digest,
    )


def resolve_frozen_target_selection(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
    n_selected: int | None = None,
) -> AdmittedTargetSelection:
    """Resolve exactly one admitted per-size entry of the frozen design."""

    design = resolve_frozen_target_design(cfg, paths, store, admit=admit)
    if n_selected is None:
        if len(design.per_size) == 1:
            return design.per_size[0]
        raise TargetSizeSelectionError(
            "The frozen target-size design contains "
            f"{len(design.per_size)} selected sizes {list(design.selected_sizes)}; "
            "name the size explicitly."
        )
    size = int(n_selected)
    for item in design.per_size:
        if item.frozen.n_selected == size:
            return item
    raise TargetSizeSelectionError(
        f"Target size {size} is not part of the current frozen design "
        f"{list(design.selected_sizes)}."
    )


def _authenticate_frozen(frozen: FrozenTargetSelection, definition: Any) -> None:
    if (
        definition.training_order.content_digest != frozen.training_order_digest
        or definition.training_order.candidate_digest(frozen.n_selected)
        != frozen.selected_membership_digest
    ):
        raise TargetSizeSelectionError(
            "The frozen target selection does not authenticate against the current "
            "P2 training order. Frozen downstream work is never reinterpreted under "
            "a changed scientific substrate."
        )


__all__ = [
    "AdmittedTargetDesign",
    "AdmittedTargetSelection",
    "ResolvedHorizons",
    "TargetSizeSelectionError",
    "authenticate_candidate_membership",
    "build_target_size_proposal",
    "commit_target_size_proposal",
    "commit_target_size_reset",
    "require_unfrozen",
    "resolve_frozen_target_design",
    "resolve_frozen_target_selection",
    "resolve_provisional_horizons",
]
