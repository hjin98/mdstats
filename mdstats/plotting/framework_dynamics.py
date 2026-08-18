"""Registered mean-framework and atomic-trajectory overlays for 3-D viewing.

The module prepares scientific geometry independently of Plotly.  It reuses the
authoritative framework-topology visualization adapter for every selected frame,
normalizes its periodic gauge, averages the registered framework geometry, and
constructs continuous or folded paths for selected atoms, and may attach
normalized periodic atomic- and framework-density fields. Rendering is a thin composition over :func:`mdstats.plotting.plot_decorated_graph_3d`.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
import sys
import tempfile
import warnings
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Literal

import numpy as np
from ase.data import atomic_numbers as ase_atomic_numbers
from ase.data import chemical_symbols
from numpy.typing import NDArray

from ..analysis.atomic_connectivity import (
    AtomicConnectivityResult,
    AtomicConnectivityState,
)
from ..analysis.framework_topology import FrameworkTopology
from ..analysis.topology_catalog import TopologyCatalog, TopologyConsistency
from ..analysis._neighbors import minimum_image_geometry
from ..collection import AtomisticFrameCollection
from ..coordinates.consumer_adapters import (
    ConsumerCoordinateView,
    prepare_plotting_coordinate_view,
)
from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port
from .atomic_density import (
    AtomicDensityResolvedPlan,
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    PeriodicScalarField3D,
    density_mesh_arrays,
    prepare_atomic_density_fields,
    resolve_density_numerics,
)
from .framework_density import (
    FRAMEWORK_DENSITY_SCHEMA,
    FrameworkDensity3DRenderOptions,
    FrameworkDensityFields,
    FrameworkDensityOptions,
    build_framework_edge_quadrature_samples,
    framework_edge_quadrature_count,
    prepare_framework_density_fields,
    resolve_framework_edge_quadrature,
)
from .density_contracts import (
    AUTO_BACKEND,
    DENSE_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    DensityOptimizationOptions,
    DensitySourceProvenance,
    PeriodicWeightedSamples3D,
    ScalarField3D,
    is_scalar_field3d,
)
from .density_backend_selection import (
    DensityBackendCandidateSet,
    make_candidate_set,
    select_density_scene_backends,
)
from .density_node_cloud import (
    DensityNodeCloud3D,
    DensityTraceProvenance,
    prepare_density_node_cloud,
)
from .density_sparse_optimization import (
    aggregate_periodic_cic_sparse_optimized,
    get_periodic_gaussian_stencil_support,
    plan_group_batched_sparse_targets_optimized,
    estimate_periodic_cic_sparse_optimized_workspace_bytes,
)
from .density_sparse_reference import (
    aggregate_periodic_cic_sparse,
    estimate_periodic_cic_sparse_workspace_bytes,
)
from .density_block_routing import get_periodic_kernel_block_routing
from .density_support_atlas import (
    build_density_support_atlas,
    pack_periodic_cic_source,
)
from .density_tiled_fft import (
    DensityHybridExecutorOptions,
    DensityHybridRealizationPlan,
    plan_hybrid_tiled_realization,
)
from .density_sparse_mesh import (
    PreparedSparseDensitySurface,
    prepare_sparse_density_mesh,
)
from .density_mesh_simplify import MeshSimplificationOptions
from .density_scene_fit import (
    BrowserMeshProfile,
    DensitySceneFitReport,
    DensityShellGeometry,
    fit_density_scene_to_browser_budget,
)
from .density_mesh_contracts import (
    DensityMeshFaceContract,
    evaluate_density_mesh_face_contract,
)
from .density_mesh_execution import (
    DensityMeshExecutionOptions,
    DensityMeshExecutionReport,
)
from .density_gpu import (
    DensityGPUExecutionPolicy,
    density_gpu_journal_scope,
    density_gpu_report,
)
from .density_autotune import (
    DensityAutoTunePolicy,
    autotuned_max_parallel_tasks,
    density_autotune_scope,
    resolve_density_autotune_profile,
)
from .density_execution_journal import (
    density_execution_journal_scope,
    density_execution_report,
)
from .density_scheduler import (
    DensityScheduledTask,
    DensitySceneScheduler,
    DensitySchedulerPolicy,
    DensitySchedulerTaskError,
    DensityTaskExecutionMode,
    DensityTaskResources,
    DensityWorkerLease,
    current_density_worker_lease,
    task_resources_from_phase_b_plan,
)
from .density_render_budget import (
    BrowserMeshBudget,
    BrowserMeshBudgetReport,
    BrowserMeshTraceUsage,
    BrowserMeshUsage,
    INTERACTIVE_BROWSER_PROFILE,
    RAW_REFERENCE_PROFILE,
    require_browser_mesh_budget,
)
from .runtime_resources import (
    DensityTimeModel,
    RuntimeResourceBudget,
    RuntimeResourceSnapshot,
    calibrate_density_time_model,
    density_resource_budget_scope,
    density_time_model_scope,
    derive_density_numeric_limits,
    resolve_runtime_resource_budget,
)
from .density_scene_budget import (
    DensitySceneAllocationOptions,
    DensitySceneBudgetPlan,
    DensitySceneShellRequest,
    allocate_density_scene_budget,
)
from .density_block_sparse import plan_block_packing, plan_sparse_target_nodes
from .density_planning import (
    DensityPhaseAFieldPlan,
    DensityPhaseBFieldPlan,
    DensityPlanningLimits,
    DensityScenePlan,
    dense_retained_bytes,
    dense_transient_bytes,
    occupied_cic_node_indices,
    plan_density_scene,
    sample_byte_count,
    validate_density_phase_a,
    validate_realized_fields,
)
from .density_diagnostics import (
    PeriodicMeanPolicy,
    evaluate_cell_equivalence,
    periodic_frechet_mean_diagnostic,
    require_equivalent_laboratory_density_cells,
)
from .framework_topology_graph import (
    FrameworkGraphDisplayMode,
    graph_view_from_framework_topology,
)
from .graph_3d import (
    Graph3DRenderOptions,
    InteractiveGraphRenderResult,
    plot_decorated_graph_3d,
)
from .graph_errors import (
    GraphAdapterError,
    GraphComplexityError,
    GraphStyleError,
    GraphUnsupportedFeatureError,
    GraphVisualizationError,
)
from .graph_styles import GraphStyle
from .graph_view import (
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphFilter,
    GraphFocus,
)
from .periodic_graph import PeriodicDisplayMode, PeriodicDisplayOptions

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

FRAMEWORK_DYNAMICS_SCENE_SCHEMA = "mdstats.framework-dynamics-scene.v15"


def _prepare_sparse_density_mesh_isolated(
    field: Any,
    mass_fraction: float,
    *,
    execution_options: DensityMeshExecutionOptions | None = None,
    **keyword_arguments: Any,
) -> PreparedSparseDensitySurface:
    """Run one large shell in a fresh interpreter and retain final geometry only.

    A fresh process avoids allocator and native-thread state retention across
    successive high-resolution shells.  Cloudpickle is part of the interactive
    extra because immutable scientific fields contain frozen mapping wrappers.
    """

    policy = (
        DensityMeshExecutionOptions()
        if execution_options is None
        else execution_options
    )
    if not isinstance(policy, DensityMeshExecutionOptions):
        raise TypeError("execution_options must be DensityMeshExecutionOptions or None.")
    try:
        import cloudpickle
    except ImportError as error:  # pragma: no cover - optional dependency guard
        raise GraphUnsupportedFeatureError(
            "Large interactive density scenes require cloudpickle; install "
            "mdstats[interactive]."
        ) from error
    with tempfile.TemporaryDirectory(prefix="mdstats-density-shell-") as directory:
        root = Path(directory)
        input_path = root / "request.pkl"
        output_path = root / "surface.pkl"
        error_path = root / "error.json"
        with input_path.open("wb") as handle:
            cloudpickle.dump(
                {
                    "field": field,
                    "mass_fraction": float(mass_fraction),
                    "keyword_arguments": dict(keyword_arguments),
                },
                handle,
                protocol=5,
            )
        environment = dict(os.environ)
        source_root = str(Path(__file__).resolve().parents[2])
        inherited_path = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            source_root
            if not inherited_path
            else source_root + os.pathsep + inherited_path
        )
        for variable in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            environment[variable] = str(policy.worker_native_threads)
        # Propagate the assigned worker slice into every nested density helper.
        # The child must not independently see the complete parent allocation.
        environment["MDSTATS_MAX_THREADS"] = str(policy.worker_native_threads)
        if policy.worker_memory_bytes is not None:
            environment["MDSTATS_MAX_MEMORY_BYTES"] = str(policy.worker_memory_bytes)
        if policy.worker_timeout_seconds is not None:
            environment["MDSTATS_MAX_WALL_TIME_SECONDS"] = str(
                policy.worker_timeout_seconds
            )
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mdstats.plotting._density_mesh_worker",
                    str(input_path),
                    str(output_path),
                    str(error_path),
                ],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=policy.worker_timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise GraphComplexityError(
                "Isolated sparse-mesh worker exceeded "
                f"worker_timeout_seconds={policy.worker_timeout_seconds:.6g}."
            ) from error
        if completed.returncode != 0 or not output_path.exists():
            if error_path.exists():
                import json

                error_payload = json.loads(error_path.read_text())
                error_type = str(error_payload.get("error_type", "GraphVisualizationError"))
                message = str(
                    error_payload.get(
                        "error_message", "Isolated sparse-mesh worker failed."
                    )
                )
                detail = str(error_payload.get("traceback", ""))
            else:
                error_type = "GraphComplexityError"
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "Isolated sparse-mesh worker failed without diagnostics."
                )
                detail = ""
            error_classes = {
                "GraphAdapterError": GraphAdapterError,
                "GraphComplexityError": GraphComplexityError,
                "GraphStyleError": GraphStyleError,
                "GraphUnsupportedFeatureError": GraphUnsupportedFeatureError,
                "MemoryError": GraphComplexityError,
            }
            error_class = error_classes.get(error_type, GraphVisualizationError)
            raise error_class(
                message if not detail else f"{message}\nChild-process traceback:\n{detail}"
            )
        with output_path.open("rb") as handle:
            surface = cloudpickle.load(handle)
        if not isinstance(surface, PreparedSparseDensitySurface):
            raise GraphAdapterError(
                "Isolated sparse-mesh worker returned an invalid surface record."
            )
        return surface


def _sparse_mesh_progress_summary(
    surface: PreparedSparseDensitySurface,
) -> tuple[str, dict[str, Any]]:
    """Return concise contour-work diagnostics for progress reporting."""

    if surface.mesh is None:
        return "faces=0", {
            "face_count": 0,
            "candidate_cell_count": 0,
            "raw_face_count": 0,
            "tile_count": 0,
        }
    mesh = surface.mesh
    tile_count = 0
    try:
        plan = mesh.metadata.get("contour_tile_plan", {})
        if isinstance(plan, Mapping):
            tile_count = int(plan.get("tile_count", 0))
    except (TypeError, ValueError):
        tile_count = 0
    resources = mesh.resources
    summary = (
        f"tiles={tile_count}, candidates={resources.candidate_cell_count}, "
        f"raw_faces={resources.raw_face_count}, faces={mesh.faces.shape[0]}"
    )
    return summary, {
        "face_count": int(mesh.faces.shape[0]),
        "candidate_cell_count": int(resources.candidate_cell_count),
        "raw_face_count": int(resources.raw_face_count),
        "tile_count": int(tile_count),
    }


def _prepare_sparse_density_mesh_isolated_timed(
    field: Any,
    mass_fraction: float,
    *,
    execution_options: DensityMeshExecutionOptions,
    **keyword_arguments: Any,
) -> tuple[PreparedSparseDensitySurface, float]:
    started = time.perf_counter()
    surface = _prepare_sparse_density_mesh_isolated(
        field,
        mass_fraction,
        execution_options=execution_options,
        **keyword_arguments,
    )
    return surface, time.perf_counter() - started


def _owned_numpy_bytes(*values: Any) -> int:
    """Count unique NumPy buffers owned by prepared scene records."""

    seen_objects: set[int] = set()
    seen_buffers: set[int] = set()

    def visit(value: Any) -> int:
        object_id = id(value)
        if object_id in seen_objects:
            return 0
        seen_objects.add(object_id)
        if isinstance(value, np.ndarray):
            root = value
            while isinstance(root.base, np.ndarray):
                root = root.base
            buffer_id = id(root)
            if buffer_id in seen_buffers:
                return 0
            seen_buffers.add(buffer_id)
            return int(root.nbytes)
        if isinstance(value, Mapping):
            return sum(visit(item) for item in value.values())
        if isinstance(value, (tuple, list, set, frozenset, deque)):
            return sum(visit(item) for item in value)
        if is_dataclass(value) and not isinstance(value, type):
            return sum(visit(getattr(value, item.name)) for item in dataclass_fields(value))
        return 0

    return sum(visit(value) for value in values)


class SpatialRegistrationMode(str, Enum):
    """Coordinate registration used by the mean framework and trajectories."""

    MATERIAL = "material"
    FRAMEWORK_REGISTERED = "framework_registered"
    LABORATORY = "laboratory"


class TrajectoryDisplayMode(str, Enum):
    """How a continuous trajectory is represented in the display cell."""

    CONTINUOUS = "continuous"
    FOLDED = "folded"


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _finite_positive(value: Any, *, name: str, allow_zero: bool = False) -> float:
    result = float(value)
    lower_ok = result >= 0.0 if allow_zero else result > 0.0
    if not np.isfinite(result) or not lower_ok:
        qualifier = "nonnegative" if allow_zero else "positive"
        raise GraphStyleError(f"{name} must be finite and {qualifier}.")
    return result


def _readonly(value: Any, dtype: Any, *, ndim: int | None = None) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphAdapterError(
            f"Expected a {ndim}-dimensional array; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError("Prepared dynamic geometry must be finite.")
    array.setflags(write=False)
    return array


def _coerce_registration(
    value: SpatialRegistrationMode | str,
) -> SpatialRegistrationMode:
    if isinstance(value, SpatialRegistrationMode):
        return value
    try:
        return SpatialRegistrationMode(str(value))
    except ValueError as exc:
        raise GraphAdapterError(
            "registration_mode must be 'material', 'framework_registered', or "
            "'laboratory'."
        ) from exc


def _coerce_path_mode(value: TrajectoryDisplayMode | str) -> TrajectoryDisplayMode:
    if isinstance(value, TrajectoryDisplayMode):
        return value
    try:
        return TrajectoryDisplayMode(str(value))
    except ValueError as exc:
        raise GraphAdapterError(
            "trajectory_display_mode must be 'continuous' or 'folded'."
        ) from exc


@dataclass(frozen=True, slots=True)
class FrameworkDynamicsOptions:
    """Scientific coordinate and display choices for one prepared scene."""

    registration_mode: SpatialRegistrationMode | str = SpatialRegistrationMode.MATERIAL
    trajectory_display_mode: TrajectoryDisplayMode | str = (
        TrajectoryDisplayMode.CONTINUOUS
    )
    display_cell: Literal["reference", "mean"] = "reference"
    reference_frame: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "registration_mode", _coerce_registration(self.registration_mode)
        )
        object.__setattr__(
            self,
            "trajectory_display_mode",
            _coerce_path_mode(self.trajectory_display_mode),
        )
        if self.display_cell not in {"reference", "mean"}:
            raise GraphAdapterError("display_cell must be 'reference' or 'mean'.")
        if self.reference_frame is not None:
            if isinstance(self.reference_frame, bool) or not isinstance(
                self.reference_frame, (int, np.integer)
            ):
                raise GraphAdapterError("reference_frame must be an integer or None.")
            if int(self.reference_frame) < 0:
                raise GraphAdapterError("reference_frame must be nonnegative.")
            object.__setattr__(self, "reference_frame", int(self.reference_frame))


@dataclass(frozen=True, slots=True)
class FrameworkDynamicsResources:
    """Runtime-derived compute policy for one complete density scene.

    The hard user controls are ``max_memory_bytes`` and ``max_threads``.  When
    omitted, memory and CPU availability are detected from process affinity,
    scheduler variables, Linux cgroups, and process limits.  Defaults use 90%
    of the detected CPU allocation and 80% of currently available memory.

    ``max_wall_time_seconds`` is retained as an advisory estimate target for
    backwards compatibility and diagnostics only.  It does not reject, truncate,
    or time out a density scene.  Legacy low-level limits remain optional expert
    overrides; default operation counts are no longer derived from wall time.
    """

    max_memory_bytes: int | str | None = None
    max_threads: int | None = None
    max_wall_time_seconds: float | None = None
    memory_fraction: float = 0.80
    thread_fraction: float = 0.90
    time_model: DensityTimeModel | None = None
    runtime_snapshot: RuntimeResourceSnapshot | None = field(
        default=None, repr=False, compare=False
    )

    max_frames: int | None = None
    max_trajectory_atoms: int | None = None
    max_trajectory_points: int | None = None
    max_trajectory_traces: int | None = None
    max_density_fields: int | None = None
    max_density_voxels: int | None = None
    max_density_samples: int | None = None
    max_density_sample_bytes: int | None = None
    max_density_planning_bytes: int | None = None
    max_density_stencil_values: int | None = None
    max_density_nonzero_nodes: int | None = None
    max_density_stored_block_values: int | None = None
    max_density_blocks: int | None = None
    max_density_kernel_pairs: int | None = None
    max_density_component_values: int | None = None
    max_density_mesh_cells: int | None = None
    max_density_mesh_faces: int | None = None
    max_density_render_points: int | None = None
    max_density_total_peak_bytes: int | None = None
    max_density_traces: int | None = None
    runtime_budget: RuntimeResourceBudget = field(init=False, repr=False)

    def __post_init__(self) -> None:
        budget = resolve_runtime_resource_budget(
            max_memory_bytes=self.max_memory_bytes,
            max_threads=self.max_threads,
            max_wall_time_seconds=self.max_wall_time_seconds,
            memory_fraction=self.memory_fraction,
            thread_fraction=self.thread_fraction,
            snapshot=self.runtime_snapshot,
        )
        object.__setattr__(self, "runtime_budget", budget)
        object.__setattr__(self, "max_memory_bytes", budget.max_memory_bytes)
        object.__setattr__(self, "max_threads", budget.max_threads)
        object.__setattr__(self, "max_wall_time_seconds", budget.max_wall_time_seconds)
        object.__setattr__(self, "memory_fraction", budget.memory_fraction)
        object.__setattr__(self, "thread_fraction", budget.thread_fraction)

        resolved_time_model = (
            calibrate_density_time_model(max_threads=budget.max_threads)
            if self.time_model is None
            else self.time_model
        )
        if not isinstance(resolved_time_model, DensityTimeModel):
            raise TypeError("time_model must be DensityTimeModel or None.")
        object.__setattr__(self, "time_model", resolved_time_model)

        derived = derive_density_numeric_limits(
            budget=budget,
            time_model=resolved_time_model,
        )
        derived["max_frames"] = derived["max_trajectory_points"]
        derived["max_trajectory_atoms"] = derived["max_trajectory_points"]

        for name, default_value in derived.items():
            current = getattr(self, name)
            resolved = default_value if current is None else min(default_value, _positive_int(current, name=name))
            object.__setattr__(self, name, resolved)

    def density_planning_limits(self) -> DensityPlanningLimits:
        """Return the immutable density-planning limits and runtime budget."""

        return DensityPlanningLimits(
            max_density_fields=int(self.max_density_fields),
            max_density_voxels=int(self.max_density_voxels),
            max_density_samples=int(self.max_density_samples),
            max_density_sample_bytes=int(self.max_density_sample_bytes),
            max_density_planning_bytes=int(self.max_density_planning_bytes),
            max_density_stencil_values=int(self.max_density_stencil_values),
            max_density_nonzero_nodes=int(self.max_density_nonzero_nodes),
            max_density_stored_block_values=int(self.max_density_stored_block_values),
            max_density_blocks=int(self.max_density_blocks),
            max_density_kernel_pairs=int(self.max_density_kernel_pairs),
            max_density_component_values=int(self.max_density_component_values),
            max_density_mesh_cells=int(self.max_density_mesh_cells),
            max_density_mesh_faces=int(self.max_density_mesh_faces),
            max_density_render_points=int(self.max_density_render_points),
            max_density_total_peak_bytes=int(self.max_density_total_peak_bytes),
            max_density_threads=int(self.max_threads),
            max_density_wall_time_seconds=float(self.max_wall_time_seconds),
            time_model=self.time_model,
        )

    def to_json_dict(self) -> dict[str, Any]:
        """Return the resolved policy, including detection and override provenance."""

        return {
            "runtime_budget": self.runtime_budget.to_json_dict(),
            "time_model": self.time_model.to_json_dict(),
            **{
                name: getattr(self, name)
                for name in (
                    "max_frames",
                    "max_trajectory_atoms",
                    "max_trajectory_points",
                    "max_trajectory_traces",
                    "max_density_fields",
                    "max_density_voxels",
                    "max_density_samples",
                    "max_density_sample_bytes",
                    "max_density_planning_bytes",
                    "max_density_stencil_values",
                    "max_density_nonzero_nodes",
                    "max_density_stored_block_values",
                    "max_density_blocks",
                    "max_density_kernel_pairs",
                    "max_density_component_values",
                    "max_density_mesh_cells",
                    "max_density_mesh_faces",
                    "max_density_render_points",
                    "max_density_total_peak_bytes",
                    "max_density_traces",
                )
            },
        }


@dataclass(frozen=True, slots=True)
class TrajectoryAtomSelection:
    """Union selection of explicit atoms and chemical species."""

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
                "TrajectoryAtomSelection requires atom_indices and/or species."
            )
        if self.label is not None and (
            not isinstance(self.label, str) or not self.label
        ):
            raise GraphAdapterError("label must be None or a nonempty string.")
        object.__setattr__(self, "atom_indices", tuple(sorted(set(indices))))
        object.__setattr__(self, "species", tuple(species))

    def resolve(self, collection: AtomisticFrameCollection) -> tuple[int, ...]:
        selected = set(self.atom_indices)
        for selector in self.species:
            number = (
                int(selector)
                if isinstance(selector, int)
                else int(ase_atomic_numbers[selector])
            )
            selected.update(
                int(index)
                for index in np.flatnonzero(collection.atomic_numbers == number)
            )
        if selected and max(selected) >= collection.n_atoms:
            raise GraphAdapterError(
                "Trajectory selection contains an atom outside the collection."
            )
        if not selected:
            raise GraphAdapterError("Trajectory selection resolved to no atoms.")
        return tuple(sorted(selected))


@dataclass(frozen=True, slots=True)
class TrajectoryPathSet:
    """Prepared continuous and display paths for selected atoms."""

    atom_indices: tuple[int, ...]
    atomic_numbers: IntArray
    frame_indices: IntArray
    frame_ids: IntArray
    times: FloatArray | None
    continuous_positions: FloatArray
    display_positions: FloatArray
    lattice_images: IntArray
    segment_breaks: BoolArray
    display_mode: TrajectoryDisplayMode | str
    selection_label: str

    def __post_init__(self) -> None:
        atoms = tuple(int(value) for value in self.atom_indices)
        if atoms != tuple(sorted(set(atoms))) or not atoms:
            raise GraphAdapterError(
                "atom_indices must be nonempty, sorted, and unique."
            )
        numbers = _readonly(self.atomic_numbers, np.int64, ndim=1)
        frames = _readonly(self.frame_indices, np.int64, ndim=1)
        frame_ids = _readonly(self.frame_ids, np.int64, ndim=1)
        continuous = _readonly(self.continuous_positions, np.float64, ndim=3)
        display = _readonly(self.display_positions, np.float64, ndim=3)
        images = _readonly(self.lattice_images, np.int64, ndim=3)
        breaks = _readonly(self.segment_breaks, np.bool_, ndim=2)
        expected = (len(atoms), len(frames), 3)
        if (
            continuous.shape != expected
            or display.shape != expected
            or images.shape != expected
        ):
            raise GraphAdapterError(
                "Trajectory path arrays must have shape (n_atoms, n_frames, 3)."
            )
        if breaks.shape != (len(atoms), max(0, len(frames) - 1)):
            raise GraphAdapterError(
                "segment_breaks must have shape (n_atoms, n_frames - 1)."
            )
        if numbers.shape != (len(atoms),) or frame_ids.shape != frames.shape:
            raise GraphAdapterError("Trajectory path metadata arrays are misaligned.")
        times = None
        if self.times is not None:
            times = _readonly(self.times, np.float64, ndim=1)
            if times.shape != frames.shape:
                raise GraphAdapterError("times must align with frame_indices.")
        if not isinstance(self.selection_label, str) or not self.selection_label:
            raise GraphAdapterError("selection_label must be a nonempty string.")
        object.__setattr__(self, "atom_indices", atoms)
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "times", times)
        object.__setattr__(self, "continuous_positions", continuous)
        object.__setattr__(self, "display_positions", display)
        object.__setattr__(self, "lattice_images", images)
        object.__setattr__(self, "segment_breaks", breaks)
        object.__setattr__(self, "display_mode", _coerce_path_mode(self.display_mode))

    @property
    def n_atoms(self) -> int:
        return len(self.atom_indices)

    @property
    def n_frames(self) -> int:
        return int(self.frame_indices.size)


@dataclass(frozen=True, slots=True)
class AtomicMeanGraphOptions:
    """Preparation policy for an averaged atomic-connectivity graph."""

    mode: Literal["persistent", "occupancy"] = "occupancy"
    occupancy_threshold: float = 0.95

    def __post_init__(self) -> None:
        if self.mode not in {"persistent", "occupancy"}:
            raise GraphAdapterError(
                "AtomicMeanGraphOptions.mode must be 'persistent' or 'occupancy'."
            )
        threshold = float(self.occupancy_threshold)
        if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise GraphAdapterError("occupancy_threshold must lie in [0, 1].")
        object.__setattr__(self, "occupancy_threshold", threshold)


@dataclass(frozen=True, slots=True)
class AtomicMeanGraph:
    """Prepared averaged atomic net in the scene display cell."""

    atom_indices: tuple[int, ...]
    atomic_numbers: IntArray
    display_positions: FloatArray
    edge_endpoints: IntArray
    edge_image_shifts: IntArray
    edge_occupancies: FloatArray
    display_cell: FloatArray
    pbc: BoolArray
    mode: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        atoms = tuple(int(value) for value in self.atom_indices)
        if atoms != tuple(sorted(set(atoms))) or not atoms:
            raise GraphAdapterError(
                "AtomicMeanGraph atom_indices must be nonempty, sorted, and unique."
            )
        numbers = _readonly(self.atomic_numbers, np.int64, ndim=1)
        positions = _readonly(self.display_positions, np.float64, ndim=2)
        endpoints = _readonly(self.edge_endpoints, np.int64, ndim=2)
        shifts = _readonly(self.edge_image_shifts, np.int64, ndim=2)
        occupancies = _readonly(self.edge_occupancies, np.float64, ndim=1)
        cell = _readonly(self.display_cell, np.float64, ndim=2)
        pbc = _readonly(self.pbc, np.bool_, ndim=1)
        if numbers.shape != (len(atoms),):
            raise GraphAdapterError(
                "AtomicMeanGraph atomic_numbers must align with atom_indices."
            )
        if positions.shape != (len(atoms), 3):
            raise GraphAdapterError(
                "AtomicMeanGraph display_positions must have shape (n_atoms, 3)."
            )
        if endpoints.shape[1:] != (2,) or shifts.shape != (endpoints.shape[0], 3):
            raise GraphAdapterError(
                "AtomicMeanGraph edges must have shape (n_edges, 2) and shifts (n_edges, 3)."
            )
        if occupancies.shape != (endpoints.shape[0],):
            raise GraphAdapterError(
                "AtomicMeanGraph edge_occupancies must align with edges."
            )
        if cell.shape != (3, 3) or abs(float(np.linalg.det(cell))) <= 1.0e-12:
            raise GraphAdapterError(
                "AtomicMeanGraph display_cell must be a nonsingular 3x3 matrix."
            )
        if pbc.shape != (3,):
            raise GraphAdapterError("AtomicMeanGraph pbc must have shape (3,).")
        if np.any(endpoints < 0) or np.any(endpoints >= len(atoms)):
            raise GraphAdapterError(
                "AtomicMeanGraph edges reference invalid node indices."
            )
        if np.any(~np.isfinite(occupancies)) or np.any(
            (occupancies < -1.0e-12) | (occupancies > 1.0 + 1.0e-12)
        ):
            raise GraphAdapterError("AtomicMeanGraph occupancies must lie in [0, 1].")
        object.__setattr__(self, "atom_indices", atoms)
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "display_positions", positions)
        object.__setattr__(self, "edge_endpoints", endpoints)
        object.__setattr__(self, "edge_image_shifts", shifts)
        object.__setattr__(self, "edge_occupancies", occupancies)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class FrameworkTopologyCategoryLayer:
    """One topology-conditioned averaged framework and atomic mean graph."""

    topology_id: int
    topology: FrameworkTopology
    frame_indices: IntArray
    probability: float
    segment_count: int
    mean_framework: DecoratedGraphView
    atomic_mean_graph: AtomicMeanGraph | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        topology_id = int(self.topology_id)
        if topology_id < 0:
            raise GraphAdapterError("topology_id must be nonnegative.")
        if not isinstance(self.topology, FrameworkTopology):
            raise TypeError("topology must be FrameworkTopology.")
        frames = _readonly(self.frame_indices, np.int64, ndim=1)
        if frames.size == 0:
            raise GraphAdapterError("Topology category frame_indices must be nonempty.")
        probability = float(self.probability)
        if not np.isfinite(probability) or not 0.0 < probability <= 1.0:
            raise GraphAdapterError("Topology category probability must lie in (0, 1].")
        segment_count = int(self.segment_count)
        if segment_count < 1:
            raise GraphAdapterError("Topology category segment_count must be positive.")
        if not isinstance(self.mean_framework, DecoratedGraphView):
            raise TypeError("mean_framework must be DecoratedGraphView.")
        if self.atomic_mean_graph is not None and not isinstance(self.atomic_mean_graph, AtomicMeanGraph):
            raise TypeError("atomic_mean_graph must be AtomicMeanGraph or None.")
        object.__setattr__(self, "topology_id", topology_id)
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "segment_count", segment_count)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def legend_title(self) -> str:
        return (
            f"Topology {self.topology_id} — {100.0 * self.probability:.1f}% · "
            f"{len(self.frame_indices)} frames · {self.segment_count} segments"
        )


@dataclass(frozen=True, slots=True)
class FrameworkDynamicsScene:
    """Renderer-independent mean framework and optional dynamic overlays."""

    mean_framework: DecoratedGraphView
    trajectory_paths: TrajectoryPathSet | None
    atomic_mean_graph: AtomicMeanGraph | None
    frame_indices: IntArray
    weights: FloatArray
    display_cell: FloatArray
    options: FrameworkDynamicsOptions
    resources: FrameworkDynamicsResources
    atomic_density_fields: tuple[ScalarField3D, ...] = ()
    framework_density_fields: FrameworkDensityFields | None = None
    planning_record: DensityScenePlan | None = None
    topology_categories: tuple[FrameworkTopologyCategoryLayer, ...] = ()
    topology_catalog: TopologyCatalog | None = None
    dominant_topology_id: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.mean_framework, DecoratedGraphView):
            raise TypeError("mean_framework must be a DecoratedGraphView.")
        frames = _readonly(self.frame_indices, np.int64, ndim=1)
        weights = _readonly(self.weights, np.float64, ndim=1)
        cell = _readonly(self.display_cell, np.float64, ndim=2)
        if frames.size == 0 or weights.shape != frames.shape:
            raise GraphAdapterError(
                "Scene frames and weights must be nonempty and aligned."
            )
        if not np.isclose(float(np.sum(weights)), 1.0, rtol=0.0, atol=1.0e-12):
            raise GraphAdapterError("Scene weights must sum to one.")
        if cell.shape != (3, 3) or abs(float(np.linalg.det(cell))) <= 1.0e-12:
            raise GraphAdapterError("display_cell must be a nonsingular 3x3 matrix.")
        if self.trajectory_paths is not None and not np.array_equal(
            self.trajectory_paths.frame_indices, frames
        ):
            raise GraphAdapterError(
                "Trajectory paths must use the scene frame sequence."
            )
        if self.atomic_mean_graph is not None:
            if not isinstance(self.atomic_mean_graph, AtomicMeanGraph):
                raise TypeError("atomic_mean_graph must be AtomicMeanGraph or None.")
            if not np.allclose(
                self.atomic_mean_graph.display_cell, cell, rtol=0.0, atol=1.0e-12
            ):
                raise GraphAdapterError(
                    "Atomic mean graph must use the scene display cell."
                )
        densities = tuple(self.atomic_density_fields)
        if any(not is_scalar_field3d(value) for value in densities):
            raise TypeError("atomic_density_fields must contain ScalarField3D objects.")
        if any(
            not np.allclose(value.display_cell, cell, rtol=0.0, atol=1.0e-12)
            for value in densities
        ):
            raise GraphAdapterError(
                "Atomic density fields must use the scene display cell."
            )
        framework_density = self.framework_density_fields
        if framework_density is not None:
            if not isinstance(framework_density, FrameworkDensityFields):
                raise TypeError(
                    "framework_density_fields must be FrameworkDensityFields or None."
                )
            if any(
                not np.allclose(value.display_cell, cell, rtol=0.0, atol=1.0e-12)
                for value in framework_density.fields
            ):
                raise GraphAdapterError(
                    "Framework density fields must use the scene display cell."
                )
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "display_cell", cell)
        planning = self.planning_record
        if planning is not None and not isinstance(planning, DensityScenePlan):
            raise TypeError("planning_record must be DensityScenePlan or None.")
        if (densities or framework_density is not None) and planning is None:
            raise GraphAdapterError(
                "Density-bearing scenes require an approved planning_record."
            )
        object.__setattr__(self, "atomic_density_fields", densities)
        object.__setattr__(self, "framework_density_fields", framework_density)
        object.__setattr__(self, "planning_record", planning)
        categories = tuple(self.topology_categories)
        if any(not isinstance(item, FrameworkTopologyCategoryLayer) for item in categories):
            raise TypeError("topology_categories must contain FrameworkTopologyCategoryLayer values.")
        if categories:
            category_ids = tuple(item.topology_id for item in categories)
            if len(set(category_ids)) != len(category_ids):
                raise GraphAdapterError("topology category IDs must be unique.")
            if int(self.dominant_topology_id) not in category_ids:
                raise GraphAdapterError("dominant_topology_id must identify a stored category.")
            if not np.isclose(sum(item.probability for item in categories), 1.0, atol=1.0e-12):
                raise GraphAdapterError("Topology category probabilities must sum to one.")
        catalog = self.topology_catalog
        if catalog is not None and not isinstance(catalog, TopologyCatalog):
            raise TypeError("topology_catalog must be TopologyCatalog or None.")
        object.__setattr__(self, "topology_categories", categories)
        object.__setattr__(self, "topology_catalog", catalog)
        object.__setattr__(self, "dominant_topology_id", int(self.dominant_topology_id))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class Trajectory3DRenderOptions:
    """Plotly styling for prepared atomic trajectories.

    ``group_by_species`` is the browser-safe default.  It concatenates all paths
    of one chemical species into one Plotly line trace with ``None`` separators,
    reducing hundreds of WebGL objects to one trace per species without changing
    the sampled trajectory coordinates.
    """

    line_width: float = 4.0
    opacity: float = 0.82
    show_start_end: bool = True
    endpoint_size: float = 5.0
    show_legend: bool = True
    group_by_species: bool = True
    enable_hover: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "line_width", _finite_positive(self.line_width, name="line_width")
        )
        opacity = float(self.opacity)
        if not np.isfinite(opacity) or not 0.0 <= opacity <= 1.0:
            raise GraphStyleError("opacity must lie in [0, 1].")
        object.__setattr__(self, "opacity", opacity)
        object.__setattr__(
            self,
            "endpoint_size",
            _finite_positive(self.endpoint_size, name="endpoint_size"),
        )
        object.__setattr__(self, "show_start_end", bool(self.show_start_end))
        object.__setattr__(self, "show_legend", bool(self.show_legend))
        object.__setattr__(self, "group_by_species", bool(self.group_by_species))
        object.__setattr__(self, "enable_hover", bool(self.enable_hover))


@dataclass(frozen=True, slots=True)
class AtomicMeanGraph3DRenderOptions:
    """Plotly styling for the averaged atomic-connectivity net."""

    node_size: float = 5.5
    node_opacity: float = 0.95
    edge_width: float = 2.2
    edge_opacity: float = 0.55
    edge_color: str = "rgb(120, 120, 120)"
    show_legend: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "node_size", _finite_positive(self.node_size, name="node_size")
        )
        object.__setattr__(
            self, "edge_width", _finite_positive(self.edge_width, name="edge_width")
        )
        node_opacity = float(self.node_opacity)
        edge_opacity = float(self.edge_opacity)
        if not np.isfinite(node_opacity) or not 0.0 <= node_opacity <= 1.0:
            raise GraphStyleError("node_opacity must lie in [0, 1].")
        if not np.isfinite(edge_opacity) or not 0.0 <= edge_opacity <= 1.0:
            raise GraphStyleError("edge_opacity must lie in [0, 1].")
        if not isinstance(self.edge_color, str) or not self.edge_color:
            raise GraphStyleError("edge_color must be a nonempty CSS color string.")
        object.__setattr__(self, "node_opacity", node_opacity)
        object.__setattr__(self, "edge_opacity", edge_opacity)
        object.__setattr__(self, "show_legend", bool(self.show_legend))


@dataclass(slots=True)
class FrameworkDynamicsRenderResult:
    """Composite Plotly result for a mean framework and trajectory overlays."""

    figure: Any
    scene: FrameworkDynamicsScene
    base_result: InteractiveGraphRenderResult
    trajectory_trace_indices: Mapping[int, tuple[int, ...]]
    atomic_mean_graph_trace_indices: Mapping[str, tuple[int, ...]]
    endpoint_trace_indices: tuple[int, ...]
    density_trace_indices: Mapping[str, tuple[int, ...]]
    framework_density_trace_indices: Mapping[str, tuple[int, ...]]
    render_metadata: Mapping[str, Any]
    density_trace_provenance: Mapping[int, DensityTraceProvenance] = field(
        default_factory=dict
    )
    browser_budget: BrowserMeshBudget | None = None
    browser_profile: Literal["interactive_browser", "raw_reference"] = INTERACTIVE_BROWSER_PROFILE
    browser_usage: BrowserMeshUsage | None = None
    browser_budget_report: BrowserMeshBudgetReport | None = None

    def __post_init__(self) -> None:
        self.trajectory_trace_indices = MappingProxyType(
            {
                int(key): tuple(value)
                for key, value in self.trajectory_trace_indices.items()
            }
        )
        self.atomic_mean_graph_trace_indices = MappingProxyType(
            {
                str(key): tuple(value)
                for key, value in self.atomic_mean_graph_trace_indices.items()
            }
        )
        self.endpoint_trace_indices = tuple(self.endpoint_trace_indices)
        self.density_trace_indices = MappingProxyType(
            {
                str(key): tuple(value)
                for key, value in self.density_trace_indices.items()
            }
        )
        self.framework_density_trace_indices = MappingProxyType(
            {
                str(key): tuple(value)
                for key, value in self.framework_density_trace_indices.items()
            }
        )
        self.density_trace_provenance = MappingProxyType(
            {int(key): value for key, value in self.density_trace_provenance.items()}
        )
        self.render_metadata = MappingProxyType(dict(self.render_metadata))
        if self.browser_budget is not None and not isinstance(self.browser_budget, BrowserMeshBudget):
            raise TypeError("browser_budget must be BrowserMeshBudget or None.")
        if self.browser_profile not in {INTERACTIVE_BROWSER_PROFILE, RAW_REFERENCE_PROFILE}:
            raise GraphStyleError("Unsupported browser_profile.")
        if self.browser_usage is not None and not isinstance(self.browser_usage, BrowserMeshUsage):
            raise TypeError("browser_usage must be BrowserMeshUsage or None.")
        if self.browser_budget_report is not None and not isinstance(
            self.browser_budget_report, BrowserMeshBudgetReport
        ):
            raise TypeError("browser_budget_report must be BrowserMeshBudgetReport or None.")

    def to_html(
        self,
        *,
        include_plotlyjs: Literal["cdn", "directory"] | bool = "cdn",
        full_html: bool = True,
    ) -> str:
        try:
            html = self.figure.to_html(
                include_plotlyjs=include_plotlyjs, full_html=full_html
            )
        except Exception as exc:  # pragma: no cover - Plotly serializer owned upstream
            raise GraphVisualizationError(
                "Could not serialize framework-dynamics figure to HTML."
            ) from exc
        if self.browser_budget is not None and self.browser_usage is not None:
            usage = BrowserMeshUsage(
                density_traces=self.browser_usage.density_traces,
                non_density_trace_count=self.browser_usage.non_density_trace_count,
                final_html_bytes=len(html.encode("utf-8")),
                metadata=self.browser_usage.metadata,
            )
            report = require_browser_mesh_budget(
                usage,
                budget=self.browser_budget,
                profile=self.browser_profile,
            )
            self.browser_usage = usage
            self.browser_budget_report = report
        return html

    def write_html(
        self,
        path: str | os.PathLike[str],
        *,
        include_plotlyjs: Literal["cdn", "directory"] | bool = "cdn",
        full_html: bool = True,
        auto_open: bool = False,
    ) -> None:
        target = Path(path)
        html = self.to_html(include_plotlyjs=include_plotlyjs, full_html=full_html)
        try:
            target.write_text(html, encoding="utf-8")
        except Exception as exc:
            raise GraphVisualizationError(
                f"Could not write framework-dynamics HTML to {target}."
            ) from exc
        if auto_open:  # pragma: no cover - environment dependent
            import webbrowser
            webbrowser.open(target.resolve().as_uri())


def _selected_frames(
    collection: AtomisticFrameCollection, frame_indices: Sequence[int] | None
) -> tuple[int, ...]:
    if frame_indices is None:
        frames = tuple(range(collection.n_frames))
    else:
        frames = tuple(int(value) for value in frame_indices)
    if not frames or len(set(frames)) != len(frames):
        raise GraphAdapterError("frame_indices must be nonempty and unique.")
    if tuple(sorted(frames)) != frames:
        raise GraphAdapterError("frame_indices must be strictly increasing.")
    if frames[0] < 0 or frames[-1] >= collection.n_frames:
        raise GraphAdapterError("A selected frame lies outside the collection.")
    return frames


def _uniform_weights(n_frames: int) -> FloatArray:
    return np.full(n_frames, 1.0 / n_frames, dtype=np.float64)


def _graph_gauge(view: DecoratedGraphView) -> tuple[IntArray, IntArray, IntArray]:
    if (
        view.node_positions_3d is None
        or view.cell is None
        or view.edge_image_shifts is None
    ):
        raise GraphAdapterError(
            "Framework dynamics require spatial graph positions, cell, and edge shifts."
        )
    n_nodes = view.n_nodes
    adjacency: list[list[tuple[int, np.ndarray, int]]] = [
        list() for _ in range(n_nodes)
    ]
    for edge_index, ((source, target), shift) in enumerate(
        zip(view.edge_endpoints, view.edge_image_shifts, strict=True)
    ):
        i, j = int(source), int(target)
        directed = np.asarray(shift, dtype=np.int64)
        if i == j:
            continue
        adjacency[i].append((j, directed, edge_index))
        adjacency[j].append((i, -directed, edge_index))
    for values in adjacency:
        values.sort(key=lambda item: (item[0], *item[1].tolist(), item[2]))
    gauge = np.zeros((n_nodes, 3), dtype=np.int64)
    component = np.full(n_nodes, -1, dtype=np.int64)
    assigned = np.zeros(n_nodes, dtype=bool)
    component_id = 0
    for root in range(n_nodes):
        if assigned[root]:
            continue
        assigned[root] = True
        component[root] = component_id
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, shift, _edge_index in adjacency[current]:
                if assigned[neighbor]:
                    continue
                gauge[neighbor] = gauge[current] + shift
                assigned[neighbor] = True
                component[neighbor] = component_id
                queue.append(neighbor)
        component_id += 1
    residual = np.asarray(view.edge_image_shifts, dtype=np.int64).copy()
    for edge_index, (source, target) in enumerate(view.edge_endpoints):
        residual[edge_index] += gauge[int(source)] - gauge[int(target)]
    return gauge, residual, component


def _lifted_fractional_graph(
    collection: AtomisticFrameCollection,
    frame_index: int,
    view: DecoratedGraphView,
) -> tuple[FloatArray, IntArray]:
    gauge, residual, component = _graph_gauge(view)
    assert view.node_positions_3d is not None and view.cell is not None
    fractional = np.asarray(view.node_positions_3d, dtype=np.float64) @ np.linalg.inv(
        np.asarray(view.cell, dtype=np.float64)
    )
    lifted = fractional + gauge
    for component_id in range(int(np.max(component)) + 1):
        members = np.flatnonzero(component == component_id)
        root = int(members[0])
        anchor_key = view.node_keys[root]
        if not isinstance(anchor_key, (int, np.integer)):
            raise GraphAdapterError(
                "Framework dynamics require atom-index graph node keys."
            )
        anchor_atom = int(anchor_key)
        if collection.is_trajectory:
            target = np.asarray(
                collection.fractional_positions[frame_index, anchor_atom],
                dtype=np.float64,
            )
            delta = target - lifted[root]
            global_shift = np.rint(delta).astype(np.int64)
            if not np.allclose(delta, global_shift, rtol=0.0, atol=2.0e-8):
                raise GraphAdapterError(
                    "Trajectory framework gauge cannot be aligned to a component anchor."
                )
        else:
            global_shift = -np.floor(lifted[root]).astype(np.int64)
        lifted[members] += global_shift
    return lifted, residual




@dataclass(frozen=True, slots=True)
class _PreparedFrameworkFrame:
    """One frame-local framework graph plus its normalized periodic lift."""

    view: DecoratedGraphView
    lifted_fractional: FloatArray
    residual_shifts: IntArray


class _FrameworkGeometryCache:
    """Thread-safe in-process cache for frame-local framework display geometry.

    PAR-DENS4 intentionally keeps this cache execution-local.  Its keys are
    scientific frame/topology/display-mode identities and never contain worker
    counts, executor choices, or timing measurements.  The cache therefore
    removes repeated projected/path reconstruction across global and
    topology-conditioned scene preparation without changing provenance.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[tuple[str, int, str], _PreparedFrameworkFrame] = {}
        self.hits = 0
        self.misses = 0
        self.bulk_static_projected_frames = 0

    def get_or_build(
        self,
        collection: AtomisticFrameCollection,
        topology: FrameworkTopology,
        *,
        frame_index: int,
        display_mode: FrameworkGraphDisplayMode | str,
    ) -> _PreparedFrameworkFrame:
        mode = FrameworkGraphDisplayMode(display_mode)
        key = (str(topology.digest), int(frame_index), mode.value)
        with self._lock:
            cached = self._items.get(key)
            if cached is not None:
                self.hits += 1
                return cached
        view = graph_view_from_framework_topology(
            collection,
            topology,
            frame_index=int(frame_index),
            display_mode=mode,
        )
        lifted, residual = _lifted_fractional_graph(collection, int(frame_index), view)
        prepared = _PreparedFrameworkFrame(
            view=view,
            lifted_fractional=np.asarray(lifted, dtype=np.float64),
            residual_shifts=np.asarray(residual, dtype=np.int64),
        )
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                self.hits += 1
                return existing
            self._items[key] = prepared
            self.misses += 1
        return prepared

    def record_bulk_static_projected(self, frame_count: int) -> None:
        with self._lock:
            self.bulk_static_projected_frames += max(0, int(frame_count))

    def summary(self) -> dict[str, int | str]:
        with self._lock:
            return {
                "policy": "par_dens4_frame_geometry_cache_v1",
                "entries": len(self._items),
                "hits": int(self.hits),
                "misses": int(self.misses),
                "bulk_static_projected_frames": int(self.bulk_static_projected_frames),
                "harden1_bulk_static_projected_enabled": True,
            }


