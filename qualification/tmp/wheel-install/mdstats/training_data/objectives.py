"""Training objectives, configuration weights, and checkpoint metrics for DATA7."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator, Sequence
from typing import Any, Mapping

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .feature_metric import FeatureFitDomain, build_feature_fit_domains

TRAINING_OBJECTIVE_POLICY_SCHEMA = "mdstats.training-objective-policy.v2"
CONFIGURATION_WEIGHT_POLICY_SCHEMA = "mdstats.configuration-weight-policy.v1"
FRAME_TRAINING_WEIGHT_SCHEMA = "mdstats.frame-training-weight.v1"
TRAINING_WEIGHT_CATALOG_SCHEMA = "mdstats.training-weight-catalog.v1"
CHECKPOINT_METRIC_POLICY_SCHEMA = "mdstats.checkpoint-metric-policy.v2"
TRAINING_OBJECTIVE_POLICY_VERSION = "mdstats.mlff-data7.training-objective.2026-07.v2"
CONFIGURATION_WEIGHT_POLICY_VERSION = "mdstats.mlff-data7.configuration-weight.2026-07.v1"
CHECKPOINT_METRIC_POLICY_VERSION = "mdstats.mlff-data7.checkpoint-metric.2026-07.v2"


@dataclass(frozen=True, slots=True)
class TrainingObjectivePolicy:
    energy_weight: float = 1.0
    forces_weight: float = 10.0
    stress_weight: float = 1.0
    group_aware_force_objective: bool = False
    focus_atom_group_ids: tuple[str, ...] = ()
    focus_atomic_numbers: tuple[int, ...] = ()
    policy_version: str = TRAINING_OBJECTIVE_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in ("energy_weight", "forces_weight", "stress_weight"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if self.energy_weight + self.forces_weight + self.stress_weight <= 0.0:
            raise TrainingDataInputError("At least one training property weight must be positive.")
        groups = tuple(sorted(set(str(v).strip() for v in self.focus_atom_group_ids if str(v).strip())))
        numbers = tuple(sorted(set(int(v) for v in self.focus_atomic_numbers)))
        if any(v <= 0 for v in numbers):
            raise TrainingDataInputError("Focus atomic numbers must be positive.")
        if self.group_aware_force_objective and not groups and not numbers:
            raise TrainingDataInputError("A group-aware force objective requires explicit focus groups or atomic numbers.")
        object.__setattr__(self, "focus_atom_group_ids", groups)
        object.__setattr__(self, "focus_atomic_numbers", numbers)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_OBJECTIVE_POLICY_SCHEMA, "policy_version": self.policy_version,
            "energy_weight": self.energy_weight, "forces_weight": self.forces_weight,
            "stress_weight": self.stress_weight, "group_aware_force_objective": self.group_aware_force_objective,
            "focus_atom_group_ids": list(self.focus_atom_group_ids),
            "focus_atomic_numbers": list(self.focus_atomic_numbers),
        }

    @property
    def policy_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingObjectivePolicy":
        if payload.get("schema") != TRAINING_OBJECTIVE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-objective schema.")
        result = cls(
            energy_weight=float(payload["energy_weight"]),
            forces_weight=float(payload["forces_weight"]),
            stress_weight=float(payload["stress_weight"]),
            group_aware_force_objective=bool(payload.get("group_aware_force_objective", False)),
            focus_atom_group_ids=tuple(str(v) for v in payload.get("focus_atom_group_ids", ())),
            focus_atomic_numbers=tuple(int(v) for v in payload.get("focus_atomic_numbers", ())),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Training-objective digest mismatch.")
        return result



@dataclass(frozen=True, slots=True)
class ConfigurationWeightPolicy:
    equalize_condition_strata: bool = True
    event_anchor_multiplier: float = 2.0
    protected_event_multiplier: float = 1.25
    degraded_frame_multiplier: float = 0.5
    minimum_configuration_weight: float = 0.05
    maximum_configuration_weight: float = 10.0
    policy_version: str = CONFIGURATION_WEIGHT_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in ("event_anchor_multiplier", "protected_event_multiplier", "degraded_frame_multiplier", "minimum_configuration_weight", "maximum_configuration_weight"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be positive and finite.")
            object.__setattr__(self, name, value)
        if self.minimum_configuration_weight > 1.0 or self.maximum_configuration_weight < 1.0:
            raise TrainingDataInputError("Configuration weight bounds must contain the normalized mean value one.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CONFIGURATION_WEIGHT_POLICY_SCHEMA, "policy_version": self.policy_version,
            "equalize_condition_strata": self.equalize_condition_strata,
            "event_anchor_multiplier": self.event_anchor_multiplier,
            "protected_event_multiplier": self.protected_event_multiplier,
            "degraded_frame_multiplier": self.degraded_frame_multiplier,
            "minimum_configuration_weight": self.minimum_configuration_weight,
            "maximum_configuration_weight": self.maximum_configuration_weight,
        }

    @property
    def policy_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConfigurationWeightPolicy":
        if payload.get("schema") != CONFIGURATION_WEIGHT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported configuration-weight schema.")
        result = cls(
            equalize_condition_strata=bool(payload["equalize_condition_strata"]),
            event_anchor_multiplier=float(payload["event_anchor_multiplier"]),
            protected_event_multiplier=float(payload["protected_event_multiplier"]),
            degraded_frame_multiplier=float(payload["degraded_frame_multiplier"]),
            minimum_configuration_weight=float(payload["minimum_configuration_weight"]),
            maximum_configuration_weight=float(payload["maximum_configuration_weight"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Configuration-weight digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameTrainingWeight:
    frame_uid: str
    configuration_weight: float
    energy_weight: float
    forces_weight: float
    stress_weight: float
    reason_codes: tuple[str, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        for name in ("configuration_weight", "energy_weight", "forces_weight", "stress_weight"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if self.configuration_weight <= 0.0:
            raise TrainingDataInputError("configuration_weight must be positive.")
        object.__setattr__(self, "reason_codes", tuple(sorted(set(str(v) for v in self.reason_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_TRAINING_WEIGHT_SCHEMA, "frame_uid": self.frame_uid,
            "configuration_weight": self.configuration_weight, "energy_weight": self.energy_weight,
            "forces_weight": self.forces_weight, "stress_weight": self.stress_weight,
            "reason_codes": list(self.reason_codes),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameTrainingWeight":
        if payload.get("schema") != FRAME_TRAINING_WEIGHT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-training-weight schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]), configuration_weight=float(payload["configuration_weight"]),
            energy_weight=float(payload["energy_weight"]), forces_weight=float(payload["forces_weight"]),
            stress_weight=float(payload["stress_weight"]), reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Frame-training-weight digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class FrameTrainingWeightTable(Sequence[FrameTrainingWeight]):
    """Columnar, lazy storage for one training weight per frame."""

    frame_uids: tuple[str, ...]
    configuration_weights: np.ndarray
    energy_weights: np.ndarray
    forces_weights: np.ndarray
    stress_weights: np.ndarray
    reason_codes: tuple[tuple[str, ...], ...]
    _index_by_uid: Mapping[str, int] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _record_digest_cache: tuple[str, ...] = field(
        default=(), init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        uids = tuple(validate_digest(uid, name="frame_uid") for uid in self.frame_uids)
        arrays = tuple(
            np.asarray(value, dtype=np.float64, order="C")
            for value in (
                self.configuration_weights,
                self.energy_weights,
                self.forces_weights,
                self.stress_weights,
            )
        )
        reasons = tuple(
            tuple(sorted(set(str(code) for code in row)))
            for row in self.reason_codes
        )
        n = len(uids)
        if not uids or len(set(uids)) != n or len(reasons) != n:
            raise TrainingDataInputError(
                "Training-weight table requires aligned unique frame UIDs."
            )
        if any(array.shape != (n,) for array in arrays):
            raise TrainingDataInputError(
                "Training-weight table arrays must align with frame UIDs."
            )
        if any(np.any(~np.isfinite(array)) or np.any(array < 0.0) for array in arrays):
            raise TrainingDataInputError(
                "Training-weight table values must be finite and nonnegative."
            )
        if np.any(arrays[0] <= 0.0):
            raise TrainingDataInputError(
                "Configuration weights must be strictly positive."
            )
        for array in arrays:
            array.setflags(write=False)
        object.__setattr__(self, "frame_uids", uids)
        object.__setattr__(self, "configuration_weights", arrays[0])
        object.__setattr__(self, "energy_weights", arrays[1])
        object.__setattr__(self, "forces_weights", arrays[2])
        object.__setattr__(self, "stress_weights", arrays[3])
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(
            self, "_index_by_uid", {uid: index for index, uid in enumerate(uids)}
        )

    @classmethod
    def from_records(
        cls, records: Sequence[FrameTrainingWeight]
    ) -> "FrameTrainingWeightTable":
        ordered = tuple(sorted(records, key=lambda item: item.frame_uid))
        if not ordered:
            raise TrainingDataInputError("Training-weight table cannot be empty.")
        return cls(
            frame_uids=tuple(item.frame_uid for item in ordered),
            configuration_weights=np.asarray(
                [item.configuration_weight for item in ordered], dtype=np.float64
            ),
            energy_weights=np.asarray(
                [item.energy_weight for item in ordered], dtype=np.float64
            ),
            forces_weights=np.asarray(
                [item.forces_weight for item in ordered], dtype=np.float64
            ),
            stress_weights=np.asarray(
                [item.stress_weight for item in ordered], dtype=np.float64
            ),
            reason_codes=tuple(item.reason_codes for item in ordered),
        )

    @classmethod
    def _from_authenticated_arrays(
        cls,
        *,
        frame_uids: Sequence[str],
        configuration_weights: np.ndarray,
        energy_weights: np.ndarray,
        forces_weights: np.ndarray,
        stress_weights: np.ndarray,
        reason_codes: Sequence[Sequence[str]],
    ) -> "FrameTrainingWeightTable":
        uids = tuple(validate_digest(uid, name="frame_uid") for uid in frame_uids)
        arrays = tuple(
            np.asarray(value, dtype=np.float64, order="C")
            for value in (
                configuration_weights,
                energy_weights,
                forces_weights,
                stress_weights,
            )
        )
        reasons = tuple(tuple(str(code) for code in row) for row in reason_codes)
        n = len(uids)
        if any(array.shape != (n,) for array in arrays) or len(reasons) != n:
            raise TrainingDataInputError(
                "Authenticated training-weight arrays are misaligned."
            )
        for array in arrays:
            array.setflags(write=False)
        result = object.__new__(cls)
        object.__setattr__(result, "frame_uids", uids)
        object.__setattr__(result, "configuration_weights", arrays[0])
        object.__setattr__(result, "energy_weights", arrays[1])
        object.__setattr__(result, "forces_weights", arrays[2])
        object.__setattr__(result, "stress_weights", arrays[3])
        object.__setattr__(result, "reason_codes", reasons)
        object.__setattr__(
            result, "_index_by_uid", {uid: index for index, uid in enumerate(uids)}
        )
        object.__setattr__(result, "_record_digest_cache", ())
        return result

    def __len__(self) -> int:
        return len(self.frame_uids)

    def _record(self, index: int) -> FrameTrainingWeight:
        return FrameTrainingWeight(
            frame_uid=self.frame_uids[index],
            configuration_weight=float(self.configuration_weights[index]),
            energy_weight=float(self.energy_weights[index]),
            forces_weight=float(self.forces_weights[index]),
            stress_weight=float(self.stress_weights[index]),
            reason_codes=self.reason_codes[index],
        )

    def __getitem__(
        self, index: int | slice
    ) -> FrameTrainingWeight | tuple[FrameTrainingWeight, ...]:
        if isinstance(index, slice):
            return tuple(self._record(i) for i in range(*index.indices(len(self))))
        normalized = int(index)
        if normalized < 0:
            normalized += len(self)
        if normalized < 0 or normalized >= len(self):
            raise IndexError(index)
        return self._record(normalized)

    def __iter__(self) -> Iterator[FrameTrainingWeight]:
        for index in range(len(self)):
            yield self._record(index)

    def for_frame(self, frame_uid: str) -> FrameTrainingWeight:
        try:
            return self._record(self._index_by_uid[frame_uid])
        except KeyError:
            raise KeyError(frame_uid) from None

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FrameTrainingWeightTable)
            and self.frame_uids == other.frame_uids
            and np.array_equal(
                self.configuration_weights, other.configuration_weights
            )
            and np.array_equal(self.energy_weights, other.energy_weights)
            and np.array_equal(self.forces_weights, other.forces_weights)
            and np.array_equal(self.stress_weights, other.stress_weights)
            and self.reason_codes == other.reason_codes
        )

    @property
    def record_digests(self) -> tuple[str, ...]:
        cached = self._record_digest_cache
        if not cached:
            cached = tuple(self._record(index).content_digest for index in range(len(self)))
            object.__setattr__(self, "_record_digest_cache", cached)
        return cached



@dataclass(frozen=True, slots=True)
class TrainingWeightCatalog:
    domain: FeatureFitDomain
    objective_policy: TrainingObjectivePolicy
    configuration_policy: ConfigurationWeightPolicy
    data4_bundle_digest: str
    data5_bundle_digest: str
    records: FrameTrainingWeightTable | Sequence[FrameTrainingWeight]
    _by_frame_uid: Mapping[str, FrameTrainingWeight] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("data4_bundle_digest", "data5_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        records = (
            self.records
            if isinstance(self.records, FrameTrainingWeightTable)
            else FrameTrainingWeightTable.from_records(tuple(self.records))
        )
        if set(records.frame_uids) != set(self.domain.frame_uids):
            raise TrainingDataInputError("Training weights must cover exactly the training domain.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_by_frame_uid", {})

    def for_frame(self, frame_uid: str) -> FrameTrainingWeight:
        assert isinstance(self.records, FrameTrainingWeightTable)
        return self.records.for_frame(frame_uid)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_WEIGHT_CATALOG_SCHEMA, "domain": self.domain.to_dict(),
            "objective_policy": self.objective_policy.to_dict(), "configuration_policy": self.configuration_policy.to_dict(),
            "data4_bundle_digest": self.data4_bundle_digest, "data5_bundle_digest": self.data5_bundle_digest,
            "records": [item.to_dict() for item in self.records],
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_WEIGHT_CATALOG_SCHEMA,
            "domain_digest": self.domain.content_digest,
            "objective_policy_digest": self.objective_policy.policy_digest,
            "configuration_policy_digest": self.configuration_policy.policy_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "record_digests": list(
                self.records.record_digests
                if isinstance(self.records, FrameTrainingWeightTable)
                else tuple(item.content_digest for item in self.records)
            ),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingWeightCatalog":
        if payload.get("schema") != TRAINING_WEIGHT_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-weight-catalog schema.")
        result = cls(
            domain=FeatureFitDomain.from_dict(payload["domain"]),
            objective_policy=TrainingObjectivePolicy.from_dict(payload["objective_policy"]),
            configuration_policy=ConfigurationWeightPolicy.from_dict(payload["configuration_policy"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]), data5_bundle_digest=str(payload["data5_bundle_digest"]),
            records=tuple(FrameTrainingWeight.from_dict(item) for item in payload["records"]),
        )
        expected = payload.get("content_digest")
        if expected is not None and expected != result.content_digest:
            legacy_payload = {
                key: value for key, value in payload.items()
                if key != "content_digest"
            }
            if expected != digest(legacy_payload):
                raise TrainingDataSerializationError(
                    "Training-weight-catalog digest mismatch."
                )
        return result


def build_training_weight_catalog(
    frame_catalog: Any, data4_bundle: Any, data5_bundle: Any, domain: FeatureFitDomain,
    *, objective_policy: TrainingObjectivePolicy | None = None, configuration_policy: ConfigurationWeightPolicy | None = None,
    canonical_domain_digests: set[str] | frozenset[str] | None = None,
    frame_record_by_uid: Mapping[str, Any] | None = None,
    event_anchor_frame_uids: set[str] | frozenset[str] | None = None,
    protected_event_frame_uids: set[str] | frozenset[str] | None = None,
) -> TrainingWeightCatalog:
    canonical = (
        {item.content_digest for item in build_feature_fit_domains(data5_bundle)}
        if canonical_domain_digests is None
        else canonical_domain_digests
    )
    if domain.content_digest not in canonical:
        raise TrainingDataInputError("Training weights require a canonical DATA5 training domain.")
    objective = TrainingObjectivePolicy() if objective_policy is None else objective_policy
    config = ConfigurationWeightPolicy() if configuration_policy is None else configuration_policy
    unit_by_frame = {uid: unit for unit_id in domain.unit_ids for unit in (data5_bundle.unit_catalog.unit(unit_id),) for uid in unit.frame_uids}
    condition_counts: dict[str, int] = {}
    for uid in domain.frame_uids:
        condition_id = unit_by_frame[uid].condition.condition_id
        condition_counts[condition_id] = condition_counts.get(condition_id, 0) + 1
    anchor_frames = (
        {event.anchor_frame_uid for event in data4_bundle.events.events}
        if event_anchor_frame_uids is None
        else event_anchor_frame_uids
    )
    protected_frames = (
        set(data4_bundle.events.protected_frame_uids)
        if protected_event_frame_uids is None
        else protected_event_frame_uids
    )
    frame_records = (
        {item.frame_uid: item for item in frame_catalog.frames}
        if frame_record_by_uid is None
        else frame_record_by_uid
    )
    raw: list[tuple[str, float, list[str]]] = []
    for uid in domain.frame_uids:
        reasons: list[str] = []
        weight = 1.0
        if config.equalize_condition_strata:
            weight *= 1.0 / condition_counts[unit_by_frame[uid].condition.condition_id]
            reasons.append("inverse_condition_frequency")
        if uid in anchor_frames:
            weight *= config.event_anchor_multiplier; reasons.append("event_anchor")
        elif uid in protected_frames:
            weight *= config.protected_event_multiplier; reasons.append("protected_event_window")
        eligibility = frame_catalog.eligibility.for_frame(uid)
        if eligibility.state.value == "degraded":
            weight *= config.degraded_frame_multiplier; reasons.append("degraded_frame")
        raw.append((uid, weight, reasons))
    values = np.asarray([value for _, value, _ in raw], dtype=np.float64)
    values /= float(np.mean(values))
    # Project onto the declared bounds while preserving mean one. The active set
    # converges rapidly for the small number of scalar configuration weights.
    for _ in range(32):
        values = np.clip(values, config.minimum_configuration_weight, config.maximum_configuration_weight)
        delta = 1.0 - float(np.mean(values))
        if abs(delta) <= 1.0e-12:
            break
        movable = (values > config.minimum_configuration_weight + 1.0e-14) & (values < config.maximum_configuration_weight - 1.0e-14)
        if not np.any(movable):
            raise TrainingDataInputError("Configuration-weight bounds cannot preserve mean one.")
        values[movable] += delta * values.size / int(np.count_nonzero(movable))
    values = np.clip(values, config.minimum_configuration_weight, config.maximum_configuration_weight)
    if not np.isclose(float(np.mean(values)), 1.0, rtol=0.0, atol=1.0e-10):
        raise TrainingDataInputError("Configuration weights could not be normalized within bounds.")
    records = []
    for (uid, _, reasons), normalized in zip(raw, values, strict=True):
        frame = frame_records[uid]
        records.append(FrameTrainingWeight(
            frame_uid=uid, configuration_weight=float(normalized),
            energy_weight=objective.energy_weight if frame.energy_present else 0.0,
            forces_weight=objective.forces_weight if frame.forces_present else 0.0,
            stress_weight=objective.stress_weight if frame.stress_present else 0.0,
            reason_codes=tuple(reasons),
        ))
    return TrainingWeightCatalog(
        domain=domain, objective_policy=objective, configuration_policy=config,
        data4_bundle_digest=data4_bundle.content_digest, data5_bundle_digest=data5_bundle.content_digest,
        records=tuple(records),
    )


@dataclass(frozen=True, slots=True)
class CheckpointMetricPolicy:
    primary_metric: str = "target_force_component_rmse"
    focus_atom_group_ids: tuple[str, ...] = ()
    focus_atomic_numbers: tuple[int, ...] = ()
    maximum_energy_mae_ev_per_atom: float | None = None
    maximum_focus_force_rmse_ev_per_angstrom: float | None = None
    maximum_stress_rmse_ev_per_angstrom3: float | None = None
    maximum_worst_condition_force_rmse_ev_per_angstrom: float | None = None
    maximum_replay_degradation_fraction: float | None = 0.20
    policy_version: str = CHECKPOINT_METRIC_POLICY_VERSION

    def __post_init__(self) -> None:
        allowed = {"target_force_component_rmse", "target_energy_mae_per_atom", "target_combined_loss"}
        if self.primary_metric not in allowed:
            raise TrainingDataInputError("Unsupported checkpoint primary metric.")
        groups = tuple(sorted(set(str(v).strip() for v in self.focus_atom_group_ids if str(v).strip())))
        numbers = tuple(sorted(set(int(v) for v in self.focus_atomic_numbers)))
        if any(v <= 0 for v in numbers):
            raise TrainingDataInputError("Invalid checkpoint focus atomic numbers.")
        object.__setattr__(self, "focus_atom_group_ids", groups)
        object.__setattr__(self, "focus_atomic_numbers", numbers)
        for name in ("maximum_energy_mae_ev_per_atom", "maximum_focus_force_rmse_ev_per_angstrom", "maximum_stress_rmse_ev_per_angstrom3", "maximum_worst_condition_force_rmse_ev_per_angstrom", "maximum_replay_degradation_fraction"):
            value = getattr(self, name)
            if value is not None and (not np.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"{name} must be nonnegative and finite when present.")
        if self.maximum_focus_force_rmse_ev_per_angstrom is not None and not groups and not numbers:
            raise TrainingDataInputError("A focus-force checkpoint threshold requires explicit focus groups or atomic numbers.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_METRIC_POLICY_SCHEMA, "policy_version": self.policy_version,
            "primary_metric": self.primary_metric,
            "focus_atom_group_ids": list(self.focus_atom_group_ids),
            "focus_atomic_numbers": list(self.focus_atomic_numbers),
            "maximum_energy_mae_ev_per_atom": self.maximum_energy_mae_ev_per_atom,
            "maximum_focus_force_rmse_ev_per_angstrom": self.maximum_focus_force_rmse_ev_per_angstrom,
            "maximum_stress_rmse_ev_per_angstrom3": self.maximum_stress_rmse_ev_per_angstrom3,
            "maximum_worst_condition_force_rmse_ev_per_angstrom": self.maximum_worst_condition_force_rmse_ev_per_angstrom,
            "maximum_replay_degradation_fraction": self.maximum_replay_degradation_fraction,
        }

    @property
    def policy_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointMetricPolicy":
        if payload.get("schema") != CHECKPOINT_METRIC_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-metric schema.")
        result = cls(
            primary_metric=str(payload["primary_metric"]),
            focus_atom_group_ids=tuple(str(v) for v in payload.get("focus_atom_group_ids", ())),
            focus_atomic_numbers=tuple(int(v) for v in payload.get("focus_atomic_numbers", ())),
            maximum_energy_mae_ev_per_atom=None if payload.get("maximum_energy_mae_ev_per_atom") is None else float(payload["maximum_energy_mae_ev_per_atom"]),
            maximum_focus_force_rmse_ev_per_angstrom=None if payload.get("maximum_focus_force_rmse_ev_per_angstrom") is None else float(payload["maximum_focus_force_rmse_ev_per_angstrom"]),
            maximum_stress_rmse_ev_per_angstrom3=None if payload.get("maximum_stress_rmse_ev_per_angstrom3") is None else float(payload["maximum_stress_rmse_ev_per_angstrom3"]),
            maximum_worst_condition_force_rmse_ev_per_angstrom=None if payload.get("maximum_worst_condition_force_rmse_ev_per_angstrom") is None else float(payload["maximum_worst_condition_force_rmse_ev_per_angstrom"]),
            maximum_replay_degradation_fraction=None if payload.get("maximum_replay_degradation_fraction") is None else float(payload["maximum_replay_degradation_fraction"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Checkpoint-metric digest mismatch.")
        return result
