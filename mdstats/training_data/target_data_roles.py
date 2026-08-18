"""TARGET-DATA2A lineage-aware authority for target-size selection.

DATA5 owns correlation-aware partition units and the statistical role split.
This module freezes the subset of those decisions that is allowed to influence
TARGET-DATA2 target-size selection.  Later coverage, foundation-residual, and
size-convergence code must authenticate evidence against this object instead of
reconstructing a development set ad hoc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)
from .partition import OuterRole

TARGET_DATA_ROLE_FREEZE_POLICY_SCHEMA = "mdstats.target-data-role-freeze-policy.v1"
TARGET_DATA_DEVELOPMENT_INTERVAL_SCHEMA = "mdstats.target-data-development-interval.v1"
TARGET_DATA_DOMAIN_ROLE_FREEZE_SCHEMA = "mdstats.target-data-domain-role-freeze.v1"
TARGET_DATA_SOURCE_LINEAGE_SCHEMA = "mdstats.target-data-source-lineage.v1"
TARGET_DATA_CORRELATION_FAMILY_SCHEMA = "mdstats.target-data-correlation-family.v1"
TARGET_DATA_ROLE_FREEZE_SCHEMA = "mdstats.target-data-role-freeze.v1"
TARGET_DATA_ROLE_FREEZE_VERSION = "mdstats.target-data2a.role-freeze.2026-08.v1"

_CV_EVIDENCE_ROLES = ("training", "checkpoint_monitor", "evaluation")


@dataclass(frozen=True, slots=True)
class TargetDataRoleFreezePolicy:
    """Immutable fail-closed policy for TARGET-DATA2A role authority."""

    require_passing_data5_leakage_audit: bool = True
    reject_exact_geometry_family_split: bool = True
    reject_declared_structural_family_split: bool = True
    reject_explicit_correlation_family_split: bool = True
    explicit_correlation_group_assertion_keys: tuple[str, ...] = (
        "correlation_family_id",
        "near_duplicate_family_id",
        "active_learning_correlation_family_id",
    )
    lineage_metadata_assertion_keys: tuple[str, ...] = (
        "active_learning_lineage_id",
        "active_learning_generation",
        "al_lineage_id",
        "al_generation",
        "lineage_id",
        "generation_id",
    )
    policy_version: str = TARGET_DATA_ROLE_FREEZE_VERSION

    def __post_init__(self) -> None:
        for name in (
            "explicit_correlation_group_assertion_keys",
            "lineage_metadata_assertion_keys",
        ):
            values = tuple(str(v).strip() for v in getattr(self, name))
            if any(not value for value in values) or len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} must contain unique non-empty keys.")
            object.__setattr__(self, name, values)
        if not self.policy_version.strip():
            raise TrainingDataInputError("TARGET-DATA2A policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_ROLE_FREEZE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "require_passing_data5_leakage_audit": self.require_passing_data5_leakage_audit,
            "reject_exact_geometry_family_split": self.reject_exact_geometry_family_split,
            "reject_declared_structural_family_split": self.reject_declared_structural_family_split,
            "reject_explicit_correlation_family_split": self.reject_explicit_correlation_family_split,
            "explicit_correlation_group_assertion_keys": list(self.explicit_correlation_group_assertion_keys),
            "lineage_metadata_assertion_keys": list(self.lineage_metadata_assertion_keys),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataRoleFreezePolicy":
        if payload.get("schema") != TARGET_DATA_ROLE_FREEZE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A policy schema.")
        result = cls(
            require_passing_data5_leakage_audit=bool(payload["require_passing_data5_leakage_audit"]),
            reject_exact_geometry_family_split=bool(payload["reject_exact_geometry_family_split"]),
            reject_declared_structural_family_split=bool(payload["reject_declared_structural_family_split"]),
            reject_explicit_correlation_family_split=bool(payload["reject_explicit_correlation_family_split"]),
            explicit_correlation_group_assertion_keys=tuple(
                str(v) for v in payload.get("explicit_correlation_group_assertion_keys", ())
            ),
            lineage_metadata_assertion_keys=tuple(
                str(v) for v in payload.get("lineage_metadata_assertion_keys", ())
            ),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDevelopmentInterval:
    """One authorized correlation-aware development interval."""

    unit_id: str
    run_id: str
    label_domain_id: str
    condition_id: str
    source_frame_start: int
    source_frame_stop: int
    frame_uids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_id", validate_digest(self.unit_id, name="unit_id"))
        object.__setattr__(self, "condition_id", validate_digest(self.condition_id, name="condition_id"))
        if not self.run_id.strip() or not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2A interval identifiers must be non-empty.")
        if self.source_frame_start < 0 or self.source_frame_stop <= self.source_frame_start:
            raise TrainingDataInputError("TARGET-DATA2A development interval is invalid.")
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if not frames or len(set(frames)) != len(frames):
            raise TrainingDataInputError("TARGET-DATA2A interval frames must be non-empty and unique.")
        object.__setattr__(self, "frame_uids", frames)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_DEVELOPMENT_INTERVAL_SCHEMA,
            "unit_id": self.unit_id,
            "run_id": self.run_id,
            "label_domain_id": self.label_domain_id,
            "condition_id": self.condition_id,
            "source_frame_start": self.source_frame_start,
            "source_frame_stop": self.source_frame_stop,
            "frame_uids": list(self.frame_uids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDevelopmentInterval":
        if payload.get("schema") != TARGET_DATA_DEVELOPMENT_INTERVAL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A interval schema.")
        result = cls(
            unit_id=str(payload["unit_id"]),
            run_id=str(payload["run_id"]),
            label_domain_id=str(payload["label_domain_id"]),
            condition_id=str(payload["condition_id"]),
            source_frame_start=int(payload["source_frame_start"]),
            source_frame_stop=int(payload["source_frame_stop"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A interval digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataDomainRoleFreeze:
    """Frozen outer/CV role authority for one label domain."""

    label_domain_id: str
    outer_partition_digest: str
    cross_validation_plan_digest: str
    size_development_unit_ids: tuple[str, ...]
    size_development_frame_uids: tuple[str, ...]
    final_validation_unit_ids: tuple[str, ...]
    final_validation_frame_uids: tuple[str, ...]
    uncertainty_calibration_unit_ids: tuple[str, ...]
    uncertainty_calibration_frame_uids: tuple[str, ...]
    locked_test_unit_ids: tuple[str, ...]
    locked_test_frame_uids: tuple[str, ...]
    purged_unit_ids: tuple[str, ...]
    purged_frame_uids: tuple[str, ...]
    excluded_unit_ids: tuple[str, ...]
    excluded_frame_uids: tuple[str, ...]
    cv_evaluation_unit_ids_by_fold: tuple[tuple[int, tuple[str, ...]], ...]
    cv_checkpoint_monitor_unit_ids_by_fold: tuple[tuple[int, tuple[str, ...]], ...]
    development_intervals: tuple[TargetDevelopmentInterval, ...]
    _size_frame_set: frozenset[str] = field(default_factory=frozenset, init=False, repr=False, compare=False)
    _size_unit_set: frozenset[str] = field(default_factory=frozenset, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2A label_domain_id must be non-empty.")
        for name in ("outer_partition_digest", "cross_validation_plan_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))

        unit_names = (
            "size_development_unit_ids",
            "final_validation_unit_ids",
            "uncertainty_calibration_unit_ids",
            "locked_test_unit_ids",
            "purged_unit_ids",
            "excluded_unit_ids",
        )
        frame_names = (
            "size_development_frame_uids",
            "final_validation_frame_uids",
            "uncertainty_calibration_frame_uids",
            "locked_test_frame_uids",
            "purged_frame_uids",
            "excluded_frame_uids",
        )
        unit_sets: list[set[str]] = []
        frame_sets: list[set[str]] = []
        for name in unit_names:
            values = tuple(validate_digest(v, name="unit_id") for v in getattr(self, name))
            if len(values) != len(set(values)):
                raise TrainingDataInputError(f"TARGET-DATA2A {name} contains duplicates.")
            object.__setattr__(self, name, values)
            unit_sets.append(set(values))
        for name in frame_names:
            values = tuple(validate_digest(v, name="frame_uid") for v in getattr(self, name))
            if len(values) != len(set(values)):
                raise TrainingDataInputError(f"TARGET-DATA2A {name} contains duplicates.")
            object.__setattr__(self, name, values)
            frame_sets.append(set(values))
        if not self.size_development_unit_ids or not self.size_development_frame_uids:
            raise TrainingDataInputError("TARGET-DATA2A size-development authority cannot be empty.")
        if any(unit_sets[i] & unit_sets[j] for i in range(len(unit_sets)) for j in range(i + 1, len(unit_sets))):
            raise TrainingDataInputError("TARGET-DATA2A outer unit roles must be disjoint.")
        if any(frame_sets[i] & frame_sets[j] for i in range(len(frame_sets)) for j in range(i + 1, len(frame_sets))):
            raise TrainingDataInputError("TARGET-DATA2A outer frame roles must be disjoint.")

        evaluations = tuple(
            (int(index), tuple(validate_digest(v, name="unit_id") for v in values))
            for index, values in self.cv_evaluation_unit_ids_by_fold
        )
        monitors = tuple(
            (int(index), tuple(validate_digest(v, name="unit_id") for v in values))
            for index, values in self.cv_checkpoint_monitor_unit_ids_by_fold
        )
        if tuple(index for index, _ in evaluations) != tuple(range(len(evaluations))):
            raise TrainingDataInputError("TARGET-DATA2A CV evaluation fold indices must be contiguous.")
        if tuple(index for index, _ in monitors) != tuple(range(len(monitors))):
            raise TrainingDataInputError("TARGET-DATA2A CV monitor fold indices must be contiguous.")
        if len(evaluations) != len(monitors):
            raise TrainingDataInputError("TARGET-DATA2A CV role records disagree on fold count.")
        held_out = [unit_id for _, values in evaluations for unit_id in values]
        if len(held_out) != len(set(held_out)) or set(held_out) != set(self.size_development_unit_ids):
            raise TrainingDataInputError(
                "TARGET-DATA2A CV evaluations must hold out every size-development unit exactly once."
            )
        object.__setattr__(self, "cv_evaluation_unit_ids_by_fold", evaluations)
        object.__setattr__(self, "cv_checkpoint_monitor_unit_ids_by_fold", monitors)

        intervals = tuple(sorted(
            self.development_intervals,
            key=lambda item: (item.run_id, item.source_frame_start, item.unit_id),
        ))
        if {item.unit_id for item in intervals} != set(self.size_development_unit_ids):
            raise TrainingDataInputError(
                "TARGET-DATA2A development intervals must cover every authorized development unit."
            )
        interval_frames = [uid for item in intervals for uid in item.frame_uids]
        if len(interval_frames) != len(set(interval_frames)) or set(interval_frames) != set(self.size_development_frame_uids):
            raise TrainingDataInputError(
                "TARGET-DATA2A development intervals must cover every authorized development frame exactly once."
            )
        if any(item.label_domain_id != self.label_domain_id for item in intervals):
            raise TrainingDataInputError("TARGET-DATA2A interval label domain mismatch.")
        object.__setattr__(self, "development_intervals", intervals)
        object.__setattr__(self, "_size_frame_set", frozenset(self.size_development_frame_uids))
        object.__setattr__(self, "_size_unit_set", frozenset(self.size_development_unit_ids))

    def allows_size_selection_frame(self, frame_uid: str) -> bool:
        return str(frame_uid) in self._size_frame_set

    def allows_size_selection_unit(self, unit_id: str) -> bool:
        return str(unit_id) in self._size_unit_set

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_DOMAIN_ROLE_FREEZE_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "outer_partition_digest": self.outer_partition_digest,
            "cross_validation_plan_digest": self.cross_validation_plan_digest,
            "size_development_unit_ids": list(self.size_development_unit_ids),
            "size_development_frame_uids": list(self.size_development_frame_uids),
            "final_validation_unit_ids": list(self.final_validation_unit_ids),
            "final_validation_frame_uids": list(self.final_validation_frame_uids),
            "uncertainty_calibration_unit_ids": list(self.uncertainty_calibration_unit_ids),
            "uncertainty_calibration_frame_uids": list(self.uncertainty_calibration_frame_uids),
            "locked_test_unit_ids": list(self.locked_test_unit_ids),
            "locked_test_frame_uids": list(self.locked_test_frame_uids),
            "purged_unit_ids": list(self.purged_unit_ids),
            "purged_frame_uids": list(self.purged_frame_uids),
            "excluded_unit_ids": list(self.excluded_unit_ids),
            "excluded_frame_uids": list(self.excluded_frame_uids),
            "cv_evaluation_unit_ids_by_fold": [
                {"fold_index": index, "unit_ids": list(values)} for index, values in self.cv_evaluation_unit_ids_by_fold
            ],
            "cv_checkpoint_monitor_unit_ids_by_fold": [
                {"fold_index": index, "unit_ids": list(values)} for index, values in self.cv_checkpoint_monitor_unit_ids_by_fold
            ],
            "development_intervals": [item.to_dict() for item in self.development_intervals],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataDomainRoleFreeze":
        if payload.get("schema") != TARGET_DATA_DOMAIN_ROLE_FREEZE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A domain-role schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            outer_partition_digest=str(payload["outer_partition_digest"]),
            cross_validation_plan_digest=str(payload["cross_validation_plan_digest"]),
            size_development_unit_ids=tuple(str(v) for v in payload["size_development_unit_ids"]),
            size_development_frame_uids=tuple(str(v) for v in payload["size_development_frame_uids"]),
            final_validation_unit_ids=tuple(str(v) for v in payload.get("final_validation_unit_ids", ())),
            final_validation_frame_uids=tuple(str(v) for v in payload.get("final_validation_frame_uids", ())),
            uncertainty_calibration_unit_ids=tuple(str(v) for v in payload.get("uncertainty_calibration_unit_ids", ())),
            uncertainty_calibration_frame_uids=tuple(str(v) for v in payload.get("uncertainty_calibration_frame_uids", ())),
            locked_test_unit_ids=tuple(str(v) for v in payload.get("locked_test_unit_ids", ())),
            locked_test_frame_uids=tuple(str(v) for v in payload.get("locked_test_frame_uids", ())),
            purged_unit_ids=tuple(str(v) for v in payload.get("purged_unit_ids", ())),
            purged_frame_uids=tuple(str(v) for v in payload.get("purged_frame_uids", ())),
            excluded_unit_ids=tuple(str(v) for v in payload.get("excluded_unit_ids", ())),
            excluded_frame_uids=tuple(str(v) for v in payload.get("excluded_frame_uids", ())),
            cv_evaluation_unit_ids_by_fold=tuple(
                (int(item["fold_index"]), tuple(str(v) for v in item["unit_ids"]))
                for item in payload["cv_evaluation_unit_ids_by_fold"]
            ),
            cv_checkpoint_monitor_unit_ids_by_fold=tuple(
                (int(item["fold_index"]), tuple(str(v) for v in item["unit_ids"]))
                for item in payload["cv_checkpoint_monitor_unit_ids_by_fold"]
            ),
            development_intervals=tuple(
                TargetDevelopmentInterval.from_dict(item) for item in payload["development_intervals"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A domain-role digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataSourceLineageRecord:
    """Reviewed source-level lineage retained by the size-selection authority."""

    run_id: str
    reference_group: str | None
    replica_id: str | None
    reference_run_id: str | None
    lineage_assertions: tuple[tuple[str, Any], ...]

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise TrainingDataInputError("TARGET-DATA2A source lineage requires run_id.")
        assertions = tuple(
            sorted((str(key), json_value(value)) for key, value in self.lineage_assertions)
        )
        if len({key for key, _ in assertions}) != len(assertions):
            raise TrainingDataInputError("TARGET-DATA2A lineage assertion keys must be unique.")
        object.__setattr__(self, "lineage_assertions", assertions)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_SOURCE_LINEAGE_SCHEMA,
            "run_id": self.run_id,
            "reference_group": self.reference_group,
            "replica_id": self.replica_id,
            "reference_run_id": self.reference_run_id,
            "lineage_assertions": {key: value for key, value in self.lineage_assertions},
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataSourceLineageRecord":
        if payload.get("schema") != TARGET_DATA_SOURCE_LINEAGE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A source-lineage schema.")
        assertions = payload.get("lineage_assertions", {})
        if not isinstance(assertions, Mapping):
            raise TrainingDataSerializationError("TARGET-DATA2A lineage_assertions must be a mapping.")
        result = cls(
            run_id=str(payload["run_id"]),
            reference_group=None if payload.get("reference_group") is None else str(payload["reference_group"]),
            replica_id=None if payload.get("replica_id") is None else str(payload["replica_id"]),
            reference_run_id=None if payload.get("reference_run_id") is None else str(payload["reference_run_id"]),
            lineage_assertions=tuple((str(key), value) for key, value in assertions.items()),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A source-lineage digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataCorrelationFamilyRecord:
    """Exact, declared near-duplicate, or explicit correlation family."""

    family_kind: str
    family_id: str
    member_unit_ids: tuple[str, ...]
    member_frame_uids: tuple[str, ...] = ()
    source_label: str | None = None

    def __post_init__(self) -> None:
        if not self.family_kind.strip():
            raise TrainingDataInputError("TARGET-DATA2A correlation family kind must be non-empty.")
        object.__setattr__(self, "family_id", validate_digest(self.family_id, name="family_id"))
        units = tuple(sorted(set(validate_digest(v, name="unit_id") for v in self.member_unit_ids)))
        frames = tuple(sorted(set(validate_digest(v, name="frame_uid") for v in self.member_frame_uids)))
        if len(units) < 2:
            raise TrainingDataInputError("TARGET-DATA2A correlation families must span at least two partition units.")
        object.__setattr__(self, "member_unit_ids", units)
        object.__setattr__(self, "member_frame_uids", frames)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_CORRELATION_FAMILY_SCHEMA,
            "family_kind": self.family_kind,
            "family_id": self.family_id,
            "member_unit_ids": list(self.member_unit_ids),
            "member_frame_uids": list(self.member_frame_uids),
            "source_label": self.source_label,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataCorrelationFamilyRecord":
        if payload.get("schema") != TARGET_DATA_CORRELATION_FAMILY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A correlation-family schema.")
        result = cls(
            family_kind=str(payload["family_kind"]),
            family_id=str(payload["family_id"]),
            member_unit_ids=tuple(str(v) for v in payload["member_unit_ids"]),
            member_frame_uids=tuple(str(v) for v in payload.get("member_frame_uids", ())),
            source_label=None if payload.get("source_label") is None else str(payload["source_label"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A correlation-family digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataRoleFreeze:
    """Immutable authority limiting every N_target decision to development evidence."""

    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    partition_policy_digest: str
    partition_unit_catalog_digest: str
    leakage_audit_digest: str
    policy: TargetDataRoleFreezePolicy
    domains: tuple[TargetDataDomainRoleFreeze, ...]
    source_lineages: tuple[TargetDataSourceLineageRecord, ...]
    correlation_families: tuple[TargetDataCorrelationFamilyRecord, ...]
    external_challenge_artifact_digests: tuple[str, ...] = ()
    authority_version: str = TARGET_DATA_ROLE_FREEZE_VERSION
    _domain_by_id: dict[str, TargetDataDomainRoleFreeze] = field(default_factory=dict, init=False, repr=False, compare=False)
    _all_size_frames: frozenset[str] = field(default_factory=frozenset, init=False, repr=False, compare=False)
    _all_size_units: frozenset[str] = field(default_factory=frozenset, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2A dataset_id must be non-empty.")
        for name in (
            "source_catalog_digest",
            "frame_catalog_digest",
            "data5_bundle_digest",
            "partition_policy_digest",
            "partition_unit_catalog_digest",
            "leakage_audit_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2A domains must be non-empty and unique.")
        all_frames = [uid for domain in domains for uid in domain.size_development_frame_uids]
        all_units = [uid for domain in domains for uid in domain.size_development_unit_ids]
        if len(all_frames) != len(set(all_frames)) or len(all_units) != len(set(all_units)):
            raise TrainingDataInputError("TARGET-DATA2A development authority overlaps label domains.")
        lineages = tuple(sorted(self.source_lineages, key=lambda item: item.run_id))
        if len({item.run_id for item in lineages}) != len(lineages):
            raise TrainingDataInputError("TARGET-DATA2A source lineage run IDs must be unique.")
        families = tuple(sorted(self.correlation_families, key=lambda item: (item.family_kind, item.family_id)))
        if len({(item.family_kind, item.family_id) for item in families}) != len(families):
            raise TrainingDataInputError("TARGET-DATA2A correlation family identities must be unique.")
        challenges = tuple(sorted(validate_digest(v, name="challenge_artifact_digest") for v in self.external_challenge_artifact_digests))
        if len(challenges) != len(set(challenges)):
            raise TrainingDataInputError("TARGET-DATA2A challenge artifact digests must be unique.")
        if self.authority_version != TARGET_DATA_ROLE_FREEZE_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2A role-freeze authority version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "source_lineages", lineages)
        object.__setattr__(self, "correlation_families", families)
        object.__setattr__(self, "external_challenge_artifact_digests", challenges)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})
        object.__setattr__(self, "_all_size_frames", frozenset(all_frames))
        object.__setattr__(self, "_all_size_units", frozenset(all_units))

    def domain(self, label_domain_id: str) -> TargetDataDomainRoleFreeze:
        try:
            return self._domain_by_id[str(label_domain_id)]
        except KeyError:
            raise KeyError(label_domain_id) from None

    @property
    def size_development_frame_uids(self) -> tuple[str, ...]:
        return tuple(sorted(self._all_size_frames))

    @property
    def size_development_unit_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._all_size_units))

    def require_size_selection_frames(
        self,
        frame_uids: Sequence[str],
        *,
        label_domain_id: str | None = None,
        context: str = "TARGET-DATA2 size-selection evidence",
    ) -> tuple[str, ...]:
        requested = tuple(str(v) for v in frame_uids)
        if len(requested) != len(set(requested)):
            raise TrainingDataInputError(f"{context}: duplicate frame UIDs are not allowed.")
        allowed = self._all_size_frames if label_domain_id is None else self.domain(label_domain_id)._size_frame_set
        rejected = tuple(sorted(set(requested) - set(allowed)))
        if rejected:
            preview = ", ".join(rejected[:4]) + (" ..." if len(rejected) > 4 else "")
            raise TrainingDataInputError(
                f"{context}: {len(rejected)} frame(s) are outside the frozen training-eligible development domain: {preview}"
            )
        return requested

    def require_size_selection_units(
        self,
        unit_ids: Sequence[str],
        *,
        label_domain_id: str | None = None,
        context: str = "TARGET-DATA2 size-selection evidence",
    ) -> tuple[str, ...]:
        requested = tuple(str(v) for v in unit_ids)
        if len(requested) != len(set(requested)):
            raise TrainingDataInputError(f"{context}: duplicate unit IDs are not allowed.")
        allowed = self._all_size_units if label_domain_id is None else self.domain(label_domain_id)._size_unit_set
        rejected = tuple(sorted(set(requested) - set(allowed)))
        if rejected:
            preview = ", ".join(rejected[:4]) + (" ..." if len(rejected) > 4 else "")
            raise TrainingDataInputError(
                f"{context}: {len(rejected)} unit(s) are outside the frozen training-eligible development domain: {preview}"
            )
        return requested

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_ROLE_FREEZE_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "partition_policy_digest": self.partition_policy_digest,
            "partition_unit_catalog_digest": self.partition_unit_catalog_digest,
            "leakage_audit_digest": self.leakage_audit_digest,
            "policy": self.policy.to_dict(),
            "domains": [item.to_dict() for item in self.domains],
            "source_lineages": [item.to_dict() for item in self.source_lineages],
            "correlation_families": [item.to_dict() for item in self.correlation_families],
            "external_challenge_artifact_digests": list(self.external_challenge_artifact_digests),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataRoleFreeze":
        if payload.get("schema") != TARGET_DATA_ROLE_FREEZE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2A role-freeze schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            partition_policy_digest=str(payload["partition_policy_digest"]),
            partition_unit_catalog_digest=str(payload["partition_unit_catalog_digest"]),
            leakage_audit_digest=str(payload["leakage_audit_digest"]),
            policy=TargetDataRoleFreezePolicy.from_dict(payload["policy"]),
            domains=tuple(TargetDataDomainRoleFreeze.from_dict(item) for item in payload["domains"]),
            source_lineages=tuple(TargetDataSourceLineageRecord.from_dict(item) for item in payload.get("source_lineages", ())),
            correlation_families=tuple(TargetDataCorrelationFamilyRecord.from_dict(item) for item in payload.get("correlation_families", ())),
            external_challenge_artifact_digests=tuple(str(v) for v in payload.get("external_challenge_artifact_digests", ())),
            authority_version=str(payload.get("authority_version", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2A role-freeze digest mismatch.")
        return result


def _frames_for_units(unit_catalog: Any, unit_ids: Sequence[str]) -> tuple[str, ...]:
    result = [uid for unit_id in unit_ids for uid in unit_catalog.unit(unit_id).frame_uids]
    if len(result) != len(set(result)):
        raise TrainingDataInputError("Partition units overlap in frame membership.")
    return tuple(sorted(result))


def _unit_outer_roles(data5_bundle: Any) -> dict[str, OuterRole]:
    result: dict[str, OuterRole] = {}
    for outer in data5_bundle.outer_partitions:
        for assignment in outer.assignments:
            if assignment.unit_id in result:
                raise TrainingDataInputError("TARGET-DATA2A found a unit in multiple outer partitions.")
            result[assignment.unit_id] = assignment.role
    return result


def _cv_role_map(plan: Any, fold_index: int) -> dict[str, str]:
    fold = plan.folds[fold_index]
    result: dict[str, str] = {}
    for role, unit_ids in (
        ("training", fold.training_unit_ids),
        ("checkpoint_monitor", fold.checkpoint_monitor_unit_ids),
        ("evaluation", fold.evaluation_unit_ids),
        ("purged", fold.purged_unit_ids),
    ):
        for unit_id in unit_ids:
            if unit_id in result:
                raise TrainingDataInputError("TARGET-DATA2A CV roles overlap.")
            result[unit_id] = role
    return result


def _audit_family_roles(
    family_kind: str,
    family_id: str,
    unit_ids: Sequence[str],
    *,
    unit_outer_role: Mapping[str, OuterRole],
    cv_plan_by_domain: Mapping[str, Any],
    unit_catalog: Any,
) -> None:
    units = tuple(sorted(set(str(v) for v in unit_ids)))
    evidence_outer = {
        unit_outer_role[unit_id]
        for unit_id in units
        if unit_outer_role.get(unit_id)
        in {
            OuterRole.DEVELOPMENT,
            OuterRole.OUTER_MONITOR,
            OuterRole.UNCERTAINTY_CALIBRATION,
            OuterRole.LOCKED_INTERPOLATION_TEST,
        }
    }
    if len(evidence_outer) > 1:
        rendered = ", ".join(sorted(role.value for role in evidence_outer))
        raise TrainingDataInputError(
            f"TARGET-DATA2A {family_kind} family {family_id} crosses independent outer roles: {rendered}."
        )

    by_domain: dict[str, set[str]] = {}
    for unit_id in units:
        unit = unit_catalog.unit(unit_id)
        if unit_outer_role.get(unit_id) is OuterRole.DEVELOPMENT:
            by_domain.setdefault(unit.label_domain_id, set()).add(unit_id)
    for domain_id, family_units in by_domain.items():
        plan = cv_plan_by_domain[domain_id]
        for fold_index in range(len(plan.folds)):
            cv_roles = _cv_role_map(plan, fold_index)
            observed = {
                cv_roles[unit_id]
                for unit_id in family_units
                if cv_roles.get(unit_id) in _CV_EVIDENCE_ROLES
            }
            if len(observed) > 1:
                rendered = ", ".join(sorted(observed))
                raise TrainingDataInputError(
                    f"TARGET-DATA2A {family_kind} family {family_id} crosses CV fold {fold_index} evidence roles: {rendered}."
                )


def _correlation_family_records(
    source_catalog: Any,
    frame_catalog: Any,
    data5_bundle: Any,
    policy: TargetDataRoleFreezePolicy,
    declared_structural_family_by_frame_uid: Mapping[str, str] | None,
) -> tuple[TargetDataCorrelationFamilyRecord, ...]:
    unit_catalog = data5_bundle.unit_catalog
    frame_to_unit = {
        frame_uid: unit.unit_id for unit in unit_catalog.units for frame_uid in unit.frame_uids
    }
    known_frames = set(frame_to_unit)
    unit_outer_role = _unit_outer_roles(data5_bundle)
    cv_plan_by_domain = {
        plan.label_domain_id: plan for plan in data5_bundle.cross_validation_plans
    }
    records: list[TargetDataCorrelationFamilyRecord] = []

    exact_groups: dict[str, list[str]] = {}
    for frame in frame_catalog.frames:
        if frame.frame_uid in known_frames:
            exact_groups.setdefault(frame.geometry_fingerprint, []).append(frame.frame_uid)
    if policy.reject_exact_geometry_family_split:
        for fingerprint, frame_uids in sorted(exact_groups.items()):
            unit_ids = tuple(sorted({frame_to_unit[uid] for uid in frame_uids}))
            if len(unit_ids) < 2:
                continue
            _audit_family_roles(
                "exact_geometry",
                fingerprint,
                unit_ids,
                unit_outer_role=unit_outer_role,
                cv_plan_by_domain=cv_plan_by_domain,
                unit_catalog=unit_catalog,
            )
            records.append(TargetDataCorrelationFamilyRecord(
                family_kind="exact_geometry",
                family_id=fingerprint,
                member_unit_ids=unit_ids,
                member_frame_uids=tuple(frame_uids),
            ))

    if declared_structural_family_by_frame_uid is not None:
        unknown = sorted(set(str(uid) for uid in declared_structural_family_by_frame_uid) - known_frames)
        if unknown:
            raise TrainingDataInputError(
                "TARGET-DATA2A declared structural-family map contains frames outside DATA5: "
                + ", ".join(unknown[:4])
            )
        declared_groups: dict[str, list[str]] = {}
        for frame_uid, label in declared_structural_family_by_frame_uid.items():
            value = str(label).strip()
            if not value:
                raise TrainingDataInputError("TARGET-DATA2A declared structural-family labels must be non-empty.")
            declared_groups.setdefault(value, []).append(str(frame_uid))
        for label, frame_uids in sorted(declared_groups.items()):
            unit_ids = tuple(sorted({frame_to_unit[uid] for uid in frame_uids}))
            if len(unit_ids) < 2:
                continue
            family_id = digest({
                "schema": "mdstats.target-data-declared-structural-family-id.v1",
                "label": label,
            })
            if policy.reject_declared_structural_family_split:
                _audit_family_roles(
                    "declared_structural",
                    family_id,
                    unit_ids,
                    unit_outer_role=unit_outer_role,
                    cv_plan_by_domain=cv_plan_by_domain,
                    unit_catalog=unit_catalog,
                )
            records.append(TargetDataCorrelationFamilyRecord(
                family_kind="declared_structural",
                family_id=family_id,
                member_unit_ids=unit_ids,
                member_frame_uids=tuple(frame_uids),
                source_label=label,
            ))

    units_by_run: dict[str, set[str]] = {}
    for unit in unit_catalog.units:
        units_by_run.setdefault(unit.run_id, set()).add(unit.unit_id)

    correlation_groups: dict[tuple[str, str], set[str]] = {}
    for source in source_catalog.sources:
        assertions = dict(source.assertions)
        source_units = units_by_run.get(source.run_id, set())
        if not source_units:
            continue
        for key in policy.explicit_correlation_group_assertion_keys:
            if key not in assertions:
                continue
            value = json_value(assertions[key])
            token = digest({
                "schema": "mdstats.target-data-explicit-correlation-family-id.v1",
                "assertion_key": key,
                "assertion_value": value,
            })
            correlation_groups.setdefault((key, token), set()).update(source_units)
    for (key, family_id), unit_ids_set in sorted(correlation_groups.items()):
        unit_ids = tuple(sorted(unit_ids_set))
        if len(unit_ids) < 2:
            continue
        if policy.reject_explicit_correlation_family_split:
            _audit_family_roles(
                "explicit_source_correlation",
                family_id,
                unit_ids,
                unit_outer_role=unit_outer_role,
                cv_plan_by_domain=cv_plan_by_domain,
                unit_catalog=unit_catalog,
            )
        records.append(TargetDataCorrelationFamilyRecord(
            family_kind="explicit_source_correlation",
            family_id=family_id,
            member_unit_ids=unit_ids,
            source_label=key,
        ))

    return tuple(records)


def build_target_data_role_freeze(
    source_catalog: Any,
    frame_catalog: Any,
    data5_bundle: Any,
    *,
    policy: TargetDataRoleFreezePolicy | None = None,
    declared_structural_family_by_frame_uid: Mapping[str, str] | None = None,
    external_challenge_artifact_digests: Sequence[str] = (),
) -> TargetDataRoleFreeze:
    """Freeze the only DATA5 domain authorized to influence ``N_target``.

    ``declared_structural_family_by_frame_uid`` is an optional generic hook for
    a pre-authenticated near-duplicate/structural-family catalog.  The role
    freeze never invents a geometry-similarity tolerance: exact DATA3 geometry
    fingerprints are always checked, while non-exact families must be supplied
    by an explicit upstream policy and become immutable provenance here.
    """

    active = TargetDataRoleFreezePolicy() if policy is None else policy
    if source_catalog.dataset_id != frame_catalog.dataset_id or frame_catalog.dataset_id != data5_bundle.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2A dataset identities disagree.")
    if source_catalog.content_digest != data5_bundle.source_catalog_digest:
        raise TrainingDataInputError("TARGET-DATA2A source/DATA5 lineage mismatch.")
    if frame_catalog.content_digest != data5_bundle.frame_catalog_digest:
        raise TrainingDataInputError("TARGET-DATA2A frame/DATA5 lineage mismatch.")
    if data5_bundle.unit_catalog.policy_digest != data5_bundle.partition_policy.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2A DATA5 partition-policy lineage mismatch.")
    if active.require_passing_data5_leakage_audit and not data5_bundle.leakage_audit.passed:
        raise TrainingDataInputError("TARGET-DATA2A requires a passing DATA5 leakage audit.")
    expected_outer = tuple(sorted(item.content_digest for item in data5_bundle.outer_partitions))
    if tuple(data5_bundle.leakage_audit.outer_partition_digests) != expected_outer:
        raise TrainingDataInputError("TARGET-DATA2A leakage audit does not bind the live outer partitions.")
    expected_cv = tuple(sorted(item.content_digest for item in data5_bundle.cross_validation_plans))
    if tuple(data5_bundle.leakage_audit.cross_validation_plan_digests) != expected_cv:
        raise TrainingDataInputError("TARGET-DATA2A leakage audit does not bind the live CV plans.")

    unit_catalog = data5_bundle.unit_catalog
    outer_by_domain = {item.label_domain_id: item for item in data5_bundle.outer_partitions}
    cv_by_domain = {item.label_domain_id: item for item in data5_bundle.cross_validation_plans}
    domains: list[TargetDataDomainRoleFreeze] = []
    role_fields = (
        (OuterRole.DEVELOPMENT, "size_development"),
        (OuterRole.OUTER_MONITOR, "final_validation"),
        (OuterRole.UNCERTAINTY_CALIBRATION, "uncertainty_calibration"),
        (OuterRole.LOCKED_INTERPOLATION_TEST, "locked_test"),
        (OuterRole.PURGED, "purged"),
        (OuterRole.EXCLUDED, "excluded"),
    )
    for domain_id in unit_catalog.domain_ids:
        outer = outer_by_domain[domain_id]
        cv = cv_by_domain[domain_id]
        if outer.unit_catalog_digest != unit_catalog.content_digest:
            raise TrainingDataInputError("TARGET-DATA2A outer partition does not bind the live unit catalog.")
        if cv.outer_partition_digest != outer.content_digest:
            raise TrainingDataInputError("TARGET-DATA2A CV plan does not bind the live outer partition.")
        if cv.policy_digest != data5_bundle.partition_policy.policy_digest:
            raise TrainingDataInputError("TARGET-DATA2A CV plan does not bind the live partition policy.")
        values: dict[str, tuple[str, ...]] = {}
        frames: dict[str, tuple[str, ...]] = {}
        for role, name in role_fields:
            unit_ids = tuple(outer.units_for(role))
            values[name] = unit_ids
            frames[name] = _frames_for_units(unit_catalog, unit_ids)
        intervals = tuple(
            TargetDevelopmentInterval(
                unit_id=unit.unit_id,
                run_id=unit.run_id,
                label_domain_id=unit.label_domain_id,
                condition_id=unit.condition.condition_id,
                source_frame_start=unit.source_frame_start,
                source_frame_stop=unit.source_frame_stop,
                frame_uids=unit.frame_uids,
            )
            for unit in (unit_catalog.unit(unit_id) for unit_id in values["size_development"])
        )
        domains.append(TargetDataDomainRoleFreeze(
            label_domain_id=domain_id,
            outer_partition_digest=outer.content_digest,
            cross_validation_plan_digest=cv.content_digest,
            size_development_unit_ids=values["size_development"],
            size_development_frame_uids=frames["size_development"],
            final_validation_unit_ids=values["final_validation"],
            final_validation_frame_uids=frames["final_validation"],
            uncertainty_calibration_unit_ids=values["uncertainty_calibration"],
            uncertainty_calibration_frame_uids=frames["uncertainty_calibration"],
            locked_test_unit_ids=values["locked_test"],
            locked_test_frame_uids=frames["locked_test"],
            purged_unit_ids=values["purged"],
            purged_frame_uids=frames["purged"],
            excluded_unit_ids=values["excluded"],
            excluded_frame_uids=frames["excluded"],
            cv_evaluation_unit_ids_by_fold=tuple(
                (fold.fold_index, tuple(fold.evaluation_unit_ids)) for fold in cv.folds
            ),
            cv_checkpoint_monitor_unit_ids_by_fold=tuple(
                (fold.fold_index, tuple(fold.checkpoint_monitor_unit_ids)) for fold in cv.folds
            ),
            development_intervals=intervals,
        ))

    metadata_keys = set(active.lineage_metadata_assertion_keys)
    represented_runs = {unit.run_id for unit in unit_catalog.units}
    source_lineages = tuple(
        TargetDataSourceLineageRecord(
            run_id=source.run_id,
            reference_group=source.reference_group,
            replica_id=source.replica_id,
            reference_run_id=source.reference_run_id,
            lineage_assertions=tuple(
                (key, value) for key, value in source.assertions if key in metadata_keys
            ),
        )
        for source in source_catalog.sources
        if source.run_id in represented_runs
    )
    families = _correlation_family_records(
        source_catalog,
        frame_catalog,
        data5_bundle,
        active,
        declared_structural_family_by_frame_uid,
    )
    result = TargetDataRoleFreeze(
        dataset_id=data5_bundle.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        partition_policy_digest=data5_bundle.partition_policy.policy_digest,
        partition_unit_catalog_digest=unit_catalog.content_digest,
        leakage_audit_digest=data5_bundle.leakage_audit.content_digest,
        policy=active,
        domains=tuple(domains),
        source_lineages=source_lineages,
        correlation_families=families,
        external_challenge_artifact_digests=tuple(external_challenge_artifact_digests),
    )

    # Final fail-closed self-audit: every protected frame must be outside the
    # only domain later code can ask this authority to authenticate.
    authorized = set(result.size_development_frame_uids)
    protected = set()
    for domain in result.domains:
        protected.update(domain.final_validation_frame_uids)
        protected.update(domain.uncertainty_calibration_frame_uids)
        protected.update(domain.locked_test_frame_uids)
        protected.update(domain.purged_frame_uids)
        protected.update(domain.excluded_frame_uids)
    if authorized & protected:
        raise TrainingDataInputError("TARGET-DATA2A protected evidence leaked into size-development authority.")
    return result


__all__ = [name for name in globals() if not name.startswith("_")]