def _preprocessing_resource_estimate(
    *,
    task_id: str,
    frame_count: int,
    item_count: int,
    max_threads: int,
    construction_order: int = 0,
    retained: bool = False,
    backend: str = "trajectory_preprocessing",
) -> DensityTaskResources:
    """Return a conservative PAR-DENS2 contract for CPU-side geometry work."""

    frames = max(1, int(frame_count))
    items = max(1, int(item_count))
    # Coordinates, integer shifts, temporary graph arrays and modest Python
    # object overhead.  This is deliberately conservative without pretending
    # that opaque DecoratedGraphView object memory is scientifically exact.
    payload = frames * items * (3 * 8 * 4 + 3 * 8 * 2 + 64)
    retained_bytes = payload if retained else 0
    transient_bytes = max(1 << 20, payload * 2)
    workers = max(1, min(int(max_threads), frames))
    return DensityTaskResources(
        task_id=task_id,
        retained_bytes=retained_bytes,
        transient_bytes=transient_bytes,
        minimum_workers=1,
        preferred_workers=workers,
        execution_mode=DensityTaskExecutionMode.PYTHON_THREADS,
        backend=backend,
        construction_order=int(construction_order),
        metadata={
            "par_dens_gate": "PAR-DENS4",
            "scientific_identity_includes_worker_count": False,
            "frame_count": frames,
            "item_count": items,
        },
    )


def _run_preprocessing_task(
    scheduler: DensitySceneScheduler,
    resources: DensityTaskResources,
    function: Callable[[DensityWorkerLease], Any],
) -> Any:
    """Run one preprocessing task under the current or scene scheduler lease."""

    active = current_density_worker_lease()
    if active is not None:
        return function(active)
    return scheduler.run((DensityScheduledTask(resources=resources, function=function),))[0]


def _bulk_static_cell_projected_framework_lifts(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frames: tuple[int, ...],
) -> tuple[DecoratedGraphView, list[FloatArray], IntArray] | None:
    """Vectorize projected framework lifting for one exact static cell.

    HARDEN1 avoids constructing a full decorated graph and invoking the exact
    triclinic MIC kernel once per frame when the selected trajectory uses one
    unchanged cell.  All retained atomic-path segment vectors are evaluated in
    one batched MIC call, while the two deterministic graph gauges are applied
    across the frame axis.  The fast path is enabled only when graph traversal
    order is independent of frame-local image shifts; periodic multiedge cases
    fall back to the authoritative frame-local adapter.
    """

    if not frames:
        return None
    frame_array = np.asarray(frames, dtype=np.int64)
    cells = np.asarray(collection.cells[frame_array], dtype=np.float64)
    cell = np.asarray(cells[0], dtype=np.float64)
    if not np.array_equal(cells, np.broadcast_to(cell, cells.shape)):
        return None
    pbc = np.asarray(collection.pbc, dtype=bool)

    first_view = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=int(frames[0]),
        display_mode=FrameworkGraphDisplayMode.PROJECTED,
    )
    if first_view.edge_image_shifts is None:
        return None

    # Frame-independent segment ownership.
    segment_sources: list[int] = []
    segment_targets: list[int] = []
    edge_slices: list[tuple[int, int]] = []
    for edge in topology.edges:
        begin = len(segment_sources)
        for source, target in zip(
            edge.atomic_path_indices[:-1], edge.atomic_path_indices[1:], strict=True
        ):
            segment_sources.append(int(source))
            segment_targets.append(int(target))
        edge_slices.append((begin, len(segment_sources)))

    if segment_sources:
        source_array = np.asarray(segment_sources, dtype=np.int64)
        target_array = np.asarray(segment_targets, dtype=np.int64)
        frac = np.asarray(collection.fractional_positions[frame_array], dtype=np.float64)
        wrapped = np.array(frac, copy=True)
        for axis, periodic in enumerate(pbc):
            if periodic:
                wrapped[..., axis] -= np.floor(wrapped[..., axis])
        raw_fractional = wrapped[:, target_array, :] - wrapped[:, source_array, :]
        raw_cartesian = raw_fractional @ cell
        _vectors, _distances, segment_shifts = minimum_image_geometry(
            raw_cartesian.reshape((-1, 3)), cell=cell, pbc=pbc
        )
        segment_shifts = np.asarray(segment_shifts, dtype=np.int64).reshape(
            (len(frames), len(segment_sources), 3)
        )
    else:
        wrapped = np.asarray(collection.fractional_positions[frame_array], dtype=np.float64)
        wrapped = np.array(wrapped, copy=True)
        for axis, periodic in enumerate(pbc):
            if periodic:
                wrapped[..., axis] -= np.floor(wrapped[..., axis])
        segment_shifts = np.empty((len(frames), 0, 3), dtype=np.int64)

    path_totals = np.zeros((len(frames), topology.n_edges, 3), dtype=np.int64)
    for edge_index, (begin, end) in enumerate(edge_slices):
        if end > begin:
            path_totals[:, edge_index, :] = np.sum(
                segment_shifts[:, begin:end, :], axis=1, dtype=np.int64
            )

    vertices = tuple(int(value) for value in topology.vertex_atom_indices)
    vertex_local = {atom: index for index, atom in enumerate(vertices)}

    # Canonical->selected wrapping gauge.  Traversal ordering here matches the
    # authoritative adapter because the topology adjacency sorts only by the
    # neighbor atom and edge index (its frame-local shift is not part of this
    # first gauge's ordering).
    adjacency: dict[int, list[tuple[int, int]]] = {vertex: [] for vertex in vertices}
    for edge_index, edge in enumerate(topology.edges):
        adjacency[int(edge.key.vertex_i)].append((int(edge.key.vertex_j), edge_index))
        adjacency[int(edge.key.vertex_j)].append((int(edge.key.vertex_i), edge_index))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], item[1]))

    canonical_gauge = np.zeros((len(frames), len(vertices), 3), dtype=np.int64)
    assigned_atoms: set[int] = set()
    for root in vertices:
        if root in assigned_atoms:
            continue
        assigned_atoms.add(root)
        queue: deque[int] = deque([root])
        while queue:
            source = queue.popleft()
            source_local = vertex_local[source]
            for target, edge_index in adjacency[source]:
                if target in assigned_atoms:
                    continue
                edge = topology.edges[edge_index]
                if source == int(edge.key.vertex_i):
                    canonical = np.asarray(edge.key.image_shift, dtype=np.int64)
                    frame_shift = path_totals[:, edge_index, :]
                else:
                    canonical = -np.asarray(edge.key.image_shift, dtype=np.int64)
                    frame_shift = -path_totals[:, edge_index, :]
                canonical_gauge[:, vertex_local[target], :] = (
                    canonical_gauge[:, source_local, :] + frame_shift - canonical
                )
                assigned_atoms.add(target)
                queue.append(target)

    display_shifts = np.empty_like(path_totals)
    for edge_index, edge in enumerate(topology.edges):
        i = vertex_local[int(edge.key.vertex_i)]
        j = vertex_local[int(edge.key.vertex_j)]
        canonical = np.asarray(edge.key.image_shift, dtype=np.int64)
        display_shifts[:, edge_index, :] = (
            canonical - canonical_gauge[:, i, :] + canonical_gauge[:, j, :]
        )
    if not np.array_equal(display_shifts, path_totals):
        raise GraphAdapterError(
            "Selected frame atomic paths are incompatible with the canonical framework winding."
        )
    if not np.array_equal(
        display_shifts[0], np.asarray(first_view.edge_image_shifts, dtype=np.int64)
    ):
        raise GraphAdapterError(
            "Batched projected framework reconstruction disagrees with the authoritative first-frame adapter."
        )

    # The normalized graph gauge used by framework registration sorts adjacency
    # by (neighbor, shift, edge_index).  If parallel edges connect the same pair,
    # shift ordering can be frame-dependent; retain the exact frame-local path in
    # that uncommon multiedge case.
    endpoint_pairs: set[tuple[int, int]] = set()
    for source, target in np.asarray(first_view.edge_endpoints, dtype=np.int64):
        pair = (min(int(source), int(target)), max(int(source), int(target)))
        if pair in endpoint_pairs:
            return None
        endpoint_pairs.add(pair)

    endpoints = np.asarray(first_view.edge_endpoints, dtype=np.int64)
    node_adjacency: list[list[tuple[int, int, int]]] = [list() for _ in vertices]
    for edge_index, (source, target) in enumerate(endpoints):
        i, j = int(source), int(target)
        if i == j:
            continue
        node_adjacency[i].append((j, edge_index, +1))
        node_adjacency[j].append((i, edge_index, -1))
    for values in node_adjacency:
        values.sort(key=lambda item: (item[0], item[1]))

    lift_gauge = np.zeros((len(frames), len(vertices), 3), dtype=np.int64)
    component = np.full(len(vertices), -1, dtype=np.int64)
    assigned = np.zeros(len(vertices), dtype=bool)
    component_id = 0
    for root in range(len(vertices)):
        if assigned[root]:
            continue
        assigned[root] = True
        component[root] = component_id
        queue_local: deque[int] = deque([root])
        while queue_local:
            source = queue_local.popleft()
            for target, edge_index, orientation in node_adjacency[source]:
                if assigned[target]:
                    continue
                directed = display_shifts[:, edge_index, :]
                if orientation < 0:
                    directed = -directed
                lift_gauge[:, target, :] = lift_gauge[:, source, :] + directed
                assigned[target] = True
                component[target] = component_id
                queue_local.append(target)
        component_id += 1

    residual = np.asarray(display_shifts, dtype=np.int64).copy()
    for edge_index, (source, target) in enumerate(endpoints):
        residual[:, edge_index, :] += (
            lift_gauge[:, int(source), :] - lift_gauge[:, int(target), :]
        )
    reference_residual = np.asarray(residual[0], dtype=np.int64)
    if not np.all(residual == reference_residual[None, :, :]):
        return None

    vertex_array = np.asarray(vertices, dtype=np.int64)
    vertex_fractional = np.asarray(wrapped[:, vertex_array, :], dtype=np.float64)
    lifted = vertex_fractional + lift_gauge
    for current_component in range(component_id):
        members = np.flatnonzero(component == current_component)
        root = int(members[0])
        anchor_atom = int(vertices[root])
        if collection.is_trajectory:
            target = np.asarray(
                collection.fractional_positions[frame_array, anchor_atom], dtype=np.float64
            )
            delta = target - lifted[:, root, :]
            global_shift = np.rint(delta).astype(np.int64)
            if not np.allclose(delta, global_shift, rtol=0.0, atol=2.0e-8):
                return None
        else:
            global_shift = -np.floor(lifted[:, root, :]).astype(np.int64)
        lifted[:, members, :] += global_shift[:, None, :]

    # Exact first-frame equivalence guards the bulk path against accidental
    # divergence in wrapping/gauge conventions.
    first_lifted, first_residual = _lifted_fractional_graph(
        collection, int(frames[0]), first_view
    )
    if not np.array_equal(reference_residual, np.asarray(first_residual, dtype=np.int64)):
        raise GraphAdapterError("Batched framework residual shifts disagree with the reference adapter.")
    if not np.allclose(lifted[0], first_lifted, rtol=0.0, atol=1.0e-12):
        raise GraphAdapterError("Batched framework lift disagrees with the reference adapter.")

    return (
        first_view,
        [np.asarray(lifted[index], dtype=np.float64) for index in range(len(frames))],
        reference_residual,
    )


