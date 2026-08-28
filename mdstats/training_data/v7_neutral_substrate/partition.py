"""V7 neutral correlation/statistical substrate without compatibility domains or CV."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from mdstats.sampling import (
    AutocorrelationPolicy,
    CompleteFrameBlockPolicy,
    build_complete_frame_block_plan,
    effective_sample_count,
)

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..eligibility import FrameEligibilityState
from ..partition import (
    IndependenceGrade,
    OuterRole,
    _build_temporal_neighbor_index,
    _merge_intervals_for_events,
    _neighbor_unit_ids,
    _raw_observable,
    _regime_label,
    _spaced_indices,
    _split_intervals_by_condition,
    _temperature_label,
)
from ..profile_extensions import profile_partition_state_changed

V7_NEUTRAL_ROLE_BUDGET_SCHEMA = "mdstats.v7-neutral-role-budget.v1"
V7_NEUTRAL_PARTITION_POLICY_SCHEMA = "mdstats.v7-neutral-partition-policy.v1"
V7_NEUTRAL_PARTITION_POLICY_VERSION = "mdstats.v7-neutral-partition.2026-08.v1"
V7_NEUTRAL_CONDITION_KEY_SCHEMA = "mdstats.v7-neutral-partition-condition.v1"
V7_NEUTRAL_UNIT_SCHEMA = "mdstats.v7-neutral-partition-unit.v1"
V7_NEUTRAL_UNIT_CATALOG_SCHEMA = "mdstats.v7-neutral-partition-unit-catalog.v1"
V7_NEUTRAL_FEASIBILITY_SCHEMA = "mdstats.v7-neutral-partition-feasibility.v1"
V7_NEUTRAL_ROLE_ASSIGNMENT_SCHEMA = "mdstats.v7-neutral-outer-role-assignment.v1"
V7_NEUTRAL_OUTER_PARTITION_SCHEMA = "mdstats.v7-neutral-outer-partition.v1"
V7_NEUTRAL_INDEPENDENCE_SCHEMA = "mdstats.v7-neutral-independence-report.v1"
V7_NEUTRAL_LEAKAGE_FINDING_SCHEMA = "mdstats.v7-neutral-leakage-finding.v1"
V7_NEUTRAL_LEAKAGE_REPORT_SCHEMA = "mdstats.v7-neutral-leakage-report.v1"
V7_NEUTRAL_STATISTICAL_BASE_SCHEMA = "mdstats.v7-neutral-statistical-base.v1"


class V7NeutralFeasibilityOutcome(str, Enum):
    FULLY_SUPPORTED = "fully_supported"
    SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY = "supported_with_temporal_blocks_only"
    CALIBRATION_DEFERRED = "calibration_deferred"
    INSUFFICIENT_FOR_LOCKED_TEST = "insufficient_for_locked_test"
    INSUFFICIENT_FOR_REQUESTED_ROLES = "insufficient_for_requested_roles"


class V7LeakageSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class V7NeutralRoleBudget:
    development_minimum_independent_units: int = 4
    outer_monitor_minimum_independent_units: int = 1
    calibration_minimum_independent_units: int = 1
    locked_interpolation_test_minimum_independent_units: int = 1
    purge_units_between_roles: int = 1
    allow_calibration_deferral: bool = True

    def __post_init__(self) -> None:
        for name in (
            "development_minimum_independent_units",
            "outer_monitor_minimum_independent_units",
            "calibration_minimum_independent_units",
            "locked_interpolation_test_minimum_independent_units",
            "purge_units_between_roles",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_ROLE_BUDGET_SCHEMA,
            "development_minimum_independent_units": self.development_minimum_independent_units,
            "outer_monitor_minimum_independent_units": self.outer_monitor_minimum_independent_units,
            "calibration_minimum_independent_units": self.calibration_minimum_independent_units,
            "locked_interpolation_test_minimum_independent_units": (
                self.locked_interpolation_test_minimum_independent_units
            ),
            "purge_units_between_roles": self.purge_units_between_roles,
            "allow_calibration_deferral": self.allow_calibration_deferral,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralRoleBudget":
        if payload.get("schema") != V7_NEUTRAL_ROLE_BUDGET_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-role-budget schema.")
        result = cls(
            development_minimum_independent_units=int(
                payload["development_minimum_independent_units"]
            ),
            outer_monitor_minimum_independent_units=int(
                payload["outer_monitor_minimum_independent_units"]
            ),
            calibration_minimum_independent_units=int(
                payload["calibration_minimum_independent_units"]
            ),
            locked_interpolation_test_minimum_independent_units=int(
                payload["locked_interpolation_test_minimum_independent_units"]
            ),
            purge_units_between_roles=int(payload["purge_units_between_roles"]),
            allow_calibration_deferral=bool(payload["allow_calibration_deferral"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("V7 neutral-role-budget digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class V7NeutralPartitionPolicy:
    role_budget: V7NeutralRoleBudget = V7NeutralRoleBudget()
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
    policy_version: str = V7_NEUTRAL_PARTITION_POLICY_VERSION

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
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "accepted_eligibility_states", states)
        object.__setattr__(self, "autocorrelation_observables", observables)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_PARTITION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "role_budget": self.role_budget.to_dict(),
            "block_policy": self.block_policy.to_dict(),
            "accepted_eligibility_states": list(self.accepted_eligibility_states),
            "autocorrelation_observables": list(self.autocorrelation_observables),
            "merge_protected_event_windows": self.merge_protected_event_windows,
            "require_condition_coverage_in_outer_roles": self.require_condition_coverage_in_outer_roles,
            "allow_global_role_fallback": self.allow_global_role_fallback,
            "minimum_units_per_condition_for_full_outer_roles": (
                self.minimum_units_per_condition_for_full_outer_roles
            ),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralPartitionPolicy":
        if payload.get("schema") != V7_NEUTRAL_PARTITION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-partition-policy schema.")
        result = cls(
            role_budget=V7NeutralRoleBudget.from_dict(payload["role_budget"]),
            block_policy=CompleteFrameBlockPolicy.from_dict(payload["block_policy"]),
            accepted_eligibility_states=tuple(str(v) for v in payload["accepted_eligibility_states"]),
            autocorrelation_observables=tuple(str(v) for v in payload["autocorrelation_observables"]),
            merge_protected_event_windows=bool(payload["merge_protected_event_windows"]),
            require_condition_coverage_in_outer_roles=bool(
                payload["require_condition_coverage_in_outer_roles"]
            ),
            allow_global_role_fallback=bool(payload["allow_global_role_fallback"]),
            minimum_units_per_condition_for_full_outer_roles=int(
                payload["minimum_units_per_condition_for_full_outer_roles"]
            ),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("V7 neutral-partition-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, order=True)
class V7NeutralConditionKey:
    reduced_formula: str
    temperature_condition: str
    strain_class: str
    regime: str
    user_labels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in ("reduced_formula", "temperature_condition", "strain_class", "regime"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")
        labels = tuple(sorted((str(k), str(v)) for k, v in self.user_labels))
        if len({key for key, _ in labels}) != len(labels):
            raise TrainingDataInputError("Condition user-label keys must be unique.")
        object.__setattr__(self, "user_labels", labels)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_CONDITION_KEY_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralConditionKey":
        if payload.get("schema") != V7_NEUTRAL_CONDITION_KEY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-condition-key schema.")
        result = cls(
            reduced_formula=str(payload["reduced_formula"]),
            temperature_condition=str(payload["temperature_condition"]),
            strain_class=str(payload["strain_class"]),
            regime=str(payload["regime"]),
            user_labels=tuple((str(k), str(v)) for k, v in payload.get("user_labels", {}).items()),
        )
        if payload.get("condition_id") not in (None, result.condition_id):
            raise TrainingDataSerializationError("V7 neutral-condition-key digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class V7NeutralPartitionUnit:
    unit_id: str
    run_id: str
    condition: V7NeutralConditionKey
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
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("unit_id", "block_plan_signature"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.run_id.strip():
            raise TrainingDataInputError("run_id must be non-empty.")
        object.__setattr__(self, "frame_uids", tuple(str(v) for v in self.frame_uids))
        object.__setattr__(self, "event_ids", tuple(str(v) for v in self.event_ids))
        object.__setattr__(
            self,
            "independence_evidence_codes",
            tuple(str(v) for v in self.independence_evidence_codes),
        )
        object.__setattr__(self, "independence_grade", IndependenceGrade(self.independence_grade))

    @property
    def correlation_group_id(self) -> str:
        """Stable correlation group consumed later without frame expansion."""

        return self.unit_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_UNIT_SCHEMA,
            "unit_id": self.unit_id,
            "run_id": self.run_id,
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
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralPartitionUnit":
        if payload.get("schema") != V7_NEUTRAL_UNIT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-partition-unit schema.")
        result = cls(
            unit_id=str(payload["unit_id"]),
            run_id=str(payload["run_id"]),
            condition=V7NeutralConditionKey.from_dict(payload["condition"]),
            source_frame_start=int(payload["source_frame_start"]),
            source_frame_stop=int(payload["source_frame_stop"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            block_plan_signature=str(payload["block_plan_signature"]),
            event_ids=tuple(str(v) for v in payload.get("event_ids", ())),
            contains_protected_event_frames=bool(payload["contains_protected_event_frames"]),
            maximum_autocorrelation_time_frames=float(payload["maximum_autocorrelation_time_frames"]),
            effective_sample_count=float(payload["effective_sample_count"]),
            replica_id=None if payload.get("replica_id") is None else str(payload["replica_id"]),
            structural_realization_id=(
                None
                if payload.get("structural_realization_id") is None
                else str(payload["structural_realization_id"])
            ),
            reference_group=(
                None if payload.get("reference_group") is None else str(payload["reference_group"])
            ),
            independence_grade=IndependenceGrade(payload["independence_grade"]),
            independence_evidence_codes=tuple(
                str(v) for v in payload.get("independence_evidence_codes", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-partition-unit digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class V7NeutralUnitCatalog:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    policy_digest: str
    units: tuple[V7NeutralPartitionUnit, ...]
    run_block_plan_signatures: tuple[tuple[str, str], ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "source_catalog_digest",
            "frame_catalog_digest",
            "data4_bundle_digest",
            "policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        units = tuple(
            sorted(self.units, key=lambda item: (item.run_id, item.source_frame_start, item.unit_id))
        )
        if len({item.unit_id for item in units}) != len(units):
            raise TrainingDataInputError("Neutral partition unit IDs must be unique.")
        object.__setattr__(self, "units", units)
        object.__setattr__(
            self,
            "run_block_plan_signatures",
            tuple(sorted((str(a), str(b)) for a, b in self.run_block_plan_signatures)),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_UNIT_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "policy_digest": self.policy_digest,
            "units": [item.to_dict() for item in self.units],
            "run_block_plan_signatures": [list(item) for item in self.run_block_plan_signatures],
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralUnitCatalog":
        if payload.get("schema") != V7_NEUTRAL_UNIT_CATALOG_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported V7 neutral-unit-catalog schema."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            policy_digest=str(payload["policy_digest"]),
            units=tuple(V7NeutralPartitionUnit.from_dict(item) for item in payload["units"]),
            run_block_plan_signatures=tuple(
                (str(a), str(b)) for a, b in payload.get("run_block_plan_signatures", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-unit-catalog digest mismatch.")
        return result


def _condition_for_frame(
    *,
    source: Any,
    frame: Any,
    frame_catalog: Any,
    strain_record: Any,
    regime_by_frame_uid: Mapping[str, str] | None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None,
) -> V7NeutralConditionKey:
    temperature = frame_catalog.temperature_conditions.for_run(frame.run_id)
    labels: tuple[tuple[str, str], ...] = ()
    if user_labels_by_frame_uid is not None and frame.frame_uid in user_labels_by_frame_uid:
        labels = tuple((str(k), str(v)) for k, v in user_labels_by_frame_uid[frame.frame_uid].items())
    return V7NeutralConditionKey(
        reduced_formula=source.composition.reduced_formula,
        temperature_condition=_temperature_label(temperature),
        strain_class=strain_record.tensor_class.value,
        regime=_regime_label(source, frame.frame_uid, regime_by_frame_uid),
        user_labels=labels,
    )


def build_v7_neutral_unit_catalog(
    source_catalog: Any,
    frame_catalog: Any,
    data4_bundle: Any,
    *,
    policy: V7NeutralPartitionPolicy | None = None,
    regime_by_frame_uid: Mapping[str, str] | None = None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None = None,
) -> V7NeutralUnitCatalog:
    active = V7NeutralPartitionPolicy() if policy is None else policy
    if source_catalog.content_digest != data4_bundle.source_catalog_digest:
        raise TrainingDataInputError("Neutral substrate source catalog does not match DATA4.")
    if frame_catalog.content_digest != data4_bundle.frame_catalog_digest:
        raise TrainingDataInputError("Neutral substrate frame catalog does not match DATA4.")

    frame_map = {item.frame_uid: item for item in frame_catalog.frames}
    raw_map = {item.frame_uid: item for item in data4_bundle.raw_features.records}
    eligibility_map = {item.frame_uid: item for item in frame_catalog.eligibility.decisions}
    strain_by_uid = {item.frame_uid: item for item in frame_catalog.strain_records}
    event_by_run: dict[str, list[Any]] = {}
    for event in data4_bundle.events.events:
        event_by_run.setdefault(event.run_id, []).append(event)
    event_ordinals_by_frame_by_run: dict[str, dict[str, tuple[int, ...]]] = {}
    for run_id, run_events in event_by_run.items():
        ordinals_by_frame: dict[str, list[int]] = {}
        for event_ordinal, event in enumerate(run_events):
            for frame_uid in event.protected_frame_uids:
                ordinals_by_frame.setdefault(frame_uid, []).append(event_ordinal)
        event_ordinals_by_frame_by_run[run_id] = {
            frame_uid: tuple(ordinals) for frame_uid, ordinals in ordinals_by_frame.items()
        }
    frames_by_run: dict[str, list[Any]] = {}
    for frame in frame_catalog.frames:
        frames_by_run.setdefault(frame.run_id, []).append(frame)
    for run_frames in frames_by_run.values():
        run_frames.sort(key=lambda item: item.source_frame_index)

    units: list[V7NeutralPartitionUnit] = []
    run_plan_signatures: list[tuple[str, str]] = []
    accepted = set(active.accepted_eligibility_states)
    condition_by_uid: dict[str, V7NeutralConditionKey] = {}
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
            condition_structural_realizations.setdefault(condition.condition_id, set()).add(
                str(realization_id).strip()
            )

    for source in source_catalog.sources:
        run_frames = frames_by_run.get(source.run_id, ())
        eligible = [
            item for item in run_frames if eligibility_map[item.frame_uid].state.value in accepted
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
        state_changed = profile_partition_state_changed(
            tuple(getattr(data4_bundle, "profile_partition_features", ())), same_run_uids
        )

        for interval in intervals:
            left = int(np.searchsorted(eligible_indices, interval.frame_start, side="left"))
            right = int(np.searchsorted(eligible_indices, interval.frame_stop, side="left"))
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
                matched_event_ordinals.update(ordinals_by_frame.get(member.frame_uid, ()))
            events = tuple(run_events[event_ordinal] for event_ordinal in sorted(matched_event_ordinals))
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
                evidence = ("multiple_source_runs_for_composition_condition",)
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
                V7NeutralPartitionUnit(
                    unit_id=digest(unit_payload),
                    run_id=source.run_id,
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
        raise TrainingDataInputError("No eligible frames remain for V7 neutral partitioning.")
    return V7NeutralUnitCatalog(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        policy_digest=active.policy_digest,
        units=tuple(units),
        run_block_plan_signatures=tuple(run_plan_signatures),
    )


@dataclass(frozen=True, slots=True)
class V7NeutralFeasibilityReport:
    policy_digest: str
    unit_catalog_digest: str
    outcome: V7NeutralFeasibilityOutcome
    available_unit_count: int
    available_condition_count: int
    calibration_deferred: bool
    temporal_blocks_only: bool
    per_condition_unit_counts: tuple[tuple[str, int], ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(
            self, "unit_catalog_digest", validate_digest(self.unit_catalog_digest, name="unit_catalog_digest")
        )
        object.__setattr__(self, "outcome", V7NeutralFeasibilityOutcome(self.outcome))
        object.__setattr__(
            self,
            "per_condition_unit_counts",
            tuple(sorted((str(k), int(v)) for k, v in self.per_condition_unit_counts)),
        )
        object.__setattr__(self, "reason_codes", tuple(str(v) for v in self.reason_codes))

    @property
    def is_usable(self) -> bool:
        return self.outcome not in {
            V7NeutralFeasibilityOutcome.INSUFFICIENT_FOR_LOCKED_TEST,
            V7NeutralFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_FEASIBILITY_SCHEMA,
            "policy_digest": self.policy_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "outcome": self.outcome.value,
            "available_unit_count": self.available_unit_count,
            "available_condition_count": self.available_condition_count,
            "calibration_deferred": self.calibration_deferred,
            "temporal_blocks_only": self.temporal_blocks_only,
            "per_condition_unit_counts": dict(self.per_condition_unit_counts),
            "reason_codes": list(self.reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralFeasibilityReport":
        if payload.get("schema") != V7_NEUTRAL_FEASIBILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-feasibility schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            outcome=V7NeutralFeasibilityOutcome(payload["outcome"]),
            available_unit_count=int(payload["available_unit_count"]),
            available_condition_count=int(payload["available_condition_count"]),
            calibration_deferred=bool(payload["calibration_deferred"]),
            temporal_blocks_only=bool(payload["temporal_blocks_only"]),
            per_condition_unit_counts=tuple(
                (str(k), int(v)) for k, v in payload.get("per_condition_unit_counts", {}).items()
            ),
            reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-feasibility digest mismatch.")
        return result


def assess_v7_neutral_feasibility(
    unit_catalog: V7NeutralUnitCatalog,
    *,
    policy: V7NeutralPartitionPolicy | None = None,
) -> V7NeutralFeasibilityReport:
    active = V7NeutralPartitionPolicy() if policy is None else policy
    if unit_catalog.policy_digest != active.policy_digest:
        raise TrainingDataInputError("Unit catalog and feasibility policy differ.")
    groups: dict[str, list[V7NeutralPartitionUnit]] = {}
    for unit in unit_catalog.units:
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
    temporal_only = all(
        unit.independence_grade
        in {
            IndependenceGrade.PURGED_TEMPORAL_BLOCK,
            IndependenceGrade.SLOW_STATE_NOT_DECORRELATED,
            IndependenceGrade.INSUFFICIENT_INDEPENDENCE,
        }
        for unit in unit_catalog.units
    )
    calibration_deferred = False
    units = unit_catalog.units
    if len(units) < minimum_total:
        if budget.allow_calibration_deferral and len(units) >= (
            minimum_total - budget.calibration_minimum_independent_units
        ):
            calibration_deferred = True
            reason_codes.append("calibration_deferred_for_role_budget")
            outcome = V7NeutralFeasibilityOutcome.CALIBRATION_DEFERRED
        elif len(units) < (
            budget.locked_interpolation_test_minimum_independent_units
            + budget.development_minimum_independent_units
        ):
            outcome = V7NeutralFeasibilityOutcome.INSUFFICIENT_FOR_LOCKED_TEST
            reason_codes.append("insufficient_units_for_development_and_locked_test")
        else:
            outcome = V7NeutralFeasibilityOutcome.INSUFFICIENT_FOR_REQUESTED_ROLES
            reason_codes.append("insufficient_units_for_requested_outer_roles")
    elif temporal_only:
        outcome = V7NeutralFeasibilityOutcome.SUPPORTED_WITH_TEMPORAL_BLOCKS_ONLY
        reason_codes.append("no_independent_replica_or_run_support")
    else:
        outcome = V7NeutralFeasibilityOutcome.FULLY_SUPPORTED
    return V7NeutralFeasibilityReport(
        policy_digest=active.policy_digest,
        unit_catalog_digest=unit_catalog.content_digest,
        outcome=outcome,
        available_unit_count=len(units),
        available_condition_count=len(groups),
        calibration_deferred=calibration_deferred,
        temporal_blocks_only=temporal_only,
        per_condition_unit_counts=counts,
        reason_codes=tuple(reason_codes),
    )


@dataclass(frozen=True, slots=True)
class V7NeutralRoleAssignment:
    unit_id: str
    role: OuterRole
    assignment_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_id", validate_digest(self.unit_id, name="unit_id"))
        object.__setattr__(self, "role", OuterRole(self.role))
        object.__setattr__(
            self, "assignment_reason_codes", tuple(str(v) for v in self.assignment_reason_codes)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_ROLE_ASSIGNMENT_SCHEMA,
            "unit_id": self.unit_id,
            "role": self.role.value,
            "assignment_reason_codes": list(self.assignment_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralRoleAssignment":
        if payload.get("schema") != V7_NEUTRAL_ROLE_ASSIGNMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-role-assignment schema.")
        result = cls(
            unit_id=str(payload["unit_id"]),
            role=OuterRole(payload["role"]),
            assignment_reason_codes=tuple(str(v) for v in payload.get("assignment_reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-role-assignment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class V7NeutralOuterPartition:
    policy_digest: str
    unit_catalog_digest: str
    feasibility_report_digest: str
    assignments: tuple[V7NeutralRoleAssignment, ...]
    _by_unit_id: dict[str, V7NeutralRoleAssignment] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("policy_digest", "unit_catalog_digest", "feasibility_report_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        assignments = tuple(sorted(self.assignments, key=lambda item: item.unit_id))
        if len({item.unit_id for item in assignments}) != len(assignments):
            raise TrainingDataInputError("Outer-role assignments require unique unit IDs.")
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "_by_unit_id", {item.unit_id: item for item in assignments})

    def role_for_unit(self, unit_id: str) -> OuterRole:
        return self._by_unit_id[unit_id].role

    def units_for_role(self, role: OuterRole) -> tuple[str, ...]:
        return tuple(item.unit_id for item in self.assignments if item.role is role)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_OUTER_PARTITION_SCHEMA,
            "policy_digest": self.policy_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "feasibility_report_digest": self.feasibility_report_digest,
            "assignments": [item.to_dict() for item in self.assignments],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralOuterPartition":
        if payload.get("schema") != V7_NEUTRAL_OUTER_PARTITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-outer-partition schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            feasibility_report_digest=str(payload["feasibility_report_digest"]),
            assignments=tuple(
                V7NeutralRoleAssignment.from_dict(item) for item in payload["assignments"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-outer-partition digest mismatch.")
        return result


def build_v7_neutral_outer_partition(
    unit_catalog: V7NeutralUnitCatalog,
    feasibility: V7NeutralFeasibilityReport,
    *,
    policy: V7NeutralPartitionPolicy | None = None,
) -> V7NeutralOuterPartition:
    active = V7NeutralPartitionPolicy() if policy is None else policy
    if not feasibility.is_usable:
        raise TrainingDataInputError(
            f"Neutral population is not feasible for outer partitioning: {feasibility.outcome.value}."
        )
    units = list(unit_catalog.units)
    temporal_index = _build_temporal_neighbor_index(units)
    groups: dict[str, list[V7NeutralPartitionUnit]] = {}
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
        if not feasibility.calibration_deferred:
            role_sequence.append(OuterRole.UNCERTAINTY_CALIBRATION)
        role_sequence.append(OuterRole.LOCKED_INTERPOLATION_TEST)
        if (
            active.require_condition_coverage_in_outer_roles
            and len(group) >= active.minimum_units_per_condition_for_full_outer_roles
        ):
            positions = _spaced_indices(len(group), len(role_sequence))
            for role, position in zip(role_sequence, positions, strict=True):
                selected[role].add(group[position].unit_id)
    budget = active.role_budget
    minima = {
        OuterRole.OUTER_MONITOR: budget.outer_monitor_minimum_independent_units,
        OuterRole.UNCERTAINTY_CALIBRATION: (
            0 if feasibility.calibration_deferred else budget.calibration_minimum_independent_units
        ),
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
    assignments: list[V7NeutralRoleAssignment] = []
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
            V7NeutralRoleAssignment(
                unit_id=unit.unit_id,
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
    return V7NeutralOuterPartition(
        policy_digest=active.policy_digest,
        unit_catalog_digest=unit_catalog.content_digest,
        feasibility_report_digest=feasibility.content_digest,
        assignments=tuple(assignments),
    )


@dataclass(frozen=True, slots=True)
class V7NeutralIndependenceReport:
    unit_catalog_digest: str
    grade_counts: tuple[tuple[str, int], ...]
    weakest_grade: IndependenceGrade
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "unit_catalog_digest", validate_digest(self.unit_catalog_digest, name="unit_catalog_digest")
        )
        object.__setattr__(
            self, "grade_counts", tuple(sorted((str(k), int(v)) for k, v in self.grade_counts))
        )
        object.__setattr__(self, "weakest_grade", IndependenceGrade(self.weakest_grade))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_INDEPENDENCE_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralIndependenceReport":
        if payload.get("schema") != V7_NEUTRAL_INDEPENDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 independence-report schema.")
        result = cls(
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            grade_counts=tuple((str(k), int(v)) for k, v in payload["grade_counts"].items()),
            weakest_grade=IndependenceGrade(payload["weakest_grade"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 independence-report digest mismatch.")
        return result


def build_v7_independence_report(unit_catalog: V7NeutralUnitCatalog) -> V7NeutralIndependenceReport:
    order = {
        IndependenceGrade.INDEPENDENT_REPLICA: 0,
        IndependenceGrade.INDEPENDENT_STRUCTURAL_REALIZATION: 1,
        IndependenceGrade.INDEPENDENT_THERMODYNAMIC_RUN: 2,
        IndependenceGrade.PURGED_TEMPORAL_BLOCK: 3,
        IndependenceGrade.SLOW_STATE_NOT_DECORRELATED: 4,
        IndependenceGrade.INSUFFICIENT_INDEPENDENCE: 5,
    }
    counts: dict[str, int] = {}
    for unit in unit_catalog.units:
        counts[unit.independence_grade.value] = counts.get(unit.independence_grade.value, 0) + 1
    weakest = max((unit.independence_grade for unit in unit_catalog.units), key=lambda item: order[item])
    notes = ()
    if weakest in {IndependenceGrade.SLOW_STATE_NOT_DECORRELATED, IndependenceGrade.INSUFFICIENT_INDEPENDENCE}:
        notes = ("At least one condition lacks demonstrated slow-state independence.",)
    return V7NeutralIndependenceReport(
        unit_catalog_digest=unit_catalog.content_digest,
        grade_counts=tuple(counts.items()),
        weakest_grade=weakest,
        notes=notes,
    )


@dataclass(frozen=True, slots=True)
class V7NeutralLeakageFinding:
    code: str
    severity: V7LeakageSeverity
    unit_ids: tuple[str, ...]
    frame_uids: tuple[str, ...]
    message: str

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise TrainingDataInputError("Leakage finding code and message are required.")
        object.__setattr__(self, "severity", V7LeakageSeverity(self.severity))
        object.__setattr__(self, "unit_ids", tuple(sorted(set(str(v) for v in self.unit_ids))))
        object.__setattr__(self, "frame_uids", tuple(sorted(set(str(v) for v in self.frame_uids))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_LEAKAGE_FINDING_SCHEMA,
            "code": self.code,
            "severity": self.severity.value,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralLeakageFinding":
        if payload.get("schema") != V7_NEUTRAL_LEAKAGE_FINDING_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 leakage-finding schema.")
        result = cls(
            code=str(payload["code"]),
            severity=V7LeakageSeverity(payload["severity"]),
            unit_ids=tuple(str(v) for v in payload.get("unit_ids", ())),
            frame_uids=tuple(str(v) for v in payload.get("frame_uids", ())),
            message=str(payload["message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 leakage-finding digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class V7NeutralLeakageReport:
    unit_catalog_digest: str
    outer_partition_digest: str
    findings: tuple[V7NeutralLeakageFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "unit_catalog_digest", validate_digest(self.unit_catalog_digest, name="unit_catalog_digest")
        )
        object.__setattr__(
            self,
            "outer_partition_digest",
            validate_digest(self.outer_partition_digest, name="outer_partition_digest"),
        )
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=lambda item: (item.severity.value, item.code, item.content_digest))),
        )

    @property
    def passed(self) -> bool:
        return not any(item.severity is V7LeakageSeverity.ERROR for item in self.findings)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_LEAKAGE_REPORT_SCHEMA,
            "unit_catalog_digest": self.unit_catalog_digest,
            "outer_partition_digest": self.outer_partition_digest,
            "findings": [item.to_dict() for item in self.findings],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest, "passed": self.passed}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralLeakageReport":
        if payload.get("schema") != V7_NEUTRAL_LEAKAGE_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 leakage-report schema.")
        result = cls(
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            outer_partition_digest=str(payload["outer_partition_digest"]),
            findings=tuple(V7NeutralLeakageFinding.from_dict(item) for item in payload.get("findings", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 leakage-report digest mismatch.")
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("V7 leakage passed state mismatch.")
        return result


_PROTECTED_OUTER_ROLES = {
    OuterRole.DEVELOPMENT,
    OuterRole.OUTER_MONITOR,
    OuterRole.UNCERTAINTY_CALIBRATION,
    OuterRole.LOCKED_INTERPOLATION_TEST,
}


def audit_v7_neutral_leakage(
    unit_catalog: V7NeutralUnitCatalog,
    outer_partition: V7NeutralOuterPartition,
    *,
    policy: V7NeutralPartitionPolicy | None = None,
) -> V7NeutralLeakageReport:
    active = V7NeutralPartitionPolicy() if policy is None else policy
    findings: list[V7NeutralLeakageFinding] = []
    role_by_unit = {item.unit_id: item.role for item in outer_partition.assignments}
    if set(role_by_unit) != {item.unit_id for item in unit_catalog.units}:
        findings.append(
            V7NeutralLeakageFinding(
                code="incomplete_outer_assignment",
                severity=V7LeakageSeverity.ERROR,
                unit_ids=tuple(role_by_unit),
                frame_uids=(),
                message="Outer assignments do not cover the unit catalog exactly.",
            )
        )
    occupied = {
        unit_id
        for unit_id, role in role_by_unit.items()
        if role in _PROTECTED_OUTER_ROLES and role is not OuterRole.DEVELOPMENT
    }
    expected_purge = _neighbor_unit_ids(
        unit_catalog.units,
        occupied,
        active.role_budget.purge_units_between_roles,
        temporal_index=_build_temporal_neighbor_index(unit_catalog.units),
    )
    missing_purge = {
        unit_id
        for unit_id in expected_purge
        if role_by_unit.get(unit_id) not in {OuterRole.PURGED, OuterRole.EXCLUDED}
        and unit_id not in occupied
    }
    if missing_purge:
        findings.append(
            V7NeutralLeakageFinding(
                code="missing_outer_purge_neighbors",
                severity=V7LeakageSeverity.ERROR,
                unit_ids=tuple(missing_purge),
                frame_uids=(),
                message="Temporal neighbors of outer evidence were not purged.",
            )
        )
    protected_sets = {
        role: set(outer_partition.units_for_role(role)) for role in _PROTECTED_OUTER_ROLES
    }
    roles = list(_PROTECTED_OUTER_ROLES)
    for index, left in enumerate(roles):
        for right in roles[index + 1 :]:
            overlap = protected_sets[left] & protected_sets[right]
            if overlap:
                findings.append(
                    V7NeutralLeakageFinding(
                        code="overlapping_protected_outer_roles",
                        severity=V7LeakageSeverity.ERROR,
                        unit_ids=tuple(overlap),
                        frame_uids=(),
                        message=f"Protected roles {left.value} and {right.value} share units.",
                    )
                )
    return V7NeutralLeakageReport(
        unit_catalog_digest=unit_catalog.content_digest,
        outer_partition_digest=outer_partition.content_digest,
        findings=tuple(findings),
    )


@dataclass(frozen=True, slots=True)
class V7NeutralStatisticalBase:
    dataset_id: str
    policy: V7NeutralPartitionPolicy
    unit_catalog: V7NeutralUnitCatalog
    feasibility: V7NeutralFeasibilityReport
    outer_partition: V7NeutralOuterPartition
    independence: V7NeutralIndependenceReport
    leakage: V7NeutralLeakageReport
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.unit_catalog.dataset_id != self.dataset_id:
            raise TrainingDataInputError("Neutral statistical base dataset mismatch.")
        if self.unit_catalog.policy_digest != self.policy.policy_digest:
            raise TrainingDataInputError("Neutral statistical base policy mismatch.")
        if self.feasibility.unit_catalog_digest != self.unit_catalog.content_digest:
            raise TrainingDataInputError("Neutral feasibility lineage mismatch.")
        if self.outer_partition.unit_catalog_digest != self.unit_catalog.content_digest:
            raise TrainingDataInputError("Neutral outer-partition lineage mismatch.")
        if self.leakage.unit_catalog_digest != self.unit_catalog.content_digest:
            raise TrainingDataInputError("Neutral leakage lineage mismatch.")
        if not self.leakage.passed:
            raise TrainingDataInputError("Neutral statistical base cannot be created with leakage errors.")
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_NEUTRAL_STATISTICAL_BASE_SCHEMA,
            "dataset_id": self.dataset_id,
            "policy": self.policy.to_dict(),
            "unit_catalog": self.unit_catalog.to_dict(),
            "feasibility": self.feasibility.to_dict(),
            "outer_partition": self.outer_partition.to_dict(),
            "independence": self.independence.to_dict(),
            "leakage": self.leakage.to_dict(),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7NeutralStatisticalBase":
        if payload.get("schema") != V7_NEUTRAL_STATISTICAL_BASE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 neutral-statistical-base schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            policy=V7NeutralPartitionPolicy.from_dict(payload["policy"]),
            unit_catalog=V7NeutralUnitCatalog.from_dict(payload["unit_catalog"]),
            feasibility=V7NeutralFeasibilityReport.from_dict(payload["feasibility"]),
            outer_partition=V7NeutralOuterPartition.from_dict(payload["outer_partition"]),
            independence=V7NeutralIndependenceReport.from_dict(payload["independence"]),
            leakage=V7NeutralLeakageReport.from_dict(payload["leakage"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 neutral-statistical-base digest mismatch.")
        return result


def build_v7_neutral_statistical_base(
    source_catalog: Any,
    frame_catalog: Any,
    data4_bundle: Any,
    *,
    policy: V7NeutralPartitionPolicy | None = None,
    regime_by_frame_uid: Mapping[str, str] | None = None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None = None,
) -> V7NeutralStatisticalBase:
    active = V7NeutralPartitionPolicy() if policy is None else policy
    units = build_v7_neutral_unit_catalog(
        source_catalog,
        frame_catalog,
        data4_bundle,
        policy=active,
        regime_by_frame_uid=regime_by_frame_uid,
        user_labels_by_frame_uid=user_labels_by_frame_uid,
    )
    feasibility = assess_v7_neutral_feasibility(units, policy=active)
    outer = build_v7_neutral_outer_partition(units, feasibility, policy=active)
    leakage = audit_v7_neutral_leakage(units, outer, policy=active)
    return V7NeutralStatisticalBase(
        dataset_id=frame_catalog.dataset_id,
        policy=active,
        unit_catalog=units,
        feasibility=feasibility,
        outer_partition=outer,
        independence=build_v7_independence_report(units),
        leakage=leakage,
        notes=(
            "V7 neutral statistical base owns correlation/partition units and protected outer roles. "
            "It does not construct a cross-validation plan and does not partition by compatibility grouping.",
        ),
    )
