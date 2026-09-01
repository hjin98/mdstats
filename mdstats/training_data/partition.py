"""MLFF-DATA5 partition feasibility, outer roles, and cross-validation plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math
from typing import Any, Mapping, Sequence

import numpy as np

from mdstats.sampling import (
    AutocorrelationPolicy,
    CompleteFrameBlockPlan,
    CompleteFrameBlockPolicy,
    FrameInterval,
    build_complete_frame_block_plan,
    effective_sample_count,
)

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
    validate_serialized_digest,
)
from .eligibility import FrameEligibilityState
from .profile_extensions import profile_partition_state_changed
from .role_budget import (
    LEGACY_PARTITION_ROLE_BUDGET_POLICY_SCHEMA,
    PARTITION_ROLE_BUDGET_POLICY_SCHEMA,
    PartitionRoleBudgetPolicy,
)

PARTITION_POLICY_SCHEMA = "mdstats.mlff-partition-policy.v2"
LEGACY_PARTITION_POLICY_SCHEMA = "mdstats.mlff-partition-policy.v1"
PARTITION_POLICY_VERSION = "mdstats.mlff-data5.partition.2026-07.v1"
PARTITION_CONDITION_KEY_SCHEMA = "mdstats.partition-condition-key.v1"
PARTITION_UNIT_SCHEMA = "mdstats.partition-unit.v2"
PARTITION_UNIT_CATALOG_SCHEMA = "mdstats.partition-unit-catalog.v1"
PARTITION_FEASIBILITY_REPORT_SCHEMA = "mdstats.partition-feasibility-report.v2"
LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA = "mdstats.partition-feasibility-report.v1"
OUTER_ROLE_ASSIGNMENT_SCHEMA = "mdstats.outer-role-assignment.v1"
OUTER_PARTITION_SCHEMA = "mdstats.outer-partition.v1"
PARTITION_INDEPENDENCE_REPORT_SCHEMA = "mdstats.partition-independence-report.v1"
CROSS_VALIDATION_FOLD_SCHEMA = "mdstats.cross-validation-fold.v1"
CROSS_VALIDATION_PLAN_SCHEMA = "mdstats.cross-validation-plan.v1"


class OuterRole(str, Enum):
    DEVELOPMENT = "development"
    OUTER_MONITOR = "outer_monitor"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"
    LOCKED_INTERPOLATION_TEST = "locked_interpolation_test"
    PURGED = "purged"
    EXCLUDED = "excluded"


class IndependenceGrade(str, Enum):
    INDEPENDENT_REPLICA = "independent_replica"
    INDEPENDENT_STRUCTURAL_REALIZATION = "independent_structural_realization"
    INDEPENDENT_THERMODYNAMIC_RUN = "independent_thermodynamic_run"
    PURGED_TEMPORAL_BLOCK = "purged_temporal_block"
    SLOW_STATE_NOT_DECORRELATED = "slow_state_not_decorrelated"
    INSUFFICIENT_INDEPENDENCE = "insufficient_independence"


class PartitionFeasibilityOutcome(str, Enum):
    FULLY_SUPPORTED = "fully_supported"
    SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY = "supported_with_temporal_blocks_only"
    CALIBRATION_DEFERRED = "calibration_deferred"
    REDUCED_CROSS_VALIDATION_FOLDS = "reduced_cross_validation_folds"
    INSUFFICIENT_FOR_LOCKED_TEST = "insufficient_for_locked_test"
    INSUFFICIENT_FOR_REQUESTED_ROLES = "insufficient_for_requested_roles"


@dataclass(frozen=True, slots=True)
class PartitionPolicy:
    role_budget: PartitionRoleBudgetPolicy = PartitionRoleBudgetPolicy()
    block_policy: CompleteFrameBlockPolicy = CompleteFrameBlockPolicy(
        minimum_block_frames=32,
        autocorrelation_block_multiplier=2.0,
        autocorrelation_policy=AutocorrelationPolicy(),
    )
    accepted_eligibility_states: tuple[str, ...] = (FrameEligibilityState.ELIGIBLE.value,)
    autocorrelation_observables: tuple[str, ...] = (
        "energy_per_atom_ev",
        "force_component_rms_ev_per_angstrom",
        "pressure_ev_per_angstrom3",
        "instantaneous_temperature_kelvin",
        "cell_volume_angstrom3",
    )
    merge_protected_event_windows: bool = True
    require_condition_coverage_in_outer_roles: bool = True
    allow_global_role_fallback: bool = True
    minimum_units_per_condition_for_full_outer_roles: int = 7
    cross_validation_seed: int = 104729
    policy_version: str = PARTITION_POLICY_VERSION
    schema: str = PARTITION_POLICY_SCHEMA
    _legacy_omits_cross_validation_seed: bool = field(
        default=False, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        states = tuple(str(v) for v in self.accepted_eligibility_states)
        if not states or len(set(states)) != len(states):
            raise TrainingDataInputError("accepted_eligibility_states must be non-empty and unique.")
        allowed = {item.value for item in FrameEligibilityState}
        if any(value not in allowed for value in states):
            raise TrainingDataInputError("Unknown accepted eligibility state.")
        observables = tuple(str(v).strip() for v in self.autocorrelation_observables)
        if not observables or any(not value for value in observables) or len(set(observables)) != len(observables):
            raise TrainingDataInputError("autocorrelation_observables must be non-empty and unique.")
        if self.minimum_units_per_condition_for_full_outer_roles < 1:
            raise TrainingDataInputError("minimum_units_per_condition_for_full_outer_roles must be positive.")
        seed = int(self.cross_validation_seed)
        if seed < 0:
            raise TrainingDataInputError("cross_validation_seed must be nonnegative.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        if self.schema not in (PARTITION_POLICY_SCHEMA, LEGACY_PARTITION_POLICY_SCHEMA):
            raise TrainingDataInputError("Unsupported partition-policy schema.")
        object.__setattr__(self, "accepted_eligibility_states", states)
        object.__setattr__(self, "autocorrelation_observables", observables)
        object.__setattr__(self, "cross_validation_seed", seed)

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "policy_version": self.policy_version,
            "role_budget": self.role_budget.to_dict(),
            "block_policy": self.block_policy.to_dict(),
            "accepted_eligibility_states": list(self.accepted_eligibility_states),
            "autocorrelation_observables": list(self.autocorrelation_observables),
            "merge_protected_event_windows": self.merge_protected_event_windows,
            "require_condition_coverage_in_outer_roles": self.require_condition_coverage_in_outer_roles,
            "allow_global_role_fallback": self.allow_global_role_fallback,
            "minimum_units_per_condition_for_full_outer_roles": self.minimum_units_per_condition_for_full_outer_roles,
        }
        if self.schema == LEGACY_PARTITION_POLICY_SCHEMA and not self._legacy_omits_cross_validation_seed:
            payload["cross_validation_seed"] = self.cross_validation_seed
        return payload

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionPolicy":
        schema = payload.get("schema")
        if schema not in (PARTITION_POLICY_SCHEMA, LEGACY_PARTITION_POLICY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported partition-policy schema.")
        result = cls(
            role_budget=PartitionRoleBudgetPolicy.from_dict(payload["role_budget"]),
            block_policy=CompleteFrameBlockPolicy.from_dict(payload["block_policy"]),
            accepted_eligibility_states=tuple(str(v) for v in payload["accepted_eligibility_states"]),
            autocorrelation_observables=tuple(str(v) for v in payload["autocorrelation_observables"]),
            merge_protected_event_windows=bool(payload["merge_protected_event_windows"]),
            require_condition_coverage_in_outer_roles=bool(payload["require_condition_coverage_in_outer_roles"]),
            allow_global_role_fallback=bool(payload["allow_global_role_fallback"]),
            minimum_units_per_condition_for_full_outer_roles=int(payload["minimum_units_per_condition_for_full_outer_roles"]),
            cross_validation_seed=int(payload.get("cross_validation_seed", 104729)),
            policy_version=str(payload["policy_version"]),
            schema=schema,
        )
        if "cross_validation_seed" not in payload and schema == LEGACY_PARTITION_POLICY_SCHEMA:
            object.__setattr__(result, "_legacy_omits_cross_validation_seed", True)
        validate_serialized_digest(
            payload,
            digest_field="policy_digest",
            current_digest=result.policy_digest,
            error_message="Partition-policy digest mismatch.",
        )
        return result


@dataclass(frozen=True, slots=True, order=True)
class PartitionConditionKey:
    label_domain_id: str
    reduced_formula: str
    temperature_condition: str
    strain_class: str
    regime: str
    user_labels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in ("label_domain_id", "reduced_formula", "temperature_condition", "strain_class", "regime"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")
        labels = tuple(sorted((str(k), str(v)) for k, v in self.user_labels))
        if len({key for key, _ in labels}) != len(labels):
            raise TrainingDataInputError("Condition user-label keys must be unique.")
        object.__setattr__(self, "user_labels", labels)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PARTITION_CONDITION_KEY_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reduced_formula": self.reduced_formula,
            "temperature_condition": self.temperature_condition,
            "strain_class": self.strain_class,
            "regime": self.regime,
            "user_labels": dict(self.user_labels),
        }

    @property
    def condition_id(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "condition_id": self.condition_id}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionConditionKey":
        if payload.get("schema") != PARTITION_CONDITION_KEY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported partition-condition-key schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reduced_formula=str(payload["reduced_formula"]),
            temperature_condition=str(payload["temperature_condition"]),
            strain_class=str(payload["strain_class"]),
            regime=str(payload["regime"]),
            user_labels=tuple((str(k), str(v)) for k, v in payload.get("user_labels", {}).items()),
        )
        if payload.get("condition_id") not in (None, result.condition_id):
            raise TrainingDataSerializationError("Partition-condition-key digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PartitionUnit:
    unit_id: str
    run_id: str
    label_domain_id: str
    condition: PartitionConditionKey
    source_frame_start: int
    source_frame_stop: int
    frame_uids: tuple[str, ...]
    block_plan_signature: str
    event_ids: tuple[str, ...]
    contains_protected_event_frames: bool
    maximum_autocorrelation_time_frames: float
    effective_sample_count: float
    replica_id: str | None
    structural_realization_id: str | None
    reference_group: str | None
    independence_grade: IndependenceGrade
    independence_evidence_codes: tuple[str, ...]
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("unit_id", "block_plan_signature"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.run_id.strip() or self.label_domain_id != self.condition.label_domain_id:
            raise TrainingDataInputError("Partition-unit identifiers are inconsistent.")
        if self.source_frame_start < 0 or self.source_frame_stop <= self.source_frame_start:
            raise TrainingDataInputError("Partition-unit interval is invalid.")
        frames = tuple(str(v) for v in self.frame_uids)
        if not frames or len(set(frames)) != len(frames):
            raise TrainingDataInputError("Partition-unit frame UIDs must be non-empty and unique.")
        for uid in frames:
            validate_digest(uid, name="frame_uid")
        events = tuple(sorted(set(str(v) for v in self.event_ids)))
        for event_id in events:
            validate_digest(event_id, name="event_id")
        tau = float(self.maximum_autocorrelation_time_frames)
        n_eff = float(self.effective_sample_count)
        if not np.isfinite(tau) or tau <= 0.0 or not np.isfinite(n_eff) or n_eff <= 0.0:
            raise TrainingDataInputError("Partition-unit sampling diagnostics must be finite and positive.")
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "event_ids", events)
        object.__setattr__(self, "maximum_autocorrelation_time_frames", tau)
        object.__setattr__(self, "effective_sample_count", n_eff)
        object.__setattr__(self, "independence_grade", IndependenceGrade(self.independence_grade))
        object.__setattr__(self, "independence_evidence_codes", tuple(sorted(set(str(v) for v in self.independence_evidence_codes))))

    @property
    def frame_count(self) -> int:
        return len(self.frame_uids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PARTITION_UNIT_SCHEMA,
            "unit_id": self.unit_id,
            "run_id": self.run_id,
            "label_domain_id": self.label_domain_id,
            "condition": self.condition.to_dict(),
            "source_frame_start": self.source_frame_start,
            "source_frame_stop": self.source_frame_stop,
            "frame_uids": list(self.frame_uids),
            "block_plan_signature": self.block_plan_signature,
            "event_ids": list(self.event_ids),
            "contains_protected_event_frames": self.contains_protected_event_frames,
            "maximum_autocorrelation_time_frames": self.maximum_autocorrelation_time_frames,
            "effective_sample_count": self.effective_sample_count,
            "replica_id": self.replica_id,
            "structural_realization_id": self.structural_realization_id,
            "reference_group": self.reference_group,
            "independence_grade": self.independence_grade.value,
            "independence_evidence_codes": list(self.independence_evidence_codes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if not cached:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionUnit":
        if payload.get("schema") != PARTITION_UNIT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported partition-unit schema.")
        grade_value = str(payload["independence_grade"])
        realization = payload.get("structural_realization_id")
        result = cls(
            unit_id=str(payload["unit_id"]),
            run_id=str(payload["run_id"]),
            label_domain_id=str(payload["label_domain_id"]),
            condition=PartitionConditionKey.from_dict(payload["condition"]),
            source_frame_start=int(payload["source_frame_start"]),
            source_frame_stop=int(payload["source_frame_stop"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            block_plan_signature=str(payload["block_plan_signature"]),
            event_ids=tuple(str(v) for v in payload.get("event_ids", ())),
            contains_protected_event_frames=bool(payload["contains_protected_event_frames"]),
            maximum_autocorrelation_time_frames=float(payload["maximum_autocorrelation_time_frames"]),
            effective_sample_count=float(payload["effective_sample_count"]),
            replica_id=None if payload.get("replica_id") is None else str(payload["replica_id"]),
            structural_realization_id=None if realization is None else str(realization),
            reference_group=None if payload.get("reference_group") is None else str(payload["reference_group"]),
            independence_grade=IndependenceGrade(grade_value),
            independence_evidence_codes=tuple(str(v) for v in payload.get("independence_evidence_codes", ())),
        )
        expected = result.content_digest
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Partition-unit digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PartitionUnitCatalog:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    policy_digest: str
    units: tuple[PartitionUnit, ...]
    run_block_plan_signatures: tuple[tuple[str, str], ...]
    _by_unit_id: dict[str, PartitionUnit] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _by_domain_id: dict[str, tuple[PartitionUnit, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _unit_by_frame_uid: dict[str, PartitionUnit] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _domain_ids: tuple[str, ...] = field(
        default=(), init=False, repr=False, compare=False
    )
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("source_catalog_digest", "frame_catalog_digest", "data4_bundle_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        units = tuple(sorted(self.units, key=lambda item: (item.label_domain_id, item.condition.condition_id, item.run_id, item.source_frame_start)))
        if not units or len({item.unit_id for item in units}) != len(units):
            raise TrainingDataInputError("Partition units must be non-empty with unique IDs.")
        frame_uids = [uid for unit in units for uid in unit.frame_uids]
        if len(set(frame_uids)) != len(frame_uids):
            raise TrainingDataInputError("Partition units must not overlap in frame membership.")
        plans = tuple(sorted((str(run_id), validate_digest(sig, name="block_plan_signature")) for run_id, sig in self.run_block_plan_signatures))
        if len({run_id for run_id, _ in plans}) != len(plans):
            raise TrainingDataInputError("Run block-plan signatures must be unique.")
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "run_block_plan_signatures", plans)
        by_domain: dict[str, list[PartitionUnit]] = {}
        unit_by_frame: dict[str, PartitionUnit] = {}
        for unit in units:
            by_domain.setdefault(unit.label_domain_id, []).append(unit)
            for frame_uid in unit.frame_uids:
                unit_by_frame[frame_uid] = unit
        object.__setattr__(self, "_by_unit_id", {item.unit_id: item for item in units})
        object.__setattr__(
            self,
            "_by_domain_id",
            {key: tuple(value) for key, value in by_domain.items()},
        )
        object.__setattr__(self, "_unit_by_frame_uid", unit_by_frame)
        object.__setattr__(self, "_domain_ids", tuple(sorted(by_domain)))

    @property
    def domain_ids(self) -> tuple[str, ...]:
        return self._domain_ids

    def for_domain(self, label_domain_id: str) -> tuple[PartitionUnit, ...]:
        return self._by_domain_id.get(label_domain_id, ())

    def unit(self, unit_id: str) -> PartitionUnit:
        try:
            return self._by_unit_id[unit_id]
        except KeyError:
            raise KeyError(unit_id) from None

    def unit_for_frame(self, frame_uid: str) -> PartitionUnit:
        """Return the unique partition unit containing ``frame_uid`` in O(1)."""

        try:
            return self._unit_by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PARTITION_UNIT_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "policy_digest": self.policy_digest,
            "units": [item.to_dict() for item in self.units],
            "run_block_plan_signatures": dict(self.run_block_plan_signatures),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionUnitCatalog":
        if payload.get("schema") != PARTITION_UNIT_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported partition-unit-catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            policy_digest=str(payload["policy_digest"]),
            units=tuple(PartitionUnit.from_dict(item) for item in payload["units"]),
            run_block_plan_signatures=tuple((str(k), str(v)) for k, v in payload["run_block_plan_signatures"].items()),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Partition-unit-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PartitionFeasibilityReport:
    label_domain_id: str
    policy_digest: str
    unit_catalog_digest: str
    outcome: PartitionFeasibilityOutcome
    available_unit_count: int
    available_condition_count: int
    requested_cross_validation_folds: int = 3
    resolved_cross_validation_folds: int = 3
    calibration_deferred: bool = False
    temporal_blocks_only: bool = False
    per_condition_unit_counts: tuple[tuple[str, int], ...] = ()
    missing_outer_role_conditions: tuple[tuple[str, tuple[str, ...]], ...] = ()
    reason_codes: tuple[str, ...] = ()
    schema: str = PARTITION_FEASIBILITY_REPORT_SCHEMA

    def __post_init__(self) -> None:
        for name in ("policy_digest", "unit_catalog_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.label_domain_id.strip() or self.available_unit_count < 0 or self.available_condition_count < 0:
            raise TrainingDataInputError("Invalid feasibility-report identifiers or counts.")
        if self.requested_cross_validation_folds < 0 or self.resolved_cross_validation_folds < 0:
            raise TrainingDataInputError("Invalid cross-validation fold count.")
        if self.schema not in (PARTITION_FEASIBILITY_REPORT_SCHEMA, LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA):
            raise TrainingDataInputError("Unsupported partition-feasibility-report schema.")
        counts = tuple(sorted((str(key), int(value)) for key, value in self.per_condition_unit_counts))
        if any(value < 0 for _, value in counts):
            raise TrainingDataInputError("Condition unit counts must be nonnegative.")
        missing = tuple(sorted((str(role), tuple(sorted(set(str(v) for v in values)))) for role, values in self.missing_outer_role_conditions))
        object.__setattr__(self, "outcome", PartitionFeasibilityOutcome(self.outcome))
        object.__setattr__(self, "per_condition_unit_counts", counts)
        object.__setattr__(self, "missing_outer_role_conditions", missing)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(str(v) for v in self.reason_codes))))

    @property
    def is_usable(self) -> bool:
        return self.outcome not in {
            PartitionFeasibilityOutcome.INSUFFICIENT_FOR_LOCKED_TEST,
            PartitionFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES,
        }

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "label_domain_id": self.label_domain_id,
            "policy_digest": self.policy_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "outcome": self.outcome.value,
            "available_unit_count": self.available_unit_count,
            "available_condition_count": self.available_condition_count,
            "calibration_deferred": self.calibration_deferred,
            "temporal_blocks_only": self.temporal_blocks_only,
            "per_condition_unit_counts": dict(self.per_condition_unit_counts),
            "missing_outer_role_conditions": {role: list(values) for role, values in self.missing_outer_role_conditions},
            "reason_codes": list(self.reason_codes),
        }
        if self.schema == LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA:
            payload["requested_cross_validation_folds"] = self.requested_cross_validation_folds
            payload["resolved_cross_validation_folds"] = self.resolved_cross_validation_folds
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionFeasibilityReport":
        schema = payload.get("schema")
        if schema not in (PARTITION_FEASIBILITY_REPORT_SCHEMA, LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA):
            raise TrainingDataSerializationError("Unsupported partition-feasibility-report schema.")
        if schema == LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA:
            req_folds = int(payload.get("requested_cross_validation_folds", 3))
            res_folds = int(payload.get("resolved_cross_validation_folds", 3))
        else:
            req_folds = int(payload.get("requested_cross_validation_folds", 0))
            res_folds = int(payload.get("resolved_cross_validation_folds", 0))
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            policy_digest=str(payload["policy_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            outcome=PartitionFeasibilityOutcome(payload["outcome"]),
            available_unit_count=int(payload["available_unit_count"]),
            available_condition_count=int(payload["available_condition_count"]),
            requested_cross_validation_folds=req_folds,
            resolved_cross_validation_folds=res_folds,
            calibration_deferred=bool(payload["calibration_deferred"]),
            temporal_blocks_only=bool(payload["temporal_blocks_only"]),
            per_condition_unit_counts=tuple((str(k), int(v)) for k, v in payload["per_condition_unit_counts"].items()),
            missing_outer_role_conditions=tuple((str(k), tuple(str(v) for v in values)) for k, values in payload["missing_outer_role_conditions"].items()),
            reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
            schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Partition-feasibility-report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class OuterRoleAssignment:
    unit_id: str
    label_domain_id: str
    role: OuterRole
    assignment_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_id", validate_digest(self.unit_id, name="unit_id"))
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("label_domain_id must be non-empty.")
        object.__setattr__(self, "role", OuterRole(self.role))
        object.__setattr__(self, "assignment_reason_codes", tuple(sorted(set(str(v) for v in self.assignment_reason_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OUTER_ROLE_ASSIGNMENT_SCHEMA,
            "unit_id": self.unit_id,
            "label_domain_id": self.label_domain_id,
            "role": self.role.value,
            "assignment_reason_codes": list(self.assignment_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OuterRoleAssignment":
        if payload.get("schema") != OUTER_ROLE_ASSIGNMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported outer-role-assignment schema.")
        result = cls(
            unit_id=str(payload["unit_id"]),
            label_domain_id=str(payload["label_domain_id"]),
            role=OuterRole(payload["role"]),
            assignment_reason_codes=tuple(str(v) for v in payload.get("assignment_reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Outer-role-assignment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class OuterPartition:
    label_domain_id: str
    policy_digest: str
    unit_catalog_digest: str
    feasibility_report_digest: str
    assignments: tuple[OuterRoleAssignment, ...]
    _role_by_unit_id: dict[str, OuterRole] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _unit_ids_by_role: dict[OuterRole, tuple[str, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("policy_digest", "unit_catalog_digest", "feasibility_report_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        assignments = tuple(sorted(self.assignments, key=lambda item: item.unit_id))
        if not assignments or len({item.unit_id for item in assignments}) != len(assignments):
            raise TrainingDataInputError("Outer partition must classify every unit once.")
        if any(item.label_domain_id != self.label_domain_id for item in assignments):
            raise TrainingDataInputError("Outer partition mixes label domains.")
        object.__setattr__(self, "assignments", assignments)
        by_role: dict[OuterRole, list[str]] = {}
        for item in assignments:
            by_role.setdefault(item.role, []).append(item.unit_id)
        object.__setattr__(
            self, "_role_by_unit_id", {item.unit_id: item.role for item in assignments}
        )
        object.__setattr__(
            self,
            "_unit_ids_by_role",
            {role: tuple(unit_ids) for role, unit_ids in by_role.items()},
        )

    def role_for(self, unit_id: str) -> OuterRole:
        try:
            return self._role_by_unit_id[unit_id]
        except KeyError:
            raise KeyError(unit_id) from None

    def units_for(self, role: OuterRole | str) -> tuple[str, ...]:
        target = OuterRole(role)
        return self._unit_ids_by_role.get(target, ())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OUTER_PARTITION_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "policy_digest": self.policy_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "feasibility_report_digest": self.feasibility_report_digest,
            "assignments": [item.to_dict() for item in self.assignments],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if not cached:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OuterPartition":
        if payload.get("schema") != OUTER_PARTITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported outer-partition schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            policy_digest=str(payload["policy_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            feasibility_report_digest=str(payload["feasibility_report_digest"]),
            assignments=tuple(OuterRoleAssignment.from_dict(item) for item in payload["assignments"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Outer-partition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PartitionIndependenceReport:
    label_domain_id: str
    unit_catalog_digest: str
    grade_counts: tuple[tuple[str, int], ...]
    weakest_grade: IndependenceGrade
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_catalog_digest", validate_digest(self.unit_catalog_digest, name="unit_catalog_digest"))
        counts = tuple(sorted((str(k), int(v)) for k, v in self.grade_counts))
        if any(value < 0 for _, value in counts):
            raise TrainingDataInputError("Independence grade counts must be nonnegative.")
        object.__setattr__(self, "grade_counts", counts)
        object.__setattr__(self, "weakest_grade", IndependenceGrade(self.weakest_grade))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PARTITION_INDEPENDENCE_REPORT_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "unit_catalog_digest": self.unit_catalog_digest,
            "grade_counts": dict(self.grade_counts),
            "weakest_grade": self.weakest_grade.value,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionIndependenceReport":
        if payload.get("schema") != PARTITION_INDEPENDENCE_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported partition-independence-report schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            grade_counts=tuple((str(k), int(v)) for k, v in payload["grade_counts"].items()),
            weakest_grade=IndependenceGrade(payload["weakest_grade"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Partition-independence-report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CrossValidationFold:
    fold_index: int
    training_unit_ids: tuple[str, ...]
    checkpoint_monitor_unit_ids: tuple[str, ...]
    evaluation_unit_ids: tuple[str, ...]
    purged_unit_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.fold_index < 0:
            raise TrainingDataInputError("fold_index must be nonnegative.")
        groups = []
        for name in ("training_unit_ids", "checkpoint_monitor_unit_ids", "evaluation_unit_ids", "purged_unit_ids"):
            values = tuple(str(v) for v in getattr(self, name))
            for value in values:
                validate_digest(value, name="unit_id")
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} contains duplicates.")
            object.__setattr__(self, name, values)
            groups.append(set(values))
        if not self.training_unit_ids or not self.checkpoint_monitor_unit_ids or not self.evaluation_unit_ids:
            raise TrainingDataInputError("Every cross-validation fold requires training, checkpoint monitor, and evaluation units.")
        for index, left in enumerate(groups):
            for right in groups[index + 1 :]:
                if left & right:
                    raise TrainingDataInputError("Cross-validation fold roles must be disjoint.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CROSS_VALIDATION_FOLD_SCHEMA,
            "fold_index": self.fold_index,
            "training_unit_ids": list(self.training_unit_ids),
            "checkpoint_monitor_unit_ids": list(self.checkpoint_monitor_unit_ids),
            "evaluation_unit_ids": list(self.evaluation_unit_ids),
            "purged_unit_ids": list(self.purged_unit_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossValidationFold":
        if payload.get("schema") != CROSS_VALIDATION_FOLD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported cross-validation-fold schema.")
        result = cls(
            fold_index=int(payload["fold_index"]),
            training_unit_ids=tuple(str(v) for v in payload["training_unit_ids"]),
            checkpoint_monitor_unit_ids=tuple(str(v) for v in payload["checkpoint_monitor_unit_ids"]),
            evaluation_unit_ids=tuple(str(v) for v in payload["evaluation_unit_ids"]),
            purged_unit_ids=tuple(str(v) for v in payload.get("purged_unit_ids", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Cross-validation-fold digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CrossValidationPlan:
    label_domain_id: str
    policy_digest: str
    outer_partition_digest: str
    resolved_fold_count: int
    folds: tuple[CrossValidationFold, ...]
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("policy_digest", "outer_partition_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        folds = tuple(sorted(self.folds, key=lambda item: item.fold_index))
        if self.resolved_fold_count < 2 or len(folds) != self.resolved_fold_count:
            raise TrainingDataInputError("Cross-validation plan fold count is inconsistent.")
        if tuple(item.fold_index for item in folds) != tuple(range(self.resolved_fold_count)):
            raise TrainingDataInputError("Cross-validation fold indices must be contiguous.")
        evaluation = [unit_id for fold in folds for unit_id in fold.evaluation_unit_ids]
        if len(set(evaluation)) != len(evaluation):
            raise TrainingDataInputError("A development unit may be held out in only one evaluation fold.")
        object.__setattr__(self, "folds", folds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CROSS_VALIDATION_PLAN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "policy_digest": self.policy_digest,
            "outer_partition_digest": self.outer_partition_digest,
            "resolved_fold_count": self.resolved_fold_count,
            "folds": [item.to_dict() for item in self.folds],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if not cached:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossValidationPlan":
        if payload.get("schema") != CROSS_VALIDATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported cross-validation-plan schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            policy_digest=str(payload["policy_digest"]),
            outer_partition_digest=str(payload["outer_partition_digest"]),
            resolved_fold_count=int(payload["resolved_fold_count"]),
            folds=tuple(CrossValidationFold.from_dict(item) for item in payload["folds"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Cross-validation-plan digest mismatch.")
        return result


def _temperature_label(condition: Any) -> str:
    start = condition.target_start_kelvin
    end = condition.target_end_kelvin
    if start is None and end is None:
        return "unresolved"
    if start is None:
        start = end
    if end is None:
        end = start
    assert start is not None and end is not None
    if abs(float(start) - float(end)) <= 1.0e-10:
        return f"{float(start):g}K"
    return f"{float(start):g}-{float(end):g}K"


def _regime_label(source: Any, frame_uid: str, override: Mapping[str, str] | None) -> str:
    if override is not None and frame_uid in override:
        value = str(override[frame_uid]).strip()
        if value:
            return value
    assertions = dict(source.assertions)
    if "regime" in assertions and str(assertions["regime"]).strip():
        return str(assertions["regime"]).strip()
    if source.production_status:
        return str(source.production_status)
    return "unresolved"


def _raw_observable(record: Any, name: str) -> float | None:
    value = getattr(record, name, None)
    if value is None:
        return None
    result = float(value)
    return result if np.isfinite(result) else None


def _merge_intervals_for_events(
    intervals: Sequence[FrameInterval],
    protected_indices_by_event: Sequence[tuple[int, ...]],
) -> tuple[FrameInterval, ...]:
    """Merge block intervals connected by protected event windows.

    The former fixed-point algorithm repeatedly scanned every interval for
    every event and rebuilt the interval list after each merge. In dense event
    campaigns this could grow quadratically or worse. Event windows induce
    connected ranges of adjacent intervals, which can be resolved in one pass
    with a boundary-difference array.
    """

    ordered = tuple(intervals)
    if len(ordered) <= 1 or not protected_indices_by_event:
        return ordered
    starts = np.asarray([item.frame_start for item in ordered], dtype=np.int64)
    stops = np.asarray([item.frame_stop for item in ordered], dtype=np.int64)
    if np.any(starts[1:] < starts[:-1]) or np.any(starts[1:] < stops[:-1]):
        raise TrainingDataInputError(
            "Partition intervals must be sorted and non-overlapping."
        )
    # ``coverage[i] > 0`` means the boundary between interval i and i+1 must
    # disappear because at least one protected event touches both sides.
    difference = np.zeros(len(ordered), dtype=np.int64)
    for indices in protected_indices_by_event:
        if not indices:
            continue
        values = np.asarray(indices, dtype=np.int64)
        positions = np.searchsorted(starts, values, side="right") - 1
        valid = positions >= 0
        if np.any(valid):
            clipped = np.maximum(positions, 0)
            valid &= values < stops[clipped]
        touched = np.unique(positions[valid])
        if touched.size <= 1:
            continue
        first = int(touched[0])
        last = int(touched[-1])
        difference[first] += 1
        difference[last] -= 1
    covered_boundaries = np.cumsum(difference[:-1]) > 0
    result: list[FrameInterval] = []
    start_index = 0
    for boundary, covered in enumerate(covered_boundaries):
        if covered:
            continue
        result.append(
            FrameInterval(
                ordered[start_index].frame_start,
                ordered[boundary].frame_stop,
            )
        )
        start_index = boundary + 1
    result.append(
        FrameInterval(
            ordered[start_index].frame_start, ordered[-1].frame_stop
        )
    )
    return tuple(result)


def _condition_for_frame(
    *,
    source: Any,
    frame: Any,
    frame_catalog: Any,
    strain_record: Any,
    regime_by_frame_uid: Mapping[str, str] | None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None,
) -> PartitionConditionKey:
    temperature = frame_catalog.temperature_conditions.for_run(frame.run_id)
    strain = strain_record
    labels: tuple[tuple[str, str], ...] = ()
    if user_labels_by_frame_uid is not None and frame.frame_uid in user_labels_by_frame_uid:
        labels = tuple((str(k), str(v)) for k, v in user_labels_by_frame_uid[frame.frame_uid].items())
    return PartitionConditionKey(
        label_domain_id=frame.label_domain_id,
        reduced_formula=source.composition.reduced_formula,
        temperature_condition=_temperature_label(temperature),
        strain_class=strain.tensor_class.value,
        regime=_regime_label(source, frame.frame_uid, regime_by_frame_uid),
        user_labels=labels,
    )


def _state_changed_in_run(lta_catalog: Any | None, frame_uids: Sequence[str]) -> bool:
    if lta_catalog is None:
        return False
    for uid in frame_uids:
        record = lta_catalog.for_frame(uid)
        if record.coordination_change or record.site_change or record.ring_crossing:
            return True
    return False


def _split_intervals_by_condition(
    intervals: Sequence[FrameInterval],
    condition_by_source_index: Mapping[int, str],
) -> tuple[FrameInterval, ...]:
    result: list[FrameInterval] = []
    for interval in intervals:
        cursor = interval.frame_start
        while cursor < interval.frame_stop:
            if cursor not in condition_by_source_index:
                cursor += 1
                continue
            condition_id = condition_by_source_index[cursor]
            stop = cursor + 1
            while stop < interval.frame_stop and condition_by_source_index.get(stop) == condition_id:
                stop += 1
            result.append(FrameInterval(cursor, stop))
            cursor = stop
    return tuple(result)


def build_partition_unit_catalog(
    source_catalog: Any,
    frame_catalog: Any,
    data4_bundle: Any,
    *,
    policy: PartitionPolicy | None = None,
    regime_by_frame_uid: Mapping[str, str] | None = None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None = None,
) -> PartitionUnitCatalog:
    active = PartitionPolicy() if policy is None else policy
    if source_catalog.content_digest != data4_bundle.source_catalog_digest:
        raise TrainingDataInputError("DATA5 source catalog does not match DATA4.")
    if frame_catalog.content_digest != data4_bundle.frame_catalog_digest:
        raise TrainingDataInputError("DATA5 frame catalog does not match DATA4.")

    frame_map = {item.frame_uid: item for item in frame_catalog.frames}
    raw_map = {item.frame_uid: item for item in data4_bundle.raw_features.records}
    eligibility_map = {item.frame_uid: item for item in frame_catalog.eligibility.decisions}
    strain_by_uid = {item.frame_uid: item for item in frame_catalog.strain_records}
    event_by_run: dict[str, list[Any]] = {}
    for event in data4_bundle.events.events:
        event_by_run.setdefault(event.run_id, []).append(event)
    # Index protected-event membership once.  The former interval loop scanned
    # every event and rebuilt the interval frame set inside the predicate,
    # yielding O(I * E * M) work for I intervals, E events, and M member
    # frames.  The index makes matching proportional to actual frame/event
    # memberships plus matched events.
    event_ordinals_by_frame_by_run: dict[str, dict[str, tuple[int, ...]]] = {}
    for run_id, run_events in event_by_run.items():
        ordinals_by_frame: dict[str, list[int]] = {}
        for event_ordinal, event in enumerate(run_events):
            for frame_uid in event.protected_frame_uids:
                ordinals_by_frame.setdefault(frame_uid, []).append(event_ordinal)
        event_ordinals_by_frame_by_run[run_id] = {
            frame_uid: tuple(ordinals)
            for frame_uid, ordinals in ordinals_by_frame.items()
        }
    frames_by_run: dict[str, list[Any]] = {}
    for frame in frame_catalog.frames:
        frames_by_run.setdefault(frame.run_id, []).append(frame)
    for run_frames in frames_by_run.values():
        run_frames.sort(key=lambda item: item.source_frame_index)

    units: list[PartitionUnit] = []
    run_plan_signatures: list[tuple[str, str]] = []
    accepted = set(active.accepted_eligibility_states)
    condition_by_uid: dict[str, PartitionConditionKey] = {}
    for frame in frame_catalog.frames:
        if eligibility_map[frame.frame_uid].state.value not in accepted:
            continue
        source = source_catalog.source(frame.run_id)
        condition_by_uid[frame.frame_uid] = _condition_for_frame(
            source=source,
            frame=frame,
            frame_catalog=frame_catalog,
            strain_record=strain_by_uid[frame.frame_uid],
            regime_by_frame_uid=regime_by_frame_uid,
            user_labels_by_frame_uid=user_labels_by_frame_uid,
        )
    condition_runs: dict[str, set[str]] = {}
    condition_replicas: dict[str, set[str]] = {}
    condition_structural_realizations: dict[str, set[str]] = {}
    for uid, condition in condition_by_uid.items():
        frame = frame_map[uid]
        source = source_catalog.source(frame.run_id)
        condition_runs.setdefault(condition.condition_id, set()).add(frame.run_id)
        if source.replica_id is not None:
            condition_replicas.setdefault(condition.condition_id, set()).add(source.replica_id)
        assertions = dict(source.assertions)
        realization_id = assertions.get("structural_realization_id")
        if realization_id is not None and str(realization_id).strip():
            condition_structural_realizations.setdefault(condition.condition_id, set()).add(str(realization_id).strip())

    for source in source_catalog.sources:
        run_frames = frames_by_run.get(source.run_id, ())
        eligible = [
            item
            for item in run_frames
            if eligibility_map[item.frame_uid].state.value in accepted
        ]
        if not eligible:
            continue
        eligible_indices = np.asarray([item.source_frame_index for item in eligible], dtype=np.int64)
        maximum_index = int(max(item.source_frame_index for item in run_frames))
        observables: dict[str, np.ndarray] = {}
        for name in active.autocorrelation_observables:
            vector = np.full(maximum_index + 1, np.nan, dtype=np.float64)
            complete = True
            for item in eligible:
                value = _raw_observable(raw_map[item.frame_uid], name)
                if value is None:
                    complete = False
                    break
                vector[item.source_frame_index] = value
            if complete:
                observables[name] = vector
        if not observables:
            vector = np.full(maximum_index + 1, np.nan, dtype=np.float64)
            for item in eligible:
                vector[item.source_frame_index] = raw_map[item.frame_uid].cell_volume_angstrom3
            observables["cell_volume_angstrom3"] = vector
        plan = build_complete_frame_block_plan(
            eligible_frame_indices=eligible_indices,
            frame_observables=observables,
            policy=active.block_policy,
        )
        run_plan_signatures.append((source.run_id, plan.signature))
        condition_by_source_index = {
            item.source_frame_index: condition_by_uid[item.frame_uid].condition_id
            for item in eligible
        }
        intervals = _split_intervals_by_condition(plan.block_intervals, condition_by_source_index)
        protected_by_event: list[tuple[int, ...]] = []
        if active.merge_protected_event_windows:
            for event in event_by_run.get(source.run_id, []):
                indices = tuple(frame_map[uid].source_frame_index for uid in event.protected_frame_uids)
                event_conditions = {condition_by_source_index.get(index) for index in indices}
                event_conditions.discard(None)
                if len(event_conditions) > 1:
                    raise TrainingDataInputError(
                        "A protected event window crosses a declared condition boundary."
                    )
                protected_by_event.append(indices)
            intervals = _merge_intervals_for_events(intervals, protected_by_event)

        same_run_uids = tuple(item.frame_uid for item in eligible)
        state_changed = profile_partition_state_changed(tuple(getattr(data4_bundle, "profile_partition_features", ())), same_run_uids)

        for interval in intervals:
            left = int(np.searchsorted(
                eligible_indices, interval.frame_start, side="left"
            ))
            right = int(np.searchsorted(
                eligible_indices, interval.frame_stop, side="left"
            ))
            member_frames = tuple(eligible[left:right])
            if not member_frames:
                continue
            conditions = {condition_by_uid[item.frame_uid] for item in member_frames}
            if len(conditions) != 1:
                raise TrainingDataInputError(
                    "A partition unit crosses a condition boundary; provide a regime override or smaller block policy."
                )
            condition = next(iter(conditions))
            run_events = event_by_run.get(source.run_id, [])
            ordinals_by_frame = event_ordinals_by_frame_by_run.get(source.run_id, {})
            matched_event_ordinals: set[int] = set()
            for member in member_frames:
                matched_event_ordinals.update(
                    ordinals_by_frame.get(member.frame_uid, ())
                )
            events = tuple(
                run_events[event_ordinal]
                for event_ordinal in sorted(matched_event_ordinals)
            )
            replica_ids = condition_replicas.get(condition.condition_id, set())
            realization_ids = condition_structural_realizations.get(condition.condition_id, set())
            assertions = dict(source.assertions)
            source_structural_realization_id = assertions.get("structural_realization_id")
            if source_structural_realization_id is not None and str(source_structural_realization_id).strip():
                source_structural_realization_id = str(source_structural_realization_id).strip()
            else:
                source_structural_realization_id = None
            condition_run_count = len(condition_runs.get(condition.condition_id, set()))
            if source.replica_id is not None and len(replica_ids) >= 2:
                grade = IndependenceGrade.INDEPENDENT_REPLICA
                evidence = ("multiple_replica_ids_for_exact_condition",)
            elif source_structural_realization_id is not None and len(realization_ids) >= 2:
                grade = IndependenceGrade.INDEPENDENT_STRUCTURAL_REALIZATION
                evidence = ("multiple_structural_realizations_for_exact_condition",)
            elif condition_run_count >= 2:
                grade = IndependenceGrade.INDEPENDENT_THERMODYNAMIC_RUN
                evidence = ("multiple_source_runs_for_composition_domain",)
            elif getattr(data4_bundle, "profile_partition_features", ()) and not state_changed:
                grade = IndependenceGrade.SLOW_STATE_NOT_DECORRELATED
                evidence = ("single_run_no_observed_profile_state_transition",)
            elif len(intervals) >= 2:
                grade = IndependenceGrade.PURGED_TEMPORAL_BLOCK
                evidence = ("single_run_autocorrelation_aware_temporal_block",)
            else:
                grade = IndependenceGrade.INSUFFICIENT_INDEPENDENCE
                evidence = ("single_indivisible_unit",)
            frame_uids = tuple(item.frame_uid for item in member_frames)
            unit_payload = {
                "run_id": source.run_id,
                "frame_uids": list(frame_uids),
                "condition_id": condition.condition_id,
                "block_plan_signature": plan.signature,
            }
            units.append(
                PartitionUnit(
                    unit_id=digest(unit_payload),
                    run_id=source.run_id,
                    label_domain_id=str(source.label_domain_id),
                    condition=condition,
                    source_frame_start=interval.frame_start,
                    source_frame_stop=interval.frame_stop,
                    frame_uids=frame_uids,
                    block_plan_signature=plan.signature,
                    event_ids=tuple(event.event_id for event in events),
                    contains_protected_event_frames=bool(events),
                    maximum_autocorrelation_time_frames=plan.maximum_autocorrelation_time_frames,
                    effective_sample_count=effective_sample_count(
                        len(frame_uids),
                        plan.maximum_autocorrelation_time_frames,
                    ),
                    replica_id=source.replica_id,
                    structural_realization_id=source_structural_realization_id,
                    reference_group=source.reference_group,
                    independence_grade=grade,
                    independence_evidence_codes=evidence,
                )
            )
    if not units:
        raise TrainingDataInputError("No eligible frames remain for DATA5 partitioning.")
    return PartitionUnitCatalog(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        policy_digest=active.policy_digest,
        units=tuple(units),
        run_block_plan_signatures=tuple(run_plan_signatures),
    )


def assess_partition_feasibility(
    unit_catalog: PartitionUnitCatalog,
    *,
    policy: PartitionPolicy | None = None,
) -> tuple[PartitionFeasibilityReport, ...]:
    active = PartitionPolicy() if policy is None else policy
    if unit_catalog.policy_digest != active.policy_digest:
        raise TrainingDataInputError("Unit catalog and feasibility policy differ.")
    reports: list[PartitionFeasibilityReport] = []
    for domain_id in unit_catalog.domain_ids:
        units = unit_catalog.for_domain(domain_id)
        groups: dict[str, list[PartitionUnit]] = {}
        for unit in units:
            groups.setdefault(unit.condition.condition_id, []).append(unit)
        counts = tuple((key, len(value)) for key, value in groups.items())
        budget = active.role_budget
        minimum_total = (
            budget.development_minimum_independent_units
            + budget.outer_monitor_minimum_independent_units
            + budget.calibration_minimum_independent_units
            + budget.locked_interpolation_test_minimum_independent_units
        )
        reason_codes: list[str] = []
        missing: dict[str, list[str]] = {
            OuterRole.OUTER_MONITOR.value: [],
            OuterRole.UNCERTAINTY_CALIBRATION.value: [],
            OuterRole.LOCKED_INTERPOLATION_TEST.value: [],
        }
        if active.require_condition_coverage_in_outer_roles:
            for condition_id, group in groups.items():
                if len(group) < active.minimum_units_per_condition_for_full_outer_roles:
                    for role in missing:
                        missing[role].append(condition_id)
        temporal_only = all(
            unit.independence_grade
            in {
                IndependenceGrade.PURGED_TEMPORAL_BLOCK,
                IndependenceGrade.SLOW_STATE_NOT_DECORRELATED,
                IndependenceGrade.INSUFFICIENT_INDEPENDENCE,
            }
            for unit in units
        )
        calibration_deferred = False
        if budget.schema == LEGACY_PARTITION_ROLE_BUDGET_POLICY_SCHEMA:
            requested_folds = budget.cross_validation_folds
            resolved_folds = min(budget.cross_validation_folds, max(0, len(units) - 3))
            if len(units) < minimum_total:
                if budget.allow_calibration_deferral and len(units) >= minimum_total - budget.calibration_minimum_independent_units:
                    calibration_deferred = True
                    reason_codes.append("calibration_deferred_for_role_budget")
                    outcome = PartitionFeasibilityOutcome.CALIBRATION_DEFERRED
                elif len(units) < budget.locked_interpolation_test_minimum_independent_units + budget.development_minimum_independent_units:
                    outcome = PartitionFeasibilityOutcome.INSUFFICIENT_FOR_LOCKED_TEST
                    reason_codes.append("insufficient_units_for_development_and_locked_test")
                else:
                    outcome = PartitionFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES
                    reason_codes.append("insufficient_units_for_requested_outer_roles")
            elif resolved_folds < 2:
                outcome = PartitionFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES
                reason_codes.append("insufficient_units_for_cross_validation")
            elif resolved_folds < budget.cross_validation_folds:
                outcome = PartitionFeasibilityOutcome.REDUCED_CROSS_VALIDATION_FOLDS
                reason_codes.append("cross_validation_fold_count_reduced")
            elif temporal_only:
                outcome = PartitionFeasibilityOutcome.SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY
                reason_codes.append("no_independent_replica_or_run_support")
            elif any(missing.values()):
                outcome = PartitionFeasibilityOutcome.SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY
                reason_codes.append("not_all_conditions_support_all_outer_roles")
            else:
                outcome = PartitionFeasibilityOutcome.FULLY_SUPPORTED
            report_schema = LEGACY_PARTITION_FEASIBILITY_REPORT_SCHEMA
        else:
            requested_folds = 0
            resolved_folds = 0
            if len(units) < minimum_total:
                if budget.allow_calibration_deferral and len(units) >= minimum_total - budget.calibration_minimum_independent_units:
                    calibration_deferred = True
                    reason_codes.append("calibration_deferred_for_role_budget")
                    outcome = PartitionFeasibilityOutcome.CALIBRATION_DEFERRED
                elif len(units) < budget.locked_interpolation_test_minimum_independent_units + budget.development_minimum_independent_units:
                    outcome = PartitionFeasibilityOutcome.INSUFFICIENT_FOR_LOCKED_TEST
                    reason_codes.append("insufficient_units_for_development_and_locked_test")
                else:
                    outcome = PartitionFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES
                    reason_codes.append("insufficient_units_for_requested_outer_roles")
            elif temporal_only:
                outcome = PartitionFeasibilityOutcome.SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY
                reason_codes.append("no_independent_replica_or_run_support")
            elif any(missing.values()):
                outcome = PartitionFeasibilityOutcome.SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY
                reason_codes.append("not_all_conditions_support_all_outer_roles")
            else:
                outcome = PartitionFeasibilityOutcome.FULLY_SUPPORTED
            report_schema = PARTITION_FEASIBILITY_REPORT_SCHEMA
        reports.append(
            PartitionFeasibilityReport(
                label_domain_id=domain_id,
                policy_digest=active.policy_digest,
                unit_catalog_digest=unit_catalog.content_digest,
                outcome=outcome,
                available_unit_count=len(units),
                available_condition_count=len(groups),
                requested_cross_validation_folds=requested_folds,
                resolved_cross_validation_folds=max(0, resolved_folds),
                calibration_deferred=calibration_deferred,
                temporal_blocks_only=temporal_only,
                per_condition_unit_counts=counts,
                missing_outer_role_conditions=tuple((role, tuple(values)) for role, values in missing.items()),
                reason_codes=tuple(reason_codes),
                schema=report_schema,
            )
        )
    return tuple(reports)


def _spaced_indices(count: int, number: int) -> tuple[int, ...]:
    if number <= 0:
        return ()
    if count < number:
        raise TrainingDataInputError("Not enough units for requested spaced indices.")
    if number == 1:
        return (count - 1,)
    raw = np.linspace(0, count - 1, number + 2, dtype=float)[1:-1]
    result: list[int] = []
    for value in raw:
        candidate = int(round(float(value)))
        while candidate in result and candidate + 1 < count:
            candidate += 1
        while candidate in result and candidate - 1 >= 0:
            candidate -= 1
        result.append(candidate)
    return tuple(sorted(result))


def _neighbor_unit_ids(
    units: Sequence[PartitionUnit],
    selected_ids: set[str],
    radius: int,
    *,
    temporal_index: tuple[
        Mapping[str, tuple[PartitionUnit, ...]],
        Mapping[str, tuple[str, int]],
    ] | None = None,
) -> set[str]:
    if radius <= 0 or not selected_ids:
        return set()
    if temporal_index is None:
        temporal_index = _build_temporal_neighbor_index(units)
    ordered_by_run, location_by_unit = temporal_index
    purged: set[str] = set()
    for unit_id in selected_ids:
        try:
            run_id, position = location_by_unit[unit_id]
        except KeyError:
            continue
        ordered = ordered_by_run[run_id]
        first = max(0, position - radius)
        last = min(len(ordered), position + radius + 1)
        purged.update(item.unit_id for item in ordered[first:last])
    return purged - selected_ids


def _build_temporal_neighbor_index(
    units: Sequence[PartitionUnit],
) -> tuple[
    dict[str, tuple[PartitionUnit, ...]],
    dict[str, tuple[str, int]],
]:
    """Index temporal unit positions once for repeated purge queries.

    Cross-validation previously regrouped and resorted every development unit
    for both evaluation and monitor purges in every fold, then rescanned every
    unit to find selected anchors.  The immutable index reduces construction
    to one ``O(U log U)`` pass and each query to ``O(S * radius)`` where ``S``
    is the selected anchor count.
    """

    grouped: dict[str, list[PartitionUnit]] = {}
    for unit in units:
        grouped.setdefault(unit.run_id, []).append(unit)
    ordered_by_run = {
        run_id: tuple(sorted(run_units, key=lambda item: item.source_frame_start))
        for run_id, run_units in grouped.items()
    }
    location_by_unit = {
        unit.unit_id: (run_id, position)
        for run_id, ordered in ordered_by_run.items()
        for position, unit in enumerate(ordered)
    }
    return ordered_by_run, location_by_unit


def build_outer_partitions(
    unit_catalog: PartitionUnitCatalog,
    feasibility_reports: Sequence[PartitionFeasibilityReport],
    *,
    policy: PartitionPolicy | None = None,
) -> tuple[OuterPartition, ...]:
    active = PartitionPolicy() if policy is None else policy
    report_map = {item.label_domain_id: item for item in feasibility_reports}
    partitions: list[OuterPartition] = []
    for domain_id in unit_catalog.domain_ids:
        report = report_map[domain_id]
        if not report.is_usable:
            raise TrainingDataInputError(
                f"Label domain {domain_id} is not feasible for outer partitioning: {report.outcome.value}."
            )
        units = list(unit_catalog.for_domain(domain_id))
        temporal_index = _build_temporal_neighbor_index(units)
        groups: dict[str, list[PartitionUnit]] = {}
        for unit in units:
            groups.setdefault(unit.condition.condition_id, []).append(unit)
        selected: dict[OuterRole, set[str]] = {
            OuterRole.LOCKED_INTERPOLATION_TEST: set(),
            OuterRole.UNCERTAINTY_CALIBRATION: set(),
            OuterRole.OUTER_MONITOR: set(),
        }
        for condition_id in sorted(groups):
            group = sorted(groups[condition_id], key=lambda item: (item.run_id, item.source_frame_start))
            role_sequence = [OuterRole.OUTER_MONITOR]
            if not report.calibration_deferred:
                role_sequence.append(OuterRole.UNCERTAINTY_CALIBRATION)
            role_sequence.append(OuterRole.LOCKED_INTERPOLATION_TEST)
            if active.require_condition_coverage_in_outer_roles and len(group) >= active.minimum_units_per_condition_for_full_outer_roles:
                positions = _spaced_indices(len(group), len(role_sequence))
                for role, position in zip(role_sequence, positions, strict=True):
                    selected[role].add(group[position].unit_id)
        budget = active.role_budget
        minima = {
            OuterRole.OUTER_MONITOR: budget.outer_monitor_minimum_independent_units,
            OuterRole.UNCERTAINTY_CALIBRATION: 0 if report.calibration_deferred else budget.calibration_minimum_independent_units,
            OuterRole.LOCKED_INTERPOLATION_TEST: budget.locked_interpolation_test_minimum_independent_units,
        }
        occupied = set().union(*selected.values())
        if active.allow_global_role_fallback:
            candidates = [unit for unit in units if unit.unit_id not in occupied]
            candidates.sort(key=lambda item: (item.condition.condition_id, item.run_id, item.source_frame_start))
            for role in (OuterRole.LOCKED_INTERPOLATION_TEST, OuterRole.UNCERTAINTY_CALIBRATION, OuterRole.OUTER_MONITOR):
                while len(selected[role]) < minima[role]:
                    if not candidates:
                        raise TrainingDataInputError(f"Unable to satisfy minimum support for {role.value}.")
                    unit = candidates.pop()
                    selected[role].add(unit.unit_id)
                    occupied.add(unit.unit_id)
        purge_ids = _neighbor_unit_ids(
            units,
            occupied,
            budget.purge_units_between_roles,
            temporal_index=temporal_index,
        )
        purge_ids -= occupied
        assignments: list[OuterRoleAssignment] = []
        for unit in units:
            if unit.unit_id in selected[OuterRole.LOCKED_INTERPOLATION_TEST]:
                role = OuterRole.LOCKED_INTERPOLATION_TEST
                reasons = ("deterministic_locked_test_anchor",)
            elif unit.unit_id in selected[OuterRole.UNCERTAINTY_CALIBRATION]:
                role = OuterRole.UNCERTAINTY_CALIBRATION
                reasons = ("deterministic_calibration_anchor",)
            elif unit.unit_id in selected[OuterRole.OUTER_MONITOR]:
                role = OuterRole.OUTER_MONITOR
                reasons = ("deterministic_outer_monitor_anchor",)
            elif unit.unit_id in purge_ids:
                role = OuterRole.PURGED
                reasons = ("same_run_neighbor_of_outer_evidence",)
            else:
                role = OuterRole.DEVELOPMENT
                reasons = ("remaining_eligible_development_unit",)
            assignments.append(
                OuterRoleAssignment(
                    unit_id=unit.unit_id,
                    label_domain_id=domain_id,
                    role=role,
                    assignment_reason_codes=reasons,
                )
            )
        development_count = sum(item.role is OuterRole.DEVELOPMENT for item in assignments)
        if development_count < budget.development_minimum_independent_units:
            raise TrainingDataInputError(
                f"Outer-role purge leaves only {development_count} development units; "
                f"minimum is {budget.development_minimum_independent_units}."
            )
        partitions.append(
            OuterPartition(
                label_domain_id=domain_id,
                policy_digest=active.policy_digest,
                unit_catalog_digest=unit_catalog.content_digest,
                feasibility_report_digest=report.content_digest,
                assignments=tuple(assignments),
            )
        )
    return tuple(partitions)


def build_independence_reports(
    unit_catalog: PartitionUnitCatalog,
) -> tuple[PartitionIndependenceReport, ...]:
    order = {
        IndependenceGrade.INDEPENDENT_REPLICA: 0,
        IndependenceGrade.INDEPENDENT_STRUCTURAL_REALIZATION: 1,
        IndependenceGrade.INDEPENDENT_THERMODYNAMIC_RUN: 2,
        IndependenceGrade.PURGED_TEMPORAL_BLOCK: 3,
        IndependenceGrade.SLOW_STATE_NOT_DECORRELATED: 4,
        IndependenceGrade.INSUFFICIENT_INDEPENDENCE: 5,
    }
    reports: list[PartitionIndependenceReport] = []
    for domain_id in unit_catalog.domain_ids:
        units = unit_catalog.for_domain(domain_id)
        counts: dict[str, int] = {}
        for unit in units:
            counts[unit.independence_grade.value] = counts.get(unit.independence_grade.value, 0) + 1
        weakest = max((unit.independence_grade for unit in units), key=lambda item: order[item])
        notes = ()
        if weakest in {IndependenceGrade.SLOW_STATE_NOT_DECORRELATED, IndependenceGrade.INSUFFICIENT_INDEPENDENCE}:
            notes = ("At least one condition lacks demonstrated slow-state independence.",)
        reports.append(
            PartitionIndependenceReport(
                label_domain_id=domain_id,
                unit_catalog_digest=unit_catalog.content_digest,
                grade_counts=tuple(counts.items()),
                weakest_grade=weakest,
                notes=notes,
            )
        )
    return tuple(reports)


def _seeded_unit_order(
    units: Sequence[PartitionUnit],
    *,
    seed: int,
    condition_id: str,
) -> list[PartitionUnit]:
    """Return a platform-independent pseudo-random unit order.

    Python's process-randomized ``hash`` and NumPy RNG implementation details
    are deliberately avoided.  The ordering is a pure SHA-256 function of the
    configured seed, condition identity, and immutable unit identity.
    """

    def key(unit: PartitionUnit) -> tuple[bytes, str]:
        token = f"{int(seed)}\0{condition_id}\0{unit.unit_id}".encode("utf-8")
        return hashlib.sha256(token).digest(), unit.unit_id

    return sorted(units, key=key)


def _assign_evaluation_folds(
    units: Sequence[PartitionUnit],
    fold_count: int,
    *,
    seed: int,
) -> list[list[PartitionUnit]]:
    folds: list[list[PartitionUnit]] = [[] for _ in range(fold_count)]
    groups: dict[str, list[PartitionUnit]] = {}
    for unit in units:
        groups.setdefault(unit.condition.condition_id, []).append(unit)
    offset = 0
    for condition_id in sorted(groups):
        ordered = _seeded_unit_order(
            groups[condition_id], seed=seed, condition_id=condition_id
        )
        for index, unit in enumerate(ordered):
            folds[(offset + index) % fold_count].append(unit)
        offset = (offset + len(ordered)) % fold_count
    return folds


def _select_checkpoint_monitor(
    candidates: Sequence[PartitionUnit],
    count: int,
) -> tuple[PartitionUnit, ...]:
    if count < 1 or len(candidates) < count:
        return ()
    ordered = sorted(candidates, key=lambda item: (item.condition.condition_id, item.run_id, item.source_frame_start))
    indices = _spaced_indices(len(ordered), count)
    return tuple(ordered[index] for index in indices)


def build_cross_validation_plans(
    unit_catalog: PartitionUnitCatalog,
    outer_partitions: Sequence[OuterPartition],
    feasibility_reports: Sequence[PartitionFeasibilityReport],
    *,
    policy: PartitionPolicy | None = None,
    fold_count_override: int | None = None,
    fold_seed_override: int | None = None,
) -> tuple[CrossValidationPlan, ...]:
    active = PartitionPolicy() if policy is None else policy
    report_map = {item.label_domain_id: item for item in feasibility_reports}
    outer_map = {item.label_domain_id: item for item in outer_partitions}
    plans: list[CrossValidationPlan] = []
    for domain_id, outer in sorted(outer_map.items()):
        development = [unit_catalog.unit(unit_id) for unit_id in outer.units_for(OuterRole.DEVELOPMENT)]
        temporal_index = _build_temporal_neighbor_index(development)
        report = report_map[domain_id]
        if fold_count_override is None:
            max_avail = report.resolved_cross_validation_folds or min(
                active.role_budget.cross_validation_folds, max(0, len(development) - 3)
            )
            fold_count = min(max_avail, len(development))
        else:
            requested_override = int(fold_count_override)
            if requested_override < 2:
                raise TrainingDataInputError(
                    "Cross-validation fold override must be at least two."
                )
            limit = report.resolved_cross_validation_folds or len(development)
            if requested_override > limit:
                raise TrainingDataInputError(
                    f"Requested {requested_override} cross-validation folds for "
                    f"{domain_id}, but DATA5 supports only {limit}."
                )
            fold_count = requested_override
        if fold_count < 2:
            raise TrainingDataInputError("Cross-validation requires at least two development units and folds.")
        evaluation_groups = _assign_evaluation_folds(
            development,
            fold_count,
            seed=(
                active.cross_validation_seed
                if fold_seed_override is None
                else int(fold_seed_override)
            ),
        )
        if any(not group for group in evaluation_groups):
            raise TrainingDataInputError("Every cross-validation fold requires evaluation support.")
        folds: list[CrossValidationFold] = []
        all_ids = {unit.unit_id for unit in development}
        for fold_index, evaluation_units in enumerate(evaluation_groups):
            evaluation_ids = {unit.unit_id for unit in evaluation_units}
            purge_ids = _neighbor_unit_ids(
                development,
                evaluation_ids,
                active.role_budget.purge_units_between_roles,
                temporal_index=temporal_index,
            )
            candidate_ids = all_ids - evaluation_ids - purge_ids
            candidates = [unit_catalog.unit(unit_id) for unit_id in sorted(candidate_ids)]
            monitor_units = _select_checkpoint_monitor(
                candidates,
                active.role_budget.checkpoint_monitor_minimum_units_per_fold,
            )
            if not monitor_units:
                raise TrainingDataInputError(
                    f"Fold {fold_index} lacks a nested checkpoint monitor."
                )
            monitor_ids = {unit.unit_id for unit in monitor_units}
            monitor_purge = _neighbor_unit_ids(
                development,
                monitor_ids,
                active.role_budget.purge_units_between_roles,
                temporal_index=temporal_index,
            ) - evaluation_ids
            purge_ids |= monitor_purge
            training_ids = all_ids - evaluation_ids - monitor_ids - purge_ids
            if not training_ids:
                raise TrainingDataInputError(
                    f"Fold {fold_index} has no training units after nested monitor and purge."
                )
            folds.append(
                CrossValidationFold(
                    fold_index=fold_index,
                    training_unit_ids=tuple(sorted(training_ids)),
                    checkpoint_monitor_unit_ids=tuple(sorted(monitor_ids)),
                    evaluation_unit_ids=tuple(sorted(evaluation_ids)),
                    purged_unit_ids=tuple(sorted(purge_ids)),
                )
            )
        plans.append(
            CrossValidationPlan(
                label_domain_id=domain_id,
                policy_digest=active.policy_digest,
                outer_partition_digest=outer.content_digest,
                resolved_fold_count=fold_count,
                folds=tuple(folds),
            )
        )
    return tuple(plans)
