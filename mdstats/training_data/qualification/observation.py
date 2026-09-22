"""Compact, non-mutating observation of post-production qualification state.

``qualification status`` promised to be observational and was not.  It built a
full :class:`QualificationSession`, which re-entered P4/P5 currentness, resolved
environment/resource/executable/physical-plan state, opened evidence roots, and
for a new physical request could run model predictions just to decide whether
stress was applicable.  Describing a qualification cost more than some of the
work it described, and could create the state it claimed to be reporting.

This module answers the same operator questions from durable evidence alone.
Two properties make that honest, and they are separate:

*Coherence.*  The pointer digests this projection interprets are not read here
at all.  They arrive from :func:`campaign_owner_snapshot`, the one read
transaction that already spans the target-size revision and every descendant
P5/P7 pointer row.  Reading each pointer in its own transaction would let one
status answer combine plan, component, locked and release facts from owner
graphs that never coexisted -- and publishing a P7 pointer moves no target-size
revision, so re-reading that revision would not detect it.

*Integrity.*  A pointer names a content digest, never a fact.  Every
content-addressed P7 object whose fields reach the operator -- plan, component
evidence, locked activation, release index, terminal record -- is loaded through
:class:`QualificationEvidenceStore`, which reproduces the named digest through
the object's own accepted deserializer before a field is read.  An operator acts
on this answer, especially on locked activation and terminal/release state, so
none of it may be believed out of bytes that merely parse.

Mutable attempt-local coordination state (the attempt state file and the
component position locators) is not content-addressed and is deliberately not
promoted to a CAS object.  It is still read through its existing strict owner:
malformed or misidentified position/attempt bytes degrade to an explicit
unreadable/blocked diagnostic instead of becoming semantic truth.

It creates no directory, opens no provider, and runs no numerical work.  What it
cannot know cheaply -- whether a component *would* re-execute against a newly
arrived reference bundle, for instance -- it does not claim; that judgement
belongs to `qualification run`, which is the owner that can make it honestly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .store import (
    ATTEMPT_STATE_FILENAME,
    POINTER_LOCKED_ACTIVATION,
    POINTER_QUALIFICATION_PLAN,
    POINTER_QUALIFICATION_RECORD,
    POINTER_RELEASE_EVIDENCE,
    qualification_root,
)

#: Reported when durable bytes exist for a component/attempt but no longer
#: authenticate.  It is a diagnostic, never a scientific state.
UNREADABLE_POSITION = "unreadable_position"
UNREADABLE_EVIDENCE = "unreadable_evidence"
UNREADABLE_ATTEMPT_STATE = "unreadable"
NOT_STARTED = "not_started"

#: Pointer-level states for the two P7 objects an operator acts on directly.
#: ``UNREADABLE`` is deliberately distinct from ``ABSENT``: reporting a tampered
#: locked activation as "not activated" would state a falsehood about
#: irreversible disclosure, which is precisely the fact this command exists to
#: report truthfully.
ABSENT = "absent"
PRESENT = "present"
UNREADABLE = "unreadable"


@dataclass(frozen=True, slots=True)
class QualificationObservation:
    """Everything durable qualification state says, and nothing more."""

    generation: int
    binding_digest: str
    #: The attempt this evidence belongs to, taken from the authenticated plan.
    #: ``None`` when no authentic plan names one -- an attempt identity that was
    #: guessed instead of read would name a directory the owner never used.
    attempt_identity: str | None
    attempt_state: str | None
    plan_digest: str | None
    planned_components: tuple[str, ...]
    component_states: tuple[tuple[str, str], ...]
    locked_activated_at: str | None
    locked_state: str
    verdict: str | None
    verdict_reason: str | None
    release_evidence_digest: str | None
    release_state: str
    blocked_detail: str | None = None
    #: Set when a terminal record exists on disk but no longer binds the
    #: currently configured qualification specification.  Its verdict is
    #: historical evidence, so ``verdict`` stays ``None``.
    superseded_detail: str | None = None

    @property
    def started(self) -> bool:
        return self.plan_digest is not None


def _authenticated(store: Any, content_digest: str, deserializer: Any) -> Any | None:
    """Load one compact P7 record through its owner, or report nothing.

    ``None`` means missing, unreadable, or not reproducing the digest the
    pointer named -- three different accidents with one consequence for an
    observer: the referenced fact cannot be believed, so it is reported as
    blocked rather than interpreted.
    """

    try:
        return store.get(content_digest, deserializer)
    except Exception:  # noqa: BLE001 - every failure is one blocked observation
        return None


def _unauthenticated(kind: str, content_digest: str) -> str:
    return (
        f"the current {kind} object {str(content_digest)[:12]}... is missing, "
        "unreadable, or does not reproduce its own identity"
    )


def _attempt_state(attempt_root: Path, blocked: list[str]) -> str | None:
    """The attempt's own state, through the single strict attempt authority."""

    from .store import authenticate_attempt_state

    authority = authenticate_attempt_state(attempt_root)
    if authority.state is not None:
        return str(authority.state.state)
    state_path = attempt_root / ATTEMPT_STATE_FILENAME
    if not (state_path.exists() or state_path.is_symlink()):
        return None
    blocked.append(
        "the qualification attempt state is present but not authoritative"
        + (f" ({authority.reason})" if authority.reason else "")
    )
    return UNREADABLE_ATTEMPT_STATE


