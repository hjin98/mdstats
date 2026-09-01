"""Cross-store adoption of authenticated P3 execution heads into campaign state.

SQLite and the immutable P3 filesystem evidence cannot share one physical
atomic transaction, so the cutover uses immutable-first publication followed by
a bounded compare-and-set adoption.  P3 produces and validates its own evidence,
commits or reconciles its execution-head graph, and releases its screen lock
*before* the campaign store opens a short write transaction that binds the exact
authenticated head and reducer identity.

That ordering is the point of this module.  It never opens a campaign
transaction around P3 reconciliation, large artifact hashing, or model
reconstruction, and it never lets campaign state manufacture scientific
authority: an adopted head must already exist as immutable evidence, its
scientific identity must match the campaign generation's bound P2 experiment and
P3 execution context, and a campaign row that references a missing or corrupt
head is a hard corruption failure rather than something to be rebuilt from the
campaign summary.

``current_head.json`` never participates here.  It is a rebuildable P3-local
recovery pointer, so this module adopts only the immutable head object returned
by the real P3 reconciler.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._common import TrainingDataError, TrainingDataInputError
from .campaign_target_size_state import (
    TargetSizeCampaignRevision,
    TargetSizeCampaignState,
    TargetSizeCampaignStateError,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
)


class TargetSizeAdoptionError(TargetSizeCampaignStateError):
    """The campaign cannot adopt the supplied P3 execution state."""


class TargetSizeAdoptionCorruptionError(TargetSizeAdoptionError):
    """Campaign state references P3 evidence that is missing or unauthenticated."""


class TargetSizeScientificIdentityError(TargetSizeAdoptionError):
    """Reconciled P3 evidence belongs to a different scientific identity."""


def _head_identity(head: Any) -> tuple[str, str]:
    try:
        return str(head.content_digest), str(head.post_state.content_digest)
    except AttributeError as exc:  # pragma: no cover - defensive
        raise TrainingDataInputError(
            "Campaign adoption requires one immutable TargetSizeExecutionHead."
        ) from exc


def validate_head_scientific_identity(
    revision: TargetSizeCampaignRevision, head: Any
) -> None:
    """Reject a head that does not belong to this generation's experiment.

    Equality of a selected integer or of a head digest alone never proves
    equivalence; the experiment definition and execution context bound by the
    campaign generation must match the reducer states carried by the head.
    """

    state = revision.state
    post = head.post_state
    pre = head.pre_state
    if state.experiment_definition_digest is None:
        raise TargetSizeAdoptionError(
            "The current target-size generation has no bound P2 experiment definition; "
            "no P3 execution head can be adopted."
        )
    for name, observed in (
        ("pre-state", pre.experiment_definition_digest),
        ("post-state", post.experiment_definition_digest),
    ):
        if str(observed) != state.experiment_definition_digest:
            raise TargetSizeScientificIdentityError(
                f"Reconciled P3 execution head {name} binds a different P2 experiment "
                "definition than the current campaign generation."
            )
    if state.execution_context_digest is not None:
        for name, observed in (
            ("pre-state", pre.execution_context_digest),
            ("post-state", post.execution_context_digest),
        ):
            if observed is not None and str(observed) != state.execution_context_digest:
                raise TargetSizeScientificIdentityError(
                    f"Reconciled P3 execution head {name} binds a different P3 execution "
                    "context than the current campaign generation."
                )


def load_adopted_execution_head(resolver: Any, revision: TargetSizeCampaignRevision) -> Any:
    """Re-resolve the immutable head the campaign claims to have adopted.

    Failure here is hard corruption.  Campaign state carries references, not
    scientific authority, so a missing or unauthenticated head is never
    recreated from the campaign summary.
    """

    from .target_size_execution.coordinator import TargetSizeExecutionHead

    state = revision.state
    if state.adopted_execution_head_digest is None:
        raise TargetSizeAdoptionError(
            "The current target-size campaign state has not adopted an execution head."
        )
    path = resolver.head_path(state.adopted_execution_head_digest)
    if not path.is_file():
        raise TargetSizeAdoptionCorruptionError(
            "Campaign state references a P3 execution head that is not present in the "
            f"immutable execution root: {state.adopted_execution_head_digest}. The "
            "scientific authority cannot be rebuilt from campaign state."
        )
    try:
        head = resolver.load_typed_content_addressed(
            path,
            state.adopted_execution_head_digest,
            TargetSizeExecutionHead.from_dict,
        )
    except TrainingDataError as exc:
        raise TargetSizeAdoptionCorruptionError(
            "Campaign state references a P3 execution head that failed authentication: "
            f"{exc}"
        ) from exc
    if str(head.post_state.content_digest) != state.adopted_reducer_state_digest:
        raise TargetSizeAdoptionCorruptionError(
            "The adopted P3 execution head does not carry the reducer state the "
            "campaign generation bound to it."
        )
    return head


def adopt_reconciled_execution_head(
    store: Any,
    revision: TargetSizeCampaignRevision,
    head: Any,
    *,
    lifecycle: TargetSizeLifecycle = TargetSizeLifecycle.SCREEN_ACTIVE,
) -> TargetSizeCampaignRevision:
    """CAS-adopt the exact authenticated head/reducer identity.

    The caller must already have reconciled through the real P3 owner and let
    P3 release its screen lock.  Adopting an identity the campaign already holds
    is a no-op, which is what makes crash recovery cheap: work that is already
    durable is never rerun.
    """

    state = revision.state
    if state.regime is not TargetSizeRegime.CURRENT:
        raise TargetSizeAdoptionError(
            "Only a campaign running the current target-size architecture can adopt "
            "P3 execution state."
        )
    head_digest, reducer_digest = _head_identity(head)
    validate_head_scientific_identity(revision, head)
    if (
        state.adopted_execution_head_digest == head_digest
        and state.adopted_reducer_state_digest == reducer_digest
        and state.lifecycle is lifecycle
    ):
        return revision
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.CURRENT,
        generation=state.generation,
        lifecycle=lifecycle,
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
        adopted_execution_head_digest=head_digest,
        adopted_reducer_state_digest=reducer_digest,
    )
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.ADOPT_EXECUTION_HEAD,
        expected=revision.expectation(),
        successor=successor,
    ).revision


def reconcile_and_adopt_target_size_head(
    store: Any,
    revision: TargetSizeCampaignRevision,
    *,
    root: str | Path,
    authority: Any,
) -> tuple[TargetSizeCampaignRevision, Any]:
    """Run the frozen cross-store transition order for one adoption.

    P3 reconciles and releases its screen mutation lock, and only then does a
    short campaign transaction bind the result.  No campaign transaction is open
    while P3 reconciliation runs, and no P3 lock is held while SQLite commits.
    """

    from .target_size_execution.coordinator import reconcile_target_size_screen_root

    head = reconcile_target_size_screen_root(root, authority)
    if head is None:
        return revision, None
    return adopt_reconciled_execution_head(store, revision, head), head


__all__ = [
    "TargetSizeAdoptionCorruptionError",
    "TargetSizeAdoptionError",
    "TargetSizeScientificIdentityError",
    "adopt_reconciled_execution_head",
    "load_adopted_execution_head",
    "reconcile_and_adopt_target_size_head",
    "validate_head_scientific_identity",
]
