"""Compact, non-mutating observation of post-production qualification state.

``qualification status`` promised to be observational and was not.  It built a
full :class:`QualificationSession`, which re-entered P4/P5 currentness, resolved
environment/resource/executable/physical-plan state, opened evidence roots, and
for a new physical request could run model predictions just to decide whether
stress was applicable.  Describing a qualification cost more than some of the
work it described, and could create the state it claimed to be reporting.

This module answers the same operator questions from durable evidence alone:
the campaign store's pointer rows, the small immutable records they name, and
the attempt's own component position files.  It creates no directory, opens no
provider, and runs no numerical work.  What it cannot know cheaply -- whether a
component *would* re-execute against a newly arrived reference bundle, for
instance -- it does not claim; that judgement belongs to `qualification run`,
which is the owner that can make it honestly.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .store import (
    ATTEMPT_STATE_FILENAME,
    POINTER_LOCKED_ACTIVATION,
    POINTER_QUALIFICATION_PLAN,
    POINTER_QUALIFICATION_RECORD,
    POINTER_RELEASE_EVIDENCE,
    _expected_attempt_identity,
    qualification_root,
)


@dataclass(frozen=True, slots=True)
class QualificationObservation:
    """Everything durable qualification state says, and nothing more."""

    generation: int
    binding_digest: str
    attempt_identity: str
    attempt_state: str | None
    plan_digest: str | None
    planned_components: tuple[str, ...]
    component_states: tuple[tuple[str, str], ...]
    locked_activated_at: str | None
    verdict: str | None
    verdict_reason: str | None
    release_evidence_digest: str | None
    blocked_detail: str | None = None

    @property
    def started(self) -> bool:
        return self.plan_digest is not None


def _meta(store: Any, key: str) -> str | None:
    with store._connect() as db:  # noqa: SLF001 - the store owns its pool
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def _read_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _object(root: Path, content_digest: str) -> Mapping[str, Any] | None:
    return _read_json(root / "objects" / content_digest[:2] / f"{content_digest}.json")


def observe_current_qualification(
    paths: Any, store: Any, binding: Any
) -> QualificationObservation:
    """Read the current qualification state for ``binding`` without touching it."""

    from .runtime import COMPONENT_POSITION_DIRECTORY

    root = qualification_root(paths, binding.campaign_generation)
    prefix = f"qualification:{binding.content_digest}:"
    plan_digest = _meta(store, prefix + POINTER_QUALIFICATION_PLAN)
    record_digest = _meta(store, prefix + POINTER_QUALIFICATION_RECORD)
    locked_digest = _meta(store, prefix + POINTER_LOCKED_ACTIVATION)
    release_digest = _meta(store, prefix + POINTER_RELEASE_EVIDENCE)

    attempt_identity = _expected_attempt_identity(binding.content_digest)
    attempt_root = root / "attempts" / attempt_identity
    attempt_payload = _read_json(attempt_root / ATTEMPT_STATE_FILENAME)
    attempt_state = (
        None if attempt_payload is None else str(attempt_payload.get("state"))
    )

    blocked: list[str] = []
    planned: tuple[str, ...] = ()
    if plan_digest is not None:
        plan_payload = _object(root, plan_digest)
        if plan_payload is None:
            blocked.append(
                f"the current qualification plan object {plan_digest[:12]}... is "
                "missing or unreadable"
            )
        else:
            planned = tuple(
                str(value) for value in plan_payload.get("planned_components", ())
            )

    component_states: list[tuple[str, str]] = []
    positions = attempt_root / COMPONENT_POSITION_DIRECTORY
    for component in planned:
        position = _read_json(positions / f"{component}.json")
        if position is None:
            component_states.append((component, "not_started"))
            continue
        evidence_digest = position.get("evidence_digest")
        if position.get("position_object"):
            relative = Path(str(position["position_object"]))
            resolved = _read_json(attempt_root / relative)
            if resolved is not None:
                evidence_digest = resolved.get("evidence_digest")
        if evidence_digest is None:
            component_states.append((component, "unreadable_position"))
            continue
        evidence = _object(root, str(evidence_digest))
        if evidence is None:
            component_states.append((component, "missing_evidence"))
            blocked.append(
                f"component {component!r} names evidence "
                f"{str(evidence_digest)[:12]}... that is not present"
            )
            continue
        component_states.append((component, str(evidence.get("status", "unknown"))))

    locked_at = None
    if locked_digest is not None:
        activation = _object(root, locked_digest)
        if activation is None:
            blocked.append(
                f"the locked activation object {locked_digest[:12]}... is missing"
            )
        else:
            locked_at = str(activation.get("activated_at", "")) or "unknown time"

    verdict = None
    verdict_reason = None
    if record_digest is not None:
        record = _object(root, record_digest)
        if record is None:
            blocked.append(
                f"the terminal qualification record {record_digest[:12]}... is missing"
            )
        else:
            verdict = str(record.get("verdict", "")) or None
            verdict_reason = str(record.get("reason_code", "")) or None

    return QualificationObservation(
        generation=int(binding.campaign_generation),
        binding_digest=str(binding.content_digest),
        attempt_identity=attempt_identity,
        attempt_state=attempt_state,
        plan_digest=plan_digest,
        planned_components=planned,
        component_states=tuple(component_states),
        locked_activated_at=locked_at,
        verdict=verdict,
        verdict_reason=verdict_reason,
        release_evidence_digest=release_digest,
        blocked_detail="; ".join(blocked) if blocked else None,
    )


__all__ = ["QualificationObservation", "observe_current_qualification"]
