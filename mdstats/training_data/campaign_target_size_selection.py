"""The operator-owned target-size design: provisional proposal, then freeze.

The automatic screen used to be the only thing allowed to decide how much target
data downstream training would use.  It no longer is.  Its short-horizon
force-RMSE comparison is evidence about one configured screening protocol, not
proof that a size is asymptotically right, and the product must not let that
proxy masquerade as the experimental-design decision.

So the decision lives here instead, in two clearly separated phases:

.. code-block:: text

    select-target-size <N> | --auto     ->  one mutable provisional proposal
                                            (N, T_N identity, H_cv, H_prod)

    cross-validate                      ->  freeze: exactly that proposal
                                            becomes immutable downstream ancestry

Between those two points the operator may change their mind freely; after the
second, nothing here can change the design at all.  A proposal is complete when
it is set: both role horizons are resolved to explicit values at that moment, so
a later ``campaign.toml`` edit cannot silently rewrite a decision that already
exists.

``T_provisional`` and ``T_selected`` are never stored as lists.  Both are
``pi_train[:N]``, and their identity is re-derived through the real P2 training
order on every set and again at freeze.
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
        (resolved_cv, "--select-horizon-cv"),
        (resolved_production, "--select-horizon"),
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
    if state.frozen is not None:
        raise TargetSizeSelectionError(
            "The downstream target design is frozen: `cross-validate` already "
            f"admitted N_selected={state.frozen.n_selected} with CV horizon "
            f"{state.frozen.cv_max_num_epochs} and production horizon "
            f"{state.frozen.production_max_num_epochs}. Frozen ancestry is never "
            "edited in place; start another experiment with a fresh `prepare` "
            "generation instead."
        )


def _successor_with(
    state: TargetSizeCampaignState,
    *,
    proposal: TargetSizeProposal | None = None,
    frozen: FrozenTargetSelection | None = None,
) -> TargetSizeCampaignState:
    """Rewrite only the proposal/freeze axis of an otherwise identical state."""

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
        proposal=proposal,
        frozen=frozen,
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
    """Publish one provisional proposal through the campaign CAS boundary."""

    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeSelectionError(
            "Only the current target-size runtime can hold a provisional proposal."
        )
    require_unfrozen(state)
    if state.proposal == proposal:
        # The operator asked for the design they already have. Recording an
        # identical proposal would add a revision that decides nothing.
        return revision
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.SET_PROPOSAL,
        expected=revision.expectation(),
        successor=_successor_with(state, proposal=proposal),
    ).revision


@dataclass(frozen=True, slots=True)
class AdmittedTargetSelection:
    """The frozen design plus the authenticated substrate that proves it."""

    revision: TargetSizeCampaignRevision
    authorities: Any
    frozen: FrozenTargetSelection

    @property
    def definition(self) -> Any:
        return self.authorities.aggregate.definition


def resolve_frozen_target_selection(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
) -> AdmittedTargetSelection:
    """Resolve the frozen downstream design, admitting the proposal when asked.

    ``admit`` is the freeze authority and belongs to ``cross-validate`` alone.
    Every other post-selection reader passes ``admit=False`` and therefore
    *requires* a freeze that already happened: describing or continuing
    downstream work must never be able to commit the experiment.

    Admission is the first and only freeze point.  It re-establishes current campaign
    state, reloads and authenticates the prepared generation, revalidates the
    proposed ``N`` against the *current* qualified candidate set, re-derives the
    exact ``pi_train[:N]`` identity from the P2 training order, and publishes the
    frozen selection - target membership and both effective role horizons - in
    one CAS transition before any numerical downstream work begins.

    No automatic-screen execution head or reducer is required.  A campaign that
    never ran the diagnostic freezes exactly the same way as one that did.
    """

    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_runtime import load_prepared_target_size_generation

    revision = require_current_target_size_runtime(store)
    state = revision.state
    authorities = load_prepared_target_size_generation(cfg, paths, store, revision)
    definition = authorities.aggregate.definition

    if state.frozen is not None:
        # Freeze is idempotent for repeated/resumed post-selection invocations,
        # but never trusted from campaign state alone: the frozen membership is
        # re-derived from the current P2 training order before it is reused.
        _authenticate_frozen(state.frozen, definition)
        return AdmittedTargetSelection(revision, authorities, state.frozen)

    if not admit:
        raise TargetSizeSelectionError(
            "No frozen target selection exists for this campaign generation. "
            "`cross-validate` is the admission boundary that freezes the current "
            "provisional design; run it before any other post-selection work."
        )
    proposal = state.proposal
    if proposal is None:
        raise TargetSizeSelectionError(
            "No provisional target size has been chosen for this generation. Run "
            "`select-target-size <N>` to choose one explicitly, or "
            "`select-target-size --auto` to run the optional automatic diagnostic "
            "and adopt its recommendation."
        )
    membership_digest = authenticate_candidate_membership(
        definition, proposal.n_provisional
    )
    if (
        membership_digest != proposal.membership_digest
        or definition.training_order.content_digest != proposal.training_order_digest
    ):
        raise TargetSizeSelectionError(
            "The provisional proposal names a target membership the current P2 "
            "training order does not reproduce. The proposal is not admitted; run "
            "`select-target-size` again against the current prepared generation."
        )
    frozen = FrozenTargetSelection(
        n_selected=proposal.n_provisional,
        selected_membership_digest=membership_digest,
        training_order_digest=proposal.training_order_digest,
        cv_max_num_epochs=proposal.cv_max_num_epochs,
        production_max_num_epochs=proposal.production_max_num_epochs,
        selection_source=proposal.selection_source,
        auto_diagnostic_digest=proposal.auto_diagnostic_digest,
    )
    revision = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.FREEZE_SELECTION,
        expected=revision.expectation(),
        successor=_successor_with(state, frozen=frozen),
    ).revision
    return AdmittedTargetSelection(revision, authorities, frozen)


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
    "AdmittedTargetSelection",
    "ResolvedHorizons",
    "TargetSizeSelectionError",
    "resolve_frozen_target_selection",
    "authenticate_candidate_membership",
    "build_target_size_proposal",
    "commit_target_size_proposal",
    "require_unfrozen",
    "resolve_provisional_horizons",
]
