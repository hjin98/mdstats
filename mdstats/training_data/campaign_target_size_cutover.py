"""Destructive target-size generation cutover owned by the campaign store.

The campaign moves through exactly three durable regimes: ``legacy`` (the
workspace still holds retired derived target-size authority and has never been
converted), ``transitioning`` (a cutover is in progress and owns the campaign),
and ``current`` (the accepted P1/P2/P3 graph is the only target-size authority).

The cutover is campaign-wide and destructive by design.  Retired derived
target-size state is never translated into current P1/P2/P3 objects: it is
quarantined under a namespace that no current loader reads, so a stale selected
``N``, an old selector plan, or a retired materialization can never re-enter the
current runtime through schema translation or record-name reuse.  Only
lower-level content-addressed inputs whose identity is independent of retired
target-size semantics may be reused, and only by re-validating them through
their current owners.

Every regime step is one compare-and-set transition against the canonical
generation and the exact predecessor state revision, so an interrupted cutover
is owned by the persisted transition rather than by the process that started
it.  A fresh process resumes the exact same cutover; the original PID is
irrelevant.  Because inventory and quarantine are idempotent and run only while
the regime is ``transitioning``, a crash at any point between the two CAS steps
replays safely.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .campaign_target_size_state import (
    TargetSizeCampaignRevision,
    TargetSizeCampaignState,
    TargetSizeCampaignStateError,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    ensure_target_size_campaign_revision,
    load_target_size_campaign_revision,
)

QUARANTINE_KEY_PREFIX = "quarantine:retired-target-size:"

#: Exact campaign record keys whose meaning is retired target-size derived
#: authority.  None of these may be read as current authority after cutover.
RETIRED_TARGET_SIZE_RECORD_KEYS: tuple[str, ...] = (
    # Retired selector state and its prepare-time selected-N outcome.
    "target_size_study",
    "target_size_historical_candidate_authority",
    # Retired role/domain target-size authority.
    "target_data_role_freeze",
    # Retired FEAS/MVIDX/MVSEL/REPAIR/MVQUAL coverage-selection chain.
    "target_coverage_reference",
    "target_coverage_feasibility",
    "target_coverage_sparse_index",
    "target_multi_view_selection_v2",
    "target_multi_view_repair_v2",
    "target_multi_view_qualification_v2",
    # Retired target-size prepare receipt / migration alias.
    "prepare_restart_receipt",
    # Retired screening execution and interim ranking authority.
    "training_campaign",
    "interim_evaluation",
    "available_model_verification_set",
    # Pre-target CV/MLCV role and catalog dependencies retired by the parent.
    "mlcv_lifecycle_authority",
    "mlcv_campaign_cv",
    "mlcv_final_selection",
    "mlcv_final_committee",
    "mlcv_verification_policy",
    "mlcv_verification",
    "mlcv_locked_test_evaluation",
    "mlcv_locked_test",
    "mlcv_production_model",
    "mlcv_protocol_freeze",
    "mlcv_migration",
)

#: Record-key prefixes whose members are retired target-size derived state:
#: per-variant prescribed materialization authority, retired screening
#: execution/continuation records, and retired ranking/selection records.
RETIRED_TARGET_SIZE_RECORD_PREFIXES: tuple[str, ...] = (
    "materialization:",
    "data8:",
    "execution:",
    "train2_runtime:",
    "adaptive_stop:",
    "lightweight_rank:",
    "checkpoint_catalog:",
    "checkpoint_retention:",
    "checkpoint_shortlist:",
    "evaluation:",
    "selection:",
    "interim_member:",
    "committee_member:",
    "mlcv_run_selection:",
    "mlcv_physical_attempt:",
)

#: Lower-level content-addressed inputs whose identity does not depend on any
#: retired target-size semantics.  They may be reused, but only by
#: re-validating them through their current owners: the campaign never treats
#: their mere presence as current target-size authority.
REUSABLE_LOWER_LEVEL_RECORD_KEYS: tuple[str, ...] = (
    "source_catalog",
    "frame_catalog",
    "data4",
    "data5",
    "data6",
)


class TargetSizeCutoverError(TargetSizeCampaignStateError):
    """The campaign cannot run current target-size work in its present regime."""


def _is_retired_key(key: str) -> bool:
    if key in RETIRED_TARGET_SIZE_RECORD_KEYS:
        return True
    return any(key.startswith(prefix) for prefix in RETIRED_TARGET_SIZE_RECORD_PREFIXES)


@dataclass(frozen=True, slots=True)
class TargetSizeRetiredStateInventory:
    """What retired target-size authority a workspace still holds."""

    retired_record_keys: tuple[str, ...]
    reusable_lower_level_record_keys: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not self.retired_record_keys

    def to_dict(self) -> dict[str, Any]:
        return {
            "retired_record_keys": list(self.retired_record_keys),
            "reusable_lower_level_record_keys": list(
                self.reusable_lower_level_record_keys
            ),
        }


def inventory_retired_target_size_state(
    store: Any,
) -> TargetSizeRetiredStateInventory:
    """Enumerate retired target-size authority before any mutation.

    This reads record *names* only.  Retired payloads are never deserialized,
    because deserializing them through a current loader is exactly the
    reinterpretation the cutover forbids.
    """

    live = set(store.record_keys())
    retired = tuple(sorted(key for key in live if _is_retired_key(key)))
    reusable = tuple(
        key for key in REUSABLE_LOWER_LEVEL_RECORD_KEYS if key in live
    )
    return TargetSizeRetiredStateInventory(
        retired_record_keys=retired,
        reusable_lower_level_record_keys=reusable,
    )


def quarantine_retired_target_size_state(
    store: Any, *, generation: int
) -> tuple[str, ...]:
    """Move retired target-size records out of the current namespace.

    Quarantine renames the record key inside one SQLite transaction rather than
    decoding and rewriting the payload.  That keeps the operation cheap and
    total: sharded and content-addressed records quarantine exactly like
    compact ones, and no retired payload is ever passed through a current
    deserializer.  The quarantined rows stay readable as forensic history but
    are unreachable from every current authority lookup.

    The operation is idempotent, so an interrupted cutover replays it safely.
    """

    generation = int(generation)
    prefix = f"{QUARANTINE_KEY_PREFIX}g{generation}:"
    with store.exclusive_transaction() as db:
        rows = db.execute("SELECT key FROM records").fetchall()
        moved: list[str] = []
        for (key,) in rows:
            name = str(key)
            if name.startswith(QUARANTINE_KEY_PREFIX) or not _is_retired_key(name):
                continue
            db.execute("DELETE FROM records WHERE key=?", (prefix + name,))
            db.execute(
                "UPDATE records SET key=? WHERE key=?", (prefix + name, name)
            )
            moved.append(name)
    return tuple(sorted(moved))


def assert_no_retired_target_size_authority(store: Any) -> None:
    """Prove no retired target-size record is reachable as current authority."""

    remaining = inventory_retired_target_size_state(store).retired_record_keys
    if remaining:
        raise TargetSizeCutoverError(
            "Retired target-size records are still reachable as current authority: "
            + ", ".join(remaining[:8])
            + ("..." if len(remaining) > 8 else "")
        )


def begin_target_size_cutover(store: Any) -> TargetSizeCampaignRevision:
    """CAS ``legacy -> transitioning`` and allocate the canonical generation.

    Returns the transitioning revision.  Calling this on a campaign that is
    already transitioning returns the persisted transition unchanged, which is
    what lets a fresh process resume an interrupted cutover.
    """

    revision = ensure_target_size_campaign_revision(store)
    if revision.state.regime is TargetSizeRegime.TRANSITIONING:
        return revision
    if revision.state.regime is TargetSizeRegime.CURRENT:
        raise TargetSizeCutoverError(
            "This campaign already runs the current target-size architecture; the "
            "destructive cutover cannot be repeated. Use the ordinary "
            "`prepare`/`select-target-size` lifecycle."
        )
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.TRANSITIONING,
        generation=revision.state.generation + 1,
        lifecycle=TargetSizeLifecycle.AWAITING_AUTHORITIES,
        disposition="cutover_in_progress",
        disposition_detail=(
            "Destructive target-size generation cutover is in progress; retired "
            "derived target-size authority is being quarantined."
        ),
    )
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=revision.expectation(),
        successor=successor,
    ).revision


def bind_current_target_size_authorities(
    store: Any,
    revision: TargetSizeCampaignRevision,
    *,
    frame_authority_digest: str,
    neutral_statistical_base_digest: str,
    split_exclusion_digest: str,
    policy_digest: str,
    experiment_definition_digest: str,
    aggregate_digest: str,
) -> TargetSizeCampaignRevision:
    """CAS-bind the reconstructed current P1/P2 authority identities.

    The caller must have constructed these through the accepted P1/P2 owners.
    Only stable identities are persisted; the owning loaders revalidate them.
    """

    if revision.state.regime is not TargetSizeRegime.TRANSITIONING:
        raise TargetSizeCutoverError(
            "Current target-size authorities may be bound only while the campaign "
            "regime is transitioning."
        )
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.TRANSITIONING,
        generation=revision.state.generation,
        lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
        frame_authority_digest=frame_authority_digest,
        neutral_statistical_base_digest=neutral_statistical_base_digest,
        split_exclusion_digest=split_exclusion_digest,
        policy_digest=policy_digest,
        experiment_definition_digest=experiment_definition_digest,
        aggregate_digest=aggregate_digest,
        disposition="cutover_in_progress",
        disposition_detail=(
            "Current P1/P2 target-size authorities are bound; the cutover is "
            "awaiting final validation."
        ),
    )
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BIND_AUTHORITIES,
        expected=revision.expectation(),
        successor=successor,
    ).revision


def complete_target_size_cutover(
    store: Any, revision: TargetSizeCampaignRevision
) -> TargetSizeCampaignRevision:
    """CAS ``transitioning -> current`` after proving the cutover is complete."""

    if revision.state.regime is not TargetSizeRegime.TRANSITIONING:
        raise TargetSizeCutoverError(
            "Only a transitioning campaign can be promoted to the current "
            "target-size runtime."
        )
    if revision.state.lifecycle is not TargetSizeLifecycle.AUTHORITIES_BOUND:
        raise TargetSizeCutoverError(
            "The current target-size runtime cannot be promoted before the current "
            "P1/P2 authorities are bound."
        )
    assert_no_retired_target_size_authority(store)
    successor = TargetSizeCampaignState(
        regime=TargetSizeRegime.CURRENT,
        generation=revision.state.generation,
        lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
        frame_authority_digest=revision.state.frame_authority_digest,
        neutral_statistical_base_digest=revision.state.neutral_statistical_base_digest,
        split_exclusion_digest=revision.state.split_exclusion_digest,
        policy_digest=revision.state.policy_digest,
        experiment_definition_digest=revision.state.experiment_definition_digest,
        aggregate_digest=revision.state.aggregate_digest,
    )
    return commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.COMPLETE_CUTOVER,
        expected=revision.expectation(),
        successor=successor,
    ).revision


def require_current_target_size_runtime(store: Any) -> TargetSizeCampaignRevision:
    """Return the current revision or fail closed with actionable guidance.

    There is no mixed runtime: a campaign either executes the current
    architecture or it does not execute target-size work at all.
    """

    revision = load_target_size_campaign_revision(store)
    if revision is None or revision.state.regime is TargetSizeRegime.LEGACY:
        raise TargetSizeCutoverError(
            "This campaign workspace still holds retired target-size selection state "
            "and has not been converted to the current target-size architecture. "
            "Retired selected-size, selector, role-domain, and coverage-selection "
            "records are never migrated or reinterpreted. Run `prepare` to perform "
            "the one-time destructive target-size cutover, which quarantines the "
            "retired records and rebuilds current authority from the source inputs."
        )
    if revision.state.regime is TargetSizeRegime.TRANSITIONING:
        raise TargetSizeCutoverError(
            "A destructive target-size cutover is in progress for canonical "
            f"generation {revision.state.generation} and still owns this campaign. "
            "Re-run `prepare` to resume the exact interrupted cutover; the original "
            "process does not need to survive. Target-size commands stay unavailable "
            "until the cutover completes, because no mixed old/new runtime exists."
        )
    return revision


__all__ = [
    "QUARANTINE_KEY_PREFIX",
    "RETIRED_TARGET_SIZE_RECORD_KEYS",
    "RETIRED_TARGET_SIZE_RECORD_PREFIXES",
    "REUSABLE_LOWER_LEVEL_RECORD_KEYS",
    "TargetSizeCutoverError",
    "TargetSizeRetiredStateInventory",
    "assert_no_retired_target_size_authority",
    "begin_target_size_cutover",
    "bind_current_target_size_authorities",
    "complete_target_size_cutover",
    "inventory_retired_target_size_state",
    "quarantine_retired_target_size_state",
    "require_current_target_size_runtime",
]
