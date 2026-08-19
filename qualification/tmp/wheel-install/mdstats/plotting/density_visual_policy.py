"""Stage 11E-GR2 plotting adaptation over common density-grid records.

This module preserves the established atomic/framework visual-resolution policy
while binding its resolved grid to analysis-owned GR0 geometry and GR1 planning
records.  It deliberately owns no field production, mesh extraction, browser
admission, or scientific fixed-kernel convergence policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from ..analysis.density.grid_geometry import (
    DensityGridGeometry,
    density_grid_intervals,
    prepare_density_grid_geometry,
)
from ..analysis.density.numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalResourceError,
    DensityNumericalSerializationError,
)
from ..analysis.density.planning import (
    DensityLogicalGridPlan,
    density_logical_grid_signature,
    plan_finest_feasible_density_grid,
)
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError

DENSITY_VISUAL_GRID_ADAPTATION_SCHEMA = (
    "mdstats.density-visual-grid-adaptation.v1"
)
DENSITY_VISUAL_POLICY_ID = "mdstats.plotting-density-visual-policy.v1"


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


def _finite_nonnegative(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise GraphStyleError(f"{name} must be finite and nonnegative.")
    return result


def _finite_positive(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GraphStyleError(f"{name} must be finite and positive.")
    return result


def _optional_finite_nonnegative(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    return _finite_nonnegative(value, name=name)


def _representative_interval_for_exact_shape(
    cell: Any, shape: tuple[int, int, int]
) -> float:
    """Return an interval strictly inside the shape's ceil-mapping plateau."""

    matrix = np.asarray(cell, dtype=np.float64)
    counts = np.asarray(shape, dtype=np.int64)
    lengths = np.linalg.norm(matrix, axis=1)
    lower = float(np.max(lengths / counts.astype(np.float64)))
    upper_candidates = [
        float(lengths[index] / (int(counts[index]) - 1))
        for index in range(3)
        if int(counts[index]) > 4
    ]
    upper = min(upper_candidates) if upper_candidates else float("inf")
    if not np.isfinite(upper):
        return float(np.nextafter(lower, np.inf))
    if upper <= lower:
        return float(np.nextafter(lower, np.inf))
    return 0.5 * (lower + upper)


def _translate_common_error(error: Exception) -> GraphAdapterError:
    if isinstance(error, DensityNumericalResourceError):
        return GraphComplexityError(str(error))
    if isinstance(error, DensityNumericalSerializationError):
        return GraphAdapterError(str(error))
    if isinstance(error, DensityNumericalInputError):
        return GraphAdapterError(str(error))
    return GraphAdapterError(str(error))


