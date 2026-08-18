"""Hybrid tiled direct/FFT density realization for LD8-S3.

The executor partitions the globally aggregated packed CIC source into bounded
Cartesian logical-grid tiles.  Sparse tiles use a vectorized finite-stencil
scatter; sufficiently populated tiles use zero-padded three-dimensional
linear convolution and periodic overlap-add into the exact LD8-S1 packed
support.  Both paths realize the same normalized finite stencil retained at
``kernel_tail_tolerance=1e-8``; the selector changes execution only.

The overlap-add organization follows Oppenheim, Schafer, and Buck,
*Discrete-Time Signal Processing*, 2nd ed. (1999).  The metric-aware discrete
stencil, periodic sparse target lookup, and mixed tile selector are
project-specific mdstats designs.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy import __version__ as scipy_version
from scipy.fft import irfftn, next_fast_len, rfftn

from .density_block_routing import (
    PeriodicKernelBlockRouting,
    bitset_popcount,
    bitset_popcounts,
    stencil_content_identity,
    unpack_local_bitset,
)
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_kernel import PeriodicGaussianStencilSupport
from .density_packed_field import PeriodicPackedBlockScalarField3D
from .density_support_atlas import DensitySupportAtlas, PeriodicPackedCICSourceField3D
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port
from .runtime_resources import resolve_density_resource_limits
from .density_scheduler import current_density_worker_count, current_density_worker_lease
from .density_autotune import autotuned_fft_worker_count
from .density_gpu import try_gpu_linear_fft_convolution

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_HYBRID_OPTIONS_SCHEMA = "mdstats.density-hybrid-executor-options.v1"
DENSITY_HYBRID_LIMITS_SCHEMA = "mdstats.density-hybrid-realization-limits.v1"
DENSITY_HYBRID_TILE_PLAN_SCHEMA = "mdstats.density-hybrid-tile-plan.v1"
DENSITY_HYBRID_PLAN_SCHEMA = "mdstats.density-hybrid-realization-plan.v1"

DEFAULT_COMPUTE_TILE_SHAPE = (32, 32, 32)
DEFAULT_HYBRID_PAIR_CHUNK_SIZE = 262_144
DEFAULT_MIN_FFT_SOURCE_NODES = 32
DEFAULT_DIRECT_PAIR_SECONDS = 5.0e-8
DEFAULT_FFT_WORK_SECONDS = 1.5e-9
DEFAULT_FFT_FIXED_SECONDS = 4.0e-3
DEFAULT_MAX_HYBRID_TILES = 2_000_000
DEFAULT_MAX_HYBRID_TARGET_NODES = 100_000_000
DEFAULT_MAX_HYBRID_DIRECT_PAIRS = 20_000_000_000
DEFAULT_MAX_HYBRID_FFT_PADDED_NODES = 32_000_000
DEFAULT_MAX_HYBRID_LOOKUP_BYTES = 2_000_000_000
DEFAULT_MAX_HYBRID_KERNEL_CACHE_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_HYBRID_TRANSIENT_BYTES = 2_000_000_000
DEFAULT_MAX_HYBRID_RETAINED_BYTES = 2_000_000_000

ExecutorMode = Literal["auto", "direct", "fft"]
TileExecutor = Literal["direct", "fft"]


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _positive_float(value: Any, *, name: str, allow_zero: bool = False) -> float:
    result = float(value)
    minimum_ok = result >= 0.0 if allow_zero else result > 0.0
    if not np.isfinite(result) or not minimum_ok:
        comparator = ">= 0" if allow_zero else "> 0"
        raise GraphStyleError(f"{name} must be finite and {comparator}.")
    return result


def _shape3(value: Any, *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphStyleError(f"{name} must contain three entries.")
    return tuple(_positive_int(item, name=f"{name} entry") for item in value)  # type: ignore[return-value]


def _nonempty_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraphStyleError(f"{name} must be a nonempty string.")
    return value


def _executor_mode(value: Any) -> ExecutorMode:
    if value not in {"auto", "direct", "fft"}:
        raise GraphStyleError("executor_mode must be 'auto', 'direct', or 'fft'.")
    return value


@dataclass(frozen=True, slots=True)
class DensityHybridExecutorOptions:
    """Deterministic tile geometry and calibrated selector controls."""

    executor_mode: ExecutorMode = "auto"
    compute_tile_shape: tuple[int, int, int] = DEFAULT_COMPUTE_TILE_SHAPE
    pair_chunk_size: int | None = None
    min_fft_source_nodes: int = DEFAULT_MIN_FFT_SOURCE_NODES
    direct_pair_seconds: float | None = None
    fft_work_seconds: float | None = None
    fft_fixed_seconds: float | None = None
    fft_workers: int | None = None
    cache_kernel_spectra: bool = True
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_HYBRID_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_HYBRID_OPTIONS_SCHEMA:
            raise GraphAdapterError(f"Unsupported hybrid-options schema {self.schema_version!r}.")
        object.__setattr__(self, "executor_mode", _executor_mode(self.executor_mode))
        object.__setattr__(self, "compute_tile_shape", _shape3(self.compute_tile_shape, name="compute_tile_shape"))
        budget, model, _derived = resolve_density_resource_limits()
        default_pair_chunk = max(
            1_024,
            min(DEFAULT_HYBRID_PAIR_CHUNK_SIZE, budget.max_memory_bytes // 384),
        )
        requested_pair_chunk = self.pair_chunk_size
        pair_chunk = (
            default_pair_chunk
            if requested_pair_chunk is None
            else min(
                default_pair_chunk,
                _positive_int(requested_pair_chunk, name="pair_chunk_size"),
            )
        )
        workers = (
            budget.max_threads
            if self.fft_workers is None
            else min(_positive_int(self.fft_workers, name="fft_workers"), budget.max_threads)
        )
        # The selector costs are derived from runtime calibration rather than
        # retained benchmark constants.  They choose the cheaper executor only;
        # wall-time estimates are never realization admission bounds.
        calibrated_direct_pair_seconds = 1.0 / model.direct_reduction_pairs_per_second
        requested_direct_pair_seconds = self.direct_pair_seconds
        direct_pair_seconds = (
            calibrated_direct_pair_seconds
            if requested_direct_pair_seconds is None
            else max(
                calibrated_direct_pair_seconds,
                _positive_float(
                    requested_direct_pair_seconds, name="direct_pair_seconds"
                ),
            )
        )
        calibrated_fft_work_seconds = 1.0 / model.fft_work_units_per_second
        requested_fft_work_seconds = self.fft_work_seconds
        fft_work_seconds = (
            calibrated_fft_work_seconds
            if requested_fft_work_seconds is None
            else max(
                calibrated_fft_work_seconds,
                _positive_float(
                    requested_fft_work_seconds, name="fft_work_seconds"
                ),
            )
        )
        calibrated_fft_fixed_seconds = model.fixed_seconds_per_field
        requested_fft_fixed_seconds = self.fft_fixed_seconds
        fft_fixed_seconds = (
            calibrated_fft_fixed_seconds
            if requested_fft_fixed_seconds is None
            else max(
                calibrated_fft_fixed_seconds,
                _positive_float(
                    requested_fft_fixed_seconds,
                    name="fft_fixed_seconds",
                    allow_zero=True,
                ),
            )
        )
        object.__setattr__(self, "pair_chunk_size", pair_chunk)
        object.__setattr__(self, "min_fft_source_nodes", _positive_int(self.min_fft_source_nodes, name="min_fft_source_nodes"))
        object.__setattr__(self, "direct_pair_seconds", direct_pair_seconds)
        object.__setattr__(self, "fft_work_seconds", fft_work_seconds)
        object.__setattr__(self, "fft_fixed_seconds", fft_fixed_seconds)
        object.__setattr__(self, "fft_workers", workers)
        if not isinstance(self.cache_kernel_spectra, bool):
            raise GraphStyleError("cache_kernel_spectra must be boolean.")
        metadata = dict(freeze_json_mapping(self.metadata))
        metadata.setdefault("resource_policy", "runtime_derived_v2")
        metadata.setdefault("max_threads", budget.max_threads)
        metadata.setdefault("max_wall_time_seconds", budget.max_wall_time_seconds)
        metadata.setdefault("time_model_source", model.calibration_source)
        metadata.setdefault(
            "pair_chunk_source",
            "runtime_memory" if requested_pair_chunk is None else (
                "explicit_clamped_to_runtime"
                if requested_pair_chunk > default_pair_chunk
                else "explicit"
            ),
        )
        metadata.setdefault(
            "timing_overrides_are_tightening_only",
            True,
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "executor_mode": self.executor_mode,
            "compute_tile_shape": list(self.compute_tile_shape),
            "pair_chunk_size": self.pair_chunk_size,
            "min_fft_source_nodes": self.min_fft_source_nodes,
            "direct_pair_seconds": self.direct_pair_seconds,
            "fft_work_seconds": self.fft_work_seconds,
            "fft_fixed_seconds": self.fft_fixed_seconds,
            "fft_workers": self.fft_workers,
            "cache_kernel_spectra": self.cache_kernel_spectra,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityHybridExecutorOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            executor_mode=str(value["executor_mode"]),  # type: ignore[arg-type]
            compute_tile_shape=tuple(value["compute_tile_shape"]),
            pair_chunk_size=(None if value.get("pair_chunk_size") is None else int(value["pair_chunk_size"])),
            min_fft_source_nodes=int(value["min_fft_source_nodes"]),
            direct_pair_seconds=(None if value.get("direct_pair_seconds") is None else float(value["direct_pair_seconds"])),
            fft_work_seconds=(None if value.get("fft_work_seconds") is None else float(value["fft_work_seconds"])),
            fft_fixed_seconds=(None if value.get("fft_fixed_seconds") is None else float(value["fft_fixed_seconds"])),
            fft_workers=(None if value.get("fft_workers") is None else int(value["fft_workers"])),
            cache_kernel_spectra=bool(value["cache_kernel_spectra"]),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityHybridRealizationLimits:
    """Runtime-derived preflight limits for one hybrid realization."""

    max_compute_tiles: int | None = None
    max_target_nodes: int | None = None
    max_direct_pairs: int | None = None
    max_fft_padded_nodes_per_tile: int | None = None
    max_lookup_bytes: int | None = None
    max_kernel_cache_bytes: int | None = None
    max_transient_bytes: int | None = None
    max_retained_bytes: int | None = None
    max_total_peak_bytes: int | None = None
    max_wall_time_seconds: float | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_HYBRID_LIMITS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_HYBRID_LIMITS_SCHEMA:
            raise GraphAdapterError(f"Unsupported hybrid-limits schema {self.schema_version!r}.")
        budget, model, derived = resolve_density_resource_limits(
            max_wall_time_seconds=self.max_wall_time_seconds
        )
        defaults = {
            "max_compute_tiles": derived["max_density_blocks"],
            "max_target_nodes": derived["max_density_nonzero_nodes"],
            "max_direct_pairs": derived["max_density_kernel_pairs"],
            "max_fft_padded_nodes_per_tile": derived["max_density_voxels"],
            "max_lookup_bytes": budget.max_memory_bytes,
            "max_kernel_cache_bytes": budget.max_memory_bytes,
            "max_transient_bytes": budget.max_memory_bytes,
            "max_retained_bytes": budget.max_memory_bytes,
            "max_total_peak_bytes": budget.max_memory_bytes,
        }
        memory_names = {
            "max_lookup_bytes", "max_kernel_cache_bytes",
            "max_transient_bytes", "max_retained_bytes",
            "max_total_peak_bytes",
        }
        for name, default in defaults.items():
            current = getattr(self, name)
            resolved = default if current is None else min(default, _positive_int(current, name=name))
            if name in memory_names:
                resolved = min(resolved, budget.max_memory_bytes)
            object.__setattr__(self, name, resolved)
        wall = budget.max_wall_time_seconds
        object.__setattr__(self, "max_wall_time_seconds", wall)
        metadata = dict(freeze_json_mapping(self.metadata))
        metadata.setdefault("resource_policy", "runtime_derived_v1")
        metadata.setdefault("max_threads", budget.max_threads)
        metadata.setdefault("time_model_source", model.calibration_source)
        object.__setattr__(self, "metadata", freeze_json_mapping(metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_compute_tiles": self.max_compute_tiles,
            "max_target_nodes": self.max_target_nodes,
            "max_direct_pairs": self.max_direct_pairs,
            "max_fft_padded_nodes_per_tile": self.max_fft_padded_nodes_per_tile,
            "max_lookup_bytes": self.max_lookup_bytes,
            "max_kernel_cache_bytes": self.max_kernel_cache_bytes,
            "max_transient_bytes": self.max_transient_bytes,
            "max_retained_bytes": self.max_retained_bytes,
            "max_total_peak_bytes": self.max_total_peak_bytes,
            "max_wall_time_seconds": self.max_wall_time_seconds,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityHybridRealizationLimits":
        data = dict(value)
        data.setdefault("max_total_peak_bytes", None)
        data.setdefault("max_wall_time_seconds", None)
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DensityHybridTilePlan:
    tile_index: tuple[int, int, int]
    origin: tuple[int, int, int]
    extent: tuple[int, int, int]
    source_start: int
    source_stop: int
    source_node_count: int
    source_fill_fraction: float
    executor: TileExecutor
    direct_pair_count: int
    full_convolution_shape: tuple[int, int, int]
    fft_padded_shape: tuple[int, int, int]
    fft_padded_node_count: int
    direct_cost_estimate_seconds: float
    fft_cost_estimate_seconds: float
    transient_bytes_estimate: int
    cache_kernel_spectrum: bool
    schema_version: str = DENSITY_HYBRID_TILE_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_HYBRID_TILE_PLAN_SCHEMA:
            raise GraphAdapterError(f"Unsupported hybrid tile-plan schema {self.schema_version!r}.")
        for name in ("tile_index", "origin"):
            value = tuple(int(item) for item in getattr(self, name))
            if len(value) != 3 or any(item < 0 for item in value):
                raise GraphAdapterError(f"{name} must contain three nonnegative integers.")
            object.__setattr__(self, name, value)
        for name in ("extent", "full_convolution_shape", "fft_padded_shape"):
            object.__setattr__(self, name, _shape3(getattr(self, name), name=name))
        for name in (
            "source_start", "source_stop", "source_node_count", "direct_pair_count",
            "fft_padded_node_count", "transient_bytes_estimate",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.source_stop <= self.source_start or self.source_node_count != self.source_stop - self.source_start:
            raise GraphAdapterError("Tile source range is empty or inconsistent.")
        if self.executor not in {"direct", "fft"}:
            raise GraphAdapterError("Tile executor must be 'direct' or 'fft'.")
        fill = float(self.source_fill_fraction)
        if not np.isfinite(fill) or not (0.0 < fill <= 1.0):
            raise GraphAdapterError("source_fill_fraction must lie in (0, 1].")
        object.__setattr__(self, "source_fill_fraction", fill)
        for name in ("direct_cost_estimate_seconds", "fft_cost_estimate_seconds"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if not isinstance(self.cache_kernel_spectrum, bool):
            raise GraphAdapterError("cache_kernel_spectrum must be boolean.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tile_index": list(self.tile_index),
            "origin": list(self.origin),
            "extent": list(self.extent),
            "source_start": self.source_start,
            "source_stop": self.source_stop,
            "source_node_count": self.source_node_count,
            "source_fill_fraction": self.source_fill_fraction,
            "executor": self.executor,
            "direct_pair_count": self.direct_pair_count,
            "full_convolution_shape": list(self.full_convolution_shape),
            "fft_padded_shape": list(self.fft_padded_shape),
            "fft_padded_node_count": self.fft_padded_node_count,
            "direct_cost_estimate_seconds": self.direct_cost_estimate_seconds,
            "fft_cost_estimate_seconds": self.fft_cost_estimate_seconds,
            "transient_bytes_estimate": self.transient_bytes_estimate,
            "cache_kernel_spectrum": self.cache_kernel_spectrum,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityHybridTilePlan":
        return cls(
            schema_version=str(value["schema_version"]),
            tile_index=tuple(value["tile_index"]),
            origin=tuple(value["origin"]),
            extent=tuple(value["extent"]),
            source_start=int(value["source_start"]),
            source_stop=int(value["source_stop"]),
            source_node_count=int(value["source_node_count"]),
            source_fill_fraction=float(value["source_fill_fraction"]),
            executor=str(value["executor"]),  # type: ignore[arg-type]
            direct_pair_count=int(value["direct_pair_count"]),
            full_convolution_shape=tuple(value["full_convolution_shape"]),
            fft_padded_shape=tuple(value["fft_padded_shape"]),
            fft_padded_node_count=int(value["fft_padded_node_count"]),
            direct_cost_estimate_seconds=float(value["direct_cost_estimate_seconds"]),
            fft_cost_estimate_seconds=float(value["fft_cost_estimate_seconds"]),
            transient_bytes_estimate=int(value["transient_bytes_estimate"]),
            cache_kernel_spectrum=bool(value["cache_kernel_spectrum"]),
        )


@dataclass(frozen=True, slots=True)
class DensityHybridRealizationPlan:
    source_field_identity: str
    routing_identity: str
    atlas_identity: str
    stencil_identity: str
    logical_grid_shape: tuple[int, int, int]
    compute_tile_shape: tuple[int, int, int]
    kernel_min_offset: tuple[int, int, int]
    kernel_shape: tuple[int, int, int]
    source_node_count: int
    target_support_node_count: int
    compute_tile_count: int
    direct_tile_count: int
    fft_tile_count: int
    exact_contribution_count: int
    direct_pair_count: int
    target_lookup_bytes: int
    kernel_dense_bytes: int
    kernel_spectrum_cache_bytes: int
    packed_field_bytes_upper: int
    predicted_peak_bytes: int
    tile_plans: tuple[DensityHybridTilePlan, ...]
    options: DensityHybridExecutorOptions
    limits: DensityHybridRealizationLimits
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_HYBRID_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_HYBRID_PLAN_SCHEMA:
            raise GraphAdapterError(f"Unsupported hybrid plan schema {self.schema_version!r}.")
        for name in ("source_field_identity", "routing_identity", "atlas_identity", "stencil_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise GraphAdapterError(f"{name} must be a SHA-256 digest.")
        object.__setattr__(self, "logical_grid_shape", _shape3(self.logical_grid_shape, name="logical_grid_shape"))
        object.__setattr__(self, "compute_tile_shape", _shape3(self.compute_tile_shape, name="compute_tile_shape"))
        minimum = tuple(int(item) for item in self.kernel_min_offset)
        if len(minimum) != 3:
            raise GraphAdapterError("kernel_min_offset must contain three entries.")
        object.__setattr__(self, "kernel_min_offset", minimum)
        object.__setattr__(self, "kernel_shape", _shape3(self.kernel_shape, name="kernel_shape"))
        for name in (
            "source_node_count", "target_support_node_count", "compute_tile_count",
            "direct_tile_count", "fft_tile_count", "exact_contribution_count",
            "direct_pair_count", "target_lookup_bytes", "kernel_dense_bytes",
            "kernel_spectrum_cache_bytes", "packed_field_bytes_upper", "predicted_peak_bytes",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.compute_tile_count != len(self.tile_plans):
            raise GraphAdapterError("compute_tile_count disagrees with tile_plans.")
        if self.direct_tile_count + self.fft_tile_count != self.compute_tile_count:
            raise GraphAdapterError("Direct and FFT tile counts do not sum to compute_tile_count.")
        if sum(tile.source_node_count for tile in self.tile_plans) != self.source_node_count:
            raise GraphAdapterError("Tile plans do not partition the packed source nodes.")
        if not isinstance(self.options, DensityHybridExecutorOptions):
            raise TypeError("options must be DensityHybridExecutorOptions.")
        if not isinstance(self.limits, DensityHybridRealizationLimits):
            raise TypeError("limits must be DensityHybridRealizationLimits.")
        object.__setattr__(self, "tile_plans", tuple(self.tile_plans))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def content_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        for value in (self.source_field_identity, self.routing_identity, self.atlas_identity, self.stencil_identity):
            digest.update(value.encode("ascii"))
        digest.update(np.asarray(self.logical_grid_shape + self.compute_tile_shape + self.kernel_min_offset + self.kernel_shape, dtype=np.int64).tobytes())
        digest.update(np.asarray([
            self.source_node_count, self.target_support_node_count, self.compute_tile_count,
            self.direct_tile_count, self.fft_tile_count, self.exact_contribution_count,
            self.direct_pair_count, self.target_lookup_bytes, self.kernel_dense_bytes,
            self.kernel_spectrum_cache_bytes, self.packed_field_bytes_upper,
            self.predicted_peak_bytes,
        ], dtype=np.int64).tobytes())
        for tile in self.tile_plans:
            digest.update(json.dumps(tile.to_json_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(json.dumps(self.options.to_json_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return digest.hexdigest()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_field_identity": self.source_field_identity,
            "routing_identity": self.routing_identity,
            "atlas_identity": self.atlas_identity,
            "stencil_identity": self.stencil_identity,
            "logical_grid_shape": list(self.logical_grid_shape),
            "compute_tile_shape": list(self.compute_tile_shape),
            "kernel_min_offset": list(self.kernel_min_offset),
            "kernel_shape": list(self.kernel_shape),
            "source_node_count": self.source_node_count,
            "target_support_node_count": self.target_support_node_count,
            "compute_tile_count": self.compute_tile_count,
            "direct_tile_count": self.direct_tile_count,
            "fft_tile_count": self.fft_tile_count,
            "exact_contribution_count": self.exact_contribution_count,
            "direct_pair_count": self.direct_pair_count,
            "target_lookup_bytes": self.target_lookup_bytes,
            "kernel_dense_bytes": self.kernel_dense_bytes,
            "kernel_spectrum_cache_bytes": self.kernel_spectrum_cache_bytes,
            "packed_field_bytes_upper": self.packed_field_bytes_upper,
            "predicted_peak_bytes": self.predicted_peak_bytes,
            "tile_plans": [item.to_json_dict() for item in self.tile_plans],
            "options": self.options.to_json_dict(),
            "limits": self.limits.to_json_dict(),
            "content_identity": self.content_identity,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityHybridRealizationPlan":
        return cls(
            schema_version=str(value["schema_version"]),
            source_field_identity=str(value["source_field_identity"]),
            routing_identity=str(value["routing_identity"]),
            atlas_identity=str(value["atlas_identity"]),
            stencil_identity=str(value["stencil_identity"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            compute_tile_shape=tuple(value["compute_tile_shape"]),
            kernel_min_offset=tuple(value["kernel_min_offset"]),
            kernel_shape=tuple(value["kernel_shape"]),
            source_node_count=int(value["source_node_count"]),
            target_support_node_count=int(value["target_support_node_count"]),
            compute_tile_count=int(value["compute_tile_count"]),
            direct_tile_count=int(value["direct_tile_count"]),
            fft_tile_count=int(value["fft_tile_count"]),
            exact_contribution_count=int(value["exact_contribution_count"]),
            direct_pair_count=int(value["direct_pair_count"]),
            target_lookup_bytes=int(value["target_lookup_bytes"]),
            kernel_dense_bytes=int(value["kernel_dense_bytes"]),
            kernel_spectrum_cache_bytes=int(value["kernel_spectrum_cache_bytes"]),
            packed_field_bytes_upper=int(value["packed_field_bytes_upper"]),
            predicted_peak_bytes=int(value["predicted_peak_bytes"]),
            tile_plans=tuple(DensityHybridTilePlan.from_json_dict(item) for item in value["tile_plans"]),
            options=DensityHybridExecutorOptions.from_json_dict(value["options"]),
            limits=DensityHybridRealizationLimits.from_json_dict(value["limits"]),
            metadata=value.get("metadata", {}),
        )


def _validate_inputs(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
) -> None:
    if not isinstance(source_field, PeriodicPackedCICSourceField3D):
        raise TypeError("source_field must be PeriodicPackedCICSourceField3D.")
    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    if not isinstance(routing, PeriodicKernelBlockRouting):
        raise TypeError("routing must be PeriodicKernelBlockRouting.")
    if not isinstance(atlas, DensitySupportAtlas):
        raise TypeError("atlas must be DensitySupportAtlas.")
    logical = source_field.logical_grid_shape
    if stencil.grid_shape != logical or routing.logical_grid_shape != logical or atlas.logical_grid_shape != logical:
        raise GraphAdapterError("Source, stencil, routing, and atlas must share logical_grid_shape.")
    if routing.storage_block_shape != source_field.storage_block_shape or atlas.storage_block_shape != source_field.storage_block_shape:
        raise GraphAdapterError("Source, routing, and atlas must share storage_block_shape.")
    if atlas.source_field_identity != source_field.content_identity:
        raise GraphAdapterError("Atlas source identity does not match source_field.")
    if atlas.routing_identity != routing.cache_identity:
        raise GraphAdapterError("Atlas routing identity does not match routing.")
    if routing.stencil_identity != stencil_content_identity(stencil):
        raise GraphAdapterError("Routing stencil identity does not match stencil.")


def _source_coordinate_table(source_field: PeriodicPackedCICSourceField3D) -> tuple[IntArray, FloatArray]:
    block = np.asarray(source_field.storage_block_shape, dtype=np.int64)
    coordinates = np.empty((source_field.occupied_node_count, 3), dtype=np.int64)
    for row, block_index in enumerate(source_field.source_block_indices):
        start = int(source_field.block_value_offsets[row])
        stop = int(source_field.block_value_offsets[row + 1])
        local_flat = unpack_local_bitset(source_field.occupancy_bitsets[row], source_field.storage_block_shape)
        local = np.column_stack(np.unravel_index(local_flat, source_field.storage_block_shape, order="C")).astype(np.int64, copy=False)
        coordinates[start:stop] = block_index.astype(np.int64)[None, :] * block[None, :] + local
    values = np.asarray(source_field.packed_values, dtype=np.float64)
    return coordinates, values


def _target_lookup(atlas: DensitySupportAtlas) -> tuple[IntArray, IntArray, IntArray, IntArray]:
    logical = atlas.logical_grid_shape
    block = np.asarray(atlas.storage_block_shape, dtype=np.int64)
    packed_flats = np.empty(atlas.target_support_node_count, dtype=np.int64)
    support_counts = bitset_popcounts(atlas.target_support_bitsets)
    offsets = np.concatenate((np.asarray([0], dtype=np.int64), np.cumsum(support_counts, dtype=np.int64)))
    for row, block_index in enumerate(atlas.active_target_block_indices):
        local_flat = unpack_local_bitset(atlas.target_support_bitsets[row], atlas.storage_block_shape)
        local = np.column_stack(np.unravel_index(local_flat, atlas.storage_block_shape, order="C")).astype(np.int64, copy=False)
        global_coords = block_index.astype(np.int64)[None, :] * block[None, :] + local
        start, stop = int(offsets[row]), int(offsets[row + 1])
        packed_flats[start:stop] = np.ravel_multi_index((global_coords[:, 0], global_coords[:, 1], global_coords[:, 2]), logical, order="C")
    order = np.argsort(packed_flats, kind="stable")
    sorted_flats = np.array(packed_flats[order], dtype=np.int64, copy=True)
    sorted_positions = np.asarray(order, dtype=np.int64)
    if sorted_flats.size > 1 and np.any(sorted_flats[1:] <= sorted_flats[:-1]):
        raise GraphAdapterError("Exact target support contains duplicate global nodes.")
    return sorted_flats, sorted_positions, offsets, packed_flats


def _kernel_dense(stencil: PeriodicGaussianStencilSupport, routing: PeriodicKernelBlockRouting) -> tuple[FloatArray, tuple[int, int, int], tuple[int, int, int]]:
    signed = routing.signed_offsets.astype(np.int64, copy=False)
    minimum = np.min(signed, axis=0)
    maximum = np.max(signed, axis=0)
    shape = tuple(int(item) for item in (maximum - minimum + 1))
    kernel = np.zeros(shape, dtype=np.float64)
    shifted = signed - minimum[None, :]
    kernel[shifted[:, 0], shifted[:, 1], shifted[:, 2]] = stencil.active_weights
    return kernel, tuple(int(item) for item in minimum), shape


def _packed_field_bytes_upper(atlas: DensitySupportAtlas) -> int:
    return int(
        atlas.active_target_block_indices.nbytes
        + atlas.target_support_bitsets.nbytes
        + (atlas.target_block_count + 1) * np.dtype(np.int64).itemsize
        + atlas.target_support_node_count * np.dtype(np.float64).itemsize
        + 2 * atlas.target_block_count * np.dtype(np.float64).itemsize
    )


def _fft_transient_bytes(extent: tuple[int, int, int], kernel_shape: tuple[int, int, int], padded_shape: tuple[int, int, int]) -> int:
    source_nodes = int(np.prod(extent, dtype=object))
    kernel_nodes = int(np.prod(kernel_shape, dtype=object))
    padded_nodes = int(np.prod(padded_shape, dtype=object))
    complex_nodes = int(padded_shape[0] * padded_shape[1] * (padded_shape[2] // 2 + 1))
    # Source brick, dense kernel, inverse output, one complex source spectrum,
    # one complex kernel spectrum, and conservative allocator overhead.
    return int(8 * (source_nodes + kernel_nodes + padded_nodes) + 16 * (2 * complex_nodes) + 16 * padded_nodes)


def _direct_transient_bytes(pair_chunk_size: int) -> int:
    # Target coordinates, flat indices, lookup positions, contributions, and
    # boolean/index temporaries. HARDEN4 may evaluate disjoint source-row slices
    # of one *existing* pair chunk concurrently, but the aggregate pair count
    # remains bounded by pair_chunk_size. A small shared mapped-index buffer is
    # retained until canonical grouped reduction. 112 bytes/pair keeps the
    # worker-parallel path inside the same one-chunk resource contract without
    # multiplying transient memory by the worker count.
    return int(pair_chunk_size * 112)


def _choose_executor(
    *, source_count: int, direct_pairs: int, padded_nodes: int,
    options: DensityHybridExecutorOptions, fft_feasible: bool,
) -> tuple[TileExecutor, float, float]:
    direct_seconds = direct_pairs * options.direct_pair_seconds
    fft_work = padded_nodes * max(1.0, math.log2(max(2, padded_nodes)))
    fft_seconds = options.fft_fixed_seconds + fft_work * options.fft_work_seconds
    if options.executor_mode == "direct":
        return "direct", direct_seconds, fft_seconds
    if options.executor_mode == "fft":
        if not fft_feasible:
            raise GraphComplexityError("Forced FFT tile exceeds the declared FFT limits.")
        return "fft", direct_seconds, fft_seconds
    if source_count >= options.min_fft_source_nodes and fft_feasible and fft_seconds < direct_seconds:
        return "fft", direct_seconds, fft_seconds
    return "direct", direct_seconds, fft_seconds


def plan_hybrid_tiled_realization(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
    *,
    options: DensityHybridExecutorOptions | None = None,
    limits: DensityHybridRealizationLimits | None = None,
) -> DensityHybridRealizationPlan:
    """Build an identity-bound, byte-bounded mixed direct/FFT execution plan."""

    _validate_inputs(source_field, stencil, routing, atlas)
    resolved_options = DensityHybridExecutorOptions() if options is None else options
    resolved_limits = DensityHybridRealizationLimits() if limits is None else limits
    if not isinstance(resolved_options, DensityHybridExecutorOptions):
        raise TypeError("options must be DensityHybridExecutorOptions.")
    if not isinstance(resolved_limits, DensityHybridRealizationLimits):
        raise TypeError("limits must be DensityHybridRealizationLimits.")
    if atlas.target_support_node_count > resolved_limits.max_target_nodes:
        raise GraphComplexityError("Hybrid realization exceeds max_target_nodes.")

    coordinates, _ = _source_coordinate_table(source_field)
    logical = np.asarray(source_field.logical_grid_shape, dtype=np.int64)
    tile_shape = np.asarray(resolved_options.compute_tile_shape, dtype=np.int64)
    tile_grid = tuple(int((logical[axis] + tile_shape[axis] - 1) // tile_shape[axis]) for axis in range(3))
    tile_coordinates = np.floor_divide(coordinates, tile_shape[None, :])
    tile_flat = np.ravel_multi_index((tile_coordinates[:, 0], tile_coordinates[:, 1], tile_coordinates[:, 2]), tile_grid, order="C")
    order = np.argsort(tile_flat, kind="stable")
    sorted_tile_flat = tile_flat[order]
    unique, starts, counts = np.unique(sorted_tile_flat, return_index=True, return_counts=True)
    if unique.size > resolved_limits.max_compute_tiles:
        raise GraphComplexityError("Hybrid realization exceeds max_compute_tiles.")

    kernel, kernel_min, kernel_shape = _kernel_dense(stencil, routing)
    tile_plans: list[DensityHybridTilePlan] = []
    direct_pairs_total = 0
    direct_tiles = 0
    fft_tiles = 0
    max_transient = 0
    padded_shape_counts: dict[tuple[int, int, int], int] = {}

    for flat_raw, start_raw, count_raw in zip(unique, starts, counts, strict=True):
        tile_index = tuple(int(item) for item in np.unravel_index(int(flat_raw), tile_grid, order="C"))
        origin_array = np.asarray(tile_index, dtype=np.int64) * tile_shape
        extent_array = np.minimum(tile_shape, logical - origin_array)
        extent = tuple(int(item) for item in extent_array)
        full_shape = tuple(int(extent[axis] + kernel_shape[axis] - 1) for axis in range(3))
        padded_shape = tuple(int(next_fast_len(item)) for item in full_shape)
        padded_nodes = int(np.prod(padded_shape, dtype=object))
        source_count = int(count_raw)
        direct_pairs = source_count * stencil.stencil_offset_count
        fft_feasible = padded_nodes <= resolved_limits.max_fft_padded_nodes_per_tile
        executor, direct_seconds, fft_seconds = _choose_executor(
            source_count=source_count,
            direct_pairs=direct_pairs,
            padded_nodes=padded_nodes,
            options=resolved_options,
            fft_feasible=fft_feasible,
        )
        if executor == "direct":
            direct_pairs_total += direct_pairs
            direct_tiles += 1
            # A small direct tile never allocates a full configured chunk.
            # Bound transient pair storage by the actual tile work.
            transient = _direct_transient_bytes(
                min(resolved_options.pair_chunk_size, max(1, direct_pairs))
            )
        else:
            fft_tiles += 1
            transient = _fft_transient_bytes(extent, kernel_shape, padded_shape)
            padded_shape_counts[padded_shape] = padded_shape_counts.get(padded_shape, 0) + 1
        max_transient = max(max_transient, transient)
        tile_plans.append(
            DensityHybridTilePlan(
                tile_index=tile_index,
                origin=tuple(int(item) for item in origin_array),
                extent=extent,
                source_start=int(start_raw),
                source_stop=int(start_raw + count_raw),
                source_node_count=source_count,
                source_fill_fraction=float(source_count / np.prod(extent, dtype=object)),
                executor=executor,
                direct_pair_count=direct_pairs,
                full_convolution_shape=full_shape,
                fft_padded_shape=padded_shape,
                fft_padded_node_count=padded_nodes,
                direct_cost_estimate_seconds=direct_seconds,
                fft_cost_estimate_seconds=fft_seconds,
                transient_bytes_estimate=transient,
                cache_kernel_spectrum=False,
            )
        )

    if direct_pairs_total > resolved_limits.max_direct_pairs:
        raise GraphComplexityError("Hybrid direct tiles exceed max_direct_pairs.")
    if max_transient > resolved_limits.max_transient_bytes:
        raise GraphComplexityError("A hybrid tile exceeds max_transient_bytes.")

    # Cache the most frequently reused FFT kernel spectra first under the byte cap.
    cache_shapes: set[tuple[int, int, int]] = set()
    cache_bytes = 0
    if resolved_options.cache_kernel_spectra:
        ranked = sorted(padded_shape_counts.items(), key=lambda item: (-item[1], item[0]))
        for shape, _frequency in ranked:
            complex_nodes = int(shape[0] * shape[1] * (shape[2] // 2 + 1))
            current = complex_nodes * np.dtype(np.complex128).itemsize
            if cache_bytes + current <= resolved_limits.max_kernel_cache_bytes:
                cache_shapes.add(shape)
                cache_bytes += current
    tile_plans = [
        DensityHybridTilePlan(**{
            **tile.to_json_dict(),
            "cache_kernel_spectrum": tile.executor == "fft" and tile.fft_padded_shape in cache_shapes,
        })
        for tile in tile_plans
    ]

    # Realization retains packed target flats, sorted target flats, and the
    # sorted-to-packed permutation.  Atlas block offsets are counted as well.
    lookup_bytes = int(
        atlas.target_support_node_count * 3 * np.dtype(np.int64).itemsize
        + (atlas.target_block_count + 1) * np.dtype(np.int64).itemsize
    )
    if lookup_bytes > resolved_limits.max_lookup_bytes:
        raise GraphComplexityError("Hybrid target lookup exceeds max_lookup_bytes.")
    packed_bytes = _packed_field_bytes_upper(atlas)
    if packed_bytes > resolved_limits.max_retained_bytes:
        raise GraphComplexityError("Hybrid packed output exceeds max_retained_bytes.")
    source_coordinate_bytes = int(coordinates.nbytes + order.nbytes)
    predicted_peak = int(packed_bytes + lookup_bytes + source_coordinate_bytes + cache_bytes + max_transient)
    if predicted_peak > resolved_limits.max_total_peak_bytes:
        raise GraphComplexityError(
            "Hybrid predicted peak exceeds max_total_peak_bytes: "
            f"{predicted_peak} > {resolved_limits.max_total_peak_bytes}."
        )
    estimated_wall_seconds = float(sum(
        tile.direct_cost_estimate_seconds if tile.executor == "direct"
        else tile.fft_cost_estimate_seconds
        for tile in tile_plans
    ))
    return DensityHybridRealizationPlan(
        source_field_identity=source_field.content_identity,
        routing_identity=routing.cache_identity,
        atlas_identity=atlas.content_identity,
        stencil_identity=stencil_content_identity(stencil),
        logical_grid_shape=source_field.logical_grid_shape,
        compute_tile_shape=resolved_options.compute_tile_shape,
        kernel_min_offset=kernel_min,
        kernel_shape=kernel_shape,
        source_node_count=source_field.occupied_node_count,
        target_support_node_count=atlas.target_support_node_count,
        compute_tile_count=len(tile_plans),
        direct_tile_count=direct_tiles,
        fft_tile_count=fft_tiles,
        exact_contribution_count=source_field.occupied_node_count * stencil.stencil_offset_count,
        direct_pair_count=direct_pairs_total,
        target_lookup_bytes=lookup_bytes,
        kernel_dense_bytes=int(kernel.nbytes),
        kernel_spectrum_cache_bytes=cache_bytes,
        packed_field_bytes_upper=packed_bytes,
        predicted_peak_bytes=predicted_peak,
        tile_plans=tuple(tile_plans),
        options=resolved_options,
        limits=resolved_limits,
        metadata={
            "selector": "calibrated_direct_fft_cost_v1",
            "tile_grid_shape": list(tile_grid),
            "source_coordinate_bytes": source_coordinate_bytes,
            "estimated_wall_seconds": estimated_wall_seconds,
            "max_wall_time_seconds": resolved_limits.max_wall_time_seconds,
            "wall_time_admission_enforced": False,
            "wall_time_budget_exceeded": bool(
                estimated_wall_seconds > resolved_limits.max_wall_time_seconds
            ),
            "scipy_version": scipy_version,
        },
    )


def _validate_approved_plan(
    plan: DensityHybridRealizationPlan,
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
) -> None:
    if not isinstance(plan, DensityHybridRealizationPlan):
        raise TypeError("approved_plan must be DensityHybridRealizationPlan.")
    expected = (
        source_field.content_identity,
        routing.cache_identity,
        atlas.content_identity,
        stencil_content_identity(stencil),
    )
    actual = (
        plan.source_field_identity,
        plan.routing_identity,
        plan.atlas_identity,
        plan.stencil_identity,
    )
    if actual != expected:
        raise GraphAdapterError("approved_plan identities do not match the current inputs.")


def _map_flats_to_packed(
    flat: IntArray,
    sorted_target_flats: IntArray,
    sorted_target_positions: IntArray,
) -> tuple[IntArray, NDArray[np.bool_]]:
    positions = np.searchsorted(sorted_target_flats, flat)
    clipped = np.minimum(positions, max(0, sorted_target_flats.size - 1))
    valid = (positions < sorted_target_flats.size) & (sorted_target_flats[clipped] == flat)
    mapped = np.empty(flat.shape, dtype=np.int64)
    if np.any(valid):
        mapped[valid] = sorted_target_positions[positions[valid]]
    return mapped, valid


def _apply_total_mass_correction(values: FloatArray, *, total_measure: float) -> int:
    index = int(np.argmax(values))
    residual = float(total_measure) - float(np.sum(values, dtype=np.float64))
    values[index] += residual
    if values[index] <= 0.0 or not np.isfinite(values[index]):
        raise GraphAdapterError("Hybrid final mass correction produced a nonpositive node.")
    return index


def _recompute_nonpositive_nodes(
    node_masses: FloatArray,
    problematic: IntArray,
    packed_target_flats: IntArray,
    source_coordinates: IntArray,
    source_values: FloatArray,
    signed_offsets: IntArray,
    stencil_weights: FloatArray,
    logical_shape: tuple[int, int, int],
) -> int:
    if problematic.size == 0:
        return 0
    source_flats = np.ravel_multi_index(
        (source_coordinates[:, 0], source_coordinates[:, 1], source_coordinates[:, 2]),
        logical_shape,
        order="C",
    ).astype(np.int64, copy=False)
    source_order = np.argsort(source_flats, kind="stable")
    source_flats = source_flats[source_order]
    ordered_values = source_values[source_order]
    logical = np.asarray(logical_shape, dtype=np.int64)
    target_coords = np.column_stack(np.unravel_index(packed_target_flats[problematic], logical_shape, order="C")).astype(np.int64, copy=False)
    for packed_position, target in zip(problematic, target_coords, strict=True):
        source_needed = np.mod(target[None, :] - signed_offsets, logical[None, :])
        needed_flat = np.ravel_multi_index((source_needed[:, 0], source_needed[:, 1], source_needed[:, 2]), logical_shape, order="C")
        found = np.searchsorted(source_flats, needed_flat)
        clipped = np.minimum(found, max(0, source_flats.size - 1))
        valid = (found < source_flats.size) & (source_flats[clipped] == needed_flat)
        mass = float(np.sum(stencil_weights[valid] * ordered_values[found[valid]], dtype=np.float64))
        if mass <= 0.0 or not np.isfinite(mass):
            raise GraphAdapterError("Exact repair could not recover a positive supported node.")
        node_masses[int(packed_position)] = mass
    return int(problematic.size)


def _accumulate_grouped(
    accumulator: FloatArray, indices: IntArray, values: FloatArray
) -> None:
    """Add values by destination with a stable grouped reduction.

    The helper avoids repeated ``np.add.at`` scatter into the complete packed
    field.  Stable destination sorting preserves contribution order within each
    destination; only distinct destinations are updated after reduction.
    """

    mapped = np.asarray(indices, dtype=np.int64)
    contributions = np.asarray(values, dtype=np.float64)
    if mapped.size == 0:
        return
    if mapped.shape != contributions.shape:
        raise GraphAdapterError("Grouped density accumulation arrays are misaligned.")
    order = np.argsort(mapped, kind="stable")
    sorted_indices = mapped[order]
    sorted_values = contributions[order]
    starts = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.flatnonzero(sorted_indices[1:] != sorted_indices[:-1]).astype(np.int64) + 1,
        )
    )
    reduced = np.add.reduceat(sorted_values, starts)
    accumulator[sorted_indices[starts]] += reduced


def realize_density_hybrid_tiled(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
    *,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    options: DensityHybridExecutorOptions | None = None,
    limits: DensityHybridRealizationLimits | None = None,
    approved_plan: DensityHybridRealizationPlan | None = None,
    selected_atom_indices: tuple[int, ...] = (),
    sample_positions: FloatArray | None = None,
    metadata: Mapping[str, Any] | None = None,
    production_backend: bool = False,
    progress: ProgressPortLike | None = None,
) -> PeriodicPackedBlockScalarField3D:
    """Realize one exact-support field through mixed bounded direct/FFT tiles."""

    _validate_inputs(source_field, stencil, routing, atlas)
    key = _nonempty_string(field_key, name="field_key")
    resolved_label = _nonempty_string(label, name="label")
    units = _nonempty_string(physical_units, name="physical_units")
    metric = _nonempty_string(broadening_metric, name="broadening_metric")
    reporter = ProgressEmitter(
        resolve_progress_port(progress), source="plotting.density_tiled_fft"
    )
    if approved_plan is None:
        plan = plan_hybrid_tiled_realization(source_field, stencil, routing, atlas, options=options, limits=limits)
    else:
        _validate_approved_plan(approved_plan, source_field, stencil, routing, atlas)
        if options is not None and options != approved_plan.options:
            raise GraphAdapterError("Explicit options disagree with approved_plan.")
        if limits is not None and limits != approved_plan.limits:
            raise GraphAdapterError("Explicit limits disagree with approved_plan.")
        plan = approved_plan

    reporter.started(
        "hybrid_sparse_realization",
        f"{key}: realizing {plan.direct_tile_count} direct tile(s) and "
        f"{plan.fft_tile_count} FFT tile(s); direct sparse work is CPU execution",
        metadata={
            "field_key": key,
            "direct_tile_count": int(plan.direct_tile_count),
            "fft_tile_count": int(plan.fft_tile_count),
            "direct_pair_count": int(plan.direct_pair_count),
        },
    )
    source_coordinates, source_values = _source_coordinate_table(source_field)
    fft_worker_source = str(plan.options.metadata.get("fft_worker_source", "explicit"))
    live_lease = current_density_worker_lease()
    maximum_direct_workers = (
        1
        if live_lease is None
        else max(1, int(live_lease.resources.preferred_workers))
    )
    direct_executor: ThreadPoolExecutor | None = None

    def live_fft_workers() -> int:
        live = autotuned_fft_worker_count(current_density_worker_count(default=plan.options.fft_workers))
        if fft_worker_source == "runtime_thread_budget":
            return max(1, live)
        return max(1, min(int(plan.options.fft_workers), live))
    tile_shape = np.asarray(plan.compute_tile_shape, dtype=np.int64)
    logical = np.asarray(source_field.logical_grid_shape, dtype=np.int64)
    tile_grid = tuple(int((logical[axis] + tile_shape[axis] - 1) // tile_shape[axis]) for axis in range(3))
    tile_coordinates = np.floor_divide(source_coordinates, tile_shape[None, :])
    tile_flat = np.ravel_multi_index((tile_coordinates[:, 0], tile_coordinates[:, 1], tile_coordinates[:, 2]), tile_grid, order="C")
    source_order = np.argsort(tile_flat, kind="stable")
    ordered_coordinates = source_coordinates[source_order]
    ordered_values = source_values[source_order]

    (
        sorted_target_flats,
        sorted_target_positions,
        block_value_offsets,
        packed_target_flats,
    ) = _target_lookup(atlas)
    node_masses = np.zeros(atlas.target_support_node_count, dtype=np.float64)
    kernel, kernel_min, _kernel_shape = _kernel_dense(stencil, routing)
    signed = routing.signed_offsets.astype(np.int64, copy=False)
    weights = stencil.active_weights

    kernel_spectra: dict[tuple[int, int, int], NDArray[np.complex128]] = {}
    direct_pair_count = 0
    direct_chunk_count = 0
    parallel_direct_chunk_count = 0
    maximum_direct_workers_used = 1
    fft_tile_count = 0
    gpu_fft_tile_count = 0
    cpu_fft_tile_count = 0
    fft_kernel_transform_count = 0
    ignored_fft_output_nodes = 0
    peak_pair_count = 0
    peak_fft_padded_nodes = 0
    progress_started = time.perf_counter()
    last_progress_emit = progress_started

    def emit_direct_progress(*, force: bool = False) -> None:
        nonlocal last_progress_emit
        if plan.direct_pair_count <= 0:
            return
        now = time.perf_counter()
        if not force and now - last_progress_emit < 2.0:
            return
        last_progress_emit = now
        reporter.update(
            "hybrid_direct_realization",
            f"{key}: CPU direct sparse convolution; "
            f"workers={current_density_worker_count(default=1)}",
            current=min(int(direct_pair_count), int(plan.direct_pair_count)),
            total=int(plan.direct_pair_count),
            unit="pairs",
            metadata={
                "field_key": key,
                "workers": int(current_density_worker_count(default=1)),
                "gpu_expected_for_direct_tiles": False,
            },
        )

    def emit_fft_progress(*, force: bool = False) -> None:
        nonlocal last_progress_emit
        if plan.fft_tile_count <= 0:
            return
        now = time.perf_counter()
        if not force and now - last_progress_emit < 2.0:
            return
        last_progress_emit = now
        reporter.update(
            "hybrid_fft_realization",
            f"{key}: FFT tile convolution; live_workers={live_fft_workers()}",
            current=min(int(fft_tile_count), int(plan.fft_tile_count)),
            total=int(plan.fft_tile_count),
            unit="tiles",
            metadata={
                "field_key": key,
                "workers": int(live_fft_workers()),
            },
        )

    try:
        for tile in plan.tile_plans:
            coords = ordered_coordinates[tile.source_start:tile.source_stop]
            values = ordered_values[tile.source_start:tile.source_stop]
            if coords.shape[0] != tile.source_node_count:
                raise GraphAdapterError("Source tile partition changed after plan approval.")
            if np.any(np.floor_divide(coords, tile_shape[None, :]) != np.asarray(tile.tile_index, dtype=np.int64)[None, :]):
                raise GraphAdapterError("Approved tile range contains source nodes owned by another tile.")
            expected_origin = np.asarray(tile.tile_index, dtype=np.int64) * tile_shape
            expected_extent = np.minimum(tile_shape, logical - expected_origin)
            if not np.array_equal(expected_origin, np.asarray(tile.origin, dtype=np.int64)) or not np.array_equal(expected_extent, np.asarray(tile.extent, dtype=np.int64)):
                raise GraphAdapterError("Approved tile geometry disagrees with the logical grid.")
            if tile.executor == "direct":
                stencil_count = int(signed.shape[0])
                sources_per_chunk = max(1, plan.options.pair_chunk_size // stencil_count)
                for start in range(0, tile.source_node_count, sources_per_chunk):
                    stop = min(tile.source_node_count, start + sources_per_chunk)
                    current_coords = coords[start:stop]
                    current_values = values[start:stop]
                    pair_count = int(current_coords.shape[0]) * stencil_count
                    if pair_count > plan.options.pair_chunk_size:
                        # If the stencil itself exceeds the pair budget, split offsets.
                        offsets_per_chunk = max(1, plan.options.pair_chunk_size // int(current_coords.shape[0]))
                        offset_slices = range(0, stencil_count, offsets_per_chunk)
                    else:
                        offsets_per_chunk = stencil_count
                        offset_slices = (0,)
                    for offset_start in offset_slices:
                        offset_stop = min(stencil_count, int(offset_start) + offsets_per_chunk)
                        chosen_offsets = signed[int(offset_start):offset_stop]
                        chosen_weights = weights[int(offset_start):offset_stop]
                        offset_count = int(chosen_offsets.shape[0])
                        current_pairs = int(current_coords.shape[0]) * offset_count
                        direct_workers = max(
                            1,
                            min(
                                current_density_worker_count(default=1),
                                int(current_coords.shape[0]),
                            ),
                        )
                        maximum_direct_workers_used = max(
                            maximum_direct_workers_used, direct_workers
                        )
                        if direct_workers <= 1:
                            targets = np.mod(
                                current_coords[:, None, :] + chosen_offsets[None, :, :],
                                logical[None, None, :],
                            )
                            flat = (
                                (targets[..., 0] * logical[1] + targets[..., 1])
                                * logical[2]
                                + targets[..., 2]
                            ).reshape(-1)
                            mapped, valid = _map_flats_to_packed(
                                flat, sorted_target_flats, sorted_target_positions
                            )
                            if not np.all(valid):
                                raise GraphAdapterError(
                                    "Direct tile generated a node outside the exact support atlas."
                                )
                        else:
                            # Parallelize the geometry/lookup portion *inside* the
                            # already-approved pair chunk.  The aggregate pair count
                            # and hence the scientific/resource authority do not
                            # change with worker count.  Each worker owns a contiguous
                            # source-row slice and writes its mapped destinations into
                            # the matching canonical flattened range.  The final
                            # grouped floating-point reduction is still performed once
                            # in the exact serial pair order, preserving bitwise output.
                            if direct_executor is None:
                                direct_executor = ThreadPoolExecutor(
                                    max_workers=maximum_direct_workers,
                                    thread_name_prefix="mdstats-density-hybrid-direct",
                                )
                            mapped = np.empty(current_pairs, dtype=np.int64)
                            row_boundaries = np.linspace(
                                0,
                                int(current_coords.shape[0]),
                                direct_workers + 1,
                                dtype=np.int64,
                            )

                            def resolve_row_slice(worker_index: int) -> None:
                                row_start = int(row_boundaries[worker_index])
                                row_stop = int(row_boundaries[worker_index + 1])
                                if row_stop <= row_start:
                                    return
                                local_targets = np.mod(
                                    current_coords[row_start:row_stop, None, :]
                                    + chosen_offsets[None, :, :],
                                    logical[None, None, :],
                                )
                                local_flat = (
                                    (local_targets[..., 0] * logical[1] + local_targets[..., 1])
                                    * logical[2]
                                    + local_targets[..., 2]
                                ).reshape(-1)
                                local_mapped, local_valid = _map_flats_to_packed(
                                    local_flat,
                                    sorted_target_flats,
                                    sorted_target_positions,
                                )
                                if not np.all(local_valid):
                                    raise GraphAdapterError(
                                        "Direct tile generated a node outside the exact support atlas."
                                    )
                                pair_start = row_start * offset_count
                                pair_stop = row_stop * offset_count
                                mapped[pair_start:pair_stop] = local_mapped

                            tuple(
                                direct_executor.map(resolve_row_slice, range(direct_workers))
                            )
                            parallel_direct_chunk_count += 1
                        contributions = (
                            current_values[:, None] * chosen_weights[None, :]
                        ).reshape(-1)
                        _accumulate_grouped(node_masses, mapped, contributions)
                        direct_pair_count += current_pairs
                        peak_pair_count = max(peak_pair_count, current_pairs)
                        direct_chunk_count += 1
                        emit_direct_progress()
            else:
                extent = np.asarray(tile.extent, dtype=np.int64)
                origin = np.asarray(tile.origin, dtype=np.int64)
                local = coords - origin[None, :]
                source_dense = np.zeros(tile.extent, dtype=np.float64)
                source_dense[local[:, 0], local[:, 1], local[:, 2]] = values
                padded_shape = tile.fft_padded_shape
                fft_workers = live_fft_workers()
                # Emit before the potentially monolithic FFT call so a large first
                # tile cannot look like another scheduler stall.  Subsequent
                # pre-tile notices remain throttled by the common progress clock.
                emit_fft_progress(force=fft_tile_count == 0)
                inverse = try_gpu_linear_fft_convolution(
                    source_dense,
                    kernel,
                    padded_shape,
                    cpu_estimate_seconds=float(tile.fft_cost_estimate_seconds),
                    kernel_name="hybrid_tiled_fft",
                )
                if inverse is not None:
                    gpu_fft_tile_count += 1
                    # The GPU backend currently transforms the kernel per admitted
                    # tile; this remains execution-only evidence.
                    fft_kernel_transform_count += 1
                else:
                    cpu_fft_tile_count += 1
                    spectrum = rfftn(source_dense, padded_shape, workers=fft_workers)
                    if tile.cache_kernel_spectrum and padded_shape in kernel_spectra:
                        kernel_spectrum = kernel_spectra[padded_shape]
                    else:
                        kernel_spectrum = rfftn(kernel, padded_shape, workers=fft_workers)
                        fft_kernel_transform_count += 1
                        if tile.cache_kernel_spectrum:
                            kernel_spectra[padded_shape] = kernel_spectrum
                    spectrum *= kernel_spectrum
                    inverse = irfftn(spectrum, padded_shape, workers=fft_workers)
                full = inverse[
                    : tile.full_convolution_shape[0],
                    : tile.full_convolution_shape[1],
                    : tile.full_convolution_shape[2],
                ]
                axes = [
                    (origin[axis] + kernel_min[axis] + np.arange(tile.full_convolution_shape[axis], dtype=np.int64)) % logical[axis]
                    for axis in range(3)
                ]
                flat = (
                    (axes[0][:, None, None] * logical[1] + axes[1][None, :, None]) * logical[2]
                    + axes[2][None, None, :]
                ).reshape(-1)
                mapped, valid = _map_flats_to_packed(flat, sorted_target_flats, sorted_target_positions)
                values_flat = full.reshape(-1)
                if np.any(valid):
                    _accumulate_grouped(node_masses, mapped[valid], values_flat[valid])
                ignored_fft_output_nodes += int(valid.size - np.count_nonzero(valid))
                fft_tile_count += 1
                peak_fft_padded_nodes = max(peak_fft_padded_nodes, tile.fft_padded_node_count)
                emit_fft_progress()

    finally:
        if direct_executor is not None:
            direct_executor.shutdown(wait=True)

    if direct_pair_count != plan.direct_pair_count:
        raise GraphAdapterError("Realized direct-pair count disagrees with approved_plan.")
    if fft_tile_count != plan.fft_tile_count:
        raise GraphAdapterError("Realized FFT-tile count disagrees with approved_plan.")
    if plan.direct_pair_count > 0:
        emit_direct_progress(force=True)
    if plan.fft_tile_count > 0:
        emit_fft_progress(force=True)
    reporter.completed(
        "hybrid_sparse_realization",
        f"{key}: completed sparse realization in "
        f"{time.perf_counter() - progress_started:.1f} s; "
        f"max_direct_workers={maximum_direct_workers_used}, "
        f"gpu_fft_tiles={gpu_fft_tile_count}",
        metadata={
            "field_key": key,
            "maximum_direct_workers_used": int(maximum_direct_workers_used),
            "parallel_direct_chunk_count": int(parallel_direct_chunk_count),
            "gpu_fft_tile_count": int(gpu_fft_tile_count),
        },
    )

    problematic = np.flatnonzero((node_masses <= 0.0) | ~np.isfinite(node_masses)).astype(np.int64, copy=False)
    repaired = _recompute_nonpositive_nodes(
        node_masses,
        problematic,
        packed_target_flats,
        source_coordinates,
        source_values,
        signed,
        weights,
        source_field.logical_grid_shape,
    )
    if np.any(node_masses <= 0.0) or np.any(~np.isfinite(node_masses)):
        raise GraphAdapterError("Hybrid realization produced a nonpositive supported node.")

    raw_measure = float(np.sum(node_masses, dtype=np.float64))
    if not np.isfinite(raw_measure) or raw_measure <= 0.0:
        raise GraphAdapterError("Hybrid realization produced zero measure.")
    normalization_factor = source_field.total_measure / raw_measure
    node_masses *= normalization_factor
    correction_index = _apply_total_mass_correction(node_masses, total_measure=source_field.total_measure)
    voxel_volume = abs(float(np.linalg.det(stencil.display_cell))) / float(np.prod(source_field.logical_grid_shape, dtype=object))
    node_masses /= voxel_volume

    minima = np.empty(atlas.target_block_count, dtype=np.float64)
    maxima = np.empty(atlas.target_block_count, dtype=np.float64)
    for row, target_index in enumerate(atlas.active_target_block_indices):
        start, stop = int(block_value_offsets[row]), int(block_value_offsets[row + 1])
        current = node_masses[start:stop]
        maxima[row] = float(np.max(current))
        extent = routing.extent_for_block(tuple(int(value) for value in target_index))
        valid_count = int(np.prod(extent, dtype=object))
        support_count = bitset_popcount(atlas.target_support_bitsets[row])
        minima[row] = float(np.min(current)) if support_count == valid_count else 0.0

    retained_bytes = int(
        atlas.active_target_block_indices.nbytes + atlas.target_support_bitsets.nbytes
        + block_value_offsets.nbytes + node_masses.nbytes + minima.nbytes + maxima.nbytes
    )
    if retained_bytes > plan.limits.max_retained_bytes:
        raise GraphComplexityError("Hybrid packed field exceeds max_retained_bytes.")
    final_measure = float(np.sum(node_masses, dtype=np.float64)) * voxel_volume
    return PeriodicPackedBlockScalarField3D(
        field_key=key,
        label=resolved_label,
        physical_units=units,
        logical_grid_shape=source_field.logical_grid_shape,
        storage_block_shape=source_field.storage_block_shape,
        active_block_indices=atlas.active_target_block_indices,
        occupancy_bitsets=atlas.target_support_bitsets,
        block_value_offsets=block_value_offsets,
        packed_values=node_masses,
        block_min_values=minima,
        block_max_values=maxima,
        display_cell=stencil.display_cell,
        total_measure=source_field.total_measure,
        gaussian_bandwidth=stencil.gaussian_bandwidth,
        broadening_metric=metric,
        source_provenance=source_field.source_provenance,
        selected_atom_indices=selected_atom_indices,
        sample_positions=sample_positions,
        metadata={
            **source_field.metadata.to_json_dict(),
            **({} if metadata is None else dict(metadata)),
            "reference_path": "ld8_s3_hybrid_tiled_v1",
            "production_backend": bool(production_backend),
            "source_field_identity": source_field.content_identity,
            "routing_identity": routing.cache_identity,
            "atlas_identity": atlas.content_identity,
            "stencil_identity": stencil_content_identity(stencil),
            "hybrid_realization_plan": plan.to_json_dict(),
            "direct_tile_count": plan.direct_tile_count,
            "fft_tile_count": plan.fft_tile_count,
            "direct_pair_count": direct_pair_count,
            "direct_chunk_count": direct_chunk_count,
            "parallel_direct_chunk_count": parallel_direct_chunk_count,
            "maximum_direct_workers_used": maximum_direct_workers_used,
            "direct_parallelism_policy": "canonical_pair_chunk_row_slices_v1",
            "direct_parallelism_preserves_pair_chunk_bound": True,
            "direct_parallelism_preserves_canonical_reduction_order": True,
            "fft_kernel_transform_count": fft_kernel_transform_count,
            "gpu_fft_tile_count": gpu_fft_tile_count,
            "cpu_fft_tile_count": cpu_fft_tile_count,
            "gpu_execution_is_scientifically_neutral": True,
            "cached_fft_kernel_shape_count": len(kernel_spectra),
            "ignored_zero_box_fft_output_nodes": ignored_fft_output_nodes,
            "fft_nonpositive_node_repairs": repaired,
            "peak_direct_chunk_pair_count": peak_pair_count,
            "peak_fft_padded_node_count": peak_fft_padded_nodes,
            "fft_library": (
                "torch.cuda+scipy.fft" if gpu_fft_tile_count else "scipy.fft"
            ),
            "scipy_version": scipy_version,
            "fft_workers": plan.options.fft_workers,
            "fft_worker_execution_policy": (
                "scheduler_dynamic"
                if fft_worker_source == "runtime_thread_budget"
                else "explicit_cap"
            ),
            "raw_measure_before_final_normalization": raw_measure,
            "final_normalization_factor": float(normalization_factor),
            "mass_correction_index": correction_index,
            "final_measure": final_measure,
            "packed_field_bytes": retained_bytes,
            "complete_fine_pair_array_allocated": False,
            "global_dense_logical_grid_allocated": False,
            "global_target_coordinate_array_allocated": False,
        },
    )
