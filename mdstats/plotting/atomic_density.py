"""Periodic atomic-density fields for framework-dynamics scenes.

The deposition backend uses trilinear cloud-in-cell assignment, adapted from the
particle-mesh method of Hockney and Eastwood [Computer Simulation Using
Particles, 1988]. The dense backend supports both the historical finite-mode
spectral Gaussian and the canonical finite-support discrete periodized Gaussian.  Probability-mass shells follow the highest-density-region
construction of Hyndman [The American Statistician 50, 120-126 (1996)].
Scientific fields are prepared independently of Plotly. The default renderer
extracts explicit periodic probability-mass meshes before HTML serialization;
a sparse voxel-cloud fallback is also available.
"""

from __future__ import annotations

import warnings
import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterator, Literal, Mapping, Sequence

import numpy as np
from ase.data import atomic_numbers as ase_atomic_numbers
from ase.data import chemical_symbols
from numpy.typing import NDArray

from ..collection import AtomisticFrameCollection
from ..coordinates.consumer_adapters import ConsumerCoordinateView
from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port
from .density_execution_journal import record_density_stage_timing
from .density_contracts import (
    AUTO_BACKEND,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    EFFECTIVE_CIC_STENCIL_BROADENING,
    GAUSSIAN_SIGMA_BROADENING,
    LEGACY_SPECTRAL_OPERATOR,
    DensityKernelOptions,
    DensityOptimizationOptions,
    DensityRenderOptions,
    DensityResolutionOptions,
    DensitySourceProvenance,
    DensityStorageOptions,
    DensityStorageSummary,
    FrozenJSONMapping,
    PeriodicWeightedSamples3D,
    ScalarField3D,
    freeze_json_mapping,
    validate_density_implementation_selection,
)
from .density_mesh_contracts import (
    DensityMeshFaceContract,
    evaluate_density_mesh_face_contract,
    legacy_standalone_face_contract,
)
from .density_broadening import (
    ArtificialBroadeningDiagnostic,
    effective_artificial_broadening,
)
from .density_visual_policy import prepare_density_visual_grid_adaptation
from .density_backend_selection import (
    DensityBackendCandidateEstimate,
    DensityBackendSelection,
    preferred_auto_backend,
)
from .density_kernel import smooth_periodic_node_masses
from .density_gpu import try_gpu_cic_deposition
from .density_sparse_optimization import (
    aggregate_periodic_cic_sparse_optimized,
    get_periodic_gaussian_stencil_support,
    plan_group_batched_sparse_targets_optimized,
    prepare_sparse_canonical_density_optimized,
)
from .density_sparse_reference import (
    SparseHDRDetails,
    aggregate_periodic_cic_sparse,
    prepare_sparse_canonical_density_reference,
)
from .density_block_routing import get_periodic_kernel_block_routing
from .density_support_atlas import build_density_support_atlas, pack_periodic_cic_source
from .density_tiled_fft import (
    DensityHybridExecutorOptions,
    DensityHybridRealizationPlan,
    plan_hybrid_tiled_realization,
    realize_density_hybrid_tiled,
)
from .density_block_sparse import (
    pack_sparse_reference_blocks,
    plan_block_packing,
    plan_sparse_target_nodes,
)
from .density_diagnostics import (
    CellEquivalenceReport,
    PeriodicSpreadDiagnostics,
    ReciprocalResolutionDiagnostic,
    periodic_frechet_mean_diagnostic,
    periodic_item_spread_diagnostics,
    reciprocal_resolution_diagnostic,
    require_equivalent_laboratory_density_cells,
)
from .density_planning import dense_retained_bytes, dense_transient_bytes
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

ATOMIC_DENSITY_SCHEMA = "mdstats.atomic-density-field.v1"