@dataclass(frozen=True, slots=True)
class DensityVisualGridAdaptation:
    """Signed plotting view of one GR0 geometry and optional GR1 replay plan."""

    consumer_kind: str
    grid_geometry: DensityGridGeometry
    common_grid_plan: DensityLogicalGridPlan | None
    grid_definition: str
    grid_interval_target: float
    gaussian_bandwidth: float
    gaussian_to_grid_ratio_target: float
    smearing_definition: str
    adaptive_smearing_enabled: bool
    adaptive_smearing_triggered: bool
    adaptive_smearing_budget_limited: bool
    adaptive_target_defined: bool
    adaptive_target_width: float | None
    adaptive_target_achieved: bool | None
    max_smearing_to_sample_sd_ratio: float
    resolution_reference_source: str
    diagnostic_metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    warning_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    visual_policy_id: str = DENSITY_VISUAL_POLICY_ID
    schema_version: str = DENSITY_VISUAL_GRID_ADAPTATION_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_VISUAL_GRID_ADAPTATION_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported visual-grid adaptation schema {self.schema_version!r}."
            )
        if self.visual_policy_id != DENSITY_VISUAL_POLICY_ID:
            raise GraphAdapterError(
                f"Unsupported plotting visual policy {self.visual_policy_id!r}."
            )
        if self.consumer_kind not in {"atomic", "framework"}:
            raise GraphAdapterError("consumer_kind must be 'atomic' or 'framework'.")
        if not isinstance(self.grid_geometry, DensityGridGeometry):
            raise TypeError("grid_geometry must be DensityGridGeometry.")
        if self.common_grid_plan is not None:
            if not isinstance(self.common_grid_plan, DensityLogicalGridPlan):
                raise TypeError(
                    "common_grid_plan must be DensityLogicalGridPlan or None."
                )
            if (
                density_logical_grid_signature(
                    self.common_grid_plan.selected_geometry
                )
                != density_logical_grid_signature(self.grid_geometry)
            ):
                raise GraphAdapterError(
                    "The GR1 replay plan selects a different logical grid."
                )
        if self.grid_definition not in {"explicit_shape", "target_lattice_interval"}:
            raise GraphAdapterError("Unsupported plotting grid_definition.")
        interval = _finite_positive(
            self.grid_interval_target, name="grid_interval_target"
        )
        bandwidth = _finite_nonnegative(
            self.gaussian_bandwidth, name="gaussian_bandwidth"
        )
        ratio = _finite_positive(
            self.gaussian_to_grid_ratio_target,
            name="gaussian_to_grid_ratio_target",
        )
        max_ratio = _finite_positive(
            self.max_smearing_to_sample_sd_ratio,
            name="max_smearing_to_sample_sd_ratio",
        )
        if not self.smearing_definition:
            raise GraphAdapterError("smearing_definition must be nonempty.")
        for name in (
            "adaptive_smearing_enabled",
            "adaptive_smearing_triggered",
            "adaptive_smearing_budget_limited",
            "adaptive_target_defined",
        ):
            if not isinstance(getattr(self, name), bool):
                raise GraphAdapterError(f"{name} must be Boolean.")
        target_width = _optional_finite_nonnegative(
            self.adaptive_target_width, name="adaptive_target_width"
        )
        achieved = self.adaptive_target_achieved
        if achieved is not None and not isinstance(achieved, bool):
            raise GraphAdapterError("adaptive_target_achieved must be Boolean or None.")
        if not self.adaptive_target_defined:
            if target_width is not None or achieved is not None:
                raise GraphAdapterError(
                    "Undefined adaptive targets cannot carry a width or achievement state."
                )
        elif target_width is None and achieved is not None:
            raise GraphAdapterError(
                "A target without an explicit width cannot carry achievement state."
            )
        if self.adaptive_smearing_budget_limited and not self.adaptive_smearing_triggered:
            raise GraphAdapterError(
                "A budget-limited visual refinement must have been triggered."
            )
        if self.grid_definition == "explicit_shape" and self.common_grid_plan is not None:
            raise GraphAdapterError(
                "Explicit plotting grids do not require an automatic GR1 replay plan."
            )
        if self.grid_definition == "target_lattice_interval" and self.common_grid_plan is None:
            raise GraphAdapterError(
                "Interval-derived plotting grids require a GR1 replay plan."
            )
        source = str(self.resolution_reference_source)
        if not source:
            raise GraphAdapterError("resolution_reference_source must be nonempty.")
        warning_codes = tuple(str(value) for value in self.warning_codes)
        if any(not value for value in warning_codes):
            raise GraphAdapterError("warning_codes must contain nonempty strings.")
        if len(set(warning_codes)) != len(warning_codes):
            raise GraphAdapterError("warning_codes must be unique.")
        object.__setattr__(self, "grid_interval_target", interval)
        object.__setattr__(self, "gaussian_bandwidth", bandwidth)
        object.__setattr__(self, "gaussian_to_grid_ratio_target", ratio)
        object.__setattr__(self, "max_smearing_to_sample_sd_ratio", max_ratio)
        object.__setattr__(self, "adaptive_target_width", target_width)
        object.__setattr__(self, "resolution_reference_source", source)
        object.__setattr__(self, "warning_codes", warning_codes)
        object.__setattr__(
            self, "diagnostic_metadata", freeze_json_mapping(self.diagnostic_metadata)
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        object.__setattr__(
            self, "signature", _signature(self.to_json_dict(include_signature=False))
        )

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.grid_geometry.grid_shape

    @property
    def realized_intervals(self) -> tuple[float, float, float]:
        return self.grid_geometry.realized_intervals

    @property
    def logical_node_count(self) -> int:
        return self.grid_geometry.logical_voxel_count

    @property
    def longest_grid_interval(self) -> float:
        return self.grid_geometry.longest_grid_interval

    @property
    def common_grid_signature(self) -> str:
        return density_logical_grid_signature(self.grid_geometry)

    def grid_metadata_dict(self) -> dict[str, Any]:
        """Return the established plotting grid metadata without new keys."""

        return {
            "grid_definition": self.grid_definition,
            "grid_shape": self.grid_shape,
            "logical_node_count": self.logical_node_count,
            "grid_interval_target": self.grid_interval_target,
            "grid_intervals_realized": self.realized_intervals,
        }

    def diagnostic_metadata_dict(self) -> dict[str, Any]:
        """Return unchanged spread/reciprocal/broadening metadata."""

        return {key: value for key, value in self.diagnostic_metadata.items()}

    def visual_metadata_dict(self) -> dict[str, Any]:
        """Return the established visual-resolution metadata without new keys."""

        longest = self.longest_grid_interval
        result = {
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "gaussian_to_grid_ratio_target": self.gaussian_to_grid_ratio_target,
            "gaussian_to_longest_grid_interval_realized": (
                self.gaussian_bandwidth / longest
                if longest > 0.0
                else float("inf")
            ),
            "smearing_definition": self.smearing_definition,
            "adaptive_smearing_enabled": self.adaptive_smearing_enabled,
            "adaptive_smearing_triggered": self.adaptive_smearing_triggered,
            "adaptive_smearing_budget_limited": self.adaptive_smearing_budget_limited,
            "adaptive_target_defined": self.adaptive_target_defined,
            "adaptive_target_width": self.adaptive_target_width,
            "adaptive_target_achieved": self.adaptive_target_achieved,
            "max_smearing_to_sample_sd_ratio": self.max_smearing_to_sample_sd_ratio,
            "resolution_reference_source": self.resolution_reference_source,
        }
        result.update(self.diagnostic_metadata_dict())
        return result

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "visual_policy_id": self.visual_policy_id,
            "consumer_kind": self.consumer_kind,
            "grid_geometry": self.grid_geometry.to_json_dict(),
            "common_grid_plan": (
                None
                if self.common_grid_plan is None
                else self.common_grid_plan.to_json_dict()
            ),
            "grid_definition": self.grid_definition,
            "grid_interval_target": self.grid_interval_target,
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "gaussian_to_grid_ratio_target": self.gaussian_to_grid_ratio_target,
            "smearing_definition": self.smearing_definition,
            "adaptive_smearing_enabled": self.adaptive_smearing_enabled,
            "adaptive_smearing_triggered": self.adaptive_smearing_triggered,
            "adaptive_smearing_budget_limited": self.adaptive_smearing_budget_limited,
            "adaptive_target_defined": self.adaptive_target_defined,
            "adaptive_target_width": self.adaptive_target_width,
            "adaptive_target_achieved": self.adaptive_target_achieved,
            "max_smearing_to_sample_sd_ratio": self.max_smearing_to_sample_sd_ratio,
            "resolution_reference_source": self.resolution_reference_source,
            "diagnostic_metadata": self.diagnostic_metadata.to_json_dict(),
            "warning_codes": list(self.warning_codes),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any]
    ) -> "DensityVisualGridAdaptation":
        expected = payload.get("signature")
        plan_payload = payload.get("common_grid_plan")
        try:
            result = cls(
                consumer_kind=str(payload["consumer_kind"]),
                grid_geometry=DensityGridGeometry.from_json_dict(
                    payload["grid_geometry"]
                ),
                common_grid_plan=(
                    None
                    if plan_payload is None
                    else DensityLogicalGridPlan.from_json_dict(plan_payload)
                ),
                grid_definition=str(payload["grid_definition"]),
                grid_interval_target=payload["grid_interval_target"],
                gaussian_bandwidth=payload["gaussian_bandwidth"],
                gaussian_to_grid_ratio_target=payload[
                    "gaussian_to_grid_ratio_target"
                ],
                smearing_definition=str(payload["smearing_definition"]),
                adaptive_smearing_enabled=payload["adaptive_smearing_enabled"],
                adaptive_smearing_triggered=payload[
                    "adaptive_smearing_triggered"
                ],
                adaptive_smearing_budget_limited=payload[
                    "adaptive_smearing_budget_limited"
                ],
                adaptive_target_defined=payload["adaptive_target_defined"],
                adaptive_target_width=payload.get("adaptive_target_width"),
                adaptive_target_achieved=payload.get("adaptive_target_achieved"),
                max_smearing_to_sample_sd_ratio=payload[
                    "max_smearing_to_sample_sd_ratio"
                ],
                resolution_reference_source=str(
                    payload["resolution_reference_source"]
                ),
                diagnostic_metadata=payload.get("diagnostic_metadata", {}),
                warning_codes=tuple(payload.get("warning_codes", ())),
                metadata=payload.get("metadata", {}),
                visual_policy_id=str(payload.get("visual_policy_id", "")),
                schema_version=str(payload.get("schema_version", "")),
            )
        except (
            DensityNumericalInputError,
            DensityNumericalResourceError,
            DensityNumericalSerializationError,
        ) as error:
            raise _translate_common_error(error) from error
        if expected is not None and str(expected) != result.signature:
            raise GraphAdapterError("Visual-grid adaptation signature mismatch.")
        return result


