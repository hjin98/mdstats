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
- changing only a role's checkpoint target-force ceiling moves that role's
  policy alone;
- changing a shared method field - including a shared checkpoint constraint
  such as the replay-degradation budget - moves both, and stale CV can no longer
  authorize final production.

A run is judged under exactly one role-effective checkpoint-admissibility
policy: the shared constraints bound by the method plus the target ceiling
bound by the run's role policy (``post_selection_checkpoint_admissibility``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    resolve_configured_path,
    validate_digest,
)
from .campaign_post_selection import PostSelectionError
from .training_settings import (
    resolve_binary_model_dtype,
    resolve_shared_optimizer_settings as _resolve_shared_optimizer_settings,
    shared_optimizer_settings_payload,
)
from .mace_compatibility import (
    FOUNDATION_ADAPTATION_TRAINING_MODES,
    MACE_EXECUTION_SEMANTICS_VERSION,
    MACE_FOUNDATION_ENERGY_WEIGHT,
    MACE_FOUNDATION_FORCES_WEIGHT,
    MACE_FOUNDATION_HUBER_DELTA,
    MACE_FOUNDATION_LOSS_FAMILY,
    MACE_FOUNDATION_STRESS_WEIGHT,
    MACE_REPLAY_FORCE_MH_FT_LR,
    MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
    POST_SELECTION_TRAINING_MODES,
)

# v2 replaced the whole P3 common-training-policy parent with mode-specific
# objective, preparation, and exposure identities.  v3 still bound the shared
# checkpoint constraints and the checkpoint-selection policy.  v4 is
# training-only: assessment thresholds and representative ordering cannot
# change a fixed-budget trajectory, so they are not method parents.
POST_SELECTION_METHOD_IDENTITY_SCHEMA = "mdstats.post-selection-method-identity.v4"
#: The superseded policy-overbound generation.  Readable only by the one-time
#: historical training-equivalence derivation; never current authority.
POST_SELECTION_METHOD_IDENTITY_SCHEMA_V3 = "mdstats.post-selection-method-identity.v3"
#: The two v3 fields that were assessment-only and are excluded, and only they,
#: by the historical training-equivalence projection.
RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS = (
    "shared_checkpoint_constraints_digest",
    "checkpoint_selection_policy_digest",
)
POST_SELECTION_REPLAY_HARD_DECISION_SCHEMA = (
    "mdstats.post-selection-replay-hard-decision.v1"
)
CV_ASSESSMENT_POSITION_POLICY_SCHEMA = (
    "mdstats.post-selection-cv-assessment-position-policy.v1"
)
FINAL_SEED_ASSESSMENT_POLICY_SCHEMA = (
    "mdstats.post-selection-final-seed-assessment-policy.v1"
)
FINAL_PUBLICATION_POLICY_SCHEMA = "mdstats.post-selection-final-publication-policy.v1"

#: D2.DEF.059A: within-run representative = lexicographic minimum over hard-
#: admissible checkpoints of ``(target RMSE, epoch, checkpoint SHA-256)``.
P5_WITHIN_RUN_SELECTION_IDENTITY = (
    "mdstats.p5-within-run-representative.d2-def-059a."
    "target-rmse-then-epoch-then-sha256.v1"
)
#: D2.DEF.059B: ``single_best_final_seed`` = lexicographic minimum over frozen
#: admissible seed representatives of ``(target RMSE, optimizer seed, SHA-256)``.
P5_CROSS_SEED_SELECTION_IDENTITY = (
    "mdstats.p5-single-best-final-seed.d2-def-059b."
    "target-rmse-then-seed-then-sha256.v1"
)

#: The narrow campaign-v2 migration discriminator under ``[acceptance]``.
P5_CHECKPOINT_POLICY_GENERATION_FIELD = "post_selection_checkpoint_policy_generation"
P5_CHECKPOINT_POLICY_GENERATION = "p5_target_replay_v2"
REPLAY_WARNING_FIELD = "replay_degradation_warning_mev_per_a"
REPLAY_HARD_LIMIT_FIELD = "replay_degradation_hard_limit_mev_per_a"
#: Superseded one-number replay fields (generated default 30 meV/angstrom).
LEGACY_REPLAY_FIELDS = (
    ("acceptance", "allowed_replay_degradation_mev_per_a"),
    ("training", "replay_degradation_budget_mev_per_a"),
)
LEGACY_GENERATED_REPLAY_MEV_PER_A = 30.0
DEFAULT_REPLAY_WARNING_MEV_PER_A = 50.0
DEFAULT_REPLAY_HARD_LIMIT_MEV_PER_A = 100.0
FOUNDATION_ADAPTATION_OBJECTIVE_POLICY_SCHEMA = (
    "mdstats.post-selection-foundation-objective-policy.v1"
)
POST_SELECTION_PREPARATION_POLICY_SCHEMA = (
    "mdstats.post-selection-preparation-policy.v1"
)

#: Accepted exposure semantics bound into method identity.  Foundation P5 runs
#: the qualified single-process shuffled loader with ``drop_last=True`` over the
#: native replay/``pt_head``-first combined corpus (target-only for naive
#: fine-tuning).  P5 scratch keeps its separately accepted native exposure.
POST_SELECTION_FOUNDATION_EXPOSURE_POLICY = (
    "mdstats.p5-foundation-exposure.single-process-shuffled-drop-last-replay-first.v1"
)
POST_SELECTION_SCRATCH_EXPOSURE_POLICY = "mdstats.p5-scratch-exposure.native.v1"

#: The accepted composition-level E0 transfer rule: every governed composition
#: vector is orthogonal to the unanchored null space of the authorized fit
#: count matrix.  No anchor is currently accepted.
POST_SELECTION_COMPOSITION_TRANSFER_POLICY = (
    "mdstats.p5-composition-transfer.unanchored-null-space-orthogonality.v1"
)

#: Configuration fields retired by the restored method.  They fail closed in
#: current configuration rather than being read and ignored.
RETIRED_POST_SELECTION_TRAINING_FIELDS = ("target_head_weight", "replay_head_weight")
# v2 retired the selected-only fold checkpoint-monitor budget.  v3 (and final
# production v2) own their role's checkpoint target-force ceiling.
CV_VALIDATION_POLICY_IDENTITY_SCHEMA = "mdstats.post-selection-cv-policy-identity.v3"
FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA = (
    "mdstats.post-selection-final-production-policy-identity.v2"
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

#: The one current default outer-fold count.  An explicit override must be K>=2.
DEFAULT_CV_FOLD_COUNT = 3

#: Foundation-CV checkpoint competence default ``tau_CV``.  It is deliberately
#: not the production ceiling and not ``acceptance_maximum``, whose units follow
#: the configured outer metric.
FOUNDATION_CV_CHECKPOINT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM = 0.075

#: Default foundation-CV held-out ``theta_CV`` under the default force metric.
FOUNDATION_CV_DEFAULT_ACCEPTANCE_MAXIMUM_EV_PER_ANGSTROM = 0.075

#: Foundation final-production checkpoint ceiling default ``tau_prod``.
FOUNDATION_PRODUCTION_DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM = 0.050

#: Historical generated foundation defaults that the no-marker migration treats
#: as generated-default ancestry (``0.045/0.045`` CV, ``0.030`` production).
LEGACY_GENERATED_FOUNDATION_CV_EV_PER_ANGSTROM = 0.045
LEGACY_GENERATED_FOUNDATION_PRODUCTION_EV_PER_ANGSTROM = 0.030

#: The accepted pre-amendment foundation-CV ``acceptance_maximum`` resolution a
#: non-default outer metric keeps: it is never migrated to the force-RMSE 0.075.
FOUNDATION_CV_NON_DEFAULT_METRIC_ACCEPTANCE_MAXIMUM = 0.045

#: Scratch target ceiling for both roles (separately accepted; unchanged).
DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM = 0.030

#: The default CV outer metric.  Only under this metric does
#: ``acceptance_maximum`` have target-force units.
CV_DEFAULT_ACCEPTANCE_METRIC = "target_force_rmse_ev_per_angstrom"

#: Retired CV-policy fields that fail closed in current configuration.
RETIRED_CV_POLICY_FIELDS = ("checkpoint_monitor_components_per_fold",)

#: The current P5 fine-tuning head namespace.  Foundation-checkpoint heads are
#: a separate identity owned by ``MaceFoundationSpec``; these names describe
#: the target and replay heads created by the post-selection run itself.
POST_SELECTION_TARGET_HEAD_NAME = "target_head"
POST_SELECTION_REPLAY_HEAD_NAME = "pt_head"

# The current method recipe is the method-level cutover token, shared by
# scratch, naive fine-tuning, and replay rather than maintained per mode.  v5 is
# the restored foundation method: native UniversalLoss, selected-head residual
# E0 with composition transfer, replay-first exposure, and a common monitor.
POST_SELECTION_METHOD_RECIPE_VERSION = "mdstats.post-selection-method.2026-09.v5"


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


def resolve_post_selection_device(config: Mapping[str, Any]) -> str:
    """Resolve the shared post-selection device from campaign configuration.

    This is intentionally the same configuration-only owner used by method
    policy resolution.  Late qualification currentness fences must resolve
    binding-bearing configuration from their supplied current configuration,
    not from the session's admission-frozen policy object.
    """

    return str(_table(config, "training").get("device", "cuda"))


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingDataInputError(f"{name} must be an integer.")
    result = int(value)
    if result != value or result <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return result


def _finite_positive_threshold(value: Any, *, name: str) -> float:
    # Booleans and strings are rejected before conversion, never coerced.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingDataInputError(f"{name} must be a finite positive threshold.")
    threshold = float(value)
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise TrainingDataInputError(f"{name} must be a finite positive threshold.")
    return threshold


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


def canonical_post_selection_head_names(
    *, target_head_name: Any = None, replay_head_name: Any = None
) -> tuple[str, str]:
    """Return the fixed P5 fine-tuning namespace or fail closed.

    P5 does not expose arbitrary fine-tuning head names.  Keeping this check in
    the identity owner lets runtime-plan and executable-configuration consumers
    validate the same invariant without inventing their own fallback aliases.
    """

    target = (
        POST_SELECTION_TARGET_HEAD_NAME
        if target_head_name is None or not str(target_head_name).strip()
        else str(target_head_name).strip()
    )
    replay = (
        POST_SELECTION_REPLAY_HEAD_NAME
        if replay_head_name is None or not str(replay_head_name).strip()
        else str(replay_head_name).strip()
    )
    if target != POST_SELECTION_TARGET_HEAD_NAME:
        raise TrainingDataInputError(
            "Current P5 supports only the canonical target fine-tuning head "
            f"{POST_SELECTION_TARGET_HEAD_NAME!r}; received {target!r}."
        )
    if replay != POST_SELECTION_REPLAY_HEAD_NAME:
        raise TrainingDataInputError(
            "Current P5 supports only the canonical replay fine-tuning head "
            f"{POST_SELECTION_REPLAY_HEAD_NAME!r}; received {replay!r}."
        )
    return POST_SELECTION_TARGET_HEAD_NAME, POST_SELECTION_REPLAY_HEAD_NAME


def resolve_post_selection_head_names(
    config: Mapping[str, Any],
) -> tuple[str, str]:
    """Resolve the P5 fine-tuning head namespace from campaign configuration."""

    training = _table(config, "training")
    # ``replay_head_name`` is accepted only as a validation surface for older
    # generated configurations.  It is not introduced as a new P5 option.
    return canonical_post_selection_head_names(
        target_head_name=training.get("selected_head_name"),
        replay_head_name=(
            training.get("replay_head_name")
            if "replay_head_name" in training
            else None
        ),
    )


def _replay_label_mode(value: Any, *, name: str) -> Any:
    from .replay import ReplayLabelMode

    raw = getattr(value, "value", value)
    try:
        mode = ReplayLabelMode(str(raw))
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            f"{name} must resolve to true_dft or foundation_pseudolabel."
        ) from exc
    if mode not in {
        ReplayLabelMode.TRUE_DFT,
        ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
    }:
        raise TrainingDataInputError(
            f"{name} must resolve to true_dft or foundation_pseudolabel."
        )
    return mode


