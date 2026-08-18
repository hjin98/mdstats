"""Deterministic balanced assignment and purged fold primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ._common import SamplingInputError, SamplingSerializationError, digest

BALANCED_ASSIGNMENT_PLAN_SCHEMA = "mdstats.balanced-assignment-plan.v1"
PURGED_KFOLD_POLICY_SCHEMA = "mdstats.purged-kfold-policy.v1"
PURGED_KFOLD_POLICY_VERSION = "mdstats.purged-kfold-policy.2026-07.v1"
PURGED_FOLD_SCHEMA = "mdstats.purged-fold.v1"
PURGED_KFOLD_PLAN_SCHEMA = "mdstats.purged-kfold-plan.v1"


@dataclass(frozen=True, slots=True)
class BalancedAssignmentPlan:
    """Stable round-robin assignment of ordered items to ordered labels."""

    item_ids: tuple[str, ...]
    labels: tuple[str, ...]
    assignments: tuple[tuple[str, tuple[str, ...]], ...]
    strategy: str = "deterministic_balanced_round_robin"

    def __post_init__(self) -> None:
        items = tuple(str(value) for value in self.item_ids)
        labels = tuple(str(value) for value in self.labels)
        assignments = tuple(
            (str(label), tuple(str(value) for value in values))
            for label, values in self.assignments
        )
        if not items:
            raise SamplingInputError("Balanced assignment requires at least one item.")
        if len(set(items)) != len(items):
            raise SamplingInputError("Balanced assignment item IDs must be unique.")
        if not labels or any(not value for value in labels):
            raise SamplingInputError("Balanced assignment labels must be nonempty.")
        if len(set(labels)) != len(labels):
            raise SamplingInputError("Balanced assignment labels must be unique.")
        if self.strategy != "deterministic_balanced_round_robin":
            raise SamplingInputError("Unsupported balanced assignment strategy.")
        if tuple(label for label, _ in assignments) != labels:
            raise SamplingInputError(
                "Assignment rows must follow the declared label order."
            )
        flattened = tuple(value for _, values in assignments for value in values)
        if sorted(flattened) != sorted(items) or len(flattened) != len(items):
            raise SamplingInputError(
                "Assignments must cover every item exactly once."
            )
        counts = tuple(len(values) for _, values in assignments)
        if max(counts) - min(counts) > 1:
            raise SamplingInputError("Balanced assignment load difference exceeds one.")
        object.__setattr__(self, "item_ids", items)
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "assignments", assignments)

    def items_for(self, label: str) -> tuple[str, ...]:
        key = str(label)
        for item_label, item_ids in self.assignments:
            if item_label == key:
                return item_ids
        raise KeyError(key)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BALANCED_ASSIGNMENT_PLAN_SCHEMA,
            "item_ids": list(self.item_ids),
            "labels": list(self.labels),
            "assignments": [
                [label, list(item_ids)] for label, item_ids in self.assignments
            ],
            "strategy": self.strategy,
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BalancedAssignmentPlan":
        if payload.get("schema") != BALANCED_ASSIGNMENT_PLAN_SCHEMA:
            raise SamplingSerializationError(
                "Unsupported balanced-assignment-plan schema."
            )
        result = cls(
            item_ids=tuple(str(value) for value in payload["item_ids"]),
            labels=tuple(str(value) for value in payload["labels"]),
            assignments=tuple(
                (str(item[0]), tuple(str(value) for value in item[1]))
                for item in payload["assignments"]
            ),
            strategy=str(payload["strategy"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError(
                "Balanced-assignment-plan signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class PurgedKFoldPolicy:
    """Policy for position-based deterministic folds with neighboring purges."""

    policy_version: str = PURGED_KFOLD_POLICY_VERSION
    requested_fold_count: int = 3
    purge_radius_items: int = 0
    assignment_strategy: str = "deterministic_modulo"

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SamplingInputError("Purged-kfold policy version is required.")
        if self.requested_fold_count < 2:
            raise SamplingInputError("requested_fold_count must be at least two.")
        if self.purge_radius_items < 0:
            raise SamplingInputError("purge_radius_items must be nonnegative.")
        if self.assignment_strategy != "deterministic_modulo":
            raise SamplingInputError("Unsupported purged-kfold assignment strategy.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PURGED_KFOLD_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "requested_fold_count": self.requested_fold_count,
            "purge_radius_items": self.purge_radius_items,
            "assignment_strategy": self.assignment_strategy,
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PurgedKFoldPolicy":
        if payload.get("schema") != PURGED_KFOLD_POLICY_SCHEMA:
            raise SamplingSerializationError("Unsupported purged-kfold-policy schema.")
        result = cls(
            policy_version=str(payload["policy_version"]),
            requested_fold_count=int(payload["requested_fold_count"]),
            purge_radius_items=int(payload["purge_radius_items"]),
            assignment_strategy=str(payload["assignment_strategy"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError("Purged-kfold-policy signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PurgedFold:
    """One evaluation fold, its neighboring purge set, and remaining training set."""

    fold_index: int
    training_item_ids: tuple[str, ...]
    evaluation_item_ids: tuple[str, ...]
    purged_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.fold_index < 0:
            raise SamplingInputError("fold_index must be nonnegative.")
        training = tuple(str(value) for value in self.training_item_ids)
        evaluation = tuple(str(value) for value in self.evaluation_item_ids)
        purged = tuple(str(value) for value in self.purged_item_ids)
        if not evaluation:
            raise SamplingInputError("A purged fold requires evaluation items.")
        if not training:
            raise SamplingInputError("A purged fold requires training items.")
        sets = (set(training), set(evaluation), set(purged))
        if any(len(values) != len(set(values)) for values in (training, evaluation, purged)):
            raise SamplingInputError("Fold item IDs must be unique within each role.")
        if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
            raise SamplingInputError("Training, evaluation, and purged items must be disjoint.")
        object.__setattr__(self, "training_item_ids", training)
        object.__setattr__(self, "evaluation_item_ids", evaluation)
        object.__setattr__(self, "purged_item_ids", purged)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PURGED_FOLD_SCHEMA,
            "fold_index": self.fold_index,
            "training_item_ids": list(self.training_item_ids),
            "evaluation_item_ids": list(self.evaluation_item_ids),
            "purged_item_ids": list(self.purged_item_ids),
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PurgedFold":
        if payload.get("schema") != PURGED_FOLD_SCHEMA:
            raise SamplingSerializationError("Unsupported purged-fold schema.")
        result = cls(
            fold_index=int(payload["fold_index"]),
            training_item_ids=tuple(str(value) for value in payload["training_item_ids"]),
            evaluation_item_ids=tuple(str(value) for value in payload["evaluation_item_ids"]),
            purged_item_ids=tuple(str(value) for value in payload["purged_item_ids"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError("Purged-fold signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PurgedKFoldPlan:
    """Deterministic fold plan over one ordered item sequence."""

    policy_signature: str
    item_ids: tuple[str, ...]
    resolved_fold_count: int
    folds: tuple[PurgedFold, ...]
    omitted_fold_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if len(self.policy_signature) != 64:
            raise SamplingInputError("policy_signature must be a SHA-256 digest.")
        items = tuple(str(value) for value in self.item_ids)
        folds = tuple(self.folds)
        omitted = tuple(int(value) for value in self.omitted_fold_indices)
        if len(items) < 2 or len(set(items)) != len(items):
            raise SamplingInputError("Purged-kfold item IDs must be unique with size >= 2.")
        if not 2 <= self.resolved_fold_count <= len(items):
            raise SamplingInputError("resolved_fold_count is out of bounds.")
        if any(value < 0 or value >= self.resolved_fold_count for value in omitted):
            raise SamplingInputError("omitted_fold_indices is out of bounds.")
        if len(set(omitted)) != len(omitted):
            raise SamplingInputError("omitted_fold_indices must be unique.")
        fold_indices = tuple(fold.fold_index for fold in folds)
        if len(set(fold_indices)) != len(fold_indices):
            raise SamplingInputError("Purged fold indices must be unique.")
        if set(fold_indices) & set(omitted):
            raise SamplingInputError(
                "Realized and omitted fold indices must be disjoint."
            )
        if set(fold_indices) | set(omitted) != set(range(self.resolved_fold_count)):
            raise SamplingInputError(
                "Every resolved fold index must be realized or explicitly omitted."
            )
        known = set(items)
        for fold in folds:
            covered = set(fold.training_item_ids) | set(fold.evaluation_item_ids) | set(fold.purged_item_ids)
            if covered != known:
                raise SamplingInputError("Every fold must classify every input item.")
        object.__setattr__(self, "item_ids", items)
        object.__setattr__(self, "folds", folds)
        object.__setattr__(self, "omitted_fold_indices", omitted)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PURGED_KFOLD_PLAN_SCHEMA,
            "policy_signature": self.policy_signature,
            "item_ids": list(self.item_ids),
            "resolved_fold_count": self.resolved_fold_count,
            "folds": [item.to_dict() for item in self.folds],
            "omitted_fold_indices": list(self.omitted_fold_indices),
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PurgedKFoldPlan":
        if payload.get("schema") != PURGED_KFOLD_PLAN_SCHEMA:
            raise SamplingSerializationError("Unsupported purged-kfold-plan schema.")
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            item_ids=tuple(str(value) for value in payload["item_ids"]),
            resolved_fold_count=int(payload["resolved_fold_count"]),
            folds=tuple(PurgedFold.from_dict(item) for item in payload["folds"]),
            omitted_fold_indices=tuple(int(value) for value in payload.get("omitted_fold_indices", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError("Purged-kfold-plan signature mismatch.")
        return result


def assign_balanced_round_robin(
    item_ids: Sequence[str],
    labels: Sequence[str],
) -> BalancedAssignmentPlan:
    """Assign ordered items by position modulo ordered labels."""

    items = tuple(str(value) for value in item_ids)
    label_values = tuple(str(value) for value in labels)
    if not items:
        raise SamplingInputError("At least one item is required.")
    if len(set(items)) != len(items):
        raise SamplingInputError("item_ids must be unique.")
    if not label_values or len(set(label_values)) != len(label_values):
        raise SamplingInputError("labels must be nonempty and unique.")
    groups = {label: [] for label in label_values}
    for index, item_id in enumerate(items):
        groups[label_values[index % len(label_values)]].append(item_id)
    return BalancedAssignmentPlan(
        item_ids=items,
        labels=label_values,
        assignments=tuple((label, tuple(groups[label])) for label in label_values),
    )


def purge_neighbor_positions(
    evaluation_positions: Sequence[int],
    *,
    item_count: int,
    purge_radius_items: int,
) -> tuple[int, ...]:
    """Return ordered neighboring positions, excluding evaluation positions."""

    if item_count < 1:
        raise SamplingInputError("item_count must be positive.")
    if purge_radius_items < 0:
        raise SamplingInputError("purge_radius_items must be nonnegative.")
    evaluation = {int(value) for value in evaluation_positions}
    if not evaluation or any(value < 0 or value >= item_count for value in evaluation):
        raise SamplingInputError("evaluation_positions must be nonempty and in range.")
    purged: set[int] = set()
    for position in evaluation:
        for offset in range(1, purge_radius_items + 1):
            if position - offset >= 0:
                purged.add(position - offset)
            if position + offset < item_count:
                purged.add(position + offset)
    purged -= evaluation
    return tuple(sorted(purged))


def build_purged_kfold_plan(
    item_ids: Sequence[str],
    *,
    policy: PurgedKFoldPolicy | None = None,
) -> PurgedKFoldPlan:
    """Build deterministic modulo folds and omit folds with no training support."""

    active = PurgedKFoldPolicy() if policy is None else policy
    items = tuple(str(value) for value in item_ids)
    if len(items) < 2 or len(set(items)) != len(items):
        raise SamplingInputError("item_ids must be unique with size >= 2.")
    fold_count = min(active.requested_fold_count, len(items))
    folds: list[PurgedFold] = []
    omitted: list[int] = []
    all_positions = set(range(len(items)))
    for fold_index in range(fold_count):
        evaluation_positions = {
            index for index in range(len(items)) if index % fold_count == fold_index
        }
        purged_positions = set(
            purge_neighbor_positions(
                sorted(evaluation_positions),
                item_count=len(items),
                purge_radius_items=active.purge_radius_items,
            )
        )
        training_positions = all_positions - evaluation_positions - purged_positions
        if not training_positions:
            omitted.append(fold_index)
            continue
        folds.append(
            PurgedFold(
                fold_index=fold_index,
                training_item_ids=tuple(items[index] for index in sorted(training_positions)),
                evaluation_item_ids=tuple(items[index] for index in sorted(evaluation_positions)),
                purged_item_ids=tuple(items[index] for index in sorted(purged_positions)),
            )
        )
    return PurgedKFoldPlan(
        policy_signature=active.signature,
        item_ids=items,
        resolved_fold_count=fold_count,
        folds=tuple(folds),
        omitted_fold_indices=tuple(omitted),
    )