def _prepare_registered_framework_frames(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frames: tuple[int, ...],
    display_mode: FrameworkGraphDisplayMode | str,
    geometry_cache: _FrameworkGeometryCache,
    scheduler: DensitySceneScheduler,
    max_threads: int,
    task_id: str,
) -> tuple[DecoratedGraphView, list[FloatArray], IntArray]:
    """Prepare independent frame geometry, retaining only canonical view metadata."""

    mode = FrameworkGraphDisplayMode(display_mode)
    if mode is FrameworkGraphDisplayMode.PROJECTED:
        bulk = _bulk_static_cell_projected_framework_lifts(
            collection, topology, frames=frames
        )
        if bulk is not None:
            geometry_cache.record_bulk_static_projected(len(frames))
            return bulk

    resources = _preprocessing_resource_estimate(
        task_id=task_id,
        frame_count=len(frames),
        item_count=max(1, topology.n_vertices + topology.n_edges),
        max_threads=max_threads,
        retained=True,
        backend=f"framework_registration:{mode.value}",
    )

    def build_one(frame: int) -> _PreparedFrameworkFrame:
        return geometry_cache.get_or_build(
            collection,
            topology,
            frame_index=int(frame),
            display_mode=mode,
        )

    def build_batched(lease: DensityWorkerLease) -> list[_PreparedFrameworkFrame]:
        worker_count = max(1, min(int(lease.workers), len(frames)))
        target_batches = max(1, min(len(frames), worker_count * 4))
        chunk_size = max(1, (len(frames) + target_batches - 1) // target_batches)
        batches = tuple(frames[start:start + chunk_size] for start in range(0, len(frames), chunk_size))

        def build_chunk(batch: tuple[int, ...]) -> list[_PreparedFrameworkFrame]:
            return [build_one(frame) for frame in batch]

        nested = lease.thread_map(build_chunk, batches)
        return [item for batch in nested for item in batch]

    prepared = _run_preprocessing_task(
        scheduler,
        resources,
        build_batched,
    )
    assert prepared
    reference = prepared[0]
    for position, current in enumerate(prepared[1:], start=1):
        if (
            current.view.node_keys != reference.view.node_keys
            or current.view.edge_keys != reference.view.edge_keys
        ):
            raise GraphAdapterError(
                "Selected frames do not preserve framework graph identity "
                f"(first mismatch at collection frame {frames[position]})."
            )
        if not np.array_equal(current.residual_shifts, reference.residual_shifts):
            raise GraphAdapterError(
                "Selected frames do not preserve normalized periodic edge winding "
                f"(first mismatch at collection frame {frames[position]})."
            )
    return (
        reference.view,
        [np.asarray(item.lifted_fractional, dtype=np.float64) for item in prepared],
        np.asarray(reference.residual_shifts, dtype=np.int64),
    )

def _display_cell(
    collection: AtomisticFrameCollection,
    frames: tuple[int, ...],
    reference_frame: int,
    mode: Literal["reference", "mean"],
) -> FloatArray:
    if mode == "reference":
        cell = np.asarray(collection.cells[reference_frame], dtype=np.float64)
    else:
        cell = np.mean(
            np.asarray(collection.cells[list(frames)], dtype=np.float64), axis=0
        )
    if np.any(~np.isfinite(cell)) or abs(float(np.linalg.det(cell))) <= 1.0e-12:
        raise GraphAdapterError("The selected display cell is finite but singular.")
    return cell


def _display_fractional_coordinates(
    lifted_fractional: FloatArray,
    frames: tuple[int, ...],
    registration_view: ConsumerCoordinateView,
) -> FloatArray:
    """Transform arbitrary lifted source-fractional coordinates through C0B."""

    return np.asarray(
        registration_view.transform_fractional(
            lifted_fractional,
            frame_indices=frames,
            output="display_fractional",
        ),
        dtype=np.float64,
    )


def _edge_segments_from_view(
    display_fractional: FloatArray,
    view: DecoratedGraphView,
    residual_shifts: IntArray,
    frames: tuple[int, ...],
    registration_view: ConsumerCoordinateView,
) -> FloatArray:
    endpoints = np.asarray(view.edge_endpoints, dtype=np.int64)
    segments = np.empty(
        (display_fractional.shape[0], len(endpoints), 2, 3), dtype=np.float64
    )
    segments[:, :, 0, :] = display_fractional[:, endpoints[:, 0], :]
    display_shifts = registration_view.transform_lattice_shifts(
        np.asarray(residual_shifts, dtype=np.float64),
        frame_indices=frames,
    )
    segments[:, :, 1, :] = (
        display_fractional[:, endpoints[:, 1], :] + display_shifts
    )
    return segments


def _canonicalize_mean_framework(
    mean_positions: FloatArray,
    display_cell: FloatArray,
    edge_endpoints: IntArray,
    residual_shifts: IntArray,
    pbc: BoolArray,
) -> tuple[FloatArray, IntArray]:
    """Wrap mean nodes into the canonical cell without changing edge vectors.

    If an unwrapped node ``i`` is shifted by ``-q_i H`` into the canonical
    cell, the source-to-target edge label transforms as

    ``n'_e = n_e + q_target - q_source``.

    The target-minus-source sign is essential.  Reversing it creates spurious
    long periodic connections in the rendered framework.
    """
    cell = np.asarray(display_cell, dtype=np.float64)
    inverse = np.linalg.inv(cell)
    fractional = np.asarray(mean_positions, dtype=np.float64) @ inverse
    node_shifts = np.zeros_like(fractional, dtype=np.int64)
    wrapped = np.array(fractional, copy=True)
    for axis, periodic in enumerate(np.asarray(pbc, dtype=bool)):
        if periodic:
            shift = np.floor(wrapped[:, axis]).astype(np.int64)
            node_shifts[:, axis] = shift
            wrapped[:, axis] -= shift
    endpoints = np.asarray(edge_endpoints, dtype=np.int64)
    transformed = (
        np.asarray(residual_shifts, dtype=np.int64)
        + node_shifts[endpoints[:, 1]]
        - node_shifts[endpoints[:, 0]]
    )
    return wrapped @ cell, transformed


def _states_for_atomic_mean_graph(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    frames: tuple[int, ...],
) -> list[AtomicConnectivityState]:
    if isinstance(connectivity, AtomicConnectivityState):
        return [connectivity for _ in frames]
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise TypeError(
            "atomic_connectivity must be an AtomicConnectivityState or AtomicConnectivityResult."
        )
    frame_to_position = {
        int(frame): position
        for position, frame in enumerate(connectivity.frame_indices)
    }
    missing = [frame for frame in frames if frame not in frame_to_position]
    if missing:
        raise GraphAdapterError(
            "atomic_connectivity does not cover all selected scene frames."
        )
    states: list[AtomicConnectivityState] = []
    for frame in frames:
        position = int(frame_to_position[int(frame)])
        state_id = int(connectivity.frame_state_ids[position])
        states.append(connectivity.states[state_id])
    return states


def _connectivity_state_map(
    connectivity: AtomicConnectivityState | AtomicConnectivityResult | None,
    frames: tuple[int, ...],
) -> Mapping[int, AtomicConnectivityState] | None:
    """Hoist trajectory-wide connectivity frame lookup out of category loops."""

    if connectivity is None:
        return None
    if isinstance(connectivity, AtomicConnectivityState):
        return MappingProxyType({int(frame): connectivity for frame in frames})
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise TypeError(
            "atomic_connectivity must be an AtomicConnectivityState or AtomicConnectivityResult."
        )
    position_by_frame = {
        int(frame): position for position, frame in enumerate(connectivity.frame_indices)
    }
    missing = [int(frame) for frame in frames if int(frame) not in position_by_frame]
    if missing:
        raise GraphAdapterError(
            "atomic_connectivity does not cover all selected scene frames."
        )
    return MappingProxyType(
        {
            int(frame): connectivity.states[
                int(connectivity.frame_state_ids[position_by_frame[int(frame)]])
            ]
            for frame in frames
        }
    )


def _registered_atomic_display_fractional(
    *,
    frames: tuple[int, ...],
    atom_indices: tuple[int, ...],
    registration_view: ConsumerCoordinateView,
) -> FloatArray:
    """Return atoms in the shared display gauge resolved by C0B."""

    return np.asarray(
        registration_view.display_fractional(
            frame_indices=frames, atom_indices=atom_indices
        ),
        dtype=np.float64,
    )


def _periodic_frechet_mean(
    fractional_samples: FloatArray,
    *,
    weights: FloatArray,
    cell: FloatArray,
    pbc: BoolArray,
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


def _prepare_atomic_mean_graph(
    collection: AtomisticFrameCollection,
    *,
    frames: tuple[int, ...],
    weights: FloatArray,
    display_cell: FloatArray,
    registration_view: ConsumerCoordinateView,
    atomic_connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    options: AtomicMeanGraphOptions,
    worker_lease: DensityWorkerLease | None = None,
    state_by_frame: Mapping[int, AtomicConnectivityState] | None = None,
) -> AtomicMeanGraph:
    states = (
        [state_by_frame[int(frame)] for frame in frames]
        if state_by_frame is not None
        else _states_for_atomic_mean_graph(collection, atomic_connectivity, frames)
    )
    reference = states[0]
    atom_indices = tuple(int(v) for v in reference.active_atom_indices.tolist())
    atomic_numbers = np.asarray(reference.active_atomic_numbers, dtype=np.int64)
    pbc = np.asarray(reference.pbc, dtype=bool)
    for state in states[1:]:
        if not np.array_equal(state.active_atom_indices, reference.active_atom_indices):
            raise GraphAdapterError(
                "Atomic mean graph currently requires a consistent active atom scope across frames."
            )
        if not np.array_equal(
            state.active_atomic_numbers, reference.active_atomic_numbers
        ):
            raise GraphAdapterError(
                "Atomic mean graph currently requires consistent active atomic numbers across frames."
            )
        if not np.array_equal(state.pbc, reference.pbc):
            raise GraphAdapterError(
                "Atomic mean graph currently requires consistent periodic boundary conditions across frames."
            )

    display_fractional = _registered_atomic_display_fractional(
        frames=frames,
        atom_indices=atom_indices,
        registration_view=registration_view,
    )
    mean_policy = PeriodicMeanPolicy(certified_fast_path=True)

    def solve_mean(local: int):
        return periodic_frechet_mean_diagnostic(
            display_fractional[:, int(local), :],
            weights=weights,
            cell=display_cell,
            pbc=pbc,
            policy=mean_policy,
        )

    mean_indices = tuple(range(len(atom_indices)))
    mean_diagnostics = tuple(
        worker_lease.thread_map(solve_mean, mean_indices)
        if worker_lease is not None and len(mean_indices) > 1
        else [solve_mean(local) for local in mean_indices]
    )
    mean_positions = np.asarray(
        [diagnostic.mean_cartesian for diagnostic in mean_diagnostics],
        dtype=np.float64,
    )

    # Pair occupancy used to build a Python set of ~E tuples for every frame,
    # then update two Python dictionaries edge-by-edge.  Long LTA trajectories
    # can contain thousands of canonical states and millions of repeated edge
    # visits.  Encode a global atom pair as ``i * n_atoms + j`` and update dense
    # 1-D accumulators instead.  Each state's pair-code array is cached by object
    # identity because cataloged frame states are shared immutable objects.
    #
    # The outer loop remains in authoritative frame order and each code is unique
    # within a canonical state, so every occupancy receives the exact same ordered
    # sequence of IEEE-754 additions as the previous implementation.
    pair_capacity = int(collection.n_atoms) * int(collection.n_atoms)
    pair_occupancy_array = np.zeros(pair_capacity, dtype=np.float64)
    pair_presence_array = np.zeros(pair_capacity, dtype=np.int64)
    pair_code_cache: dict[int, IntArray] = {}
    atom_count = int(collection.n_atoms)
    for local, state in enumerate(states):
        cache_key = id(state)
        pair_codes = pair_code_cache.get(cache_key)
        if pair_codes is None:
            endpoints = np.asarray(state.edge_atom_indices, dtype=np.int64)
            pair_codes = (
                endpoints[:, 0] * atom_count + endpoints[:, 1]
                if endpoints.size
                else np.empty((0,), dtype=np.int64)
            )
            pair_code_cache[cache_key] = pair_codes
        if pair_codes.size:
            pair_occupancy_array[pair_codes] += float(weights[local])
            pair_presence_array[pair_codes] += 1

    candidate_codes = np.flatnonzero(pair_presence_array > 0)
    kept_pairs: list[tuple[int, int]] = []
    occupancies: list[float] = []
    for code in candidate_codes:
        occupancy = float(pair_occupancy_array[int(code)])
        keep = occupancy >= options.occupancy_threshold
        if options.mode == "persistent":
            keep = int(pair_presence_array[int(code)]) == len(frames)
        if keep:
            pair_code = int(code)
            kept_pairs.append((pair_code // atom_count, pair_code % atom_count))
            occupancies.append(occupancy)

    atom_to_local = {atom: local for local, atom in enumerate(atom_indices)}
    edge_endpoints = (
        np.asarray(
            [[atom_to_local[left], atom_to_local[right]] for left, right in kept_pairs],
            dtype=np.int64,
        ).reshape((-1, 2))
        if kept_pairs
        else np.empty((0, 2), dtype=np.int64)
    )
    if len(kept_pairs):
        raw = mean_positions[edge_endpoints[:, 1]] - mean_positions[edge_endpoints[:, 0]]
        _vectors, _distances, edge_shifts_raw = minimum_image_geometry(
            raw, cell=display_cell, pbc=pbc
        )
        edge_shifts = np.asarray(edge_shifts_raw, dtype=np.int64).reshape((-1, 3))
    else:
        edge_shifts = np.empty((0, 3), dtype=np.int64)
    occupancies_array = (
        np.asarray(occupancies, dtype=np.float64)
        if occupancies
        else np.empty((0,), dtype=np.float64)
    )

    return AtomicMeanGraph(
        atom_indices=atom_indices,
        atomic_numbers=atomic_numbers,
        display_positions=mean_positions,
        edge_endpoints=edge_endpoints,
        edge_image_shifts=edge_shifts,
        edge_occupancies=occupancies_array,
        display_cell=display_cell,
        pbc=pbc,
        mode=options.mode,
        metadata={
            "periodic_mean_solver": "deterministic_multistart_frechet_v1",
            "periodic_mean_converged": tuple(
                value.mean_converged for value in mean_diagnostics
            ),
            "periodic_mean_ambiguous": tuple(
                value.mean_ambiguity_detected for value in mean_diagnostics
            ),
            "periodic_mean_iteration_counts": tuple(
                value.iteration_count for value in mean_diagnostics
            ),
            "periodic_mean_candidate_solution_counts": tuple(
                value.candidate_solution_count for value in mean_diagnostics
            ),
            "consumer_registration_signature": registration_view.signature,
            "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
        },
    )


def _mean_framework_view(
    reference: DecoratedGraphView,
    mean_positions: FloatArray,
    display_cell: FloatArray,
    residual_shifts: IntArray,
    *,
    frames: tuple[int, ...],
    registration: SpatialRegistrationMode,
    display_cell_mode: str,
) -> DecoratedGraphView:
    metadata = dict(reference.metadata)
    metadata.update(
        {
            "adapter_schema_version": FRAMEWORK_DYNAMICS_SCENE_SCHEMA,
            "dynamic_geometry_kind": "registered_mean_framework",
            "source_frame_indices": frames,
            "registration_mode": registration.value,
            "display_cell_mode": display_cell_mode,
            "mean_weighting": "uniform",
        }
    )
    return DecoratedGraphView(
        node_keys=reference.node_keys,
        edge_keys=reference.edge_keys,
        edge_endpoints=reference.edge_endpoints,
        node_positions_3d=mean_positions,
        edge_image_shifts=residual_shifts,
        cell=display_cell,
        pbc=reference.pbc,
        node_attributes=reference.node_attributes,
        edge_attributes=reference.edge_attributes,
        directed=reference.directed,
        multigraph=reference.multigraph,
        metadata=metadata,
    )


def _atomic_density_label(
    selection: AtomicDensitySelection,
    atoms: tuple[int, ...],
    field_index: int,
) -> str:
    if selection.label is not None:
        return selection.label
    if len(atoms) == 1:
        return f"atom {atoms[0]} density"
    if len(selection.species) == 1 and not selection.atom_indices:
        selector = selection.species[0]
        number = (
            int(selector) if isinstance(selector, int) else ase_atomic_numbers[selector]
        )
        return f"{chemical_symbols[number]} density"
    return f"atomic density {field_index + 1}"


def _phase_a_field(
    *,
    field_key: str,
    source_kind: str,
    construction_order: int,
    sample_count_upper: int,
    logical_node_count_upper: int,
    store_sample_positions: bool,
    smoothing_operator: str,
    storage_backend: str = "dense",
    block_shape: tuple[int, int, int] = (16, 16, 16),
    limits: DensityPlanningLimits | None = None,
) -> DensityPhaseAFieldPlan:
    logical = int(logical_node_count_upper)
    samples = int(sample_count_upper)
    if storage_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}:
        if limits is None:
            raise GraphAdapterError("Sparse/auto Phase-A planning requires density limits.")
        block_volume = int(np.prod(block_shape, dtype=object))
        retained_upper = (
            8 * limits.max_density_stored_block_values
            + 24 * limits.max_density_blocks
            + limits.max_density_stored_block_values
            + (24 * samples if store_sample_positions else 0)
        )
        auto = storage_backend == AUTO_BACKEND
        return DensityPhaseAFieldPlan(
            field_key=field_key,
            source_kind=source_kind,
            construction_order=construction_order,
            sample_count_upper=samples,
            sample_bytes_upper=sample_byte_count(samples),
            logical_node_count_upper=logical,
            cic_insertions_upper=8 * samples,
            stencil_value_count_upper=limits.max_density_stencil_values,
            nonzero_node_count_upper=min(logical, limits.max_density_nonzero_nodes),
            stored_value_count_upper=limits.max_density_stored_block_values,
            stored_block_count_upper=limits.max_density_blocks,
            kernel_pair_count_upper=limits.max_density_kernel_pairs,
            component_value_count_upper=(
                limits.max_density_component_values if auto else 0
            ),
            mesh_cell_count_upper=(limits.max_density_mesh_cells if auto else 0),
            mesh_face_count_upper=(limits.max_density_mesh_faces if auto else 0),
            render_point_count_upper=(
                limits.max_density_render_points if auto else 0
            ),
            retained_bytes_upper=max(
                retained_upper,
                limits.max_density_total_peak_bytes if auto else retained_upper,
            ),
            transient_bytes_upper=limits.max_density_total_peak_bytes,
            metadata={
                "backend": storage_backend,
                "operator": smoothing_operator,
                "block_shape": list(block_shape),
                "block_volume": block_volume,
                "auto_candidate_bounds": auto,
            },
        )
    component_upper = 2 * logical
    return DensityPhaseAFieldPlan(
        field_key=field_key,
        source_kind=source_kind,
        construction_order=construction_order,
        sample_count_upper=samples,
        sample_bytes_upper=sample_byte_count(samples),
        logical_node_count_upper=logical,
        cic_insertions_upper=8 * samples,
        stencil_value_count_upper=(
            logical if smoothing_operator == DISCRETE_PERIODIZED_OPERATOR else 0
        ),
        nonzero_node_count_upper=logical,
        stored_value_count_upper=logical,
        stored_block_count_upper=0,
        kernel_pair_count_upper=0,
        component_value_count_upper=component_upper,
        mesh_cell_count_upper=logical,
        mesh_face_count_upper=15 * logical,
        render_point_count_upper=0,
        retained_bytes_upper=dense_retained_bytes(
            logical,
            sample_count=samples,
            store_sample_positions=store_sample_positions,
        ),
        transient_bytes_upper=dense_transient_bytes(logical, samples),
        metadata={"backend": "dense", "operator": smoothing_operator},
    )


def _framework_edge_sample_count(
    segments: FloatArray,
    cell: FloatArray,
    spacing: float,
    *,
    maximum: int,
) -> int:
    count = 0
    for frame_segments in np.asarray(segments, dtype=np.float64):
        for segment in frame_segments:
            length = float(np.linalg.norm((segment[1] - segment[0]) @ cell))
            if length <= 1.0e-14:
                continue
            count += framework_edge_quadrature_count(length, spacing)
            if count > maximum:
                raise GraphComplexityError(
                    f"Phase A framework edge planning requires more than "
                    f"max_density_samples={maximum} quadrature samples."
                )
    return count


def _build_density_phase_a(
    collection: AtomisticFrameCollection,
    *,
    frames: tuple[int, ...],
    atomic_selections: tuple[AtomicDensitySelection, ...],
    atomic_options: AtomicDensityOptions,
    framework_options: FrameworkDensityOptions | None,
    framework_vertex_count: int,
    framework_edge_segments: FloatArray | None,
    display_cell: FloatArray,
    limits: DensityPlanningLimits,
) -> tuple[DensityPhaseAFieldPlan, ...]:
    fields: list[DensityPhaseAFieldPlan] = []
    order = 0
    n_atomic = len(atomic_selections)
    atomic_sparse = atomic_options.storage_options.grid_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
    atomic_budget = limits.max_density_voxels // max(1, n_atomic)
    atomic_explicit_nodes = (
        None
        if atomic_options.grid_shape is None
        else int(np.prod(atomic_options.grid_shape, dtype=object))
    )
    for index, selection in enumerate(atomic_selections):
        atoms = selection.resolve(collection)
        fields.append(
            _phase_a_field(
                field_key=f"atomic-density-{index}",
                source_kind="atomic_occupancy",
                construction_order=order,
                sample_count_upper=len(frames) * len(atoms),
                logical_node_count_upper=(
                    atomic_explicit_nodes
                    if atomic_explicit_nodes is not None
                    else (
                        int(np.iinfo(np.int64).max)
                        if atomic_sparse
                        else atomic_budget
                    )
                ),
                store_sample_positions=atomic_options.store_sample_positions,
                smoothing_operator=atomic_options.kernel_options.smoothing_operator,
                storage_backend=atomic_options.storage_options.grid_backend,
                block_shape=atomic_options.storage_options.local_block_shape,
                limits=limits,
            )
        )
        order += 1
    if framework_options is not None:
        n_framework = int(framework_options.include_vertex_density) + int(
            framework_options.include_edge_density
        )
        framework_budget = limits.max_density_voxels // max(1, n_framework)
        framework_sparse = (
            framework_options.storage_options.grid_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
        )
        framework_explicit_nodes = (
            None
            if framework_options.grid_shape is None
            else int(np.prod(framework_options.grid_shape, dtype=object))
        )
        if framework_options.include_vertex_density:
            fields.append(
                _phase_a_field(
                    field_key="framework-vertex-density",
                    source_kind="framework_vertex_occupancy",
                    construction_order=order,
                    sample_count_upper=len(frames) * framework_vertex_count,
                    logical_node_count_upper=(
                        framework_explicit_nodes
                        if framework_explicit_nodes is not None
                        else (
                            int(np.iinfo(np.int64).max)
                            if framework_sparse
                            else framework_budget
                        )
                    ),
                    store_sample_positions=framework_options.store_sample_positions,
                    smoothing_operator=(
                        framework_options.kernel_options.smoothing_operator
                    ),
                    storage_backend=framework_options.storage_options.grid_backend,
                    block_shape=framework_options.storage_options.local_block_shape,
                    limits=limits,
                )
            )
            order += 1
        if framework_options.include_edge_density:
            if framework_edge_segments is None:
                raise GraphAdapterError(
                    "Framework edge segments are required for Phase A."
                )
            edge_samples = (
                limits.max_density_samples
                if framework_options.edge_sample_spacing_mode == "auto"
                else _framework_edge_sample_count(
                    framework_edge_segments,
                    display_cell,
                    framework_options.edge_sample_spacing,
                    maximum=limits.max_density_samples,
                )
            )
            fields.append(
                _phase_a_field(
                    field_key="framework-edge-length-density",
                    source_kind="framework_edge_length",
                    construction_order=order,
                    sample_count_upper=edge_samples,
                    logical_node_count_upper=(
                        framework_explicit_nodes
                        if framework_explicit_nodes is not None
                        else (
                            int(np.iinfo(np.int64).max)
                            if framework_sparse
                            else framework_budget
                        )
                    ),
                    store_sample_positions=framework_options.store_sample_positions,
                    smoothing_operator=(
                        framework_options.kernel_options.smoothing_operator
                    ),
                    storage_backend=framework_options.storage_options.grid_backend,
                    block_shape=framework_options.storage_options.local_block_shape,
                    limits=limits,
                )
            )
    return validate_density_phase_a(fields, limits)


def _phase_b_field(
    *,
    field_key: str,
    source_kind: str,
    construction_order: int,
    sample_count: int,
    grid_shape: tuple[int, int, int],
    occupied_indices: IntArray,
    store_sample_positions: bool,
    smoothing_operator: str,
    gaussian_bandwidth: float,
    metadata: Mapping[str, Any],
) -> DensityPhaseBFieldPlan:
    logical = int(np.prod(grid_shape, dtype=object))
    component_values = int(np.prod(np.asarray(grid_shape, dtype=object) + 1))
    return DensityPhaseBFieldPlan(
        field_key=field_key,
        source_kind=source_kind,
        construction_order=construction_order,
        sample_count=sample_count,
        sample_bytes=sample_byte_count(sample_count),
        grid_shape=grid_shape,
        logical_node_count=logical,
        occupied_cic_node_indices=occupied_indices,
        nonzero_node_count_upper=logical,
        stored_value_count=logical,
        stored_block_count=0,
        stencil_value_count=(
            logical
            if smoothing_operator == DISCRETE_PERIODIZED_OPERATOR
            and gaussian_bandwidth > 0.0
            else 0
        ),
        kernel_pair_count=0,
        component_value_count=component_values,
        mesh_cell_count=logical,
        mesh_face_count_upper=15 * logical,
        render_point_count_upper=0,
        planning_bytes=int(occupied_indices.nbytes),
        retained_bytes=dense_retained_bytes(
            logical,
            sample_count=sample_count,
            store_sample_positions=store_sample_positions,
        ),
        transient_bytes_upper=dense_transient_bytes(logical, sample_count),
        metadata={
            "backend": "dense",
            "operator": smoothing_operator,
            **dict(metadata),
        },
    )


def _registered_atomic_density_fractional(
    *,
    frames: tuple[int, ...],
    atoms: tuple[int, ...],
    registration_view: ConsumerCoordinateView,
) -> FloatArray:
    return np.asarray(
        registration_view.display_fractional(
            frame_indices=frames, atom_indices=atoms
        ),
        dtype=np.float64,
    )


def _plan_atomic_phase_b(
    collection: AtomisticFrameCollection,
    *,
    frames: tuple[int, ...],
    weights: FloatArray,
    display_cell: FloatArray,
    registration_view: ConsumerCoordinateView,
    selections: tuple[AtomicDensitySelection, ...],
    options: AtomicDensityOptions,
    limits: DensityPlanningLimits,
    hybrid_runtime_plans: dict[str, DensityHybridRealizationPlan] | None = None,
    hybrid_runtime_artifacts: dict[str, tuple[Any, Any, Any, Any]] | None = None,
    resolved_plans: dict[str, AtomicDensityResolvedPlan] | None = None,
) -> list[DensityBackendCandidateSet]:
    """Build forced or automatic exact Phase-B candidate sets for atomic fields."""

    if not selections:
        return []
    requested_backend = options.storage_options.grid_backend
    sparse_resolution = requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
    per_field_budget = limits.max_density_voxels // len(selections)
    candidates: list[DensityBackendCandidateSet] = []
    for index, selection in enumerate(selections):
        field_key = f"atomic-density-{index}"
        atoms = selection.resolve(collection)
        label = _atomic_density_label(selection, atoms, index)
        display_fractional = _registered_atomic_density_fractional(
            frames=frames,
            atoms=atoms,
            registration_view=registration_view,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            numerics = resolve_density_numerics(
                display_cell,
                options=options,
                fractional_by_frame=display_fractional,
                frame_weights=weights,
                pbc=np.asarray(collection.pbc, dtype=bool),
                max_voxels=(
                    int(np.iinfo(np.int64).max)
                    if sparse_resolution
                    else per_field_budget
                ),
                field_label=label,
            )
        if resolved_plans is not None:
            resolved_plans[field_key] = AtomicDensityResolvedPlan(
                field_key=field_key,
                atom_indices=tuple(atoms),
                label=label,
                numerics=numerics,
                registration_signature=str(registration_view.signature),
                options=options,
            )
        folded = display_fractional - np.floor(display_fractional)
        flat_fractional = folded.reshape((-1, 3))
        sample_count = len(frames) * len(atoms)
        common_metadata = {
            "label": label,
            "selected_atom_indices": atoms,
            "gaussian_bandwidth": numerics.gaussian_bandwidth,
            "smearing_definition": numerics.smearing_definition,
            "broadening_metric": options.resolution_options.broadening_metric,
            "effective_artificial_rms": (
                None
                if numerics.broadening_diagnostic is None
                else numerics.broadening_diagnostic.effective_rms
            ),
            "adaptive_target_width": numerics.adaptive_target_width,
            "adaptive_target_achieved": numerics.adaptive_target_achieved,
            "consumer_registration_signature": registration_view.signature,
            "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
        }

        dense_plan: DensityPhaseBFieldPlan | None = None
        sparse_plan: DensityPhaseBFieldPlan | None = None
        dense_error: str | None = None
        sparse_error: str | None = None
        if requested_backend in {DENSE_BACKEND, AUTO_BACKEND}:
            try:
                occupied = occupied_cic_node_indices(
                    flat_fractional,
                    numerics.grid_shape,
                    max_planning_bytes=limits.max_density_planning_bytes,
                )
                dense_plan = _phase_b_field(
                    field_key=field_key,
                    source_kind="atomic_occupancy",
                    construction_order=index,
                    sample_count=sample_count,
                    grid_shape=numerics.grid_shape,
                    occupied_indices=occupied,
                    store_sample_positions=options.store_sample_positions,
                    smoothing_operator=options.kernel_options.smoothing_operator,
                    gaussian_bandwidth=numerics.gaussian_bandwidth,
                    metadata=common_metadata,
                )
            except GraphComplexityError as exc:
                dense_error = str(exc)
        if requested_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}:
            try:
                sample_weights = np.repeat(weights, len(atoms))
                sparse_plan = _sparse_phase_b_field_from_samples(
                    PeriodicWeightedSamples3D(
                        fractional_positions=flat_fractional,
                        weights=sample_weights,
                        sample_group_ids=np.tile(
                            np.arange(len(atoms), dtype=np.int64), len(frames)
                        ),
                        source_provenance=DensitySourceProvenance(
                            source_kind="atomic_occupancy", atom_indices=atoms
                        ),
                        total_measure=float(len(atoms)),
                        measure_kind="occupancy",
                        measure_units="count",
                    ),
                    field_key=field_key,
                    source_kind="atomic_occupancy",
                    construction_order=index,
                    grid_shape=numerics.grid_shape,
                    display_cell=display_cell,
                    gaussian_bandwidth=numerics.gaussian_bandwidth,
                    smoothing_operator=options.kernel_options.smoothing_operator,
                    broadening_metric=options.resolution_options.broadening_metric,
                    block_shape=options.storage_options.local_block_shape,
                    store_sample_positions=options.store_sample_positions,
                    optimization_options=options.optimization_options,
                    limits=limits,
                    remaining_planning_bytes=limits.max_density_planning_bytes,
                    metadata={
                        "kernel_tail_tolerance": options.kernel_options.kernel_tail_tolerance,
                        **common_metadata,
                    },
                    hybrid_runtime_plans=hybrid_runtime_plans,
                    hybrid_runtime_artifacts=hybrid_runtime_artifacts,
                )
            except GraphComplexityError as exc:
                sparse_error = str(exc)
        candidates.append(
            make_candidate_set(
                field_key=field_key,
                requested_backend=requested_backend,
                dense_plan=dense_plan,
                sparse_plan=sparse_plan,
                limits=limits,
                sparse_activation_fraction=(
                    options.storage_options.sparse_activation_fraction
                ),
                dense_error=dense_error,
                sparse_error=sparse_error,
            )
        )
    return candidates

def _stream_edge_occupied_nodes(
    segments: FloatArray,
    *,
    cell: FloatArray,
    spacing: float,
    grid_shape: tuple[int, int, int],
    max_samples: int,
    max_planning_bytes: int,
) -> tuple[int, IntArray]:
    pieces: list[IntArray] = []
    sample_count = 0
    piece_bytes = 0
    for frame_segments in np.asarray(segments, dtype=np.float64):
        for segment in frame_segments:
            start = segment[0]
            delta = segment[1] - segment[0]
            length = float(np.linalg.norm(delta @ cell))
            if length <= 1.0e-14:
                continue
            count = max(1, int(np.ceil(length / spacing)))
            sample_count += count
            if sample_count > max_samples:
                raise GraphComplexityError(
                    f"Phase B framework edge planning requires more than "
                    f"max_density_samples={max_samples} quadrature samples."
                )
            parameters = (np.arange(count, dtype=np.float64) + 0.5) / count
            points = start[None, :] + parameters[:, None] * delta[None, :]
            remaining_for_segment = max_planning_bytes - 3 * piece_bytes
            if remaining_for_segment <= 0:
                raise GraphComplexityError(
                    "Phase B framework edge index planning exceeds "
                    f"max_density_planning_bytes={max_planning_bytes}."
                )
            occupied = occupied_cic_node_indices(
                points,
                grid_shape,
                max_planning_bytes=remaining_for_segment,
            )
            pieces.append(occupied)
            piece_bytes += int(occupied.nbytes)
            if 3 * piece_bytes > max_planning_bytes:
                raise GraphComplexityError(
                    "Phase B framework edge index planning exceeds "
                    f"max_density_planning_bytes={max_planning_bytes}."
                )
    if not pieces:
        raise GraphAdapterError(
            "Framework edge-length density contains no nondegenerate segments."
        )
    combined = np.unique(np.concatenate(pieces)).astype(np.int64, copy=False)
    if piece_bytes + int(combined.nbytes) > max_planning_bytes:
        raise GraphComplexityError(
            "Phase B framework edge index planning exceeds "
            f"max_density_planning_bytes={max_planning_bytes}."
        )
    combined.setflags(write=False)
    return sample_count, combined


def _sparse_phase_b_field_from_samples(
    samples: PeriodicWeightedSamples3D,
    *,
    field_key: str,
    source_kind: str,
    construction_order: int,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    smoothing_operator: str,
    broadening_metric: str,
    block_shape: tuple[int, int, int],
    store_sample_positions: bool,
    optimization_options: DensityOptimizationOptions,
    limits: DensityPlanningLimits,
    remaining_planning_bytes: int,
    metadata: Mapping[str, Any],
    hybrid_runtime_plans: dict[str, DensityHybridRealizationPlan] | None = None,
    hybrid_runtime_artifacts: dict[str, tuple[Any, Any, Any, Any]] | None = None,
) -> DensityPhaseBFieldPlan:
    """Build one exact sparse Phase-B plan from registered weighted samples.

    The production ``hybrid`` path plans the same packed CIC source, exact
    support atlas, and mixed direct/FFT tile execution used by realization.
    Consequently ``kernel_pair_count`` is the actual direct-tile pair count,
    not the nominal all-direct contribution count.  The latter remains in
    metadata as ``exact_contribution_count`` for diagnostics.

    The explicit ``ld7`` compatibility path retains the historical streamed
    target-union planner and its nominal pair accounting.
    """

    if remaining_planning_bytes <= 0:
        raise GraphComplexityError(
            "Sparse framework Phase-B planning exceeds max_density_planning_bytes."
        )
    cic_function = (
        aggregate_periodic_cic_sparse
        if optimization_options.sparse_evaluation_mode == "reference"
        else aggregate_periodic_cic_sparse_optimized
    )
    cic = cic_function(
        samples,
        grid_shape,
        max_cic_contributions=8 * limits.max_density_samples,
        max_workspace_bytes=remaining_planning_bytes,
    )
    cic_workspace_upper = (
        estimate_periodic_cic_sparse_workspace_bytes(
            int(samples.fractional_positions.shape[0])
        )
        if optimization_options.sparse_evaluation_mode == "reference"
        else estimate_periodic_cic_sparse_optimized_workspace_bytes(
            int(samples.fractional_positions.shape[0])
        )
    )
    support, support_cache_hit = get_periodic_gaussian_stencil_support(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=float(metadata.get("kernel_tail_tolerance", 1.0e-8)),
        max_candidate_contributions=limits.max_density_stencil_values * 64,
        max_workspace_bytes=remaining_planning_bytes,
        use_cache=(
            optimization_options.sparse_evaluation_mode == "optimized"
            and optimization_options.cache_stencil_supports
        ),
    )

    if optimization_options.sparse_realization_mode == "hybrid":
        source = pack_periodic_cic_source(
            cic,
            storage_block_shape=block_shape,
            max_source_blocks=limits.max_density_blocks,
            max_source_nodes=limits.max_density_nonzero_nodes,
            max_retained_bytes=remaining_planning_bytes,
        )
        routing, routing_cache_hit = get_periodic_kernel_block_routing(
            support,
            storage_block_shape=block_shape,
            max_stencil_offsets=limits.max_density_stencil_values,
            use_cache=optimization_options.cache_stencil_supports,
        )
        atlas = build_density_support_atlas(
            source,
            routing,
            fft_workers=optimization_options.hybrid_fft_workers,
        )
        hybrid_options = DensityHybridExecutorOptions(
            executor_mode="auto",
            compute_tile_shape=optimization_options.hybrid_compute_tile_shape,
            pair_chunk_size=optimization_options.sparse_pair_chunk_size,
            min_fft_source_nodes=optimization_options.hybrid_min_fft_source_nodes,
            fft_workers=optimization_options.hybrid_fft_workers,
            cache_kernel_spectra=optimization_options.cache_stencil_supports,
            metadata={"dispatch_stage": "phase_b_scene_planning"},
        )
        hybrid_plan = plan_hybrid_tiled_realization(
            source,
            support,
            routing,
            atlas,
            options=hybrid_options,
        )
        if hybrid_runtime_plans is not None:
            hybrid_runtime_plans[field_key] = hybrid_plan
        if hybrid_runtime_artifacts is not None:
            # Execution-only Phase-B sidecar.  These exact objects already paid
            # the scientific planning cost and are reusable by realization;
            # they never participate in serialized/cache identity.
            hybrid_runtime_artifacts[field_key] = (source, support, routing, atlas)
        estimated_wall_seconds = float(
            hybrid_plan.metadata.get("estimated_wall_seconds", 0.0)
        )
        fft_padded_nodes = int(
            sum(
                tile.fft_padded_node_count
                for tile in hybrid_plan.tile_plans
                if tile.executor == "fft"
            )
        )
        sample_position_bytes = (
            int(samples.fractional_positions.nbytes) if store_sample_positions else 0
        )
        planning_bytes = int(
            cic.flat_indices.nbytes
            + cic.node_masses.nbytes
            + support.active_flat_indices.nbytes
            + support.active_weights.nbytes
            + source.retained_array_bytes
            + routing.retained_array_bytes
            + atlas.retained_array_bytes
            + 256 * hybrid_plan.compute_tile_count
        )
        if planning_bytes > remaining_planning_bytes:
            raise GraphComplexityError(
                "Hybrid Phase-B planning requires "
                f"{planning_bytes} bytes, exceeding the remaining "
                f"max_density_planning_bytes={remaining_planning_bytes}."
            )
        retained_bytes = int(
            hybrid_plan.packed_field_bytes_upper + sample_position_bytes
        )
        auxiliary_bytes = int(
            support.active_flat_indices.nbytes
            + support.active_weights.nbytes
            + source.retained_array_bytes
            + routing.retained_array_bytes
            + atlas.retained_array_bytes
        )
        transient_upper = int(
            max(
                planning_bytes + retained_bytes,
                cic_workspace_upper + retained_bytes,
                auxiliary_bytes + hybrid_plan.predicted_peak_bytes + sample_position_bytes,
            )
        )
        return DensityPhaseBFieldPlan(
            field_key=field_key,
            source_kind=source_kind,
            construction_order=construction_order,
            sample_count=int(samples.fractional_positions.shape[0]),
            sample_bytes=sample_byte_count(
                int(samples.fractional_positions.shape[0])
            ),
            grid_shape=grid_shape,
            logical_node_count=int(np.prod(grid_shape, dtype=object)),
            occupied_cic_node_indices=cic.flat_indices,
            nonzero_node_count_upper=atlas.target_support_node_count,
            stored_value_count=atlas.target_support_node_count,
            stored_block_count=atlas.target_block_count,
            stencil_value_count=support.stencil_offset_count,
            kernel_pair_count=hybrid_plan.direct_pair_count,
            component_value_count=0,
            mesh_cell_count=0,
            mesh_face_count_upper=0,
            render_point_count_upper=0,
            planning_bytes=planning_bytes,
            retained_bytes=retained_bytes,
            transient_bytes_upper=transient_upper,
            metadata={
                "backend": LOCAL_SPARSE_BACKEND,
                "operator": smoothing_operator,
                "broadening_metric": broadening_metric,
                "block_shape": list(block_shape),
                "active_target_node_count": atlas.target_support_node_count,
                "valid_block_value_count": atlas.target_support_node_count,
                "allocated_block_value_count": atlas.target_support_node_count,
                "partial_block_count": int(
                    sum(
                        sum(int(word).bit_count() for word in row)
                        < int(np.prod(block_shape, dtype=object))
                        for row in atlas.target_support_bitsets
                    )
                ),
                "rendering_available_from_ld2": True,
                "sparse_evaluation_mode": optimization_options.sparse_evaluation_mode,
                "sparse_realization_mode": "hybrid",
                "phase_b_execution_planner": "ld8_s3_hybrid_exact_v1",
                "phase_b_support_planner": "ld8_s1_support_atlas_v1",
                "stencil_cache_enabled": optimization_options.cache_stencil_supports,
                "stencil_cache_hit_during_planning": support_cache_hit,
                "routing_cache_hit_during_planning": routing_cache_hit,
                "source_block_count": source.source_block_count,
                "source_node_count": source.occupied_node_count,
                "support_atlas_target_block_count": atlas.target_block_count,
                "support_atlas_target_node_count": atlas.target_support_node_count,
                "hybrid_compute_tile_count": hybrid_plan.compute_tile_count,
                "hybrid_direct_tile_count": hybrid_plan.direct_tile_count,
                "hybrid_fft_tile_count": hybrid_plan.fft_tile_count,
                "exact_contribution_count": hybrid_plan.exact_contribution_count,
                "direct_pair_count": hybrid_plan.direct_pair_count,
                "fft_padded_node_count": fft_padded_nodes,
                "hybrid_estimated_wall_seconds": estimated_wall_seconds,
                "hybrid_predicted_peak_bytes": hybrid_plan.predicted_peak_bytes,
                "cic_workspace_upper_bound_bytes": cic_workspace_upper,
                "hybrid_plan_identity": hybrid_plan.content_identity,
                "kernel_pair_semantics": "actual_direct_tile_pairs",
                "nominal_all_direct_pairs_are_diagnostic_only": True,
                "streaming_scatter": True,
                "streaming_scatter_chunk_pair_upper": min(
                    hybrid_plan.direct_pair_count,
                    optimization_options.sparse_pair_chunk_size,
                ),
                **dict(metadata),
            },
        )

    # Explicit LD7 compatibility path.  It performs streamed all-direct target
    # planning, so its cumulative nominal pair count remains the real work cap.
    batch_plan_metadata: Mapping[str, Any] = {}
    if optimization_options.sparse_evaluation_mode == "reference":
        targets = plan_sparse_target_nodes(
            cic,
            support,
            max_kernel_pairs=limits.max_density_kernel_pairs,
            max_planning_bytes=remaining_planning_bytes,
        )
        pair_count = cic.occupied_node_count * support.stencil_offset_count
    else:
        targets, pair_count, frozen_batch_plan = (
            plan_group_batched_sparse_targets_optimized(
                samples,
                cic,
                support,
                pair_chunk_size=optimization_options.sparse_pair_chunk_size,
                block_shape=block_shape,
                group_batch_size=optimization_options.sparse_group_batch_size,
                max_cic_contributions=8 * limits.max_density_samples,
                max_kernel_pairs=limits.max_density_kernel_pairs,
                max_planning_bytes=remaining_planning_bytes,
            )
        )
        batch_plan_metadata = frozen_batch_plan.to_json_dict()
    block_plan = plan_block_packing(
        targets,
        logical_grid_shape=grid_shape,
        block_shape=block_shape,
        max_nonzero_nodes=limits.max_density_nonzero_nodes,
        max_stored_block_values=limits.max_density_stored_block_values,
        max_blocks=limits.max_density_blocks,
        max_planning_bytes=remaining_planning_bytes,
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
        block_plan.allocated_value_count if block_plan.partial_block_count else 0
    )
    retained_bytes = int(
        8 * block_plan.allocated_value_count
        + block_plan.active_block_indices.nbytes
        + mask_bytes
        + (24 * samples.fractional_positions.shape[0] if store_sample_positions else 0)
    )
    if optimization_options.sparse_evaluation_mode == "optimized":
        peak_pairs = int(batch_plan_metadata.get("peak_batch_kernel_pair_count", pair_count))
        chunk_pairs = min(peak_pairs, optimization_options.sparse_pair_chunk_size)
        scatter_transient = int(
            104 * chunk_pairs
            + 8 * block_plan.allocated_value_count
            + 16 * targets.size
        )
    else:
        scatter_transient = int(16 * pair_count + 16 * targets.size)
    transient_upper = int(
        max(
            planning_bytes + scatter_transient + retained_bytes,
            cic_workspace_upper + retained_bytes,
        )
    )
    return DensityPhaseBFieldPlan(
        field_key=field_key,
        source_kind=source_kind,
        construction_order=construction_order,
        sample_count=int(samples.fractional_positions.shape[0]),
        sample_bytes=sample_byte_count(int(samples.fractional_positions.shape[0])),
        grid_shape=grid_shape,
        logical_node_count=int(np.prod(grid_shape, dtype=object)),
        occupied_cic_node_indices=cic.flat_indices,
        nonzero_node_count_upper=int(targets.size),
        stored_value_count=block_plan.allocated_value_count,
        stored_block_count=block_plan.active_block_count,
        stencil_value_count=support.stencil_offset_count,
        kernel_pair_count=pair_count,
        component_value_count=0,
        mesh_cell_count=0,
        mesh_face_count_upper=0,
        render_point_count_upper=0,
        planning_bytes=planning_bytes,
        retained_bytes=retained_bytes,
        transient_bytes_upper=transient_upper,
        metadata={
            "backend": LOCAL_SPARSE_BACKEND,
            "operator": smoothing_operator,
            "broadening_metric": broadening_metric,
            "block_shape": list(block_plan.block_shape),
            "block_lattice_shape": list(block_plan.block_lattice_shape),
            "active_target_node_count": int(targets.size),
            "valid_block_value_count": block_plan.valid_value_count,
            "allocated_block_value_count": block_plan.allocated_value_count,
            "partial_block_count": block_plan.partial_block_count,
            "rendering_available_from_ld2": True,
            "sparse_evaluation_mode": optimization_options.sparse_evaluation_mode,
            "sparse_realization_mode": "ld7",
            "phase_b_execution_planner": "ld7_all_direct_v1",
            "stencil_cache_enabled": optimization_options.cache_stencil_supports,
            "stencil_cache_hit_during_planning": support_cache_hit,
            "sparse_pair_chunk_size": optimization_options.sparse_pair_chunk_size,
            "cic_workspace_upper_bound_bytes": cic_workspace_upper,
            "sparse_group_batch_size": optimization_options.sparse_group_batch_size,
            **dict(batch_plan_metadata),
            "kernel_pair_semantics": "all_direct_pairs",
            "streaming_scatter": (
                optimization_options.sparse_evaluation_mode == "optimized"
            ),
            "streaming_scatter_chunk_pair_upper": min(
                pair_count, optimization_options.sparse_pair_chunk_size
            ),
            **dict(metadata),
        },
    )

def _plan_framework_phase_b_for_backend(
    *,
    vertices: FloatArray,
    edge_segments: FloatArray,
    weights: FloatArray,
    display_cell: FloatArray,
    options: FrameworkDensityOptions,
    limits: DensityPlanningLimits,
    used_voxels: int,
    construction_order: int,
    planning_bytes_used: int,
    hybrid_runtime_plans: dict[str, DensityHybridRealizationPlan] | None = None,
) -> list[DensityPhaseBFieldPlan]:
    """Build exact dense or sparse Phase-B plans for framework density fields."""

    n_fields = int(options.include_vertex_density) + int(options.include_edge_density)
    if n_fields == 0:
        return []
    sparse_backend = options.storage_options.grid_backend == LOCAL_SPARSE_BACKEND
    remaining_voxels = limits.max_density_voxels - used_voxels
    per_field_budget = remaining_voxels // n_fields
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        numerics = resolve_density_numerics(
            display_cell,
            options=numeric_options,
            fractional_by_frame=vertices,
            frame_weights=weights,
            pbc=np.ones(3, dtype=bool),
            max_voxels=(
                int(np.iinfo(np.int64).max) if sparse_backend else per_field_budget
            ),
            field_label="framework density",
        )
    plans: list[DensityPhaseBFieldPlan] = []
    order = construction_order
    retained_planning = planning_bytes_used
    if options.include_vertex_density:
        remaining = limits.max_density_planning_bytes - retained_planning
        flat = (vertices - np.floor(vertices)).reshape((-1, 3))
        sample_weights = np.repeat(weights, vertices.shape[1])
        if sparse_backend:
            plan = _sparse_phase_b_field_from_samples(
                PeriodicWeightedSamples3D(
                    fractional_positions=flat,
                    weights=sample_weights,
                    sample_group_ids=np.tile(
                        np.arange(vertices.shape[1], dtype=np.int64),
                        vertices.shape[0],
                    ),
                    source_provenance=DensitySourceProvenance(
                        source_kind="framework_vertex_occupancy"
                    ),
                    total_measure=float(vertices.shape[1]),
                    measure_kind="occupancy",
                    measure_units="count",
                ),
                field_key="framework-vertex-density",
                source_kind="framework_vertex_occupancy",
                construction_order=order,
                grid_shape=numerics.grid_shape,
                display_cell=display_cell,
                gaussian_bandwidth=numerics.gaussian_bandwidth,
                smoothing_operator=options.kernel_options.smoothing_operator,
                broadening_metric=options.resolution_options.broadening_metric,
                block_shape=options.storage_options.local_block_shape,
                store_sample_positions=options.store_sample_positions,
                optimization_options=options.optimization_options,
                limits=limits,
                remaining_planning_bytes=remaining,
                metadata={
                    "kernel_tail_tolerance": options.kernel_options.kernel_tail_tolerance,
                    "gaussian_bandwidth": numerics.gaussian_bandwidth,
                    "smearing_definition": numerics.smearing_definition,
                    "resolution_reference_source": "framework_vertices",
                    "effective_artificial_rms": (
                        None
                        if numerics.broadening_diagnostic is None
                        else numerics.broadening_diagnostic.effective_rms
                    ),
                    "adaptive_target_width": numerics.adaptive_target_width,
                    "adaptive_target_achieved": numerics.adaptive_target_achieved,
                },
                hybrid_runtime_plans=hybrid_runtime_plans,
            )
        else:
            occupied = occupied_cic_node_indices(
                flat,
                numerics.grid_shape,
                max_planning_bytes=remaining,
            )
            plan = _phase_b_field(
                field_key="framework-vertex-density",
                source_kind="framework_vertex_occupancy",
                construction_order=order,
                sample_count=int(vertices.shape[0] * vertices.shape[1]),
                grid_shape=numerics.grid_shape,
                occupied_indices=occupied,
                store_sample_positions=options.store_sample_positions,
                smoothing_operator=options.kernel_options.smoothing_operator,
                gaussian_bandwidth=numerics.gaussian_bandwidth,
                metadata={
                    "gaussian_bandwidth": numerics.gaussian_bandwidth,
                    "smearing_definition": numerics.smearing_definition,
                    "broadening_metric": options.resolution_options.broadening_metric,
                    "resolution_reference_source": "framework_vertices",
                    "effective_artificial_rms": (
                        None
                        if numerics.broadening_diagnostic is None
                        else numerics.broadening_diagnostic.effective_rms
                    ),
                    "adaptive_target_width": numerics.adaptive_target_width,
                    "adaptive_target_achieved": numerics.adaptive_target_achieved,
                },
            )
        plans.append(plan)
        retained_planning += plan.planning_bytes
        order += 1
    if options.include_edge_density:
        quadrature = resolve_framework_edge_quadrature(
            grid_shape=numerics.grid_shape,
            display_cell=display_cell,
            gaussian_bandwidth=numerics.gaussian_bandwidth,
            options=options,
            warn=False,
        )
        flat, quadrature_weights, groups, total_measure = (
            build_framework_edge_quadrature_samples(
                edge_segments,
                weights,
                display_cell,
                spacing=quadrature.realized_spacing,
                max_samples=limits.max_density_samples,
                canonicalize_orientation=sparse_backend,
            )
        )
        remaining = limits.max_density_planning_bytes - retained_planning
        if sparse_backend:
            plan = _sparse_phase_b_field_from_samples(
                PeriodicWeightedSamples3D(
                    fractional_positions=flat,
                    weights=quadrature_weights,
                    source_provenance=DensitySourceProvenance(
                        source_kind="framework_edge_length"
                    ),
                    total_measure=total_measure,
                    measure_kind="arc_length",
                    measure_units="angstrom",
                    sample_group_ids=groups,
                ),
                field_key="framework-edge-length-density",
                source_kind="framework_edge_length",
                construction_order=order,
                grid_shape=numerics.grid_shape,
                display_cell=display_cell,
                gaussian_bandwidth=numerics.gaussian_bandwidth,
                smoothing_operator=options.kernel_options.smoothing_operator,
                broadening_metric=options.resolution_options.broadening_metric,
                block_shape=options.storage_options.local_block_shape,
                store_sample_positions=options.store_sample_positions,
                optimization_options=options.optimization_options,
                limits=limits,
                remaining_planning_bytes=remaining,
                metadata={
                    "kernel_tail_tolerance": options.kernel_options.kernel_tail_tolerance,
                    "gaussian_bandwidth": numerics.gaussian_bandwidth,
                    "smearing_definition": numerics.smearing_definition,
                    "edge_source": options.edge_source,
                    **quadrature.metadata_dict(),
                    "resolution_reference_source": "framework_vertices",
                    "effective_artificial_rms": (
                        None
                        if numerics.broadening_diagnostic is None
                        else numerics.broadening_diagnostic.effective_rms
                    ),
                    "adaptive_target_width": numerics.adaptive_target_width,
                    "adaptive_target_achieved": numerics.adaptive_target_achieved,
                },
                hybrid_runtime_plans=hybrid_runtime_plans,
            )
        else:
            occupied = occupied_cic_node_indices(
                flat,
                numerics.grid_shape,
                max_planning_bytes=remaining,
            )
            plan = _phase_b_field(
                field_key="framework-edge-length-density",
                source_kind="framework_edge_length",
                construction_order=order,
                sample_count=int(flat.shape[0]),
                grid_shape=numerics.grid_shape,
                occupied_indices=occupied,
                store_sample_positions=options.store_sample_positions,
                smoothing_operator=options.kernel_options.smoothing_operator,
                gaussian_bandwidth=numerics.gaussian_bandwidth,
                metadata={
                    "gaussian_bandwidth": numerics.gaussian_bandwidth,
                    "smearing_definition": numerics.smearing_definition,
                    "edge_source": options.edge_source,
                    **quadrature.metadata_dict(),
                    "broadening_metric": options.resolution_options.broadening_metric,
                    "resolution_reference_source": "framework_vertices",
                    "effective_artificial_rms": (
                        None
                        if numerics.broadening_diagnostic is None
                        else numerics.broadening_diagnostic.effective_rms
                    ),
                    "adaptive_target_width": numerics.adaptive_target_width,
                    "adaptive_target_achieved": numerics.adaptive_target_achieved,
                },
            )
        plans.append(plan)
    return plans



def _plan_framework_phase_b(
    *,
    vertices: FloatArray,
    edge_segments: FloatArray,
    weights: FloatArray,
    display_cell: FloatArray,
    options: FrameworkDensityOptions,
    limits: DensityPlanningLimits,
    used_voxels: int,
    construction_order: int,
    planning_bytes_used: int,
    hybrid_runtime_plans: dict[str, DensityHybridRealizationPlan] | None = None,
) -> list[DensityBackendCandidateSet]:
    """Build forced or automatic Phase-B candidates for framework channels."""

    requested = options.storage_options.grid_backend
    if requested != AUTO_BACKEND:
        plans = _plan_framework_phase_b_for_backend(
            vertices=vertices,
            edge_segments=edge_segments,
            weights=weights,
            display_cell=display_cell,
            options=options,
            limits=limits,
            used_voxels=used_voxels,
            construction_order=construction_order,
            planning_bytes_used=planning_bytes_used,
            hybrid_runtime_plans=hybrid_runtime_plans,
        )
        result: list[DensityBackendCandidateSet] = []
        for plan in plans:
            result.append(
                make_candidate_set(
                    field_key=plan.field_key,
                    requested_backend=requested,
                    dense_plan=plan if requested == DENSE_BACKEND else None,
                    sparse_plan=(
                        plan if requested == LOCAL_SPARSE_BACKEND else None
                    ),
                    limits=limits,
                    sparse_activation_fraction=(
                        options.storage_options.sparse_activation_fraction
                    ),
                )
            )
        return result

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
        storage_options=replace(
            options.storage_options, grid_backend=LOCAL_SPARSE_BACKEND
        ),
        optimization_options=options.optimization_options,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        numerics = resolve_density_numerics(
            display_cell,
            options=numeric_options,
            fractional_by_frame=vertices,
            frame_weights=weights,
            pbc=np.ones(3, dtype=bool),
            max_voxels=int(np.iinfo(np.int64).max),
            field_label="framework density",
        )
    fixed_resolution = replace(
        options.resolution_options,
        grid_shape=numerics.grid_shape,
        gaussian_bandwidth=numerics.gaussian_bandwidth,
        adaptive_smearing=False,
    )
    dense_options = replace(
        options,
        resolution_options=fixed_resolution,
        storage_options=replace(options.storage_options, grid_backend=DENSE_BACKEND),
    )
    sparse_options = replace(
        options,
        resolution_options=fixed_resolution,
        storage_options=replace(
            options.storage_options, grid_backend=LOCAL_SPARSE_BACKEND
        ),
        optimization_options=options.optimization_options,
    )
    dense_plans: list[DensityPhaseBFieldPlan] = []
    sparse_plans: list[DensityPhaseBFieldPlan] = []
    dense_error: str | None = None
    sparse_error: str | None = None
    try:
        dense_plans = _plan_framework_phase_b_for_backend(
            vertices=vertices,
            edge_segments=edge_segments,
            weights=weights,
            display_cell=display_cell,
            options=dense_options,
            limits=limits,
            used_voxels=used_voxels,
            construction_order=construction_order,
            planning_bytes_used=planning_bytes_used,
            hybrid_runtime_plans=hybrid_runtime_plans,
        )
    except GraphComplexityError as exc:
        dense_error = str(exc)
    try:
        sparse_plans = _plan_framework_phase_b_for_backend(
            vertices=vertices,
            edge_segments=edge_segments,
            weights=weights,
            display_cell=display_cell,
            options=sparse_options,
            limits=limits,
            used_voxels=0,
            construction_order=construction_order,
            planning_bytes_used=planning_bytes_used,
            hybrid_runtime_plans=hybrid_runtime_plans,
        )
    except GraphComplexityError as exc:
        sparse_error = str(exc)

    keys: list[str] = []
    if options.include_vertex_density:
        keys.append("framework-vertex-density")
    if options.include_edge_density:
        keys.append("framework-edge-length-density")
    dense_by_key = {plan.field_key: plan for plan in dense_plans}
    sparse_by_key = {plan.field_key: plan for plan in sparse_plans}
    return [
        make_candidate_set(
            field_key=key,
            requested_backend=AUTO_BACKEND,
            dense_plan=dense_by_key.get(key),
            sparse_plan=sparse_by_key.get(key),
            limits=limits,
            sparse_activation_fraction=options.storage_options.sparse_activation_fraction,
            dense_error=dense_error if key not in dense_by_key else None,
            sparse_error=sparse_error if key not in sparse_by_key else None,
        )
        for key in keys
    ]

def _rebase_category_graph_view(
    view: DecoratedGraphView,
    *,
    source_cell: FloatArray,
    target_cell: FloatArray,
) -> DecoratedGraphView:
    positions = np.asarray(view.node_positions_3d, dtype=np.float64)
    fractional = positions @ np.linalg.inv(np.asarray(source_cell, dtype=np.float64))
    return replace(
        view,
        node_positions_3d=fractional @ np.asarray(target_cell, dtype=np.float64),
        cell=np.asarray(target_cell, dtype=np.float64),
        metadata={**dict(view.metadata), "category_rebased_to_global_display_cell": True},
    )


def _rebase_category_atomic_mean_graph(
    graph: AtomicMeanGraph | None,
    *,
    source_cell: FloatArray,
    target_cell: FloatArray,
) -> AtomicMeanGraph | None:
    if graph is None:
        return None
    fractional = (
        np.asarray(graph.display_positions, dtype=np.float64)
        @ np.linalg.inv(np.asarray(source_cell, dtype=np.float64))
    )
    return replace(
        graph,
        display_positions=fractional @ np.asarray(target_cell, dtype=np.float64),
        display_cell=np.asarray(target_cell, dtype=np.float64),
        metadata={**dict(graph.metadata), "category_rebased_to_global_display_cell": True},
    )


def _prepare_partitioned_framework_dynamics_scene(
    collection: AtomisticFrameCollection,
    catalog: TopologyCatalog,
    *,
    frame_indices: Sequence[int] | None,
    display_mode: FrameworkGraphDisplayMode | str,
    trajectory_selection: TrajectoryAtomSelection | None,
    atomic_connectivity: AtomicConnectivityState | AtomicConnectivityResult | None,
    atomic_mean_graph_options: AtomicMeanGraphOptions | None,
    atomic_density_selections: Sequence[AtomicDensitySelection] | None,
    atomic_density_options: AtomicDensityOptions | None,
    framework_density_options: FrameworkDensityOptions | None,
    options: FrameworkDynamicsOptions | None,
    resources: FrameworkDynamicsResources,
    progress: ProgressPortLike | None,
    progress_callback: Callable[[str], None] | None,
    category_mode: Literal["all", "dominant_only"] = "all",
) -> FrameworkDynamicsScene:
    """Prepare global dynamic fields plus requested topology-category evidence."""

    if category_mode not in {"all", "dominant_only"}:
        raise GraphAdapterError("category_mode must be 'all' or 'dominant_only'.")

    partitioned_started = time.perf_counter()
    frames = _selected_frames(collection, frame_indices)
    catalog_position = {int(frame): position for position, frame in enumerate(catalog.frame_indices)}
    missing = tuple(frame for frame in frames if int(frame) not in catalog_position)
    if missing:
        raise GraphAdapterError(
            "Selected frames are not all represented in the supplied TopologyCatalog: "
            f"{missing[:8]}."
        )
    topology_ids = np.asarray(
        [catalog.frame_topology_ids[catalog_position[int(frame)]] for frame in frames],
        dtype=np.int64,
    )
    counts = np.bincount(topology_ids, minlength=len(catalog.topologies))
    used_ids = tuple(int(value) for value in np.flatnonzero(counts))
    dominant_id = min(used_ids, key=lambda value: (-int(counts[value]), value))
    base_options = options or FrameworkDynamicsOptions()
    geometry_cache = _FrameworkGeometryCache()
    preprocessing_scheduler = DensitySceneScheduler(
            resources.runtime_budget,
            policy=DensitySchedulerPolicy(max_parallel_tasks=autotuned_max_parallel_tasks()),
        )
    state_by_frame = _connectivity_state_map(atomic_connectivity, frames)
    base_scene = _prepare_framework_dynamics_scene_impl(
        collection,
        catalog.topologies[dominant_id],
        frame_indices=frames,
        display_mode=display_mode,
        trajectory_selection=trajectory_selection,
        atomic_connectivity=atomic_connectivity,
        atomic_mean_graph_options=atomic_mean_graph_options,
        atomic_density_selections=atomic_density_selections,
        atomic_density_options=atomic_density_options,
        framework_density_options=framework_density_options,
        options=base_options,
        resources=resources,
        progress=progress,
        progress_callback=progress_callback,
        _geometry_cache=geometry_cache,
        _preprocessing_scheduler=preprocessing_scheduler,
        _state_by_frame=state_by_frame,
    )
    total = len(frames)
    if category_mode == "dominant_only":
        dominant_frames = tuple(
            int(frame)
            for frame, assigned in zip(frames, topology_ids, strict=True)
            if int(assigned) == dominant_id
        )
        dominant_scene = _prepare_framework_dynamics_scene_impl(
            collection,
            catalog.topologies[dominant_id],
            frame_indices=dominant_frames,
            display_mode=display_mode,
            trajectory_selection=None,
            atomic_connectivity=atomic_connectivity,
            atomic_mean_graph_options=atomic_mean_graph_options,
            atomic_density_selections=None,
            atomic_density_options=None,
            framework_density_options=None,
            options=replace(base_options, reference_frame=dominant_frames[0]),
            resources=resources,
            progress=None,
            progress_callback=None,
            _geometry_cache=geometry_cache,
            _preprocessing_scheduler=preprocessing_scheduler,
            _state_by_frame=state_by_frame,
        )
        partitioned_wall_seconds = time.perf_counter() - partitioned_started
        return replace(
            base_scene,
            mean_framework=_rebase_category_graph_view(
                dominant_scene.mean_framework,
                source_cell=dominant_scene.display_cell,
                target_cell=base_scene.display_cell,
            ),
            atomic_mean_graph=_rebase_category_atomic_mean_graph(
                dominant_scene.atomic_mean_graph,
                source_cell=dominant_scene.display_cell,
                target_cell=base_scene.display_cell,
            ),
            topology_categories=(),
            topology_catalog=catalog,
            dominant_topology_id=dominant_id,
            metadata={
                **dict(base_scene.metadata),
                "topology_catalog_digest": catalog.digest,
                "topology_consistency": catalog.consistency.value,
                "topology_category_count": len(used_ids),
                "dominant_topology_id": dominant_id,
                "topology_category_policy": "gfx3d_dominant_only_fast_path_v1",
                "topology_category_materialization_omitted": True,
                "dominant_category_frame_count": len(dominant_frames),
                "dominant_category_probability": len(dominant_frames) / total,
                "partitioned_wall_seconds": float(partitioned_wall_seconds),
                "preparation_wall_seconds": float(partitioned_wall_seconds),
                "framework_geometry_cache": geometry_cache.summary(),
                "trajectory_wide_state_lookup_hoisted": state_by_frame is not None,
            },
        )

    layers: list[FrameworkTopologyCategoryLayer] = []
    category_specs: list[tuple[int, tuple[int, ...], tuple[Any, ...], FrameworkDynamicsOptions]] = []
    for topology_id in used_ids:
        category_frames = tuple(
            int(frame) for frame, assigned in zip(frames, topology_ids, strict=True)
            if int(assigned) == topology_id
        )
        relevant_positions = {catalog_position[frame] for frame in category_frames}
        segments = tuple(
            item for item in (catalog.segments or ())
            if item.topology_id == topology_id
            and any(
                position in relevant_positions
                for position in range(item.result_position_start, item.result_position_stop)
            )
        )
        category_specs.append(
            (
                topology_id,
                category_frames,
                segments,
                replace(base_options, reference_frame=category_frames[0]),
            )
        )

    # PAR-DENS4: topology categories are independent once the global density
    # fields and trajectory-wide lookup tables have been prepared.  Run the
    # category graph reductions through one bounded scheduler; each nested
    # registration/mean calculation observes the live category lease rather
    # than creating an independent CPU authority.
    category_scheduler = DensitySceneScheduler(
            resources.runtime_budget,
            policy=DensitySchedulerPolicy(max_parallel_tasks=autotuned_max_parallel_tasks()),
        )
    category_tasks: list[DensityScheduledTask[FrameworkDynamicsScene]] = []
    for construction_order, (topology_id, category_frames, _segments, category_options) in enumerate(category_specs):
        topology = catalog.topologies[topology_id]
        contract = _preprocessing_resource_estimate(
            task_id=f"topology-category:{topology_id}",
            frame_count=len(category_frames),
            item_count=max(1, topology.n_vertices + topology.n_edges),
            max_threads=int(resources.max_threads),
            construction_order=construction_order,
            retained=True,
            backend="topology_category_scene",
        )

        def prepare_category(
            lease: DensityWorkerLease,
            *,
            _topology_id: int = topology_id,
            _category_frames: tuple[int, ...] = category_frames,
            _category_options: FrameworkDynamicsOptions = category_options,
        ) -> FrameworkDynamicsScene:
            del lease  # the active lease is context-bound by DensitySceneScheduler
            return _prepare_framework_dynamics_scene_impl(
                collection,
                catalog.topologies[_topology_id],
                frame_indices=_category_frames,
                display_mode=display_mode,
                trajectory_selection=None,
                atomic_connectivity=atomic_connectivity,
                atomic_mean_graph_options=atomic_mean_graph_options,
                atomic_density_selections=None,
                atomic_density_options=None,
                framework_density_options=None,
                options=_category_options,
                resources=resources,
                progress=None,
                progress_callback=None,
                _geometry_cache=geometry_cache,
                _preprocessing_scheduler=preprocessing_scheduler,
                _state_by_frame=state_by_frame,
            )

        category_tasks.append(DensityScheduledTask(resources=contract, function=prepare_category))

    try:
        category_scenes = category_scheduler.run(tuple(category_tasks))
    except DensitySchedulerTaskError as error:
        raise error.original from error

    for (topology_id, category_frames, segments, _category_options), category_scene in zip(
        category_specs, category_scenes, strict=True
    ):
        layers.append(
            FrameworkTopologyCategoryLayer(
                topology_id=topology_id,
                topology=catalog.topologies[topology_id],
                frame_indices=np.asarray(category_frames, dtype=np.int64),
                probability=len(category_frames) / total,
                segment_count=max(1, len(segments)),
                mean_framework=_rebase_category_graph_view(
                    category_scene.mean_framework,
                    source_cell=category_scene.display_cell,
                    target_cell=base_scene.display_cell,
                ),
                atomic_mean_graph=_rebase_category_atomic_mean_graph(
                    category_scene.atomic_mean_graph,
                    source_cell=category_scene.display_cell,
                    target_cell=base_scene.display_cell,
                ),
                metadata={
                    "catalog_digest": catalog.digest,
                    "category_frame_count": len(category_frames),
                    "category_probability": len(category_frames) / total,
                    "trajectory_wide_state_lookup_reused": state_by_frame is not None,
                },
            )
        )
    layers.sort(key=lambda item: (-item.probability, item.topology_id))
    dominant_layer = next(item for item in layers if item.topology_id == dominant_id)
    partitioned_wall_seconds = time.perf_counter() - partitioned_started
    return replace(
        base_scene,
        mean_framework=dominant_layer.mean_framework,
        atomic_mean_graph=dominant_layer.atomic_mean_graph,
        topology_categories=tuple(layers),
        topology_catalog=catalog,
        dominant_topology_id=dominant_id,
        metadata={
            **dict(base_scene.metadata),
            "topology_catalog_digest": catalog.digest,
            "topology_consistency": catalog.consistency.value,
            "topology_category_count": len(layers),
            "dominant_topology_id": dominant_id,
            "topology_category_policy": "par_dens4_parallel_partitioned_category_graphs_v2",
            "partitioned_wall_seconds": float(partitioned_wall_seconds),
            "wall_time_admission_enforced": False,
            "partitioned_wall_time_budget_exceeded": bool(
                partitioned_wall_seconds > float(resources.max_wall_time_seconds)
            ),
            "preparation_wall_seconds": float(partitioned_wall_seconds),
            "partitioned_category_preparation_wall_seconds": float(partitioned_wall_seconds),
            "topology_category_scheduler_summary": (
                {}
                if category_scheduler.last_report is None
                else category_scheduler.last_report.to_json_dict()
            ),
            "framework_geometry_cache": geometry_cache.summary(),
            "trajectory_wide_state_lookup_hoisted": state_by_frame is not None,
        },
    )


def prepare_framework_dynamics_scene(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology | TopologyCatalog,
    *,
    frame_indices: Sequence[int] | None = None,
    display_mode: FrameworkGraphDisplayMode | str = FrameworkGraphDisplayMode.PROJECTED,
    trajectory_selection: TrajectoryAtomSelection | None = None,
    atomic_connectivity: AtomicConnectivityState
    | AtomicConnectivityResult
    | None = None,
    atomic_mean_graph_options: AtomicMeanGraphOptions | None = None,
    atomic_density_selections: Sequence[AtomicDensitySelection] | None = None,
    atomic_density_options: AtomicDensityOptions | None = None,
    framework_density_options: FrameworkDensityOptions | None = None,
    options: FrameworkDynamicsOptions | None = None,
    resources: FrameworkDynamicsResources | None = None,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
    _topology_category_mode: Literal["all", "dominant_only"] = "all",
) -> FrameworkDynamicsScene:
    """Prepare one scene under a runtime-derived native-thread ceiling."""

    if _topology_category_mode not in {"all", "dominant_only"}:
        raise GraphAdapterError("_topology_category_mode must be 'all' or 'dominant_only'.")

    resolved_resources = resources or FrameworkDynamicsResources()
    try:
        from threadpoolctl import threadpool_limits
    except ImportError as error:  # pragma: no cover - declared base dependency
        raise GraphUnsupportedFeatureError(
            "Runtime thread containment requires threadpoolctl."
        ) from error
    gpu_policy = DensityGPUExecutionPolicy.from_environment()
    autotune_policy = DensityAutoTunePolicy.from_environment()
    autotune_profile = resolve_density_autotune_profile(
        resolved_resources.runtime_budget, policy=autotune_policy
    )
    with (
        density_resource_budget_scope(resolved_resources.runtime_budget),
        density_time_model_scope(resolved_resources.time_model),
        density_autotune_scope(autotune_profile),
        threadpool_limits(limits=int(resolved_resources.max_threads)),
        density_gpu_journal_scope() as gpu_journal,
        density_execution_journal_scope() as execution_journal,
    ):
        if isinstance(topology, TopologyCatalog):
            if topology.consistency is TopologyConsistency.UNIFORM and len(topology.topologies) == 1:
                # A uniform catalog contains one exact framework topology.  The
                # generic partitioned path would prepare the same geometry once
                # for the base scene and again for its sole category.  Bypass
                # that duplication while retaining the public catalog/category
                # evidence expected by callers.
                scene = _prepare_framework_dynamics_scene_impl(
                    collection,
                    topology.topologies[0],
                    frame_indices=frame_indices,
                    display_mode=display_mode,
                    trajectory_selection=trajectory_selection,
                    atomic_connectivity=atomic_connectivity,
                    atomic_mean_graph_options=atomic_mean_graph_options,
                    atomic_density_selections=atomic_density_selections,
                    atomic_density_options=atomic_density_options,
                    framework_density_options=framework_density_options,
                    options=options,
                    resources=resolved_resources,
                    progress=progress,
                    progress_callback=progress_callback,
                )
                selected = tuple(int(v) for v in scene.frame_indices)
                segment_count = 1
                if topology.segments is not None:
                    catalog_positions = {int(frame): pos for pos, frame in enumerate(topology.frame_indices)}
                    selected_positions = {catalog_positions[frame] for frame in selected if frame in catalog_positions}
                    segment_count = max(
                        1,
                        sum(
                            any(pos in selected_positions for pos in range(seg.result_position_start, seg.result_position_stop))
                            for seg in topology.segments
                        ),
                    )
                category = FrameworkTopologyCategoryLayer(
                    topology_id=0,
                    topology=topology.topologies[0],
                    frame_indices=np.asarray(selected, dtype=np.int64),
                    probability=1.0,
                    segment_count=segment_count,
                    mean_framework=scene.mean_framework,
                    atomic_mean_graph=scene.atomic_mean_graph,
                    metadata={
                        "catalog_digest": topology.digest,
                        "category_frame_count": len(selected),
                        "category_probability": 1.0,
                        "uniform_catalog_fast_path": True,
                    },
                )
                scene = replace(
                    scene,
                    topology_categories=(category,),
                    topology_catalog=topology,
                    dominant_topology_id=0,
                    metadata={
                        **dict(scene.metadata),
                        "topology_catalog_digest": topology.digest,
                        "topology_consistency": topology.consistency.value,
                        "topology_category_count": 1,
                        "dominant_topology_id": 0,
                        "topology_category_policy": "uniform_catalog_fast_path_v1",
                        "uniform_catalog_duplicate_preparation_avoided": True,
                    },
                )
            else:
                scene = _prepare_partitioned_framework_dynamics_scene(
                    collection,
                    topology,
                    frame_indices=frame_indices,
                    display_mode=display_mode,
                    trajectory_selection=trajectory_selection,
                    atomic_connectivity=atomic_connectivity,
                    atomic_mean_graph_options=atomic_mean_graph_options,
                    atomic_density_selections=atomic_density_selections,
                    atomic_density_options=atomic_density_options,
                    framework_density_options=framework_density_options,
                    options=options,
                    resources=resolved_resources,
                    progress=progress,
                    progress_callback=progress_callback,
                    category_mode=_topology_category_mode,
                )
        else:
            if not isinstance(topology, FrameworkTopology):
                raise TypeError("topology must be FrameworkTopology or TopologyCatalog.")
            scene = _prepare_framework_dynamics_scene_impl(
                collection,
                topology,
                frame_indices=frame_indices,
                display_mode=display_mode,
                trajectory_selection=trajectory_selection,
                atomic_connectivity=atomic_connectivity,
                atomic_mean_graph_options=atomic_mean_graph_options,
                atomic_density_selections=atomic_density_selections,
                atomic_density_options=atomic_density_options,
                framework_density_options=framework_density_options,
                options=options,
                resources=resolved_resources,
                progress=progress,
                progress_callback=progress_callback,
            )
        return replace(
            scene,
            metadata={
                **dict(scene.metadata),
                "density_gpu_policy": gpu_policy.to_json_dict(),
                "density_gpu_summary": density_gpu_report(gpu_journal),
                "density_gpu_scientific_precision": "fp64_only",
                "density_autotune_policy": autotune_policy.to_json_dict(),
                "density_autotune_profile": autotune_profile.to_json_dict(),
                "density_autotune_scientific_identity_neutral": True,
                "density_execution_summary": density_execution_report(execution_journal),
            },
        )


def _prepare_framework_dynamics_scene_impl(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_indices: Sequence[int] | None = None,
    display_mode: FrameworkGraphDisplayMode | str = FrameworkGraphDisplayMode.PROJECTED,
    trajectory_selection: TrajectoryAtomSelection | None = None,
    atomic_connectivity: AtomicConnectivityState
    | AtomicConnectivityResult
    | None = None,
    atomic_mean_graph_options: AtomicMeanGraphOptions | None = None,
    atomic_density_selections: Sequence[AtomicDensitySelection] | None = None,
    atomic_density_options: AtomicDensityOptions | None = None,
    framework_density_options: FrameworkDensityOptions | None = None,
    options: FrameworkDynamicsOptions | None = None,
    resources: FrameworkDynamicsResources | None = None,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
    _geometry_cache: _FrameworkGeometryCache | None = None,
    _preprocessing_scheduler: DensitySceneScheduler | None = None,
    _state_by_frame: Mapping[int, AtomicConnectivityState] | None = None,
) -> FrameworkDynamicsScene:
    """Prepare registered mean-framework geometry and selected atomic paths.

    A trajectory selection requires explicit trajectory semantics.  Mean framework
    geometry alone may also be prepared from an independent ensemble, with each
    frame placed independently in the canonical reference gauge.
    """
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    if not isinstance(topology, FrameworkTopology):
        raise TypeError("topology must be a FrameworkTopology.")
    preparation_started = time.perf_counter()
    progress_port = resolve_progress_port(
        progress,
        progress_callback=progress_callback,
        environment_variable="MDSTATS_PREPARE_PROGRESS",
        environment_label="mdstats-prepare",
        environment_stream=sys.stderr,
    )
    reporter = ProgressEmitter(
        progress_port,
        source="plotting.framework_dynamics.prepare",
    )
    reporter.started(
        "scene_preparation",
        "validating inputs and resolving resources",
    )
    options = options or FrameworkDynamicsOptions()
    resources = resources or FrameworkDynamicsResources()
    geometry_cache = _FrameworkGeometryCache() if _geometry_cache is None else _geometry_cache
    preprocessing_scheduler = (
        DensitySceneScheduler(
            resources.runtime_budget,
            policy=DensitySchedulerPolicy(max_parallel_tasks=autotuned_max_parallel_tasks()),
        )
        if _preprocessing_scheduler is None
        else _preprocessing_scheduler
    )
    if not isinstance(geometry_cache, _FrameworkGeometryCache):
        raise TypeError("_geometry_cache must be _FrameworkGeometryCache or None.")
    if not isinstance(preprocessing_scheduler, DensitySceneScheduler):
        raise TypeError("_preprocessing_scheduler must be DensitySceneScheduler or None.")
    frames = _selected_frames(collection, frame_indices)
    if len(frames) > resources.max_frames:
        raise GraphComplexityError(
            f"Selected {len(frames)} frames, exceeding max_frames={resources.max_frames}."
        )
    reporter.update(
        "scene_preparation",
        f"selected {len(frames)} frames",
        metadata={"frame_count": len(frames)},
    )
    reference_frame = (
        frames[0] if options.reference_frame is None else options.reference_frame
    )
    if reference_frame not in frames:
        raise GraphAdapterError("reference_frame must be one of frame_indices.")
    display_cell = _display_cell(
        collection, frames, reference_frame, options.display_cell
    )
    cell_equivalence = evaluate_cell_equivalence(
        np.asarray(collection.cells[list(frames)], dtype=np.float64),
        display_cell,
    )
    density_requested = bool(atomic_density_selections) or (
        framework_density_options is not None
    )
    if (
        density_requested
        and options.registration_mode is SpatialRegistrationMode.LABORATORY
    ):
        require_equivalent_laboratory_density_cells(
            np.asarray(collection.cells[list(frames)], dtype=np.float64),
            display_cell,
            field_context="framework-dynamics density scene",
        )

    reporter.started(
        "framework_registration",
        "processing registered framework frames in bounded parallel batches",
        current=0,
        total=len(frames),
        unit="frames",
    )
    frame_view, lifted_frames, residual_reference = _prepare_registered_framework_frames(
        collection,
        topology,
        frames=frames,
        display_mode=display_mode,
        geometry_cache=geometry_cache,
        scheduler=preprocessing_scheduler,
        max_threads=int(resources.max_threads),
        task_id=f"framework-registration:{topology.digest[:16]}:{FrameworkGraphDisplayMode(display_mode).value}",
    )

    reporter.completed(
        "framework_registration",
        "registered all frames; averaging framework geometry",
        current=len(frames),
        total=len(frames),
        unit="frames",
    )
    fractional = np.asarray(lifted_frames, dtype=np.float64)
    framework_reference_atoms = tuple(int(value) for value in frame_view.node_keys)
    registration_view = prepare_plotting_coordinate_view(
        collection,
        frame_indices=frames,
        display_cell=display_cell,
        spatial_mode=options.registration_mode.value,
        framework_atom_indices=framework_reference_atoms,
        framework_fractional_by_frame=fractional,
    )
    registered_cartesian = np.asarray(
        registration_view.transform_fractional(
            fractional, frame_indices=frames, output="cartesian"
        ),
        dtype=np.float64,
    )
    weights = _uniform_weights(len(frames))
    mean_positions = np.einsum(
        "t,tni->ni", weights, registered_cartesian, optimize=True
    )
    assert residual_reference is not None
    canonical_mean_positions, canonical_mean_shifts = _canonicalize_mean_framework(
        mean_positions,
        display_cell,
        np.asarray(frame_view.edge_endpoints, dtype=np.int64),
        residual_reference,
        np.asarray(frame_view.pbc, dtype=bool),
    )
    mean_view = _mean_framework_view(
        frame_view,
        canonical_mean_positions,
        display_cell,
        canonical_mean_shifts,
        frames=frames,
        registration=options.registration_mode,
        display_cell_mode=options.display_cell,
    )

    paths: TrajectoryPathSet | None = None
    selected_atoms: tuple[int, ...] = ()
    if trajectory_selection is not None:
        reporter.started(
            "trajectory_preparation",
            "resolving selected atoms and folded paths",
        )
        collection.require_trajectory("atomic trajectory visualization")
        selected_atoms = trajectory_selection.resolve(collection)
        n_points = len(selected_atoms) * len(frames)
        if len(selected_atoms) > resources.max_trajectory_atoms:
            raise GraphComplexityError(
                f"Selected {len(selected_atoms)} atoms, exceeding "
                f"max_trajectory_atoms={resources.max_trajectory_atoms}."
            )
        if n_points > resources.max_trajectory_points:
            raise GraphComplexityError(
                f"Selected trajectory contains {n_points} points, exceeding "
                f"max_trajectory_points={resources.max_trajectory_points}."
            )
        raw_fractional = np.asarray(
            collection.fractional_positions[np.ix_(frames, selected_atoms)],
            dtype=np.float64,
        )
        continuous_tna = np.asarray(
            registration_view.transform_fractional(
                raw_fractional, frame_indices=frames, output="cartesian"
            ),
            dtype=np.float64,
        )
        if options.registration_mode is SpatialRegistrationMode.LABORATORY:
            wrapping_fractional = np.array(raw_fractional, copy=True)
        else:
            wrapping_fractional = np.asarray(
                registration_view.transform_fractional(
                    raw_fractional,
                    frame_indices=frames,
                    output="display_fractional",
                ),
                dtype=np.float64,
            )

        images = np.zeros_like(wrapping_fractional, dtype=np.int64)
        folded = np.array(wrapping_fractional, copy=True)
        for axis, periodic in enumerate(collection.pbc):
            if periodic:
                images[..., axis] = np.floor(wrapping_fractional[..., axis]).astype(np.int64)
                folded[..., axis] -= np.floor(folded[..., axis])
        boundary_crossings = np.any(np.diff(images, axis=0) != 0, axis=2)
        folded_cartesian = folded @ display_cell
        if options.trajectory_display_mode is TrajectoryDisplayMode.CONTINUOUS:
            display_tna = continuous_tna
            breaks_tna = np.zeros_like(boundary_crossings, dtype=bool)
        else:
            display_tna = folded_cartesian
            breaks_tna = boundary_crossings
        label = trajectory_selection.label or "selected atoms"
        paths = TrajectoryPathSet(
            atom_indices=selected_atoms,
            atomic_numbers=np.asarray(
                collection.atomic_numbers[list(selected_atoms)], dtype=np.int64
            ),
            frame_indices=np.asarray(frames, dtype=np.int64),
            frame_ids=np.asarray(collection.frame_ids[list(frames)], dtype=np.int64),
            times=(
                None
                if collection.times is None
                else np.asarray(collection.times[list(frames)], dtype=np.float64)
            ),
            continuous_positions=np.transpose(continuous_tna, (1, 0, 2)),
            display_positions=np.transpose(display_tna, (1, 0, 2)),
            lattice_images=np.transpose(images, (1, 0, 2)),
            segment_breaks=np.transpose(breaks_tna, (1, 0)),
            display_mode=options.trajectory_display_mode,
            selection_label=label,
        )

    atomic_options = atomic_density_options or AtomicDensityOptions()
    atomic_options = replace(
        atomic_options,
        optimization_options=atomic_options.optimization_options.resolve(
            runtime_budget=resources.runtime_budget,
        ),
    )
    if framework_density_options is not None:
        framework_density_options = replace(
            framework_density_options,
            optimization_options=framework_density_options.optimization_options.resolve(
                runtime_budget=resources.runtime_budget,
            ),
        )
    atomic_selections = tuple(atomic_density_selections or ())

    atomic_mean_graph: AtomicMeanGraph | None = None
    if atomic_mean_graph_options is not None:
        reporter.started(
            "atomic_mean_graph",
            "aggregating connectivity occupancy",
        )
        if atomic_connectivity is None:
            raise GraphAdapterError(
                "atomic_connectivity must be provided when atomic_mean_graph_options are requested."
            )
        state_map = (
            _state_by_frame
            if _state_by_frame is not None
            else _connectivity_state_map(atomic_connectivity, frames)
        )
        assert state_map is not None
        first_state = state_map[int(frames[0])]
        mean_resources = _preprocessing_resource_estimate(
            task_id=f"atomic-mean-graph:{topology.digest[:16]}",
            frame_count=len(frames),
            item_count=max(1, int(first_state.active_atom_indices.size)),
            max_threads=int(resources.max_threads),
            retained=True,
            backend="periodic_atomic_mean_and_connectivity_reduction",
        )

        def build_atomic_mean(lease: DensityWorkerLease) -> AtomicMeanGraph:
            return _prepare_atomic_mean_graph(
                collection,
                frames=frames,
                weights=weights,
                display_cell=display_cell,
                registration_view=registration_view,
                atomic_connectivity=atomic_connectivity,
                options=atomic_mean_graph_options,
                worker_lease=lease,
                state_by_frame=state_map,
            )

        atomic_mean_graph = _run_preprocessing_task(
            preprocessing_scheduler, mean_resources, build_atomic_mean
        )

    framework_densities: FrameworkDensityFields | None = None
    projected_display_fractional: FloatArray | None = None
    edge_segments: FloatArray | None = None
    edge_atoms: tuple[int, ...] = ()
    if framework_density_options is not None:
        if not np.all(collection.pbc):
            raise GraphAdapterError(
                "The first framework-density backend requires periodicity along all three axes."
            )
        projected_lifted: list[FloatArray] = []
        projected_residual: IntArray | None = None
        if (
            FrameworkGraphDisplayMode(display_mode)
            is FrameworkGraphDisplayMode.PROJECTED
        ):
            projected_view = frame_view
            projected_lifted = lifted_frames
            projected_residual = residual_reference
        else:
            projected_view, projected_lifted, projected_residual = (
                _prepare_registered_framework_frames(
                    collection,
                    topology,
                    frames=frames,
                    display_mode=FrameworkGraphDisplayMode.PROJECTED,
                    geometry_cache=geometry_cache,
                    scheduler=preprocessing_scheduler,
                    max_threads=int(resources.max_threads),
                    task_id=f"framework-projected:{topology.digest[:16]}",
                )
            )
        assert projected_residual is not None
        projected_display_fractional = _display_fractional_coordinates(
            np.asarray(projected_lifted, dtype=np.float64),
            frames,
            registration_view,
        )

        edge_view = projected_view
        edge_display_fractional = projected_display_fractional
        edge_residual = projected_residual
        edge_atoms = tuple(int(v) for v in topology.vertex_atom_indices)
        if framework_density_options.edge_source == "atomic_paths":
            path_view, path_lifted, path_residual = _prepare_registered_framework_frames(
                collection,
                topology,
                frames=frames,
                display_mode=FrameworkGraphDisplayMode.ATOMIC_PATHS,
                geometry_cache=geometry_cache,
                scheduler=preprocessing_scheduler,
                max_threads=int(resources.max_threads),
                task_id=f"framework-atomic-paths:{topology.digest[:16]}",
            )
            edge_view = path_view
            edge_display_fractional = _display_fractional_coordinates(
                np.asarray(path_lifted, dtype=np.float64),
                frames,
                registration_view,
            )
            edge_residual = path_residual
            edge_atoms = tuple(int(v) for v in edge_view.node_keys)

        edge_segments = _edge_segments_from_view(
            edge_display_fractional,
            edge_view,
            edge_residual,
            frames,
            registration_view,
        )

    planning_record: DensityScenePlan | None = None
    planning_metadata_by_field: dict[str, Mapping[str, Any]] = {}
    realization_metadata: Mapping[str, int] = {}
    density_fields: tuple[ScalarField3D, ...] = ()
    density_scheduler_policy: str | None = None
    preprocessing_wall_seconds: float | None = None
    density_planning_wall_seconds: float | None = None
    density_realization_wall_seconds: float | None = None
    if atomic_selections or framework_density_options is not None:
        requested_field_count = len(atomic_selections) + (0 if framework_density_options is None else 2)
        planning_started = time.perf_counter()
        preprocessing_wall_seconds = planning_started - preparation_started

        reporter.started(
            "density_planning",
            "estimating dense and sparse candidates",
            current=0,
            total=requested_field_count,
            unit="fields",
            metadata={"requested_field_count": requested_field_count},
        )
        limits = resources.density_planning_limits()
        phase_a = _build_density_phase_a(
            collection,
            frames=frames,
            atomic_selections=atomic_selections,
            atomic_options=atomic_options,
            framework_options=framework_density_options,
            framework_vertex_count=len(topology.vertex_atom_indices),
            framework_edge_segments=edge_segments,
            display_cell=display_cell,
            limits=limits,
        )
        hybrid_runtime_plans: dict[str, DensityHybridRealizationPlan] = {}
        hybrid_runtime_artifacts: dict[str, tuple[Any, Any, Any, Any]] = {}
        atomic_resolved_plans: dict[str, AtomicDensityResolvedPlan] = {}
        atomic_candidates = _plan_atomic_phase_b(
            collection,
            frames=frames,
            weights=weights,
            display_cell=display_cell,
            registration_view=registration_view,
            selections=atomic_selections,
            options=atomic_options,
            limits=limits,
            hybrid_runtime_plans=hybrid_runtime_plans,
            hybrid_runtime_artifacts=hybrid_runtime_artifacts,
            resolved_plans=atomic_resolved_plans,
        )
        provisional_atomic = [
            candidate.plan_for(candidate.preferred_backend)
            for candidate in atomic_candidates
        ]
        used_voxels = sum(
            plan.logical_node_count
            for plan in provisional_atomic
            if str(plan.metadata.get("backend", DENSE_BACKEND)) == DENSE_BACKEND
        )
        planning_bytes_used = sum(v.planning_bytes for v in provisional_atomic)
        framework_candidates: list[DensityBackendCandidateSet] = []
        if framework_density_options is not None:
            assert projected_display_fractional is not None
            assert edge_segments is not None
            framework_candidates = _plan_framework_phase_b(
                vertices=projected_display_fractional,
                edge_segments=edge_segments,
                weights=weights,
                display_cell=display_cell,
                options=framework_density_options,
                limits=limits,
                used_voxels=used_voxels,
                construction_order=len(atomic_candidates),
                planning_bytes_used=planning_bytes_used,
                hybrid_runtime_plans=hybrid_runtime_plans,
            )
        all_candidates = tuple(atomic_candidates + framework_candidates)
        planning_record = select_density_scene_backends(
            phase_a_fields=phase_a,
            candidates=all_candidates,
            limits=limits,
            metadata={
                "registration_mode": options.registration_mode.value,
                "frame_count": len(frames),
            },
            planner=plan_density_scene,
        )
        # Phase B may evaluate both dense and sparse candidates in AUTO mode.
        # Retain execution-only sparse sidecars only for fields whose approved
        # backend is actually local_sparse; otherwise candidate planning would
        # unnecessarily pin packed CIC/support-atlas arrays through realization.
        approved_sparse_keys = {
            item.field_key
            for item in planning_record.phase_b_fields
            if str(item.metadata.get("backend", DENSE_BACKEND)) == LOCAL_SPARSE_BACKEND
        }
        for runtime_key in tuple(hybrid_runtime_artifacts):
            if runtime_key not in approved_sparse_keys:
                hybrid_runtime_artifacts.pop(runtime_key, None)
        planning_metadata_by_field = {
            exact.field_key: {
                "density_planning": {
                    "scene_approval_id": planning_record.approval_id,
                    "phase_a": upper.to_json_dict(),
                    "phase_b": exact.to_json_dict(include_indices=False),
                }
            }
            for upper, exact in zip(
                planning_record.phase_a_fields,
                planning_record.phase_b_fields,
                strict=True,
            )
        }

        density_planning_wall_seconds = time.perf_counter() - planning_started

        # PAR-DENS3: execute the exact Phase-B field plan through the one
        # PAR-DENS2 scene scheduler.  Each field keeps its planned scientific
        # identity and memory contract; only execution order/concurrency and
        # worker allocation change.  Deterministic scheduler collation restores
        # construction order before the realized fields are authenticated.
        density_scheduler = DensitySceneScheduler(
            resources.runtime_budget,
            policy=DensitySchedulerPolicy(max_parallel_tasks=autotuned_max_parallel_tasks()),
            progress=progress_port,
        )
        field_task_resources = tuple(
            task_resources_from_phase_b_plan(
                field_plan, preferred_workers=int(resources.max_threads)
            )
            for field_plan in planning_record.phase_b_fields
        )
        density_scheduler.validate_resources(field_task_resources)
        task_resources_by_key = {item.task_id: item for item in field_task_resources}

        atomic_plan_count = sum(
            1 for item in planning_record.phase_b_fields
            if item.source_kind == "atomic_occupancy"
        )
        framework_plan_count = len(planning_record.phase_b_fields) - atomic_plan_count
        atomic_per_field_voxel_budget = (
            int(resources.max_density_voxels)
            if atomic_plan_count == 0
            else max(1, int(resources.max_density_voxels) // atomic_plan_count)
        )
        atomic_dense_voxels = sum(
            int(item.logical_node_count)
            for item in planning_record.phase_b_fields
            if item.source_kind == "atomic_occupancy"
            and str(item.metadata.get("backend", DENSE_BACKEND)) == DENSE_BACKEND
        )
        framework_remaining_voxels = max(
            1, int(resources.max_density_voxels) - atomic_dense_voxels
        )
        framework_per_field_voxel_budget = (
            framework_remaining_voxels
            if framework_plan_count == 0
            else max(1, framework_remaining_voxels // framework_plan_count)
        )

        scheduled_density_tasks: list[DensityScheduledTask[ScalarField3D]] = []
        atomic_selection_by_key = {
            f"atomic-density-{index}": (index, selection)
            for index, selection in enumerate(atomic_selections)
        }

        for field_plan in planning_record.phase_b_fields:
            field_key = field_plan.field_key
            task_resources = task_resources_by_key[field_key]
            if field_plan.source_kind == "atomic_occupancy":
                try:
                    atomic_index, atomic_selection = atomic_selection_by_key[field_key]
                except KeyError as exc:
                    raise GraphAdapterError(
                        f"Phase-B atomic field {field_key!r} has no matching selection."
                    ) from exc

                def realize_atomic(
                    lease: Any,
                    *,
                    selection: AtomicDensitySelection = atomic_selection,
                    field_index: int = atomic_index,
                ) -> ScalarField3D:
                    # Refresh the nested budget at field entry.  Chunked kernels
                    # query the live lease directly and may consume CPUs returned
                    # by shorter sibling fields later in the realization.
                    with lease.budget_scope():
                        fields = prepare_atomic_density_fields(
                            collection,
                            frame_indices=frames,
                            frame_weights=weights,
                            display_cell=display_cell,
                            registration_mode=options.registration_mode.value,
                            framework_drift=np.zeros((len(frames), 3), dtype=np.float64),
                            registration_view=registration_view,
                            selections=(selection,),
                            options=atomic_options,
                            max_fields=1,
                            max_total_voxels=atomic_per_field_voxel_budget,
                            max_samples=resources.max_density_samples,
                            planning_metadata_by_field=planning_metadata_by_field,
                            resolved_plans_by_field=atomic_resolved_plans,
                            approved_hybrid_plans_by_field=hybrid_runtime_plans,
                            precomputed_hybrid_artifacts_by_field=hybrid_runtime_artifacts,
                            max_nonzero_nodes=limits.max_density_nonzero_nodes,
                            max_stored_block_values=limits.max_density_stored_block_values,
                            max_blocks=limits.max_density_blocks,
                            max_kernel_pairs=limits.max_density_kernel_pairs,
                            max_planning_bytes=limits.max_density_planning_bytes,
                            max_workspace_bytes=limits.max_density_total_peak_bytes,
                            max_cic_contributions=8 * limits.max_density_samples,
                            field_index_offset=field_index,
                            progress=progress_port,
                        )
                    if len(fields) != 1 or fields[0].field_key != f"atomic-density-{field_index}":
                        raise GraphAdapterError(
                            "Parallel atomic realization changed the planned field identity."
                        )
                    return fields[0]

                scheduled_density_tasks.append(
                    DensityScheduledTask(task_resources, realize_atomic)
                )
                continue

            if framework_density_options is None:
                raise GraphAdapterError(
                    f"Phase-B framework field {field_key!r} exists without framework options."
                )
            assert projected_display_fractional is not None
            assert edge_segments is not None
            if field_plan.source_kind == "framework_vertex_occupancy":
                channel_options = replace(
                    framework_density_options,
                    include_vertex_density=True,
                    include_edge_density=False,
                )
                expected_key = "framework-vertex-density"
            elif field_plan.source_kind == "framework_edge_length":
                channel_options = replace(
                    framework_density_options,
                    include_vertex_density=False,
                    include_edge_density=True,
                )
                expected_key = "framework-edge-length-density"
            else:
                raise GraphAdapterError(
                    f"Unsupported Phase-B density source kind {field_plan.source_kind!r}."
                )
            if field_key != expected_key:
                raise GraphAdapterError(
                    f"Phase-B framework field key {field_key!r} disagrees with {expected_key!r}."
                )

            def realize_framework_channel(
                lease: Any,
                *,
                local_options: FrameworkDensityOptions = channel_options,
                planned_key: str = field_key,
            ) -> ScalarField3D:
                with lease.budget_scope():
                    bundle = prepare_framework_density_fields(
                        vertex_fractional_by_frame=projected_display_fractional,
                        vertex_atom_indices=tuple(int(v) for v in topology.vertex_atom_indices),
                        edge_segments_fractional_by_frame=edge_segments,
                        edge_atom_indices=edge_atoms,
                        frame_weights=weights,
                        display_cell=display_cell,
                        registration_mode=options.registration_mode.value,
                        options=local_options,
                        max_fields=1,
                        consumer_registration_signature=registration_view.signature,
                        scientific_drift_owner="mdstats.coordinates.consumer_adapters",
                        max_total_voxels=framework_per_field_voxel_budget,
                        max_samples=resources.max_density_samples,
                        planning_metadata_by_field=planning_metadata_by_field,
                        approved_hybrid_plans_by_field=hybrid_runtime_plans,
                        vertex_source_keys=tuple(projected_view.node_keys),
                        edge_source_keys=tuple(edge_view.edge_keys),
                        max_nonzero_nodes=limits.max_density_nonzero_nodes,
                        max_stored_block_values=limits.max_density_stored_block_values,
                        max_blocks=limits.max_density_blocks,
                        max_kernel_pairs=limits.max_density_kernel_pairs,
                        max_planning_bytes=limits.max_density_planning_bytes,
                        max_workspace_bytes=limits.max_density_total_peak_bytes,
                        max_cic_contributions=8 * limits.max_density_samples,
                        progress=progress_port,
                    )
                fields = bundle.fields
                if len(fields) != 1 or fields[0].field_key != planned_key:
                    raise GraphAdapterError(
                        "Parallel framework realization changed the planned field identity."
                    )
                return fields[0]

            scheduled_density_tasks.append(
                DensityScheduledTask(task_resources, realize_framework_channel)
            )

        reporter.started(
            "density_realization",
            "constructing independent density fields through the PAR-DENS3 scheduler",
            current=0,
            total=len(scheduled_density_tasks),
            unit="fields",
            metadata={
                "parallel_field_realization_enabled": True,
                "scheduler_policy": "par_dens3_parallel_field_realization_v1",
            },
        )
        realization_started = time.perf_counter()
        try:
            realized_fields = density_scheduler.run(tuple(scheduled_density_tasks))
        except DensitySchedulerTaskError as exc:
            # Preserve the public plotting facade's historical exception type.
            # Scheduler wrappers are execution detail and remain available to
            # callers that invoke DensitySceneScheduler directly.
            raise exc.original from exc
        density_realization_wall_seconds = time.perf_counter() - realization_started
        scheduler_report = density_scheduler.last_report
        if scheduler_report is None:
            raise GraphAdapterError("PAR-DENS3 scheduler completed without an execution report.")
        reporter.completed(
            "density_realization",
            "completed parallel density field realization",
            current=len(realized_fields),
            total=len(realized_fields),
            unit="fields",
            metadata={
                "maximum_concurrent_tasks": scheduler_report.maximum_concurrent_tasks,
                "peak_reserved_bytes": scheduler_report.peak_reserved_bytes,
            },
        )

        density_fields = tuple(
            field
            for plan, field in zip(
                planning_record.phase_b_fields, realized_fields, strict=True
            )
            if plan.source_kind == "atomic_occupancy"
        )
        framework_vertex_field = next(
            (
                field
                for plan, field in zip(
                    planning_record.phase_b_fields, realized_fields, strict=True
                )
                if plan.source_kind == "framework_vertex_occupancy"
            ),
            None,
        )
        framework_edge_field = next(
            (
                field
                for plan, field in zip(
                    planning_record.phase_b_fields, realized_fields, strict=True
                )
                if plan.source_kind == "framework_edge_length"
            ),
            None,
        )
        if framework_vertex_field is None and framework_edge_field is None:
            framework_densities = None
        else:
            assert framework_density_options is not None
            framework_densities = FrameworkDensityFields(
                vertex_density=framework_vertex_field,
                edge_length_density=framework_edge_field,
                edge_source=framework_density_options.edge_source,
                metadata={
                    "schema_version": FRAMEWORK_DENSITY_SCHEMA,
                    "channels_are_dimensionally_distinct": True,
                    "consumer_registration_signature": registration_view.signature,
                    "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
                    "consumer_migration_stage": "C0B",
                },
            )
        realization_metadata = validate_realized_fields(
            planning_record, realized_fields
        )
        density_scheduler_policy = "par_dens3_parallel_field_realization_v1"

    preparation_wall_seconds = time.perf_counter() - preparation_started
    reporter.completed(
        "scene_preparation",
        f"completed in {preparation_wall_seconds:.3f} s",
        metadata={"wall_seconds": float(preparation_wall_seconds)},
    )
    return FrameworkDynamicsScene(
        mean_framework=mean_view,
        trajectory_paths=paths,
        atomic_mean_graph=atomic_mean_graph,
        atomic_density_fields=density_fields,
        framework_density_fields=framework_densities,
        planning_record=planning_record,
        frame_indices=np.asarray(frames, dtype=np.int64),
        weights=weights,
        display_cell=display_cell,
        options=options,
        resources=resources,
        metadata={
            "schema_version": FRAMEWORK_DYNAMICS_SCENE_SCHEMA,
            "source_framework_topology_digest": topology.digest,
            "source_framework_graph_digest": topology.graph_digest,
            "collection_semantics": collection.frame_semantics.value,
            "reference_frame": reference_frame,
            "registration_mode": options.registration_mode.value,
            "display_cell_policy": options.display_cell,
            "consumer_registration_signature": registration_view.signature,
            "frame_registration_signature": registration_view.registration.signature,
            "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
            "pair_geometry_policy": "physical",
            "consumer_migration_stage": "C0B",
            **cell_equivalence.metadata_dict(),
            "display_mode": FrameworkGraphDisplayMode(display_mode).value,
            "trajectory_atom_indices": selected_atoms,
            "atomic_mean_graph": atomic_mean_graph is not None,
            "atomic_density_field_keys": tuple(v.field_key for v in density_fields),
            "framework_density_field_keys": (
                ()
                if framework_densities is None
                else tuple(v.field_key for v in framework_densities.fields)
            ),
            "density_planning_approval_id": (
                None if planning_record is None else planning_record.approval_id
            ),
            "density_planning_summary": (
                {}
                if planning_record is None
                else planning_record.to_json_dict(include_indices=False)
            ),
            "density_realization_summary": dict(realization_metadata),
            "density_scheduler_policy": density_scheduler_policy,
            "density_scheduler_summary": (
                {}
                if planning_record is None or density_scheduler.last_report is None
                else density_scheduler.last_report.to_json_dict()
            ),
            "density_scheduler_field_contract_schema": (
                None
                if planning_record is None
                else "mdstats.density-task-resources.v1"
            ),
            "trajectory_preprocessing_policy": "par_dens4_parallel_geometry_reuse_v1",
            "trajectory_preprocessing_scheduler_summary": (
                {}
                if preprocessing_scheduler.last_report is None
                else preprocessing_scheduler.last_report.to_json_dict()
            ),
            "framework_geometry_cache": geometry_cache.summary(),
            "resource_policy": resources.to_json_dict(),
            "preparation_wall_seconds": preparation_wall_seconds,
            "trajectory_preprocessing_wall_seconds": preprocessing_wall_seconds,
            "density_planning_wall_seconds": density_planning_wall_seconds,
            "density_realization_wall_seconds": density_realization_wall_seconds,
        },
    )


def _path_coordinates(
    positions: FloatArray, breaks: BoolArray
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    x: list[float | None] = []
    y: list[float | None] = []
    z: list[float | None] = []
    for index, point in enumerate(positions):
        if index > 0 and bool(breaks[index - 1]):
            x.append(None)
            y.append(None)
            z.append(None)
        x.append(float(point[0]))
        y.append(float(point[1]))
        z.append(float(point[2]))
    return x, y, z


def _expanded_ranges(points: FloatArray) -> list[list[float]]:
    minima = np.min(points, axis=0)
    maxima = np.max(points, axis=0)
    extents = maxima - minima
    maximum = max(1.0, float(np.max(extents)))
    result: list[list[float]] = []
    for low, high, extent in zip(minima, maxima, extents, strict=True):
        pad = 0.04 * (float(extent) if float(extent) > 1.0e-12 else maximum)
        result.append([float(low - pad), float(high + pad)])
    return result


def _apply_equal_aspect_ranges(figure: Any, points: FloatArray) -> None:
    """Update composite scene ranges and keep one Cartesian unit equally scaled."""
    ranges = _expanded_ranges(np.asarray(points, dtype=np.float64))
    extents = np.asarray([high - low for low, high in ranges], dtype=np.float64)
    maximum = max(float(np.max(extents)), 1.0)
    aspectratio = {
        axis: float(extent / maximum) if extent > 0.0 else 1.0
        for axis, extent in zip(("x", "y", "z"), extents, strict=True)
    }
    figure.update_layout(
        scene={
            "xaxis": {"range": ranges[0]},
            "yaxis": {"range": ranges[1]},
            "zaxis": {"range": ranges[2]},
            "aspectmode": "manual",
            "aspectratio": aspectratio,
        }
    )


def _density_grid_arrays(
    field: PeriodicScalarField3D,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Return a periodic seam-closed Cartesian grid with raw density values."""
    values = np.asarray(field.values, dtype=np.float64)
    extended = np.pad(values, ((0, 1), (0, 1), (0, 1)), mode="wrap")
    axes = [np.arange(n + 1, dtype=np.float64) / n for n in field.grid_shape]
    fx, fy, fz = np.meshgrid(*axes, indexing="ij")
    fractional = np.stack((fx, fy, fz), axis=-1)
    cartesian = fractional @ field.display_cell
    return (
        cartesian[..., 0].ravel(),
        cartesian[..., 1].ravel(),
        cartesian[..., 2].ravel(),
        extended.ravel(),
    )


def _append_category_atomic_mean_graph(
    figure: Any,
    graph: AtomicMeanGraph | None,
    *,
    render_options: AtomicMeanGraph3DRenderOptions,
    legendgroup: str,
    visible: bool | Literal["legendonly"],
    key_prefix: str,
) -> dict[str, tuple[int, ...]]:
    if graph is None:
        return {}
    try:
        import plotly.graph_objects as go
        from ase.data.colors import jmol_colors
    except ImportError as exc:  # pragma: no cover
        raise GraphVisualizationError(
            "Plotly and ASE are required for atomic mean-graph rendering."
        ) from exc
    result: dict[str, tuple[int, ...]] = {}
    positions = np.asarray(graph.display_positions, dtype=np.float64)
    numbers = np.asarray(graph.atomic_numbers, dtype=np.int64)
    if graph.edge_endpoints.shape[0] > 0:
        starts = positions[np.asarray(graph.edge_endpoints[:, 0], dtype=np.int64)]
        ends = (
            positions[np.asarray(graph.edge_endpoints[:, 1], dtype=np.int64)]
            + np.asarray(graph.edge_image_shifts, dtype=np.float64)
            @ np.asarray(graph.display_cell, dtype=np.float64)
        )
        x = np.column_stack((starts[:, 0], ends[:, 0], np.full(len(starts), np.nan))).ravel()
        y = np.column_stack((starts[:, 1], ends[:, 1], np.full(len(starts), np.nan))).ravel()
        z = np.column_stack((starts[:, 2], ends[:, 2], np.full(len(starts), np.nan))).ravel()
        index = len(figure.data)
        figure.add_trace(
            go.Scatter3d(
                x=x, y=y, z=z, mode="lines", name="Atomic connectivity",
                legendgroup=legendgroup, showlegend=False, visible=visible,
                line={"width": render_options.edge_width, "color": render_options.edge_color},
                opacity=render_options.edge_opacity, hoverinfo="skip",
            )
        )
        result[f"{key_prefix}:bonds"] = (index,)
    for number in sorted(set(int(value) for value in numbers.tolist())):
        mask = numbers == number
        rgb = np.asarray(jmol_colors[number], dtype=np.float64)
        color = f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, {round(rgb[2] * 255)})"
        index = len(figure.data)
        figure.add_trace(
            go.Scatter3d(
                x=positions[mask, 0], y=positions[mask, 1], z=positions[mask, 2],
                mode="markers", name=f"{chemical_symbols[number]} atoms",
                legendgroup=legendgroup, showlegend=False, visible=visible,
                marker={
                    "size": render_options.node_size,
                    "color": color,
                    "opacity": render_options.node_opacity,
                },
                hoverinfo="skip",
            )
        )
        result[f"{key_prefix}:{chemical_symbols[number]}"] = (index,)
    return result


def _apply_topology_legend_group(
    figure: Any,
    trace_indices: Sequence[int],
    *,
    layer: FrameworkTopologyCategoryLayer,
    visible: bool | Literal["legendonly"],
) -> None:
    indices = tuple(dict.fromkeys(int(value) for value in trace_indices))
    if not indices:
        return
    group = f"framework-topology:{layer.topology_id}"
    for position, index in enumerate(indices):
        trace = figure.data[index]
        trace.legendgroup = group
        trace.visible = visible
        trace.showlegend = position == 0
        if position == 0:
            trace.name = layer.legend_title
            trace.legendgrouptitle = {"text": f"Framework topology {layer.topology_id}"}


def _compact_partitioned_base_result(
    base: InteractiveGraphRenderResult,
) -> InteractiveGraphRenderResult:
    """Retain only cell traces before compact category traces are appended.

    The general decorated-graph renderer intentionally emits one trace per
    resolved style bucket.  That is useful for a standalone graph, but it
    multiplies traces by the number of topology categories.  Partitioned scenes
    therefore reuse its validated periodic view, layout, and cell wireframe
    while rendering category graphs through the compact four-trace adapter.
    """

    try:
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover
        raise GraphVisualizationError(
            "Plotly is required for compact topology-category rendering."
        ) from exc
    cell_traces = tuple(base.figure.data[index] for index in base.cell_trace_indices)
    figure = go.Figure(data=cell_traces, layout=base.figure.layout)
    return InteractiveGraphRenderResult(
        figure=figure,
        periodic_view=base.periodic_view,
        rendered_node_keys=base.rendered_node_keys,
        rendered_edge_keys=base.rendered_edge_keys,
        node_trace_indices={},
        edge_trace_indices={},
        hover_trace_indices={},
        cell_trace_indices=tuple(range(len(cell_traces))),
        complexity=base.complexity,
        style_metadata={
            **dict(base.style_metadata),
            "partitioned_category_adapter": "compact_four_trace_v1",
        },
        render_metadata={
            **dict(base.render_metadata),
            "partitioned_category_adapter": "compact_four_trace_v1",
            "discarded_general_graph_trace_count": (
                len(base.figure.data) - len(cell_traces)
            ),
        },
        warnings=base.warnings,
    )


def _framework_node_colors(view: DecoratedGraphView) -> list[str]:
    """Return one Plotly color per framework node without trace splitting."""

    try:
        from ase.data.colors import jmol_colors
    except ImportError as exc:  # pragma: no cover
        raise GraphVisualizationError(
            "ASE colors are required for compact topology-category rendering."
        ) from exc
    symbols = view.node_attributes.get("symbol")
    atomic_numbers = view.node_attributes.get("atomic_number")
    result: list[str] = []
    for index in range(view.n_nodes):
        number = 0
        if atomic_numbers is not None:
            try:
                number = int(atomic_numbers[index])
            except (TypeError, ValueError):
                number = 0
        elif symbols is not None:
            symbol = str(symbols[index])
            try:
                number = chemical_symbols.index(symbol)
            except ValueError:
                number = 0
        if 0 < number < len(jmol_colors):
            rgb = np.asarray(jmol_colors[number], dtype=np.float64)
            result.append(
                f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, "
                f"{round(rgb[2] * 255)})"
            )
        else:
            result.append("rgb(80, 120, 170)")
    return result


def _append_compact_topology_category(
    figure: Any,
    layer: FrameworkTopologyCategoryLayer,
    *,
    atomic_options: AtomicMeanGraph3DRenderOptions,
    visible: bool | Literal["legendonly"],
    node_hover: bool,
    edge_hover: bool,
) -> tuple[tuple[int, ...], dict[str, tuple[int, ...]]]:
    """Append at most four traces for one topology category.

    The compact representation uses one framework-edge trace, one framework-node
    trace, one atomic-edge trace, and one atomic-node trace.  Per-node colors are
    carried by Plotly marker arrays rather than by creating one trace per species
    or style bucket.
    """

    try:
        import plotly.graph_objects as go
        from ase.data.colors import jmol_colors
    except ImportError as exc:  # pragma: no cover
        raise GraphVisualizationError(
            "Plotly and ASE are required for topology-category rendering."
        ) from exc
    group = f"framework-topology:{layer.topology_id}"
    indices: list[int] = []
    atomic_indices: dict[str, tuple[int, ...]] = {}
    view = layer.mean_framework
    if view.node_positions_3d is None or view.cell is None:
        raise GraphAdapterError(
            "Compact topology-category rendering requires 3-D node positions and a cell."
        )
    positions = np.asarray(view.node_positions_3d, dtype=np.float64)
    cell = np.asarray(view.cell, dtype=np.float64)
    endpoints = np.asarray(view.edge_endpoints, dtype=np.int64)
    shifts = (
        np.zeros((endpoints.shape[0], 3), dtype=np.int64)
        if view.edge_image_shifts is None
        else np.asarray(view.edge_image_shifts, dtype=np.int64)
    )
    if endpoints.shape[0] > 0:
        starts = positions[endpoints[:, 0]]
        ends = positions[endpoints[:, 1]] + shifts @ cell
        xyz = [
            np.column_stack((starts[:, axis], ends[:, axis], np.full(len(starts), np.nan))).ravel()
            for axis in range(3)
        ]
        hover = None
        if edge_hover:
            hover = np.repeat(
                np.asarray(
                    [f"framework edge={key!r}" for key in view.edge_keys],
                    dtype=object,
                ),
                3,
            )
            hover[2::3] = None
        index = len(figure.data)
        figure.add_trace(
            go.Scatter3d(
                x=xyz[0], y=xyz[1], z=xyz[2], mode="lines",
                name="Framework connectivity", legendgroup=group,
                showlegend=False, visible=visible,
                line={"width": 2.0, "color": "rgba(105, 105, 105, 0.78)"},
                text=hover,
                hovertemplate=("%{text}<extra></extra>" if hover is not None else None),
                hoverinfo=(None if hover is not None else "skip"),
            )
        )
        indices.append(index)
    node_hover_text = None
    if node_hover:
        symbols = view.node_attributes.get("symbol")
        node_hover_text = [
            (
                f"node={key!r}"
                if symbols is None
                else f"node={key!r}<br>species={symbols[position]}"
            )
            for position, key in enumerate(view.node_keys)
        ]
    index = len(figure.data)
    figure.add_trace(
        go.Scatter3d(
            x=positions[:, 0], y=positions[:, 1], z=positions[:, 2],
            mode="markers", name="Framework atoms", legendgroup=group,
            showlegend=False, visible=visible,
            marker={
                "size": 5.5,
                "color": _framework_node_colors(view),
                "opacity": 0.95,
            },
            text=node_hover_text,
            hovertemplate=(
                "%{text}<extra></extra>" if node_hover_text is not None else None
            ),
            hoverinfo=(None if node_hover_text is not None else "skip"),
        )
    )
    indices.append(index)

    graph = layer.atomic_mean_graph
    if graph is not None:
        atomic_positions = np.asarray(graph.display_positions, dtype=np.float64)
        numbers = np.asarray(graph.atomic_numbers, dtype=np.int64)
        if graph.edge_endpoints.shape[0] > 0:
            atomic_endpoints = np.asarray(graph.edge_endpoints, dtype=np.int64)
            starts = atomic_positions[atomic_endpoints[:, 0]]
            ends = (
                atomic_positions[atomic_endpoints[:, 1]]
                + np.asarray(graph.edge_image_shifts, dtype=np.float64)
                @ np.asarray(graph.display_cell, dtype=np.float64)
            )
            xyz = [
                np.column_stack((starts[:, axis], ends[:, axis], np.full(len(starts), np.nan))).ravel()
                for axis in range(3)
            ]
            hover = None
            if edge_hover:
                labels = [
                    f"atomic edge occupancy={float(value):.3f}"
                    for value in graph.edge_occupancies
                ]
                hover = np.repeat(np.asarray(labels, dtype=object), 3)
                hover[2::3] = None
            edge_index = len(figure.data)
            figure.add_trace(
                go.Scatter3d(
                    x=xyz[0], y=xyz[1], z=xyz[2], mode="lines",
                    name="Atomic connectivity", legendgroup=group,
                    showlegend=False, visible=visible,
                    line={
                        "width": atomic_options.edge_width,
                        "color": atomic_options.edge_color,
                    },
                    opacity=atomic_options.edge_opacity,
                    text=hover,
                    hovertemplate=(
                        "%{text}<extra></extra>" if hover is not None else None
                    ),
                    hoverinfo=(None if hover is not None else "skip"),
                )
            )
            indices.append(edge_index)
            atomic_indices[f"topology:{layer.topology_id}:bonds"] = (edge_index,)
        colors: list[str] = []
        hover = []
        for atom_index, number in zip(graph.atom_indices, numbers, strict=True):
            rgb = np.asarray(jmol_colors[int(number)], dtype=np.float64)
            colors.append(
                f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, "
                f"{round(rgb[2] * 255)})"
            )
            hover.append(
                f"atom={atom_index}<br>species={chemical_symbols[int(number)]}"
            )
        node_index = len(figure.data)
        figure.add_trace(
            go.Scatter3d(
                x=atomic_positions[:, 0], y=atomic_positions[:, 1],
                z=atomic_positions[:, 2], mode="markers",
                name="Atomic mean positions", legendgroup=group,
                showlegend=False, visible=visible,
                marker={
                    "size": atomic_options.node_size,
                    "color": colors,
                    "opacity": atomic_options.node_opacity,
                },
                text=(hover if node_hover else None),
                hovertemplate=(
                    "%{text}<extra></extra>" if node_hover else None
                ),
                hoverinfo=(None if node_hover else "skip"),
            )
        )
        indices.append(node_index)
        atomic_indices[f"topology:{layer.topology_id}:atoms"] = (node_index,)
    _apply_topology_legend_group(
        figure,
        indices,
        layer=layer,
        visible=visible,
    )
    return tuple(indices), atomic_indices


def plot_framework_dynamics_3d(
    scene: FrameworkDynamicsScene,
    *,
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    graph_options: Graph3DRenderOptions | None = None,
    atomic_mean_graph_options: AtomicMeanGraph3DRenderOptions | None = None,
    trajectory_options: Trajectory3DRenderOptions | None = None,
    density_options: AtomicDensity3DRenderOptions | None = None,
    framework_density_options: FrameworkDensity3DRenderOptions | None = None,
    browser_budget: BrowserMeshBudget | None = None,
    browser_profile: Literal["interactive_browser", "raw_reference"] = INTERACTIVE_BROWSER_PROFILE,
    mesh_profile: BrowserMeshProfile | Literal["compact", "balanced", "quality", "custom"] | None = None,
    scene_allocation_options: DensitySceneAllocationOptions | None = None,
    mesh_simplification_options: MeshSimplificationOptions | None = None,
    mesh_execution_options: DensityMeshExecutionOptions | None = None,
    isolate_large_sparse_meshes: bool = True,
    isolation_node_threshold: int = 250_000,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> FrameworkDynamicsRenderResult:
    """Render one scene while containing package-controlled native threads."""

    if not isinstance(scene, FrameworkDynamicsScene):
        raise TypeError("scene must be a FrameworkDynamicsScene.")
    try:
        from threadpoolctl import threadpool_limits
    except ImportError as error:  # pragma: no cover - declared base dependency
        raise GraphUnsupportedFeatureError(
            "Runtime thread containment requires threadpoolctl."
        ) from error
    with (
        density_resource_budget_scope(scene.resources.runtime_budget),
        density_time_model_scope(scene.resources.time_model),
        threadpool_limits(limits=int(scene.resources.max_threads)),
    ):
        return _plot_framework_dynamics_3d_impl(
            scene,
            periodic=periodic,
            style=style,
            focus=focus,
            graph_filter=graph_filter,
            complexity_policy=complexity_policy,
            graph_options=graph_options,
            atomic_mean_graph_options=atomic_mean_graph_options,
            trajectory_options=trajectory_options,
            density_options=density_options,
            framework_density_options=framework_density_options,
            browser_budget=browser_budget,
            browser_profile=browser_profile,
            mesh_profile=mesh_profile,
            scene_allocation_options=scene_allocation_options,
            mesh_simplification_options=mesh_simplification_options,
            mesh_execution_options=mesh_execution_options,
            isolate_large_sparse_meshes=isolate_large_sparse_meshes,
            isolation_node_threshold=isolation_node_threshold,
            progress=progress,
            progress_callback=progress_callback,
        )


def _plot_framework_dynamics_3d_impl(
    scene: FrameworkDynamicsScene,
    *,
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    graph_options: Graph3DRenderOptions | None = None,
    atomic_mean_graph_options: AtomicMeanGraph3DRenderOptions | None = None,
    trajectory_options: Trajectory3DRenderOptions | None = None,
    density_options: AtomicDensity3DRenderOptions | None = None,
    framework_density_options: FrameworkDensity3DRenderOptions | None = None,
    browser_budget: BrowserMeshBudget | None = None,
    browser_profile: Literal["interactive_browser", "raw_reference"] = INTERACTIVE_BROWSER_PROFILE,
    mesh_profile: BrowserMeshProfile | Literal["compact", "balanced", "quality", "custom"] | None = None,
    scene_allocation_options: DensitySceneAllocationOptions | None = None,
    mesh_simplification_options: MeshSimplificationOptions | None = None,
    mesh_execution_options: DensityMeshExecutionOptions | None = None,
    isolate_large_sparse_meshes: bool = True,
    isolation_node_threshold: int = 250_000,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> FrameworkDynamicsRenderResult:
    """Render a prepared mean framework and selected atomic trajectories."""
    if not isinstance(scene, FrameworkDynamicsScene):
        raise TypeError("scene must be a FrameworkDynamicsScene.")
    render_started = time.perf_counter()
    preparation_wall_seconds = float(
        scene.metadata.get("preparation_wall_seconds", 0.0)
    )
    # Wall time is advisory only.  Keep the configured target for diagnostics,
    # but never turn elapsed preparation time into a rendering admission gate.
    remaining_scene_wall_seconds: float | None = None
    atomic_mean_graph_options = (
        atomic_mean_graph_options or AtomicMeanGraph3DRenderOptions()
    )
    trajectory_options = trajectory_options or Trajectory3DRenderOptions()
    density_options = density_options or AtomicDensity3DRenderOptions()
    framework_density_options = (
        framework_density_options
        or FrameworkDensity3DRenderOptions(inner_opacity=0.22, outer_opacity=0.035)
    )
    resolved_mesh_profile = BrowserMeshProfile.coerce(
        mesh_profile, custom_budget=browser_budget
    )
    resolved_browser_budget = resolved_mesh_profile.budget
    resolved_browser_budget.validate_for_profile(browser_profile)
    resolved_allocation_options = (
        DensitySceneAllocationOptions()
        if scene_allocation_options is None
        else scene_allocation_options
    )
    if not isinstance(resolved_allocation_options, DensitySceneAllocationOptions):
        raise TypeError("scene_allocation_options must be DensitySceneAllocationOptions or None.")
    requested_mesh_execution_options = (
        DensityMeshExecutionOptions()
        if mesh_execution_options is None
        else mesh_execution_options
    )
    if not isinstance(requested_mesh_execution_options, DensityMeshExecutionOptions):
        raise TypeError(
            "mesh_execution_options must be DensityMeshExecutionOptions or None."
        )
    resolved_simplification_options = (
        MeshSimplificationOptions(
            local_target_fraction=0.25,
            min_component_faces=4,
            max_attempts=6,
            aggressiveness=7.0,
            max_samples=10_000,
            max_surface_error_p99=0.06,
            max_surface_error_max=0.24,
            max_implicit_displacement_p99=0.04,
            max_normal_degradation_degrees=30.0,
            max_relative_scalar_residual_p99=0.35,
            hard_target=False,
        )
        if mesh_simplification_options is None
        else mesh_simplification_options
    )
    if not isinstance(resolved_simplification_options, MeshSimplificationOptions):
        raise TypeError("mesh_simplification_options must be MeshSimplificationOptions or None.")
    if not isinstance(isolate_large_sparse_meshes, bool):
        raise TypeError("isolate_large_sparse_meshes must be bool.")
    if isinstance(isolation_node_threshold, bool) or int(isolation_node_threshold) <= 0:
        raise GraphStyleError("isolation_node_threshold must be a positive integer.")
    resolved_isolation_node_threshold = int(isolation_node_threshold)
    progress_port = resolve_progress_port(
        progress,
        progress_callback=progress_callback,
        environment_variable="MDSTATS_RENDER_PROGRESS",
        environment_label="mdstats-render",
        environment_stream=sys.stderr,
    )
    reporter = ProgressEmitter(
        progress_port,
        source="plotting.framework_dynamics.render",
    )
    reporter.started("scene_assembly", "begin scene assembly")
    resolved_graph_options = graph_options or Graph3DRenderOptions(
        edge_color_mode="constant"
    )
    base = plot_decorated_graph_3d(
        scene.mean_framework,
        periodic=periodic,
        style=style or GraphStyle.framework_default(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        options=resolved_graph_options,
    )
    partitioned_categories = bool(scene.topology_categories)
    if partitioned_categories:
        base = _compact_partitioned_base_result(base)
    figure = base.figure
    traces: dict[int, tuple[int, ...]] = {}
    atomic_mean_graph_trace_indices: dict[str, tuple[int, ...]] = {}
    endpoint_indices: list[int] = []
    atomic_mean_graph = None if partitioned_categories else scene.atomic_mean_graph
    if atomic_mean_graph is not None:
        try:
            import plotly.graph_objects as go
            from ase.data.colors import jmol_colors
        except ImportError as exc:  # pragma: no cover
            raise GraphVisualizationError(
                "Plotly and ASE are required for atomic mean-graph rendering."
            ) from exc
        projected = len(set(int(v) for v in atomic_mean_graph.atomic_numbers.tolist()))
        if atomic_mean_graph.edge_endpoints.shape[0] > 0:
            projected += 1
        total_traces = len(base.figure.data) + projected
        if total_traces > resolved_graph_options.max_plotly_traces:
            raise GraphComplexityError(
                f"Composite rendering requires {total_traces} Plotly traces, exceeding "
                f"max_plotly_traces={resolved_graph_options.max_plotly_traces}."
            )
        positions = np.asarray(atomic_mean_graph.display_positions, dtype=np.float64)
        atom_indices = atomic_mean_graph.atom_indices
        numbers = np.asarray(atomic_mean_graph.atomic_numbers, dtype=np.int64)
        unique_numbers = tuple(sorted(set(int(v) for v in numbers.tolist())))
        if atomic_mean_graph.edge_endpoints.shape[0] > 0:
            x: list[float | None] = []
            y: list[float | None] = []
            z: list[float | None] = []
            hover: list[str | None] = []
            cell = np.asarray(atomic_mean_graph.display_cell, dtype=np.float64)
            for edge_position, ((source, target), shift, occ) in enumerate(
                zip(
                    atomic_mean_graph.edge_endpoints,
                    atomic_mean_graph.edge_image_shifts,
                    atomic_mean_graph.edge_occupancies,
                    strict=True,
                )
            ):
                i = int(source)
                j = int(target)
                start = positions[i]
                end = positions[j] + np.asarray(shift, dtype=np.float64) @ cell
                x.extend([float(start[0]), float(end[0]), None])
                y.extend([float(start[1]), float(end[1]), None])
                z.extend([float(start[2]), float(end[2]), None])
                left = atom_indices[i]
                right = atom_indices[j]
                left_symbol = chemical_symbols[int(numbers[i])]
                right_symbol = chemical_symbols[int(numbers[j])]
                hover.extend(
                    [
                        f"bond {left}-{right}<br>{left_symbol}-{right_symbol}<br>occupancy={float(occ):.3f}",
                        f"bond {left}-{right}<br>{left_symbol}-{right_symbol}<br>occupancy={float(occ):.3f}",
                        None,
                    ]
                )
            trace_index = len(figure.data)
            figure.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="lines",
                    name="Atomic bonds",
                    legendgroup="atomic-mean-graph:edges",
                    showlegend=atomic_mean_graph_options.show_legend,
                    line={
                        "width": atomic_mean_graph_options.edge_width,
                        "color": atomic_mean_graph_options.edge_color,
                    },
                    opacity=atomic_mean_graph_options.edge_opacity,
                    text=hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
            atomic_mean_graph_trace_indices["bonds"] = (trace_index,)
        for number in unique_numbers:
            mask = numbers == number
            species_positions = positions[mask]
            species_atoms = [atom_indices[idx] for idx in np.flatnonzero(mask)]
            symbol = chemical_symbols[number]
            rgb = np.asarray(jmol_colors[number], dtype=np.float64)
            color = f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, {round(rgb[2] * 255)})"
            hover = [f"atom={atom}<br>species={symbol}" for atom in species_atoms]
            trace_index = len(figure.data)
            figure.add_trace(
                go.Scatter3d(
                    x=species_positions[:, 0],
                    y=species_positions[:, 1],
                    z=species_positions[:, 2],
                    mode="markers",
                    name=f"{symbol} atoms",
                    legendgroup=f"atomic-mean-graph:species:{symbol}",
                    showlegend=atomic_mean_graph_options.show_legend,
                    marker={
                        "size": atomic_mean_graph_options.node_size,
                        "color": color,
                        "opacity": atomic_mean_graph_options.node_opacity,
                    },
                    text=hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
            atomic_mean_graph_trace_indices[symbol] = (trace_index,)
    topology_category_trace_indices: dict[int, tuple[int, ...]] = {}
    if scene.topology_categories:
        projected_category_traces = 4 * len(scene.topology_categories)
        if len(figure.data) + projected_category_traces > resolved_graph_options.max_plotly_traces:
            raise GraphComplexityError(
                "Compact topology-category rendering requires at most "
                f"{projected_category_traces} category traces plus "
                f"{len(figure.data)} retained traces, exceeding "
                f"max_plotly_traces={resolved_graph_options.max_plotly_traces}."
            )
        for layer in scene.topology_categories:
            visible: bool | Literal["legendonly"] = (
                True
                if layer.topology_id == scene.dominant_topology_id
                else "legendonly"
            )
            category_indices, category_atomic = _append_compact_topology_category(
                figure,
                layer,
                atomic_options=atomic_mean_graph_options,
                visible=visible,
                node_hover=resolved_graph_options.node_hover,
                edge_hover=resolved_graph_options.edge_hover,
            )
            atomic_mean_graph_trace_indices.update(category_atomic)
            topology_category_trace_indices[layer.topology_id] = category_indices

    paths = scene.trajectory_paths
    if paths is not None:
        unique_numbers = tuple(sorted(set(int(v) for v in paths.atomic_numbers.tolist())))
        projected_path_traces = (
            len(unique_numbers) if trajectory_options.group_by_species else paths.n_atoms
        )
        projected = projected_path_traces + (2 if trajectory_options.show_start_end else 0)
        if projected > scene.resources.max_trajectory_traces:
            raise GraphComplexityError(
                f"Trajectory rendering requires {projected} traces, exceeding "
                f"max_trajectory_traces={scene.resources.max_trajectory_traces}."
            )
        total_traces = len(figure.data) + projected
        if total_traces > resolved_graph_options.max_plotly_traces:
            raise GraphComplexityError(
                f"Composite rendering requires {total_traces} Plotly traces, exceeding "
                f"max_plotly_traces={resolved_graph_options.max_plotly_traces}."
            )
        try:
            import plotly.graph_objects as go
            from ase.data.colors import jmol_colors
        except ImportError as exc:  # pragma: no cover - base renderer already checks
            raise GraphVisualizationError(
                "Plotly and ASE are required for 3-D trajectories."
            ) from exc

        if trajectory_options.group_by_species:
            for number in unique_numbers:
                species_locals = np.flatnonzero(paths.atomic_numbers == number)
                symbol = chemical_symbols[number]
                rgb = np.asarray(jmol_colors[number], dtype=np.float64)
                color = f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, {round(rgb[2] * 255)})"
                x: list[float | None] = []
                y: list[float | None] = []
                z: list[float | None] = []
                hover: list[str | None] | None = [] if trajectory_options.enable_hover else None
                for item_position, local in enumerate(species_locals):
                    if item_position > 0:
                        x.append(None); y.append(None); z.append(None)
                        if hover is not None:
                            hover.append(None)
                    atom = paths.atom_indices[int(local)]
                    positions = paths.display_positions[int(local)]
                    px, py, pz = _path_coordinates(positions, paths.segment_breaks[int(local)])
                    x.extend(px); y.extend(py); z.extend(pz)
                    if hover is not None:
                        for frame_position, frame in enumerate(paths.frame_indices):
                            if frame_position > 0 and bool(paths.segment_breaks[int(local), frame_position - 1]):
                                hover.append(None)
                            time_text = (
                                "" if paths.times is None
                                else f"<br>time={float(paths.times[frame_position]):.6g} fs"
                            )
                            hover.append(
                                f"atom={atom} ({symbol})<br>frame={int(frame)}"
                                f"<br>frame_id={int(paths.frame_ids[frame_position])}{time_text}"
                            )
                trace_index = len(figure.data)
                figure.add_trace(
                    go.Scatter3d(
                        x=x, y=y, z=z, mode="lines",
                        name=f"{symbol} trajectories",
                        legendgroup=f"trajectory-species:{symbol}",
                        showlegend=trajectory_options.show_legend,
                        line={"width": trajectory_options.line_width, "color": color},
                        opacity=trajectory_options.opacity,
                        text=hover,
                        hovertemplate=("%{text}<extra></extra>" if hover is not None else None),
                        hoverinfo=(None if hover is not None else "skip"),
                    )
                )
                for local in species_locals:
                    traces[paths.atom_indices[int(local)]] = (trace_index,)
        else:
            for local, atom in enumerate(paths.atom_indices):
                positions = paths.display_positions[local]
                x, y, z = _path_coordinates(positions, paths.segment_breaks[local])
                number = int(paths.atomic_numbers[local])
                symbol = chemical_symbols[number]
                hover: list[str | None] | None = [] if trajectory_options.enable_hover else None
                if hover is not None:
                    for frame_position, frame in enumerate(paths.frame_indices):
                        if frame_position > 0 and bool(paths.segment_breaks[local, frame_position - 1]):
                            hover.append(None)
                        time_text = (
                            "" if paths.times is None
                            else f"<br>time={float(paths.times[frame_position]):.6g} fs"
                        )
                        hover.append(
                            f"atom={atom} ({symbol})<br>frame={int(frame)}"
                            f"<br>frame_id={int(paths.frame_ids[frame_position])}{time_text}"
                        )
                trace_index = len(figure.data)
                figure.add_trace(
                    go.Scatter3d(
                        x=x, y=y, z=z, mode="lines",
                        name=paths.selection_label,
                        legendgroup=f"trajectory-selection:{paths.selection_label}",
                        showlegend=(trajectory_options.show_legend and local == 0),
                        line={"width": trajectory_options.line_width},
                        opacity=trajectory_options.opacity,
                        text=hover,
                        hovertemplate=("%{text}<extra></extra>" if hover is not None else None),
                        hoverinfo=(None if hover is not None else "skip"),
                    )
                )
                traces[atom] = (trace_index,)

        if trajectory_options.show_start_end:
            endpoint_colors = []
            for number in paths.atomic_numbers:
                rgb = np.asarray(jmol_colors[int(number)], dtype=np.float64)
                endpoint_colors.append(
                    f"rgb({round(rgb[0] * 255)}, {round(rgb[1] * 255)}, {round(rgb[2] * 255)})"
                )
            for which, position_index, symbol_marker in (
                ("start", 0, "circle"),
                ("end", -1, "diamond"),
            ):
                points = paths.display_positions[:, position_index, :]
                labels = (
                    [
                        f"{which}: {chemical_symbols[int(number)]} atom {atom}"
                        for atom, number in zip(paths.atom_indices, paths.atomic_numbers, strict=True)
                    ]
                    if trajectory_options.enable_hover
                    else None
                )
                endpoint_indices.append(len(figure.data))
                figure.add_trace(
                    go.Scatter3d(
                        x=points[:, 0], y=points[:, 1], z=points[:, 2],
                        mode="markers",
                        name=f"{paths.selection_label} {which}",
                        legendgroup=f"trajectory-endpoint:{which}",
                        showlegend=trajectory_options.show_legend,
                        marker={
                            "size": trajectory_options.endpoint_size,
                            "symbol": symbol_marker,
                            "color": endpoint_colors,
                        },
                        text=labels,
                        hovertemplate=("%{text}<extra></extra>" if labels is not None else None),
                        hoverinfo=(None if labels is not None else "skip"),
                    )
                )

    density_indices: dict[str, tuple[int, ...]] = {}
    framework_density_indices: dict[str, tuple[int, ...]] = {}
    density_trace_provenance: dict[int, DensityTraceProvenance] = {}
    density_cloud_metadata: dict[str, dict[str, Any]] = {}
    density_range_points: list[FloatArray] = []
    framework_fields = (
        ()
        if scene.framework_density_fields is None
        else scene.framework_density_fields.fields
    )
    field_specs: list[tuple[ScalarField3D, AtomicDensity3DRenderOptions, str]] = [
        *((field, density_options, "atomic") for field in scene.atomic_density_fields),
        *(
            (field, framework_density_options, "framework")
            for field in framework_fields
        ),
    ]
    prepared_clouds: dict[
        tuple[str, str],
        tuple[DensityNodeCloud3D, tuple[tuple[int, int, int], ...]],
    ] = {}
    prepared_meshes: dict[
        tuple[str, str, float],
        tuple[
            PreparedSparseDensitySurface | tuple[FloatArray, IntArray, float],
            tuple[tuple[int, int, int], ...],
        ],
    ] = {}
    density_mesh_metadata: dict[str, list[dict[str, Any]]] = {}
    density_scene_fit_report: DensitySceneFitReport | None = None

    def density_image_shifts(replication: str) -> tuple[tuple[int, int, int], ...]:
        if replication == "canonical":
            return ((0, 0, 0),)
        if base.periodic_view.mode is not PeriodicDisplayMode.EXPANDED:
            raise GraphUnsupportedFeatureError(
                "display_replication='match_graph' requires an expanded-cell "
                "periodic graph view."
            )
        shifts = tuple(
            tuple(int(value) for value in shift)
            for shift in base.periodic_view.primary_cell_image_shifts
        )
        if not shifts:
            raise GraphAdapterError(
                "Expanded periodic graph view contains no primary cell shifts."
            )
        return shifts

    scene_budget_plan: DensitySceneBudgetPlan | None = None
    density_usage_records: list[BrowserMeshTraceUsage] = []
    browser_usage_pre_html = BrowserMeshUsage(
        density_traces=(),
        non_density_trace_count=len(figure.data),
        metadata={"stage": "pre_plotly_serialization"},
    )
    browser_budget_report_pre_html = require_browser_mesh_budget(
        browser_usage_pre_html,
        budget=resolved_browser_budget,
        profile=browser_profile,
    )
    if field_specs and browser_profile == INTERACTIVE_BROWSER_PROFILE:
        shell_requests: list[DensitySceneShellRequest] = []
        for field, render_options, channel in field_specs:
            if render_options.render_mode != "mesh":
                continue
            image_shifts = density_image_shifts(
                render_options.render_options.display_replication
            )
            for shell_position, mass_fraction in enumerate(render_options.mass_fractions):
                importance_values = resolved_allocation_options.shell_importance
                importance = importance_values[min(shell_position, len(importance_values) - 1)]
                details = field.hdr_details(mass_fraction)
                shell_requests.append(
                    DensitySceneShellRequest(
                        shell_key=f"{channel}:{field.field_key}:{mass_fraction:.12g}",
                        field_key=field.field_key,
                        label=field.label,
                        mass_fraction=mass_fraction,
                        selected_node_count=details.selected_node_count,
                        display_replication=len(image_shifts),
                        visual_importance=importance,
                        max_canonical_faces=scene.resources.max_density_mesh_faces,
                        metadata={"channel": channel, "shell_position": shell_position},
                    )
                )
        scene_budget_plan = allocate_density_scene_budget(
            shell_requests,
            budget=resolved_browser_budget,
            options=resolved_allocation_options,
        )

    def density_shell_face_contract(
        *,
        channel: str,
        field_key: str,
        mass_fraction: float,
        render_options: AtomicDensity3DRenderOptions,
    ) -> DensityMeshFaceContract:
        shell_key = f"{channel}:{field_key}:{mass_fraction:.12g}"
        target_faces = (
            render_options.standalone_final_mesh_faces
            if scene_budget_plan is None
            else scene_budget_plan.allocation_for(shell_key).target_canonical_faces
        )
        if scene_budget_plan is None:
            return DensityMeshFaceContract.standalone(
                final_face_limit=render_options.standalone_final_mesh_faces,
                raw_extraction_face_limit=scene.resources.max_density_mesh_faces,
                visual_target_faces=target_faces,
                metadata={
                    "owner": "standalone_render",
                    "shell_key": shell_key,
                },
            )
        return DensityMeshFaceContract.scene_controller(
            raw_extraction_face_limit=scene.resources.max_density_mesh_faces,
            visual_target_faces=target_faces,
            metadata={
                "owner": "density_scene_fitting_controller",
                "shell_key": shell_key,
            },
        )

    density_mesh_execution_report: DensityMeshExecutionReport | None = None
    estimated_mesh_wall_seconds = 0.0
    estimated_render_peak_bytes = 0
    parent_scene_retained_bytes = 0
    final_output_reserve_bytes = 0
    resolved_mesh_execution_options = requested_mesh_execution_options.resolve(
        max_threads=int(scene.resources.max_threads),
        remaining_wall_time_seconds=remaining_scene_wall_seconds,
        max_memory_bytes=int(scene.resources.max_memory_bytes),
        parent_retained_bytes=0,
        final_output_reserve_bytes=0,
        largest_worker_peak_bytes=1,
        isolated_shell_count=0,
    )
    if field_specs:
        phase_b_by_key = (
            {}
            if scene.planning_record is None
            else {plan.field_key: plan for plan in scene.planning_record.phase_b_fields}
        )
        planning_retained_bytes = (
            0 if scene.planning_record is None else int(scene.planning_record.retained_bytes)
        )
        parent_scene_retained_bytes = planning_retained_bytes + _owned_numpy_bytes(
            scene.mean_framework,
            scene.trajectory_paths,
            scene.atomic_mean_graph,
            scene.frame_indices,
            scene.weights,
            scene.display_cell,
            scene.planning_record,
        )
        if scene_budget_plan is None:
            canonical_face_reserve = sum(
                len(render_options.mass_fractions)
                * render_options.standalone_final_mesh_faces
                for _field, render_options, _channel in field_specs
                if render_options.render_mode == "mesh"
            )
        else:
            canonical_face_reserve = sum(
                item.target_canonical_faces for item in scene_budget_plan.allocations
            )
        cloud_point_reserve = sum(
            render_options.cloud_max_points
            for _field, render_options, _channel in field_specs
            if render_options.render_mode != "mesh"
        )
        # Prepared mesh arrays are float64 vertices plus int64 triangles before
        # compact Plotly serialization.  Three vertices per face is a strict
        # topology upper bound; 25% covers object/allocator overhead.
        final_output_reserve_bytes = int(
            np.ceil(1.25 * (96 * canonical_face_reserve + 32 * cloud_point_reserve))
        )

        serial_shell_count = 0
        serial_mesh_cell_work = 0
        serial_mesh_face_work = 0
        isolated_shell_count = 0
        isolated_mesh_cell_work = 0
        isolated_mesh_face_work = 0
        largest_worker_peak_bytes = 1
        largest_serial_transient_bytes = 0
        for field, render_options, _channel in field_specs:
            if render_options.render_mode != "mesh":
                continue
            field_shells = len(render_options.mass_fractions)
            plan = phase_b_by_key.get(field.field_key)
            if plan is None:
                summary = field.storage_summary()
                cells = int(summary.nonzero_node_count)
                faces = 5 * cells
                retained = max(1, 32 * int(summary.stored_value_count))
                transient = max(64 * 1024**2, 128 * max(1, cells))
            else:
                cells = int(plan.mesh_cell_count)
                faces = int(plan.mesh_face_count_upper)
                retained = int(plan.retained_bytes)
                transient = int(plan.transient_bytes_upper)
            use_isolated = (
                field.storage_backend == LOCAL_SPARSE_BACKEND
                and isolate_large_sparse_meshes
                and browser_profile == INTERACTIVE_BROWSER_PROFILE
                and field.storage_summary().nonzero_node_count
                >= resolved_isolation_node_threshold
            )
            if use_isolated:
                isolated_shell_count += field_shells
                isolated_mesh_cell_work += field_shells * cells
                isolated_mesh_face_work += field_shells * faces
                largest_worker_peak_bytes = max(
                    largest_worker_peak_bytes,
                    int(np.ceil(1.20 * (retained + transient))),
                )
            else:
                serial_shell_count += field_shells
                serial_mesh_cell_work += field_shells * cells
                serial_mesh_face_work += field_shells * faces
                largest_serial_transient_bytes = max(
                    largest_serial_transient_bytes, transient
                )

        serial_render_peak = (
            parent_scene_retained_bytes
            + final_output_reserve_bytes
            + largest_serial_transient_bytes
        )
        if serial_render_peak > int(scene.resources.max_memory_bytes):
            raise GraphComplexityError(
                "Density rendering is estimated to exceed max_memory_bytes in the "
                "parent process: "
                f"parent_retained_bytes={parent_scene_retained_bytes}, "
                f"final_output_reserve_bytes={final_output_reserve_bytes}, "
                f"largest_serial_transient_bytes={largest_serial_transient_bytes}, "
                f"max_memory_bytes={int(scene.resources.max_memory_bytes)}."
            )
        resolved_mesh_execution_options = requested_mesh_execution_options.resolve(
            max_threads=int(scene.resources.max_threads),
            remaining_wall_time_seconds=remaining_scene_wall_seconds,
            max_memory_bytes=int(scene.resources.max_memory_bytes),
            parent_retained_bytes=parent_scene_retained_bytes,
            final_output_reserve_bytes=final_output_reserve_bytes,
            largest_worker_peak_bytes=largest_worker_peak_bytes,
            isolated_shell_count=isolated_shell_count,
        )
        isolated_worker_count = resolved_mesh_execution_options.resolved_worker_count(
            isolated_shell_count
        )
        estimated_serial_mesh_seconds = scene.resources.time_model.estimate_mesh_seconds(
            shell_count=serial_shell_count,
            mesh_cell_count=serial_mesh_cell_work,
            mesh_face_count=serial_mesh_face_work,
            max_workers=1,
            isolated_workers=False,
        )
        estimated_isolated_mesh_seconds = scene.resources.time_model.estimate_mesh_seconds(
            shell_count=isolated_shell_count,
            mesh_cell_count=isolated_mesh_cell_work,
            mesh_face_count=isolated_mesh_face_work,
            max_workers=isolated_worker_count,
            isolated_workers=True,
        )
        estimated_mesh_wall_seconds = (
            estimated_serial_mesh_seconds + estimated_isolated_mesh_seconds
        )
        estimated_worker_pool_bytes = (
            0
            if isolated_shell_count == 0
            else isolated_worker_count * largest_worker_peak_bytes
        )
        estimated_render_peak_bytes = max(
            serial_render_peak,
            parent_scene_retained_bytes
            + final_output_reserve_bytes
            + estimated_worker_pool_bytes,
        )
        if estimated_render_peak_bytes > int(scene.resources.max_memory_bytes):
            raise GraphComplexityError(
                "Resolved density-shell worker pool exceeds max_memory_bytes: "
                f"estimated_render_peak_bytes={estimated_render_peak_bytes}, "
                f"max_memory_bytes={int(scene.resources.max_memory_bytes)}."
            )
        projected_points = 0
        projected_traces = 0
        projected_mesh_faces = 0
        projected_mesh_bytes = 0
        isolated_pending: list[
            tuple[
                tuple[str, str, float],
                tuple[tuple[int, int, int], ...],
                Future[tuple[PreparedSparseDensitySurface, float]],
            ]
        ] = []
        isolated_requests: list[
            tuple[
                tuple[str, str, float],
                tuple[tuple[int, int, int], ...],
                ScalarField3D,
                float,
                dict[str, Any],
            ]
        ] = []
        isolated_wall_started = 0.0
        mesh_shell_total = sum(
            len(render_options.mass_fractions)
            for _field, render_options, _channel in field_specs
            if render_options.render_mode == "mesh"
        )
        mesh_shell_started = 0
        mesh_shell_completed = 0
        for field, render_options, channel in field_specs:
            replication = render_options.render_options.display_replication
            image_shifts = density_image_shifts(replication)
            if render_options.render_mode == "mesh":
                for mass_fraction in render_options.mass_fractions:
                    mesh_shell_started += 1
                    shell_ordinal = mesh_shell_started
                    reporter.started(
                        "density_mesh",
                        f"preparing {field.label!r} HDR={mass_fraction:.2f}",
                        current=shell_ordinal,
                        total=mesh_shell_total,
                        unit="shells",
                        metadata={
                            "field_key": field.field_key,
                            "label": field.label,
                            "mass_fraction": float(mass_fraction),
                        },
                    )
                    shell_key = f"{channel}:{field.field_key}:{mass_fraction:.12g}"
                    face_contract = density_shell_face_contract(
                        channel=channel,
                        field_key=field.field_key,
                        mass_fraction=float(mass_fraction),
                        render_options=render_options,
                    )
                    assert face_contract.visual_target_faces is not None
                    target_faces = int(face_contract.visual_target_faces)
                    shell_position = render_options.mass_fractions.index(mass_fraction)
                    shell_fidelity = (
                        {
                            "max_surface_error_p99": 0.11,
                            "max_surface_error_max": 1.20,
                            "max_implicit_displacement_p99": 0.23,
                            "max_normal_degradation_degrees": 66.0,
                            "max_relative_scalar_residual_p99": 3.20,
                        },
                        {
                            "max_surface_error_p99": 0.10,
                            "max_surface_error_max": 0.50,
                            "max_implicit_displacement_p99": 0.10,
                            "max_normal_degradation_degrees": 50.0,
                            "max_relative_scalar_residual_p99": 2.0,
                        },
                        {
                            "max_surface_error_p99": 0.35,
                            "max_surface_error_max": 2.5,
                            "max_implicit_displacement_p99": 0.40,
                            "max_normal_degradation_degrees": 85.0,
                            "max_relative_scalar_residual_p99": 40.0,
                        },
                    )[min(shell_position, 2)]
                    simplification_policy = (
                        None
                        if scene_budget_plan is None and mesh_simplification_options is None
                        else replace(
                            resolved_simplification_options,
                            target_faces=target_faces,
                            hard_target=False,
                            **(
                                shell_fidelity
                                if mesh_simplification_options is None
                                else {}
                            ),
                        )
                    )
                    if field.storage_backend == LOCAL_SPARSE_BACKEND:
                        sparse_keyword_arguments = {
                            "face_contract": face_contract,
                            "max_candidate_cells": scene.resources.max_density_mesh_cells,
                            "max_raw_vertices": 3 * scene.resources.max_density_mesh_faces,
                            "max_workspace_bytes": max(
                                1,
                                int(scene.resources.max_memory_bytes)
                                - parent_scene_retained_bytes
                                - final_output_reserve_bytes,
                            ),
                            "max_dense_fallback_nodes": scene.resources.max_density_voxels,
                            "allow_cloud_fallback": (
                                browser_profile != INTERACTIVE_BROWSER_PROFILE
                            ),
                            "cloud_max_points": render_options.cloud_max_points,
                            "simplification_options": simplification_policy,
                        }
                        field_nonzero_nodes = field.storage_summary().nonzero_node_count
                        use_isolated_worker = (
                            isolate_large_sparse_meshes
                            and browser_profile == INTERACTIVE_BROWSER_PROFILE
                            and field_nonzero_nodes >= resolved_isolation_node_threshold
                        )
                        reporter.update(
                            "density_mesh",
                            f"backend=local_sparse, target_faces={target_faces}, "
                            f"isolated={use_isolated_worker}",
                            current=shell_ordinal,
                            total=mesh_shell_total,
                            unit="shells",
                            metadata={
                                "field_key": field.field_key,
                                "mass_fraction": float(mass_fraction),
                                "target_faces": int(target_faces),
                                "raw_extraction_face_limit": int(
                                    face_contract.raw_extraction_face_limit or 0
                                ),
                                "standalone_final_face_limit": (
                                    face_contract.standalone_final_face_limit
                                ),
                                "mesh_face_contract_mode": face_contract.mode,
                                "isolated_worker": bool(use_isolated_worker),
                            },
                        )
                        if use_isolated_worker:
                            sparse_keyword_arguments["max_workspace_bytes"] = int(
                                resolved_mesh_execution_options.worker_memory_bytes
                            )
                            isolated_requests.append(
                                (
                                    (channel, field.field_key, float(mass_fraction)),
                                    image_shifts,
                                    field,
                                    float(mass_fraction),
                                    sparse_keyword_arguments,
                                )
                            )
                            projected_traces += len(image_shifts)
                            continue
                        surface = prepare_sparse_density_mesh(
                            field,
                            mass_fraction,
                            **sparse_keyword_arguments,
                        )
                        mesh_shell_completed += 1
                        mesh_summary, mesh_metadata = _sparse_mesh_progress_summary(
                            surface
                        )
                        reporter.completed(
                            "density_mesh",
                            f"completed {field.label!r} HDR={mass_fraction:.2f}, "
                            f"kind={surface.render_kind}, {mesh_summary}",
                            current=mesh_shell_completed,
                            total=mesh_shell_total,
                            unit="shells",
                            metadata={
                                "field_key": field.field_key,
                                "mass_fraction": float(mass_fraction),
                                "render_kind": surface.render_kind,
                                **mesh_metadata,
                            },
                        )
                        prepared_meshes[
                            (channel, field.field_key, float(mass_fraction))
                        ] = (
                            surface,
                            image_shifts,
                        )
                        if surface.render_kind == "mesh":
                            assert surface.mesh is not None
                            projected_points += surface.mesh.vertices_cartesian.shape[
                                0
                            ] * len(image_shifts)
                            projected_mesh_faces += surface.mesh.faces.shape[0] * len(
                                image_shifts
                            )
                            projected_mesh_bytes = max(
                                projected_mesh_bytes,
                                surface.mesh.resources.estimated_peak_bytes,
                            )
                        else:
                            assert surface.cloud is not None
                            projected_points += (
                                surface.cloud.resources.selected_point_count
                                * len(image_shifts)
                            )
                    else:
                        vertices, faces, threshold = density_mesh_arrays(
                            field,
                            mass_fraction,
                            face_contract=face_contract,
                        )
                        mesh_shell_completed += 1
                        reporter.completed(
                            "density_mesh",
                            f"completed {field.label!r} HDR={mass_fraction:.2f}, "
                            f"backend=dense, faces={faces.shape[0]}",
                            current=mesh_shell_completed,
                            total=mesh_shell_total,
                            unit="shells",
                            metadata={
                                "field_key": field.field_key,
                                "mass_fraction": float(mass_fraction),
                                "backend": "dense",
                                "face_count": int(faces.shape[0]),
                            },
                        )
                        prepared_meshes[
                            (channel, field.field_key, float(mass_fraction))
                        ] = (
                            (vertices, faces, threshold),
                            image_shifts,
                        )
                        projected_points += vertices.shape[0] * len(image_shifts)
                        projected_mesh_faces += faces.shape[0] * len(image_shifts)
                        projected_mesh_bytes = max(
                            projected_mesh_bytes, int(vertices.nbytes + faces.nbytes)
                        )
                    projected_traces += len(image_shifts)
            else:
                cloud = prepare_density_node_cloud(
                    field,
                    max(render_options.mass_fractions),
                    max_points=render_options.cloud_max_points,
                    display_replication=replication,
                )
                prepared_clouds[(channel, field.field_key)] = (cloud, image_shifts)
                projected_points += cloud.resources.selected_point_count * len(
                    image_shifts
                )
                projected_traces += len(image_shifts)
            if render_options.show_samples and field.sample_positions is not None:
                projected_traces += 1
        isolated_executor: ThreadPoolExecutor | None = None
        if isolated_requests:
            isolated_wall_started = time.perf_counter()
            isolated_executor = ThreadPoolExecutor(
                max_workers=int(
                    resolved_mesh_execution_options.max_parallel_shell_workers
                ),
                thread_name_prefix="mdstats-density-shell",
            )
            for key, image_shifts, field, mass_fraction, keyword_arguments in isolated_requests:
                future = isolated_executor.submit(
                    _prepare_sparse_density_mesh_isolated_timed,
                    field,
                    mass_fraction,
                    execution_options=resolved_mesh_execution_options,
                    **keyword_arguments,
                )
                isolated_pending.append((key, image_shifts, future))
        isolated_shell_seconds: list[float] = []
        try:
            for key, image_shifts, future in isolated_pending:
                surface, shell_seconds = future.result()
                isolated_shell_seconds.append(float(shell_seconds))
                channel_key, field_key, mass_fraction = key
                mesh_shell_completed += 1
                mesh_summary, mesh_metadata = _sparse_mesh_progress_summary(surface)
                reporter.completed(
                    "density_mesh",
                    f"completed {channel_key}:{field_key} HDR={mass_fraction:.2f}, "
                    f"kind={surface.render_kind}, {mesh_summary}, "
                    f"seconds={shell_seconds:.3f}",
                    current=mesh_shell_completed,
                    total=mesh_shell_total,
                    unit="shells",
                    metadata={
                        "field_key": field_key,
                        "channel": channel_key,
                        "mass_fraction": float(mass_fraction),
                        "render_kind": surface.render_kind,
                        **mesh_metadata,
                        "wall_seconds": float(shell_seconds),
                    },
                )
                prepared_meshes[key] = (surface, image_shifts)
                if surface.render_kind == "mesh":
                    assert surface.mesh is not None
                    projected_points += (
                        surface.mesh.vertices_cartesian.shape[0] * len(image_shifts)
                    )
                    projected_mesh_faces += (
                        surface.mesh.faces.shape[0] * len(image_shifts)
                    )
                    projected_mesh_bytes = max(
                        projected_mesh_bytes,
                        surface.mesh.resources.estimated_peak_bytes,
                    )
                else:
                    assert surface.cloud is not None
                    projected_points += (
                        surface.cloud.resources.selected_point_count
                        * len(image_shifts)
                    )
        finally:
            if isolated_executor is not None:
                isolated_executor.shutdown(wait=True, cancel_futures=True)
        isolated_wall_seconds = (
            0.0
            if not isolated_pending
            else time.perf_counter() - isolated_wall_started
        )
        worker_count = resolved_mesh_execution_options.resolved_worker_count(
            len(isolated_pending)
        )
        density_mesh_execution_report = DensityMeshExecutionReport(
            isolated_shell_count=len(isolated_pending),
            parallel_worker_count=worker_count,
            wall_seconds=isolated_wall_seconds,
            sum_shell_seconds=float(sum(isolated_shell_seconds)),
            maximum_shell_seconds=(
                0.0 if not isolated_shell_seconds else max(isolated_shell_seconds)
            ),
            metadata={
                "scheduler": "bounded_fresh_process_shell_pool_v1",
                "native_threads_per_worker": (
                    resolved_mesh_execution_options.worker_native_threads
                ),
            },
        )
        if browser_profile == INTERACTIVE_BROWSER_PROFILE and prepared_meshes:
            field_lookup = {
                (channel_name, field.field_key): field
                for field, _render_options, channel_name in field_specs
            }
            shell_geometries: list[DensityShellGeometry] = []
            for (channel_key, field_key, mass_fraction), (prepared, image_shifts) in sorted(
                prepared_meshes.items(), key=lambda item: item[0]
            ):
                field = field_lookup[(channel_key, field_key)]
                if isinstance(prepared, PreparedSparseDensitySurface):
                    if prepared.render_kind != "mesh":
                        continue
                    assert prepared.mesh is not None
                    vertices_fractional = prepared.mesh.vertices_fractional
                    vertices_cartesian = prepared.mesh.vertices_cartesian
                    faces = prepared.mesh.faces
                    contour_level = prepared.mesh.render_level
                    source_kind = "local_sparse"
                else:
                    vertices_cartesian, faces, contour_level = prepared
                    vertices_fractional = (
                        np.asarray(vertices_cartesian, dtype=np.float64)
                        @ np.linalg.inv(np.asarray(field.display_cell, dtype=np.float64))
                    )
                    source_kind = "dense"
                shell_key = f"{channel_key}:{field_key}:{mass_fraction:.12g}"
                allocation_weight = 1.0
                minimum_faces = 4
                if scene_budget_plan is not None:
                    allocation = scene_budget_plan.allocation_for(shell_key)
                    allocation_weight = allocation.allocation_weight
                    minimum_faces = min(
                        int(faces.shape[0]),
                        max(4, resolved_mesh_profile.minimum_canonical_faces_per_shell),
                    )
                shell_geometries.append(
                    DensityShellGeometry(
                        shell_key=shell_key,
                        field=field,
                        mass_fraction=float(mass_fraction),
                        contour_level=float(contour_level),
                        vertices_fractional=vertices_fractional,
                        vertices_cartesian=vertices_cartesian,
                        faces=faces,
                        display_replication=len(image_shifts),
                        visual_importance=float(allocation_weight),
                        minimum_faces=minimum_faces,
                        source_kind=source_kind,
                        metadata={"channel": channel_key, "field_key": field_key},
                    )
                )
            if shell_geometries:
                future_sample_trace_count = sum(
                    1
                    for field, render_options, _channel in field_specs
                    if render_options.show_samples and field.sample_positions is not None
                )
                future_cloud_trace_count = sum(
                    len(image_shifts)
                    for _key, (_cloud, image_shifts) in prepared_clouds.items()
                )
                fitted_geometries, density_scene_fit_report = fit_density_scene_to_browser_budget(
                    shell_geometries,
                    profile=resolved_mesh_profile,
                    non_density_trace_count=(
                        len(figure.data)
                        + future_sample_trace_count
                        + future_cloud_trace_count
                    ),
                    simplification_options=resolved_simplification_options,
                    progress=progress_port,
                )
                fitted_by_key = {item.shell_key: item for item in fitted_geometries}
                for key, (prepared, image_shifts) in tuple(prepared_meshes.items()):
                    channel_key, field_key, mass_fraction = key
                    shell_key = f"{channel_key}:{field_key}:{mass_fraction:.12g}"
                    fitted = fitted_by_key.get(shell_key)
                    if fitted is None:
                        continue
                    if isinstance(prepared, PreparedSparseDensitySurface):
                        assert prepared.mesh is not None
                        fitted_resources = replace(
                            prepared.mesh.resources,
                            canonical_vertex_count=fitted.vertex_count,
                            canonical_face_count=fitted.face_count,
                        )
                        fitted_mesh = replace(
                            prepared.mesh,
                            vertices_fractional=fitted.vertices_fractional,
                            vertices_cartesian=fitted.vertices_cartesian,
                            faces=fitted.faces,
                            resources=fitted_resources,
                            metadata={
                                **prepared.mesh.metadata.to_json_dict(),
                                "scene_fit_source_kind": fitted.source_kind,
                                "scene_fit_applied": True,
                            },
                        )
                        prepared_meshes[key] = (
                            replace(prepared, mesh=fitted_mesh),
                            image_shifts,
                        )
                    else:
                        prepared_meshes[key] = (
                            (
                                fitted.vertices_cartesian,
                                fitted.faces,
                                fitted.contour_level,
                            ),
                            image_shifts,
                        )

        density_usage_records = []
        for (channel_key, field_key, mass_fraction), (prepared, image_shifts) in sorted(
            prepared_meshes.items(), key=lambda item: item[0]
        ):
            if isinstance(prepared, PreparedSparseDensitySurface):
                if prepared.render_kind == "mesh":
                    assert prepared.mesh is not None
                    face_count = int(prepared.mesh.faces.shape[0])
                    vertex_count = int(prepared.mesh.vertices_cartesian.shape[0])
                    retained_bytes = int(
                        vertex_count * 3 * np.dtype(np.float32).itemsize
                        + face_count * 3 * np.dtype(np.int32).itemsize
                    )
                else:
                    assert prepared.cloud is not None
                    face_count = 0
                    vertex_count = int(prepared.cloud.resources.selected_point_count)
                    retained_bytes = int(vertex_count * 4 * np.dtype(np.float32).itemsize)
            else:
                vertices, faces, _threshold = prepared
                face_count = int(faces.shape[0])
                vertex_count = int(vertices.shape[0])
                retained_bytes = int(
                    vertex_count * 3 * np.dtype(np.float32).itemsize
                    + face_count * 3 * np.dtype(np.int32).itemsize
                )
            density_usage_records.append(
                BrowserMeshTraceUsage(
                    trace_key=f"{channel_key}:{field_key}:{mass_fraction:.12g}",
                    face_count=face_count,
                    vertex_count=vertex_count,
                    display_replication=len(image_shifts),
                    retained_array_bytes=retained_bytes,
                )
            )
        for (channel_key, field_key), (cloud, image_shifts) in sorted(
            prepared_clouds.items(), key=lambda item: item[0]
        ):
            count = int(cloud.resources.selected_point_count)
            density_usage_records.append(
                BrowserMeshTraceUsage(
                    trace_key=f"{channel_key}:{field_key}:cloud",
                    face_count=0,
                    vertex_count=count,
                    display_replication=len(image_shifts),
                    retained_array_bytes=count * 4 * np.dtype(np.float32).itemsize,
                )
            )
        projected_mesh_faces = sum(
            item.face_count * item.display_replication for item in density_usage_records
        )
        projected_points = sum(
            item.vertex_count * item.display_replication for item in density_usage_records
        )
        density_trace_count_for_budget = sum(
            item.display_replication for item in density_usage_records
        )
        sample_trace_count = max(0, projected_traces - density_trace_count_for_budget)
        browser_usage_pre_html = BrowserMeshUsage(
            density_traces=tuple(density_usage_records),
            non_density_trace_count=len(figure.data) + sample_trace_count,
            metadata={
                "stage": "pre_plotly_serialization",
                "scene_budget_plan": (
                    None if scene_budget_plan is None else scene_budget_plan.to_json_dict()
                ),
            },
        )
        browser_budget_report_pre_html = require_browser_mesh_budget(
            browser_usage_pre_html,
            budget=resolved_browser_budget,
            profile=browser_profile,
        )

        if projected_mesh_bytes > scene.resources.max_density_total_peak_bytes:
            raise GraphComplexityError(
                f"Prepared density meshes require approximately {projected_mesh_bytes} bytes, "
                "exceeding max_density_total_peak_bytes."
            )
        if projected_points > scene.resources.max_density_render_points:
            raise GraphComplexityError(
                f"Density rendering requires {projected_points} points, exceeding "
                f"max_density_render_points={scene.resources.max_density_render_points}."
            )
        if projected_traces > scene.resources.max_density_traces:
            raise GraphComplexityError(
                f"Density rendering requires {projected_traces} traces, exceeding "
                f"max_density_traces={scene.resources.max_density_traces}."
            )
        if (
            len(figure.data) + projected_traces
            > resolved_graph_options.max_plotly_traces
        ):
            raise GraphComplexityError(
                "Composite density rendering exceeds max_plotly_traces."
            )
        try:
            import plotly.graph_objects as go
            from plotly.colors import qualitative
            from matplotlib.colors import to_rgba
        except ImportError as exc:  # pragma: no cover
            raise GraphVisualizationError(
                "Plotly is required for density rendering."
            ) from exc
        palette = tuple(qualitative.Plotly)
        for local, (field, render_options, channel) in enumerate(field_specs):
            color = palette[local % len(palette)]
            red, green, blue, _ = to_rgba(color)
            solid_color = (
                f"rgb({round(red * 255)}, {round(green * 255)}, {round(blue * 255)})"
            )
            trace_ids: list[int] = []
            if render_options.render_mode == "mesh":
                n_shells = len(render_options.mass_fractions)
                mesh_records: list[dict[str, Any]] = []
                for shell_position in reversed(range(n_shells)):
                    fraction = shell_position / max(1, n_shells - 1)
                    alpha = (
                        (1.0 - fraction) * render_options.inner_opacity
                        + fraction * render_options.outer_opacity
                    )
                    mass_fraction = render_options.mass_fractions[shell_position]
                    prepared, image_shifts = prepared_meshes[
                        (channel, field.field_key, float(mass_fraction))
                    ]
                    face_contract = density_shell_face_contract(
                        channel=channel,
                        field_key=field.field_key,
                        mass_fraction=float(mass_fraction),
                        render_options=render_options,
                    )
                    if isinstance(prepared, PreparedSparseDensitySurface):
                        if prepared.render_kind == "node_cloud":
                            assert prepared.cloud is not None
                            cloud = prepared.cloud
                            marker_sizes = render_options.cloud_point_size * (
                                0.55
                                + 0.85
                                * np.sqrt(np.clip(cloud.relative_intensities, 0.0, 1.0))
                            )
                            for shift_position, image_shift in enumerate(image_shifts):
                                points = cloud.translated_positions(
                                    image_shift, field.display_cell
                                )
                                density_range_points.append(points)
                                trace_index = len(figure.data)
                                trace_ids.append(trace_index)
                                provenance = cloud.provenance.with_image_shift(
                                    image_shift
                                )
                                density_trace_provenance[trace_index] = provenance
                                figure.add_trace(
                                    go.Scatter3d(
                                        x=points[:, 0],
                                        y=points[:, 1],
                                        z=points[:, 2],
                                        mode="markers",
                                        name=field.label,
                                        legendgroup=field.field_key,
                                        showlegend=(
                                            render_options.show_legend
                                            and shell_position == n_shells - 1
                                            and shift_position == 0
                                        ),
                                        marker={
                                            "size": marker_sizes,
                                            "color": cloud.relative_intensities,
                                            "cmin": 0.0,
                                            "cmax": 1.0,
                                            "colorscale": [
                                                [0.0, solid_color],
                                                [1.0, solid_color],
                                            ],
                                            "opacity": render_options.cloud_opacity,
                                            "showscale": False,
                                        },
                                        hoverinfo="skip",
                                    )
                                )
                            mesh_records.append(
                                {
                                    "requested_mass_fraction": mass_fraction,
                                    "render_kind": "node_cloud",
                                    "fallback_mode": prepared.fallback_mode,
                                    "hdr_details": cloud.hdr_details.to_json_dict(),
                                    "resources": cloud.resources.to_json_dict(),
                                }
                            )
                            continue
                        assert prepared.mesh is not None
                        mesh = prepared.mesh
                        base_vertices = mesh.vertices_cartesian
                        faces = mesh.faces
                        threshold = mesh.scientific_hdr_threshold
                        render_level = mesh.render_level
                        achieved_mass_fraction = mesh.achieved_mass_fraction
                        face_report = evaluate_density_mesh_face_contract(
                            int(faces.shape[0]),
                            face_contract,
                        )
                        mesh_records.append(
                            {
                                "requested_mass_fraction": mass_fraction,
                                "render_kind": "mesh",
                                "fallback_mode": prepared.fallback_mode,
                                "scientific_hdr_threshold": threshold,
                                "render_level": render_level,
                                "achieved_mass_fraction": achieved_mass_fraction,
                                "resources": mesh.resources.to_json_dict(),
                                "topology": mesh.topology.to_json_dict(),
                                "mesh_face_contract": face_contract.to_json_dict(),
                                "mesh_face_report": face_report.to_json_dict(),
                            }
                        )
                    else:
                        base_vertices, faces, render_level = prepared
                        details = field.hdr_details(mass_fraction)
                        threshold = details.threshold
                        achieved_mass_fraction = details.achieved_mass_fraction
                        face_report = evaluate_density_mesh_face_contract(
                            int(faces.shape[0]),
                            face_contract,
                        )
                        mesh_records.append(
                            {
                                "requested_mass_fraction": mass_fraction,
                                "render_kind": "mesh",
                                "fallback_mode": "none",
                                "scientific_hdr_threshold": threshold,
                                "render_level": render_level,
                                "achieved_mass_fraction": achieved_mass_fraction,
                                "resources": {
                                    "canonical_vertex_count": int(
                                        base_vertices.shape[0]
                                    ),
                                    "canonical_face_count": int(faces.shape[0]),
                                },
                                "mesh_face_contract": face_contract.to_json_dict(),
                                "mesh_face_report": face_report.to_json_dict(),
                            }
                        )
                    for shift_position, image_shift in enumerate(image_shifts):
                        vertices = np.ascontiguousarray(
                            np.asarray(base_vertices, dtype=np.float64)
                            + np.asarray(image_shift, dtype=np.float64)
                            @ field.display_cell,
                            dtype=np.float32,
                        )
                        faces_plotly = np.ascontiguousarray(faces, dtype=np.int32)
                        density_range_points.append(np.asarray(vertices, dtype=np.float64))
                        trace_index = len(figure.data)
                        trace_ids.append(trace_index)
                        density_trace_provenance[trace_index] = DensityTraceProvenance(
                            field_key=field.field_key,
                            label=field.label,
                            storage_backend=field.storage_backend,
                            source_provenance=field.source_provenance,
                            requested_mass_fraction=mass_fraction,
                            scientific_hdr_threshold=threshold,
                            achieved_mass_fraction=achieved_mass_fraction,
                            eligible_node_count=max(1, int(base_vertices.shape[0])),
                            selected_point_count=max(1, int(base_vertices.shape[0])),
                            selection_policy="periodic_density_mesh_v1",
                            display_replication=render_options.render_options.display_replication,
                            image_shift=image_shift,
                            metadata={
                                "render_kind": "mesh",
                                "render_level": render_level,
                                "face_count": int(faces.shape[0]),
                            },
                        )
                        figure.add_trace(
                            go.Mesh3d(
                                x=vertices[:, 0],
                                y=vertices[:, 1],
                                z=vertices[:, 2],
                                i=faces_plotly[:, 0],
                                j=faces_plotly[:, 1],
                                k=faces_plotly[:, 2],
                                color=solid_color,
                                opacity=alpha,
                                flatshading=False,
                                lighting={
                                    "ambient": 0.72,
                                    "diffuse": 0.58,
                                    "specular": 0.12,
                                    "roughness": 0.88,
                                    "fresnel": 0.04,
                                },
                                lightposition={"x": 100.0, "y": 200.0, "z": 300.0},
                                name=field.label,
                                legendgroup=field.field_key,
                                showlegend=(
                                    render_options.show_legend
                                    and shell_position == n_shells - 1
                                    and shift_position == 0
                                ),
                                hoverinfo="skip",
                            )
                        )
                density_mesh_metadata[field.field_key] = mesh_records
            else:
                cloud, image_shifts = prepared_clouds[(channel, field.field_key)]
                low_red = round(0.72 * 255 + 0.28 * red * 255)
                low_green = round(0.72 * 255 + 0.28 * green * 255)
                low_blue = round(0.72 * 255 + 0.28 * blue * 255)
                light_color = f"rgb({low_red}, {low_green}, {low_blue})"
                marker_sizes = render_options.cloud_point_size * (
                    0.55 + 0.85 * np.sqrt(np.clip(cloud.relative_intensities, 0.0, 1.0))
                )
                for shift_position, image_shift in enumerate(image_shifts):
                    points = cloud.translated_positions(image_shift, field.display_cell)
                    density_range_points.append(points)
                    trace_index = len(figure.data)
                    trace_ids.append(trace_index)
                    provenance = cloud.provenance.with_image_shift(image_shift)
                    density_trace_provenance[trace_index] = provenance
                    figure.add_trace(
                        go.Scatter3d(
                            x=points[:, 0],
                            y=points[:, 1],
                            z=points[:, 2],
                            mode="markers",
                            name=field.label,
                            legendgroup=field.field_key,
                            showlegend=(
                                render_options.show_legend and shift_position == 0
                            ),
                            marker={
                                "size": marker_sizes,
                                "color": cloud.relative_intensities,
                                "cmin": 0.0,
                                "cmax": 1.0,
                                "colorscale": [
                                    [0.0, light_color],
                                    [1.0, solid_color],
                                ],
                                "opacity": render_options.cloud_opacity,
                                "showscale": False,
                            },
                            hoverinfo="skip",
                        )
                    )
                density_cloud_metadata[field.field_key] = {
                    "bounds": cloud.bounds.to_json_dict(),
                    "resources": cloud.resources.to_json_dict(),
                    "hdr_details": cloud.hdr_details.to_json_dict(),
                    "display_replication": cloud.provenance.display_replication,
                    "image_shifts": [list(value) for value in image_shifts],
                }
            if render_options.show_samples and field.sample_positions is not None:
                trace_ids.append(len(figure.data))
                samples = field.sample_positions
                figure.add_trace(
                    go.Scatter3d(
                        x=samples[:, 0],
                        y=samples[:, 1],
                        z=samples[:, 2],
                        mode="markers",
                        name=f"{field.label} samples",
                        legendgroup=field.field_key,
                        showlegend=False,
                        marker={"size": render_options.sample_size, "color": color},
                        opacity=render_options.sample_opacity,
                        hoverinfo="skip",
                    )
                )
            target = (
                density_indices if channel == "atomic" else framework_density_indices
            )
            target[field.field_key] = tuple(trace_ids)

    range_points: list[FloatArray] = [
        np.asarray(base.periodic_view.graph.node_positions_3d, dtype=np.float64)
    ]
    range_points.extend(density_range_points)
    if atomic_mean_graph is not None:
        range_points.append(
            np.asarray(atomic_mean_graph.display_positions, dtype=np.float64)
        )
        if atomic_mean_graph.edge_endpoints.shape[0] > 0:
            edge_points = []
            cell = np.asarray(atomic_mean_graph.display_cell, dtype=np.float64)
            for (source, target), shift in zip(
                atomic_mean_graph.edge_endpoints,
                atomic_mean_graph.edge_image_shifts,
                strict=True,
            ):
                edge_points.append(atomic_mean_graph.display_positions[int(source)])
                edge_points.append(
                    atomic_mean_graph.display_positions[int(target)]
                    + np.asarray(shift, dtype=np.float64) @ cell
                )
            if edge_points:
                range_points.append(np.asarray(edge_points, dtype=np.float64))
    if paths is not None:
        range_points.append(paths.display_positions.reshape((-1, 3)))
    # Include cell-wireframe coordinates because canonical ghost stubs and the
    # oblique cell can extend beyond the source-node bounding box.
    for trace_index in base.cell_trace_indices:
        trace = figure.data[trace_index]
        coordinates = np.column_stack(
            [
                np.asarray(
                    [np.nan if value is None else value for value in trace.x],
                    dtype=np.float64,
                ),
                np.asarray(
                    [np.nan if value is None else value for value in trace.y],
                    dtype=np.float64,
                ),
                np.asarray(
                    [np.nan if value is None else value for value in trace.z],
                    dtype=np.float64,
                ),
            ]
        )
        coordinates = coordinates[np.all(np.isfinite(coordinates), axis=1)]
        if coordinates.size:
            range_points.append(coordinates)
    _apply_equal_aspect_ranges(figure, np.concatenate(range_points, axis=0))
    figure.update_layout(legend={"groupclick": "togglegroup"})

    final_density_plotly_traces = sum(
        item.display_replication for item in density_usage_records
    )
    final_non_density_traces = len(figure.data) - final_density_plotly_traces
    if final_non_density_traces < 0:
        raise GraphAdapterError("Density trace accounting exceeds Plotly trace count.")
    browser_usage_pre_html = BrowserMeshUsage(
        density_traces=tuple(density_usage_records),
        non_density_trace_count=final_non_density_traces,
        metadata={
            "stage": "post_plotly_pre_html",
            "scene_budget_plan": (
                None if scene_budget_plan is None else scene_budget_plan.to_json_dict()
            ),
        },
    )
    browser_budget_report_pre_html = require_browser_mesh_budget(
        browser_usage_pre_html,
        budget=resolved_browser_budget,
        profile=browser_profile,
    )

    reporter.completed("scene_assembly", "completed Plotly scene assembly")
    render_wall_seconds = time.perf_counter() - render_started
    complete_scene_wall_seconds = preparation_wall_seconds + render_wall_seconds
    return FrameworkDynamicsRenderResult(
        figure=figure,
        scene=scene,
        base_result=base,
        trajectory_trace_indices=traces,
        atomic_mean_graph_trace_indices=atomic_mean_graph_trace_indices,
        endpoint_trace_indices=tuple(endpoint_indices),
        density_trace_indices=density_indices,
        framework_density_trace_indices=framework_density_indices,
        density_trace_provenance=density_trace_provenance,
        render_metadata={
            "trajectory_trace_count": sum(len(value) for value in traces.values()),
            "atomic_mean_graph_trace_count": sum(
                len(value) for value in atomic_mean_graph_trace_indices.values()
            ),
            "endpoint_trace_count": len(endpoint_indices),
            "trajectory_display_mode": (
                None if paths is None else paths.display_mode.value
            ),
            "atomic_density_field_count": len(scene.atomic_density_fields),
            "framework_density_field_count": len(framework_fields),
            "density_trace_count": (
                sum(len(v) for v in density_indices.values())
                + sum(len(v) for v in framework_density_indices.values())
            ),
            "density_trace_provenance": {
                str(index): provenance.to_json_dict()
                for index, provenance in sorted(density_trace_provenance.items())
            },
            "density_node_clouds": density_cloud_metadata,
            "density_meshes": density_mesh_metadata,
            "density_scene_budget_plan": (
                None if scene_budget_plan is None else scene_budget_plan.to_json_dict()
            ),
            "density_scene_fit_report": (
                None if density_scene_fit_report is None else density_scene_fit_report.to_json_dict()
            ),
            "browser_mesh_profile": resolved_mesh_profile.to_json_dict(),
            "topology_category_trace_indices": {
                str(key): list(value) for key, value in sorted(topology_category_trace_indices.items())
            },
            "topology_category_count": len(scene.topology_categories),
            "topology_category_trace_adapter": (
                "compact_four_trace_v1" if scene.topology_categories else None
            ),
            "topology_category_trace_count": sum(
                len(value) for value in topology_category_trace_indices.values()
            ),
            "density_mesh_execution": (
                None
                if density_mesh_execution_report is None
                else density_mesh_execution_report.to_json_dict()
            ),
            "browser_budget_report_pre_html": browser_budget_report_pre_html.to_json_dict(),
            "runtime_resource_budget": scene.resources.runtime_budget.to_json_dict(),
            "estimated_mesh_wall_seconds": estimated_mesh_wall_seconds,
            "wall_time_admission_enforced": False,
            "wall_time_target_seconds": float(scene.resources.max_wall_time_seconds),
            "wall_time_target_exceeded": bool(
                complete_scene_wall_seconds > float(scene.resources.max_wall_time_seconds)
            ),
            "estimated_render_peak_bytes": estimated_render_peak_bytes,
            "parent_scene_retained_bytes": parent_scene_retained_bytes,
            "final_output_reserve_bytes": final_output_reserve_bytes,
            "preparation_wall_seconds": preparation_wall_seconds,
            "render_wall_seconds": render_wall_seconds,
            "complete_scene_wall_seconds": complete_scene_wall_seconds,
            "mesh_execution_options": resolved_mesh_execution_options.to_json_dict(),
            "compact_plotly_geometry": {
                "mesh_vertex_dtype": "float32",
                "mesh_index_dtype": "int32",
                "mesh_hover": "disabled",
                "trajectory_grouping": (
                    "species" if trajectory_options.group_by_species else "atom"
                ),
            },
        },
        browser_budget=resolved_browser_budget,
        browser_profile=browser_profile,
        browser_usage=browser_usage_pre_html,
        browser_budget_report=browser_budget_report_pre_html,
    )