def resolve_post_selection_replay_training_label_mode(
    config: Mapping[str, Any],
    *,
    single_replay: Any | None = None,
    has_legacy_replay: bool | None = None,
) -> Any | None:
    """Normalize the replay label semantic consumed by P5 training.

    The canonical single-source configuration is preferred when present.  For
    the historical split-file interface, the existing ``ReplayMode`` is the
    only interpretation authority: supported external pseudo/true modes map to
    their corresponding ``ReplayLabelMode`` and ambiguous modes fail closed.
    """

    from .replay import (
        ReplayLabelMode,
        ReplayMode,
        single_source_replay_config_from_campaign,
    )

    if single_replay is None:
        single_replay = single_source_replay_config_from_campaign(config)
    if single_replay is not None:
        return _replay_label_mode(
            single_replay.label_mode, name="single-source replay label_mode"
        )

    paths = _table(config, "paths")
    if has_legacy_replay is None:
        has_legacy_replay = any(
            str(paths.get(key, "")).strip()
            for key in ("replay_train", "replay_monitor", "replay_true_labels")
        )
    if not has_legacy_replay:
        return None

    replay = _table(config, "replay")
    raw_mode_value = replay.get("mode")
    if raw_mode_value in (None, ""):
        # The historical split-file interface once defaulted an omitted mode to
        # foundation pseudo-labels.  That omission is ambiguous for the
        # restored method, whose canonical default is TRUE_DFT, so it fails.
        raise PostSelectionError(
            "Legacy split-file replay requires an explicit [replay].mode "
            "(external_true_label or external_pseudolabel); an omitted mode has no "
            "unambiguous P5 training-label semantic. Prefer [paths].replay_set, "
            "whose omitted label_mode resolves to true_dft."
        )
    raw_mode = str(getattr(raw_mode_value, "value", raw_mode_value)).strip().lower()
    try:
        mode = ReplayMode(raw_mode)
    except ValueError as exc:
        supported = ", ".join(
            item.value
            for item in (
                ReplayMode.EXTERNAL_PSEUDOLABEL,
                ReplayMode.EXTERNAL_TRUE_LABEL,
            )
        )
        raise TrainingDataInputError(
            "Unsupported legacy [replay].mode for P5; choose one of: "
            f"{supported}. Other replay modes have no unambiguous P5 training "
            "label semantic."
        ) from exc
    if mode is ReplayMode.EXTERNAL_PSEUDOLABEL:
        return ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    if mode is ReplayMode.EXTERNAL_TRUE_LABEL:
        return ReplayLabelMode.TRUE_DFT
    raise PostSelectionError(
        "Legacy replay mode "
        f"{mode.value!r} has no unambiguous supported P5 training-label "
        "semantic; refusing to begin CV or final production."
    )


def _post_selection_replay_configuration_present(
    replay: Mapping[str, Any],
    *,
    single_replay: Any | None,
    has_replay_paths: bool,
) -> bool:
    """Report whether a campaign declares any P5 replay configuration.

    A source path is an enabled replay declaration.  An explicit replay table
    without a source is still configuration, however, and must not be silently
    ignored when the selected training mode is scratch or naive fine-tuning.
    ``mode = none`` by itself is the one explicit way to say that the replay
    table is disabled.
    """

    if single_replay is not None or has_replay_paths:
        return True
    if not replay:
        return False
    mode = getattr(replay.get("mode"), "value", replay.get("mode"))
    label_mode = getattr(
        replay.get("label_mode"), "value", replay.get("label_mode")
    )
    mode_token = "" if mode in (None, "") else str(mode).strip().lower()
    label_token = (
        "" if label_mode in (None, "") else str(label_mode).strip().lower()
    )
    if mode_token not in {"", "none"} or label_token not in {"", "none"}:
        return True
    return any(key not in {"mode", "label_mode"} for key in replay)


