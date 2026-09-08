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
from typing import Any, Mapping
import json
import os
import tempfile

from .campaign_target_size_state import TargetSizeCampaignRevision

TARGET_SIZE_RESULT_VIEW_SCHEMA = "mdstats.target-size-result-view.v3"


def _build_diagnostic_target_size_result_view(
    validated_result: Any,
) -> dict[str, Any]:
    """Private helper: construct the completed-diagnostic result view payload.

    This helper is reachable only from expose_current_target_size_auto_diagnostic
    or write_current_target_size_result_view after exposure-time CampaignStore
    currentness validation.
    """
    from .campaign_target_size_diagnostic import ValidatedTargetSizeAutoDiagnostic

    if not isinstance(validated_result, ValidatedTargetSizeAutoDiagnostic):
        raise TypeError(
            f"_build_diagnostic_target_size_result_view requires ValidatedTargetSizeAutoDiagnostic, got {type(validated_result).__name__}"
        )

    from .target_size_experiment import (
        CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE,
    )

    revision = validated_result.revision
    state = revision.state
    head = validated_result.head
    reason_codes = tuple(head.post_state.terminal_reason_codes)
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
        "auto_diagnostic": (
            None if state.auto_diagnostic is None else state.auto_diagnostic.to_dict()
        ),
        "provisional_entries": [
            entry.to_dict() for entry in state.provisional_entries
        ],
        "frozen_entries": (
            None
            if state.frozen_entries is None
            else [entry.to_dict() for entry in state.frozen_entries]
        ),
        "reducer_status": head.post_state.status.value,
        "active_candidate_sizes": list(head.post_state.active_candidate_sizes),
        "completed_boundary_epochs": list(head.post_state.completed_boundary_epochs),
        "recommended_target_size": head.post_state.selected_target_size,
        "recommended_membership_digest": head.post_state.selected_membership_digest,
        "terminal_reason_codes": list(reason_codes),
        # A recommendation at the ceiling carries a scientific warning: the
        # configured practical budget, not a demonstrated plateau, bounded the
        # screen. It is a diagnostic caveat on advice, never a frozen decision.
        "nonconverged_at_configured_ceiling": (
            CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE in reason_codes
        ),
    }


