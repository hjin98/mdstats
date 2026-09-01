"""EVAL2 target-first checkpoint-trajectory evaluation authorities.

EVAL2 is the static-evidence counterpart to TRAIN2B.  It never mutates the
optimizer or LR schedule.  Replay is evaluated as a hard admissibility
constraint only; all ordering is target-side and uncertainty-aware.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, Sequence

import numpy as np
from ase.data import chemical_symbols
from ase.stress import full_3x3_to_voigt_6_stress

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .train2_policy import CheckpointAdmissibilityPolicy, CheckpointSelectionPolicy

EVAL2_TRAJECTORY_POINT_SCHEMA = "mdstats.eval2-trajectory-point.v1"
EVAL2_TARGET_BLOCK_METRIC_SCHEMA = "mdstats.eval2-target-block-metric.v1"
EVAL2_TARGET_METRIC_SCHEMA = "mdstats.eval2-target-metric.v1"
EVAL2_CHECKPOINT_RECORD_SCHEMA = "mdstats.eval2-checkpoint-record.v1"
EVAL2_BOOTSTRAP_COMPARISON_SCHEMA = "mdstats.eval2-bootstrap-comparison.v1"
EVAL2_RUN_RECORD_SCHEMA = "mdstats.eval2-run-record.v1"
EVAL2_EVALUATION_PLAN_SCHEMA = "mdstats.eval2-evaluation-plan.v1"
EVAL2_NUMERICAL_FAILURE_SCHEMA = "mdstats.eval2-numerical-failure.v1"
EVAL2_NUMERICAL_FAILURE_CODES = frozenset({
    "eval_nonfinite_energy_prediction",
    "eval_nonfinite_force_prediction",
    "eval_nonfinite_stress_prediction",
    "eval_nonfinite_target_metric",
})


class Eval2NumericalEvaluationError(RuntimeError):
    """Positive non-finite scientific failure during target-only EVAL2.

    Shape, schema, lineage, missing-artifact, and programming defects remain
    ordinary errors and are never converted to target-size scientific evidence.
    """

    def __init__(
        self, failure_code: str, reason: str, *, target_role_digest: str, prediction_digest: str
    ) -> None:
        code = str(failure_code)
        if code not in EVAL2_NUMERICAL_FAILURE_CODES:
            raise ValueError(f"Unsupported EVAL2 numerical failure code: {code!r}")
        self.failure_code = code
        self.reason = str(reason)
        self.target_role_digest = validate_digest(target_role_digest, name="target_role_digest")
        self.prediction_digest = validate_digest(prediction_digest, name="prediction_digest")
        self.content_digest = digest({
            "schema": EVAL2_NUMERICAL_FAILURE_SCHEMA,
            "failure_code": self.failure_code,
            "reason": self.reason,
            "target_role_digest": self.target_role_digest,
            "prediction_digest": self.prediction_digest,
        })
        super().__init__(f"{self.failure_code}: {self.reason}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": EVAL2_NUMERICAL_FAILURE_SCHEMA,
            "failure_code": self.failure_code,
            "reason": self.reason,
            "target_role_digest": self.target_role_digest,
            "prediction_digest": self.prediction_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Eval2NumericalEvaluationError:
        if payload.get("schema") != EVAL2_NUMERICAL_FAILURE_SCHEMA:
            raise TrainingDataSerializationError("Invalid EVAL2 numerical failure schema.")
        result = cls(
            failure_code=str(payload["failure_code"]),
            reason=str(payload.get("reason", "")),
            target_role_digest=str(payload["target_role_digest"]),
            prediction_digest=str(payload["prediction_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "EVAL2 numerical failure digest mismatch."
            )
        return result


# AUDIT-EVAL-PERF1 execution-only cache.  The authoritative target-role and
# prediction digests remain the scientific identity; this cache only retains
# immutable indexing metadata that is otherwise rebuilt for every checkpoint.
@dataclass(frozen=True, slots=True)
class _Eval2StaticReductionMetadata:
    view: Any
    block_ids: tuple[str, ...]
    composition_keys: tuple[tuple[tuple[int, int], ...], ...]
    species_atomic_numbers: tuple[int, ...]
    species_groups_per_frame: tuple[tuple[tuple[int, np.ndarray], ...], ...]
    focus_masks_per_frame: tuple[np.ndarray | None, ...]
    block_labels: tuple[str, ...]
    block_codes: np.ndarray
    resident_bytes: int


_EVAL2_STATIC_CACHE: "OrderedDict[tuple[int, tuple[str, ...]], _Eval2StaticReductionMetadata]" = OrderedDict()
_EVAL2_STATIC_CACHE_LOCK = RLock()
_EVAL2_STATIC_CACHE_MAX_BYTES = max(
    0, int(os.environ.get("MDSTATS_MLFF_EVAL2_STATIC_CACHE_BYTES", str(256 * 1024**2)))
)
_EVAL2_STATIC_CACHE_BYTES = 0


def _build_eval2_static_reduction_metadata(
    view: Any, block_ids: Sequence[str]
) -> _Eval2StaticReductionMetadata:
    count = int(view.configuration_count)
    blocks = tuple(str(value) for value in block_ids)
    if len(blocks) != count:
        raise TrainingDataInputError("EVAL2 target block IDs do not match the target role.")
    block_labels = tuple(sorted(set(blocks)))
    block_index = {value: index for index, value in enumerate(block_labels)}
    block_codes = np.asarray([block_index[value] for value in blocks], dtype=np.int32)
    block_codes.setflags(write=False)

    all_species = tuple(int(value) for value in np.unique(np.asarray(view.atomic_numbers, dtype=np.int64)))
    species_index = {value: index for index, value in enumerate(all_species)}
    composition_keys: list[tuple[tuple[int, int], ...]] = []
    species_groups: list[tuple[tuple[int, np.ndarray], ...]] = []
    focus_masks: list[np.ndarray | None] = []
    focus_numbers = np.asarray(tuple(int(v) for v in getattr(view, "focus_atomic_numbers", ())), dtype=np.int64)
    resident_bytes = int(block_codes.nbytes)

    for frame_index in range(count):
        start = int(view.force_offsets[frame_index])
        stop = int(view.force_offsets[frame_index + 1])
        numbers = np.asarray(view.atomic_numbers[start:stop], dtype=np.int64)
        unique_z, unique_counts = np.unique(numbers, return_counts=True)
        composition_keys.append(tuple((int(z), int(n)) for z, n in zip(unique_z, unique_counts)))
        frame_groups: list[tuple[int, np.ndarray]] = []
        for z in unique_z:
            local = np.flatnonzero(numbers == int(z)).astype(np.int32, copy=False)
            local.setflags(write=False)
            resident_bytes += int(local.nbytes)
            frame_groups.append((species_index[int(z)], local))
        species_groups.append(tuple(frame_groups))
        if focus_numbers.size:
            mask = np.isin(numbers, focus_numbers)
            mask.setflags(write=False)
            resident_bytes += int(mask.nbytes)
            focus_masks.append(mask)
        else:
            focus_masks.append(None)

    return _Eval2StaticReductionMetadata(
        view=view,
        block_ids=blocks,
        composition_keys=tuple(composition_keys),
        species_atomic_numbers=all_species,
        species_groups_per_frame=tuple(species_groups),
        focus_masks_per_frame=tuple(focus_masks),
        block_labels=block_labels,
        block_codes=block_codes,
        resident_bytes=max(1, resident_bytes),
    )


def _eval2_static_reduction_metadata(
    view: Any, block_ids: Sequence[str]
) -> _Eval2StaticReductionMetadata:
    """Return immutable EVAL2 indexing metadata without changing authority."""

    global _EVAL2_STATIC_CACHE_BYTES
    blocks = tuple(str(value) for value in block_ids)
    key = (id(view), blocks)
    with _EVAL2_STATIC_CACHE_LOCK:
        cached = _EVAL2_STATIC_CACHE.get(key)
        if cached is not None and cached.view is view:
            _EVAL2_STATIC_CACHE.move_to_end(key)
            return cached
    built = _build_eval2_static_reduction_metadata(view, blocks)
    with _EVAL2_STATIC_CACHE_LOCK:
        cached = _EVAL2_STATIC_CACHE.get(key)
        if cached is not None and cached.view is view:
            _EVAL2_STATIC_CACHE.move_to_end(key)
            return cached
        if _EVAL2_STATIC_CACHE_MAX_BYTES <= 0 or built.resident_bytes > _EVAL2_STATIC_CACHE_MAX_BYTES:
            return built
        _EVAL2_STATIC_CACHE[key] = built
        _EVAL2_STATIC_CACHE_BYTES += built.resident_bytes
        while _EVAL2_STATIC_CACHE and _EVAL2_STATIC_CACHE_BYTES > _EVAL2_STATIC_CACHE_MAX_BYTES:
            _, removed = _EVAL2_STATIC_CACHE.popitem(last=False)
            _EVAL2_STATIC_CACHE_BYTES -= removed.resident_bytes
        return built


def clear_eval2_static_reduction_cache() -> None:
    global _EVAL2_STATIC_CACHE_BYTES
    with _EVAL2_STATIC_CACHE_LOCK:
        _EVAL2_STATIC_CACHE.clear()
        _EVAL2_STATIC_CACHE_BYTES = 0


def _finite_nonnegative(value: float, *, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return value


def _optional_metric(value: float | None, *, name: str) -> float | None:
    return None if value is None else _finite_nonnegative(value, name=name)


def _validate_record_digest(payload: Mapping[str, Any], current: str, *, name: str) -> None:
    if payload.get("content_digest") not in (None, current):
        raise TrainingDataSerializationError(f"{name} digest mismatch.")













@dataclass(frozen=True, slots=True)
class Eval2TrajectoryPoint:
    """One durable TRAIN2 checkpoint with lightweight target diagnostics."""

    epoch: int
    checkpoint_sha256: str
    lightweight_target_score_ev_per_angstrom: float
    normalized_schedule_progress: float
    instantaneous_learning_rate: float
    phase: str
    runtime_summary_digest: str
    stable_candidate_identity: str
    serialization_schema: str = field(default=EVAL2_TRAJECTORY_POINT_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_TRAJECTORY_POINT_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 trajectory-point schema.")
        if int(self.epoch) < 0:
            raise TrainingDataInputError("EVAL2 checkpoint epoch must be nonnegative.")
        object.__setattr__(self, "epoch", int(self.epoch))
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        object.__setattr__(self, "runtime_summary_digest", validate_digest(self.runtime_summary_digest, name="runtime_summary_digest"))
        object.__setattr__(
            self,
            "lightweight_target_score_ev_per_angstrom",
            _finite_nonnegative(self.lightweight_target_score_ev_per_angstrom, name="lightweight target score"),
        )
        progress = float(self.normalized_schedule_progress)
        if not math.isfinite(progress) or progress < 0.0 or progress > 1.0:
            raise TrainingDataInputError("EVAL2 trajectory progress must lie in [0,1].")
        object.__setattr__(self, "normalized_schedule_progress", progress)
        lr = float(self.instantaneous_learning_rate)
        if not math.isfinite(lr) or lr <= 0.0:
            raise TrainingDataInputError("EVAL2 trajectory LR must be finite and positive.")
        object.__setattr__(self, "instantaneous_learning_rate", lr)
        phase = str(self.phase).strip().lower()
        if phase not in {"warmup", "adaptation", "refinement"}:
            raise TrainingDataInputError("Unsupported EVAL2 TRAIN2 phase.")
        object.__setattr__(self, "phase", phase)
        identity = str(self.stable_candidate_identity).strip()
        if not identity:
            raise TrainingDataInputError("EVAL2 stable candidate identity cannot be empty.")
        object.__setattr__(self, "stable_candidate_identity", identity)

    @property
    def in_refinement_phase(self) -> bool:
        return self.phase == "refinement"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "epoch": self.epoch,
            "checkpoint_sha256": self.checkpoint_sha256,
            "lightweight_target_score_ev_per_angstrom": self.lightweight_target_score_ev_per_angstrom,
            "normalized_schedule_progress": self.normalized_schedule_progress,
            "instantaneous_learning_rate": self.instantaneous_learning_rate,
            "phase": self.phase,
            "runtime_summary_digest": self.runtime_summary_digest,
            "stable_candidate_identity": self.stable_candidate_identity,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2TrajectoryPoint":
        if payload.get("schema") != EVAL2_TRAJECTORY_POINT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 trajectory-point schema.")
        result = cls(
            epoch=int(payload["epoch"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            lightweight_target_score_ev_per_angstrom=float(payload["lightweight_target_score_ev_per_angstrom"]),
            normalized_schedule_progress=float(payload["normalized_schedule_progress"]),
            instantaneous_learning_rate=float(payload["instantaneous_learning_rate"]),
            phase=str(payload["phase"]),
            runtime_summary_digest=str(payload["runtime_summary_digest"]),
            stable_candidate_identity=str(payload["stable_candidate_identity"]),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 trajectory-point")
        return result


@dataclass(frozen=True, slots=True)
class Eval2TargetBlockMetric:
    block_id: str
    force_squared_error_sum: float
    force_component_count: int
    configuration_count: int
    serialization_schema: str = field(default=EVAL2_TARGET_BLOCK_METRIC_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_TARGET_BLOCK_METRIC_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 block-metric schema.")
        block = str(self.block_id).strip()
        if not block:
            raise TrainingDataInputError("EVAL2 block ID cannot be empty.")
        object.__setattr__(self, "block_id", block)
        object.__setattr__(self, "force_squared_error_sum", _finite_nonnegative(self.force_squared_error_sum, name="block force SSE"))
        if int(self.force_component_count) <= 0 or int(self.configuration_count) <= 0:
            raise TrainingDataInputError("EVAL2 block counts must be positive.")
        object.__setattr__(self, "force_component_count", int(self.force_component_count))
        object.__setattr__(self, "configuration_count", int(self.configuration_count))

    @property
    def force_rmse_ev_per_angstrom(self) -> float:
        return math.sqrt(self.force_squared_error_sum / self.force_component_count)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "block_id": self.block_id,
            "force_squared_error_sum": self.force_squared_error_sum,
            "force_component_count": self.force_component_count,
            "configuration_count": self.configuration_count,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2TargetBlockMetric":
        if payload.get("schema") != EVAL2_TARGET_BLOCK_METRIC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 block-metric schema.")
        result = cls(
            block_id=str(payload["block_id"]),
            force_squared_error_sum=float(payload["force_squared_error_sum"]),
            force_component_count=int(payload["force_component_count"]),
            configuration_count=int(payload["configuration_count"]),
        )
        expected = result.to_dict()["content_digest"]
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("EVAL2 block-metric digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Eval2TargetMetricRecord:
    """Full target-side metric evidence used by EVAL2 ordering."""

    configuration_count: int
    atom_count: int
    energy_mae_ev_per_atom: float
    relative_energy_rmse_ev_per_atom: float | None
    force_component_rmse_ev_per_angstrom: float
    species_macro_force_rmse_ev_per_angstrom: float
    species_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...]
    force_error_p90_ev_per_angstrom: float
    force_error_p95_ev_per_angstrom: float
    force_error_p99_ev_per_angstrom: float
    worst_stratum_force_rmse_ev_per_angstrom: float | None
    stratum_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...]
    stress_rmse_ev_per_angstrom3: float | None
    block_metrics: tuple[Eval2TargetBlockMetric, ...]
    target_role_digest: str
    prediction_digest: str
    serialization_schema: str = field(default=EVAL2_TARGET_METRIC_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_TARGET_METRIC_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 target-metric schema.")
        if int(self.configuration_count) <= 0 or int(self.atom_count) <= 0:
            raise TrainingDataInputError("EVAL2 target metric counts must be positive.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        object.__setattr__(self, "atom_count", int(self.atom_count))
        for name in (
            "energy_mae_ev_per_atom",
            "force_component_rmse_ev_per_angstrom",
            "species_macro_force_rmse_ev_per_angstrom",
            "force_error_p90_ev_per_angstrom",
            "force_error_p95_ev_per_angstrom",
            "force_error_p99_ev_per_angstrom",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=f"EVAL2 {name}"))
        object.__setattr__(self, "relative_energy_rmse_ev_per_atom", _optional_metric(self.relative_energy_rmse_ev_per_atom, name="EVAL2 relative-energy RMSE"))
        object.__setattr__(self, "worst_stratum_force_rmse_ev_per_angstrom", _optional_metric(self.worst_stratum_force_rmse_ev_per_angstrom, name="EVAL2 worst-stratum RMSE"))
        object.__setattr__(self, "stress_rmse_ev_per_angstrom3", _optional_metric(self.stress_rmse_ev_per_angstrom3, name="EVAL2 stress RMSE"))
        species = tuple(sorted((str(k), _finite_nonnegative(v, name=f"EVAL2 species RMSE {k}")) for k, v in self.species_force_rmse_ev_per_angstrom))
        strata = tuple(sorted((str(k), _finite_nonnegative(v, name=f"EVAL2 stratum RMSE {k}")) for k, v in self.stratum_force_rmse_ev_per_angstrom))
        if any(not k for k, _ in species) or len({k for k, _ in species}) != len(species):
            raise TrainingDataInputError("EVAL2 species metric IDs must be unique and non-empty.")
        if any(not k for k, _ in strata) or len({k for k, _ in strata}) != len(strata):
            raise TrainingDataInputError("EVAL2 stratum metric IDs must be unique and non-empty.")
        object.__setattr__(self, "species_force_rmse_ev_per_angstrom", species)
        object.__setattr__(self, "stratum_force_rmse_ev_per_angstrom", strata)
        blocks = tuple(sorted(self.block_metrics, key=lambda x: x.block_id))
        if not blocks or len({x.block_id for x in blocks}) != len(blocks):
            raise TrainingDataInputError("EVAL2 target metrics require unique non-empty correlation blocks.")
        if sum(x.configuration_count for x in blocks) != self.configuration_count:
            raise TrainingDataInputError("EVAL2 block configuration counts do not cover the target role.")
        object.__setattr__(self, "block_metrics", blocks)
        object.__setattr__(self, "target_role_digest", validate_digest(self.target_role_digest, name="target_role_digest"))
        object.__setattr__(self, "prediction_digest", validate_digest(self.prediction_digest, name="prediction_digest"))

    def secondary_values(self, policy: CheckpointSelectionPolicy) -> tuple[float | None, ...]:
        known: dict[str, float | None] = {
            "worst_stratum_force_rmse_ev_per_angstrom": self.worst_stratum_force_rmse_ev_per_angstrom,
            "species_macro_force_rmse_ev_per_angstrom": self.species_macro_force_rmse_ev_per_angstrom,
            "force_error_p95_ev_per_angstrom": self.force_error_p95_ev_per_angstrom,
            "force_error_p99_ev_per_angstrom": self.force_error_p99_ev_per_angstrom,
        }
        unknown = [name for name in policy.secondary_target_metrics if name not in known]
        if unknown:
            raise TrainingDataInputError(f"EVAL2 does not implement secondary target metric(s): {unknown}.")
        return tuple(known[name] for name in policy.secondary_target_metrics)

    def block_map(self) -> dict[str, Eval2TargetBlockMetric]:
        return {item.block_id: item for item in self.block_metrics}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "configuration_count": self.configuration_count,
            "atom_count": self.atom_count,
            "energy_mae_ev_per_atom": self.energy_mae_ev_per_atom,
            "relative_energy_rmse_ev_per_atom": self.relative_energy_rmse_ev_per_atom,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
            "species_macro_force_rmse_ev_per_angstrom": self.species_macro_force_rmse_ev_per_angstrom,
            "species_force_rmse_ev_per_angstrom": dict(self.species_force_rmse_ev_per_angstrom),
            "force_error_p90_ev_per_angstrom": self.force_error_p90_ev_per_angstrom,
            "force_error_p95_ev_per_angstrom": self.force_error_p95_ev_per_angstrom,
            "force_error_p99_ev_per_angstrom": self.force_error_p99_ev_per_angstrom,
            "worst_stratum_force_rmse_ev_per_angstrom": self.worst_stratum_force_rmse_ev_per_angstrom,
            "stratum_force_rmse_ev_per_angstrom": dict(self.stratum_force_rmse_ev_per_angstrom),
            "stress_rmse_ev_per_angstrom3": self.stress_rmse_ev_per_angstrom3,
            "block_metrics": [item.to_dict() for item in self.block_metrics],
            "target_role_digest": self.target_role_digest,
            "prediction_digest": self.prediction_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2TargetMetricRecord":
        if payload.get("schema") != EVAL2_TARGET_METRIC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 target-metric schema.")
        result = cls(
            configuration_count=int(payload["configuration_count"]),
            atom_count=int(payload["atom_count"]),
            energy_mae_ev_per_atom=float(payload["energy_mae_ev_per_atom"]),
            relative_energy_rmse_ev_per_atom=(None if payload.get("relative_energy_rmse_ev_per_atom") is None else float(payload["relative_energy_rmse_ev_per_atom"])),
            force_component_rmse_ev_per_angstrom=float(payload["force_component_rmse_ev_per_angstrom"]),
            species_macro_force_rmse_ev_per_angstrom=float(payload["species_macro_force_rmse_ev_per_angstrom"]),
            species_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("species_force_rmse_ev_per_angstrom", {}).items()),
            force_error_p90_ev_per_angstrom=float(payload["force_error_p90_ev_per_angstrom"]),
            force_error_p95_ev_per_angstrom=float(payload["force_error_p95_ev_per_angstrom"]),
            force_error_p99_ev_per_angstrom=float(payload["force_error_p99_ev_per_angstrom"]),
            worst_stratum_force_rmse_ev_per_angstrom=(None if payload.get("worst_stratum_force_rmse_ev_per_angstrom") is None else float(payload["worst_stratum_force_rmse_ev_per_angstrom"])),
            stratum_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("stratum_force_rmse_ev_per_angstrom", {}).items()),
            stress_rmse_ev_per_angstrom3=(None if payload.get("stress_rmse_ev_per_angstrom3") is None else float(payload["stress_rmse_ev_per_angstrom3"])),
            block_metrics=tuple(Eval2TargetBlockMetric.from_dict(v) for v in payload["block_metrics"]),
            target_role_digest=str(payload["target_role_digest"]),
            prediction_digest=str(payload["prediction_digest"]),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 target metric")
        return result


@dataclass(frozen=True, slots=True)
class Eval2BootstrapComparison:
    first_candidate_identity: str
    second_candidate_identity: str
    first_minus_second_ev_per_angstrom: float
    confidence_low_ev_per_angstrom: float | None
    confidence_high_ev_per_angstrom: float | None
    independent_block_count: int
    bootstrap_replicates: int
    bootstrap_confidence: float
    decision: str
    seed: int | None
    serialization_schema: str = field(default=EVAL2_BOOTSTRAP_COMPARISON_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_BOOTSTRAP_COMPARISON_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 bootstrap-comparison schema.")
        if self.decision not in {"first_materially_better", "second_materially_better", "indistinguishable", "insufficient_blocks"}:
            raise TrainingDataInputError("Unsupported EVAL2 bootstrap decision.")
        if int(self.independent_block_count) <= 0 or int(self.bootstrap_replicates) <= 0:
            raise TrainingDataInputError("EVAL2 bootstrap counts must be positive.")
        if not 0.0 < float(self.bootstrap_confidence) < 1.0:
            raise TrainingDataInputError("EVAL2 bootstrap confidence must lie in (0,1).")
        delta = float(self.first_minus_second_ev_per_angstrom)
        if not math.isfinite(delta):
            raise TrainingDataInputError("EVAL2 bootstrap metric difference must be finite.")
        object.__setattr__(self, "first_minus_second_ev_per_angstrom", delta)
        for name in ("confidence_low_ev_per_angstrom", "confidence_high_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise TrainingDataInputError("EVAL2 bootstrap confidence bounds must be finite.")
        if (self.confidence_low_ev_per_angstrom is None) != (self.confidence_high_ev_per_angstrom is None):
            raise TrainingDataInputError("EVAL2 bootstrap confidence bounds must be stored together.")
        if self.seed is not None and int(self.seed) < 0:
            raise TrainingDataInputError("EVAL2 bootstrap seed must be nonnegative.")
        object.__setattr__(self, "independent_block_count", int(self.independent_block_count))
        object.__setattr__(self, "bootstrap_replicates", int(self.bootstrap_replicates))
        object.__setattr__(self, "bootstrap_confidence", float(self.bootstrap_confidence))
        object.__setattr__(self, "seed", None if self.seed is None else int(self.seed))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "first_candidate_identity": self.first_candidate_identity,
            "second_candidate_identity": self.second_candidate_identity,
            "first_minus_second_ev_per_angstrom": self.first_minus_second_ev_per_angstrom,
            "confidence_low_ev_per_angstrom": self.confidence_low_ev_per_angstrom,
            "confidence_high_ev_per_angstrom": self.confidence_high_ev_per_angstrom,
            "independent_block_count": self.independent_block_count,
            "bootstrap_replicates": self.bootstrap_replicates,
            "bootstrap_confidence": self.bootstrap_confidence,
            "decision": self.decision,
            "seed": self.seed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2BootstrapComparison":
        if payload.get("schema") != EVAL2_BOOTSTRAP_COMPARISON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 bootstrap-comparison schema.")
        result = cls(
            first_candidate_identity=str(payload["first_candidate_identity"]),
            second_candidate_identity=str(payload["second_candidate_identity"]),
            first_minus_second_ev_per_angstrom=float(payload["first_minus_second_ev_per_angstrom"]),
            confidence_low_ev_per_angstrom=None if payload.get("confidence_low_ev_per_angstrom") is None else float(payload["confidence_low_ev_per_angstrom"]),
            confidence_high_ev_per_angstrom=None if payload.get("confidence_high_ev_per_angstrom") is None else float(payload["confidence_high_ev_per_angstrom"]),
            independent_block_count=int(payload["independent_block_count"]),
            bootstrap_replicates=int(payload["bootstrap_replicates"]),
            bootstrap_confidence=float(payload["bootstrap_confidence"]),
            decision=str(payload["decision"]),
            seed=None if payload.get("seed") is None else int(payload["seed"]),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 bootstrap comparison")
        return result


@dataclass(frozen=True, slots=True)
class Eval2CheckpointRecord:
    trajectory_point: Eval2TrajectoryPoint
    evaluation_record_digest: str
    target_metrics: Eval2TargetMetricRecord
    replay_candidate_force_rmse_ev_per_angstrom: float | None
    replay_foundation_force_rmse_ev_per_angstrom: float | None
    replay_degradation_ev_per_angstrom: float | None
    replay_label_mode: str | None
    admissible: bool
    rejection_reasons: tuple[str, ...]
    shortlist_reasons: tuple[str, ...] = ()
    full_evaluation_rank: int = 0
    serialization_schema: str = field(default=EVAL2_CHECKPOINT_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_CHECKPOINT_RECORD_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 checkpoint-record schema.")
        object.__setattr__(self, "evaluation_record_digest", validate_digest(self.evaluation_record_digest, name="evaluation_record_digest"))
        for name in (
            "replay_candidate_force_rmse_ev_per_angstrom",
            "replay_foundation_force_rmse_ev_per_angstrom",
        ):
            object.__setattr__(self, name, _optional_metric(getattr(self, name), name=f"EVAL2 {name}"))
        degradation = self.replay_degradation_ev_per_angstrom
        if degradation is not None:
            degradation = float(degradation)
            if not math.isfinite(degradation):
                raise TrainingDataInputError("EVAL2 replay degradation must be finite when present.")
        object.__setattr__(self, "replay_degradation_ev_per_angstrom", degradation)
        mode = None if self.replay_label_mode in (None, "") else str(self.replay_label_mode).strip().lower()
        object.__setattr__(self, "replay_label_mode", mode)
        object.__setattr__(self, "rejection_reasons", tuple(sorted(set(str(v) for v in self.rejection_reasons))))
        object.__setattr__(self, "shortlist_reasons", tuple(sorted(set(str(v) for v in self.shortlist_reasons))))
        if int(self.full_evaluation_rank) < 0:
            raise TrainingDataInputError("EVAL2 full-evaluation rank cannot be negative.")
        object.__setattr__(self, "full_evaluation_rank", int(self.full_evaluation_rank))
        if bool(self.admissible) != (len(self.rejection_reasons) == 0):
            raise TrainingDataInputError("EVAL2 admissible flag disagrees with rejection reasons.")

    @property
    def stable_candidate_identity(self) -> str:
        return self.trajectory_point.stable_candidate_identity

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "trajectory_point": self.trajectory_point.to_dict(),
            "evaluation_record_digest": self.evaluation_record_digest,
            "target_metrics": self.target_metrics.to_dict(),
            "replay_candidate_force_rmse_ev_per_angstrom": self.replay_candidate_force_rmse_ev_per_angstrom,
            "replay_foundation_force_rmse_ev_per_angstrom": self.replay_foundation_force_rmse_ev_per_angstrom,
            "replay_degradation_ev_per_angstrom": self.replay_degradation_ev_per_angstrom,
            "replay_label_mode": self.replay_label_mode,
            "admissible": bool(self.admissible),
            "rejection_reasons": list(self.rejection_reasons),
            "shortlist_reasons": list(self.shortlist_reasons),
            "full_evaluation_rank": self.full_evaluation_rank,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2CheckpointRecord":
        if payload.get("schema") != EVAL2_CHECKPOINT_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 checkpoint-record schema.")
        result = cls(
            trajectory_point=Eval2TrajectoryPoint.from_dict(payload["trajectory_point"]),
            evaluation_record_digest=str(payload["evaluation_record_digest"]),
            target_metrics=Eval2TargetMetricRecord.from_dict(payload["target_metrics"]),
            replay_candidate_force_rmse_ev_per_angstrom=None if payload.get("replay_candidate_force_rmse_ev_per_angstrom") is None else float(payload["replay_candidate_force_rmse_ev_per_angstrom"]),
            replay_foundation_force_rmse_ev_per_angstrom=None if payload.get("replay_foundation_force_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_force_rmse_ev_per_angstrom"]),
            replay_degradation_ev_per_angstrom=None if payload.get("replay_degradation_ev_per_angstrom") is None else float(payload["replay_degradation_ev_per_angstrom"]),
            replay_label_mode=None if payload.get("replay_label_mode") is None else str(payload["replay_label_mode"]),
            admissible=bool(payload["admissible"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
            shortlist_reasons=tuple(str(v) for v in payload.get("shortlist_reasons", ())),
            full_evaluation_rank=int(payload.get("full_evaluation_rank", 0)),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 checkpoint record")
        return result


@dataclass(frozen=True, slots=True)
class Eval2EvaluationPlan:
    run_plan_digest: str
    training_protocol_digest: str
    selection_policy_digest: str
    admissibility_policy_digest: str
    target_role_digest: str
    replay_role_digest: str | None
    candidate_rescue_cap: int
    bootstrap_seed_material_digest: str
    serialization_schema: str = field(default=EVAL2_EVALUATION_PLAN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_EVALUATION_PLAN_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 evaluation-plan schema.")
        for name in (
            "run_plan_digest", "training_protocol_digest", "selection_policy_digest",
            "admissibility_policy_digest", "target_role_digest", "bootstrap_seed_material_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.replay_role_digest is not None:
            object.__setattr__(self, "replay_role_digest", validate_digest(self.replay_role_digest, name="replay_role_digest"))
        if int(self.candidate_rescue_cap) < 0:
            raise TrainingDataInputError("EVAL2 candidate rescue cap cannot be negative.")
        object.__setattr__(self, "candidate_rescue_cap", int(self.candidate_rescue_cap))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "training_protocol_digest": self.training_protocol_digest,
            "selection_policy_digest": self.selection_policy_digest,
            "admissibility_policy_digest": self.admissibility_policy_digest,
            "target_role_digest": self.target_role_digest,
            "replay_role_digest": self.replay_role_digest,
            "candidate_rescue_cap": self.candidate_rescue_cap,
            "bootstrap_seed_material_digest": self.bootstrap_seed_material_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2EvaluationPlan":
        if payload.get("schema") != EVAL2_EVALUATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 evaluation-plan schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            training_protocol_digest=str(payload["training_protocol_digest"]),
            selection_policy_digest=str(payload["selection_policy_digest"]),
            admissibility_policy_digest=str(payload["admissibility_policy_digest"]),
            target_role_digest=str(payload["target_role_digest"]),
            replay_role_digest=None if payload.get("replay_role_digest") is None else str(payload["replay_role_digest"]),
            candidate_rescue_cap=int(payload["candidate_rescue_cap"]),
            bootstrap_seed_material_digest=str(payload["bootstrap_seed_material_digest"]),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 evaluation plan")
        return result


@dataclass(frozen=True, slots=True)
class Eval2RunRecord:
    evaluation_plan: Eval2EvaluationPlan
    trajectory_points: tuple[Eval2TrajectoryPoint, ...]
    initial_shortlist_checkpoint_sha256s: tuple[str, ...]
    evaluated_checkpoints: tuple[Eval2CheckpointRecord, ...]
    bootstrap_comparisons: tuple[Eval2BootstrapComparison, ...]
    selected_checkpoint_sha256: str | None
    selected_checkpoint_epoch: int | None
    outcome: str
    rescue_evaluated_count: int = 0
    serialization_schema: str = field(default=EVAL2_RUN_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != EVAL2_RUN_RECORD_SCHEMA:
            raise TrainingDataInputError("Unsupported EVAL2 run-record schema.")
        points = tuple(sorted(self.trajectory_points, key=lambda x: x.epoch))
        if not points or len({x.checkpoint_sha256 for x in points}) != len(points) or len({x.epoch for x in points}) != len(points):
            raise TrainingDataInputError("EVAL2 run trajectory must contain unique durable checkpoints.")
        object.__setattr__(self, "trajectory_points", points)
        shortlist = tuple(validate_digest(v, name="checkpoint_sha256") for v in self.initial_shortlist_checkpoint_sha256s)
        if len(shortlist) != len(set(shortlist)) or any(v not in {x.checkpoint_sha256 for x in points} for v in shortlist):
            raise TrainingDataInputError("EVAL2 initial shortlist is inconsistent with the trajectory.")
        object.__setattr__(self, "initial_shortlist_checkpoint_sha256s", shortlist)
        evaluated = tuple(self.evaluated_checkpoints)
        if len({x.trajectory_point.checkpoint_sha256 for x in evaluated}) != len(evaluated):
            raise TrainingDataInputError("EVAL2 run record contains duplicate full evaluations.")
        object.__setattr__(self, "evaluated_checkpoints", evaluated)
        if self.outcome not in {"selected", "no_admissible_checkpoint", "awaiting_more_evaluations"}:
            raise TrainingDataInputError("Unsupported EVAL2 run outcome.")
        if self.outcome == "selected":
            if self.selected_checkpoint_sha256 is None or self.selected_checkpoint_epoch is None:
                raise TrainingDataInputError("Selected EVAL2 outcome requires selected checkpoint identity.")
            selected = [x for x in evaluated if x.trajectory_point.checkpoint_sha256 == self.selected_checkpoint_sha256]
            if len(selected) != 1 or not selected[0].admissible or selected[0].trajectory_point.epoch != int(self.selected_checkpoint_epoch):
                raise TrainingDataInputError("EVAL2 selected checkpoint is not one admissible evaluated candidate.")
        elif self.selected_checkpoint_sha256 is not None or self.selected_checkpoint_epoch is not None:
            raise TrainingDataInputError("Non-selected EVAL2 outcome cannot carry a selected checkpoint.")
        if int(self.rescue_evaluated_count) < 0:
            raise TrainingDataInputError("EVAL2 rescue count cannot be negative.")
        object.__setattr__(self, "rescue_evaluated_count", int(self.rescue_evaluated_count))

    @property
    def selected_checkpoint(self) -> Eval2CheckpointRecord | None:
        if self.selected_checkpoint_sha256 is None:
            return None
        return next(x for x in self.evaluated_checkpoints if x.trajectory_point.checkpoint_sha256 == self.selected_checkpoint_sha256)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "evaluation_plan": self.evaluation_plan.to_dict(),
            "trajectory_points": [x.to_dict() for x in self.trajectory_points],
            "initial_shortlist_checkpoint_sha256s": list(self.initial_shortlist_checkpoint_sha256s),
            "evaluated_checkpoints": [x.to_dict() for x in self.evaluated_checkpoints],
            "bootstrap_comparisons": [x.to_dict() for x in self.bootstrap_comparisons],
            "selected_checkpoint_sha256": self.selected_checkpoint_sha256,
            "selected_checkpoint_epoch": self.selected_checkpoint_epoch,
            "outcome": self.outcome,
            "rescue_evaluated_count": self.rescue_evaluated_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Eval2RunRecord":
        if payload.get("schema") != EVAL2_RUN_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 run-record schema.")
        result = cls(
            evaluation_plan=Eval2EvaluationPlan.from_dict(payload["evaluation_plan"]),
            trajectory_points=tuple(Eval2TrajectoryPoint.from_dict(v) for v in payload["trajectory_points"]),
            initial_shortlist_checkpoint_sha256s=tuple(str(v) for v in payload.get("initial_shortlist_checkpoint_sha256s", ())),
            evaluated_checkpoints=tuple(Eval2CheckpointRecord.from_dict(v) for v in payload.get("evaluated_checkpoints", ())),
            bootstrap_comparisons=tuple(Eval2BootstrapComparison.from_dict(v) for v in payload.get("bootstrap_comparisons", ())),
            selected_checkpoint_sha256=None if payload.get("selected_checkpoint_sha256") is None else str(payload["selected_checkpoint_sha256"]),
            selected_checkpoint_epoch=None if payload.get("selected_checkpoint_epoch") is None else int(payload["selected_checkpoint_epoch"]),
            outcome=str(payload["outcome"]),
            rescue_evaluated_count=int(payload.get("rescue_evaluated_count", 0)),
        )
        _validate_record_digest(payload, result.content_digest, name="EVAL2 run record")
        return result


def build_eval2_shortlist(
    trajectory_points: Sequence[Eval2TrajectoryPoint],
    policy: CheckpointSelectionPolicy,
) -> tuple[tuple[Eval2TrajectoryPoint, tuple[str, ...]], ...]:
    """Return deterministic target-only 3+2 shortlist with refinement reservation."""

    points = tuple(trajectory_points)
    if not points:
        raise TrainingDataInputError("EVAL2 shortlist requires at least one finite trajectory point.")
    if len({x.checkpoint_sha256 for x in points}) != len(points):
        raise TrainingDataInputError("EVAL2 trajectory contains duplicate checkpoint bytes.")
    target_rank = sorted(points, key=lambda x: (x.lightweight_target_score_ev_per_angstrom, x.epoch, x.checkpoint_sha256))
    total = int(policy.initial_full_evaluation_candidates)
    reserved = int(policy.refinement_reserved_candidates)
    general_count = max(0, total - reserved)
    selected: list[Eval2TrajectoryPoint] = []
    reasons: dict[str, set[str]] = {}

    def add(point: Eval2TrajectoryPoint, reason: str) -> None:
        reasons.setdefault(point.checkpoint_sha256, set()).add(reason)
        if point not in selected:
            selected.append(point)

    for point in target_rank[:general_count]:
        add(point, "best_lightweight_target_overall")
    refinement = [x for x in target_rank if x.in_refinement_phase]
    for point in refinement[:reserved]:
        add(point, "best_lightweight_target_refinement")

    # Preserve at least one refinement checkpoint whenever one exists and the
    # configured shortlist has capacity. If the first pass was filled entirely
    # by overlapping overall/refinement points, target-rank backfill fills the
    # vacancies without sacrificing that reservation.
    for point in target_rank:
        if len(selected) >= min(total, len(points)):
            break
        add(point, "target_rank_backfill")
    if refinement and total > 0 and not any(x.in_refinement_phase for x in selected):
        replacement = refinement[0]
        if len(selected) >= total:
            # Replace the target-worst non-refinement item, deterministically.
            non_ref = [x for x in selected if not x.in_refinement_phase]
            if non_ref:
                victim = max(non_ref, key=lambda x: (x.lightweight_target_score_ev_per_angstrom, x.epoch, x.checkpoint_sha256))
                selected.remove(victim)
                reasons.pop(victim.checkpoint_sha256, None)
        add(replacement, "mandatory_refinement_presence")
    selected.sort(key=lambda x: (x.lightweight_target_score_ev_per_angstrom, x.epoch, x.checkpoint_sha256))
    return tuple((x, tuple(sorted(reasons[x.checkpoint_sha256]))) for x in selected)


def eval2_target_metrics_from_prediction_view(
    view: Any,
    predictions: Sequence[Any],
    *,
    block_ids: Sequence[str],
    target_role_digest: str,
    prediction_digest: str,
) -> Eval2TargetMetricRecord:
    """Reduce full target predictions into the EVAL2 metric/tie-break evidence.

    AUDIT-EVAL-PERF1 keeps all scalar reduction order that contributes to the
    persisted authority, but caches static dataset metadata and preallocates the
    force-tail buffer so repeated checkpoint evaluations avoid Python metadata
    reconstruction and ragged list concatenation.
    """

    if len(predictions) != int(view.configuration_count) or len(block_ids) != int(view.configuration_count):
        raise TrainingDataInputError("EVAL2 target predictions/block IDs do not match the target role.")
    if any(not str(v).strip() for v in block_ids):
        raise TrainingDataInputError("EVAL2 target block IDs must be non-empty.")
    metadata = _eval2_static_reduction_metadata(view, block_ids)

    count = int(view.configuration_count)
    force_sse = 0.0
    force_count = 0
    energy_abs_per_atom = np.empty(count, dtype=np.float64)
    energy_signed_per_atom_by_composition: dict[tuple[tuple[int, int], ...], list[float]] = {}
    vector = np.empty(int(view.total_atom_count), dtype=np.float64)
    species_sse = np.zeros(len(metadata.species_atomic_numbers), dtype=np.float64)
    species_count = np.zeros(len(metadata.species_atomic_numbers), dtype=np.int64)
    condition_sse = np.zeros(len(getattr(view, "condition_labels", ())), dtype=np.float64)
    condition_count = np.zeros(len(getattr(view, "condition_labels", ())), dtype=np.int64)
    group_sse = np.zeros(2, dtype=np.float64)
    group_count = np.zeros(2, dtype=np.int64)
    block_sse = np.zeros(len(metadata.block_labels), dtype=np.float64)
    block_count = np.zeros(len(metadata.block_labels), dtype=np.int64)
    block_configs = np.zeros(len(metadata.block_labels), dtype=np.int64)
    stress_sse = 0.0
    stress_count = 0

    for index, prediction in enumerate(predictions):
        natoms = int(view.atom_counts[index])
        start = int(view.force_offsets[index])
        stop = int(view.force_offsets[index + 1])
        pred_e = float(prediction.energy_ev)
        if not math.isfinite(pred_e):
            raise Eval2NumericalEvaluationError(
                "eval_nonfinite_energy_prediction",
                f"EVAL2 predicted energy is non-finite for target frame index {index}.",
                target_role_digest=target_role_digest,
                prediction_digest=prediction_digest,
            )
        signed_energy_error_per_atom = (pred_e - float(view.reference_energies[index])) / natoms
        energy_abs_per_atom[index] = abs(signed_energy_error_per_atom)
        composition_key = metadata.composition_keys[index]
        energy_signed_per_atom_by_composition.setdefault(composition_key, []).append(signed_energy_error_per_atom)

        pred_f = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
        if pred_f.shape != (natoms, 3):
            raise TrainingDataInputError("EVAL2 predicted force shape is invalid.")
        if np.any(~np.isfinite(pred_f)):
            raise Eval2NumericalEvaluationError(
                "eval_nonfinite_force_prediction",
                f"EVAL2 predicted forces are non-finite for target frame index {index}.",
                target_role_digest=target_role_digest,
                prediction_digest=prediction_digest,
            )
        delta = pred_f - view.reference_forces[start:stop]
        sse = float(np.sum(delta * delta, dtype=np.float64))
        components = int(delta.size)
        force_sse += sse
        force_count += components
        vector[start:stop] = np.linalg.norm(delta, axis=1)

        for species_code, local_indices in metadata.species_groups_per_frame[index]:
            selected = delta[local_indices]
            species_sse[species_code] += float(np.sum(selected * selected, dtype=np.float64))
            species_count[species_code] += int(selected.size)

        focus_mask = metadata.focus_masks_per_frame[index]
        if focus_mask is not None:
            for group_code, mask in ((0, focus_mask), (1, ~focus_mask)):
                if np.any(mask):
                    group_delta = delta[mask]
                    group_sse[group_code] += float(np.sum(group_delta * group_delta, dtype=np.float64))
                    group_count[group_code] += int(group_delta.size)

        if getattr(view, "condition_labels", ()):
            cid = int(view.condition_ids[index])
            if cid >= 0:
                condition_sse[cid] += sse
                condition_count[cid] += components

        block_code = int(metadata.block_codes[index])
        block_sse[block_code] += sse
        block_count[block_code] += components
        block_configs[block_code] += 1

        if bool(view.stress_present[index]):
            if prediction.stress_ev_per_angstrom3 is None:
                raise TrainingDataInputError("EVAL2 target has stress labels but prediction omitted stress.")
            predicted_stress = full_3x3_to_voigt_6_stress(np.asarray(prediction.stress_ev_per_angstrom3, dtype=np.float64)).reshape(-1)
            if predicted_stress.shape != (6,):
                raise TrainingDataInputError("EVAL2 predicted stress shape is invalid.")
            if np.any(~np.isfinite(predicted_stress)):
                raise Eval2NumericalEvaluationError(
                    "eval_nonfinite_stress_prediction",
                    f"EVAL2 predicted stress is non-finite for target frame index {index}.",
                    target_role_digest=target_role_digest,
                    prediction_digest=prediction_digest,
                )
            delta_stress = predicted_stress - view.reference_stresses[index]
            stress_sse += float(np.sum(delta_stress * delta_stress, dtype=np.float64))
            stress_count += int(delta_stress.size)

    if force_count <= 0:
        raise TrainingDataInputError("EVAL2 target role contains no force components.")
    species = tuple(
        (chemical_symbols[z], math.sqrt(species_sse[code] / species_count[code]))
        for code, z in enumerate(metadata.species_atomic_numbers)
        if int(species_count[code]) > 0
    )
    species_macro = float(np.mean([value for _, value in species]))
    conditions = tuple(
        (f"condition:{label}", math.sqrt(condition_sse[code] / condition_count[code]))
        for code, label in enumerate(getattr(view, "condition_labels", ()))
        if int(condition_count[code]) > 0
    )
    species_strata = tuple((f"species:{symbol}", value) for symbol, value in species)
    group_names = ("focus", "nonfocus")
    group_strata = tuple(
        (f"group:{group_names[code]}", math.sqrt(group_sse[code] / group_count[code]))
        for code in range(2)
        if int(group_count[code]) > 0
    )
    strata = tuple(sorted((*conditions, *group_strata, *species_strata)))
    worst = None if not strata else max(value for _, value in strata)

    relative_energy_residuals: list[float] = []
    for values in energy_signed_per_atom_by_composition.values():
        if len(values) < 2:
            continue
        arr = np.asarray(values, dtype=np.float64)
        centered = arr - float(np.mean(arr))
        relative_energy_residuals.extend(float(v) for v in centered)
    relative_energy_rmse = (
        None
        if not relative_energy_residuals
        else math.sqrt(float(np.mean(np.square(np.asarray(relative_energy_residuals, dtype=np.float64)))))
    )
    block_metrics = tuple(
        Eval2TargetBlockMetric(
            block_id=block,
            force_squared_error_sum=float(block_sse[code]),
            force_component_count=int(block_count[code]),
            configuration_count=int(block_configs[code]),
        )
        for code, block in enumerate(metadata.block_labels)
    )
    energy_mae = float(np.mean(energy_abs_per_atom))
    force_rmse = math.sqrt(force_sse / force_count)
    p90 = float(np.quantile(vector, 0.90))
    p95 = float(np.quantile(vector, 0.95))
    p99 = float(np.quantile(vector, 0.99))
    stress_rmse = None if stress_count == 0 else math.sqrt(stress_sse / stress_count)
    numerical_metrics = [
        energy_mae, force_rmse, species_macro, p90, p95, p99,
        *(value for _, value in species),
        *(value for _, value in strata),
    ]
    for optional in (relative_energy_rmse, worst, stress_rmse):
        if optional is not None:
            numerical_metrics.append(float(optional))
    if any(not math.isfinite(float(value)) for value in numerical_metrics):
        raise Eval2NumericalEvaluationError(
            "eval_nonfinite_target_metric",
            "EVAL2 target-only reduction produced a non-finite scientific metric.",
            target_role_digest=target_role_digest,
            prediction_digest=prediction_digest,
        )
    return Eval2TargetMetricRecord(
        configuration_count=count,
        atom_count=int(view.total_atom_count),
        energy_mae_ev_per_atom=energy_mae,
        relative_energy_rmse_ev_per_atom=relative_energy_rmse,
        force_component_rmse_ev_per_angstrom=force_rmse,
        species_macro_force_rmse_ev_per_angstrom=species_macro,
        species_force_rmse_ev_per_angstrom=species,
        force_error_p90_ev_per_angstrom=p90,
        force_error_p95_ev_per_angstrom=p95,
        force_error_p99_ev_per_angstrom=p99,
        worst_stratum_force_rmse_ev_per_angstrom=worst,
        stratum_force_rmse_ev_per_angstrom=strata,
        stress_rmse_ev_per_angstrom3=stress_rmse,
        block_metrics=block_metrics,
        target_role_digest=target_role_digest,
        prediction_digest=prediction_digest,
    )


def assess_eval2_checkpoint(
    trajectory_point: Eval2TrajectoryPoint,
    *,
    evaluation_record_digest: str,
    target_metrics: Eval2TargetMetricRecord,
    admissibility_policy: CheckpointAdmissibilityPolicy,
    replay_candidate_force_rmse_ev_per_angstrom: float | None,
    replay_foundation_force_rmse_ev_per_angstrom: float | None,
    replay_label_mode: str | None,
    shortlist_reasons: Sequence[str] = (),
    full_evaluation_rank: int = 0,
) -> Eval2CheckpointRecord:
    degradation = None
    if replay_candidate_force_rmse_ev_per_angstrom is not None and replay_foundation_force_rmse_ev_per_angstrom is not None:
        degradation = float(replay_candidate_force_rmse_ev_per_angstrom) - float(replay_foundation_force_rmse_ev_per_angstrom)
    reasons = admissibility_policy.failure_reasons(
        target_force_rmse_ev_per_angstrom=target_metrics.force_component_rmse_ev_per_angstrom,
        replay_degradation_ev_per_angstrom=degradation,
        replay_label_mode=replay_label_mode,
    )
    return Eval2CheckpointRecord(
        trajectory_point=trajectory_point,
        evaluation_record_digest=evaluation_record_digest,
        target_metrics=target_metrics,
        replay_candidate_force_rmse_ev_per_angstrom=replay_candidate_force_rmse_ev_per_angstrom,
        replay_foundation_force_rmse_ev_per_angstrom=replay_foundation_force_rmse_ev_per_angstrom,
        replay_degradation_ev_per_angstrom=degradation,
        replay_label_mode=replay_label_mode,
        admissible=not reasons,
        rejection_reasons=reasons,
        shortlist_reasons=tuple(shortlist_reasons),
        full_evaluation_rank=full_evaluation_rank,
    )


def _seed_from_digest(value: str) -> int:
    raw = bytes.fromhex(validate_digest(value, name="bootstrap_seed_material_digest"))
    return int.from_bytes(raw[:8], "big", signed=False) & 0x7FFF_FFFF


def paired_block_bootstrap_compare(
    first: Eval2CheckpointRecord,
    second: Eval2CheckpointRecord,
    *,
    policy: CheckpointSelectionPolicy,
    seed_material_digest: str,
) -> Eval2BootstrapComparison:
    """Paired block bootstrap of the full target force-RMSE difference.

    The same block draw is applied to both candidates in every replicate.  The
    block metric stores sufficient statistics, so no atom/prediction arrays are
    resampled or duplicated.
    """

    first_map = first.target_metrics.block_map()
    second_map = second.target_metrics.block_map()
    if set(first_map) != set(second_map):
        raise TrainingDataInputError("EVAL2 paired bootstrap requires identical frozen correlation blocks.")
    blocks = tuple(sorted(first_map))
    if any(first_map[key].force_component_count != second_map[key].force_component_count for key in blocks):
        raise TrainingDataInputError("EVAL2 paired bootstrap block component counts changed between candidates.")
    delta = first.target_metrics.force_component_rmse_ev_per_angstrom - second.target_metrics.force_component_rmse_ev_per_angstrom
    eps = float(policy.practical_equivalence_ev_per_angstrom)
    if abs(delta) <= eps:
        return Eval2BootstrapComparison(
            first_candidate_identity=first.stable_candidate_identity,
            second_candidate_identity=second.stable_candidate_identity,
            first_minus_second_ev_per_angstrom=delta,
            confidence_low_ev_per_angstrom=None,
            confidence_high_ev_per_angstrom=None,
            independent_block_count=len(blocks),
            bootstrap_replicates=policy.bootstrap_replicates,
            bootstrap_confidence=policy.bootstrap_confidence,
            decision="indistinguishable",
            seed=None,
        )
    if len(blocks) < int(policy.bootstrap_min_independent_blocks):
        return Eval2BootstrapComparison(
            first_candidate_identity=first.stable_candidate_identity,
            second_candidate_identity=second.stable_candidate_identity,
            first_minus_second_ev_per_angstrom=delta,
            confidence_low_ev_per_angstrom=None,
            confidence_high_ev_per_angstrom=None,
            independent_block_count=len(blocks),
            bootstrap_replicates=policy.bootstrap_replicates,
            bootstrap_confidence=policy.bootstrap_confidence,
            decision="insufficient_blocks",
            seed=None,
        )
    seed = _seed_from_digest(digest({
        "schema": "mdstats.eval2-bootstrap-seed.v1",
        "seed_material_digest": validate_digest(seed_material_digest, name="seed_material_digest"),
        "first": first.stable_candidate_identity,
        "second": second.stable_candidate_identity,
        "blocks": list(blocks),
    }))
    rng = np.random.default_rng(seed)
    count = len(blocks)
    replicates = np.empty(int(policy.bootstrap_replicates), dtype=np.float64)
    first_sse = np.asarray([first_map[key].force_squared_error_sum for key in blocks], dtype=np.float64)
    second_sse = np.asarray([second_map[key].force_squared_error_sum for key in blocks], dtype=np.float64)
    components = np.asarray([first_map[key].force_component_count for key in blocks], dtype=np.float64)
    # AUDIT-EVAL-PERF1 preserves the exact RNG stream but amortizes Python
    # overhead over bounded batches.  Each row remains one canonical block draw.
    # The cap bounds temporary integer and gather arrays independently of the
    # configured bootstrap replicate count.
    bootstrap_target_temporary_bytes = 32 * 1024**2
    bytes_per_draw_entry = 2 * np.dtype(np.int64).itemsize  # draw + one gathered float64 array
    memory_bounded_batch = max(1, bootstrap_target_temporary_bytes // max(1, count * bytes_per_draw_entry))
    bootstrap_batch = max(1, min(256, replicates.size, int(memory_bounded_batch)))
    cursor = 0
    while cursor < replicates.size:
        batch = min(bootstrap_batch, replicates.size - cursor)
        draws = rng.integers(0, count, size=(batch, count))
        sampled_components = components[draws]
        denom = np.sum(sampled_components, axis=1, dtype=np.float64)
        if np.any(denom <= 0.0):
            raise TrainingDataInputError("EVAL2 bootstrap sampled a zero-component block set.")
        first_sum = np.sum(first_sse[draws], axis=1, dtype=np.float64)
        second_sum = np.sum(second_sse[draws], axis=1, dtype=np.float64)
        replicates[cursor : cursor + batch] = np.sqrt(first_sum / denom) - np.sqrt(second_sum / denom)
        cursor += batch
    alpha = (1.0 - float(policy.bootstrap_confidence)) / 2.0
    low, high = (float(v) for v in np.quantile(replicates, [alpha, 1.0 - alpha]))
    # A material decision requires agreement between the unrounded point
    # improvement and the paired interval direction.  The bootstrap may not
    # reverse a > practical-equivalence point estimate merely because block
    # resampling changes effective block frequency.
    threshold = float(policy.practical_equivalence_ev_per_angstrom)
    if delta < -threshold and high < 0.0:
        decision = "first_materially_better"
    elif delta > threshold and low > 0.0:
        decision = "second_materially_better"
    else:
        decision = "indistinguishable"
    return Eval2BootstrapComparison(
        first_candidate_identity=first.stable_candidate_identity,
        second_candidate_identity=second.stable_candidate_identity,
        first_minus_second_ev_per_angstrom=delta,
        confidence_low_ev_per_angstrom=low,
        confidence_high_ev_per_angstrom=high,
        independent_block_count=len(blocks),
        bootstrap_replicates=policy.bootstrap_replicates,
        bootstrap_confidence=policy.bootstrap_confidence,
        decision=decision,
        seed=seed,
    )


def _secondary_key(candidate: Eval2CheckpointRecord, policy: CheckpointSelectionPolicy) -> tuple[Any, ...]:
    values = candidate.target_metrics.secondary_values(policy)
    finite_values = tuple(math.inf if value is None else float(value) for value in values)
    maturity = 0 if (policy.prefer_later_lower_lr_when_equivalent and candidate.trajectory_point.in_refinement_phase) else 1
    later = -candidate.trajectory_point.epoch if policy.prefer_later_lower_lr_when_equivalent else 0
    return (*finite_values, maturity, later, candidate.stable_candidate_identity)


def order_eval2_admissible_candidates(
    candidates: Sequence[Eval2CheckpointRecord],
    *,
    policy: CheckpointSelectionPolicy,
    seed_material_digest: str,
) -> tuple[tuple[Eval2CheckpointRecord, ...], tuple[Eval2BootstrapComparison, ...]]:
    """Return deterministic uncertainty-aware target-only ordering.

    Ordering is built in anchored primary bands: the raw-primary best remaining
    candidate is the band anchor; candidates not demonstrably materially worse
    than that anchor are ordered by the frozen secondary/maturity tuple.  This
    avoids non-transitive pairwise sort behavior while preserving the EVAL2
    semantics that uncertainty may promote a mature/safer target-tied candidate.
    """

    pool = [item for item in candidates if item.admissible]
    comparisons: list[Eval2BootstrapComparison] = []
    ordered: list[Eval2CheckpointRecord] = []
    while pool:
        pool.sort(key=lambda x: (x.target_metrics.force_component_rmse_ev_per_angstrom, x.stable_candidate_identity))
        anchor = pool[0]
        band = [anchor]
        materially_worse: list[Eval2CheckpointRecord] = []
        for item in pool[1:]:
            comparison = paired_block_bootstrap_compare(anchor, item, policy=policy, seed_material_digest=seed_material_digest)
            comparisons.append(comparison)
            # Anchor has raw primary <= item. The item is materially worse only
            # if practical/bootstrap evidence grants the anchor primary authority.
            if comparison.decision == "first_materially_better":
                materially_worse.append(item)
            elif comparison.decision == "insufficient_blocks":
                if (item.target_metrics.force_component_rmse_ev_per_angstrom - anchor.target_metrics.force_component_rmse_ev_per_angstrom) > policy.practical_equivalence_ev_per_angstrom:
                    materially_worse.append(item)
                else:
                    band.append(item)
            else:
                band.append(item)
        band.sort(key=lambda x: _secondary_key(x, policy))
        ordered.extend(band)
        pool = materially_worse
    return tuple(ordered), tuple(comparisons)


def build_eval2_run_record(
    *,
    evaluation_plan: Eval2EvaluationPlan,
    trajectory_points: Sequence[Eval2TrajectoryPoint],
    evaluated_checkpoints: Sequence[Eval2CheckpointRecord],
    selection_policy: CheckpointSelectionPolicy,
    rescue_evaluated_count: int = 0,
) -> Eval2RunRecord:
    shortlist = build_eval2_shortlist(trajectory_points, selection_policy)
    shortlist_ids = tuple(item.checkpoint_sha256 for item, _ in shortlist)
    evaluated = tuple(evaluated_checkpoints)
    admissible = tuple(item for item in evaluated if item.admissible)
    if admissible:
        ordered, comparisons = order_eval2_admissible_candidates(
            admissible,
            policy=selection_policy,
            seed_material_digest=evaluation_plan.bootstrap_seed_material_digest,
        )
        winner = ordered[0]
        return Eval2RunRecord(
            evaluation_plan=evaluation_plan,
            trajectory_points=tuple(trajectory_points),
            initial_shortlist_checkpoint_sha256s=shortlist_ids,
            evaluated_checkpoints=evaluated,
            bootstrap_comparisons=comparisons,
            selected_checkpoint_sha256=winner.trajectory_point.checkpoint_sha256,
            selected_checkpoint_epoch=winner.trajectory_point.epoch,
            outcome="selected",
            rescue_evaluated_count=rescue_evaluated_count,
        )
    finite_evaluated = {item.trajectory_point.checkpoint_sha256 for item in evaluated}
    remaining = [item for item in trajectory_points if item.checkpoint_sha256 not in finite_evaluated]
    can_rescue = int(rescue_evaluated_count) < evaluation_plan.candidate_rescue_cap and bool(remaining)
    return Eval2RunRecord(
        evaluation_plan=evaluation_plan,
        trajectory_points=tuple(trajectory_points),
        initial_shortlist_checkpoint_sha256s=shortlist_ids,
        evaluated_checkpoints=evaluated,
        bootstrap_comparisons=(),
        selected_checkpoint_sha256=None,
        selected_checkpoint_epoch=None,
        outcome="awaiting_more_evaluations" if can_rescue else "no_admissible_checkpoint",
        rescue_evaluated_count=rescue_evaluated_count,
    )


def read_train2_trajectory_points(
    checkpoint_directory: str | Path,
    *,
    checkpoint_catalog: Any,
    target_head_name: str,
) -> tuple[Eval2TrajectoryPoint, ...]:
    """Authenticate TRAIN2 history and expose finite lightweight target points."""

    root = Path(checkpoint_directory).resolve()
    history_path = root / "train2_history.jsonl"
    if not history_path.is_file():
        raise TrainingDataInputError("EVAL2 requires TRAIN2B epoch history.")
    catalog_by_epoch = {int(item.epoch): item for item in checkpoint_catalog.checkpoints}
    latest: dict[int, Mapping[str, Any]] = {}
    for line in history_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception as exc:
            raise TrainingDataSerializationError(f"Invalid TRAIN2 history JSON: {exc}") from exc
        if payload.get("schema") != "mdstats.train2-epoch-history.v1":
            continue
        latest[int(payload["epoch"])] = payload
    points: list[Eval2TrajectoryPoint] = []
    for epoch, checkpoint in sorted(catalog_by_epoch.items()):
        item = latest.get(epoch)
        if item is None:
            raise TrainingDataInputError(f"EVAL2 checkpoint epoch {epoch} lacks TRAIN2 history evidence.")
        if str(item.get("raw_checkpoint_sha256")) != checkpoint.sha256:
            raise TrainingDataInputError(f"EVAL2 checkpoint epoch {epoch} bytes disagree with TRAIN2 history.")
        validation = item.get("validation_force_rmse_ev_per_angstrom", {})
        if not isinstance(validation, Mapping):
            raise TrainingDataSerializationError("TRAIN2 history validation metrics are malformed.")
        value = validation.get(target_head_name)
        if value is None:
            # Some source MACE builds log the final target validation under a
            # generic Default head. Only one unambiguous finite non-replay value
            # may be accepted as a compatibility fallback.
            candidates = [
                float(v) for k, v in validation.items()
                if str(k) not in {"pt_head", "replay_head", "train2_true_replay"}
                and math.isfinite(float(v)) and float(v) >= 0.0
            ]
            if len(candidates) != 1:
                continue
            value = candidates[0]
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            continue
        points.append(Eval2TrajectoryPoint(
            epoch=epoch,
            checkpoint_sha256=checkpoint.sha256,
            lightweight_target_score_ev_per_angstrom=value,
            normalized_schedule_progress=float(item["normalized_progress"]),
            instantaneous_learning_rate=float(item["instantaneous_learning_rate"]),
            phase=str(item["phase"]),
            runtime_summary_digest=str(item["runtime_summary_digest"]),
            stable_candidate_identity=f"epoch-{epoch}:{checkpoint.sha256}",
        ))
    if not points:
        raise TrainingDataInputError("EVAL2 found no finite lightweight target checkpoints.")
    return tuple(points)


def next_eval2_checkpoint_batch(
    record: Eval2RunRecord | None,
    *,
    trajectory_points: Sequence[Eval2TrajectoryPoint],
    policy: CheckpointSelectionPolicy,
    rescue_cap: int,
) -> tuple[Eval2TrajectoryPoint, ...]:
    """Return the next target-ranked full-evaluation purchase without replay input."""

    shortlist = build_eval2_shortlist(trajectory_points, policy)
    if record is None:
        return tuple(item for item, _ in shortlist)
    evaluated = {item.trajectory_point.checkpoint_sha256 for item in record.evaluated_checkpoints}
    if any(item.admissible for item in record.evaluated_checkpoints):
        return ()
    already_rescued = int(record.rescue_evaluated_count)
    remaining_budget = max(0, int(rescue_cap) - already_rescued)
    if remaining_budget <= 0:
        return ()
    ranked = sorted(
        (item for item in trajectory_points if item.checkpoint_sha256 not in evaluated),
        key=lambda x: (x.lightweight_target_score_ev_per_angstrom, x.epoch, x.checkpoint_sha256),
    )
    return tuple(ranked[:remaining_budget])
