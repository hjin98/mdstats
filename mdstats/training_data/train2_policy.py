"""TRAIN2/EVAL2 versioned policy authorities.

The TRAIN2 family deliberately separates concerns that were historically
entangled in :class:`AdaptiveTrainingStopPolicy`.  TRAIN2A establishes the
immutable policy identities and, critically, turns replay retention into a
hard admissibility constraint with zero ranking credit.  TRAIN2B/EVAL2 own the
later runtime scheduler and full checkpoint-trajectory evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest

TRAINING_BUDGET_POLICY_SCHEMA = "mdstats.train2-training-budget-policy.v1"
LEARNING_RATE_SCHEDULE_POLICY_SCHEMA = "mdstats.train2-learning-rate-schedule-policy.v1"
CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA = "mdstats.train2-checkpoint-admissibility-policy.v1"
CHECKPOINT_SELECTION_POLICY_SCHEMA = "mdstats.train2-checkpoint-selection-policy.v1"
TRAIN2_POLICY_FAMILY = "train2"
TRAIN2_DEFAULT_REPLAY_DEGRADATION_EV_PER_ANGSTROM = 0.030
TRAIN2_DEFAULT_PRACTICAL_EQUIVALENCE_EV_PER_ANGSTROM = 0.001
TRAIN2_DEFAULT_BOOTSTRAP_REPLICATES = 2000
TRAIN2_DEFAULT_BOOTSTRAP_CONFIDENCE = 0.95
TRAIN2_DEFAULT_BOOTSTRAP_MIN_BLOCKS = 10


def _finite_positive(value: float, *, name: str, allow_zero: bool = False) -> float:
    value = float(value)
    lower_ok = value >= 0.0 if allow_zero else value > 0.0
    if not math.isfinite(value) or not lower_ok:
        qualifier = "non-negative" if allow_zero else "positive"
        raise TrainingDataInputError(f"{name} must be finite and {qualifier}.")
    return value


def _validate_digest(payload: Mapping[str, Any], current: str, *, label: str) -> None:
    observed = payload.get("policy_digest")
    if observed not in (None, current):
        raise TrainingDataSerializationError(f"{label} digest mismatch.")


@dataclass(frozen=True, slots=True)
class TrainingBudgetPolicy:
    """Fixed-budget TRAIN2 termination authority.

    TRAIN2A freezes this identity; TRAIN2B enforces it at runtime.  Performance
    thresholds are intentionally absent from this schema.
    """

    planned_epochs: int = 30
    checkpoint_interval_epochs: int = 1
    allow_performance_driven_termination: bool = False
    genuine_failure_reasons: tuple[str, ...] = (
        "nonfinite_objective",
        "nonfinite_model_state",
        "nonfinite_optimizer_state",
        "corrupt_restart_state",
        "unrecoverable_runtime_failure",
    )
    serialization_schema: str = field(
        default=TRAINING_BUDGET_POLICY_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != TRAINING_BUDGET_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported TRAIN2 training-budget policy schema.")
        if int(self.planned_epochs) <= 0:
            raise TrainingDataInputError("TRAIN2 planned_epochs must be positive.")
        if int(self.checkpoint_interval_epochs) <= 0:
            raise TrainingDataInputError("TRAIN2 checkpoint_interval_epochs must be positive.")
        if self.allow_performance_driven_termination:
            raise TrainingDataInputError(
                "TRAIN2 forbids target/replay performance-driven termination."
            )
        reasons = tuple(str(v).strip() for v in self.genuine_failure_reasons)
        if not reasons or any(not v for v in reasons) or len(set(reasons)) != len(reasons):
            raise TrainingDataInputError(
                "TRAIN2 genuine_failure_reasons must be unique non-empty identifiers."
            )
        object.__setattr__(self, "genuine_failure_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "planned_epochs": int(self.planned_epochs),
            "checkpoint_interval_epochs": int(self.checkpoint_interval_epochs),
            "allow_performance_driven_termination": False,
            "genuine_failure_reasons": list(self.genuine_failure_reasons),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingBudgetPolicy":
        if payload.get("schema") != TRAINING_BUDGET_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 training-budget policy schema.")
        result = cls(
            planned_epochs=int(payload["planned_epochs"]),
            checkpoint_interval_epochs=int(payload["checkpoint_interval_epochs"]),
            allow_performance_driven_termination=bool(
                payload.get("allow_performance_driven_termination", False)
            ),
            genuine_failure_reasons=tuple(str(v) for v in payload["genuine_failure_reasons"]),
        )
        _validate_digest(payload, result.policy_digest, label="TRAIN2 training-budget policy")
        return result


@dataclass(frozen=True, slots=True)
class LearningRateSchedulePolicy:
    """Identity of the deterministic progress-normalized TRAIN2 LR schedule.

    The exact multiplier function is available now so Stage-B/Stage-C evidence
    can authenticate schedule identity.  TRAIN2B owns actual optimizer stepping.
    """

    base_learning_rate: float = 1.0e-4
    warmup_end_fraction: float = 0.05
    adaptation_end_fraction: float = 0.80
    initial_multiplier: float = 0.10
    adaptation_end_multiplier: float = 0.10
    final_multiplier: float = 0.01
    update_driven: bool = True
    validation_can_mutate_schedule: bool = False
    native_adaptive_scheduler_enabled: bool = False
    serialization_schema: str = field(
        default=LEARNING_RATE_SCHEDULE_POLICY_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != LEARNING_RATE_SCHEDULE_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported TRAIN2 LR-schedule policy schema.")
        object.__setattr__(
            self,
            "base_learning_rate",
            _finite_positive(self.base_learning_rate, name="TRAIN2 base_learning_rate"),
        )
        for name in (
            "warmup_end_fraction",
            "adaptation_end_fraction",
            "initial_multiplier",
            "adaptation_end_multiplier",
            "final_multiplier",
        ):
            object.__setattr__(
                self,
                name,
                _finite_positive(getattr(self, name), name=f"TRAIN2 {name}"),
            )
        if not 0.0 < self.warmup_end_fraction < self.adaptation_end_fraction < 1.0:
            raise TrainingDataInputError(
                "TRAIN2 LR phase boundaries must satisfy 0 < warmup < adaptation < 1."
            )
        if self.initial_multiplier > 1.0:
            raise TrainingDataInputError("TRAIN2 initial LR multiplier may not exceed 1.")
        if not math.isclose(self.adaptation_end_multiplier, self.initial_multiplier, rel_tol=0.0, abs_tol=1e-15):
            # The v1 analytic schedule reaches the same low multiplier at the
            # adaptation/refinement boundary that warmup starts from.
            raise TrainingDataInputError(
                "TRAIN2 v1 requires adaptation_end_multiplier == initial_multiplier."
            )
        if self.final_multiplier >= self.adaptation_end_multiplier:
            raise TrainingDataInputError(
                "TRAIN2 final multiplier must be below the adaptation-end multiplier."
            )
        if not self.update_driven:
            raise TrainingDataInputError("TRAIN2 v1 LR schedule must advance per optimizer update.")
        if self.validation_can_mutate_schedule:
            raise TrainingDataInputError("TRAIN2 validation may not mutate the LR schedule.")
        if self.native_adaptive_scheduler_enabled:
            raise TrainingDataInputError(
                "TRAIN2 forbids a competing native/adaptive LR scheduler."
            )

    def multiplier(self, progress: float) -> float:
        """Return the exact v1 multiplier at normalized update progress ``p``."""

        p = float(progress)
        if not math.isfinite(p) or p < 0.0 or p > 1.0:
            raise TrainingDataInputError("TRAIN2 LR progress must lie in [0, 1].")
        w = float(self.warmup_end_fraction)
        a = float(self.adaptation_end_fraction)
        m0 = float(self.initial_multiplier)
        ma = float(self.adaptation_end_multiplier)
        mf = float(self.final_multiplier)
        if p < w:
            return m0 + (1.0 - m0) * (p / w)
        if p < a:
            q = (p - w) / (a - w)
            return ma + 0.5 * (1.0 - ma) * (1.0 + math.cos(math.pi * q))
        q = (p - a) / (1.0 - a)
        return mf + 0.5 * (ma - mf) * (1.0 + math.cos(math.pi * q))

    def learning_rate_for_update(self, update_index: int, planned_updates: int) -> float:
        if int(planned_updates) < 2:
            raise TrainingDataInputError("TRAIN2 requires at least two planned optimizer updates.")
        u = int(update_index)
        U = int(planned_updates)
        if u < 0 or u >= U:
            raise TrainingDataInputError("TRAIN2 update_index is outside the planned update budget.")
        return self.base_learning_rate * self.multiplier(u / (U - 1))

    def phase(self, progress: float) -> str:
        p = float(progress)
        if not math.isfinite(p) or p < 0.0 or p > 1.0:
            raise TrainingDataInputError("TRAIN2 LR progress must lie in [0, 1].")
        if p < self.warmup_end_fraction:
            return "warmup"
        if p < self.adaptation_end_fraction:
            return "adaptation"
        return "refinement"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "base_learning_rate": self.base_learning_rate,
            "warmup_end_fraction": self.warmup_end_fraction,
            "adaptation_end_fraction": self.adaptation_end_fraction,
            "initial_multiplier": self.initial_multiplier,
            "adaptation_end_multiplier": self.adaptation_end_multiplier,
            "final_multiplier": self.final_multiplier,
            "update_driven": True,
            "validation_can_mutate_schedule": False,
            "native_adaptive_scheduler_enabled": False,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LearningRateSchedulePolicy":
        if payload.get("schema") != LEARNING_RATE_SCHEDULE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 LR-schedule policy schema.")
        result = cls(
            base_learning_rate=float(payload["base_learning_rate"]),
            warmup_end_fraction=float(payload["warmup_end_fraction"]),
            adaptation_end_fraction=float(payload["adaptation_end_fraction"]),
            initial_multiplier=float(payload["initial_multiplier"]),
            adaptation_end_multiplier=float(payload["adaptation_end_multiplier"]),
            final_multiplier=float(payload["final_multiplier"]),
            update_driven=bool(payload["update_driven"]),
            validation_can_mutate_schedule=bool(payload["validation_can_mutate_schedule"]),
            native_adaptive_scheduler_enabled=bool(payload["native_adaptive_scheduler_enabled"]),
        )
        _validate_digest(payload, result.policy_digest, label="TRAIN2 LR-schedule policy")
        return result


@dataclass(frozen=True, slots=True)
class CheckpointAdmissibilityPolicy:
    """Hard target/replay qualification gates for TRAIN2/EVAL2 candidates.

    Replay degradation is a constraint only.  No replay weight, reward, score,
    or tie-break parameter exists in this schema.
    """

    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    replay_enabled: bool = True
    replay_degradation_budget_ev_per_angstrom: float | None = (
        TRAIN2_DEFAULT_REPLAY_DEGRADATION_EV_PER_ANGSTROM
    )
    replay_label_requirement: str = "true_dft"
    require_finite_metrics: bool = True
    required_physical_gates: tuple[str, ...] = ()
    serialization_schema: str = field(
        default=CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported TRAIN2 checkpoint-admissibility policy schema.")
        object.__setattr__(
            self,
            "maximum_target_force_rmse_ev_per_angstrom",
            _finite_positive(
                self.maximum_target_force_rmse_ev_per_angstrom,
                name="TRAIN2 maximum_target_force_rmse_ev_per_angstrom",
            ),
        )
        if self.replay_enabled:
            if self.replay_degradation_budget_ev_per_angstrom is None:
                raise TrainingDataInputError(
                    "Replay-enabled TRAIN2 admissibility requires a degradation budget."
                )
            object.__setattr__(
                self,
                "replay_degradation_budget_ev_per_angstrom",
                _finite_positive(
                    self.replay_degradation_budget_ev_per_angstrom,
                    name="TRAIN2 replay_degradation_budget_ev_per_angstrom",
                ),
            )
            if str(self.replay_label_requirement).strip().lower() != "true_dft":
                raise TrainingDataInputError(
                    "TRAIN2 replay admissibility requires authenticated TRUE_DFT evidence."
                )
        elif self.replay_degradation_budget_ev_per_angstrom is not None:
            raise TrainingDataInputError(
                "Replay-disabled TRAIN2 admissibility cannot carry a replay degradation budget."
            )
        if not self.require_finite_metrics:
            raise TrainingDataInputError("TRAIN2 v1 requires finite admissibility metrics.")
        gates = tuple(str(v).strip() for v in self.required_physical_gates)
        if any(not v for v in gates) or len(set(gates)) != len(gates):
            raise TrainingDataInputError(
                "TRAIN2 required physical gates must be unique non-empty identifiers."
            )
        object.__setattr__(self, "required_physical_gates", gates)
        object.__setattr__(self, "replay_label_requirement", str(self.replay_label_requirement).strip().lower())

    def replay_absolute_ceiling_ev_per_angstrom(self, foundation_rmse: float) -> float | None:
        if not self.replay_enabled:
            return None
        baseline = _finite_positive(
            foundation_rmse,
            name="TRAIN2 foundation replay RMSE",
            allow_zero=True,
        )
        assert self.replay_degradation_budget_ev_per_angstrom is not None
        return baseline + self.replay_degradation_budget_ev_per_angstrom

    def failure_reasons(
        self,
        *,
        target_force_rmse_ev_per_angstrom: float,
        replay_degradation_ev_per_angstrom: float | None,
        replay_label_mode: str | None = None,
        physical_gate_results: Mapping[str, bool] | None = None,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        target = float(target_force_rmse_ev_per_angstrom)
        if not math.isfinite(target) or target < 0.0:
            reasons.append("target_metric_nonfinite")
        elif target > self.maximum_target_force_rmse_ev_per_angstrom:
            reasons.append("target_threshold_exceeded")
        if self.replay_enabled:
            if replay_label_mode is None or str(replay_label_mode).strip().lower() != self.replay_label_requirement:
                reasons.append("replay_true_dft_evidence_missing")
            if replay_degradation_ev_per_angstrom is None:
                reasons.append("replay_degradation_missing")
            else:
                replay = float(replay_degradation_ev_per_angstrom)
                if not math.isfinite(replay):
                    reasons.append("replay_metric_nonfinite")
                elif replay > float(self.replay_degradation_budget_ev_per_angstrom):
                    reasons.append("replay_retention_ceiling_exceeded")
        observed = {} if physical_gate_results is None else {
            str(key): bool(value) for key, value in physical_gate_results.items()
        }
        for gate in self.required_physical_gates:
            if observed.get(gate) is not True:
                reasons.append(f"physical_gate_failed:{gate}")
        return tuple(reasons)

    def candidate_admissible(self, **kwargs: Any) -> bool:
        return not self.failure_reasons(**kwargs)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "replay_enabled": self.replay_enabled,
            "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
            "replay_label_requirement": self.replay_label_requirement,
            "require_finite_metrics": self.require_finite_metrics,
            "required_physical_gates": list(self.required_physical_gates),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointAdmissibilityPolicy":
        if payload.get("schema") != CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported TRAIN2 checkpoint-admissibility policy schema."
            )
        result = cls(
            maximum_target_force_rmse_ev_per_angstrom=float(
                payload["maximum_target_force_rmse_ev_per_angstrom"]
            ),
            replay_enabled=bool(payload["replay_enabled"]),
            replay_degradation_budget_ev_per_angstrom=(
                None
                if payload.get("replay_degradation_budget_ev_per_angstrom") is None
                else float(payload["replay_degradation_budget_ev_per_angstrom"])
            ),
            replay_label_requirement=str(payload["replay_label_requirement"]),
            require_finite_metrics=bool(payload["require_finite_metrics"]),
            required_physical_gates=tuple(str(v) for v in payload.get("required_physical_gates", ())),
        )
        _validate_digest(payload, result.policy_digest, label="TRAIN2 checkpoint-admissibility policy")
        return result


@dataclass(frozen=True, slots=True)
class CheckpointSelectionPolicy:
    """Target-only TRAIN2/EVAL2 ordering policy.

    This schema intentionally has no replay metric, replay weight, replay margin,
    or replay tie-break.  Admissibility is evaluated first by the separate
    :class:`CheckpointAdmissibilityPolicy`.
    """

    primary_target_metric: str = "target_force_rmse_ev_per_angstrom"
    primary_direction: str = "minimize"
    initial_full_evaluation_candidates: int = 5
    refinement_reserved_candidates: int = 2
    practical_equivalence_ev_per_angstrom: float = TRAIN2_DEFAULT_PRACTICAL_EQUIVALENCE_EV_PER_ANGSTROM
    secondary_target_metrics: tuple[str, ...] = (
        "worst_stratum_force_rmse_ev_per_angstrom",
        "species_macro_force_rmse_ev_per_angstrom",
        "force_error_p95_ev_per_angstrom",
        "force_error_p99_ev_per_angstrom",
    )
    prefer_later_lower_lr_when_equivalent: bool = True
    bootstrap_replicates: int = TRAIN2_DEFAULT_BOOTSTRAP_REPLICATES
    bootstrap_confidence: float = TRAIN2_DEFAULT_BOOTSTRAP_CONFIDENCE
    bootstrap_min_independent_blocks: int = TRAIN2_DEFAULT_BOOTSTRAP_MIN_BLOCKS
    exact_tie_break: str = "stable_candidate_identity"
    serialization_schema: str = field(
        default=CHECKPOINT_SELECTION_POLICY_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != CHECKPOINT_SELECTION_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported TRAIN2 checkpoint-selection policy schema.")
        if not str(self.primary_target_metric).strip():
            raise TrainingDataInputError("TRAIN2 primary target metric must be non-empty.")
        if self.primary_direction != "minimize":
            raise TrainingDataInputError("TRAIN2 v1 supports target-metric minimization only.")
        if int(self.initial_full_evaluation_candidates) <= 0:
            raise TrainingDataInputError("TRAIN2 initial shortlist size must be positive.")
        if not 0 <= int(self.refinement_reserved_candidates) <= int(self.initial_full_evaluation_candidates):
            raise TrainingDataInputError(
                "TRAIN2 refinement reservation must lie within the shortlist size."
            )
        object.__setattr__(
            self,
            "practical_equivalence_ev_per_angstrom",
            _finite_positive(
                self.practical_equivalence_ev_per_angstrom,
                name="TRAIN2 practical equivalence",
                allow_zero=True,
            ),
        )
        metrics = tuple(str(v).strip() for v in self.secondary_target_metrics)
        if any(not v for v in metrics) or len(set(metrics)) != len(metrics):
            raise TrainingDataInputError(
                "TRAIN2 secondary target metrics must be unique non-empty identifiers."
            )
        if any("replay" in v.lower() for v in (self.primary_target_metric, *metrics)):
            raise TrainingDataInputError(
                "TRAIN2 checkpoint-selection metrics may not contain replay observables."
            )
        object.__setattr__(self, "secondary_target_metrics", metrics)
        if int(self.bootstrap_replicates) <= 0:
            raise TrainingDataInputError("TRAIN2 bootstrap_replicates must be positive.")
        if not 0.0 < float(self.bootstrap_confidence) < 1.0:
            raise TrainingDataInputError("TRAIN2 bootstrap_confidence must lie strictly in (0,1).")
        if int(self.bootstrap_min_independent_blocks) < 2:
            raise TrainingDataInputError(
                "TRAIN2 bootstrap_min_independent_blocks must be at least two."
            )
        if self.exact_tie_break != "stable_candidate_identity":
            raise TrainingDataInputError(
                "TRAIN2 v1 exact ties must resolve by stable candidate identity, never replay."
            )

    def practically_equivalent(self, first: float, second: float) -> bool:
        a, b = float(first), float(second)
        if not math.isfinite(a) or not math.isfinite(b):
            return False
        return abs(a - b) <= self.practical_equivalence_ev_per_angstrom

    def target_rank_key(
        self,
        *,
        primary_value: float,
        secondary_values: Sequence[float | None] = (),
        in_refinement_phase: bool = False,
        checkpoint_index: int = 0,
        stable_candidate_identity: str,
    ) -> tuple[Any, ...]:
        """Deterministic target-only ordering key.

        Replay evidence is intentionally not accepted as an argument.  EVAL2
        will add uncertainty-aware pairwise equivalence before applying this
        deterministic fallback ordering.
        """

        primary = float(primary_value)
        if not math.isfinite(primary):
            raise TrainingDataInputError("TRAIN2 target ranking requires a finite primary metric.")
        values: list[float] = []
        for value in secondary_values:
            values.append(math.inf if value is None else float(value))
        maturity = 0
        checkpoint = 0
        if self.prefer_later_lower_lr_when_equivalent:
            maturity = 0 if bool(in_refinement_phase) else 1
            checkpoint = -int(checkpoint_index)
        return (
            primary,
            *values,
            maturity,
            checkpoint,
            str(stable_candidate_identity),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "primary_target_metric": self.primary_target_metric,
            "primary_direction": self.primary_direction,
            "initial_full_evaluation_candidates": int(self.initial_full_evaluation_candidates),
            "refinement_reserved_candidates": int(self.refinement_reserved_candidates),
            "practical_equivalence_ev_per_angstrom": self.practical_equivalence_ev_per_angstrom,
            "secondary_target_metrics": list(self.secondary_target_metrics),
            "prefer_later_lower_lr_when_equivalent": self.prefer_later_lower_lr_when_equivalent,
            "bootstrap_replicates": int(self.bootstrap_replicates),
            "bootstrap_confidence": float(self.bootstrap_confidence),
            "bootstrap_min_independent_blocks": int(self.bootstrap_min_independent_blocks),
            "exact_tie_break": self.exact_tie_break,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointSelectionPolicy":
        if payload.get("schema") != CHECKPOINT_SELECTION_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported TRAIN2 checkpoint-selection policy schema."
            )
        result = cls(
            primary_target_metric=str(payload["primary_target_metric"]),
            primary_direction=str(payload["primary_direction"]),
            initial_full_evaluation_candidates=int(payload["initial_full_evaluation_candidates"]),
            refinement_reserved_candidates=int(payload["refinement_reserved_candidates"]),
            practical_equivalence_ev_per_angstrom=float(
                payload["practical_equivalence_ev_per_angstrom"]
            ),
            secondary_target_metrics=tuple(str(v) for v in payload["secondary_target_metrics"]),
            prefer_later_lower_lr_when_equivalent=bool(
                payload["prefer_later_lower_lr_when_equivalent"]
            ),
            bootstrap_replicates=int(payload["bootstrap_replicates"]),
            bootstrap_confidence=float(payload["bootstrap_confidence"]),
            bootstrap_min_independent_blocks=int(payload["bootstrap_min_independent_blocks"]),
            exact_tie_break=str(payload["exact_tie_break"]),
        )
        _validate_digest(payload, result.policy_digest, label="TRAIN2 checkpoint-selection policy")
        return result


def validate_train2_policy_set(
    *,
    budget: TrainingBudgetPolicy | None,
    learning_rate: LearningRateSchedulePolicy | None,
    admissibility: CheckpointAdmissibilityPolicy | None,
    selection: CheckpointSelectionPolicy | None,
) -> bool:
    """Require the four TRAIN2/EVAL2 policy authorities atomically.

    Returns ``True`` when the complete set is present and ``False`` when all are
    absent.  Partial sets fail closed.
    """

    values = (budget, learning_rate, admissibility, selection)
    present = tuple(value is not None for value in values)
    if any(present) and not all(present):
        raise TrainingDataInputError(
            "TRAIN2 policy authority requires budget, LR, admissibility, and selection policies together."
        )
    return all(present)
