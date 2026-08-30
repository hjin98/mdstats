"""Post-selection method and role-specific policy identities.

Three identities live here, and the split between them is the whole point.

``PostSelectionMethodIdentity`` is the scientific *method*: the thing
cross-validation validates and the thing final production must therefore
execute.  ``CvValidationPolicyIdentity`` and ``FinalProductionPolicyIdentity``
are the two role-specific *policies* layered on top of it - how the method is
cross-validated, and how it is finally produced.

All three are pure functions of resolved configuration and stable policy
definitions.  None of them may contain a fold membership, a fitted preparation
product, a checkpoint, an evaluation result, an M3 membership, or any other
realized descendant: a policy authorizes work, so it must be computable before
that work exists.  Plans bind the exact scientific lineage instead, and evidence
binds plans - a strictly downward dependency with no cycle.

Because of that split, the invalidation consequences follow the parent DAG
directly:

- changing only ``[training].max_num_epochs`` moves the production policy alone;
- changing only fold count/seed/CV budget moves the CV policy alone;
- changing a shared method field moves both, and stale CV can no longer
  authorize final production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import PostSelectionError

POST_SELECTION_METHOD_IDENTITY_SCHEMA = "mdstats.post-selection-method-identity.v1"
CV_VALIDATION_POLICY_IDENTITY_SCHEMA = "mdstats.post-selection-cv-policy-identity.v1"
FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA = (
    "mdstats.post-selection-final-production-policy-identity.v1"
)

#: Stable identity of the fold-construction algorithm owned by this package.
CV_FOLD_CONSTRUCTION_ALGORITHM = "mdstats.post-selection-cv-folds.2026-08.v1"

#: The only current CV aggregation rule; every required fold and every required
#: seed/variant must pass.  Named so a future governing revision has somewhere
#: to change it explicitly rather than by accident.
CV_AGGREGATION_ALL_REQUIRED = "all_required_folds_and_variants"

#: Cross-fold/cross-seed dispersion and replay summaries are recorded but never
#: gate acceptance.
CV_DISPERSION_DIAGNOSTIC_ONLY = "diagnostic_only"

#: Established default cross-validation training extent.  It is deliberately its
#: own value: aliasing it to ``[training].max_num_epochs`` would make a
#: production-only horizon edit invalidate accepted CV evidence.
DEFAULT_CV_MAX_NUM_EPOCHS = 30


def _table(config: Mapping[str, Any], *path: str) -> Mapping[str, Any]:
    current: Any = config
    for name in path:
        value = current.get(name, {}) if isinstance(current, Mapping) else None
        if value is None:
            value = {}
        if not isinstance(value, Mapping):
            raise TrainingDataInputError(
                "[" + ".".join(path) + "] must be a configuration table."
            )
        current = value
    return current


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingDataInputError(f"{name} must be an integer.")
    result = int(value)
    if result != value or result <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return result


def _seed_tuple(value: Any, *, name: str) -> tuple[int, ...]:
    if value is None:
        raise TrainingDataInputError(f"{name} must be a non-empty list of integers.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value]
    if not isinstance(value, (tuple, list)):
        raise TrainingDataInputError(f"{name} must be a list of integers.")
    seeds = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise TrainingDataInputError(f"{name} entries must be integers.")
        seed = int(item)
        if seed != item or seed < 0:
            raise TrainingDataInputError(f"{name} entries must be nonnegative integers.")
        seeds.append(seed)
    if not seeds or len(set(seeds)) != len(seeds):
        raise TrainingDataInputError(f"{name} must be non-empty and unique.")
    return tuple(sorted(seeds))


# ---------------------------------------------------------------------------
# Shared scientific method
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionMethodIdentity:
    """The training method shared by cross-validation and final production.

    Changing any field here means cross-validation validated a scientifically
    different method, so both CV and final-production descendants are stale.
    Nothing role-specific belongs here: not the CV folds, not the CV budget, not
    the production horizon, not M3, and not any fitted product.
    """

    method_recipe_version: str
    training_mode: str
    common_training_policy_digest: str
    learning_rate_schedule_policy_digest: str
    checkpoint_admissibility_policy_digest: str
    checkpoint_selection_policy_digest: str
    shared_optimizer_settings_digest: str
    replay_exposure_policy_digest: str
    extxyz_policy_digest: str
    checkpoint_interval_epochs: int
    default_dtype: str
    device: str
    acceleration_backend: str

    def __post_init__(self) -> None:
        for name in (
            "common_training_policy_digest",
            "learning_rate_schedule_policy_digest",
            "checkpoint_admissibility_policy_digest",
            "checkpoint_selection_policy_digest",
            "shared_optimizer_settings_digest",
            "replay_exposure_policy_digest",
            "extxyz_policy_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in (
            "method_recipe_version",
            "training_mode",
            "default_dtype",
            "device",
            "acceleration_backend",
        ):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"{name} must be non-empty.")
            object.__setattr__(self, name, value)
        object.__setattr__(
            self,
            "checkpoint_interval_epochs",
            _positive_int(
                self.checkpoint_interval_epochs, name="checkpoint_interval_epochs"
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_METHOD_IDENTITY_SCHEMA,
            "method_recipe_version": self.method_recipe_version,
            "training_mode": self.training_mode,
            "common_training_policy_digest": self.common_training_policy_digest,
            "learning_rate_schedule_policy_digest": (
                self.learning_rate_schedule_policy_digest
            ),
            "checkpoint_admissibility_policy_digest": (
                self.checkpoint_admissibility_policy_digest
            ),
            "checkpoint_selection_policy_digest": (
                self.checkpoint_selection_policy_digest
            ),
            "shared_optimizer_settings_digest": self.shared_optimizer_settings_digest,
            "replay_exposure_policy_digest": self.replay_exposure_policy_digest,
            "extxyz_policy_digest": self.extxyz_policy_digest,
            "checkpoint_interval_epochs": self.checkpoint_interval_epochs,
            "default_dtype": self.default_dtype,
            "device": self.device,
            "acceleration_backend": self.acceleration_backend,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionMethodIdentity":
        if payload.get("schema") != POST_SELECTION_METHOD_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection method-identity schema."
            )
        result = cls(
            method_recipe_version=str(payload["method_recipe_version"]),
            training_mode=str(payload["training_mode"]),
            common_training_policy_digest=str(payload["common_training_policy_digest"]),
            learning_rate_schedule_policy_digest=str(
                payload["learning_rate_schedule_policy_digest"]
            ),
            checkpoint_admissibility_policy_digest=str(
                payload["checkpoint_admissibility_policy_digest"]
            ),
            checkpoint_selection_policy_digest=str(
                payload["checkpoint_selection_policy_digest"]
            ),
            shared_optimizer_settings_digest=str(
                payload["shared_optimizer_settings_digest"]
            ),
            replay_exposure_policy_digest=str(payload["replay_exposure_policy_digest"]),
            extxyz_policy_digest=str(payload["extxyz_policy_digest"]),
            checkpoint_interval_epochs=int(payload["checkpoint_interval_epochs"]),
            default_dtype=str(payload["default_dtype"]),
            device=str(payload["device"]),
            acceleration_backend=str(payload["acceleration_backend"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection method-identity digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# CV-only validation policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CvValidationPolicyIdentity:
    """How the shared method is cross-validated - configuration only.

    The fold *count*, *seed*, and *construction algorithm* live here; the fold
    memberships they produce do not.  Membership is a deterministic descendant
    of this policy plus the current selected data and the current P1 relation
    authority, so it belongs to the CV plan.
    """

    fold_count: int
    partition_seed: int
    seed_mode: str
    fold_construction_algorithm: str
    checkpoint_monitor_components_per_fold: int
    purge_components_between_roles: int
    cv_max_num_epochs: int
    acceptance_metric: str
    acceptance_maximum: float
    aggregation_rule: str
    dispersion_policy: str
    required_cv_seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        if isinstance(self.fold_count, bool) or not isinstance(
            self.fold_count, (int, float)
        ):
            raise TrainingDataInputError("fold_count must be an integer.")
        folds = int(self.fold_count)
        if folds != self.fold_count or folds < 2:
            raise PostSelectionError(
                "Post-selection cross-validation requires at least two folds "
                f"(configured K={folds}). K=0 and K=1 are not a reduced CV: they are "
                "no CV, and no current production run may be authorized without "
                "actual methodological cross-validation."
            )
        object.__setattr__(self, "fold_count", folds)
        seed = int(self.partition_seed)
        if seed < 0:
            raise TrainingDataInputError("partition_seed must be nonnegative.")
        object.__setattr__(self, "partition_seed", seed)
        for name in (
            "seed_mode",
            "fold_construction_algorithm",
            "acceptance_metric",
            "aggregation_rule",
            "dispersion_policy",
        ):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"{name} must be non-empty.")
            object.__setattr__(self, name, value)
        if self.aggregation_rule != CV_AGGREGATION_ALL_REQUIRED:
            raise PostSelectionError(
                "The current CV aggregation rule is "
                f"{CV_AGGREGATION_ALL_REQUIRED!r}: every required fold of every "
                "required seed/variant must pass. Mean, majority, best-seed, and "
                "partial-fold aggregations are not representable."
            )
        if self.dispersion_policy != CV_DISPERSION_DIAGNOSTIC_ONLY:
            raise PostSelectionError(
                "Cross-fold dispersion is diagnostic-only unless a governing "
                "scientific revision explicitly promotes it to a gate."
            )
        object.__setattr__(
            self,
            "checkpoint_monitor_components_per_fold",
            _positive_int(
                self.checkpoint_monitor_components_per_fold,
                name="checkpoint_monitor_components_per_fold",
            ),
        )
        purge = int(self.purge_components_between_roles)
        if purge < 0:
            raise TrainingDataInputError(
                "purge_components_between_roles must be nonnegative."
            )
        object.__setattr__(self, "purge_components_between_roles", purge)
        object.__setattr__(
            self,
            "cv_max_num_epochs",
            _positive_int(self.cv_max_num_epochs, name="cv_max_num_epochs"),
        )
        threshold = float(self.acceptance_maximum)
        if not (threshold > 0.0) or threshold != threshold or threshold == float("inf"):
            raise TrainingDataInputError(
                "acceptance_maximum must be a finite positive threshold."
            )
        object.__setattr__(self, "acceptance_maximum", threshold)
        object.__setattr__(
            self,
            "required_cv_seeds",
            _seed_tuple(self.required_cv_seeds, name="required_cv_seeds"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CV_VALIDATION_POLICY_IDENTITY_SCHEMA,
            "fold_count": self.fold_count,
            "partition_seed": self.partition_seed,
            "seed_mode": self.seed_mode,
            "fold_construction_algorithm": self.fold_construction_algorithm,
            "checkpoint_monitor_components_per_fold": (
                self.checkpoint_monitor_components_per_fold
            ),
            "purge_components_between_roles": self.purge_components_between_roles,
            "cv_max_num_epochs": self.cv_max_num_epochs,
            "acceptance_metric": self.acceptance_metric,
            "acceptance_maximum": self.acceptance_maximum,
            "aggregation_rule": self.aggregation_rule,
            "dispersion_policy": self.dispersion_policy,
            "required_cv_seeds": list(self.required_cv_seeds),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CvValidationPolicyIdentity":
        if payload.get("schema") != CV_VALIDATION_POLICY_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported CV validation-policy identity schema."
            )
        result = cls(
            fold_count=int(payload["fold_count"]),
            partition_seed=int(payload["partition_seed"]),
            seed_mode=str(payload["seed_mode"]),
            fold_construction_algorithm=str(payload["fold_construction_algorithm"]),
            checkpoint_monitor_components_per_fold=int(
                payload["checkpoint_monitor_components_per_fold"]
            ),
            purge_components_between_roles=int(
                payload["purge_components_between_roles"]
            ),
            cv_max_num_epochs=int(payload["cv_max_num_epochs"]),
            acceptance_metric=str(payload["acceptance_metric"]),
            acceptance_maximum=float(payload["acceptance_maximum"]),
            aggregation_rule=str(payload["aggregation_rule"]),
            dispersion_policy=str(payload["dispersion_policy"]),
            required_cv_seeds=tuple(int(v) for v in payload["required_cv_seeds"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "CV validation-policy identity digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# Production-only policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinalProductionPolicyIdentity:
    """How the CV-accepted method is finally produced - configuration only.

    ``[training].max_num_epochs`` is the production horizon and lives only here.
    It is not the CV budget and is not target-size ``n3``; changing it must
    leave the P4 selection and the accepted CV evidence untouched.

    M3 is deliberately absent.  It is inherited P2/P4 development evidence that
    binds the final *plan*, not a production knob an operator may set.
    """

    production_max_num_epochs: int
    production_seeds: tuple[int, ...]
    committee_policy: str
    allow_performance_driven_termination: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "production_max_num_epochs",
            _positive_int(
                self.production_max_num_epochs, name="production_max_num_epochs"
            ),
        )
        object.__setattr__(
            self,
            "production_seeds",
            _seed_tuple(self.production_seeds, name="production_seeds"),
        )
        committee = str(self.committee_policy).strip()
        if committee not in {"all_qualified_final_seeds", "single_best_final_seed"}:
            raise TrainingDataInputError(
                "Unsupported final-production committee policy."
            )
        object.__setattr__(self, "committee_policy", committee)
        object.__setattr__(
            self,
            "allow_performance_driven_termination",
            bool(self.allow_performance_driven_termination),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA,
            "production_max_num_epochs": self.production_max_num_epochs,
            "production_seeds": list(self.production_seeds),
            "committee_policy": self.committee_policy,
            "allow_performance_driven_termination": (
                self.allow_performance_driven_termination
            ),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalProductionPolicyIdentity":
        if payload.get("schema") != FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-production policy identity schema."
            )
        result = cls(
            production_max_num_epochs=int(payload["production_max_num_epochs"]),
            production_seeds=tuple(int(v) for v in payload["production_seeds"]),
            committee_policy=str(payload["committee_policy"]),
            allow_performance_driven_termination=bool(
                payload["allow_performance_driven_termination"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-production policy identity digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# Configuration resolution
# ---------------------------------------------------------------------------


def resolve_shared_optimizer_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    """The optimizer settings CV and final production must share.

    The optimizer *seed*, the epoch *budget*, and worker counts are excluded on
    purpose: seeds are per-run identity, budgets are role-specific policy, and
    worker counts are a resource choice with no scientific meaning.
    """

    training = _table(config, "training")
    return {
        "optimizer_family": str(training.get("optimizer", "adam")).strip() or "adam",
        "learning_rate": float(training.get("learning_rate", 1.0e-4)),
        "batch_size": int(training.get("batch_size", 2)),
        "valid_batch_size": int(training.get("valid_batch_size", 2)),
        "eval_interval": int(training.get("eval_interval", 1)),
        "ema": bool(training.get("ema", True)),
        "ema_decay": float(training.get("ema_decay", 0.99)),
        "amsgrad": bool(training.get("amsgrad", True)),
        "weight_decay": float(training.get("weight_decay", 5.0e-7)),
        "clip_grad": float(training.get("clip_grad", 10.0)),
    }


@dataclass(frozen=True, slots=True)
class PostSelectionMethodPolicies:
    """The accepted policy objects the shared method identity summarizes.

    Both the identity and the execution owners resolve the method through this
    one function, so the policy a run actually executes and the digest that
    claims to describe it cannot drift apart.
    """

    common_training: Any
    learning_rate_schedule: Any
    checkpoint_admissibility: Any
    checkpoint_selection: Any
    extxyz: Any
    training_mode: str
    acceleration_backend: str
    checkpoint_interval_epochs: int
    device: str


def resolve_post_selection_method_policies(
    config: Mapping[str, Any],
) -> PostSelectionMethodPolicies:
    """Resolve the shared method's policy objects from configuration alone.

    Replay admissibility follows the campaign's configured replay corpus: a
    campaign with no TRUE_DFT replay source does not acquire a replay
    constraint it cannot satisfy, and one that configures replay cannot lose it.
    Either way replay only ever gates admissibility - the selection policy below
    is target-only.
    """

    from .mace_export import MaceExtxyzPolicy
    from .target_size_execution import TargetSizeCommonTrainingPolicy
    from .train2_policy import (
        CheckpointAdmissibilityPolicy,
        CheckpointSelectionPolicy,
        LearningRateSchedulePolicy,
    )

    training = _table(config, "training")
    acceptance = _table(config, "acceptance")
    acceleration = _table(config, "acceleration")
    paths = _table(config, "paths")

    modes = training.get("modes")
    if isinstance(modes, (tuple, list)) and modes:
        if len(modes) != 1:
            raise PostSelectionError(
                "Post-selection work requires exactly one enabled training method."
            )
        training_mode = str(modes[0])
    else:
        training_mode = str(training.get("mode", "multihead_replay"))

    replay_enabled = bool(str(paths.get("replay_true_labels", "")).strip())
    replay_budget_mev = float(
        acceptance.get("allowed_replay_degradation_mev_per_a", 30.0)
    )
    source_backend = str(acceleration.get("backend", "e3nn")).strip().lower()
    return PostSelectionMethodPolicies(
        common_training=TargetSizeCommonTrainingPolicy(),
        learning_rate_schedule=LearningRateSchedulePolicy(
            base_learning_rate=float(training.get("learning_rate", 1.0e-4)),
            warmup_end_fraction=float(
                training.get("train2_warmup_end_fraction", 0.05)
            ),
            adaptation_end_fraction=float(
                training.get("train2_adaptation_end_fraction", 0.80)
            ),
            initial_multiplier=float(
                training.get("train2_initial_lr_multiplier", 0.10)
            ),
            adaptation_end_multiplier=float(
                training.get("train2_refinement_start_lr_multiplier", 0.10)
            ),
            final_multiplier=float(training.get("train2_final_lr_multiplier", 0.01)),
            update_driven=True,
            validation_can_mutate_schedule=False,
            native_adaptive_scheduler_enabled=False,
        ),
        checkpoint_admissibility=CheckpointAdmissibilityPolicy(
            maximum_target_force_rmse_ev_per_angstrom=float(
                acceptance.get("maximum_target_force_rmse_ev_per_angstrom", 0.030)
            ),
            replay_enabled=replay_enabled,
            replay_degradation_budget_ev_per_angstrom=(
                replay_budget_mev / 1000.0 if replay_enabled else None
            ),
            replay_label_requirement="true_dft",
            required_physical_gates=(),
        ),
        checkpoint_selection=CheckpointSelectionPolicy(),
        extxyz=MaceExtxyzPolicy(),
        training_mode=training_mode,
        acceleration_backend=str(
            acceleration.get("training_backend", source_backend)
        )
        .strip()
        .lower(),
        checkpoint_interval_epochs=int(training.get("checkpoint_interval_epochs", 1)),
        device=str(training.get("device", "cuda")),
    )


def resolve_post_selection_method_identity(
    config: Mapping[str, Any],
    *,
    policies: PostSelectionMethodPolicies | None = None,
) -> PostSelectionMethodIdentity:
    """Summarize the resolved shared method policies into one digest.

    No argument may be a fitted product, a fold membership, or an evaluation
    result: the identity must be computable before any of those exist.
    """

    resolved = (
        resolve_post_selection_method_policies(config) if policies is None else policies
    )
    return PostSelectionMethodIdentity(
        method_recipe_version="mdstats.post-selection-method.2026-08.v1",
        training_mode=resolved.training_mode,
        common_training_policy_digest=resolved.common_training.content_digest,
        learning_rate_schedule_policy_digest=(
            resolved.learning_rate_schedule.policy_digest
        ),
        checkpoint_admissibility_policy_digest=(
            resolved.checkpoint_admissibility.policy_digest
        ),
        checkpoint_selection_policy_digest=resolved.checkpoint_selection.policy_digest,
        shared_optimizer_settings_digest=digest(
            resolve_shared_optimizer_settings(config)
        ),
        replay_exposure_policy_digest=(
            resolved.common_training.replay_exposure_policy_digest
        ),
        extxyz_policy_digest=resolved.extxyz.policy_digest,
        checkpoint_interval_epochs=resolved.checkpoint_interval_epochs,
        default_dtype=str(resolved.common_training.default_dtype),
        device=resolved.device,
        acceleration_backend=resolved.acceleration_backend,
    )


def resolve_cv_validation_policy_identity(
    config: Mapping[str, Any],
) -> CvValidationPolicyIdentity:
    """Resolve ``[post_selection.cv]`` into the CV-only policy identity.

    The CV training budget is resolved here and nowhere else.  It deliberately
    does not read ``[training].max_num_epochs``: a production horizon edit must
    not invalidate accepted cross-validation evidence.
    """

    cv = _table(config, "post_selection", "cv")
    for forbidden in ("max_num_epochs_from_training", "n3", "target_size"):
        if forbidden in cv:
            raise PostSelectionError(
                f"[post_selection.cv].{forbidden} is not a CV policy field. The CV "
                "budget is independent of both target-size n3 and the production "
                "horizon."
            )
    return CvValidationPolicyIdentity(
        fold_count=int(cv.get("fold_count", 5)),
        partition_seed=int(cv.get("partition_seed", 104729)),
        seed_mode=str(cv.get("seed_mode", "explicit")),
        fold_construction_algorithm=CV_FOLD_CONSTRUCTION_ALGORITHM,
        checkpoint_monitor_components_per_fold=int(
            cv.get("checkpoint_monitor_components_per_fold", 1)
        ),
        purge_components_between_roles=int(cv.get("purge_components_between_roles", 0)),
        cv_max_num_epochs=int(cv.get("max_num_epochs", DEFAULT_CV_MAX_NUM_EPOCHS)),
        acceptance_metric=str(
            cv.get("acceptance_metric", "target_force_rmse_ev_per_angstrom")
        ),
        acceptance_maximum=float(cv.get("acceptance_maximum", 0.030)),
        aggregation_rule=CV_AGGREGATION_ALL_REQUIRED,
        dispersion_policy=CV_DISPERSION_DIAGNOSTIC_ONLY,
        required_cv_seeds=cv.get("seeds", (0,)),
    )


def resolve_final_production_policy_identity(
    config: Mapping[str, Any],
) -> FinalProductionPolicyIdentity:
    """Resolve the production-only policy, including the configured horizon.

    ``[training].max_num_epochs`` is read exactly once, here.  Nothing derives
    it from target-size ``n3`` and nothing derives ``n3`` from it.
    """

    training = _table(config, "training")
    production = _table(config, "post_selection", "production")
    if "max_num_epochs" in production:
        raise PostSelectionError(
            "The final-production horizon is [training].max_num_epochs. "
            "[post_selection.production].max_num_epochs would create a second "
            "horizon authority."
        )
    return FinalProductionPolicyIdentity(
        production_max_num_epochs=int(training.get("max_num_epochs", 30)),
        production_seeds=production.get("seeds", training.get("seeds", (1,))),
        committee_policy=str(
            production.get("committee_policy", "all_qualified_final_seeds")
        ),
        allow_performance_driven_termination=bool(
            production.get("allow_performance_driven_termination", False)
        ),
    )


def cv_training_budget_policy(
    method: PostSelectionMethodIdentity, policy: CvValidationPolicyIdentity
) -> Any:
    """Materialize the CV TRAIN2 budget from the CV-only policy."""

    from .train2_policy import TrainingBudgetPolicy

    return TrainingBudgetPolicy(
        planned_epochs=policy.cv_max_num_epochs,
        checkpoint_interval_epochs=method.checkpoint_interval_epochs,
        allow_performance_driven_termination=False,
    )


def final_production_training_budget_policy(
    method: PostSelectionMethodIdentity, policy: FinalProductionPolicyIdentity
) -> Any:
    """Materialize the final-production TRAIN2 budget from the configured horizon."""

    from .train2_policy import TrainingBudgetPolicy

    return TrainingBudgetPolicy(
        planned_epochs=policy.production_max_num_epochs,
        checkpoint_interval_epochs=method.checkpoint_interval_epochs,
        allow_performance_driven_termination=(
            policy.allow_performance_driven_termination
        ),
    )


__all__ = [
    "CV_AGGREGATION_ALL_REQUIRED",
    "CV_DISPERSION_DIAGNOSTIC_ONLY",
    "CV_FOLD_CONSTRUCTION_ALGORITHM",
    "CV_VALIDATION_POLICY_IDENTITY_SCHEMA",
    "DEFAULT_CV_MAX_NUM_EPOCHS",
    "FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA",
    "POST_SELECTION_METHOD_IDENTITY_SCHEMA",
    "CvValidationPolicyIdentity",
    "FinalProductionPolicyIdentity",
    "PostSelectionMethodIdentity",
    "PostSelectionMethodPolicies",
    "cv_training_budget_policy",
    "final_production_training_budget_policy",
    "resolve_cv_validation_policy_identity",
    "resolve_final_production_policy_identity",
    "resolve_post_selection_method_identity",
    "resolve_post_selection_method_policies",
    "resolve_shared_optimizer_settings",
]
