"""Evidence-based research profiler for optional multilevel density storage.

This module implements architecture gate LD6.  It does **not** introduce a
production multilevel field.  Instead, it profiles the completed single-level
block-sparse architecture and an optimistic dyadic coarse/fine surrogate before
any future multilevel specification is approved.

The patch-hierarchy motivation follows Berger and Colella (1989).  The periodic
phase sweep, highest-density-region refinement rule, conservative bin averaging,
error accounting, decision policy, and serialized evidence records are
project-specific mdstats definitions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from .density_block_sparse import plan_block_packing
from .density_contracts import (
    DENSE_BACKEND,
    LOCAL_SPARSE_BACKEND,
    FrozenJSONMapping,
    ScalarField3D,
    freeze_json_mapping,
    is_periodic_node_field_access,
    is_scalar_field3d,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

MULTILEVEL_RESEARCH_OPTIONS_SCHEMA = "mdstats.density-multilevel-research-options.v1"
MULTILEVEL_PHASE_PROFILE_SCHEMA = "mdstats.density-multilevel-phase-profile.v1"
MULTILEVEL_CANDIDATE_PROFILE_SCHEMA = "mdstats.density-multilevel-candidate-profile.v1"
MULTILEVEL_BLOCK_PROFILE_SCHEMA = "mdstats.density-single-level-block-profile.v1"
MULTILEVEL_FIELD_PROFILE_SCHEMA = "mdstats.density-multilevel-field-profile.v1"
MULTILEVEL_DECISION_SCHEMA = "mdstats.density-multilevel-research-decision.v1"

DEFAULT_COARSENING_FACTORS = (2, 4)
DEFAULT_FINE_MASS_FRACTIONS = (0.90, 0.95, 0.99)
DEFAULT_BLOCK_SHAPES = ((4, 4, 4), (8, 8, 8), (16, 16, 16))
DEFAULT_MAX_PROFILE_NODES = 4_000_000
DEFAULT_MAX_PHASE_EVALUATIONS = 2_000
DEFAULT_MAX_PROFILE_WORKSPACE_BYTES = 512_000_000

MultilevelDecisionOutcome = Literal[
    "retain_single_level",
    "write_multilevel_specification",
    "insufficient_evidence",
]
SupportRegime = Literal["localized", "intermediate", "broad"]


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _finite_fraction(value: Any, *, name: str, lower: float, upper: float) -> float:
    result = float(value)
    if not np.isfinite(result) or not lower <= result <= upper:
        raise GraphStyleError(f"{name} must lie in [{lower}, {upper}].")
    return result


def _shape3(value: Sequence[Any], *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphStyleError(f"{name} must contain three entries.")
    return tuple(_positive_int(item, name=f"{name} entry") for item in value)  # type: ignore[return-value]


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise GraphAdapterError(f"{name} must be {ndim}-dimensional.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain finite values.")
    array.setflags(write=False)
    return array


def _validate_sorted_positive_nodes(
    coordinates: IntArray,
    values: FloatArray,
    logical_shape: tuple[int, int, int],
) -> tuple[IntArray, FloatArray, IntArray]:
    coords = _readonly(coordinates, np.int64, ndim=2, name="logical_indices")
    vals = _readonly(values, np.float64, ndim=1, name="values")
    if coords.shape != (vals.size, 3):
        raise GraphAdapterError("logical_indices and values must align.")
    if vals.size == 0 or np.any(vals <= 0.0):
        raise GraphAdapterError("The research profiler requires positive stored nodes.")
    shape_array = np.asarray(logical_shape, dtype=np.int64)
    if np.any(coords < 0) or np.any(coords >= shape_array[None, :]):
        raise GraphAdapterError("logical_indices lie outside the logical grid.")
    flat = np.ravel_multi_index(
        (coords[:, 0], coords[:, 1], coords[:, 2]), logical_shape, order="C"
    ).astype(np.int64, copy=False)
    order = np.argsort(flat, kind="stable")
    flat = np.array(flat[order], dtype=np.int64, copy=True, order="C")
    coords = np.array(coords[order], dtype=np.int64, copy=True, order="C")
    vals = np.array(vals[order], dtype=np.float64, copy=True, order="C")
    if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
        raise GraphAdapterError("Stored node iteration contains duplicate logical nodes.")
    flat.setflags(write=False)
    coords.setflags(write=False)
    vals.setflags(write=False)
    return coords, vals, flat


def _collect_positive_nodes(
    field: ScalarField3D,
    *,
    max_profile_nodes: int,
    max_workspace_bytes: int,
) -> tuple[IntArray, FloatArray, IntArray]:
    if not is_periodic_node_field_access(field):
        raise GraphAdapterError(
            "Multilevel research requires the public PeriodicNodeFieldAccess capability."
        )
    node_limit = _positive_int(max_profile_nodes, name="max_profile_nodes")
    workspace_limit = _positive_int(max_workspace_bytes, name="max_workspace_bytes")
    summary = field.storage_summary()
    if summary.nonzero_node_count > node_limit:
        raise GraphComplexityError(
            "Multilevel profiling requires "
            f"{summary.nonzero_node_count} positive nodes, exceeding "
            f"max_profile_nodes={node_limit}."
        )
    estimated = int(summary.nonzero_node_count) * (3 * 8 + 8 + 8)
    if estimated > workspace_limit:
        raise GraphComplexityError(
            "Multilevel profiling requires approximately "
            f"{estimated} bytes of node workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )
    coord_parts: list[IntArray] = []
    value_parts: list[FloatArray] = []
    count = 0
    for coordinates, values in field.iter_stored_nodes(batch_size=262_144):
        positive = np.asarray(values, dtype=np.float64) > 0.0
        if not np.any(positive):
            continue
        coords = np.asarray(coordinates, dtype=np.int64)[positive]
        vals = np.asarray(values, dtype=np.float64)[positive]
        count += int(vals.size)
        if count > node_limit:
            raise GraphComplexityError(
                f"Multilevel profiling exceeded max_profile_nodes={node_limit}."
            )
        coord_parts.append(coords)
        value_parts.append(vals)
    if not value_parts:
        raise GraphAdapterError("A normalized density field has no positive nodes.")
    coordinates = np.concatenate(coord_parts, axis=0)
    values = np.concatenate(value_parts)
    return _validate_sorted_positive_nodes(coordinates, values, field.grid_shape)


def _weighted_hdr(
    values: FloatArray,
    multiplicities: IntArray,
    *,
    voxel_volume: float,
    total_measure: float,
    fraction: float,
) -> tuple[float, float]:
    positive = values > 0.0
    if not np.any(positive):
        raise GraphAdapterError("HDR reconstruction has no positive values.")
    vals = np.asarray(values[positive], dtype=np.float64)
    mult = np.asarray(multiplicities[positive], dtype=np.int64)
    order = np.argsort(-vals, kind="stable")
    vals = vals[order]
    mult = mult[order]
    cumulative = np.cumsum(vals * mult, dtype=np.float64) * float(voxel_volume)
    target = float(fraction) * float(total_measure)
    index = min(int(np.searchsorted(cumulative, target, side="left")), vals.size - 1)
    threshold = float(vals[index])
    selected = vals >= threshold
    achieved = (
        float(np.sum(vals[selected] * mult[selected], dtype=np.float64))
        * float(voxel_volume)
        / float(total_measure)
    )
    return threshold, achieved


def _coarse_flat_indices(
    coordinates: IntArray,
    *,
    logical_shape: tuple[int, int, int],
    factor: int,
    phase: tuple[int, int, int],
) -> tuple[IntArray, tuple[int, int, int]]:
    shape = np.asarray(logical_shape, dtype=np.int64)
    phase_array = np.asarray(phase, dtype=np.int64)
    shifted = np.mod(coordinates - phase_array[None, :], shape[None, :])
    coarse = shifted // int(factor)
    coarse_shape = tuple(int(item // factor) for item in logical_shape)
    flat = np.ravel_multi_index(
        (coarse[:, 0], coarse[:, 1], coarse[:, 2]), coarse_shape, order="C"
    ).astype(np.int64, copy=False)
    return flat, coarse_shape


@dataclass(frozen=True, slots=True)
class MultilevelResearchOptions:
    """Normative tolerances and decision policy for the LD6 research gate."""

    coarsening_factors: tuple[int, ...] = DEFAULT_COARSENING_FACTORS
    fine_mass_fractions: tuple[float, ...] = DEFAULT_FINE_MASS_FRACTIONS
    block_shapes: tuple[tuple[int, int, int], ...] = DEFAULT_BLOCK_SHAPES
    hdr_fractions: tuple[float, ...] = (0.50, 0.80, 0.95)
    max_relative_l1_error: float = 2.0e-3
    max_relative_linf_error: float = 1.0e-2
    max_relative_hdr_threshold_error: float = 1.0e-2
    max_hdr_mass_fraction_error: float = 1.0e-3
    minimum_incremental_storage_reduction: float = 2.0
    localized_active_fraction: float = 0.20
    broad_active_fraction: float = 0.50
    minimum_adoption_cases: int = 2
    max_profile_nodes: int | None = None
    max_phase_evaluations: int | None = None
    max_workspace_bytes: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = FrozenJSONMapping()
    schema_version: str = MULTILEVEL_RESEARCH_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_RESEARCH_OPTIONS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported multilevel-research-options schema {self.schema_version!r}."
            )
        factors = tuple(
            sorted({_positive_int(item, name="coarsening factor", minimum=2) for item in self.coarsening_factors})
        )
        if any(factor & (factor - 1) for factor in factors):
            raise GraphStyleError("coarsening_factors must be powers of two.")
        fractions = tuple(
            sorted(
                {
                    _finite_fraction(item, name="fine mass fraction", lower=0.0, upper=1.0)
                    for item in self.fine_mass_fractions
                }
            )
        )
        if any(item <= 0.0 or item >= 1.0 for item in fractions):
            raise GraphStyleError("fine_mass_fractions must lie strictly between zero and one.")
        blocks = tuple(dict.fromkeys(_shape3(item, name="block shape") for item in self.block_shapes))
        hdr = tuple(
            sorted(
                {
                    _finite_fraction(item, name="HDR fraction", lower=0.0, upper=1.0)
                    for item in self.hdr_fractions
                }
            )
        )
        if any(item <= 0.0 or item >= 1.0 for item in hdr):
            raise GraphStyleError("hdr_fractions must lie strictly between zero and one.")
        object.__setattr__(self, "coarsening_factors", factors)
        object.__setattr__(self, "fine_mass_fractions", fractions)
        object.__setattr__(self, "block_shapes", blocks)
        object.__setattr__(self, "hdr_fractions", hdr)
        object.__setattr__(
            self,
            "max_relative_l1_error",
            _finite_fraction(self.max_relative_l1_error, name="max_relative_l1_error", lower=0.0, upper=1.0),
        )
        object.__setattr__(
            self,
            "max_relative_linf_error",
            _finite_fraction(self.max_relative_linf_error, name="max_relative_linf_error", lower=0.0, upper=1.0),
        )
        object.__setattr__(
            self,
            "max_relative_hdr_threshold_error",
            _finite_fraction(
                self.max_relative_hdr_threshold_error,
                name="max_relative_hdr_threshold_error",
                lower=0.0,
                upper=1.0,
            ),
        )
        object.__setattr__(
            self,
            "max_hdr_mass_fraction_error",
            _finite_fraction(
                self.max_hdr_mass_fraction_error,
                name="max_hdr_mass_fraction_error",
                lower=0.0,
                upper=1.0,
            ),
        )
        reduction = float(self.minimum_incremental_storage_reduction)
        if not np.isfinite(reduction) or reduction <= 1.0:
            raise GraphStyleError("minimum_incremental_storage_reduction must exceed one.")
        object.__setattr__(self, "minimum_incremental_storage_reduction", reduction)
        localized = _finite_fraction(
            self.localized_active_fraction,
            name="localized_active_fraction",
            lower=0.0,
            upper=1.0,
        )
        broad = _finite_fraction(
            self.broad_active_fraction,
            name="broad_active_fraction",
            lower=0.0,
            upper=1.0,
        )
        if localized >= broad:
            raise GraphStyleError("localized_active_fraction must be less than broad_active_fraction.")
        object.__setattr__(self, "localized_active_fraction", localized)
        object.__setattr__(self, "broad_active_fraction", broad)
        object.__setattr__(
            self,
            "minimum_adoption_cases",
            _positive_int(self.minimum_adoption_cases, name="minimum_adoption_cases"),
        )
        budget, model, derived = resolve_density_resource_limits()
        profile_default = min(4_000_000, derived["max_density_voxels"])
        profile_nodes = (
            profile_default
            if self.max_profile_nodes is None
            else min(profile_default, _positive_int(self.max_profile_nodes, name="max_profile_nodes"))
        )
        # LD6 is an offline research profiler with a documented deterministic
        # phase-sweep contract.  Host throughput calibration governs production
        # scene admission, not which dyadic periodic offsets this evidence run
        # is allowed to inspect.
        phase_evaluations = (
            2_000
            if self.max_phase_evaluations is None
            else _positive_int(self.max_phase_evaluations, name="max_phase_evaluations")
        )
        workspace_default = min(
            512_000_000,
            budget.max_memory_bytes,
        )
        workspace = (
            workspace_default
            if self.max_workspace_bytes is None
            else min(
                _positive_int(self.max_workspace_bytes, name="max_workspace_bytes"),
                budget.max_memory_bytes,
            )
        )
        object.__setattr__(self, "max_profile_nodes", profile_nodes)
        object.__setattr__(self, "max_phase_evaluations", phase_evaluations)
        object.__setattr__(self, "max_workspace_bytes", workspace)
        metadata = dict(freeze_json_mapping(self.metadata))
        metadata.setdefault("resource_policy", "runtime_derived_v1")
        metadata.setdefault("max_threads", budget.max_threads)
        metadata.setdefault("max_wall_time_seconds", budget.max_wall_time_seconds)
        metadata.setdefault("time_model_source", model.calibration_source)
        object.__setattr__(self, "metadata", freeze_json_mapping(metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "coarsening_factors": list(self.coarsening_factors),
            "fine_mass_fractions": list(self.fine_mass_fractions),
            "block_shapes": [list(item) for item in self.block_shapes],
            "hdr_fractions": list(self.hdr_fractions),
            "max_relative_l1_error": self.max_relative_l1_error,
            "max_relative_linf_error": self.max_relative_linf_error,
            "max_relative_hdr_threshold_error": self.max_relative_hdr_threshold_error,
            "max_hdr_mass_fraction_error": self.max_hdr_mass_fraction_error,
            "minimum_incremental_storage_reduction": self.minimum_incremental_storage_reduction,
            "localized_active_fraction": self.localized_active_fraction,
            "broad_active_fraction": self.broad_active_fraction,
            "minimum_adoption_cases": self.minimum_adoption_cases,
            "max_profile_nodes": self.max_profile_nodes,
            "max_phase_evaluations": self.max_phase_evaluations,
            "max_workspace_bytes": self.max_workspace_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MultilevelResearchOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            coarsening_factors=tuple(value["coarsening_factors"]),
            fine_mass_fractions=tuple(value["fine_mass_fractions"]),
            block_shapes=tuple(tuple(item) for item in value["block_shapes"]),
            hdr_fractions=tuple(value["hdr_fractions"]),
            max_relative_l1_error=float(value["max_relative_l1_error"]),
            max_relative_linf_error=float(value["max_relative_linf_error"]),
            max_relative_hdr_threshold_error=float(value["max_relative_hdr_threshold_error"]),
            max_hdr_mass_fraction_error=float(value["max_hdr_mass_fraction_error"]),
            minimum_incremental_storage_reduction=float(value["minimum_incremental_storage_reduction"]),
            localized_active_fraction=float(value["localized_active_fraction"]),
            broad_active_fraction=float(value["broad_active_fraction"]),
            minimum_adoption_cases=int(value["minimum_adoption_cases"]),
            max_profile_nodes=(None if value.get("max_profile_nodes") is None else int(value["max_profile_nodes"])),
            max_phase_evaluations=(None if value.get("max_phase_evaluations") is None else int(value["max_phase_evaluations"])),
            max_workspace_bytes=(None if value.get("max_workspace_bytes") is None else int(value["max_workspace_bytes"])),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class MultilevelPhaseProfile:
    phase: tuple[int, int, int]
    fine_bin_count: int
    coarse_bin_count: int
    fine_value_count: int
    coarse_value_count: int
    estimated_value_count: int
    estimated_index_bytes: int
    estimated_total_bytes: int
    relative_l1_error: float
    relative_linf_error: float
    max_relative_hdr_threshold_error: float
    max_hdr_mass_fraction_error: float
    mass_error: float
    schema_version: str = MULTILEVEL_PHASE_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_PHASE_PROFILE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported multilevel-phase-profile schema {self.schema_version!r}."
            )
        if len(self.phase) != 3:
            raise GraphAdapterError("phase must contain three entries.")
        phase = tuple(int(item) for item in self.phase)
        if any(item < 0 for item in phase):
            raise GraphAdapterError("phase entries must be nonnegative.")
        object.__setattr__(self, "phase", phase)
        for name in (
            "fine_bin_count",
            "coarse_bin_count",
            "fine_value_count",
            "coarse_value_count",
            "estimated_value_count",
            "estimated_index_bytes",
            "estimated_total_bytes",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        for name in (
            "relative_l1_error",
            "relative_linf_error",
            "max_relative_hdr_threshold_error",
            "max_hdr_mass_fraction_error",
            "mass_error",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase": list(self.phase),
            "fine_bin_count": self.fine_bin_count,
            "coarse_bin_count": self.coarse_bin_count,
            "fine_value_count": self.fine_value_count,
            "coarse_value_count": self.coarse_value_count,
            "estimated_value_count": self.estimated_value_count,
            "estimated_index_bytes": self.estimated_index_bytes,
            "estimated_total_bytes": self.estimated_total_bytes,
            "relative_l1_error": self.relative_l1_error,
            "relative_linf_error": self.relative_linf_error,
            "max_relative_hdr_threshold_error": self.max_relative_hdr_threshold_error,
            "max_hdr_mass_fraction_error": self.max_hdr_mass_fraction_error,
            "mass_error": self.mass_error,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MultilevelPhaseProfile":
        return cls(
            schema_version=str(value["schema_version"]),
            phase=tuple(value["phase"]),
            fine_bin_count=int(value["fine_bin_count"]),
            coarse_bin_count=int(value["coarse_bin_count"]),
            fine_value_count=int(value["fine_value_count"]),
            coarse_value_count=int(value["coarse_value_count"]),
            estimated_value_count=int(value["estimated_value_count"]),
            estimated_index_bytes=int(value["estimated_index_bytes"]),
            estimated_total_bytes=int(value["estimated_total_bytes"]),
            relative_l1_error=float(value["relative_l1_error"]),
            relative_linf_error=float(value["relative_linf_error"]),
            max_relative_hdr_threshold_error=float(value["max_relative_hdr_threshold_error"]),
            max_hdr_mass_fraction_error=float(value["max_hdr_mass_fraction_error"]),
            mass_error=float(value["mass_error"]),
        )


@dataclass(frozen=True, slots=True)
class MultilevelCandidateProfile:
    coarsening_factor: int
    fine_mass_fraction: float
    phase_count: int
    minimum_estimated_value_count: int
    maximum_estimated_value_count: int
    minimum_estimated_total_bytes: int
    maximum_estimated_total_bytes: int
    best_storage_reduction_vs_current: float
    worst_storage_reduction_vs_current: float
    best_incremental_reduction_vs_single_level: float
    worst_incremental_reduction_vs_single_level: float
    worst_relative_l1_error: float
    worst_relative_linf_error: float
    worst_relative_hdr_threshold_error: float
    worst_hdr_mass_fraction_error: float
    worst_mass_error: float
    all_phases_pass: bool
    meets_incremental_reduction_gate: bool
    phase_profiles: tuple[MultilevelPhaseProfile, ...]
    metadata: FrozenJSONMapping | Mapping[str, Any] = FrozenJSONMapping()
    schema_version: str = MULTILEVEL_CANDIDATE_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_CANDIDATE_PROFILE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported multilevel-candidate-profile schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "coarsening_factor",
            _positive_int(self.coarsening_factor, name="coarsening_factor", minimum=2),
        )
        object.__setattr__(
            self,
            "fine_mass_fraction",
            _finite_fraction(self.fine_mass_fraction, name="fine_mass_fraction", lower=0.0, upper=1.0),
        )
        object.__setattr__(self, "phase_count", _positive_int(self.phase_count, name="phase_count"))
        if self.phase_count != len(self.phase_profiles):
            raise GraphAdapterError("phase_count does not match phase_profiles.")
        for name in (
            "minimum_estimated_value_count",
            "maximum_estimated_value_count",
            "minimum_estimated_total_bytes",
            "maximum_estimated_total_bytes",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        for name in (
            "best_storage_reduction_vs_current",
            "worst_storage_reduction_vs_current",
            "best_incremental_reduction_vs_single_level",
            "worst_incremental_reduction_vs_single_level",
            "worst_relative_l1_error",
            "worst_relative_linf_error",
            "worst_relative_hdr_threshold_error",
            "worst_hdr_mass_fraction_error",
            "worst_mass_error",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "phase_profiles", tuple(self.phase_profiles))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def qualifies_for_adoption(self) -> bool:
        return bool(self.all_phases_pass and self.meets_incremental_reduction_gate)

    def to_json_dict(self, *, include_phases: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "coarsening_factor": self.coarsening_factor,
            "fine_mass_fraction": self.fine_mass_fraction,
            "phase_count": self.phase_count,
            "minimum_estimated_value_count": self.minimum_estimated_value_count,
            "maximum_estimated_value_count": self.maximum_estimated_value_count,
            "minimum_estimated_total_bytes": self.minimum_estimated_total_bytes,
            "maximum_estimated_total_bytes": self.maximum_estimated_total_bytes,
            "best_storage_reduction_vs_current": self.best_storage_reduction_vs_current,
            "worst_storage_reduction_vs_current": self.worst_storage_reduction_vs_current,
            "best_incremental_reduction_vs_single_level": self.best_incremental_reduction_vs_single_level,
            "worst_incremental_reduction_vs_single_level": self.worst_incremental_reduction_vs_single_level,
            "worst_relative_l1_error": self.worst_relative_l1_error,
            "worst_relative_linf_error": self.worst_relative_linf_error,
            "worst_relative_hdr_threshold_error": self.worst_relative_hdr_threshold_error,
            "worst_hdr_mass_fraction_error": self.worst_hdr_mass_fraction_error,
            "worst_mass_error": self.worst_mass_error,
            "all_phases_pass": self.all_phases_pass,
            "meets_incremental_reduction_gate": self.meets_incremental_reduction_gate,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_phases:
            result["phase_profiles"] = [item.to_json_dict() for item in self.phase_profiles]
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MultilevelCandidateProfile":
        if "phase_profiles" not in value:
            raise GraphAdapterError("Candidate JSON requires phase_profiles.")
        return cls(
            schema_version=str(value["schema_version"]),
            coarsening_factor=int(value["coarsening_factor"]),
            fine_mass_fraction=float(value["fine_mass_fraction"]),
            phase_count=int(value["phase_count"]),
            minimum_estimated_value_count=int(value["minimum_estimated_value_count"]),
            maximum_estimated_value_count=int(value["maximum_estimated_value_count"]),
            minimum_estimated_total_bytes=int(value["minimum_estimated_total_bytes"]),
            maximum_estimated_total_bytes=int(value["maximum_estimated_total_bytes"]),
            best_storage_reduction_vs_current=float(value["best_storage_reduction_vs_current"]),
            worst_storage_reduction_vs_current=float(value["worst_storage_reduction_vs_current"]),
            best_incremental_reduction_vs_single_level=float(value["best_incremental_reduction_vs_single_level"]),
            worst_incremental_reduction_vs_single_level=float(value["worst_incremental_reduction_vs_single_level"]),
            worst_relative_l1_error=float(value["worst_relative_l1_error"]),
            worst_relative_linf_error=float(value["worst_relative_linf_error"]),
            worst_relative_hdr_threshold_error=float(value["worst_relative_hdr_threshold_error"]),
            worst_hdr_mass_fraction_error=float(value["worst_hdr_mass_fraction_error"]),
            worst_mass_error=float(value["worst_mass_error"]),
            all_phases_pass=bool(value["all_phases_pass"]),
            meets_incremental_reduction_gate=bool(value["meets_incremental_reduction_gate"]),
            phase_profiles=tuple(
                MultilevelPhaseProfile.from_json_dict(item)
                for item in value["phase_profiles"]
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class SingleLevelBlockProfile:
    block_shape: tuple[int, int, int]
    active_block_count: int
    allocated_value_count: int
    valid_value_count: int
    estimated_total_bytes: int
    storage_fraction: float
    schema_version: str = MULTILEVEL_BLOCK_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_BLOCK_PROFILE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported single-level-block-profile schema {self.schema_version!r}."
            )
        object.__setattr__(self, "block_shape", _shape3(self.block_shape, name="block_shape"))
        for name in (
            "active_block_count",
            "allocated_value_count",
            "valid_value_count",
            "estimated_total_bytes",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        object.__setattr__(
            self,
            "storage_fraction",
            _finite_fraction(self.storage_fraction, name="storage_fraction", lower=0.0, upper=10_000.0),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "block_shape": list(self.block_shape),
            "active_block_count": self.active_block_count,
            "allocated_value_count": self.allocated_value_count,
            "valid_value_count": self.valid_value_count,
            "estimated_total_bytes": self.estimated_total_bytes,
            "storage_fraction": self.storage_fraction,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "SingleLevelBlockProfile":
        return cls(
            schema_version=str(value["schema_version"]),
            block_shape=tuple(value["block_shape"]),
            active_block_count=int(value["active_block_count"]),
            allocated_value_count=int(value["allocated_value_count"]),
            valid_value_count=int(value["valid_value_count"]),
            estimated_total_bytes=int(value["estimated_total_bytes"]),
            storage_fraction=float(value["storage_fraction"]),
        )


@dataclass(frozen=True, slots=True)
class MultilevelFieldResearchProfile:
    field_key: str
    storage_backend: str
    logical_grid_shape: tuple[int, int, int]
    logical_node_count: int
    nonzero_node_count: int
    current_stored_value_count: int
    current_realized_bytes: int
    active_fraction: float
    stored_fraction: float
    support_regime: SupportRegime
    single_level_sufficient: bool
    block_profiles: tuple[SingleLevelBlockProfile, ...]
    best_single_level_value_count: int
    best_single_level_total_bytes: int
    candidates: tuple[MultilevelCandidateProfile, ...]
    best_candidate_index: int | None
    metadata: FrozenJSONMapping | Mapping[str, Any] = FrozenJSONMapping()
    schema_version: str = MULTILEVEL_FIELD_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_FIELD_PROFILE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported multilevel-field-profile schema {self.schema_version!r}."
            )
        if self.storage_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND}:
            raise GraphAdapterError("storage_backend must be dense or local_sparse.")
        object.__setattr__(self, "logical_grid_shape", _shape3(self.logical_grid_shape, name="logical_grid_shape"))
        for name in (
            "logical_node_count",
            "nonzero_node_count",
            "current_stored_value_count",
            "current_realized_bytes",
            "best_single_level_value_count",
            "best_single_level_total_bytes",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        for name in ("active_fraction", "stored_fraction"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if self.support_regime not in {"localized", "intermediate", "broad"}:
            raise GraphAdapterError("Unsupported support_regime.")
        blocks = tuple(self.block_profiles)
        candidates = tuple(self.candidates)
        object.__setattr__(self, "block_profiles", blocks)
        object.__setattr__(self, "candidates", candidates)
        if self.best_candidate_index is not None:
            index = int(self.best_candidate_index)
            if not 0 <= index < len(candidates):
                raise GraphAdapterError("best_candidate_index lies outside candidates.")
            object.__setattr__(self, "best_candidate_index", index)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def best_candidate(self) -> MultilevelCandidateProfile | None:
        if self.best_candidate_index is None:
            return None
        return self.candidates[self.best_candidate_index]

    @property
    def has_adoption_candidate(self) -> bool:
        candidate = self.best_candidate
        return bool(candidate is not None and candidate.qualifies_for_adoption)

    def to_json_dict(self, *, include_phases: bool = False) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "storage_backend": self.storage_backend,
            "logical_grid_shape": list(self.logical_grid_shape),
            "logical_node_count": self.logical_node_count,
            "nonzero_node_count": self.nonzero_node_count,
            "current_stored_value_count": self.current_stored_value_count,
            "current_realized_bytes": self.current_realized_bytes,
            "active_fraction": self.active_fraction,
            "stored_fraction": self.stored_fraction,
            "support_regime": self.support_regime,
            "single_level_sufficient": self.single_level_sufficient,
            "block_profiles": [item.to_json_dict() for item in self.block_profiles],
            "best_single_level_value_count": self.best_single_level_value_count,
            "best_single_level_total_bytes": self.best_single_level_total_bytes,
            "candidates": [
                item.to_json_dict(include_phases=include_phases) for item in self.candidates
            ],
            "best_candidate_index": self.best_candidate_index,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MultilevelFieldResearchProfile":
        if "candidates" not in value:
            raise GraphAdapterError("Field-profile JSON requires candidates.")
        return cls(
            schema_version=str(value["schema_version"]),
            field_key=str(value["field_key"]),
            storage_backend=str(value["storage_backend"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            logical_node_count=int(value["logical_node_count"]),
            nonzero_node_count=int(value["nonzero_node_count"]),
            current_stored_value_count=int(value["current_stored_value_count"]),
            current_realized_bytes=int(value["current_realized_bytes"]),
            active_fraction=float(value["active_fraction"]),
            stored_fraction=float(value["stored_fraction"]),
            support_regime=str(value["support_regime"]),  # type: ignore[arg-type]
            single_level_sufficient=bool(value["single_level_sufficient"]),
            block_profiles=tuple(
                SingleLevelBlockProfile.from_json_dict(item)
                for item in value["block_profiles"]
            ),
            best_single_level_value_count=int(value["best_single_level_value_count"]),
            best_single_level_total_bytes=int(value["best_single_level_total_bytes"]),
            candidates=tuple(
                MultilevelCandidateProfile.from_json_dict(item)
                for item in value["candidates"]
            ),
            best_candidate_index=(
                None
                if value.get("best_candidate_index") is None
                else int(value["best_candidate_index"])
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class MultilevelResearchDecision:
    outcome: MultilevelDecisionOutcome
    profile_count: int
    localized_profile_count: int
    broad_profile_count: int
    insufficient_profile_count: int
    qualifying_candidate_count: int
    adoption_case_count: int
    rationale: tuple[str, ...]
    field_keys: tuple[str, ...]
    options: MultilevelResearchOptions
    metadata: FrozenJSONMapping | Mapping[str, Any] = FrozenJSONMapping()
    schema_version: str = MULTILEVEL_DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MULTILEVEL_DECISION_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported multilevel-research-decision schema {self.schema_version!r}."
            )
        if self.outcome not in {
            "retain_single_level",
            "write_multilevel_specification",
            "insufficient_evidence",
        }:
            raise GraphAdapterError("Unsupported multilevel research outcome.")
        for name in (
            "profile_count",
            "localized_profile_count",
            "broad_profile_count",
            "insufficient_profile_count",
            "qualifying_candidate_count",
            "adoption_case_count",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        if self.profile_count != len(self.field_keys):
            raise GraphAdapterError("profile_count does not match field_keys.")
        object.__setattr__(self, "rationale", tuple(str(item) for item in self.rationale))
        object.__setattr__(self, "field_keys", tuple(str(item) for item in self.field_keys))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "outcome": self.outcome,
            "profile_count": self.profile_count,
            "localized_profile_count": self.localized_profile_count,
            "broad_profile_count": self.broad_profile_count,
            "insufficient_profile_count": self.insufficient_profile_count,
            "qualifying_candidate_count": self.qualifying_candidate_count,
            "adoption_case_count": self.adoption_case_count,
            "rationale": list(self.rationale),
            "field_keys": list(self.field_keys),
            "options": self.options.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MultilevelResearchDecision":
        return cls(
            schema_version=str(value["schema_version"]),
            outcome=str(value["outcome"]),  # type: ignore[arg-type]
            profile_count=int(value["profile_count"]),
            localized_profile_count=int(value["localized_profile_count"]),
            broad_profile_count=int(value["broad_profile_count"]),
            insufficient_profile_count=int(value["insufficient_profile_count"]),
            qualifying_candidate_count=int(value["qualifying_candidate_count"]),
            adoption_case_count=int(value["adoption_case_count"]),
            rationale=tuple(value["rationale"]),
            field_keys=tuple(value["field_keys"]),
            options=MultilevelResearchOptions.from_json_dict(value["options"]),
            metadata=value.get("metadata", {}),
        )


def _profile_phase(
    coordinates: IntArray,
    values: FloatArray,
    *,
    logical_shape: tuple[int, int, int],
    factor: int,
    phase: tuple[int, int, int],
    fine_threshold: float,
    voxel_volume: float,
    total_measure: float,
    hdr_fractions: tuple[float, ...],
    reference_hdr: Mapping[float, tuple[float, float]],
) -> MultilevelPhaseProfile:
    coarse_flat, coarse_shape = _coarse_flat_indices(
        coordinates,
        logical_shape=logical_shape,
        factor=factor,
        phase=phase,
    )
    order = np.argsort(coarse_flat, kind="stable")
    coarse_sorted = coarse_flat[order]
    values_sorted = values[order]
    starts = np.r_[0, np.nonzero(coarse_sorted[1:] != coarse_sorted[:-1])[0] + 1]
    stops = np.r_[starts[1:], coarse_sorted.size]
    unique_bins = coarse_sorted[starts]
    sums = np.add.reduceat(values_sorted, starts)
    counts = stops - starts
    fine_nodes = values_sorted >= fine_threshold
    fine_bin_flags = np.logical_or.reduceat(fine_nodes, starts)
    bin_capacity = int(factor) ** 3
    fine_bin_count = int(np.count_nonzero(fine_bin_flags))
    coarse_bin_count = int(unique_bins.size - fine_bin_count)
    fine_value_count = fine_bin_count * bin_capacity
    coarse_value_count = coarse_bin_count
    estimated_value_count = fine_value_count + coarse_value_count
    estimated_index_bytes = (fine_bin_count + coarse_bin_count) * 3 * 8
    estimated_total_bytes = estimated_value_count * 8 + estimated_index_bytes

    group_ids = np.repeat(np.arange(unique_bins.size, dtype=np.int64), counts)
    means = sums / float(bin_capacity)
    node_is_fine = fine_bin_flags[group_ids]
    coarse_node_mask = ~node_is_fine
    node_differences = np.abs(values_sorted - means[group_ids])
    l1_numerator = float(
        np.sum(node_differences[coarse_node_mask], dtype=np.float64)
    )
    coarse_groups = ~fine_bin_flags
    zero_counts = bin_capacity - counts
    l1_numerator += float(
        np.sum(zero_counts[coarse_groups] * means[coarse_groups], dtype=np.float64)
    )
    linf_numerator = 0.0
    if np.any(coarse_node_mask):
        linf_numerator = float(np.max(node_differences[coarse_node_mask]))
    coarse_with_zeros = coarse_groups & (zero_counts > 0)
    if np.any(coarse_with_zeros):
        linf_numerator = max(
            linf_numerator, float(np.max(np.abs(means[coarse_with_zeros])))
        )
    fine_values = values_sorted[node_is_fine]
    coarse_means = means[coarse_groups]
    reconstructed = np.concatenate((fine_values, coarse_means))
    multiplicities = np.concatenate(
        (
            np.ones(fine_values.size, dtype=np.int64),
            np.full(coarse_means.size, bin_capacity, dtype=np.int64),
        )
    )
    denominator_l1 = max(float(np.sum(values, dtype=np.float64)), np.finfo(np.float64).tiny)
    denominator_linf = max(float(np.max(values)), np.finfo(np.float64).tiny)
    relative_l1 = l1_numerator / denominator_l1
    relative_linf = linf_numerator / denominator_linf
    reconstructed_measure = (
        float(np.sum(reconstructed * multiplicities, dtype=np.float64)) * voxel_volume
    )
    mass_error = abs(reconstructed_measure - total_measure)
    max_threshold_error = 0.0
    max_fraction_error = 0.0
    for fraction in hdr_fractions:
        threshold, achieved = _weighted_hdr(
            reconstructed,
            multiplicities,
            voxel_volume=voxel_volume,
            total_measure=total_measure,
            fraction=fraction,
        )
        reference_threshold, reference_achieved = reference_hdr[fraction]
        max_threshold_error = max(
            max_threshold_error,
            abs(threshold - reference_threshold) / denominator_linf,
        )
        max_fraction_error = max(max_fraction_error, abs(achieved - reference_achieved))
    del coarse_shape
    return MultilevelPhaseProfile(
        phase=phase,
        fine_bin_count=fine_bin_count,
        coarse_bin_count=coarse_bin_count,
        fine_value_count=fine_value_count,
        coarse_value_count=coarse_value_count,
        estimated_value_count=estimated_value_count,
        estimated_index_bytes=estimated_index_bytes,
        estimated_total_bytes=estimated_total_bytes,
        relative_l1_error=relative_l1,
        relative_linf_error=relative_linf,
        max_relative_hdr_threshold_error=max_threshold_error,
        max_hdr_mass_fraction_error=max_fraction_error,
        mass_error=mass_error,
    )


def _candidate_profile(
    field: ScalarField3D,
    coordinates: IntArray,
    values: FloatArray,
    *,
    factor: int,
    fine_mass_fraction: float,
    current_stored_value_count: int,
    best_single_level_value_count: int,
    options: MultilevelResearchOptions,
) -> MultilevelCandidateProfile:
    if any(size % factor for size in field.grid_shape):
        raise GraphStyleError(
            f"grid_shape={field.grid_shape} is not divisible by coarsening_factor={factor}."
        )
    phase_count = factor**3
    if phase_count > options.max_phase_evaluations:
        raise GraphComplexityError(
            f"Coarsening factor {factor} requires {phase_count} phase evaluations, "
            f"exceeding max_phase_evaluations={options.max_phase_evaluations}."
        )
    fine_threshold = float(field.hdr_details(fine_mass_fraction).threshold)
    reference_hdr = {
        fraction: (
            float(field.hdr_details(fraction).threshold),
            float(field.hdr_details(fraction).achieved_mass_fraction),
        )
        for fraction in options.hdr_fractions
    }
    profiles: list[MultilevelPhaseProfile] = []
    for p0 in range(factor):
        for p1 in range(factor):
            for p2 in range(factor):
                profiles.append(
                    _profile_phase(
                        coordinates,
                        values,
                        logical_shape=field.grid_shape,
                        factor=factor,
                        phase=(p0, p1, p2),
                        fine_threshold=fine_threshold,
                        voxel_volume=float(field.voxel_volume),
                        total_measure=float(field.total_measure),
                        hdr_fractions=options.hdr_fractions,
                        reference_hdr=reference_hdr,
                    )
                )
    value_counts = np.asarray([item.estimated_value_count for item in profiles], dtype=np.int64)
    byte_counts = np.asarray([item.estimated_total_bytes for item in profiles], dtype=np.int64)
    worst_l1 = max(item.relative_l1_error for item in profiles)
    worst_linf = max(item.relative_linf_error for item in profiles)
    worst_hdr = max(item.max_relative_hdr_threshold_error for item in profiles)
    worst_hdr_mass = max(item.max_hdr_mass_fraction_error for item in profiles)
    worst_mass = max(item.mass_error for item in profiles)
    all_pass = bool(
        worst_l1 <= options.max_relative_l1_error
        and worst_linf <= options.max_relative_linf_error
        and worst_hdr <= options.max_relative_hdr_threshold_error
        and worst_hdr_mass <= options.max_hdr_mass_fraction_error
        and worst_mass <= 5.0e-13 * max(1.0, float(field.total_measure))
    )
    min_count = int(np.min(value_counts))
    max_count = int(np.max(value_counts))
    return MultilevelCandidateProfile(
        coarsening_factor=factor,
        fine_mass_fraction=fine_mass_fraction,
        phase_count=len(profiles),
        minimum_estimated_value_count=min_count,
        maximum_estimated_value_count=max_count,
        minimum_estimated_total_bytes=int(np.min(byte_counts)),
        maximum_estimated_total_bytes=int(np.max(byte_counts)),
        best_storage_reduction_vs_current=float(current_stored_value_count) / max(1, min_count),
        worst_storage_reduction_vs_current=float(current_stored_value_count) / max(1, max_count),
        best_incremental_reduction_vs_single_level=float(best_single_level_value_count) / max(1, min_count),
        worst_incremental_reduction_vs_single_level=float(best_single_level_value_count) / max(1, max_count),
        worst_relative_l1_error=worst_l1,
        worst_relative_linf_error=worst_linf,
        worst_relative_hdr_threshold_error=worst_hdr,
        worst_hdr_mass_fraction_error=worst_hdr_mass,
        worst_mass_error=worst_mass,
        all_phases_pass=all_pass,
        meets_incremental_reduction_gate=(
            float(best_single_level_value_count) / max(1, int(np.max(value_counts)))
            >= options.minimum_incremental_storage_reduction
        ),
        phase_profiles=tuple(profiles),
        metadata={
            "fine_threshold": fine_threshold,
            "phase_policy": "all_periodic_offsets",
            "reconstruction": "fine_exact_coarse_piecewise_constant",
            "storage_estimate": "optimistic_value_plus_region_indices",
        },
    )


def profile_multilevel_field(
    field: ScalarField3D,
    *,
    options: MultilevelResearchOptions | None = None,
) -> MultilevelFieldResearchProfile:
    """Profile one realized field without changing its production representation."""

    if not is_scalar_field3d(field):
        raise GraphAdapterError("field must satisfy the ScalarField3D protocol.")
    resolved = MultilevelResearchOptions() if options is None else options
    coordinates, values, flat = _collect_positive_nodes(
        field,
        max_profile_nodes=resolved.max_profile_nodes,
        max_workspace_bytes=resolved.max_workspace_bytes,
    )
    summary = field.storage_summary()
    logical_count = int(np.prod(field.grid_shape, dtype=object))
    active_fraction = int(values.size) / float(logical_count)
    stored_fraction = summary.stored_value_count / float(logical_count)
    if active_fraction <= resolved.localized_active_fraction:
        regime: SupportRegime = "localized"
    elif active_fraction >= resolved.broad_active_fraction:
        regime = "broad"
    else:
        regime = "intermediate"

    block_profiles: list[SingleLevelBlockProfile] = []
    for block_shape in resolved.block_shapes:
        plan = plan_block_packing(
            flat,
            logical_grid_shape=field.grid_shape,
            block_shape=block_shape,
            max_nonzero_nodes=max(resolved.max_profile_nodes, int(values.size)),
            max_stored_block_values=max(logical_count * 8, 1),
            max_blocks=max(logical_count, 1),
            max_planning_bytes=resolved.max_workspace_bytes,
        )
        mask_bytes = 0
        if plan.partial_block_count:
            mask_bytes = plan.allocated_value_count
        estimated_bytes = (
            plan.allocated_value_count * 8
            + plan.active_block_count * 3 * 8
            + mask_bytes
        )
        block_profiles.append(
            SingleLevelBlockProfile(
                block_shape=block_shape,
                active_block_count=plan.active_block_count,
                allocated_value_count=plan.allocated_value_count,
                valid_value_count=plan.valid_value_count,
                estimated_total_bytes=estimated_bytes,
                storage_fraction=plan.allocated_value_count / float(logical_count),
            )
        )
    best_block = min(
        block_profiles,
        key=lambda item: (item.estimated_total_bytes, item.allocated_value_count, item.block_shape),
    )
    candidates: list[MultilevelCandidateProfile] = []
    for factor in resolved.coarsening_factors:
        if any(size % factor for size in field.grid_shape):
            continue
        for fine_fraction in resolved.fine_mass_fractions:
            candidates.append(
                _candidate_profile(
                    field,
                    coordinates,
                    values,
                    factor=factor,
                    fine_mass_fraction=fine_fraction,
                    current_stored_value_count=summary.stored_value_count,
                    best_single_level_value_count=best_block.allocated_value_count,
                    options=resolved,
                )
            )
    qualifying = [
        (index, item)
        for index, item in enumerate(candidates)
        if item.all_phases_pass
    ]
    best_index: int | None = None
    if qualifying:
        best_index = max(
            qualifying,
            key=lambda pair: (
                pair[1].worst_incremental_reduction_vs_single_level,
                pair[1].worst_storage_reduction_vs_current,
                -pair[1].worst_relative_l1_error,
                -pair[0],
            ),
        )[0]

    if field.storage_backend == DENSE_BACKEND and regime == "broad":
        single_level_sufficient = True
        sufficient_reason = "broad_support_dense_backend"
    elif (
        field.storage_backend == LOCAL_SPARSE_BACKEND
        and min(stored_fraction, best_block.storage_fraction)
        <= resolved.localized_active_fraction
    ):
        single_level_sufficient = True
        sufficient_reason = "localized_sparse_or_alternative_block_storage_within_policy_anchor"
    else:
        single_level_sufficient = False
        sufficient_reason = "intermediate_or_inefficient_single_level_storage"

    return MultilevelFieldResearchProfile(
        field_key=str(field.field_key),
        storage_backend=str(field.storage_backend),
        logical_grid_shape=field.grid_shape,
        logical_node_count=logical_count,
        nonzero_node_count=int(values.size),
        current_stored_value_count=int(summary.stored_value_count),
        current_realized_bytes=int(summary.realized_bytes or summary.estimated_bytes),
        active_fraction=active_fraction,
        stored_fraction=stored_fraction,
        support_regime=regime,
        single_level_sufficient=single_level_sufficient,
        block_profiles=tuple(block_profiles),
        best_single_level_value_count=best_block.allocated_value_count,
        best_single_level_total_bytes=best_block.estimated_total_bytes,
        candidates=tuple(candidates),
        best_candidate_index=best_index,
        metadata={
            "single_level_sufficiency_reason": sufficient_reason,
            "positive_measure_from_nodes": float(np.sum(values, dtype=np.float64))
            * float(field.voxel_volume),
            "phase_robustness_required": True,
            "prototype_is_not_a_production_field": True,
        },
    )


def decide_multilevel_research(
    profiles: Iterable[MultilevelFieldResearchProfile],
    *,
    options: MultilevelResearchOptions | None = None,
) -> MultilevelResearchDecision:
    """Apply the LD6 evidence policy to a representative profile collection."""

    resolved = MultilevelResearchOptions() if options is None else options
    items = tuple(profiles)
    if not items:
        raise GraphStyleError("At least one multilevel field profile is required.")
    localized = sum(item.support_regime == "localized" for item in items)
    broad = sum(item.support_regime == "broad" for item in items)
    insufficient = sum(not item.single_level_sufficient for item in items)
    qualifying = sum(item.has_adoption_candidate for item in items)
    adoption_cases = sum(
        (not item.single_level_sufficient) and item.has_adoption_candidate
        for item in items
    )
    rationale: list[str] = []
    if localized == 0 or broad == 0:
        outcome: MultilevelDecisionOutcome = "insufficient_evidence"
        rationale.append(
            "The benchmark set must contain at least one localized and one broad field."
        )
    elif adoption_cases >= resolved.minimum_adoption_cases:
        outcome = "write_multilevel_specification"
        rationale.append(
            f"{adoption_cases} insufficient single-level cases retain at least "
            f"{resolved.minimum_incremental_storage_reduction:.2f}x phase-robust incremental "
            "storage reduction within all scientific tolerances."
        )
    else:
        outcome = "retain_single_level"
        if insufficient == 0:
            rationale.append(
                "Every representative field is already served efficiently by either dense "
                "or single-level block-sparse storage."
            )
        else:
            rationale.append(
                "No required number of insufficient single-level cases shows a phase-robust "
                "multilevel gain large enough to justify transfer and contouring complexity."
            )
        if qualifying:
            rationale.append(
                "Some optimistic coarse/fine surrogates pass numerical tolerances, but they "
                "do not establish a production need beyond the completed backend selector."
            )
        rationale.append(
            "True multilevel transfer, HDR integration, and crack-free coarse/fine meshing "
            "remain unimplemented and must not be inferred from this research profiler."
        )
    return MultilevelResearchDecision(
        outcome=outcome,
        profile_count=len(items),
        localized_profile_count=localized,
        broad_profile_count=broad,
        insufficient_profile_count=insufficient,
        qualifying_candidate_count=qualifying,
        adoption_case_count=adoption_cases,
        rationale=tuple(rationale),
        field_keys=tuple(item.field_key for item in items),
        options=resolved,
        metadata={
            "decision_policy": "ld6_evidence_gate_v1",
            "production_multilevel_implemented": False,
            "single_level_architecture_status": "complete_through_ld5",
        },
    )
