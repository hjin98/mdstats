"""Leakage audits for MLFF-DATA5 outer and cross-validation roles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .partition import (
    CrossValidationPlan,
    OuterPartition,
    OuterRole,
    PartitionPolicy,
    PartitionUnit,
    PartitionUnitCatalog,
    _build_temporal_neighbor_index,
    _neighbor_unit_ids,
)

LEAKAGE_AUDIT_POLICY_SCHEMA = "mdstats.mlff-leakage-audit-policy.v1"
LEAKAGE_AUDIT_POLICY_VERSION = "mdstats.mlff-data5.leakage.2026-07.v1"
LEAKAGE_FINDING_SCHEMA = "mdstats.mlff-leakage-finding.v1"
LEAKAGE_AUDIT_REPORT_SCHEMA = "mdstats.mlff-leakage-audit-report.v1"


class LeakageSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class LeakageAuditPolicy:
    reject_geometry_duplicates_across_outer_roles: bool = True
    reject_labeled_duplicates_across_outer_roles: bool = True
    reject_event_window_role_split: bool = True
    reject_missing_purge_neighbors: bool = True
    policy_version: str = LEAKAGE_AUDIT_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LEAKAGE_AUDIT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "reject_geometry_duplicates_across_outer_roles": self.reject_geometry_duplicates_across_outer_roles,
            "reject_labeled_duplicates_across_outer_roles": self.reject_labeled_duplicates_across_outer_roles,
            "reject_event_window_role_split": self.reject_event_window_role_split,
            "reject_missing_purge_neighbors": self.reject_missing_purge_neighbors,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeakageAuditPolicy":
        if payload.get("schema") != LEAKAGE_AUDIT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported leakage-audit-policy schema.")
        result = cls(
            reject_geometry_duplicates_across_outer_roles=bool(payload["reject_geometry_duplicates_across_outer_roles"]),
            reject_labeled_duplicates_across_outer_roles=bool(payload["reject_labeled_duplicates_across_outer_roles"]),
            reject_event_window_role_split=bool(payload["reject_event_window_role_split"]),
            reject_missing_purge_neighbors=bool(payload["reject_missing_purge_neighbors"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Leakage-audit-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LeakageFinding:
    code: str
    severity: LeakageSeverity
    label_domain_id: str | None
    unit_ids: tuple[str, ...]
    frame_uids: tuple[str, ...]
    message: str

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise TrainingDataInputError("Leakage finding code and message are required.")
        object.__setattr__(self, "severity", LeakageSeverity(self.severity))
        units = tuple(sorted(set(str(v) for v in self.unit_ids)))
        frames = tuple(sorted(set(str(v) for v in self.frame_uids)))
        for value in units:
            validate_digest(value, name="unit_id")
        for value in frames:
            validate_digest(value, name="frame_uid")
        object.__setattr__(self, "unit_ids", units)
        object.__setattr__(self, "frame_uids", frames)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LEAKAGE_FINDING_SCHEMA,
            "code": self.code,
            "severity": self.severity.value,
            "label_domain_id": self.label_domain_id,
            "unit_ids": list(self.unit_ids),
            "frame_uids": list(self.frame_uids),
            "message": self.message,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeakageFinding":
        if payload.get("schema") != LEAKAGE_FINDING_SCHEMA:
            raise TrainingDataSerializationError("Unsupported leakage-finding schema.")
        result = cls(
            code=str(payload["code"]),
            severity=LeakageSeverity(payload["severity"]),
            label_domain_id=None if payload.get("label_domain_id") is None else str(payload["label_domain_id"]),
            unit_ids=tuple(str(v) for v in payload.get("unit_ids", ())),
            frame_uids=tuple(str(v) for v in payload.get("frame_uids", ())),
            message=str(payload["message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Leakage-finding digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LeakageAuditReport:
    policy_digest: str
    unit_catalog_digest: str
    outer_partition_digests: tuple[str, ...]
    cross_validation_plan_digests: tuple[str, ...]
    findings: tuple[LeakageFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "unit_catalog_digest", validate_digest(self.unit_catalog_digest, name="unit_catalog_digest"))
        object.__setattr__(self, "outer_partition_digests", tuple(sorted(validate_digest(v, name="outer_partition_digest") for v in self.outer_partition_digests)))
        object.__setattr__(self, "cross_validation_plan_digests", tuple(sorted(validate_digest(v, name="cross_validation_plan_digest") for v in self.cross_validation_plan_digests)))
        object.__setattr__(self, "findings", tuple(sorted(self.findings, key=lambda item: (item.severity.value, item.code, item.content_digest))))

    @property
    def passed(self) -> bool:
        return not any(item.severity is LeakageSeverity.ERROR for item in self.findings)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LEAKAGE_AUDIT_REPORT_SCHEMA,
            "policy_digest": self.policy_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "outer_partition_digests": list(self.outer_partition_digests),
            "cross_validation_plan_digests": list(self.cross_validation_plan_digests),
            "findings": [item.to_dict() for item in self.findings],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest, "passed": self.passed}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeakageAuditReport":
        if payload.get("schema") != LEAKAGE_AUDIT_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported leakage-audit-report schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            outer_partition_digests=tuple(str(v) for v in payload["outer_partition_digests"]),
            cross_validation_plan_digests=tuple(str(v) for v in payload["cross_validation_plan_digests"]),
            findings=tuple(LeakageFinding.from_dict(item) for item in payload.get("findings", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Leakage-audit-report digest mismatch.")
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("Leakage-audit passed state mismatch.")
        return result


def _role_by_unit(partitions: Sequence[OuterPartition]) -> dict[str, OuterRole]:
    result: dict[str, OuterRole] = {}
    for partition in partitions:
        for assignment in partition.assignments:
            if assignment.unit_id in result:
                raise TrainingDataInputError("A unit is present in multiple outer partitions.")
            result[assignment.unit_id] = assignment.role
    return result


def _expected_neighbor_ids(
    unit_catalog: PartitionUnitCatalog,
    selected_ids: set[str],
    radius: int,
    *,
    allowed_unit_ids: set[str] | None = None,
    temporal_index: tuple[
        Mapping[str, tuple[PartitionUnit, ...]],
        Mapping[str, tuple[str, int]],
    ] | None = None,
) -> set[str]:
    if radius <= 0 or not selected_ids:
        return set()
    units = unit_catalog.units if allowed_unit_ids is None else tuple(
        unit for unit in unit_catalog.units if unit.unit_id in allowed_unit_ids
    )
    return _neighbor_unit_ids(
        units,
        selected_ids,
        radius,
        temporal_index=temporal_index,
    )


def audit_partition_leakage(
    unit_catalog: PartitionUnitCatalog,
    outer_partitions: Sequence[OuterPartition],
    cross_validation_plans: Sequence[CrossValidationPlan],
    frame_catalog: Any,
    data4_bundle: Any,
    *,
    policy: LeakageAuditPolicy | None = None,
    partition_policy: PartitionPolicy | None = None,
) -> LeakageAuditReport:
    active = LeakageAuditPolicy() if policy is None else policy
    active_partition = PartitionPolicy() if partition_policy is None else partition_policy
    if unit_catalog.policy_digest != active_partition.policy_digest:
        raise TrainingDataInputError("Leakage audit partition policy does not match the unit catalog.")
    findings: list[LeakageFinding] = []
    role_by_unit = _role_by_unit(outer_partitions)
    known_units = {item.unit_id for item in unit_catalog.units}
    if set(role_by_unit) != known_units:
        findings.append(LeakageFinding(
            code="outer_partition_incomplete",
            severity=LeakageSeverity.ERROR,
            label_domain_id=None,
            unit_ids=tuple(sorted(known_units ^ set(role_by_unit))),
            frame_uids=(),
            message="Outer partitions do not classify every partition unit exactly once.",
        ))
    frame_to_unit = {uid: unit.unit_id for unit in unit_catalog.units for uid in unit.frame_uids}
    frame_to_role = {uid: role_by_unit[unit_id] for uid, unit_id in frame_to_unit.items() if unit_id in role_by_unit}

    if active.reject_missing_purge_neighbors:
        radius = active_partition.role_budget.purge_units_between_roles
        all_unit_temporal_index = _build_temporal_neighbor_index(unit_catalog.units)
        protected_outer_ids = {
            unit_id
            for unit_id, role in role_by_unit.items()
            if role in {
                OuterRole.OUTER_MONITOR,
                OuterRole.UNCERTAINTY_CALIBRATION,
                OuterRole.LOCKED_INTERPOLATION_TEST,
            }
        }
        expected_outer_purge = _expected_neighbor_ids(
            unit_catalog,
            protected_outer_ids,
            radius,
            temporal_index=all_unit_temporal_index,
        )
        missing_outer_purge = {
            unit_id
            for unit_id in expected_outer_purge
            if role_by_unit.get(unit_id) is not OuterRole.PURGED
        }
        if missing_outer_purge:
            findings.append(LeakageFinding(
                code="missing_outer_purge_neighbor",
                severity=LeakageSeverity.ERROR,
                label_domain_id=None,
                unit_ids=tuple(sorted(missing_outer_purge)),
                frame_uids=tuple(
                    uid for unit_id in sorted(missing_outer_purge) for uid in unit_catalog.unit(unit_id).frame_uids
                ),
                message="A same-run neighbor of outer evidence is not assigned to the outer purge role.",
            ))

    incompatible = {
        OuterRole.DEVELOPMENT,
        OuterRole.OUTER_MONITOR,
        OuterRole.UNCERTAINTY_CALIBRATION,
        OuterRole.LOCKED_INTERPOLATION_TEST,
    }
    geometry_roles: dict[str, set[OuterRole]] = {}
    labeled_roles: dict[str, set[OuterRole]] = {}
    geometry_frames: dict[str, list[str]] = {}
    labeled_frames: dict[str, list[str]] = {}
    for frame in frame_catalog.frames:
        role = frame_to_role.get(frame.frame_uid)
        if role not in incompatible:
            continue
        geometry_roles.setdefault(frame.geometry_fingerprint, set()).add(role)
        geometry_frames.setdefault(frame.geometry_fingerprint, []).append(frame.frame_uid)
        labeled_roles.setdefault(frame.labeled_configuration_fingerprint, set()).add(role)
        labeled_frames.setdefault(frame.labeled_configuration_fingerprint, []).append(frame.frame_uid)
    if active.reject_geometry_duplicates_across_outer_roles:
        for fingerprint, roles in geometry_roles.items():
            if len(roles) > 1:
                findings.append(LeakageFinding(
                    code="geometry_duplicate_crosses_outer_roles",
                    severity=LeakageSeverity.ERROR,
                    label_domain_id=None,
                    unit_ids=tuple(sorted({frame_to_unit[uid] for uid in geometry_frames[fingerprint]})),
                    frame_uids=tuple(geometry_frames[fingerprint]),
                    message="An exact geometry fingerprint appears in incompatible outer roles.",
                ))
    if active.reject_labeled_duplicates_across_outer_roles:
        for fingerprint, roles in labeled_roles.items():
            if len(roles) > 1:
                findings.append(LeakageFinding(
                    code="labeled_duplicate_crosses_outer_roles",
                    severity=LeakageSeverity.ERROR,
                    label_domain_id=None,
                    unit_ids=tuple(sorted({frame_to_unit[uid] for uid in labeled_frames[fingerprint]})),
                    frame_uids=tuple(labeled_frames[fingerprint]),
                    message="An exact labeled configuration appears in incompatible outer roles.",
                ))
    if active.reject_event_window_role_split:
        for event in data4_bundle.events.events:
            roles = {frame_to_role.get(uid) for uid in event.protected_frame_uids}
            roles.discard(None)
            if len(roles) > 1:
                findings.append(LeakageFinding(
                    code="protected_event_window_split",
                    severity=LeakageSeverity.ERROR,
                    label_domain_id=None,
                    unit_ids=tuple(sorted({frame_to_unit[uid] for uid in event.protected_frame_uids if uid in frame_to_unit})),
                    frame_uids=event.protected_frame_uids,
                    message="A DATA4 protected event window crosses outer statistical roles.",
                ))

    outer_by_domain = {item.label_domain_id: item for item in outer_partitions}
    for plan in cross_validation_plans:
        outer = outer_by_domain[plan.label_domain_id]
        development = set(outer.units_for(OuterRole.DEVELOPMENT))
        development_units = tuple(
            unit_catalog.unit(unit_id) for unit_id in sorted(development)
        )
        development_temporal_index = _build_temporal_neighbor_index(
            development_units
        )
        held_out_seen: set[str] = set()
        for fold in plan.folds:
            groups = [set(fold.training_unit_ids), set(fold.checkpoint_monitor_unit_ids), set(fold.evaluation_unit_ids), set(fold.purged_unit_ids)]
            if active.reject_missing_purge_neighbors:
                protected_ids = set(fold.evaluation_unit_ids) | set(fold.checkpoint_monitor_unit_ids)
                expected_purge = _expected_neighbor_ids(
                    unit_catalog,
                    protected_ids,
                    active_partition.role_budget.purge_units_between_roles,
                    allowed_unit_ids=development,
                    temporal_index=development_temporal_index,
                )
                missing_purge = expected_purge - set(fold.purged_unit_ids) - protected_ids
                if missing_purge:
                    findings.append(LeakageFinding(
                        code="missing_cross_validation_purge_neighbor",
                        severity=LeakageSeverity.ERROR,
                        label_domain_id=plan.label_domain_id,
                        unit_ids=tuple(sorted(missing_purge)),
                        frame_uids=tuple(
                            uid for unit_id in sorted(missing_purge) for uid in unit_catalog.unit(unit_id).frame_uids
                        ),
                        message="A same-run neighbor of a held-out or checkpoint-monitor unit remains unpurged in a cross-validation fold.",
                    ))
            if any(groups[i] & groups[j] for i in range(len(groups)) for j in range(i + 1, len(groups))):
                findings.append(LeakageFinding(
                    code="cross_validation_role_overlap",
                    severity=LeakageSeverity.ERROR,
                    label_domain_id=plan.label_domain_id,
                    unit_ids=tuple(sorted(set().union(*groups))),
                    frame_uids=(),
                    message="Cross-validation training, monitor, evaluation, and purge roles overlap.",
                ))
            classified = set().union(*groups)
            if classified != development:
                findings.append(LeakageFinding(
                    code="cross_validation_does_not_classify_development",
                    severity=LeakageSeverity.ERROR,
                    label_domain_id=plan.label_domain_id,
                    unit_ids=tuple(sorted(classified ^ development)),
                    frame_uids=(),
                    message="A cross-validation fold does not classify every development unit.",
                ))
            held_out_seen |= set(fold.evaluation_unit_ids)
        if held_out_seen != development:
            findings.append(LeakageFinding(
                code="development_not_held_out_exactly_once",
                severity=LeakageSeverity.ERROR,
                label_domain_id=plan.label_domain_id,
                unit_ids=tuple(sorted(held_out_seen ^ development)),
                frame_uids=(),
                message="Every development unit must appear in one held-out evaluation fold.",
            ))

    if not findings:
        findings.append(LeakageFinding(
            code="no_partition_leakage_detected",
            severity=LeakageSeverity.INFO,
            label_domain_id=None,
            unit_ids=(),
            frame_uids=(),
            message="All DATA5 identity, event-window, role, and fold checks passed.",
        ))
    return LeakageAuditReport(
        policy_digest=active.policy_digest,
        unit_catalog_digest=unit_catalog.content_digest,
        outer_partition_digests=tuple(item.content_digest for item in outer_partitions),
        cross_validation_plan_digests=tuple(item.content_digest for item in cross_validation_plans),
        findings=tuple(findings),
    )
