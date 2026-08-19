"""Requested statistical-role budgets for later DATA5 feasibility analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)

PARTITION_ROLE_BUDGET_POLICY_SCHEMA = "mdstats.partition-role-budget-policy.v1"
PARTITION_ROLE_BUDGET_POLICY_VERSION = "mdstats.mlff-data4.partition-role-budget.2026-07.v1"


@dataclass(frozen=True, slots=True)
class PartitionRoleBudgetPolicy:
    development_minimum_independent_units: int = 4
    outer_monitor_minimum_independent_units: int = 1
    calibration_minimum_independent_units: int = 1
    locked_interpolation_test_minimum_independent_units: int = 1
    cross_validation_folds: int = 3
    checkpoint_monitor_minimum_units_per_fold: int = 1
    purge_units_between_roles: int = 1
    allow_calibration_deferral: bool = True
    allow_external_challenge_tests: bool = True
    required_condition_axes: tuple[str, ...] = (
        "composition",
        "temperature_condition",
        "strain_class",
        "regime",
    )
    policy_version: str = PARTITION_ROLE_BUDGET_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "development_minimum_independent_units",
            "outer_monitor_minimum_independent_units",
            "calibration_minimum_independent_units",
            "locked_interpolation_test_minimum_independent_units",
            "checkpoint_monitor_minimum_units_per_fold",
            "purge_units_between_roles",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        folds = int(self.cross_validation_folds)
        if folds < 2:
            raise TrainingDataInputError("cross_validation_folds must be at least two.")
        object.__setattr__(self, "cross_validation_folds", folds)
        axes = tuple(str(v).strip() for v in self.required_condition_axes)
        if not axes or any(not value for value in axes) or len(set(axes)) != len(axes):
            raise TrainingDataInputError("required_condition_axes must be non-empty and unique.")
        object.__setattr__(self, "required_condition_axes", axes)
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PARTITION_ROLE_BUDGET_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "development_minimum_independent_units": self.development_minimum_independent_units,
            "outer_monitor_minimum_independent_units": self.outer_monitor_minimum_independent_units,
            "calibration_minimum_independent_units": self.calibration_minimum_independent_units,
            "locked_interpolation_test_minimum_independent_units": self.locked_interpolation_test_minimum_independent_units,
            "cross_validation_folds": self.cross_validation_folds,
            "checkpoint_monitor_minimum_units_per_fold": self.checkpoint_monitor_minimum_units_per_fold,
            "purge_units_between_roles": self.purge_units_between_roles,
            "allow_calibration_deferral": self.allow_calibration_deferral,
            "allow_external_challenge_tests": self.allow_external_challenge_tests,
            "required_condition_axes": list(self.required_condition_axes),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PartitionRoleBudgetPolicy":
        if payload.get("schema") != PARTITION_ROLE_BUDGET_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported partition-role-budget policy schema.")
        result = cls(
            development_minimum_independent_units=int(payload["development_minimum_independent_units"]),
            outer_monitor_minimum_independent_units=int(payload["outer_monitor_minimum_independent_units"]),
            calibration_minimum_independent_units=int(payload["calibration_minimum_independent_units"]),
            locked_interpolation_test_minimum_independent_units=int(payload["locked_interpolation_test_minimum_independent_units"]),
            cross_validation_folds=int(payload["cross_validation_folds"]),
            checkpoint_monitor_minimum_units_per_fold=int(payload["checkpoint_monitor_minimum_units_per_fold"]),
            purge_units_between_roles=int(payload["purge_units_between_roles"]),
            allow_calibration_deferral=bool(payload["allow_calibration_deferral"]),
            allow_external_challenge_tests=bool(payload["allow_external_challenge_tests"]),
            required_condition_axes=tuple(str(v) for v in payload["required_condition_axes"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Partition-role-budget policy digest mismatch.")
        return result
