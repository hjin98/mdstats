"""Periodic framework vertex-occupancy and edge-length density fields.

The voxel assignment and periodic Gaussian convolution reuse the cloud-in-cell
particle-mesh construction attributed in :mod:`mdstats.plotting.atomic_density`
to Hockney and Eastwood.  The framework-specific scientific measures are:

* a vertex occupancy measure with unit mass per projected framework vertex; and
* an edge arc-length measure with line element ``ds`` along every retained
  projected edge or retained atom-resolved path segment.

The channels are intentionally separate because their physical dimensions are
``angstrom^-3`` and ``angstrom^-2`` respectively.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Literal, Mapping

import numpy as np
from numpy.typing import NDArray

from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port

from .atomic_density import (
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    PeriodicScalarField3D,
    _deposit_cic,
    _prepare_sparse_field_for_options,
    _planned_backend_from_metadata,
    _select_atomic_auto_backend,
    _warn_if_underresolved_density_grid,
    resolve_density_numerics,
)
from .density_contracts import (
    AUTO_BACKEND,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    EFFECTIVE_CIC_STENCIL_BROADENING,
    LEGACY_SPECTRAL_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    DensityKernelOptions,
    DensityOptimizationOptions,
    DensityResolutionOptions,
    DensitySourceProvenance,
    DensityStorageOptions,
    FrozenJSONMapping,
    PeriodicWeightedSamples3D,
    ScalarField3D,
    freeze_json_mapping,
    is_scalar_field3d,
    validate_density_implementation_selection,
)
from .density_block_sparse import pack_sparse_reference_blocks
from .density_tiled_fft import DensityHybridRealizationPlan
from .density_broadening import effective_artificial_broadening
from .density_visual_policy import prepare_density_visual_grid_adaptation
from .density_kernel import smooth_periodic_node_masses
from .graph_errors import (
    GraphAdapterError,
    GraphComplexityError,
    GraphStyleError,
)
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

FRAMEWORK_DENSITY_SCHEMA = "mdstats.framework-density-fields.v2"


@dataclass(frozen=True, slots=True)
class FrameworkEdgeQuadratureResolution:
    """Resolved midpoint-quadrature interval for framework edge density."""

    mode: Literal["auto", "explicit"]
    nominal_spacing: float
    realized_spacing: float
    axis_min_spacing: float
    gaussian_half_spacing: float | None
    policy_spacing: float
    refinement_levels: int
    explicit_underresolved: bool

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "edge_sample_spacing_mode": self.mode,
            "edge_sample_spacing_nominal": self.nominal_spacing,
            "edge_sample_spacing_realized": self.realized_spacing,
            "edge_sampling_axis_min_spacing": self.axis_min_spacing,
            "edge_sampling_gaussian_half_spacing": self.gaussian_half_spacing,
            "edge_sampling_policy_spacing": self.policy_spacing,
            "edge_quadrature_refinement_levels": self.refinement_levels,
            "edge_sample_spacing_underresolved": self.explicit_underresolved,
        }


@dataclass(frozen=True, slots=True)
class FrameworkDensity3DRenderOptions(AtomicDensity3DRenderOptions):
    """Styling for framework vertex and edge probability-mass clouds.

    Framework density defaults to explicit marching-cubes ``mesh`` shells for
    a continuous cloud appearance. ``voxel_cloud`` remains available as a
    browser-safe fallback.
    """

    render_mode: Literal["mesh", "voxel_cloud"] = "mesh"
    cloud_point_size: float = 2.8
    cloud_opacity: float = 0.28


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be nonnegative.")
    return result


@dataclass(frozen=True, slots=True)
class FrameworkDensityOptions:
    """Numerical policy for framework vertex and edge density measures.

    The default grid is resolved from ``grid_interval`` and the display-cell
    vector lengths. The Gaussian is derived from the longest realized grid
    interval and may be refined using the periodic standard deviations of the
    framework vertices. By default, the canonical periodized kernel and
    automatic dense-versus-local-sparse planner resolve this scientific
    resolution before choosing storage. Explicit shapes, bandwidths, operators,
    and backends remain authoritative.
    """

    grid_shape: tuple[int, int, int] | None = None
    grid_interval: float = 0.20
    gaussian_bandwidth: float | None = None
    gaussian_to_grid_ratio: float = 2.0
    adaptive_smearing: bool = True
    max_smearing_to_sample_sd_ratio: float = 0.50
    sample_sd_quantile: float = 0.10
    spread_sample_size: int = 128
    spread_sample_seed: int = 0
    spread_sampling_strategy: Literal["all", "stratified_random"] = (
        "stratified_random"
    )
    spread_replicate_count: int = 4
    spread_max_replicate_count: int = 8
    spread_convergence_relative_tolerance: float = 0.01
    spread_basin_mode: Literal["auto", "global"] = "auto"
    include_vertex_density: bool = True
    include_edge_density: bool = True
    edge_source: Literal["projected", "atomic_paths"] = "projected"
    edge_sample_spacing: float = 0.20
    edge_sample_spacing_mode: Literal["auto", "explicit"] = "auto"
    edge_quadrature_refinement_levels: int = 2
    store_sample_positions: bool = False
    resolution_options: DensityResolutionOptions | None = None
    kernel_options: DensityKernelOptions = field(default_factory=DensityKernelOptions)
    storage_options: DensityStorageOptions = field(
        default_factory=DensityStorageOptions
    )
    optimization_options: DensityOptimizationOptions = field(
        default_factory=DensityOptimizationOptions
    )

    def __post_init__(self) -> None:
        resolution = self.resolution_options
        if resolution is not None:
            if not isinstance(resolution, DensityResolutionOptions):
                raise TypeError(
                    "resolution_options must be DensityResolutionOptions or None."
                )
            object.__setattr__(self, "grid_shape", resolution.grid_shape)
            object.__setattr__(self, "grid_interval", resolution.grid_interval)
            object.__setattr__(
                self, "gaussian_bandwidth", resolution.gaussian_bandwidth
            )
            object.__setattr__(
                self, "gaussian_to_grid_ratio", resolution.gaussian_to_grid_ratio
            )
            object.__setattr__(self, "adaptive_smearing", resolution.adaptive_smearing)
            object.__setattr__(
                self,
                "max_smearing_to_sample_sd_ratio",
                resolution.max_smearing_to_sample_sd_ratio,
            )
            object.__setattr__(
                self, "sample_sd_quantile", resolution.sample_sd_quantile
            )
            object.__setattr__(self, "spread_sample_size", resolution.spread_sample_size)
            object.__setattr__(self, "spread_sample_seed", resolution.spread_sample_seed)
            object.__setattr__(
                self,
                "spread_sampling_strategy",
                resolution.spread_sampling_strategy,
            )
            object.__setattr__(self, "spread_replicate_count", resolution.spread_replicate_count)
            object.__setattr__(self, "spread_max_replicate_count", resolution.spread_max_replicate_count)
            object.__setattr__(
                self,
                "spread_convergence_relative_tolerance",
                resolution.spread_convergence_relative_tolerance,
            )
            object.__setattr__(self, "spread_basin_mode", resolution.spread_basin_mode)
        shape = self.grid_shape
        if shape is not None:
            if len(shape) != 3:
                raise GraphStyleError(
                    "grid_shape must contain three integers or be None."
                )
            shape = tuple(_positive_int(v, name="grid_shape entry") for v in shape)
            if min(shape) < 4:
                raise GraphStyleError("Every grid_shape entry must be at least 4.")
        interval = float(self.grid_interval)
        if not np.isfinite(interval) or interval <= 0.0:
            raise GraphStyleError("grid_interval must be finite and positive.")
        bandwidth = self.gaussian_bandwidth
        if bandwidth is not None:
            bandwidth = float(bandwidth)
            if not np.isfinite(bandwidth) or bandwidth < 0.0:
                raise GraphStyleError(
                    "gaussian_bandwidth must be finite and nonnegative or None."
                )
        ratio = float(self.gaussian_to_grid_ratio)
        if not np.isfinite(ratio) or ratio <= 0.0:
            raise GraphStyleError("gaussian_to_grid_ratio must be finite and positive.")
        sd_ratio = float(self.max_smearing_to_sample_sd_ratio)
        if not np.isfinite(sd_ratio) or sd_ratio <= 0.0:
            raise GraphStyleError(
                "max_smearing_to_sample_sd_ratio must be finite and positive."
            )
        quantile = float(self.sample_sd_quantile)
        if not np.isfinite(quantile) or not 0.0 <= quantile <= 1.0:
            raise GraphStyleError("sample_sd_quantile must lie in [0, 1].")
        sample_size = _positive_int(self.spread_sample_size, name="spread_sample_size")
        if sample_size < 2:
            raise GraphStyleError("spread_sample_size must be at least 2.")
        if isinstance(self.spread_sample_seed, bool) or not isinstance(
            self.spread_sample_seed, (int, np.integer)
        ):
            raise GraphStyleError("spread_sample_seed must be an integer.")
        sample_seed = int(self.spread_sample_seed)
        if self.spread_sampling_strategy not in {"all", "stratified_random"}:
            raise GraphStyleError(
                "spread_sampling_strategy must be all or stratified_random."
            )
        replicate_count = _positive_int(self.spread_replicate_count, name="spread_replicate_count")
        max_replicates = _positive_int(self.spread_max_replicate_count, name="spread_max_replicate_count")
        if max_replicates < replicate_count:
            raise GraphStyleError(
                "spread_max_replicate_count cannot be smaller than spread_replicate_count."
            )
        convergence_tolerance = float(self.spread_convergence_relative_tolerance)
        if not np.isfinite(convergence_tolerance) or convergence_tolerance <= 0.0:
            raise GraphStyleError(
                "spread_convergence_relative_tolerance must be finite and positive."
            )
        if self.spread_basin_mode not in {"auto", "global"}:
            raise GraphStyleError("spread_basin_mode must be auto or global.")
        spacing = float(self.edge_sample_spacing)
        if not np.isfinite(spacing) or spacing <= 0.0:
            raise GraphStyleError("edge_sample_spacing must be finite and positive.")
        if self.edge_sample_spacing_mode not in {"auto", "explicit"}:
            raise GraphStyleError(
                "edge_sample_spacing_mode must be 'auto' or 'explicit'."
            )
        refinement_levels = _nonnegative_int(
            self.edge_quadrature_refinement_levels,
            name="edge_quadrature_refinement_levels",
        )
        if refinement_levels > 8:
            raise GraphStyleError(
                "edge_quadrature_refinement_levels must not exceed 8."
            )
        if not self.include_vertex_density and not self.include_edge_density:
            raise GraphStyleError(
                "At least one framework density channel must be enabled."
            )
        if self.edge_source not in {"projected", "atomic_paths"}:
            raise GraphStyleError("edge_source must be 'projected' or 'atomic_paths'.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "grid_interval", interval)
        object.__setattr__(self, "gaussian_bandwidth", bandwidth)
        object.__setattr__(self, "gaussian_to_grid_ratio", ratio)
        object.__setattr__(self, "adaptive_smearing", bool(self.adaptive_smearing))
        object.__setattr__(self, "max_smearing_to_sample_sd_ratio", sd_ratio)
        object.__setattr__(self, "sample_sd_quantile", quantile)
        object.__setattr__(self, "spread_sample_size", sample_size)
        object.__setattr__(self, "spread_sample_seed", sample_seed)
        object.__setattr__(self, "spread_replicate_count", replicate_count)
        object.__setattr__(self, "spread_max_replicate_count", max_replicates)
        object.__setattr__(
            self, "spread_convergence_relative_tolerance", convergence_tolerance
        )
        object.__setattr__(self, "edge_sample_spacing", spacing)
        object.__setattr__(self, "edge_quadrature_refinement_levels", refinement_levels)
        object.__setattr__(
            self, "include_vertex_density", bool(self.include_vertex_density)
        )
        object.__setattr__(
            self, "include_edge_density", bool(self.include_edge_density)
        )
        object.__setattr__(
            self, "store_sample_positions", bool(self.store_sample_positions)
        )
        normalized_resolution = DensityResolutionOptions(
            grid_shape=shape,
            grid_interval=interval,
            gaussian_bandwidth=bandwidth,
            gaussian_to_grid_ratio=ratio,
            adaptive_smearing=bool(self.adaptive_smearing),
            max_smearing_to_sample_sd_ratio=sd_ratio,
            sample_sd_quantile=quantile,
            spread_sample_size=sample_size,
            spread_sample_seed=sample_seed,
            spread_sampling_strategy=self.spread_sampling_strategy,
            spread_replicate_count=replicate_count,
            spread_max_replicate_count=max_replicates,
            spread_convergence_relative_tolerance=convergence_tolerance,
            spread_basin_mode=self.spread_basin_mode,
            broadening_metric=(
                "gaussian_sigma_v1"
                if resolution is None
                else resolution.broadening_metric
            ),
        )
        if not isinstance(self.kernel_options, DensityKernelOptions):
            raise TypeError("kernel_options must be DensityKernelOptions.")
        if not isinstance(self.storage_options, DensityStorageOptions):
            raise TypeError("storage_options must be DensityStorageOptions.")
        if not isinstance(self.optimization_options, DensityOptimizationOptions):
            raise TypeError("optimization_options must be DensityOptimizationOptions.")
        validate_density_implementation_selection(
            resolution=normalized_resolution,
            kernel=self.kernel_options,
            storage=self.storage_options,
        )
        object.__setattr__(self, "resolution_options", normalized_resolution)


@dataclass(frozen=True, slots=True)
class FrameworkDensityFields:
    """The two dimensionally distinct framework-density channels."""

    vertex_density: ScalarField3D | None
    edge_length_density: ScalarField3D | None
    edge_source: Literal["projected", "atomic_paths"]
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.vertex_density is None and self.edge_length_density is None:
            raise GraphAdapterError(
                "FrameworkDensityFields requires at least one channel."
            )
        for value in (self.vertex_density, self.edge_length_density):
            if value is not None and not is_scalar_field3d(value):
                raise TypeError(
                    "Framework density channels must satisfy ScalarField3D."
                )
        if self.edge_source not in {"projected", "atomic_paths"}:
            raise GraphAdapterError("Invalid framework edge source.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def fields(self) -> tuple[ScalarField3D, ...]:
        return tuple(
            value
            for value in (self.vertex_density, self.edge_length_density)
            if value is not None
        )


def _canonical_framework_source_key(kind: str, value: Any) -> tuple[Any, ...]:
    """Return one deterministic tagged source key for provenance records."""

    if isinstance(value, (int, np.integer)):
        return (kind, int(value))
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        payload = json.dumps(
            to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return (kind, payload)
    if isinstance(value, (tuple, list)) and value and isinstance(value[0], str):
        return tuple(value)
    raise GraphAdapterError(
        f"Cannot serialize {kind} density provenance key {value!r}."
    )


def resolve_framework_edge_quadrature(
    *,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    options: FrameworkDensityOptions,
    warn: bool = True,
) -> FrameworkEdgeQuadratureResolution:
    """Resolve the edge midpoint interval after density resolution is known."""

    cell = np.asarray(display_cell, dtype=np.float64)
    basis = np.diag(1.0 / np.asarray(grid_shape, dtype=np.float64)) @ cell
    axis_min = float(np.min(np.linalg.norm(basis, axis=1)))
    sigma = float(gaussian_bandwidth)
    gaussian_half = None if sigma <= 0.0 else 0.5 * sigma
    policy = axis_min if gaussian_half is None else min(axis_min, gaussian_half)
    nominal = float(options.edge_sample_spacing)
    mode = options.edge_sample_spacing_mode
    refinement_levels = (
        int(options.edge_quadrature_refinement_levels) if mode == "auto" else 0
    )
    certified_policy = policy / float(2**refinement_levels)
    realized = min(nominal, certified_policy) if mode == "auto" else nominal
    underresolved = bool(mode == "explicit" and realized > policy * (1.0 + 1.0e-12))
    if underresolved and warn:
        warnings.warn(
            "Explicit framework edge_sample_spacing is coarser than the resolved "
            "grid/kernel sampling policy; edge density may appear bead-like. "
            f"spacing={realized:.6g} angstrom, policy={policy:.6g} angstrom.",
            RuntimeWarning,
            stacklevel=3,
        )
    return FrameworkEdgeQuadratureResolution(
        mode=mode,
        nominal_spacing=nominal,
        realized_spacing=realized,
        axis_min_spacing=axis_min,
        gaussian_half_spacing=gaussian_half,
        policy_spacing=policy,
        refinement_levels=refinement_levels,
        explicit_underresolved=underresolved,
    )


def framework_edge_quadrature_count(length: float, spacing: float) -> int:
    """Return a stable midpoint count near exact integer length ratios."""

    ratio = float(length) / float(spacing)
    nearest = int(np.rint(ratio))
    if abs(ratio - nearest) <= 1.0e-12 * max(1.0, abs(ratio)):
        return max(1, nearest)
    return max(1, int(np.ceil(ratio)))


def build_framework_edge_quadrature_samples(
    edge_segments_fractional_by_frame: FloatArray,
    frame_weights: FloatArray,
    display_cell: FloatArray,
    *,
    spacing: float,
    max_samples: int,
    canonicalize_orientation: bool = False,
) -> tuple[FloatArray, FloatArray, IntArray, float]:
    """Build deterministic, orientation-invariant midpoint arc-length samples."""

    segments = np.asarray(edge_segments_fractional_by_frame, dtype=np.float64)
    weights = np.asarray(frame_weights, dtype=np.float64)
    cell = np.asarray(display_cell, dtype=np.float64)
    if segments.ndim != 4 or segments.shape[2:] != (2, 3):
        raise GraphAdapterError(
            "edge_segments_fractional_by_frame must have shape "
            "(n_frames, n_segments, 2, 3)."
        )
    if weights.shape != (segments.shape[0],):
        raise GraphAdapterError("Framework edge frame weights are misaligned.")
    all_points: list[FloatArray] = []
    all_weights: list[FloatArray] = []
    all_groups: list[IntArray] = []
    total_measure_terms: list[float] = []
    sample_count = 0
    for frame_index, frame_segments in enumerate(segments):
        frame_weight = float(weights[frame_index])
        for segment_index, segment in enumerate(frame_segments):
            start = np.asarray(segment[0], dtype=np.float64)
            end = np.asarray(segment[1], dtype=np.float64)
            start_cart = start @ cell
            end_cart = end @ cell
            if canonicalize_orientation and tuple(end_cart.tolist()) < tuple(
                start_cart.tolist()
            ):
                start, end = end, start
            delta = end - start
            length = float(np.linalg.norm(delta @ cell))
            if length <= 1.0e-14:
                continue
            count = framework_edge_quadrature_count(length, spacing)
            sample_count += count
            if sample_count > max_samples:
                raise GraphComplexityError(
                    "Framework edge density requires more than "
                    f"max_density_samples={max_samples} quadrature samples."
                )
            parameters = (np.arange(count, dtype=np.float64) + 0.5) / count
            points = start[None, :] + parameters[:, None] * delta[None, :]
            segment_measure = frame_weight * length
            quadrature_weights = np.full(
                count, segment_measure / count, dtype=np.float64
            )
            if count > 1:
                quadrature_weights[-1] = segment_measure - float(
                    np.sum(quadrature_weights[:-1], dtype=np.float64)
                )
            else:
                quadrature_weights[0] = segment_measure
            all_points.append(points - np.floor(points))
            all_weights.append(quadrature_weights)
            all_groups.append(np.full(count, segment_index, dtype=np.int64))
            total_measure_terms.append(segment_measure)
    if not all_points:
        raise GraphAdapterError(
            "Framework edge-length density contains no nondegenerate segments."
        )
    flat = np.concatenate(all_points, axis=0)
    quadrature_weights = np.concatenate(all_weights, axis=0)
    groups = np.concatenate(all_groups, axis=0)
    total_measure = float(np.sum(total_measure_terms, dtype=np.float64))
    correction = total_measure - float(np.sum(quadrature_weights, dtype=np.float64))
    quadrature_weights[-1] += correction
    return flat, quadrature_weights, groups, total_measure


def _density_from_mass(
    mass_grid: FloatArray,
    *,
    display_cell: FloatArray,
    total_measure: float,
    gaussian_bandwidth: float,
    kernel_options: DensityKernelOptions,
) -> tuple[FloatArray, FrozenJSONMapping]:
    smoothed, kernel_diagnostics = smooth_periodic_node_masses(
        mass_grid,
        display_cell,
        gaussian_bandwidth,
        kernel_options,
    )
    voxel_volume = abs(float(np.linalg.det(display_cell))) / float(smoothed.size)
    values = smoothed / voxel_volume
    actual = float(np.sum(values) * voxel_volume)
    if actual <= 0.0:
        raise GraphAdapterError("Framework density has zero numerical measure.")
    values *= float(total_measure) / actual
    return values, kernel_diagnostics


def prepare_framework_density_fields(
    *,
    vertex_fractional_by_frame: FloatArray,
    vertex_atom_indices: tuple[int, ...],
    edge_segments_fractional_by_frame: FloatArray,
    edge_atom_indices: tuple[int, ...],
    frame_weights: FloatArray,
    display_cell: FloatArray,
    registration_mode: str,
    options: FrameworkDensityOptions,
    max_fields: int,
    consumer_registration_signature: str | None = None,
    scientific_drift_owner: str | None = None,
    max_total_voxels: int,
    max_samples: int,
    planning_metadata_by_field: Mapping[str, Mapping[str, Any]] | None = None,
    approved_hybrid_plans_by_field: Mapping[str, DensityHybridRealizationPlan] | None = None,
    vertex_source_keys: tuple[Any, ...] | None = None,
    edge_source_keys: tuple[Any, ...] | None = None,
    max_nonzero_nodes: int | None = None,
    max_stored_block_values: int | None = None,
    max_blocks: int | None = None,
    max_kernel_pairs: int | None = None,
    max_planning_bytes: int | None = None,
    max_workspace_bytes: int | None = None,
    max_cic_contributions: int | None = None,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> FrameworkDensityFields:
    """Prepare normalized framework vertex and edge-length measures.

    Input coordinates are continuous display-cell fractional coordinates.  Edge
    segments have shape ``(n_frames, n_segments, 2, 3)`` and may cross periodic
    boundaries; midpoint quadrature samples are folded only at deposition time.
    """
    budget, _model, derived = resolve_density_resource_limits()
    max_fields = min(derived["max_density_fields"], int(max_fields))
    max_total_voxels = min(derived["max_density_voxels"], int(max_total_voxels))
    max_samples = min(derived["max_density_samples"], int(max_samples))
    if not options.optimization_options.resource_resolved:
        options = replace(
            options,
            optimization_options=options.optimization_options.resolve(
                max_memory_bytes=(
                    budget.max_memory_bytes
                    if max_workspace_bytes is None
                    else min(int(max_workspace_bytes), budget.max_memory_bytes)
                )
            ),
        )
    max_nonzero_nodes = derived["max_density_nonzero_nodes"] if max_nonzero_nodes is None else min(derived["max_density_nonzero_nodes"], int(max_nonzero_nodes))
    max_stored_block_values = derived["max_density_stored_block_values"] if max_stored_block_values is None else min(derived["max_density_stored_block_values"], int(max_stored_block_values))
    max_blocks = derived["max_density_blocks"] if max_blocks is None else min(derived["max_density_blocks"], int(max_blocks))
    max_kernel_pairs = derived["max_density_kernel_pairs"] if max_kernel_pairs is None else min(derived["max_density_kernel_pairs"], int(max_kernel_pairs))
    max_planning_bytes = budget.max_memory_bytes if max_planning_bytes is None else min(int(max_planning_bytes), budget.max_memory_bytes)
    max_workspace_bytes = budget.max_memory_bytes if max_workspace_bytes is None else min(int(max_workspace_bytes), budget.max_memory_bytes)
    max_cic_contributions = derived["max_density_kernel_pairs"] if max_cic_contributions is None else min(derived["max_density_kernel_pairs"], int(max_cic_contributions))
    progress_port = resolve_progress_port(
        progress,
        progress_callback=progress_callback,
        environment_variable="MDSTATS_PREPARE_PROGRESS",
        environment_label="mdstats-prepare",
    )
    reporter = ProgressEmitter(
        progress_port,
        source="plotting.framework_density",
    )
    vertices = np.asarray(vertex_fractional_by_frame, dtype=np.float64)
    segments = np.asarray(edge_segments_fractional_by_frame, dtype=np.float64)
    weights = np.asarray(frame_weights, dtype=np.float64)
    cell = np.asarray(display_cell, dtype=np.float64)
    if vertices.ndim != 3 or vertices.shape[2] != 3:
        raise GraphAdapterError(
            "vertex_fractional_by_frame must have shape (n_frames, n_vertices, 3)."
        )
    if segments.ndim != 4 or segments.shape[2:] != (2, 3):
        raise GraphAdapterError(
            "edge_segments_fractional_by_frame must have shape (n_frames, n_segments, 2, 3)."
        )
    if vertices.shape[0] != segments.shape[0] or weights.shape != (vertices.shape[0],):
        raise GraphAdapterError("Framework density frame arrays are misaligned.")
    if not np.isclose(float(np.sum(weights)), 1.0, rtol=0.0, atol=1.0e-12):
        raise GraphAdapterError("Framework density frame weights must sum to one.")
    n_fields = int(options.include_vertex_density) + int(options.include_edge_density)
    if n_fields > max_fields:
        raise GraphComplexityError(
            f"Requested {n_fields} framework density fields, exceeding the remaining max_density_fields={max_fields}."
        )
    reporter.started(
        "framework_density_realization",
        "preparing framework density channels",
        current=0,
        total=n_fields,
        unit="fields",
        metadata={"field_count": n_fields},
    )
    requested_backend = options.storage_options.grid_backend
    if (
        requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
        and options.kernel_options.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR
    ):
        raise GraphStyleError(
            "Framework local_sparse and auto density require "
            "discrete_periodized_v1."
        )
    per_field_voxel_budget = int(max_total_voxels) // n_fields
    numeric_options = AtomicDensityOptions(
        grid_shape=options.grid_shape,
        grid_interval=options.grid_interval,
        gaussian_bandwidth=options.gaussian_bandwidth,
        gaussian_to_grid_ratio=options.gaussian_to_grid_ratio,
        adaptive_smearing=options.adaptive_smearing,
        max_smearing_to_sample_sd_ratio=options.max_smearing_to_sample_sd_ratio,
        sample_sd_quantile=options.sample_sd_quantile,
        spread_sample_size=options.spread_sample_size,
        spread_sample_seed=options.spread_sample_seed,
        spread_sampling_strategy=options.spread_sampling_strategy,
        store_sample_positions=options.store_sample_positions,
        resolution_options=options.resolution_options,
        kernel_options=options.kernel_options,
        storage_options=options.storage_options,
        optimization_options=options.optimization_options,
    )
    numerics = resolve_density_numerics(
        cell,
        options=numeric_options,
        fractional_by_frame=vertices,
        frame_weights=weights,
        pbc=np.ones(3, dtype=bool),
        max_voxels=(
            int(np.iinfo(np.int64).max)
            if requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
            else per_field_voxel_budget
        ),
        field_label="framework density",
    )
    visual_adaptation = prepare_density_visual_grid_adaptation(
        cell,
        options=numeric_options,
        resolved_numerics=numerics,
        max_logical_voxels=(
            int(np.iinfo(np.int64).max)
            if requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
            else per_field_voxel_budget
        ),
        consumer_kind="framework",
        resolution_reference_source="framework_vertices",
        metadata={"field_bundle": "framework_density"},
    )
    grid_shape = visual_adaptation.grid_shape
    bandwidth = visual_adaptation.gaussian_bandwidth
    voxels = visual_adaptation.logical_node_count
    used_dense_voxels = 0

    consumer_metadata = {
        "consumer_registration_signature": consumer_registration_signature,
        "scientific_drift_owner": scientific_drift_owner,
        "consumer_migration_stage": (
            "C0B" if consumer_registration_signature is not None else None
        ),
    }
    consumer_metadata = {
        key: value for key, value in consumer_metadata.items() if value is not None
    }

    adaptive_metadata = visual_adaptation.visual_metadata_dict()

    vertex_field: ScalarField3D | None = None
    _warn_if_underresolved_density_grid(
        np.asarray(display_cell, dtype=np.float64),
        grid_shape,
        bandwidth,
    )
    completed_fields = 0
    if options.include_vertex_density:
        reporter.started(
            "framework_density_field",
            "preparing framework vertex occupancy",
            current=completed_fields + 1,
            total=n_fields,
            unit="fields",
            metadata={"field_key": "framework-vertex-density"},
        )
        n_samples = int(vertices.shape[0] * vertices.shape[1])
        if n_samples > max_samples:
            raise GraphComplexityError(
                f"Framework vertex density requires {n_samples} samples, exceeding max_density_samples={max_samples}."
            )
        folded = vertices - np.floor(vertices)
        flat = folded.reshape((-1, 3))
        sample_weights = np.repeat(weights, vertices.shape[1])
        total = float(vertices.shape[1])
        samples = flat @ cell if options.store_sample_positions else None
        atoms = tuple(sorted(set(int(v) for v in vertex_atom_indices)))
        source_keys = (
            tuple(("framework_vertex", int(value)) for value in atoms)
            if vertex_source_keys is None
            else tuple(
                _canonical_framework_source_key("framework_vertex", value)
                for value in vertex_source_keys
            )
        )
        provenance = DensitySourceProvenance(
            source_kind="framework_vertex_occupancy",
            atom_indices=atoms,
            vertex_keys=source_keys,
            metadata={"resolution_reference_source": "framework_vertices"},
        )
        vertex_planning_metadata = (
            {}
            if planning_metadata_by_field is None
            else dict(
                planning_metadata_by_field.get("framework-vertex-density", {})
            )
        )
        vertex_backend = requested_backend
        vertex_selection_metadata: Mapping[str, Any] | None = None
        if requested_backend == AUTO_BACKEND:
            vertex_backend, vertex_selection_metadata = _planned_backend_from_metadata(
                vertex_planning_metadata
            )
            if vertex_backend is None:
                vertex_selection = _select_atomic_auto_backend(
                    PeriodicWeightedSamples3D(
                        fractional_positions=flat,
                        weights=sample_weights,
                        sample_group_ids=np.tile(
                            np.arange(vertices.shape[1], dtype=np.int64),
                            vertices.shape[0],
                        ),
                        source_provenance=provenance,
                        total_measure=total,
                        measure_kind="occupancy",
                        measure_units="count",
                    ),
                    field_key="framework-vertex-density",
                    grid_shape=grid_shape,
                    display_cell=cell,
                    gaussian_bandwidth=bandwidth,
                    options=numeric_options,
                    max_total_voxels=per_field_voxel_budget,
                    max_nonzero_nodes=max_nonzero_nodes,
                    max_stored_block_values=max_stored_block_values,
                    max_blocks=max_blocks,
                    max_kernel_pairs=max_kernel_pairs,
                    max_planning_bytes=max_planning_bytes,
                    max_workspace_bytes=max_workspace_bytes,
                    max_cic_contributions=max_cic_contributions,
                )
                vertex_backend = vertex_selection.selected_backend
                vertex_selection_metadata = vertex_selection.to_json_dict()
        vertex_sparse = vertex_backend == LOCAL_SPARSE_BACKEND
        if not vertex_sparse:
            used_dense_voxels += voxels
            if used_dense_voxels > max_total_voxels:
                raise GraphComplexityError(
                    "Framework density dense fields exceed the remaining "
                    f"max_density_voxels={max_total_voxels}."
                )
        common_vertex_metadata = {
            "schema_version": FRAMEWORK_DENSITY_SCHEMA,
            "source_kind": "framework_vertex_occupancy",
            "physical_units": "angstrom^-3",
            "normalization": "one_per_projected_framework_vertex",
            "deposition": "periodic_trilinear_cloud_in_cell",
            "smoothing_operator": options.kernel_options.smoothing_operator,
            "broadening_metric": options.resolution_options.broadening_metric,
            "storage_backend": vertex_backend,
            "requested_storage_backend": requested_backend,
            "backend_selection": vertex_selection_metadata,
            "sparse_evaluation_mode": options.optimization_options.sparse_evaluation_mode,
            "stencil_cache_enabled": options.optimization_options.cache_stencil_supports,
            "sparse_pair_chunk_size": options.optimization_options.sparse_pair_chunk_size,
            "sparse_group_batch_size": options.optimization_options.sparse_group_batch_size,
            "sparse_realization_mode": options.optimization_options.sparse_realization_mode,
            "allow_ld7_fallback": options.optimization_options.allow_ld7_fallback,
            "registration_mode": registration_mode,
            **consumer_metadata,
            "frame_count": int(vertices.shape[0]),
            **visual_adaptation.grid_metadata_dict(),
            **adaptive_metadata,
            **vertex_planning_metadata,
        }
        if vertex_sparse:
            vertex_field = _prepare_sparse_field_for_options(
                PeriodicWeightedSamples3D(
                    fractional_positions=flat,
                    weights=sample_weights,
                    source_provenance=provenance,
                    total_measure=total,
                    measure_kind="occupancy",
                    measure_units="count",
                    sample_group_ids=np.tile(
                        np.arange(vertices.shape[1], dtype=np.int64),
                        vertices.shape[0],
                    ),
                    metadata={"registration_mode": registration_mode},
                ),
                grid_shape=grid_shape,
                display_cell=cell,
                gaussian_bandwidth=bandwidth,
                field_key="framework-vertex-density",
                label="framework vertex occupancy",
                physical_units="angstrom^-3",
                broadening_metric=options.resolution_options.broadening_metric,
                options=options,
                selected_atom_indices=atoms,
                sample_positions=samples,
                metadata=common_vertex_metadata,
                max_cic_contributions=max_cic_contributions,
                max_kernel_pairs=max_kernel_pairs,
                max_workspace_bytes=max_workspace_bytes,
                max_nonzero_nodes=max_nonzero_nodes,
                max_stored_block_values=max_stored_block_values,
                max_blocks=max_blocks,
                max_planning_bytes=max_planning_bytes,
                approved_hybrid_plan=(
                    None
                    if approved_hybrid_plans_by_field is None
                    else approved_hybrid_plans_by_field.get("framework-vertex-density")
                ),
            )
        else:
            mass = _deposit_cic(flat, sample_weights, grid_shape)
            values, vertex_kernel_diagnostics = _density_from_mass(
                mass,
                display_cell=cell,
                total_measure=total,
                gaussian_bandwidth=bandwidth,
                kernel_options=options.kernel_options,
            )
            vertex_field = PeriodicScalarField3D(
                field_key="framework-vertex-density",
                label="framework vertex occupancy",
                values=values,
                display_cell=cell,
                total_measure=total,
                selected_atom_indices=atoms,
                gaussian_bandwidth=bandwidth,
                sample_positions=samples,
                source_provenance=provenance,
                metadata={
                    **common_vertex_metadata,
                    "smoothing": (
                        "periodic_cartesian_isotropic_gaussian_fft"
                        if options.kernel_options.smoothing_operator
                        == LEGACY_SPECTRAL_OPERATOR
                        else "periodic_discrete_periodized_gaussian_fft"
                    ),
                    **vertex_kernel_diagnostics.to_json_dict(),
                },
            )
        completed_fields += 1
        assert vertex_field is not None
        reporter.completed(
            "framework_density_field",
            f"completed framework vertex occupancy with backend={vertex_field.storage_backend}",
            current=completed_fields,
            total=n_fields,
            unit="fields",
            metadata={
                "field_key": vertex_field.field_key,
                "backend": vertex_field.storage_backend,
                "sigma_angstrom": float(vertex_field.gaussian_bandwidth),
            },
        )

    edge_field: ScalarField3D | None = None
    if options.include_edge_density:
        reporter.started(
            "framework_density_field",
            "preparing framework edge-length density",
            current=completed_fields + 1,
            total=n_fields,
            unit="fields",
            metadata={"field_key": "framework-edge-length-density"},
        )
        quadrature = resolve_framework_edge_quadrature(
            grid_shape=grid_shape,
            display_cell=cell,
            gaussian_bandwidth=bandwidth,
            options=options,
        )
        flat, quadrature_weights, sample_groups, total_measure = (
            build_framework_edge_quadrature_samples(
                segments,
                weights,
                cell,
                spacing=quadrature.realized_spacing,
                max_samples=max_samples,
                canonicalize_orientation=requested_backend != DENSE_BACKEND,
            )
        )
        sample_count = int(flat.shape[0])
        samples = flat @ cell if options.store_sample_positions else None
        edge_broadening_metadata: dict[str, Any] = {}
        if (
            options.resolution_options.broadening_metric
            == EFFECTIVE_CIC_STENCIL_BROADENING
        ):
            edge_diagnostic = effective_artificial_broadening(
                flat,
                quadrature_weights,
                grid_shape,
                cell,
                bandwidth,
                kernel_tail_tolerance=options.kernel_options.kernel_tail_tolerance,
                metadata={"field_label": "framework edge-length density"},
            )
            edge_broadening_metadata.update(edge_diagnostic.metadata_dict())
            edge_broadening_metadata["resolution_reference_source"] = (
                "framework_vertices"
            )
            edge_broadening_metadata[
                "resolution_reference_effective_artificial_rms"
            ] = (
                None
                if numerics.broadening_diagnostic is None
                else numerics.broadening_diagnostic.effective_rms
            )
            edge_broadening_metadata["field_artificial_to_reference_target_ratio"] = (
                None
                if numerics.adaptive_target_width is None
                else edge_diagnostic.effective_rms / numerics.adaptive_target_width
            )
        atoms = tuple(sorted(set(int(v) for v in edge_atom_indices)))
        source_keys = (
            tuple(("framework_edge", int(value)) for value in range(segments.shape[1]))
            if edge_source_keys is None
            else tuple(
                _canonical_framework_source_key("framework_edge", value)
                for value in edge_source_keys
            )
        )
        provenance = DensitySourceProvenance(
            source_kind="framework_edge_length",
            atom_indices=atoms,
            edge_keys=source_keys,
            metadata={
                "edge_source": options.edge_source,
                "resolution_reference_source": "framework_vertices",
            },
        )
        edge_planning_metadata = (
            {}
            if planning_metadata_by_field is None
            else dict(
                planning_metadata_by_field.get(
                    "framework-edge-length-density", {}
                )
            )
        )
        edge_backend = requested_backend
        edge_selection_metadata: Mapping[str, Any] | None = None
        if requested_backend == AUTO_BACKEND:
            edge_backend, edge_selection_metadata = _planned_backend_from_metadata(
                edge_planning_metadata
            )
            if edge_backend is None:
                edge_selection = _select_atomic_auto_backend(
                    PeriodicWeightedSamples3D(
                        fractional_positions=flat,
                        weights=quadrature_weights,
                        source_provenance=provenance,
                        total_measure=total_measure,
                        measure_kind="arc_length",
                        measure_units="angstrom",
                        sample_group_ids=sample_groups,
                    ),
                    field_key="framework-edge-length-density",
                    grid_shape=grid_shape,
                    display_cell=cell,
                    gaussian_bandwidth=bandwidth,
                    options=numeric_options,
                    max_total_voxels=per_field_voxel_budget,
                    max_nonzero_nodes=max_nonzero_nodes,
                    max_stored_block_values=max_stored_block_values,
                    max_blocks=max_blocks,
                    max_kernel_pairs=max_kernel_pairs,
                    max_planning_bytes=max_planning_bytes,
                    max_workspace_bytes=max_workspace_bytes,
                    max_cic_contributions=max_cic_contributions,
                )
                edge_backend = edge_selection.selected_backend
                edge_selection_metadata = edge_selection.to_json_dict()
        edge_sparse = edge_backend == LOCAL_SPARSE_BACKEND
        if not edge_sparse:
            used_dense_voxels += voxels
            if used_dense_voxels > max_total_voxels:
                raise GraphComplexityError(
                    "Framework density dense fields exceed the remaining "
                    f"max_density_voxels={max_total_voxels}."
                )
        common_edge_metadata = {
            "schema_version": FRAMEWORK_DENSITY_SCHEMA,
            "source_kind": "framework_edge_length",
            "physical_units": "angstrom^-2",
            "normalization": "time_or_ensemble_averaged_total_arc_length",
            "edge_source": options.edge_source,
            **quadrature.metadata_dict(),
            "quadrature": "uniform_midpoint_arc_length",
            "quadrature_orientation_policy": (
                "canonical_cartesian_endpoints"
                if requested_backend != DENSE_BACKEND
                else "input_segment_order"
            ),
            "quadrature_sample_count": sample_count,
            "quadrature_group_count": int(segments.shape[1]),
            "quadrature_weight_sum": float(
                np.sum(quadrature_weights, dtype=np.float64)
            ),
            "quadrature_convergence_policy": "ld3_validation_certified",
            "deposition": "periodic_trilinear_cloud_in_cell",
            "smoothing_operator": options.kernel_options.smoothing_operator,
            "broadening_metric": options.resolution_options.broadening_metric,
            "storage_backend": edge_backend,
            "requested_storage_backend": requested_backend,
            "backend_selection": edge_selection_metadata,
            "sparse_evaluation_mode": options.optimization_options.sparse_evaluation_mode,
            "stencil_cache_enabled": options.optimization_options.cache_stencil_supports,
            "sparse_pair_chunk_size": options.optimization_options.sparse_pair_chunk_size,
            "registration_mode": registration_mode,
            **consumer_metadata,
            "frame_count": int(segments.shape[0]),
            **visual_adaptation.grid_metadata_dict(),
            **adaptive_metadata,
            **edge_broadening_metadata,
            **edge_planning_metadata,
        }
        if edge_sparse:
            edge_field = _prepare_sparse_field_for_options(
                PeriodicWeightedSamples3D(
                    fractional_positions=flat,
                    weights=quadrature_weights,
                    source_provenance=provenance,
                    total_measure=total_measure,
                    measure_kind="arc_length",
                    measure_units="angstrom",
                    sample_group_ids=sample_groups,
                    metadata={
                        "registration_mode": registration_mode,
                        "edge_source": options.edge_source,
                    },
                ),
                grid_shape=grid_shape,
                display_cell=cell,
                gaussian_bandwidth=bandwidth,
                field_key="framework-edge-length-density",
                label=f"framework edge-length density ({options.edge_source})",
                physical_units="angstrom^-2",
                broadening_metric=options.resolution_options.broadening_metric,
                options=options,
                selected_atom_indices=atoms,
                sample_positions=samples,
                metadata=common_edge_metadata,
                max_cic_contributions=max_cic_contributions,
                max_kernel_pairs=max_kernel_pairs,
                max_workspace_bytes=max_workspace_bytes,
                max_nonzero_nodes=max_nonzero_nodes,
                max_stored_block_values=max_stored_block_values,
                max_blocks=max_blocks,
                max_planning_bytes=max_planning_bytes,
                approved_hybrid_plan=(
                    None
                    if approved_hybrid_plans_by_field is None
                    else approved_hybrid_plans_by_field.get("framework-edge-length-density")
                ),
            )
        else:
            mass = _deposit_cic(flat, quadrature_weights, grid_shape)
            values, edge_kernel_diagnostics = _density_from_mass(
                mass,
                display_cell=cell,
                total_measure=total_measure,
                gaussian_bandwidth=bandwidth,
                kernel_options=options.kernel_options,
            )
            edge_field = PeriodicScalarField3D(
                field_key="framework-edge-length-density",
                label=f"framework edge-length density ({options.edge_source})",
                values=values,
                display_cell=cell,
                total_measure=total_measure,
                selected_atom_indices=atoms,
                gaussian_bandwidth=bandwidth,
                sample_positions=samples,
                source_provenance=provenance,
                metadata={
                    **common_edge_metadata,
                    "smoothing": (
                        "periodic_cartesian_isotropic_gaussian_fft"
                        if options.kernel_options.smoothing_operator
                        == LEGACY_SPECTRAL_OPERATOR
                        else "periodic_discrete_periodized_gaussian_fft"
                    ),
                    **edge_kernel_diagnostics.to_json_dict(),
                },
            )
        completed_fields += 1
        assert edge_field is not None
        reporter.completed(
            "framework_density_field",
            f"completed framework edge-length density with backend={edge_field.storage_backend}",
            current=completed_fields,
            total=n_fields,
            unit="fields",
            metadata={
                "field_key": edge_field.field_key,
                "backend": edge_field.storage_backend,
                "sigma_angstrom": float(edge_field.gaussian_bandwidth),
            },
        )

    reporter.completed(
        "framework_density_realization",
        "completed framework density channels",
        current=completed_fields,
        total=n_fields,
        unit="fields",
    )
    return FrameworkDensityFields(
        vertex_density=vertex_field,
        edge_length_density=edge_field,
        edge_source=options.edge_source,
        metadata={
            "schema_version": FRAMEWORK_DENSITY_SCHEMA,
            "channels_are_dimensionally_distinct": True,
            **consumer_metadata,
        },
    )