def _component_states(
    store: Any,
    attempt_root: Path,
    qualification_binding_digest: str,
    planned: tuple[str, ...],
    blocked: list[str],
) -> tuple[tuple[str, str], ...]:
    from .components import QualificationComponentEvidence
    from .errors import QualificationLineageError
    from .runtime import read_component_position

    states: list[tuple[str, str]] = []
    for component in planned:
        try:
            position = read_component_position(attempt_root, component)
        except QualificationLineageError as exc:
            states.append((component, UNREADABLE_POSITION))
            blocked.append(f"component {component!r} position is unusable: {exc}")
            continue
        if position is None:
            states.append((component, NOT_STARTED))
            continue
        evidence_digest = position.get("evidence_digest")
        if evidence_digest is None:
            states.append((component, UNREADABLE_POSITION))
            blocked.append(
                f"component {component!r} position names no evidence object"
            )
            continue
        evidence = _authenticated(
            store, str(evidence_digest), QualificationComponentEvidence.from_dict
        )
        if evidence is None:
            states.append((component, UNREADABLE_EVIDENCE))
            blocked.append(
                f"component {component!r} names evidence "
                + _unauthenticated("component evidence", str(evidence_digest))
            )
            continue
        if (
            str(evidence.component) != str(component)
            or str(evidence.binding_digest) != qualification_binding_digest
        ):
            # Authentic bytes, wrong subject: an evidence object that belongs to
            # another component or another qualification identity is not this
            # component's state, however well it reproduces its own digest.
            states.append((component, UNREADABLE_EVIDENCE))
            blocked.append(
                f"component {component!r} names evidence that belongs to a "
                "different component or qualification identity"
            )
            continue
        states.append((component, str(evidence.status.value)))
    return tuple(states)