def _readonly(value: Any, dtype: Any, *, ndim: int | None = None) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphAdapterError(
            f"Expected a {ndim}-dimensional array; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError("Atomic-density arrays must be finite.")
    array.setflags(write=False)
    return array


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


@dataclass(frozen=True, slots=True)
class AtomicDensitySelection:
    """Union selection for one atomic occupancy field."""

    atom_indices: tuple[int, ...] = ()
    species: tuple[str | int, ...] = ()
    label: str | None = None

    def __post_init__(self) -> None:
        indices: list[int] = []
        for value in self.atom_indices:
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GraphAdapterError("atom_indices must contain integers.")
            index = int(value)
            if index < 0:
                raise GraphAdapterError("atom_indices must be nonnegative.")
            indices.append(index)
        species: list[str | int] = []
        for value in self.species:
            if isinstance(value, bool):
                raise GraphAdapterError("species cannot contain Boolean values.")
            if isinstance(value, (int, np.integer)):
                number = int(value)
                if number <= 0 or number >= len(chemical_symbols):
                    raise GraphAdapterError(f"Invalid atomic number {number}.")
                species.append(number)
            elif isinstance(value, str) and value in ase_atomic_numbers:
                species.append(value)
            else:
                raise GraphAdapterError(f"Invalid species selector {value!r}.")
        if not indices and not species:
            raise GraphAdapterError(
                "AtomicDensitySelection requires atom_indices and/or species."
            )
        if self.label is not None and (not isinstance(self.label, str) or not self.label):
            raise GraphAdapterError("label must be None or a nonempty string.")
        object.__setattr__(self, "atom_indices", tuple(sorted(set(indices))))
        object.__setattr__(self, "species", tuple(species))

    def resolve(self, collection: AtomisticFrameCollection) -> tuple[int, ...]:
        selected = set(self.atom_indices)
        for selector in self.species:
            number = int(selector) if isinstance(selector, int) else int(ase_atomic_numbers[selector])
            selected.update(int(i) for i in np.flatnonzero(collection.atomic_numbers == number))
        if selected and max(selected) >= collection.n_atoms:
            raise GraphAdapterError("Atomic-density selection contains an atom outside the collection.")
        if not selected:
            raise GraphAdapterError("Atomic-density selection resolved to no atoms.")
        return tuple(sorted(selected))


@dataclass(frozen=True, slots=True)
class AtomicDensityOptions:
    """Numerical preparation policy for periodic atomic occupancy fields.

    By default the grid shape is derived from ``grid_interval`` and the three
    display-cell vector lengths. The Gaussian bandwidth is then derived from
    ``gaussian_to_grid_ratio`` times the longest realized lattice-grid edge.
    When adaptive smearing is enabled, per-atom periodic Cartesian standard
    deviations are compared with the kernel width and the grid is refined
    toward the configured broadening limit. By default, the canonical
    periodized kernel and automatic dense-versus-local-sparse planner resolve
    the physical grid first and select the feasible implementation afterward;
    the dense voxel allowance therefore cannot silently broaden the Gaussian.
    Explicit ``grid_shape``, ``gaussian_bandwidth``, operator, or backend values
    remain authoritative.
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
    store_sample_positions: bool = False
    resolution_options: DensityResolutionOptions | None = None
    kernel_options: DensityKernelOptions = field(default_factory=DensityKernelOptions)
    storage_options: DensityStorageOptions = field(default_factory=DensityStorageOptions)
    optimization_options: DensityOptimizationOptions = field(
        default_factory=DensityOptimizationOptions
    )

    def __post_init__(self) -> None:
        resolution = self.resolution_options
        if resolution is not None:
            if not isinstance(resolution, DensityResolutionOptions):
                raise TypeError("resolution_options must be DensityResolutionOptions or None.")
            object.__setattr__(self, "grid_shape", resolution.grid_shape)
            object.__setattr__(self, "grid_interval", resolution.grid_interval)
            object.__setattr__(self, "gaussian_bandwidth", resolution.gaussian_bandwidth)
            object.__setattr__(self, "gaussian_to_grid_ratio", resolution.gaussian_to_grid_ratio)
            object.__setattr__(self, "adaptive_smearing", resolution.adaptive_smearing)
            object.__setattr__(self, "max_smearing_to_sample_sd_ratio", resolution.max_smearing_to_sample_sd_ratio)
            object.__setattr__(self, "sample_sd_quantile", resolution.sample_sd_quantile)
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
                raise GraphStyleError("grid_shape must contain three integers or be None.")
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
                raise GraphStyleError("gaussian_bandwidth must be finite and nonnegative or None.")
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
        object.__setattr__(self, "store_sample_positions", bool(self.store_sample_positions))
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
                GAUSSIAN_SIGMA_BROADENING
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
class AtomicDensity3DRenderOptions:
    """Interactive probability-mass density styling.

    ``render_mode='mesh'`` extracts the probability-mass shells with the
    Lewiner marching-cubes implementation provided by scikit-image before the
    Plotly document is written.  This is the reliable browser default because
    the browser receives explicit triangles rather than being asked to
    triangulate an almost zero-width ``Isosurface`` interval at runtime.

    ``render_mode='voxel_cloud'`` is a dependency-light fallback that displays
    the highest-density voxels as transparent points.  It is less geometrically
    smooth but robust on limited WebGL implementations.
    """

    mass_fractions: tuple[float, ...] = (0.50, 0.80, 0.95)
    inner_opacity: float = 0.46
    outer_opacity: float = 0.12
    render_mode: Literal["mesh", "voxel_cloud"] = "mesh"
    standalone_final_mesh_faces: int = 250_000
    max_mesh_faces: int | None = None
    cloud_max_points: int = 40_000
    cloud_point_size: float = 2.2
    cloud_opacity: float = 0.18
    show_samples: bool = False
    sample_size: float = 2.0
    sample_opacity: float = 0.08
    show_legend: bool = True
    render_options: DensityRenderOptions | None = None

    def __post_init__(self) -> None:
        shared = self.render_options
        if shared is not None:
            if not isinstance(shared, DensityRenderOptions):
                raise TypeError("render_options must be DensityRenderOptions or None.")
            object.__setattr__(self, "mass_fractions", shared.mass_fractions)
            object.__setattr__(self, "render_mode", shared.render_mode)
            object.__setattr__(
                self,
                "standalone_final_mesh_faces",
                shared.standalone_final_mesh_faces,
            )
            object.__setattr__(self, "max_mesh_faces", None)
            object.__setattr__(self, "cloud_max_points", shared.cloud_max_points)
        fractions = tuple(float(v) for v in self.mass_fractions)
        if len(fractions) < 2 or any(not np.isfinite(v) or not 0.0 < v < 1.0 for v in fractions):
            raise GraphStyleError("mass_fractions must contain at least two values strictly between zero and one.")
        if tuple(sorted(set(fractions))) != fractions:
            raise GraphStyleError("mass_fractions must be strictly increasing.")
        if self.render_mode not in {"mesh", "voxel_cloud"}:
            raise GraphStyleError("render_mode must be 'mesh' or 'voxel_cloud'.")
        for name in ("inner_opacity", "outer_opacity", "sample_opacity", "cloud_opacity"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or not 0.0 <= value <= 1.0:
                raise GraphStyleError(f"{name} must lie in [0, 1].")
            object.__setattr__(self, name, value)
        for name in ("sample_size", "cloud_point_size"):
            size = float(getattr(self, name))
            if not np.isfinite(size) or size <= 0.0:
                raise GraphStyleError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, size)
        standalone_limit = _positive_int(
            self.standalone_final_mesh_faces,
            name="standalone_final_mesh_faces",
        )
        if self.max_mesh_faces is not None:
            legacy_limit = _positive_int(self.max_mesh_faces, name="max_mesh_faces")
            if (
                self.standalone_final_mesh_faces != 250_000
                and standalone_limit != legacy_limit
            ):
                raise GraphStyleError(
                    "standalone_final_mesh_faces and deprecated max_mesh_faces disagree."
                )
            standalone_limit = legacy_limit
        object.__setattr__(
            self,
            "standalone_final_mesh_faces",
            standalone_limit,
        )
        object.__setattr__(self, "max_mesh_faces", standalone_limit)
        object.__setattr__(
            self, "cloud_max_points", _positive_int(self.cloud_max_points, name="cloud_max_points")
        )
        object.__setattr__(self, "render_mode", str(self.render_mode))
        object.__setattr__(self, "mass_fractions", fractions)
        object.__setattr__(self, "show_samples", bool(self.show_samples))
        object.__setattr__(self, "show_legend", bool(self.show_legend))
        object.__setattr__(
            self,
            "render_options",
            DensityRenderOptions(
                mass_fractions=fractions,
                render_mode=self.render_mode,
                display_replication=(
                    "canonical" if shared is None else shared.display_replication
                ),
                standalone_final_mesh_faces=self.standalone_final_mesh_faces,
                max_mesh_faces=None,
                cloud_max_points=self.cloud_max_points,
            ),
        )


@dataclass(frozen=True, slots=True)
class PeriodicScalarField3D:
    """One normalized dense scalar density field on a periodic logical-node grid.

    The class directly satisfies :class:`ScalarField3D` and
    :class:`PeriodicNodeFieldAccess`.  Existing construction semantics remain
    compatible; the structured provenance is derived when callers do not supply it.
    """

    field_key: str
    label: str
    values: FloatArray
    display_cell: FloatArray
    total_measure: float
    selected_atom_indices: tuple[int, ...]
    gaussian_bandwidth: float
    sample_positions: FloatArray | None = None
    metadata: Mapping[str, Any] | FrozenJSONMapping = field(default_factory=dict)
    source_provenance: DensitySourceProvenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.field_key, str) or not self.field_key:
            raise GraphAdapterError("field_key must be a nonempty string.")
        if not isinstance(self.label, str) or not self.label:
            raise GraphAdapterError("label must be a nonempty string.")
        values = _readonly(self.values, np.float64, ndim=3)
        if np.any(values < -1.0e-14):
            raise GraphAdapterError("Density values must be nonnegative.")
        cell = _readonly(self.display_cell, np.float64, ndim=2)
        if cell.shape != (3, 3) or abs(float(np.linalg.det(cell))) <= 1.0e-12:
            raise GraphAdapterError("display_cell must be a nonsingular 3x3 matrix.")
        total = float(self.total_measure)
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        bandwidth = float(self.gaussian_bandwidth)
        if not np.isfinite(bandwidth) or bandwidth < 0.0:
            raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
        atoms = tuple(int(v) for v in self.selected_atom_indices)
        if not atoms or atoms != tuple(sorted(set(atoms))):
            raise GraphAdapterError("selected_atom_indices must be nonempty, sorted, and unique.")
        samples = None
        if self.sample_positions is not None:
            samples = _readonly(self.sample_positions, np.float64, ndim=2)
            if samples.shape[1:] != (3,):
                raise GraphAdapterError("sample_positions must have shape (n, 3).")
        metadata = freeze_json_mapping(self.metadata)
        provenance = self.source_provenance
        if provenance is None:
            provenance = DensitySourceProvenance(
                source_kind=str(metadata.get("source_kind", "atomic_occupancy")),
                atom_indices=atoms,
            )
        if not isinstance(provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance or None.")
        if provenance.atom_indices and provenance.atom_indices != atoms:
            raise GraphAdapterError(
                "source_provenance.atom_indices must match selected_atom_indices when present."
            )
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "selected_atom_indices", atoms)
        object.__setattr__(self, "gaussian_bandwidth", bandwidth)
        object.__setattr__(self, "sample_positions", samples)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "source_provenance", provenance)

    @property
    def schema_version(self) -> str:
        return str(self.metadata.get("schema_version", ATOMIC_DENSITY_SCHEMA))

    @property
    def physical_units(self) -> str:
        return str(self.metadata.get("physical_units", "angstrom^-3"))

    @property
    def smoothing_operator(self) -> str:
        return str(self.metadata.get("smoothing_operator", LEGACY_SPECTRAL_OPERATOR))

    @property
    def broadening_metric(self) -> str:
        return str(self.metadata.get("broadening_metric", GAUSSIAN_SIGMA_BROADENING))

    @property
    def storage_backend(self) -> str:
        return DENSE_BACKEND

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return tuple(int(v) for v in self.values.shape)

    @property
    def voxel_volume(self) -> float:
        return abs(float(np.linalg.det(self.display_cell))) / float(self.values.size)

    @property
    def integral(self) -> float:
        return float(np.sum(self.values) * self.voxel_volume)

    def hdr_details(self, fraction: float) -> SparseHDRDetails:
        q = float(fraction)
        if not np.isfinite(q) or not 0.0 < q < 1.0:
            raise GraphStyleError("fraction must lie strictly between zero and one.")
        values = np.asarray(self.values, dtype=np.float64).ravel()
        descending = np.sort(values)[::-1]
        cumulative = np.cumsum(descending, dtype=np.float64) * self.voxel_volume
        index = min(
            int(np.searchsorted(cumulative, q * self.total_measure, side="left")),
            descending.size - 1,
        )
        threshold = float(descending[index])
        selected = values >= threshold
        measure = float(np.sum(values[selected], dtype=np.float64)) * self.voxel_volume
        return SparseHDRDetails(
            requested_mass_fraction=q,
            threshold=threshold,
            achieved_mass_fraction=measure / self.total_measure,
            selected_node_count=int(np.count_nonzero(selected)),
            threshold_tie_count=int(np.count_nonzero(values == threshold)),
            selected_measure=measure,
            total_measure=self.total_measure,
        )

    def threshold_for_mass_fraction(self, fraction: float) -> float:
        return self.hdr_details(fraction).threshold

    def storage_summary(self) -> DensityStorageSummary:
        count = int(self.values.size)
        return DensityStorageSummary(
            storage_backend=DENSE_BACKEND,
            logical_grid_shape=self.grid_shape,
            logical_node_count=count,
            nonzero_node_count=int(np.count_nonzero(self.values)),
            stored_value_count=count,
            stored_block_count=0,
            estimated_bytes=int(self.values.nbytes),
            realized_bytes=int(self.values.nbytes),
            metadata={"array_order": "C", "dtype": "float64"},
        )

    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        total = int(self.values.size)
        size = total if batch_size is None else _positive_int(batch_size, name="batch_size")
        shape = self.grid_shape
        flat_values = self.values.reshape(-1)
        for start in range(0, total, size):
            stop = min(total, start + size)
            flat = np.arange(start, stop, dtype=np.int64)
            i = flat // (shape[1] * shape[2])
            remainder = flat % (shape[1] * shape[2])
            j = remainder // shape[2]
            k = remainder % shape[2]
            indices = np.column_stack((i, j, k)).astype(np.int64, copy=False)
            indices.setflags(write=False)
            values = flat_values[start:stop]
            values.setflags(write=False)
            yield indices, values

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray:
        indices = np.asarray(logical_indices)
        if indices.ndim != 2 or indices.shape[1:] != (3,):
            raise GraphAdapterError("logical_indices must have shape (n, 3).")
        if not np.issubdtype(indices.dtype, np.integer):
            raise GraphAdapterError("logical_indices must contain integers.")
        wrapped = np.mod(indices.astype(np.int64, copy=False), np.asarray(self.grid_shape, dtype=np.int64))
        result = np.asarray(
            self.values[wrapped[:, 0], wrapped[:, 1], wrapped[:, 2]],
            dtype=np.float64,
        )
        result.setflags(write=False)
        return result

    def to_json_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "label": self.label,
            "physical_units": self.physical_units,
            "display_cell": self.display_cell.tolist(),
            "total_measure": self.total_measure,
            "selected_atom_indices": list(self.selected_atom_indices),
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "smoothing_operator": self.smoothing_operator,
            "broadening_metric": self.broadening_metric,
            "storage_backend": self.storage_backend,
            "source_provenance": self.source_provenance.to_json_dict(),
            "sample_positions": (
                None if self.sample_positions is None else self.sample_positions.tolist()
            ),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_values:
            result["values"] = self.values.tolist()
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicScalarField3D":
        if value.get("storage_backend", DENSE_BACKEND) != DENSE_BACKEND:
            raise GraphAdapterError("PeriodicScalarField3D can deserialize only dense fields.")
        if "values" not in value:
            raise GraphAdapterError("Dense field JSON requires values.")
        metadata = dict(value.get("metadata", {}))
        return cls(
            field_key=str(value["field_key"]),
            label=str(value["label"]),
            values=np.asarray(value["values"], dtype=np.float64),
            display_cell=np.asarray(value["display_cell"], dtype=np.float64),
            total_measure=float(value["total_measure"]),
            selected_atom_indices=tuple(value["selected_atom_indices"]),
            gaussian_bandwidth=float(value["gaussian_bandwidth"]),
            sample_positions=(
                None
                if value.get("sample_positions") is None
                else np.asarray(value["sample_positions"], dtype=np.float64)
            ),
            metadata=metadata,
            source_provenance=DensitySourceProvenance.from_json_dict(
                value["source_provenance"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ResolvedDensityNumerics:
    """Resolved grid and Gaussian policy for one density field."""

    grid_shape: tuple[int, int, int]
    realized_intervals: tuple[float, float, float]
    gaussian_bandwidth: float
    sample_standard_deviations: tuple[float, ...]
    sample_sd_reference: float | None
    adaptive_triggered: bool
    adaptive_budget_limited: bool
    adaptive_target_defined: bool
    smearing_definition: str
    spread_diagnostics: PeriodicSpreadDiagnostics
    reciprocal_resolution: ReciprocalResolutionDiagnostic
    broadening_diagnostic: ArtificialBroadeningDiagnostic | None = None
    adaptive_target_width: float | None = None
    adaptive_target_achieved: bool | None = None

    @property
    def longest_grid_interval(self) -> float:
        return float(max(self.realized_intervals))


@dataclass(frozen=True, slots=True)
class AtomicDensityResolvedPlan:
    """Reusable numerical result from Phase-B atomic-density planning.

    The scene planner already resolves the expensive adaptive grid/bandwidth
    policy before backend selection.  Realization may consume this compact
    record instead of re-running the same spread diagnostics for the same
    field.  Coordinate samples are deliberately *not* retained here so the
    optimization does not increase the scene's peak sample-memory footprint.
    """

    field_key: str
    atom_indices: tuple[int, ...]
    label: str
    numerics: ResolvedDensityNumerics
    registration_signature: str
    options: AtomicDensityOptions


def _periodic_frechet_mean(
    fractional_samples: FloatArray,
    *,
    weights: FloatArray,
    cell: FloatArray,
    pbc: NDArray[np.bool_],
    tolerance: float = 1.0e-12,
    max_iterations: int = 64,
) -> FloatArray:
    """Compatibility wrapper around the LD0-R2 diagnostic mean solver."""

    del tolerance, max_iterations
    return periodic_frechet_mean_diagnostic(
        fractional_samples,
        weights=weights,
        cell=cell,
        pbc=pbc,
    ).mean_cartesian


def periodic_item_standard_deviations(
    fractional_by_frame: FloatArray,
    *,
    weights: FloatArray,
    cell: FloatArray,
    pbc: NDArray[np.bool_],
) -> FloatArray:
    """Return per-item isotropic Cartesian positional standard deviations.

    For item ``i``, the scalar spread is

    ``s_i = sqrt(trace(C_i) / 3)``,

    where ``C_i`` is the weighted covariance of minimum-image displacements
    from the item's periodic Fréchet mean.  This per-Cartesian-component scale
    is directly comparable to the isotropic Gaussian kernel bandwidth
    ``sigma``.  A convolution adds ``sigma**2`` to each component variance.
    """
    return periodic_item_spread_diagnostics(
        fractional_by_frame,
        weights=weights,
        cell=cell,
        pbc=pbc,
        quantile=0.10,
    ).standard_deviations


def _voxel_count(shape: tuple[int, int, int]) -> int:
    return int(shape[0]) * int(shape[1]) * int(shape[2])


def _finest_budgeted_grid_shape(
    cell: FloatArray,
    *,
    target_interval: float,
    nominal_interval: float,
    max_voxels: int,
) -> tuple[tuple[int, int, int], bool]:
    """Return the finest automatic shape not exceeding a voxel budget."""
    if target_interval > 0.0:
        target_shape = resolve_density_grid_shape(
            cell, grid_shape=None, grid_interval=target_interval
        )
        if _voxel_count(target_shape) <= max_voxels:
            return target_shape, False
    nominal_shape = resolve_density_grid_shape(
        cell, grid_shape=None, grid_interval=nominal_interval
    )
    if _voxel_count(nominal_shape) > max_voxels:
        raise GraphComplexityError(
            f"The nominal density grid requires {_voxel_count(nominal_shape)} voxels, "
            f"exceeding the per-field voxel budget {max_voxels}."
        )
    low = max(0.0, float(target_interval))
    high = float(nominal_interval)
    for _ in range(80):
        middle = 0.5 * (low + high)
        shape = resolve_density_grid_shape(
            cell, grid_shape=None, grid_interval=middle
        )
        if _voxel_count(shape) > max_voxels:
            low = middle
        else:
            high = middle
    shape = resolve_density_grid_shape(cell, grid_shape=None, grid_interval=high)
    return shape, True



def _effective_sample_batch(
    fractional_by_frame: FloatArray,
    frame_weights: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    positions = np.asarray(fractional_by_frame, dtype=np.float64)
    weights = np.asarray(frame_weights, dtype=np.float64)
    if positions.ndim != 3 or positions.shape[2] != 3 or positions.shape[1] < 1:
        raise GraphAdapterError(
            "fractional_by_frame must have shape (n_frames, n_items, 3)."
        )
    if weights.shape != (positions.shape[0],):
        raise GraphAdapterError("frame_weights must align with fractional_by_frame.")
    return positions.reshape((-1, 3)), np.repeat(weights, positions.shape[1])


def _effective_target_tolerance(target_width: float) -> float:
    return 5.0e-13 * max(1.0, float(target_width))


def _representative_interval_for_shape(
    cell: FloatArray,
    shape: tuple[int, int, int],
) -> float:
    lengths = np.linalg.norm(np.asarray(cell, dtype=np.float64), axis=1)
    lower = float(np.max(lengths / np.asarray(shape, dtype=np.float64)))
    upper_values = [
        float(lengths[index] / (shape[index] - 1))
        for index in range(3)
        if shape[index] > 4
    ]
    upper = min(upper_values) if upper_values else max(1.0, lower * 2.0)
    if upper <= lower:
        return float(np.nextafter(lower, np.inf))
    return 0.5 * (lower + upper)


def _next_finer_interval(
    cell: FloatArray,
    shape: tuple[int, int, int],
    current_interval: float,
) -> float:
    lengths = np.linalg.norm(np.asarray(cell, dtype=np.float64), axis=1)
    thresholds = lengths / np.asarray(shape, dtype=np.float64)
    candidates = thresholds[thresholds <= current_interval * (1.0 + 1.0e-14)]
    if candidates.size == 0:
        return 0.9 * current_interval
    threshold = float(np.max(candidates))
    result = float(np.nextafter(threshold, 0.0))
    if result <= 0.0 or result >= current_interval:
        result = 0.9 * current_interval
    return result


def _resolve_effective_density_numerics(
    cell: FloatArray,
    *,
    options: AtomicDensityOptions,
    fractional_by_frame: FloatArray,
    frame_weights: FloatArray,
    pbc: NDArray[np.bool_],
    max_voxels: int,
    field_label: str,
) -> ResolvedDensityNumerics:
    """Resolve ``effective_cic_stencil_rms_v1`` without changing legacy policy."""

    matrix = np.asarray(cell, dtype=np.float64)
    weights = np.asarray(frame_weights, dtype=np.float64)
    if max_voxels < 64:
        raise GraphComplexityError("A density field requires at least 4^3 voxels.")
    spread = periodic_item_spread_diagnostics(
        fractional_by_frame,
        weights=weights,
        cell=matrix,
        pbc=pbc,
        quantile=options.sample_sd_quantile,
        sample_size=options.spread_sample_size,
        sample_seed=options.spread_sample_seed,
        sampling_strategy=options.spread_sampling_strategy,
        replicate_count=options.spread_replicate_count,
        max_replicate_count=options.spread_max_replicate_count,
        convergence_relative_tolerance=options.spread_convergence_relative_tolerance,
        basin_mode=options.spread_basin_mode,
    )
    item_sds = spread.standard_deviations
    reference_sd = spread.reference_standard_deviation
    if (
        options.adaptive_smearing
        and fractional_by_frame.shape[0] >= 2
        and spread.insufficient_valid_reference
    ):
        warnings.warn(
            f"Automatic density refinement for {field_label!r} was disabled because "
            f"only {spread.valid_reference_count} of {spread.total_item_count} "
            "periodic means were converged and unambiguous; "
            f"{spread.required_reference_count} valid items are required.",
            RuntimeWarning,
            stacklevel=3,
        )
    elif (
        options.adaptive_smearing
        and reference_sd is not None
        and not spread.adaptive_target_defined
    ):
        warnings.warn(
            f"Automatic density refinement for {field_label!r} has no finite "
            "positive target because the valid reference positional spread is "
            "zero. Nominal or explicit resolution was retained.",
            RuntimeWarning,
            stacklevel=3,
        )

    flat_positions, sample_weights = _effective_sample_batch(
        fractional_by_frame, weights
    )
    target_width = (
        options.max_smearing_to_sample_sd_ratio * float(reference_sd)
        if spread.adaptive_target_defined and reference_sd is not None
        else None
    )
    target_tolerance = (
        None if target_width is None else _effective_target_tolerance(target_width)
    )
    cache: dict[
        tuple[tuple[int, int, int], float],
        tuple[
            tuple[float, float, float],
            ArtificialBroadeningDiagnostic,
        ],
    ] = {}

    def evaluate(
        shape: tuple[int, int, int], bandwidth: float
    ) -> tuple[tuple[float, float, float], ArtificialBroadeningDiagnostic]:
        key = (shape, float(bandwidth))
        cached = cache.get(key)
        if cached is not None:
            return cached
        realized = density_grid_intervals(matrix, shape)
        diagnostic = effective_artificial_broadening(
            flat_positions,
            sample_weights,
            shape,
            matrix,
            bandwidth,
            kernel_tail_tolerance=options.kernel_options.kernel_tail_tolerance,
            metadata={"field_label": field_label},
        )
        result = (realized, diagnostic)
        cache[key] = result
        return result

    def achieved(diagnostic: ArtificialBroadeningDiagnostic) -> bool | None:
        if target_width is None or target_tolerance is None:
            return None
        return bool(diagnostic.effective_rms <= target_width + target_tolerance)

    if options.grid_shape is not None:
        shape = tuple(int(v) for v in options.grid_shape)
        if _voxel_count(shape) > max_voxels:
            raise GraphComplexityError(
                f"The explicit density grid for {field_label!r} requires "
                f"{_voxel_count(shape)} voxels, exceeding the per-field "
                f"max_density_voxels budget {max_voxels}."
            )
        realized = density_grid_intervals(matrix, shape)
        bandwidth = (
            float(options.gaussian_bandwidth)
            if options.gaussian_bandwidth is not None
            else options.gaussian_to_grid_ratio * max(realized)
        )
        realized, diagnostic = evaluate(shape, bandwidth)
        target_achieved = achieved(diagnostic)
        if options.adaptive_smearing and target_achieved is False:
            warnings.warn(
                f"The effective CIC-plus-stencil width for {field_label!r} "
                "exceeds the positional-spread target, but grid_shape was "
                "explicitly fixed; automatic refinement was not applied. "
                f"s_art={diagnostic.effective_rms:.6g} A, "
                f"target={target_width:.6g} A.",
                RuntimeWarning,
                stacklevel=3,
            )
        return ResolvedDensityNumerics(
            grid_shape=shape,
            realized_intervals=realized,
            gaussian_bandwidth=bandwidth,
            sample_standard_deviations=tuple(float(v) for v in item_sds),
            sample_sd_reference=reference_sd,
            adaptive_triggered=False,
            adaptive_budget_limited=False,
            adaptive_target_defined=spread.adaptive_target_defined,
            smearing_definition=(
                "explicit_bandwidth_effective"
                if options.gaussian_bandwidth is not None
                else "grid_ratio_explicit_shape_effective"
            ),
            spread_diagnostics=spread,
            reciprocal_resolution=reciprocal_resolution_diagnostic(matrix, shape),
            broadening_diagnostic=diagnostic,
            adaptive_target_width=target_width,
            adaptive_target_achieved=target_achieved,
        )

    nominal_shape = resolve_density_grid_shape(
        matrix, grid_shape=None, grid_interval=options.grid_interval
    )
    if _voxel_count(nominal_shape) > max_voxels:
        raise GraphComplexityError(
            f"The nominal density grid for {field_label!r} requires "
            f"{_voxel_count(nominal_shape)} voxels, exceeding the per-field "
            f"max_density_voxels budget {max_voxels}."
        )
    nominal_realized = density_grid_intervals(matrix, nominal_shape)
    if options.gaussian_bandwidth is not None:
        bandwidth = float(options.gaussian_bandwidth)
        nominal_realized, diagnostic = evaluate(nominal_shape, bandwidth)
        target_achieved = achieved(diagnostic)
        if options.adaptive_smearing and target_achieved is False:
            warnings.warn(
                f"The effective CIC-plus-stencil width for {field_label!r} "
                "exceeds the positional-spread target; explicit "
                "gaussian_bandwidth was preserved. "
                f"s_art={diagnostic.effective_rms:.6g} A, "
                f"target={target_width:.6g} A.",
                RuntimeWarning,
                stacklevel=3,
            )
        return ResolvedDensityNumerics(
            grid_shape=nominal_shape,
            realized_intervals=nominal_realized,
            gaussian_bandwidth=bandwidth,
            sample_standard_deviations=tuple(float(v) for v in item_sds),
            sample_sd_reference=reference_sd,
            adaptive_triggered=False,
            adaptive_budget_limited=False,
            adaptive_target_defined=spread.adaptive_target_defined,
            smearing_definition="explicit_bandwidth_effective",
            spread_diagnostics=spread,
            reciprocal_resolution=reciprocal_resolution_diagnostic(
                matrix, nominal_shape
            ),
            broadening_diagnostic=diagnostic,
            adaptive_target_width=target_width,
            adaptive_target_achieved=target_achieved,
        )

    nominal_bandwidth = options.gaussian_to_grid_ratio * max(nominal_realized)
    nominal_realized, nominal_diagnostic = evaluate(
        nominal_shape, nominal_bandwidth
    )
    nominal_achieved = achieved(nominal_diagnostic)
    triggered = bool(options.adaptive_smearing and nominal_achieved is False)
    if not triggered:
        return ResolvedDensityNumerics(
            grid_shape=nominal_shape,
            realized_intervals=nominal_realized,
            gaussian_bandwidth=nominal_bandwidth,
            sample_standard_deviations=tuple(float(v) for v in item_sds),
            sample_sd_reference=reference_sd,
            adaptive_triggered=False,
            adaptive_budget_limited=False,
            adaptive_target_defined=spread.adaptive_target_defined,
            smearing_definition="grid_ratio_effective",
            spread_diagnostics=spread,
            reciprocal_resolution=reciprocal_resolution_diagnostic(
                matrix, nominal_shape
            ),
            broadening_diagnostic=nominal_diagnostic,
            adaptive_target_width=target_width,
            adaptive_target_achieved=nominal_achieved,
        )

    assert target_width is not None and target_tolerance is not None
    fail_interval = float(options.grid_interval)
    fail_shape = nominal_shape
    fail_diagnostic = nominal_diagnostic
    current_interval = fail_interval
    pass_interval: float | None = None
    pass_shape: tuple[int, int, int] | None = None
    pass_realized: tuple[float, float, float] | None = None
    pass_bandwidth: float | None = None
    pass_diagnostic: ArtificialBroadeningDiagnostic | None = None
    budget_limited = False

    for _ in range(128):
        scale = min(
            0.9,
            max(0.05, 0.98 * target_width / fail_diagnostic.effective_rms),
        )
        proposal_interval = current_interval * scale
        proposal_shape = resolve_density_grid_shape(
            matrix, grid_shape=None, grid_interval=proposal_interval
        )
        if proposal_shape == fail_shape:
            proposal_interval = _next_finer_interval(
                matrix, fail_shape, current_interval
            )
            proposal_shape = resolve_density_grid_shape(
                matrix, grid_shape=None, grid_interval=proposal_interval
            )
        if _voxel_count(proposal_shape) > max_voxels:
            finest_shape, _ = _finest_budgeted_grid_shape(
                matrix,
                target_interval=0.0,
                nominal_interval=options.grid_interval,
                max_voxels=max_voxels,
            )
            finest_interval = _representative_interval_for_shape(
                matrix, finest_shape
            )
            finest_realized = density_grid_intervals(matrix, finest_shape)
            finest_bandwidth = options.gaussian_to_grid_ratio * max(finest_realized)
            finest_realized, finest_diagnostic = evaluate(
                finest_shape, finest_bandwidth
            )
            if finest_diagnostic.effective_rms <= target_width + target_tolerance:
                pass_interval = finest_interval
                pass_shape = finest_shape
                pass_realized = finest_realized
                pass_bandwidth = finest_bandwidth
                pass_diagnostic = finest_diagnostic
            else:
                budget_limited = True
                pass_interval = finest_interval
                pass_shape = finest_shape
                pass_realized = finest_realized
                pass_bandwidth = finest_bandwidth
                pass_diagnostic = finest_diagnostic
            break
        proposal_realized = density_grid_intervals(matrix, proposal_shape)
        proposal_bandwidth = options.gaussian_to_grid_ratio * max(proposal_realized)
        proposal_realized, proposal_diagnostic = evaluate(
            proposal_shape, proposal_bandwidth
        )
        if proposal_diagnostic.effective_rms <= target_width + target_tolerance:
            pass_interval = proposal_interval
            pass_shape = proposal_shape
            pass_realized = proposal_realized
            pass_bandwidth = proposal_bandwidth
            pass_diagnostic = proposal_diagnostic
            break
        fail_interval = proposal_interval
        fail_shape = proposal_shape
        fail_diagnostic = proposal_diagnostic
        current_interval = proposal_interval
    else:
        raise GraphComplexityError(
            "Effective broadening refinement did not converge within 128 steps."
        )

    assert (
        pass_interval is not None
        and pass_shape is not None
        and pass_realized is not None
        and pass_bandwidth is not None
        and pass_diagnostic is not None
    )
    if not budget_limited:
        for _ in range(60):
            middle = 0.5 * (pass_interval + fail_interval)
            middle_shape = resolve_density_grid_shape(
                matrix, grid_shape=None, grid_interval=middle
            )
            middle_realized = density_grid_intervals(matrix, middle_shape)
            middle_bandwidth = options.gaussian_to_grid_ratio * max(middle_realized)
            middle_realized, middle_diagnostic = evaluate(
                middle_shape, middle_bandwidth
            )
            if middle_diagnostic.effective_rms <= target_width + target_tolerance:
                pass_interval = middle
                pass_shape = middle_shape
                pass_realized = middle_realized
                pass_bandwidth = middle_bandwidth
                pass_diagnostic = middle_diagnostic
            else:
                fail_interval = middle
            if middle_shape == pass_shape and middle_shape == fail_shape:
                break

    target_achieved = bool(
        pass_diagnostic.effective_rms <= target_width + target_tolerance
    )
    if not target_achieved:
        budget_limited = True
    detail = (
        " The requested effective-width criterion could not be reached within "
        f"the per-field voxel budget {max_voxels}."
        if budget_limited
        else ""
    )
    warnings.warn(
        f"Adaptive density refinement was triggered for {field_label!r}: "
        f"nominal effective artificial RMS={nominal_diagnostic.effective_rms:.6g} A "
        f"exceeds target={target_width:.6g} A. The resolved grid is "
        f"{pass_shape} with s_art={pass_diagnostic.effective_rms:.6g} A "
        f"(s_art/SD={pass_diagnostic.effective_rms / float(reference_sd):.3f})."
        f"{detail}",
        RuntimeWarning,
        stacklevel=3,
    )
    return ResolvedDensityNumerics(
        grid_shape=pass_shape,
        realized_intervals=pass_realized,
        gaussian_bandwidth=pass_bandwidth,
        sample_standard_deviations=tuple(float(v) for v in item_sds),
        sample_sd_reference=reference_sd,
        adaptive_triggered=True,
        adaptive_budget_limited=budget_limited,
        adaptive_target_defined=spread.adaptive_target_defined,
        smearing_definition="adaptive_grid_ratio_effective",
        spread_diagnostics=spread,
        reciprocal_resolution=reciprocal_resolution_diagnostic(matrix, pass_shape),
        broadening_diagnostic=pass_diagnostic,
        adaptive_target_width=target_width,
        adaptive_target_achieved=target_achieved,
    )


def resolve_density_numerics(
    cell: FloatArray,
    *,
    options: AtomicDensityOptions,
    fractional_by_frame: FloatArray,
    frame_weights: FloatArray,
    pbc: NDArray[np.bool_],
    max_voxels: int,
    field_label: str,
) -> ResolvedDensityNumerics:
    """Resolve the grid and kernel, including bounded spread-aware refinement."""
    if (
        options.resolution_options.broadening_metric
        == EFFECTIVE_CIC_STENCIL_BROADENING
    ):
        return _resolve_effective_density_numerics(
            cell,
            options=options,
            fractional_by_frame=fractional_by_frame,
            frame_weights=frame_weights,
            pbc=pbc,
            max_voxels=max_voxels,
            field_label=field_label,
        )
    matrix = np.asarray(cell, dtype=np.float64)
    weights = np.asarray(frame_weights, dtype=np.float64)
    if max_voxels < 64:
        raise GraphComplexityError("A density field requires at least 4^3 voxels.")
    spread = periodic_item_spread_diagnostics(
        fractional_by_frame,
        weights=weights,
        cell=matrix,
        pbc=pbc,
        quantile=options.sample_sd_quantile,
        sample_size=options.spread_sample_size,
        sample_seed=options.spread_sample_seed,
        sampling_strategy=options.spread_sampling_strategy,
        replicate_count=options.spread_replicate_count,
        max_replicate_count=options.spread_max_replicate_count,
        convergence_relative_tolerance=options.spread_convergence_relative_tolerance,
        basin_mode=options.spread_basin_mode,
    )
    item_sds = spread.standard_deviations
    reference_sd = spread.reference_standard_deviation
    if (
        options.adaptive_smearing
        and fractional_by_frame.shape[0] >= 2
        and spread.insufficient_valid_reference
    ):
        warnings.warn(
            f"Automatic density refinement for {field_label!r} was disabled because "
            f"only {spread.valid_reference_count} of {spread.total_item_count} "
            "periodic means were converged and unambiguous; "
            f"{spread.required_reference_count} valid items are required.",
            RuntimeWarning,
            stacklevel=3,
        )
    elif (
        options.adaptive_smearing
        and reference_sd is not None
        and not spread.adaptive_target_defined
    ):
        warnings.warn(
            f"Automatic density refinement for {field_label!r} has no finite "
            "positive target because the valid reference positional spread is "
            "zero. Nominal or explicit resolution was retained.",
            RuntimeWarning,
            stacklevel=3,
        )

    if options.grid_shape is not None:
        shape = tuple(int(v) for v in options.grid_shape)
        if _voxel_count(shape) > max_voxels:
            raise GraphComplexityError(
                f"The explicit density grid for {field_label!r} requires "
                f"{_voxel_count(shape)} voxels, exceeding the per-field max_density_voxels budget "
                f"{max_voxels}."
            )
        realized = density_grid_intervals(matrix, shape)
        bandwidth = (
            float(options.gaussian_bandwidth)
            if options.gaussian_bandwidth is not None
            else options.gaussian_to_grid_ratio * max(realized)
        )
        if (
            options.adaptive_smearing
            and spread.adaptive_target_defined
            and reference_sd is not None
            and bandwidth
            > options.max_smearing_to_sample_sd_ratio * reference_sd
        ):
            warnings.warn(
                f"The Gaussian bandwidth for {field_label!r} is comparable to or "
                "larger than the measured positional spread, but grid_shape was "
                "explicitly fixed; automatic refinement was not applied. "
                f"sigma={bandwidth:.6g} A, reference SD={reference_sd:.6g} A.",
                RuntimeWarning,
                stacklevel=3,
            )
        return ResolvedDensityNumerics(
            grid_shape=shape,
            realized_intervals=realized,
            gaussian_bandwidth=bandwidth,
            sample_standard_deviations=tuple(float(v) for v in item_sds),
            sample_sd_reference=reference_sd,
            adaptive_triggered=False,
            adaptive_budget_limited=False,
            adaptive_target_defined=spread.adaptive_target_defined,
            smearing_definition=(
                "explicit_bandwidth"
                if options.gaussian_bandwidth is not None
                else "grid_ratio_explicit_shape"
            ),
            spread_diagnostics=spread,
            reciprocal_resolution=reciprocal_resolution_diagnostic(matrix, shape),
        )

    nominal_shape = resolve_density_grid_shape(
        matrix, grid_shape=None, grid_interval=options.grid_interval
    )
    if _voxel_count(nominal_shape) > max_voxels:
        raise GraphComplexityError(
            f"The nominal density grid for {field_label!r} requires "
            f"{_voxel_count(nominal_shape)} voxels, exceeding the per-field max_density_voxels budget "
            f"{max_voxels}."
        )
    nominal_realized = density_grid_intervals(matrix, nominal_shape)
    if options.gaussian_bandwidth is not None:
        bandwidth = float(options.gaussian_bandwidth)
        if (
            options.adaptive_smearing
            and spread.adaptive_target_defined
            and reference_sd is not None
            and bandwidth
            > options.max_smearing_to_sample_sd_ratio * reference_sd
        ):
            warnings.warn(
                f"The explicit Gaussian bandwidth for {field_label!r} is comparable "
                "to or larger than the measured positional spread; explicit "
                "gaussian_bandwidth was preserved. "
                f"sigma={bandwidth:.6g} A, reference SD={reference_sd:.6g} A.",
                RuntimeWarning,
                stacklevel=3,
            )
        return ResolvedDensityNumerics(
            grid_shape=nominal_shape,
            realized_intervals=nominal_realized,
            gaussian_bandwidth=bandwidth,
            sample_standard_deviations=tuple(float(v) for v in item_sds),
            sample_sd_reference=reference_sd,
            adaptive_triggered=False,
            adaptive_budget_limited=False,
            adaptive_target_defined=spread.adaptive_target_defined,
            smearing_definition="explicit_bandwidth",
            spread_diagnostics=spread,
            reciprocal_resolution=reciprocal_resolution_diagnostic(
                matrix, nominal_shape
            ),
        )

    nominal_bandwidth = options.gaussian_to_grid_ratio * max(nominal_realized)
    triggered = bool(
        options.adaptive_smearing
        and spread.adaptive_target_defined
        and reference_sd is not None
        and nominal_bandwidth
        > options.max_smearing_to_sample_sd_ratio * reference_sd
    )
    shape = nominal_shape
    budget_limited = False
    if triggered:
        target_bandwidth = (
            options.max_smearing_to_sample_sd_ratio * float(reference_sd)
        )
        target_interval = (
            target_bandwidth / options.gaussian_to_grid_ratio
            if target_bandwidth > 0.0
            else 0.0
        )
        shape, budget_limited = _finest_budgeted_grid_shape(
            matrix,
            target_interval=target_interval,
            nominal_interval=options.grid_interval,
            max_voxels=max_voxels,
        )
    realized = density_grid_intervals(matrix, shape)
    bandwidth = options.gaussian_to_grid_ratio * max(realized)
    if triggered:
        residual_ratio = (
            bandwidth / float(reference_sd)
            if float(reference_sd) > 0.0
            else float("inf")
        )
        detail = (
            " The requested spread criterion could not be reached within the "
            f"per-field voxel budget {max_voxels}."
            if budget_limited
            else ""
        )
        warnings.warn(
            f"Adaptive density refinement was triggered for {field_label!r}: "
            f"nominal sigma={nominal_bandwidth:.6g} A is large relative to the "
            f"reference positional SD={reference_sd:.6g} A. The resolved grid is "
            f"{shape} with sigma={bandwidth:.6g} A "
            f"(sigma/SD={residual_ratio:.3f}).{detail}",
            RuntimeWarning,
            stacklevel=3,
        )
    return ResolvedDensityNumerics(
        grid_shape=shape,
        realized_intervals=realized,
        gaussian_bandwidth=bandwidth,
        sample_standard_deviations=tuple(float(v) for v in item_sds),
        sample_sd_reference=reference_sd,
        adaptive_triggered=triggered,
        adaptive_budget_limited=budget_limited,
        adaptive_target_defined=spread.adaptive_target_defined,
        smearing_definition=(
            "adaptive_grid_ratio" if triggered else "grid_ratio"
        ),
        spread_diagnostics=spread,
        reciprocal_resolution=reciprocal_resolution_diagnostic(matrix, shape),
    )

def resolve_density_grid_shape(
    cell: FloatArray,
    *,
    grid_shape: tuple[int, int, int] | None,
    grid_interval: float,
) -> tuple[int, int, int]:
    """Resolve a periodic grid from an explicit shape or target edge interval.

    The display-cell vectors are stored as rows.  In automatic mode, axis
    ``i`` receives ``ceil(|a_i| / h)`` intervals, where ``h`` is the requested
    ``grid_interval``.  Therefore every lattice-grid edge has Euclidean length
    no greater than the requested interval, including for oblique cells.
    """
    matrix = np.asarray(cell, dtype=np.float64)
    if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
        raise GraphAdapterError("display_cell must be a finite 3x3 matrix.")
    if abs(float(np.linalg.det(matrix))) <= 1.0e-12:
        raise GraphAdapterError("display_cell must be nonsingular.")
    if grid_shape is not None:
        return tuple(int(v) for v in grid_shape)
    interval = float(grid_interval)
    if not np.isfinite(interval) or interval <= 0.0:
        raise GraphStyleError("grid_interval must be finite and positive.")
    lengths = np.linalg.norm(matrix, axis=1)
    if np.any(lengths <= 0.0):
        raise GraphAdapterError("display_cell vectors must have positive length.")
    resolved = tuple(
        max(4, int(np.ceil(float(length) / interval - 1.0e-12)))
        for length in lengths
    )
    return resolved


def density_grid_intervals(
    cell: FloatArray, shape: tuple[int, int, int]
) -> tuple[float, float, float]:
    """Return realized Euclidean lattice-grid edge lengths in angstrom."""
    matrix = np.asarray(cell, dtype=np.float64)
    counts = np.asarray(shape, dtype=np.float64)
    return tuple(float(v) for v in np.linalg.norm(matrix, axis=1) / counts)


def _density_resolution_ratio(
    cell: FloatArray, shape: tuple[int, int, int], sigma: float
) -> float:
    """Return Gaussian bandwidth divided by the longest lattice-grid edge."""
    bandwidth = float(sigma)
    if bandwidth <= 0.0:
        return float("inf")
    steps = np.asarray(cell, dtype=np.float64) / np.asarray(shape, dtype=np.float64)[:, None]
    longest = float(np.max(np.linalg.norm(steps, axis=1)))
    if longest <= 0.0:
        return float("inf")
    return bandwidth / longest


def _warn_if_underresolved_density_grid(
    cell: FloatArray, shape: tuple[int, int, int], sigma: float
) -> float:
    """Warn when a Gaussian shell is too narrow for the oblique voxel grid."""
    ratio = _density_resolution_ratio(cell, shape, sigma)
    if np.isfinite(ratio) and ratio < 1.5:
        warnings.warn(
            "The Gaussian density bandwidth is under-resolved by the periodic "
            f"grid (sigma / longest_grid_edge = {ratio:.3f} < 1.5). "
            "Marching-cubes shells may appear systematically elliptical, "
            "especially in oblique cells. Decrease grid_interval, increase an "
            "explicit grid_shape, and/or increase gaussian_bandwidth.",
            RuntimeWarning,
            stacklevel=3,
        )
    return ratio


def _deposit_cic(fractional: FloatArray, sample_weights: FloatArray, shape: tuple[int, int, int]) -> FloatArray:
    _budget, time_model, _derived = resolve_density_resource_limits()
    cpu_estimate = (
        8.0 * float(np.asarray(fractional).shape[0])
        / max(1.0, float(time_model.direct_reduction_pairs_per_second))
    )
    gpu_grid = try_gpu_cic_deposition(
        fractional, sample_weights, shape, cpu_estimate_seconds=cpu_estimate
    )
    if gpu_grid is not None:
        return gpu_grid
    grid = np.zeros(shape, dtype=np.float64)
    scale = np.asarray(shape, dtype=np.float64)
    scaled = fractional * scale
    base = np.floor(scaled).astype(np.int64)
    delta = scaled - base
    for ox in (0, 1):
        wx = (1.0 - delta[:, 0]) if ox == 0 else delta[:, 0]
        ix = (base[:, 0] + ox) % shape[0]
        for oy in (0, 1):
            wy = (1.0 - delta[:, 1]) if oy == 0 else delta[:, 1]
            iy = (base[:, 1] + oy) % shape[1]
            for oz in (0, 1):
                wz = (1.0 - delta[:, 2]) if oz == 0 else delta[:, 2]
                iz = (base[:, 2] + oz) % shape[2]
                np.add.at(grid, (ix, iy, iz), sample_weights * wx * wy * wz)
    return grid


def _periodic_gaussian(mass_grid: FloatArray, cell: FloatArray, sigma: float) -> FloatArray:
    """Compatibility wrapper for the historical legacy spectral operator."""

    smoothed, _ = smooth_periodic_node_masses(
        mass_grid,
        cell,
        sigma,
        DensityKernelOptions(smoothing_operator=LEGACY_SPECTRAL_OPERATOR),
    )
    return smoothed



def _planning_execution_journal_metadata(
    planning_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract execution-only Phase-B estimates for PAR-DENS6 telemetry."""

    planning = planning_metadata.get("density_planning")
    if not isinstance(planning, Mapping):
        return {}
    phase_b = planning.get("phase_b")
    if not isinstance(phase_b, Mapping):
        return {}
    metadata = phase_b.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key in (
        "backend",
        "phase_b_execution_planner",
        "hybrid_compute_tile_count",
        "hybrid_direct_tile_count",
        "hybrid_fft_tile_count",
        "direct_pair_count",
        "fft_padded_node_count",
        "hybrid_estimated_wall_seconds",
        "hybrid_predicted_peak_bytes",
        "hybrid_plan_identity",
    ):
        if key in metadata:
            result[key] = metadata[key]
    return result


def _planned_backend_from_metadata(
    planning_metadata: Mapping[str, Any],
) -> tuple[str | None, Mapping[str, Any] | None]:
    planning = planning_metadata.get("density_planning")
    if not isinstance(planning, Mapping):
        return None, None
    phase_b = planning.get("phase_b")
    if not isinstance(phase_b, Mapping):
        return None, None
    metadata = phase_b.get("metadata")
    if not isinstance(metadata, Mapping):
        return None, None
    backend = metadata.get("backend")
    selection = metadata.get("backend_selection")
    return (
        None if backend is None else str(backend),
        selection if isinstance(selection, Mapping) else None,
    )



def _aggregate_sparse_cic_for_options(
    samples: PeriodicWeightedSamples3D,
    grid_shape: tuple[int, int, int],
    *,
    options: AtomicDensityOptions,
    max_cic_contributions: int,
    max_workspace_bytes: int,
):
    if options.optimization_options.sparse_evaluation_mode == "reference":
        return aggregate_periodic_cic_sparse(
            samples,
            grid_shape,
            max_cic_contributions=max_cic_contributions,
            max_workspace_bytes=max_workspace_bytes,
        )
    return aggregate_periodic_cic_sparse_optimized(
        samples,
        grid_shape,
        max_cic_contributions=max_cic_contributions,
        max_workspace_bytes=max_workspace_bytes,
    )


def _stencil_support_for_options(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    options: AtomicDensityOptions,
    max_candidate_contributions: int,
    max_workspace_bytes: int,
):
    return get_periodic_gaussian_stencil_support(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=options.kernel_options.kernel_tail_tolerance,
        max_candidate_contributions=max_candidate_contributions,
        max_workspace_bytes=max_workspace_bytes,
        use_cache=(
            options.optimization_options.sparse_evaluation_mode == "optimized"
            and options.optimization_options.cache_stencil_supports
        ),
    )


def _prepare_sparse_reference_for_options(
    samples: PeriodicWeightedSamples3D,
    *,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    options: AtomicDensityOptions,
    max_cic_contributions: int,
    max_kernel_pairs: int,
    max_workspace_bytes: int,
):
    if options.optimization_options.sparse_evaluation_mode == "reference":
        return prepare_sparse_canonical_density_reference(
            samples,
            grid_shape=grid_shape,
            display_cell=display_cell,
            gaussian_bandwidth=gaussian_bandwidth,
            field_key=field_key,
            label=label,
            physical_units=physical_units,
            broadening_metric=broadening_metric,
            kernel_tail_tolerance=options.kernel_options.kernel_tail_tolerance,
            max_cic_contributions=max_cic_contributions,
            max_kernel_pairs=max_kernel_pairs,
            max_workspace_bytes=max_workspace_bytes,
        )
    return prepare_sparse_canonical_density_optimized(
        samples,
        grid_shape=grid_shape,
        display_cell=display_cell,
        gaussian_bandwidth=gaussian_bandwidth,
        field_key=field_key,
        label=label,
        physical_units=physical_units,
        broadening_metric=broadening_metric,
        kernel_tail_tolerance=options.kernel_options.kernel_tail_tolerance,
        pair_chunk_size=options.optimization_options.sparse_pair_chunk_size,
        block_shape=options.storage_options.local_block_shape,
        group_batch_size=options.optimization_options.sparse_group_batch_size,
        cache_stencil_supports=options.optimization_options.cache_stencil_supports,
        max_cic_contributions=max_cic_contributions,
        max_kernel_pairs=max_kernel_pairs,
        max_workspace_bytes=max_workspace_bytes,
    )



def _prepare_sparse_field_for_options(
    samples: PeriodicWeightedSamples3D,
    *,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    options: AtomicDensityOptions,
    selected_atom_indices: tuple[int, ...] = (),
    sample_positions: FloatArray | None = None,
    metadata: Mapping[str, Any] | None = None,
    max_cic_contributions: int,
    max_kernel_pairs: int,
    max_workspace_bytes: int,
    max_nonzero_nodes: int,
    max_stored_block_values: int,
    max_blocks: int,
    max_planning_bytes: int,
    approved_hybrid_plan: DensityHybridRealizationPlan | None = None,
    precomputed_hybrid_artifacts: tuple[Any, Any, Any, Any] | None = None,
    progress: ProgressPortLike | None = None,
) -> ScalarField3D:
    """Prepare one local-sparse field through the S4 production dispatcher.

    ``hybrid`` constructs the exact S1 support atlas and realizes values through
    S3.  A complexity or allocation failure may fall back to LD7 only when the
    explicit optimization option permits it.  Scientific or identity errors are
    never swallowed by the fallback.
    """

    common = {} if metadata is None else dict(metadata)

    def legacy(*, reason: str | None = None) -> ScalarField3D:
        reference = _prepare_sparse_reference_for_options(
            samples,
            grid_shape=grid_shape,
            display_cell=display_cell,
            gaussian_bandwidth=gaussian_bandwidth,
            field_key=field_key,
            label=label,
            physical_units=physical_units,
            broadening_metric=broadening_metric,
            options=options,
            max_cic_contributions=max_cic_contributions,
            max_kernel_pairs=max_kernel_pairs,
            max_workspace_bytes=max_workspace_bytes,
        )
        fallback_metadata: dict[str, Any] = {
            **common,
            "smoothing": "periodic_discrete_periodized_gaussian_sparse",
            "sparse_resolution_independent_of_dense_voxel_budget": True,
            "sparse_realization_backend": "ld7",
            "production_backend": options.optimization_options.sparse_realization_mode == "ld7",
        }
        if reason is not None:
            fallback_metadata.update({
                "ld8_s4_fallback_used": True,
                "ld8_s4_fallback_reason": reason,
            })
        return pack_sparse_reference_blocks(
            reference,
            block_shape=options.storage_options.local_block_shape,
            selected_atom_indices=selected_atom_indices,
            sample_positions=sample_positions,
            max_nonzero_nodes=max_nonzero_nodes,
            max_stored_block_values=max_stored_block_values,
            max_blocks=max_blocks,
            max_planning_bytes=max_planning_bytes,
            metadata=fallback_metadata,
        )

    if options.optimization_options.sparse_realization_mode == "ld7":
        return legacy()

    progress_port = resolve_progress_port(progress)
    reporter = ProgressEmitter(progress_port, source="plotting.atomic_density")
    sparse_started = time.perf_counter()
    try:
        if precomputed_hybrid_artifacts is not None:
            if len(precomputed_hybrid_artifacts) != 4:
                raise GraphAdapterError(
                    "precomputed_hybrid_artifacts must contain source, stencil, routing, and atlas."
                )
            source, stencil, routing, atlas = precomputed_hybrid_artifacts
            stencil_cache_hit = True
            routing_cache_hit = True
            reporter.completed(
                "sparse_field_preparation",
                f"{field_key}: reusing exact Phase-B CIC/stencil/routing/support atlas; "
                "no duplicate sparse planning",
                current=5,
                total=5,
                unit="steps",
                metadata={
                    "field_key": field_key,
                    "phase_b_runtime_artifacts_reused": True,
                },
            )
        else:
            reporter.started(
                "sparse_field_preparation",
                f"{field_key}: aggregating periodic CIC source from "
                f"{samples.fractional_positions.shape[0]} samples",
                current=0,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
            cic = _aggregate_sparse_cic_for_options(
                samples,
                grid_shape,
                options=options,
                max_cic_contributions=max_cic_contributions,
                max_workspace_bytes=max_planning_bytes,
            )
            reporter.update(
                "sparse_field_preparation",
                f"{field_key}: CIC source aggregated; resolving Gaussian stencil",
                current=1,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
            stencil, stencil_cache_hit = _stencil_support_for_options(
                grid_shape,
                display_cell,
                gaussian_bandwidth,
                options=options,
                max_candidate_contributions=max(64, max_kernel_pairs),
                max_workspace_bytes=max_planning_bytes,
            )
            reporter.update(
                "sparse_field_preparation",
                f"{field_key}: Gaussian stencil resolved ({stencil.active_flat_indices.size} offsets); "
                "packing positive CIC source",
                current=2,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
            source = pack_periodic_cic_source(
                cic, storage_block_shape=options.storage_options.local_block_shape
            )
            reporter.update(
                "sparse_field_preparation",
                f"{field_key}: packed {source.source_block_count} source blocks; resolving block routing",
                current=3,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
            routing, routing_cache_hit = get_periodic_kernel_block_routing(
                stencil,
                storage_block_shape=options.storage_options.local_block_shape,
                use_cache=options.optimization_options.cache_stencil_supports,
            )
            reporter.update(
                "sparse_field_preparation",
                f"{field_key}: routing resolved; constructing exact support atlas",
                current=4,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
            atlas = build_density_support_atlas(
                source,
                routing,
                progress=progress_port,
                field_key=field_key,
            )
            reporter.completed(
                "sparse_field_preparation",
                f"{field_key}: sparse pre-convolution preparation complete in "
                f"{time.perf_counter() - sparse_started:.1f} s",
                current=5,
                total=5,
                unit="steps",
                metadata={"field_key": field_key},
            )
        if approved_hybrid_plan is None:
            hybrid_options = DensityHybridExecutorOptions(
                executor_mode="auto",
                compute_tile_shape=options.optimization_options.hybrid_compute_tile_shape,
                pair_chunk_size=options.optimization_options.sparse_pair_chunk_size,
                min_fft_source_nodes=options.optimization_options.hybrid_min_fft_source_nodes,
                fft_workers=options.optimization_options.hybrid_fft_workers,
                cache_kernel_spectra=options.optimization_options.cache_stencil_supports,
                metadata={
                    "dispatch_stage": "ld8_s4",
                    "fft_worker_source": str(
                        options.optimization_options.metadata.get(
                            "hybrid_fft_workers_source", "explicit"
                        )
                    ),
                },
            )
            plan = plan_hybrid_tiled_realization(
                source, stencil, routing, atlas, options=hybrid_options
            )
            plan_authority = "realization_local_planning"
        else:
            # PAR-DENS6 freezes the direct-vs-FFT tile partition during the
            # scene-level Phase-B planning pass.  A live worker lease may
            # change how quickly an approved tile executes, but it must never
            # change which floating-point reduction path owns that tile.
            # Do not even rebuild live selector options here: calibration and
            # lease-local worker counts are execution facts, not replanning
            # authority.
            plan = approved_hybrid_plan
            plan_authority = "phase_b_approved_execution_plan"
        production_metadata = dict(common)
        density_planning = production_metadata.get("density_planning")
        if isinstance(density_planning, Mapping):
            planning_copy = dict(density_planning)
            phase_b = planning_copy.get("phase_b")
            if isinstance(phase_b, Mapping):
                phase_b_copy = dict(phase_b)
                packed_retained = int(
                    atlas.active_target_block_indices.nbytes
                    + atlas.target_support_bitsets.nbytes
                    + (atlas.target_block_count + 1) * np.dtype(np.int64).itemsize
                    + atlas.target_support_node_count * np.dtype(np.float64).itemsize
                    + 2 * atlas.target_block_count * np.dtype(np.float64).itemsize
                    + (0 if sample_positions is None else np.asarray(sample_positions).nbytes)
                )
                if (
                    str(phase_b_copy.get("metadata", {}).get("phase_b_execution_planner", ""))
                    == "ld8_s3_hybrid_exact_v1"
                ):
                    phase_b_copy["realized_target_node_count"] = atlas.target_support_node_count
                    phase_b_copy["realized_target_block_count"] = atlas.target_block_count
                    phase_b_copy["realized_retained_bytes"] = packed_retained
                    phase_b_copy["hybrid_phase_b_matches_realization"] = bool(
                        int(phase_b_copy.get("stored_value_count", -1))
                        == atlas.target_support_node_count
                        and int(phase_b_copy.get("stored_block_count", -1))
                        == atlas.target_block_count
                    )
                else:
                    phase_b_copy["planned_fixed_block_stored_value_count"] = phase_b_copy.get("stored_value_count")
                    phase_b_copy["stored_value_count"] = atlas.target_support_node_count
                    phase_b_copy["nonzero_node_count_upper"] = atlas.target_support_node_count
                    phase_b_copy["stored_block_count"] = atlas.target_block_count
                    phase_b_copy["planned_fixed_block_retained_bytes"] = phase_b_copy.get("retained_bytes")
                    phase_b_copy["retained_bytes"] = packed_retained
                phase_b_copy["realized_representation"] = "packed_positive_block_sparse"
                planning_copy["phase_b"] = phase_b_copy
                production_metadata["density_planning"] = planning_copy
        return realize_density_hybrid_tiled(
            source,
            stencil,
            routing,
            atlas,
            field_key=field_key,
            label=label,
            physical_units=physical_units,
            broadening_metric=broadening_metric,
            approved_plan=plan,
            selected_atom_indices=selected_atom_indices,
            sample_positions=sample_positions,
            production_backend=True,
            progress=progress_port,
            metadata={
                **production_metadata,
                "smoothing": "periodic_discrete_periodized_gaussian_sparse",
                "sparse_resolution_independent_of_dense_voxel_budget": True,
                "sparse_realization_backend": "ld8_s3_hybrid",
                "ld8_s4_normal_dispatch": True,
                "stencil_cache_hit": bool(stencil_cache_hit),
                "routing_cache_hit": bool(routing_cache_hit),
                "support_atlas_retained_bytes": atlas.retained_array_bytes,
                "hybrid_execution_plan_authority": plan_authority,
                "hybrid_execution_plan_identity": plan.content_identity,
            },
        )
    except (GraphComplexityError, MemoryError) as exc:
        if not options.optimization_options.allow_ld7_fallback:
            raise
        return legacy(reason=f"{type(exc).__name__}: {exc}")

def _select_atomic_auto_backend(
    samples: PeriodicWeightedSamples3D,
    *,
    field_key: str,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    options: AtomicDensityOptions,
    max_total_voxels: int,
    max_nonzero_nodes: int,
    max_stored_block_values: int,
    max_blocks: int,
    max_kernel_pairs: int,
    max_planning_bytes: int,
    max_workspace_bytes: int,
    max_cic_contributions: int,
) -> DensityBackendSelection:
    """Select a backend for a standalone atomic preparation before allocation."""

    logical = int(np.prod(grid_shape, dtype=object))
    sample_count = int(samples.fractional_positions.shape[0])
    dense_peak = max(
        dense_transient_bytes(logical, sample_count),
        dense_retained_bytes(
            logical,
            sample_count=sample_count,
            store_sample_positions=options.store_sample_positions,
        ),
    )
    dense_feasible = logical <= int(max_total_voxels) and dense_peak <= int(
        max_workspace_bytes
    )
    dense = DensityBackendCandidateEstimate(
        backend=DENSE_BACKEND,
        feasible=dense_feasible,
        logical_node_count=logical,
        active_node_count=logical,
        stored_value_count=logical,
        stored_block_count=0,
        kernel_pair_count=0,
        planning_bytes=0,
        retained_bytes=dense_retained_bytes(
            logical,
            sample_count=sample_count,
            store_sample_positions=options.store_sample_positions,
        ),
        estimated_peak_bytes=dense_peak,
        estimated_work=8 * sample_count
        + logical * max(1, int(np.ceil(np.log2(max(2, logical)))))
        + logical,
        infeasible_reason=(
            None
            if dense_feasible
            else "dense_voxel_or_peak_limit_exceeded"
        ),
    )
    sparse_error: str | None = None
    sparse: DensityBackendCandidateEstimate
    try:
        cic = _aggregate_sparse_cic_for_options(
            samples,
            grid_shape,
            options=options,
            max_cic_contributions=max_cic_contributions,
            max_workspace_bytes=max_planning_bytes,
        )
        support, _ = _stencil_support_for_options(
            grid_shape,
            display_cell,
            gaussian_bandwidth,
            options=options,
            max_candidate_contributions=max(64, max_stored_block_values * 64),
            max_workspace_bytes=max_planning_bytes,
        )
        batch_plan_metadata: Mapping[str, Any] = {}
        if options.optimization_options.sparse_evaluation_mode == "reference":
            targets = plan_sparse_target_nodes(
                cic,
                support,
                max_kernel_pairs=max_kernel_pairs,
                max_planning_bytes=max_planning_bytes,
            )
            pair_count = cic.occupied_node_count * support.stencil_offset_count
        else:
            targets, pair_count, frozen_batch_plan = (
                plan_group_batched_sparse_targets_optimized(
                    samples,
                    cic,
                    support,
                    pair_chunk_size=(
                        options.optimization_options.sparse_pair_chunk_size
                    ),
                    block_shape=options.storage_options.local_block_shape,
                    group_batch_size=(
                        options.optimization_options.sparse_group_batch_size
                    ),
                    max_cic_contributions=max_cic_contributions,
                    max_kernel_pairs=max_kernel_pairs,
                    max_planning_bytes=max_planning_bytes,
                )
            )
            batch_plan_metadata = frozen_batch_plan.to_json_dict()
        block_plan = plan_block_packing(
            targets,
            logical_grid_shape=grid_shape,
            block_shape=options.storage_options.local_block_shape,
            max_nonzero_nodes=max_nonzero_nodes,
            max_stored_block_values=max_stored_block_values,
            max_blocks=max_blocks,
            max_planning_bytes=max_planning_bytes,
        )
        planning_bytes = int(
            cic.flat_indices.nbytes
            + cic.node_masses.nbytes
            + support.active_flat_indices.nbytes
            + support.active_weights.nbytes
            + targets.nbytes
            + block_plan.active_block_indices.nbytes
            + block_plan.active_block_flat_indices.nbytes
        )
        mask_bytes = (
            block_plan.allocated_value_count
            if block_plan.partial_block_count
            else 0
        )
        retained = int(
            8 * block_plan.allocated_value_count
            + block_plan.active_block_indices.nbytes
            + mask_bytes
            + (24 * sample_count if options.store_sample_positions else 0)
        )
        if options.optimization_options.sparse_evaluation_mode == "optimized":
            peak_pairs = int(
                batch_plan_metadata.get("peak_batch_kernel_pair_count", pair_count)
            )
            chunk_pairs = min(
                peak_pairs,
                options.optimization_options.sparse_pair_chunk_size,
            )
            scatter_transient = int(
                104 * chunk_pairs
                + 8 * block_plan.allocated_value_count
                + 16 * targets.size
            )
        else:
            scatter_transient = int(16 * pair_count + 16 * targets.size)
        sparse_peak = int(planning_bytes + scatter_transient + retained)
        sparse_feasible = sparse_peak <= int(max_workspace_bytes)
        sparse = DensityBackendCandidateEstimate(
            backend=LOCAL_SPARSE_BACKEND,
            feasible=sparse_feasible,
            logical_node_count=logical,
            active_node_count=int(targets.size),
            stored_value_count=block_plan.allocated_value_count,
            stored_block_count=block_plan.active_block_count,
            kernel_pair_count=pair_count,
            planning_bytes=planning_bytes,
            retained_bytes=retained,
            estimated_peak_bytes=sparse_peak,
            estimated_work=8 * sample_count
            + pair_count
            + block_plan.allocated_value_count,
            infeasible_reason=(
                None if sparse_feasible else "sparse_peak_limit_exceeded"
            ),
        )
    except GraphComplexityError as exc:
        sparse_error = str(exc)
        sparse = DensityBackendCandidateEstimate(
            backend=LOCAL_SPARSE_BACKEND,
            feasible=False,
            logical_node_count=logical,
            active_node_count=0,
            stored_value_count=0,
            stored_block_count=0,
            kernel_pair_count=0,
            planning_bytes=0,
            retained_bytes=0,
            estimated_peak_bytes=0,
            estimated_work=0,
            infeasible_reason=sparse_error,
        )
    selected, reason = preferred_auto_backend(
        dense,
        sparse,
        sparse_activation_fraction=options.storage_options.sparse_activation_fraction,
    )
    return DensityBackendSelection(
        field_key=field_key,
        requested_backend=AUTO_BACKEND,
        selected_backend=selected,
        reason=reason,
        dense=dense,
        local_sparse=sparse,
    )

def prepare_atomic_density_fields(
    collection: AtomisticFrameCollection,
    *,
    frame_indices: Sequence[int],
    frame_weights: FloatArray,
    display_cell: FloatArray,
    registration_mode: str,
    framework_drift: FloatArray,
    registration_view: ConsumerCoordinateView | None = None,
    selections: Sequence[AtomicDensitySelection],
    options: AtomicDensityOptions,
    max_fields: int,
    max_total_voxels: int,
    max_samples: int,
    planning_metadata_by_field: Mapping[str, Mapping[str, Any]] | None = None,
    resolved_plans_by_field: Mapping[str, AtomicDensityResolvedPlan] | None = None,
    approved_hybrid_plans_by_field: Mapping[str, DensityHybridRealizationPlan] | None = None,
    precomputed_hybrid_artifacts_by_field: Mapping[str, tuple[Any, Any, Any, Any]] | None = None,
    max_nonzero_nodes: int | None = None,
    max_stored_block_values: int | None = None,
    max_blocks: int | None = None,
    max_kernel_pairs: int | None = None,
    max_planning_bytes: int | None = None,
    max_workspace_bytes: int | None = None,
    max_cic_contributions: int | None = None,
    field_index_offset: int = 0,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[ScalarField3D, ...]:
    """Prepare normalized atomic occupancy fields in the scene display cell.

    The dense path preserves the historical implementation.  Explicit
    ``grid_backend='local_sparse'`` uses the LD1-A canonical sparse oracle and
    packs it into :class:`PeriodicBlockScalarField3D` without allocating the
    logical dense field.
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
    reporter = ProgressEmitter(progress_port, source="plotting.atomic_density")
    if isinstance(field_index_offset, bool) or not isinstance(field_index_offset, (int, np.integer)):
        raise GraphStyleError("field_index_offset must be a nonnegative integer.")
    field_index_offset = int(field_index_offset)
    if field_index_offset < 0:
        raise GraphStyleError("field_index_offset must be a nonnegative integer.")
    if not selections:
        return ()
    if not np.all(collection.pbc):
        raise GraphAdapterError(
            "The atomic-density backend requires periodicity along all three axes."
        )
    if len(selections) > max_fields:
        raise GraphComplexityError(
            f"Requested {len(selections)} density fields, exceeding "
            f"max_density_fields={max_fields}."
        )
    cell = np.asarray(display_cell, dtype=np.float64)
    frames = tuple(int(v) for v in frame_indices)
    weights = np.asarray(frame_weights, dtype=np.float64)
    inverse_display = np.linalg.inv(display_cell)
    if registration_view is not None:
        if registration_view.metadata.get("consumer") != "plotting":
            raise GraphAdapterError(
                "Atomic density requires a plotting consumer coordinate view."
            )
        if registration_view.display_cell is None or not np.allclose(
            registration_view.display_cell,
            cell,
            rtol=0.0,
            atol=2.0e-12,
        ):
            raise GraphAdapterError(
                "Atomic-density display_cell disagrees with the registration view."
            )
        if str(registration_view.spatial_mode) != str(registration_mode):
            raise GraphAdapterError(
                "Atomic-density registration_mode disagrees with the registration view."
            )
    cell_equivalence: CellEquivalenceReport | None = None
    if registration_mode == "laboratory":
        cell_equivalence = require_equivalent_laboratory_density_cells(
            np.asarray(collection.cells[list(frames)], dtype=np.float64),
            display_cell,
            field_context="atomic density",
        )
    requested_backend = options.storage_options.grid_backend
    if (
        requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
        and options.kernel_options.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR
    ):
        raise GraphStyleError(
            "The local_sparse and auto atomic backends require "
            "discrete_periodized_v1."
        )
    per_field_voxel_budget = int(max_total_voxels) // len(selections)
    if requested_backend == DENSE_BACKEND and per_field_voxel_budget < 64:
        raise GraphComplexityError(
            "The total density voxel budget is too small to allocate a 4^3 grid "
            "to every requested dense field."
        )
    used_voxels = 0
    results: list[ScalarField3D] = []
    total_fields = len(selections)
    for local_field_index, selection in enumerate(selections):
        field_index = field_index_offset + local_field_index
        reporter.started(
            "field_realization",
            "resolving samples and numerical plan",
            current=local_field_index + 1,
            total=total_fields,
            unit="fields",
            metadata={"field_index": field_index, "field_key": f"atomic-density-{field_index}"},
        )
        field_key = f"atomic-density-{field_index}"
        field_stage_started = time.perf_counter()
        resolved_plan = (
            None
            if resolved_plans_by_field is None
            else resolved_plans_by_field.get(field_key)
        )
        atoms = selection.resolve(collection)
        if resolved_plan is not None:
            if tuple(atoms) != tuple(resolved_plan.atom_indices):
                raise GraphAdapterError(
                    f"Cached density plan for {field_key!r} disagrees with the "
                    "resolved atom selection."
                )
            if registration_view is None:
                raise GraphAdapterError(
                    f"Cached density plan for {field_key!r} requires the plotting "
                    "registration view used during Phase-B planning."
                )
            if str(registration_view.signature) != str(resolved_plan.registration_signature):
                raise GraphAdapterError(
                    f"Cached density plan for {field_key!r} has a stale registration "
                    "signature."
                )
            if resolved_plan.options != options:
                raise GraphAdapterError(
                    f"Cached density plan for {field_key!r} was resolved under "
                    "different density options."
                )
        sample_count = len(frames) * len(atoms)
        if sample_count > max_samples:
            raise GraphComplexityError(
                f"Density preparation requires {sample_count} samples, exceeding "
                f"max_density_samples={max_samples}."
            )
        if registration_view is not None:
            display_fractional = np.asarray(
                registration_view.display_fractional(
                    frame_indices=frames, atom_indices=atoms
                ),
                dtype=np.float64,
            )
        else:
            fractional = np.asarray(
                collection.fractional_positions[np.ix_(frames, atoms)], dtype=np.float64
            )
            if registration_mode == "framework_registered":
                fractional = fractional - framework_drift[:, None, :]
            if registration_mode == "laboratory":
                frame_cells = np.asarray(collection.cells[list(frames)], dtype=np.float64)
                cartesian = fractional @ frame_cells
                display_fractional = cartesian @ inverse_display
            else:
                display_fractional = fractional

        label = None if resolved_plan is None else resolved_plan.label
        if label is None:
            label = selection.label
        if label is None:
            if len(atoms) == 1:
                label = f"atom {atoms[0]} density"
            elif len(selection.species) == 1 and not selection.atom_indices:
                selector = selection.species[0]
                number = (
                    int(selector)
                    if isinstance(selector, int)
                    else ase_atomic_numbers[selector]
                )
                label = f"{chemical_symbols[number]} density"
            else:
                label = f"atomic density {field_index + 1}"

        record_density_stage_timing(
            field_key=field_key,
            stage="preprocessing",
            wall_seconds=time.perf_counter() - field_stage_started,
            metadata={"frame_count": len(frames), "atom_count": len(atoms)},
        )
        planning_stage_started = time.perf_counter()

        # Sparse resolution is independent of the dense scalar-allocation cap.
        resolution_budget = (
            int(np.iinfo(np.int64).max)
            if requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
            else per_field_voxel_budget
        )
        if resolved_plan is None:
            numerics = resolve_density_numerics(
                cell,
                options=options,
                fractional_by_frame=display_fractional,
                frame_weights=weights,
                pbc=np.asarray(collection.pbc, dtype=bool),
                max_voxels=resolution_budget,
                field_label=label,
            )
        else:
            numerics = resolved_plan.numerics
        visual_adaptation = prepare_density_visual_grid_adaptation(
            cell,
            options=options,
            resolved_numerics=numerics,
            max_logical_voxels=resolution_budget,
            consumer_kind="atomic",
            resolution_reference_source="atomic_samples",
            metadata={"field_key": field_key},
        )
        grid_shape = visual_adaptation.grid_shape
        bandwidth = visual_adaptation.gaussian_bandwidth
        _warn_if_underresolved_density_grid(cell, grid_shape, bandwidth)

        folded = display_fractional - np.floor(display_fractional)
        flat_fractional = folded.reshape(-1, 3)
        sample_weights = np.repeat(weights, len(atoms))
        total = float(len(atoms))
        samples = None
        if options.store_sample_positions:
            samples = flat_fractional @ display_cell
        visual_metadata = visual_adaptation.visual_metadata_dict()
        if cell_equivalence is not None:
            visual_metadata.update(cell_equivalence.metadata_dict())
        planning_metadata = (
            {}
            if planning_metadata_by_field is None
            else dict(planning_metadata_by_field.get(field_key, {}))
        )
        execution_plan_journal_metadata = _planning_execution_journal_metadata(
            planning_metadata
        )
        selected_backend = requested_backend
        backend_selection_metadata: Mapping[str, Any] | None = None
        if requested_backend == AUTO_BACKEND:
            selected_backend, backend_selection_metadata = _planned_backend_from_metadata(
                planning_metadata
            )
            if selected_backend is None:
                weighted_for_selection = PeriodicWeightedSamples3D(
                    fractional_positions=flat_fractional,
                    weights=sample_weights,
                    source_provenance=DensitySourceProvenance(
                        source_kind="atomic_occupancy", atom_indices=atoms
                    ),
                    total_measure=total,
                    measure_kind="occupancy",
                    measure_units="count",
                )
                local_selection = _select_atomic_auto_backend(
                    weighted_for_selection,
                    field_key=field_key,
                    grid_shape=grid_shape,
                    display_cell=cell,
                    gaussian_bandwidth=bandwidth,
                    options=options,
                    max_total_voxels=per_field_voxel_budget,
                    max_nonzero_nodes=max_nonzero_nodes,
                    max_stored_block_values=max_stored_block_values,
                    max_blocks=max_blocks,
                    max_kernel_pairs=max_kernel_pairs,
                    max_planning_bytes=max_planning_bytes,
                    max_workspace_bytes=max_workspace_bytes,
                    max_cic_contributions=max_cic_contributions,
                )
                selected_backend = local_selection.selected_backend
                backend_selection_metadata = local_selection.to_json_dict()
        sparse_backend = selected_backend == LOCAL_SPARSE_BACKEND
        if not sparse_backend:
            used_voxels += _voxel_count(grid_shape)
            if used_voxels > max_total_voxels:
                raise GraphComplexityError(
                    f"Density preparation requires {used_voxels} voxels, exceeding "
                    f"max_density_voxels={max_total_voxels}."
                )
        common_metadata = {
            "schema_version": ATOMIC_DENSITY_SCHEMA,
            "source_kind": "atomic_occupancy",
            "physical_units": "angstrom^-3",
            "deposition": "periodic_trilinear_cloud_in_cell",
            "smoothing_operator": options.kernel_options.smoothing_operator,
            "broadening_metric": options.resolution_options.broadening_metric,
            "storage_backend": selected_backend,
            "requested_storage_backend": requested_backend,
            "backend_selection": backend_selection_metadata,
            "sparse_evaluation_mode": options.optimization_options.sparse_evaluation_mode,
            "stencil_cache_enabled": options.optimization_options.cache_stencil_supports,
            "sparse_pair_chunk_size": options.optimization_options.sparse_pair_chunk_size,
            "sparse_group_batch_size": options.optimization_options.sparse_group_batch_size,
            "sparse_realization_mode": options.optimization_options.sparse_realization_mode,
            "allow_ld7_fallback": options.optimization_options.allow_ld7_fallback,
            "registration_mode": registration_mode,
            "consumer_registration_signature": (
                None if registration_view is None else registration_view.signature
            ),
            "scientific_drift_owner": (
                "legacy_plotting_arguments"
                if registration_view is None
                else "mdstats.coordinates.consumer_adapters"
            ),
            "frame_count": len(frames),
            "weighting": "scene_weights",
            **visual_adaptation.grid_metadata_dict(),
            **visual_metadata,
            **planning_metadata,
        }

        if sparse_backend:
            record_density_stage_timing(
                field_key=field_key,
                stage="planning",
                wall_seconds=time.perf_counter() - planning_stage_started,
                metadata={
                    "backend": selected_backend,
                    "grid_shape": list(grid_shape),
                    **execution_plan_journal_metadata,
                },
            )
            realization_stage_started = time.perf_counter()
            weighted_samples = PeriodicWeightedSamples3D(
                fractional_positions=flat_fractional,
                weights=sample_weights,
                sample_group_ids=np.tile(
                    np.arange(len(atoms), dtype=np.int64), len(frames)
                ),
                source_provenance=DensitySourceProvenance(
                    source_kind="atomic_occupancy",
                    atom_indices=atoms,
                ),
                total_measure=total,
                measure_kind="occupancy",
                measure_units="count",
                metadata={
                    "registration_mode": registration_mode,
                    "frame_count": len(frames),
                    "selected_atom_indices": list(atoms),
                },
            )
            realized_sparse_field = _prepare_sparse_field_for_options(
                    weighted_samples,
                    grid_shape=grid_shape,
                    display_cell=display_cell,
                    gaussian_bandwidth=bandwidth,
                    field_key=field_key,
                    label=label,
                    physical_units="angstrom^-3",
                    broadening_metric=options.resolution_options.broadening_metric,
                    options=options,
                    selected_atom_indices=atoms,
                    sample_positions=samples,
                    metadata=common_metadata,
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
                        else approved_hybrid_plans_by_field.get(field_key)
                    ),
                    precomputed_hybrid_artifacts=(
                        None
                        if precomputed_hybrid_artifacts_by_field is None
                        else precomputed_hybrid_artifacts_by_field.get(field_key)
                    ),
                    progress=progress_port,
                )
            results.append(realized_sparse_field)
            record_density_stage_timing(
                field_key=field_key,
                stage="realization",
                wall_seconds=time.perf_counter() - realization_stage_started,
                metadata={
                    "backend": selected_backend,
                    **execution_plan_journal_metadata,
                    "hybrid_execution_plan_authority": realized_sparse_field.metadata.get(
                        "hybrid_execution_plan_authority"
                    ),
                    "hybrid_execution_plan_identity": realized_sparse_field.metadata.get(
                        "hybrid_execution_plan_identity"
                    ),
                },
            )
            reporter.completed(
                "field_realization",
                f"completed {label!r} with backend={selected_backend}, "
                f"grid={grid_shape}, sigma={bandwidth:.6g} A",
                current=local_field_index + 1,
                total=total_fields,
                unit="fields",
                metadata={
                    "field_index": field_index,
                    "field_key": field_key,
                    "label": label,
                    "backend": selected_backend,
                    "sigma_angstrom": float(bandwidth),
                },
            )
            continue

        record_density_stage_timing(
            field_key=field_key,
            stage="planning",
            wall_seconds=time.perf_counter() - planning_stage_started,
            metadata={
                "backend": selected_backend,
                "grid_shape": list(grid_shape),
                **execution_plan_journal_metadata,
            },
        )
        realization_stage_started = time.perf_counter()
        mass_grid = _deposit_cic(flat_fractional, sample_weights, grid_shape)
        mass_grid, kernel_diagnostics = smooth_periodic_node_masses(
            mass_grid,
            cell,
            bandwidth,
            options.kernel_options,
        )
        voxel_volume = abs(float(np.linalg.det(display_cell))) / float(mass_grid.size)
        density = mass_grid / voxel_volume
        actual = float(np.sum(density) * voxel_volume)
        density *= total / actual
        results.append(
            PeriodicScalarField3D(
                field_key=field_key,
                label=label,
                values=density,
                display_cell=display_cell,
                total_measure=total,
                selected_atom_indices=atoms,
                gaussian_bandwidth=bandwidth,
                sample_positions=samples,
                metadata={
                    **common_metadata,
                    "smoothing": (
                        "periodic_cartesian_isotropic_gaussian_fft"
                        if options.kernel_options.smoothing_operator
                        == LEGACY_SPECTRAL_OPERATOR
                        else "periodic_discrete_periodized_gaussian_fft"
                    ),
                    **kernel_diagnostics.to_json_dict(),
                },
            )
        )
        record_density_stage_timing(
            field_key=field_key,
            stage="realization",
            wall_seconds=time.perf_counter() - realization_stage_started,
            metadata={
                "backend": selected_backend,
                **execution_plan_journal_metadata,
            },
        )
        reporter.completed(
            "field_realization",
            f"completed {label!r} with backend={selected_backend}, "
            f"grid={grid_shape}, sigma={bandwidth:.6g} A",
            current=local_field_index + 1,
            total=total_fields,
            unit="fields",
            metadata={
                "field_index": field_index,
                "field_key": field_key,
                "label": label,
                "backend": selected_backend,
                "sigma_angstrom": float(bandwidth),
            },
        )
    return tuple(results)



def density_mesh_arrays(
    field: PeriodicScalarField3D,
    mass_fraction: float,
    *,
    face_contract: DensityMeshFaceContract | None = None,
    max_faces: int | None = None,
) -> tuple[FloatArray, IntArray, float]:
    """Extract one periodic probability-mass shell as explicit triangles.

    The scalar field is seam-closed by appending the wrapped first grid plane
    along every periodic axis.  Surface extraction uses the Lewiner marching-
    cubes implementation in scikit-image, which is topologically robust and is
    based on the marching-cubes method of Lorensen and Cline (SIGGRAPH 1987,
    DOI: 10.1145/37402.37422) and the ambiguity resolution of Lewiner et al.
    (Journal of Graphics Tools 8, 1-15, 2003,
    DOI: 10.1080/10867651.2003.10487582).

    The browser receives a Plotly ``Mesh3d`` triangle list; it does not perform
    scalar-field triangulation itself.
    """
    if face_contract is not None and not isinstance(
        face_contract, DensityMeshFaceContract
    ):
        raise TypeError("face_contract must be DensityMeshFaceContract or None.")
    if face_contract is not None and max_faces is not None:
        raise GraphStyleError(
            "face_contract cannot be combined with legacy max_faces."
        )
    requested_face_contract = (
        legacy_standalone_face_contract(
            max_faces=max_faces,
            max_raw_faces=None,
        )
        if face_contract is None
        else face_contract
    )
    _budget, _model, derived = resolve_density_resource_limits()
    resolved_face_contract = requested_face_contract.resolve_raw_limit(
        derived["max_density_mesh_faces"]
    )

    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise GraphAdapterError(
            "Mesh density rendering requires scikit-image. Install "
            "'mdstats[interactive]' or use render_mode='voxel_cloud'."
        ) from exc

    fraction = float(mass_fraction)
    if not np.isfinite(fraction) or not 0.0 < fraction < 1.0:
        raise GraphStyleError("mass_fraction must lie strictly between zero and one.")
    level = float(field.threshold_for_mass_fraction(fraction))
    values = np.asarray(field.values, dtype=np.float64)
    extended = np.pad(values, ((0, 1), (0, 1), (0, 1)), mode="wrap")
    minimum = float(np.min(extended))
    maximum = float(np.max(extended))
    if not minimum < level < maximum:
        raise GraphAdapterError(
            f"Density shell level {level:.12g} is outside the open scalar range "
            f"({minimum:.12g}, {maximum:.12g})."
        )
    shape = np.asarray(field.grid_shape, dtype=np.float64)
    # scikit-image converts the volume to float32 internally.  A highest-
    # density-region threshold can be only a few float64 ulps below the field
    # maximum and therefore round *to* that maximum in float32, producing no
    # crossing.  Move such levels to the next representable interior value.
    volume32 = np.ascontiguousarray(extended, dtype=np.float32)
    minimum32 = np.float32(np.min(volume32))
    maximum32 = np.float32(np.max(volume32))
    level32 = np.float32(level)
    if not minimum32 < level32 < maximum32:
        level32 = np.nextafter(maximum32, minimum32, dtype=np.float32)
    try:
        vertices_fractional, faces, _normals, _values = marching_cubes(
            volume32,
            level=float(level32),
            spacing=tuple(float(1.0 / value) for value in shape),
            allow_degenerate=False,
            method="lewiner",
        )
    except RuntimeError as exc:
        # Very small synthetic fields can still contain a flat maximum plateau.
        # Step progressively farther into the scalar range before declaring the
        # requested shell unrenderable.
        span32 = float(maximum32 - minimum32)
        vertices_fractional = faces = None
        for scale in (1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3):
            candidate = float(maximum32) - scale * span32
            if not float(minimum32) < candidate < float(maximum32):
                continue
            try:
                vertices_fractional, faces, _normals, _values = marching_cubes(
                    volume32,
                    level=candidate,
                    spacing=tuple(float(1.0 / value) for value in shape),
                    allow_degenerate=False,
                    method="lewiner",
                )
                level32 = np.float32(candidate)
                break
            except RuntimeError:
                continue
        if vertices_fractional is None or faces is None:
            raise GraphAdapterError(
                "No triangular surface could be extracted for the requested "
                "density mass fraction. Use render_mode='voxel_cloud' for this field."
            ) from exc
    level = float(level32)
    faces = np.asarray(faces, dtype=np.int64)
    raw_face_limit = resolved_face_contract.raw_extraction_face_limit
    assert raw_face_limit is not None
    if faces.shape[0] > int(raw_face_limit):
        raise GraphComplexityError(
            f"Density mesh raw extraction produced {faces.shape[0]} faces, "
            f"exceeding raw_extraction_face_limit={int(raw_face_limit)}."
        )
    face_report = evaluate_density_mesh_face_contract(
        int(faces.shape[0]),
        resolved_face_contract,
    )
    final_face_limit = resolved_face_contract.standalone_final_face_limit
    if face_report.standalone_final_limit_met is False:
        assert final_face_limit is not None
        raise GraphComplexityError(
            f"Density mesh contains {faces.shape[0]} faces, exceeding "
            f"standalone_final_face_limit={int(final_face_limit)}. Reduce the "
            "density grid, simplify the mesh, or use render_mode='voxel_cloud'."
        )
    vertices_cartesian = (
        np.asarray(vertices_fractional, dtype=np.float64) @ field.display_cell
    )
    vertices_cartesian.setflags(write=False)
    faces.setflags(write=False)
    return vertices_cartesian, faces, level


def density_voxel_cloud_arrays(
    field: ScalarField3D,
    outer_mass_fraction: float,
    *,
    max_points: int,
) -> tuple[FloatArray, FloatArray, float]:
    """Return a deterministic backend-neutral logical-node density cloud."""
    from .density_node_cloud import prepare_density_node_cloud

    cloud = prepare_density_node_cloud(
        field,
        outer_mass_fraction,
        max_points=max_points,
    )
    return (
        cloud.cartesian_positions,
        cloud.relative_intensities,
        cloud.hdr_details.threshold,
    )

def density_render_arrays(
    field: PeriodicScalarField3D, fractions: Sequence[float]
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, tuple[float, ...]]:
    """Return periodic seam-closed Cartesian grid and transformed shell levels."""
    fractions_tuple = tuple(float(v) for v in fractions)
    thresholds = tuple(field.threshold_for_mass_fraction(v) for v in fractions_tuple)
    values = np.asarray(field.values)
    extended = np.pad(values, ((0, 1), (0, 1), (0, 1)), mode="wrap")
    shape = field.grid_shape
    axes = [np.arange(n + 1, dtype=np.float64) / n for n in shape]
    fx, fy, fz = np.meshgrid(*axes, indexing="ij")
    fractional = np.stack((fx, fy, fz), axis=-1)
    cartesian = fractional @ field.display_cell
    low_to_high = list(reversed(thresholds))
    x = np.asarray([float(np.min(values)), *low_to_high, float(np.max(values))], dtype=float)
    n = len(thresholds)
    y = np.asarray([n - 0.5, *range(n - 1, -1, -1), -0.5], dtype=float)
    # Remove duplicate x locations to keep interpolation well-defined.
    unique_x: list[float] = []
    unique_y: list[float] = []
    for xv, yv in zip(x, y, strict=True):
        if unique_x and np.isclose(xv, unique_x[-1], rtol=0.0, atol=1.0e-15):
            unique_y[-1] = yv
        else:
            unique_x.append(float(xv))
            unique_y.append(float(yv))
    shell = np.interp(extended, unique_x, unique_y)
    return (
        cartesian[..., 0].ravel(),
        cartesian[..., 1].ravel(),
        cartesian[..., 2].ravel(),
        shell.ravel(),
        thresholds,
    )

# Stage 11E-GR0 compatibility ownership: common grid geometry is analysis-owned.
from ..analysis.density.grid_geometry import (
    density_grid_intervals as _analysis_density_grid_intervals,
    resolve_density_grid_shape as _analysis_resolve_density_grid_shape,
)
from ..analysis.density.numerical_errors import (
    DensityNumericalInputError as _DensityNumericalInputError,
)


def resolve_density_grid_shape(
    cell: FloatArray,
    *,
    grid_shape: tuple[int, int, int] | None,
    grid_interval: float,
) -> tuple[int, int, int]:
    """Plotting adapter for analysis-owned common grid-shape geometry."""

    try:
        return _analysis_resolve_density_grid_shape(
            cell, grid_shape=grid_shape, grid_interval=grid_interval
        )
    except _DensityNumericalInputError as error:
        message = str(error)
        if message.startswith("grid_interval"):
            raise GraphStyleError(message) from error
        raise GraphAdapterError(message) from error


def density_grid_intervals(
    cell: FloatArray, shape: tuple[int, int, int]
) -> tuple[float, float, float]:
    """Plotting adapter for analysis-owned realized grid intervals."""

    try:
        return _analysis_density_grid_intervals(cell, shape)
    except _DensityNumericalInputError as error:
        raise GraphAdapterError(str(error)) from error

# Stage 11E-GR1 compatibility ownership: finest-feasible logical-grid planning
# is analysis-owned.  Plotting retains graph-specific exception translation.
from ..analysis.density.planning import (
    plan_finest_feasible_density_grid as _analysis_plan_finest_feasible_density_grid,
)
from ..analysis.density.numerical_errors import (
    DensityNumericalResourceError as _DensityNumericalResourceError,
)


def _finest_budgeted_grid_shape(
    cell: FloatArray,
    *,
    target_interval: float,
    nominal_interval: float,
    max_voxels: int,
) -> tuple[tuple[int, int, int], bool]:
    """Plotting adapter for the analysis-owned finest-feasible grid planner."""

    try:
        plan = _analysis_plan_finest_feasible_density_grid(
            cell,
            target_interval=target_interval,
            coarsest_interval=nominal_interval,
            max_logical_voxels=max_voxels,
            metadata={"compatibility_consumer": "mdstats.plotting.atomic_density"},
        )
    except (_DensityNumericalInputError, _DensityNumericalResourceError) as error:
        raise GraphComplexityError(str(error)) from error
    return plan.selected_geometry.grid_shape, plan.budget_limited
