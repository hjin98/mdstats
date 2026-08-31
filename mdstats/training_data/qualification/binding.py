"""The P7 descendant binding: exactly what a qualification attempt is about.

The accepted predecessor publication carries scientific product identity and
nothing else - it predates P7 and must not be widened with qualification-only
concerns.  ``QualificationInputBinding`` is therefore a strict *descendant*: it
names the immutable publication it descends from and adds the executable,
environment, specification, and evidence-role identities that make a
qualification claim meaningful.  It has no publication-membership or selection
authority; it can only ever point at a member set that already exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .identity import (
    EnvironmentFingerprint,
    ExecutableCandidateIdentity,
    QualificationSpecIdentity,
)

QUALIFICATION_INPUT_BINDING_SCHEMA = "mdstats.qualification-input-binding.v1"
EVIDENCE_ROLE_MEMBERSHIP_SCHEMA = "mdstats.qualification-evidence-role-membership.v1"


@dataclass(frozen=True, slots=True)
class EvidenceRoleMembership:
    """The exact frozen neutral evidence-role cohorts qualification may use."""

    outer_monitor_unit_ids: tuple[str, ...]
    outer_monitor_frame_uids: tuple[str, ...]
    calibration_unit_ids: tuple[str, ...]
    calibration_frame_uids: tuple[str, ...]
    locked_unit_ids: tuple[str, ...]
    locked_frame_uids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "outer_monitor_unit_ids",
            "outer_monitor_frame_uids",
            "calibration_unit_ids",
            "calibration_frame_uids",
            "locked_unit_ids",
            "locked_frame_uids",
        ):
            values = tuple(str(v) for v in getattr(self, name))
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} contains duplicates.")
            object.__setattr__(self, name, values)
        overlaps = (
            set(self.outer_monitor_frame_uids) & set(self.calibration_frame_uids),
            set(self.outer_monitor_frame_uids) & set(self.locked_frame_uids),
            set(self.calibration_frame_uids) & set(self.locked_frame_uids),
        )
        if any(overlaps):
            raise TrainingDataInputError(
                "Neutral evidence roles must remain disjoint; qualification never "
                "synthesizes an independent role from another role's frames."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVIDENCE_ROLE_MEMBERSHIP_SCHEMA,
            "outer_monitor_unit_ids": list(self.outer_monitor_unit_ids),
            "outer_monitor_frame_uids": list(self.outer_monitor_frame_uids),
            "calibration_unit_ids": list(self.calibration_unit_ids),
            "calibration_frame_uids": list(self.calibration_frame_uids),
            "locked_unit_ids": list(self.locked_unit_ids),
            "locked_frame_uids": list(self.locked_frame_uids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def outer_monitor_digest(self) -> str:
        return digest({"outer_monitor_frame_uids": list(self.outer_monitor_frame_uids)})

    @property
    def calibration_digest(self) -> str:
        return digest({"calibration_frame_uids": list(self.calibration_frame_uids)})

    @property
    def locked_digest(self) -> str:
        return digest({"locked_frame_uids": list(self.locked_frame_uids)})

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceRoleMembership":
        if payload.get("schema") != EVIDENCE_ROLE_MEMBERSHIP_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification evidence-role-membership schema."
            )
        result = cls(
            outer_monitor_unit_ids=tuple(payload["outer_monitor_unit_ids"]),
            outer_monitor_frame_uids=tuple(payload["outer_monitor_frame_uids"]),
            calibration_unit_ids=tuple(payload["calibration_unit_ids"]),
            calibration_frame_uids=tuple(payload["calibration_frame_uids"]),
            locked_unit_ids=tuple(payload["locked_unit_ids"]),
            locked_frame_uids=tuple(payload["locked_frame_uids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification evidence-role-membership digest mismatch."
            )
        return result


def resolve_evidence_role_membership(context: Any) -> EvidenceRoleMembership:
    """Project the accepted P1 neutral roles; qualification never re-partitions."""

    from ..partition import OuterRole

    base = context.selected.authorities.neutral_base
    units = {unit.unit_id: unit for unit in base.unit_catalog.units}

    def cohort(role: OuterRole) -> tuple[tuple[str, ...], tuple[str, ...]]:
        unit_ids = tuple(sorted(base.outer_partition.unit_ids_for_role(role)))
        frames: list[str] = []
        for unit_id in unit_ids:
            frames.extend(units[unit_id].frame_uids)
        return unit_ids, tuple(frames)

    outer_units, outer_frames = cohort(OuterRole.OUTER_MONITOR)
    calibration_units, calibration_frames = cohort(OuterRole.UNCERTAINTY_CALIBRATION)
    locked_units, locked_frames = cohort(OuterRole.LOCKED_INTERPOLATION_TEST)
    return EvidenceRoleMembership(
        outer_monitor_unit_ids=outer_units,
        outer_monitor_frame_uids=outer_frames,
        calibration_unit_ids=calibration_units,
        calibration_frame_uids=calibration_frames,
        locked_unit_ids=locked_units,
        locked_frame_uids=locked_frames,
    )


@dataclass(frozen=True, slots=True)
class QualificationInputBinding:
    """One immutable descendant identity for a qualification attempt."""

    selected_binding_digest: str
    publication_digest: str
    publication_member_digest: str
    executable: ExecutableCandidateIdentity
    environment: EnvironmentFingerprint
    specification: QualificationSpecIdentity
    evidence_roles: EvidenceRoleMembership

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "publication_digest",
            "publication_member_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name, expected in (
            ("executable", ExecutableCandidateIdentity),
            ("environment", EnvironmentFingerprint),
            ("specification", QualificationSpecIdentity),
            ("evidence_roles", EvidenceRoleMembership),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TrainingDataInputError(
                    f"A qualification input binding requires a real {expected.__name__}."
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": QUALIFICATION_INPUT_BINDING_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "publication_digest": self.publication_digest,
            "publication_member_digest": self.publication_member_digest,
            "executable_digest": self.executable.content_digest,
            "environment_digest": self.environment.content_digest,
            "specification_digest": self.specification.content_digest,
            "evidence_role_digest": self.evidence_roles.content_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def attempt_identity(self) -> str:
        """Immutable attempt key: never a directory name or process lifetime."""

        return digest(
            {"schema": "mdstats.qualification-attempt-identity.v1", "binding": self.content_digest}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "executable": self.executable.to_dict(),
            "environment": self.environment.to_dict(),
            "specification": self.specification.to_dict(),
            "evidence_roles": self.evidence_roles.to_dict(),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualificationInputBinding":
        if payload.get("schema") != QUALIFICATION_INPUT_BINDING_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification input-binding schema."
            )
        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            executable=ExecutableCandidateIdentity.from_dict(payload["executable"]),
            environment=EnvironmentFingerprint.from_dict(payload["environment"]),
            specification=QualificationSpecIdentity.from_dict(payload["specification"]),
            evidence_roles=EvidenceRoleMembership.from_dict(payload["evidence_roles"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification input-binding digest mismatch."
            )
        return result


__all__ = [
    "EVIDENCE_ROLE_MEMBERSHIP_SCHEMA",
    "QUALIFICATION_INPUT_BINDING_SCHEMA",
    "EvidenceRoleMembership",
    "QualificationInputBinding",
    "resolve_evidence_role_membership",
]
