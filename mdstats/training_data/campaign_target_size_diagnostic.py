"""Automatic target-size diagnostic projection and invalidation classification.

The automatic screen is a short-horizon force-RMSE experiment.  What it produces
is evidence and, when its comparison is valid, a *recommendation*: it is not the
authority that fixes how much data downstream training uses.  That authority is
the operator's proposal, frozen at ``cross-validate`` admission
(:mod:`mdstats.training_data.campaign_target_size_selection`).

A recommended target size is never an editable field.  It and the exact
membership identity it names are authenticated projections of terminal P2/P3
state: the reducer state carried by the adopted immutable execution head decides
the recommended ``N``, and the P2 training order decides which frames that ``N``
names.  This module derives that projection, commits it together with the head
and reducer references it depends on, and re-derives it on every reload so a
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
    TargetSizeAutoDiagnostic,
    TargetSizeCampaignRevision,
    TargetSizeCampaignState,
    TargetSizeCampaignStateError,
    TargetSizeLifecycle,
    TargetSizeRegime,
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


class TargetSizeDiagnosticProjectionError(TargetSizeCampaignStateError):
    """Persisted diagnostic state does not match authenticated P2/P3 state."""


def derive_auto_diagnostic(head: Any, *, definition: Any) -> TargetSizeAutoDiagnostic:
    """Project the authenticated terminal reducer state onto campaign state.

    The recommended ``N`` comes from the terminal reducer state, and the exact
    membership identity is re-derived from the P2 training order rather than
    copied, so a reducer state carrying a membership digest that the training
    order does not produce is rejected here instead of being persisted.
    """

    post = head.post_state
    if not post.is_terminal:
        raise TargetSizeDiagnosticProjectionError(
            "A complete automatic target-size diagnostic requires a terminal reducer state."
        )
    if str(post.experiment_definition_digest) != str(definition.content_digest):
        raise TargetSizeDiagnosticProjectionError(
            "Terminal reducer state belongs to a different P2 experiment definition."
        )
    training_order = definition.training_order
    # ``selected_target_size`` is the historical P2/P3 spelling of the screen's
    # own ranking outcome. Crossing this boundary it is a recommendation.
    recommended_size = post.selected_target_size
    membership_digest = None
    if recommended_size is not None:
        membership_digest = training_order.candidate_digest(int(recommended_size))
        if membership_digest != str(post.selected_membership_digest):
            raise TargetSizeDiagnosticProjectionError(
                "Terminal reducer state carries a membership identity that the P2 "
                "training order does not produce for the recommended N."
            )
    return TargetSizeAutoDiagnostic(
        reducer_status=post.status.value,
        experiment_definition_digest=definition.content_digest,
        reducer_state_digest=post.content_digest,
        execution_head_digest=head.content_digest,
        training_order_digest=training_order.content_digest,
        recommended_target_size=(
            None if recommended_size is None else int(recommended_size)
        ),
        recommended_membership_digest=membership_digest,
        terminal_reason_codes=tuple(post.terminal_reason_codes),
    )


def commit_auto_diagnostic(
    store: Any,
    revision: TargetSizeCampaignRevision,
    head: Any,
    *,
    definition: Any,
) -> TargetSizeCampaignRevision:
    """Atomically bind the adopted head, reducer digest, and diagnostic projection.

    The three are written in one transition because they are one claim: a
    campaign may never hold a recommendation whose head or reducer reference was
    committed separately.

    This transition records *evidence only*.  It deliberately carries the
    predecessor's proposal forward untouched: an operator choice that already
    existed is not destroyed, replaced, or blocked by a diagnostic outcome.
    """

    projection = derive_auto_diagnostic(head, definition=definition)
    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeDiagnosticProjectionError(
            "Only the current target-size runtime can record a diagnostic result."
        )
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.CURRENT,
        generation=state.generation,
        lifecycle=TargetSizeLifecycle.DIAGNOSTIC_COMPLETE,
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
        adopted_execution_head_digest=head.content_digest,
        adopted_reducer_state_digest=head.post_state.content_digest,
        auto_diagnostic=projection,
        provisional_entries=state.provisional_entries,
        frozen_entries=state.frozen_entries,
        legacy_scalar_binding=state.legacy_scalar_binding,
        disposition=(
            "auto_diagnostic_recommendation"
            if projection.has_recommendation
            else "auto_diagnostic_no_recommendation"
        ),
        disposition_detail=(
            None
            if projection.has_recommendation
            else "The automatic screen reached a terminal scientific outcome without "
            "a valid comparison; this is a diagnostic result, not an operational "
            "interruption, the same screen is not resumable, and manual target "
            "selection remains available."
        ),
    )
    kind = (
        TargetSizeTransitionKind.RECORD_AUTO_DIAGNOSTIC_RECOMMENDATION
        if projection.has_recommendation
        else TargetSizeTransitionKind.RECORD_AUTO_DIAGNOSTIC_NO_RECOMMENDATION
    )
    return commit_target_size_campaign_transition(
        store, kind=kind, expected=revision.expectation(), successor=successor
    ).revision


def validate_auto_diagnostic(
    revision: TargetSizeCampaignRevision, *, resolver: Any, definition: Any
) -> Any:
    """Re-derive the diagnostic projection before exposing it.

    Nothing persisted is trusted: the referenced head is re-resolved and
    authenticated through the real P3 resolver, the reducer digest the campaign
    bound is checked against it, and both ``N`` and the exact ``T_selected``
    identity are re-derived from the authenticated terminal state before being
    compared with the stored projection.
    """

    from .campaign_target_size_adoption import load_adopted_execution_head

    state = revision.state
    persisted = state.auto_diagnostic
    if persisted is None:
        raise TargetSizeDiagnosticProjectionError(
            "This campaign generation has no complete automatic target-size diagnostic."
        )
    head = load_adopted_execution_head(resolver, revision)
    if str(head.post_state.content_digest) != str(state.adopted_reducer_state_digest):
        raise TargetSizeDiagnosticProjectionError(
            "The adopted execution head does not carry the reducer state the campaign "
            "bound to the diagnostic result."
        )
    rederived = derive_auto_diagnostic(head, definition=definition)
    if rederived != persisted:
        raise TargetSizeDiagnosticProjectionError(
            "The persisted automatic target-size diagnostic does not match the value "
            "re-derived from authenticated P2/P3 state; the recommended size and the "
            "exact data it names are never accepted from campaign state alone."
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
class ValidatedTargetSizeAutoDiagnostic:
    """Authenticated bundle returned by the validated diagnostic loader.

    A consumer holding this object has established that:
    1. Campaign regime is CURRENT and the automatic diagnostic is complete;
    2. The immutable prepared generation was loaded and authenticated;
    3. Target-size scientific identity matches the canonical generation;
    4. P3 execution context matches the canonical generation;
    5. The persisted execution root was resolved through the real P3 owner;
    6. The adopted execution head and reducer state were authenticated;
    7. The recommended N and the exact identity of the data it names were
       re-derived from the authenticated terminal reducer state and P2 training
       order;
    8. The persisted diagnostic projection matches the re-derived projection.

    Holding this object establishes what the automatic screen found.  It does
    not establish, and never has established, what the campaign will train on.
    """

    revision: TargetSizeCampaignRevision
    authorities: Any
    head: Any
    projection: TargetSizeAutoDiagnostic
    #: The P3 execution identity this load already reconstructed and checked.
    #: The portable report is a projection of exactly these objects, so it never
    #: rebuilds a second, possibly divergent, view of the same screen.
    schedule: Any = None
    context: Any = None
    optimizer_policy: Any = None

    @property
    def has_recommendation(self) -> bool:
        return self.projection.has_recommendation

    @property
    def recommended_target_size(self) -> int | None:
        return self.projection.recommended_target_size

    @property
    def recommended_membership_digest(self) -> str | None:
        return self.projection.recommended_membership_digest

    @property
    def reducer_status(self) -> str:
        return self.projection.reducer_status

    @property
    def terminal_reason_codes(self) -> tuple[str, ...]:
        return self.projection.terminal_reason_codes


def load_validated_target_size_auto_diagnostic(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    expected_revision: TargetSizeCampaignRevision | None = None,
) -> ValidatedTargetSizeAutoDiagnostic:
    """Reconstruct, authenticate, and re-derive the current automatic diagnostic.

    This is the single authoritative load path for the automatic screen's own
    evidence.  It is *not* a post-selection entry point: P5 binds to the frozen
    selection admitted at ``cross-validate``. The loader always establishes the
    current campaign revision directly from CampaignStore. If an expected_revision
    assertion token is passed, it must match the current revision exactly.
    Nothing persisted is trusted blindly: the immutable prepared generation is
    loaded and authenticated against the identities the campaign store binds,
    the P3 execution context is re-derived, the persisted execution root and
    adopted immutable head are re-authenticated through P3 owners, and the
    diagnostic recommendation is re-derived before returning.
    """

    from ._campaign_cli_core import _cfg, _optimizer_policy
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_paths import target_size_execution_root
    from .campaign_prepared_generation import PreparedGenerationError
    from .campaign_target_size_runtime import (
        load_prepared_target_size_generation,
    )
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        build_target_size_execution_context,
        build_target_size_screen_schedule,
        resolve_target_size_optimizer_normalization_policy,
    )

    current = require_current_target_size_runtime(store)
    if expected_revision is not None:
        if (
            current.state_revision != expected_revision.state_revision
            or current.sequence != expected_revision.sequence
            or current.state.generation != expected_revision.state.generation
            or current.state.lifecycle != expected_revision.state.lifecycle
        ):
            raise TargetSizeDiagnosticProjectionError(
                f"Supplied expected revision (generation {expected_revision.state.generation}, "
                f"revision {expected_revision.state_revision}) does not match the current "
                f"CampaignStore revision (generation {current.state.generation}, "
                f"revision {current.state_revision}). Historical diagnostic state cannot "
                "be loaded as current."
            )

    state = current.state
    if state.lifecycle is not TargetSizeLifecycle.DIAGNOSTIC_COMPLETE:
        raise TargetSizeDiagnosticProjectionError(
            f"Campaign canonical generation {state.generation} has no complete automatic "
            f"target-size diagnostic (lifecycle={state.lifecycle.value})."
        )
    if state.auto_diagnostic is None:
        raise TargetSizeDiagnosticProjectionError(
            f"Campaign canonical generation {state.generation} has no persisted "
            "automatic diagnostic projection."
        )

    # The prepared generation is loaded, not rebuilt: exposing a terminal result
    # must not depend on reinterpreting live source bytes, and the loader itself
    # proves the published substrate matches every identity the campaign store
    # binds for this generation.
    try:
        authorities = load_prepared_target_size_generation(
            cfg, paths, store, current
        )
    except PreparedGenerationError as exc:
        # Exposing a diagnostic result under a substrate that no longer
        # authenticates is exactly the projection failure this error names.
        raise TargetSizeDiagnosticProjectionError(str(exc)) from exc

    aggregate = authorities.aggregate
    definition = aggregate.definition
    schedule = build_target_size_screen_schedule(
        definition.policy.fidelity_epochs,
        normalization_policy=resolve_target_size_optimizer_normalization_policy(cfg),
    )
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
        raise TargetSizeDiagnosticProjectionError(
            "The reconstructed P3 execution context does not match the persisted "
            "diagnostic generation. Run `prepare` to bind a fresh canonical generation."
        )

    root = target_size_execution_root(paths, state.generation)
    if not root.is_dir():
        from .campaign_target_size_adoption import TargetSizeAdoptionCorruptionError

        raise TargetSizeAdoptionCorruptionError(
            f"The campaign-owned target-size execution root {root} does not exist."
        )
    resolver = TargetSizeExecutionResolver(root)

    head = validate_auto_diagnostic(current, resolver=resolver, definition=definition)

    return ValidatedTargetSizeAutoDiagnostic(
        revision=current,
        authorities=authorities,
        head=head,
        projection=state.auto_diagnostic,
        schedule=schedule,
        context=context,
        optimizer_policy=optimizer_policy,
    )


__all__ = [
    "SCIENTIFIC_IDENTITY_FIELDS",
    "TargetSizeDiagnosticProjectionError",
    "TargetSizeInvalidation",
    "ValidatedTargetSizeAutoDiagnostic",
    "classify_target_size_invalidation",
    "commit_auto_diagnostic",
    "derive_auto_diagnostic",
    "load_validated_target_size_auto_diagnostic",
    "validate_auto_diagnostic",
]
