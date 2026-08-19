"""SIZE-FIDELITY2 survivor-fidelity requalification for the MV fixed-eight funnel.

This authority is deliberately pre-migration and GPU-deferred.  It freezes the
exhaustive calibration work required for the future SIZE-HALVE2 policy and can
retrospectively evaluate that policy once uninterrupted 30-epoch trajectories
are supplied.  Halving is disabled during calibration: every independently
hard-qualified target size is trained to epoch 30 for each frozen seed, and the
q=4..8 admission-width decisions are reconstructed from those same trajectories.

Monitor-size views are derived from the already-authorized epoch-3 full
prediction product; they are not additional model-inference passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .size_halve2 import (
    SIZE_HALVE2_FIXED_TARGET_SIZES,
    SizeHalve2Plan,
    _equivalence_aware_order,
)
from .target_size_convergence import TargetSizeTrainingEvidence

SIZE_FIDELITY2_POLICY_SCHEMA = "mdstats.size-fidelity2-policy.v1"
SIZE_FIDELITY2_MONITOR_SCHEMA = "mdstats.size-fidelity2-monitor-view.v1"
SIZE_FIDELITY2_CHECKPOINT_SCHEMA = "mdstats.size-fidelity2-checkpoint.v1"
SIZE_FIDELITY2_EXECUTION_PLAN_SCHEMA = "mdstats.size-fidelity2-execution-plan.v1"
SIZE_FIDELITY2_WIDTH_SCHEMA = "mdstats.size-fidelity2-width-assessment.v1"
SIZE_FIDELITY2_REPORT_SCHEMA = "mdstats.size-fidelity2-qualification-report.v1"
SIZE_FIDELITY2_VERSION = "mdstats.size-fidelity2.mv-survivor-requalification.2026-08.v1"

_READY = "ready_for_final_gpu_calibration"
_BLOCKED = "blocked_by_size_halve2"
_DEFERRED = "deferred_final_gpu_qualification"


def _as_tuple_int(values: Sequence[int], *, name: str) -> tuple[int, ...]:
    out = tuple(int(v) for v in values)
    if not out or len(set(out)) != len(out):
        raise TrainingDataInputError(f"{name} must contain unique integers.")
    return out


def _score_order(
    rows: Sequence[tuple[int, float]], *, epsilon: float, boundary_preserve_size: int | None = None
) -> tuple[int, ...]:
    remaining = sorted(((int(size), float(score)) for size, score in rows), key=lambda x: (x[1], x[0]))
    ordered: list[int] = []
    boundary = None if boundary_preserve_size is None else int(boundary_preserve_size)
    while remaining:
        anchor = remaining[0][1]
        band = [x for x in remaining if x[1] <= anchor + float(epsilon) + 1.0e-12]
        band.sort(key=lambda x: (0 if boundary is not None and x[0] == boundary else 1, x[0]))
        ordered.extend(size for size, _ in band)
        band_sizes = {size for size, _ in band}
        remaining = [x for x in remaining if x[0] not in band_sizes]
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class SizeFidelity2Policy:
    """Frozen q=4..8 survivor-recall calibration surface."""

    screening_seeds: tuple[int, ...] = (1, 2, 3)
    admission_widths: tuple[int, ...] = (4, 5, 6, 7, 8)
    monitor_configuration_candidates: tuple[int, ...] = (128, 256, 512, 1024)
    required_epoch3_finalist_recall: float = 1.0
    required_epoch10_finalist_recall: float = 1.0
    require_monitor_decision_equivalence: bool = True
    require_no_fixed_ceiling_nonconvergence: bool = True
    minimum_calibration_seeds: int = 3
    authority_version: str = SIZE_FIDELITY2_VERSION

    def __post_init__(self) -> None:
        seeds = tuple(sorted(set(_as_tuple_int(self.screening_seeds, name="SIZE-FIDELITY2 screening_seeds"))))
        widths = tuple(sorted(set(_as_tuple_int(self.admission_widths, name="SIZE-FIDELITY2 admission_widths"))))
        monitors = tuple(sorted(set(_as_tuple_int(self.monitor_configuration_candidates, name="SIZE-FIDELITY2 monitor_configuration_candidates"))))
        if any(v < 0 for v in seeds) or len(seeds) < int(self.minimum_calibration_seeds) or int(self.minimum_calibration_seeds) < 3:
            raise TrainingDataInputError("SIZE-FIDELITY2 requires at least three nonnegative frozen optimizer seeds.")
        if widths != (4, 5, 6, 7, 8):
            raise TrainingDataInputError("SIZE-FIDELITY2 freezes admission widths q=4,5,6,7,8.")
        if monitors != (128, 256, 512, 1024):
            raise TrainingDataInputError("SIZE-FIDELITY2 inherits the SIZE-FIDELITY1 128/256/512/1024 monitor grid.")
        for name in ("required_epoch3_finalist_recall", "required_epoch10_finalist_recall"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not (0.0 < value <= 1.0):
                raise TrainingDataInputError(f"SIZE-FIDELITY2 {name} must lie in (0,1].")
            object.__setattr__(self, name, value)
        if self.authority_version != SIZE_FIDELITY2_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY2 authority version.")
        object.__setattr__(self, "screening_seeds", seeds)
        object.__setattr__(self, "admission_widths", widths)
        object.__setattr__(self, "monitor_configuration_candidates", monitors)
        object.__setattr__(self, "minimum_calibration_seeds", int(self.minimum_calibration_seeds))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "screening_seeds": list(self.screening_seeds),
            "admission_widths": list(self.admission_widths),
            "monitor_configuration_candidates": list(self.monitor_configuration_candidates),
            "required_epoch3_finalist_recall": self.required_epoch3_finalist_recall,
            "required_epoch10_finalist_recall": self.required_epoch10_finalist_recall,
            "require_monitor_decision_equivalence": self.require_monitor_decision_equivalence,
            "require_no_fixed_ceiling_nonconvergence": self.require_no_fixed_ceiling_nonconvergence,
            "minimum_calibration_seeds": self.minimum_calibration_seeds,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2Policy":
        if payload.get("schema") != SIZE_FIDELITY2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 policy schema.")
        result = cls(
            screening_seeds=tuple(int(v) for v in payload["screening_seeds"]),
            admission_widths=tuple(int(v) for v in payload["admission_widths"]),
            monitor_configuration_candidates=tuple(int(v) for v in payload["monitor_configuration_candidates"]),
            required_epoch3_finalist_recall=float(payload["required_epoch3_finalist_recall"]),
            required_epoch10_finalist_recall=float(payload["required_epoch10_finalist_recall"]),
            require_monitor_decision_equivalence=bool(payload["require_monitor_decision_equivalence"]),
            require_no_fixed_ceiling_nonconvergence=bool(payload["require_no_fixed_ceiling_nonconvergence"]),
            minimum_calibration_seeds=int(payload["minimum_calibration_seeds"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SizeFidelity2MonitorView:
    monitor_configurations: int
    target_force_score_mev_per_a: float
    numerical_valid: bool
    target_hard_gates_passed: bool
    source_full_prediction_digest: str

    def __post_init__(self) -> None:
        monitor = int(self.monitor_configurations)
        score = float(self.target_force_score_mev_per_a)
        if monitor <= 0 or not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError("SIZE-FIDELITY2 monitor view has invalid size or score.")
        object.__setattr__(self, "monitor_configurations", monitor)
        object.__setattr__(self, "target_force_score_mev_per_a", score)
        object.__setattr__(self, "source_full_prediction_digest", validate_digest(self.source_full_prediction_digest, name="source_full_prediction_digest"))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_MONITOR_SCHEMA,
            "monitor_configurations": self.monitor_configurations,
            "target_force_score_mev_per_a": self.target_force_score_mev_per_a,
            "numerical_valid": bool(self.numerical_valid),
            "target_hard_gates_passed": bool(self.target_hard_gates_passed),
            "source_full_prediction_digest": self.source_full_prediction_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2MonitorView":
        if payload.get("schema") != SIZE_FIDELITY2_MONITOR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 monitor-view schema.")
        result = cls(
            int(payload["monitor_configurations"]), float(payload["target_force_score_mev_per_a"]),
            bool(payload["numerical_valid"]), bool(payload["target_hard_gates_passed"]),
            str(payload["source_full_prediction_digest"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 monitor-view digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SizeFidelity2Checkpoint:
    evidence: TargetSizeTrainingEvidence
    full_prediction_digest: str
    monitor_views: tuple[SizeFidelity2MonitorView, ...] = ()

    def __post_init__(self) -> None:
        pred = validate_digest(self.full_prediction_digest, name="full_prediction_digest")
        monitors = tuple(sorted(self.monitor_views, key=lambda v: v.monitor_configurations))
        if len({v.monitor_configurations for v in monitors}) != len(monitors):
            raise TrainingDataInputError("SIZE-FIDELITY2 checkpoint contains duplicate monitor views.")
        if any(v.source_full_prediction_digest != pred for v in monitors):
            raise TrainingDataInputError("SIZE-FIDELITY2 monitor views must derive from the checkpoint full-prediction authority.")
        object.__setattr__(self, "full_prediction_digest", pred)
        object.__setattr__(self, "monitor_views", monitors)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_CHECKPOINT_SCHEMA,
            "evidence": self.evidence.to_dict(),
            "full_prediction_digest": self.full_prediction_digest,
            "monitor_views": [v.to_dict() for v in self.monitor_views],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2Checkpoint":
        if payload.get("schema") != SIZE_FIDELITY2_CHECKPOINT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 checkpoint schema.")
        result = cls(
            TargetSizeTrainingEvidence.from_dict(payload["evidence"]),
            str(payload["full_prediction_digest"]),
            tuple(SizeFidelity2MonitorView.from_dict(v) for v in payload.get("monitor_views", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 checkpoint digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class SizeFidelity2ExecutionPlan:
    dataset_id: str
    size_halve2_digest: str
    policy: SizeFidelity2Policy
    coverage_qualified_sizes: tuple[int, ...]
    admission_widths: tuple[int, ...]
    required_training_runs: tuple[tuple[int, int], ...]
    required_checkpoint_epochs: tuple[int, ...] = (3, 10, 30)
    practical_equivalence_mev_per_a: float = 1.0
    coarse_practical_equivalence_mev_per_a: float = 1.0
    monitor_views_derived_from_full_predictions: bool = True
    status: str = _READY
    decision_reason: str = "exhaustive q-width calibration matrix frozen; positive GPU execution deferred"
    authority_version: str = SIZE_FIDELITY2_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        dataset_id = str(self.dataset_id).strip()
        if not dataset_id:
            raise TrainingDataInputError("SIZE-FIDELITY2 dataset_id cannot be empty.")
        object.__setattr__(self, "size_halve2_digest", validate_digest(self.size_halve2_digest, name="size_halve2_digest"))
        qualified = tuple(int(v) for v in self.coverage_qualified_sizes)
        widths = tuple(int(v) for v in self.admission_widths)
        runs = tuple(sorted((int(seed), int(size)) for seed, size in self.required_training_runs))
        checkpoints = tuple(int(v) for v in self.required_checkpoint_epochs)
        final_eps = float(self.practical_equivalence_mev_per_a)
        coarse_eps = float(self.coarse_practical_equivalence_mev_per_a)
        if not math.isfinite(final_eps) or final_eps <= 0.0 or not math.isfinite(coarse_eps) or coarse_eps <= 0.0:
            raise TrainingDataInputError("SIZE-FIDELITY2 equivalence widths must be positive and finite.")
        if self.status not in {_READY, _BLOCKED}:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY2 execution-plan status.")
        if self.status == _READY:
            q = len(qualified)
            if q < 4 or q > 8:
                raise TrainingDataInputError("SIZE-FIDELITY2 ready plan requires q in [4,8].")
            expected_suffix = SIZE_HALVE2_FIXED_TARGET_SIZES[-q:]
            if qualified != expected_suffix:
                raise TrainingDataInputError("SIZE-FIDELITY2 requires the nested hard-qualified population to be a contiguous fixed-ladder suffix.")
            expected_widths = tuple(v for v in self.policy.admission_widths if v <= q)
            if widths != expected_widths:
                raise TrainingDataInputError("SIZE-FIDELITY2 admission widths do not match the scientifically available q surface.")
            expected_runs = tuple(sorted((seed, size) for seed in self.policy.screening_seeds for size in qualified))
            if runs != expected_runs:
                raise TrainingDataInputError("SIZE-FIDELITY2 must train every seed x hard-qualified size exactly once to epoch 30.")
            if checkpoints != (3, 10, 30):
                raise TrainingDataInputError("SIZE-FIDELITY2 freezes checkpoints at 3,10,30 epochs.")
            if not self.monitor_views_derived_from_full_predictions:
                raise TrainingDataInputError("SIZE-FIDELITY2 forbids repeated inference for monitor-size variants.")
        else:
            if widths or runs:
                raise TrainingDataInputError("Blocked SIZE-FIDELITY2 plans cannot authorize calibration work.")
        if self.authority_version != SIZE_FIDELITY2_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY2 execution-plan authority version.")
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "coverage_qualified_sizes", qualified)
        object.__setattr__(self, "admission_widths", widths)
        object.__setattr__(self, "required_training_runs", runs)
        object.__setattr__(self, "required_checkpoint_epochs", checkpoints)
        object.__setattr__(self, "practical_equivalence_mev_per_a", final_eps)
        object.__setattr__(self, "coarse_practical_equivalence_mev_per_a", coarse_eps)

    @property
    def expected_training_run_count(self) -> int:
        return len(self.required_training_runs)

    @property
    def expected_full_inference_count(self) -> int:
        return len(self.required_training_runs) * len(self.required_checkpoint_epochs)

    @property
    def expected_additional_monitor_inference_count(self) -> int:
        return 0

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_EXECUTION_PLAN_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "size_halve2_digest": self.size_halve2_digest,
            "policy": self.policy.to_dict(),
            "coverage_qualified_sizes": list(self.coverage_qualified_sizes),
            "admission_widths": list(self.admission_widths),
            "required_training_runs": [list(v) for v in self.required_training_runs],
            "required_checkpoint_epochs": list(self.required_checkpoint_epochs),
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "coarse_practical_equivalence_mev_per_a": self.coarse_practical_equivalence_mev_per_a,
            "monitor_views_derived_from_full_predictions": self.monitor_views_derived_from_full_predictions,
            "status": self.status,
            "decision_reason": self.decision_reason,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2ExecutionPlan":
        if payload.get("schema") != SIZE_FIDELITY2_EXECUTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 execution-plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), size_halve2_digest=str(payload["size_halve2_digest"]),
            policy=SizeFidelity2Policy.from_dict(payload["policy"]),
            coverage_qualified_sizes=tuple(int(v) for v in payload["coverage_qualified_sizes"]),
            admission_widths=tuple(int(v) for v in payload["admission_widths"]),
            required_training_runs=tuple((int(v[0]), int(v[1])) for v in payload["required_training_runs"]),
            required_checkpoint_epochs=tuple(int(v) for v in payload["required_checkpoint_epochs"]),
            practical_equivalence_mev_per_a=float(payload["practical_equivalence_mev_per_a"]),
            coarse_practical_equivalence_mev_per_a=float(payload["coarse_practical_equivalence_mev_per_a"]),
            monitor_views_derived_from_full_predictions=bool(payload["monitor_views_derived_from_full_predictions"]),
            status=str(payload["status"]), decision_reason=str(payload.get("decision_reason", "")),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 execution-plan digest mismatch.")
        return result


def build_size_fidelity2_execution_plan(
    size_halve2_plan: SizeHalve2Plan, *, policy: SizeFidelity2Policy | None = None
) -> SizeFidelity2ExecutionPlan:
    policy = policy or SizeFidelity2Policy()
    qualified = tuple(size_halve2_plan.coverage_qualified_sizes)
    if size_halve2_plan.outcome != "ready_for_size_fidelity2":
        return SizeFidelity2ExecutionPlan(
            dataset_id=size_halve2_plan.dataset_id,
            size_halve2_digest=size_halve2_plan.content_digest,
            policy=policy,
            coverage_qualified_sizes=qualified,
            admission_widths=(), required_training_runs=(),
            practical_equivalence_mev_per_a=float(size_halve2_plan.policy.practical_equivalence_mev_per_a),
            coarse_practical_equivalence_mev_per_a=float(size_halve2_plan.policy.coarse_practical_equivalence_mev_per_a),
            status=_BLOCKED,
            decision_reason=f"SIZE-HALVE2 outcome={size_halve2_plan.outcome}; calibration work is not authorized",
        )
    q = len(qualified)
    widths = tuple(v for v in policy.admission_widths if v <= q)
    runs = tuple((seed, size) for seed in policy.screening_seeds for size in qualified)
    return SizeFidelity2ExecutionPlan(
        dataset_id=size_halve2_plan.dataset_id,
        size_halve2_digest=size_halve2_plan.content_digest,
        policy=policy,
        coverage_qualified_sizes=qualified,
        admission_widths=widths,
        required_training_runs=runs,
        practical_equivalence_mev_per_a=float(size_halve2_plan.policy.practical_equivalence_mev_per_a),
        coarse_practical_equivalence_mev_per_a=float(size_halve2_plan.policy.coarse_practical_equivalence_mev_per_a),
        status=_READY,
        decision_reason=(
            f"q={q} hard-qualified sizes; calibrate widths {list(widths)} from the same {len(runs)} uninterrupted "
            "30-epoch trajectories; monitor views reuse epoch-3 full predictions"
        ),
    )


@dataclass(frozen=True, slots=True)
class SizeFidelity2WidthAssessment:
    admission_width: int
    population_sizes: tuple[int, ...]
    seed_count: int
    epoch3_finalist_recall: float
    epoch10_finalist_recall: float
    epoch3_winner_recall: float
    epoch10_winner_recall: float
    boundary_nonconverged_count: int
    monitor_decision_equivalence_rates: tuple[tuple[int, float], ...]
    monitor_finalist_recall_rates: tuple[tuple[int, float], ...]
    passed: bool

    def __post_init__(self) -> None:
        width = int(self.admission_width)
        population = tuple(int(v) for v in self.population_sizes)
        seeds = int(self.seed_count)
        if width not in (4, 5, 6, 7, 8) or len(population) != width or seeds <= 0:
            raise TrainingDataInputError("SIZE-FIDELITY2 width assessment dimensions are invalid.")
        for name in ("epoch3_finalist_recall", "epoch10_finalist_recall", "epoch3_winner_recall", "epoch10_winner_recall"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise TrainingDataInputError(f"SIZE-FIDELITY2 {name} must lie in [0,1].")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "admission_width", width)
        object.__setattr__(self, "population_sizes", population)
        object.__setattr__(self, "seed_count", seeds)
        object.__setattr__(self, "boundary_nonconverged_count", int(self.boundary_nonconverged_count))
        object.__setattr__(self, "monitor_decision_equivalence_rates", tuple((int(k), float(v)) for k, v in self.monitor_decision_equivalence_rates))
        object.__setattr__(self, "monitor_finalist_recall_rates", tuple((int(k), float(v)) for k, v in self.monitor_finalist_recall_rates))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_WIDTH_SCHEMA,
            "admission_width": self.admission_width,
            "population_sizes": list(self.population_sizes),
            "seed_count": self.seed_count,
            "epoch3_finalist_recall": self.epoch3_finalist_recall,
            "epoch10_finalist_recall": self.epoch10_finalist_recall,
            "epoch3_winner_recall": self.epoch3_winner_recall,
            "epoch10_winner_recall": self.epoch10_winner_recall,
            "boundary_nonconverged_count": self.boundary_nonconverged_count,
            "monitor_decision_equivalence_rates": [list(v) for v in self.monitor_decision_equivalence_rates],
            "monitor_finalist_recall_rates": [list(v) for v in self.monitor_finalist_recall_rates],
            "passed": bool(self.passed),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2WidthAssessment":
        if payload.get("schema") != SIZE_FIDELITY2_WIDTH_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 width-assessment schema.")
        result = cls(
            int(payload["admission_width"]), tuple(int(v) for v in payload["population_sizes"]), int(payload["seed_count"]),
            float(payload["epoch3_finalist_recall"]), float(payload["epoch10_finalist_recall"]),
            float(payload["epoch3_winner_recall"]), float(payload["epoch10_winner_recall"]),
            int(payload["boundary_nonconverged_count"]),
            tuple((int(v[0]), float(v[1])) for v in payload["monitor_decision_equivalence_rates"]),
            tuple((int(v[0]), float(v[1])) for v in payload["monitor_finalist_recall_rates"]), bool(payload["passed"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 width-assessment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class SizeFidelity2QualificationReport:
    dataset_id: str
    execution_plan_digest: str
    policy: SizeFidelity2Policy
    coverage_qualified_sizes: tuple[int, ...]
    checkpoints: tuple[SizeFidelity2Checkpoint, ...]
    width_assessments: tuple[SizeFidelity2WidthAssessment, ...]
    recommended_monitor_configurations: int | None
    passed: bool
    gpu_qualification_status: str = _DEFERRED
    decision_reason: str = ""
    authority_version: str = SIZE_FIDELITY2_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("SIZE-FIDELITY2 report dataset_id cannot be empty.")
        object.__setattr__(self, "execution_plan_digest", validate_digest(self.execution_plan_digest, name="execution_plan_digest"))
        if self.gpu_qualification_status not in {_DEFERRED, "passed"}:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY2 GPU-qualification status.")
        if self.passed != (self.recommended_monitor_configurations is not None and all(v.passed for v in self.width_assessments)):
            raise TrainingDataInputError("SIZE-FIDELITY2 report pass flag contradicts width/monitor authority.")
        if self.authority_version != SIZE_FIDELITY2_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY2 report authority version.")
        object.__setattr__(self, "coverage_qualified_sizes", tuple(int(v) for v in self.coverage_qualified_sizes))
        object.__setattr__(self, "checkpoints", tuple(sorted(self.checkpoints, key=lambda v: (v.evidence.optimizer_seed, v.evidence.target_size, v.evidence.completed_epochs))))
        object.__setattr__(self, "width_assessments", tuple(sorted(self.width_assessments, key=lambda v: v.admission_width)))
        if self.recommended_monitor_configurations is not None:
            object.__setattr__(self, "recommended_monitor_configurations", int(self.recommended_monitor_configurations))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY2_REPORT_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "execution_plan_digest": self.execution_plan_digest,
            "policy": self.policy.to_dict(),
            "coverage_qualified_sizes": list(self.coverage_qualified_sizes),
            "checkpoints": [v.to_dict() for v in self.checkpoints],
            "width_assessments": [v.to_dict() for v in self.width_assessments],
            "recommended_monitor_configurations": self.recommended_monitor_configurations,
            "passed": bool(self.passed),
            "gpu_qualification_status": self.gpu_qualification_status,
            "decision_reason": self.decision_reason,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelity2QualificationReport":
        if payload.get("schema") != SIZE_FIDELITY2_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY2 qualification-report schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), execution_plan_digest=str(payload["execution_plan_digest"]),
            policy=SizeFidelity2Policy.from_dict(payload["policy"]),
            coverage_qualified_sizes=tuple(int(v) for v in payload["coverage_qualified_sizes"]),
            checkpoints=tuple(SizeFidelity2Checkpoint.from_dict(v) for v in payload["checkpoints"]),
            width_assessments=tuple(SizeFidelity2WidthAssessment.from_dict(v) for v in payload["width_assessments"]),
            recommended_monitor_configurations=None if payload.get("recommended_monitor_configurations") is None else int(payload["recommended_monitor_configurations"]),
            passed=bool(payload["passed"]), gpu_qualification_status=str(payload["gpu_qualification_status"]),
            decision_reason=str(payload.get("decision_reason", "")), authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY2 qualification-report digest mismatch.")
        return result


def _checkpoint_map(
    checkpoints: Sequence[SizeFidelity2Checkpoint],
) -> dict[tuple[int, int, int], SizeFidelity2Checkpoint]:
    out: dict[tuple[int, int, int], SizeFidelity2Checkpoint] = {}
    for row in checkpoints:
        key = (row.evidence.optimizer_seed, row.evidence.target_size, row.evidence.completed_epochs)
        if key in out:
            raise TrainingDataInputError(f"Duplicate SIZE-FIDELITY2 checkpoint {key}.")
        out[key] = row
    return out


def _validate_trajectory_matrix(plan: SizeFidelity2ExecutionPlan, checkpoints: Sequence[SizeFidelity2Checkpoint]) -> dict[tuple[int, int, int], SizeFidelity2Checkpoint]:
    if plan.status != _READY:
        raise TrainingDataInputError("Blocked SIZE-FIDELITY2 execution plans cannot be qualified.")
    rows = _checkpoint_map(checkpoints)
    expected = {(seed, size, epoch) for seed, size in plan.required_training_runs for epoch in plan.required_checkpoint_epochs}
    if set(rows) != expected:
        missing = sorted(expected - set(rows)); extra = sorted(set(rows) - expected)
        raise TrainingDataInputError(f"SIZE-FIDELITY2 checkpoint matrix must be exact; missing={missing[:4]}, extra={extra[:4]}.")
    monitor_set = set(plan.policy.monitor_configuration_candidates)
    for seed, size in plan.required_training_runs:
        coarse = rows[(seed, size, 3)]; short = rows[(seed, size, 10)]; final = rows[(seed, size, 30)]
        ce, se, fe = coarse.evidence, short.evidence, final.evidence
        if (ce.stage, ce.completed_epochs, ce.planned_epochs) != ("coarse", 3, 30):
            raise TrainingDataInputError("SIZE-FIDELITY2 epoch-3 evidence is not exact 3-of-30 authority.")
        if (se.stage, se.completed_epochs, se.planned_epochs) != ("short", 10, 30):
            raise TrainingDataInputError("SIZE-FIDELITY2 epoch-10 evidence is not exact 10-of-30 authority.")
        if (fe.stage, fe.completed_epochs, fe.planned_epochs) != ("final", 30, 30):
            raise TrainingDataInputError("SIZE-FIDELITY2 epoch-30 evidence is not exact 30-of-30 authority.")
        if not math.isclose(ce.normalized_schedule_progress, 0.1, abs_tol=1e-12, rel_tol=0.0) or not math.isclose(se.normalized_schedule_progress, 1.0/3.0, abs_tol=1e-12, rel_tol=0.0) or not math.isclose(fe.normalized_schedule_progress, 1.0, abs_tol=1e-12, rel_tol=0.0):
            raise TrainingDataInputError("SIZE-FIDELITY2 normalized schedule progress is not exact 3/30,10/30,30/30.")
        if (se.parent_checkpoint_digest, se.parent_optimizer_state_digest, se.parent_rng_state_digest) != (ce.checkpoint_digest, ce.optimizer_state_digest, ce.rng_state_digest):
            raise TrainingDataInputError(f"SIZE-FIDELITY2 n{size}/seed{seed} epoch-10 continuation ancestry differs from epoch 3.")
        if (fe.parent_checkpoint_digest, fe.parent_optimizer_state_digest, fe.parent_rng_state_digest) != (se.checkpoint_digest, se.optimizer_state_digest, se.rng_state_digest):
            raise TrainingDataInputError(f"SIZE-FIDELITY2 n{size}/seed{seed} epoch-30 continuation ancestry differs from epoch 10.")
        for attr in ("foundation_identity_digest", "evaluation_role_digest", "training_policy_digest", "training_run_digest", "schedule_digest"):
            if len({getattr(ce, attr), getattr(se, attr), getattr(fe, attr)}) != 1:
                raise TrainingDataInputError(f"SIZE-FIDELITY2 n{size}/seed{seed} {attr} changed inside one uninterrupted trajectory.")
        if not (ce.optimizer_update_count < se.optimizer_update_count < fe.optimizer_update_count and ce.structures_presented < se.structures_presented < fe.structures_presented):
            raise TrainingDataInputError(f"SIZE-FIDELITY2 n{size}/seed{seed} exposure did not increase across 3/10/30.")
        if set(v.monitor_configurations for v in coarse.monitor_views) != monitor_set:
            raise TrainingDataInputError("SIZE-FIDELITY2 epoch-3 checkpoint lacks the exact monitor-view grid.")
        if short.monitor_views or final.monitor_views:
            raise TrainingDataInputError("SIZE-FIDELITY2 monitor variants are derived only from the authorized epoch-3 full prediction.")
    # Cross-size scientific identities are common within each seed and across the matrix.
    for attr in ("foundation_identity_digest", "evaluation_role_digest", "training_policy_digest", "schedule_digest"):
        values = {getattr(v.evidence, attr) for v in rows.values()}
        if len(values) != 1:
            raise TrainingDataInputError(f"SIZE-FIDELITY2 {attr} changed inside the calibration matrix.")
    return rows


def build_size_fidelity2_qualification(
    execution_plan: SizeFidelity2ExecutionPlan,
    checkpoints: Sequence[SizeFidelity2Checkpoint],
    *, gpu_qualification_status: str = _DEFERRED,
) -> SizeFidelity2QualificationReport:
    rows = _validate_trajectory_matrix(execution_plan, checkpoints)
    policy = execution_plan.policy
    assessments: list[SizeFidelity2WidthAssessment] = []
    monitor_global_ok = {monitor: True for monitor in policy.monitor_configuration_candidates}

    for width in execution_plan.admission_widths:
        population = execution_plan.coverage_qualified_sizes[-width:]
        boundary = max(population)
        coarse_hits = short_hits = coarse_winner_hits = short_winner_hits = 0
        boundary_nonconverged = 0
        monitor_eq_hits = {m: 0 for m in policy.monitor_configuration_candidates}
        monitor_finalist_hits = {m: 0 for m in policy.monitor_configuration_candidates}
        total_finalists = 0
        total_seeds = len(policy.screening_seeds)

        for seed in policy.screening_seeds:
            coarse_rows = [rows[(seed, size, 3)] for size in population]
            short_rows = {size: rows[(seed, size, 10)] for size in population}
            final_rows = [rows[(seed, size, 30)] for size in population]
            final_admissible = [r.evidence for r in final_rows if r.evidence.admissible_for_stage_c]
            if len(final_admissible) < 2:
                continue
            final_order = _equivalence_aware_order(final_admissible, epsilon=execution_plan_to_halve_policy_epsilon(execution_plan))
            reference_finalists = tuple(final_order[:2])
            reference_winner = reference_finalists[0]
            total_finalists += 2

            final_by = {r.evidence.target_size: r.evidence for r in final_rows}
            if reference_winner == boundary:
                smaller = [v for v in final_admissible if v.target_size < boundary]
                if not smaller:
                    boundary_nonconverged += 1
                else:
                    best_smaller = min(smaller, key=lambda v: (v.target_force_score_mev_per_a, v.target_size))
                    improvement = best_smaller.target_force_score_mev_per_a - final_by[boundary].target_force_score_mev_per_a
                    if improvement > execution_plan_to_halve_policy_epsilon(execution_plan) + 1.0e-12:
                        boundary_nonconverged += 1

            coarse_admissible = [r.evidence for r in coarse_rows if r.evidence.admissible_for_screening]
            if len(coarse_admissible) >= min(width, 4):
                coarse_order = _equivalence_aware_order(
                    coarse_admissible,
                    epsilon=execution_plan_to_coarse_epsilon(execution_plan),
                    boundary_preserve_size=boundary,
                )
                coarse_survivors = tuple(coarse_order[: min(width, 4)])
            else:
                coarse_survivors = ()
            coarse_hits += sum(v in coarse_survivors for v in reference_finalists)
            coarse_winner_hits += int(reference_winner in coarse_survivors)

            short_admissible = [short_rows[size].evidence for size in coarse_survivors if short_rows[size].evidence.admissible_for_screening]
            if len(short_admissible) >= 2:
                short_order = _equivalence_aware_order(
                    short_admissible,
                    epsilon=execution_plan_to_halve_policy_epsilon(execution_plan),
                    boundary_preserve_size=boundary,
                )
                short_finalists = tuple(short_order[:2])
            else:
                short_finalists = ()
            short_hits += sum(v in short_finalists for v in reference_finalists)
            short_winner_hits += int(reference_winner in short_finalists)

            full_set = set(coarse_survivors)
            for monitor in policy.monitor_configuration_candidates:
                monitor_rows: list[tuple[int, float]] = []
                for row in coarse_rows:
                    view = next(v for v in row.monitor_views if v.monitor_configurations == monitor)
                    if view.numerical_valid:
                        monitor_rows.append((row.evidence.target_size, view.target_force_score_mev_per_a))
                if len(monitor_rows) >= min(width, 4):
                    order = _score_order(
                        monitor_rows,
                        epsilon=execution_plan_to_coarse_epsilon(execution_plan),
                        boundary_preserve_size=boundary,
                    )
                    monitor_survivors = tuple(order[: min(width, 4)])
                else:
                    monitor_survivors = ()
                exact = set(monitor_survivors) == full_set
                monitor_eq_hits[monitor] += int(exact)
                monitor_finalist_hits[monitor] += sum(v in monitor_survivors for v in reference_finalists)
                if not exact:
                    monitor_global_ok[monitor] = False

        denom_finalists = max(1, total_finalists)
        denom_seeds = max(1, total_seeds)
        epoch3_recall = coarse_hits / denom_finalists
        epoch10_recall = short_hits / denom_finalists
        epoch3_winner = coarse_winner_hits / denom_seeds
        epoch10_winner = short_winner_hits / denom_seeds
        monitor_eq = tuple((m, monitor_eq_hits[m] / denom_seeds) for m in policy.monitor_configuration_candidates)
        monitor_recall = tuple((m, monitor_finalist_hits[m] / denom_finalists) for m in policy.monitor_configuration_candidates)
        passed = (
            total_finalists == 2 * total_seeds
            and epoch3_recall + 1.0e-12 >= policy.required_epoch3_finalist_recall
            and epoch10_recall + 1.0e-12 >= policy.required_epoch10_finalist_recall
            and (not policy.require_no_fixed_ceiling_nonconvergence or boundary_nonconverged == 0)
        )
        assessments.append(SizeFidelity2WidthAssessment(
            admission_width=width, population_sizes=population, seed_count=total_seeds,
            epoch3_finalist_recall=epoch3_recall, epoch10_finalist_recall=epoch10_recall,
            epoch3_winner_recall=epoch3_winner, epoch10_winner_recall=epoch10_winner,
            boundary_nonconverged_count=boundary_nonconverged,
            monitor_decision_equivalence_rates=monitor_eq,
            monitor_finalist_recall_rates=monitor_recall,
            passed=passed,
        ))

    recommended = None
    for monitor in policy.monitor_configuration_candidates:
        if not monitor_global_ok[monitor]:
            continue
        if all(dict(a.monitor_finalist_recall_rates)[monitor] + 1.0e-12 >= policy.required_epoch3_finalist_recall for a in assessments):
            recommended = monitor
            break
    if not policy.require_monitor_decision_equivalence:
        recommended = policy.monitor_configuration_candidates[0]
    passed = bool(assessments and all(v.passed for v in assessments) and recommended is not None)
    reason = (
        f"SIZE-FIDELITY2 certified q={list(execution_plan.admission_widths)} with 100% finalist retention at 3/10 epochs; "
        f"smallest exact monitor={recommended}; positive GPU record status={gpu_qualification_status}"
        if passed else
        "SIZE-FIDELITY2 did not satisfy the complete admission-width survivor-recall/monitor/ceiling authority"
    )
    return SizeFidelity2QualificationReport(
        dataset_id=execution_plan.dataset_id, execution_plan_digest=execution_plan.content_digest,
        policy=policy, coverage_qualified_sizes=execution_plan.coverage_qualified_sizes,
        checkpoints=tuple(checkpoints), width_assessments=tuple(assessments),
        recommended_monitor_configurations=recommended, passed=passed,
        gpu_qualification_status=gpu_qualification_status, decision_reason=reason,
    )


def execution_plan_to_halve_policy_epsilon(plan: SizeFidelity2ExecutionPlan) -> float:
    # SIZE-FIDELITY2 is content-bound to the SIZE-HALVE2 plan digest; the
    # production-equivalent v1 epsilon is frozen at 1 meV/A by SIZE-HALVE2.
    return float(plan.practical_equivalence_mev_per_a)


def execution_plan_to_coarse_epsilon(plan: SizeFidelity2ExecutionPlan) -> float:
    return float(plan.coarse_practical_equivalence_mev_per_a)


def validate_size_fidelity2_execution_plan(
    plan: SizeFidelity2ExecutionPlan, *, size_halve2_plan: SizeHalve2Plan, policy: SizeFidelity2Policy | None = None
) -> None:
    rebuilt = build_size_fidelity2_execution_plan(size_halve2_plan, policy=policy or plan.policy)
    if rebuilt.content_digest != plan.content_digest:
        raise TrainingDataInputError("SIZE-FIDELITY2 execution plan differs from recomputed SIZE-HALVE2 authority.")


def validate_size_fidelity2_qualification(
    report: SizeFidelity2QualificationReport, *, execution_plan: SizeFidelity2ExecutionPlan
) -> None:
    if report.execution_plan_digest != execution_plan.content_digest:
        raise TrainingDataInputError("SIZE-FIDELITY2 qualification references a different execution plan.")
    rebuilt = build_size_fidelity2_qualification(
        execution_plan, report.checkpoints, gpu_qualification_status=report.gpu_qualification_status
    )
    if rebuilt.content_digest != report.content_digest:
        raise TrainingDataInputError("SIZE-FIDELITY2 persisted qualification differs from recomputed authority.")
