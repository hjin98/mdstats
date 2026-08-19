"""Blinding boundaries for outer MLFF evidence roles."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .partition import OuterPartition, OuterRole

BLINDING_POLICY_SCHEMA = "mdstats.mlff-blinding-policy.v1"
BLINDING_POLICY_VERSION = "mdstats.mlff-data5.blinding.2026-07.v1"
ROLE_BLINDING_BOUNDARY_SCHEMA = "mdstats.role-blinding-boundary.v1"
BLINDING_BOUNDARY_CATALOG_SCHEMA = "mdstats.blinding-boundary-catalog.v1"


class EvidenceOperation(str, Enum):
    RAW_GEOMETRY_ACCESS = "raw_geometry_access"
    LABEL_DERIVED_SELECTION = "label_derived_selection"
    CHECKPOINT_MONITORING = "checkpoint_monitoring"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"
    POST_FREEZE_EVALUATION = "post_freeze_evaluation"


class EvidenceAccess(str, Enum):
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    SEALED_UNTIL_PROTOCOL_FREEZE = "sealed_until_protocol_freeze"
    PROVENANCE_ONLY = "provenance_only"


@dataclass(frozen=True, slots=True)
class BlindingPolicy:
    policy_version: str = BLINDING_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": BLINDING_POLICY_SCHEMA, "policy_version": self.policy_version}

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BlindingPolicy":
        if payload.get("schema") != BLINDING_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported blinding-policy schema.")
        result = cls(policy_version=str(payload["policy_version"]))
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Blinding-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RoleBlindingBoundary:
    role: OuterRole
    operation_access: tuple[tuple[str, str], ...]
    reason_codes: tuple[str, ...]
    _access_by_operation: Mapping[str, str] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", OuterRole(self.role))
        access = tuple(sorted((EvidenceOperation(k).value, EvidenceAccess(v).value) for k, v in self.operation_access))
        if {k for k, _ in access} != {item.value for item in EvidenceOperation}:
            raise TrainingDataInputError("Every evidence operation must have one access state.")
        object.__setattr__(self, "operation_access", access)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(str(v) for v in self.reason_codes))))
        object.__setattr__(self, "_access_by_operation", dict(access))

    def access_for(self, operation: EvidenceOperation | str) -> EvidenceAccess:
        key = EvidenceOperation(operation).value
        try:
            return EvidenceAccess(self._access_by_operation[key])
        except KeyError:
            raise KeyError(key) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ROLE_BLINDING_BOUNDARY_SCHEMA,
            "role": self.role.value,
            "operation_access": dict(self.operation_access),
            "reason_codes": list(self.reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RoleBlindingBoundary":
        if payload.get("schema") != ROLE_BLINDING_BOUNDARY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported role-blinding-boundary schema.")
        result = cls(
            role=OuterRole(payload["role"]),
            operation_access=tuple((str(k), str(v)) for k, v in payload["operation_access"].items()),
            reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Role-blinding-boundary digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class BlindingBoundaryCatalog:
    policy_digest: str
    outer_partition_digests: tuple[str, ...]
    boundaries: tuple[RoleBlindingBoundary, ...]
    _by_role: Mapping[OuterRole, RoleBlindingBoundary] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        partitions = tuple(sorted(validate_digest(v, name="outer_partition_digest") for v in self.outer_partition_digests))
        boundaries = tuple(sorted(self.boundaries, key=lambda item: item.role.value))
        if {item.role for item in boundaries} != set(OuterRole):
            raise TrainingDataInputError("Blinding catalog must cover every outer role.")
        object.__setattr__(self, "outer_partition_digests", partitions)
        object.__setattr__(self, "boundaries", boundaries)
        object.__setattr__(self, "_by_role", {item.role: item for item in boundaries})

    def for_role(self, role: OuterRole | str) -> RoleBlindingBoundary:
        target = OuterRole(role)
        try:
            return self._by_role[target]
        except KeyError:
            raise KeyError(target) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BLINDING_BOUNDARY_CATALOG_SCHEMA,
            "policy_digest": self.policy_digest,
            "outer_partition_digests": list(self.outer_partition_digests),
            "boundaries": [item.to_dict() for item in self.boundaries],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BlindingBoundaryCatalog":
        if payload.get("schema") != BLINDING_BOUNDARY_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported blinding-boundary-catalog schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            outer_partition_digests=tuple(str(v) for v in payload["outer_partition_digests"]),
            boundaries=tuple(RoleBlindingBoundary.from_dict(item) for item in payload["boundaries"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Blinding-boundary-catalog digest mismatch.")
        return result


def _access_map(role: OuterRole) -> tuple[tuple[str, str], ...]:
    allowed = EvidenceAccess.ALLOWED.value
    forbidden = EvidenceAccess.FORBIDDEN.value
    sealed = EvidenceAccess.SEALED_UNTIL_PROTOCOL_FREEZE.value
    provenance = EvidenceAccess.PROVENANCE_ONLY.value
    mapping = {
        OuterRole.DEVELOPMENT: {
            EvidenceOperation.RAW_GEOMETRY_ACCESS: allowed,
            EvidenceOperation.LABEL_DERIVED_SELECTION: allowed,
            EvidenceOperation.CHECKPOINT_MONITORING: forbidden,
            EvidenceOperation.UNCERTAINTY_CALIBRATION: forbidden,
            EvidenceOperation.POST_FREEZE_EVALUATION: forbidden,
        },
        OuterRole.OUTER_MONITOR: {
            EvidenceOperation.RAW_GEOMETRY_ACCESS: allowed,
            EvidenceOperation.LABEL_DERIVED_SELECTION: forbidden,
            EvidenceOperation.CHECKPOINT_MONITORING: allowed,
            EvidenceOperation.UNCERTAINTY_CALIBRATION: forbidden,
            EvidenceOperation.POST_FREEZE_EVALUATION: forbidden,
        },
        OuterRole.UNCERTAINTY_CALIBRATION: {
            EvidenceOperation.RAW_GEOMETRY_ACCESS: allowed,
            EvidenceOperation.LABEL_DERIVED_SELECTION: forbidden,
            EvidenceOperation.CHECKPOINT_MONITORING: forbidden,
            EvidenceOperation.UNCERTAINTY_CALIBRATION: allowed,
            EvidenceOperation.POST_FREEZE_EVALUATION: forbidden,
        },
        OuterRole.LOCKED_INTERPOLATION_TEST: {
            EvidenceOperation.RAW_GEOMETRY_ACCESS: sealed,
            EvidenceOperation.LABEL_DERIVED_SELECTION: forbidden,
            EvidenceOperation.CHECKPOINT_MONITORING: forbidden,
            EvidenceOperation.UNCERTAINTY_CALIBRATION: forbidden,
            EvidenceOperation.POST_FREEZE_EVALUATION: sealed,
        },
        OuterRole.PURGED: {operation: provenance for operation in EvidenceOperation},
        OuterRole.EXCLUDED: {operation: provenance for operation in EvidenceOperation},
    }
    return tuple((operation.value, mapping[role][operation]) for operation in EvidenceOperation)


def build_blinding_boundary_catalog(
    outer_partitions: tuple[OuterPartition, ...],
    *,
    policy: BlindingPolicy | None = None,
) -> BlindingBoundaryCatalog:
    active = BlindingPolicy() if policy is None else policy
    boundaries = tuple(
        RoleBlindingBoundary(
            role=role,
            operation_access=_access_map(role),
            reason_codes=("canonical_mlff_data5_role_boundary",),
        )
        for role in OuterRole
    )
    return BlindingBoundaryCatalog(
        policy_digest=active.policy_digest,
        outer_partition_digests=tuple(item.content_digest for item in outer_partitions),
        boundaries=boundaries,
    )