def terminal_currentness_failure(
    paths: Any,
    binding: Any,
    pointers: Mapping[str, str | None],
    record: Any,
    store: Any,
) -> str | None:
    """Why this terminal record is not current, or ``None`` when it is.

    One observational owner for the product/executable dependencies this cycle
    touches, shared by ``qualification status`` and the compact campaign
    lifecycle.  Two observers that interpreted a terminal record differently
    would eventually disagree in public about whether a campaign is released,
    and the cheaper one would be the wrong one.

    Everything it reads is either the *captured* snapshot mapping or an
    immutable object that mapping names.  It performs no session construction,
    no reference request, no locked activation, no provider or model
    reconstruction, and - decisively - it never reads or rebuilds attempt-local
    deployment scratch: released-attempt scratch may legitimately have been
    reclaimed, and its absence is not evidence corruption.
    """

    from ..post_selection_product_observation import (
        PRODUCT_STATE_COMPLETE,
        observe_current_product,
    )
    from .components import QualificationComponentEvidence
    from .identity import resolve_executable_candidate_identity
    from .record import DEPLOYMENT_REALIZATION_SET_NOT_APPLICABLE

    if getattr(record, "is_historical_v1", False):
        return (
            "the terminal qualification record predates the P5 model-publication "
            "and deployment-realization boundary; it remains readable historical "
            "evidence and is never the current release verdict"
        )
    observation = observe_current_product(paths, binding, pointers)
    if observation.state != PRODUCT_STATE_COMPLETE:
        return f"the current P5 product is not exposable: {observation.message}"
    if str(record.publication_digest) != str(observation.decision.content_digest):
        return "the terminal record binds a superseded final-production decision"
    if str(record.predecessor_reclosure_digest or "") != str(
        observation.reclosure.content_digest
    ):
        return "the terminal record binds a superseded P5/P6 predecessor reclosure"
    if str(record.model_artifact_set_digest or "") != str(
        observation.model_artifact_set_digest
    ):
        return (
            "the terminal record was reduced over a different serialized P5 model "
            "representation than the one current now"
        )
    try:
        current_executable = resolve_executable_candidate_identity().content_digest
    except Exception:  # noqa: BLE001 - unreadable source is a blocked observation
        return "the current qualification executable identity is unreadable"
    if str(record.executable_digest) != str(current_executable):
        return (
            "the terminal record was produced by a different qualification "
            "executable candidate than the one importable now"
        )
    # The stored realization-set identity must agree with the immutable
    # deployment-dependent component evidence it references.  Reading the
    # attempt's mutable receipt instead would make public currentness depend on
    # scratch that accepted retention policy may already have reclaimed.
    declared = str(record.deployment_realization_set_digest or "")
    observed: set[str] = set()
    for outcome in record.components:
        evidence = _authenticated(
            store, outcome.evidence_digest, QualificationComponentEvidence.from_dict
        )
        if evidence is None:
            return (
                "a component evidence object the terminal record references is "
                "missing, unreadable, or does not reproduce its own identity"
            )
        payload = evidence.payload if isinstance(evidence.payload, Mapping) else {}
        value = payload.get("deployment_realization_set_digest")
        if value is not None:
            observed.add(str(value))
    if len(observed) > 1:
        return (
            "the terminal record references deployment-dependent evidence bound to "
            f"different deployed realization sets {sorted(observed)}; that is an "
            "incomplete or internally inconsistent reduction, not a release"
        )
    expected = observed.pop() if observed else DEPLOYMENT_REALIZATION_SET_NOT_APPLICABLE
    if declared != expected:
        return (
            "the terminal record's deployed-realization identity disagrees with the "
            "component evidence it references"
        )
    return None


def release_currentness_failure(record: Any, index: Any) -> str | None:
    """Why this release index cannot expose ``record`` as released, if it cannot.

    A crash that published the terminal record but not its release index is
    recoverable incomplete exposure, not a complete release claim, so pointer
    presence alone never yields ``release_qualified``.
    """

    if index is None:
        return (
            "no release-evidence index authenticates the terminal record; the "
            "release exposure is incomplete and is repaired by rerunning "
            "qualification"
        )
    if getattr(index, "is_historical_v1", False):
        return (
            "the release-evidence index predates the P5 model-publication and "
            "deployment-realization boundary and is historical evidence only"
        )
    mismatches = {
        "qualification_record_digest": (
            str(index.qualification_record_digest),
            str(record.content_digest),
        ),
        "publication_member_digest": (
            str(index.publication_member_digest),
            str(record.publication_member_digest),
        ),
        "model_artifact_set_digest": (
            str(index.model_artifact_set_digest or ""),
            str(record.model_artifact_set_digest or ""),
        ),
        "deployment_realization_set_digest": (
            str(index.deployment_realization_set_digest or ""),
            str(record.deployment_realization_set_digest or ""),
        ),
        "locked_activation_digest": (
            str(index.locked_activation_digest or ""),
            str(record.locked_activation_digest or ""),
        ),
        "resource_scope_digest": (
            str(index.resource_scope_digest or ""),
            str(record.resource_scope_digest or ""),
        ),
        "verdict": (str(index.verdict.value), str(record.verdict.value)),
    }
    stale = sorted(name for name, (left, right) in mismatches.items() if left != right)
    if stale:
        return (
            f"the release-evidence index does not authenticate the terminal record ({stale})"
        )
    return None


