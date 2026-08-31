"""One immutable typed component-evidence record for every qualification claim.

Deployment parity, local PES, relaxation, dynamics, calibration, and the locked
test are mathematically very different, but they are not six lifecycles.  They
all answer the same question about the same frozen product under the same frozen
specification, so they share one immutable evidence shape and one status
vocabulary.  A future storage or release consumer therefore has exactly one
record type to understand, and no component can invent a private notion of
"complete".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)

COMPONENT_EVIDENCE_SCHEMA = "mdstats.qualification-component-evidence.v1"

COMPONENT_DEPLOYMENT_PARITY = "deployment_parity"
COMPONENT_PHYSICAL_PES = "physical_pes"
COMPONENT_RELAXATION = "relaxation"
COMPONENT_DYNAMICS = "dynamics"
COMPONENT_CALIBRATION = "calibration"
COMPONENT_LOCKED_TEST = "locked_interpolation_test"

#: Every component the qualification owner knows how to produce.  Nonlocked
#: components are the ones ``qualification run`` may execute; the locked test is
#: reachable only through explicit activation.
NONLOCKED_COMPONENTS = (
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    COMPONENT_DYNAMICS,
    COMPONENT_CALIBRATION,
)
ALL_COMPONENTS = NONLOCKED_COMPONENTS + (COMPONENT_LOCKED_TEST,)


class ComponentStatus(str, Enum):
    """Typed outcomes.  There is deliberately no ``degraded`` or ``retry``."""

    PASSED = "passed"
    REJECTED = "rejected"
    WAITING_FOR_REFERENCE = "waiting_for_reference"
    NOT_APPLICABLE = "not_applicable"

    @property
    def is_terminal_success(self) -> bool:
        return self in (ComponentStatus.PASSED, ComponentStatus.NOT_APPLICABLE)


@dataclass(frozen=True, slots=True)
class QualificationComponentEvidence:
    """Immutable evidence for one component of one exact qualification attempt."""

    component: str
    binding_digest: str
    publication_digest: str
    publication_member_digest: str
    specification_digest: str
    environment_digest: str
    executable_digest: str
    status: ComponentStatus
    reason_code: str
    detail: str
    metrics: Mapping[str, Any]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        component = str(self.component)
        if component not in ALL_COMPONENTS:
            raise TrainingDataInputError(f"Unknown qualification component {component!r}.")
        object.__setattr__(self, "component", component)
        for name in (
            "binding_digest",
            "publication_digest",
            "publication_member_digest",
            "specification_digest",
            "environment_digest",
            "executable_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "status", ComponentStatus(self.status))
        reason = str(self.reason_code).strip()
        if not reason:
            raise TrainingDataInputError(
                "Component evidence requires a typed reason code, including on pass."
            )
        object.__setattr__(self, "reason_code", reason)
        object.__setattr__(self, "detail", str(self.detail))
        object.__setattr__(self, "metrics", json_value(dict(self.metrics)))
        object.__setattr__(self, "payload", json_value(dict(self.payload)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMPONENT_EVIDENCE_SCHEMA,
            "component": self.component,
            "binding_digest": self.binding_digest,
            "publication_digest": self.publication_digest,
            "publication_member_digest": self.publication_member_digest,
            "specification_digest": self.specification_digest,
            "environment_digest": self.environment_digest,
            "executable_digest": self.executable_digest,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "metrics": dict(self.metrics),
            "payload": dict(self.payload),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualificationComponentEvidence":
        if payload.get("schema") != COMPONENT_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification component-evidence schema."
            )
        result = cls(
            component=str(payload["component"]),
            binding_digest=str(payload["binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            specification_digest=str(payload["specification_digest"]),
            environment_digest=str(payload["environment_digest"]),
            executable_digest=str(payload["executable_digest"]),
            status=ComponentStatus(payload["status"]),
            reason_code=str(payload["reason_code"]),
            detail=str(payload.get("detail", "")),
            metrics=dict(payload.get("metrics", {})),
            payload=dict(payload.get("payload", {})),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification component-evidence digest mismatch."
            )
        return result


def build_component_evidence(
    *,
    component: str,
    binding: Any,
    status: ComponentStatus,
    reason_code: str,
    detail: str = "",
    metrics: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
) -> QualificationComponentEvidence:
    """Bind one component result to the exact attempt identity that produced it."""

    return QualificationComponentEvidence(
        component=component,
        binding_digest=binding.content_digest,
        publication_digest=binding.publication_digest,
        publication_member_digest=binding.publication_member_digest,
        specification_digest=binding.specification.content_digest,
        environment_digest=binding.environment.content_digest,
        executable_digest=binding.executable.content_digest,
        status=status,
        reason_code=reason_code,
        detail=detail,
        metrics=dict(metrics or {}),
        payload=dict(payload or {}),
    )


__all__ = [
    "ALL_COMPONENTS",
    "COMPONENT_CALIBRATION",
    "COMPONENT_DEPLOYMENT_PARITY",
    "COMPONENT_DYNAMICS",
    "COMPONENT_EVIDENCE_SCHEMA",
    "COMPONENT_LOCKED_TEST",
    "COMPONENT_PHYSICAL_PES",
    "COMPONENT_RELAXATION",
    "NONLOCKED_COMPONENTS",
    "ComponentStatus",
    "QualificationComponentEvidence",
    "build_component_evidence",
]
