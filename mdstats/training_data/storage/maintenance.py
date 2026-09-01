"""CampaignStore maintenance as a separately authorized owner action.

Bounding diagnostic events and rewriting a SQLite file are two different
decisions with two different costs, and neither is a free tail call on the end
of a cleanup.

*It is planned, not implied.*  Maintenance appears in the cleanup plan as its
own action or it does not happen.  A cleanup that was refused as stale, or that
mutated nothing, cannot piggyback a database rewrite it never asked for.

*The rewrite is benefit-gated.*  ``VACUUM`` rewrites the whole database.  It runs
only when SQLite's own freelist says there is material space to reclaim, or when
there are genuinely excess diagnostic events to prune, and only after storage
admission covers the temporary copy it makes beside the original.

*Cleanup never depends on it.*  A skipped or failed maintenance is reported
truthfully and changes nothing about whether the file actions succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .admission import StorageAdmissionError, admit_storage_operation
from .plan import ACTION_MAINTAIN_STATE, PlannedAction, planned_action
from .policy import StoragePolicy

MAINTENANCE_ARTIFACT_ID = "campaign_store:state"


@dataclass(frozen=True, slots=True)
class MaintenanceDecision:
    """Whether campaign-state maintenance earned a place in this plan."""

    action: PlannedAction | None
    reason: str
    reclaimable_bytes: int = 0
    excess_events: int = 0


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


def plan_campaign_state_maintenance(
    store: Any, paths: Any, policy: StoragePolicy
) -> MaintenanceDecision:
    """Decide whether this invocation should maintain the campaign store."""

    state_db = Path(paths.state_db)
    if not state_db.is_file():
        return MaintenanceDecision(None, "campaign state database is absent")

    reclaimable, total, events = measure_reclaimable(store)
    excess = max(0, events - int(policy.sqlite_compaction_maximum_events))
    fraction = (reclaimable / total) if total else 0.0
    worthwhile = (
        excess > 0
        or reclaimable >= int(policy.sqlite_compaction_minimum_reclaimable_bytes)
        or fraction >= float(policy.sqlite_compaction_minimum_reclaimable_fraction)
    )
    if not worthwhile:
        return MaintenanceDecision(
            None,
            (
                f"campaign state maintenance is not worthwhile: {reclaimable} reclaimable "
                f"byte(s) ({fraction:.1%}) and no excess diagnostic events"
            ),
            reclaimable_bytes=reclaimable,
            excess_events=excess,
        )
    return MaintenanceDecision(
        planned_action(
            action=ACTION_MAINTAIN_STATE,
            path=state_db,
            artifact_id=MAINTENANCE_ARTIFACT_ID,
            reason=(
                f"bound diagnostic events (excess={excess}) and reclaim "
                f"{reclaimable} byte(s) of database free space"
            ),
            capability_cost="diagnostic_history_only",
            binding={
                "reclaimable_bytes": reclaimable,
                "excess_events": excess,
                "maximum_events": int(policy.sqlite_compaction_maximum_events),
            },
            size_bytes=0,
        ),
        "campaign state maintenance is worthwhile",
        reclaimable_bytes=reclaimable,
        excess_events=excess,
    )


def campaign_state_maintenance_engine(store: Any, policy: StoragePolicy):
    """Execute one planned maintenance action, or refuse it truthfully."""

    def _maintain(action: PlannedAction, snapshot: Any, result: Any) -> None:
        if action.action != ACTION_MAINTAIN_STATE:
            result.refused.append(
                {**action.to_dict(), "refusal": "not a campaign-state maintenance action"}
            )
            return
        # The campaign store is protected by its own owner and by everything
        # downstream of it. That is exactly the artifact this action maintains,
        # so protection is expected here; what must not happen is maintaining a
        # file some *other* owner is protecting.
        view = snapshot.view(MAINTENANCE_ARTIFACT_ID)
        if view is None or view.path != action.path:
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
                    "refusal": f"maintenance was not admitted and was skipped: {exc}",
                }
            )
            return
        try:
            store.compact(maximum_events=int(policy.sqlite_compaction_maximum_events))
        except Exception as exc:
            # Cleanup correctness never depends on maintenance succeeding.
            result.refused.append(
                {**action.to_dict(), "refusal": f"maintenance failed: {exc}"}
            )
            return
        result.completed.append(
            {
                **action.to_dict(),
                "maintained": True,
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
]
