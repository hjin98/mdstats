"""Backend-neutral periodic cell and logical-grid geometry for density fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from ._frozen_json import FrozenJSONMapping, freeze_json_mapping
from .numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalSerializationError,
)

FloatArray = NDArray[np.float64]
DENSITY_GRID_GEOMETRY_SCHEMA = "mdstats.density-grid-geometry.v1"


def _validated_cell(value: Any) -> FloatArray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
        raise DensityNumericalInputError("display_cell must be a finite 3x3 matrix.")
    if abs(float(np.linalg.det(matrix))) <= 1.0e-12:
        raise DensityNumericalInputError("display_cell must be nonsingular.")
    result = np.array(matrix, dtype=np.float64, copy=True, order="C")
    result.setflags(write=False)
    return result


def _validated_shape(value: Any) -> tuple[int, int, int]:
    try:
        entries = tuple(value)
    except TypeError as error:
        raise DensityNumericalInputError(
            "grid_shape must contain three positive integers."
        ) from error
    if len(entries) != 3:
        raise DensityNumericalInputError("grid_shape must contain three entries.")
    result: list[int] = []
    for entry in entries:
        if isinstance(entry, bool) or not isinstance(entry, (int, np.integer)):
            raise DensityNumericalInputError(
                "grid_shape entries must be positive integers."
            )
        item = int(entry)
        if item <= 0:
            raise DensityNumericalInputError(
                "grid_shape entries must be positive integers."
            )
        result.append(item)
    return tuple(result)  # type: ignore[return-value]


def resolve_density_grid_shape(
    cell: Any,
    *,
    grid_shape: tuple[int, int, int] | None,
    grid_interval: float,
) -> tuple[int, int, int]:
    """Resolve an explicit shape or ``ceil(|a_i| / h)`` periodic shape."""

    matrix = _validated_cell(cell)
    if grid_shape is not None:
        return _validated_shape(grid_shape)
    interval = float(grid_interval)
    if not np.isfinite(interval) or interval <= 0.0:
        raise DensityNumericalInputError(
            "grid_interval must be finite and positive."
        )
    lengths = np.linalg.norm(matrix, axis=1)
    if np.any(lengths <= 0.0):
        raise DensityNumericalInputError(
            "display_cell vectors must have positive length."
        )
    return tuple(
        max(4, int(np.ceil(float(length) / interval - 1.0e-12)))
        for length in lengths
    )  # type: ignore[return-value]


def density_grid_intervals(
    cell: Any, shape: tuple[int, int, int]
) -> tuple[float, float, float]:
    """Return realized Euclidean lattice-grid edge lengths in angstrom."""

    matrix = _validated_cell(cell)
    counts = np.asarray(_validated_shape(shape), dtype=np.float64)
    return tuple(float(v) for v in np.linalg.norm(matrix, axis=1) / counts)


def density_resolution_ratio(
    cell: Any, shape: tuple[int, int, int], gaussian_bandwidth: float
) -> float:
    """Return Gaussian bandwidth divided by the longest lattice-grid edge."""

    matrix = _validated_cell(cell)
    validated_shape = _validated_shape(shape)
    sigma = float(gaussian_bandwidth)
    if not np.isfinite(sigma) or sigma < 0.0:
        raise DensityNumericalInputError(
            "gaussian_bandwidth must be finite and nonnegative."
        )
    if sigma == 0.0:
        return float("inf")
    steps = matrix / np.asarray(validated_shape, dtype=np.float64)[:, None]
    longest = float(np.max(np.linalg.norm(steps, axis=1)))
    return sigma / longest


@dataclass(frozen=True, slots=True)
class DensityGridGeometry:
    """Immutable cell-metric description of one logical periodic grid."""

    display_cell: FloatArray
    grid_shape: tuple[int, int, int]
    requested_grid_interval: float | None
    realized_intervals: tuple[float, float, float]
    grid_step_vectors: FloatArray
    cell_volume: float
    voxel_volume: float
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_GRID_GEOMETRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_GRID_GEOMETRY_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported density-grid geometry schema {self.schema_version!r}."
            )
        cell = _validated_cell(self.display_cell)
        shape = _validated_shape(self.grid_shape)
        realized = density_grid_intervals(cell, shape)
        supplied = tuple(float(value) for value in self.realized_intervals)
        if len(supplied) != 3 or np.any(~np.isfinite(supplied)):
            raise DensityNumericalInputError(
                "realized_intervals must contain three finite values."
            )
        if not np.allclose(supplied, realized, rtol=0.0, atol=5.0e-15):
            raise DensityNumericalInputError(
                "realized_intervals are inconsistent with cell and grid_shape."
            )
        requested = self.requested_grid_interval
        if requested is not None:
            requested = float(requested)
            if not np.isfinite(requested) or requested <= 0.0:
                raise DensityNumericalInputError(
                    "requested_grid_interval must be finite and positive."
                )
        steps = np.array(
            cell / np.asarray(shape, dtype=np.float64)[:, None],
            dtype=np.float64,
            copy=True,
            order="C",
        )
        supplied_steps = np.asarray(self.grid_step_vectors, dtype=np.float64)
        if supplied_steps.shape != (3, 3) or np.any(~np.isfinite(supplied_steps)):
            raise DensityNumericalInputError(
                "grid_step_vectors must be a finite 3x3 matrix."
            )
        if not np.allclose(supplied_steps, steps, rtol=0.0, atol=5.0e-15):
            raise DensityNumericalInputError(
                "grid_step_vectors are inconsistent with cell and grid_shape."
            )
        volume = abs(float(np.linalg.det(cell)))
        voxel = volume / float(np.prod(shape, dtype=object))
        if abs(float(self.cell_volume) - volume) > 5.0e-13 * max(1.0, volume):
            raise DensityNumericalInputError("cell_volume is inconsistent.")
        if abs(float(self.voxel_volume) - voxel) > 5.0e-13 * max(1.0, voxel):
            raise DensityNumericalInputError("voxel_volume is inconsistent.")
        steps.setflags(write=False)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "requested_grid_interval", requested)
        object.__setattr__(self, "realized_intervals", realized)
        object.__setattr__(self, "grid_step_vectors", steps)
        object.__setattr__(self, "cell_volume", volume)
        object.__setattr__(self, "voxel_volume", voxel)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def logical_voxel_count(self) -> int:
        return int(np.prod(self.grid_shape, dtype=object))

    @property
    def longest_grid_interval(self) -> float:
        return float(max(self.realized_intervals))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "display_cell": self.display_cell.tolist(),
            "grid_shape": list(self.grid_shape),
            "requested_grid_interval": self.requested_grid_interval,
            "realized_intervals": list(self.realized_intervals),
            "grid_step_vectors": self.grid_step_vectors.tolist(),
            "cell_volume": self.cell_volume,
            "voxel_volume": self.voxel_volume,
            "logical_voxel_count": self.logical_voxel_count,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityGridGeometry":
        if payload.get("schema_version") != DENSITY_GRID_GEOMETRY_SCHEMA:
            raise DensityNumericalSerializationError(
                "Unsupported or missing density-grid geometry schema."
            )
        return cls(
            display_cell=payload["display_cell"],
            grid_shape=tuple(payload["grid_shape"]),
            requested_grid_interval=payload.get("requested_grid_interval"),
            realized_intervals=tuple(payload["realized_intervals"]),
            grid_step_vectors=payload["grid_step_vectors"],
            cell_volume=payload["cell_volume"],
            voxel_volume=payload["voxel_volume"],
            metadata=payload.get("metadata", {}),
            schema_version=str(payload["schema_version"]),
        )


def prepare_density_grid_geometry(
    cell: Any,
    *,
    grid_shape: tuple[int, int, int] | None = None,
    grid_interval: float = 0.20,
    metadata: Mapping[str, Any] | None = None,
) -> DensityGridGeometry:
    matrix = _validated_cell(cell)
    shape = resolve_density_grid_shape(
        matrix, grid_shape=grid_shape, grid_interval=grid_interval
    )
    requested = None if grid_shape is not None else float(grid_interval)
    realized = density_grid_intervals(matrix, shape)
    steps = matrix / np.asarray(shape, dtype=np.float64)[:, None]
    volume = abs(float(np.linalg.det(matrix)))
    return DensityGridGeometry(
        display_cell=matrix,
        grid_shape=shape,
        requested_grid_interval=requested,
        realized_intervals=realized,
        grid_step_vectors=steps,
        cell_volume=volume,
        voxel_volume=volume / float(np.prod(shape, dtype=object)),
        metadata={} if metadata is None else metadata,
    )