# ---------------------------------------------------------------------------
# Shared scientific method
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionMethodIdentity:
    """The training method shared by cross-validation and final production.

    Changing any field here means cross-validation validated a scientifically
    different method, so both CV and final-production descendants are stale.
    Nothing role-specific belongs here: not the CV folds, not the CV budget, not
    the production horizon, not a role's checkpoint target-force ceiling, not
    M3, and not any fitted product.  Nothing assessment-only belongs here
    either: replay warning/hard limits, role target ceilings, and the P5
    representative ordering cannot change a fixed-budget TRAIN2 trajectory.

    It binds only method-bearing P5 components.  In particular it does not bind
    the whole P3 ``TargetSizeCommonTrainingPolicy``: a P3-only objective,
    weighting, or harness edit leaves foundation P5 untouched, while the P5
    objective, preparation, and exposure identities below move exactly when the
    P5 method does.
    """

    method_recipe_version: str
    training_mode: str
    objective_policy_digest: str
    preparation_policy_digest: str
    exposure_policy: str
    learning_rate_schedule_policy_digest: str
    shared_optimizer_settings_digest: str
    replay_exposure_policy_digest: str
    extxyz_policy_digest: str
    mace_architecture_digest: str
    checkpoint_interval_epochs: int
    default_dtype: str
    device: str
    acceleration_backend: str

    def __post_init__(self) -> None:
        for name in (
            "objective_policy_digest",
            "preparation_policy_digest",
            "learning_rate_schedule_policy_digest",
            "shared_optimizer_settings_digest",
            "replay_exposure_policy_digest",
            "extxyz_policy_digest",
            "mace_architecture_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in (
            "method_recipe_version",
            "training_mode",
            "exposure_policy",
            "default_dtype",
            "device",
            "acceleration_backend",
        ):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"{name} must be non-empty.")
            object.__setattr__(self, name, value)
        if self.training_mode not in POST_SELECTION_TRAINING_MODES:
            raise TrainingDataInputError(
                f"Unsupported post-selection training mode: {self.training_mode!r}."
            )
        expected_exposure = (
            POST_SELECTION_FOUNDATION_EXPOSURE_POLICY
            if self.training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES
            else POST_SELECTION_SCRATCH_EXPOSURE_POLICY
        )
        if self.exposure_policy != expected_exposure:
            raise TrainingDataInputError(
                f"Post-selection {self.training_mode} requires exposure policy "
                f"{expected_exposure!r}."
            )
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
            "objective_policy_digest": self.objective_policy_digest,
            "preparation_policy_digest": self.preparation_policy_digest,
            "exposure_policy": self.exposure_policy,
            "learning_rate_schedule_policy_digest": (
                self.learning_rate_schedule_policy_digest
            ),
            "shared_optimizer_settings_digest": self.shared_optimizer_settings_digest,
            "replay_exposure_policy_digest": self.replay_exposure_policy_digest,
            "extxyz_policy_digest": self.extxyz_policy_digest,
            "mace_architecture_digest": self.mace_architecture_digest,
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
        # Only the current generation deserializes.  A v3 payload is readable
        # only through ``historical_method_training_projection``.
        if payload.get("schema") != POST_SELECTION_METHOD_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection method-identity schema."
            )
        result = cls(
            method_recipe_version=str(payload["method_recipe_version"]),
            training_mode=str(payload["training_mode"]),
            objective_policy_digest=str(payload["objective_policy_digest"]),
            preparation_policy_digest=str(payload["preparation_policy_digest"]),
            exposure_policy=str(payload["exposure_policy"]),
            learning_rate_schedule_policy_digest=str(
                payload["learning_rate_schedule_policy_digest"]
            ),
            shared_optimizer_settings_digest=str(
                payload["shared_optimizer_settings_digest"]
            ),
            replay_exposure_policy_digest=str(payload["replay_exposure_policy_digest"]),
            extxyz_policy_digest=str(payload["extxyz_policy_digest"]),
            mace_architecture_digest=str(payload["mace_architecture_digest"]),
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

    def training_projection(self) -> dict[str, Any]:
        """Every training-bearing field, without the schema token."""

        return {
            key: value for key, value in self._payload().items() if key != "schema"
        }


def historical_method_training_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project one authenticated historical v3 method record onto training fields.

    This is the bounded source-preserving derivation of the one-time cutover,
    not a general translator: the payload must be the exact v3 schema and must
    reproduce its own recorded digest, and only the two retired assessment-only
    parents are excluded.  Every other field is compared exactly by the caller
    against :meth:`PostSelectionMethodIdentity.training_projection`.
    """

    if payload.get("schema") != POST_SELECTION_METHOD_IDENTITY_SCHEMA_V3:
        raise TrainingDataSerializationError(
            "Historical training-equivalence accepts only the exact v3 method schema."
        )
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    if str(payload.get("content_digest", "")) != digest(body):
        raise TrainingDataSerializationError(
            "Historical v3 method record does not reproduce its own digest."
        )
    missing = [name for name in RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS if name not in body]
    if missing:
        raise TrainingDataSerializationError(
            f"Historical v3 method record lacks retired fields {missing}."
        )
    return {
        key: value
        for key, value in body.items()
        if key != "schema" and key not in RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS
    }


@dataclass(frozen=True, slots=True)
class FoundationAdaptationObjectivePolicy:
    """The fixed foundation-P5 robust objective realized by native UniversalLoss.

    It has no fields: the accepted numerical method fixes every value, and the
    three dimensional Huber thresholds are interpretations of one numeric
    parameter rather than independent knobs.  P3 ``[objective]`` and
    ``[weighting]`` overrides never reach it.
    """

    @property
    def loss_family(self) -> str:
        return MACE_FOUNDATION_LOSS_FAMILY

    @property
    def huber_delta(self) -> float:
        return MACE_FOUNDATION_HUBER_DELTA

    @property
    def energy_weight(self) -> float:
        return MACE_FOUNDATION_ENERGY_WEIGHT

    @property
    def forces_weight(self) -> float:
        return MACE_FOUNDATION_FORCES_WEIGHT

    @property
    def stress_weight(self) -> float:
        return MACE_FOUNDATION_STRESS_WEIGHT

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FOUNDATION_ADAPTATION_OBJECTIVE_POLICY_SCHEMA,
            "loss_family": self.loss_family,
            "huber_delta": self.huber_delta,
            "dimensional_thresholds": {
                "energy": "0.01 eV/atom",
                "force_base": "0.01 eV/Angstrom",
                "stress": "0.01 eV/Angstrom^3",
            },
            "force_threshold_regimes": {
                "reference_force_norm_boundaries_ev_per_angstrom": [100.0, 200.0, 300.0],
                "threshold_factors": [1.0, 0.7, 0.4, 0.1],
            },
            "stress_reduction": "mean_over_nine_stored_cartesian_entries",
            "energy_reduction": "mean_over_configurations_of_per_atom_residual",
            "energy_weight": self.energy_weight,
            "forces_weight": self.forces_weight,
            "stress_weight": self.stress_weight,
            "property_masks": "binary_label_availability",
            "configuration_weight": "neutral_transport",
            "stage_two_phase": "disabled",
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}


@dataclass(frozen=True, slots=True)
class PostSelectionPreparationPolicy:
    """The P5 fitted-preparation policy, distinct from the P3 common policy.

    One tagged, mode-disjoint type.  ``scratch`` binds its separately accepted
    from-scratch E0 and configuration-weight policies.  Foundation modes bind
    only the selected-head foundation-residual E0 method and the accepted
    composition-transfer rule; a field that belongs to the other mode is a
    validation failure, never a silently ignored default.
    """

    training_mode: str
    atomic_reference_policy: Any
    configuration_weight_policy: Any = None
    foundation_checkpoint_digest: str | None = None
    foundation_head: str | None = None
    composition_transfer_policy: str | None = None

    def __post_init__(self) -> None:
        from .reference_fit import AtomicReferenceFitMode

        mode = str(self.training_mode)
        if mode not in POST_SELECTION_TRAINING_MODES:
            raise TrainingDataInputError(
                f"Unsupported post-selection training mode: {mode!r}."
            )
        object.__setattr__(self, "training_mode", mode)
        fit_mode = self.atomic_reference_policy.fit_mode
        if mode in FOUNDATION_ADAPTATION_TRAINING_MODES:
            if fit_mode is not AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
                raise PostSelectionError(
                    "Foundation-P5 preparation requires the foundation_residual E0 fit."
                )
            if (
                self.atomic_reference_policy.ridge_lambda != 0.0
                or self.atomic_reference_policy.prior_by_atomic_number
            ):
                raise PostSelectionError(
                    "Foundation-P5 preparation has no accepted E0 prior/anchor; a "
                    "ridge or prior would manufacture identifiability."
                )
            if not self.atomic_reference_policy.allow_rank_deficient_fixed_domain:
                raise PostSelectionError(
                    "Foundation-P5 preparation decides identifiability by composition "
                    "transfer, not by rejecting every rank-deficient fit."
                )
            if self.configuration_weight_policy is not None:
                raise PostSelectionError(
                    "Foundation-P5 preparation cannot bind a configuration-weight policy."
                )
            if self.foundation_checkpoint_digest is None or not str(
                self.foundation_head or ""
            ).strip():
                raise PostSelectionError(
                    "Foundation-P5 preparation requires the selected foundation "
                    "checkpoint and head."
                )
            object.__setattr__(
                self,
                "foundation_checkpoint_digest",
                validate_digest(
                    self.foundation_checkpoint_digest,
                    name="foundation_checkpoint_digest",
                ),
            )
            object.__setattr__(self, "foundation_head", str(self.foundation_head).strip())
            if self.composition_transfer_policy != POST_SELECTION_COMPOSITION_TRANSFER_POLICY:
                raise PostSelectionError(
                    "Foundation-P5 preparation requires the accepted composition-"
                    "transfer policy."
                )
        else:
            if fit_mode is not AtomicReferenceFitMode.FROM_SCRATCH_TOTAL_ENERGY:
                raise PostSelectionError(
                    "P5 scratch preparation requires the from-scratch E0 fit."
                )
            if self.configuration_weight_policy is None:
                raise PostSelectionError(
                    "P5 scratch preparation requires its configuration-weight policy."
                )
            if (
                self.foundation_checkpoint_digest is not None
                or self.foundation_head is not None
                or self.composition_transfer_policy is not None
            ):
                raise PostSelectionError(
                    "P5 scratch preparation cannot bind foundation residual fields."
                )

    @property
    def is_foundation(self) -> bool:
        return self.training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": POST_SELECTION_PREPARATION_POLICY_SCHEMA,
            "training_mode": self.training_mode,
            "atomic_reference_policy": self.atomic_reference_policy.to_dict(),
        }
        if self.is_foundation:
            payload.update(
                {
                    "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
                    "foundation_head": self.foundation_head,
                    "composition_transfer_policy": self.composition_transfer_policy,
                }
            )
        else:
            payload["configuration_weight_policy"] = (
                self.configuration_weight_policy.to_dict()
            )
        return payload

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}


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

    ``checkpoint_maximum_target_force_rmse_ev_per_angstrom`` is the CV role's
    checkpoint target ceiling on the common monitor, always in eV/angstrom.  It
    is independent of ``acceptance_maximum``, the held-out outer threshold whose
    units follow ``acceptance_metric``.
    """

    fold_count: int
    partition_seed: int
    seed_mode: str
    fold_construction_algorithm: str
    purge_components_between_roles: int
    cv_max_num_epochs: int
    checkpoint_maximum_target_force_rmse_ev_per_angstrom: float
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
        for name in (
            "checkpoint_maximum_target_force_rmse_ev_per_angstrom",
            "acceptance_maximum",
        ):
            object.__setattr__(
                self, name, _finite_positive_threshold(getattr(self, name), name=name)
            )
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
            "purge_components_between_roles": self.purge_components_between_roles,
            "cv_max_num_epochs": self.cv_max_num_epochs,
            "checkpoint_maximum_target_force_rmse_ev_per_angstrom": (
                self.checkpoint_maximum_target_force_rmse_ev_per_angstrom
            ),
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
            purge_components_between_roles=int(
                payload["purge_components_between_roles"]
            ),
            cv_max_num_epochs=int(payload["cv_max_num_epochs"]),
            checkpoint_maximum_target_force_rmse_ev_per_angstrom=float(
                payload["checkpoint_maximum_target_force_rmse_ev_per_angstrom"]
            ),
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

    ``checkpoint_maximum_target_force_rmse_ev_per_angstrom`` is the production
    role's checkpoint target ceiling on the common monitor (eV/angstrom).
    """

    production_max_num_epochs: int
    production_seeds: tuple[int, ...]
    committee_policy: str
    allow_performance_driven_termination: bool
    checkpoint_maximum_target_force_rmse_ev_per_angstrom: float

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
        object.__setattr__(
            self,
            "checkpoint_maximum_target_force_rmse_ev_per_angstrom",
            _finite_positive_threshold(
                self.checkpoint_maximum_target_force_rmse_ev_per_angstrom,
                name="checkpoint_maximum_target_force_rmse_ev_per_angstrom",
            ),
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
            "checkpoint_maximum_target_force_rmse_ev_per_angstrom": (
                self.checkpoint_maximum_target_force_rmse_ev_per_angstrom
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
            checkpoint_maximum_target_force_rmse_ev_per_angstrom=float(
                payload["checkpoint_maximum_target_force_rmse_ev_per_angstrom"]
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


#: P5 resolves the shared optimizer semantics through the one canonical owner.
#: The re-export keeps the P5-facing name while removing the second, differently
#: defaulted resolution that let method identity describe a method that never
#: executed.
resolve_shared_optimizer_settings = _resolve_shared_optimizer_settings


def _canonical_configured_foundation_path(
    value: str, config_dir: str | Path | None
) -> Path:
    """Interpret ``[paths].foundation_model`` through the one campaign owner.

    Without a campaign configuration directory a relative locator has no
    campaign meaning at all, and resolving it against the process CWD is the
    split-brain interpretation this owner exists to remove, so it fails closed
    rather than guessing.
    """

    if config_dir is None:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            raise PostSelectionError(
                "A relative foundation checkpoint locator requires the campaign "
                f"configuration directory to be interpreted: {value!r}."
            )
        return candidate.resolve()
    return resolve_configured_path(value, config_dir)


def resolve_post_selection_foundation_identity(
    path: str | Path | None,
    *,
    requested_head: str | None = None,
    model_family: str = "MACE-MPA-0",
) -> Any | None:
    """Resolve the canonical scientific identity of a foundation checkpoint."""

    if path is None or not str(path).strip():
        return None
    # The caller resolves the configured locator through the one canonical
    # campaign path owner; inspection must authenticate exactly that file
    # rather than re-derive a second interpretation of the same value.
    source = Path(path)
    if not source.is_file():
        raise TrainingDataInputError(f"Foundation checkpoint does not exist: {source!s}.")

    from .foundation import MaceFoundationSpec, inspect_mace_foundation

    inspection = inspect_mace_foundation(source)
    identity = MaceFoundationSpec(
        family=model_family,
        requested_head=requested_head,
    ).resolve(inspection)

    if identity.inspection_state != "inspected":
        raise TrainingDataInputError(
            "Current P5 requires an inspected canonical foundation identity."
        )
    return identity


#: The accepted multihead replay exposure shared by both replay interfaces:
#: native UniversalLoss, authenticated LR/EMA, no ratio-driven duplication, and
#: MACE's own replay/``pt_head``-first combined corpus before seeded shuffle.
_REPLAY_TRAINING_EXPOSURE: dict[str, Any] = {
    "execution_semantics_version": MACE_EXECUTION_SEMANTICS_VERSION,
    "loss_family": MACE_FOUNDATION_LOSS_FAMILY,
    "force_mh_ft_lr": MACE_REPLAY_FORCE_MH_FT_LR,
    "real_pt_data_ratio_threshold": MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
    "target_duplication_factor": 1,
    "training_head_scalar_weights": "none",
    "pre_shuffle_corpus_layout": ["replay_head", "target_head"],
}


def resolve_post_selection_replay_policy_digest(
    *,
    single_replay: Any | None,
    has_legacy_replay: bool,
    training_label_mode: Any | None = None,
    target_head_name: str = POST_SELECTION_TARGET_HEAD_NAME,
    replay_head_name: str = POST_SELECTION_REPLAY_HEAD_NAME,
) -> str:
    """Path-free shared replay method policy identity."""

    target_head_name, replay_head_name = canonical_post_selection_head_names(
        target_head_name=target_head_name,
        replay_head_name=replay_head_name,
    )
    if single_replay is not None:
        normalized_label_mode = _replay_label_mode(
            single_replay.label_mode, name="single-source replay label_mode"
        )
        if training_label_mode is not None and _replay_label_mode(
            training_label_mode, name="replay training label_mode"
        ) is not normalized_label_mode:
            raise TrainingDataInputError(
                "Replay policy received a training label semantic different from "
                "the canonical single-source configuration."
            )
        payload = {
            "schema": "mdstats.post-selection-replay-policy.v4",
            "enabled": True,
            "interface": "single_source",
            "training_exposure": "separate_multihead_replay",
            "training_label_mode": normalized_label_mode.value,
            "split_ratio": list(single_replay.split_ratio),
            "split_seed": int(single_replay.split_seed),
            "true_dft_monitor_required": True,
            "target_head_name": target_head_name,
            "replay_head_name": replay_head_name,
            **_REPLAY_TRAINING_EXPOSURE,
        }
    elif has_legacy_replay:
        if training_label_mode is None:
            raise TrainingDataInputError(
                "Legacy replay policy identity requires a normalized training "
                "label semantic."
            )
        normalized_label_mode = _replay_label_mode(
            training_label_mode, name="legacy replay training label_mode"
        )
        payload = {
            "schema": "mdstats.post-selection-replay-policy.v4",
            "enabled": True,
            "interface": "legacy_split",
            "training_exposure": "separate_multihead_replay",
            "training_label_mode": normalized_label_mode.value,
            "true_dft_monitor_required": True,
            "target_head_name": target_head_name,
            "replay_head_name": replay_head_name,
            **_REPLAY_TRAINING_EXPOSURE,
        }
    else:
        payload = {
            "schema": "mdstats.post-selection-replay-policy.v2",
            "enabled": False,
            "interface": "none",
            "training_exposure": "none",
            "training_label_mode": "none",
            "split_ratio": [],
            "split_seed": None,
            "true_dft_monitor_required": False,
            "target_head_name": target_head_name,
            "replay_head_name": replay_head_name,
        }
    return digest(payload)


def compute_replay_lineage_digest(replay_resolution: Any) -> str | None:
    """Deterministic scientific lineage digest of authenticated replay artifacts."""

    if replay_resolution is None:
        return None

    # Current P5 evidence is a current-generation cutover.  Do not infer an
    # interface or scientific label meaning from a helper object's shape: an
    # incomplete transport must be rejected and its derived CV/final evidence
    # recomputed by the canonical replay resolver.
    interface = getattr(replay_resolution, "interface", None)
    if interface is None:
        raise PostSelectionError(
            "Replay lineage requires an explicit authenticated interface."
        )
    interface = str(getattr(interface, "value", interface)).strip()
    if not interface:
        raise PostSelectionError(
            "Replay lineage requires an explicit authenticated interface."
        )
    if interface not in {"single_source", "legacy_split"}:
        raise PostSelectionError(
            f"Unsupported replay interface in resolution: {interface!r}"
        )

    train_artifact = getattr(replay_resolution, "train_artifact", None)
    monitor_artifact = getattr(replay_resolution, "monitor_artifact", None)
    if train_artifact is None or monitor_artifact is None:
        raise PostSelectionError("Replay resolution is missing required train or monitor artifact.")

    def required_digest(
        owner: Any, names: tuple[str, ...], *, name: str
    ) -> str:
        value = None
        for attribute in names:
            candidate = getattr(owner, attribute, None)
            if candidate not in (None, ""):
                value = candidate
                break
        if value in (None, ""):
            raise PostSelectionError(
                f"Replay lineage requires authenticated {name} content identity."
            )
        try:
            return validate_digest(str(value), name=name)
        except TrainingDataInputError as exc:
            raise PostSelectionError(
                f"Replay lineage {name} is not a valid SHA256/content digest."
            ) from exc

    def required_digest_value(value: Any, *, name: str) -> str:
        if value in (None, ""):
            raise PostSelectionError(
                f"Replay lineage requires authenticated {name} content identity."
            )
        try:
            return validate_digest(str(value), name=name)
        except TrainingDataInputError as exc:
            raise PostSelectionError(
                f"Replay lineage {name} is not a valid SHA256/content digest."
            ) from exc

    train_sha = required_digest(train_artifact, ("sha256",), name="train_sha256")
    train_digest = required_digest(
        train_artifact,
        ("content_digest", "logical_digest"),
        name="train_content_digest",
    )
    monitor_sha = required_digest(
        monitor_artifact, ("sha256",), name="monitor_sha256"
    )
    monitor_digest = required_digest(
        monitor_artifact,
        ("content_digest", "logical_digest"),
        name="monitor_content_digest",
    )

    from .replay import ReplayLabelMode

    true_label_mode = getattr(replay_resolution, "true_label_mode", None)
    if true_label_mode in (None, ""):
        raise PostSelectionError(
            "Replay lineage requires an explicit TRUE_DFT monitor label semantic."
        )
    true_label_mode = _replay_label_mode(
        true_label_mode,
        name="replay TRUE_DFT monitor label_mode",
    )
    if true_label_mode is not ReplayLabelMode.TRUE_DFT:
        raise PostSelectionError(
            "Replay lineage requires an independent TRUE_DFT monitor artifact."
        )
    training_label_mode = getattr(replay_resolution, "training_label_mode", None)
    if training_label_mode is None:
        raise PostSelectionError(
            "Replay lineage requires an explicit replay training label semantic."
        )
    training_label_mode = _replay_label_mode(
        training_label_mode, name="replay training label_mode"
    )
    artifact_label_mode = getattr(train_artifact, "label_mode", None)
    if artifact_label_mode is not None:
        artifact_label_mode = getattr(artifact_label_mode, "value", artifact_label_mode)
        if _replay_label_mode(
            artifact_label_mode, name="replay training artifact label_mode"
        ) is not training_label_mode:
            raise PostSelectionError(
                "Replay training artifact label semantics disagree with the "
                "normalized replay-training semantic."
            )
    monitor_artifact_label_mode = getattr(monitor_artifact, "label_mode", None)
    if monitor_artifact_label_mode is not None:
        if _replay_label_mode(
            monitor_artifact_label_mode, name="replay monitor artifact label_mode"
        ) is not ReplayLabelMode.TRUE_DFT:
            raise PostSelectionError(
                "Replay monitor artifact is not an independent TRUE_DFT artifact."
            )
    true_label_mode_value = true_label_mode.value
    training_label_mode_value = training_label_mode.value

    if interface == "single_source":
        source_sha = getattr(replay_resolution, "source_sha256", None)
        source_digest = getattr(replay_resolution, "source_content_digest", None)
        split_digest = getattr(replay_resolution, "split_manifest_digest", None)
        if source_digest in (None, "") or source_sha in (None, "") or split_digest in (
            None,
            "",
        ):
            raise PostSelectionError(
                "Single-source replay lineage requires source content digest, "
                "source SHA256, and split manifest digest."
            )
        source_digest = required_digest_value(
            source_digest, name="source_content_digest"
        )
        source_sha = required_digest_value(source_sha, name="source_sha256")
        split_digest = required_digest_value(
            split_digest, name="split_manifest_digest"
        )
        payload = {
            "schema": "mdstats.post-selection-replay-lineage.v3",
            "interface": "single_source",
            "source_content_digest": source_digest,
            "source_sha256": source_sha,
            "split_manifest_digest": split_digest,
            "train_view_digest": train_digest,
            "train_sha256": train_sha,
            "true_monitor_view_digest": monitor_digest,
            "true_monitor_sha256": monitor_sha,
            "training_label_mode": training_label_mode_value,
            "true_monitor_label_mode": true_label_mode_value,
        }
    elif interface == "legacy_split":
        payload = {
            "schema": "mdstats.post-selection-replay-lineage.v3",
            "interface": "legacy_split",
            "training_label_mode": training_label_mode_value,
            "train_view_digest": train_digest,
            "train_sha256": train_sha,
            "true_monitor_view_digest": monitor_digest,
            "true_monitor_sha256": monitor_sha,
            "true_monitor_label_mode": true_label_mode_value,
        }
        source_sha = getattr(replay_resolution, "true_label_source_sha256", None)
        if source_sha is not None:
            try:
                payload["true_label_source_sha256"] = validate_digest(
                    str(source_sha), name="true_label_source_sha256"
                )
            except TrainingDataInputError as exc:
                raise PostSelectionError(
                    "Replay TRUE_DFT source identity is not a valid SHA256."
                ) from exc
    return digest(payload)


@dataclass(frozen=True, slots=True)
class PostSelectionMethodPolicies:
    """The accepted policy objects the shared method identity summarizes.

    Both the identity and the execution owners resolve the method through this
    one function, so the policy a run actually executes and the digest that
    claims to describe it cannot drift apart.

    The replay hard limit and warning threshold are resolved here by the same
    configuration owner, but they are *assessment* coordinates: neither enters
    :class:`PostSelectionMethodIdentity`.  They are exposed as two separate
    dependency projections - the hard-decision constraints and the
    diagnostic-only warning policy - so a warning edit has no hard edge.
    """

    objective: Any
    preparation: PostSelectionPreparationPolicy
    replay_exposure_policy_digest: str
    learning_rate_schedule: Any
    replay_enabled: bool
    replay_hard_limit_ev_per_angstrom: float | None
    replay_warning_ev_per_angstrom: float | None
    extxyz: Any
    training_mode: str
    acceleration_backend: str
    checkpoint_interval_epochs: int
    device: str
    mace_architecture: dict[str, Any]
    mace_architecture_digest: str
    default_dtype: str = "float32"
    foundation_potential_identity: Any = None
    foundation_model: str | None = None
    foundation_head: str | None = None
    target_head_name: str = POST_SELECTION_TARGET_HEAD_NAME
    replay_head_name: str = POST_SELECTION_REPLAY_HEAD_NAME
    replay_training_label_mode: Any = None
    checkpoint_policy_configuration: Any = None

    def replay_hard_constraints(self) -> dict[str, Any]:
        """The shared hard constraints every role applies identically."""

        return {
            "replay_enabled": bool(self.replay_enabled),
            "replay_degradation_hard_limit_ev_per_angstrom": (
                self.replay_hard_limit_ev_per_angstrom if self.replay_enabled else None
            ),
            "replay_label_requirement": "true_dft",
            "required_physical_gates": (),
        }

    @property
    def replay_hard_decision_digest(self) -> str:
        """Dependency projection of the shared replay hard decision only."""

        return digest(
            {
                "schema": POST_SELECTION_REPLAY_HARD_DECISION_SCHEMA,
                **{
                    key: (list(value) if isinstance(value, tuple) else value)
                    for key, value in self.replay_hard_constraints().items()
                },
            }
        )

    @property
    def replay_warning_policy(self) -> Any | None:
        """The diagnostic-only warning policy, or ``None`` without replay."""

        if not self.replay_enabled or self.replay_warning_ev_per_angstrom is None:
            return None
        from .train2_policy import ReplayWarningDiagnosticPolicy

        return ReplayWarningDiagnosticPolicy(
            warning_threshold_ev_per_angstrom=self.replay_warning_ev_per_angstrom
        )


def post_selection_checkpoint_admissibility(
    policies: PostSelectionMethodPolicies,
    role_policy: CvValidationPolicyIdentity | FinalProductionPolicyIdentity,
) -> Any:
    """Compose the one role-effective hard checkpoint-decision policy of a run.

    The shared replay hard constraint comes from the configuration owner's
    hard-decision projection and the target-force ceiling from the run's role
    policy; there is no other source of either.  The replay warning threshold
    is never a parent of this policy.
    """

    from .train2_policy import CheckpointAdmissibilityPolicy

    if not isinstance(
        role_policy, (CvValidationPolicyIdentity, FinalProductionPolicyIdentity)
    ):
        raise PostSelectionError(
            "Checkpoint admissibility requires a CV or final-production role policy."
        )
    return CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=(
            role_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom
        ),
        **policies.replay_hard_constraints(),
    )


def cv_assessment_position_policy_digest(
    admissibility: Any, cv_policy: CvValidationPolicyIdentity
) -> str:
    """CV fold assessment position: hard policy + D2.DEF.059A + outer verdict policy.

    It deliberately excludes the replay warning policy and every training
    coordinate (those move the training trajectory, not the assessment).
    """

    return digest(
        {
            "schema": CV_ASSESSMENT_POSITION_POLICY_SCHEMA,
            "hard_checkpoint_policy_digest": admissibility.policy_digest,
            "within_run_selection_identity": P5_WITHIN_RUN_SELECTION_IDENTITY,
            "acceptance_metric": cv_policy.acceptance_metric,
            "acceptance_maximum": cv_policy.acceptance_maximum,
        }
    )


def final_seed_assessment_policy_digest(admissibility: Any) -> str:
    """Final-seed assessment position: final hard policy + D2.DEF.059A only.

    Current-CV authorization, publication mode and D2.DEF.059B are excluded:
    they are separate authorization/aggregate-publication parents.
    """

    return digest(
        {
            "schema": FINAL_SEED_ASSESSMENT_POLICY_SCHEMA,
            "hard_checkpoint_policy_digest": admissibility.policy_digest,
            "within_run_selection_identity": P5_WITHIN_RUN_SELECTION_IDENTITY,
        }
    )


def final_publication_policy_digest(policy: FinalProductionPolicyIdentity) -> str:
    """Aggregate publication policy: publication mode (+ D2.DEF.059B if single-best)."""

    committee = str(policy.committee_policy)
    return digest(
        {
            "schema": FINAL_PUBLICATION_POLICY_SCHEMA,
            "committee_policy": committee,
            "cross_seed_selection_identity": (
                P5_CROSS_SEED_SELECTION_IDENTITY
                if committee == "single_best_final_seed"
                else None
            ),
        }
    )


# ---------------------------------------------------------------------------
# P5 checkpoint-policy configuration generation (campaign schema v2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class P5CheckpointPolicyConfiguration:
    """The one resolution of every P5 threshold coordinate, with migration.

    ``generation`` is the migration discriminator only; it is never hashed.
    Every value here is already validated and in eV/angstrom (the CV outer
    maximum keeps the units of its configured metric).
    """

    generation: str
    replay_warning_ev_per_angstrom: float
    replay_hard_limit_ev_per_angstrom: float
    production_target_ev_per_angstrom: float
    cv_checkpoint_target_ev_per_angstrom: float | None
    cv_acceptance_metric: str
    cv_acceptance_maximum: float
    migration_notices: tuple[str, ...] = ()


def _config_number(value: Any, *, name: str) -> float:
    return _finite_positive_threshold(value, name=name)


def resolve_p5_checkpoint_policy_configuration(
    config: Mapping[str, Any], *, training_mode: str
) -> P5CheckpointPolicyConfiguration:
    """Resolve replay/role thresholds under the narrow policy-generation rules.

    Global campaign schema stays v2.  ``[acceptance].post_selection_checkpoint_
    policy_generation = "p5_target_replay_v2"`` marks the current authored
    contract; without it the historical generated defaults are migrated by the
    exact ratified table and ambiguous historical states fail closed.
    """

    acceptance = _table(config, "acceptance")
    training = _table(config, "training")
    cv = _table(config, "post_selection", "cv")
    mode = str(training_mode)
    if mode not in POST_SELECTION_TRAINING_MODES:
        raise TrainingDataInputError(f"Unsupported post-selection training mode: {mode!r}.")
    foundation = mode in FOUNDATION_ADAPTATION_TRAINING_MODES

    raw_marker = acceptance.get(P5_CHECKPOINT_POLICY_GENERATION_FIELD)
    if raw_marker is not None and raw_marker != P5_CHECKPOINT_POLICY_GENERATION:
        raise PostSelectionError(
            f"[acceptance].{P5_CHECKPOINT_POLICY_GENERATION_FIELD} must be "
            f"{P5_CHECKPOINT_POLICY_GENERATION!r}; received {raw_marker!r}."
        )
    current = raw_marker == P5_CHECKPOINT_POLICY_GENERATION
    legacy_present = {
        f"[{table}].{name}": (acceptance if table == "acceptance" else training)[name]
        for table, name in LEGACY_REPLAY_FIELDS
        if name in (acceptance if table == "acceptance" else training)
    }
    new_present = [name for name in (REPLAY_WARNING_FIELD, REPLAY_HARD_LIMIT_FIELD) if name in acceptance]
    notices: list[str] = []

    # --- replay warning/hard -------------------------------------------------
    if current:
        if legacy_present:
            raise PostSelectionError(
                "The retired one-number replay field(s) "
                f"{sorted(legacy_present)} are invalid under "
                f"{P5_CHECKPOINT_POLICY_GENERATION!r}: set "
                f"[acceptance].{REPLAY_WARNING_FIELD} and "
                f"[acceptance].{REPLAY_HARD_LIMIT_FIELD} instead."
            )
        warning_mev = _config_number(
            acceptance.get(REPLAY_WARNING_FIELD, DEFAULT_REPLAY_WARNING_MEV_PER_A),
            name=f"[acceptance].{REPLAY_WARNING_FIELD}",
        )
        hard_mev = _config_number(
            acceptance.get(REPLAY_HARD_LIMIT_FIELD, DEFAULT_REPLAY_HARD_LIMIT_MEV_PER_A),
            name=f"[acceptance].{REPLAY_HARD_LIMIT_FIELD}",
        )
    else:
        if new_present:
            raise PostSelectionError(
                f"Replay field(s) {['[acceptance].' + n for n in new_present]} "
                "belong to the current checkpoint-policy generation. Add "
                f"[acceptance].{P5_CHECKPOINT_POLICY_GENERATION_FIELD} = "
                f"{P5_CHECKPOINT_POLICY_GENERATION!r}"
                + (
                    f" and remove the retired {sorted(legacy_present)}"
                    if legacy_present
                    else ""
                )
                + "; mixed or unmarked replay authorities are refused."
            )
        for name, value in legacy_present.items():
            legacy = _config_number(value, name=name)
            if legacy != LEGACY_GENERATED_REPLAY_MEV_PER_A:
                raise PostSelectionError(
                    f"{name} = {value!r} is a custom historical one-number replay "
                    "budget whose meaning under the current warning/hard replay "
                    "policy is ambiguous. Add "
                    f"[acceptance].{P5_CHECKPOINT_POLICY_GENERATION_FIELD} = "
                    f"{P5_CHECKPOINT_POLICY_GENERATION!r}, remove {name}, and set "
                    f"{REPLAY_WARNING_FIELD}/{REPLAY_HARD_LIMIT_FIELD} explicitly."
                )
        if legacy_present:
            notices.append(
                f"migrated historical generated replay budget {sorted(legacy_present)} "
                f"= {LEGACY_GENERATED_REPLAY_MEV_PER_A:g} meV/angstrom to the current "
                f"diagnostic warning {DEFAULT_REPLAY_WARNING_MEV_PER_A:g} and catastrophic "
                f"hard limit {DEFAULT_REPLAY_HARD_LIMIT_MEV_PER_A:g} meV/angstrom; add "
                f"{P5_CHECKPOINT_POLICY_GENERATION_FIELD} = "
                f"{P5_CHECKPOINT_POLICY_GENERATION!r} to adopt the current fields"
            )
        warning_mev = DEFAULT_REPLAY_WARNING_MEV_PER_A
        hard_mev = DEFAULT_REPLAY_HARD_LIMIT_MEV_PER_A
    if not warning_mev < hard_mev:
        raise PostSelectionError(
            f"Replay warning ({warning_mev:g}) must be strictly below the replay hard "
            f"limit ({hard_mev:g}) meV/angstrom."
        )

    # --- role target thresholds ---------------------------------------------
    acceptance_metric = str(cv.get("acceptance_metric", CV_DEFAULT_ACCEPTANCE_METRIC))
    default_metric = acceptance_metric == CV_DEFAULT_ACCEPTANCE_METRIC
    raw_production = acceptance.get("maximum_target_force_rmse_ev_per_angstrom")
    raw_cv_checkpoint = cv.get("checkpoint_maximum_target_force_rmse_ev_per_angstrom")
    raw_cv_maximum = cv.get("acceptance_maximum")
    if foundation:
        if raw_production is None:
            production = FOUNDATION_PRODUCTION_DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
        else:
            production = _config_number(
                raw_production, name="maximum_target_force_rmse_ev_per_angstrom"
            )
            if not current and production == LEGACY_GENERATED_FOUNDATION_PRODUCTION_EV_PER_ANGSTROM:
                production = FOUNDATION_PRODUCTION_DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
                notices.append(
                    "migrated historical generated foundation production target 0.030 "
                    "-> 0.050 eV/angstrom"
                )
        if raw_cv_checkpoint is None:
            cv_checkpoint = FOUNDATION_CV_CHECKPOINT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
        else:
            cv_checkpoint = _config_number(
                raw_cv_checkpoint,
                name="checkpoint_maximum_target_force_rmse_ev_per_angstrom",
            )
            if not current and cv_checkpoint == LEGACY_GENERATED_FOUNDATION_CV_EV_PER_ANGSTROM:
                cv_checkpoint = FOUNDATION_CV_CHECKPOINT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
                notices.append(
                    "migrated historical generated foundation CV checkpoint ceiling "
                    "0.045 -> 0.075 eV/angstrom"
                )
        if default_metric:
            if raw_cv_maximum is None:
                cv_maximum = FOUNDATION_CV_DEFAULT_ACCEPTANCE_MAXIMUM_EV_PER_ANGSTROM
            else:
                cv_maximum = _config_number(raw_cv_maximum, name="acceptance_maximum")
                if not current and cv_maximum == LEGACY_GENERATED_FOUNDATION_CV_EV_PER_ANGSTROM:
                    cv_maximum = FOUNDATION_CV_DEFAULT_ACCEPTANCE_MAXIMUM_EV_PER_ANGSTROM
                    notices.append(
                        "migrated historical generated foundation CV held-out ceiling "
                        "0.045 -> 0.075 eV/angstrom"
                    )
        else:
            # A non-default outer metric keeps its accepted units/resolution and
            # is never force-RMSE-migrated.
            cv_maximum = (
                FOUNDATION_CV_NON_DEFAULT_METRIC_ACCEPTANCE_MAXIMUM
                if raw_cv_maximum is None
                else _config_number(raw_cv_maximum, name="acceptance_maximum")
            )
    else:
        if raw_cv_checkpoint is not None:
            raise PostSelectionError(
                "[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom "
                "is valid only for foundation adaptation modes. Scratch CV reads its "
                "checkpoint target-force ceiling from [acceptance]."
            )
        production = _config_number(
            DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
            if raw_production is None
            else raw_production,
            name="maximum_target_force_rmse_ev_per_angstrom",
        )
        cv_checkpoint = None
        cv_maximum = _config_number(
            DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM
            if raw_cv_maximum is None
            else raw_cv_maximum,
            name="acceptance_maximum",
        )
    return P5CheckpointPolicyConfiguration(
        generation=P5_CHECKPOINT_POLICY_GENERATION if current else "historical_unmarked",
        replay_warning_ev_per_angstrom=warning_mev / 1000.0,
        replay_hard_limit_ev_per_angstrom=hard_mev / 1000.0,
        production_target_ev_per_angstrom=production,
        cv_checkpoint_target_ev_per_angstrom=cv_checkpoint,
        cv_acceptance_metric=acceptance_metric,
        cv_acceptance_maximum=cv_maximum,
        migration_notices=tuple(notices),
    )


def resolve_post_selection_training_mode(config: Mapping[str, Any]) -> str:
    """Resolve the one enabled P5 training mode from configuration alone."""

    training = _table(config, "training")
    paths = _table(config, "paths")
    model = _table(config, "model")
    modes = training.get("modes")
    if isinstance(modes, (tuple, list)) and modes:
        if len(modes) != 1:
            raise PostSelectionError(
                "Post-selection work requires exactly one enabled training method."
            )
        training_mode = str(modes[0])
    elif "mode" in training and str(training["mode"]).strip():
        training_mode = str(training["mode"]).strip()
    elif "training_mode" in training and str(training["training_mode"]).strip():
        training_mode = str(training["training_mode"]).strip()
    elif any(
        str(paths.get(key, "")).strip()
        for key in ("replay_set", "replay_train", "replay_monitor", "replay_true_labels")
    ):
        training_mode = "multihead_replay"
    elif paths.get("foundation_model") or paths.get("model") or model.get(
        "foundation_model"
    ):
        training_mode = "naive_fine_tuning"
    else:
        training_mode = "scratch"
    if training_mode not in POST_SELECTION_TRAINING_MODES:
        raise TrainingDataInputError(
            f"Unsupported training mode: '{training_mode}'. Accepted values are 'scratch', 'naive_fine_tuning', or 'multihead_replay'."
        )
    return training_mode


def resolve_post_selection_method_policies(
    config: Mapping[str, Any],
    *,
    config_dir: str | Path | None = None,
) -> PostSelectionMethodPolicies:
    """Resolve the shared method's policy objects from configuration alone.

    ``config_dir`` is the campaign configuration directory that configured
    relative paths are anchored to.  Production always supplies it, so the
    foundation checkpoint a P5 method identity describes is the same file
    ``doctor`` and P5 execution reach, independent of the invocation CWD.

    Replay admissibility follows the campaign's configured replay corpus: a
    campaign with no TRUE_DFT replay source does not acquire a replay
    constraint it cannot satisfy, and one that configures replay cannot lose it.
    Replay only ever hard-gates at the catastrophic limit and warns below it;
    representative ordering is strict target RMSE.
    """

    from .mace_export import MaceExtxyzPolicy
    from .model_features import canonicalize_mace_candidate_architecture
    from .objectives import (
        resolve_configuration_weight_policy,
        resolve_training_objective_policy,
    )
    from .reference_fit import resolve_atomic_reference_fit_policy
    from .reference_fit import AtomicReferenceFitMode, AtomicReferenceFitPolicy
    from .replay import ReplayLabelMode, single_source_replay_config_from_campaign
    from .train2_policy import LearningRateSchedulePolicy

    training = _table(config, "training")
    acceleration = _table(config, "acceleration")
    paths = _table(config, "paths")
    model = _table(config, "model")
    foundation = _table(config, "foundation")
    replay = _table(config, "replay")

    retired = sorted(
        name for name in RETIRED_POST_SELECTION_TRAINING_FIELDS if name in training
    )
    if retired:
        raise PostSelectionError(
            "Retired target/replay training-head scalar weights are not a current "
            f"P5 method field: [training].{', [training].'.join(retired)}. Remove "
            "them; checkpoint/adaptive-stop target/replay score weights are separate "
            "and unchanged."
        )

    # 1. Canonical replay-source presence.  A replay table with no source is
    # still a configuration error for scratch/naive methods; it must not be
    # silently downgraded to an admissibility-only mode.  The replay policy
    # this owner derives is path-free, but it is resolved through the campaign
    # configuration directory so P5 never becomes a second interpretation of a
    # configured replay locator.
    single_replay = single_source_replay_config_from_campaign(
        config, base_directory=config_dir
    )
    legacy_replay_train = str(paths.get("replay_train", "")).strip()
    legacy_replay_monitor = str(paths.get("replay_monitor", "")).strip()
    legacy_replay_true = str(paths.get("replay_true_labels", "")).strip()
    legacy_replay_set = str(paths.get("replay_set", "")).strip()
    has_legacy_replay = bool(
        legacy_replay_train
        or legacy_replay_monitor
        or legacy_replay_true
        or legacy_replay_set
    )
    replay_enabled = single_replay is not None or has_legacy_replay
    replay_training_source_enabled = single_replay is not None or bool(
        legacy_replay_train
    )
    replay_configured = _post_selection_replay_configuration_present(
        replay,
        single_replay=single_replay,
        has_replay_paths=has_legacy_replay,
    )
    target_head_name, replay_head_name = resolve_post_selection_head_names(config)

    # 2. Canonical training-mode resolution.
    training_mode = resolve_post_selection_training_mode(config)

    foundation_model_value = paths.get("foundation_model")
    if foundation_model_value in (None, ""):
        foundation_model_value = paths.get("model")
    if foundation_model_value in (None, ""):
        foundation_model_value = model.get("foundation_model")
    f_model_raw = (
        ""
        if foundation_model_value in (None, "")
        else str(foundation_model_value).strip()
    )

    # 3. The three supported P5 methods have an exact foundation/replay
    # topology.  Validate it before resolving any downstream policy identity.
    if training_mode == "scratch":
        if f_model_raw:
            raise PostSelectionError(
                "P5 scratch training cannot configure a foundation checkpoint."
            )
        if replay_configured:
            raise PostSelectionError(
                "P5 scratch training cannot configure replay sources or replay policy."
            )
    elif training_mode == "naive_fine_tuning":
        if not f_model_raw:
            raise PostSelectionError(
                "P5 naive_fine_tuning requires a foundation checkpoint."
            )
        if replay_configured:
            raise PostSelectionError(
                "P5 naive_fine_tuning cannot configure replay sources or replay policy."
            )
    else:
        if not f_model_raw:
            raise PostSelectionError(
                "P5 multihead_replay requires a foundation checkpoint."
            )
        if not replay_training_source_enabled:
            raise PostSelectionError(
                "P5 multihead_replay requires a canonical replay training source."
            )
        if single_replay is None and not legacy_replay_monitor:
            raise PostSelectionError(
                "P5 multihead_replay requires an independent TRUE_DFT monitor "
                "path."
            )

    replay_training_label_mode = resolve_post_selection_replay_training_label_mode(
        config,
        single_replay=single_replay,
        has_legacy_replay=has_legacy_replay,
    )
    if (
        training_mode == "multihead_replay"
        and single_replay is None
        and replay_training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        and not legacy_replay_true
    ):
        raise PostSelectionError(
            "P5 pseudolabel replay requires the independent TRUE_DFT monitor "
            "source root."
        )

    # 4. Replay exposure digest.  The compatibility matrix above guarantees
    # that an enabled replay digest can only describe executable multihead
    # replay training, never a scratch or naive run.
    replay_exposure_policy_digest = resolve_post_selection_replay_policy_digest(
        single_replay=single_replay,
        has_legacy_replay=has_legacy_replay,
        training_label_mode=replay_training_label_mode,
        target_head_name=target_head_name,
        replay_head_name=replay_head_name,
    )

    configured_atomic_reference_policy = resolve_atomic_reference_fit_policy(config)

    # The learned-model dtype is resolved by the one binary precision authority
    # that executable optimizer construction uses.  Independently defaulting P5
    # identity to FP64 while the campaign executes FP32 is exactly the
    # identity/execution split this owner must not reintroduce.
    default_dtype = resolve_binary_model_dtype(config)
    shared_optimizer = _resolve_shared_optimizer_settings(config)

    f_head_configured = training.get(
        "foundation_head",
        model.get("foundation_head", foundation.get("head")),
    )
    f_head_req = (
        str(f_head_configured).strip()
        if f_head_configured is not None and str(f_head_configured).strip()
        else None
    )

    foundation_locator = (
        _canonical_configured_foundation_path(f_model_raw, config_dir)
        if f_model_raw
        else None
    )
    foundation_identity = None
    if foundation_locator is not None:
        foundation_identity = resolve_post_selection_foundation_identity(
            foundation_locator,
            requested_head=f_head_req,
            model_family=str(
                foundation.get("family", model.get("family", "MACE-MPA-0"))
            ),
        )
    foundation_checkpoint_digest = (
        foundation_identity.canonical_content_digest
        if foundation_identity is not None
        else None
    )
    resolved_foundation_head = (
        foundation_identity.foundation_head
        if foundation_identity is not None
        else None
    )

    # 5. Mode-specific objective and preparation policies.  P5 scratch keeps
    # its separately accepted weighted objective, configuration weights, and
    # from-scratch E0 through the shared component owners.  Foundation P5 has a
    # fixed objective independent of P3 [objective]/[weighting], and its E0 is
    # the selected-head foundation residual with composition transfer.
    if training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES:
        objective: Any = FoundationAdaptationObjectivePolicy()
        atomic_table = config.get("atomic_references")
        explicit_fit_mode = (
            atomic_table.get("fit_mode")
            if isinstance(atomic_table, Mapping)
            else None
        )
        if explicit_fit_mode not in (
            None,
            AtomicReferenceFitMode.FOUNDATION_RESIDUAL.value,
        ):
            raise PostSelectionError(
                "Foundation-model P5 fits selected-head foundation-residual E0 "
                "corrections; [atomic_references].fit_mode = "
                f"{explicit_fit_mode!r} is incompatible. Remove it or set "
                "'foundation_residual'."
            )
        preparation = PostSelectionPreparationPolicy(
            training_mode=training_mode,
            atomic_reference_policy=AtomicReferenceFitPolicy(
                fit_mode=AtomicReferenceFitMode.FOUNDATION_RESIDUAL,
                ridge_lambda=configured_atomic_reference_policy.ridge_lambda,
                allow_rank_deficient_fixed_domain=(
                    configured_atomic_reference_policy.allow_rank_deficient_fixed_domain
                ),
            ),
            foundation_checkpoint_digest=foundation_checkpoint_digest,
            foundation_head=resolved_foundation_head,
            composition_transfer_policy=POST_SELECTION_COMPOSITION_TRANSFER_POLICY,
        )
    else:
        objective = resolve_training_objective_policy(config)
        preparation = PostSelectionPreparationPolicy(
            training_mode=training_mode,
            atomic_reference_policy=configured_atomic_reference_policy,
            configuration_weight_policy=resolve_configuration_weight_policy(config),
        )

    # 6. MACE Architecture Resolution
    raw_arch = model.get("mace_architecture")
    if raw_arch is None and any(
        k in model
        for k in (
            "r_max",
            "num_interactions",
            "hidden_irreps",
            "num_channels",
            "max_L",
        )
    ):
        raw_arch = model
    if raw_arch is None:
        raw_arch = training.get("mace_architecture")
    mace_architecture = canonicalize_mace_candidate_architecture(raw_arch)
    mace_architecture_digest = digest(mace_architecture)

    # 7. Assessment thresholds and LR schedule.  One configuration owner
    # resolves every threshold coordinate (with the narrow generation
    # migration); none of them enters the training method identity.
    checkpoint_policy_configuration = resolve_p5_checkpoint_policy_configuration(
        config, training_mode=training_mode
    )
    from .acceleration import MaceAccelerationBackend, MaceAccelerationPolicy
    source_backend = str(acceleration.get("backend", "e3nn")).strip().lower()
    req_backend = str(acceleration.get("training_backend", source_backend)).strip().lower()
    acc_policy = MaceAccelerationPolicy(
        backend=MaceAccelerationBackend(req_backend),
        only_cueq=bool(acceleration.get("only_cueq", False)),
    )
    acceleration_backend = acc_policy.backend.value
    return PostSelectionMethodPolicies(
        objective=objective,
        preparation=preparation,
        replay_exposure_policy_digest=replay_exposure_policy_digest,
        learning_rate_schedule=LearningRateSchedulePolicy(
            # One canonical resolved value; never a second independent read of
            # ``[training].learning_rate``.
            base_learning_rate=shared_optimizer["learning_rate"],
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
        replay_enabled=replay_enabled,
        replay_hard_limit_ev_per_angstrom=(
            checkpoint_policy_configuration.replay_hard_limit_ev_per_angstrom
            if replay_enabled
            else None
        ),
        replay_warning_ev_per_angstrom=(
            checkpoint_policy_configuration.replay_warning_ev_per_angstrom
            if replay_enabled
            else None
        ),
        extxyz=MaceExtxyzPolicy(),
        training_mode=training_mode,
        acceleration_backend=acceleration_backend,
        checkpoint_interval_epochs=int(training.get("checkpoint_interval_epochs", 1)),
        device=resolve_post_selection_device(config),
        mace_architecture=mace_architecture,
        mace_architecture_digest=mace_architecture_digest,
        default_dtype=default_dtype,
        foundation_potential_identity=foundation_identity,
        foundation_model=str(foundation_locator) if foundation_locator else None,
        foundation_head=resolved_foundation_head if f_model_raw else None,
        target_head_name=target_head_name,
        replay_head_name=replay_head_name,
        replay_training_label_mode=replay_training_label_mode,
        checkpoint_policy_configuration=checkpoint_policy_configuration,
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
        # Identity cutover: the shared optimizer semantics and the learned-model
        # dtype now come from the canonical resolvers that execution uses.  Old
        # evidence may have executed different effective values than its
        # identity claimed, so it must not authenticate under the corrected
        # method.
        method_recipe_version=POST_SELECTION_METHOD_RECIPE_VERSION,
        training_mode=resolved.training_mode,
        objective_policy_digest=resolved.objective.policy_digest,
        preparation_policy_digest=resolved.preparation.policy_digest,
        exposure_policy=(
            POST_SELECTION_FOUNDATION_EXPOSURE_POLICY
            if resolved.training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES
            else POST_SELECTION_SCRATCH_EXPOSURE_POLICY
        ),
        learning_rate_schedule_policy_digest=(
            resolved.learning_rate_schedule.policy_digest
        ),
        shared_optimizer_settings_digest=digest(
            shared_optimizer_settings_payload(config)
        ),
        replay_exposure_policy_digest=resolved.replay_exposure_policy_digest,
        extxyz_policy_digest=resolved.extxyz.policy_digest,
        mace_architecture_digest=resolved.mace_architecture_digest,
        checkpoint_interval_epochs=resolved.checkpoint_interval_epochs,
        default_dtype=str(resolved.default_dtype),
        device=resolved.device,
        acceleration_backend=resolved.acceleration_backend,
    )


def resolve_cv_validation_policy_identity(
    config: Mapping[str, Any],
    *,
    max_num_epochs: int | None = None,
    training_mode: str | None = None,
) -> CvValidationPolicyIdentity:
    """Resolve ``[post_selection.cv]`` into the CV-only policy identity.

    The CV training budget is resolved here and nowhere else.  It deliberately
    does not read ``[training].max_num_epochs``: a production horizon edit must
    not invalidate accepted cross-validation evidence.

    ``max_num_epochs`` is the *frozen effective* CV horizon admitted with the
    target selection.  Once an experiment is frozen its budget is part of that
    experiment, so a later configuration edit must not silently rewrite it.
    Every other field still comes from its existing configuration owner: this is
    one field substitution, not a second policy resolver.

    Target ceilings are method-aware and resolved by the one P5 threshold
    owner :func:`resolve_p5_checkpoint_policy_configuration`: foundation CV
    defaults to ``tau_CV = theta_CV = 0.075`` under the default force metric
    (with the narrow historical-generation migration), and scratch keeps its
    separately accepted ``[acceptance]`` ceiling and 0.030 outer default.
    """

    cv = _table(config, "post_selection", "cv")
    retired = sorted(name for name in RETIRED_CV_POLICY_FIELDS if name in cv)
    if retired:
        raise PostSelectionError(
            f"[post_selection.cv].{retired[0]} is retired: current P5 checkpoint "
            "control uses one campaign-common target monitor outside every fold, so "
            "folds reserve no selected-only monitor components. Remove the field."
        )
    for forbidden in ("max_num_epochs_from_training", "n3", "target_size"):
        if forbidden in cv:
            raise PostSelectionError(
                f"[post_selection.cv].{forbidden} is not a CV policy field. The CV "
                "budget is independent of both target-size n3 and the production "
                "horizon."
            )
    mode = (
        resolve_post_selection_training_mode(config)
        if training_mode is None
        else str(training_mode)
    )
    thresholds = resolve_p5_checkpoint_policy_configuration(config, training_mode=mode)
    checkpoint_ceiling = (
        thresholds.production_target_ev_per_angstrom
        if thresholds.cv_checkpoint_target_ev_per_angstrom is None
        else thresholds.cv_checkpoint_target_ev_per_angstrom
    )
    return CvValidationPolicyIdentity(
        fold_count=int(cv.get("fold_count", DEFAULT_CV_FOLD_COUNT)),
        partition_seed=int(cv.get("partition_seed", 104729)),
        seed_mode=str(cv.get("seed_mode", "explicit")),
        fold_construction_algorithm=CV_FOLD_CONSTRUCTION_ALGORITHM,
        purge_components_between_roles=int(cv.get("purge_components_between_roles", 0)),
        cv_max_num_epochs=(
            int(max_num_epochs)
            if max_num_epochs is not None
            else int(cv.get("max_num_epochs", DEFAULT_CV_MAX_NUM_EPOCHS))
        ),
        checkpoint_maximum_target_force_rmse_ev_per_angstrom=checkpoint_ceiling,
        acceptance_metric=thresholds.cv_acceptance_metric,
        acceptance_maximum=thresholds.cv_acceptance_maximum,
        aggregation_rule=CV_AGGREGATION_ALL_REQUIRED,
        dispersion_policy=CV_DISPERSION_DIAGNOSTIC_ONLY,
        required_cv_seeds=cv.get("seeds", (0,)),
    )


def resolve_final_production_policy_identity(
    config: Mapping[str, Any],
    *,
    max_num_epochs: int | None = None,
    training_mode: str | None = None,
) -> FinalProductionPolicyIdentity:
    """Resolve the production-only policy, including the effective horizon.

    ``[training].max_num_epochs`` is read exactly once, here.  Nothing derives
    it from target-size ``n3`` and nothing derives ``n3`` from it.

    The production checkpoint target ceiling is the ``[acceptance]`` target
    ceiling for every training mode; its omitted/historical-generated value is
    resolved mode-aware by :func:`resolve_p5_checkpoint_policy_configuration`
    (foundation 0.050, scratch 0.030).

    ``max_num_epochs`` is the frozen effective production horizon admitted with
    the target selection, and it substitutes for the configured value alone.  It
    does not reach the CV policy: the two role horizons stay independent, so
    changing one never invalidates the other role's accepted evidence.
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
        production_max_num_epochs=(
            int(max_num_epochs)
            if max_num_epochs is not None
            else int(training.get("max_num_epochs", 30))
        ),
        production_seeds=production.get("seeds", training.get("seeds", (1,))),
        committee_policy=str(
            production.get("committee_policy", "all_qualified_final_seeds")
        ),
        allow_performance_driven_termination=bool(
            production.get("allow_performance_driven_termination", False)
        ),
        checkpoint_maximum_target_force_rmse_ev_per_angstrom=(
            resolve_p5_checkpoint_policy_configuration(
                config,
                training_mode=(
                    resolve_post_selection_training_mode(config)
                    if training_mode is None
                    else str(training_mode)
                ),
            ).production_target_ev_per_angstrom
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
    "CV_ASSESSMENT_POSITION_POLICY_SCHEMA",
    "FINAL_PUBLICATION_POLICY_SCHEMA",
    "FINAL_SEED_ASSESSMENT_POLICY_SCHEMA",
    "FOUNDATION_PRODUCTION_DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM",
    "P5_CHECKPOINT_POLICY_GENERATION",
    "P5_CHECKPOINT_POLICY_GENERATION_FIELD",
    "P5_CROSS_SEED_SELECTION_IDENTITY",
    "P5_WITHIN_RUN_SELECTION_IDENTITY",
    "P5CheckpointPolicyConfiguration",
    "POST_SELECTION_METHOD_IDENTITY_SCHEMA_V3",
    "POST_SELECTION_REPLAY_HARD_DECISION_SCHEMA",
    "RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS",
    "cv_assessment_position_policy_digest",
    "final_publication_policy_digest",
    "final_seed_assessment_policy_digest",
    "historical_method_training_projection",
    "resolve_p5_checkpoint_policy_configuration",
    "CV_DEFAULT_ACCEPTANCE_METRIC",
    "DEFAULT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM",
    "FOUNDATION_CV_CHECKPOINT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM",
    "FOUNDATION_CV_DEFAULT_ACCEPTANCE_MAXIMUM_EV_PER_ANGSTROM",
    "post_selection_checkpoint_admissibility",
    "resolve_post_selection_training_mode",
    "CV_AGGREGATION_ALL_REQUIRED",
    "CV_DISPERSION_DIAGNOSTIC_ONLY",
    "CV_FOLD_CONSTRUCTION_ALGORITHM",
    "CV_VALIDATION_POLICY_IDENTITY_SCHEMA",
    "DEFAULT_CV_FOLD_COUNT",
    "DEFAULT_CV_MAX_NUM_EPOCHS",
    "FINAL_PRODUCTION_POLICY_IDENTITY_SCHEMA",
    "FOUNDATION_ADAPTATION_OBJECTIVE_POLICY_SCHEMA",
    "POST_SELECTION_COMPOSITION_TRANSFER_POLICY",
    "POST_SELECTION_FOUNDATION_EXPOSURE_POLICY",
    "POST_SELECTION_METHOD_IDENTITY_SCHEMA",
    "POST_SELECTION_PREPARATION_POLICY_SCHEMA",
    "POST_SELECTION_SCRATCH_EXPOSURE_POLICY",
    "RETIRED_POST_SELECTION_TRAINING_FIELDS",
    "POST_SELECTION_REPLAY_HEAD_NAME",
    "POST_SELECTION_TARGET_HEAD_NAME",
    "CvValidationPolicyIdentity",
    "FinalProductionPolicyIdentity",
    "FoundationAdaptationObjectivePolicy",
    "PostSelectionMethodIdentity",
    "PostSelectionMethodPolicies",
    "PostSelectionPreparationPolicy",
    "canonical_post_selection_head_names",
    "compute_replay_lineage_digest",
    "cv_training_budget_policy",
    "final_production_training_budget_policy",
    "resolve_cv_validation_policy_identity",
    "resolve_final_production_policy_identity",
    "resolve_post_selection_foundation_identity",
    "resolve_post_selection_head_names",
    "resolve_post_selection_method_identity",
    "resolve_post_selection_method_policies",
    "resolve_post_selection_device",
    "resolve_post_selection_replay_training_label_mode",
    "resolve_shared_optimizer_settings",
]
