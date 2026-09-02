"""CampaignStore maintenance as separately authorized owner actions.

Bounding diagnostic events and rewriting a SQLite file are two different
decisions with two different costs, and neither is a free tail call on the end
of a cleanup.

*They are planned, not implied.*  Maintenance appears in the cleanup plan as its
own action or it does not happen.  A cleanup that was refused as stale, or that
mutated nothing, cannot piggyback a database rewrite it never asked for.

*They are two authorities, not one.*  Pruning diagnostic events is a small
transaction; ``VACUUM`` rewrites the entire database beside itself.  A plan that
authorized the cheap one must never widen into the expensive one - not even when
the prune is what created the free pages.  So a prune action can only prune, a
rewrite action exists only when a *fresh* observation already satisfies the
configured reclaimable-byte/fraction predicate, and the post-prune rewrite (if it
ever becomes worthwhile) is left for the next fresh maintenance plan.

*Cleanup never depends on them.*  A skipped or failed maintenance is reported
truthfully and changes nothing about whether the file actions succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .admission import StorageAdmissionError, admit_storage_operation
from .plan import ACTION_PRUNE_EVENTS, ACTION_VACUUM_STATE, PlannedAction, planned_action
from .policy import StoragePolicy

MAINTENANCE_ARTIFACT_ID = "campaign_store:state"


@dataclass(frozen=True, slots=True)
class MaintenanceDecision:
    """Which campaign-state maintenance earned a place in this plan."""

    actions: tuple[PlannedAction, ...] = ()
    reasons: tuple[str, ...] = ()
    reclaimable_bytes: int = 0
    reclaimable_fraction: float = 0.0
    excess_events: int = 0

    @property
    def prune_action(self) -> PlannedAction | None:
        for action in self.actions:
            if action.action == ACTION_PRUNE_EVENTS:
                return action
        return None

    @property
    def vacuum_action(self) -> PlannedAction | None:
        for action in self.actions:
            if action.action == ACTION_VACUUM_STATE:
                return action
        return None

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


def measure_reclaimable(store: Any) -> tuple[int, int, int]:
    """``(reclaimable_bytes, total_bytes, event_count)`` from the store itself.

    The freelist is SQLite's own answer to "how much of this file is dead
    space", which is the only honest basis for deciding that a rewrite is worth
    its cost.
    """

    try:
        with store._connect() as db:  # noqa: SLF001 - the store owns its pool
            page_size = int(db.execute("PRAGMA page_size").fetchone()[0])
            page_count = int(db.execute("PRAGMA page_count").fetchone()[0])
            freelist = int(db.execute("PRAGMA freelist_count").fetchone()[0])
            events = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
    except Exception:
        return 0, 0, 0
    return freelist * page_size, page_count * page_size, events


def vacuum_is_worthwhile(
    store: Any, policy: StoragePolicy
) -> tuple[bool, int, float, str]:
    """Whether a fresh observation says the rewrite earns its cost."""

    reclaimable, total, _events = measure_reclaimable(store)
    fraction = (reclaimable / total) if total else 0.0
    worthwhile = reclaimable >= int(
        policy.sqlite_compaction_minimum_reclaimable_bytes
    ) or fraction >= float(policy.sqlite_compaction_minimum_reclaimable_fraction)
    detail = (
        f"{reclaimable} reclaimable byte(s) ({fraction:.1%}) of "
        f"{total} byte(s) in the campaign state database"
    )
    return worthwhile, reclaimable, fraction, detail


def plan_campaign_state_maintenance(
    store: Any, paths: Any, policy: StoragePolicy
) -> MaintenanceDecision:
    """Decide, separately, whether to prune events and whether to rewrite."""

    state_db = Path(paths.state_db)
    if not state_db.is_file():
        return MaintenanceDecision(
            reasons=("campaign state database is absent",)
        )

    reclaimable, total, events = measure_reclaimable(store)
    maximum_events = int(policy.sqlite_compaction_maximum_events)
    excess = max(0, events - maximum_events)
    worthwhile, _bytes, fraction, rewrite_detail = vacuum_is_worthwhile(store, policy)

    actions: list[PlannedAction] = []
    reasons: list[str] = []

    if excess > 0:
        actions.append(
            planned_action(
                action=ACTION_PRUNE_EVENTS,
                path=state_db,
                artifact_id=MAINTENANCE_ARTIFACT_ID,
                reason=(
                    f"bound diagnostic history to the newest {maximum_events} "
                    f"event(s); {excess} excess record(s) are present"
                ),
                capability_cost="diagnostic_history_only",
                binding={
                    "excess_events": excess,
                    "maximum_events": maximum_events,
                    "observed_events": events,
                },
                size_bytes=0,
            )
        )
    else:
        reasons.append(
            f"diagnostic history is within its bound ({events} <= {maximum_events})"
        )

    if worthwhile:
        actions.append(
            planned_action(
                action=ACTION_VACUUM_STATE,
                path=state_db,
                artifact_id=MAINTENANCE_ARTIFACT_ID,
                reason=f"rewrite the campaign state database: {rewrite_detail}",
                capability_cost="none",
                binding={
                    "reclaimable_bytes": reclaimable,
                    "reclaimable_fraction": round(fraction, 6),
                    "total_bytes": total,
                },
                size_bytes=0,
            )
        )
    else:
        # Deliberately *not* re-evaluated after pruning. Free pages the prune
        # itself creates may well make a rewrite worthwhile, and the next fresh
        # maintenance plan is where that decision belongs: a plan that
        # authorized cheap pruning must not become authorization for a full
        # database rewrite.
        reasons.append(f"a database rewrite is not worthwhile: {rewrite_detail}")

    return MaintenanceDecision(
        actions=tuple(actions),
        reasons=tuple(reasons)
        or ("campaign state maintenance is worthwhile",),
        reclaimable_bytes=reclaimable,
        reclaimable_fraction=fraction,
        excess_events=excess,
    )


def campaign_state_maintenance_engine(store: Any, policy: StoragePolicy):
    """Execute one planned prune or rewrite action, or refuse it truthfully."""

    def _claims_the_path(action: PlannedAction, snapshot: Any) -> bool:
        # The campaign store is protected by its own owner and by everything
        # downstream of it. That is exactly the artifact these actions maintain,
        # so protection is expected here; what must not happen is maintaining a
        # file some *other* owner is protecting.
        view = snapshot.view(MAINTENANCE_ARTIFACT_ID)
        return view is not None and view.path == action.path

    def _maintain(action: PlannedAction, snapshot: Any, result: Any) -> None:
        if action.action not in (ACTION_PRUNE_EVENTS, ACTION_VACUUM_STATE):
            result.refused.append(
                {**action.to_dict(), "refusal": "not a campaign-state maintenance action"}
            )
            return
        if not _claims_the_path(action, snapshot):
            result.refused.append(
                {
                    **action.to_dict(),
                    "refusal": (
                        "the campaign-state owner does not claim this path; "
                        "maintenance never touches anything else"
                    ),
                }
            )
            return

        if action.action == ACTION_PRUNE_EVENTS:
            try:
                pruned = store.prune_events(
                    maximum_events=int(policy.sqlite_compaction_maximum_events)
                )
            except Exception as exc:
                # Cleanup correctness never depends on maintenance succeeding.
                result.refused.append(
                    {**action.to_dict(), "refusal": f"event pruning failed: {exc}"}
                )
                return
            result.completed.append(
                {
                    **action.to_dict(),
                    "events_pruned": int(pruned),
                    "vacuum_performed": False,
                }
            )
            return

        # A rewrite re-establishes its own benefit under the fresh state it is
        # about to rewrite, so a plan built when the file was full of free pages
        # cannot rewrite a file that no longer is.
        worthwhile, _bytes, _fraction, detail = vacuum_is_worthwhile(store, policy)
        if not worthwhile:
            result.refused.append(
                {
                    **action.to_dict(),
                    "refusal": (
                        f"the database rewrite is no longer worthwhile: {detail}"
                    ),
                    "vacuum_performed": False,
                }
            )
            return
        try:
            size = int(action.path.stat().st_size) if action.path.is_file() else 0
            admission = admit_storage_operation(
                action.path.parent,
                policy,
                # VACUUM's peak is the original plus its rewritten copy.
                required_peak_bytes=2 * size,
                required_inodes=2,
            )
        except StorageAdmissionError as exc:
            result.refused.append(
                {
                    **action.to_dict(),
                    "refusal": f"the rewrite was not admitted and was skipped: {exc}",
                    "vacuum_performed": False,
                }
            )
            return
        try:
            store.vacuum()
        except Exception as exc:
            result.refused.append(
                {
                    **action.to_dict(),
                    "refusal": f"the database rewrite failed: {exc}",
                    "vacuum_performed": False,
                }
            )
            return
        result.completed.append(
            {
                **action.to_dict(),
                "events_pruned": 0,
                "vacuum_performed": True,
                "admission": admission.to_dict(),
            }
        )

    return _maintain


__all__ = [
    "MAINTENANCE_ARTIFACT_ID",
    "MaintenanceDecision",
    "campaign_state_maintenance_engine",
    "measure_reclaimable",
    "plan_campaign_state_maintenance",
    "vacuum_is_worthwhile",
]
