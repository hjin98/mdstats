"""Current target-size statistical experiment authorities.

This module is deliberately unreachable from the campaign runtime until the
atomic cutover.  It defines the one-study statistical graph constructed from
the neutral scientific substrate; training and evaluation execution belong to
the later execution-context owner.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .eligibility import FrameEligibilityState
from .neutral_substrate import (
    CanonicalFrameAuthority,
    NeutralSplitExclusionEvidence,
    NeutralStatisticalBase,
    build_neutral_split_exclusion_evidence,
    project_split_exclusion_constraint_components,
    split_exclusion_component_digest,
)
from .partition import OuterRole

TARGET_SIZE_POLICY_SCHEMA = "mdstats.target-size-scientific-policy.v1"
TARGET_SIZE_POPULATION_SCHEMA = "mdstats.target-size-population.v1"
TARGET_SIZE_POPULATION_FRAME_SCHEMA = "mdstats.target-size-population-frame.v1"
TARGET_SIZE_SPLIT_SCHEMA = "mdstats.target-size-population-split.v1"
TARGET_TRAINING_ORDER_SCHEMA = "mdstats.target-training-order.v1"
TARGET_EVALUATION_ORDER_SCHEMA = "mdstats.target-evaluation-order.v1"
TARGET_SIZE_DEFINITION_SCHEMA = "mdstats.target-size-experiment-definition.v1"
TARGET_SIZE_METRIC_SCHEMA = "mdstats.target-size-boundary-metric.v1"
TARGET_SIZE_FAILURE_SCHEMA = "mdstats.target-size-numerical-failure.v1"
TARGET_SIZE_REDUCER_SCHEMA = "mdstats.target-size-reducer-state.v1"
TARGET_SIZE_AGGREGATE_SCHEMA = "mdstats.target-size-statistical-aggregate.v1"
TARGET_SIZE_HARD_OBLIGATION_SCHEMA = "mdstats.target-size-hard-support-obligation.v1"
TARGET_SIZE_QUALIFICATION_SCHEMA = "mdstats.target-size-candidate-qualification.v1"
TARGET_SIZE_FUNNEL_POLICY_SCHEMA = "mdstats.target-size-funnel.v1"
TARGET_SIZE_FUNNEL_TRANSITION = "q->min(q,4)->2->1"


def _checked_dict_digest(
    payload: Mapping[str, Any], result_digest: str, *, name: str
) -> None:
    supplied = payload.get("content_digest")
    if supplied not in (None, result_digest):
        raise TrainingDataSerializationError(f"{name} digest mismatch.")


# Frozen pre-candidate evidence authorized for hard-support selectors.  Every
# attribute is canonical P1/P2 membership evidence carried by the bound
# population; provenance, CV, candidate, and seed namespaces are deliberately
# absent and are rejected as unknown selectors.
HARD_SUPPORT_CONDITION_ATTRIBUTES = (
    "condition_id",
    "reduced_formula",
    "temperature_condition",
    "strain_class",
    "regime",
)
HARD_SUPPORT_USER_LABEL_PREFIX = "user_label."


@dataclass(frozen=True, slots=True)
class TargetSizeHardSupportObligation:
    """One declarative, serializable hard-support obligation.

    The obligation identifies a support subset using only frozen pre-candidate
    evidence already authorized for P2 ordering/qualification (canonical P1/P2
    condition membership), together with the required minimum membership count.
    Obligation identity never depends on callbacks, object identity, mutable
    runtime state, model predictions, candidate outcomes, CV state, or
    execution results.
    """

    obligation_id: str
    attribute: str
    value: str
    minimum_count: int

    def __post_init__(self) -> None:
        obligation_id = str(self.obligation_id).strip()
        if not obligation_id:
            raise TrainingDataInputError(
                "Hard-support obligation_id must be non-empty."
            )
        attribute = str(self.attribute).strip()
        value = str(self.value)
        if not value.strip():
            raise TrainingDataInputError(
                "Hard-support obligation selector value must be non-empty."
            )
        if attribute in HARD_SUPPORT_CONDITION_ATTRIBUTES:
            pass
        elif attribute.startswith(HARD_SUPPORT_USER_LABEL_PREFIX):
            if not attribute[len(HARD_SUPPORT_USER_LABEL_PREFIX) :].strip():
                raise TrainingDataInputError(
                    "A user_label hard-support selector requires a non-empty label key."
                )
        else:
            raise TrainingDataInputError(
                f"Unknown hard-support selector attribute: {attribute!r}."
            )
        minimum = _positive_int(self.minimum_count, name="minimum_count")
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "attribute", attribute)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "minimum_count", minimum)

    def matches(self, condition_attributes: tuple[tuple[str, str], ...]) -> bool:
        return (str(self.attribute), str(self.value)) in set(condition_attributes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_HARD_OBLIGATION_SCHEMA,
            "obligation_id": self.obligation_id,
            "attribute": self.attribute,
            "value": self.value,
            "minimum_count": self.minimum_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeHardSupportObligation:
        if payload.get("schema") != TARGET_SIZE_HARD_OBLIGATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size hard-support obligation schema."
            )
        result = cls(
            obligation_id=str(payload["obligation_id"]),
            attribute=str(payload["attribute"]),
            value=str(payload["value"]),
            minimum_count=int(payload["minimum_count"]),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size hard-support obligation"
        )
        return result


def _normalize_hard_support_obligations(
    obligations: Sequence[TargetSizeHardSupportObligation | Mapping[str, Any]],
) -> tuple[TargetSizeHardSupportObligation, ...]:
    """Canonical normalization: validated selectors, stable order, no aliases."""

    parsed: list[TargetSizeHardSupportObligation] = []
    for item in obligations:
        if isinstance(item, TargetSizeHardSupportObligation):
            parsed.append(item)
        elif isinstance(item, Mapping):
            try:
                parsed.append(
                    TargetSizeHardSupportObligation(
                        obligation_id=str(item["obligation_id"]),
                        attribute=str(item["attribute"]),
                        value=str(item["value"]),
                        minimum_count=item["minimum_count"],
                    )
                )
            except KeyError as error:
                raise TrainingDataInputError(
                    f"Hard-support obligation is missing required field: {error.args[0]!r}."
                ) from None
        else:
            raise TrainingDataInputError(
                "Hard-support obligations must be declarative mappings."
            )
    by_id: dict[str, TargetSizeHardSupportObligation] = {}
    for obligation in parsed:
        existing = by_id.get(obligation.obligation_id)
        if existing is None:
            by_id[obligation.obligation_id] = obligation
        elif existing == obligation:
            continue
        else:
            raise TrainingDataInputError(
                f"Contradictory hard-support obligations share obligation_id {obligation.obligation_id!r}."
            )
    return tuple(sorted(by_id.values(), key=lambda item: item.obligation_id))


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class ResolvedTargetSizePolicy:
    """Canonical target-size scientific policy; no parser/default state leaks."""

    candidate_sizes: tuple[int, ...] = tuple(2**p for p in range(7, 15))
    evaluation_sizes: tuple[int, int, int] = (256, 512, 1024)
    fidelity_epochs: tuple[int, int, int] = (1, 3, 10)
    optimizer_seeds: tuple[int, ...] = (1, 2)
    paired_seed_aggregation: str = "arithmetic_mean"
    ranking_metric: str = "target_force_rmse_mev_per_a"
    practical_equivalence_mev_per_a: float = 1.0
    training_order_policy: str = "candidate_independent_priority.v1"
    split_policy: str = "training_priority_exact_reserve.v1"
    evaluation_order_policy: str = "candidate_independent_representative.v1"
    hard_support_obligations: tuple[TargetSizeHardSupportObligation, ...] = ()

    def __post_init__(self) -> None:
        sizes = tuple(self.candidate_sizes)
        if any(isinstance(v, bool) or not isinstance(v, int) for v in sizes):
            raise TrainingDataInputError("candidate_sizes must contain integers only.")
        sizes = tuple(int(v) for v in sizes)
        if (
            len(sizes) < 3
            or len(set(sizes)) != len(sizes)
            or tuple(sorted(sizes)) != sizes
        ):
            raise TrainingDataInputError(
                "candidate_sizes must be at least three unique strictly increasing values."
            )
        if any(v <= 0 or v & (v - 1) for v in sizes):
            raise TrainingDataInputError(
                "candidate_sizes must be positive powers of two."
            )
        # q -> min(q,4) -> 2 -> 1 requires at least three candidates.
        evaluation = tuple(self.evaluation_sizes)
        if len(evaluation) != 3 or any(
            isinstance(v, bool) or not isinstance(v, int) for v in evaluation
        ):
            raise TrainingDataInputError(
                "evaluation_sizes must contain exactly three integers."
            )
        evaluation = tuple(int(v) for v in evaluation)
        if not (0 < evaluation[0] < evaluation[1] < evaluation[2]):
            raise TrainingDataInputError(
                "evaluation_sizes must be three unique strictly increasing positive values."
            )
        if any(v & (v - 1) for v in evaluation):
            raise TrainingDataInputError("evaluation_sizes must be powers of two.")
        epochs = tuple(self.fidelity_epochs)
        if len(epochs) != 3 or any(
            isinstance(v, bool) or not isinstance(v, int) for v in epochs
        ):
            raise TrainingDataInputError(
                "fidelity_epochs must contain exactly three integers."
            )
        epochs = tuple(int(v) for v in epochs)
        if not (0 < epochs[0] < epochs[1] < epochs[2]):
            raise TrainingDataInputError(
                "fidelity_epochs must be three strictly increasing positive boundaries."
            )
        seeds = tuple(self.optimizer_seeds)
        if not seeds or any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in seeds
        ):
            raise TrainingDataInputError(
                "optimizer_seeds must be one nonempty ordered set of nonnegative integers."
            )
        seeds = tuple(int(v) for v in seeds)
        if len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "optimizer_seeds must be unique and order-preserving."
            )
        if self.paired_seed_aggregation != "arithmetic_mean":
            raise TrainingDataInputError(
                "Only arithmetic_mean paired-seed aggregation is supported."
            )
        if self.ranking_metric != "target_force_rmse_mev_per_a":
            raise TrainingDataInputError(
                "Only the target-force ranking metric is authorized."
            )
        epsilon = float(self.practical_equivalence_mev_per_a)
        if not math.isfinite(epsilon) or epsilon < 0.0:
            raise TrainingDataInputError(
                "practical_equivalence_mev_per_a must be finite and nonnegative."
            )
        for name in (
            "training_order_policy",
            "split_policy",
            "evaluation_order_policy",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be nonempty.")
        # Canonical normalization participates in policy identity: stable
        # ordering, validated selectors, no contradictory aliases.
        obligations = _normalize_hard_support_obligations(self.hard_support_obligations)
        object.__setattr__(self, "hard_support_obligations", obligations)
        object.__setattr__(self, "candidate_sizes", sizes)
        object.__setattr__(self, "evaluation_sizes", evaluation)
        object.__setattr__(self, "fidelity_epochs", epochs)
        object.__setattr__(self, "optimizer_seeds", seeds)
        object.__setattr__(self, "practical_equivalence_mev_per_a", epsilon)

    @property
    def nmax(self) -> int:
        return self.candidate_sizes[-1]

    @property
    def m1(self) -> int:
        return self.evaluation_sizes[0]

    @property
    def m2(self) -> int:
        return self.evaluation_sizes[1]

    @property
    def m3(self) -> int:
        return self.evaluation_sizes[2]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_POLICY_SCHEMA,
            "candidate_sizes": list(self.candidate_sizes),
            "evaluation_sizes": list(self.evaluation_sizes),
            "fidelity_epochs": list(self.fidelity_epochs),
            "optimizer_seeds": list(self.optimizer_seeds),
            "paired_seed_aggregation": self.paired_seed_aggregation,
            "ranking_metric": self.ranking_metric,
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "training_order_policy": self.training_order_policy,
            "split_policy": self.split_policy,
            "evaluation_order_policy": self.evaluation_order_policy,
            "hard_support_obligations": [
                item.to_dict() for item in self.hard_support_obligations
            ],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def policy_digest(self) -> str:
        return self.content_digest

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResolvedTargetSizePolicy:
        if payload.get("schema") != TARGET_SIZE_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size policy schema."
            )
        result = cls(
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            evaluation_sizes=tuple(int(v) for v in payload["evaluation_sizes"]),
            fidelity_epochs=tuple(int(v) for v in payload["fidelity_epochs"]),
            optimizer_seeds=tuple(int(v) for v in payload["optimizer_seeds"]),
            paired_seed_aggregation=str(payload["paired_seed_aggregation"]),
            ranking_metric=str(payload["ranking_metric"]),
            practical_equivalence_mev_per_a=float(
                payload["practical_equivalence_mev_per_a"]
            ),
            training_order_policy=str(payload["training_order_policy"]),
            split_policy=str(payload["split_policy"]),
            evaluation_order_policy=str(payload["evaluation_order_policy"]),
            hard_support_obligations=tuple(
                TargetSizeHardSupportObligation.from_dict(item)
                for item in payload["hard_support_obligations"]
            ),
        )
        _checked_dict_digest(payload, result.content_digest, name="Target-size policy")
        return result


def resolve_target_size_policy(
    *,
    target_size_power_min: int = 7,
    target_size_power_max: int = 14,
    evaluation_size_powers: Sequence[int] = (8, 9, 10),
    fidelity_epochs: Sequence[int] = (1, 3, 10),
    optimizer_seeds: Sequence[int] = (1, 2),
    ranking_metric: str = "target_force_rmse_mev_per_a",
    practical_equivalence_mev_per_a: float = 1.0,
    training_order_policy: str = "candidate_independent_priority.v1",
    split_policy: str = "training_priority_exact_reserve.v1",
    evaluation_order_policy: str = "candidate_independent_representative.v1",
    hard_support_obligations: Sequence[
        TargetSizeHardSupportObligation | Mapping[str, Any]
    ] = (),
) -> ResolvedTargetSizePolicy:
    pmin = _positive_int(target_size_power_min, name="target_size_power_min")
    pmax = _positive_int(target_size_power_max, name="target_size_power_max")
    if pmin > pmax:
        raise TrainingDataInputError(
            "target_size_power_min cannot exceed target_size_power_max."
        )
    eval_powers = tuple(evaluation_size_powers)
    if len(eval_powers) != 3 or any(
        isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in eval_powers
    ):
        raise TrainingDataInputError(
            "evaluation_size_powers must contain three nonnegative integers."
        )
    return ResolvedTargetSizePolicy(
        candidate_sizes=tuple(2**p for p in range(pmin, pmax + 1)),
        evaluation_sizes=tuple(2 ** int(p) for p in eval_powers),
        fidelity_epochs=tuple(fidelity_epochs),
        optimizer_seeds=tuple(optimizer_seeds),
        ranking_metric=ranking_metric,
        practical_equivalence_mev_per_a=practical_equivalence_mev_per_a,
        training_order_policy=training_order_policy,
        split_policy=split_policy,
        evaluation_order_policy=evaluation_order_policy,
        hard_support_obligations=tuple(hard_support_obligations),
    )


def resolve_target_size_policy_from_config(
    config: Mapping[str, Any],
) -> ResolvedTargetSizePolicy:
    """Resolve only the owning config namespaces into canonical P2 identity.

    CV, replay, projection, bootstrap, monitor, and evaluation-order seeds are
    intentionally never searched.  The ordered seed list of the sole enabled
    training method is the one target-size replicate namespace.
    """

    target_data = config.get("target_data", {})
    if not isinstance(target_data, Mapping):
        raise TrainingDataInputError("[target_data] must be a table.")
    size = target_data.get("size_convergence", {})
    if not isinstance(size, Mapping):
        raise TrainingDataInputError("[target_data.size_convergence] must be a table.")
    if "screening_optimizer_seed" in size or "screening_optimizer_seeds" in size:
        raise TrainingDataInputError(
            "Target-size optimizer seeds belong only to the sole enabled training method."
        )
    training = config.get("training", {})
    if not isinstance(training, Mapping):
        raise TrainingDataInputError("[training] must be a table.")
    method_names = ("naive_fine_tuning", "multihead_replay")
    nested_present = any(
        isinstance(training.get(name), Mapping) for name in method_names
    )
    enabled: list[Mapping[str, Any]] = []
    if nested_present:
        for name in method_names:
            method = training.get(name)
            if method is None:
                continue
            if not isinstance(method, Mapping):
                raise TrainingDataInputError(f"[training.{name}] must be a table.")
            if bool(method.get("enabled", True)):
                enabled.append(method)
    else:
        modes = tuple(str(v) for v in training.get("modes", ("multihead_replay",)))
        if len(modes) == 1:
            enabled.append({"seeds": training.get("seeds", (1, 2))})
        elif modes:
            enabled.extend({"seeds": training.get("seeds", (1, 2))} for _ in modes)
    if len(enabled) != 1:
        raise TrainingDataInputError(
            "Target-size policy requires exactly one enabled training method."
        )
    raw_seeds = enabled[0].get("seeds", (1, 2))
    if not isinstance(raw_seeds, (tuple, list)):
        raise TrainingDataInputError(
            "The enabled training method seeds must be an array."
        )
    raw_evaluation_powers = size.get("evaluation_size_powers", (8, 9, 10))
    raw_fidelity = size.get("fidelity_epochs", (1, 3, 10))
    if not isinstance(raw_evaluation_powers, (tuple, list)):
        raise TrainingDataInputError("evaluation_size_powers must be an array.")
    if not isinstance(raw_fidelity, (tuple, list)):
        raise TrainingDataInputError("fidelity_epochs must be an array.")
    raw_obligations = size.get("hard_support_obligations", ())
    if not isinstance(raw_obligations, (tuple, list)):
        raise TrainingDataInputError(
            "hard_support_obligations must be an array of tables."
        )
    # Validate the production horizon but deliberately exclude it from P2 identity.
    max_epochs = training.get("max_num_epochs", 30)
    _positive_int(max_epochs, name="[training].max_num_epochs")
    return resolve_target_size_policy(
        target_size_power_min=size.get("target_size_power_min", 7),
        target_size_power_max=size.get("target_size_power_max", 14),
        evaluation_size_powers=raw_evaluation_powers,
        fidelity_epochs=raw_fidelity,
        optimizer_seeds=raw_seeds,
        ranking_metric=str(size.get("ranking_metric", "target_force_rmse_mev_per_a")),
        practical_equivalence_mev_per_a=float(
            size.get("practical_equivalence_mev_per_a", 1.0)
        ),
        training_order_policy=str(
            size.get("training_order_policy", "candidate_independent_priority.v1")
        ),
        split_policy=str(
            size.get("split_policy", "training_priority_exact_reserve.v1")
        ),
        evaluation_order_policy=str(
            size.get(
                "evaluation_order_policy", "candidate_independent_representative.v1"
            )
        ),
        hard_support_obligations=tuple(raw_obligations),
    )


@dataclass(frozen=True, slots=True)
class TargetSizePopulationFrame:
    frame_uid: str
    unit_id: str
    condition_id: str
    geometry_fingerprint: str
    canonical_label_payload_digest: str
    frame_record_digest: str
    condition_attributes: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "unit_id",
            "condition_id",
            "geometry_fingerprint",
            "canonical_label_payload_digest",
            "frame_record_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        attributes = tuple(
            sorted((str(key), str(value)) for key, value in self.condition_attributes)
        )
        if not attributes or len(set(key for key, _ in attributes)) != len(attributes):
            raise TrainingDataInputError(
                "Target-size population frame requires unique non-empty condition attributes."
            )
        object.__setattr__(self, "condition_attributes", attributes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_POPULATION_FRAME_SCHEMA,
            "frame_uid": self.frame_uid,
            "unit_id": self.unit_id,
            "condition_id": self.condition_id,
            "geometry_fingerprint": self.geometry_fingerprint,
            "canonical_label_payload_digest": self.canonical_label_payload_digest,
            "frame_record_digest": self.frame_record_digest,
            "condition_attributes": dict(self.condition_attributes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizePopulationFrame:
        if payload.get("schema") != TARGET_SIZE_POPULATION_FRAME_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size population-frame schema."
            )
        result = cls(
            **{
                name: str(payload[name])
                for name in (
                    "frame_uid",
                    "unit_id",
                    "condition_id",
                    "geometry_fingerprint",
                    "canonical_label_payload_digest",
                    "frame_record_digest",
                )
            },
            condition_attributes=tuple(
                (str(key), str(value))
                for key, value in payload["condition_attributes"].items()
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size population frame"
        )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizePopulation:
    dataset_id: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    neutral_unit_catalog_digest: str
    frames: tuple[TargetSizePopulationFrame, ...]
    _by_uid: dict[str, TargetSizePopulationFrame] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "neutral_unit_catalog_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        frames = tuple(sorted(self.frames, key=lambda item: item.frame_uid))
        if not frames or len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError(
                "Target-size population requires unique frames."
            )
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "_by_uid", {item.frame_uid: item for item in frames})

    @property
    def frame_uids(self) -> tuple[str, ...]:
        return tuple(item.frame_uid for item in self.frames)

    def frame(self, frame_uid: str) -> TargetSizePopulationFrame:
        try:
            return self._by_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_POPULATION_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "neutral_unit_catalog_digest": self.neutral_unit_catalog_digest,
            "frames": [item.to_dict() for item in self.frames],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizePopulation:
        if payload.get("schema") != TARGET_SIZE_POPULATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size population schema."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            neutral_statistical_base_digest=str(
                payload["neutral_statistical_base_digest"]
            ),
            neutral_unit_catalog_digest=str(payload["neutral_unit_catalog_digest"]),
            frames=tuple(
                TargetSizePopulationFrame.from_dict(v) for v in payload["frames"]
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size population"
        )
        return result


def build_target_size_population(
    frame_authority: CanonicalFrameAuthority,
    neutral_base: NeutralStatisticalBase,
) -> TargetSizePopulation:
    """Project exact DEVELOPMENT frames from the accepted P1 authorities."""

    if not isinstance(frame_authority, CanonicalFrameAuthority):
        raise TrainingDataInputError(
            "TargetSizePopulation requires CanonicalFrameAuthority."
        )
    if not isinstance(neutral_base, NeutralStatisticalBase):
        raise TrainingDataInputError(
            "TargetSizePopulation requires NeutralStatisticalBase."
        )
    if frame_authority.dataset_id != neutral_base.dataset_id:
        raise TrainingDataInputError(
            "P1 target-size population dataset lineage mismatch."
        )
    catalog = neutral_base.unit_catalog
    if catalog.frame_authority_digest != frame_authority.content_digest:
        raise TrainingDataInputError(
            "Neutral base does not bind the supplied frame authority."
        )
    development = set(
        neutral_base.outer_partition.unit_ids_for_role(OuterRole.DEVELOPMENT)
    )
    result: list[TargetSizePopulationFrame] = []
    for unit in catalog.units:
        if unit.unit_id not in development:
            continue
        condition = unit.condition
        condition_attributes = (
            ("condition_id", condition.condition_id),
            ("reduced_formula", condition.reduced_formula),
            ("temperature_condition", condition.temperature_condition),
            ("strain_class", condition.strain_class),
            ("regime", condition.regime),
        ) + tuple(
            (f"{HARD_SUPPORT_USER_LABEL_PREFIX}{key}", value)
            for key, value in condition.user_labels
        )
        for uid in unit.frame_uids:
            frame = frame_authority.frame(uid)
            decision = frame_authority.eligibility.for_frame(uid)
            if decision.state is not FrameEligibilityState.ELIGIBLE:
                raise TrainingDataInputError(
                    "A non-eligible P1 frame cannot enter U_size."
                )
            if frame.canonical_label_payload_digest is None:
                raise TrainingDataInputError(
                    "A physical-only frame cannot enter U_size."
                )
            result.append(
                TargetSizePopulationFrame(
                    frame_uid=uid,
                    unit_id=unit.unit_id,
                    condition_id=unit.condition.condition_id,
                    geometry_fingerprint=frame.geometry_fingerprint,
                    canonical_label_payload_digest=frame.canonical_label_payload_digest,
                    frame_record_digest=frame.content_digest,
                    condition_attributes=condition_attributes,
                )
            )
    if not result:
        raise TrainingDataInputError(
            "P1 contains no authorized DEVELOPMENT frames for U_size."
        )
    return TargetSizePopulation(
        dataset_id=frame_authority.dataset_id,
        frame_authority_digest=frame_authority.content_digest,
        neutral_statistical_base_digest=neutral_base.content_digest,
        neutral_unit_catalog_digest=catalog.content_digest,
        frames=tuple(result),
    )


def _constraint_components(
    population: TargetSizePopulation,
    split_exclusion_evidence: NeutralSplitExclusionEvidence,
) -> tuple[tuple[str, ...], ...]:
    """Constraint components of this U_size population.

    The transitive-closure projection is the single canonical P1-owned
    implementation; P2 contributes no duplicate component algorithm.
    """

    return project_split_exclusion_constraint_components(
        population.frame_uids,
        split_exclusion_evidence,
        frame_authority_digest=population.frame_authority_digest,
        neutral_unit_catalog_digest=population.neutral_unit_catalog_digest,
    )


@dataclass(frozen=True, slots=True)
class TargetSizePopulationSplit:
    population_digest: str
    policy_digest: str
    split_exclusion_evidence_digest: str
    training_frame_uids: tuple[str, ...]
    evaluation_reserve_frame_uids: tuple[str, ...]
    constraint_component_digests: tuple[str, ...]
    allocation_diagnostics: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for name in (
            "population_digest",
            "policy_digest",
            "split_exclusion_evidence_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        train = tuple(self.training_frame_uids)
        evaluation = tuple(self.evaluation_reserve_frame_uids)
        if len(set(train)) != len(train) or len(set(evaluation)) != len(evaluation):
            raise TrainingDataInputError(
                "Split memberships must contain unique frame UIDs."
            )
        if set(train).intersection(evaluation):
            raise TrainingDataInputError("P_train and M3 must be disjoint.")
        object.__setattr__(self, "training_frame_uids", train)
        object.__setattr__(self, "evaluation_reserve_frame_uids", evaluation)
        object.__setattr__(
            self,
            "constraint_component_digests",
            tuple(self.constraint_component_digests),
        )
        object.__setattr__(
            self,
            "allocation_diagnostics",
            tuple(sorted((str(k), int(v)) for k, v in self.allocation_diagnostics)),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_SPLIT_SCHEMA,
            "population_digest": self.population_digest,
            "policy_digest": self.policy_digest,
            "split_exclusion_evidence_digest": self.split_exclusion_evidence_digest,
            "training_frame_uids": list(self.training_frame_uids),
            "evaluation_reserve_frame_uids": list(self.evaluation_reserve_frame_uids),
            "constraint_component_digests": list(self.constraint_component_digests),
            "allocation_diagnostics": dict(self.allocation_diagnostics),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizePopulationSplit:
        if payload.get("schema") != TARGET_SIZE_SPLIT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size split schema."
            )
        result = cls(
            population_digest=str(payload["population_digest"]),
            policy_digest=str(payload["policy_digest"]),
            split_exclusion_evidence_digest=str(
                payload["split_exclusion_evidence_digest"]
            ),
            training_frame_uids=tuple(str(v) for v in payload["training_frame_uids"]),
            evaluation_reserve_frame_uids=tuple(
                str(v) for v in payload["evaluation_reserve_frame_uids"]
            ),
            constraint_component_digests=tuple(
                str(v) for v in payload["constraint_component_digests"]
            ),
            allocation_diagnostics=tuple(
                (str(k), int(v))
                for k, v in payload.get("allocation_diagnostics", {}).items()
            ),
        )
        _checked_dict_digest(payload, result.content_digest, name="Target-size split")
        return result


def _exact_component_subset(
    components: Sequence[tuple[str, ...]], target: int
) -> tuple[int, ...] | None:
    """Deterministic exact subset-sum with O(component_count * target) state."""

    # Each total stores one predecessor edge.  Retaining a full chosen-index
    # tuple at every total would make the bounded DP state deceptively cubic in
    # path-copy volume for singleton-heavy populations.
    reachable: dict[int, tuple[int, int] | None] = {0: None}
    for index, component in enumerate(components):
        weight = len(component)
        for total in tuple(sorted(reachable, reverse=True)):
            candidate = total + weight
            if candidate <= target and candidate not in reachable:
                reachable[candidate] = (total, index)
        if target in reachable:
            break
    if target not in reachable:
        return None
    chosen: list[int] = []
    total = target
    while total:
        edge = reachable[total]
        if edge is None:  # pragma: no cover - total=0 is the only root
            raise RuntimeError("Corrupt exact-allocation predecessor graph.")
        total, index = edge
        chosen.append(index)
    chosen.reverse()
    return tuple(chosen)


def reference_exact_split_feasible(
    component_sizes: Sequence[int], evaluation_size: int
) -> bool:
    """Bounded exhaustive oracle for adversarial/reference fixtures."""

    sizes = tuple(_positive_int(v, name="component size") for v in component_sizes)
    if len(sizes) > 24:
        raise TrainingDataInputError(
            "Reference split oracle is bounded to 24 components."
        )
    target = _positive_int(evaluation_size, name="evaluation_size")
    sums = {0}
    for size in sizes:
        sums |= {value + size for value in tuple(sums) if value + size <= target}
    return target in sums


def _allocation_component_order(
    population: TargetSizePopulation,
    components: Sequence[tuple[str, ...]],
) -> tuple[tuple[str, ...], ...]:
    """Prefer redundancy while round-robining deterministic condition support."""

    by_uid = {item.frame_uid: item for item in population.frames}
    by_size: dict[int, dict[str, list[tuple[str, ...]]]] = {}
    for component in components:
        condition = min(by_uid[uid].condition_id for uid in component)
        by_size.setdefault(len(component), {}).setdefault(condition, []).append(
            component
        )
    result: list[tuple[str, ...]] = []
    for component_size in sorted(by_size, reverse=True):
        buckets = by_size[component_size]
        for values in buckets.values():
            values.sort()
        queues = {condition: deque(values) for condition, values in buckets.items()}
        while any(queues.values()):
            for condition in sorted(queues):
                if queues[condition]:
                    result.append(queues[condition].popleft())
    return tuple(result)


def split_target_size_population(
    population: TargetSizePopulation,
    policy: ResolvedTargetSizePolicy,
    split_exclusion_evidence: NeutralSplitExclusionEvidence,
) -> TargetSizePopulationSplit:
    """Construct one exact ``U_size -> P_train + M3`` split.

    ``split_exclusion_evidence`` is the one canonical P1 relation input.  The
    complete connected-component closure is built before any allocation, so a
    greedy or partial pre-pass can never allocate before every inherited P1
    protected relation is applied.
    """

    if len(population.frames) < policy.nmax + policy.m3:
        raise TrainingDataInputError(
            f"U_size has {len(population.frames)} configurations; at least {policy.nmax + policy.m3} are required."
        )
    components = _constraint_components(population, split_exclusion_evidence)
    # Prefer redundant/larger components for the reserve, then use exact DP so
    # a failed greedy prefix can never become a false infeasibility verdict.
    ordered = _allocation_component_order(population, components)
    chosen_indices = _exact_component_subset(ordered, policy.m3)
    if chosen_indices is None:
        raise TrainingDataInputError(
            "No exact P_train/M3 allocation satisfies the P1 correlation and duplicate constraints."
        )
    chosen = {uid for index in chosen_indices for uid in ordered[index]}
    evaluation = tuple(sorted(chosen))
    training = tuple(uid for uid in population.frame_uids if uid not in chosen)
    if len(training) < policy.nmax:
        raise TrainingDataInputError(
            "Exact evaluation allocation leaves insufficient training support."
        )
    component_digests = tuple(
        split_exclusion_component_digest(group) for group in components
    )
    return TargetSizePopulationSplit(
        population_digest=population.content_digest,
        policy_digest=policy.content_digest,
        split_exclusion_evidence_digest=split_exclusion_evidence.content_digest,
        training_frame_uids=training,
        evaluation_reserve_frame_uids=evaluation,
        constraint_component_digests=component_digests,
        allocation_diagnostics=(
            ("authorized_configuration_count", len(population.frames)),
            ("constraint_component_count", len(components)),
            ("evaluation_configuration_count", len(evaluation)),
            ("training_configuration_count", len(training)),
        ),
    )


def _normalize_priority_evidence(
    frame_uids: Sequence[str],
    evidence: Mapping[str, Sequence[float] | float] | None,
    *,
    name: str,
) -> tuple[dict[str, tuple[float, ...]], str]:
    expected = set(frame_uids)
    if evidence is None:
        values = {uid: () for uid in frame_uids}
    else:
        if set(evidence) != expected:
            raise TrainingDataInputError(
                f"{name} must cover the bound population exactly."
            )
        values: dict[str, tuple[float, ...]] = {}
        for uid in frame_uids:
            raw = evidence[uid]
            vector = (
                (float(raw),)
                if isinstance(raw, (int, float))
                else tuple(float(v) for v in raw)
            )
            if any(not math.isfinite(value) for value in vector):
                raise TrainingDataInputError(f"{name} must contain finite values.")
            values[uid] = vector
    evidence_digest = digest(
        {
            "schema": "mdstats.candidate-independent-priority-evidence.v1",
            "values": {uid: list(values[uid]) for uid in sorted(values)},
        }
    )
    return values, evidence_digest


def _condition_balanced_order(
    population: TargetSizePopulation,
    frame_uids: Sequence[str],
    values: Mapping[str, tuple[float, ...]],
) -> tuple[str, ...]:
    """One deterministic priority order with condition-support round robin."""

    buckets: dict[str, list[str]] = {}
    for uid in frame_uids:
        buckets.setdefault(population.frame(uid).condition_id, []).append(uid)
    for members in buckets.values():
        members.sort(key=lambda uid: (tuple(-value for value in values[uid]), uid))
    queues = {condition: deque(members) for condition, members in buckets.items()}
    result: list[str] = []
    while any(queues.values()):
        for condition in sorted(queues):
            if queues[condition]:
                result.append(queues[condition].popleft())
    return tuple(result)


def target_training_prefix_digest(
    training_order_digest: str,
    target_size: int,
    frame_uids: Sequence[str],
) -> str:
    """Canonical exact-prefix membership digest shared by every authority
    that binds a ``T_N`` membership (P2 orders and the P3 execution bridge)."""

    return digest(
        {
            "schema": "mdstats.target-training-prefix.v1",
            "training_order_digest": training_order_digest,
            "target_size": int(target_size),
            "frame_uids": list(frame_uids),
        }
    )


@dataclass(frozen=True, slots=True)
class TargetTrainingOrder:
    population_digest: str
    split_digest: str
    policy_digest: str
    selection_evidence_digest: str
    frame_uids: tuple[str, ...]
    diagnostics: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "population_digest",
            "split_digest",
            "policy_digest",
            "selection_evidence_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        values = tuple(self.frame_uids)
        if not values or len(set(values)) != len(values):
            raise TrainingDataInputError(
                "pi_train must be a nonempty exact permutation."
            )
        object.__setattr__(self, "frame_uids", values)
        object.__setattr__(
            self,
            "diagnostics",
            tuple(sorted((str(k), int(v)) for k, v in self.diagnostics)),
        )

    def candidate_membership(self, target_size: int) -> tuple[str, ...]:
        size = _positive_int(target_size, name="target_size")
        if size > len(self.frame_uids):
            raise TrainingDataInputError(
                f"pi_train has no exact prefix of size {size}."
            )
        return self.frame_uids[:size]

    def candidate_digest(self, target_size: int) -> str:
        size = _positive_int(target_size, name="target_size")
        return target_training_prefix_digest(
            self.content_digest, size, self.candidate_membership(size)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_TRAINING_ORDER_SCHEMA,
            "population_digest": self.population_digest,
            "split_digest": self.split_digest,
            "policy_digest": self.policy_digest,
            "selection_evidence_digest": self.selection_evidence_digest,
            "frame_uids": list(self.frame_uids),
            "diagnostics": dict(self.diagnostics),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetTrainingOrder:
        if payload.get("schema") != TARGET_TRAINING_ORDER_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-training-order schema."
            )
        result = cls(
            population_digest=str(payload["population_digest"]),
            split_digest=str(payload["split_digest"]),
            policy_digest=str(payload["policy_digest"]),
            selection_evidence_digest=str(payload["selection_evidence_digest"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            diagnostics=tuple(
                (str(k), int(v)) for k, v in payload.get("diagnostics", {}).items()
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target training order"
        )
        return result


def build_target_training_order(
    population: TargetSizePopulation,
    split: TargetSizePopulationSplit,
    policy: ResolvedTargetSizePolicy,
    *,
    selection_evidence: Mapping[str, Sequence[float] | float] | None = None,
) -> TargetTrainingOrder:
    if (
        split.population_digest != population.content_digest
        or split.policy_digest != policy.content_digest
    ):
        raise TrainingDataInputError("Target-training order parent lineage mismatch.")
    values, evidence_digest = _normalize_priority_evidence(
        split.training_frame_uids, selection_evidence, name="selection_evidence"
    )
    # Larger priority coordinates sort first.  The frame UID supplies the one
    # stable final tie breaker and avoids any per-domain/seed/CV fanout.
    order = _condition_balanced_order(population, split.training_frame_uids, values)
    return TargetTrainingOrder(
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        policy_digest=policy.content_digest,
        selection_evidence_digest=evidence_digest,
        frame_uids=order,
        diagnostics=(("ordered_configuration_count", len(order)),),
    )


@dataclass(frozen=True, slots=True)
class TargetEvaluationOrder:
    population_digest: str
    split_digest: str
    policy_digest: str
    ordering_evidence_digest: str
    frame_uids: tuple[str, ...]
    diagnostics: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "population_digest",
            "split_digest",
            "policy_digest",
            "ordering_evidence_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        values = tuple(self.frame_uids)
        if not values or len(set(values)) != len(values):
            raise TrainingDataInputError(
                "pi_eval must be a nonempty exact permutation."
            )
        object.__setattr__(self, "frame_uids", values)
        object.__setattr__(
            self,
            "diagnostics",
            tuple(sorted((str(k), int(v)) for k, v in self.diagnostics)),
        )

    def membership(self, evaluation_size: int) -> tuple[str, ...]:
        size = _positive_int(evaluation_size, name="evaluation_size")
        if size > len(self.frame_uids):
            raise TrainingDataInputError(f"pi_eval has no exact prefix of size {size}.")
        return self.frame_uids[:size]

    def membership_digest(self, evaluation_size: int) -> str:
        size = _positive_int(evaluation_size, name="evaluation_size")
        return digest(
            {
                "schema": "mdstats.target-evaluation-prefix.v1",
                "evaluation_order_digest": self.content_digest,
                "evaluation_size": size,
                "frame_uids": list(self.membership(size)),
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_EVALUATION_ORDER_SCHEMA,
            "population_digest": self.population_digest,
            "split_digest": self.split_digest,
            "policy_digest": self.policy_digest,
            "ordering_evidence_digest": self.ordering_evidence_digest,
            "frame_uids": list(self.frame_uids),
            "diagnostics": dict(self.diagnostics),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetEvaluationOrder:
        if payload.get("schema") != TARGET_EVALUATION_ORDER_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-evaluation-order schema."
            )
        result = cls(
            population_digest=str(payload["population_digest"]),
            split_digest=str(payload["split_digest"]),
            policy_digest=str(payload["policy_digest"]),
            ordering_evidence_digest=str(payload["ordering_evidence_digest"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            diagnostics=tuple(
                (str(k), int(v)) for k, v in payload.get("diagnostics", {}).items()
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target evaluation order"
        )
        return result


def build_target_evaluation_order(
    population: TargetSizePopulation,
    split: TargetSizePopulationSplit,
    policy: ResolvedTargetSizePolicy,
    *,
    ordering_evidence: Mapping[str, Sequence[float] | float] | None = None,
) -> TargetEvaluationOrder:
    if (
        split.population_digest != population.content_digest
        or split.policy_digest != policy.content_digest
    ):
        raise TrainingDataInputError("Target-evaluation order parent lineage mismatch.")
    values, evidence_digest = _normalize_priority_evidence(
        split.evaluation_reserve_frame_uids,
        ordering_evidence,
        name="ordering_evidence",
    )
    order = _condition_balanced_order(
        population, split.evaluation_reserve_frame_uids, values
    )
    if len(order) != policy.m3:
        raise TrainingDataInputError("pi_eval must cover the exact M3 reserve.")
    return TargetEvaluationOrder(
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        policy_digest=policy.content_digest,
        ordering_evidence_digest=evidence_digest,
        frame_uids=order,
        diagnostics=(("ordered_configuration_count", len(order)),),
    )


@dataclass(frozen=True, slots=True)
class TargetSizeCandidateQualification:
    """Derived per-N qualification evidence for one exact candidate prefix.

    Qualification is exactly:

        qualified(N) = prefix_exists(N)
                       AND labels_training_usable(T_N)
                       AND all_configured_hard_support_obligations_satisfied(T_N)

    It never reorders, repairs, swaps, or constructs a different prefix, and it
    never depends on optimizer seed results, evaluation outcomes, survivor
    state, selection diagnostics, or P3 runtime accidents.  Persisted
    qualification evidence is derived/checkable state, not an editable
    authority.
    """

    target_size: int
    prefix_exists: bool
    labels_training_usable: bool
    obligation_counts: tuple[tuple[str, int], ...]
    unsatisfied_obligation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_size", _positive_int(self.target_size, name="target_size")
        )
        if not self.prefix_exists:
            raise TrainingDataInputError(
                "Qualification evidence is only defined for an existing exact prefix."
            )
        if not self.labels_training_usable:
            raise TrainingDataInputError(
                "A prefix with unusable training labels cannot carry qualification counts."
            )
        object.__setattr__(
            self,
            "obligation_counts",
            tuple(sorted((str(k), int(v)) for k, v in self.obligation_counts)),
        )
        object.__setattr__(
            self,
            "unsatisfied_obligation_ids",
            tuple(str(v) for v in self.unsatisfied_obligation_ids),
        )

    @property
    def qualified(self) -> bool:
        return not self.unsatisfied_obligation_ids

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_QUALIFICATION_SCHEMA,
            "target_size": self.target_size,
            "prefix_exists": self.prefix_exists,
            "labels_training_usable": self.labels_training_usable,
            "obligation_counts": dict(self.obligation_counts),
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCandidateQualification:
        if payload.get("schema") != TARGET_SIZE_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size qualification schema."
            )
        result = cls(
            target_size=int(payload["target_size"]),
            prefix_exists=bool(payload["prefix_exists"]),
            labels_training_usable=bool(payload["labels_training_usable"]),
            obligation_counts=tuple(
                (str(k), int(v)) for k, v in payload["obligation_counts"].items()
            ),
            unsatisfied_obligation_ids=tuple(
                str(v) for v in payload["unsatisfied_obligation_ids"]
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size qualification"
        )
        return result


def qualify_target_size_candidates(
    population: TargetSizePopulation,
    training_order: TargetTrainingOrder,
    policy: ResolvedTargetSizePolicy,
) -> tuple[TargetSizeCandidateQualification, ...]:
    """Qualify each configured exact prefix under the resolved policy.

    Only explicitly configured hard-support obligations gate a prefix.
    Coverage, novelty, residual, balance, and other diagnostics remain
    ordering/observational evidence and never enter this decision.
    """

    by_uid = population._by_uid
    result: list[TargetSizeCandidateQualification] = []
    for size in policy.candidate_sizes:
        if size > len(training_order.frame_uids):
            raise TrainingDataInputError(
                f"pi_train has no exact prefix of size {size}."
            )
        prefix = training_order.candidate_membership(size)
        labels_usable = all(
            uid in by_uid and by_uid[uid].canonical_label_payload_digest is not None
            for uid in prefix
        )
        if not labels_usable:
            raise TrainingDataInputError(
                "A configured candidate prefix contains frames without usable canonical labels."
            )
        counts: list[tuple[str, int]] = []
        unsatisfied: list[str] = []
        for obligation in policy.hard_support_obligations:
            matched = sum(
                1
                for uid in prefix
                if obligation.matches(by_uid[uid].condition_attributes)
            )
            counts.append((obligation.obligation_id, matched))
            if matched < obligation.minimum_count:
                unsatisfied.append(obligation.obligation_id)
        result.append(
            TargetSizeCandidateQualification(
                target_size=size,
                prefix_exists=True,
                labels_training_usable=labels_usable,
                obligation_counts=tuple(counts),
                unsatisfied_obligation_ids=tuple(unsatisfied),
            )
        )
    return tuple(result)


REQUIRED_QUALIFIED_CANDIDATE_COUNT = 3


@dataclass(frozen=True, slots=True)
class TargetSizeExperimentDefinition:
    dataset_id: str
    population_digest: str
    policy: ResolvedTargetSizePolicy
    split_digest: str
    training_order: TargetTrainingOrder
    evaluation_order: TargetEvaluationOrder
    candidate_membership_digests: tuple[tuple[int, str], ...]
    evaluation_membership_digests: tuple[tuple[int, str], ...]
    candidate_qualification: tuple[TargetSizeCandidateQualification, ...]

    def __post_init__(self) -> None:
        for name in ("population_digest", "split_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.training_order.policy_digest != self.policy.content_digest:
            raise TrainingDataInputError(
                "Training order and target-size policy differ."
            )
        if self.evaluation_order.policy_digest != self.policy.content_digest:
            raise TrainingDataInputError(
                "Evaluation order and target-size policy differ."
            )
        if (
            self.training_order.split_digest != self.split_digest
            or self.evaluation_order.split_digest != self.split_digest
        ):
            raise TrainingDataInputError("Experiment order/split lineage mismatch.")
        candidates = tuple(
            (int(size), validate_digest(value, name="candidate membership digest"))
            for size, value in self.candidate_membership_digests
        )
        evaluations = tuple(
            (int(size), validate_digest(value, name="evaluation membership digest"))
            for size, value in self.evaluation_membership_digests
        )
        expected_candidates = tuple(
            (size, self.training_order.candidate_digest(size))
            for size in self.policy.candidate_sizes
        )
        expected_evaluations = tuple(
            (size, self.evaluation_order.membership_digest(size))
            for size in self.policy.evaluation_sizes
        )
        if candidates != expected_candidates:
            raise TrainingDataInputError(
                "T_N memberships do not match exact pi_train prefixes."
            )
        if evaluations != expected_evaluations:
            raise TrainingDataInputError(
                "M ladder memberships do not match exact pi_eval prefixes."
            )
        object.__setattr__(self, "candidate_membership_digests", candidates)
        object.__setattr__(self, "evaluation_membership_digests", evaluations)
        object.__setattr__(self, "candidate_qualification", tuple(self.candidate_qualification))

    @property
    def funnel_policy(self) -> dict[str, str]:
        """Version-agnostic, fidelity-agnostic funnel transition identity.

        The configured ``fidelity_epochs`` tuple remains the sole scientific
        identity of the configured boundary values; this schema name must never
        encode a historical fidelity ladder.
        """
        return {
            "schema": TARGET_SIZE_FUNNEL_POLICY_SCHEMA,
            "transition": TARGET_SIZE_FUNNEL_TRANSITION,
        }

    @property
    def qualified_candidate_sizes(self) -> tuple[int, ...]:
        return tuple(
            item.target_size
            for item in self.candidate_qualification
            if item.qualified
        )

    def qualification(self, target_size: int) -> TargetSizeCandidateQualification:
        for item in self.candidate_qualification:
            if item.target_size == target_size:
                return item
        raise TrainingDataInputError(
            "Target size is outside the configured candidate universe."
        )

    def candidate_membership(self, target_size: int) -> tuple[str, ...]:
        if target_size not in self.policy.candidate_sizes:
            raise TrainingDataInputError(
                "Target size is outside the configured candidate universe."
            )
        return self.training_order.candidate_membership(target_size)

    def evaluation_membership(self, evaluation_size: int) -> tuple[str, ...]:
        if evaluation_size not in self.policy.evaluation_sizes:
            raise TrainingDataInputError(
                "Evaluation size is outside the configured M ladder."
            )
        return self.evaluation_order.membership(evaluation_size)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_DEFINITION_SCHEMA,
            "dataset_id": self.dataset_id,
            "population_digest": self.population_digest,
            "policy": self.policy.to_dict(),
            "split_digest": self.split_digest,
            "training_order": self.training_order.to_dict(),
            "evaluation_order": self.evaluation_order.to_dict(),
            "funnel_policy": self.funnel_policy,
            "candidate_qualification": [
                item.to_dict() for item in self.candidate_qualification
            ],
            "candidate_membership_digests": {
                str(k): v for k, v in self.candidate_membership_digests
            },
            "evaluation_membership_digests": {
                str(k): v for k, v in self.evaluation_membership_digests
            },
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeExperimentDefinition:
        if payload.get("schema") != TARGET_SIZE_DEFINITION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size experiment schema."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            population_digest=str(payload["population_digest"]),
            policy=ResolvedTargetSizePolicy.from_dict(payload["policy"]),
            split_digest=str(payload["split_digest"]),
            training_order=TargetTrainingOrder.from_dict(payload["training_order"]),
            evaluation_order=TargetEvaluationOrder.from_dict(
                payload["evaluation_order"]
            ),
            candidate_membership_digests=tuple(
                sorted(
                    (int(k), str(v))
                    for k, v in payload["candidate_membership_digests"].items()
                )
            ),
            evaluation_membership_digests=tuple(
                sorted(
                    (int(k), str(v))
                    for k, v in payload["evaluation_membership_digests"].items()
                )
            ),
            candidate_qualification=tuple(
                TargetSizeCandidateQualification.from_dict(item)
                for item in payload["candidate_qualification"]
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size experiment definition"
        )
        return result


def build_target_size_experiment_definition(
    population: TargetSizePopulation,
    split: TargetSizePopulationSplit,
    training_order: TargetTrainingOrder,
    evaluation_order: TargetEvaluationOrder,
    policy: ResolvedTargetSizePolicy,
) -> TargetSizeExperimentDefinition:
    expected_train = set(split.training_frame_uids)
    expected_eval = set(split.evaluation_reserve_frame_uids)
    if set(training_order.frame_uids) != expected_train or len(
        training_order.frame_uids
    ) != len(expected_train):
        raise TrainingDataInputError("pi_train is not an exact permutation of P_train.")
    if set(evaluation_order.frame_uids) != expected_eval or len(
        evaluation_order.frame_uids
    ) != len(expected_eval):
        raise TrainingDataInputError("pi_eval is not an exact permutation of M3.")
    if expected_train.intersection(expected_eval):
        raise TrainingDataInputError(
            "Target training and evaluation populations overlap."
        )
    qualification = qualify_target_size_candidates(population, training_order, policy)
    qualified_sizes = tuple(item.target_size for item in qualification if item.qualified)
    if len(qualified_sizes) < REQUIRED_QUALIFIED_CANDIDATE_COUNT:
        raise TrainingDataInputError(
            "Hard-support qualification leaves "
            f"{len(qualified_sizes)} qualified candidate(s) {list(qualified_sizes)}; "
            f"the {TARGET_SIZE_FUNNEL_TRANSITION} funnel requires at least "
            f"{REQUIRED_QUALIFIED_CANDIDATE_COUNT} qualified candidate sizes."
        )
    return TargetSizeExperimentDefinition(
        dataset_id=population.dataset_id,
        population_digest=population.content_digest,
        policy=policy,
        split_digest=split.content_digest,
        training_order=training_order,
        evaluation_order=evaluation_order,
        candidate_membership_digests=tuple(
            (size, training_order.candidate_digest(size))
            for size in policy.candidate_sizes
        ),
        evaluation_membership_digests=tuple(
            (size, evaluation_order.membership_digest(size))
            for size in policy.evaluation_sizes
        ),
        candidate_qualification=qualification,
    )


class ReducerStatus(str, Enum):
    AWAITING_EXECUTION_CONTEXT = "awaiting_execution_context"
    AWAITING_FIRST_BOUNDARY = "awaiting_first_boundary"
    AWAITING_SECOND_BOUNDARY = "awaiting_second_boundary"
    AWAITING_TERMINAL_BOUNDARY = "awaiting_terminal_boundary"
    SELECTED = "selected"
    NONCONVERGED_AT_CONFIGURED_CEILING = "nonconverged_at_configured_ceiling"
    INSUFFICIENT_COMPARISON = "insufficient_comparison"


_TERMINAL_REDUCER_STATUSES = frozenset(
    {
        ReducerStatus.SELECTED,
        ReducerStatus.NONCONVERGED_AT_CONFIGURED_CEILING,
        ReducerStatus.INSUFFICIENT_COMPARISON,
    }
)


class NumericalFailureKind(str, Enum):
    TRAIN_NONFINITE_MODEL_STATE = "train_nonfinite_model_state"
    TRAIN_NONFINITE_OPTIMIZER_STATE = "train_nonfinite_optimizer_state"
    EVAL_NONFINITE_PREDICTION = "eval_nonfinite_prediction"
    EVAL_NONFINITE_TARGET_METRIC = "eval_nonfinite_target_metric"


@dataclass(frozen=True, slots=True)
class TargetSizeBoundaryMetric:
    experiment_definition_digest: str
    execution_context_digest: str
    target_size: int
    optimizer_seed: int
    boundary_epoch: int
    evaluation_membership_digest: str
    target_force_rmse_mev_per_a: float

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "execution_context_digest",
            "evaluation_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        object.__setattr__(
            self, "target_size", _positive_int(self.target_size, name="target_size")
        )
        if (
            isinstance(self.optimizer_seed, bool)
            or not isinstance(self.optimizer_seed, int)
            or self.optimizer_seed < 0
        ):
            raise TrainingDataInputError(
                "optimizer_seed must be a nonnegative integer."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        object.__setattr__(
            self,
            "boundary_epoch",
            _positive_int(self.boundary_epoch, name="boundary_epoch"),
        )
        score = float(self.target_force_rmse_mev_per_a)
        if not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError(
                "Target-force metric must be finite and nonnegative."
            )
        object.__setattr__(self, "target_force_rmse_mev_per_a", score)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_METRIC_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "target_force_rmse_mev_per_a": self.target_force_rmse_mev_per_a,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeBoundaryMetric:
        if payload.get("schema") != TARGET_SIZE_METRIC_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size boundary metric schema."
            )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=str(payload["execution_context_digest"]),
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_membership_digest=str(payload["evaluation_membership_digest"]),
            target_force_rmse_mev_per_a=float(payload["target_force_rmse_mev_per_a"]),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size boundary metric"
        )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeNumericalFailure:
    experiment_definition_digest: str
    execution_context_digest: str
    target_size: int
    optimizer_seed: int
    boundary_epoch: int
    evaluation_membership_digest: str
    kind: NumericalFailureKind
    classification_evidence_digest: str

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "execution_context_digest",
            "evaluation_membership_digest",
            "classification_evidence_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        object.__setattr__(
            self, "target_size", _positive_int(self.target_size, name="target_size")
        )
        if (
            isinstance(self.optimizer_seed, bool)
            or not isinstance(self.optimizer_seed, int)
            or self.optimizer_seed < 0
        ):
            raise TrainingDataInputError(
                "optimizer_seed must be a nonnegative integer."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        object.__setattr__(
            self,
            "boundary_epoch",
            _positive_int(self.boundary_epoch, name="boundary_epoch"),
        )
        try:
            kind = NumericalFailureKind(self.kind)
        except ValueError:
            raise TrainingDataInputError(
                "Only authenticated TRAIN2/EVAL2 numerical failure kinds are reducer evidence."
            ) from None
        object.__setattr__(self, "kind", kind)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_FAILURE_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "kind": self.kind.value,
            "classification_evidence_digest": self.classification_evidence_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeNumericalFailure:
        if payload.get("schema") != TARGET_SIZE_FAILURE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size numerical-failure schema."
            )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=str(payload["execution_context_digest"]),
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_membership_digest=str(payload["evaluation_membership_digest"]),
            kind=NumericalFailureKind(payload["kind"]),
            classification_evidence_digest=str(
                payload["classification_evidence_digest"]
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size numerical failure"
        )
        return result


BoundaryOutcome = TargetSizeBoundaryMetric | TargetSizeNumericalFailure


@dataclass(frozen=True, slots=True)
class TargetSizeReducerState:
    experiment_definition_digest: str
    execution_context_digest: str | None
    status: ReducerStatus
    active_candidate_sizes: tuple[int, ...]
    completed_boundary_epochs: tuple[int, ...] = ()
    outcome_history: tuple[BoundaryOutcome, ...] = ()
    selected_target_size: int | None = None
    selected_membership_digest: str | None = None
    terminal_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "experiment_definition_digest",
            validate_digest(
                self.experiment_definition_digest, name="experiment_definition_digest"
            ),
        )
        if self.execution_context_digest is not None:
            object.__setattr__(
                self,
                "execution_context_digest",
                validate_digest(
                    self.execution_context_digest, name="execution_context_digest"
                ),
            )
        status = ReducerStatus(self.status)
        sizes = tuple(int(v) for v in self.active_candidate_sizes)
        if (
            len(set(sizes)) != len(sizes)
            or tuple(sorted(sizes)) != sizes
            or any(v <= 0 for v in sizes)
        ):
            raise TrainingDataInputError(
                "Reducer active candidates must be unique increasing sizes."
            )
        epochs = tuple(int(v) for v in self.completed_boundary_epochs)
        if (
            len(set(epochs)) != len(epochs)
            or tuple(sorted(epochs)) != epochs
            or any(v <= 0 for v in epochs)
        ):
            raise TrainingDataInputError(
                "Completed reducer boundaries must be unique increasing epochs."
            )
        if (
            status is ReducerStatus.AWAITING_EXECUTION_CONTEXT
            and self.execution_context_digest is not None
        ):
            raise TrainingDataInputError(
                "Unbound reducer state cannot carry execution context."
            )
        if (
            status is not ReducerStatus.AWAITING_EXECUTION_CONTEXT
            and self.execution_context_digest is None
        ):
            raise TrainingDataInputError(
                "Reducer transitions require an explicit execution context."
            )
        if status is ReducerStatus.SELECTED:
            if (
                self.selected_target_size is None
                or self.selected_membership_digest is None
            ):
                raise TrainingDataInputError(
                    "Selected reducer state requires N_selected and T_selected identity."
                )
            object.__setattr__(
                self,
                "selected_membership_digest",
                validate_digest(
                    self.selected_membership_digest, name="selected_membership_digest"
                ),
            )
        elif (
            self.selected_target_size is not None
            or self.selected_membership_digest is not None
        ):
            raise TrainingDataInputError(
                "Non-selected state cannot fabricate selected target data."
            )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "active_candidate_sizes", sizes)
        object.__setattr__(self, "completed_boundary_epochs", epochs)
        object.__setattr__(self, "outcome_history", tuple(self.outcome_history))
        object.__setattr__(
            self,
            "terminal_reason_codes",
            tuple(str(v) for v in self.terminal_reason_codes),
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_REDUCER_STATUSES

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_REDUCER_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "status": self.status.value,
            "active_candidate_sizes": list(self.active_candidate_sizes),
            "completed_boundary_epochs": list(self.completed_boundary_epochs),
            "outcome_history": [item.to_dict() for item in self.outcome_history],
            "selected_target_size": self.selected_target_size,
            "selected_membership_digest": self.selected_membership_digest,
            "terminal_reason_codes": list(self.terminal_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeReducerState:
        if payload.get("schema") != TARGET_SIZE_REDUCER_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size reducer schema."
            )
        history: list[BoundaryOutcome] = []
        for item in payload.get("outcome_history", ()):
            if item.get("schema") == TARGET_SIZE_METRIC_SCHEMA:
                history.append(TargetSizeBoundaryMetric.from_dict(item))
            elif item.get("schema") == TARGET_SIZE_FAILURE_SCHEMA:
                history.append(TargetSizeNumericalFailure.from_dict(item))
            else:
                raise TrainingDataSerializationError(
                    "Unsupported target-size outcome schema."
                )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=(
                None
                if payload.get("execution_context_digest") is None
                else str(payload["execution_context_digest"])
            ),
            status=ReducerStatus(payload["status"]),
            active_candidate_sizes=tuple(
                int(v) for v in payload["active_candidate_sizes"]
            ),
            completed_boundary_epochs=tuple(
                int(v) for v in payload.get("completed_boundary_epochs", ())
            ),
            outcome_history=tuple(history),
            selected_target_size=(
                None
                if payload.get("selected_target_size") is None
                else int(payload["selected_target_size"])
            ),
            selected_membership_digest=(
                None
                if payload.get("selected_membership_digest") is None
                else str(payload["selected_membership_digest"])
            ),
            terminal_reason_codes=tuple(
                str(v) for v in payload.get("terminal_reason_codes", ())
            ),
        )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size reducer state"
        )
        return result


def initial_target_size_reducer(
    definition: TargetSizeExperimentDefinition,
) -> TargetSizeReducerState:
    active = definition.qualified_candidate_sizes
    if not active:
        raise TrainingDataInputError(
            "A target-size experiment requires at least one qualified candidate size."
        )
    return TargetSizeReducerState(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=None,
        status=ReducerStatus.AWAITING_EXECUTION_CONTEXT,
        active_candidate_sizes=active,
    )


def bind_target_size_execution_context(
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    execution_context_digest: str,
) -> TargetSizeReducerState:
    context = validate_digest(execution_context_digest, name="execution_context_digest")
    if state.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError("Reducer/definition lineage mismatch.")
    if state.status is not ReducerStatus.AWAITING_EXECUTION_CONTEXT:
        if state.execution_context_digest != context:
            raise TrainingDataInputError("Execution context is immutable once bound.")
        return state
    return replace(
        state,
        execution_context_digest=context,
        status=ReducerStatus.AWAITING_FIRST_BOUNDARY,
    )


def _boundary_index(status: ReducerStatus) -> int:
    mapping = {
        ReducerStatus.AWAITING_FIRST_BOUNDARY: 0,
        ReducerStatus.AWAITING_SECOND_BOUNDARY: 1,
        ReducerStatus.AWAITING_TERMINAL_BOUNDARY: 2,
    }
    try:
        return mapping[status]
    except KeyError:
        raise TrainingDataInputError(
            f"Reducer state {status.value!r} does not accept boundary evidence."
        ) from None


def _equivalence_order(scores: Mapping[int, float], epsilon: float) -> tuple[int, ...]:
    remaining = dict(scores)
    ordered: list[int] = []
    while remaining:
        best = min(remaining.values())
        equivalent = [
            size
            for size, score in remaining.items()
            if score <= best + epsilon + 1.0e-12
        ]
        winner = min(equivalent)
        ordered.append(winner)
        del remaining[winner]
    return tuple(ordered)


def advance_target_size_reducer(
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    outcomes: Sequence[BoundaryOutcome],
) -> TargetSizeReducerState:
    """Apply one complete exact-boundary outcome matrix to the pure reducer."""

    if state.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError("Reducer/definition lineage mismatch.")
    qualified = definition.qualified_candidate_sizes
    unqualified_sizes = sorted(
        {item.target_size for item in outcomes if item.target_size not in qualified}
    )
    if unqualified_sizes:
        raise TrainingDataInputError(
            "Boundary evidence targets unqualified candidate size(s) "
            f"{unqualified_sizes}; only qualified configured sizes "
            f"{list(qualified)} may enter ordinary funnel execution."
        )
    index = _boundary_index(state.status)
    policy = definition.policy
    epoch = policy.fidelity_epochs[index]
    evaluation_size = policy.evaluation_sizes[index]
    evaluation_digest = definition.evaluation_order.membership_digest(evaluation_size)
    expected_keys = tuple(
        (size, seed)
        for size in state.active_candidate_sizes
        for seed in policy.optimizer_seeds
    )
    observed: dict[tuple[int, int], BoundaryOutcome] = {}
    invalid_reason: str | None = None
    for item in outcomes:
        key = (item.target_size, item.optimizer_seed)
        if key in observed:
            invalid_reason = "duplicate_boundary_outcome"
            break
        observed[key] = item
        if (
            item.experiment_definition_digest != definition.content_digest
            or item.execution_context_digest != state.execution_context_digest
            or item.boundary_epoch != epoch
            or item.evaluation_membership_digest != evaluation_digest
        ):
            invalid_reason = "outcome_lineage_or_boundary_mismatch"
            break
    if invalid_reason is None and tuple(observed) != expected_keys:
        # Insertion order is authenticated: silently reordering a seed matrix is
        # forbidden even if the same mathematical keys are present.
        invalid_reason = "missing_reordered_or_foreign_seed_population"
    if invalid_reason is not None:
        return TargetSizeReducerState(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            status=ReducerStatus.INSUFFICIENT_COMPARISON,
            active_candidate_sizes=(),
            completed_boundary_epochs=state.completed_boundary_epochs + (epoch,),
            outcome_history=state.outcome_history + tuple(outcomes),
            terminal_reason_codes=(invalid_reason,),
        )

    scores: dict[int, float] = {}
    successful_sizes: list[int] = []
    for size in state.active_candidate_sizes:
        per_seed = [observed[(size, seed)] for seed in policy.optimizer_seeds]
        if all(isinstance(item, TargetSizeBoundaryMetric) for item in per_seed):
            scores[size] = sum(
                item.target_force_rmse_mev_per_a for item in per_seed
            ) / len(per_seed)
            successful_sizes.append(size)
        # Any authenticated numerical failure eliminates that candidate; a
        # mixed success/failure seed population is never averaged over a subset.

    required = min(len(state.active_candidate_sizes), 4) if index == 0 else 2
    if index == 2:
        required = 2
    if len(successful_sizes) < required:
        return TargetSizeReducerState(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            status=ReducerStatus.INSUFFICIENT_COMPARISON,
            active_candidate_sizes=(),
            completed_boundary_epochs=state.completed_boundary_epochs + (epoch,),
            outcome_history=state.outcome_history + tuple(outcomes),
            terminal_reason_codes=("too_few_complete_comparable_candidates",),
        )
    ranking = _equivalence_order(scores, policy.practical_equivalence_mev_per_a)
    history = state.outcome_history + tuple(outcomes)
    completed = state.completed_boundary_epochs + (epoch,)
    if index == 0:
        survivors = tuple(sorted(ranking[: min(len(ranking), 4)]))
        return TargetSizeReducerState(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            status=ReducerStatus.AWAITING_SECOND_BOUNDARY,
            active_candidate_sizes=survivors,
            completed_boundary_epochs=completed,
            outcome_history=history,
        )
    if index == 1:
        finalists = tuple(sorted(ranking[:2]))
        return TargetSizeReducerState(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            status=ReducerStatus.AWAITING_TERMINAL_BOUNDARY,
            active_candidate_sizes=finalists,
            completed_boundary_epochs=completed,
            outcome_history=history,
        )
    largest = policy.nmax
    if largest in scores and all(
        scores[largest] + policy.practical_equivalence_mev_per_a + 1.0e-12 < score
        for size, score in scores.items()
        if size != largest
    ):
        return TargetSizeReducerState(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            status=ReducerStatus.NONCONVERGED_AT_CONFIGURED_CEILING,
            active_candidate_sizes=(),
            completed_boundary_epochs=completed,
            outcome_history=history,
            terminal_reason_codes=("configured_ceiling_materially_superior",),
        )
    winner = ranking[0]
    return TargetSizeReducerState(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=state.execution_context_digest,
        status=ReducerStatus.SELECTED,
        active_candidate_sizes=(),
        completed_boundary_epochs=completed,
        outcome_history=history,
        selected_target_size=winner,
        selected_membership_digest=definition.training_order.candidate_digest(winner),
    )


def _evidence_items(
    frame_uids: Sequence[str],
    evidence: Mapping[str, Sequence[float] | float] | None,
    *,
    name: str,
) -> tuple[tuple[str, tuple[float, ...]], ...]:
    values, _ = _normalize_priority_evidence(frame_uids, evidence, name=name)
    return tuple((uid, values[uid]) for uid in sorted(values))


def _evidence_mapping(
    values: Sequence[tuple[str, Sequence[float]]],
) -> dict[str, tuple[float, ...]]:
    return {str(uid): tuple(float(v) for v in vector) for uid, vector in values}


def target_size_active_boundary_index(status: ReducerStatus) -> int:
    """Public accessor for the active boundary index of a reducer state.

    P3 orchestration derives the active screen boundary only from P2 reducer
    authority; it never recomputes or tracks an independent index.
    """

    return _boundary_index(status)


def validate_target_size_reducer_state(
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
) -> None:
    """Replay the reducer history through the real transition owner."""

    if state.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Reducer state binds a different experiment definition."
        )
    rebuilt = initial_target_size_reducer(definition)
    if state.execution_context_digest is None:
        if state.content_digest != rebuilt.content_digest:
            raise TrainingDataInputError(
                "Unbound reducer state is not the canonical initial state."
            )
        return
    rebuilt = bind_target_size_execution_context(
        definition, rebuilt, state.execution_context_digest
    )
    cursor = 0
    completed_epochs = state.completed_boundary_epochs
    for boundary_position, epoch in enumerate(completed_epochs):
        if rebuilt.is_terminal:
            raise TrainingDataInputError(
                "Reducer history continues after terminal state."
            )
        if boundary_position == len(completed_epochs) - 1:
            batch = state.outcome_history[cursor:]
        else:
            count = len(rebuilt.active_candidate_sizes) * len(
                definition.policy.optimizer_seeds
            )
            batch = state.outcome_history[cursor : cursor + count]
        if not batch and state.status is not ReducerStatus.INSUFFICIENT_COMPARISON:
            raise TrainingDataInputError("Reducer history is incomplete.")
        rebuilt = advance_target_size_reducer(definition, rebuilt, batch)
        cursor += len(batch)
    if cursor != len(state.outcome_history):
        raise TrainingDataInputError("Reducer history contains unconsumed evidence.")
    if rebuilt.content_digest != state.content_digest:
        raise TrainingDataInputError(
            "Reducer state does not match deterministic history replay."
        )


@dataclass(frozen=True, slots=True)
class TargetSizeStatisticalAggregate:
    """Restart-authenticated P2 graph rooted in accepted external P1 owners."""

    frame_authority_digest: str
    neutral_statistical_base_digest: str
    population: TargetSizePopulation
    policy: ResolvedTargetSizePolicy
    split: TargetSizePopulationSplit
    training_priority_evidence: tuple[tuple[str, tuple[float, ...]], ...]
    evaluation_priority_evidence: tuple[tuple[str, tuple[float, ...]], ...]
    definition: TargetSizeExperimentDefinition
    reducer_state: TargetSizeReducerState

    def __post_init__(self) -> None:
        for name in ("frame_authority_digest", "neutral_statistical_base_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        training_evidence = tuple(
            (str(uid), tuple(float(v) for v in vector))
            for uid, vector in self.training_priority_evidence
        )
        evaluation_evidence = tuple(
            (str(uid), tuple(float(v) for v in vector))
            for uid, vector in self.evaluation_priority_evidence
        )
        if tuple(sorted(uid for uid, _ in training_evidence)) != tuple(
            uid for uid, _ in training_evidence
        ):
            raise TrainingDataInputError(
                "Training priority evidence must use canonical UID order."
            )
        if tuple(sorted(uid for uid, _ in evaluation_evidence)) != tuple(
            uid for uid, _ in evaluation_evidence
        ):
            raise TrainingDataInputError(
                "Evaluation priority evidence must use canonical UID order."
            )
        if self.population.frame_authority_digest != self.frame_authority_digest:
            raise TrainingDataInputError("Aggregate frame-authority lineage mismatch.")
        if (
            self.population.neutral_statistical_base_digest
            != self.neutral_statistical_base_digest
        ):
            raise TrainingDataInputError("Aggregate neutral-base lineage mismatch.")
        if self.split.population_digest != self.population.content_digest:
            raise TrainingDataInputError("Aggregate split/population lineage mismatch.")
        if self.split.policy_digest != self.policy.content_digest:
            raise TrainingDataInputError("Aggregate split/policy lineage mismatch.")
        if self.definition.population_digest != self.population.content_digest:
            raise TrainingDataInputError(
                "Aggregate definition/population lineage mismatch."
            )
        if self.definition.split_digest != self.split.content_digest:
            raise TrainingDataInputError("Aggregate definition/split lineage mismatch.")
        if self.definition.policy.content_digest != self.policy.content_digest:
            raise TrainingDataInputError(
                "Aggregate definition/policy lineage mismatch."
            )
        # Derived candidate qualification is freshly re-derivable from the
        # exact prefixes, the bound population, and the normalized hard-support
        # obligations; stored qualified=true can never survive a policy or
        # prefix change.
        derived_qualification = qualify_target_size_candidates(
            self.population, self.definition.training_order, self.policy
        )
        if tuple(item.content_digest for item in derived_qualification) != tuple(
            item.content_digest for item in self.definition.candidate_qualification
        ):
            raise TrainingDataInputError(
                "Persisted candidate qualification does not match deterministic "
                "re-derivation from the exact prefixes and bound policy."
            )
        validate_target_size_reducer_state(self.definition, self.reducer_state)
        object.__setattr__(self, "training_priority_evidence", training_evidence)
        object.__setattr__(self, "evaluation_priority_evidence", evaluation_evidence)

    def with_reducer_state(
        self, state: TargetSizeReducerState
    ) -> TargetSizeStatisticalAggregate:
        return replace(self, reducer_state=state)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_AGGREGATE_SCHEMA,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "population": self.population.to_dict(),
            "policy": self.policy.to_dict(),
            "split": self.split.to_dict(),
            "training_priority_evidence": {
                uid: list(vector) for uid, vector in self.training_priority_evidence
            },
            "evaluation_priority_evidence": {
                uid: list(vector) for uid, vector in self.evaluation_priority_evidence
            },
            "definition": self.definition.to_dict(),
            "reducer_state": self.reducer_state.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        frame_authority: CanonicalFrameAuthority,
        neutral_base: NeutralStatisticalBase,
    ) -> TargetSizeStatisticalAggregate:
        """Deserialize and re-derive the complete graph from accepted P1 owners."""

        if payload.get("schema") != TARGET_SIZE_AGGREGATE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size aggregate schema."
            )
        serialized_population = TargetSizePopulation.from_dict(payload["population"])
        serialized_policy = ResolvedTargetSizePolicy.from_dict(payload["policy"])
        serialized_split = TargetSizePopulationSplit.from_dict(payload["split"])
        serialized_definition = TargetSizeExperimentDefinition.from_dict(
            payload["definition"]
        )
        serialized_reducer = TargetSizeReducerState.from_dict(payload["reducer_state"])
        # Re-derive the inherited P1 split-exclusion relation authority through
        # the real P1 owners before trusting any stored split descendant.
        derived_evidence = build_neutral_split_exclusion_evidence(
            frame_authority, neutral_base
        )
        training_evidence = tuple(
            (str(uid), tuple(float(v) for v in vector))
            for uid, vector in sorted(
                payload.get("training_priority_evidence", {}).items()
            )
        )
        evaluation_evidence = tuple(
            (str(uid), tuple(float(v) for v in vector))
            for uid, vector in sorted(
                payload.get("evaluation_priority_evidence", {}).items()
            )
        )
        if (
            serialized_split.split_exclusion_evidence_digest
            != derived_evidence.content_digest
        ):
            raise TrainingDataSerializationError(
                "Target-size aggregate inherited P1 split-exclusion relation "
                "authority does not match the accepted P1 owners; the stale "
                "split and all descendants are rejected."
            )
        rebuilt = build_target_size_statistical_aggregate(
            frame_authority,
            neutral_base,
            policy=serialized_policy,
            training_priority_evidence=_evidence_mapping(training_evidence),
            evaluation_priority_evidence=_evidence_mapping(evaluation_evidence),
        )
        for name, serialized, derived in (
            (
                "population",
                serialized_population.content_digest,
                rebuilt.population.content_digest,
            ),
            ("split", serialized_split.content_digest, rebuilt.split.content_digest),
            (
                "definition",
                serialized_definition.content_digest,
                rebuilt.definition.content_digest,
            ),
        ):
            if serialized != derived:
                raise TrainingDataSerializationError(
                    f"Target-size aggregate {name} does not match deterministic derivation."
                )
        result = cls(
            frame_authority_digest=rebuilt.frame_authority_digest,
            neutral_statistical_base_digest=rebuilt.neutral_statistical_base_digest,
            population=serialized_population,
            policy=serialized_policy,
            split=serialized_split,
            training_priority_evidence=training_evidence,
            evaluation_priority_evidence=evaluation_evidence,
            definition=serialized_definition,
            reducer_state=serialized_reducer,
        )
        if payload.get("frame_authority_digest") != frame_authority.content_digest:
            raise TrainingDataSerializationError(
                "Target-size aggregate P1 frame authority mismatch."
            )
        if (
            payload.get("neutral_statistical_base_digest")
            != neutral_base.content_digest
        ):
            raise TrainingDataSerializationError(
                "Target-size aggregate P1 neutral base mismatch."
            )
        _checked_dict_digest(
            payload, result.content_digest, name="Target-size statistical aggregate"
        )
        return result


def build_target_size_statistical_aggregate(
    frame_authority: CanonicalFrameAuthority,
    neutral_base: NeutralStatisticalBase,
    *,
    policy: ResolvedTargetSizePolicy | None = None,
    training_priority_evidence: Mapping[str, Sequence[float] | float] | None = None,
    evaluation_priority_evidence: Mapping[str, Sequence[float] | float] | None = None,
) -> TargetSizeStatisticalAggregate:
    active = ResolvedTargetSizePolicy() if policy is None else policy
    population = build_target_size_population(frame_authority, neutral_base)
    split_exclusion = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    split = split_target_size_population(population, active, split_exclusion)
    training_items = _evidence_items(
        split.training_frame_uids,
        training_priority_evidence,
        name="training_priority_evidence",
    )
    evaluation_items = _evidence_items(
        split.evaluation_reserve_frame_uids,
        evaluation_priority_evidence,
        name="evaluation_priority_evidence",
    )
    training_order = build_target_training_order(
        population,
        split,
        active,
        selection_evidence=_evidence_mapping(training_items),
    )
    evaluation_order = build_target_evaluation_order(
        population,
        split,
        active,
        ordering_evidence=_evidence_mapping(evaluation_items),
    )
    definition = build_target_size_experiment_definition(
        population, split, training_order, evaluation_order, active
    )
    return TargetSizeStatisticalAggregate(
        frame_authority_digest=frame_authority.content_digest,
        neutral_statistical_base_digest=neutral_base.content_digest,
        population=population,
        policy=active,
        split=split,
        training_priority_evidence=training_items,
        evaluation_priority_evidence=evaluation_items,
        definition=definition,
        reducer_state=initial_target_size_reducer(definition),
    )


__all__ = (
    "BoundaryOutcome",
    "HARD_SUPPORT_CONDITION_ATTRIBUTES",
    "HARD_SUPPORT_USER_LABEL_PREFIX",
    "NumericalFailureKind",
    "REQUIRED_QUALIFIED_CANDIDATE_COUNT",
    "ReducerStatus",
    "ResolvedTargetSizePolicy",
    "TARGET_SIZE_FUNNEL_POLICY_SCHEMA",
    "TARGET_SIZE_FUNNEL_TRANSITION",
    "TargetEvaluationOrder",
    "TargetSizeBoundaryMetric",
    "TargetSizeCandidateQualification",
    "TargetSizeExperimentDefinition",
    "TargetSizeHardSupportObligation",
    "TargetSizeNumericalFailure",
    "TargetSizePopulation",
    "TargetSizePopulationFrame",
    "TargetSizePopulationSplit",
    "TargetSizeReducerState",
    "TargetSizeStatisticalAggregate",
    "TargetTrainingOrder",
    "advance_target_size_reducer",
    "bind_target_size_execution_context",
    "build_target_evaluation_order",
    "build_target_size_experiment_definition",
    "build_target_size_population",
    "build_target_size_statistical_aggregate",
    "build_target_training_order",
    "initial_target_size_reducer",
    "qualify_target_size_candidates",
    "reference_exact_split_feasible",
    "resolve_target_size_policy",
    "resolve_target_size_policy_from_config",
    "split_target_size_population",
    "target_size_active_boundary_index",
    "validate_target_size_reducer_state",
)
