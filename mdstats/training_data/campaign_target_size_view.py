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


def _build_terminal_target_size_result_view(
    validated_result: Any,
) -> dict[str, Any]:
    """Private helper: construct the terminal target-size result view payload.

    This helper is reachable only from expose_current_target_size_terminal_result
    or write_current_target_size_result_view after exposure-time CampaignStore
    currentness validation.
    """
    from .campaign_target_size_terminal import ValidatedTargetSizeTerminalResult

    if not isinstance(validated_result, ValidatedTargetSizeTerminalResult):
        raise TypeError(
            f"_build_terminal_target_size_result_view requires ValidatedTargetSizeTerminalResult, got {type(validated_result).__name__}"
        )

    revision = validated_result.revision
    state = revision.state
    head = validated_result.head
    return {
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
        "reducer_status": head.post_state.status.value,
        "active_candidate_sizes": list(head.post_state.active_candidate_sizes),
        "completed_boundary_epochs": list(head.post_state.completed_boundary_epochs),
        "selected_target_size": head.post_state.selected_target_size,
        "selected_membership_digest": head.post_state.selected_membership_digest,
    }


def _write_terminal_target_size_result_view(
    path: str | os.PathLike[str],
    validated_result: Any,
) -> dict[str, Any]:
    """Private helper: atomically write the terminal result view to disk."""
    payload = _build_terminal_target_size_result_view(validated_result)
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


def build_target_size_result_view(
    revision: TargetSizeCampaignRevision,
    *,
    validated_result: Any | None = None,
    resolver: Any | None = None,
) -> dict[str, Any]:
    """Render the nonterminal target-size campaign state as a derived view.

    Nonterminal views render intermediate progress metadata without scientific
    terminal selection. Any terminal revision is rejected unconditionally: terminal
    views must be rendered via expose_current_target_size_terminal_result /
    write_current_target_size_result_view to guarantee exposure-time CampaignStore
    currentness.
    """
    from .campaign_target_size_terminal import TargetSizeTerminalProjectionError

    if revision.state.terminal is not None:
        raise TargetSizeTerminalProjectionError(
            "build_target_size_result_view cannot render terminal target-size state. "
            "Public terminal results require exposure-time CampaignStore currentness validation via "
            "expose_current_target_size_terminal_result or write_current_target_size_result_view."
        )

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
        "terminal": None,
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
    validated_result: Any | None = None,
    resolver: Any | None = None,
) -> dict[str, Any]:
    """Atomically (re)write a nonterminal derived view; safe to repeat after any crash.

    Any terminal revision is rejected unconditionally: terminal views must be
    written via write_current_target_size_result_view.
    """
    from .campaign_target_size_terminal import TargetSizeTerminalProjectionError

    if revision.state.terminal is not None:
        raise TargetSizeTerminalProjectionError(
            "write_target_size_result_view cannot write terminal target-size state. "
            "Public terminal results require exposure-time CampaignStore currentness validation via "
            "write_current_target_size_result_view."
        )

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


def write_nonterminal_target_size_result_view(
    path: str | os.PathLike[str],
    revision: TargetSizeCampaignRevision,
    *,
    resolver: Any | None = None,
) -> dict[str, Any]:
    """Atomically write a non-authoritative progress view for active/waiting state."""
    return write_target_size_result_view(path, revision, resolver=resolver)


def expose_current_target_size_terminal_result(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    expected_revision: TargetSizeCampaignRevision | None = None,
) -> Any:
    """Authoritative exposure-time entrypoint for the current terminal target-size result.

    This function re-establishes CampaignStore currentness and executes the full
    canonical P1/P2/P3 validation chain in the same invocation. It is the single
    exposure boundary for all current-terminal views, reporting, and P5 consumption.
    """
    from .campaign_target_size_terminal import (
        load_validated_target_size_terminal_result,
    )

    return load_validated_target_size_terminal_result(
        cfg, paths, store, expected_revision=expected_revision
    )


def write_current_target_size_result_view(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    path: str | os.PathLike[str] | None = None,
    expected_revision: TargetSizeCampaignRevision | None = None,
) -> dict[str, Any]:
    """Atomically write the current terminal result view after exposure-time currentness validation."""
    validated = expose_current_target_size_terminal_result(
        cfg, paths, store, expected_revision=expected_revision
    )
    destination = (
        Path(path)
        if path is not None
        else (Path(paths.results) / "target-size-state.json")
    )
    return _write_terminal_target_size_result_view(destination, validated)


__all__ = [
    "TARGET_SIZE_RESULT_VIEW_SCHEMA",
    "build_target_size_result_view",
    "expose_current_target_size_terminal_result",
    "write_current_target_size_result_view",
    "write_nonterminal_target_size_result_view",
    "write_target_size_result_view",
]
