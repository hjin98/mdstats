"""Non-authoritative human-readable projection of current target-size state.

Nothing in this module is authority.  The campaign store plus authenticated P3
evidence remain the only sources of truth; a view is a derived rendering that
can be deleted and rebuilt at any time without touching science.  That is
exactly the recovery contract for the case where a campaign transaction
committed but the derived result file was lost: the view is rebuilt from
campaign state and P3, and the committed scientific transition is never rolled
back to match a missing file.

The projection deliberately re-resolves the adopted execution head through the
real P3 resolver instead of copying reducer content into the campaign database,
so a view can never drift into a second result manifest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import tempfile

from .campaign_target_size_state import TargetSizeCampaignRevision

TARGET_SIZE_RESULT_VIEW_SCHEMA = "mdstats.target-size-result-view.v1"


def build_target_size_result_view(
    revision: TargetSizeCampaignRevision, *, resolver: Any | None = None
) -> dict[str, Any]:
    """Render the current target-size campaign state as a derived view."""

    state = revision.state
    payload: dict[str, Any] = {
        "schema": TARGET_SIZE_RESULT_VIEW_SCHEMA,
        "authoritative": False,
        "authority": "campaign store plus authenticated P3 immutable evidence",
        "regime": state.regime.value,
        "canonical_generation": state.generation,
        "execution_attempt": state.attempt,
        "lifecycle": state.lifecycle.value,
        "campaign_state_revision": revision.state_revision,
        "campaign_state_sequence": revision.sequence,
        "experiment_definition_digest": state.experiment_definition_digest,
        "execution_context_digest": state.execution_context_digest,
        "execution_root": state.execution_root,
        "adopted_execution_head_digest": state.adopted_execution_head_digest,
        "adopted_reducer_state_digest": state.adopted_reducer_state_digest,
        "terminal": None if state.terminal is None else state.terminal.to_dict(),
    }
    if resolver is not None and state.adopted_execution_head_digest is not None:
        from .campaign_target_size_adoption import load_adopted_execution_head

        head = load_adopted_execution_head(resolver, revision)
        payload["reducer_status"] = head.post_state.status.value
        payload["active_candidate_sizes"] = list(head.post_state.active_candidate_sizes)
        payload["completed_boundary_epochs"] = list(
            head.post_state.completed_boundary_epochs
        )
        payload["selected_target_size"] = head.post_state.selected_target_size
        payload["selected_membership_digest"] = (
            head.post_state.selected_membership_digest
        )
    return payload


def write_target_size_result_view(
    path: str | os.PathLike[str],
    revision: TargetSizeCampaignRevision,
    *,
    resolver: Any | None = None,
) -> dict[str, Any]:
    """Atomically (re)write the derived view; safe to repeat after any crash."""

    payload = build_target_size_result_view(revision, resolver=resolver)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=destination.name, suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return payload


__all__ = [
    "TARGET_SIZE_RESULT_VIEW_SCHEMA",
    "build_target_size_result_view",
    "write_target_size_result_view",
]
