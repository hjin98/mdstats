"""SIZE-FIDELITY1 calibration authority for the flexible target-size funnel.

The production target-size policy uses hard coverage followed by a coarse
training screen.  This module does not train models itself.  It authenticates
an exhaustive calibration matrix collected from uninterrupted full-horizon
TRAIN2 trajectories and asks whether a proposed low-fidelity screen would have
kept both eventual full-horizon target finalists for every frozen calibration
seed.

The hard qualification requirements are intentionally recall based.  Rank
correlation is recorded only as a diagnostic because a high global correlation
can still hide the one false elimination that matters scientifically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .target_size_study import TargetSizeStudyPolicy, _equivalence_aware_target_order

SIZE_FIDELITY_POLICY_SCHEMA = "mdstats.size-fidelity1-policy.flexible-fidelity.v3"
SIZE_FIDELITY_EXECUTION_PLAN_SCHEMA = "mdstats.size-fidelity1-execution-plan.flexible-fidelity.v3"
SIZE_FIDELITY_METRIC_SCHEMA = "mdstats.size-fidelity1-metric.v1"
SIZE_FIDELITY_CANDIDATE_SCHEMA = "mdstats.size-fidelity1-candidate-assessment.v2"
SIZE_FIDELITY_REPORT_SCHEMA = "mdstats.size-fidelity1-qualification-report.flexible-fidelity.v4"
SIZE_FIDELITY_VERSION = "mdstats.size-fidelity1.coarse-screen-calibration.flexible-fidelity.2026-08.v4"

_FULL_ROLE = "full_development"


def _sorted_unique_ints(values: Sequence[int], *, name: str, minimum: int = 0) -> tuple[int, ...]:
    result = tuple(sorted({int(v) for v in values}))
    if not result or any(v < minimum for v in result):
        raise TrainingDataInputError(f"{name} must contain unique integers >= {minimum}.")
    return result


def _sorted_unique_floats(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    result = tuple(sorted({float(v) for v in values}))
    if not result or any((not math.isfinite(v) or v <= 0.0) for v in result):
        raise TrainingDataInputError(f"{name} must contain positive finite values.")
    return result


@dataclass(frozen=True, slots=True)
class SizeFidelityCalibrationPolicy:
    """Frozen scientific calibration matrix for SIZE-FIDELITY1.

    The first coarse epoch and first equivalence width are the current
    production defaults.  Later coarse epochs and wider equivalence bands are
    fallback hypotheses to test in the same exhaustive full-horizon campaign if
    the configured production coarse boundary is not sufficiently faithful.
    """

    screening_seeds: tuple[int, ...] = (1, 2, 3)
    coarse_epoch_candidates: tuple[int, ...] = (1, 2)
    coarse_monitor_configuration_candidates: tuple[int, ...] = (128, 256, 512, 1024)
    coarse_equivalence_candidates_mev_per_a: tuple[float, ...] = (1.0, 2.0, 4.0)
    required_coarse_finalist_recall: float = 1.0
    required_short_finalist_recall: float = 1.0
    require_monitor_decision_equivalence: bool = True
    minimum_calibration_seeds: int = 3
    authority_version: str = SIZE_FIDELITY_VERSION

    def __post_init__(self) -> None:
        seeds = _sorted_unique_ints(self.screening_seeds, name="SIZE-FIDELITY1 screening_seeds", minimum=0)
        coarse_epochs = _sorted_unique_ints(self.coarse_epoch_candidates, name="SIZE-FIDELITY1 coarse_epoch_candidates", minimum=1)
        monitor_sizes = _sorted_unique_ints(
            self.coarse_monitor_configuration_candidates,
            name="SIZE-FIDELITY1 coarse_monitor_configuration_candidates",
            minimum=1,
        )
        epsilons = _sorted_unique_floats(
            self.coarse_equivalence_candidates_mev_per_a,
            name="SIZE-FIDELITY1 coarse_equivalence_candidates_mev_per_a",
        )
        minimum = int(self.minimum_calibration_seeds)
        if minimum < 3 or len(seeds) < minimum:
            raise TrainingDataInputError("SIZE-FIDELITY1 requires at least three frozen calibration seeds.")
        for name, value in (
            ("required_coarse_finalist_recall", self.required_coarse_finalist_recall),
            ("required_short_finalist_recall", self.required_short_finalist_recall),
        ):
            value = float(value)
            if not math.isfinite(value) or not (0.0 < value <= 1.0):
                raise TrainingDataInputError(f"SIZE-FIDELITY1 {name} must lie in (0, 1].")
            object.__setattr__(self, name, value)
        if self.authority_version != SIZE_FIDELITY_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY1 authority version.")
        object.__setattr__(self, "screening_seeds", seeds)
        object.__setattr__(self, "coarse_epoch_candidates", coarse_epochs)
        object.__setattr__(self, "coarse_monitor_configuration_candidates", monitor_sizes)
        object.__setattr__(self, "coarse_equivalence_candidates_mev_per_a", epsilons)
        object.__setattr__(self, "minimum_calibration_seeds", minimum)

    def validate_against_target_size_policy(self, policy: TargetSizeStudyPolicy) -> None:
        if self.coarse_epoch_candidates[0] != int(policy.fidelity_epochs[0]):
            raise TrainingDataInputError(
                "SIZE-FIDELITY1 first coarse endpoint must equal the current target-size v5 production endpoint."
            )
        if any(epoch >= int(policy.fidelity_epochs[1]) for epoch in self.coarse_epoch_candidates):
            raise TrainingDataInputError(
                "SIZE-FIDELITY1 coarse endpoint candidates must precede the configured short screen."
            )
        if abs(self.coarse_equivalence_candidates_mev_per_a[0] - float(policy.coarse_practical_equivalence_mev_per_a)) > 1.0e-12:
            raise TrainingDataInputError(
                "SIZE-FIDELITY1 first coarse equivalence width must equal the current target-size v5 production width."
            )
        if int(policy.coarse_survivor_limit) < int(policy.short_finalist_count):
            raise TrainingDataInputError("target-size v5 survivor counts are inconsistent with SIZE-FIDELITY1.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "screening_seeds": list(self.screening_seeds),
            "coarse_epoch_candidates": list(self.coarse_epoch_candidates),
            "coarse_monitor_configuration_candidates": list(self.coarse_monitor_configuration_candidates),
            "coarse_equivalence_candidates_mev_per_a": list(self.coarse_equivalence_candidates_mev_per_a),
            "required_coarse_finalist_recall": self.required_coarse_finalist_recall,
            "required_short_finalist_recall": self.required_short_finalist_recall,
            "require_monitor_decision_equivalence": bool(self.require_monitor_decision_equivalence),
            "minimum_calibration_seeds": self.minimum_calibration_seeds,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelityCalibrationPolicy":
        if payload.get("schema") != SIZE_FIDELITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY1 policy schema.")
        result = cls(
            screening_seeds=tuple(int(v) for v in payload["screening_seeds"]),
            coarse_epoch_candidates=tuple(int(v) for v in payload["coarse_epoch_candidates"]),
            coarse_monitor_configuration_candidates=tuple(int(v) for v in payload["coarse_monitor_configuration_candidates"]),
            coarse_equivalence_candidates_mev_per_a=tuple(float(v) for v in payload["coarse_equivalence_candidates_mev_per_a"]),
            required_coarse_finalist_recall=float(payload["required_coarse_finalist_recall"]),
            required_short_finalist_recall=float(payload["required_short_finalist_recall"]),
            require_monitor_decision_equivalence=bool(payload["require_monitor_decision_equivalence"]),
            minimum_calibration_seeds=int(payload["minimum_calibration_seeds"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SizeFidelityExecutionPlan:
    """Exact exhaustive run/evaluation matrix required to execute SIZE-FIDELITY1."""

    dataset_id: str
    target_size_candidate_authority_digest: str
    target_size_policy_digest: str
    calibration_policy: SizeFidelityCalibrationPolicy
    target_sizes: tuple[int, ...]
    required_training_runs: tuple[tuple[int, int], ...]
    required_checkpoint_epochs: tuple[int, ...]
    short_screen_epoch: int
    final_screen_epoch: int
    reference_training_epoch: int
    monitor_views_derived_from_full_predictions: bool = True
    authority_version: str = SIZE_FIDELITY_VERSION

    def __post_init__(self) -> None:
        dataset_id = str(self.dataset_id).strip()
        if not dataset_id:
            raise TrainingDataInputError("SIZE-FIDELITY1 execution-plan dataset_id cannot be empty.")
        sizes = _sorted_unique_ints(self.target_sizes, name="SIZE-FIDELITY1 execution-plan target_sizes", minimum=1)
        runs = tuple(sorted((int(seed), int(size)) for seed, size in self.required_training_runs))
        expected_runs = tuple((seed, size) for seed in self.calibration_policy.screening_seeds for size in sizes)
        if runs != tuple(sorted(expected_runs)):
            raise TrainingDataInputError("SIZE-FIDELITY1 execution plan must contain every seed x coverage-qualified-size run exactly once.")
        checkpoints = _sorted_unique_ints(self.required_checkpoint_epochs, name="SIZE-FIDELITY1 required_checkpoint_epochs", minimum=1)
        short_epoch, final_epoch, reference_epoch = (
            int(self.short_screen_epoch), int(self.final_screen_epoch), int(self.reference_training_epoch)
        )
        if not (0 < short_epoch < final_epoch <= reference_epoch):
            raise TrainingDataInputError("SIZE-FIDELITY1 execution-plan short/final epochs are invalid.")
        expected_checkpoints = tuple(sorted(set(self.calibration_policy.coarse_epoch_candidates + (short_epoch, final_epoch, reference_epoch))))
        if checkpoints != expected_checkpoints:
            raise TrainingDataInputError("SIZE-FIDELITY1 execution-plan checkpoints do not match the calibration policy and semantic screen/reference boundaries.")
        if not self.monitor_views_derived_from_full_predictions:
            raise TrainingDataInputError("SIZE-FIDELITY1 v1 requires monitor metrics to be derived from full-role prediction authority, not repeated inference.")
        if self.authority_version != SIZE_FIDELITY_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY1 execution-plan authority version.")
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "target_size_candidate_authority_digest", validate_digest(self.target_size_candidate_authority_digest, name="target_size_candidate_authority_digest"))
        object.__setattr__(self, "target_size_policy_digest", validate_digest(self.target_size_policy_digest, name="target_size_policy_digest"))
        object.__setattr__(self, "target_sizes", sizes)
        object.__setattr__(self, "required_training_runs", runs)
        object.__setattr__(self, "required_checkpoint_epochs", checkpoints)
        object.__setattr__(self, "short_screen_epoch", short_epoch)
        object.__setattr__(self, "final_screen_epoch", final_epoch)
        object.__setattr__(self, "reference_training_epoch", reference_epoch)

    @property
    def expected_training_run_count(self) -> int:
        return len(self.required_training_runs)

    @property
    def expected_checkpoint_count(self) -> int:
        return self.expected_training_run_count * len(self.required_checkpoint_epochs)

    @property
    def expected_full_role_inference_count(self) -> int:
        return self.expected_checkpoint_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY_EXECUTION_PLAN_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_size_candidate_authority_digest": self.target_size_candidate_authority_digest,
            "target_size_policy_digest": self.target_size_policy_digest,
            "calibration_policy": self.calibration_policy.to_dict(),
            "target_sizes": list(self.target_sizes),
            "required_training_runs": [list(v) for v in self.required_training_runs],
            "required_checkpoint_epochs": list(self.required_checkpoint_epochs),
            "short_screen_epoch": self.short_screen_epoch,
            "final_screen_epoch": self.final_screen_epoch,
            "reference_training_epoch": self.reference_training_epoch,
            "monitor_views_derived_from_full_predictions": self.monitor_views_derived_from_full_predictions,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelityExecutionPlan":
        if payload.get("schema") != SIZE_FIDELITY_EXECUTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY1 execution-plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_size_candidate_authority_digest=str(payload["target_size_candidate_authority_digest"]),
            target_size_policy_digest=str(payload["target_size_policy_digest"]),
            calibration_policy=SizeFidelityCalibrationPolicy.from_dict(payload["calibration_policy"]),
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            required_training_runs=tuple((int(a), int(b)) for a, b in payload["required_training_runs"]),
            required_checkpoint_epochs=tuple(int(v) for v in payload["required_checkpoint_epochs"]),
            short_screen_epoch=int(payload["short_screen_epoch"]),
            final_screen_epoch=int(payload["final_screen_epoch"]),
            reference_training_epoch=int(payload["reference_training_epoch"]),
            monitor_views_derived_from_full_predictions=bool(payload["monitor_views_derived_from_full_predictions"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY1 execution-plan digest mismatch.")
        return result


def build_size_fidelity_execution_plan(
    *,
    dataset_id: str,
    target_size_candidate_authority_digest: str,
    target_size_policy: TargetSizeStudyPolicy,
    target_sizes: Sequence[int],
    training_horizon_epochs: int = 30,
    calibration_policy: SizeFidelityCalibrationPolicy | None = None,
) -> SizeFidelityExecutionPlan:
    policy = calibration_policy or SizeFidelityCalibrationPolicy()
    policy.validate_against_target_size_policy(target_size_policy)
    sizes = _sorted_unique_ints(target_sizes, name="SIZE-FIDELITY1 target_sizes", minimum=1)
    if len(sizes) < target_size_policy.minimum_qualified_sizes:
        raise TrainingDataInputError("SIZE-FIDELITY1 execution plan requires at least the target-size v5 minimum coverage qualifiers.")
    runs = tuple((seed, size) for seed in policy.screening_seeds for size in sizes)
    reference_epoch = int(training_horizon_epochs)
    if target_size_policy.fidelity_epochs[-1] > reference_epoch:
        raise TrainingDataInputError("SIZE-FIDELITY1 final screen exceeds its full-reference TRAIN2 horizon.")
    checkpoints = tuple(sorted(set(policy.coarse_epoch_candidates + (target_size_policy.fidelity_epochs[1], target_size_policy.fidelity_epochs[2], reference_epoch))))
    return SizeFidelityExecutionPlan(
        dataset_id=dataset_id,
        target_size_candidate_authority_digest=target_size_candidate_authority_digest,
        target_size_policy_digest=target_size_policy.policy_digest,
        calibration_policy=policy,
        target_sizes=sizes,
        required_training_runs=runs,
        required_checkpoint_epochs=checkpoints,
        short_screen_epoch=int(target_size_policy.fidelity_epochs[1]),
        final_screen_epoch=int(target_size_policy.fidelity_epochs[2]),
        reference_training_epoch=reference_epoch,
    )


@dataclass(frozen=True, slots=True)
class SizeFidelityMetric:
    """One target-only endpoint measurement from an uninterrupted full-horizon run."""

    optimizer_seed: int
    target_size: int
    epoch: int
    target_force_score_mev_per_a: float
    numerical_valid: bool
    target_hard_gates_passed: bool
    evaluation_role_kind: str
    monitor_configurations: int | None
    foundation_identity_digest: str
    training_policy_digest: str
    schedule_digest: str
    training_run_digest: str
    checkpoint_digest: str
    evaluation_role_digest: str
    target_evaluation_digest: str

    def __post_init__(self) -> None:
        seed, size, epoch = int(self.optimizer_seed), int(self.target_size), int(self.epoch)
        score = float(self.target_force_score_mev_per_a)
        role = str(self.evaluation_role_kind)
        monitor = None if self.monitor_configurations is None else int(self.monitor_configurations)
        if seed < 0 or size <= 0 or epoch <= 0:
            raise TrainingDataInputError("SIZE-FIDELITY1 seed, target size, and epoch are invalid.")
        if not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError("SIZE-FIDELITY1 target force score must be finite and nonnegative.")
        if role not in {_FULL_ROLE, "coarse_monitor"}:
            raise TrainingDataInputError("SIZE-FIDELITY1 evaluation_role_kind must be full_development or coarse_monitor.")
        if role == _FULL_ROLE and monitor is not None:
            raise TrainingDataInputError("SIZE-FIDELITY1 full-development evidence cannot carry a monitor size.")
        if role == "coarse_monitor" and (monitor is None or monitor <= 0):
            raise TrainingDataInputError("SIZE-FIDELITY1 coarse-monitor evidence requires a positive monitor size.")
        for name in (
            "foundation_identity_digest", "training_policy_digest", "schedule_digest", "training_run_digest",
            "checkpoint_digest", "evaluation_role_digest", "target_evaluation_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "optimizer_seed", seed)
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "epoch", epoch)
        object.__setattr__(self, "target_force_score_mev_per_a", score)
        object.__setattr__(self, "evaluation_role_kind", role)
        object.__setattr__(self, "monitor_configurations", monitor)

    @property
    def admissible(self) -> bool:
        return bool(self.numerical_valid and self.target_hard_gates_passed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY_METRIC_SCHEMA,
            "optimizer_seed": self.optimizer_seed,
            "target_size": self.target_size,
            "epoch": self.epoch,
            "target_force_score_mev_per_a": self.target_force_score_mev_per_a,
            "numerical_valid": bool(self.numerical_valid),
            "target_hard_gates_passed": bool(self.target_hard_gates_passed),
            "evaluation_role_kind": self.evaluation_role_kind,
            "monitor_configurations": self.monitor_configurations,
            "foundation_identity_digest": self.foundation_identity_digest,
            "training_policy_digest": self.training_policy_digest,
            "schedule_digest": self.schedule_digest,
            "training_run_digest": self.training_run_digest,
            "checkpoint_digest": self.checkpoint_digest,
            "evaluation_role_digest": self.evaluation_role_digest,
            "target_evaluation_digest": self.target_evaluation_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelityMetric":
        if payload.get("schema") != SIZE_FIDELITY_METRIC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY1 metric schema.")
        kwargs = dict(payload)
        kwargs.pop("schema", None); kwargs.pop("content_digest", None)
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY1 metric digest mismatch.")
        return result


def _average_ranks(values: Sequence[float]) -> np.ndarray:
    data = np.asarray(values, dtype=np.float64)
    order = np.argsort(data, kind="mergesort")
    ranks = np.empty(data.size, dtype=np.float64)
    i = 0
    while i < data.size:
        j = i + 1
        while j < data.size and data[order[j]] == data[order[i]]:
            j += 1
        rank = 0.5 * ((i + 1) + j)
        ranks[order[i:j]] = rank
        i = j
    return ranks


def _spearman_rho(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return float("nan")
    a, b = _average_ranks(left), _average_ranks(right)
    a = a - float(np.mean(a)); b = b - float(np.mean(b))
    denom = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    if denom == 0.0:
        return 1.0 if np.array_equal(a, b) else 0.0
    return float(np.sum(a * b) / denom)


def _metric_key(item: SizeFidelityMetric) -> tuple[int, int, int, str, int | None]:
    return (item.optimizer_seed, item.target_size, item.epoch, item.evaluation_role_kind, item.monitor_configurations)


def _screen_order(
    metrics: Sequence[SizeFidelityMetric],
    *,
    epsilon: float,
    boundary_size: int | None,
) -> tuple[int, ...]:
    admissible = tuple(item for item in metrics if item.admissible)
    if not admissible:
        return ()
    # _equivalence_aware_target_order reads only target_size and target_force_score_mev_per_a.
    # ``boundary_size`` remains in this calibration helper's call surface for
    # historical result compatibility, but current target-size v5 deliberately
    # gives the fixed ceiling no ordering priority inside an equivalence band.
    del boundary_size
    return _equivalence_aware_target_order(admissible, epsilon=float(epsilon))


@dataclass(frozen=True, slots=True)
class SizeFidelityCandidateAssessment:
    coarse_epoch: int
    monitor_configurations: int
    coarse_equivalence_mev_per_a: float
    seed_count: int
    monitor_decision_equivalence_rate: float
    coarse_finalist_recall: float
    short_finalist_recall: float
    final_screen_winner_recall: float
    coarse_winner_recall: float
    short_winner_recall: float
    boundary_miss_count: int
    mean_coarse_final_rank_spearman_rho: float
    coarse_survivor_sizes_by_seed: tuple[tuple[int, tuple[int, ...]], ...]
    short_finalist_sizes_by_seed: tuple[tuple[int, tuple[int, ...]], ...]
    final_screen_sizes_by_seed: tuple[tuple[int, tuple[int, ...]], ...]
    reference_finalist_sizes_by_seed: tuple[tuple[int, tuple[int, ...]], ...]
    passed: bool
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if int(self.coarse_epoch) <= 0 or int(self.monitor_configurations) <= 0 or int(self.seed_count) <= 0:
            raise TrainingDataInputError("SIZE-FIDELITY1 candidate assessment has invalid dimensions.")
        epsilon = float(self.coarse_equivalence_mev_per_a)
        if not math.isfinite(epsilon) or epsilon <= 0.0:
            raise TrainingDataInputError("SIZE-FIDELITY1 candidate epsilon must be positive and finite.")
        for name in (
            "monitor_decision_equivalence_rate", "coarse_finalist_recall", "short_finalist_recall",
            "final_screen_winner_recall",
            "coarse_winner_recall", "short_winner_recall",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not (0.0 <= value <= 1.0):
                raise TrainingDataInputError(f"SIZE-FIDELITY1 {name} must lie in [0, 1].")
            object.__setattr__(self, name, value)
        rho = float(self.mean_coarse_final_rank_spearman_rho)
        if not math.isfinite(rho) or not (-1.0 <= rho <= 1.0):
            raise TrainingDataInputError("SIZE-FIDELITY1 mean Spearman rho must lie in [-1, 1].")
        object.__setattr__(self, "coarse_epoch", int(self.coarse_epoch))
        object.__setattr__(self, "monitor_configurations", int(self.monitor_configurations))
        object.__setattr__(self, "coarse_equivalence_mev_per_a", epsilon)
        object.__setattr__(self, "seed_count", int(self.seed_count))
        object.__setattr__(self, "boundary_miss_count", int(self.boundary_miss_count))
        object.__setattr__(self, "mean_coarse_final_rank_spearman_rho", rho)
        object.__setattr__(self, "coarse_survivor_sizes_by_seed", tuple(sorted((int(s), tuple(int(v) for v in sizes)) for s, sizes in self.coarse_survivor_sizes_by_seed)))
        object.__setattr__(self, "short_finalist_sizes_by_seed", tuple(sorted((int(s), tuple(int(v) for v in sizes)) for s, sizes in self.short_finalist_sizes_by_seed)))
        object.__setattr__(self, "final_screen_sizes_by_seed", tuple(sorted((int(s), tuple(int(v) for v in sizes)) for s, sizes in self.final_screen_sizes_by_seed)))
        object.__setattr__(self, "reference_finalist_sizes_by_seed", tuple(sorted((int(s), tuple(int(v) for v in sizes)) for s, sizes in self.reference_finalist_sizes_by_seed)))
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY_CANDIDATE_SCHEMA,
            "coarse_epoch": self.coarse_epoch,
            "monitor_configurations": self.monitor_configurations,
            "coarse_equivalence_mev_per_a": self.coarse_equivalence_mev_per_a,
            "seed_count": self.seed_count,
            "monitor_decision_equivalence_rate": self.monitor_decision_equivalence_rate,
            "coarse_finalist_recall": self.coarse_finalist_recall,
            "short_finalist_recall": self.short_finalist_recall,
            "final_screen_winner_recall": self.final_screen_winner_recall,
            "coarse_winner_recall": self.coarse_winner_recall,
            "short_winner_recall": self.short_winner_recall,
            "boundary_miss_count": self.boundary_miss_count,
            "mean_coarse_final_rank_spearman_rho": self.mean_coarse_final_rank_spearman_rho,
            "coarse_survivor_sizes_by_seed": [[s, list(v)] for s, v in self.coarse_survivor_sizes_by_seed],
            "short_finalist_sizes_by_seed": [[s, list(v)] for s, v in self.short_finalist_sizes_by_seed],
            "final_screen_sizes_by_seed": [[s, list(v)] for s, v in self.final_screen_sizes_by_seed],
            "reference_finalist_sizes_by_seed": [[s, list(v)] for s, v in self.reference_finalist_sizes_by_seed],
            "passed": bool(self.passed),
            "failure_reasons": list(self.failure_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelityCandidateAssessment":
        if payload.get("schema") != SIZE_FIDELITY_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY1 candidate schema.")
        kwargs = dict(payload); kwargs.pop("schema", None); kwargs.pop("content_digest", None)
        for key in ("coarse_survivor_sizes_by_seed", "short_finalist_sizes_by_seed", "final_screen_sizes_by_seed", "reference_finalist_sizes_by_seed"):
            kwargs[key] = tuple((int(s), tuple(int(v) for v in sizes)) for s, sizes in kwargs[key])
        kwargs["failure_reasons"] = tuple(str(v) for v in kwargs.get("failure_reasons", ()))
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY1 candidate digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SizeFidelityQualificationReport:
    dataset_id: str
    target_size_candidate_authority_digest: str
    target_size_policy_digest: str
    reference_training_epoch: int
    calibration_policy: SizeFidelityCalibrationPolicy
    target_sizes: tuple[int, ...]
    metrics: tuple[SizeFidelityMetric, ...]
    candidate_assessments: tuple[SizeFidelityCandidateAssessment, ...]
    recommended_coarse_epoch: int | None
    recommended_monitor_configurations: int | None
    recommended_coarse_equivalence_mev_per_a: float | None
    passed: bool
    decision_reason: str
    authority_version: str = SIZE_FIDELITY_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.authority_version != SIZE_FIDELITY_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-FIDELITY1 report authority version.")
        dataset_id = str(self.dataset_id).strip()
        if not dataset_id:
            raise TrainingDataInputError("SIZE-FIDELITY1 dataset_id cannot be empty.")
        sizes = _sorted_unique_ints(self.target_sizes, name="SIZE-FIDELITY1 target_sizes", minimum=1)
        if len(sizes) < 3:
            raise TrainingDataInputError("SIZE-FIDELITY1 requires at least three coverage-qualified sizes.")
        metrics = tuple(sorted(self.metrics, key=_metric_key))
        if len({_metric_key(v) for v in metrics}) != len(metrics):
            raise TrainingDataInputError("SIZE-FIDELITY1 metrics contain duplicate scientific keys.")
        assessments = tuple(sorted(self.candidate_assessments, key=lambda x: (x.coarse_epoch, x.monitor_configurations, x.coarse_equivalence_mev_per_a)))
        recommended = (self.recommended_coarse_epoch, self.recommended_monitor_configurations, self.recommended_coarse_equivalence_mev_per_a)
        if bool(self.passed) != all(v is not None for v in recommended):
            raise TrainingDataInputError("SIZE-FIDELITY1 passed flag and recommendation presence disagree.")
        if self.passed:
            if not any(
                item.passed
                and item.coarse_epoch == int(self.recommended_coarse_epoch)
                and item.monitor_configurations == int(self.recommended_monitor_configurations)
                and abs(item.coarse_equivalence_mev_per_a - float(self.recommended_coarse_equivalence_mev_per_a)) <= 1.0e-12
                for item in assessments
            ):
                raise TrainingDataInputError("SIZE-FIDELITY1 recommendation does not reference a passing candidate assessment.")
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "target_size_candidate_authority_digest", validate_digest(self.target_size_candidate_authority_digest, name="target_size_candidate_authority_digest"))
        object.__setattr__(self, "target_size_policy_digest", validate_digest(self.target_size_policy_digest, name="target_size_policy_digest"))
        reference_epoch = int(self.reference_training_epoch)
        if reference_epoch <= 0:
            raise TrainingDataInputError("SIZE-FIDELITY1 reference training epoch must be positive.")
        object.__setattr__(self, "reference_training_epoch", reference_epoch)
        object.__setattr__(self, "target_sizes", sizes)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "candidate_assessments", assessments)
        object.__setattr__(self, "decision_reason", str(self.decision_reason))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_FIDELITY_REPORT_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_size_candidate_authority_digest": self.target_size_candidate_authority_digest,
            "target_size_policy_digest": self.target_size_policy_digest,
            "reference_training_epoch": self.reference_training_epoch,
            "calibration_policy": self.calibration_policy.to_dict(),
            "target_sizes": list(self.target_sizes),
            "metrics": [v.to_dict() for v in self.metrics],
            "candidate_assessments": [v.to_dict() for v in self.candidate_assessments],
            "recommended_coarse_epoch": self.recommended_coarse_epoch,
            "recommended_monitor_configurations": self.recommended_monitor_configurations,
            "recommended_coarse_equivalence_mev_per_a": self.recommended_coarse_equivalence_mev_per_a,
            "passed": bool(self.passed),
            "decision_reason": self.decision_reason,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached:
            return cached
        result = digest(self._payload())
        object.__setattr__(self, "_content_digest_cache", result)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeFidelityQualificationReport":
        if payload.get("schema") != SIZE_FIDELITY_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-FIDELITY1 qualification-report schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_size_candidate_authority_digest=str(payload["target_size_candidate_authority_digest"]),
            target_size_policy_digest=str(payload["target_size_policy_digest"]),
            reference_training_epoch=int(payload["reference_training_epoch"]),
            calibration_policy=SizeFidelityCalibrationPolicy.from_dict(payload["calibration_policy"]),
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            metrics=tuple(SizeFidelityMetric.from_dict(v) for v in payload["metrics"]),
            candidate_assessments=tuple(SizeFidelityCandidateAssessment.from_dict(v) for v in payload["candidate_assessments"]),
            recommended_coarse_epoch=None if payload.get("recommended_coarse_epoch") is None else int(payload["recommended_coarse_epoch"]),
            recommended_monitor_configurations=None if payload.get("recommended_monitor_configurations") is None else int(payload["recommended_monitor_configurations"]),
            recommended_coarse_equivalence_mev_per_a=None if payload.get("recommended_coarse_equivalence_mev_per_a") is None else float(payload["recommended_coarse_equivalence_mev_per_a"]),
            passed=bool(payload["passed"]),
            decision_reason=str(payload["decision_reason"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-FIDELITY1 qualification-report digest mismatch.")
        return result


def build_size_fidelity_qualification(
    *,
    dataset_id: str,
    target_size_candidate_authority_digest: str,
    target_size_policy: TargetSizeStudyPolicy,
    target_sizes: Sequence[int],
    metrics: Sequence[SizeFidelityMetric],
    calibration_policy: SizeFidelityCalibrationPolicy | None = None,
    training_horizon_epochs: int = 30,
) -> SizeFidelityQualificationReport:
    """Evaluate exhaustive target-size trajectories and certify a coarse screen.

    The complete metric matrix is required for every frozen seed and every
    coverage-qualified target size.  At each candidate coarse endpoint we need
    both full-development evidence and every proposed coarse-monitor size; the
    full-development role is also required at epochs 10 and 30.
    """

    policy = calibration_policy or SizeFidelityCalibrationPolicy()
    policy.validate_against_target_size_policy(target_size_policy)
    reference_epoch = int(training_horizon_epochs)
    if target_size_policy.fidelity_epochs[-1] > reference_epoch:
        raise TrainingDataInputError("SIZE-FIDELITY1 final screen lies beyond the full reference horizon.")
    sizes = _sorted_unique_ints(target_sizes, name="SIZE-FIDELITY1 target_sizes", minimum=1)
    if len(sizes) < target_size_policy.minimum_qualified_sizes:
        raise TrainingDataInputError("SIZE-FIDELITY1 target sizes do not satisfy target-size v5 coverage-qualifier minimum.")
    metric_tuple = tuple(sorted(metrics, key=_metric_key))
    metric_map = {_metric_key(v): v for v in metric_tuple}
    if len(metric_map) != len(metric_tuple):
        raise TrainingDataInputError("SIZE-FIDELITY1 metric matrix contains duplicate keys.")

    # Common scientific identities must not drift across the calibration matrix.
    for attr, text in (
        ("foundation_identity_digest", "foundation identity"),
        ("training_policy_digest", "TRAIN2 policy"),
        ("schedule_digest", "training schedule"),
    ):
        identities = {getattr(v, attr) for v in metric_tuple}
        if len(identities) != 1:
            raise TrainingDataInputError(f"SIZE-FIDELITY1 {text} changed inside the calibration matrix.")

    required_keys: list[tuple[int, int, int, str, int | None]] = []
    for seed in policy.screening_seeds:
        for size in sizes:
            for epoch in policy.coarse_epoch_candidates:
                required_keys.append((seed, size, epoch, _FULL_ROLE, None))
                for monitor in policy.coarse_monitor_configuration_candidates:
                    required_keys.append((seed, size, epoch, "coarse_monitor", monitor))
            required_keys.append((seed, size, int(target_size_policy.fidelity_epochs[1]), _FULL_ROLE, None))
            required_keys.append((seed, size, int(target_size_policy.fidelity_epochs[2]), _FULL_ROLE, None))
            required_keys.append((seed, size, reference_epoch, _FULL_ROLE, None))
    expected_key_set = set(required_keys)
    actual_key_set = set(metric_map)
    missing = tuple(sorted(expected_key_set - actual_key_set))
    extra = tuple(sorted(actual_key_set - expected_key_set, key=str))
    if missing or extra:
        preview_missing = ", ".join(str(v) for v in missing[:4])
        preview_extra = ", ".join(str(v) for v in extra[:4])
        raise TrainingDataInputError(
            "SIZE-FIDELITY1 calibration matrix must exactly equal the frozen scientific grid; "
            f"missing={len(missing)} [{preview_missing}], extra={len(extra)} [{preview_extra}]."
        )

    role_identities: dict[tuple[str, int | None], set[str]] = {}
    for item in metric_tuple:
        role_identities.setdefault((item.evaluation_role_kind, item.monitor_configurations), set()).add(item.evaluation_role_digest)
    if any(len(values) != 1 for values in role_identities.values()):
        raise TrainingDataInputError("SIZE-FIDELITY1 evaluation-role identity changed across seeds, sizes, or epochs.")

    # Same seed/target trajectory must identify one uninterrupted checkpoint stream.
    for seed in policy.screening_seeds:
        for size in sizes:
            run_ids = {
                metric_map[key].training_run_digest
                for key in required_keys
                if key[0] == seed and key[1] == size
            }
            if len(run_ids) != 1:
                raise TrainingDataInputError(f"SIZE-FIDELITY1 n{size}/seed{seed} does not identify one uninterrupted training run.")
            by_epoch: dict[int, set[str]] = {}
            for key in required_keys:
                if key[0] == seed and key[1] == size:
                    by_epoch.setdefault(key[2], set()).add(metric_map[key].checkpoint_digest)
            if any(len(values) != 1 for values in by_epoch.values()):
                raise TrainingDataInputError(f"SIZE-FIDELITY1 n{size}/seed{seed} evaluation roles disagree on checkpoint identity at one epoch.")

    assessments: list[SizeFidelityCandidateAssessment] = []
    boundary_size = max(sizes)
    final_epsilon = float(target_size_policy.practical_equivalence_mev_per_a)
    short_count = int(target_size_policy.short_finalist_count)
    coarse_count = int(target_size_policy.coarse_survivor_limit)

    for coarse_epoch in policy.coarse_epoch_candidates:
        for monitor_size in policy.coarse_monitor_configuration_candidates:
            for coarse_epsilon in policy.coarse_equivalence_candidates_mev_per_a:
                monitor_matches = 0
                coarse_finalists_retained = 0
                short_finalists_retained = 0
                final_screen_winner_retained = 0
                coarse_winner_retained = 0
                short_winner_retained = 0
                boundary_misses = 0
                rhos: list[float] = []
                coarse_sets: list[tuple[int, tuple[int, ...]]] = []
                short_sets: list[tuple[int, tuple[int, ...]]] = []
                final_screen_sets: list[tuple[int, tuple[int, ...]]] = []
                final_sets: list[tuple[int, tuple[int, ...]]] = []

                for seed in policy.screening_seeds:
                    reference_metrics = [metric_map[(seed, size, reference_epoch, _FULL_ROLE, None)] for size in sizes]
                    reference_order = _screen_order(reference_metrics, epsilon=final_epsilon, boundary_size=None)
                    if len(reference_order) < short_count:
                        raise TrainingDataInputError(f"SIZE-FIDELITY1 seed {seed} has fewer than {short_count} valid full-horizon target candidates.")
                    reference_finalists = tuple(reference_order[:short_count])
                    reference_winner = reference_finalists[0]

                    coarse_full = [metric_map[(seed, size, coarse_epoch, _FULL_ROLE, None)] for size in sizes]
                    coarse_monitor = [metric_map[(seed, size, coarse_epoch, "coarse_monitor", monitor_size)] for size in sizes]
                    full_order = _screen_order(coarse_full, epsilon=coarse_epsilon, boundary_size=boundary_size)
                    monitor_order = _screen_order(coarse_monitor, epsilon=coarse_epsilon, boundary_size=boundary_size)
                    if len(full_order) < min(coarse_count, len(sizes)) or len(monitor_order) < min(coarse_count, len(sizes)):
                        raise TrainingDataInputError(f"SIZE-FIDELITY1 seed {seed} has insufficient valid coarse candidates at epoch {coarse_epoch}.")
                    full_survivors = tuple(full_order[:min(coarse_count, len(full_order))])
                    coarse_survivors = tuple(monitor_order[:min(coarse_count, len(monitor_order))])
                    if set(full_survivors) == set(coarse_survivors):
                        monitor_matches += 1

                    short_metrics = [metric_map[(seed, size, int(target_size_policy.fidelity_epochs[1]), _FULL_ROLE, None)] for size in coarse_survivors]
                    short_order = _screen_order(short_metrics, epsilon=coarse_epsilon, boundary_size=boundary_size)
                    if len(short_order) < short_count:
                        raise TrainingDataInputError(
                            f"SIZE-FIDELITY1 seed {seed} has insufficient valid short-screen survivors."
                        )
                    short_finalists = tuple(short_order[:short_count])

                    final_screen_metrics = [
                        metric_map[(seed, size, int(target_size_policy.fidelity_epochs[2]), _FULL_ROLE, None)]
                        for size in short_finalists
                    ]
                    final_screen_order = _screen_order(
                        final_screen_metrics, epsilon=final_epsilon, boundary_size=boundary_size
                    )
                    if len(final_screen_order) < short_count:
                        raise TrainingDataInputError(
                            f"SIZE-FIDELITY1 seed {seed} has insufficient valid final-screen finalists."
                        )
                    final_screen_winner = final_screen_order[0]

                    if reference_winner in coarse_survivors:
                        coarse_winner_retained += 1
                    if reference_winner in short_finalists:
                        short_winner_retained += 1
                    if reference_winner == final_screen_winner:
                        final_screen_winner_retained += 1
                    if set(reference_finalists).issubset(coarse_survivors):
                        coarse_finalists_retained += 1
                    if set(reference_finalists).issubset(short_finalists):
                        short_finalists_retained += 1
                    if boundary_size in reference_finalists and (
                        boundary_size not in coarse_survivors or boundary_size not in short_finalists
                    ):
                        boundary_misses += 1

                    coarse_score_by_size = {v.target_size: v.target_force_score_mev_per_a for v in coarse_full}
                    reference_score_by_size = {v.target_size: v.target_force_score_mev_per_a for v in reference_metrics}
                    common = [size for size in sizes if metric_map[(seed, size, coarse_epoch, _FULL_ROLE, None)].admissible and metric_map[(seed, size, reference_epoch, _FULL_ROLE, None)].admissible]
                    if len(common) >= 2:
                        rho = _spearman_rho([coarse_score_by_size[s] for s in common], [reference_score_by_size[s] for s in common])
                        if math.isfinite(rho):
                            rhos.append(rho)
                    coarse_sets.append((seed, coarse_survivors))
                    short_sets.append((seed, short_finalists))
                    final_screen_sets.append((seed, final_screen_order))
                    final_sets.append((seed, reference_finalists))

                n = len(policy.screening_seeds)
                monitor_rate = monitor_matches / n
                coarse_finalist_recall = coarse_finalists_retained / n
                short_finalist_recall = short_finalists_retained / n
                final_screen_winner_recall = final_screen_winner_retained / n
                coarse_winner_recall = coarse_winner_retained / n
                short_winner_recall = short_winner_retained / n
                mean_rho = float(np.mean(rhos)) if rhos else 0.0
                failures: list[str] = []
                if policy.require_monitor_decision_equivalence and monitor_rate < 1.0:
                    failures.append("coarse_monitor_promotion_differs_from_full_development")
                if coarse_finalist_recall + 1.0e-12 < policy.required_coarse_finalist_recall:
                    failures.append("coarse_screen_drops_full_horizon_reference_finalist")
                if short_finalist_recall + 1.0e-12 < policy.required_short_finalist_recall:
                    failures.append("short_screen_drops_full_horizon_reference_finalist")
                if final_screen_winner_recall < 1.0:
                    failures.append("final_screen_winner_differs_from_full_horizon_reference")
                if boundary_misses:
                    failures.append("largest_boundary_finalist_missed")
                assessments.append(SizeFidelityCandidateAssessment(
                    coarse_epoch=coarse_epoch,
                    monitor_configurations=monitor_size,
                    coarse_equivalence_mev_per_a=coarse_epsilon,
                    seed_count=n,
                    monitor_decision_equivalence_rate=monitor_rate,
                    coarse_finalist_recall=coarse_finalist_recall,
                    short_finalist_recall=short_finalist_recall,
                    final_screen_winner_recall=final_screen_winner_recall,
                    coarse_winner_recall=coarse_winner_recall,
                    short_winner_recall=short_winner_recall,
                    boundary_miss_count=boundary_misses,
                    mean_coarse_final_rank_spearman_rho=mean_rho,
                    coarse_survivor_sizes_by_seed=tuple(coarse_sets),
                    short_finalist_sizes_by_seed=tuple(short_sets),
                    final_screen_sizes_by_seed=tuple(final_screen_sets),
                    reference_finalist_sizes_by_seed=tuple(final_sets),
                    passed=not failures,
                    failure_reasons=tuple(failures),
                ))

    passing = [item for item in assessments if item.passed]
    recommendation: SizeFidelityCandidateAssessment | None = None
    if passing:
        # Scientific/performance preference: earliest faithful endpoint first,
        # then the smallest faithful monitor.  Within that pair, do not tighten
        # the equivalence band below the production default; candidates are
        # enumerated from the current width upward and the smallest passing
        # width is retained.
        recommendation = min(
            passing,
            key=lambda x: (x.coarse_epoch, x.monitor_configurations, x.coarse_equivalence_mev_per_a),
        )
    passed = recommendation is not None
    reason = (
        f"SIZE-FIDELITY1 certified epoch {recommendation.coarse_epoch}, monitor {recommendation.monitor_configurations}, "
        f"and coarse equivalence {recommendation.coarse_equivalence_mev_per_a:g} meV/A across {len(policy.screening_seeds)} frozen seeds; "
        f"both full-reference finalists survived coarse/short screens and the final screen agreed at epoch {int(target_size_policy.fidelity_epochs[2])}."
        if recommendation is not None
        else "SIZE-FIDELITY1 found no candidate coarse endpoint/monitor/equivalence combination with complete finalist recall and monitor-decision equivalence."
    )
    return SizeFidelityQualificationReport(
        dataset_id=dataset_id,
        target_size_candidate_authority_digest=target_size_candidate_authority_digest,
        target_size_policy_digest=target_size_policy.policy_digest,
        reference_training_epoch=reference_epoch,
        calibration_policy=policy,
        target_sizes=sizes,
        metrics=metric_tuple,
        candidate_assessments=tuple(assessments),
        recommended_coarse_epoch=None if recommendation is None else recommendation.coarse_epoch,
        recommended_monitor_configurations=None if recommendation is None else recommendation.monitor_configurations,
        recommended_coarse_equivalence_mev_per_a=None if recommendation is None else recommendation.coarse_equivalence_mev_per_a,
        passed=passed,
        decision_reason=reason,
    )


def validate_size_fidelity_qualification(
    report: SizeFidelityQualificationReport,
    *,
    target_size_policy: TargetSizeStudyPolicy,
) -> None:
    """Fail closed when a persisted SIZE-FIDELITY1 report no longer matches policy."""

    report.calibration_policy.validate_against_target_size_policy(target_size_policy)
    if report.target_size_policy_digest != target_size_policy.policy_digest:
        raise TrainingDataInputError("SIZE-FIDELITY1 report references a different target-size v5 policy.")
    rebuilt = build_size_fidelity_qualification(
        dataset_id=report.dataset_id,
        target_size_candidate_authority_digest=report.target_size_candidate_authority_digest,
        target_size_policy=target_size_policy,
        target_sizes=report.target_sizes,
        metrics=report.metrics,
        calibration_policy=report.calibration_policy,
        training_horizon_epochs=report.reference_training_epoch,
    )
    if rebuilt.content_digest != report.content_digest:
        raise TrainingDataInputError("SIZE-FIDELITY1 persisted qualification differs from recomputed authority.")
