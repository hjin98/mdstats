"""Stage 11E-GR3 fixed-kernel scientific density-grid refinement.

The numerical hypothesis is frozen before this module is entered: one source,
one sample/weight selection, one Gaussian covariance, and one common cell metric.
GR3 refines only the logical grid and emits orthogonal field, basin, and corridor
certificates.  Presentation-specific resource policies are deliberately absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from ...io.sampling_crossfit import (
    FeatureCorrespondencePolicy,
    FeatureType,
)
from ._frozen_json import FrozenJSONMapping, freeze_json_mapping
from .attractors import AttractorGeometry, DensityAttractorCatalog
from .numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalSerializationError,
)
from .planning import (
    DensityGridPlanStatus,
    DensityNestedGridLadder,
    plan_deterministic_density_grid_ladder,
)
from .resources import ScientificDensityResourcePolicy
from .species import PeriodicSpeciesDensityEstimate

GRID_CONVERGENCE_STOPPING_POLICY_SCHEMA = (
    "mdstats.grid-convergence-stopping-policy.v1"
)
SCIENTIFIC_GRID_REFINEMENT_POLICY_SCHEMA = (
    "mdstats.scientific-grid-refinement-policy.v1"
)
DENSITY_FIELD_LEVEL_EVIDENCE_SCHEMA = "mdstats.density-field-level-evidence.v1"
FEATURE_GRID_CORRESPONDENCE_SCHEMA = "mdstats.feature-grid-correspondence.v1"
BASIN_GRID_PAIR_COMPARISON_SCHEMA = "mdstats.basin-grid-pair-comparison.v1"
CORRIDOR_GRID_LEVEL_EVIDENCE_SCHEMA = (
    "mdstats.corridor-grid-level-evidence.v1"
)
CORRIDOR_GRID_PAIR_COMPARISON_SCHEMA = (
    "mdstats.corridor-grid-pair-comparison.v1"
)
DENSITY_FIELD_RESOLUTION_CERTIFICATE_SCHEMA = (
    "mdstats.density-field-resolution-certificate.v1"
)
BASIN_GRID_CONVERGENCE_CERTIFICATE_SCHEMA = (
    "mdstats.basin-grid-convergence-certificate.v1"
)
CORRIDOR_GRID_CONVERGENCE_CERTIFICATE_SCHEMA = (
    "mdstats.corridor-grid-convergence-certificate.v1"
)
SCIENTIFIC_GRID_REFINEMENT_BUNDLE_SCHEMA = (
    "mdstats.scientific-grid-refinement-bundle.v1"
)

GRID_CONVERGENCE_STOPPING_POLICY_VERSION = "stage11_grid_stopping_v1"


class GridConvergenceStatus(str, Enum):
    CONVERGED = "converged"
    UNRESOLVED_DUE_TO_RESOLUTION_BUDGET = (
        "unresolved_due_to_resolution_budget"
    )
    UNRESOLVED_DUE_TO_REFINEMENT_LIMIT = (
        "unresolved_due_to_refinement_limit"
    )
    UNRESOLVED_DUE_TO_INSUFFICIENT_PASSING_LEVELS = (
        "unresolved_due_to_insufficient_passing_levels"
    )
    UNRESOLVED_DUE_TO_METRIC_FAILURE = "unresolved_due_to_metric_failure"
    UNRESOLVED_DUE_TO_MISSING_EVIDENCE = "unresolved_due_to_missing_evidence"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _signature(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def _digest_text(value: str, *, name: str) -> str:
    result = str(value)
    if len(result) != 64:
        raise DensityNumericalInputError(f"{name} must be a SHA-256 digest.")
    try:
        int(result, 16)
    except ValueError as error:
        raise DensityNumericalInputError(
            f"{name} must be a SHA-256 digest."
        ) from error
    return result


def _positive(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise DensityNumericalInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise DensityNumericalInputError(
            f"{name} must be finite and nonnegative."
        )
    return result


def _fraction(value: Any, *, name: str) -> float:
    result = _nonnegative(value, name=name)
    if result > 1.0:
        raise DensityNumericalInputError(f"{name} must not exceed one.")
    return result


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise DensityNumericalInputError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise DensityNumericalInputError(f"{name} must be positive.")
    return result


def _shape(value: Sequence[int], *, name: str = "grid_shape") -> tuple[int, int, int]:
    result = tuple(_positive_int(item, name=name) for item in value)
    if len(result) != 3:
        raise DensityNumericalInputError(f"{name} must contain three entries.")
    return result


def _matrix3(value: Any, *, name: str, positive_definite: bool = False) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (3, 3) or np.any(~np.isfinite(result)):
        raise DensityNumericalInputError(f"{name} must be a finite 3x3 matrix.")
    result = 0.5 * (result + result.T)
    if positive_definite and np.min(np.linalg.eigvalsh(result)) <= 0.0:
        raise DensityNumericalInputError(f"{name} must be positive definite.")
    result = np.array(result, copy=True)
    result.setflags(write=False)
    return result


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    header = f"{array.dtype.str}|{array.shape}|".encode("ascii")
    return hashlib.sha256(header + array.tobytes(order="C")).hexdigest()


def _periodic_distance(
    left: np.ndarray, right: np.ndarray, cell: np.ndarray
) -> float:
    delta = np.asarray(right, dtype=np.float64) - np.asarray(left, dtype=np.float64)
    delta -= np.rint(delta)
    return float(np.linalg.norm(delta @ cell))


def _feature_type(geometry: AttractorGeometry) -> FeatureType:
    if geometry is AttractorGeometry.ISOLATED_MODE:
        return FeatureType.POINT
    return FeatureType.RIDGE


def _status_for_unpassed_ladder(ladder: DensityNestedGridLadder) -> GridConvergenceStatus:
    if ladder.status is DensityGridPlanStatus.BUDGET_LIMITED:
        return GridConvergenceStatus.UNRESOLVED_DUE_TO_RESOLUTION_BUDGET
    if ladder.status is DensityGridPlanStatus.LEVEL_LIMITED:
        return GridConvergenceStatus.UNRESOLVED_DUE_TO_REFINEMENT_LIMIT
    return GridConvergenceStatus.UNRESOLVED_DUE_TO_INSUFFICIENT_PASSING_LEVELS


def _consecutive_tail_passes(
    passed: Sequence[bool], eligible: Sequence[bool]
) -> int:
    count = 0
    for is_passed, is_eligible in zip(reversed(passed), reversed(eligible), strict=True):
        if not is_eligible or not is_passed:
            break
        count += 1
    return count


@dataclass(frozen=True, slots=True)
class GridConvergenceStoppingPolicy:
    """Versioned GR3 stopping and basin/corridor tolerance policy."""

    policy_version: str = GRID_CONVERGENCE_STOPPING_POLICY_VERSION
    refinement_factor: int = 2
    target_max_interval_to_sigma_min: float = 0.5
    maximum_levels: int = 8
    consecutive_passing_level_pairs: int = 2
    maximum_field_probability_l1_change: float = 0.02
    maximum_field_normalization_residual: float = 1.0e-6
    require_unchanged_basin_count: bool = True
    maximum_basin_anchor_displacement_sigma: float = 0.10
    minimum_basin_overlap: float = 0.95
    maximum_basin_probability_change: float = 0.02
    require_unambiguous_basin_correspondence: bool = True
    require_unchanged_corridor_adjacency: bool = True
    minimum_corridor_overlap: float = 0.90
    maximum_bottleneck_displacement_sigma: float = 0.15
    maximum_corridor_relative_width_change: float = 0.10
    maximum_corridor_relative_density_change: float = 0.10
    require_unambiguous_corridor_correspondence: bool = True

    def __post_init__(self) -> None:
        if self.policy_version != GRID_CONVERGENCE_STOPPING_POLICY_VERSION:
            raise DensityNumericalInputError(
                "Unsupported grid-convergence stopping preset."
            )
        factor = _positive_int(self.refinement_factor, name="refinement_factor")
        if factor < 2:
            raise DensityNumericalInputError(
                "refinement_factor must be at least two."
            )
        levels = _positive_int(self.maximum_levels, name="maximum_levels")
        consecutive = _positive_int(
            self.consecutive_passing_level_pairs,
            name="consecutive_passing_level_pairs",
        )
        if consecutive < 2:
            raise DensityNumericalInputError(
                "GR3 requires at least two consecutive passing level pairs."
            )
        if levels < consecutive + 1:
            raise DensityNumericalInputError(
                "maximum_levels cannot support the required consecutive pairs."
            )
        for name in (
            "target_max_interval_to_sigma_min",
            "maximum_field_probability_l1_change",
            "maximum_field_normalization_residual",
            "maximum_basin_anchor_displacement_sigma",
            "maximum_basin_probability_change",
            "maximum_bottleneck_displacement_sigma",
            "maximum_corridor_relative_width_change",
            "maximum_corridor_relative_density_change",
        ):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        for name in ("minimum_basin_overlap", "minimum_corridor_overlap"):
            object.__setattr__(self, name, _fraction(getattr(self, name), name=name))
        object.__setattr__(self, "refinement_factor", factor)
        object.__setattr__(self, "maximum_levels", levels)
        object.__setattr__(self, "consecutive_passing_level_pairs", consecutive)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": GRID_CONVERGENCE_STOPPING_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "refinement_factor": self.refinement_factor,
            "target_max_interval_to_sigma_min": self.target_max_interval_to_sigma_min,
            "maximum_levels": self.maximum_levels,
            "consecutive_passing_level_pairs": self.consecutive_passing_level_pairs,
            "maximum_field_probability_l1_change": self.maximum_field_probability_l1_change,
            "maximum_field_normalization_residual": self.maximum_field_normalization_residual,
            "require_unchanged_basin_count": self.require_unchanged_basin_count,
            "maximum_basin_anchor_displacement_sigma": self.maximum_basin_anchor_displacement_sigma,
            "minimum_basin_overlap": self.minimum_basin_overlap,
            "maximum_basin_probability_change": self.maximum_basin_probability_change,
            "require_unambiguous_basin_correspondence": self.require_unambiguous_basin_correspondence,
            "require_unchanged_corridor_adjacency": self.require_unchanged_corridor_adjacency,
            "minimum_corridor_overlap": self.minimum_corridor_overlap,
            "maximum_bottleneck_displacement_sigma": self.maximum_bottleneck_displacement_sigma,
            "maximum_corridor_relative_width_change": self.maximum_corridor_relative_width_change,
            "maximum_corridor_relative_density_change": self.maximum_corridor_relative_density_change,
            "require_unambiguous_corridor_correspondence": self.require_unambiguous_corridor_correspondence,
        }

    @property
    def signature(self) -> str:
        return _signature(self._payload())

    def to_json_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "GridConvergenceStoppingPolicy":
        if payload.get("schema") != GRID_CONVERGENCE_STOPPING_POLICY_SCHEMA:
            raise DensityNumericalSerializationError(
                "Unsupported grid-convergence stopping-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            refinement_factor=int(payload["refinement_factor"]),
            target_max_interval_to_sigma_min=float(
                payload["target_max_interval_to_sigma_min"]
            ),
            maximum_levels=int(payload["maximum_levels"]),
            consecutive_passing_level_pairs=int(
                payload["consecutive_passing_level_pairs"]
            ),
            maximum_field_probability_l1_change=float(
                payload["maximum_field_probability_l1_change"]
            ),
            maximum_field_normalization_residual=float(
                payload["maximum_field_normalization_residual"]
            ),
            require_unchanged_basin_count=bool(
                payload["require_unchanged_basin_count"]
            ),
            maximum_basin_anchor_displacement_sigma=float(
                payload["maximum_basin_anchor_displacement_sigma"]
            ),
            minimum_basin_overlap=float(payload["minimum_basin_overlap"]),
            maximum_basin_probability_change=float(
                payload["maximum_basin_probability_change"]
            ),
            require_unambiguous_basin_correspondence=bool(
                payload["require_unambiguous_basin_correspondence"]
            ),
            require_unchanged_corridor_adjacency=bool(
                payload["require_unchanged_corridor_adjacency"]
            ),
            minimum_corridor_overlap=float(payload["minimum_corridor_overlap"]),
            maximum_bottleneck_displacement_sigma=float(
                payload["maximum_bottleneck_displacement_sigma"]
            ),
            maximum_corridor_relative_width_change=float(
                payload["maximum_corridor_relative_width_change"]
            ),
            maximum_corridor_relative_density_change=float(
                payload["maximum_corridor_relative_density_change"]
            ),
            require_unambiguous_corridor_correspondence=bool(
                payload["require_unambiguous_corridor_correspondence"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Grid-convergence stopping-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class ScientificGridRefinementPolicy:
    """Source- and kernel-bound GR3 policy."""

    fixed_kernel_covariance_cartesian: np.ndarray
    fixed_kernel_signature: str
    scientific_resource_policy_signature: str
    crossfit_partition_signature: str
    coarsest_interval: float
    stopping_policy: GridConvergenceStoppingPolicy = field(
        default_factory=GridConvergenceStoppingPolicy
    )
    correspondence_policy: FeatureCorrespondencePolicy = field(
        default_factory=FeatureCorrespondencePolicy
    )
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = SCIENTIFIC_GRID_REFINEMENT_POLICY_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != SCIENTIFIC_GRID_REFINEMENT_POLICY_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported scientific-grid policy schema {self.schema_version!r}."
            )
        covariance = _matrix3(
            self.fixed_kernel_covariance_cartesian,
            name="fixed_kernel_covariance_cartesian",
            positive_definite=True,
        )
        kernel = _digest_text(
            self.fixed_kernel_signature, name="fixed_kernel_signature"
        )
        resources = _digest_text(
            self.scientific_resource_policy_signature,
            name="scientific_resource_policy_signature",
        )
        crossfit = _digest_text(
            self.crossfit_partition_signature,
            name="crossfit_partition_signature",
        )
        interval = _positive(self.coarsest_interval, name="coarsest_interval")
        if not isinstance(self.stopping_policy, GridConvergenceStoppingPolicy):
            raise TypeError("stopping_policy must be GridConvergenceStoppingPolicy.")
        if not isinstance(self.correspondence_policy, FeatureCorrespondencePolicy):
            raise TypeError("correspondence_policy must be FeatureCorrespondencePolicy.")
        metadata = freeze_json_mapping(self.metadata)
        object.__setattr__(self, "fixed_kernel_covariance_cartesian", covariance)
        object.__setattr__(self, "fixed_kernel_signature", kernel)
        object.__setattr__(self, "scientific_resource_policy_signature", resources)
        object.__setattr__(self, "crossfit_partition_signature", crossfit)
        object.__setattr__(self, "coarsest_interval", interval)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    @property
    def sigma_min(self) -> float:
        return float(
            math.sqrt(
                float(np.min(np.linalg.eigvalsh(self.fixed_kernel_covariance_cartesian)))
            )
        )

    @property
    def physical_resolution_interval(self) -> float:
        return (
            self.sigma_min
            * self.stopping_policy.target_max_interval_to_sigma_min
        )

    @property
    def requested_finest_interval(self) -> float:
        return self.physical_resolution_interval / float(
            self.stopping_policy.refinement_factor
            ** (self.stopping_policy.consecutive_passing_level_pairs - 1)
        )

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "fixed_kernel_covariance_cartesian": self.fixed_kernel_covariance_cartesian.tolist(),
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "scientific_resource_policy_signature": self.scientific_resource_policy_signature,
            "crossfit_partition_signature": self.crossfit_partition_signature,
            "coarsest_interval": self.coarsest_interval,
            "stopping_policy": self.stopping_policy.to_json_dict(),
            "correspondence_policy": self.correspondence_policy.to_dict(),
            "sigma_min": self.sigma_min,
            "physical_resolution_interval": self.physical_resolution_interval,
            "requested_finest_interval": self.requested_finest_interval,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "ScientificGridRefinementPolicy":
        result = cls(
            fixed_kernel_covariance_cartesian=np.asarray(
                payload["fixed_kernel_covariance_cartesian"], dtype=np.float64
            ),
            fixed_kernel_signature=str(payload["fixed_kernel_signature"]),
            scientific_resource_policy_signature=str(
                payload["scientific_resource_policy_signature"]
            ),
            crossfit_partition_signature=str(payload["crossfit_partition_signature"]),
            coarsest_interval=float(payload["coarsest_interval"]),
            stopping_policy=GridConvergenceStoppingPolicy.from_json_dict(
                payload["stopping_policy"]
            ),
            correspondence_policy=FeatureCorrespondencePolicy.from_dict(
                payload["correspondence_policy"]
            ),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Scientific-grid refinement-policy signature mismatch."
            )
        return result


def plan_scientific_grid_refinement(
    cell: Any,
    policy: ScientificGridRefinementPolicy,
    *,
    resource_policy: ScientificDensityResourcePolicy | None = None,
    max_logical_voxels: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DensityNestedGridLadder:
    """Plan the extra fine level(s) needed for consecutive post-gate passes."""

    if not isinstance(policy, ScientificGridRefinementPolicy):
        raise TypeError("policy must be ScientificGridRefinementPolicy.")
    if resource_policy is not None and resource_policy.signature != policy.scientific_resource_policy_signature:
        raise DensityNumericalInputError(
            "The scientific resource signature disagrees with the GR3 policy."
        )
    ladder = plan_deterministic_density_grid_ladder(
        cell,
        coarsest_interval=policy.coarsest_interval,
        finest_interval=policy.requested_finest_interval,
        refinement_factor=policy.stopping_policy.refinement_factor,
        max_levels=policy.stopping_policy.maximum_levels,
        resource_policy=resource_policy,
        max_logical_voxels=max_logical_voxels,
        metadata={
            "planner_role": "stage11_fixed_kernel_scientific_refinement",
            "policy_signature": policy.signature,
            "fixed_kernel_signature": policy.fixed_kernel_signature,
            "physical_resolution_interval": policy.physical_resolution_interval,
            **({} if metadata is None else dict(metadata)),
        },
    )
    if ladder.scientific_resource_signature != policy.scientific_resource_policy_signature:
        raise DensityNumericalInputError(
            "The ladder scientific-resource signature disagrees with the GR3 policy."
        )
    return ladder


@dataclass(frozen=True, slots=True)
class DensityFieldLevelEvidence:
    level_index: int
    grid_shape: tuple[int, int, int]
    realized_intervals: tuple[float, float, float]
    estimate_signature: str
    fixed_kernel_signature: str
    backend: str
    probability_normalization_residual: float
    number_normalization_residual: float
    probability_l1_change_from_previous: float | None
    probability_linf_change_from_previous: float | None
    cic_covariance_cartesian: np.ndarray
    stencil_covariance_cartesian: np.ndarray
    effective_artificial_covariance_cartesian: np.ndarray
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_FIELD_LEVEL_EVIDENCE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_FIELD_LEVEL_EVIDENCE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported density-field level-evidence schema.")
        level = int(self.level_index)
        if level < 0:
            raise DensityNumericalInputError("level_index must be nonnegative.")
        shape = _shape(self.grid_shape)
        intervals = tuple(_positive(v, name="realized_interval") for v in self.realized_intervals)
        if len(intervals) != 3:
            raise DensityNumericalInputError("realized_intervals must contain three entries.")
        estimate = _digest_text(self.estimate_signature, name="estimate_signature")
        kernel = _digest_text(self.fixed_kernel_signature, name="fixed_kernel_signature")
        backend = str(self.backend).strip()
        if not backend:
            raise DensityNumericalInputError("backend must be nonempty.")
        probability_residual = _nonnegative(
            self.probability_normalization_residual,
            name="probability_normalization_residual",
        )
        number_residual = _nonnegative(
            self.number_normalization_residual,
            name="number_normalization_residual",
        )
        l1 = None if self.probability_l1_change_from_previous is None else _nonnegative(
            self.probability_l1_change_from_previous,
            name="probability_l1_change_from_previous",
        )
        linf = None if self.probability_linf_change_from_previous is None else _nonnegative(
            self.probability_linf_change_from_previous,
            name="probability_linf_change_from_previous",
        )
        if level == 0 and (l1 is not None or linf is not None):
            raise DensityNumericalInputError(
                "The first field level cannot carry previous-level changes."
            )
        if level > 0 and (l1 is None or linf is None):
            raise DensityNumericalInputError(
                "Refined field levels require L1 and Linf changes."
            )
        cic = _matrix3(self.cic_covariance_cartesian, name="cic_covariance_cartesian")
        stencil = _matrix3(
            self.stencil_covariance_cartesian, name="stencil_covariance_cartesian"
        )
        total = _matrix3(
            self.effective_artificial_covariance_cartesian,
            name="effective_artificial_covariance_cartesian",
        )
        if not np.allclose(total, cic + stencil, rtol=5e-13, atol=5e-13):
            raise DensityNumericalInputError(
                "Effective artificial covariance must equal CIC plus stencil covariance."
            )
        metadata = freeze_json_mapping(self.metadata)
        for name, value in (
            ("level_index", level),
            ("grid_shape", shape),
            ("realized_intervals", intervals),
            ("estimate_signature", estimate),
            ("fixed_kernel_signature", kernel),
            ("backend", backend),
            ("probability_normalization_residual", probability_residual),
            ("number_normalization_residual", number_residual),
            ("probability_l1_change_from_previous", l1),
            ("probability_linf_change_from_previous", linf),
            ("cic_covariance_cartesian", cic),
            ("stencil_covariance_cartesian", stencil),
            ("effective_artificial_covariance_cartesian", total),
            ("metadata", metadata),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "level_index": self.level_index,
            "grid_shape": list(self.grid_shape),
            "realized_intervals": list(self.realized_intervals),
            "estimate_signature": self.estimate_signature,
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "backend": self.backend,
            "probability_normalization_residual": self.probability_normalization_residual,
            "number_normalization_residual": self.number_normalization_residual,
            "probability_l1_change_from_previous": self.probability_l1_change_from_previous,
            "probability_linf_change_from_previous": self.probability_linf_change_from_previous,
            "cic_covariance_cartesian": self.cic_covariance_cartesian.tolist(),
            "stencil_covariance_cartesian": self.stencil_covariance_cartesian.tolist(),
            "effective_artificial_covariance_cartesian": self.effective_artificial_covariance_cartesian.tolist(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityFieldLevelEvidence":
        result = cls(
            level_index=int(payload["level_index"]),
            grid_shape=tuple(payload["grid_shape"]),
            realized_intervals=tuple(payload["realized_intervals"]),
            estimate_signature=str(payload["estimate_signature"]),
            fixed_kernel_signature=str(payload["fixed_kernel_signature"]),
            backend=str(payload["backend"]),
            probability_normalization_residual=float(payload["probability_normalization_residual"]),
            number_normalization_residual=float(payload["number_normalization_residual"]),
            probability_l1_change_from_previous=payload.get("probability_l1_change_from_previous"),
            probability_linf_change_from_previous=payload.get("probability_linf_change_from_previous"),
            cic_covariance_cartesian=np.asarray(payload["cic_covariance_cartesian"]),
            stencil_covariance_cartesian=np.asarray(payload["stencil_covariance_cartesian"]),
            effective_artificial_covariance_cartesian=np.asarray(payload["effective_artificial_covariance_cartesian"]),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Density-field level-evidence signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class FeatureGridCorrespondence:
    source_feature_id: int
    target_feature_id: int
    normalized_cost: float
    anchor_displacement: float
    overlap: float
    probability_change: float
    ambiguous: bool = False
    schema_version: str = FEATURE_GRID_CORRESPONDENCE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != FEATURE_GRID_CORRESPONDENCE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported feature-grid correspondence schema.")
        source = int(self.source_feature_id)
        target = int(self.target_feature_id)
        if source < 0 or target < 0:
            raise DensityNumericalInputError("Feature identifiers must be nonnegative.")
        values = {
            "normalized_cost": _nonnegative(self.normalized_cost, name="normalized_cost"),
            "anchor_displacement": _nonnegative(self.anchor_displacement, name="anchor_displacement"),
            "overlap": _fraction(self.overlap, name="overlap"),
            "probability_change": _nonnegative(self.probability_change, name="probability_change"),
        }
        object.__setattr__(self, "source_feature_id", source)
        object.__setattr__(self, "target_feature_id", target)
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "ambiguous", bool(self.ambiguous))
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "source_feature_id": self.source_feature_id,
            "target_feature_id": self.target_feature_id,
            "normalized_cost": self.normalized_cost,
            "anchor_displacement": self.anchor_displacement,
            "overlap": self.overlap,
            "probability_change": self.probability_change,
            "ambiguous": self.ambiguous,
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "FeatureGridCorrespondence":
        result = cls(
            source_feature_id=int(payload["source_feature_id"]),
            target_feature_id=int(payload["target_feature_id"]),
            normalized_cost=float(payload["normalized_cost"]),
            anchor_displacement=float(payload["anchor_displacement"]),
            overlap=float(payload["overlap"]),
            probability_change=float(payload["probability_change"]),
            ambiguous=bool(payload.get("ambiguous", False)),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Feature-grid correspondence signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class BasinGridPairComparison:
    coarse_level_index: int
    fine_level_index: int
    coarse_catalog_signature: str
    fine_catalog_signature: str
    coarse_count: int
    fine_count: int
    correspondences: tuple[FeatureGridCorrespondence, ...]
    source_unmatched: tuple[int, ...] = ()
    target_unmatched: tuple[int, ...] = ()
    split_records: tuple[tuple[int, tuple[int, ...]], ...] = ()
    merge_records: tuple[tuple[tuple[int, ...], int], ...] = ()
    ambiguity_detected: bool = False
    schema_version: str = BASIN_GRID_PAIR_COMPARISON_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != BASIN_GRID_PAIR_COMPARISON_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported basin-grid pair-comparison schema.")
        coarse_level = int(self.coarse_level_index)
        fine_level = int(self.fine_level_index)
        if coarse_level < 0 or fine_level != coarse_level + 1:
            raise DensityNumericalInputError(
                "Basin comparison levels must be consecutive."
            )
        coarse_signature = _digest_text(
            self.coarse_catalog_signature, name="coarse_catalog_signature"
        )
        fine_signature = _digest_text(
            self.fine_catalog_signature, name="fine_catalog_signature"
        )
        coarse_count = int(self.coarse_count)
        fine_count = int(self.fine_count)
        if coarse_count < 0 or fine_count < 0:
            raise DensityNumericalInputError("Basin counts must be nonnegative.")
        correspondences = tuple(self.correspondences)
        if len({item.source_feature_id for item in correspondences}) != len(correspondences):
            raise DensityNumericalInputError("Source basin correspondences must be unique.")
        if len({item.target_feature_id for item in correspondences}) != len(correspondences):
            raise DensityNumericalInputError("Target basin correspondences must be unique.")
        source_unmatched = tuple(sorted(int(item) for item in self.source_unmatched))
        target_unmatched = tuple(sorted(int(item) for item in self.target_unmatched))
        splits = tuple(
            sorted((int(source), tuple(sorted(int(v) for v in targets))) for source, targets in self.split_records)
        )
        merges = tuple(
            sorted((tuple(sorted(int(v) for v in sources)), int(target)) for sources, target in self.merge_records)
        )
        ambiguity = bool(self.ambiguity_detected) or any(item.ambiguous for item in correspondences)
        for name, value in (
            ("coarse_level_index", coarse_level),
            ("fine_level_index", fine_level),
            ("coarse_catalog_signature", coarse_signature),
            ("fine_catalog_signature", fine_signature),
            ("coarse_count", coarse_count),
            ("fine_count", fine_count),
            ("correspondences", correspondences),
            ("source_unmatched", source_unmatched),
            ("target_unmatched", target_unmatched),
            ("split_records", splits),
            ("merge_records", merges),
            ("ambiguity_detected", ambiguity),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    @property
    def maximum_anchor_displacement(self) -> float | None:
        if not self.correspondences:
            return None
        return max(item.anchor_displacement for item in self.correspondences)

    @property
    def minimum_overlap(self) -> float | None:
        if not self.correspondences:
            return None
        return min(item.overlap for item in self.correspondences)

    @property
    def maximum_probability_change(self) -> float | None:
        if not self.correspondences:
            return None
        return max(item.probability_change for item in self.correspondences)

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "coarse_level_index": self.coarse_level_index,
            "fine_level_index": self.fine_level_index,
            "coarse_catalog_signature": self.coarse_catalog_signature,
            "fine_catalog_signature": self.fine_catalog_signature,
            "coarse_count": self.coarse_count,
            "fine_count": self.fine_count,
            "correspondences": [item.to_json_dict() for item in self.correspondences],
            "source_unmatched": list(self.source_unmatched),
            "target_unmatched": list(self.target_unmatched),
            "split_records": [[source, list(targets)] for source, targets in self.split_records],
            "merge_records": [[list(sources), target] for sources, target in self.merge_records],
            "ambiguity_detected": self.ambiguity_detected,
            "maximum_anchor_displacement": self.maximum_anchor_displacement,
            "minimum_overlap": self.minimum_overlap,
            "maximum_probability_change": self.maximum_probability_change,
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "BasinGridPairComparison":
        result = cls(
            coarse_level_index=int(payload["coarse_level_index"]),
            fine_level_index=int(payload["fine_level_index"]),
            coarse_catalog_signature=str(payload["coarse_catalog_signature"]),
            fine_catalog_signature=str(payload["fine_catalog_signature"]),
            coarse_count=int(payload["coarse_count"]),
            fine_count=int(payload["fine_count"]),
            correspondences=tuple(
                FeatureGridCorrespondence.from_json_dict(item)
                for item in payload["correspondences"]
            ),
            source_unmatched=tuple(payload.get("source_unmatched", ())),
            target_unmatched=tuple(payload.get("target_unmatched", ())),
            split_records=tuple(
                (int(item[0]), tuple(item[1])) for item in payload.get("split_records", ())
            ),
            merge_records=tuple(
                (tuple(item[0]), int(item[1])) for item in payload.get("merge_records", ())
            ),
            ambiguity_detected=bool(payload.get("ambiguity_detected", False)),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Basin-grid pair-comparison signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CorridorGridLevelEvidence:
    level_index: int
    catalog_signature: str
    adjacency_pairs: tuple[tuple[int, int], ...]
    bottleneck_fractional_by_pair: tuple[tuple[tuple[int, int], tuple[float, float, float]], ...]
    width_by_pair: tuple[tuple[tuple[int, int], float], ...]
    density_by_pair: tuple[tuple[tuple[int, int], float], ...]
    support_nodes_by_pair: tuple[tuple[tuple[int, int], tuple[int, ...]], ...] = ()
    schema_version: str = CORRIDOR_GRID_LEVEL_EVIDENCE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != CORRIDOR_GRID_LEVEL_EVIDENCE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported corridor-grid level-evidence schema.")
        level = int(self.level_index)
        if level < 0:
            raise DensityNumericalInputError("level_index must be nonnegative.")
        catalog = _digest_text(self.catalog_signature, name="catalog_signature")
        adjacency = tuple(sorted({tuple(sorted((int(a), int(b)))) for a, b in self.adjacency_pairs}))
        if any(a < 0 or a == b for a, b in adjacency):
            raise DensityNumericalInputError("Corridor adjacency pairs are invalid.")
        bottlenecks = tuple(
            sorted(
                (
                    tuple(sorted((int(pair[0]), int(pair[1])))),
                    tuple(float(v) % 1.0 for v in point),
                )
                for pair, point in self.bottleneck_fractional_by_pair
            )
        )
        widths = tuple(
            sorted((tuple(sorted((int(pair[0]), int(pair[1])))), _positive(value, name="corridor_width")) for pair, value in self.width_by_pair)
        )
        densities = tuple(
            sorted((tuple(sorted((int(pair[0]), int(pair[1])))), _nonnegative(value, name="corridor_density")) for pair, value in self.density_by_pair)
        )
        supports = tuple(
            sorted((tuple(sorted((int(pair[0]), int(pair[1])))), tuple(sorted(int(v) for v in nodes))) for pair, nodes in self.support_nodes_by_pair)
        )
        keys = set(adjacency)
        if {pair for pair, _ in bottlenecks} != keys or {pair for pair, _ in widths} != keys or {pair for pair, _ in densities} != keys:
            raise DensityNumericalInputError(
                "Each corridor adjacency requires bottleneck, width, and density evidence."
            )
        if supports and {pair for pair, _ in supports} != keys:
            raise DensityNumericalInputError(
                "Corridor support-node evidence must cover every adjacency."
            )
        for name, value in (
            ("level_index", level),
            ("catalog_signature", catalog),
            ("adjacency_pairs", adjacency),
            ("bottleneck_fractional_by_pair", bottlenecks),
            ("width_by_pair", widths),
            ("density_by_pair", densities),
            ("support_nodes_by_pair", supports),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "level_index": self.level_index,
            "catalog_signature": self.catalog_signature,
            "adjacency_pairs": [list(pair) for pair in self.adjacency_pairs],
            "bottleneck_fractional_by_pair": [[list(pair), list(point)] for pair, point in self.bottleneck_fractional_by_pair],
            "width_by_pair": [[list(pair), value] for pair, value in self.width_by_pair],
            "density_by_pair": [[list(pair), value] for pair, value in self.density_by_pair],
            "support_nodes_by_pair": [[list(pair), list(nodes)] for pair, nodes in self.support_nodes_by_pair],
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CorridorGridLevelEvidence":
        result = cls(
            level_index=int(payload["level_index"]),
            catalog_signature=str(payload["catalog_signature"]),
            adjacency_pairs=tuple(tuple(item) for item in payload["adjacency_pairs"]),
            bottleneck_fractional_by_pair=tuple(
                (tuple(item[0]), tuple(item[1]))
                for item in payload["bottleneck_fractional_by_pair"]
            ),
            width_by_pair=tuple(
                (tuple(item[0]), float(item[1])) for item in payload["width_by_pair"]
            ),
            density_by_pair=tuple(
                (tuple(item[0]), float(item[1])) for item in payload["density_by_pair"]
            ),
            support_nodes_by_pair=tuple(
                (tuple(item[0]), tuple(item[1]))
                for item in payload.get("support_nodes_by_pair", ())
            ),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Corridor-grid level-evidence signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CorridorGridPairComparison:
    coarse_level_index: int
    fine_level_index: int
    adjacency_equal: bool
    minimum_overlap: float | None
    maximum_bottleneck_displacement: float | None
    maximum_relative_width_change: float | None
    maximum_relative_density_change: float | None
    split_records: tuple[tuple[tuple[int, int], tuple[tuple[int, int], ...]], ...] = ()
    merge_records: tuple[tuple[tuple[tuple[int, int], ...], tuple[int, int]], ...] = ()
    ambiguity_detected: bool = False
    evidence_complete: bool = True
    schema_version: str = CORRIDOR_GRID_PAIR_COMPARISON_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != CORRIDOR_GRID_PAIR_COMPARISON_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported corridor-grid pair-comparison schema.")
        coarse = int(self.coarse_level_index)
        fine = int(self.fine_level_index)
        if coarse < 0 or fine != coarse + 1:
            raise DensityNumericalInputError(
                "Corridor comparison levels must be consecutive."
            )
        overlap = None if self.minimum_overlap is None else _fraction(self.minimum_overlap, name="minimum_overlap")
        displacement = None if self.maximum_bottleneck_displacement is None else _nonnegative(self.maximum_bottleneck_displacement, name="maximum_bottleneck_displacement")
        width = None if self.maximum_relative_width_change is None else _nonnegative(self.maximum_relative_width_change, name="maximum_relative_width_change")
        density = None if self.maximum_relative_density_change is None else _nonnegative(self.maximum_relative_density_change, name="maximum_relative_density_change")
        complete = bool(self.evidence_complete)
        if complete and any(item is None for item in (overlap, displacement, width, density)):
            raise DensityNumericalInputError(
                "Complete corridor comparison requires every numerical metric."
            )
        object.__setattr__(self, "coarse_level_index", coarse)
        object.__setattr__(self, "fine_level_index", fine)
        object.__setattr__(self, "minimum_overlap", overlap)
        object.__setattr__(self, "maximum_bottleneck_displacement", displacement)
        object.__setattr__(self, "maximum_relative_width_change", width)
        object.__setattr__(self, "maximum_relative_density_change", density)
        object.__setattr__(self, "split_records", tuple(self.split_records))
        object.__setattr__(self, "merge_records", tuple(self.merge_records))
        object.__setattr__(self, "ambiguity_detected", bool(self.ambiguity_detected))
        object.__setattr__(self, "evidence_complete", complete)
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "coarse_level_index": self.coarse_level_index,
            "fine_level_index": self.fine_level_index,
            "adjacency_equal": self.adjacency_equal,
            "minimum_overlap": self.minimum_overlap,
            "maximum_bottleneck_displacement": self.maximum_bottleneck_displacement,
            "maximum_relative_width_change": self.maximum_relative_width_change,
            "maximum_relative_density_change": self.maximum_relative_density_change,
            "split_records": [
                [list(source), [list(target) for target in targets]]
                for source, targets in self.split_records
            ],
            "merge_records": [
                [[list(source) for source in sources], list(target)]
                for sources, target in self.merge_records
            ],
            "ambiguity_detected": self.ambiguity_detected,
            "evidence_complete": self.evidence_complete,
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CorridorGridPairComparison":
        result = cls(
            coarse_level_index=int(payload["coarse_level_index"]),
            fine_level_index=int(payload["fine_level_index"]),
            adjacency_equal=bool(payload["adjacency_equal"]),
            minimum_overlap=payload.get("minimum_overlap"),
            maximum_bottleneck_displacement=payload.get("maximum_bottleneck_displacement"),
            maximum_relative_width_change=payload.get("maximum_relative_width_change"),
            maximum_relative_density_change=payload.get("maximum_relative_density_change"),
            split_records=tuple(
                (tuple(item[0]), tuple(tuple(v) for v in item[1]))
                for item in payload.get("split_records", ())
            ),
            merge_records=tuple(
                (tuple(tuple(v) for v in item[0]), tuple(item[1]))
                for item in payload.get("merge_records", ())
            ),
            ambiguity_detected=bool(payload.get("ambiguity_detected", False)),
            evidence_complete=bool(payload.get("evidence_complete", True)),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError(
                "Corridor-grid pair-comparison signature mismatch."
            )
        return result


def _certificate_signature_payload(
    *,
    schema: str,
    policy_signature: str,
    ladder_signature: str,
    status: GridConvergenceStatus,
    pair_signatures: Sequence[str],
    consecutive_passing_pairs: int,
    accepted_level_index: int | None,
    reasons: Sequence[str],
    metadata: FrozenJSONMapping,
) -> dict[str, Any]:
    return {
        "schema_version": schema,
        "policy_signature": policy_signature,
        "ladder_signature": ladder_signature,
        "status": status.value,
        "pair_signatures": list(pair_signatures),
        "consecutive_passing_pairs": consecutive_passing_pairs,
        "accepted_level_index": accepted_level_index,
        "reason_codes": list(reasons),
        "metadata": metadata.to_json_dict(),
    }


@dataclass(frozen=True, slots=True)
class DensityFieldResolutionCertificate:
    policy_signature: str
    ladder_signature: str
    level_evidence: tuple[DensityFieldLevelEvidence, ...]
    pair_passed: tuple[bool, ...]
    pair_physical_resolution_eligible: tuple[bool, ...]
    status: GridConvergenceStatus | str
    consecutive_passing_pairs: int
    accepted_level_index: int | None
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_FIELD_RESOLUTION_CERTIFICATE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_FIELD_RESOLUTION_CERTIFICATE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported DensityFieldResolutionCertificate schema.")
        policy = _digest_text(self.policy_signature, name="policy_signature")
        ladder = _digest_text(self.ladder_signature, name="ladder_signature")
        levels = tuple(self.level_evidence)
        if not levels or tuple(item.level_index for item in levels) != tuple(range(len(levels))):
            raise DensityNumericalInputError("Field evidence levels must be contiguous from zero.")
        passed = tuple(bool(v) for v in self.pair_passed)
        eligible = tuple(bool(v) for v in self.pair_physical_resolution_eligible)
        if len(passed) != len(levels) - 1 or len(eligible) != len(passed):
            raise DensityNumericalInputError("Field pair vectors do not align with levels.")
        status = GridConvergenceStatus(self.status)
        consecutive = int(self.consecutive_passing_pairs)
        accepted = None if self.accepted_level_index is None else int(self.accepted_level_index)
        if status is GridConvergenceStatus.CONVERGED and accepted is None:
            raise DensityNumericalInputError("Converged field certificate requires an accepted level.")
        reasons = tuple(str(v) for v in self.reason_codes)
        metadata = freeze_json_mapping(self.metadata)
        for name, value in (
            ("policy_signature", policy), ("ladder_signature", ladder),
            ("level_evidence", levels), ("pair_passed", passed),
            ("pair_physical_resolution_eligible", eligible), ("status", status),
            ("consecutive_passing_pairs", consecutive), ("accepted_level_index", accepted),
            ("reason_codes", reasons), ("metadata", metadata),
        ):
            object.__setattr__(self, name, value)
        payload = _certificate_signature_payload(
            schema=self.schema_version,
            policy_signature=policy,
            ladder_signature=ladder,
            status=status,
            pair_signatures=[item.signature for item in levels],
            consecutive_passing_pairs=consecutive,
            accepted_level_index=accepted,
            reasons=reasons,
            metadata=metadata,
        )
        payload["pair_passed"] = list(passed)
        payload["pair_physical_resolution_eligible"] = list(eligible)
        object.__setattr__(self, "signature", _signature(payload))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_signature": self.policy_signature,
            "ladder_signature": self.ladder_signature,
            "level_evidence": [item.to_json_dict() for item in self.level_evidence],
            "pair_passed": list(self.pair_passed),
            "pair_physical_resolution_eligible": list(self.pair_physical_resolution_eligible),
            "status": self.status.value,
            "consecutive_passing_pairs": self.consecutive_passing_pairs,
            "accepted_level_index": self.accepted_level_index,
            "reason_codes": list(self.reason_codes),
            "metadata": self.metadata.to_json_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityFieldResolutionCertificate":
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            ladder_signature=str(payload["ladder_signature"]),
            level_evidence=tuple(DensityFieldLevelEvidence.from_json_dict(item) for item in payload["level_evidence"]),
            pair_passed=tuple(payload["pair_passed"]),
            pair_physical_resolution_eligible=tuple(payload["pair_physical_resolution_eligible"]),
            status=str(payload["status"]),
            consecutive_passing_pairs=int(payload["consecutive_passing_pairs"]),
            accepted_level_index=payload.get("accepted_level_index"),
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError("Field-resolution certificate signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class BasinGridConvergenceCertificate:
    policy_signature: str
    ladder_signature: str
    pair_comparisons: tuple[BasinGridPairComparison, ...]
    pair_passed: tuple[bool, ...]
    pair_physical_resolution_eligible: tuple[bool, ...]
    status: GridConvergenceStatus | str
    consecutive_passing_pairs: int
    accepted_level_index: int | None
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = BASIN_GRID_CONVERGENCE_CERTIFICATE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != BASIN_GRID_CONVERGENCE_CERTIFICATE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported BasinGridConvergenceCertificate schema.")
        policy = _digest_text(self.policy_signature, name="policy_signature")
        ladder = _digest_text(self.ladder_signature, name="ladder_signature")
        pairs = tuple(self.pair_comparisons)
        passed = tuple(bool(v) for v in self.pair_passed)
        eligible = tuple(bool(v) for v in self.pair_physical_resolution_eligible)
        if len(pairs) != len(passed) or len(pairs) != len(eligible):
            raise DensityNumericalInputError("Basin pair vectors are inconsistent.")
        if tuple((item.coarse_level_index, item.fine_level_index) for item in pairs) != tuple((i, i + 1) for i in range(len(pairs))):
            raise DensityNumericalInputError("Basin comparisons must cover consecutive levels from zero.")
        status = GridConvergenceStatus(self.status)
        consecutive = int(self.consecutive_passing_pairs)
        accepted = None if self.accepted_level_index is None else int(self.accepted_level_index)
        reasons = tuple(str(v) for v in self.reason_codes)
        metadata = freeze_json_mapping(self.metadata)
        for name, value in (
            ("policy_signature", policy), ("ladder_signature", ladder),
            ("pair_comparisons", pairs), ("pair_passed", passed),
            ("pair_physical_resolution_eligible", eligible), ("status", status),
            ("consecutive_passing_pairs", consecutive), ("accepted_level_index", accepted),
            ("reason_codes", reasons), ("metadata", metadata),
        ):
            object.__setattr__(self, name, value)
        payload = _certificate_signature_payload(
            schema=self.schema_version, policy_signature=policy,
            ladder_signature=ladder, status=status,
            pair_signatures=[item.signature for item in pairs],
            consecutive_passing_pairs=consecutive, accepted_level_index=accepted,
            reasons=reasons, metadata=metadata,
        )
        payload["pair_passed"] = list(passed)
        payload["pair_physical_resolution_eligible"] = list(eligible)
        object.__setattr__(self, "signature", _signature(payload))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_signature": self.policy_signature,
            "ladder_signature": self.ladder_signature,
            "pair_comparisons": [item.to_json_dict() for item in self.pair_comparisons],
            "pair_passed": list(self.pair_passed),
            "pair_physical_resolution_eligible": list(self.pair_physical_resolution_eligible),
            "status": self.status.value,
            "consecutive_passing_pairs": self.consecutive_passing_pairs,
            "accepted_level_index": self.accepted_level_index,
            "reason_codes": list(self.reason_codes),
            "metadata": self.metadata.to_json_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "BasinGridConvergenceCertificate":
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            ladder_signature=str(payload["ladder_signature"]),
            pair_comparisons=tuple(BasinGridPairComparison.from_json_dict(item) for item in payload["pair_comparisons"]),
            pair_passed=tuple(payload["pair_passed"]),
            pair_physical_resolution_eligible=tuple(payload["pair_physical_resolution_eligible"]),
            status=str(payload["status"]),
            consecutive_passing_pairs=int(payload["consecutive_passing_pairs"]),
            accepted_level_index=payload.get("accepted_level_index"),
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError("Basin-convergence certificate signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CorridorGridConvergenceCertificate:
    policy_signature: str
    ladder_signature: str
    pair_comparisons: tuple[CorridorGridPairComparison, ...]
    pair_passed: tuple[bool, ...]
    pair_physical_resolution_eligible: tuple[bool, ...]
    status: GridConvergenceStatus | str
    consecutive_passing_pairs: int
    accepted_level_index: int | None
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = CORRIDOR_GRID_CONVERGENCE_CERTIFICATE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != CORRIDOR_GRID_CONVERGENCE_CERTIFICATE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported CorridorGridConvergenceCertificate schema.")
        policy = _digest_text(self.policy_signature, name="policy_signature")
        ladder = _digest_text(self.ladder_signature, name="ladder_signature")
        pairs = tuple(self.pair_comparisons)
        passed = tuple(bool(v) for v in self.pair_passed)
        eligible = tuple(bool(v) for v in self.pair_physical_resolution_eligible)
        if len(pairs) != len(passed) or len(pairs) != len(eligible):
            raise DensityNumericalInputError("Corridor pair vectors are inconsistent.")
        status = GridConvergenceStatus(self.status)
        consecutive = int(self.consecutive_passing_pairs)
        accepted = None if self.accepted_level_index is None else int(self.accepted_level_index)
        reasons = tuple(str(v) for v in self.reason_codes)
        metadata = freeze_json_mapping(self.metadata)
        for name, value in (
            ("policy_signature", policy), ("ladder_signature", ladder),
            ("pair_comparisons", pairs), ("pair_passed", passed),
            ("pair_physical_resolution_eligible", eligible), ("status", status),
            ("consecutive_passing_pairs", consecutive), ("accepted_level_index", accepted),
            ("reason_codes", reasons), ("metadata", metadata),
        ):
            object.__setattr__(self, name, value)
        payload = _certificate_signature_payload(
            schema=self.schema_version, policy_signature=policy,
            ladder_signature=ladder, status=status,
            pair_signatures=[item.signature for item in pairs],
            consecutive_passing_pairs=consecutive, accepted_level_index=accepted,
            reasons=reasons, metadata=metadata,
        )
        payload["pair_passed"] = list(passed)
        payload["pair_physical_resolution_eligible"] = list(eligible)
        object.__setattr__(self, "signature", _signature(payload))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_signature": self.policy_signature,
            "ladder_signature": self.ladder_signature,
            "pair_comparisons": [item.to_json_dict() for item in self.pair_comparisons],
            "pair_passed": list(self.pair_passed),
            "pair_physical_resolution_eligible": list(self.pair_physical_resolution_eligible),
            "status": self.status.value,
            "consecutive_passing_pairs": self.consecutive_passing_pairs,
            "accepted_level_index": self.accepted_level_index,
            "reason_codes": list(self.reason_codes),
            "metadata": self.metadata.to_json_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CorridorGridConvergenceCertificate":
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            ladder_signature=str(payload["ladder_signature"]),
            pair_comparisons=tuple(CorridorGridPairComparison.from_json_dict(item) for item in payload["pair_comparisons"]),
            pair_passed=tuple(payload["pair_passed"]),
            pair_physical_resolution_eligible=tuple(payload["pair_physical_resolution_eligible"]),
            status=str(payload["status"]),
            consecutive_passing_pairs=int(payload["consecutive_passing_pairs"]),
            accepted_level_index=payload.get("accepted_level_index"),
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError("Corridor-convergence certificate signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ScientificGridRefinementBundle:
    policy: ScientificGridRefinementPolicy
    ladder: DensityNestedGridLadder
    field_certificate: DensityFieldResolutionCertificate
    basin_certificate: BasinGridConvergenceCertificate
    corridor_certificate: CorridorGridConvergenceCertificate
    schema_version: str = SCIENTIFIC_GRID_REFINEMENT_BUNDLE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != SCIENTIFIC_GRID_REFINEMENT_BUNDLE_SCHEMA:
            raise DensityNumericalSerializationError("Unsupported ScientificGridRefinementBundle schema.")
        if self.ladder.scientific_resource_signature != self.policy.scientific_resource_policy_signature:
            raise DensityNumericalInputError("Bundle ladder/resource provenance mismatch.")
        for certificate in (
            self.field_certificate,
            self.basin_certificate,
            self.corridor_certificate,
        ):
            if certificate.policy_signature != self.policy.signature or certificate.ladder_signature != self.ladder.signature:
                raise DensityNumericalInputError("Bundle certificate provenance mismatch.")
        object.__setattr__(self, "signature", _signature(self.to_json_dict(include_signature=False)))

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "policy": self.policy.to_json_dict(),
            "ladder": self.ladder.to_json_dict(),
            "field_certificate": self.field_certificate.to_json_dict(),
            "basin_certificate": self.basin_certificate.to_json_dict(),
            "corridor_certificate": self.corridor_certificate.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "ScientificGridRefinementBundle":
        result = cls(
            policy=ScientificGridRefinementPolicy.from_json_dict(payload["policy"]),
            ladder=DensityNestedGridLadder.from_json_dict(payload["ladder"]),
            field_certificate=DensityFieldResolutionCertificate.from_json_dict(payload["field_certificate"]),
            basin_certificate=BasinGridConvergenceCertificate.from_json_dict(payload["basin_certificate"]),
            corridor_certificate=CorridorGridConvergenceCertificate.from_json_dict(payload["corridor_certificate"]),
            schema_version=str(payload.get("schema_version", "")),
        )
        if payload.get("signature") not in (None, result.signature):
            raise DensityNumericalSerializationError("Scientific-grid refinement-bundle signature mismatch.")
        return result


def prepare_density_field_level_evidence(
    estimates: Sequence[PeriodicSpeciesDensityEstimate],
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
) -> tuple[DensityFieldLevelEvidence, ...]:
    """Convert fixed-kernel E1 estimates into compact GR3 field evidence."""

    values = tuple(estimates)
    if len(values) != len(ladder.levels):
        raise DensityNumericalInputError(
            "E1 estimate count must match the GR3 ladder level count."
        )
    if any(item.kernel_covariance.signature != policy.fixed_kernel_signature for item in values):
        raise DensityNumericalInputError(
            "A kernel change was detected inside the GR3 grid ladder."
        )
    if len({item.catalog_signature for item in values}) != 1 or len({item.domain.signature for item in values}) != 1:
        raise DensityNumericalInputError(
            "GR3 field levels must share source catalog and periodic domain."
        )
    records: list[DensityFieldLevelEvidence] = []
    previous_probability: np.ndarray | None = None
    previous_shape: tuple[int, int, int] | None = None
    zeros = np.zeros((3, 3), dtype=np.float64)
    for index, (estimate, geometry) in enumerate(zip(values, ladder.levels, strict=True)):
        if estimate.realization.grid_shape != geometry.grid_shape:
            raise DensityNumericalInputError(
                "E1 realization shape disagrees with the GR3 ladder."
            )
        probability = estimate.realization.probability_density_dense()
        l1: float | None = None
        linf: float | None = None
        if previous_probability is not None and previous_shape is not None:
            ratios = tuple(
                geometry.grid_shape[axis] // previous_shape[axis]
                for axis in range(3)
            )
            if any(
                geometry.grid_shape[axis] != previous_shape[axis] * ratios[axis]
                for axis in range(3)
            ):
                raise DensityNumericalInputError(
                    "GR3 field estimates are not on exactly nested logical grids."
                )
            restricted = probability[
                :: ratios[0], :: ratios[1], :: ratios[2]
            ]
            if restricted.shape != previous_probability.shape:
                raise DensityNumericalInputError(
                    "Fine-grid restriction does not reproduce the previous grid."
                )
            difference = np.abs(restricted - previous_probability)
            coarse_voxel = values[index - 1].voxel_volume
            l1 = float(np.sum(difference, dtype=np.float64) * coarse_voxel)
            linf = float(np.max(difference))
        records.append(
            DensityFieldLevelEvidence(
                level_index=index,
                grid_shape=geometry.grid_shape,
                realized_intervals=geometry.realized_intervals,
                estimate_signature=estimate.signature,
                fixed_kernel_signature=estimate.kernel_covariance.signature,
                backend=estimate.realization.backend.value,
                probability_normalization_residual=estimate.error_certificate.discrete_probability_normalization_residual,
                number_normalization_residual=estimate.error_certificate.discrete_number_normalization_residual,
                probability_l1_change_from_previous=l1,
                probability_linf_change_from_previous=linf,
                cic_covariance_cartesian=zeros,
                stencil_covariance_cartesian=zeros,
                effective_artificial_covariance_cartesian=zeros,
                metadata={
                    "direct_periodized_gaussian_evaluation": True,
                    "cic_or_stencil_convolution_used": False,
                    "source_catalog_signature": estimate.catalog_signature,
                    "domain_signature": estimate.domain.signature,
                },
            )
        )
        previous_probability = probability
        previous_shape = geometry.grid_shape
    return tuple(records)


def _basin_overlap_matrix(
    coarse: DensityAttractorCatalog,
    fine: DensityAttractorCatalog,
) -> np.ndarray:
    coarse_shape = np.asarray(coarse.cell_complex.grid_shape, dtype=np.int64)
    fine_shape = np.asarray(fine.cell_complex.grid_shape, dtype=np.int64)
    if np.any(fine_shape % coarse_shape != 0):
        raise DensityNumericalInputError(
            "Basin catalogs must use exactly nested grid shapes."
        )
    ratio = fine_shape // coarse_shape
    fine_owner = fine.cell_complex.basin_owner[
        :: int(ratio[0]), :: int(ratio[1]), :: int(ratio[2])
    ]
    fine_support = fine.cell_complex.support_mask[
        :: int(ratio[0]), :: int(ratio[1]), :: int(ratio[2])
    ]
    coarse_owner = coarse.cell_complex.basin_owner
    shared_support = coarse.cell_complex.support_mask & fine_support
    result = np.zeros((len(coarse.attractors), len(fine.attractors)), dtype=np.float64)
    for source in range(len(coarse.attractors)):
        left = shared_support & (coarse_owner == source)
        for target in range(len(fine.attractors)):
            right = shared_support & (fine_owner == target)
            union = int(np.count_nonzero(left | right))
            if union:
                result[source, target] = float(np.count_nonzero(left & right) / union)
    return result


def compare_basin_catalog_pair(
    coarse: DensityAttractorCatalog,
    fine: DensityAttractorCatalog,
    *,
    coarse_level_index: int,
    cell: Any,
    policy: ScientificGridRefinementPolicy,
) -> BasinGridPairComparison:
    """Match two E2 catalogs using the signed SAMP0 correspondence policy."""

    if coarse.domain_signature != fine.domain_signature:
        raise DensityNumericalInputError("Basin catalogs use different periodic domains.")
    if coarse.covariance_signature != policy.fixed_kernel_signature or fine.covariance_signature != policy.fixed_kernel_signature:
        raise DensityNumericalInputError("Basin catalogs changed the fixed GR3 kernel.")
    matrix = _basin_overlap_matrix(coarse, fine)
    n_source, n_target = matrix.shape
    if n_source == 0 or n_target == 0:
        return BasinGridPairComparison(
            coarse_level_index=coarse_level_index,
            fine_level_index=coarse_level_index + 1,
            coarse_catalog_signature=coarse.signature,
            fine_catalog_signature=fine.signature,
            coarse_count=n_source,
            fine_count=n_target,
            correspondences=(),
            source_unmatched=tuple(range(n_source)),
            target_unmatched=tuple(range(n_target)),
        )
    cell_matrix = np.asarray(cell, dtype=np.float64)
    probability_scale = max(
        max((item.basin_probability for item in coarse.attractors), default=0.0),
        max((item.basin_probability for item in fine.attractors), default=0.0),
        np.finfo(np.float64).tiny,
    )
    cost = np.full((n_source, n_target), np.inf, dtype=np.float64)
    distances = np.zeros_like(cost)
    probability_changes = np.zeros_like(cost)
    for i, source in enumerate(coarse.attractors):
        for j, target in enumerate(fine.attractors):
            distance = _periodic_distance(source.anchor_fractional, target.anchor_fractional, cell_matrix)
            probability_change = abs(source.basin_probability - target.basin_probability)
            distances[i, j] = distance
            probability_changes[i, j] = probability_change
            cost[i, j] = policy.correspondence_policy.normalized_cost(
                distance=distance,
                overlap=float(matrix[i, j]),
                probability_left=source.basin_probability,
                probability_right=target.basin_probability,
                sigma_min=policy.sigma_min,
                probability_scale=probability_scale,
                left_type=_feature_type(source.geometry),
                right_type=_feature_type(target.geometry),
            )
    finite_cost = np.where(np.isfinite(cost), cost, 1.0e100)
    rows, columns = linear_sum_assignment(finite_cost)
    selected: list[FeatureGridCorrespondence] = []
    selected_sources: set[int] = set()
    selected_targets: set[int] = set()
    ambiguity_detected = False
    for row, column in sorted(zip(rows.tolist(), columns.tolist(), strict=True)):
        selected_cost = float(cost[row, column])
        if not np.isfinite(selected_cost) or selected_cost > policy.correspondence_policy.maximum_assignment_cost:
            continue
        alternatives = [
            float(cost[row, other])
            for other in range(n_target)
            if other != column and np.isfinite(cost[row, other])
        ] + [
            float(cost[other, column])
            for other in range(n_source)
            if other != row and np.isfinite(cost[other, column])
        ]
        ambiguous = bool(
            alternatives
            and min(alternatives) - selected_cost
            <= policy.correspondence_policy.ambiguity_margin
        )
        ambiguity_detected |= ambiguous
        selected.append(
            FeatureGridCorrespondence(
                source_feature_id=row,
                target_feature_id=column,
                normalized_cost=selected_cost,
                anchor_displacement=float(distances[row, column]),
                overlap=float(matrix[row, column]),
                probability_change=float(probability_changes[row, column]),
                ambiguous=ambiguous,
            )
        )
        selected_sources.add(row)
        selected_targets.add(column)
    admissible = (cost <= policy.correspondence_policy.maximum_assignment_cost) & (matrix > 0.0)
    splits = tuple(
        (source, tuple(int(v) for v in np.flatnonzero(admissible[source])))
        for source in range(n_source)
        if int(np.count_nonzero(admissible[source])) > 1
    )
    merges = tuple(
        (tuple(int(v) for v in np.flatnonzero(admissible[:, target])), target)
        for target in range(n_target)
        if int(np.count_nonzero(admissible[:, target])) > 1
    )
    return BasinGridPairComparison(
        coarse_level_index=coarse_level_index,
        fine_level_index=coarse_level_index + 1,
        coarse_catalog_signature=coarse.signature,
        fine_catalog_signature=fine.signature,
        coarse_count=n_source,
        fine_count=n_target,
        correspondences=tuple(selected),
        source_unmatched=tuple(sorted(set(range(n_source)) - selected_sources)),
        target_unmatched=tuple(sorted(set(range(n_target)) - selected_targets)),
        split_records=splits,
        merge_records=merges,
        ambiguity_detected=ambiguity_detected,
    )


def prepare_basin_grid_pair_comparisons(
    catalogs: Sequence[DensityAttractorCatalog],
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
    *,
    cell: Any,
) -> tuple[BasinGridPairComparison, ...]:
    values = tuple(catalogs)
    if len(values) != len(ladder.levels):
        raise DensityNumericalInputError(
            "E2 catalog count must match the GR3 ladder level count."
        )
    if any(item.cell_complex.grid_shape != geometry.grid_shape for item, geometry in zip(values, ladder.levels, strict=True)):
        raise DensityNumericalInputError("E2 catalog shapes disagree with the GR3 ladder.")
    return tuple(
        compare_basin_catalog_pair(
            coarse,
            fine,
            coarse_level_index=index,
            cell=cell,
            policy=policy,
        )
        for index, (coarse, fine) in enumerate(zip(values[:-1], values[1:], strict=True))
    )


def compare_corridor_level_pair(
    coarse: CorridorGridLevelEvidence,
    fine: CorridorGridLevelEvidence,
    *,
    cell: Any,
) -> CorridorGridPairComparison:
    if fine.level_index != coarse.level_index + 1:
        raise DensityNumericalInputError("Corridor levels must be consecutive.")
    coarse_pairs = set(coarse.adjacency_pairs)
    fine_pairs = set(fine.adjacency_pairs)
    adjacency_equal = coarse_pairs == fine_pairs
    if not adjacency_equal:
        return CorridorGridPairComparison(
            coarse_level_index=coarse.level_index,
            fine_level_index=fine.level_index,
            adjacency_equal=False,
            minimum_overlap=None,
            maximum_bottleneck_displacement=None,
            maximum_relative_width_change=None,
            maximum_relative_density_change=None,
            evidence_complete=False,
        )
    coarse_bottleneck = dict(coarse.bottleneck_fractional_by_pair)
    fine_bottleneck = dict(fine.bottleneck_fractional_by_pair)
    coarse_width = dict(coarse.width_by_pair)
    fine_width = dict(fine.width_by_pair)
    coarse_density = dict(coarse.density_by_pair)
    fine_density = dict(fine.density_by_pair)
    coarse_support = dict(coarse.support_nodes_by_pair)
    fine_support = dict(fine.support_nodes_by_pair)
    cell_matrix = np.asarray(cell, dtype=np.float64)
    displacements: list[float] = []
    width_changes: list[float] = []
    density_changes: list[float] = []
    overlaps: list[float] = []
    for pair in sorted(coarse_pairs):
        displacements.append(
            _periodic_distance(coarse_bottleneck[pair], fine_bottleneck[pair], cell_matrix)
        )
        width_changes.append(
            abs(fine_width[pair] - coarse_width[pair])
            / max(abs(coarse_width[pair]), np.finfo(np.float64).tiny)
        )
        density_changes.append(
            abs(fine_density[pair] - coarse_density[pair])
            / max(abs(coarse_density[pair]), np.finfo(np.float64).tiny)
        )
        if coarse_support and fine_support:
            left = set(coarse_support[pair])
            right = set(fine_support[pair])
            union = left | right
            overlaps.append(1.0 if not union else len(left & right) / len(union))
        else:
            overlaps.append(1.0)
    return CorridorGridPairComparison(
        coarse_level_index=coarse.level_index,
        fine_level_index=fine.level_index,
        adjacency_equal=True,
        minimum_overlap=min(overlaps, default=1.0),
        maximum_bottleneck_displacement=max(displacements, default=0.0),
        maximum_relative_width_change=max(width_changes, default=0.0),
        maximum_relative_density_change=max(density_changes, default=0.0),
        evidence_complete=True,
    )


def prepare_corridor_grid_pair_comparisons(
    levels: Sequence[CorridorGridLevelEvidence],
    *,
    cell: Any,
) -> tuple[CorridorGridPairComparison, ...]:
    values = tuple(levels)
    if not values:
        return ()
    if tuple(item.level_index for item in values) != tuple(range(len(values))):
        raise DensityNumericalInputError("Corridor evidence levels must be contiguous from zero.")
    return tuple(
        compare_corridor_level_pair(coarse, fine, cell=cell)
        for coarse, fine in zip(values[:-1], values[1:], strict=True)
    )


def _pair_eligibility(
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
) -> tuple[bool, ...]:
    return tuple(
        max(fine.realized_intervals) / policy.sigma_min
        <= policy.stopping_policy.target_max_interval_to_sigma_min * (1.0 + 5.0e-15)
        for fine in ladder.levels[1:]
    )


def certify_density_field_resolution(
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
    level_evidence: Sequence[DensityFieldLevelEvidence],
) -> DensityFieldResolutionCertificate:
    levels = tuple(level_evidence)
    if len(levels) != len(ladder.levels):
        raise DensityNumericalInputError("Field evidence must cover every ladder level.")
    if any(item.fixed_kernel_signature != policy.fixed_kernel_signature for item in levels):
        raise DensityNumericalInputError("A kernel change was detected inside the GR3 ladder.")
    for item, geometry in zip(levels, ladder.levels, strict=True):
        if item.grid_shape != geometry.grid_shape or not np.allclose(item.realized_intervals, geometry.realized_intervals, rtol=0.0, atol=5e-14):
            raise DensityNumericalInputError("Field evidence geometry disagrees with the GR3 ladder.")
    eligible = _pair_eligibility(ladder, policy)
    stopping = policy.stopping_policy
    passed = tuple(
        bool(
            levels[index + 1].probability_l1_change_from_previous
            <= stopping.maximum_field_probability_l1_change
            and levels[index].probability_normalization_residual
            <= stopping.maximum_field_normalization_residual
            and levels[index].number_normalization_residual
            <= stopping.maximum_field_normalization_residual
            and levels[index + 1].probability_normalization_residual
            <= stopping.maximum_field_normalization_residual
            and levels[index + 1].number_normalization_residual
            <= stopping.maximum_field_normalization_residual
        )
        for index in range(len(levels) - 1)
    )
    consecutive = _consecutive_tail_passes(passed, eligible)
    if consecutive >= stopping.consecutive_passing_level_pairs:
        status = GridConvergenceStatus.CONVERGED
        accepted = len(levels) - 1
        reasons: tuple[str, ...] = ()
    else:
        status = _status_for_unpassed_ladder(ladder)
        if status is GridConvergenceStatus.UNRESOLVED_DUE_TO_INSUFFICIENT_PASSING_LEVELS:
            status = GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE
        accepted = None
        reasons = (status.value,)
    return DensityFieldResolutionCertificate(
        policy_signature=policy.signature,
        ladder_signature=ladder.signature,
        level_evidence=levels,
        pair_passed=passed,
        pair_physical_resolution_eligible=eligible,
        status=status,
        consecutive_passing_pairs=consecutive,
        accepted_level_index=accepted,
        reason_codes=reasons,
        metadata={
            "fixed_kernel_signature": policy.fixed_kernel_signature,
            "sigma_min": policy.sigma_min,
            "target_max_interval_to_sigma_min": stopping.target_max_interval_to_sigma_min,
            "scientific_resource_policy_signature": policy.scientific_resource_policy_signature,
        },
    )


def certify_basin_grid_convergence(
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
    pair_comparisons: Sequence[BasinGridPairComparison],
) -> BasinGridConvergenceCertificate:
    pairs = tuple(pair_comparisons)
    eligible = _pair_eligibility(ladder, policy)
    if len(pairs) != len(eligible):
        raise DensityNumericalInputError("Basin comparisons must cover every ladder pair.")
    stopping = policy.stopping_policy
    passed: list[bool] = []
    for pair in pairs:
        anchor = pair.maximum_anchor_displacement
        overlap = pair.minimum_overlap
        probability = pair.maximum_probability_change
        pair_passed = bool(
            (not stopping.require_unchanged_basin_count or pair.coarse_count == pair.fine_count)
            and not pair.source_unmatched
            and not pair.target_unmatched
            and not pair.split_records
            and not pair.merge_records
            and (not stopping.require_unambiguous_basin_correspondence or not pair.ambiguity_detected)
            and anchor is not None
            and anchor <= stopping.maximum_basin_anchor_displacement_sigma * policy.sigma_min
            and overlap is not None
            and overlap >= stopping.minimum_basin_overlap
            and probability is not None
            and probability <= stopping.maximum_basin_probability_change
        )
        passed.append(pair_passed)
    passed_tuple = tuple(passed)
    consecutive = _consecutive_tail_passes(passed_tuple, eligible)
    if consecutive >= stopping.consecutive_passing_level_pairs:
        status = GridConvergenceStatus.CONVERGED
        accepted = len(ladder.levels) - 1
        reasons: tuple[str, ...] = ()
    else:
        status = _status_for_unpassed_ladder(ladder)
        if status is GridConvergenceStatus.UNRESOLVED_DUE_TO_INSUFFICIENT_PASSING_LEVELS:
            status = GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE
        accepted = None
        reasons = (status.value,)
    return BasinGridConvergenceCertificate(
        policy_signature=policy.signature,
        ladder_signature=ladder.signature,
        pair_comparisons=pairs,
        pair_passed=passed_tuple,
        pair_physical_resolution_eligible=eligible,
        status=status,
        consecutive_passing_pairs=consecutive,
        accepted_level_index=accepted,
        reason_codes=reasons,
        metadata={
            "correspondence_policy_signature": policy.correspondence_policy.signature,
            "fixed_kernel_signature": policy.fixed_kernel_signature,
        },
    )


def certify_corridor_grid_convergence(
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
    pair_comparisons: Sequence[CorridorGridPairComparison],
) -> CorridorGridConvergenceCertificate:
    pairs = tuple(pair_comparisons)
    eligible = _pair_eligibility(ladder, policy)
    if not pairs:
        return CorridorGridConvergenceCertificate(
            policy_signature=policy.signature,
            ladder_signature=ladder.signature,
            pair_comparisons=(),
            pair_passed=(),
            pair_physical_resolution_eligible=(),
            status=GridConvergenceStatus.UNRESOLVED_DUE_TO_MISSING_EVIDENCE,
            consecutive_passing_pairs=0,
            accepted_level_index=None,
            reason_codes=("corridor_width_or_support_evidence_unavailable",),
            metadata={"basin_convergence_does_not_imply_corridor_convergence": True},
        )
    if len(pairs) != len(eligible):
        raise DensityNumericalInputError("Corridor comparisons must cover every ladder pair.")
    stopping = policy.stopping_policy
    passed = tuple(
        bool(
            pair.evidence_complete
            and (not stopping.require_unchanged_corridor_adjacency or pair.adjacency_equal)
            and pair.minimum_overlap is not None
            and pair.minimum_overlap >= stopping.minimum_corridor_overlap
            and pair.maximum_bottleneck_displacement is not None
            and pair.maximum_bottleneck_displacement <= stopping.maximum_bottleneck_displacement_sigma * policy.sigma_min
            and pair.maximum_relative_width_change is not None
            and pair.maximum_relative_width_change <= stopping.maximum_corridor_relative_width_change
            and pair.maximum_relative_density_change is not None
            and pair.maximum_relative_density_change <= stopping.maximum_corridor_relative_density_change
            and not pair.split_records
            and not pair.merge_records
            and (not stopping.require_unambiguous_corridor_correspondence or not pair.ambiguity_detected)
        )
        for pair in pairs
    )
    consecutive = _consecutive_tail_passes(passed, eligible)
    if consecutive >= stopping.consecutive_passing_level_pairs:
        status = GridConvergenceStatus.CONVERGED
        accepted = len(ladder.levels) - 1
        reasons: tuple[str, ...] = ()
    else:
        status = _status_for_unpassed_ladder(ladder)
        if status is GridConvergenceStatus.UNRESOLVED_DUE_TO_INSUFFICIENT_PASSING_LEVELS:
            status = GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE
        accepted = None
        reasons = (status.value,)
    return CorridorGridConvergenceCertificate(
        policy_signature=policy.signature,
        ladder_signature=ladder.signature,
        pair_comparisons=pairs,
        pair_passed=passed,
        pair_physical_resolution_eligible=eligible,
        status=status,
        consecutive_passing_pairs=consecutive,
        accepted_level_index=accepted,
        reason_codes=reasons,
        metadata={
            "fixed_kernel_signature": policy.fixed_kernel_signature,
            "basin_convergence_does_not_imply_corridor_convergence": True,
        },
    )


def prepare_scientific_grid_refinement_bundle(
    ladder: DensityNestedGridLadder,
    policy: ScientificGridRefinementPolicy,
    *,
    field_level_evidence: Sequence[DensityFieldLevelEvidence],
    basin_pair_comparisons: Sequence[BasinGridPairComparison],
    corridor_pair_comparisons: Sequence[CorridorGridPairComparison] = (),
) -> ScientificGridRefinementBundle:
    """Certify one fixed-kernel grid ladder without combining the three verdicts."""

    if ladder.scientific_resource_signature != policy.scientific_resource_policy_signature:
        raise DensityNumericalInputError("Ladder/resource provenance disagrees with GR3 policy.")
    field_certificate = certify_density_field_resolution(
        ladder, policy, field_level_evidence
    )
    basin_certificate = certify_basin_grid_convergence(
        ladder, policy, basin_pair_comparisons
    )
    corridor_certificate = certify_corridor_grid_convergence(
        ladder, policy, corridor_pair_comparisons
    )
    return ScientificGridRefinementBundle(
        policy=policy,
        ladder=ladder,
        field_certificate=field_certificate,
        basin_certificate=basin_certificate,
        corridor_certificate=corridor_certificate,
    )


__all__ = [
    "GRID_CONVERGENCE_STOPPING_POLICY_SCHEMA",
    "SCIENTIFIC_GRID_REFINEMENT_POLICY_SCHEMA",
    "DENSITY_FIELD_LEVEL_EVIDENCE_SCHEMA",
    "FEATURE_GRID_CORRESPONDENCE_SCHEMA",
    "BASIN_GRID_PAIR_COMPARISON_SCHEMA",
    "CORRIDOR_GRID_LEVEL_EVIDENCE_SCHEMA",
    "CORRIDOR_GRID_PAIR_COMPARISON_SCHEMA",
    "DENSITY_FIELD_RESOLUTION_CERTIFICATE_SCHEMA",
    "BASIN_GRID_CONVERGENCE_CERTIFICATE_SCHEMA",
    "CORRIDOR_GRID_CONVERGENCE_CERTIFICATE_SCHEMA",
    "SCIENTIFIC_GRID_REFINEMENT_BUNDLE_SCHEMA",
    "GRID_CONVERGENCE_STOPPING_POLICY_VERSION",
    "GridConvergenceStatus",
    "GridConvergenceStoppingPolicy",
    "ScientificGridRefinementPolicy",
    "DensityFieldLevelEvidence",
    "FeatureGridCorrespondence",
    "BasinGridPairComparison",
    "CorridorGridLevelEvidence",
    "CorridorGridPairComparison",
    "DensityFieldResolutionCertificate",
    "BasinGridConvergenceCertificate",
    "CorridorGridConvergenceCertificate",
    "ScientificGridRefinementBundle",
    "plan_scientific_grid_refinement",
    "prepare_density_field_level_evidence",
    "compare_basin_catalog_pair",
    "prepare_basin_grid_pair_comparisons",
    "compare_corridor_level_pair",
    "prepare_corridor_grid_pair_comparisons",
    "certify_density_field_resolution",
    "certify_basin_grid_convergence",
    "certify_corridor_grid_convergence",
    "prepare_scientific_grid_refinement_bundle",
]
