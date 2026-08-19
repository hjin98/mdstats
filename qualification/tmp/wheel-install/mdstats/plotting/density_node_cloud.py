"""Backend-neutral logical-node density cloud preparation.

Architecture gate LD2-A prepares highest-density-region node clouds through the
public :class:`ScalarField3D` and :class:`PeriodicNodeFieldAccess` contracts.
The implementation never materializes a dense logical array for sparse fields.
Highest-density regions follow Hyndman, *The American Statistician* 50,
120-126 (1996).  Deterministic thinning, provenance, bounds, replication, and
resource accounting are project-specific mdstats policies.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_contracts import (
    DensitySourceProvenance,
    FrozenJSONMapping,
    PeriodicNodeFieldAccess,
    ScalarField3D,
    freeze_json_mapping,
    is_periodic_node_field_access,
    is_scalar_field3d,
)
from .density_sparse_reference import SparseHDRDetails
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_CARTESIAN_BOUNDS_SCHEMA = "mdstats.density-cartesian-bounds.v1"
DENSITY_NODE_CLOUD_RESOURCES_SCHEMA = "mdstats.density-node-cloud-resources.v1"
DENSITY_TRACE_PROVENANCE_SCHEMA = "mdstats.density-trace-provenance.v1"
DENSITY_NODE_CLOUD_SCHEMA = "mdstats.density-node-cloud.v1"
DENSITY_NODE_CLOUD_SELECTION_POLICY = "hdr_lexicographic_linspace_v1"

DEFAULT_MAX_CLOUD_WORKSPACE_BYTES = 512_000_000


def _readonly_array(
    value: Any,
    dtype: Any,
    *,
    ndim: int | None = None,
    name: str,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphAdapterError(
            f"{name} must be {ndim}-dimensional; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _shape3(value: Any, *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError(f"{name} must contain three entries.")
    result = tuple(_positive_int(item, name=f"{name} entry") for item in value)
    return result  # type: ignore[return-value]


def _validated_shift(value: Any) -> tuple[int, int, int]:
    if len(value) != 3 or any(
        isinstance(item, bool) or not isinstance(item, (int, np.integer))
        for item in value
    ):
        raise GraphAdapterError("image_shift must contain exactly three integers.")
    return tuple(int(item) for item in value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class DensityCartesianBounds:
    """Exact componentwise Cartesian bounds of one prepared point cloud."""

    minimum: FloatArray
    maximum: FloatArray
    schema_version: str = DENSITY_CARTESIAN_BOUNDS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_CARTESIAN_BOUNDS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-bounds schema {self.schema_version!r}."
            )
        minimum = _readonly_array(self.minimum, np.float64, ndim=1, name="minimum")
        maximum = _readonly_array(self.maximum, np.float64, ndim=1, name="maximum")
        if minimum.shape != (3,) or maximum.shape != (3,):
            raise GraphAdapterError("Density bounds must have shape (3,).")
        if np.any(maximum < minimum):
            raise GraphAdapterError("Density maximum bounds must not precede minimum bounds.")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "minimum": self.minimum.tolist(),
            "maximum": self.maximum.tolist(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityCartesianBounds":
        return cls(
            schema_version=str(value["schema_version"]),
            minimum=np.asarray(value["minimum"], dtype=np.float64),
            maximum=np.asarray(value["maximum"], dtype=np.float64),
        )


@dataclass(frozen=True, slots=True)
class DensityNodeCloudResources:
    """Exact resource counts for one canonical logical-node cloud."""

    scanned_stored_node_count: int
    eligible_node_count: int
    selected_point_count: int
    truncated: bool
    index_bytes: int
    value_bytes: int
    cartesian_bytes: int
    intensity_bytes: int
    estimated_peak_bytes: int
    trace_count: int = 1
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_NODE_CLOUD_RESOURCES_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_NODE_CLOUD_RESOURCES_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported node-cloud-resource schema {self.schema_version!r}."
            )
        counts = {}
        for name in (
            "scanned_stored_node_count",
            "eligible_node_count",
            "selected_point_count",
            "index_bytes",
            "value_bytes",
            "cartesian_bytes",
            "intensity_bytes",
            "estimated_peak_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GraphAdapterError(f"{name} must be a nonnegative integer.")
            integer = int(value)
            if integer < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            counts[name] = integer
        trace_count = _positive_int(self.trace_count, name="trace_count")
        if counts["eligible_node_count"] > counts["scanned_stored_node_count"]:
            raise GraphAdapterError("eligible_node_count exceeds scanned nodes.")
        if counts["selected_point_count"] > counts["eligible_node_count"]:
            raise GraphAdapterError("selected_point_count exceeds eligible nodes.")
        if bool(self.truncated) != (
            counts["selected_point_count"] < counts["eligible_node_count"]
        ):
            raise GraphAdapterError("truncated is inconsistent with point counts.")
        for name, integer in counts.items():
            object.__setattr__(self, name, integer)
        object.__setattr__(self, "trace_count", trace_count)
        object.__setattr__(self, "truncated", bool(self.truncated))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scanned_stored_node_count": self.scanned_stored_node_count,
            "eligible_node_count": self.eligible_node_count,
            "selected_point_count": self.selected_point_count,
            "truncated": self.truncated,
            "index_bytes": self.index_bytes,
            "value_bytes": self.value_bytes,
            "cartesian_bytes": self.cartesian_bytes,
            "intensity_bytes": self.intensity_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "trace_count": self.trace_count,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityNodeCloudResources":
        return cls(
            schema_version=str(value["schema_version"]),
            scanned_stored_node_count=int(value["scanned_stored_node_count"]),
            eligible_node_count=int(value["eligible_node_count"]),
            selected_point_count=int(value["selected_point_count"]),
            truncated=bool(value["truncated"]),
            index_bytes=int(value["index_bytes"]),
            value_bytes=int(value["value_bytes"]),
            cartesian_bytes=int(value["cartesian_bytes"]),
            intensity_bytes=int(value["intensity_bytes"]),
            estimated_peak_bytes=int(value["estimated_peak_bytes"]),
            trace_count=int(value.get("trace_count", 1)),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityTraceProvenance:
    """Scientific and display identity of one density-render trace."""

    field_key: str
    label: str
    storage_backend: str
    source_provenance: DensitySourceProvenance
    requested_mass_fraction: float
    scientific_hdr_threshold: float
    achieved_mass_fraction: float
    eligible_node_count: int
    selected_point_count: int
    selection_policy: str = DENSITY_NODE_CLOUD_SELECTION_POLICY
    display_replication: str = "canonical"
    image_shift: tuple[int, int, int] = (0, 0, 0)
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_TRACE_PROVENANCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_TRACE_PROVENANCE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-trace schema {self.schema_version!r}."
            )
        for name in (
            "field_key",
            "label",
            "storage_backend",
            "selection_policy",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise GraphAdapterError(f"{name} must be a nonempty string.")
        if self.display_replication not in {"canonical", "match_graph"}:
            raise GraphAdapterError(
                "display_replication must be canonical or match_graph."
            )
        if not isinstance(self.source_provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance.")
        requested = float(self.requested_mass_fraction)
        threshold = float(self.scientific_hdr_threshold)
        achieved = float(self.achieved_mass_fraction)
        if not 0.0 < requested < 1.0:
            raise GraphStyleError("requested_mass_fraction must lie in (0, 1).")
        if not np.isfinite(threshold) or threshold <= 0.0:
            raise GraphAdapterError("scientific_hdr_threshold must be positive.")
        if not np.isfinite(achieved) or not requested <= achieved <= 1.0 + 5.0e-13:
            raise GraphAdapterError("achieved_mass_fraction is inconsistent.")
        eligible = _positive_int(self.eligible_node_count, name="eligible_node_count")
        selected = _positive_int(self.selected_point_count, name="selected_point_count")
        if selected > eligible:
            raise GraphAdapterError("selected_point_count exceeds eligible_node_count.")
        object.__setattr__(self, "requested_mass_fraction", requested)
        object.__setattr__(self, "scientific_hdr_threshold", threshold)
        object.__setattr__(self, "achieved_mass_fraction", min(1.0, achieved))
        object.__setattr__(self, "eligible_node_count", eligible)
        object.__setattr__(self, "selected_point_count", selected)
        object.__setattr__(self, "image_shift", _validated_shift(self.image_shift))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def with_image_shift(self, shift: tuple[int, int, int]) -> "DensityTraceProvenance":
        return DensityTraceProvenance(
            field_key=self.field_key,
            label=self.label,
            storage_backend=self.storage_backend,
            source_provenance=self.source_provenance,
            requested_mass_fraction=self.requested_mass_fraction,
            scientific_hdr_threshold=self.scientific_hdr_threshold,
            achieved_mass_fraction=self.achieved_mass_fraction,
            eligible_node_count=self.eligible_node_count,
            selected_point_count=self.selected_point_count,
            selection_policy=self.selection_policy,
            display_replication=self.display_replication,
            image_shift=shift,
            metadata=self.metadata,
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "label": self.label,
            "storage_backend": self.storage_backend,
            "source_provenance": self.source_provenance.to_json_dict(),
            "requested_mass_fraction": self.requested_mass_fraction,
            "scientific_hdr_threshold": self.scientific_hdr_threshold,
            "achieved_mass_fraction": self.achieved_mass_fraction,
            "eligible_node_count": self.eligible_node_count,
            "selected_point_count": self.selected_point_count,
            "selection_policy": self.selection_policy,
            "display_replication": self.display_replication,
            "image_shift": list(self.image_shift),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityTraceProvenance":
        return cls(
            schema_version=str(value["schema_version"]),
            field_key=str(value["field_key"]),
            label=str(value["label"]),
            storage_backend=str(value["storage_backend"]),
            source_provenance=DensitySourceProvenance.from_json_dict(
                value["source_provenance"]
            ),
            requested_mass_fraction=float(value["requested_mass_fraction"]),
            scientific_hdr_threshold=float(value["scientific_hdr_threshold"]),
            achieved_mass_fraction=float(value["achieved_mass_fraction"]),
            eligible_node_count=int(value["eligible_node_count"]),
            selected_point_count=int(value["selected_point_count"]),
            selection_policy=str(value["selection_policy"]),
            display_replication=str(value["display_replication"]),
            image_shift=tuple(value["image_shift"]),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityNodeCloud3D:
    """Prepared canonical logical-node point cloud for one density field."""

    logical_indices: IntArray
    cartesian_positions: FloatArray
    relative_intensities: FloatArray
    hdr_details: SparseHDRDetails
    bounds: DensityCartesianBounds
    resources: DensityNodeCloudResources
    provenance: DensityTraceProvenance
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_NODE_CLOUD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_NODE_CLOUD_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-node-cloud schema {self.schema_version!r}."
            )
        indices = _readonly_array(
            self.logical_indices, np.int64, ndim=2, name="logical_indices"
        )
        positions = _readonly_array(
            self.cartesian_positions,
            np.float64,
            ndim=2,
            name="cartesian_positions",
        )
        intensities = _readonly_array(
            self.relative_intensities,
            np.float64,
            ndim=1,
            name="relative_intensities",
        )
        if indices.shape[1:] != (3,) or indices.shape[0] == 0:
            raise GraphAdapterError(
                "logical_indices must have shape (n_points, 3), n_points > 0."
            )
        if positions.shape != indices.shape or intensities.shape != (indices.shape[0],):
            raise GraphAdapterError("Density cloud arrays are not aligned.")
        if np.any((intensities <= 0.0) | (intensities > 1.0 + 4.0e-15)):
            raise GraphAdapterError("relative_intensities must lie in (0, 1].")
        if not isinstance(self.hdr_details, SparseHDRDetails):
            raise TypeError("hdr_details must be SparseHDRDetails.")
        if not isinstance(self.bounds, DensityCartesianBounds):
            raise TypeError("bounds must be DensityCartesianBounds.")
        if not isinstance(self.resources, DensityNodeCloudResources):
            raise TypeError("resources must be DensityNodeCloudResources.")
        if not isinstance(self.provenance, DensityTraceProvenance):
            raise TypeError("provenance must be DensityTraceProvenance.")
        if self.resources.selected_point_count != indices.shape[0]:
            raise GraphAdapterError("Resource selected-point count is inconsistent.")
        object.__setattr__(self, "logical_indices", indices)
        object.__setattr__(self, "cartesian_positions", positions)
        object.__setattr__(self, "relative_intensities", intensities)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def translated_positions(self, image_shift: tuple[int, int, int], cell: FloatArray) -> FloatArray:
        shift = np.asarray(_validated_shift(image_shift), dtype=np.float64)
        matrix = np.asarray(cell, dtype=np.float64)
        if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
            raise GraphAdapterError("cell must be a finite 3x3 matrix.")
        result = np.asarray(
            self.cartesian_positions + shift @ matrix,
            dtype=np.float64,
        )
        result.setflags(write=False)
        return result

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "logical_indices": self.logical_indices.tolist(),
            "cartesian_positions": self.cartesian_positions.tolist(),
            "relative_intensities": self.relative_intensities.tolist(),
            "hdr_details": self.hdr_details.to_json_dict(),
            "bounds": self.bounds.to_json_dict(),
            "resources": self.resources.to_json_dict(),
            "provenance": self.provenance.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityNodeCloud3D":
        hdr = value["hdr_details"]
        return cls(
            schema_version=str(value["schema_version"]),
            logical_indices=np.asarray(value["logical_indices"], dtype=np.int64),
            cartesian_positions=np.asarray(
                value["cartesian_positions"], dtype=np.float64
            ),
            relative_intensities=np.asarray(
                value["relative_intensities"], dtype=np.float64
            ),
            hdr_details=SparseHDRDetails(
                schema_version=str(hdr["schema_version"]),
                requested_mass_fraction=float(hdr["requested_mass_fraction"]),
                threshold=float(hdr["threshold"]),
                achieved_mass_fraction=float(hdr["achieved_mass_fraction"]),
                selected_node_count=int(hdr["selected_node_count"]),
                threshold_tie_count=int(hdr["threshold_tie_count"]),
                selected_measure=float(hdr["selected_measure"]),
                total_measure=float(hdr["total_measure"]),
            ),
            bounds=DensityCartesianBounds.from_json_dict(value["bounds"]),
            resources=DensityNodeCloudResources.from_json_dict(value["resources"]),
            provenance=DensityTraceProvenance.from_json_dict(value["provenance"]),
            metadata=value.get("metadata", {}),
        )


def _validated_node_batches(
    field: ScalarField3D,
) -> Iterator[tuple[IntArray, FloatArray]]:
    if not is_periodic_node_field_access(field):
        raise TypeError("field must satisfy PeriodicNodeFieldAccess.")
    node_access: PeriodicNodeFieldAccess = field
    shape = _shape3(field.grid_shape, name="grid_shape")
    shape_array = np.asarray(shape, dtype=np.int64)
    previous_flat = -1
    for indices_value, values_value in node_access.iter_stored_nodes():
        indices = np.asarray(indices_value)
        values = np.asarray(values_value, dtype=np.float64)
        if indices.ndim != 2 or indices.shape[1:] != (3,):
            raise GraphAdapterError("Stored logical indices must have shape (n, 3).")
        if not np.issubdtype(indices.dtype, np.integer):
            raise GraphAdapterError("Stored logical indices must be integers.")
        indices = indices.astype(np.int64, copy=False)
        if values.ndim != 1 or values.shape != (indices.shape[0],):
            raise GraphAdapterError("Stored node values must align with logical indices.")
        if np.any(indices < 0) or np.any(indices >= shape_array[None, :]):
            raise GraphAdapterError("Stored logical indices lie outside the logical grid.")
        if np.any(~np.isfinite(values)) or np.any(values < 0.0):
            raise GraphAdapterError("Stored node values must be finite and nonnegative.")
        if indices.shape[0] == 0:
            continue
        flat = np.ravel_multi_index(
            (indices[:, 0], indices[:, 1], indices[:, 2]), shape, order="C"
        ).astype(np.int64, copy=False)
        if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
            raise GraphAdapterError(
                "Stored node iteration must be strictly lexicographic."
            )
        if int(flat[0]) <= previous_flat:
            raise GraphAdapterError(
                "Stored node batches must be globally strictly lexicographic."
            )
        previous_flat = int(flat[-1])
        yield indices, values


def _selection_ranks(eligible_count: int, selected_count: int) -> IntArray:
    if selected_count == eligible_count:
        ranks = np.arange(eligible_count, dtype=np.int64)
    else:
        ranks = np.linspace(
            0,
            eligible_count - 1,
            selected_count,
            dtype=np.int64,
        )
    if ranks.size > 1 and np.any(ranks[1:] <= ranks[:-1]):
        raise GraphAdapterError("Deterministic cloud ranks are not strictly increasing.")
    ranks.setflags(write=False)
    return ranks


def prepare_density_node_cloud(
    field: ScalarField3D,
    mass_fraction: float,
    *,
    max_points: int,
    max_workspace_bytes: int | None = None,
    display_replication: str = "canonical",
) -> DensityNodeCloud3D:
    """Prepare one deterministic logical-node cloud without dense conversion."""

    if not is_scalar_field3d(field):
        raise TypeError("field must satisfy ScalarField3D.")
    if not is_periodic_node_field_access(field):
        raise TypeError("field must satisfy PeriodicNodeFieldAccess.")
    point_limit = _positive_int(max_points, name="max_points")
    budget, _model, _derived = resolve_density_resource_limits()
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    if display_replication not in {"canonical", "match_graph"}:
        raise GraphStyleError(
            "display_replication must be canonical or match_graph."
        )
    details = field.hdr_details(float(mass_fraction))
    threshold = float(details.threshold)

    scanned = 0
    eligible = 0
    for _indices, values in _validated_node_batches(field):
        scanned += int(values.size)
        eligible += int(np.count_nonzero(values >= threshold))
    if eligible == 0:
        raise GraphAdapterError("The requested density cloud contains no nodes.")
    selected_count = min(eligible, point_limit)
    ranks = _selection_ranks(eligible, selected_count)

    index_bytes = selected_count * 3 * np.dtype(np.int64).itemsize
    value_bytes = selected_count * np.dtype(np.float64).itemsize
    cartesian_bytes = selected_count * 3 * np.dtype(np.float64).itemsize
    intensity_bytes = value_bytes
    fractional_bytes = cartesian_bytes
    estimated_peak = int(
        ranks.nbytes
        + index_bytes
        + value_bytes
        + cartesian_bytes
        + intensity_bytes
        + fractional_bytes
    )
    if estimated_peak > workspace_limit:
        raise GraphComplexityError(
            f"Density cloud preparation requires an estimated {estimated_peak} bytes, "
            f"exceeding max_workspace_bytes={workspace_limit}."
        )

    selected_indices = np.empty((selected_count, 3), dtype=np.int64)
    selected_values = np.empty(selected_count, dtype=np.float64)
    rank_cursor = 0
    eligible_seen = 0
    output_cursor = 0
    for indices, values in _validated_node_batches(field):
        mask = values >= threshold
        count = int(np.count_nonzero(mask))
        if count == 0:
            continue
        batch_indices = indices[mask]
        batch_values = values[mask]
        upper = eligible_seen + count
        start_rank_cursor = rank_cursor
        while rank_cursor < selected_count and int(ranks[rank_cursor]) < upper:
            rank_cursor += 1
        if rank_cursor > start_rank_cursor:
            local = ranks[start_rank_cursor:rank_cursor] - eligible_seen
            amount = int(local.size)
            selected_indices[output_cursor : output_cursor + amount] = batch_indices[local]
            selected_values[output_cursor : output_cursor + amount] = batch_values[local]
            output_cursor += amount
        eligible_seen = upper
    if output_cursor != selected_count or rank_cursor != selected_count:
        raise GraphAdapterError("Density cloud selection did not realize its exact plan.")

    shape = np.asarray(field.grid_shape, dtype=np.float64)
    fractional = selected_indices.astype(np.float64) / shape[None, :]
    cartesian = np.asarray(fractional @ field.display_cell, dtype=np.float64)
    peak = float(np.max(selected_values))
    if not np.isfinite(peak) or peak <= 0.0:
        raise GraphAdapterError("Selected density cloud has no positive peak.")
    intensities = np.asarray(selected_values / peak, dtype=np.float64)
    bounds = DensityCartesianBounds(
        minimum=np.min(cartesian, axis=0),
        maximum=np.max(cartesian, axis=0),
    )
    resources = DensityNodeCloudResources(
        scanned_stored_node_count=scanned,
        eligible_node_count=eligible,
        selected_point_count=selected_count,
        truncated=selected_count < eligible,
        index_bytes=index_bytes,
        value_bytes=value_bytes,
        cartesian_bytes=cartesian_bytes,
        intensity_bytes=intensity_bytes,
        estimated_peak_bytes=estimated_peak,
        metadata={
            "logical_grid_shape": list(field.grid_shape),
            "selection_policy": DENSITY_NODE_CLOUD_SELECTION_POLICY,
            "workspace_limit_bytes": workspace_limit,
        },
    )
    provenance = DensityTraceProvenance(
        field_key=field.field_key,
        label=field.label,
        storage_backend=field.storage_backend,
        source_provenance=field.source_provenance,
        requested_mass_fraction=details.requested_mass_fraction,
        scientific_hdr_threshold=details.threshold,
        achieved_mass_fraction=details.achieved_mass_fraction,
        eligible_node_count=eligible,
        selected_point_count=selected_count,
        display_replication=display_replication,
        metadata={
            "truncated": selected_count < eligible,
            "threshold_tie_count": details.threshold_tie_count,
        },
    )
    return DensityNodeCloud3D(
        logical_indices=selected_indices,
        cartesian_positions=cartesian,
        relative_intensities=intensities,
        hdr_details=details,
        bounds=bounds,
        resources=resources,
        provenance=provenance,
        metadata={
            "logical_node_convention": "fractional_index_over_shape",
            "dense_materialization_used": False,
        },
    )