def prepare_density_visual_grid_adaptation(
    cell: Any,
    *,
    options: Any,
    resolved_numerics: Any,
    max_logical_voxels: int,
    consumer_kind: str,
    resolution_reference_source: str,
    metadata: Mapping[str, Any] | None = None,
) -> DensityVisualGridAdaptation:
    """Bind resolved plotting numerics to common GR0/GR1 records.

    The caller's visual resolver remains authoritative.  This function verifies
    and signs its outcome; it does not alter the selected grid or bandwidth.
    """

    try:
        shape = tuple(int(value) for value in resolved_numerics.grid_shape)
        geometry = prepare_density_grid_geometry(cell, grid_shape=shape)
        supplied_intervals = tuple(
            float(value) for value in resolved_numerics.realized_intervals
        )
        common_intervals = density_grid_intervals(cell, shape)
        if not np.allclose(
            supplied_intervals, common_intervals, rtol=0.0, atol=5.0e-15
        ):
            raise GraphAdapterError(
                "Resolved plotting intervals disagree with common GR0 geometry."
            )

        explicit_shape = options.grid_shape is not None
        grid_definition = (
            "explicit_shape" if explicit_shape else "target_lattice_interval"
        )
        common_plan: DensityLogicalGridPlan | None = None
        if not explicit_shape:
            replay_interval = _representative_interval_for_exact_shape(cell, shape)
            coarsest = max(float(options.grid_interval), replay_interval)
            common_plan = plan_finest_feasible_density_grid(
                cell,
                target_interval=replay_interval,
                coarsest_interval=coarsest,
                max_logical_voxels=int(max_logical_voxels),
                metadata={
                    "planner_role": "selected_visual_grid_replay",
                    "consumer_kind": consumer_kind,
                },
            )
            if common_plan.selected_geometry.grid_shape != shape:
                raise GraphAdapterError(
                    "The GR1 replay plan did not reproduce the resolved visual grid."
                )

        diagnostic_metadata: dict[str, Any] = {
            **resolved_numerics.spread_diagnostics.metadata_dict(),
            **resolved_numerics.reciprocal_resolution.metadata_dict(),
        }
        broadening = resolved_numerics.broadening_diagnostic
        if broadening is not None:
            diagnostic_metadata.update(broadening.metadata_dict())
            diagnostic_metadata["adaptive_target_ratio"] = (
                None
                if resolved_numerics.adaptive_target_width is None
                else broadening.effective_rms
                / resolved_numerics.adaptive_target_width
            )

        warning_codes: list[str] = []
        if bool(resolved_numerics.adaptive_triggered):
            warning_codes.append("adaptive_visual_refinement")
        if bool(resolved_numerics.adaptive_budget_limited):
            warning_codes.append("visual_resolution_budget_limited")
        if resolved_numerics.adaptive_target_achieved is False:
            warning_codes.append("visual_target_unresolved")

        return DensityVisualGridAdaptation(
            consumer_kind=consumer_kind,
            grid_geometry=geometry,
            common_grid_plan=common_plan,
            grid_definition=grid_definition,
            grid_interval_target=float(options.grid_interval),
            gaussian_bandwidth=float(resolved_numerics.gaussian_bandwidth),
            gaussian_to_grid_ratio_target=float(options.gaussian_to_grid_ratio),
            smearing_definition=str(resolved_numerics.smearing_definition),
            adaptive_smearing_enabled=bool(options.adaptive_smearing),
            adaptive_smearing_triggered=bool(
                resolved_numerics.adaptive_triggered
            ),
            adaptive_smearing_budget_limited=bool(
                resolved_numerics.adaptive_budget_limited
            ),
            adaptive_target_defined=bool(
                resolved_numerics.adaptive_target_defined
            ),
            adaptive_target_width=resolved_numerics.adaptive_target_width,
            adaptive_target_achieved=resolved_numerics.adaptive_target_achieved,
            max_smearing_to_sample_sd_ratio=float(
                options.max_smearing_to_sample_sd_ratio
            ),
            resolution_reference_source=resolution_reference_source,
            diagnostic_metadata=diagnostic_metadata,
            warning_codes=tuple(warning_codes),
            metadata={} if metadata is None else metadata,
        )
    except (GraphAdapterError, GraphComplexityError, GraphStyleError):
        raise
    except (
        DensityNumericalInputError,
        DensityNumericalResourceError,
        DensityNumericalSerializationError,
    ) as error:
        raise _translate_common_error(error) from error
    except (AttributeError, TypeError, ValueError) as error:
        raise GraphAdapterError(
            "Resolved plotting numerics are incompatible with the GR2 adapter."
        ) from error


__all__ = [
    "DENSITY_VISUAL_GRID_ADAPTATION_SCHEMA",
    "DENSITY_VISUAL_POLICY_ID",
    "DensityVisualGridAdaptation",
    "prepare_density_visual_grid_adaptation",
]
