"""Temperature and source-condition records for MLFF-DATA3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

TEMPERATURE_CONDITION_SCHEMA = "mdstats.temperature-condition.v1"
TEMPERATURE_CONDITION_CATALOG_SCHEMA = "mdstats.temperature-condition-catalog.v1"


class TemperatureScheduleKind(str, Enum):
    CONSTANT = "constant"
    RAMP = "ramp"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class TemperatureTargetEvidence:
    target_start_kelvin: float | None = None
    target_end_kelvin: float | None = None
    evidence: str = "unavailable"

    def __post_init__(self) -> None:
        if not self.evidence.strip():
            raise TrainingDataInputError("Temperature target evidence must be non-empty.")
        for name in ("target_start_kelvin", "target_end_kelvin"):
            value = getattr(self, name)
            if value is not None:
                result = float(value)
                if not np.isfinite(result) or result < 0.0:
                    raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
                object.__setattr__(self, name, result)


@dataclass(frozen=True, slots=True)
class TemperatureConditionRecord:
    run_id: str
    source_identity_signature: str
    ensemble: str
    schedule_kind: TemperatureScheduleKind
    target_start_kelvin: float | None
    target_end_kelvin: float | None
    target_evidence: str
    instantaneous_count: int
    instantaneous_mean_kelvin: float | None
    instantaneous_standard_deviation_kelvin: float | None
    instantaneous_minimum_kelvin: float | None
    instantaneous_maximum_kelvin: float | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.ensemble.strip() or not self.target_evidence.strip():
            raise TrainingDataInputError("Temperature-condition identifiers must be non-empty.")
        object.__setattr__(
            self,
            "source_identity_signature",
            validate_digest(
                self.source_identity_signature, name="source_identity_signature"
            ),
        )
        object.__setattr__(self, "schedule_kind", TemperatureScheduleKind(self.schedule_kind))
        for name in (
            "target_start_kelvin",
            "target_end_kelvin",
            "instantaneous_mean_kelvin",
            "instantaneous_standard_deviation_kelvin",
            "instantaneous_minimum_kelvin",
            "instantaneous_maximum_kelvin",
        ):
            value = getattr(self, name)
            if value is not None:
                result = float(value)
                if not np.isfinite(result) or result < 0.0:
                    raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
                object.__setattr__(self, name, result)
        if self.instantaneous_count < 0:
            raise TrainingDataInputError("instantaneous_count must be nonnegative.")
        statistic_names = (
            "instantaneous_mean_kelvin",
            "instantaneous_standard_deviation_kelvin",
            "instantaneous_minimum_kelvin",
            "instantaneous_maximum_kelvin",
        )
        if self.instantaneous_count == 0 and any(
            getattr(self, name) is not None for name in statistic_names
        ):
            raise TrainingDataInputError(
                "Temperature statistics cannot be present when count is zero."
            )
        if self.instantaneous_count > 0 and any(
            getattr(self, name) is None for name in statistic_names
        ):
            raise TrainingDataInputError(
                "All temperature statistics are required when count is positive."
            )
        if self.instantaneous_count > 0:
            assert self.instantaneous_minimum_kelvin is not None
            assert self.instantaneous_mean_kelvin is not None
            assert self.instantaneous_maximum_kelvin is not None
            if not (
                self.instantaneous_minimum_kelvin
                <= self.instantaneous_mean_kelvin
                <= self.instantaneous_maximum_kelvin
            ):
                raise TrainingDataInputError(
                    "Temperature minimum, mean, and maximum are inconsistent."
                )
        if self.schedule_kind in {
            TemperatureScheduleKind.CONSTANT,
            TemperatureScheduleKind.RAMP,
        } and (
            self.target_start_kelvin is None or self.target_end_kelvin is None
        ):
            raise TrainingDataInputError(
                "Resolved thermostat schedules require start and end targets."
            )
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TEMPERATURE_CONDITION_SCHEMA,
            "run_id": self.run_id,
            "source_identity_signature": self.source_identity_signature,
            "ensemble": self.ensemble,
            "schedule_kind": self.schedule_kind.value,
            "target_start_kelvin": self.target_start_kelvin,
            "target_end_kelvin": self.target_end_kelvin,
            "target_evidence": self.target_evidence,
            "instantaneous_count": self.instantaneous_count,
            "instantaneous_mean_kelvin": self.instantaneous_mean_kelvin,
            "instantaneous_standard_deviation_kelvin": self.instantaneous_standard_deviation_kelvin,
            "instantaneous_minimum_kelvin": self.instantaneous_minimum_kelvin,
            "instantaneous_maximum_kelvin": self.instantaneous_maximum_kelvin,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TemperatureConditionRecord":
        if payload.get("schema") != TEMPERATURE_CONDITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported temperature-condition schema.")
        result = cls(
            run_id=str(payload["run_id"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            ensemble=str(payload["ensemble"]),
            schedule_kind=TemperatureScheduleKind(payload["schedule_kind"]),
            target_start_kelvin=(
                None if payload.get("target_start_kelvin") is None
                else float(payload["target_start_kelvin"])
            ),
            target_end_kelvin=(
                None if payload.get("target_end_kelvin") is None
                else float(payload["target_end_kelvin"])
            ),
            target_evidence=str(payload["target_evidence"]),
            instantaneous_count=int(payload["instantaneous_count"]),
            instantaneous_mean_kelvin=(
                None if payload.get("instantaneous_mean_kelvin") is None
                else float(payload["instantaneous_mean_kelvin"])
            ),
            instantaneous_standard_deviation_kelvin=(
                None if payload.get("instantaneous_standard_deviation_kelvin") is None
                else float(payload["instantaneous_standard_deviation_kelvin"])
            ),
            instantaneous_minimum_kelvin=(
                None if payload.get("instantaneous_minimum_kelvin") is None
                else float(payload["instantaneous_minimum_kelvin"])
            ),
            instantaneous_maximum_kelvin=(
                None if payload.get("instantaneous_maximum_kelvin") is None
                else float(payload["instantaneous_maximum_kelvin"])
            ),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Temperature-condition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TemperatureConditionCatalog:
    records: tuple[TemperatureConditionRecord, ...]
    _by_run_id: Mapping[str, TemperatureConditionRecord] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        records = tuple(sorted(self.records, key=lambda item: item.run_id))
        if len({item.run_id for item in records}) != len(records):
            raise TrainingDataInputError("Duplicate run IDs in temperature catalog.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_by_run_id", {item.run_id: item for item in records})

    def for_run(self, run_id: str) -> TemperatureConditionRecord:
        try:
            return self._by_run_id[run_id]
        except KeyError:
            raise KeyError(run_id) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TEMPERATURE_CONDITION_CATALOG_SCHEMA,
            "records": [item.to_dict() for item in self.records],
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
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TemperatureConditionCatalog":
        if payload.get("schema") != TEMPERATURE_CONDITION_CATALOG_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported temperature-condition-catalog schema."
            )
        result = cls(
            records=tuple(
                TemperatureConditionRecord.from_dict(item)
                for item in payload.get("records", ())
            )
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Temperature-condition-catalog digest mismatch."
            )
        return result


def build_temperature_condition(
    *,
    run_id: str,
    source_identity_signature: str,
    ensemble: str,
    instantaneous_temperatures_kelvin: Sequence[float] | np.ndarray | None,
    target_start_kelvin: float | None = None,
    target_end_kelvin: float | None = None,
    target_evidence: str = "unavailable",
) -> TemperatureConditionRecord:
    values = (
        np.empty(0, dtype=np.float64)
        if instantaneous_temperatures_kelvin is None
        else np.asarray(instantaneous_temperatures_kelvin, dtype=np.float64)
    )
    if values.ndim != 1:
        raise TrainingDataInputError("Instantaneous temperatures must be one-dimensional.")
    finite = values[np.isfinite(values)]
    if np.any(finite < 0.0):
        raise TrainingDataInputError("Instantaneous temperatures must be nonnegative.")

    ensemble_lower = ensemble.lower()
    if target_start_kelvin is None and target_end_kelvin is None:
        if "nve" in ensemble_lower or ensemble_lower in {"microcanonical", "nph"}:
            schedule = TemperatureScheduleKind.NOT_APPLICABLE
        else:
            schedule = TemperatureScheduleKind.UNRESOLVED
    else:
        start = target_start_kelvin if target_start_kelvin is not None else target_end_kelvin
        end = target_end_kelvin if target_end_kelvin is not None else target_start_kelvin
        assert start is not None and end is not None
        schedule = (
            TemperatureScheduleKind.CONSTANT
            if abs(float(start) - float(end)) <= 1.0e-10
            else TemperatureScheduleKind.RAMP
        )
        target_start_kelvin = float(start)
        target_end_kelvin = float(end)

    return TemperatureConditionRecord(
        run_id=run_id,
        source_identity_signature=source_identity_signature,
        ensemble=ensemble,
        schedule_kind=schedule,
        target_start_kelvin=target_start_kelvin,
        target_end_kelvin=target_end_kelvin,
        target_evidence=target_evidence,
        instantaneous_count=int(finite.size),
        instantaneous_mean_kelvin=None if finite.size == 0 else float(np.mean(finite)),
        instantaneous_standard_deviation_kelvin=(
            None if finite.size == 0 else float(np.std(finite))
        ),
        instantaneous_minimum_kelvin=None if finite.size == 0 else float(np.min(finite)),
        instantaneous_maximum_kelvin=None if finite.size == 0 else float(np.max(finite)),
        notes=(
            ()
            if finite.size == values.size
            else (f"Ignored {values.size - finite.size} non-finite temperature values.",)
        ),
    )