def observe_current_qualification(
    paths: Any,
    binding: Any,
    pointers: Mapping[str, str | None],
    *,
    specification_digest: str | None = None,
) -> QualificationObservation:
    """Read the current qualification state for ``binding`` without touching it.

    ``pointers`` is the coherent pointer mapping produced by
    :func:`mdstats.training_data.campaign_lifecycle.campaign_owner_snapshot`
    for the same ``binding``; this function reads no pointer row of its own, so
    one status answer describes one owner ancestry.

    ``specification_digest`` is the currently configured qualification policy
    identity -- a pure configuration projection, so supplying it costs nothing.
    A published record that binds a different specification is historical
    evidence: `qualification run` would not accept it as current, and status
    must not report its verdict as if it were.
    """

    from .locked import LockedActivationRecord
    from .plan import ProductionQualificationPlan
    from .record import ProductionQualificationRecord, ReleaseEvidenceIndex
    from .store import QualificationEvidenceStore

    root = qualification_root(paths, binding.campaign_generation)
    # A pure path holder: naming a root never brings one into existence, so
    # "no evidence was ever published" stays distinguishable afterwards.
    store = QualificationEvidenceStore(root=root)
    prefix = f"qualification:{binding.content_digest}:"
    plan_digest = pointers.get(prefix + POINTER_QUALIFICATION_PLAN)
    record_digest = pointers.get(prefix + POINTER_QUALIFICATION_RECORD)
    locked_digest = pointers.get(prefix + POINTER_LOCKED_ACTIVATION)
    release_digest = pointers.get(prefix + POINTER_RELEASE_EVIDENCE)

    blocked: list[str] = []
    planned: tuple[str, ...] = ()
    # The attempt identity, the qualification input binding, and the planned
    # component list all come from the one authenticated plan.  Re-deriving the
    # attempt identity from the selected binding would name a different
    # directory than the owner ever wrote to, and every component would then
    # look permanently unstarted.
    attempt_identity: str | None = None
    qualification_binding_digest: str | None = None
    if plan_digest is not None:
        plan = _authenticated(
            store, plan_digest, ProductionQualificationPlan.from_dict
        )
        if plan is None:
            blocked.append(_unauthenticated("qualification plan", plan_digest))
        elif str(plan.selected_binding_digest) != str(binding.content_digest):
            blocked.append(
                "the current qualification plan belongs to a different selected "
                "binding"
            )
        else:
            planned = tuple(str(value) for value in plan.planned_components)
            attempt_identity = str(plan.attempt_identity)
            qualification_binding_digest = str(plan.binding.content_digest)

    attempt_state = None
    component_states: tuple[tuple[str, str], ...] = ()
    if attempt_identity is not None:
        attempt_root = root / "attempts" / attempt_identity
        attempt_state = _attempt_state(attempt_root, blocked)
        component_states = _component_states(
            store,
            attempt_root,
            str(qualification_binding_digest),
            planned,
            blocked,
        )

    locked_at = None
    locked_state = ABSENT
    if locked_digest is not None:
        locked_state = UNREADABLE
        activation = _authenticated(
            store, locked_digest, LockedActivationRecord.from_dict
        )
        if activation is None:
            blocked.append(_unauthenticated("locked activation", locked_digest))
        elif str(activation.selected_binding_digest) != str(
            binding.content_digest
        ) or (
            qualification_binding_digest is not None
            and str(activation.binding_digest) != qualification_binding_digest
        ):
            blocked.append(
                "the current locked activation belongs to a different "
                "qualification identity"
            )
        else:
            locked_at = str(activation.activated_at) or "unknown time"
            locked_state = PRESENT

    release_evidence_digest = None
    release_state = ABSENT
    if release_digest is not None:
        release_state = UNREADABLE
        index = _authenticated(store, release_digest, ReleaseEvidenceIndex.from_dict)
        if index is None:
            blocked.append(_unauthenticated("release evidence index", release_digest))
        elif str(index.selected_binding_digest) != str(binding.content_digest):
            blocked.append(
                "the current release evidence index belongs to a different "
                "selected binding"
            )
        else:
            release_evidence_digest = str(release_digest)
            release_state = PRESENT

    verdict = None
    verdict_reason = None
    superseded = None
    if record_digest is not None:
        record = _authenticated(
            store, record_digest, ProductionQualificationRecord.from_dict
        )
        if record is None:
            blocked.append(
                _unauthenticated("terminal qualification record", record_digest)
            )
        elif str(record.selected_binding_digest) != str(binding.content_digest):
            blocked.append(
                "the current terminal qualification record belongs to a "
                "different selected binding"
            )
        elif (
            specification_digest is not None
            and str(record.specification_digest) != str(specification_digest)
        ):
            superseded = (
                "the published terminal record binds qualification specification "
                f"{str(record.specification_digest)[:12]}..., but "
                f"{str(specification_digest)[:12]}... is configured now"
            )
        else:
            stale = terminal_currentness_failure(
                paths, binding, pointers, record, store
            )
            if stale is not None:
                superseded = stale
            else:
                release_index = (
                    None
                    if release_evidence_digest is None
                    else _authenticated(
                        store, release_evidence_digest, ReleaseEvidenceIndex.from_dict
                    )
                )
                release_failure = release_currentness_failure(record, release_index)
                if release_failure is not None and str(
                    record.verdict.value
                ) == "release_qualified":
                    # A release claim needs its matching authenticated index;
                    # a terminal-record pointer alone never states one.
                    superseded = release_failure
                else:
                    verdict = str(record.verdict.value) or None
                    verdict_reason = str(record.reason_code) or None

    from ..campaign_lifecycle import (
        REPLAY_CURRENT_LINEAGE_OBSERVATION,
        REPLAY_CURRENT_LINEAGE_STATUS_OBSERVATION,
        _single_source_replay_applicable,
    )

    if _single_source_replay_applicable(paths):
        current_lineage = pointers.get(REPLAY_CURRENT_LINEAGE_OBSERVATION)
        current_status = pointers.get(REPLAY_CURRENT_LINEAGE_STATUS_OBSERVATION)
        if current_status in {"missing", "malformed"} or current_lineage is None:
            superseded = (
                "single-source replay current lineage is missing or malformed; rerun `prepare`"
            )
            verdict = None
            verdict_reason = None

    return QualificationObservation(
        generation=int(binding.campaign_generation),
        binding_digest=str(binding.content_digest),
        attempt_identity=attempt_identity,
        attempt_state=attempt_state,
        plan_digest=plan_digest,
        planned_components=planned,
        component_states=component_states,
        locked_activated_at=locked_at,
        locked_state=locked_state,
        verdict=verdict,
        verdict_reason=verdict_reason,
        release_evidence_digest=release_evidence_digest,
        release_state=release_state,
        blocked_detail="; ".join(blocked) if blocked else None,
        superseded_detail=superseded,
    )


__all__ = [
    "QualificationObservation",
    "observe_current_qualification",
    "release_currentness_failure",
    "terminal_currentness_failure",
]