def _write_diagnostic_target_size_result_view(
    path: str | os.PathLike[str],
    validated_result: Any,
) -> dict[str, Any]:
    """Private helper: atomically write the diagnostic result view to disk."""
    payload = _build_diagnostic_target_size_result_view(validated_result)
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
    """Render an in-progress target-size campaign state as a derived view.

    These views render intermediate diagnostic progress and the current
    proposal/freeze facts. A revision whose automatic diagnostic has completed is
    rejected unconditionally: those views must be rendered via
    expose_current_target_size_auto_diagnostic /
    write_current_target_size_result_view to guarantee exposure-time
    CampaignStore currentness.
    """
    from .campaign_target_size_diagnostic import TargetSizeDiagnosticProjectionError

    if revision.state.auto_diagnostic is not None:
        raise TargetSizeDiagnosticProjectionError(
            "build_target_size_result_view cannot render a completed automatic diagnostic. "
            "Public diagnostic results require exposure-time CampaignStore currentness validation via "
            "expose_current_target_size_auto_diagnostic or write_current_target_size_result_view."
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
        "auto_diagnostic": None,
        "provisional_entries": [
            entry.to_dict() for entry in state.provisional_entries
        ],
        "frozen_entries": (
            None
            if state.frozen_entries is None
            else [entry.to_dict() for entry in state.frozen_entries]
        ),
    }
    if resolver is not None and state.adopted_execution_head_digest is not None:
        from .campaign_target_size_adoption import load_adopted_execution_head

        head = load_adopted_execution_head(resolver, revision)
        payload["reducer_status"] = head.post_state.status.value
        payload["active_candidate_sizes"] = list(head.post_state.active_candidate_sizes)
        payload["completed_boundary_epochs"] = list(
            head.post_state.completed_boundary_epochs
        )
        payload["recommended_target_size"] = head.post_state.selected_target_size
        payload["recommended_membership_digest"] = (
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
    """Atomically (re)write an in-progress derived view; safe to repeat after a crash.

    A revision whose automatic diagnostic has completed is rejected
    unconditionally: those views are written via
    write_current_target_size_result_view.
    """
    from .campaign_target_size_diagnostic import TargetSizeDiagnosticProjectionError

    if revision.state.auto_diagnostic is not None:
        raise TargetSizeDiagnosticProjectionError(
            "write_target_size_result_view cannot write a completed automatic diagnostic. "
            "Public diagnostic results require exposure-time CampaignStore currentness validation via "
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


def expose_current_target_size_auto_diagnostic(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    expected_revision: TargetSizeCampaignRevision | None = None,
) -> Any:
    """Authoritative exposure-time entrypoint for the current automatic diagnostic.

    This function re-establishes CampaignStore currentness and executes the full
    canonical P1/P2/P3 validation chain in the same invocation. It is the single
    exposure boundary for every current diagnostic view and report. It is *not* a
    post-selection entry point: P5 binds to the frozen selection admitted at
    `cross-validate`, which needs no diagnostic at all.
    """
    from .campaign_target_size_diagnostic import (
        load_validated_target_size_auto_diagnostic,
    )

    return load_validated_target_size_auto_diagnostic(
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
    """Atomically write the current diagnostic result view after exposure-time currentness validation."""
    validated = expose_current_target_size_auto_diagnostic(
        cfg, paths, store, expected_revision=expected_revision
    )
    destination = (
        Path(path)
        if path is not None
        else (Path(paths.results) / "target-size-state.json")
    )
    return _write_diagnostic_target_size_result_view(destination, validated)


def build_selection_target_size_result_view(
    revision: TargetSizeCampaignRevision,
    *,
    existing_view: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a derived target-size result view after a selection change.

    This helper derives purely from committed ``revision.state`` without executing
    P3 diagnostic validation, loading frames, or requiring execution contexts.
    If diagnostic metadata was already established or committed, it is preserved.
    """
    from .target_size_experiment import (
        CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE,
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
        "auto_diagnostic": (
            None if state.auto_diagnostic is None else state.auto_diagnostic.to_dict()
        ),
        "provisional_entries": [
            entry.to_dict() for entry in state.provisional_entries
        ],
        "frozen_entries": (
            None
            if state.frozen_entries is None
            else [entry.to_dict() for entry in state.frozen_entries]
        ),
    }

    if (
        isinstance(existing_view, Mapping)
        and existing_view.get("canonical_generation") == state.generation
        and existing_view.get("execution_attempt") == state.attempt
    ):
        for key in (
            "reducer_status",
            "active_candidate_sizes",
            "completed_boundary_epochs",
            "recommended_target_size",
            "recommended_membership_digest",
            "terminal_reason_codes",
            "nonconverged_at_configured_ceiling",
        ):
            if key in existing_view:
                payload[key] = existing_view[key]
    elif state.auto_diagnostic is not None:
        diag = state.auto_diagnostic
        reason_codes = tuple(diag.terminal_reason_codes)
        payload["reducer_status"] = diag.reducer_status
        payload["recommended_target_size"] = diag.recommended_target_size
        payload["recommended_membership_digest"] = diag.recommended_membership_digest
        payload["terminal_reason_codes"] = list(reason_codes)
        payload["nonconverged_at_configured_ceiling"] = (
            CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE in reason_codes
        )

    return payload


def write_selection_target_size_result_view(
    path: str | os.PathLike[str],
    revision: TargetSizeCampaignRevision,
) -> dict[str, Any]:
    """Atomically write a derived view for selection/freeze changes without P3 validation."""
    destination = Path(path)
    existing_view: dict[str, Any] | None = None
    if destination.is_file():
        try:
            with open(destination, "r", encoding="utf-8") as stream:
                loaded = json.load(stream)
            if (
                isinstance(loaded, dict)
                and loaded.get("schema") == TARGET_SIZE_RESULT_VIEW_SCHEMA
            ):
                existing_view = loaded
        except Exception:
            existing_view = None

    payload = build_selection_target_size_result_view(
        revision, existing_view=existing_view
    )
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
    "build_selection_target_size_result_view",
    "build_target_size_result_view",
    "expose_current_target_size_auto_diagnostic",
    "write_current_target_size_result_view",
    "write_nonterminal_target_size_result_view",
    "write_selection_target_size_result_view",
    "write_target_size_result_view",
]
