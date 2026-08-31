"""The single terminal qualification record and the release-evidence index.

There is exactly one owner of "is this product qualified?".  Component evidence
stays separately typed because the mathematics differ, but a consumer - a
release process, or the successor storage subsystem - never has to reconcile six
independent state machines: it reads one record, and that record points at, but
never duplicates, everything it depends on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .components import (
    COMPONENT_LOCKED_TEST,
    ComponentStatus,
    QualificationComponentEvidence,
)

QUALIFICATION_RECORD_SCHEMA = "mdstats.qualification-record.v1"
RELEASE_EVIDENCE_SCHEMA = "mdstats.qualification-release-evidence.v1"


class QualificationVerdict(str, Enum):
    INCOMPLETE = "incomplete"
    WAITING_FOR_REFERENCE = "waiting_for_reference"
    REJECTED = "rejected"
    RELEASE_QUALIFIED = "release_qualified"

    @property
    def is_terminal(self) -> bool:
        return self in (QualificationVerdict.REJECTED, QualificationVerdict.RELEASE_QUALIFIED)


@dataclass(frozen=True, slots=True)
class ComponentOutcome:
    component: str
    status: ComponentStatus
    reason_code: str
    evidence_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "component", str(self.component))
        object.__setattr__(self, "status", ComponentStatus(self.status))
        object.__setattr__(self, "reason_code", str(self.reason_code))
        object.__setattr__(
            self, "evidence_digest", validate_digest(self.evidence_digest, name="evidence_digest")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "evidence_digest": self.evidence_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ComponentOutcome":
        return cls(
            component=str(payload["component"]),
            status=ComponentStatus(payload["status"]),
            reason_code=str(payload["reason_code"]),
            evidence_digest=str(payload["evidence_digest"]),
        )

    @classmethod
    def of(cls, evidence: QualificationComponentEvidence) -> "ComponentOutcome":
        return cls(
            component=evidence.component,
            status=evidence.status,
            reason_code=evidence.reason_code,
            evidence_digest=evidence.content_digest,
        )


@dataclass(frozen=True, slots=True)
class ProductionQualificationRecord:
    """Immutable release evidence for one exact product/candidate/environment."""

    selected_binding_digest: str
    binding_digest: str
    publication_digest: str
    publication_member_digest: str
    plan_digest: str
    specification_digest: str
    environment_digest: str
    executable_digest: str
    predecessor_executable_commit: str
    predecessor_evidence_commit: str
    components: tuple[ComponentOutcome, ...]
    locked_activation_digest: str | None
    verdict: QualificationVerdict
    reason_code: str
    recorded_at: str
    resource_scope_digest: str | None = None
    predecessor_reclosure_digest: str | None = None
    predecessor_executable_tree_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "binding_digest",
            "publication_digest",
            "publication_member_digest",
            "plan_digest",
            "specification_digest",
            "environment_digest",
            "executable_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.locked_activation_digest is not None:
            object.__setattr__(
                self,
                "locked_activation_digest",
                validate_digest(self.locked_activation_digest, name="locked_activation_digest"),
            )
        components = tuple(sorted(self.components, key=lambda item: item.component))
        names = [item.component for item in components]
        if len(set(names)) != len(names):
            raise TrainingDataInputError("A qualification record holds one outcome per component.")
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "verdict", QualificationVerdict(self.verdict))
        for name in ("predecessor_executable_commit", "predecessor_evidence_commit", "reason_code"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"A qualification record requires {name}.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "recorded_at", str(self.recorded_at))
        if self.resource_scope_digest is not None:
            object.__setattr__(
                self,
                "resource_scope_digest",
                validate_digest(self.resource_scope_digest, name="resource_scope_digest"),
            )
        for name in (
            "predecessor_reclosure_digest",
            "predecessor_executable_tree_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))

    def outcome(self, component: str) -> ComponentOutcome | None:
        for item in self.components:
            if item.component == str(component):
                return item
        return None

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": QUALIFICATION_RECORD_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "binding_digest": self.binding_digest,
            "publication_digest": self.publication_digest,
            "publication_member_digest": self.publication_member_digest,
            "plan_digest": self.plan_digest,
            "specification_digest": self.specification_digest,
            "environment_digest": self.environment_digest,
            "executable_digest": self.executable_digest,
            "predecessor_executable_commit": self.predecessor_executable_commit,
            "predecessor_evidence_commit": self.predecessor_evidence_commit,
            "components": [item.to_dict() for item in self.components],
            "locked_activation_digest": self.locked_activation_digest,
            "verdict": self.verdict.value,
            "reason_code": self.reason_code,
            "recorded_at": self.recorded_at,
            "resource_scope_digest": self.resource_scope_digest,
        }
        if self.predecessor_reclosure_digest is not None:
            payload["predecessor_reclosure_digest"] = self.predecessor_reclosure_digest
        if self.predecessor_executable_tree_digest is not None:
            payload["predecessor_executable_tree_digest"] = self.predecessor_executable_tree_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionQualificationRecord":
        if payload.get("schema") != QUALIFICATION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported qualification-record schema.")
        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            binding_digest=str(payload["binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            plan_digest=str(payload["plan_digest"]),
            specification_digest=str(payload["specification_digest"]),
            environment_digest=str(payload["environment_digest"]),
            executable_digest=str(payload["executable_digest"]),
            predecessor_executable_commit=str(payload["predecessor_executable_commit"]),
            predecessor_evidence_commit=str(payload["predecessor_evidence_commit"]),
            components=tuple(ComponentOutcome.from_dict(item) for item in payload["components"]),
            locked_activation_digest=payload.get("locked_activation_digest"),
            verdict=QualificationVerdict(payload["verdict"]),
            reason_code=str(payload["reason_code"]),
            recorded_at=str(payload["recorded_at"]),
            resource_scope_digest=(
                None
                if payload.get("resource_scope_digest") is None
                else str(payload["resource_scope_digest"])
            ),
            predecessor_reclosure_digest=(
                None
                if payload.get("predecessor_reclosure_digest") is None
                else str(payload["predecessor_reclosure_digest"])
            ),
            predecessor_executable_tree_digest=(
                None
                if payload.get("predecessor_executable_tree_digest") is None
                else str(payload["predecessor_executable_tree_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Qualification-record digest mismatch.")
        return result


def derive_verdict(
    *,
    specification: Any,
    components: Sequence[ComponentOutcome],
    locked_required: bool,
) -> tuple[QualificationVerdict, str]:
    """One place decides the release verdict, from typed component outcomes."""

    by_name = {item.component: item for item in components}
    required = list(specification.required_components)
    if locked_required:
        required.append(COMPONENT_LOCKED_TEST)
    for name in required:
        outcome = by_name.get(name)
        if outcome is not None and outcome.status is ComponentStatus.REJECTED:
            return QualificationVerdict.REJECTED, f"required_component_rejected:{name}"
    for name in required:
        outcome = by_name.get(name)
        if outcome is not None and outcome.status is ComponentStatus.WAITING_FOR_REFERENCE:
            return (
                QualificationVerdict.WAITING_FOR_REFERENCE,
                f"required_component_waiting_for_reference:{name}",
            )
    for name in required:
        outcome = by_name.get(name)
        if outcome is None:
            return QualificationVerdict.INCOMPLETE, f"required_component_missing:{name}"
        if not outcome.status.is_terminal_success:
            return QualificationVerdict.INCOMPLETE, f"required_component_incomplete:{name}"
    return QualificationVerdict.RELEASE_QUALIFIED, "all_required_components_satisfied"


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceIndex:
    """One immutable index that points at, and never duplicates, the evidence."""

    qualification_record_digest: str
    selected_binding_digest: str
    publication_digest: str
    publication_member_digest: str
    executable_digest: str
    specification_digest: str
    environment_digest: str
    plan_digest: str
    component_evidence_digests: tuple[str, ...]
    locked_activation_digest: str | None
    verdict: QualificationVerdict
    published_at: str
    resource_scope_digest: str | None = None
    predecessor_reclosure_digest: str | None = None
    predecessor_executable_tree_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "qualification_record_digest",
            "selected_binding_digest",
            "publication_digest",
            "publication_member_digest",
            "executable_digest",
            "specification_digest",
            "environment_digest",
            "plan_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.locked_activation_digest is not None:
            object.__setattr__(
                self,
                "locked_activation_digest",
                validate_digest(self.locked_activation_digest, name="locked_activation_digest"),
            )
        object.__setattr__(
            self,
            "component_evidence_digests",
            tuple(
                validate_digest(str(v), name="component_evidence_digest")
                for v in sorted(self.component_evidence_digests)
            ),
        )
        object.__setattr__(self, "verdict", QualificationVerdict(self.verdict))
        object.__setattr__(self, "published_at", str(self.published_at))
        if self.resource_scope_digest is not None:
            object.__setattr__(
                self,
                "resource_scope_digest",
                validate_digest(self.resource_scope_digest, name="resource_scope_digest"),
            )
        for name in (
            "predecessor_reclosure_digest",
            "predecessor_executable_tree_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": RELEASE_EVIDENCE_SCHEMA,
            "qualification_record_digest": self.qualification_record_digest,
            "selected_binding_digest": self.selected_binding_digest,
            "publication_digest": self.publication_digest,
            "publication_member_digest": self.publication_member_digest,
            "executable_digest": self.executable_digest,
            "specification_digest": self.specification_digest,
            "environment_digest": self.environment_digest,
            "plan_digest": self.plan_digest,
            "component_evidence_digests": list(self.component_evidence_digests),
            "locked_activation_digest": self.locked_activation_digest,
            "verdict": self.verdict.value,
            "published_at": self.published_at,
            "resource_scope_digest": self.resource_scope_digest,
        }
        if self.predecessor_reclosure_digest is not None:
            payload["predecessor_reclosure_digest"] = self.predecessor_reclosure_digest
        if self.predecessor_executable_tree_digest is not None:
            payload["predecessor_executable_tree_digest"] = self.predecessor_executable_tree_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReleaseEvidenceIndex":
        if payload.get("schema") != RELEASE_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported release-evidence schema.")
        result = cls(
            qualification_record_digest=str(payload["qualification_record_digest"]),
            selected_binding_digest=str(payload["selected_binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            executable_digest=str(payload["executable_digest"]),
            specification_digest=str(payload["specification_digest"]),
            environment_digest=str(payload["environment_digest"]),
            plan_digest=str(payload["plan_digest"]),
            component_evidence_digests=tuple(payload["component_evidence_digests"]),
            locked_activation_digest=payload.get("locked_activation_digest"),
            verdict=QualificationVerdict(payload["verdict"]),
            published_at=str(payload["published_at"]),
            resource_scope_digest=(
                None
                if payload.get("resource_scope_digest") is None
                else str(payload["resource_scope_digest"])
            ),
            predecessor_reclosure_digest=(
                None
                if payload.get("predecessor_reclosure_digest") is None
                else str(payload["predecessor_reclosure_digest"])
            ),
            predecessor_executable_tree_digest=(
                None
                if payload.get("predecessor_executable_tree_digest") is None
                else str(payload["predecessor_executable_tree_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Release-evidence digest mismatch.")
        return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "QUALIFICATION_RECORD_SCHEMA",
    "RELEASE_EVIDENCE_SCHEMA",
    "ComponentOutcome",
    "ProductionQualificationRecord",
    "QualificationVerdict",
    "ReleaseEvidenceIndex",
    "derive_verdict",
    "utc_now",
]
