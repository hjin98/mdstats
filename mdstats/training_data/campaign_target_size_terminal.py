"""Terminal target-size projection and current-state invalidation classification.

A terminal target size is never an editable field.  ``N_selected`` and the exact
``T_selected`` membership identity are authenticated projections of terminal
P2/P3 state: the reducer state carried by the adopted immutable execution head
decides ``N``, and the P2 training order decides which frames that ``N`` names.
This module derives that projection, commits it together with the head and
reducer references it depends on, and re-derives it on every reload so a
divergent persisted copy fails closed instead of being trusted.

Editing only one field can therefore never make divergent state valid: changing
the stored ``N``, the stored membership identity, or the adopted head reference
breaks the re-derivation, because each is checked against the authenticated
source rather than against the others.

The module also owns the current-state invalidation classification.  Scientific
identity changes retire the current generation and justify a fresh one; they are
never repaired in place, because equality of a selected integer proves nothing
after the authority that produced it has changed.  Settings the accepted P2
policy owner deliberately excludes - cross-validation and production-only
configuration - cannot change target-size identity at all, so they never
invalidate a target-size result.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import TrainingDataError
from .campaign_target_size_state import (
    TargetSizeCampaignRevision,
    TargetSizeCampaignState,
    TargetSizeCampaignStateError,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTerminalProjection,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
)

#: The scientific identities whose change retires the current generation.
SCIENTIFIC_IDENTITY_FIELDS: tuple[str, ...] = (
    "frame_authority_digest",
    "neutral_statistical_base_digest",
    "split_exclusion_digest",
    "policy_digest",
    "experiment_definition_digest",
    "aggregate_digest",
)


class TargetSizeTerminalProjectionError(TargetSizeCampaignStateError):
    """Persisted terminal state does not match authenticated P2/P3 state."""


def _terminal_lifecycle(status: str) -> TargetSizeLifecycle:
    return (
        TargetSizeLifecycle.TERMINAL_SELECTED
        if str(status) == "selected"
        else TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE
    )


def derive_terminal_projection(
    head: Any, *, definition: Any
) -> TargetSizeTerminalProjection:
    """Project the authenticated terminal reducer state onto campaign state.

    ``N`` comes from the terminal reducer state, and the exact ``T_selected``
    identity is re-derived from the P2 training order rather than copied, so a
    reducer state carrying a membership digest that the training order does not
    produce is rejected here instead of being persisted.
    """

    post = head.post_state
    if not post.is_terminal:
        raise TargetSizeTerminalProjectionError(
            "A terminal target-size projection requires a terminal reducer state."
        )
    if str(post.experiment_definition_digest) != str(definition.content_digest):
        raise TargetSizeTerminalProjectionError(
            "Terminal reducer state belongs to a different P2 experiment definition."
        )
    training_order = definition.training_order
    selected_size = post.selected_target_size
    membership_digest = None
    if selected_size is not None:
        membership_digest = training_order.candidate_digest(int(selected_size))
        if membership_digest != str(post.selected_membership_digest):
            raise TargetSizeTerminalProjectionError(
                "Terminal reducer state carries a T_selected identity that the P2 "
                "training order does not produce for the selected N."
            )
    return TargetSizeTerminalProjection(
        reducer_status=post.status.value,
        experiment_definition_digest=definition.content_digest,
        reducer_state_digest=post.content_digest,
        execution_head_digest=head.content_digest,
        training_order_digest=training_order.content_digest,
        selected_target_size=None if selected_size is None else int(selected_size),
        selected_membership_digest=membership_digest,
        terminal_reason_codes=tuple(post.terminal_reason_codes),
    )


def commit_terminal_projection(
    store: Any,
    revision: TargetSizeCampaignRevision,
    head: Any,
    *,
    definition: Any,
) -> TargetSizeCampaignRevision:
    """Atomically bind the adopted head, reducer digest, and terminal projection.

    The three are written in one transition because they are one claim: a
    campaign may never hold a selected size whose head or reducer reference was
    committed separately.
    """

    projection = derive_terminal_projection(head, definition=definition)
    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeTerminalProjectionError(
            "Only the current target-size runtime can record a terminal result."
        )
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.CURRENT,
        generation=state.generation,
        lifecycle=_terminal_lifecycle(projection.reducer_status),
        attempt=state.attempt,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        policy_digest=state.policy_digest,
        experiment_definition_digest=state.experiment_definition_digest,
        aggregate_digest=state.aggregate_digest,
        execution_context_digest=state.execution_context_digest,
        common_preparation_digest=state.common_preparation_digest,
        screen_window_digest=state.screen_window_digest,
        execution_root=state.execution_root,
        adopted_execution_head_digest=head.content_digest,
        adopted_reducer_state_digest=head.post_state.content_digest,
        terminal=projection,
        disposition=(
            "terminal_selection"
            if projection.is_selection
            else "terminal_scientific_outcome"
        ),
        disposition_detail=(
            None
            if projection.is_selection
            else "The reducer reached a terminal scientific outcome; this is a "
            "result, not an operational interruption, and the same screen is not "
            "resumable."
        ),
    )
    kind = (
        TargetSizeTransitionKind.RECORD_TERMINAL_SELECTION
        if projection.is_selection
        else TargetSizeTransitionKind.RECORD_TERMINAL_SCIENTIFIC_FAILURE
    )
    return commit_target_size_campaign_transition(
        store, kind=kind, expected=revision.expectation(), successor=successor
    ).revision


def validate_terminal_projection(
    revision: TargetSizeCampaignRevision, *, resolver: Any, definition: Any
) -> Any:
    """Re-derive the terminal projection before exposing it downstream.

    Nothing persisted is trusted: the referenced head is re-resolved and
    authenticated through the real P3 resolver, the reducer digest the campaign
    bound is checked against it, and both ``N`` and the exact ``T_selected``
    identity are re-derived from the authenticated terminal state before being
    compared with the stored projection.
    """

    from .campaign_target_size_adoption import load_adopted_execution_head

    state = revision.state
    persisted = state.terminal
    if persisted is None:
        raise TargetSizeTerminalProjectionError(
            "This campaign generation has no terminal target-size result."
        )
    head = load_adopted_execution_head(resolver, revision)
    if str(head.post_state.content_digest) != str(state.adopted_reducer_state_digest):
        raise TargetSizeTerminalProjectionError(
            "The adopted execution head does not carry the reducer state the campaign "
            "bound to the terminal result."
        )
    rederived = derive_terminal_projection(head, definition=definition)
    if rederived != persisted:
        raise TargetSizeTerminalProjectionError(
            "The persisted terminal target-size projection does not match the value "
            "re-derived from authenticated P2/P3 state; the selected size and exact "
            "selected data are never accepted from campaign state alone."
        )
    if _terminal_lifecycle(persisted.reducer_status) is not state.lifecycle:
        raise TargetSizeTerminalProjectionError(
            "Terminal lifecycle disagrees with the authenticated reducer outcome."
        )
    return head


# ---------------------------------------------------------------------------
# Section 8: current-state invalidation classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetSizeInvalidation:
    """How a reconstructed scientific identity relates to the persisted one."""

    changed_fields: tuple[str, ...]
    disposition: str
    detail: str

    @property
    def is_current(self) -> bool:
        return self.disposition == "current"


def classify_target_size_invalidation(
    state: TargetSizeCampaignState, observed: Mapping[str, str]
) -> TargetSizeInvalidation:
    """Classify a reconstructed identity against the persisted generation.

    A changed scientific authority is never repaired in place. The persisted
    generation is retired and a fresh one is justified, because equality of a
    selected integer says nothing once the authority that produced it changed.
    """

    missing = [name for name in SCIENTIFIC_IDENTITY_FIELDS if name not in observed]
    if missing:
        raise TrainingDataError(
            "Target-size invalidation classification requires the complete scientific "
            "identity; missing: " + ", ".join(sorted(missing))
        )
    changed = tuple(
        name
        for name in SCIENTIFIC_IDENTITY_FIELDS
        if getattr(state, name) != observed[name]
    )
    if not changed:
        return TargetSizeInvalidation(
            changed_fields=(),
            disposition="current",
            detail="The reconstructed scientific identity matches this generation.",
        )
    if state.frame_authority_digest is None:
        return TargetSizeInvalidation(
            changed_fields=changed,
            disposition="fresh_generation",
            detail="This generation never bound a scientific identity.",
        )
    return TargetSizeInvalidation(
        changed_fields=changed,
        disposition="fresh_generation",
        detail=(
            "Changed target-size scientific authority ("
            + ", ".join(changed)
            + "); the persisted generation is retired and a fresh canonical generation "
            "is required. Prior target-size evidence is never reinterpreted under a "
            "changed identity."
        ),
    )


@dataclass(frozen=True, slots=True)
class ValidatedTargetSizeTerminalResult:
    """Authenticated bundle returned by the validated terminal loader.

    A consumer holding this object has established that:
    1. Campaign regime is CURRENT and lifecycle is terminal;
    2. Current P1/P2 scientific authorities were reconstructed through accepted owners;
    3. Target-size scientific identity matches the canonical generation;
    4. P3 execution context matches the canonical generation;
    5. The persisted execution root was resolved through the real P3 owner;
    6. The adopted execution head and reducer state were authenticated;
    7. Terminal N and exact T_selected identity were re-derived from the authenticated
       terminal reducer state and P2 training order;
    8. The persisted terminal projection matches the re-derived projection.
    """

    revision: TargetSizeCampaignRevision
    authorities: Any
    head: Any
    projection: TargetSizeTerminalProjection

    @property
    def is_selection(self) -> bool:
        return self.projection.is_selection

    @property
    def selected_target_size(self) -> int | None:
        return self.projection.selected_target_size

    @property
    def selected_membership_digest(self) -> str | None:
        return self.projection.selected_membership_digest

    @property
    def reducer_status(self) -> str:
        return self.projection.reducer_status

    @property
    def terminal_reason_codes(self) -> tuple[str, ...]:
        return self.projection.terminal_reason_codes


def load_validated_target_size_terminal_result(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    revision: TargetSizeCampaignRevision | None = None,
) -> ValidatedTargetSizeTerminalResult:
    """Reconstruct, authenticate, and re-derive the terminal target-size state.

    This is the single authoritative terminal-load path for select-target-size
    replay and downstream P5 consumption. Nothing persisted is trusted: current
    P1/P2 authorities are reconstructed from source inputs, scientific and
    context identities are verified against the persisted generation, the
    persisted execution root and adopted immutable head are re-authenticated
    through P3 owners, and the terminal selection is re-derived before returning.
    """

    from ._campaign_cli_core import _cfg, _optimizer_policy
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_runtime import (
        build_current_target_size_authorities,
        current_target_size_execution_root,
    )
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        build_target_size_execution_context,
        build_target_size_screen_schedule,
    )

    if revision is None:
        revision = require_current_target_size_runtime(store)
    state = revision.state
    if state.lifecycle not in (
        TargetSizeLifecycle.TERMINAL_SELECTED,
        TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
    ):
        raise TargetSizeTerminalProjectionError(
            f"Campaign canonical generation {state.generation} is not in a terminal state "
            f"(lifecycle={state.lifecycle.value})."
        )
    if state.terminal is None:
        raise TargetSizeTerminalProjectionError(
            f"Campaign canonical generation {state.generation} has no persisted terminal projection."
        )

    authorities = build_current_target_size_authorities(cfg, paths, store)

    invalidation = classify_target_size_invalidation(state, authorities.identity)
    if not invalidation.is_current:
        raise TargetSizeTerminalProjectionError(
            "The reconstructed target-size scientific identity does not match the persisted "
            f"terminal generation ({', '.join(invalidation.changed_fields)}). Run `prepare` to bind "
            "a fresh canonical generation; prior terminal results cannot be exposed or "
            "reinterpreted under a changed identity."
        )

    if state.common_preparation_digest != authorities.common.content_digest:
        raise TargetSizeTerminalProjectionError(
            "The reconstructed common preparation digest does not match the persisted "
            "terminal generation. Run `prepare` to bind a fresh canonical generation."
        )

    aggregate = authorities.aggregate
    definition = aggregate.definition
    schedule = build_target_size_screen_schedule(definition.policy.fidelity_epochs)
    seeds = tuple(definition.policy.optimizer_seeds)
    optimizer_policy = _optimizer_policy(
        cfg,
        seed=int(seeds[0]),
        num_workers=int(_cfg(cfg, "training", "num_workers", 0)),
        paths=paths,
        planned_epochs=int(schedule.n3),
    )
    context = build_target_size_execution_context(
        definition,
        authorities.common,
        schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
    )
    if state.execution_context_digest != context.content_digest:
        raise TargetSizeTerminalProjectionError(
            "The reconstructed P3 execution context does not match the persisted terminal "
            "generation. Run `prepare` to bind a fresh canonical generation."
        )

    root = current_target_size_execution_root(paths, state.generation)
    if not root.is_dir():
        from .campaign_target_size_adoption import TargetSizeAdoptionCorruptionError

        raise TargetSizeAdoptionCorruptionError(
            f"The campaign-owned target-size execution root {root} does not exist."
        )
    resolver = TargetSizeExecutionResolver(root)

    head = validate_terminal_projection(
        revision, resolver=resolver, definition=definition
    )

    return ValidatedTargetSizeTerminalResult(
        revision=revision,
        authorities=authorities,
        head=head,
        projection=state.terminal,
    )


__all__ = [
    "SCIENTIFIC_IDENTITY_FIELDS",
    "TargetSizeInvalidation",
    "TargetSizeTerminalProjectionError",
    "ValidatedTargetSizeTerminalResult",
    "classify_target_size_invalidation",
    "commit_terminal_projection",
    "derive_terminal_projection",
    "load_validated_target_size_terminal_result",
    "validate_terminal_projection",
]
